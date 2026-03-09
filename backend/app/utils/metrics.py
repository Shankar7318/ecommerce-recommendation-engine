import numpy as np
from typing import List, Dict, Set


def precision_at_k(recommended: List[str], relevant: Set[str], k: int = 10) -> float:
    """Precision@K for a single user."""
    if not recommended or not relevant:
        return 0.0
    recommended_k = recommended[:k]
    hits = sum(1 for item in recommended_k if item in relevant)
    return hits / k


def recall_at_k(recommended: List[str], relevant: Set[str], k: int = 10) -> float:
    """Recall@K for a single user."""
    if not recommended or not relevant:
        return 0.0
    recommended_k = recommended[:k]
    hits = sum(1 for item in recommended_k if item in relevant)
    return hits / len(relevant)


def ndcg_at_k(recommended: List[str], relevant: Set[str], k: int = 10) -> float:
    """Normalized Discounted Cumulative Gain @ K."""
    recommended_k = recommended[:k]
    dcg = sum(
        (1 / np.log2(i + 2)) for i, item in enumerate(recommended_k) if item in relevant
    )
    ideal_hits = min(len(relevant), k)
    idcg = sum(1 / np.log2(i + 2) for i in range(ideal_hits))
    return dcg / idcg if idcg > 0 else 0.0


def evaluate_model(
    recommendations: Dict[str, List[str]],
    ground_truth: Dict[str, Set[str]],
    k: int = 10,
) -> Dict[str, float]:
    """
    Evaluate across all users.
    recommendations: {visitor_id: [item_id, ...]}
    ground_truth: {visitor_id: {item_id, ...}}
    """
    precisions, recalls, ndcgs = [], [], []

    for uid, rec_items in recommendations.items():
        relevant = ground_truth.get(uid, set())
        if not relevant:
            continue
        precisions.append(precision_at_k(rec_items, relevant, k))
        recalls.append(recall_at_k(rec_items, relevant, k))
        ndcgs.append(ndcg_at_k(rec_items, relevant, k))

    return {
        f"precision@{k}": round(float(np.mean(precisions)), 4) if precisions else 0.0,
        f"recall@{k}": round(float(np.mean(recalls)), 4) if recalls else 0.0,
        f"ndcg@{k}": round(float(np.mean(ndcgs)), 4) if ndcgs else 0.0,
        "num_users_evaluated": len(precisions),
    }
