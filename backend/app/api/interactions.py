from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

from app.database.mongodb import log_interaction, get_user_interactions
from app.services.recommendation_service import recommendation_service

router = APIRouter(prefix="/interaction", tags=["interactions"])


class InteractionRequest(BaseModel):
    visitor_id: str
    item_id: str
    event: str = "view"  # view | addtocart | transaction
    timestamp: Optional[datetime] = None


class InteractionResponse(BaseModel):
    success: bool
    interaction_id: str
    message: str


@router.post("/", response_model=InteractionResponse)
async def log_user_interaction(interaction: InteractionRequest):
    """
    Log a user-product interaction event.
    Invalidates Redis cache for this user.

    Events: view (weight=1), addtocart (weight=3), transaction (weight=5)
    """
    try:
        doc = interaction.model_dump()
        doc["timestamp"] = doc["timestamp"] or datetime.utcnow()

        interaction_id = await log_interaction(doc)

        # Invalidate cache so next request gets fresh recommendations
        await recommendation_service.invalidate_cache(interaction.visitor_id)

        return {
            "success": True,
            "interaction_id": interaction_id,
            "message": f"Interaction logged for visitor {interaction.visitor_id}",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{visitor_id}")
async def get_visitor_history(visitor_id: str, limit: int = 50):
    """Retrieve interaction history for a visitor."""
    try:
        history = await get_user_interactions(visitor_id, limit=limit)
        return {"visitor_id": visitor_id, "interactions": history, "count": len(history)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
