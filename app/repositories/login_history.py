"""
Repository for tbl_loginhistory (Persistent Login & Session Audit Log).
"""
from typing import Optional, Sequence
from datetime import datetime
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import LoginHistory
from app.repositories.base import BaseRepository


class LoginHistoryRepository(BaseRepository[LoginHistory]):
    """
    Data-access repository for LoginHistory entity (tbl_loginhistory).
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(LoginHistory, session)

    async def create_log(
        self,
        user_id: Optional[int],
        username: Optional[str],
        action: str,
        fun_perform: Optional[str] = None,
        ip_address: Optional[str] = None,
        remark: Optional[str] = None,
    ) -> LoginHistory:
        """Create a new login/logout/failed attempt audit entry."""
        entry = LoginHistory(
            UserId=user_id,
            UserName=username,
            LogInOrLogOut=action,
            funPerform=fun_perform or action,
            IPAddress=ip_address,
            CreateDate=datetime.utcnow(),
            Remark=remark,
        )
        self.session.add(entry)
        await self.session.flush()
        return entry

    async def list_history(
        self,
        user_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        action: Optional[str] = None,
        offset: int = 0,
        limit: int = 50,
    ) -> Sequence[LoginHistory]:
        """List login history entries matching criteria."""
        query = select(LoginHistory)
        if user_id is not None:
            query = query.where(LoginHistory.UserId == user_id)
        if start_date is not None:
            query = query.where(LoginHistory.CreateDate >= start_date)
        if end_date is not None:
            query = query.where(LoginHistory.CreateDate <= end_date)
        if action:
            query = query.where(LoginHistory.LogInOrLogOut.ilike(f"%{action}%"))

        query = query.order_by(LoginHistory.LoginHistoryId.desc()).offset(offset).limit(limit)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def count_history(
        self,
        user_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        action: Optional[str] = None,
    ) -> int:
        """Count login history entries matching criteria."""
        query = select(func.count(LoginHistory.LoginHistoryId))
        if user_id is not None:
            query = query.where(LoginHistory.UserId == user_id)
        if start_date is not None:
            query = query.where(LoginHistory.CreateDate >= start_date)
        if end_date is not None:
            query = query.where(LoginHistory.CreateDate <= end_date)
        if action:
            query = query.where(LoginHistory.LogInOrLogOut.ilike(f"%{action}%"))

        result = await self.session.execute(query)
        return result.scalar() or 0
