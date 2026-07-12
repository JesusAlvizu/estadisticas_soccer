"""API-Football Adapter implementation."""
import httpx
import json
import os
import re
from datetime import datetime, timezone
from typing import List
from loguru import logger

from app.adapters import BaseAdapter, TeamDTO, MatchDTO, PlayerDTO
from app.core.config.settings import get_settings


settings = get_settings()


class APIFootballAdapter(BaseAdapter):
    """Adapter for API-Football (RapidAPI)."""

    BASE_URL = "https://v3.football.api-sports.io"

    def _headers(self) -> dict:
        """Build API-Football auth headers."""
        return {"x-apisports-key": self.api_key}

    def _quota_file(self) -> str:
        return settings.API_FOOTBALL_QUOTA_FILE

    def _daily_limit(self) -> int:
        return settings.API_FOOTBALL_DAILY_LIMIT

    def _today_str(self) -> str:
        return datetime.utcnow().strftime("%Y-%m-%d")

    def _load_quota(self) -> dict:
        """Load persisted daily counter from local file."""
        path = self._quota_file()
        if not path:
            return {"date": self._today_str(), "used": 0}
        if not os.path.exists(path):
            return {"date": self._today_str(), "used": 0}

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if not isinstance(data, dict):
                    return {"date": self._today_str(), "used": 0}
                return {
                    "date": str(data.get("date", self._today_str())),
                    "used": int(data.get("used", 0)),
                }
        except Exception:
            return {"date": self._today_str(), "used": 0}

    def _save_quota(self, quota: dict) -> None:
        """Persist daily counter to local file."""
        path = self._quota_file()
        if not path:
            return
        folder = os.path.dirname(path)
        if folder:
            os.makedirs(folder, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(quota, f)

    def _get_local_usage(self) -> dict:
        """Get local usage, auto-resetting when UTC date changes."""
        quota = self._load_quota()
        today = self._today_str()
        if quota.get("date") != today:
            quota = {"date": today, "used": 0}
            self._save_quota(quota)
        return quota

    def _consume_quota(self, endpoint: str, units: int = 1) -> None:
        """Consume request units from daily quota and fail fast at limit."""
        quota = self._get_local_usage()
        used = int(quota.get("used", 0))
        limit = self._daily_limit()
        if used + units > limit:
            raise RuntimeError(
                f"API_FOOTBALL_DAILY_LIMIT reached ({used}/{limit}). "
                f"Blocked endpoint: {endpoint}"
            )
        quota["used"] = used + units
        self._save_quota(quota)

    def get_local_usage_summary(self) -> dict:
        """Return local usage snapshot for current UTC day."""
        quota = self._get_local_usage()
        used = int(quota.get("used", 0))
        limit = self._daily_limit()
        return {
            "date": quota["date"],
            "used": used,
            "limit": limit,
            "remaining": max(0, limit - used),
        }

    def sync_local_usage_with_remote(self, remote_current: int) -> dict:
        """Keep local counter aligned with remote usage to avoid overconsumption."""
        quota = self._get_local_usage()
        used = int(quota.get("used", 0))
        adjusted = max(used, int(remote_current))
        if adjusted != used:
            quota["used"] = adjusted
            self._save_quota(quota)
        return self.get_local_usage_summary()

    async def get_usage_status(self) -> dict:
        """Return local usage and API status when available."""
        local = self._get_local_usage()
        remote = {}
        try:
            # status endpoint provides account usage in API-Football.
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/status",
                    headers=self._headers(),
                    timeout=10.0,
                )
                response.raise_for_status()
                remote = response.json()
        except Exception as e:
            logger.warning(f"Could not fetch remote API-Football status: {e}")

        return {
            "local": {
                "date": local["date"],
                "used": local["used"],
                "limit": self._daily_limit(),
                "remaining": max(0, self._daily_limit() - int(local["used"])),
            },
            "remote": remote,
        }

    @staticmethod
    def _parse_round_number(round_label: str) -> int:
        """Extract round number from labels like 'Regular Season - 5'."""
        if not round_label:
            return 0
        match = re.search(r"(\d+)", round_label)
        return int(match.group(1)) if match else 0

    @staticmethod
    def _parse_match_date(value: str) -> datetime:
        """Parse API datetime string to Python datetime."""
        if not value:
            return datetime.utcnow()
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is not None:
            return parsed.astimezone(timezone.utc).replace(tzinfo=None)
        return parsed

    async def get_teams(self, league_id: int, season: int | None = None) -> List[TeamDTO]:
        """Get teams from API-Football."""
        logger.info(
            "Fetching teams from API-Football for league {}{}",
            league_id,
            f", season {season}" if season else "",
        )
        
        try:
            self._consume_quota(endpoint="/teams")
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/teams",
                    params={
                        "league": league_id,
                        **({"season": season} if season is not None else {}),
                    },
                    headers=self._headers(),
                    timeout=10.0,
                )
                response.raise_for_status()
                data = response.json()

                teams = []
                for team_data in data.get("response", []):
                    team_info = team_data["team"]
                    team_code = team_info.get("code") or f"TM{team_info['id']}"
                    teams.append(
                        TeamDTO(
                            id=team_info["id"],
                            name=team_info["name"],
                            code=team_code,
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
            self._consume_quota(endpoint="/fixtures")
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/fixtures",
                    params={"league": league_id, "season": season},
                    headers=self._headers(),
                    timeout=10.0,
                )
                response.raise_for_status()
                data = response.json()

                matches = []
                for match_data in data.get("response", []):
                    fixture = match_data["fixture"]
                    goals = match_data["goals"]
                    round_label = match_data.get("league", {}).get("round", "")
                    
                    matches.append(
                        MatchDTO(
                            id=fixture["id"],
                            home_team_id=match_data["teams"]["home"]["id"],
                            away_team_id=match_data["teams"]["away"]["id"],
                            match_date=self._parse_match_date(fixture.get("date")),
                            league_id=league_id,
                            round_number=self._parse_round_number(round_label),
                            home_goals=goals.get("home"),
                            away_goals=goals.get("away"),
                            status=fixture.get("status", {}).get("short", "SCHEDULED"),
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
            self._consume_quota(endpoint="/players/squads")
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/players/squads",
                    params={"team": team_id},
                    headers=self._headers(),
                    timeout=10.0,
                )
                response.raise_for_status()
                data = response.json()

                players = []
                for squad_data in data.get("response", []):
                    for player_info in squad_data.get("players", []):
                        players.append(
                            PlayerDTO(
                                id=player_info["id"],
                                name=player_info.get("name", "Unknown"),
                                position=player_info.get("position", "Unknown"),
                                team_id=team_id,
                                shirt_number=player_info.get("number"),
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
            self._consume_quota(endpoint="/standings")
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/standings",
                    params={"league": league_id, "season": season},
                    headers=self._headers(),
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
            self._consume_quota(endpoint="/fixtures/statistics")
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/fixtures/statistics",
                    params={"fixture": match_id, "team": team_id},
                    headers=self._headers(),
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
            self._consume_quota(endpoint="/injuries")
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/injuries",
                    params={"team": team_id},
                    headers=self._headers(),
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
            self._consume_quota(endpoint="/transfers")
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/transfers",
                    params={"team": team_id},
                    headers=self._headers(),
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
            self._consume_quota(endpoint="/odds")
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/odds",
                    params={"fixture": match_id},
                    headers=self._headers(),
                    timeout=10.0,
                )
                response.raise_for_status()
                data = response.json()
                return data.get("response", [])

        except Exception as e:
            logger.error(f"Error fetching odds from API-Football: {e}")
            return []
