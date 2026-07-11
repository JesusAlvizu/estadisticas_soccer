"""Match service."""
from datetime import datetime, timedelta
from loguru import logger

from app.repositories.match_repository import MatchRepository
from app.services.base import BaseService


class MatchService(BaseService):
    """Match service for business logic."""

    def __init__(self, repository: MatchRepository):
        """Initialize match service."""
        super().__init__(repository)

    async def get_upcoming_matches(self, limit: int = 10):
        """Get upcoming matches."""
        logger.info(f"Fetching {limit} upcoming matches")
        matches = await self.repository.get_upcoming_matches(limit=limit)
        logger.info(f"Found {len(matches)} upcoming matches")
        return matches

    async def get_match_predictions(self, match_id: int):
        """Get all predictions for a match."""
        logger.info(f"Fetching predictions for match {match_id}")
        predictions = await self.repository.get_match_predictions(match_id)
        logger.info(f"Found {len(predictions)} predictions for match {match_id}")
        return predictions

    async def get_match_analysis(self, match_id: int):
        """Get complete analysis for a match."""
        logger.info(f"Analyzing match {match_id}")
        
        match = await self.repository.get(match_id)
        if not match:
            logger.warning(f"Match {match_id} not found")
            return None

        predictions = await self.repository.get_match_predictions(match_id)
        simulation = await self.repository.get_match_simulation(match_id)

        return {
            "match_id": match_id,
            "home_team": match.home_team_id,
            "away_team": match.away_team_id,
            "match_date": match.match_date,
            "predictions_count": len(predictions),
            "has_simulation": simulation is not None,
            "predictions": predictions,
            "simulation": simulation,
        }
