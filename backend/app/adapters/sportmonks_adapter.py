"""Sportmonks Adapter implementation.

Primary provider for historical Liga MX ingestion.
"""
import httpx
import json
import os
from datetime import datetime
from typing import Any, List
from loguru import logger

from app.adapters import BaseAdapter, MatchDTO, PlayerDTO, TeamDTO
from app.core.config.settings import get_settings


settings = get_settings()


class SportmonksAdapter(BaseAdapter):
    """Adapter for Sportmonks Football API."""

    BASE_URL = settings.SPORTMONKS_BASE_URL

    def _quota_file(self) -> str:
        return settings.SPORTMONKS_QUOTA_FILE

    def _rate_file(self) -> str:
        return settings.SPORTMONKS_RATE_LIMIT_FILE

    def _daily_limit(self) -> int:
        return settings.SPORTMONKS_DAILY_LIMIT

    def _params_with_token(self, params: dict[str, Any] | None = None) -> dict[str, Any]:
        out = dict(params or {})
        out["api_token"] = self.api_key
        return out

    @staticmethod
    def _utc_now() -> datetime:
        return datetime.utcnow()

    def _today_str(self) -> str:
        return self._utc_now().strftime("%Y-%m-%d")

    @staticmethod
    def _load_json(path: str, fallback: dict) -> dict:
        if not path or not os.path.exists(path):
            return fallback
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else fallback
        except Exception:
            return fallback

    @staticmethod
    def _save_json(path: str, payload: dict) -> None:
        if not path:
            return
        folder = os.path.dirname(path)
        if folder:
            os.makedirs(folder, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f)

    def _get_local_quota(self) -> dict:
        quota = self._load_json(
            self._quota_file(),
            {"date": self._today_str(), "used": 0},
        )
        if quota.get("date") != self._today_str():
            quota = {"date": self._today_str(), "used": 0}
            self._save_json(self._quota_file(), quota)
        return quota

    def _consume_daily_quota(self, endpoint: str, units: int = 1) -> None:
        quota = self._get_local_quota()
        used = int(quota.get("used", 0))
        limit = self._daily_limit()
        if used + units > limit:
            raise RuntimeError(
                f"SPORTMONKS_DAILY_LIMIT reached ({used}/{limit}). Blocked endpoint: {endpoint}"
            )
        quota["used"] = used + units
        self._save_json(self._quota_file(), quota)

    def _rate_guard(self, endpoint: str) -> None:
        snapshot = self._load_json(self._rate_file(), {})
        remaining = snapshot.get("remaining")
        reset_epoch = snapshot.get("reset_epoch")
        now_epoch = int(self._utc_now().timestamp())
        if isinstance(remaining, int) and isinstance(reset_epoch, int):
            if now_epoch < reset_epoch and remaining <= 0:
                raise RuntimeError(
                    f"Sportmonks rate limit exhausted before reset. Blocked endpoint: {endpoint}"
                )

    def _update_rate_snapshot(self, response: httpx.Response, payload: dict | None = None) -> None:
        headers = response.headers
        limit_raw = headers.get("X-Ratelimit-Limit")
        remaining_raw = headers.get("X-Ratelimit-Remaining")

        limit = int(limit_raw) if isinstance(limit_raw, str) and limit_raw.isdigit() else None
        remaining = int(remaining_raw) if isinstance(remaining_raw, str) and remaining_raw.isdigit() else None

        reset_secs = None
        if isinstance(payload, dict):
            rate_limit = payload.get("rate_limit") or {}
            raw = rate_limit.get("resets_in_seconds")
            if isinstance(raw, int):
                reset_secs = raw
            elif isinstance(raw, str) and raw.isdigit():
                reset_secs = int(raw)

        snapshot = self._load_json(self._rate_file(), {})
        if limit is not None:
            snapshot["limit"] = limit
        if remaining is not None:
            snapshot["remaining"] = remaining
        if isinstance(reset_secs, int):
            snapshot["reset_epoch"] = int(self._utc_now().timestamp()) + reset_secs
        snapshot["updated_at"] = self._utc_now().isoformat()
        self._save_json(self._rate_file(), snapshot)

    async def _request(self, endpoint: str, params: dict[str, Any] | None = None, timeout: float = 15.0) -> dict:
        """Shared request path with quota and rate-limit guards."""
        self._rate_guard(endpoint)
        self._consume_daily_quota(endpoint)
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}{endpoint}",
                params=self._params_with_token(params),
                timeout=timeout,
            )
            payload = response.json() if "application/json" in response.headers.get("content-type", "") else {}
            self._update_rate_snapshot(response, payload if isinstance(payload, dict) else {})
            response.raise_for_status()
            return payload if isinstance(payload, dict) else {}

    def get_local_usage_summary(self) -> dict:
        quota = self._get_local_quota()
        used = int(quota.get("used", 0))
        limit = self._daily_limit()
        return {
            "date": quota["date"],
            "used": used,
            "limit": limit,
            "remaining": max(0, limit - used),
        }

    async def get_usage_status(self) -> dict:
        """Return local daily quota and last remote rate-limit snapshot."""
        local = self.get_local_usage_summary()
        remote = {}
        try:
            remote = await self._request("/leagues", params={"per_page": 1}, timeout=10.0)
        except Exception as e:
            logger.warning("Could not fetch Sportmonks usage status: {}", e)
        rate = self._load_json(self._rate_file(), {})
        return {"local": local, "remote": remote, "rate_snapshot": rate}

    @staticmethod
    def _safe_dt(value: str | None) -> datetime:
        if not value:
            return datetime.utcnow()
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return datetime.utcnow()

    @staticmethod
    def _pick_round(raw: dict[str, Any]) -> int:
        # Sportmonks payloads vary by endpoint, this keeps a stable fallback.
        for key in ("round_id", "round", "stage_id"):
            val = raw.get(key)
            if isinstance(val, int):
                return val
        return 0

    @staticmethod
    def _extract_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
        data = payload.get("data", [])
        return data if isinstance(data, list) else []

    async def get_teams(self, league_id: int) -> List[TeamDTO]:
        """Get teams from Sportmonks for current configured season."""
        season = settings.LIGA_MX_SEASON
        return await self.get_teams_by_season(league_id, season)

    async def get_teams_by_season(self, league_id: int, season: int) -> List[TeamDTO]:
        """Get teams for specific season."""
        logger.info("Fetching Sportmonks teams for league_id={} season={}", league_id, season)
        try:
            payload = await self._request(
                "/teams",
                params={"league_id": league_id, "season": season},
                timeout=15.0,
            )
            rows = self._extract_rows(payload)

            teams: list[TeamDTO] = []
            for row in rows:
                teams.append(
                    TeamDTO(
                        id=int(row.get("id")),
                        name=row.get("name", "Unknown"),
                        code=(row.get("short_code") or row.get("code") or f"TM{row.get('id')}")[:10],
                        country=(row.get("country") or {}).get("name") if isinstance(row.get("country"), dict) else row.get("country_name"),
                        logo_url=row.get("image_path") or row.get("logo_path"),
                    )
                )
            return teams
        except Exception as e:
            logger.error("Error fetching Sportmonks teams: {}", e)
            return []

    async def get_matches(self, league_id: int, season: int) -> List[MatchDTO]:
        """Get fixtures for specific season."""
        logger.info("Fetching Sportmonks fixtures for league_id={} season={}", league_id, season)
        try:
            payload = await self._request(
                "/fixtures",
                params={
                    "league_id": league_id,
                    "season": season,
                    "include": "participants;scores",
                },
                timeout=20.0,
            )
            rows = self._extract_rows(payload)

            matches: list[MatchDTO] = []
            for row in rows:
                participants = row.get("participants", [])
                home_id = None
                away_id = None
                for p in participants:
                    meta = p.get("meta", {}) if isinstance(p, dict) else {}
                    location = (meta.get("location") or "").lower()
                    if location == "home":
                        home_id = p.get("id")
                    elif location == "away":
                        away_id = p.get("id")

                if home_id is None or away_id is None:
                    continue

                score_home = None
                score_away = None
                for score in row.get("scores", []):
                    desc = str(score.get("description", "")).lower()
                    if "current" in desc or "fulltime" in desc or "ft" in desc:
                        if score.get("participant") == "home":
                            score_home = score.get("score")
                        elif score.get("participant") == "away":
                            score_away = score.get("score")

                matches.append(
                    MatchDTO(
                        id=int(row.get("id")),
                        home_team_id=int(home_id),
                        away_team_id=int(away_id),
                        match_date=self._safe_dt(row.get("starting_at") or row.get("starting_at_timestamp")),
                        league_id=league_id,
                        round_number=self._pick_round(row),
                        home_goals=int(score_home) if isinstance(score_home, (int, float, str)) and str(score_home).isdigit() else None,
                        away_goals=int(score_away) if isinstance(score_away, (int, float, str)) and str(score_away).isdigit() else None,
                        status=str(row.get("state", {}).get("short_name") or row.get("status") or "SCHEDULED"),
                    )
                )
            return matches
        except Exception as e:
            logger.error("Error fetching Sportmonks fixtures: {}", e)
            return []

    async def get_players(self, team_id: int) -> List[PlayerDTO]:
        """Get players for a team."""
        logger.info("Fetching Sportmonks players for team_id={}", team_id)
        try:
            payload = await self._request(
                f"/squads/teams/{team_id}",
                params={},
                timeout=15.0,
            )
            rows = self._extract_rows(payload)

            players: list[PlayerDTO] = []
            for row in rows:
                players.append(
                    PlayerDTO(
                        id=int(row.get("id")),
                        name=row.get("common_name") or row.get("display_name") or row.get("name", "Unknown"),
                        position=(row.get("position") or {}).get("name") if isinstance(row.get("position"), dict) else str(row.get("position") or "Unknown"),
                        team_id=team_id,
                        shirt_number=row.get("jersey_number"),
                        nationality=(row.get("nationality") or {}).get("name") if isinstance(row.get("nationality"), dict) else row.get("nationality"),
                    )
                )
            return players
        except Exception as e:
            logger.error("Error fetching Sportmonks players: {}", e)
            return []

    async def get_standings(self, league_id: int, season: int) -> dict:
        """Get standings for a season."""
        logger.info("Fetching Sportmonks standings for league_id={} season={}", league_id, season)
        try:
            return await self._request(
                "/standings",
                params={"league_id": league_id, "season": season},
                timeout=15.0,
            )
        except Exception as e:
            logger.error("Error fetching Sportmonks standings: {}", e)
            return {}

    async def get_statistics(self, match_id: int, team_id: int) -> dict:
        """Get fixture statistics for team in fixture."""
        logger.info("Fetching Sportmonks stats for match_id={} team_id={}", match_id, team_id)
        try:
            return await self._request(
                f"/fixtures/{match_id}",
                params={"include": "statistics"},
                timeout=15.0,
            )
        except Exception as e:
            logger.error("Error fetching Sportmonks statistics: {}", e)
            return {}

    async def get_injuries(self, team_id: int) -> List[dict]:
        """Get injuries from Sportmonks."""
        try:
            payload = await self._request(
                "/injuries",
                params={"filters": f"team_id:{team_id}"},
                timeout=15.0,
            )
            return self._extract_rows(payload)
        except Exception as e:
            logger.error("Error fetching Sportmonks injuries: {}", e)
            return []

    async def get_transfers(self, team_id: int) -> List[dict]:
        """Get transfers from Sportmonks."""
        try:
            payload = await self._request(
                "/transfers",
                params={"filters": f"team_id:{team_id}"},
                timeout=15.0,
            )
            return self._extract_rows(payload)
        except Exception as e:
            logger.error("Error fetching Sportmonks transfers: {}", e)
            return []

    async def get_odds(self, match_id: int) -> List[dict]:
        """Odds are delegated to API-Football in this project."""
        return []
