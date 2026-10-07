"""
Repository Layer for Phase 8 Payments, Cheques, Reconciliation & E-Wallet Engine.
Encapsulates SQLAlchemy 2.0 AsyncSession queries and InnoDB FOR UPDATE row locks for:
- tbl_transactionpayment (TransactionPayment)
- tbl_transaction (Transaction)
- tbl_transactionappnew (TransactionAppNew)
- tbl_account (Account)
- tbl_ledgermaster (LedgerMaster)
- tbl_cutnpaycommpayable (CutNPayCommPayable)
- tbl_agentcommissionpayment (AgentCommissionPayment)
- tbl_franchisecommission (FranchiseCommission)
"""
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional, Sequence, Tuple
from sqlalchemy import desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account
from app.models.ledger import LedgerMaster
from app.models.payment import TransactionPayment
from app.models.transaction import Transaction
from app.models.transaction_app import TransactionAppNew
from app.repositories.quotation import _to_decimal


TWO_DP = Decimal("0.01")
ZERO = Decimal("0.00")


def _round_2dp(val: Decimal) -> Decimal:
    return val.quantize(TWO_DP, rounding=ROUND_HALF_UP)


class PaymentEngineRepository:
    """Data-access layer for Phase 8 Payments, Cheques, Reconciliation & E-Wallet Engine."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # -----------------------------------------------------------------------
    # 1. Payment & Cheque Queries (tbl_transactionpayment)
    # -----------------------------------------------------------------------

    async def get_payment_by_id(
        self,
        payment_id: int,
        include_deleted: bool = True,
        for_update: bool = False,
    ) -> Optional[TransactionPayment]:
        stmt = select(TransactionPayment).where(TransactionPayment.PaymentId == payment_id)
        if not include_deleted:
            stmt = stmt.where(
                or_(
                    TransactionPayment.isdeleted == "0",
                    TransactionPayment.isdeleted.is_(None),
                )
            )
        if for_update:
            stmt = stmt.with_for_update()
        res = await self.session.execute(stmt)
        return res.scalars().first()

    async def get_active_payment_by_idempotency(
        self,
        transaction_id: int,
        idempotency_key: str,
    ) -> Optional[TransactionPayment]:
        if not idempotency_key or not idempotency_key.strip():
            return None
        tag = f"IDEMP:{idempotency_key.strip()}"
        stmt = (
            select(TransactionPayment)
            .where(
                TransactionPayment.TransanctionId == transaction_id,
                TransactionPayment.Extra2 == tag,
                or_(
                    TransactionPayment.isdeleted == "0",
                    TransactionPayment.isdeleted.is_(None),
                ),
            )
            .with_for_update()
        )
        res = await self.session.execute(stmt)
        return res.scalars().first()

    async def get_active_cheque_duplicate(
        self,
        transaction_id: int,
        docno: str,
        bankname: str,
    ) -> Optional[TransactionPayment]:
        if not docno or not bankname:
            return None
        stmt = (
            select(TransactionPayment)
            .where(
                TransactionPayment.TransanctionId == transaction_id,
                TransactionPayment.docno == docno.strip(),
                TransactionPayment.bankname == bankname.strip(),
                or_(
                    TransactionPayment.isdeleted == "0",
                    TransactionPayment.isdeleted.is_(None),
                ),
            )
            .with_for_update()
        )
        res = await self.session.execute(stmt)
        return res.scalars().first()

    async def get_all_payments_by_tx(
        self,
        transaction_id: int,
        include_deleted: bool = True,
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

    async def list_payments(
        self,
        *,
        branch_id: Optional[int] = None,
        transaction_id: Optional[int] = None,
        payment_type: Optional[str] = None,
        status_filter: Optional[str] = None,
        docno: Optional[str] = None,
        include_deleted: bool = True,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[int, Sequence[TransactionPayment]]:
        conditions = []
        if not include_deleted:
            conditions.append(
                or_(
                    TransactionPayment.isdeleted == "0",
                    TransactionPayment.isdeleted.is_(None),
                )
            )
        if branch_id is not None:
            conditions.append(TransactionPayment.BranchId == branch_id)
        if transaction_id is not None:
            conditions.append(TransactionPayment.TransanctionId == transaction_id)
        if payment_type:
            conditions.append(TransactionPayment.PaymentType == payment_type.strip().upper())
        if status_filter:
            conditions.append(TransactionPayment.Extra1 == status_filter.strip().upper())
        if docno:
            conditions.append(TransactionPayment.docno == docno.strip())

        count_stmt = select(func.count(TransactionPayment.PaymentId))
        if conditions:
            count_stmt = count_stmt.where(*conditions)
        total_res = await self.session.execute(count_stmt)
        total = int(total_res.scalar() or 0)

        data_stmt = select(TransactionPayment)
        if conditions:
            data_stmt = data_stmt.where(*conditions)
        data_stmt = (
            data_stmt.order_by(desc(TransactionPayment.PaymentId))
            .limit(limit)
            .offset(offset)
        )
        rows_res = await self.session.execute(data_stmt)
        return total, rows_res.scalars().all()

    # -----------------------------------------------------------------------
    # 2. Policy Transaction Row-Locking & Reconciliation Queries (tbl_transaction)
    # -----------------------------------------------------------------------

    async def get_transaction_for_update(
        self,
        transaction_id: int,
        include_deleted: bool = False,
    ) -> Optional[Transaction]:
        stmt = select(Transaction).where(Transaction.TransanctionId == transaction_id)
        if not include_deleted:
            stmt = stmt.where(
                or_(Transaction.isdeleted == "0", Transaction.isdeleted.is_(None))
            )
        stmt = stmt.with_for_update()
        res = await self.session.execute(stmt)
        return res.scalars().first()

    async def list_reconciliation_transactions(
        self,
        *,
        branch_id: Optional[int] = None,
        insurance_company_id: Optional[int] = None,
        is_rcon_data_match: Optional[int] = None,
        ib_receipt_status: Optional[int] = None,
        policy_no: Optional[str] = None,
        inward_no: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[int, Sequence[Transaction]]:
        conditions = [
            or_(Transaction.isdeleted == "0", Transaction.isdeleted.is_(None))
        ]
        if branch_id is not None:
            conditions.append(Transaction.BranchId == branch_id)
        if insurance_company_id is not None:
            conditions.append(Transaction.InsuranceCompanyId == insurance_company_id)
        if is_rcon_data_match is not None:
            conditions.append(Transaction.IsRconDataMatch == is_rcon_data_match)
        if ib_receipt_status is not None:
            conditions.append(Transaction.IB_ReceiptStatus == ib_receipt_status)
        if policy_no:
            conditions.append(Transaction.PolicyNo == policy_no.strip())
        if inward_no:
            conditions.append(Transaction.InwardNo == inward_no.strip())

        count_stmt = select(func.count(Transaction.TransanctionId)).where(*conditions)
        total_res = await self.session.execute(count_stmt)
        total = int(total_res.scalar() or 0)

        data_stmt = (
            select(Transaction)
            .where(*conditions)
            .order_by(desc(Transaction.TransanctionId))
            .limit(limit)
            .offset(offset)
        )
        rows_res = await self.session.execute(data_stmt)
        return total, rows_res.scalars().all()

    # -----------------------------------------------------------------------
    # 3. Partner E-Wallet Sub-Ledger & Balance Computation (tbl_ledgermaster + tbl_account)
    # -----------------------------------------------------------------------

    async def resolve_or_create_wallet_ledger(
        self,
        owner_type: str,
        owner_id: int,
        branch_id: int,
        actor_user_id: int,
        for_update: bool = False,
    ) -> LedgerMaster:
        """
        Resolves the partner E-Wallet sub-ledger in tbl_ledgermaster:
        - LedgerTypeId = 5 for AGENT E-Wallet
        - LedgerTypeId = 6 for FRANCHISE E-Wallet
        - ReferenceId = owner_id
        Uses SELECT ... FOR UPDATE when for_update=True to serialize all concurrent
        wallet operations on this partner's sub-ledger.
        """
        norm_type = owner_type.strip().upper()
        ledger_type_id = 5 if norm_type == "AGENT" else 6

        stmt = (
            select(LedgerMaster)
            .where(
                LedgerMaster.LedgerTypeId == ledger_type_id,
                LedgerMaster.ReferenceId == owner_id,
                or_(LedgerMaster.isdeleted == "0", LedgerMaster.isdeleted.is_(None)),
            )
            .order_by(LedgerMaster.LedgerMId)
            .limit(1)
        )
        if for_update:
            stmt = stmt.with_for_update()

        res = await self.session.execute(stmt)
        existing = res.scalars().first()
        if existing is not None:
            return existing

        now = datetime.utcnow()
        ledger = LedgerMaster(
            LedgerTypeId=ledger_type_id,
            LedgerName=f"EWALLET - {norm_type} #{owner_id}",
            LedgerGroupId=2,
            ReferenceId=owner_id,
            BranchId=branch_id or 1,
            isdeleted="0",
            CreateUser=str(actor_user_id),
            CreateDate=now,
            UpdateUser=str(actor_user_id),
            UpdateDate=now,
        )
        self.session.add(ledger)
        await self.session.flush()

        if for_update:
            # Acquire row lock on newly created ledger row
            lock_stmt = (
                select(LedgerMaster)
                .where(LedgerMaster.LedgerMId == ledger.LedgerMId)
                .with_for_update()
            )
            await self.session.execute(lock_stmt)

        return ledger

    async def compute_wallet_balances(
        self,
        ledger_m_id: int,
        *,
        for_update: bool = False,
    ) -> Tuple[Decimal, Decimal, Decimal]:
        """
        Computes (settled_balance, locked_balance, available_balance) in Decimal(0.01)
        for a partner's E-Wallet sub-ledger (LedgerMId):
        - settled_balance = SUM(amount) WHERE AccTransId IN (10, 13, 14) AND isdeleted = 0
        - locked_balance  = SUM(ABS(amount)) WHERE AccTransId = 11 AND Extra1 = 'WALLET_LOCK' AND isdeleted = 0
        - available_balance = settled_balance - locked_balance
        When for_update=True, executes an InnoDB locking current read (SELECT ... FOR UPDATE)
        to guarantee latest committed balances under MySQL REPEATABLE READ isolation.
        """
        stmt = (
            select(Account)
            .where(
                Account.LedgerMId == ledger_m_id,
                or_(Account.isdeleted == 0, Account.isdeleted.is_(None)),
            )
            .execution_options(populate_existing=True)
        )
        if for_update:
            stmt = stmt.with_for_update()
        res = await self.session.execute(stmt)
        rows = res.scalars().all()

        settled = ZERO
        locked = ZERO
        for row in rows:
            amt = _round_2dp(_to_decimal(row.amount))
            if row.AccTransId in (10, 13, 14):
                settled = _round_2dp(settled + amt)
            elif row.AccTransId == 11 and (row.Extra1 or "") == "WALLET_LOCK":
                locked = _round_2dp(locked + abs(amt))

        available = _round_2dp(settled - locked)
        return settled, locked, available

    async def get_wallet_entry_by_idempotency(
        self,
        ledger_m_id: int,
        idempotency_key: str,
    ) -> Optional[Account]:
        if not idempotency_key or not idempotency_key.strip():
            return None
        tag = f"IDEMP:{idempotency_key.strip()}"
        stmt = (
            select(Account)
            .where(
                Account.LedgerMId == ledger_m_id,
                Account.Extra2 == tag,
                or_(Account.isdeleted == 0, Account.isdeleted.is_(None)),
            )
            .with_for_update()
        )
        res = await self.session.execute(stmt)
        return res.scalars().first()

    async def get_wallet_lock_for_update(
        self,
        *,
        lock_account_id: Optional[int] = None,
        proposal_trans_id: Optional[int] = None,
        ledger_m_id: Optional[int] = None,
    ) -> Optional[Account]:
        conditions = [
            Account.AccTransId == 11,
            or_(Account.isdeleted == 0, Account.isdeleted.is_(None)),
        ]
        if lock_account_id is not None:
            conditions.append(Account.AccountId == lock_account_id)
        if proposal_trans_id is not None:
            conditions.append(Account.TransId == proposal_trans_id)
        if ledger_m_id is not None:
            conditions.append(Account.LedgerMId == ledger_m_id)

        stmt = (
            select(Account)
            .where(*conditions)
            .order_by(desc(Account.AccountId))
            .limit(1)
            .with_for_update()
        )
        res = await self.session.execute(stmt)
        return res.scalars().first()

    async def list_wallet_entries(
        self,
        ledger_m_id: int,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[int, Sequence[Account]]:
        conditions = [
            Account.LedgerMId == ledger_m_id,
            or_(Account.isdeleted == 0, Account.isdeleted.is_(None)),
        ]
        count_stmt = select(func.count(Account.AccountId)).where(*conditions)
        total_res = await self.session.execute(count_stmt)
        total = int(total_res.scalar() or 0)

        data_stmt = (
            select(Account)
            .where(*conditions)
            .order_by(desc(Account.AccountId))
            .limit(limit)
            .offset(offset)
        )
        rows_res = await self.session.execute(data_stmt)
        return total, rows_res.scalars().all()
