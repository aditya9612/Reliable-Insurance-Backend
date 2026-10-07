from typing import Optional, Sequence
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.ledger import LedgerMaster
from app.repositories.base import BaseRepository


class LedgerRepository(BaseRepository[LedgerMaster]):
    """
    Data-access repository for Chart of Accounts / Master Ledger entity (tbl_ledgermaster).
    Pure database access.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(LedgerMaster, session)

    async def get_by_name(self, ledger_name: str) -> Optional[LedgerMaster]:
        """Lookup ledger master account by LedgerName."""
        query = select(LedgerMaster).where(LedgerMaster.LedgerName == ledger_name)
        result = await self.session.execute(query)
        return result.scalars().first()

    async def get_by_type(self, type_id: int) -> Sequence[LedgerMaster]:
        """Lookup ledger accounts by LedgerTypeId."""
        query = select(LedgerMaster).where(LedgerMaster.LedgerTypeId == type_id)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_by_group(self, group_id: int) -> Sequence[LedgerMaster]:
        """Lookup ledger accounts by LedgerGroupId."""
        query = select(LedgerMaster).where(LedgerMaster.LedgerGroupId == group_id)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_by_branch_id(self, branch_id: int) -> Sequence[LedgerMaster]:
        """Lookup ledger accounts for a specific BranchId."""
        query = select(LedgerMaster).where(LedgerMaster.BranchId == branch_id)
        result = await self.session.execute(query)
        return result.scalars().all()
