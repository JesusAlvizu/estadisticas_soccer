"""Synchronization tasks."""
import asyncio
from datetime import date, datetime

from celery import chain
from celery import shared_task
from loguru import logger
from sqlalchemy import func, select

from app.adapters.api_football_adapter import APIFootballAdapter
from app.adapters.sportmonks_adapter import SportmonksAdapter
from app.core.config.settings import get_settings
from app.core.database import AsyncSessionLocal
from app.models.models import (
    Bookmaker,
    League,
    Market,
    Match,
    Odd,
    Player,
    Round,
    Season,
    Sport,
    Team,
    TeamSeason,
)


settings = get_settings()


def _is_non_retryable_error(exc: Exception) -> bool:
    """Errors that should not trigger Celery retries."""
    message = str(exc)
    return (
        "API_KEY_FOOTBALL is required" in message
        or "API_FOOTBALL_DAILY_LIMIT reached" in message
    )


def _is_in_tournament_window() -> bool:
    """Return True when we should execute Liga MX sync jobs."""
    if not settings.LIGA_MX_SYNC_ENABLED:
        return False

    if not settings.LIGA_MX_TOURNAMENT_START or not settings.LIGA_MX_TOURNAMENT_END:
        return True

    try:
        start = datetime.fromisoformat(settings.LIGA_MX_TOURNAMENT_START).date()
        end = datetime.fromisoformat(settings.LIGA_MX_TOURNAMENT_END).date()
    except ValueError:
        logger.warning(
            "Invalid tournament window format. Expected YYYY-MM-DD. Running sync anyway."
        )
        return True

    today = date.today()
    return start <= today <= end


def _build_adapter() -> APIFootballAdapter:
    """Build API adapter with configured API key."""
    key = settings.API_KEY_FOOTBALL
    if not key or key.strip().lower() in {"your-api-key-here", "changeme", "none"}:
        raise RuntimeError("API_KEY_FOOTBALL is required to sync Liga MX data")
    return APIFootballAdapter(key)


def _build_primary_adapter() -> APIFootballAdapter | SportmonksAdapter:
    """Primary adapter for active sync.

    API-Football is used here because current available Liga MX coverage in the
    active plans is stable for this project's sync flow.
    """
    return _build_adapter()


def _build_secondary_odds_adapter() -> APIFootballAdapter:
    """Secondary adapter for odds and lightweight fixtures."""
    return _build_adapter()


async def _ensure_competition_context(
    session,
    league_id: int,
    season_year: int,
) -> tuple[Sport, League, Season]:
    """Ensure sport/league/season records exist before syncing detailed data."""
    sport = (
        await session.execute(select(Sport).where(Sport.code == "FOOTBALL"))
    ).scalar_one_or_none()
    if not sport:
        sport = Sport(name="Football", code="FOOTBALL")
        session.add(sport)
        await session.flush()

    league_code = f"LIGA_MX_{league_id}"
    league = (
        await session.execute(
            select(League).where(League.sport_id == sport.id, League.code == league_code)
        )
    ).scalar_one_or_none()
    if not league:
        league = League(
            sport_id=sport.id,
            name="Liga MX",
            code=league_code,
            country="Mexico",
        )
        session.add(league)
        await session.flush()

    season = (
        await session.execute(
            select(Season).where(Season.league_id == league.id, Season.year == season_year)
        )
    ).scalar_one_or_none()
    if not season:
        season = Season(
            league_id=league.id,
            year=season_year,
            is_current=True,
        )
        session.add(season)
        await session.flush()

    return sport, league, season


async def _sync_teams_async(league_id: int, season: int) -> dict:
    """Sync teams and upsert into local DB."""
    adapter = _build_primary_adapter()
    if hasattr(adapter, "get_teams_by_season"):
        teams = await adapter.get_teams_by_season(league_id, season)
    else:
        teams = await adapter.get_teams(league_id, season)

    async with AsyncSessionLocal() as session:
        sport, _, _ = await _ensure_competition_context(session, league_id, season)
        existing_codes = (
            await session.execute(select(Team.id, Team.code).where(Team.sport_id == sport.id))
        ).all()
        used_codes: dict[str, int] = {code: team_id for team_id, code in existing_codes}

        upserted = 0
        for team_dto in teams:
            with session.no_autoflush:
                team = (
                    await session.execute(select(Team).where(Team.id == team_dto.id))
                ).scalar_one_or_none()

                base_code = (team_dto.code or f"T{team_dto.id}")[:10]
                safe_code = base_code
                owner_id = used_codes.get(base_code)
                if owner_id is not None and owner_id != team_dto.id:
                    safe_code = f"T{team_dto.id}"[:10]
                    owner_id = used_codes.get(safe_code)
                    if owner_id is not None and owner_id != team_dto.id:
                        safe_code = f"X{str(team_dto.id)[-9:]}"

            if not team:
                team = Team(id=team_dto.id, sport_id=sport.id, name=team_dto.name, code=safe_code)
                session.add(team)
            else:
                team.name = team_dto.name
                team.code = safe_code

            team.country = team_dto.country
            team.logo_url = team_dto.logo_url
            used_codes[safe_code] = team_dto.id
            upserted += 1

        await session.commit()

    return {"upserted": upserted, "league_id": league_id, "season": season}


async def _sync_matches_async(league_id: int, season: int) -> dict:
    """Sync matches and upsert into local DB."""
    adapter = _build_primary_adapter()
    matches = await adapter.get_matches(league_id, season)

    async with AsyncSessionLocal() as session:
        _, _, season_obj = await _ensure_competition_context(session, league_id, season)
        upserted = 0
        for match_dto in matches:
            round_obj = (
                await session.execute(
                    select(Round).where(
                        Round.season_id == season_obj.id,
                        Round.round_number == match_dto.round_number,
                    )
                )
            ).scalar_one_or_none()

            if not round_obj:
                round_obj = Round(
                    season_id=season_obj.id,
                    round_number=match_dto.round_number,
                    name=f"Round {match_dto.round_number}",
                )
                session.add(round_obj)
                await session.flush()

            match = (
                await session.execute(select(Match).where(Match.id == match_dto.id))
            ).scalar_one_or_none()
            if not match:
                match = Match(
                    id=match_dto.id,
                    round_id=round_obj.id,
                    home_team_id=match_dto.home_team_id,
                    away_team_id=match_dto.away_team_id,
                    match_date=match_dto.match_date,
                    status=match_dto.status,
                )
                session.add(match)
            else:
                match.round_id = round_obj.id
                match.home_team_id = match_dto.home_team_id
                match.away_team_id = match_dto.away_team_id
                match.match_date = match_dto.match_date
                match.status = match_dto.status

            match.home_goals = match_dto.home_goals
            match.away_goals = match_dto.away_goals
            upserted += 1

        await session.commit()

    return {"upserted": upserted, "league_id": league_id, "season": season}


async def _sync_players_async(league_id: int, season: int) -> dict:
    """Sync all players from local Liga MX teams."""
    adapter = _build_primary_adapter()
    async with AsyncSessionLocal() as session:
        teams = (await session.execute(select(Team))).scalars().all()
        upserted = 0
        teams_processed = 0
        for team in teams:
            if isinstance(adapter, APIFootballAdapter):
                remaining = adapter.get_local_usage_summary().get("remaining", 0)
                if remaining <= 0:
                    logger.warning("Daily API quota exhausted while syncing players")
                    break
            players = await adapter.get_players(team.id)
            teams_processed += 1
            for player_dto in players:
                player = (
                    await session.execute(select(Player).where(Player.id == player_dto.id))
                ).scalar_one_or_none()
                if not player:
                    player = Player(
                        id=player_dto.id,
                        team_id=team.id,
                        name=player_dto.name,
                        position=player_dto.position,
                        shirt_number=player_dto.shirt_number,
                        nationality=player_dto.nationality,
                    )
                    session.add(player)
                else:
                    player.team_id = team.id
                    player.name = player_dto.name
                    player.position = player_dto.position
                    player.shirt_number = player_dto.shirt_number
                    player.nationality = player_dto.nationality
                upserted += 1

        await session.commit()

    return {
        "upserted": upserted,
        "teams_processed": teams_processed,
        "teams_total": len(teams),
        "league_id": league_id,
        "season": season,
        "usage": adapter.get_local_usage_summary() if isinstance(adapter, APIFootballAdapter) else {"provider": "sportmonks"},
    }


async def _sync_statistics_async(league_id: int, season: int) -> dict:
    """Sync standings and map them into team_seasons statistics."""
    adapter = _build_primary_adapter()
    standings_data = await adapter.get_standings(league_id, season)

    async with AsyncSessionLocal() as session:
        _, _, season_obj = await _ensure_competition_context(session, league_id, season)
        # API-Football shape
        table_entries = (
            standings_data.get("response", [{}])[0]
            .get("league", {})
            .get("standings", [[]])[0]
        )
        # Sportmonks shape fallback
        if not table_entries and isinstance(standings_data.get("data"), list):
            table_entries = standings_data.get("data", [])

        updated = 0
        for row in table_entries:
            team_id = row.get("team", {}).get("id")
            if not team_id:
                participant = row.get("participant") or {}
                team_id = participant.get("id")
            if not team_id:
                continue
            team = (await session.execute(select(Team).where(Team.id == team_id))).scalar_one_or_none()
            if not team:
                continue

            team_season = (
                await session.execute(
                    select(TeamSeason).where(
                        TeamSeason.team_id == team.id,
                        TeamSeason.season_id == season_obj.id,
                    )
                )
            ).scalar_one_or_none()

            if not team_season:
                team_season = TeamSeason(team_id=team.id, season_id=season_obj.id)
                session.add(team_season)

            # API-Football mapping
            goals = row.get("all", {}).get("goals", {})
            played = row.get("all", {}).get("played", 0)
            team_season.position = row.get("rank")
            team_season.points = row.get("points", 0)
            team_season.matches_played = played
            team_season.wins = row.get("all", {}).get("win", 0)
            team_season.draws = row.get("all", {}).get("draw", 0)
            team_season.losses = row.get("all", {}).get("lose", 0)
            team_season.goals_for = goals.get("for", 0)
            team_season.goals_against = goals.get("against", 0)

            # Sportmonks fallback mapping
            if played == 0 and row.get("played") is not None:
                team_season.position = row.get("position") or team_season.position
                team_season.points = row.get("points") or team_season.points
                team_season.matches_played = row.get("played") or 0
                team_season.wins = row.get("won") or row.get("wins") or 0
                team_season.draws = row.get("drawn") or row.get("draws") or 0
                team_season.losses = row.get("lost") or row.get("losses") or 0
                team_season.goals_for = row.get("goals_for") or 0
                team_season.goals_against = row.get("goals_against") or 0
                played = team_season.matches_played

            team_season.goal_difference = team_season.goals_for - team_season.goals_against
            team_season.average_goals = (
                team_season.goals_for / played if played else 0.0
            )
            updated += 1

        await session.commit()

    return {"updated": updated, "league_id": league_id, "season": season}


async def _sync_odds_async(league_id: int, season: int) -> dict:
    """Sync odds for upcoming matches into bookmakers/markets/odds tables."""
    adapter = _build_secondary_odds_adapter()
    async with AsyncSessionLocal() as session:
        upcoming_matches = (
            await session.execute(select(Match).where(Match.match_date >= datetime.utcnow()))
        ).scalars().all()

        upserted = 0
        matches_processed = 0
        for match in upcoming_matches:
            remaining = adapter.get_local_usage_summary().get("remaining", 0)
            if remaining <= 0:
                logger.warning("Daily API quota exhausted while syncing odds")
                break
            odds_payload = await adapter.get_odds(match.id)
            matches_processed += 1
            for item in odds_payload:
                fixture = item.get("fixture", {})
                if fixture.get("id") != match.id:
                    continue

                for bookmaker_item in item.get("bookmakers", []):
                    bookmaker_name = bookmaker_item.get("name", "Unknown")
                    bookmaker_code = bookmaker_name.upper().replace(" ", "_")[:20] or "UNKNOWN"

                    bookmaker = (
                        await session.execute(
                            select(Bookmaker).where(Bookmaker.code == bookmaker_code)
                        )
                    ).scalar_one_or_none()
                    if not bookmaker:
                        bookmaker = Bookmaker(name=bookmaker_name, code=bookmaker_code)
                        session.add(bookmaker)
                        await session.flush()

                    for bet in bookmaker_item.get("bets", []):
                        market_name = bet.get("name", "Match Winner")
                        market_code = market_name.upper().replace(" ", "_")[:50]
                        market = (
                            await session.execute(select(Market).where(Market.code == market_code))
                        ).scalar_one_or_none()
                        if not market:
                            market = Market(name=market_name, code=market_code)
                            session.add(market)
                            await session.flush()

                        for value in bet.get("values", []):
                            outcome = str(value.get("value", "N/A"))
                            odd_val_raw = value.get("odd")
                            try:
                                odd_value = float(odd_val_raw)
                            except (TypeError, ValueError):
                                continue
                            implied_probability = (1.0 / odd_value) if odd_value > 0 else 0.0

                            existing = (
                                await session.execute(
                                    select(Odd).where(
                                        Odd.match_id == match.id,
                                        Odd.bookmaker_id == bookmaker.id,
                                        Odd.market_id == market.id,
                                        Odd.outcome == outcome,
                                    )
                                )
                            ).scalar_one_or_none()
                            if not existing:
                                existing = Odd(
                                    match_id=match.id,
                                    bookmaker_id=bookmaker.id,
                                    market_id=market.id,
                                    outcome=outcome,
                                    value=odd_value,
                                    probability=implied_probability,
                                )
                                session.add(existing)
                            else:
                                existing.value = odd_value
                                existing.probability = implied_probability
                            upserted += 1

        await session.commit()

    return {
        "upserted": upserted,
        "matches_processed": matches_processed,
        "matches_total": len(upcoming_matches),
        "league_id": league_id,
        "season": season,
        "usage": adapter.get_local_usage_summary(),
    }


async def _pick_next_historical_season(league_id: int, seasons: list[int]) -> int | None:
    """Pick next season with missing or empty match data."""
    async with AsyncSessionLocal() as session:
        for season_year in seasons:
            season_obj = (
                await session.execute(
                    select(Season).join(League, Season.league_id == League.id).where(
                        League.code == f"LIGA_MX_{league_id}",
                        Season.year == season_year,
                    )
                )
            ).scalar_one_or_none()
            if not season_obj:
                return season_year

            matches_count = (
                await session.execute(
                    select(func.count(Match.id)).join(Round, Match.round_id == Round.id).where(
                        Round.season_id == season_obj.id
                    )
                )
            ).scalar_one()

            if int(matches_count or 0) == 0:
                return season_year

    return None


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def sync_teams(self, league_id: int | None = None, season: int | None = None):
    """Sync teams from external API."""
    try:
        target_league_id = league_id or settings.LIGA_MX_LEAGUE_ID
        target_season = season or settings.LIGA_MX_SEASON
        logger.info(
            "Starting teams synchronization for league_id={} season={}...",
            target_league_id,
            target_season,
        )
        result = asyncio.run(_sync_teams_async(target_league_id, target_season))
        logger.info("Teams synchronized successfully: {}", result)
        return {"status": "success", **result}
    except Exception as exc:
        logger.error(f"Error syncing teams: {exc}")
        if _is_non_retryable_error(exc):
            return {"status": "skipped", "reason": str(exc)}
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def sync_matches(self, league_id: int | None = None, season: int | None = None):
    """Sync matches from external API."""
    try:
        target_league_id = league_id or settings.LIGA_MX_LEAGUE_ID
        target_season = season or settings.LIGA_MX_SEASON
        logger.info(
            "Starting matches synchronization for league_id={} season={}...",
            target_league_id,
            target_season,
        )
        result = asyncio.run(_sync_matches_async(target_league_id, target_season))
        logger.info("Matches synchronized successfully: {}", result)
        return {"status": "success", **result}
    except Exception as exc:
        logger.error(f"Error syncing matches: {exc}")
        if _is_non_retryable_error(exc):
            return {"status": "skipped", "reason": str(exc)}
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def sync_statistics(self, league_id: int | None = None, season: int | None = None):
    """Sync statistics from external API."""
    try:
        target_league_id = league_id or settings.LIGA_MX_LEAGUE_ID
        target_season = season or settings.LIGA_MX_SEASON
        logger.info(
            "Starting statistics synchronization for league_id={} season={}...",
            target_league_id,
            target_season,
        )
        result = asyncio.run(_sync_statistics_async(target_league_id, target_season))
        logger.info("Statistics synchronized successfully: {}", result)
        return {"status": "success", **result}
    except Exception as exc:
        logger.error(f"Error syncing statistics: {exc}")
        if _is_non_retryable_error(exc):
            return {"status": "skipped", "reason": str(exc)}
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def sync_odds(self, league_id: int | None = None, season: int | None = None):
    """Sync odds from external API."""
    try:
        target_league_id = league_id or settings.LIGA_MX_LEAGUE_ID
        target_season = season or settings.LIGA_MX_SEASON
        logger.info(
            "Starting odds synchronization for league_id={} season={}...",
            target_league_id,
            target_season,
        )
        result = asyncio.run(_sync_odds_async(target_league_id, target_season))
        logger.info("Odds synchronized successfully: {}", result)
        return {"status": "success", **result}
    except Exception as exc:
        logger.error(f"Error syncing odds: {exc}")
        if _is_non_retryable_error(exc):
            return {"status": "skipped", "reason": str(exc)}
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=2, default_retry_delay=60)
def sync_players(self, league_id: int | None = None, season: int | None = None):
    """Sync players from external API for all Liga MX teams."""
    try:
        target_league_id = league_id or settings.LIGA_MX_LEAGUE_ID
        target_season = season or settings.LIGA_MX_SEASON
        logger.info(
            "Starting players synchronization for league_id={} season={}...",
            target_league_id,
            target_season,
        )
        result = asyncio.run(_sync_players_async(target_league_id, target_season))
        logger.info("Players synchronized successfully: {}", result)
        return {"status": "success", **result}
    except Exception as exc:
        logger.error(f"Error syncing players: {exc}")
        if _is_non_retryable_error(exc):
            return {"status": "skipped", "reason": str(exc)}
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=2, default_retry_delay=60)
def sync_liga_mx_pipeline(self):
    """Run the complete Liga MX sync pipeline while tournament is active."""
    if not _is_in_tournament_window():
        logger.info("Liga MX pipeline skipped: outside configured tournament window")
        return {"status": "skipped", "reason": "outside_tournament_window"}

    league_id = settings.LIGA_MX_LEAGUE_ID
    season = settings.LIGA_MX_SEASON
    adapter = _build_adapter()
    usage_snapshot = asyncio.run(adapter.get_usage_status())
    remote_current = (
        usage_snapshot.get("remote", {})
        .get("response", {})
        .get("requests", {})
        .get("current")
    )
    if isinstance(remote_current, int):
        adapter.sync_local_usage_with_remote(remote_current)

    usage = adapter.get_local_usage_summary()
    if usage["remaining"] <= 0:
        logger.warning("Liga MX pipeline skipped: daily API quota exhausted ({}/{})", usage["used"], usage["limit"])
        return {
            "status": "skipped",
            "reason": "daily_quota_exhausted",
            "usage": usage,
        }

    logger.info("Running Liga MX sync pipeline for league_id={} season={}", league_id, season)

    workflow = chain(
        sync_teams.si(league_id, season),
        sync_matches.si(league_id, season),
        sync_statistics.si(league_id, season),
        sync_players.si(league_id, season),
        sync_odds.si(league_id, season),
    )
    async_result = workflow.apply_async()

    return {
        "status": "scheduled",
        "league_id": league_id,
        "season": season,
        "jobs": ["sync_teams", "sync_players", "sync_matches", "sync_statistics", "sync_odds"],
        "workflow_id": async_result.id,
        "usage": usage,
    }


@shared_task(bind=True, max_retries=0)
def sync_historical_10_tournaments(self):
    """Backfill historical data for last N seasons (Sportmonks primary)."""
    if not settings.SPORTMONKS_API_KEY or not settings.SPORTMONKS_API_KEY.strip():
        return {
            "status": "skipped",
            "reason": "SPORTMONKS_API_KEY is required for historical backfill",
        }

    league_id = settings.SPORTMONKS_LEAGUE_ID or settings.LIGA_MX_LEAGUE_ID
    latest_excluded = settings.LIGA_MX_SEASON
    start_year = latest_excluded - settings.HISTORICAL_SEASONS_COUNT
    # Start from previous season and move backwards.
    seasons = list(range(latest_excluded - 1, start_year - 1, -1))

    logger.info(
        "Historical backfill started for seasons {}-{} ({} seasons)",
        start_year,
        latest_excluded - 1,
        len(seasons),
    )

    next_season = asyncio.run(_pick_next_historical_season(league_id, seasons))
    if next_season is None:
        return {
            "status": "completed",
            "league_id": league_id,
            "message": "Historical backfill already complete",
            "seasons": seasons,
        }

    workflow = chain(
        sync_teams.si(league_id, next_season),
        sync_matches.si(league_id, next_season),
        sync_statistics.si(league_id, next_season),
        sync_players.si(league_id, next_season),
    )
    async_result = workflow.apply_async()

    return {
        "status": "scheduled",
        "league_id": league_id,
        "season": next_season,
        "season_window": [latest_excluded - 1, start_year],
        "provider": "sportmonks_primary",
        "workflow_id": async_result.id,
    }


@shared_task(bind=True, max_retries=0)
def report_api_football_usage(self):
    """Report local API-Football daily usage and remote status metadata."""
    adapter = _build_adapter()
    usage = asyncio.run(adapter.get_usage_status())
    logger.info("API-Football usage status: {}", usage)
    return usage


@shared_task(bind=True, max_retries=0)
def report_sportmonks_usage(self):
    """Report local Sportmonks daily usage and remote rate-limit metadata."""
    if not settings.SPORTMONKS_API_KEY or not settings.SPORTMONKS_API_KEY.strip():
        return {"status": "skipped", "reason": "SPORTMONKS_API_KEY missing"}

    adapter = SportmonksAdapter(settings.SPORTMONKS_API_KEY)
    usage = asyncio.run(adapter.get_usage_status())
    logger.info("Sportmonks usage status: {}", usage)
    return usage
