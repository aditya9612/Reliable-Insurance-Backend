from typing import Optional, Sequence
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.transaction_app import TransactionAppNew
from app.repositories.base import BaseRepository


class TransactionAppRepository(BaseRepository[TransactionAppNew]):
    """
    Data-access repository for Mobile / Proposal Intake Staging entity (tbl_transactionappnew).
    Pure database access.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(TransactionAppNew, session)

    async def get_by_user_id(self, user_id: int) -> Sequence[TransactionAppNew]:
        """Lookup intake proposals created by a specific UserId."""
        query = select(TransactionAppNew).where(TransactionAppNew.UserId == user_id)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_by_contact_no(self, contact_no: str) -> Sequence[TransactionAppNew]:
        """Lookup intake proposals by customer ContactNo."""
        query = select(TransactionAppNew).where(
            (TransactionAppNew.ContactNo == contact_no) | (TransactionAppNew.ContactNo2 == contact_no)
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_by_lead_no(self, lead_no: str) -> Optional[TransactionAppNew]:
        """Lookup intake proposal by LeadNo."""
        query = select(TransactionAppNew).where(TransactionAppNew.LeadNo == lead_no)
        result = await self.session.execute(query)
        return result.scalars().first()

    async def get_by_cash_status(self, cash_status: str) -> Sequence[TransactionAppNew]:
        """Lookup intake proposals by CashStatus."""
        query = select(TransactionAppNew).where(TransactionAppNew.CashStatus == cash_status)
        result = await self.session.execute(query)
        return result.scalars().all()
