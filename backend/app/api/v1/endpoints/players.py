"""Players endpoints."""
from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def get_players():
    """Get all players."""
    return {"message": "Players endpoint"}


@router.post("/")
async def create_player():
    """Create a new player."""
    return {"message": "Create player endpoint"}
