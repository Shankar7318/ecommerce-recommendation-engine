from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.ab_test_service import ab_test_service

router = APIRouter(prefix="/ab-test", tags=["ab-testing"])


class ClickEvent(BaseModel):
    visitor_id: str
    item_id: str


class ConversionEvent(BaseModel):
    visitor_id: str
    item_id: str


@router.get("/metrics")
async def get_ab_test_metrics():
    """
    Return aggregated A/B test metrics:
    - CTR per variant
    - Conversion rate per variant
    - Recommendation lift (model_b vs model_a)
    """
    try:
        return await ab_test_service.get_metrics()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/click")
async def record_click(event: ClickEvent):
    """Record a click event for A/B tracking."""
    try:
        await ab_test_service.record_click(event.visitor_id, event.item_id)
        return {"success": True, "message": "Click recorded"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/conversion")
async def record_conversion(event: ConversionEvent):
    """Record a purchase/conversion for A/B tracking."""
    try:
        await ab_test_service.record_conversion(event.visitor_id, event.item_id)
        return {"success": True, "message": "Conversion recorded"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/variant/{visitor_id}")
async def get_visitor_variant(visitor_id: str):
    """Check which A/B variant a visitor is assigned to."""
    variant = ab_test_service.assign_variant(visitor_id)
    return {"visitor_id": visitor_id, "assigned_variant": variant}
