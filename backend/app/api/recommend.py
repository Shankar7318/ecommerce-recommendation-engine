from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional

from app.services.recommendation_service import recommendation_service
from app.services.ab_test_service import ab_test_service

router = APIRouter(prefix="/recommend", tags=["recommendations"])


class RecommendationResponse(BaseModel):
    visitor_id: str
    model_variant: str
    recommendations: list
    count: int
    latency_ms: float
    cache_hit: bool


@router.get("/{visitor_id}", response_model=RecommendationResponse)
async def get_recommendations(
    visitor_id: str,
    ab_test: bool = Query(default=True, description="Enable A/B variant assignment"),
    model_variant: Optional[str] = Query(default=None, description="Force specific variant (model_a/model_b)"),
):
    """
    Get top-10 product recommendations for a visitor.
    - Assigns A/B variant deterministically by visitor_id
    - Returns enriched product metadata
    - Cached in Redis for 5 minutes
    """
    try:
        # Determine variant
        if model_variant in ("model_a", "model_b"):
            variant = model_variant
        elif ab_test:
            variant = ab_test_service.assign_variant(visitor_id)
        else:
            variant = "model_a"

        result = await recommendation_service.get_recommendations(
            visitor_id=visitor_id,
            model_variant=variant,
            enrich=True,
        )

        # Record impression for A/B tracking
        if result["recommendations"] and not result["cache_hit"]:
            item_ids = [r["item_id"] for r in result["recommendations"]]
            avg_score = sum(r.get("score", 0) for r in result["recommendations"]) / max(len(item_ids), 1)
            await ab_test_service.record_impression(
                visitor_id=visitor_id,
                model_variant=variant,
                item_ids=item_ids,
                recommendation_score=avg_score,
            )

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
