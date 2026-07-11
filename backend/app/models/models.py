"""Database models for the application."""
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    String,
    Integer,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    UniqueConstraint,
    Enum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Sport(Base):
    """Sports entity."""

    __tablename__ = "sports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    code: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    leagues = relationship("League", back_populates="sport")

    __table_args__ = (Index("idx_sport_code", "code"),)


class League(Base):
    """League entity."""

    __tablename__ = "leagues"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sport_id: Mapped[int] = mapped_column(Integer, ForeignKey("sports.id"))
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str] = mapped_column(String(20), nullable=False)
    country: Mapped[str] = mapped_column(String(100), nullable=True)
    logo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    sport = relationship("Sport", back_populates="leagues")
    seasons = relationship("Season", back_populates="league")

    __table_args__ = (
        UniqueConstraint("sport_id", "code", name="uq_league_sport_code"),
        Index("idx_league_sport", "sport_id"),
    )


class Season(Base):
    """Season entity."""

    __tablename__ = "seasons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    league_id: Mapped[int] = mapped_column(Integer, ForeignKey("leagues.id"))
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    start_date: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    end_date: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    league = relationship("League", back_populates="seasons")
    rounds = relationship("Round", back_populates="season")
    teams_season = relationship("TeamSeason", back_populates="season")

    __table_args__ = (
        UniqueConstraint("league_id", "year", name="uq_season_league_year"),
        Index("idx_season_league", "league_id"),
    )


class Round(Base):
    """Round/Gameweek entity."""

    __tablename__ = "rounds"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    season_id: Mapped[int] = mapped_column(Integer, ForeignKey("seasons.id"))
    round_number: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    start_date: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    end_date: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    season = relationship("Season", back_populates="rounds")
    matches = relationship("Match", back_populates="round")

    __table_args__ = (
        UniqueConstraint("season_id", "round_number", name="uq_round_season_number"),
        Index("idx_round_season", "season_id"),
    )


class Team(Base):
    """Team entity."""

    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sport_id: Mapped[int] = mapped_column(Integer, ForeignKey("sports.id"))
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str] = mapped_column(String(10), nullable=False)
    country: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    logo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    sport = relationship("Sport")
    seasons = relationship("TeamSeason", back_populates="team")
    home_matches = relationship(
        "Match", foreign_keys="Match.home_team_id", back_populates="home_team"
    )
    away_matches = relationship(
        "Match", foreign_keys="Match.away_team_id", back_populates="away_team"
    )
    players = relationship("Player", back_populates="team")

    __table_args__ = (
        UniqueConstraint("code", "sport_id", name="uq_team_code_sport"),
        Index("idx_team_sport", "sport_id"),
    )


class TeamSeason(Base):
    """Team season statistics."""

    __tablename__ = "team_seasons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    team_id: Mapped[int] = mapped_column(Integer, ForeignKey("teams.id"))
    season_id: Mapped[int] = mapped_column(Integer, ForeignKey("seasons.id"))
    matches_played: Mapped[int] = mapped_column(Integer, default=0)
    wins: Mapped[int] = mapped_column(Integer, default=0)
    draws: Mapped[int] = mapped_column(Integer, default=0)
    losses: Mapped[int] = mapped_column(Integer, default=0)
    goals_for: Mapped[int] = mapped_column(Integer, default=0)
    goals_against: Mapped[int] = mapped_column(Integer, default=0)
    goal_difference: Mapped[int] = mapped_column(Integer, default=0)
    points: Mapped[int] = mapped_column(Integer, default=0)
    position: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    average_goals: Mapped[float] = mapped_column(Float, default=0.0)
    average_expected_goals: Mapped[float] = mapped_column(Float, default=0.0)
    possession_percentage: Mapped[float] = mapped_column(Float, default=0.0)
    clean_sheets: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    team = relationship("Team", back_populates="seasons")
    season = relationship("Season", back_populates="teams_season")

    __table_args__ = (
        UniqueConstraint("team_id", "season_id", name="uq_team_season"),
        Index("idx_team_season_team", "team_id"),
        Index("idx_team_season_season", "season_id"),
    )


class Player(Base):
    """Player entity."""

    __tablename__ = "players"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    team_id: Mapped[int] = mapped_column(Integer, ForeignKey("teams.id"))
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    first_name: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    position: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    shirt_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    date_of_birth: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True
    )
    nationality: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    height: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    weight: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    photo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    team = relationship("Team", back_populates="players")
    statistics = relationship("PlayerStatistic", back_populates="player")
    injuries = relationship("Injury", back_populates="player")
    suspensions = relationship("Suspension", back_populates="player")

    __table_args__ = (Index("idx_player_team", "team_id"),)


class PlayerStatistic(Base):
    """Player statistics entity."""

    __tablename__ = "player_statistics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    player_id: Mapped[int] = mapped_column(Integer, ForeignKey("players.id"))
    season_id: Mapped[int] = mapped_column(Integer, ForeignKey("seasons.id"))
    matches_played: Mapped[int] = mapped_column(Integer, default=0)
    goals: Mapped[int] = mapped_column(Integer, default=0)
    assists: Mapped[int] = mapped_column(Integer, default=0)
    yellow_cards: Mapped[int] = mapped_column(Integer, default=0)
    red_cards: Mapped[int] = mapped_column(Integer, default=0)
    minutes_played: Mapped[int] = mapped_column(Integer, default=0)
    shots: Mapped[int] = mapped_column(Integer, default=0)
    shots_on_target: Mapped[int] = mapped_column(Integer, default=0)
    expected_goals: Mapped[float] = mapped_column(Float, default=0.0)
    expected_assists: Mapped[float] = mapped_column(Float, default=0.0)
    pass_accuracy: Mapped[float] = mapped_column(Float, default=0.0)
    tackles: Mapped[int] = mapped_column(Integer, default=0)
    interceptions: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    player = relationship("Player", back_populates="statistics")
    season = relationship("Season")

    __table_args__ = (
        UniqueConstraint("player_id", "season_id", name="uq_player_season"),
        Index("idx_player_stat_player", "player_id"),
        Index("idx_player_stat_season", "season_id"),
    )


class Match(Base):
    """Match entity."""

    __tablename__ = "matches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    round_id: Mapped[int] = mapped_column(Integer, ForeignKey("rounds.id"))
    home_team_id: Mapped[int] = mapped_column(Integer, ForeignKey("teams.id"))
    away_team_id: Mapped[int] = mapped_column(Integer, ForeignKey("teams.id"))
    match_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="scheduled")
    home_goals: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    away_goals: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    home_goals_halftime: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )
    away_goals_halftime: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True
    )
    home_expected_goals: Mapped[float] = mapped_column(Float, default=0.0)
    away_expected_goals: Mapped[float] = mapped_column(Float, default=0.0)
    home_possession: Mapped[float] = mapped_column(Float, default=0.0)
    away_possession: Mapped[float] = mapped_column(Float, default=0.0)
    venue: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    referee: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    weather: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    round = relationship("Round", back_populates="matches")
    home_team = relationship("Team", foreign_keys=[home_team_id], back_populates="home_matches")
    away_team = relationship("Team", foreign_keys=[away_team_id], back_populates="away_matches")
    lineups = relationship("Lineup", back_populates="match")
    events = relationship("MatchEvent", back_populates="match")
    odds = relationship("Odd", back_populates="match")
    predictions = relationship("Prediction", back_populates="match")

    __table_args__ = (
        Index("idx_match_round", "round_id"),
        Index("idx_match_home_team", "home_team_id"),
        Index("idx_match_away_team", "away_team_id"),
        Index("idx_match_date", "match_date"),
    )


class Lineup(Base):
    """Match lineup entity."""

    __tablename__ = "lineups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    match_id: Mapped[int] = mapped_column(Integer, ForeignKey("matches.id"))
    team_id: Mapped[int] = mapped_column(Integer, ForeignKey("teams.id"))
    player_id: Mapped[int] = mapped_column(Integer, ForeignKey("players.id"))
    position: Mapped[str] = mapped_column(String(20), nullable=False)
    formation_position: Mapped[Optional[str]] = mapped_column(String(5), nullable=True)
    is_starter: Mapped[bool] = mapped_column(Boolean, default=False)
    substitute_in_minute: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    substitute_out_minute: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    match = relationship("Match", back_populates="lineups")
    team = relationship("Team")
    player = relationship("Player")

    __table_args__ = (
        Index("idx_lineup_match", "match_id"),
        Index("idx_lineup_team", "team_id"),
    )


class MatchEvent(Base):
    """Match event entity."""

    __tablename__ = "match_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    match_id: Mapped[int] = mapped_column(Integer, ForeignKey("matches.id"))
    player_id: Mapped[int] = mapped_column(Integer, ForeignKey("players.id"))
    team_id: Mapped[int] = mapped_column(Integer, ForeignKey("teams.id"))
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    minute: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    match = relationship("Match", back_populates="events")
    player = relationship("Player")
    team = relationship("Team")

    __table_args__ = (Index("idx_event_match", "match_id"),)


class Injury(Base):
    """Injury entity."""

    __tablename__ = "injuries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    player_id: Mapped[int] = mapped_column(Integer, ForeignKey("players.id"))
    injury_type: Mapped[str] = mapped_column(String(100), nullable=False)
    start_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    expected_return_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    player = relationship("Player", back_populates="injuries")

    __table_args__ = (Index("idx_injury_player", "player_id"),)


class Suspension(Base):
    """Suspension entity."""

    __tablename__ = "suspensions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    player_id: Mapped[int] = mapped_column(Integer, ForeignKey("players.id"))
    reason: Mapped[str] = mapped_column(String(100), nullable=False)
    start_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    matches_remaining: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    player = relationship("Player", back_populates="suspensions")

    __table_args__ = (Index("idx_suspension_player", "player_id"),)


class Transfer(Base):
    """Transfer entity."""

    __tablename__ = "transfers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    player_id: Mapped[int] = mapped_column(Integer, ForeignKey("players.id"))
    from_team_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("teams.id"), nullable=True
    )
    to_team_id: Mapped[int] = mapped_column(Integer, ForeignKey("teams.id"))
    transfer_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    transfer_fee: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    type: Mapped[str] = mapped_column(String(20), default="transfer")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    player = relationship("Player")
    from_team = relationship("Team", foreign_keys=[from_team_id])
    to_team = relationship("Team", foreign_keys=[to_team_id])


class Bookmaker(Base):
    """Bookmaker entity."""

    __tablename__ = "bookmakers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    odds = relationship("Odd", back_populates="bookmaker")

    __table_args__ = (Index("idx_bookmaker_code", "code"),)


class Market(Base):
    """Betting market entity."""

    __tablename__ = "markets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    odds = relationship("Odd", back_populates="market")

    __table_args__ = (Index("idx_market_code", "code"),)


class Odd(Base):
    """Betting odds entity."""

    __tablename__ = "odds"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    match_id: Mapped[int] = mapped_column(Integer, ForeignKey("matches.id"))
    bookmaker_id: Mapped[int] = mapped_column(Integer, ForeignKey("bookmakers.id"))
    market_id: Mapped[int] = mapped_column(Integer, ForeignKey("markets.id"))
    outcome: Mapped[str] = mapped_column(String(50), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    probability: Mapped[float] = mapped_column(Float, default=0.0)
    last_updated: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    match = relationship("Match", back_populates="odds")
    bookmaker = relationship("Bookmaker", back_populates="odds")
    market = relationship("Market", back_populates="odds")

    __table_args__ = (
        Index("idx_odd_match", "match_id"),
        Index("idx_odd_bookmaker", "bookmaker_id"),
        Index("idx_odd_market", "market_id"),
    )


class Prediction(Base):
    """Prediction entity."""

    __tablename__ = "predictions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    match_id: Mapped[int] = mapped_column(Integer, ForeignKey("matches.id"))
    market: Mapped[str] = mapped_column(String(50), nullable=False)
    predicted_outcome: Mapped[str] = mapped_column(String(50), nullable=False)
    predicted_probability: Mapped[float] = mapped_column(Float, nullable=False)
    confidence_level: Mapped[float] = mapped_column(Float, nullable=False)
    model_name: Mapped[str] = mapped_column(String(50), nullable=False)
    reasoning: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    match = relationship("Match", back_populates="predictions")

    __table_args__ = (
        Index("idx_prediction_match", "match_id"),
        Index("idx_prediction_model", "model_name"),
    )


class SimulationResult(Base):
    """Simulation result entity."""

    __tablename__ = "simulation_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    match_id: Mapped[int] = mapped_column(Integer, ForeignKey("matches.id"))
    simulation_count: Mapped[int] = mapped_column(Integer, nullable=False)
    home_win_probability: Mapped[float] = mapped_column(Float, nullable=False)
    draw_probability: Mapped[float] = mapped_column(Float, nullable=False)
    away_win_probability: Mapped[float] = mapped_column(Float, nullable=False)
    most_likely_score: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    average_goals: Mapped[float] = mapped_column(Float, nullable=False)
    over_under_25_probability: Mapped[float] = mapped_column(Float, default=0.0)
    both_score_probability: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    match = relationship("Match")

    __table_args__ = (Index("idx_simulation_match", "match_id"),)


class User(Base):
    """User entity."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    first_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (
        Index("idx_user_email", "email"),
        Index("idx_user_username", "username"),
    )
