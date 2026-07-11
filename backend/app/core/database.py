"""Database configuration and session management."""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool

from app.core.config.settings import get_settings

settings = get_settings()

# Convert postgresql:// to postgresql+asyncpg://
async_database_url = settings.DATABASE_URL.replace(
    "postgresql://", "postgresql+asyncpg://"
)

# Create async engine
engine = create_async_engine(
    async_database_url,
    echo=settings.DATABASE_ECHO,
    future=True,
    pool_pre_ping=True,
    poolclass=NullPool,
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

# Create base model class
Base = declarative_base()


async def get_db() -> AsyncSession:
    """Get database session."""
    async with AsyncSessionLocal() as session:
        yield session
