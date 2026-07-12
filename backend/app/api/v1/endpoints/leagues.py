"""Leagues endpoints."""
from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.models import League, Match, Round, Season, Team


router = APIRouter()


@router.get("/")
async def get_leagues(db: AsyncSession = Depends(get_db)):
    """Get leagues with season/team/match counters."""
    leagues = (await db.execute(select(League))).scalars().all()

    payload = []
    for league in leagues:
        season_ids = (
            await db.execute(select(Season.id).where(Season.league_id == league.id))
        ).scalars().all()

        team_count = 0
        match_count = 0
        current_season = None

        if season_ids:
            current_season = (
                await db.execute(
                    select(Season).where(Season.league_id == league.id).order_by(Season.year.desc())
                )
            ).scalars().first()

            match_count = int(
                (
                    await db.execute(
                        select(func.count(Match.id))
                        .join(Round, Match.round_id == Round.id)
                        .where(Round.season_id.in_(season_ids))
                    )
                ).scalar_one()
                or 0
            )

            team_count = int(
                (
                    await db.execute(
                        select(func.count(Team.id.distinct()))
                        .join(Match, (Team.id == Match.home_team_id) | (Team.id == Match.away_team_id))
                        .join(Round, Match.round_id == Round.id)
                        .where(Round.season_id.in_(season_ids))
                    )
                ).scalar_one()
                or 0
            )

        payload.append(
            {
                "id": league.id,
                "name": league.name,
                "code": league.code,
                "country": league.country,
                "logo_url": league.logo_url,
                "seasons": len(season_ids),
                "current_season": current_season.year if current_season else None,
                "teams": team_count,
                "matches": match_count,
            }
        )

    return payload
