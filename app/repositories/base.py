from typing import Generic, TypeVar, Type, Optional, Sequence, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete as sa_delete
from app.db.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """
    Generic asynchronous SQLAlchemy repository providing foundational CRUD primitives.
    Contains strictly data-access routines without business logic or calculations.
    """

    def __init__(self, model: Type[ModelType], session: AsyncSession) -> None:
        self.model = model
        self.session = session

    async def get_by_id(self, id_val: Any) -> Optional[ModelType]:
        """Fetch single entity by primary key."""
        return await self.session.get(self.model, id_val)

    async def list(self, offset: int = 0, limit: int = 100) -> Sequence[ModelType]:
        """List entities with pagination."""
        query = select(self.model).offset(offset).limit(limit)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def create(self, instance: ModelType) -> ModelType:
        """Add and flush entity to session."""
        self.session.add(instance)
        await self.session.flush()
        return instance

    async def update(self, instance: ModelType) -> ModelType:
        """Flush changes to session."""
        await self.session.flush()
        return instance

    async def delete(self, instance: ModelType) -> None:
        """Delete entity from session."""
        await self.session.delete(instance)
        await self.session.flush()

    async def count(self) -> int:
        """Count total entities in table."""
        pk_column = list(self.model.__table__.primary_key.columns)[0]
        query = select(func.count(pk_column))
        result = await self.session.execute(query)
        return result.scalar_one() or 0

    async def exists(self, id_val: Any) -> bool:
        """Check if an entity exists by primary key."""
        pk_column = list(self.model.__table__.primary_key.columns)[0]
        query = select(func.count(pk_column)).where(pk_column == id_val)
        result = await self.session.execute(query)
        cnt = result.scalar_one() or 0
        return cnt > 0
