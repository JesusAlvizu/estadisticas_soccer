"""Application settings and configuration."""
from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # API
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Estadísticas Soccer"
    PROJECT_DESCRIPTION: str = "Plataforma de análisis estadístico deportivo con IA"
    VERSION: str = "1.0.0"

    # Database
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/estadisticas_db"
    DATABASE_ECHO: bool = False

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # RabbitMQ
    RABBITMQ_URL: str = "amqp://guest:guest@localhost:5672/"
    CELERY_BROKER_URL: Optional[str] = None
    CELERY_RESULT_BACKEND: Optional[str] = None

    # JWT
    JWT_SECRET_KEY: str = "dev-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 24

    # APIs externas
    API_KEY_FOOTBALL: Optional[str] = None
    API_KEY_SPORTS: Optional[str] = None
    API_KEY_RAPIDAPI: Optional[str] = None
    SPORTMONKS_API_KEY: Optional[str] = None
    SPORTMONKS_BASE_URL: str = "https://api.sportmonks.com/v3/football"
    SPORTMONKS_LEAGUE_ID: int = 262
    SPORTMONKS_DAILY_LIMIT: int = 250
    SPORTMONKS_QUOTA_FILE: str = "/tmp/sportmonks_quota.json"
    SPORTMONKS_RATE_LIMIT_FILE: str = "/tmp/sportmonks_rate_limit.json"
    API_FOOTBALL_DAILY_LIMIT: int = 100
    API_FOOTBALL_QUOTA_FILE: str = "/tmp/api_football_quota.json"

    # Application Settings
    MAX_SIMULATIONS: int = 10000
    MODELS_RETRAIN_FREQUENCY: str = "daily"
    ODDS_UPDATE_FREQUENCY: str = "hourly"

    # Liga MX focus (API-Football league id 262)
    LIGA_MX_SYNC_ENABLED: bool = True
    LIGA_MX_LEAGUE_ID: int = 262
    LIGA_MX_SEASON: int = 2026
    LIGA_MX_TOURNAMENT_START: Optional[str] = None
    LIGA_MX_TOURNAMENT_END: Optional[str] = None

    # Sync cadences (minutes)
    SYNC_TEAMS_MINUTES: int = 720
    SYNC_PLAYERS_MINUTES: int = 360
    SYNC_MATCHES_MINUTES: int = 15
    SYNC_STATISTICS_MINUTES: int = 15
    SYNC_ODDS_MINUTES: int = 5
    GENERATE_PREDICTIONS_MINUTES: int = 5
    DAILY_SYNC_HOUR_UTC: int = 3
    DAILY_SYNC_MINUTE_UTC: int = 0
    DAILY_PREDICTIONS_HOUR_UTC: int = 4
    DAILY_PREDICTIONS_MINUTE_UTC: int = 0
    HISTORICAL_SEASONS_COUNT: int = 10

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:8000"]

    class Config:
        """Pydantic settings configuration."""

        env_file = ".env"
        case_sensitive = True


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
