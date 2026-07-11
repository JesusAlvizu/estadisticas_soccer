"""Base repository class."""
from typing import TypeVar, Generic, Type, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

T = TypeVar('T')


class BaseRepository(Generic[T]):
    """Generic repository for CRUD operations."""

    def __init__(self, session: AsyncSession, model: Type[T]):
        """Initialize repository."""
        self.session = session
        self.model = model

    async def create(self, obj_in: dict) -> T:
        """Create a new record."""
        db_obj = self.model(**obj_in)
        self.session.add(db_obj)
        await self.session.commit()
        await self.session.refresh(db_obj)
        return db_obj

    async def get(self, id: int) -> Optional[T]:
        """Get a record by ID."""
        result = await self.session.execute(
            select(self.model).where(self.model.id == id)
        )
        return result.scalar_one_or_none()

    async def get_all(
        self, skip: int = 0, limit: int = 10
    ) -> tuple[List[T], int]:
        """Get all records with pagination."""
        # Get total count
        count_result = await self.session.execute(
            select(func.count(self.model.id))
        )
        total = count_result.scalar()

        # Get paginated records
        result = await self.session.execute(
            select(self.model).offset(skip).limit(limit)
        )
        records = result.scalars().all()
        return records, total

    async def update(self, id: int, obj_in: dict) -> Optional[T]:
        """Update a record."""
        db_obj = await self.get(id)
        if not db_obj:
            return None

        for key, value in obj_in.items():
            setattr(db_obj, key, value)

        await self.session.commit()
        await self.session.refresh(db_obj)
        return db_obj

    async def delete(self, id: int) -> bool:
        """Delete a record."""
        db_obj = await self.get(id)
        if not db_obj:
            return False

        await self.session.delete(db_obj)
        await self.session.commit()
        return True
