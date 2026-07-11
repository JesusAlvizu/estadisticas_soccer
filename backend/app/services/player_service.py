"""Player service."""
from loguru import logger

from app.repositories.player_repository import PlayerRepository
from app.services.base import BaseService


class PlayerService(BaseService):
    """Player service for business logic."""

    def __init__(self, repository: PlayerRepository):
        """Initialize player service."""
        super().__init__(repository)

    async def get_player_by_name(self, name: str):
        """Get player by name."""
        logger.info(f"Searching player: {name}")
        player = await self.repository.get_by_name(name)
        if not player:
            logger.warning(f"Player not found: {name}")
        return player

    async def get_team_players(
        self, team_id: int, skip: int = 0, limit: int = 10
    ):
        """Get all players from a team."""
        logger.info(f"Fetching players from team {team_id}")
        players, count = await self.repository.get_team_players(
            team_id, skip=skip, limit=limit
        )
        logger.info(f"Found {len(players)} players in team {team_id}")
        return players

    async def get_player_performance(self, player_id: int, season_id: int):
        """Get player performance for a season."""
        logger.info(f"Analyzing player {player_id} for season {season_id}")
        
        stats = await self.repository.get_player_stats(player_id, season_id)
        if not stats:
            logger.warning(f"Stats not found for player {player_id} in season {season_id}")
            return None

        goal_per_match = (
            stats.goals / stats.matches_played if stats.matches_played > 0 else 0
        )
        assists_per_match = (
            stats.assists / stats.matches_played if stats.matches_played > 0 else 0
        )
        shot_accuracy = (
            stats.shots_on_target / stats.shots if stats.shots > 0 else 0
        )

        return {
            "player_id": player_id,
            "season_id": season_id,
            "matches_played": stats.matches_played,
            "goals": stats.goals,
            "assists": stats.assists,
            "goals_per_match": goal_per_match,
            "assists_per_match": assists_per_match,
            "shot_accuracy": shot_accuracy,
            "expected_goals": stats.expected_goals,
            "pass_accuracy": stats.pass_accuracy,
        }
