"""
train_model.py — Train collaborative filtering model on RetailRocket dataset.

RetailRocket Kaggle Dataset:
  https://www.kaggle.com/datasets/retailrocket/ecommerce-dataset

Expected input files in data/:
  - events.csv        (visitor_id, timestamp, event, itemid, transactionid)
  - item_properties_part1.csv / part2.csv (itemid, timestamp, property, value)
  - category_tree.csv (categoryid, parentid)

Usage:
  python training/train_model.py --data-dir data/ --output-dir training/models/
"""

import argparse
import os
import pickle
import logging
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.models.recommender import CollaborativeFilteringRecommender
from app.utils.metrics import evaluate_model

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)


def load_retailrocket_events(data_dir: str) -> pd.DataFrame:
    """Load and preprocess RetailRocket events.csv."""
    events_path = os.path.join(data_dir, "events.csv")
    logger.info(f"Loading events from {events_path}")

    df = pd.read_csv(events_path)
    # Normalize column names
    df.columns = [c.lower().strip() for c in df.columns]

    # RetailRocket columns: visitorid, timestamp, event, itemid, transactionid
    rename_map = {
        "visitorid": "visitor_id",
        "itemid": "item_id",
        "event": "event",
        "timestamp": "timestamp",
    }
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

    # Convert timestamps
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", errors="coerce")
    df = df.dropna(subset=["visitor_id", "item_id"])
    df["visitor_id"] = df["visitor_id"].astype(str)
    df["item_id"] = df["item_id"].astype(str)

    logger.info(f"Loaded {len(df):,} events | {df['visitor_id'].nunique():,} visitors | {df['item_id'].nunique():,} items")
    return df


def generate_synthetic_data(n_interactions: int = 50000) -> pd.DataFrame:
    """
    Generate synthetic RetailRocket-style data for testing
    when the actual dataset is not available.
    """
    logger.info(f"Generating {n_interactions:,} synthetic interactions...")
    rng = np.random.default_rng(42)

    n_users = 5000
    n_items = 1000
    events = ["view", "view", "view", "addtocart", "transaction"]  # realistic distribution

    df = pd.DataFrame({
        "visitor_id": [str(rng.integers(1, n_users)) for _ in range(n_interactions)],
        "item_id": [str(rng.integers(1, n_items)) for _ in range(n_interactions)],
        "event": rng.choice(events, size=n_interactions),
        "timestamp": pd.date_range("2024-01-01", periods=n_interactions, freq="1min"),
    })
    return df


def train_test_split_temporal(df: pd.DataFrame, test_ratio: float = 0.2):
    """Split by time — train on older, test on newer interactions."""
    cutoff = df["timestamp"].quantile(1 - test_ratio)
    train = df[df["timestamp"] <= cutoff]
    test = df[df["timestamp"] > cutoff]
    logger.info(f"Train: {len(train):,} | Test: {len(test):,}")
    return train, test


def main(data_dir: str, output_dir: str, use_synthetic: bool = False):
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # Load data
    if use_synthetic or not os.path.exists(os.path.join(data_dir, "events.csv")):
        logger.warning("events.csv not found — using synthetic data")
        df = generate_synthetic_data(50000)
    else:
        df = load_retailrocket_events(data_dir)

    # Temporal split
    train_df, test_df = train_test_split_temporal(df, test_ratio=0.2)

    # Train
    model = CollaborativeFilteringRecommender(top_n=10)
    train_records = train_df[["visitor_id", "item_id", "event"]].to_dict("records")
    model.fit(train_records)

    # Evaluate Precision@10
    test_records = test_df[["visitor_id", "item_id", "event"]].to_dict("records")

    # Build ground truth
    ground_truth = {}
    for row in test_records:
        ground_truth.setdefault(row["visitor_id"], set()).add(row["item_id"])

    # Sample up to 2000 users for speed
    sampled_users = list(ground_truth.keys())[:2000]
    recommendations = {
        uid: [r["item_id"] for r in model.recommend(uid)]
        for uid in sampled_users
    }

    from app.utils.metrics import evaluate_model
    metrics = evaluate_model(recommendations, ground_truth, k=10)

    logger.info("=" * 50)
    logger.info("Evaluation Results:")
    for k, v in metrics.items():
        logger.info(f"  {k}: {v}")
    logger.info("=" * 50)

    # Save model
    model_path = os.path.join(output_dir, "recommender_model.pkl")
    model.save(model_path)

    # Save metrics
    metrics_path = os.path.join(output_dir, "metrics.json")
    import json
    with open(metrics_path, "w") as f:
        json.dump({
            **metrics,
            "trained_at": datetime.utcnow().isoformat(),
            "train_size": len(train_df),
            "test_size": len(test_df),
            "n_users": df["visitor_id"].nunique(),
            "n_items": df["item_id"].nunique(),
        }, f, indent=2)

    logger.info(f"Model saved to {model_path}")
    logger.info(f"Metrics saved to {metrics_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train RetailRocket recommendation model")
    parser.add_argument("--data-dir", default="data/", help="Path to RetailRocket data directory")
    parser.add_argument("--output-dir", default="training/models/", help="Path to save model")
    parser.add_argument("--synthetic", action="store_true", help="Use synthetic data for testing")
    args = parser.parse_args()

    main(data_dir=args.data_dir, output_dir=args.output_dir, use_synthetic=args.synthetic)
