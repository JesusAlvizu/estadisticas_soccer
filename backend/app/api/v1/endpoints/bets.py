"""Bets endpoints."""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.models import Bet, Match


router = APIRouter()


class BetCreateRequest(BaseModel):
    """Payload for creating a new bet."""

    match_id: int
    sportsbook: str = "Caliente"
    market: str
    outcome: str
    odd_value: float = Field(gt=1.0)
    stake: float = Field(gt=0)
    expected_probability: float | None = Field(default=None, ge=0.0, le=1.0)
    notes: str | None = None


class BetSettleRequest(BaseModel):
    """Payload for manual bet settlement."""

    status: str = Field(pattern="^(won|lost|void)$")
    actual_payout: float = Field(ge=0)


def _evaluate_bet(bet: Bet, match: Match) -> str | None:
    """Evaluate bet outcome using available match result fields."""
    if match.home_goals is None or match.away_goals is None:
        return None

    market = (bet.market or "").strip().upper()
    outcome = (bet.outcome or "").strip().upper()

    if market in {"1X2", "MATCH_RESULT", "RESULTADO_FINAL"}:
        final_outcome = "DRAW"
        if match.home_goals > match.away_goals:
            final_outcome = "HOME"
        elif match.home_goals < match.away_goals:
            final_outcome = "AWAY"
        return "won" if final_outcome == outcome else "lost"

    if market in {"BTTS", "BOTH_TEAMS_SCORE", "AMBOS_ANOTAN"}:
        both_score = match.home_goals > 0 and match.away_goals > 0
        expected = outcome in {"YES", "SI", "TRUE"}
        return "won" if both_score == expected else "lost"

    if market in {"TOTAL_GOALS_OU", "OVER_UNDER", "GOLES_OU"}:
        # Expected format: OVER_2.5 or UNDER_3.5
        if "_" not in outcome:
            return None
        side, line_raw = outcome.split("_", 1)
        try:
            line = float(line_raw)
        except ValueError:
            return None

        total_goals = float(match.home_goals + match.away_goals)
        if side == "OVER":
            return "won" if total_goals > line else "lost"
        if side == "UNDER":
            return "won" if total_goals < line else "lost"
        return None

    return None


def _build_bet_payload(bet: Bet) -> dict:
    """Serialize bet with match context."""
    match = bet.match
    return {
        "id": bet.id,
        "match_id": bet.match_id,
        "sportsbook": bet.sportsbook,
        "market": bet.market,
        "outcome": bet.outcome,
        "odd_value": bet.odd_value,
        "stake": bet.stake,
        "expected_probability": bet.expected_probability,
        "status": bet.status,
        "potential_payout": bet.potential_payout,
        "actual_payout": bet.actual_payout,
        "placed_at": bet.placed_at.isoformat() if bet.placed_at else None,
        "settled_at": bet.settled_at.isoformat() if bet.settled_at else None,
        "notes": bet.notes,
        "match": {
            "id": match.id if match else None,
            "date": match.match_date.isoformat() if match and match.match_date else None,
            "status": match.status if match else None,
            "home_team": match.home_team.name if match and match.home_team else "N/A",
            "away_team": match.away_team.name if match and match.away_team else "N/A",
            "score_home": match.home_goals if match else None,
            "score_away": match.away_goals if match else None,
        },
    }


@router.get("/")
async def list_bets(
    status: str | None = Query(default=None),
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    """List bets with optional status filter."""
    query = (
        select(Bet)
        .options(
            selectinload(Bet.match).selectinload(Match.home_team),
            selectinload(Bet.match).selectinload(Match.away_team),
        )
        .order_by(Bet.placed_at.desc())
        .offset(skip)
        .limit(limit)
    )
    if status:
        query = query.where(Bet.status == status)

    bets = (await db.execute(query)).scalars().unique().all()
    return [_build_bet_payload(bet) for bet in bets]


@router.post("/")
async def create_bet(payload: BetCreateRequest, db: AsyncSession = Depends(get_db)):
    """Create a new registered bet."""
    match = (
        await db.execute(
            select(Match)
            .options(selectinload(Match.home_team), selectinload(Match.away_team))
            .where(Match.id == payload.match_id)
        )
    ).scalar_one_or_none()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    potential = float(payload.stake * payload.odd_value)
    bet = Bet(
        match_id=payload.match_id,
        sportsbook=payload.sportsbook,
        market=payload.market,
        outcome=payload.outcome,
        odd_value=payload.odd_value,
        stake=payload.stake,
        expected_probability=payload.expected_probability,
        status="open",
        potential_payout=potential,
        actual_payout=0.0,
        notes=payload.notes,
    )
    db.add(bet)
    await db.commit()
    await db.refresh(bet)

    bet = (
        await db.execute(
            select(Bet)
            .options(
                selectinload(Bet.match).selectinload(Match.home_team),
                selectinload(Bet.match).selectinload(Match.away_team),
            )
            .where(Bet.id == bet.id)
        )
    ).scalar_one()
    return _build_bet_payload(bet)


@router.post("/{bet_id}/settle")
async def settle_bet(bet_id: int, payload: BetSettleRequest, db: AsyncSession = Depends(get_db)):
    """Settle a bet manually."""
    bet = (
        await db.execute(
            select(Bet)
            .options(
                selectinload(Bet.match).selectinload(Match.home_team),
                selectinload(Bet.match).selectinload(Match.away_team),
            )
            .where(Bet.id == bet_id)
        )
    ).scalar_one_or_none()
    if not bet:
        raise HTTPException(status_code=404, detail="Bet not found")

    bet.status = payload.status
    bet.actual_payout = payload.actual_payout
    bet.settled_at = datetime.utcnow()
    await db.commit()
    await db.refresh(bet)
    return _build_bet_payload(bet)


@router.post("/settle/auto")
async def auto_settle_bets(db: AsyncSession = Depends(get_db)):
    """Auto-settle open bets for finished matches with available score."""
    open_bets = (
        await db.execute(
            select(Bet)
            .options(selectinload(Bet.match))
            .where(Bet.status == "open")
        )
    ).scalars().all()

    settled = 0
    skipped = 0

    for bet in open_bets:
        match = bet.match
        if not match:
            skipped += 1
            continue

        normalized_status = (match.status or "").upper()
        if normalized_status not in {"FT", "AET", "PEN", "FINISHED"}:
            skipped += 1
            continue

        result = _evaluate_bet(bet, match)
        if result is None:
            skipped += 1
            continue

        bet.status = result
        bet.actual_payout = bet.potential_payout if result == "won" else 0.0
        bet.settled_at = datetime.utcnow()
        settled += 1

    await db.commit()

    return {
        "status": "ok",
        "open_bets_checked": len(open_bets),
        "settled": settled,
        "skipped": skipped,
    }
