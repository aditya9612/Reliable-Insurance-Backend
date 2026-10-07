"""
Repository Layer for Phase 7 Policy Booking & Transaction Engine.
Encapsulates all SQLAlchemy 2.0 AsyncSession queries and writes for:
- tbl_transaction (Transaction)
- tbl_transactionappnew (TransactionAppNew)
- tbl_transactionpayment (TransactionPayment)
- tbl_franchisecommission (FranchiseCommission)
- tbl_agentcommissionpayment (AgentCommissionPayment)
- tbl_cutnpaycommpayable (CutNPayCommPayable)
- tbl_account (Account)
- tbl_ledgermaster (LedgerMaster)
"""
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional, Sequence, Tuple
from sqlalchemy import desc, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account
from app.models.commission import (
    AgentCommissionPayment,
    CutNPayCommPayable,
    FranchiseCommission,
)
from app.models.customer import Customer
from app.models.ledger import LedgerMaster
from app.models.payment import TransactionPayment
from app.models.transaction import Transaction
from app.models.transaction_app import TransactionAppNew
from app.models.vehicle import VehicleDetails


def resolve_financial_year(target_date: Optional[date] = None) -> Tuple[str, str]:
    """
    Returns (financial_year_full, fy_short_code) for a given date.
    Example: 2026-10-06 -> ("2026-2027", "2627")
    """
    d = target_date or date.today()
    if d.month >= 4:
        start_yr = d.year
        end_yr = d.year + 1
    else:
        start_yr = d.year - 1
        end_yr = d.year
    full_fy = f"{start_yr}-{end_yr}"
    short_fy = f"{str(start_yr)[-2:]}{str(end_yr)[-2:]}"
    return full_fy, short_fy


class PolicyBookingRepository:
    """Data-access layer for Phase 7 Policy Booking & Transaction Engine."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # -----------------------------------------------------------------------
    # 1. Customer & Vehicle Verification
    # -----------------------------------------------------------------------

    async def get_active_customer(self, customer_id: int) -> Optional[Customer]:
        stmt = select(Customer).where(
            Customer.CustomerId == customer_id,
            or_(Customer.isdeleted == "0", Customer.isdeleted.is_(None), Customer.isdeleted == ""),
        )
        res = await self.session.execute(stmt)
        return res.scalars().first()

    async def get_active_vehicle(self, cust_veh_id: int) -> Optional[VehicleDetails]:
        stmt = select(VehicleDetails).where(
            VehicleDetails.CustVehId == cust_veh_id,
            or_(
                VehicleDetails.isdeleted == "0",
                VehicleDetails.isdeleted.is_(None),
                VehicleDetails.isdeleted == "",
            ),
        )
        res = await self.session.execute(stmt)
        return res.scalars().first()

    # -----------------------------------------------------------------------
    # 2. Concurrency-Safe Inward Number Allocation (sp_generateInwardNo parity)
    # -----------------------------------------------------------------------

    async def allocate_inward_no(
        self,
        branch_id: int,
        target_date: Optional[date] = None,
    ) -> Tuple[str, str]:
        """
        Generates a concurrency-safe sequential InwardNo in format:
            INW-{branch_id:02d}-{fy_short}-{seq:06d}
        Uses InnoDB locking read (FOR UPDATE) so concurrent transactions read the
        latest committed sequence and never allocate duplicate inward numbers.
        Returns (inward_no, financial_year).
        """
        eff_branch_id = branch_id if branch_id and branch_id > 0 else 1
        full_fy, short_fy = resolve_financial_year(target_date)
        prefix = f"INW-{eff_branch_id:02d}-{short_fy}-"

        # Lock matching rows in tbl_transaction using FOR UPDATE (locking read bypasses MVCC snapshot)
        res = await self.session.execute(
            text(
                "SELECT InwardNo FROM tbl_transaction "
                "WHERE BranchId = :bid AND InwardNo LIKE :prefix "
                "ORDER BY TransanctionId DESC LIMIT 25 FOR UPDATE"
            ),
            {"bid": eff_branch_id, "prefix": f"{prefix}%"},
        )
        rows = res.fetchall()
        max_seq = 0
        for (inw_val,) in rows:
            if inw_val and str(inw_val).startswith(prefix):
                suffix = str(inw_val)[len(prefix):]
                if suffix.isdigit():
                    seq_num = int(suffix)
                    if seq_num > max_seq:
                        max_seq = seq_num

        next_seq = max_seq + 1
        candidate = f"{prefix}{next_seq:06d}"

        # Verify no collision exists across the entire table
        while True:
            chk = await self.session.execute(
                text(
                    "SELECT 1 FROM tbl_transaction WHERE InwardNo = :cand LIMIT 1 FOR UPDATE"
                ),
                {"cand": candidate},
            )
            if chk.first() is None:
                break
            next_seq += 1
            candidate = f"{prefix}{next_seq:06d}"

        return candidate, full_fy

    # -----------------------------------------------------------------------
    # 3. Idempotency & Duplicate Booking Guards (Locking Reads)
    # -----------------------------------------------------------------------

    async def get_active_by_policy_no(
        self,
        policy_no: str,
        insurance_company_id: int,
    ) -> Optional[Transaction]:
        if not policy_no or policy_no.strip().upper() in {"", "PENDING", "TBA", "NA"}:
            return None
        stmt = (
            select(Transaction)
            .where(
                Transaction.PolicyNo == policy_no.strip(),
                Transaction.InsuranceCompanyId == insurance_company_id,
                or_(Transaction.isdeleted == "0", Transaction.isdeleted.is_(None)),
            )
            .with_for_update()
        )
        res = await self.session.execute(stmt)
        return res.scalars().first()

    async def get_active_by_quotation_code(
        self,
        quotation_code: str,
    ) -> Optional[Transaction]:
        if not quotation_code or not quotation_code.strip():
            return None
        stmt = (
            select(Transaction)
            .where(
                Transaction.QuatationCode == quotation_code.strip(),
                or_(Transaction.isdeleted == "0", Transaction.isdeleted.is_(None)),
            )
            .with_for_update()
        )
        res = await self.session.execute(stmt)
        return res.scalars().first()

    async def get_active_by_proposal_id(
        self,
        proposal_trans_id: int,
    ) -> Optional[Transaction]:
        if not proposal_trans_id or proposal_trans_id <= 0:
            return None
        stmt = (
            select(Transaction)
            .where(
                Transaction.TransId == proposal_trans_id,
                or_(Transaction.isdeleted == "0", Transaction.isdeleted.is_(None)),
            )
            .with_for_update()
        )
        res = await self.session.execute(stmt)
        return res.scalars().first()

    async def get_active_by_idempotency_key(
        self,
        idempotency_key: str,
    ) -> Optional[Transaction]:
        if not idempotency_key or not idempotency_key.strip():
            return None
        tag = f"IDEMP:{idempotency_key.strip()}"
        stmt = (
            select(Transaction)
            .where(
                Transaction.PolicyRequest == tag
                if hasattr(Transaction, "PolicyRequest")
                else Transaction.PaymentRequest == tag,
                or_(Transaction.isdeleted == "0", Transaction.isdeleted.is_(None)),
            )
            .with_for_update()
        )
        res = await self.session.execute(stmt)
        return res.scalars().first()

    # -----------------------------------------------------------------------
    # 4. Transaction Persistence & Retrieval (tbl_transaction)
    # -----------------------------------------------------------------------

    async def create_transaction(self, tx: Transaction) -> Transaction:
        self.session.add(tx)
        await self.session.flush()
        return tx

    async def get_transaction_by_id(
        self,
        transaction_id: int,
        include_deleted: bool = False,
    ) -> Optional[Transaction]:
        stmt = select(Transaction).where(Transaction.TransanctionId == transaction_id)
        if not include_deleted:
            stmt = stmt.where(
                or_(Transaction.isdeleted == "0", Transaction.isdeleted.is_(None))
            )
        res = await self.session.execute(stmt)
        return res.scalars().first()

    async def list_transactions(
        self,
        *,
        branch_id: Optional[int] = None,
        agent_id: Optional[int] = None,
        sales_ex_id: Optional[int] = None,
        franchise_code: Optional[str] = None,
        customer_id: Optional[int] = None,
        cust_veh_id: Optional[int] = None,
        policy_no: Optional[str] = None,
        inward_no: Optional[str] = None,
        quotation_code: Optional[str] = None,
        t_status: Optional[str] = None,
        include_deleted: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[int, Sequence[Transaction]]:
        conditions = []
        if not include_deleted:
            conditions.append(
                or_(Transaction.isdeleted == "0", Transaction.isdeleted.is_(None))
            )
        if branch_id is not None:
            conditions.append(Transaction.BranchId == branch_id)
        if agent_id is not None:
            conditions.append(Transaction.AgentId == agent_id)
        if sales_ex_id is not None:
            conditions.append(Transaction.SalesEx_id == sales_ex_id)
        if franchise_code is not None:
            conditions.append(Transaction.FranchiseCode == str(franchise_code))
        if customer_id is not None:
            conditions.append(Transaction.CustomerId == customer_id)
        if cust_veh_id is not None:
            conditions.append(Transaction.CustVehId == cust_veh_id)
        if policy_no:
            conditions.append(Transaction.PolicyNo == policy_no.strip())
        if inward_no:
            conditions.append(Transaction.InwardNo == inward_no.strip())
        if quotation_code:
            conditions.append(Transaction.QuatationCode == quotation_code.strip())
        if t_status:
            conditions.append(Transaction.TStatus == t_status.strip())

        count_stmt = select(func.count(Transaction.TransanctionId))
        if conditions:
            count_stmt = count_stmt.where(*conditions)
        total_res = await self.session.execute(count_stmt)
        total = int(total_res.scalar() or 0)

        data_stmt = select(Transaction)
        if conditions:
            data_stmt = data_stmt.where(*conditions)
        data_stmt = (
            data_stmt.order_by(desc(Transaction.TransanctionId))
            .limit(limit)
            .offset(offset)
        )
        rows_res = await self.session.execute(data_stmt)
        return total, rows_res.scalars().all()

    # -----------------------------------------------------------------------
    # 5. Payment Instruments (tbl_transactionpayment)
    # -----------------------------------------------------------------------

    async def create_payment(self, payment: TransactionPayment) -> TransactionPayment:
        self.session.add(payment)
        await self.session.flush()
        return payment

    async def get_payments_by_transaction_id(
        self,
        transaction_id: int,
        include_deleted: bool = False,
    ) -> Sequence[TransactionPayment]:
        stmt = select(TransactionPayment).where(
            TransactionPayment.TransanctionId == transaction_id
        )
        if not include_deleted:
            stmt = stmt.where(
                or_(
                    TransactionPayment.isdeleted == "0",
                    TransactionPayment.isdeleted.is_(None),
                )
            )
        stmt = stmt.order_by(TransactionPayment.PaymentId)
        res = await self.session.execute(stmt)
        return res.scalars().all()

    # -----------------------------------------------------------------------
    # 6. Commission Tables (tbl_franchisecommission, tbl_cutnpaycommpayable, tbl_agentcommissionpayment)
    # -----------------------------------------------------------------------

    async def create_franchise_commission(
        self,
        fc: FranchiseCommission,
    ) -> FranchiseCommission:
        self.session.add(fc)
        await self.session.flush()
        return fc

    async def get_franchise_commissions_by_tx(
        self,
        transaction_id: int,
        include_deleted: bool = False,
    ) -> Sequence[FranchiseCommission]:
        stmt = select(FranchiseCommission).where(
            FranchiseCommission.TransanctionId == transaction_id
        )
        if not include_deleted:
            stmt = stmt.where(
                or_(
                    FranchiseCommission.isdeleted == 0,
                    FranchiseCommission.isdeleted.is_(None),
                )
            )
        res = await self.session.execute(stmt)
        return res.scalars().all()

    async def create_cutnpay_payable(
        self,
        cnp: CutNPayCommPayable,
    ) -> CutNPayCommPayable:
        self.session.add(cnp)
        await self.session.flush()
        return cnp

    async def get_cutnpay_by_tx(
        self,
        transaction_id: int,
        include_deleted: bool = False,
    ) -> Sequence[CutNPayCommPayable]:
        stmt = select(CutNPayCommPayable).where(
            CutNPayCommPayable.TransactionId == transaction_id
        )
        if not include_deleted:
            stmt = stmt.where(
                or_(
                    CutNPayCommPayable.Isdeleted == 0,
                    CutNPayCommPayable.Isdeleted.is_(None),
                )
            )
        res = await self.session.execute(stmt)
        return res.scalars().all()

    async def create_agent_commission_payment(
        self,
        acp: AgentCommissionPayment,
    ) -> AgentCommissionPayment:
        self.session.add(acp)
        await self.session.flush()
        return acp

    async def get_agent_comm_payments_by_tx(
        self,
        transaction_id: int,
        include_deleted: bool = False,
    ) -> Sequence[AgentCommissionPayment]:
        stmt = select(AgentCommissionPayment).where(
            AgentCommissionPayment.TransanctionId == transaction_id
        )
        if not include_deleted:
            stmt = stmt.where(
                or_(
                    AgentCommissionPayment.isdeleted == "0",
                    AgentCommissionPayment.isdeleted.is_(None),
                )
            )
        res = await self.session.execute(stmt)
        return res.scalars().all()

    # -----------------------------------------------------------------------
    # 7. Double-Entry Accounting Ledger (tbl_account & tbl_ledgermaster)
    # -----------------------------------------------------------------------

    async def resolve_or_create_policy_ledger(
        self,
        branch_id: int,
        actor_user_id: int,
    ) -> int:
        """
        Resolves the active Policy Underwriting LedgerMId in tbl_ledgermaster for the branch,
        creating a default master row if none exists yet.
        """
        stmt = select(LedgerMaster).where(
            LedgerMaster.BranchId == branch_id,
            or_(LedgerMaster.isdeleted == "0", LedgerMaster.isdeleted.is_(None)),
        ).order_by(LedgerMaster.LedgerMId).limit(1)
        res = await self.session.execute(stmt)
        existing = res.scalars().first()
        if existing is not None:
            return existing.LedgerMId

        now = datetime.utcnow()
        ledger = LedgerMaster(
            LedgerTypeId=1,
            LedgerName="POLICY UNDERWRITING LEDGER",
            LedgerGroupId=1,
            ReferenceId=0,
            BranchId=branch_id,
            isdeleted="0",
            CreateUser=str(actor_user_id),
            CreateDate=now,
            UpdateUser=str(actor_user_id),
            UpdateDate=now,
        )
        self.session.add(ledger)
        await self.session.flush()
        return ledger.LedgerMId

    async def create_account_entry(self, entry: Account) -> Account:
        self.session.add(entry)
        await self.session.flush()
        return entry

    async def get_account_entries_by_tx(
        self,
        transaction_id: int,
        include_deleted: bool = False,
    ) -> Sequence[Account]:
        stmt = select(Account).where(Account.TransactionId == transaction_id)
        if not include_deleted:
            stmt = stmt.where(
                or_(Account.isdeleted == 0, Account.isdeleted.is_(None))
            )
        stmt = stmt.order_by(Account.AccTransId, Account.AccountId)
        res = await self.session.execute(stmt)
        return res.scalars().all()

    # -----------------------------------------------------------------------
    # 8. Staged Policy Proposals (tbl_transactionappnew)
    # -----------------------------------------------------------------------

    async def create_proposal(
        self,
        proposal: TransactionAppNew,
    ) -> TransactionAppNew:
        self.session.add(proposal)
        await self.session.flush()
        return proposal

    async def get_proposal_by_id(
        self,
        trans_id: int,
    ) -> Optional[TransactionAppNew]:
        stmt = select(TransactionAppNew).where(TransactionAppNew.TransId == trans_id)
        res = await self.session.execute(stmt)
        return res.scalars().first()

    async def list_proposals(
        self,
        *,
        user_id: Optional[int] = None,
        sales_executive_id: Optional[int] = None,
        franchise_id: Optional[int] = None,
        quotation_code: Optional[str] = None,
        registration_no: Optional[str] = None,
        is_submit: Optional[int] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[int, Sequence[TransactionAppNew]]:
        conditions = []
        if user_id is not None:
            conditions.append(TransactionAppNew.UserId == user_id)
        if sales_executive_id is not None:
            conditions.append(TransactionAppNew.SalesExecutiveId == sales_executive_id)
        if franchise_id is not None:
            conditions.append(TransactionAppNew.FranchaiseId == franchise_id)
        if quotation_code:
            conditions.append(TransactionAppNew.QuatationCode == quotation_code.strip())
        if registration_no:
            conditions.append(TransactionAppNew.RegistrationNo == registration_no.strip())
        if is_submit is not None:
            conditions.append(TransactionAppNew.IsSubmit == is_submit)

        count_stmt = select(func.count(TransactionAppNew.TransId))
        if conditions:
            count_stmt = count_stmt.where(*conditions)
        total_res = await self.session.execute(count_stmt)
        total = int(total_res.scalar() or 0)

        data_stmt = select(TransactionAppNew)
        if conditions:
            data_stmt = data_stmt.where(*conditions)
        data_stmt = (
            data_stmt.order_by(desc(TransactionAppNew.TransId))
            .limit(limit)
            .offset(offset)
        )
        rows_res = await self.session.execute(data_stmt)
        return total, rows_res.scalars().all()
