"""Matches endpoints."""
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.models import Match, Odd

router = APIRouter()


@router.get("/")
async def get_matches(
    skip: int = 0,
    limit: int = 20,
    upcoming_only: bool = False,
    db: AsyncSession = Depends(get_db),
):
    """Get matches with teams, odds and predictions."""
    query = (
        select(Match)
        .options(
            selectinload(Match.home_team),
            selectinload(Match.away_team),
            selectinload(Match.odds).selectinload(Odd.bookmaker),
            selectinload(Match.odds).selectinload(Odd.market),
            selectinload(Match.predictions),
        )
        .order_by(Match.match_date.desc())
        .offset(skip)
        .limit(limit)
    )
    if upcoming_only:
        query = query.where(Match.match_date >= datetime.utcnow())

    matches = (await db.execute(query)).scalars().unique().all()

    payload = []
    for match in matches:
        odds = []
        for odd in match.odds[:12]:
            odds.append(
                {
                    "id": odd.id,
                    "bookmaker": odd.bookmaker.name if odd.bookmaker else None,
                    "market": odd.market.name if odd.market else None,
                    "outcome": odd.outcome,
                    "odd": odd.value,
                    "implied_probability": odd.probability,
                    "updated_at": odd.last_updated.isoformat() if odd.last_updated else None,
                }
            )

        predictions = []
        for p in match.predictions:
            predictions.append(
                {
                    "id": p.id,
                    "market": p.market,
                    "outcome": p.predicted_outcome,
                    "probability": p.predicted_probability,
                    "confidence": p.confidence_level,
                    "model": p.model_name,
                }
            )

        payload.append(
            {
                "id": match.id,
                "match_date": match.match_date.isoformat() if match.match_date else None,
                "status": match.status,
                "home_team": {
                    "id": match.home_team.id if match.home_team else None,
                    "name": match.home_team.name if match.home_team else "N/A",
                },
                "away_team": {
                    "id": match.away_team.id if match.away_team else None,
                    "name": match.away_team.name if match.away_team else "N/A",
                },
                "score": {
                    "home": match.home_goals,
                    "away": match.away_goals,
                },
                "odds": odds,
                "predictions": predictions,
            }
        )

    return payload


@router.post("/")
async def create_match():
    """Create a new match."""
    return {"message": "Create match endpoint"}
