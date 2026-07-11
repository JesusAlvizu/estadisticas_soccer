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

    # Application Settings
    MAX_SIMULATIONS: int = 10000
    MODELS_RETRAIN_FREQUENCY: str = "daily"
    ODDS_UPDATE_FREQUENCY: str = "hourly"

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
