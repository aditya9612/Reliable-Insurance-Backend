from typing import Optional, Sequence
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """
    Data-access repository for User entity (tbl_user).
    Strictly data-access oriented; contains NO password policy, JWT issuance, or business rules.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(User, session)

    async def get_by_username(self, username: str) -> Optional[User]:
        """Lookup user by unique UserName."""
        query = select(User).where(User.UserName == username)
        result = await self.session.execute(query)
        return result.scalars().first()

    async def get_by_mobile(self, mobile_no: str) -> Optional[User]:
        """Lookup user by mobile_no."""
        query = select(User).where(User.mobile_no == mobile_no)
        result = await self.session.execute(query)
        return result.scalars().first()

    async def get_by_role_id(self, role_id: int) -> Sequence[User]:
        """Lookup users mapped to specific UserRoleId."""
        query = select(User).where(User.UserRoleId == role_id)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_by_branch_id(self, branch_id: int) -> Sequence[User]:
        """Lookup users assigned to specific BranchId."""
        query = select(User).where(User.BranchId == branch_id)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def update_password(self, user: User, new_hashed_password: str) -> User:
        """
        Updates the user's password hash in the session.
        SAFETY RULE: Only applied to local development database; never touches legacy production.
        """
        user.UserPassword = new_hashed_password
        user.UpdateDate = datetime.utcnow()
        await self.session.flush()
        return user

    async def update_status(self, user: User, is_deleted: str) -> User:
        """Updates user account active/deleted status ('0'=active, '1'=deleted)."""
        user.isdeleted = is_deleted
        user.UpdateDate = datetime.utcnow()
        await self.session.flush()
        return user
