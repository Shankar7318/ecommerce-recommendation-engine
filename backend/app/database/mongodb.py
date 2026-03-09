from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import IndexModel, ASCENDING, DESCENDING
from typing import Optional, List, Dict, Any
import logging
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class MongoDB:
    client: Optional[AsyncIOMotorClient] = None
    db = None


db_instance = MongoDB()


async def connect_db():
    """Create MongoDB connection with pooling."""
    db_instance.client = AsyncIOMotorClient(
        settings.MONGODB_URL,
        maxPoolSize=50,
        minPoolSize=10,
        maxIdleTimeMS=30000,
        waitQueueTimeoutMS=5000,
    )
    db_instance.db = db_instance.client[settings.MONGODB_DB]
    await _create_indexes()
    logger.info("Connected to MongoDB")


async def close_db():
    """Close MongoDB connection."""
    if db_instance.client:
        db_instance.client.close()
        logger.info("Disconnected from MongoDB")


async def _create_indexes():
    """Create optimized indexes for fast queries."""
    # Interactions collection indexes
    await db_instance.db.interactions.create_indexes([
        IndexModel([("visitor_id", ASCENDING)]),
        IndexModel([("item_id", ASCENDING)]),
        IndexModel([("timestamp", DESCENDING)]),
        IndexModel([("visitor_id", ASCENDING), ("item_id", ASCENDING)]),
    ])

    # Products collection indexes
    await db_instance.db.products.create_indexes([
        IndexModel([("item_id", ASCENDING)], unique=True),
        IndexModel([("category_id", ASCENDING)]),
    ])

    # AB test results indexes
    await db_instance.db.ab_test_results.create_indexes([
        IndexModel([("visitor_id", ASCENDING)]),
        IndexModel([("model_variant", ASCENDING)]),
        IndexModel([("timestamp", DESCENDING)]),
    ])
    logger.info("MongoDB indexes created")


def get_db():
    return db_instance.db


# ─── Interactions CRUD ──────────────────────────────────────────────────────

async def log_interaction(interaction: Dict[str, Any]) -> str:
    """Log a user-product interaction."""
    result = await db_instance.db.interactions.insert_one(interaction)
    return str(result.inserted_id)


async def get_user_interactions(visitor_id: str, limit: int = 100) -> List[Dict]:
    """Get recent interactions for a user."""
    cursor = db_instance.db.interactions.find(
        {"visitor_id": visitor_id},
        {"_id": 0}
    ).sort("timestamp", DESCENDING).limit(limit)
    return await cursor.to_list(length=limit)


async def get_interaction_matrix_sample(limit: int = 50000) -> List[Dict]:
    """Fetch interaction matrix sample for model training."""
    cursor = db_instance.db.interactions.find(
        {},
        {"visitor_id": 1, "item_id": 1, "event": 1, "timestamp": 1, "_id": 0}
    ).limit(limit)
    return await cursor.to_list(length=limit)


# ─── Products CRUD ──────────────────────────────────────────────────────────

async def get_product(item_id: str) -> Optional[Dict]:
    """Fetch product details by item_id."""
    return await db_instance.db.products.find_one(
        {"item_id": item_id}, {"_id": 0}
    )


async def get_products_bulk(item_ids: List[str]) -> List[Dict]:
    """Fetch multiple products by item_ids."""
    cursor = db_instance.db.products.find(
        {"item_id": {"$in": item_ids}},
        {"_id": 0}
    )
    return await cursor.to_list(length=len(item_ids))


async def upsert_product(product: Dict[str, Any]) -> None:
    """Upsert a product record."""
    await db_instance.db.products.update_one(
        {"item_id": product["item_id"]},
        {"$set": product},
        upsert=True
    )


# ─── A/B Test CRUD ──────────────────────────────────────────────────────────

async def log_ab_result(result: Dict[str, Any]) -> str:
    """Log an A/B test result."""
    res = await db_instance.db.ab_test_results.insert_one(result)
    return str(res.inserted_id)


async def get_ab_metrics() -> Dict[str, Any]:
    """Aggregate A/B test metrics per variant."""
    pipeline = [
        {
            "$group": {
                "_id": "$model_variant",
                "total_served": {"$sum": 1},
                "total_clicks": {"$sum": "$clicked"},
                "total_conversions": {"$sum": "$converted"},
                "avg_score": {"$avg": "$recommendation_score"},
            }
        },
        {
            "$project": {
                "variant": "$_id",
                "total_served": 1,
                "total_clicks": 1,
                "total_conversions": 1,
                "avg_score": 1,
                "ctr": {
                    "$cond": [
                        {"$eq": ["$total_served", 0]},
                        0,
                        {"$divide": ["$total_clicks", "$total_served"]}
                    ]
                },
                "conversion_rate": {
                    "$cond": [
                        {"$eq": ["$total_served", 0]},
                        0,
                        {"$divide": ["$total_conversions", "$total_served"]}
                    ]
                },
            }
        }
    ]
    cursor = db_instance.db.ab_test_results.aggregate(pipeline)
    results = await cursor.to_list(length=10)
    return {r["variant"]: r for r in results}
