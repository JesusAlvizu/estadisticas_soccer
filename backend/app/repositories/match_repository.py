"""Match repository."""
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from app.models.models import Match, Prediction, SimulationResult
from app.repositories.base import BaseRepository


class MatchRepository(BaseRepository[Match]):
    """Match repository for data access."""

    def __init__(self, session: AsyncSession):
        """Initialize match repository."""
        super().__init__(session, Match)

    async def get_upcoming_matches(self, limit: int = 10) -> list:
        """Get upcoming matches."""
        result = await self.session.execute(
            select(Match)
            .where(
                and_(
                    Match.match_date > datetime.utcnow(),
                    Match.status == "scheduled"
                )
            )
            .order_by(Match.match_date.asc())
            .limit(limit)
        )
        return result.scalars().all()

    async def get_match_predictions(self, match_id: int) -> list:
        """Get all predictions for a match."""
        result = await self.session.execute(
            select(Prediction).where(Prediction.match_id == match_id)
        )
        return result.scalars().all()

    async def get_match_simulation(
        self, match_id: int
    ) -> SimulationResult | None:
        """Get simulation results for a match."""
        result = await self.session.execute(
            select(SimulationResult).where(
                SimulationResult.match_id == match_id
            )
        )
        return result.scalar_one_or_none()
