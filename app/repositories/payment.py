from typing import Optional, Sequence
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.payment import TransactionPayment
from app.repositories.base import BaseRepository


class PaymentRepository(BaseRepository[TransactionPayment]):
    """
    Data-access repository for Payment Instrument Tracking entity (tbl_transactionpayment).
    Pure database access.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(TransactionPayment, session)

    async def get_by_transaction_id(self, trans_id: int) -> Sequence[TransactionPayment]:
        """Lookup payment records linked to TransanctionId."""
        query = select(TransactionPayment).where(TransactionPayment.TransanctionId == trans_id)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_by_doc_no(self, doc_no: str) -> Sequence[TransactionPayment]:
        """Lookup payment records matching document / instrument number docno."""
        query = select(TransactionPayment).where(TransactionPayment.docno == doc_no)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_by_branch_id(self, branch_id: int) -> Sequence[TransactionPayment]:
        """Lookup payment records for a given BranchId."""
        query = select(TransactionPayment).where(TransactionPayment.BranchId == branch_id)
        result = await self.session.execute(query)
        return result.scalars().all()
