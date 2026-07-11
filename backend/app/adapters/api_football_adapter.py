"""API-Football Adapter implementation."""
import httpx
from typing import List
from loguru import logger

from app.adapters import BaseAdapter, TeamDTO, MatchDTO, PlayerDTO


class APIFootballAdapter(BaseAdapter):
    """Adapter for API-Football (RapidAPI)."""

    BASE_URL = "https://v3.football.api-sports.io"

    async def get_teams(self, league_id: int) -> List[TeamDTO]:
        """Get teams from API-Football."""
        logger.info(f"Fetching teams from API-Football for league {league_id}")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/teams",
                    params={"league": league_id},
                    headers={"x-rapidapi-key": self.api_key},
                    timeout=10.0,
                )
                response.raise_for_status()
                data = response.json()

                teams = []
                for team_data in data.get("response", []):
                    team_info = team_data["team"]
                    teams.append(
                        TeamDTO(
                            id=team_info["id"],
                            name=team_info["name"],
                            code=team_info.get("code", team_info["name"][:3]),
                            country=team_info.get("country"),
                            logo_url=team_info.get("logo"),
                        )
                    )
                
                logger.info(f"Successfully fetched {len(teams)} teams")
                return teams

        except Exception as e:
            logger.error(f"Error fetching teams from API-Football: {e}")
            return []

    async def get_matches(
        self, league_id: int, season: int
    ) -> List[MatchDTO]:
        """Get matches from API-Football."""
        logger.info(
            f"Fetching matches from API-Football for league {league_id}, season {season}"
        )
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/fixtures",
                    params={"league": league_id, "season": season},
                    headers={"x-rapidapi-key": self.api_key},
                    timeout=10.0,
                )
                response.raise_for_status()
                data = response.json()

                matches = []
                for match_data in data.get("response", []):
                    fixture = match_data["fixture"]
                    goals = match_data["goals"]
                    
                    matches.append(
                        MatchDTO(
                            id=fixture["id"],
                            home_team_id=match_data["teams"]["home"]["id"],
                            away_team_id=match_data["teams"]["away"]["id"],
                            match_date=fixture["date"],
                            league_id=league_id,
                            round_number=int(
                                match_data["league"].get("round", "0").split("-")[0]
                            ),
                            home_goals=goals.get("home"),
                            away_goals=goals.get("away"),
                            status=fixture["status"]["short"],
                        )
                    )
                
                logger.info(f"Successfully fetched {len(matches)} matches")
                return matches

        except Exception as e:
            logger.error(f"Error fetching matches from API-Football: {e}")
            return []

    async def get_players(self, team_id: int) -> List[PlayerDTO]:
        """Get players from API-Football."""
        logger.info(f"Fetching players from API-Football for team {team_id}")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/players",
                    params={"team": team_id},
                    headers={"x-rapidapi-key": self.api_key},
                    timeout=10.0,
                )
                response.raise_for_status()
                data = response.json()

                players = []
                for player_data in data.get("response", []):
                    player_info = player_data["player"]
                    players.append(
                        PlayerDTO(
                            id=player_info["id"],
                            name=player_info["name"],
                            position=player_data["statistics"][0].get("position", "Unknown"),
                            team_id=team_id,
                            shirt_number=player_data["statistics"][0].get("number"),
                            nationality=player_info.get("nationality"),
                        )
                    )
                
                logger.info(f"Successfully fetched {len(players)} players")
                return players

        except Exception as e:
            logger.error(f"Error fetching players from API-Football: {e}")
            return []

    async def get_standings(self, league_id: int, season: int) -> dict:
        """Get league standings from API-Football."""
        logger.info(f"Fetching standings from API-Football for league {league_id}, season {season}")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/standings",
                    params={"league": league_id, "season": season},
                    headers={"x-rapidapi-key": self.api_key},
                    timeout=10.0,
                )
                response.raise_for_status()
                return response.json()

        except Exception as e:
            logger.error(f"Error fetching standings from API-Football: {e}")
            return {}

    async def get_statistics(self, match_id: int, team_id: int) -> dict:
        """Get match statistics from API-Football."""
        logger.info(f"Fetching stats for match {match_id}, team {team_id}")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/fixtures/statistics",
                    params={"fixture": match_id, "team": team_id},
                    headers={"x-rapidapi-key": self.api_key},
                    timeout=10.0,
                )
                response.raise_for_status()
                return response.json()

        except Exception as e:
            logger.error(f"Error fetching statistics from API-Football: {e}")
            return {}

    async def get_injuries(self, team_id: int) -> List[dict]:
        """Get injuries from API-Football."""
        logger.info(f"Fetching injuries for team {team_id}")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/injuries",
                    params={"team": team_id},
                    headers={"x-rapidapi-key": self.api_key},
                    timeout=10.0,
                )
                response.raise_for_status()
                data = response.json()
                return data.get("response", [])

        except Exception as e:
            logger.error(f"Error fetching injuries from API-Football: {e}")
            return []

    async def get_transfers(self, team_id: int) -> List[dict]:
        """Get transfers from API-Football."""
        logger.info(f"Fetching transfers for team {team_id}")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/transfers",
                    params={"team": team_id},
                    headers={"x-rapidapi-key": self.api_key},
                    timeout=10.0,
                )
                response.raise_for_status()
                data = response.json()
                return data.get("response", [])

        except Exception as e:
            logger.error(f"Error fetching transfers from API-Football: {e}")
            return []

    async def get_odds(self, match_id: int) -> List[dict]:
        """Get odds from API-Football."""
        logger.info(f"Fetching odds for match {match_id}")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/odds",
                    params={"fixture": match_id},
                    headers={"x-rapidapi-key": self.api_key},
                    timeout=10.0,
                )
                response.raise_for_status()
                data = response.json()
                return data.get("response", [])

        except Exception as e:
            logger.error(f"Error fetching odds from API-Football: {e}")
            return []
