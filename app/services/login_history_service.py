"""
Service for persistent login history, session tracking, and account unlocking.
"""
from typing import Optional, Sequence, Tuple
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from app.models.user import LoginHistory, User
from app.repositories.login_history import LoginHistoryRepository
from app.repositories.user import UserRepository
from app.schemas.login_history import AccountUnlockResponse


class LoginHistoryService:
    """
    Domain service for tbl_loginhistory session audit and account unlock operations.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.history_repo = LoginHistoryRepository(session)
        self.user_repo = UserRepository(session)

    async def record_login(
        self,
        user_id: Optional[int],
        username: Optional[str],
        ip_address: Optional[str] = None,
        success: bool = True,
        remark: Optional[str] = None,
    ) -> LoginHistory:
        """Records a successful or failed login attempt."""
        action = "LOGIN" if success else "FAILED_LOGIN"
        fun = "User Logged In" if success else "Login Failed"
        entry = await self.history_repo.create_log(
            user_id=user_id,
            username=username,
            action=action,
            fun_perform=fun,
            ip_address=ip_address,
            remark=remark or ("Success" if success else "Failed"),
        )
        await self.session.commit()
        return entry

    async def record_logout(
        self,
        user_id: int,
        username: Optional[str],
        ip_address: Optional[str] = None,
    ) -> LoginHistory:
        """Records a user logout event."""
        entry = await self.history_repo.create_log(
            user_id=user_id,
            username=username,
            action="LOGOUT",
            fun_perform="User Logged Out",
            ip_address=ip_address,
            remark="User Initiated Logout",
        )
        await self.session.commit()
        return entry

    async def list_history(
        self,
        user_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        action: Optional[str] = None,
        offset: int = 0,
        limit: int = 50,
    ) -> Tuple[Sequence[LoginHistory], int]:
        """Fetch paginated audit history with total count."""
        items = await self.history_repo.list_history(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            action=action,
            offset=offset,
            limit=limit,
        )
        total = await self.history_repo.count_history(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            action=action,
        )
        return items, total

    async def unlock_account(self, target_user_id: int, admin_user: User) -> AccountUnlockResponse:
        """Unlocks a locked/disabled user account and logs audit entry."""
        user = await self.user_repo.get_by_id(target_user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with ID {target_user_id} not found",
            )

        # Unlock user account
        user.isdeleted = "0"
        user.UpdateDate = datetime.utcnow()
        user.UpdateUser = admin_user.UserName

        await self.history_repo.create_log(
            user_id=user.UserId,
            username=user.UserName,
            action="ACCOUNT_UNLOCKED",
            fun_perform=f"Account unlocked by admin {admin_user.UserName}",
            ip_address=None,
            remark=f"Unlocked by {admin_user.UserName}",
        )
        await self.session.commit()

        return AccountUnlockResponse(
            user_id=user.UserId,
            username=user.UserName or "",
            unlocked=True,
            message=f"User account {user.UserName} successfully unlocked",
        )
