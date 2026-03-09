"""
recommendation_service.py — Core inference layer with Redis caching.
"""

import logging
import time
from typing import Dict, Optional

from app.models.recommender import CollaborativeFilteringRecommender
from app.database.mongodb import get_products_bulk
from app.database.redis_cache import cache_get, cache_set, cache_delete, rec_cache_key
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class RecommendationService:
    def __init__(self):
        self.model_a: Optional[CollaborativeFilteringRecommender] = None
        self.model_b: Optional[CollaborativeFilteringRecommender] = None

    async def initialize(self):
        try:
            self.model_a = CollaborativeFilteringRecommender.load(settings.MODEL_PATH)
            logger.info("Model A loaded")
        except FileNotFoundError:
            logger.warning(f"Model not found at {settings.MODEL_PATH} — cold-start mode active")
            self.model_a = CollaborativeFilteringRecommender(top_n=settings.TOP_N_RECOMMENDATIONS)
        self.model_b = self.model_a

    async def get_recommendations(self, visitor_id: str, model_variant: str = "model_a", enrich: bool = True) -> Dict:
        cache_key = rec_cache_key(visitor_id, model_variant)
        cached = await cache_get(cache_key)
        if cached:
            cached["cache_hit"] = True
            return cached

        t0 = time.perf_counter()
        model = self.model_a if model_variant == "model_a" else self.model_b
        raw_recs = model.recommend(visitor_id) if (model and model.is_trained) else []
        latency_ms = round((time.perf_counter() - t0) * 1000, 2)

        if enrich and raw_recs:
            item_ids = [r["item_id"] for r in raw_recs]
            products = await get_products_bulk(item_ids)
            product_map = {p["item_id"]: p for p in products}
            for rec in raw_recs:
                rec.update(product_map.get(rec["item_id"], {}))

        result = {
            "visitor_id": visitor_id,
            "model_variant": model_variant,
            "recommendations": raw_recs,
            "count": len(raw_recs),
            "latency_ms": latency_ms,
            "cache_hit": False,
        }
        if raw_recs:
            await cache_set(cache_key, result, ttl=settings.REDIS_CACHE_TTL)
        return result

    async def invalidate_cache(self, visitor_id: str) -> None:
        await cache_delete(rec_cache_key(visitor_id, "model_a"), rec_cache_key(visitor_id, "model_b"))


recommendation_service = RecommendationService()
