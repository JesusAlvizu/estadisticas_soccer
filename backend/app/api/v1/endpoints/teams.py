"""Teams endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.base import TeamCreate, TeamResponse
from app.models.models import Team, Sport

router = APIRouter()


@router.get("/", response_model=list[TeamResponse])
async def get_teams(skip: int = 0, limit: int = 10, db: AsyncSession = Depends(get_db)):
    """Get all teams with pagination."""
    from sqlalchemy import select

    result = await db.execute(select(Team).offset(skip).limit(limit))
    teams = result.scalars().all()
    return teams


@router.post("/", response_model=TeamResponse)
async def create_team(team: TeamCreate, db: AsyncSession = Depends(get_db)):
    """Create a new team."""
    # Check if sport exists
    from sqlalchemy import select

    sport_result = await db.execute(select(Sport).where(Sport.id == team.sport_id))
    if not sport_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Sport not found")

    db_team = Team(**team.model_dump())
    db.add(db_team)
    await db.commit()
    await db.refresh(db_team)
    return db_team


@router.get("/{team_id}", response_model=TeamResponse)
async def get_team(team_id: int, db: AsyncSession = Depends(get_db)):
    """Get a team by ID."""
    from sqlalchemy import select

    result = await db.execute(select(Team).where(Team.id == team_id))
    team = result.scalar_one_or_none()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    return team
