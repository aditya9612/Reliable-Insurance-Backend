from datetime import datetime
from typing import List, Optional, Tuple
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.claims_endorsement import Claim, ClaimDocument, PolicyEndorsement
from app.models.commission import AgentCommissionPayment, FranchiseCommission
from app.models.customer import Customer
from app.models.transaction import Transaction
from app.models.vehicle import VehicleDetails


class ClaimsEndorsementRepository:
    """
    Async SQLAlchemy Repository for Phase 10 Claims, Claim Documents, and Policy Endorsements.
    Enforces row-level pessimistic locking (SELECT ... FOR UPDATE) for atomic mutations.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # Policy / Customer / Vehicle Lookup & Locking
    # ------------------------------------------------------------------
    async def get_policy_for_update(self, transaction_id: int) -> Optional[Transaction]:
        stmt = (
            select(Transaction)
            .where(
                Transaction.TransanctionId == transaction_id,
                Transaction.isdeleted == "0",
            )
            .with_for_update()
        )
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def get_policy_readonly(self, transaction_id: int) -> Optional[Transaction]:
        stmt = select(Transaction).where(
            Transaction.TransanctionId == transaction_id,
            Transaction.isdeleted == "0",
        )
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def get_customer_for_update(self, customer_id: int) -> Optional[Customer]:
        stmt = (
            select(Customer)
            .where(Customer.CustomerId == customer_id)
            .with_for_update()
        )
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def get_vehicle_for_update(self, cust_veh_id: int) -> Optional[VehicleDetails]:
        stmt = (
            select(VehicleDetails)
            .where(VehicleDetails.CustVehId == cust_veh_id)
            .with_for_update()
        )
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def get_agent_commission_rows_for_update(
        self, transaction_id: int
    ) -> List[AgentCommissionPayment]:
        stmt = (
            select(AgentCommissionPayment)
            .where(
                AgentCommissionPayment.TransanctionId == transaction_id,
                AgentCommissionPayment.isdeleted == "0",
            )
            .order_by(AgentCommissionPayment.AgentCommId.asc())
            .with_for_update()
        )
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def get_franchise_commission_rows_for_update(
        self, transaction_id: int
    ) -> List[FranchiseCommission]:
        stmt = (
            select(FranchiseCommission)
            .where(
                FranchiseCommission.TransanctionId == transaction_id,
                FranchiseCommission.isdeleted == 0,
            )
            .order_by(FranchiseCommission.FranchiseCommId.asc())
            .with_for_update()
        )
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    # ------------------------------------------------------------------
    # Claims Repository Operations
    # ------------------------------------------------------------------
    async def get_claim_by_idempotency_key(self, idempotency_key: str) -> Optional[Claim]:
        stmt = select(Claim).where(
            Claim.IdempotencyKey == idempotency_key,
            Claim.isdeleted == "0",
        )
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def get_duplicate_active_claim(
        self,
        transaction_id: int,
        loss_date: datetime,
        claim_type: str,
    ) -> Optional[Claim]:
        stmt = select(Claim).where(
            Claim.TransanctionId == transaction_id,
            Claim.LossDate == loss_date,
            Claim.ClaimType == claim_type,
            Claim.isdeleted == "0",
            Claim.ClaimStatus.notin_(["CANCELLED", "REJECTED"]),
        )
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def get_claim_for_update(self, claim_id: int) -> Optional[Claim]:
        stmt = (
            select(Claim)
            .where(
                Claim.ClaimId == claim_id,
                Claim.isdeleted == "0",
            )
            .with_for_update()
        )
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def get_claim_readonly(self, claim_id: int) -> Optional[Claim]:
        stmt = select(Claim).where(
            Claim.ClaimId == claim_id,
            Claim.isdeleted == "0",
        )
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def list_claims(
        self,
        *,
        transaction_id: Optional[int] = None,
        policy_no: Optional[str] = None,
        claim_status: Optional[str] = None,
        claim_type: Optional[str] = None,
        branch_id: Optional[int] = None,
        agent_id: Optional[int] = None,
        franchise_id: Optional[int] = None,
        sales_ex_id: Optional[int] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[Claim], int]:
        filters = [Claim.isdeleted == "0"]
        if transaction_id is not None:
            filters.append(Claim.TransanctionId == transaction_id)
        if policy_no is not None:
            filters.append(Claim.PolicyNo == policy_no)
        if claim_status is not None:
            filters.append(Claim.ClaimStatus == claim_status)
        if claim_type is not None:
            filters.append(Claim.ClaimType == claim_type)
        if branch_id is not None:
            filters.append(Claim.BranchId == branch_id)
        if agent_id is not None:
            filters.append(Claim.AgentId == agent_id)
        if franchise_id is not None:
            filters.append(Claim.FranchiseId == franchise_id)
        if sales_ex_id is not None:
            filters.append(Claim.SalesExId == sales_ex_id)

        count_stmt = select(func.count(Claim.ClaimId)).where(*filters)
        total = (await self.db.execute(count_stmt)).scalar_one() or 0

        stmt = (
            select(Claim)
            .where(*filters)
            .order_by(Claim.ClaimId.desc())
            .limit(limit)
            .offset(offset)
        )
        rows = list((await self.db.execute(stmt)).scalars().all())
        return rows, int(total)

    async def list_claim_documents(self, claim_id: int) -> List[ClaimDocument]:
        stmt = (
            select(ClaimDocument)
            .where(
                ClaimDocument.ClaimId == claim_id,
                ClaimDocument.isdeleted == "0",
            )
            .order_by(ClaimDocument.ClaimDocId.asc())
        )
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    # ------------------------------------------------------------------
    # Endorsements Repository Operations
    # ------------------------------------------------------------------
    async def get_endorsement_by_idempotency_key(
        self, idempotency_key: str
    ) -> Optional[PolicyEndorsement]:
        stmt = select(PolicyEndorsement).where(
            PolicyEndorsement.IdempotencyKey == idempotency_key,
            PolicyEndorsement.isdeleted == "0",
        )
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def get_pending_conflicting_endorsement(
        self, transaction_id: int, exclude_endorsement_id: Optional[int] = None
    ) -> Optional[PolicyEndorsement]:
        filters = [
            PolicyEndorsement.TransanctionId == transaction_id,
            PolicyEndorsement.isdeleted == "0",
            PolicyEndorsement.EndorsementStatus.in_(["SUBMITTED", "APPROVED"]),
        ]
        if exclude_endorsement_id is not None:
            filters.append(PolicyEndorsement.EndorsementId != exclude_endorsement_id)
        stmt = select(PolicyEndorsement).where(*filters).limit(1)
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def get_endorsement_for_update(
        self, endorsement_id: int
    ) -> Optional[PolicyEndorsement]:
        stmt = (
            select(PolicyEndorsement)
            .where(
                PolicyEndorsement.EndorsementId == endorsement_id,
                PolicyEndorsement.isdeleted == "0",
            )
            .with_for_update()
        )
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def get_endorsement_readonly(
        self, endorsement_id: int
    ) -> Optional[PolicyEndorsement]:
        stmt = select(PolicyEndorsement).where(
            PolicyEndorsement.EndorsementId == endorsement_id,
            PolicyEndorsement.isdeleted == "0",
        )
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    async def list_endorsements(
        self,
        *,
        transaction_id: Optional[int] = None,
        endorsement_status: Optional[str] = None,
        endorsement_type: Optional[str] = None,
        refund_status: Optional[str] = None,
        branch_id: Optional[int] = None,
        agent_id: Optional[int] = None,
        franchise_id: Optional[int] = None,
        sales_ex_id: Optional[int] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[PolicyEndorsement], int]:
        filters = [PolicyEndorsement.isdeleted == "0"]
        if transaction_id is not None:
            filters.append(PolicyEndorsement.TransanctionId == transaction_id)
        if endorsement_status is not None:
            filters.append(PolicyEndorsement.EndorsementStatus == endorsement_status)
        if endorsement_type is not None:
            filters.append(PolicyEndorsement.EndorsementType == endorsement_type)
        if refund_status is not None:
            filters.append(PolicyEndorsement.RefundStatus == refund_status)
        if branch_id is not None:
            filters.append(PolicyEndorsement.BranchId == branch_id)
        if agent_id is not None:
            filters.append(PolicyEndorsement.AgentId == agent_id)
        if franchise_id is not None:
            filters.append(PolicyEndorsement.FranchiseId == franchise_id)
        if sales_ex_id is not None:
            filters.append(PolicyEndorsement.SalesExId == sales_ex_id)

        count_stmt = select(func.count(PolicyEndorsement.EndorsementId)).where(*filters)
        total = (await self.db.execute(count_stmt)).scalar_one() or 0

        stmt = (
            select(PolicyEndorsement)
            .where(*filters)
            .order_by(PolicyEndorsement.EndorsementId.desc())
            .limit(limit)
            .offset(offset)
        )
        rows = list((await self.db.execute(stmt)).scalars().all())
        return rows, int(total)
