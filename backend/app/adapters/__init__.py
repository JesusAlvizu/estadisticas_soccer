"""Base adapter for external APIs."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime


@dataclass
class TeamDTO:
    """Data Transfer Object for Team."""

    id: int
    name: str
    code: str
    country: Optional[str] = None
    logo_url: Optional[str] = None


@dataclass
class MatchDTO:
    """Data Transfer Object for Match."""

    id: int
    home_team_id: int
    away_team_id: int
    match_date: datetime
    league_id: int
    round_number: int
    home_goals: Optional[int] = None
    away_goals: Optional[int] = None
    status: str = "scheduled"


@dataclass
class PlayerDTO:
    """Data Transfer Object for Player."""

    id: int
    name: str
    position: str
    team_id: int
    shirt_number: Optional[int] = None
    nationality: Optional[str] = None


class BaseAdapter(ABC):
    """Base adapter for external sports APIs."""

    def __init__(self, api_key: str):
        """Initialize adapter."""
        self.api_key = api_key

    @abstractmethod
    async def get_teams(self, league_id: int) -> List[TeamDTO]:
        """Get teams from external API."""
        pass

    @abstractmethod
    async def get_matches(
        self, league_id: int, season: int
    ) -> List[MatchDTO]:
        """Get matches from external API."""
        pass

    @abstractmethod
    async def get_players(self, team_id: int) -> List[PlayerDTO]:
        """Get players from external API."""
        pass

    @abstractmethod
    async def get_standings(self, league_id: int, season: int) -> dict:
        """Get league standings from external API."""
        pass

    @abstractmethod
    async def get_statistics(
        self, match_id: int, team_id: int
    ) -> dict:
        """Get match statistics from external API."""
        pass

    @abstractmethod
    async def get_injuries(self, team_id: int) -> List[dict]:
        """Get injuries from external API."""
        pass

    @abstractmethod
    async def get_transfers(self, team_id: int) -> List[dict]:
        """Get transfers from external API."""
        pass

    @abstractmethod
    async def get_odds(self, match_id: int) -> List[dict]:
        """Get odds from external API."""
        pass
