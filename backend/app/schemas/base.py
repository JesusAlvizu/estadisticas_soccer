"""Pydantic schemas for API requests and responses."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


# Sports
class SportBase(BaseModel):
    """Base sport schema."""

    name: str
    code: str


class SportCreate(SportBase):
    """Create sport schema."""

    pass


class SportUpdate(BaseModel):
    """Update sport schema."""

    name: Optional[str] = None
    code: Optional[str] = None


class SportResponse(SportBase):
    """Sport response schema."""

    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        """Pydantic configuration."""

        from_attributes = True


# Teams
class TeamBase(BaseModel):
    """Base team schema."""

    name: str
    code: str
    country: Optional[str] = None
    logo_url: Optional[str] = None


class TeamCreate(TeamBase):
    """Create team schema."""

    sport_id: int


class TeamUpdate(BaseModel):
    """Update team schema."""

    name: Optional[str] = None
    country: Optional[str] = None
    logo_url: Optional[str] = None


class TeamResponse(TeamBase):
    """Team response schema."""

    id: int
    sport_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        """Pydantic configuration."""

        from_attributes = True


# Matches
class MatchBase(BaseModel):
    """Base match schema."""

    match_date: datetime
    home_team_id: int
    away_team_id: int
    round_id: int
    venue: Optional[str] = None


class MatchCreate(MatchBase):
    """Create match schema."""

    pass


class MatchUpdate(BaseModel):
    """Update match schema."""

    status: Optional[str] = None
    home_goals: Optional[int] = None
    away_goals: Optional[int] = None
    home_expected_goals: Optional[float] = None
    away_expected_goals: Optional[float] = None


class MatchResponse(MatchBase):
    """Match response schema."""

    id: int
    status: str
    home_goals: Optional[int]
    away_goals: Optional[int]
    created_at: datetime
    updated_at: datetime

    class Config:
        """Pydantic configuration."""

        from_attributes = True


# Players
class PlayerBase(BaseModel):
    """Base player schema."""

    name: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    position: Optional[str] = None
    shirt_number: Optional[int] = None
    date_of_birth: Optional[datetime] = None


class PlayerCreate(PlayerBase):
    """Create player schema."""

    team_id: int


class PlayerUpdate(BaseModel):
    """Update player schema."""

    position: Optional[str] = None
    shirt_number: Optional[int] = None


class PlayerResponse(PlayerBase):
    """Player response schema."""

    id: int
    team_id: int
    nationality: Optional[str]
    photo_url: Optional[str]
    created_at: datetime

    class Config:
        """Pydantic configuration."""

        from_attributes = True


# Predictions
class PredictionBase(BaseModel):
    """Base prediction schema."""

    market: str
    predicted_outcome: str
    predicted_probability: float = Field(..., ge=0.0, le=1.0)
    confidence_level: float = Field(..., ge=0.0, le=1.0)
    model_name: str
    reasoning: Optional[str] = None


class PredictionCreate(PredictionBase):
    """Create prediction schema."""

    match_id: int


class PredictionResponse(PredictionBase):
    """Prediction response schema."""

    id: int
    match_id: int
    created_at: datetime

    class Config:
        """Pydantic configuration."""

        from_attributes = True


# Odds
class OddBase(BaseModel):
    """Base odd schema."""

    outcome: str
    value: float = Field(..., gt=0)
    probability: float = Field(..., ge=0.0, le=1.0)


class OddCreate(OddBase):
    """Create odd schema."""

    match_id: int
    bookmaker_id: int
    market_id: int


class OddResponse(OddBase):
    """Odd response schema."""

    id: int
    match_id: int
    bookmaker_id: int
    market_id: int
    last_updated: datetime

    class Config:
        """Pydantic configuration."""

        from_attributes = True


# Simulation
class SimulationResultBase(BaseModel):
    """Base simulation result schema."""

    simulation_count: int = Field(..., gt=0)
    home_win_probability: float = Field(..., ge=0.0, le=1.0)
    draw_probability: float = Field(..., ge=0.0, le=1.0)
    away_win_probability: float = Field(..., ge=0.0, le=1.0)
    average_goals: float = Field(..., ge=0.0)


class SimulationResultResponse(SimulationResultBase):
    """Simulation result response schema."""

    id: int
    match_id: int
    most_likely_score: Optional[str]
    over_under_25_probability: float
    both_score_probability: float
    created_at: datetime

    class Config:
        """Pydantic configuration."""

        from_attributes = True


# Users
class UserBase(BaseModel):
    """Base user schema."""

    email: EmailStr
    username: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class UserCreate(UserBase):
    """Create user schema."""

    password: str = Field(..., min_length=8)


class UserUpdate(BaseModel):
    """Update user schema."""

    first_name: Optional[str] = None
    last_name: Optional[str] = None


class UserResponse(UserBase):
    """User response schema."""

    id: int
    is_active: bool
    is_admin: bool
    created_at: datetime

    class Config:
        """Pydantic configuration."""

        from_attributes = True


# Auth
class TokenResponse(BaseModel):
    """Token response schema."""

    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    """Login request schema."""

    username: str
    password: str


# Pagination
class PaginationParams(BaseModel):
    """Pagination parameters."""

    skip: int = Field(0, ge=0)
    limit: int = Field(10, ge=1, le=100)


class PaginatedResponse(BaseModel):
    """Paginated response schema."""

    total: int
    skip: int
    limit: int
    items: list
