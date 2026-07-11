"""Base service class."""
from typing import TypeVar, Generic, Type, List, Optional

T = TypeVar('T')


class BaseService(Generic[T]):
    """Generic service for business logic."""

    def __init__(self, repository):
        """Initialize service."""
        self.repository = repository

    async def create(self, obj_in: dict) -> T:
        """Create a new record."""
        return await self.repository.create(obj_in)

    async def get(self, id: int) -> Optional[T]:
        """Get a record by ID."""
        return await self.repository.get(id)

    async def get_all(
        self, skip: int = 0, limit: int = 10
    ) -> tuple[List[T], int]:
        """Get all records."""
        return await self.repository.get_all(skip=skip, limit=limit)

    async def update(self, id: int, obj_in: dict) -> Optional[T]:
        """Update a record."""
        return await self.repository.update(id, obj_in)

    async def delete(self, id: int) -> bool:
        """Delete a record."""
        return await self.repository.delete(id)
