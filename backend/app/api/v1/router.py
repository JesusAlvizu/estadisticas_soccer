"""API v1 router configuration."""
from fastapi import APIRouter

from app.api.v1.endpoints import health, teams, matches, players, predictions

api_router = APIRouter()

# Include endpoint routers
api_router.include_router(health.router, prefix="/health", tags=["Health"])
api_router.include_router(teams.router, prefix="/teams", tags=["Teams"])
api_router.include_router(matches.router, prefix="/matches", tags=["Matches"])
api_router.include_router(players.router, prefix="/players", tags=["Players"])
api_router.include_router(predictions.router, prefix="/predictions", tags=["Predictions"])
