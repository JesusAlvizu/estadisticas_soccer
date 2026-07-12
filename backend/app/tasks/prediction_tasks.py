"""Prediction tasks."""
import asyncio
from datetime import datetime, timedelta

from celery import shared_task
from loguru import logger
from sqlalchemy import select

from app.analytics.monte_carlo import MonteCarlo
from app.core.config.settings import get_settings
from app.core.database import AsyncSessionLocal
from app.models.models import Match, Prediction, SimulationResult, TeamSeason, Season


settings = get_settings()


async def _get_team_stats(session, team_id: int, season_year: int) -> dict:
    """Build a lightweight stats dict for model input."""
    season_row = (
        await session.execute(select(Season).where(Season.year == season_year))
    ).scalar_one_or_none()

    if not season_row:
        return {"goals_per_match": 1.2, "expected_goals": 1.2}

    stats = (
        await session.execute(
            select(TeamSeason).where(
                TeamSeason.team_id == team_id,
                TeamSeason.season_id == season_row.id,
            )
        )
    ).scalar_one_or_none()

    if not stats or stats.matches_played == 0:
        return {"goals_per_match": 1.2, "expected_goals": 1.2}

    return {
        "goals_per_match": stats.average_goals or (stats.goals_for / stats.matches_played),
        "expected_goals": stats.average_expected_goals or 1.2,
        "win_rate": (stats.wins / stats.matches_played) if stats.matches_played else 0.5,
        "recent_form": (stats.points / (stats.matches_played * 3)) if stats.matches_played else 0.5,
        "clean_sheets": stats.clean_sheets,
        "possession": stats.possession_percentage or 50.0,
    }


async def _upsert_prediction(session, match_id: int, market: str, outcome: str, probability: float):
    """Upsert a prediction record for a given match/market/outcome."""
    record = (
        await session.execute(
            select(Prediction).where(
                Prediction.match_id == match_id,
                Prediction.market == market,
                Prediction.predicted_outcome == outcome,
            )
        )
    ).scalar_one_or_none()

    confidence = min(0.95, max(0.5, probability + 0.15))
    if not record:
        record = Prediction(
            match_id=match_id,
            market=market,
            predicted_outcome=outcome,
            predicted_probability=probability,
            confidence_level=confidence,
            model_name="monte_carlo_liga_mx",
            reasoning="Generated from team season stats and Monte Carlo simulation.",
        )
        session.add(record)
    else:
        record.predicted_probability = probability
        record.confidence_level = confidence
        record.model_name = "monte_carlo_liga_mx"
        record.reasoning = "Updated from latest Liga MX synchronization and Monte Carlo simulation."


async def _upsert_simulation(session, match_id: int, simulation):
    """Upsert simulation_results record."""
    record = (
        await session.execute(
            select(SimulationResult).where(SimulationResult.match_id == match_id)
        )
    ).scalar_one_or_none()

    payload = {
        "simulation_count": simulation.simulations,
        "home_win_probability": simulation.home_win_probability,
        "draw_probability": simulation.draw_probability,
        "away_win_probability": simulation.away_win_probability,
        "most_likely_score": simulation.most_likely_score,
        "average_goals": simulation.average_goals,
        "over_under_25_probability": simulation.over_2_5_probability,
        "both_score_probability": simulation.both_teams_score_probability,
    }

    if not record:
        record = SimulationResult(match_id=match_id, **payload)
        session.add(record)
    else:
        for key, value in payload.items():
            setattr(record, key, value)


async def _generate_liga_mx_predictions_async() -> dict:
    """Generate predictions for upcoming Liga MX matches."""
    async with AsyncSessionLocal() as session:
        horizon = datetime.utcnow() + timedelta(days=3)
        upcoming_matches = (
            await session.execute(
                select(Match).where(
                    Match.match_date >= datetime.utcnow(),
                    Match.match_date <= horizon,
                )
            )
        ).scalars().all()

        processed = 0
        for match in upcoming_matches:
            home_stats = await _get_team_stats(session, match.home_team_id, settings.LIGA_MX_SEASON)
            away_stats = await _get_team_stats(session, match.away_team_id, settings.LIGA_MX_SEASON)

            simulation = MonteCarlo(
                home_team_stats=home_stats,
                away_team_stats=away_stats,
                simulations=settings.MAX_SIMULATIONS,
            ).run()

            await _upsert_prediction(
                session,
                match.id,
                "1X2",
                "HOME",
                simulation.home_win_probability,
            )
            await _upsert_prediction(
                session,
                match.id,
                "1X2",
                "DRAW",
                simulation.draw_probability,
            )
            await _upsert_prediction(
                session,
                match.id,
                "1X2",
                "AWAY",
                simulation.away_win_probability,
            )

            await _upsert_simulation(session, match.id, simulation)
            processed += 1

        await session.commit()
        return {"processed_matches": processed}


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def generate_predictions(self, match_id: int):
    """Generate predictions for a match."""
    try:
        logger.info(f"Generating predictions for match {match_id}...")
        # TODO: Implement prediction logic
        logger.info(f"Predictions generated for match {match_id}")
        return {"status": "success", "match_id": match_id}
    except Exception as exc:
        logger.error(f"Error generating predictions: {exc}")
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def run_monte_carlo_simulation(self, match_id: int, simulations: int = 5000):
    """Run Monte Carlo simulation for a match."""
    try:
        logger.info(f"Running {simulations} simulations for match {match_id}...")
        # TODO: Implement simulation logic
        logger.info(f"Simulations completed for match {match_id}")
        return {"status": "success", "match_id": match_id, "simulations": simulations}
    except Exception as exc:
        logger.error(f"Error running simulations: {exc}")
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=2, default_retry_delay=60)
def generate_liga_mx_predictions(self):
    """Generate/update probabilities for Liga MX active matches."""
    try:
        logger.info(
            "Generating Liga MX predictions for league_id={} season={}...",
            settings.LIGA_MX_LEAGUE_ID,
            settings.LIGA_MX_SEASON,
        )
        result = asyncio.run(_generate_liga_mx_predictions_async())
        logger.info("Liga MX prediction generation completed: {}", result)
        return {
            "status": "success",
            "league_id": settings.LIGA_MX_LEAGUE_ID,
            "season": settings.LIGA_MX_SEASON,
            **result,
        }
    except Exception as exc:
        logger.error(f"Error generating Liga MX predictions: {exc}")
        raise self.retry(exc=exc)
