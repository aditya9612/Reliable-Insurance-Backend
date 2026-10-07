from typing import Optional, Sequence
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.account import Account
from app.repositories.base import BaseRepository


class AccountRepository(BaseRepository[Account]):
    """
    Data-access repository for Double-Entry Financial Ledger Account Entry entity (tbl_account).
    Pure database access.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Account, session)

    async def get_by_transaction_id(self, transaction_id: int) -> Sequence[Account]:
        """Lookup ledger journal entries associated with TransactionId."""
        query = select(Account).where(Account.TransactionId == transaction_id)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_by_ledger_id(self, ledger_m_id: int) -> Sequence[Account]:
        """Lookup journal lines posted to specific LedgerMId."""
        query = select(Account).where(Account.LedgerMId == ledger_m_id)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_by_doc_no(self, doc_no: int) -> Sequence[Account]:
        """Lookup journal lines matching voucher Doc_No."""
        query = select(Account).where(Account.Doc_No == doc_no)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_by_branch_id(self, branch_id: int) -> Sequence[Account]:
        """Lookup journal lines for a given BranchId."""
        query = select(Account).where(Account.BranchId == branch_id)
        result = await self.session.execute(query)
        return result.scalars().all()
