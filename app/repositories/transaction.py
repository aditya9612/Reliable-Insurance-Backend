from typing import Optional, Sequence
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.transaction import Transaction
from app.repositories.base import BaseRepository


class TransactionRepository(BaseRepository[Transaction]):
    """
    Data-access repository for Transaction entity (tbl_transaction).
    No business logic, calculations, or status transition rules.
    Pure database access.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Transaction, session)

    async def get_by_policy_no(self, policy_no: str) -> Optional[Transaction]:
        """Lookup transaction by PolicyNo."""
        query = select(Transaction).where(Transaction.PolicyNo == policy_no)
        result = await self.session.execute(query)
        return result.scalars().first()

    async def get_by_inward_no(self, inward_no: str) -> Optional[Transaction]:
        """Lookup transaction by InwardNo."""
        query = select(Transaction).where(Transaction.InwardNo == inward_no)
        result = await self.session.execute(query)
        return result.scalars().first()

    async def get_by_customer_id(self, customer_id: int) -> Sequence[Transaction]:
        """Lookup transactions for a given CustomerId."""
        query = select(Transaction).where(Transaction.CustomerId == customer_id)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_by_vehicle_id(self, cust_veh_id: int) -> Sequence[Transaction]:
        """Lookup transactions for a given CustVehId."""
        query = select(Transaction).where(Transaction.CustVehId == cust_veh_id)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_by_status(self, status: str) -> Sequence[Transaction]:
        """Lookup transactions matching legacy TStatus field."""
        query = select(Transaction).where(Transaction.TStatus == status)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_by_agent_id(self, agent_id: int) -> Sequence[Transaction]:
        """Lookup transactions for a given AgentId."""
        query = select(Transaction).where(Transaction.AgentId == agent_id)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_by_branch_id(self, branch_id: int) -> Sequence[Transaction]:
        """Lookup transactions for a given BranchId."""
        query = select(Transaction).where(Transaction.BranchId == branch_id)
        result = await self.session.execute(query)
        return result.scalars().all()
