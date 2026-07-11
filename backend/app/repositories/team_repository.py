"""Team repository."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Team, TeamSeason, Season
from app.repositories.base import BaseRepository


class TeamRepository(BaseRepository[Team]):
    """Team repository for data access."""

    def __init__(self, session: AsyncSession):
        """Initialize team repository."""
        super().__init__(session, Team)

    async def get_by_code(self, code: str) -> Team | None:
        """Get team by code."""
        result = await self.session.execute(
            select(Team).where(Team.code == code)
        )
        return result.scalar_one_or_none()

    async def get_team_season_stats(
        self, team_id: int, season_id: int
    ) -> TeamSeason | None:
        """Get team season statistics."""
        result = await self.session.execute(
            select(TeamSeason).where(
                (TeamSeason.team_id == team_id)
                & (TeamSeason.season_id == season_id)
            )
        )
        return result.scalar_one_or_none()

    async def get_last_seasons(self, team_id: int, count: int = 5) -> list:
        """Get last N seasons for a team."""
        result = await self.session.execute(
            select(TeamSeason)
            .where(TeamSeason.team_id == team_id)
            .order_by(TeamSeason.season_id.desc())
            .limit(count)
        )
        return result.scalars().all()
