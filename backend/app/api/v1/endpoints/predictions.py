"""Predictions endpoints."""
from datetime import datetime

import numpy as np
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.analytics.monte_carlo import MonteCarlo
from app.core.database import get_db
from app.models.models import League, Match, MatchEvent, Prediction, Round, Season, Team

router = APIRouter()

FINISHED_STATUSES = {"FT", "AET", "PEN", "FINISHED"}
LIGA_MX_STADIUM_FALLBACK = [
    "Estadio Akron",
    "Estadio Azteca",
    "Estadio BBVA",
    "Estadio Caliente",
    "Estadio Corona",
    "Estadio Cuauhtemoc",
    "Estadio Hidalgo",
    "Estadio Jalisco",
    "Estadio Leon",
    "Estadio Morelos",
    "Estadio Nemesio Diez",
    "Estadio Olimpico Benito Juarez",
    "Estadio Olimpico Universitario",
    "Estadio Universitario",
    "Estadio Victoria",
    "Estadio Alfonso Lastras Ramirez",
    "Estadio TSM Corona",
    "Estadio Ciudad de los Deportes",
]


class MatchProbabilityRequest(BaseModel):
    """Input payload for manual match probability calculation."""

    home_team: str
    away_team: str
    stadium: str | None = None
    simulations: int = Field(default=5000, ge=1000, le=10000)


@router.get("/manual-match-options")
async def manual_match_options(db: AsyncSession = Depends(get_db)):
    """Return selectable Liga MX teams and stadiums for manual calculator."""
    league = (
        await db.execute(
            select(League)
            .where(
                or_(
                    func.lower(League.name).like("%liga mx%"),
                    func.lower(League.code).like("%liga mx%"),
                    func.lower(League.code) == "mx",
                )
            )
            .order_by(League.id.asc())
            .limit(1)
        )
    ).scalar_one_or_none()

    if not league:
        return {"league": None, "teams": [], "stadiums": []}

    season_ids = (
        await db.execute(select(Season.id).where(Season.league_id == league.id))
    ).scalars().all()

    if not season_ids:
        return {"league": league.name, "teams": [], "stadiums": []}

    team_rows = (
        await db.execute(
            select(Team.name)
            .join(Match, or_(Team.id == Match.home_team_id, Team.id == Match.away_team_id))
            .join(Round, Match.round_id == Round.id)
            .where(Round.season_id.in_(season_ids))
            .distinct()
            .order_by(Team.name.asc())
        )
    ).scalars().all()

    stadium_rows = (
        await db.execute(
            select(Match.venue)
            .join(Round, Match.round_id == Round.id)
            .where(
                Round.season_id.in_(season_ids),
                Match.venue.is_not(None),
                func.length(func.trim(Match.venue)) > 0,
            )
            .distinct()
            .order_by(Match.venue.asc())
        )
    ).scalars().all()

    stadiums = [name for name in stadium_rows if name]
    if not stadiums:
        stadiums = LIGA_MX_STADIUM_FALLBACK

    return {
        "league": league.name,
        "teams": [name for name in team_rows if name],
        "stadiums": stadiums,
    }


async def _find_team(db: AsyncSession, name: str) -> Team | None:
    """Resolve team by exact or partial name match."""
    team = (
        await db.execute(select(Team).where(func.lower(Team.name) == name.strip().lower()))
    ).scalar_one_or_none()
    if team:
        return team

    return (
        await db.execute(
            select(Team)
            .where(Team.name.ilike(f"%{name.strip()}%"))
            .order_by(func.length(Team.name).asc())
            .limit(1)
        )
    ).scalar_one_or_none()


async def _team_recent_matches(db: AsyncSession, team_id: int, limit: int = 30) -> list[Match]:
    """Get recent finished matches for a team."""
    rows = (
        await db.execute(
            select(Match)
            .where(
                or_(Match.home_team_id == team_id, Match.away_team_id == team_id),
                Match.home_goals.is_not(None),
                Match.away_goals.is_not(None),
            )
            .order_by(Match.match_date.desc())
            .limit(limit)
        )
    ).scalars().all()

    return [m for m in rows if (m.status or "").upper() in FINISHED_STATUSES]


async def _head_to_head(db: AsyncSession, home_id: int, away_id: int, limit: int = 20) -> list[Match]:
    """Get historical head-to-head matches between both teams."""
    rows = (
        await db.execute(
            select(Match)
            .where(
                Match.home_goals.is_not(None),
                Match.away_goals.is_not(None),
                or_(
                    (Match.home_team_id == home_id) & (Match.away_team_id == away_id),
                    (Match.home_team_id == away_id) & (Match.away_team_id == home_id),
                ),
            )
            .order_by(Match.match_date.desc())
            .limit(limit)
        )
    ).scalars().all()

    return [m for m in rows if (m.status or "").upper() in FINISHED_STATUSES]


def _goal_profile(matches: list[Match], team_id: int) -> dict:
    """Build goals profile from historical matches for a given team."""
    if not matches:
        return {
            "gf": 1.2,
            "ga": 1.2,
            "ht_gf": 0.55,
            "ht_ga": 0.55,
        }

    gf = 0.0
    ga = 0.0
    ht_gf = 0.0
    ht_ga = 0.0

    for m in matches:
        is_home = m.home_team_id == team_id
        gf += float(m.home_goals if is_home else m.away_goals)
        ga += float(m.away_goals if is_home else m.home_goals)
        ht_gf += float((m.home_goals_halftime if is_home else m.away_goals_halftime) or 0)
        ht_ga += float((m.away_goals_halftime if is_home else m.home_goals_halftime) or 0)

    n = float(len(matches))
    return {
        "gf": gf / n,
        "ga": ga / n,
        "ht_gf": ht_gf / n,
        "ht_ga": ht_ga / n,
    }


async def _event_rate(db: AsyncSession, team_id: int, keyword: str, fallback: float) -> float:
    """Estimate per-match rate for event types (cards/corners)."""
    events_count = (
        await db.execute(
            select(func.count(MatchEvent.id)).where(
                MatchEvent.team_id == team_id,
                MatchEvent.event_type.ilike(f"%{keyword}%"),
            )
        )
    ).scalar_one()

    matches_count = (
        await db.execute(
            select(func.count(func.distinct(MatchEvent.match_id))).where(
                MatchEvent.team_id == team_id,
                MatchEvent.event_type.ilike(f"%{keyword}%"),
            )
        )
    ).scalar_one()

    events_count = int(events_count or 0)
    matches_count = int(matches_count or 0)
    if matches_count == 0:
        return fallback

    return events_count / float(matches_count)


def _poisson_over_probability(lam: float, line: float, simulations: int = 8000) -> float:
    """Estimate over-line probability with Poisson simulation."""
    lam = max(0.2, lam)
    draws = np.random.poisson(lam, simulations)
    return float(np.mean(draws > line))


@router.post("/manual-match-probabilities")
async def manual_match_probabilities(payload: MatchProbabilityRequest, db: AsyncSession = Depends(get_db)):
    """Return five betting market probabilities from DB history for input match."""
    home_team = await _find_team(db, payload.home_team)
    away_team = await _find_team(db, payload.away_team)

    if not home_team:
        raise HTTPException(status_code=404, detail=f"Home team not found: {payload.home_team}")
    if not away_team:
        raise HTTPException(status_code=404, detail=f"Away team not found: {payload.away_team}")
    if home_team.id == away_team.id:
        raise HTTPException(status_code=400, detail="Home and away team cannot be the same")

    home_recent = await _team_recent_matches(db, home_team.id, limit=30)
    away_recent = await _team_recent_matches(db, away_team.id, limit=30)
    h2h_matches = await _head_to_head(db, home_team.id, away_team.id, limit=20)

    home_profile = _goal_profile(home_recent, home_team.id)
    away_profile = _goal_profile(away_recent, away_team.id)

    h2h_goal_delta = 0.0
    if h2h_matches:
        delta_acc = 0.0
        for m in h2h_matches:
            if m.home_team_id == home_team.id:
                delta_acc += float((m.home_goals or 0) - (m.away_goals or 0))
            else:
                delta_acc += float((m.away_goals or 0) - (m.home_goals or 0))
        h2h_goal_delta = delta_acc / float(len(h2h_matches))

    venue_boost = 0.0
    if payload.stadium:
        venue_matches = [m for m in home_recent if (m.venue or "").strip().lower() == payload.stadium.strip().lower()]
        if venue_matches:
            wins = 0
            for m in venue_matches:
                if m.home_team_id == home_team.id and (m.home_goals or 0) > (m.away_goals or 0):
                    wins += 1
                if m.away_team_id == home_team.id and (m.away_goals or 0) > (m.home_goals or 0):
                    wins += 1
            venue_boost = ((wins / float(len(venue_matches))) - 0.5) * 0.16

    h2h_adjustment = max(-0.2, min(0.2, h2h_goal_delta * 0.08))
    home_lambda = max(0.2, home_profile["gf"] * (1.12 + h2h_adjustment + venue_boost))
    away_lambda = max(0.2, away_profile["gf"] * (1.0 - h2h_adjustment))

    simulation = MonteCarlo(
        home_team_stats={"goals_per_match": home_profile["gf"], "expected_goals": home_lambda},
        away_team_stats={"goals_per_match": away_profile["gf"], "expected_goals": away_lambda},
        simulations=payload.simulations,
    ).run()

    home_ht_lambda = max(0.1, home_profile["ht_gf"] * (1.1 + h2h_adjustment / 2.0 + venue_boost))
    away_ht_lambda = max(0.1, away_profile["ht_gf"] * (1.0 - h2h_adjustment / 2.0))
    home_ht_goals = np.random.poisson(home_ht_lambda, payload.simulations)
    away_ht_goals = np.random.poisson(away_ht_lambda, payload.simulations)
    home_ht_prob = float(np.mean(home_ht_goals > away_ht_goals))
    draw_ht_prob = float(np.mean(home_ht_goals == away_ht_goals))
    away_ht_prob = float(np.mean(home_ht_goals < away_ht_goals))

    home_corners = await _event_rate(db, home_team.id, "corner", fallback=4.8)
    away_corners = await _event_rate(db, away_team.id, "corner", fallback=4.3)
    expected_corners = home_corners + away_corners
    corners_over_prob = _poisson_over_probability(expected_corners, line=9.5, simulations=payload.simulations)
    corners_pick = "OVER_9.5" if corners_over_prob >= 0.5 else "UNDER_9.5"
    corners_pick_prob = corners_over_prob if corners_over_prob >= 0.5 else (1.0 - corners_over_prob)

    home_cards = await _event_rate(db, home_team.id, "card", fallback=2.4)
    away_cards = await _event_rate(db, away_team.id, "card", fallback=2.3)
    expected_cards = home_cards + away_cards
    cards_over_prob = _poisson_over_probability(expected_cards, line=4.5, simulations=payload.simulations)
    cards_pick = "OVER_4.5" if cards_over_prob >= 0.5 else "UNDER_4.5"
    cards_pick_prob = cards_over_prob if cards_over_prob >= 0.5 else (1.0 - cards_over_prob)

    goals_over_prob = float(simulation.over_2_5_probability)
    goals_pick = "OVER_2.5" if goals_over_prob >= 0.5 else "UNDER_2.5"
    goals_pick_prob = goals_over_prob if goals_over_prob >= 0.5 else (1.0 - goals_over_prob)

    ht_choices = [
        ("HOME", home_ht_prob),
        ("DRAW", draw_ht_prob),
        ("AWAY", away_ht_prob),
    ]
    ht_pick, ht_pick_prob = max(ht_choices, key=lambda x: x[1])

    exact_score = simulation.most_likely_score
    exact_score_prob = float(simulation.score_distribution.get(exact_score, 0) / float(payload.simulations))
    exact_score_top5 = [
        {
            "score": score,
            "probability": round(float(count) / float(payload.simulations), 4),
        }
        for score, count in sorted(
            simulation.score_distribution.items(),
            key=lambda item: item[1],
            reverse=True,
        )
    ]

    data_points = len(home_recent) + len(away_recent) + len(h2h_matches)
    confidence = max(0.45, min(0.9, 0.5 + (data_points / 250.0)))

    return {
        "input": {
            "home_team": payload.home_team,
            "away_team": payload.away_team,
            "stadium": payload.stadium,
            "simulations": payload.simulations,
        },
        "resolved": {
            "home_team_id": home_team.id,
            "home_team_name": home_team.name,
            "away_team_id": away_team.id,
            "away_team_name": away_team.name,
        },
        "model_context": {
            "home_expected_goals": round(home_lambda, 3),
            "away_expected_goals": round(away_lambda, 3),
            "expected_corners": round(expected_corners, 3),
            "expected_cards": round(expected_cards, 3),
            "h2h_matches_used": len(h2h_matches),
            "home_recent_matches_used": len(home_recent),
            "away_recent_matches_used": len(away_recent),
            "confidence": round(confidence, 3),
        },
        "recommended_bets_top5": [
            {
                "market": "GOALS_OU_2.5",
                "selection": goals_pick,
                "probability": round(goals_pick_prob, 4),
            },
            {
                "market": "CORNERS_OU_9.5",
                "selection": corners_pick,
                "probability": round(corners_pick_prob, 4),
            },
            {
                "market": "CARDS_OU_4.5",
                "selection": cards_pick,
                "probability": round(cards_pick_prob, 4),
            },
            {
                "market": "FIRST_HALF_WINNER",
                "selection": ht_pick,
                "probability": round(ht_pick_prob, 4),
            },
            {
                "market": "EXACT_SCORE",
                "selection": exact_score,
                "probability": round(exact_score_prob, 4),
            },
        ],
        "exact_score_top5": exact_score_top5,
    }


@router.get("/")
async def get_predictions(
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    """Get predictions with match and model context."""
    predictions = (
        await db.execute(
            select(Prediction)
            .options(
                selectinload(Prediction.match).selectinload(Match.home_team),
                selectinload(Prediction.match).selectinload(Match.away_team),
            )
            .order_by(Prediction.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
    ).scalars().unique().all()

    payload = []
    for p in predictions:
        payload.append(
            {
                "id": p.id,
                "market": p.market,
                "outcome": p.predicted_outcome,
                "probability": p.predicted_probability,
                "confidence": p.confidence_level,
                "model": p.model_name,
                "reasoning": p.reasoning,
                "created_at": p.created_at.isoformat() if p.created_at else None,
                "match": {
                    "id": p.match.id if p.match else None,
                    "date": p.match.match_date.isoformat() if p.match and p.match.match_date else None,
                    "home_team": p.match.home_team.name if p.match and p.match.home_team else "N/A",
                    "away_team": p.match.away_team.name if p.match and p.match.away_team else "N/A",
                },
            }
        )

    return payload


@router.post("/")
async def create_prediction():
    """Create a new prediction."""
    return {"message": "Create prediction endpoint"}
