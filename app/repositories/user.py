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

    async def list_users(
        self,
        search: Optional[str] = None,
        branch_id: Optional[int] = None,
        role_id: Optional[int] = None,
        is_active: Optional[bool] = None,
        offset: int = 0,
        limit: int = 50,
    ) -> Sequence[User]:
        """List users with pagination and search/filters."""
        query = select(User)
        if search:
            s = f"%{search}%"
            query = query.where((User.UserName.ilike(s)) | (User.mobile_no.ilike(s)))
        if branch_id is not None:
            query = query.where(User.BranchId == branch_id)
        if role_id is not None:
            query = query.where(User.UserRoleId == role_id)
        if is_active is True:
            query = query.where((User.isdeleted == None) | (User.isdeleted != "1"))  # noqa: E711
        elif is_active is False:
            query = query.where(User.isdeleted == "1")

        query = query.order_by(User.UserId.desc()).offset(offset).limit(limit)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def count_users(
        self,
        search: Optional[str] = None,
        branch_id: Optional[int] = None,
        role_id: Optional[int] = None,
        is_active: Optional[bool] = None,
    ) -> int:
        """Count users matching search/filters."""
        from sqlalchemy import func
        query = select(func.count(User.UserId))
        if search:
            s = f"%{search}%"
            query = query.where((User.UserName.ilike(s)) | (User.mobile_no.ilike(s)))
        if branch_id is not None:
            query = query.where(User.BranchId == branch_id)
        if role_id is not None:
            query = query.where(User.UserRoleId == role_id)
        if is_active is True:
            query = query.where((User.isdeleted == None) | (User.isdeleted != "1"))  # noqa: E711
        elif is_active is False:
            query = query.where(User.isdeleted == "1")

        result = await self.session.execute(query)
        return result.scalar() or 0
