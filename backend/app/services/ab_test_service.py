import hashlib
import logging
from datetime import datetime
from typing import Dict, Any

from app.database.mongodb import log_ab_result, get_ab_metrics
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class ABTestService:
    """
    Deterministic A/B variant assignment + metrics tracking.
    Uses MD5 hash of visitor_id for stable, reproducible splits.
    """

    def assign_variant(self, visitor_id: str) -> str:
        """
        Deterministically assign visitor to model_a or model_b.
        Same visitor always gets the same variant (no session drift).
        """
        hash_val = int(hashlib.md5(visitor_id.encode()).hexdigest(), 16)
        bucket = (hash_val % 100) / 100.0
        return "model_b" if bucket < settings.AB_TEST_SPLIT else "model_a"

    async def record_impression(
        self,
        visitor_id: str,
        model_variant: str,
        item_ids: list,
        recommendation_score: float = 0.0,
    ) -> None:
        """Log that recommendations were shown to this visitor."""
        await log_ab_result({
            "visitor_id": visitor_id,
            "model_variant": model_variant,
            "item_ids_shown": item_ids,
            "recommendation_score": recommendation_score,
            "clicked": 0,
            "converted": 0,
            "event_type": "impression",
            "timestamp": datetime.utcnow(),
        })

    async def record_click(self, visitor_id: str, item_id: str) -> None:
        """Record a click event for A/B metrics."""
        variant = self.assign_variant(visitor_id)
        await log_ab_result({
            "visitor_id": visitor_id,
            "model_variant": variant,
            "item_id_clicked": item_id,
            "clicked": 1,
            "converted": 0,
            "event_type": "click",
            "timestamp": datetime.utcnow(),
        })

    async def record_conversion(self, visitor_id: str, item_id: str) -> None:
        """Record a purchase/conversion for A/B metrics."""
        variant = self.assign_variant(visitor_id)
        await log_ab_result({
            "visitor_id": visitor_id,
            "model_variant": variant,
            "item_id_converted": item_id,
            "clicked": 1,
            "converted": 1,
            "event_type": "conversion",
            "timestamp": datetime.utcnow(),
        })

    async def get_metrics(self) -> Dict[str, Any]:
        """
        Retrieve aggregated A/B metrics from MongoDB.
        Calculates lift = (model_b_ctr / model_a_ctr) - 1
        """
        raw = await get_ab_metrics()

        metrics = {}
        for variant, data in raw.items():
            metrics[variant] = {
                "total_served": data.get("total_served", 0),
                "total_clicks": data.get("total_clicks", 0),
                "total_conversions": data.get("total_conversions", 0),
                "ctr": round(data.get("ctr", 0) * 100, 2),
                "conversion_rate": round(data.get("conversion_rate", 0) * 100, 2),
                "avg_score": round(data.get("avg_score", 0), 4),
            }

        # Compute lift
        if "model_a" in metrics and "model_b" in metrics:
            ctr_a = metrics["model_a"]["ctr"]
            ctr_b = metrics["model_b"]["ctr"]
            if ctr_a > 0:
                lift = round(((ctr_b - ctr_a) / ctr_a) * 100, 2)
                metrics["lift_percent"] = lift
            else:
                metrics["lift_percent"] = None

        return metrics


ab_test_service = ABTestService()
