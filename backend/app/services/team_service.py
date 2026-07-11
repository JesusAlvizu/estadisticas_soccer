"""Team service."""
from loguru import logger

from app.repositories.team_repository import TeamRepository
from app.services.base import BaseService


class TeamService(BaseService):
    """Team service for business logic."""

    def __init__(self, repository: TeamRepository):
        """Initialize team service."""
        super().__init__(repository)

    async def get_team_by_code(self, code: str):
        """Get team by code."""
        logger.info(f"Fetching team with code: {code}")
        team = await self.repository.get_by_code(code)
        if not team:
            logger.warning(f"Team not found with code: {code}")
        return team

    async def get_team_performance(self, team_id: int, seasons: int = 5):
        """Get team performance over N seasons."""
        logger.info(f"Analyzing team {team_id} performance over {seasons} seasons")
        
        seasons_data = await self.repository.get_last_seasons(team_id, seasons)
        
        if not seasons_data:
            logger.warning(f"No season data found for team {team_id}")
            return None

        # Calculate averages
        avg_goals = sum(s.goals_for for s in seasons_data) / len(seasons_data)
        avg_goals_against = sum(s.goals_against for s in seasons_data) / len(seasons_data)
        avg_points = sum(s.points for s in seasons_data) / len(seasons_data)
        win_rate = sum(s.wins for s in seasons_data) / sum(s.matches_played for s in seasons_data) if sum(s.matches_played for s in seasons_data) > 0 else 0

        return {
            "team_id": team_id,
            "seasons": seasons,
            "avg_goals_for": avg_goals,
            "avg_goals_against": avg_goals_against,
            "avg_points": avg_points,
            "win_rate": win_rate,
            "total_matches": sum(s.matches_played for s in seasons_data),
        }
