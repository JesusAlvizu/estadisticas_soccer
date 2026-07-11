"""Player repository."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Player, PlayerStatistic
from app.repositories.base import BaseRepository


class PlayerRepository(BaseRepository[Player]):
    """Player repository for data access."""

    def __init__(self, session: AsyncSession):
        """Initialize player repository."""
        super().__init__(session, Player)

    async def get_by_name(self, name: str) -> Player | None:
        """Get player by name."""
        result = await self.session.execute(
            select(Player).where(Player.name == name)
        )
        return result.scalar_one_or_none()

    async def get_team_players(
        self, team_id: int, skip: int = 0, limit: int = 10
    ) -> tuple[list, int]:
        """Get players by team."""
        return await self.get_all_where(
            Player.team_id == team_id, skip=skip, limit=limit
        )

    async def get_all_where(
        self, condition, skip: int = 0, limit: int = 10
    ) -> tuple[list, int]:
        """Get all records matching condition."""
        result = await self.session.execute(
            select(Player).where(condition).offset(skip).limit(limit)
        )
        records = result.scalars().all()
        return records, len(records)

    async def get_player_stats(
        self, player_id: int, season_id: int
    ) -> PlayerStatistic | None:
        """Get player statistics for a season."""
        result = await self.session.execute(
            select(PlayerStatistic).where(
                (PlayerStatistic.player_id == player_id)
                & (PlayerStatistic.season_id == season_id)
            )
        )
        return result.scalar_one_or_none()
