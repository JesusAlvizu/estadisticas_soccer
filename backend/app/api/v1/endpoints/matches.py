"""Matches endpoints."""
from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def get_matches():
    """Get all matches."""
    return {"message": "Matches endpoint"}


@router.post("/")
async def create_match():
    """Create a new match."""
    return {"message": "Create match endpoint"}
