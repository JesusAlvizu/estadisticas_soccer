"""Predictions endpoints."""
from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def get_predictions():
    """Get all predictions."""
    return {"message": "Predictions endpoint"}


@router.post("/")
async def create_prediction():
    """Create a new prediction."""
    return {"message": "Create prediction endpoint"}
