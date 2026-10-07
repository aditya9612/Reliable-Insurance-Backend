from typing import Optional, Sequence
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.commission import FranchiseCommission, AgentCommissionPayment, CutNPayCommPayable
from app.repositories.base import BaseRepository


class FranchiseCommissionRepository(BaseRepository[FranchiseCommission]):
    """
    Data-access repository for Franchise & Partner Commission Ledger (tbl_franchisecommission).
    Pure database access.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(FranchiseCommission, session)

    async def get_by_transaction_id(self, trans_id: int) -> Sequence[FranchiseCommission]:
        """Lookup franchise commission entries by TransanctionId."""
        query = select(FranchiseCommission).where(FranchiseCommission.TransanctionId == trans_id)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_by_franchise_id(self, franchise_id: int) -> Sequence[FranchiseCommission]:
        """Lookup commission records for a specific FranchiseId."""
        query = select(FranchiseCommission).where(FranchiseCommission.FranchiseId == franchise_id)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_by_agent_id(self, agent_id: int) -> Sequence[FranchiseCommission]:
        """Lookup franchise commission entries for a specific AgentId."""
        query = select(FranchiseCommission).where(FranchiseCommission.AgentId == agent_id)
        result = await self.session.execute(query)
        return result.scalars().all()


class AgentCommissionRepository(BaseRepository[AgentCommissionPayment]):
    """
    Data-access repository for Agent Commission Payment Settlement (tbl_agentcommissionpayment).
    Pure database access.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(AgentCommissionPayment, session)

    async def get_by_transaction_id(self, trans_id: int) -> Sequence[AgentCommissionPayment]:
        """Lookup agent commission payment rows by TransanctionId."""
        query = select(AgentCommissionPayment).where(AgentCommissionPayment.TransanctionId == trans_id)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_by_agent_name(self, agent_name: str) -> Sequence[AgentCommissionPayment]:
        """Lookup agent commission records by AgentName."""
        query = select(AgentCommissionPayment).where(AgentCommissionPayment.AgentName == agent_name)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_by_branch_name(self, branch_name: str) -> Sequence[AgentCommissionPayment]:
        """Lookup agent commission records by BranchName."""
        query = select(AgentCommissionPayment).where(AgentCommissionPayment.BranchName == branch_name)
        result = await self.session.execute(query)
        return result.scalars().all()


class CutNPayCommissionRepository(BaseRepository[CutNPayCommPayable]):
    """
    Data-access repository for Cut & Pay Commission Deduction Ledger (tbl_cutnpaycommpayable).
    Pure database access.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(CutNPayCommPayable, session)

    async def get_by_transaction_id(self, trans_id: int) -> Sequence[CutNPayCommPayable]:
        """Lookup cut-and-pay deductions by TransactionId."""
        query = select(CutNPayCommPayable).where(CutNPayCommPayable.TransactionId == trans_id)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_by_policy_no(self, policy_no: str) -> Sequence[CutNPayCommPayable]:
        """Lookup cut-and-pay deductions by PolicyNo."""
        query = select(CutNPayCommPayable).where(CutNPayCommPayable.PolicyNo == policy_no)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_by_agent_id(self, agent_id: int) -> Sequence[CutNPayCommPayable]:
        """Lookup cut-and-pay deductions by AgentId."""
        query = select(CutNPayCommPayable).where(CutNPayCommPayable.AgentId == agent_id)
        result = await self.session.execute(query)
        return result.scalars().all()
