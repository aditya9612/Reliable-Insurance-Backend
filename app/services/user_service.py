"""
Service for User Management, Password Lifecycle, Status Toggle, and Role Directory.
"""
from typing import Optional, Sequence, Tuple, List
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.core.rbac import GLOBAL_ADMIN_ROLES
from app.core.security import get_password_hash, verify_password
from app.models.user import User, UserRole
from app.repositories.user import UserRepository
from app.repositories.role import RoleRepository
from app.schemas.user import (
    UserCreate,
    UserUpdate,
    UserPasswordResetRequest,
    UserPasswordChangeRequest,
    UserStatusUpdateRequest,
    UsernameCheckResponse,
)


class UserService:
    """
    Domain service for tbl_user CRUD, password management, and account lifecycle.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.user_repo = UserRepository(session)
        self.role_repo = RoleRepository(session)

    def _is_global_admin(self, user: User) -> bool:
        role_name = getattr(user, "role_name", None) or ""
        return role_name.strip().upper() in GLOBAL_ADMIN_ROLES

    async def list_users(
        self,
        current_user: User,
        search: Optional[str] = None,
        branch_id: Optional[int] = None,
        role_id: Optional[int] = None,
        is_active: Optional[bool] = None,
        offset: int = 0,
        limit: int = 50,
    ) -> Tuple[Sequence[User], int]:
        """
        List users with branch scoping and role enforcement.
        Global admins can see all branches; branch users are constrained to their own branch.
        """
        effective_branch = branch_id
        if not self._is_global_admin(current_user):
            effective_branch = current_user.BranchId

        items = await self.user_repo.list_users(
            search=search,
            branch_id=effective_branch,
            role_id=role_id,
            is_active=is_active,
            offset=offset,
            limit=limit,
        )
        total = await self.user_repo.count_users(
            search=search,
            branch_id=effective_branch,
            role_id=role_id,
            is_active=is_active,
        )
        return items, total

    async def get_user_by_id(self, user_id: int, current_user: User) -> User:
        """Fetch user by ID with branch isolation check."""
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {user_id} not found",
            )

        if not self._is_global_admin(current_user):
            if user.BranchId != current_user.BranchId and user.UserId != current_user.UserId:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Cross-branch user access forbidden",
                )

        return user

    async def create_user(self, user_in: UserCreate, current_user: User) -> User:
        """Create a new user with password hashing and branch validation."""
        existing = await self.user_repo.get_by_username(user_in.UserName)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken",
            )

        effective_branch = user_in.BranchId
        if not self._is_global_admin(current_user):
            effective_branch = current_user.BranchId

        hashed_pw = get_password_hash(user_in.UserPassword)
        new_user = User(
            UserName=user_in.UserName,
            UserPassword=hashed_pw,
            UserRoleId=user_in.UserRoleId,
            BranchId=effective_branch,
            isappuser=user_in.isappuser or "0",
            isdeleted="0",
            CreateDate=datetime.utcnow(),
            CreateUser=current_user.UserName,
            partner_user_id=user_in.partner_user_id,
            mobile_no=user_in.mobile_no,
        )
        self.session.add(new_user)
        await self.session.commit()
        await self.session.refresh(new_user)
        return new_user

    async def update_user(self, user_id: int, user_in: UserUpdate, current_user: User) -> User:
        """Update existing user record."""
        user = await self.get_user_by_id(user_id, current_user)

        if user_in.UserRoleId is not None:
            user.UserRoleId = user_in.UserRoleId
        if user_in.BranchId is not None and self._is_global_admin(current_user):
            user.BranchId = user_in.BranchId
        if user_in.isappuser is not None:
            user.isappuser = user_in.isappuser
        if user_in.partner_user_id is not None:
            user.partner_user_id = user_in.partner_user_id
        if user_in.mobile_no is not None:
            user.mobile_no = user_in.mobile_no

        user.UpdateDate = datetime.utcnow()
        user.UpdateUser = current_user.UserName

        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def reset_password(self, user_id: int, new_password: str, current_user: User) -> User:
        """Reset password by administrator."""
        user = await self.get_user_by_id(user_id, current_user)

        hashed_pw = get_password_hash(new_password)
        await self.user_repo.update_password(user, hashed_pw)
        user.UpdateUser = current_user.UserName
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def change_own_password(
        self, user_id: int, old_password: str, new_password: str, current_user: User
    ) -> User:
        """User self-service password update with verification of old password."""
        if current_user.UserId != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot change another user's password using self-service endpoint",
            )

        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        is_valid, _ = verify_password(old_password, user.UserPassword or "")
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Incorrect current password",
            )

        hashed_pw = get_password_hash(new_password)
        await self.user_repo.update_password(user, hashed_pw)
        user.UpdateUser = current_user.UserName
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def update_status(
        self, user_id: int, status_in: UserStatusUpdateRequest, current_user: User
    ) -> User:
        """Toggle active/inactive status ('0' active, '1' locked/deleted)."""
        if not self._is_global_admin(current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Administrative privilege required to update user account status",
            )

        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {user_id} not found",
            )

        new_status = "0"
        if status_in.isdeleted is not None:
            new_status = str(status_in.isdeleted).strip()
        elif status_in.is_active is not None:
            new_status = "0" if status_in.is_active else "1"

        await self.user_repo.update_status(user, new_status)
        user.UpdateUser = current_user.UserName
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def check_username(self, username: str) -> UsernameCheckResponse:
        """Check availability of a username."""
        existing = await self.user_repo.get_by_username(username.strip())
        return UsernameCheckResponse(
            username=username,
            is_available=existing is None,
        )

    async def list_roles(self) -> Sequence[UserRole]:
        """Fetch all active user roles."""
        return await self.role_repo.list_active()
