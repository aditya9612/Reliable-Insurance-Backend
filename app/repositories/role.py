from typing import Optional, Sequence
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import UserRole
from app.repositories.base import BaseRepository


class RoleRepository(BaseRepository[UserRole]):
    """
    Data-access repository for UserRole entity (tbl_userrole).
    Strictly data-access oriented; contains NO authorization logic.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(UserRole, session)

    async def get_by_name(self, role_name: str) -> Optional[UserRole]:
        """Lookup role by UserRole name (case-insensitive)."""
        query = select(UserRole).where(UserRole.UserRole.ilike(role_name))
        result = await self.session.execute(query)
        return result.scalars().first()

    async def get_by_code(self, code: str) -> Optional[UserRole]:
        """Lookup role by unique code identifier (case-insensitive)."""
        query = select(UserRole).where(UserRole.code.ilike(code))
        result = await self.session.execute(query)
        return result.scalars().first()

    async def list_active(self) -> Sequence[UserRole]:
        """List all active roles (isdeleted != '1')."""
        query = select(UserRole).where(
            (UserRole.isdeleted == None) | (UserRole.isdeleted != "1")  # noqa: E711
        )
        result = await self.session.execute(query)
        return result.scalars().all()
