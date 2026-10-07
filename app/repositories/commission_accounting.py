"""
Async SQLAlchemy Repository for Phase 9 — Commission & Accounting Engine.

Handles:
1. Commission records in `tbl_agentcommissionpayment`, `tbl_franchisecommission`, and `tbl_cutnpaycommpayable`
   with InnoDB `SELECT ... FOR UPDATE` and `populate_existing=True` for `REPEATABLE READ` safety.
2. Chart of Accounts / Master Ledgers in `tbl_ledgermaster`.
3. Double-Entry Voucher & Payout journal entries in `tbl_account` (`AccTransId = 6, 7, 8, 9`).
4. Concurrency-safe `Doc_No` sequence allocation and Trial Balance query aggregation.
"""
from datetime import date, datetime
from decimal import Decimal
from typing import Dict, List, Literal, Optional, Sequence, Tuple
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account
from app.models.commission import (
    AgentCommissionPayment,
    CutNPayCommPayable,
    FranchiseCommission,
)
from app.models.ledger import LedgerMaster
from app.models.transaction import Transaction


ZERO = Decimal("0.00")


class CommissionAccountingRepository:
    """Data access layer for Phase 9 Commission, Payout, Ledger, Voucher & Trial Balance operations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # -----------------------------------------------------------------------
    # 1. Policy Transaction & Commission Row Queries (with FOR UPDATE locks)
    # -----------------------------------------------------------------------

    async def get_transaction_by_id(
        self,
        transaction_id: int,
        include_deleted: bool = False,
        for_update: bool = False,
    ) -> Optional[Transaction]:
        stmt = select(Transaction).where(Transaction.TransanctionId == transaction_id)
        if not include_deleted:
            stmt = stmt.where(
                or_(Transaction.isdeleted == "0", Transaction.isdeleted.is_(None))
            )
        if for_update:
            stmt = stmt.with_for_update().execution_options(populate_existing=True)
        res = await self.session.execute(stmt)
        return res.scalars().first()

    async def get_agent_comm_by_tx(
        self,
        transaction_id: int,
        include_deleted: bool = False,
        for_update: bool = False,
    ) -> Optional[AgentCommissionPayment]:
        stmt = (
            select(AgentCommissionPayment)
            .where(AgentCommissionPayment.TransanctionId == transaction_id)
            .order_by(AgentCommissionPayment.AgentCommId.desc())
        )
        if not include_deleted:
            stmt = stmt.where(
                or_(
                    AgentCommissionPayment.isdeleted == "0",
                    AgentCommissionPayment.isdeleted.is_(None),
                )
            )
        if for_update:
            stmt = stmt.with_for_update().execution_options(populate_existing=True)
        res = await self.session.execute(stmt)
        return res.scalars().first()

    async def get_franchise_comm_by_tx(
        self,
        transaction_id: int,
        include_deleted: bool = False,
        for_update: bool = False,
    ) -> Optional[FranchiseCommission]:
        stmt = (
            select(FranchiseCommission)
            .where(FranchiseCommission.TransanctionId == transaction_id)
            .order_by(FranchiseCommission.FranchiseCommId.desc())
        )
        if not include_deleted:
            stmt = stmt.where(
                or_(
                    FranchiseCommission.isdeleted == 0,
                    FranchiseCommission.isdeleted.is_(None),
                )
            )
        if for_update:
            stmt = stmt.with_for_update().execution_options(populate_existing=True)
        res = await self.session.execute(stmt)
        return res.scalars().first()

    async def get_cutnpay_by_tx(
        self,
        transaction_id: int,
        include_deleted: bool = False,
        for_update: bool = False,
    ) -> Optional[CutNPayCommPayable]:
        stmt = (
            select(CutNPayCommPayable)
            .where(CutNPayCommPayable.TransactionId == transaction_id)
            .order_by(CutNPayCommPayable.CutNPayCommPayId.desc())
        )
        if not include_deleted:
            stmt = stmt.where(
                or_(
                    CutNPayCommPayable.Isdeleted == 0,
                    CutNPayCommPayable.Isdeleted.is_(None),
                )
            )
        if for_update:
            stmt = stmt.with_for_update().execution_options(populate_existing=True)
        res = await self.session.execute(stmt)
        return res.scalars().first()

    async def list_commission_transactions(
        self,
        *,
        branch_id: Optional[int] = None,
        agent_id: Optional[int] = None,
        franchise_code: Optional[str] = None,
        sales_ex_id: Optional[int] = None,
        policy_no: Optional[str] = None,
        inward_no: Optional[str] = None,
        commission_paid: Optional[int] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[int, List[Transaction]]:
        filters = [or_(Transaction.isdeleted == "0", Transaction.isdeleted.is_(None))]
        if branch_id is not None:
            filters.append(Transaction.BranchId == branch_id)
        if agent_id is not None:
            filters.append(Transaction.AgentId == agent_id)
        if franchise_code is not None:
            filters.append(Transaction.FranchiseCode == franchise_code)
        if sales_ex_id is not None:
            filters.append(
                or_(
                    Transaction.SalesEx_id == sales_ex_id,
                    Transaction.LocationHeadId == sales_ex_id,
                )
            )
        if policy_no:
            filters.append(Transaction.PolicyNo == policy_no.strip())
        if inward_no:
            filters.append(Transaction.InwardNo == inward_no.strip())
        if commission_paid is not None:
            filters.append(Transaction.CommissionPaid == commission_paid)

        count_stmt = select(func.count(Transaction.TransanctionId)).where(and_(*filters))
        total = int((await self.session.execute(count_stmt)).scalar() or 0)

        stmt = (
            select(Transaction)
            .where(and_(*filters))
            .order_by(Transaction.TransanctionId.desc())
            .limit(limit)
            .offset(offset)
        )
        rows = list((await self.session.execute(stmt)).scalars().all())
        return total, rows

    async def list_agent_comm_rows_for_partner(
        self,
        *,
        agent_id: Optional[int] = None,
        transaction_ids: Optional[Sequence[int]] = None,
        only_unpaid: bool = True,
        for_update: bool = False,
    ) -> List[AgentCommissionPayment]:
        filters = [
            or_(
                AgentCommissionPayment.isdeleted == "0",
                AgentCommissionPayment.isdeleted.is_(None),
            )
        ]
        if agent_id is not None:
            filters.append(AgentCommissionPayment.Extra1 == str(agent_id))
        if transaction_ids:
            filters.append(AgentCommissionPayment.TransanctionId.in_(list(transaction_ids)))
        if only_unpaid:
            filters.append(AgentCommissionPayment.NetAmount > 0)

        stmt = (
            select(AgentCommissionPayment)
            .where(and_(*filters))
            .order_by(AgentCommissionPayment.AgentCommId.asc())
        )
        if for_update:
            stmt = stmt.with_for_update().execution_options(populate_existing=True)
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def list_franchise_comm_rows_for_partner(
        self,
        *,
        franchise_id: Optional[int] = None,
        transaction_ids: Optional[Sequence[int]] = None,
        only_unpaid: bool = True,
        for_update: bool = False,
    ) -> List[FranchiseCommission]:
        filters = [
            or_(
                FranchiseCommission.isdeleted == 0,
                FranchiseCommission.isdeleted.is_(None),
            )
        ]
        if franchise_id is not None:
            filters.append(FranchiseCommission.FranchiseId == franchise_id)
        if transaction_ids:
            filters.append(FranchiseCommission.TransanctionId.in_(list(transaction_ids)))
        if only_unpaid:
            filters.append(
                func.coalesce(FranchiseCommission.FranchiseNetComm, 0)
                > func.coalesce(FranchiseCommission.FCommissionPaid, 0)
            )

        stmt = (
            select(FranchiseCommission)
            .where(and_(*filters))
            .order_by(FranchiseCommission.FranchiseCommId.asc())
        )
        if for_update:
            stmt = stmt.with_for_update().execution_options(populate_existing=True)
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    # -----------------------------------------------------------------------
    # 2. Chart of Accounts / Master Ledger (`tbl_ledgermaster`)
    # -----------------------------------------------------------------------

    async def get_ledger_by_id(
        self,
        ledger_m_id: int,
        include_deleted: bool = False,
        for_update: bool = False,
    ) -> Optional[LedgerMaster]:
        stmt = select(LedgerMaster).where(LedgerMaster.LedgerMId == ledger_m_id)
        if not include_deleted:
            stmt = stmt.where(
                or_(LedgerMaster.isdeleted == "0", LedgerMaster.isdeleted.is_(None))
            )
        if for_update:
            stmt = stmt.with_for_update().execution_options(populate_existing=True)
        res = await self.session.execute(stmt)
        return res.scalars().first()

    async def get_ledger_by_name_and_branch(
        self,
        ledger_name: str,
        branch_id: int,
        for_update: bool = False,
    ) -> Optional[LedgerMaster]:
        stmt = (
            select(LedgerMaster)
            .where(
                and_(
                    LedgerMaster.LedgerName == ledger_name.strip(),
                    LedgerMaster.BranchId == branch_id,
                    or_(LedgerMaster.isdeleted == "0", LedgerMaster.isdeleted.is_(None)),
                )
            )
            .order_by(LedgerMaster.LedgerMId.asc())
        )
        if for_update:
            stmt = stmt.with_for_update().execution_options(populate_existing=True)
        res = await self.session.execute(stmt)
        return res.scalars().first()

    async def resolve_or_create_system_ledger(
        self,
        *,
        ledger_name: str,
        ledger_type_id: int,
        ledger_group_id: int,
        reference_id: int,
        branch_id: int,
        actor_user_id: int,
        for_update: bool = False,
    ) -> LedgerMaster:
        existing = await self.get_ledger_by_name_and_branch(
            ledger_name=ledger_name,
            branch_id=branch_id,
            for_update=for_update,
        )
        if existing is not None:
            return existing

        now_dt = datetime.utcnow()
        row = LedgerMaster(
            LedgerTypeId=ledger_type_id,
            LedgerName=ledger_name.strip(),
            LedgerGroupId=ledger_group_id,
            ReferenceId=reference_id,
            BranchId=branch_id,
            isdeleted="0",
            CreateUser=str(actor_user_id),
            CreateDate=now_dt,
            UpdateUser=str(actor_user_id),
            UpdateDate=now_dt,
        )
        self.session.add(row)
        await self.session.flush()
        return row

    async def create_ledger(self, row: LedgerMaster) -> LedgerMaster:
        self.session.add(row)
        await self.session.flush()
        return row

    async def list_ledgers(
        self,
        *,
        branch_id: Optional[int] = None,
        ledger_type_id: Optional[int] = None,
        ledger_group_id: Optional[int] = None,
        reference_id: Optional[int] = None,
        search: Optional[str] = None,
        include_deleted: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[int, List[LedgerMaster]]:
        filters = []
        if not include_deleted:
            filters.append(
                or_(LedgerMaster.isdeleted == "0", LedgerMaster.isdeleted.is_(None))
            )
        if branch_id is not None:
            filters.append(LedgerMaster.BranchId == branch_id)
        if ledger_type_id is not None:
            filters.append(LedgerMaster.LedgerTypeId == ledger_type_id)
        if ledger_group_id is not None:
            filters.append(LedgerMaster.LedgerGroupId == ledger_group_id)
        if reference_id is not None:
            filters.append(LedgerMaster.ReferenceId == reference_id)
        if search:
            filters.append(LedgerMaster.LedgerName.ilike(f"%{search.strip()}%"))

        where_clause = and_(*filters) if filters else True
        count_stmt = select(func.count(LedgerMaster.LedgerMId)).where(where_clause)
        total = int((await self.session.execute(count_stmt)).scalar() or 0)

        stmt = (
            select(LedgerMaster)
            .where(where_clause)
            .order_by(LedgerMaster.LedgerMId.asc())
            .limit(limit)
            .offset(offset)
        )
        rows = list((await self.session.execute(stmt)).scalars().all())
        return total, rows

    # -----------------------------------------------------------------------
    # 3. Accounting Entries, Vouchers & Payouts (`tbl_account`)
    # -----------------------------------------------------------------------

    async def allocate_next_doc_no(self) -> int:
        """
        Concurrency-safe allocation of the next monotonically increasing `Doc_No` in `tbl_account`.
        Uses `with_for_update().execution_options(populate_existing=True)` inside `_COMMISSION_WRITE_LOCK`.
        """
        stmt = (
            select(func.coalesce(func.max(Account.Doc_No), 1000))
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        max_doc = int((await self.session.execute(stmt)).scalar() or 1000)
        return max(max_doc, 1000) + 1

    async def create_account_entry(self, entry: Account) -> Account:
        self.session.add(entry)
        await self.session.flush()
        return entry

    async def get_account_rows_by_doc_no(
        self,
        doc_no: int,
        acc_trans_ids: Optional[Sequence[int]] = None,
        include_deleted: bool = False,
        for_update: bool = False,
    ) -> List[Account]:
        filters = [Account.Doc_No == doc_no]
        if acc_trans_ids:
            filters.append(Account.AccTransId.in_(list(acc_trans_ids)))
        if not include_deleted:
            filters.append(or_(Account.isdeleted == 0, Account.isdeleted.is_(None)))

        stmt = (
            select(Account)
            .where(and_(*filters))
            .order_by(Account.AccountId.asc())
        )
        if for_update:
            stmt = stmt.with_for_update().execution_options(populate_existing=True)
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def get_account_by_idempotency(
        self,
        idempotency_marker: str,
        acc_trans_ids: Sequence[int],
    ) -> Optional[Account]:
        stmt = (
            select(Account)
            .where(
                and_(
                    Account.AccTransId.in_(list(acc_trans_ids)),
                    Account.Extra2.ilike(f"%{idempotency_marker}%"),
                    or_(Account.isdeleted == 0, Account.isdeleted.is_(None)),
                )
            )
            .order_by(Account.AccountId.asc())
        )
        res = await self.session.execute(stmt)
        return res.scalars().first()

    async def list_distinct_voucher_doc_nos(
        self,
        *,
        acc_trans_ids: Sequence[int],
        branch_id: Optional[int] = None,
        reference_agent_id: Optional[int] = None,
        extra1_prefix: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[int, List[int]]:
        filters = [
            Account.AccTransId.in_(list(acc_trans_ids)),
            Account.Doc_No.is_not(None),
            or_(Account.isdeleted == 0, Account.isdeleted.is_(None)),
        ]
        if branch_id is not None:
            filters.append(Account.BranchId == branch_id)
        if reference_agent_id is not None:
            filters.append(Account.ReferenceAgentId == reference_agent_id)
        if extra1_prefix:
            filters.append(Account.Extra1.ilike(f"{extra1_prefix}%"))

        count_stmt = select(func.count(func.distinct(Account.Doc_No))).where(and_(*filters))
        total = int((await self.session.execute(count_stmt)).scalar() or 0)

        stmt = (
            select(Account.Doc_No)
            .where(and_(*filters))
            .group_by(Account.Doc_No)
            .order_by(Account.Doc_No.desc())
            .limit(limit)
            .offset(offset)
        )
        doc_nos = [int(r) for r in (await self.session.execute(stmt)).scalars().all() if r is not None]
        return total, doc_nos

    async def list_ledger_entries(
        self,
        ledger_m_id: int,
        *,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        include_deleted: bool = False,
    ) -> List[Account]:
        filters = [Account.LedgerMId == ledger_m_id]
        if not include_deleted:
            filters.append(or_(Account.isdeleted == 0, Account.isdeleted.is_(None)))
        if from_date is not None:
            filters.append(
                Account.AccountDate >= datetime.combine(from_date, datetime.min.time())
            )
        if to_date is not None:
            filters.append(
                Account.AccountDate <= datetime.combine(to_date, datetime.max.time())
            )

        stmt = (
            select(Account)
            .where(and_(*filters))
            .order_by(Account.AccountDate.asc(), Account.AccountId.asc())
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def list_active_account_entries(
        self,
        *,
        branch_id: Optional[int] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
    ) -> List[Account]:
        filters = [or_(Account.isdeleted == 0, Account.isdeleted.is_(None))]
        if branch_id is not None:
            filters.append(Account.BranchId == branch_id)
        if from_date is not None:
            filters.append(
                Account.AccountDate >= datetime.combine(from_date, datetime.min.time())
            )
        if to_date is not None:
            filters.append(
                Account.AccountDate <= datetime.combine(to_date, datetime.max.time())
            )

        stmt = (
            select(Account)
            .where(and_(*filters))
            .order_by(Account.AccountId.asc())
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())
