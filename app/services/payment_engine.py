"""
Service Layer for Phase 8 Payments, Cheques, Reconciliation & E-Wallet Engine.

Orchestrates:
1. Payment & Cheque Lifecycle (Pending Clearance -> Deposited -> Cleared -> Bounced + Penalty -> Re-presentation)
2. Payment Reversal & Contra Accounting Ledger Entries (AccTransId = 2, 4)
3. Insurer Payment & Brokerage Reconciliation (IsRconDataMatch, RconGrid, RconComm, IB_Doc_No, AccTransId = 5)
4. Partner E-Wallet Sub-Ledger & Concurrency-Safe Lock/Release/Debit/Top-Up/Refund (AccTransId = 10, 11, 12, 13, 14)
"""
import asyncio
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Literal, Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac import (
    AGENT_PRINCIPAL_ROLES,
    EMPLOYEE_PRINCIPAL_ROLES,
    FRANCHISE_PRINCIPAL_ROLES,
    PrincipalContext,
    WALLET_ADMIN_WRITE_ROLES,
    _normalize,
    is_global_admin_role,
    is_global_read_role,
)
from app.models.account import Account
from app.models.ledger import LedgerMaster
from app.models.payment import TransactionPayment
from app.models.transaction import Transaction
from app.models.user import User
from app.repositories.payment_engine import PaymentEngineRepository
from app.repositories.policy_booking import PolicyBookingRepository
from app.repositories.quotation import _to_decimal
from app.schemas.payment import (
    ChequeBounceRequest,
    ChequeClearRequest,
    ChequeDepositRequest,
    PaymentLifecycleActionResponse,
    PaymentListResponse,
    PaymentReversalRequest,
    ReconciliationListResponse,
    ReconciliationMatchRequest,
    ReconciliationMatchResponse,
    WalletBalanceResponse,
    WalletDebitRequest,
    WalletLedgerListResponse,
    WalletLockRequest,
    WalletOperationResponse,
    WalletReleaseRequest,
    WalletTopupRequest,
    WalletTransactionEntryResponse,
)
from app.schemas.policy import (
    AccountingEntryResponse,
    PaymentInstrumentResponse,
)
from app.services.rating import HUNDRED, ONE_RUPEE, ZERO, round_rupee


TWO_DP = Decimal("0.01")

# Process-level locks complementing MySQL InnoDB FOR UPDATE row locks
_PAYMENT_WRITE_LOCK = asyncio.Lock()
_WALLET_WRITE_LOCK = asyncio.Lock()

_AGENT_ROLES_NORM = frozenset(_normalize(r) for r in AGENT_PRINCIPAL_ROLES)
_EMPLOYEE_ROLES_NORM = frozenset(_normalize(r) for r in EMPLOYEE_PRINCIPAL_ROLES)
_FRANCHISE_ROLES_NORM = frozenset(_normalize(r) for r in FRANCHISE_PRINCIPAL_ROLES)
_WALLET_ADMIN_NORM = frozenset(_normalize(r) for r in WALLET_ADMIN_WRITE_ROLES)


def round_2dp(val: Decimal) -> Decimal:
    """Rounds a Decimal monetary or percentage value to 2 decimal places using ROUND_HALF_UP."""
    return val.quantize(TWO_DP, rounding=ROUND_HALF_UP)


# ---------------------------------------------------------------------------
# Pure Deterministic Calculation Helpers (Unit-Testable)
# ---------------------------------------------------------------------------


def evaluate_payment_instrument_state(payment_type: str) -> Tuple[str, int]:
    """
    Returns (initial_status, cashier_approval) for a newly recorded payment instrument:
    - CHEQUE and DD start in ("PENDING_CLEARANCE", 0)
    - All immediate instruments start in ("RECEIVED", 1)
    """
    norm = payment_type.strip().upper()
    if norm in {"CHEQUE", "DD"}:
        return "PENDING_CLEARANCE", 0
    return "RECEIVED", 1


def calculate_cheque_bounce_effect(
    current_paid: Decimal,
    current_outstanding: Decimal,
    cheque_amount: Decimal,
    penalty_amount: Decimal = ZERO,
) -> Tuple[Decimal, Decimal, Decimal]:
    """
    Calculates (new_paid, new_outstanding, contra_reversal_amount) when a cheque bounces:
    - new_paid = max(0.00, current_paid - cheque_amount)
    - new_outstanding = current_outstanding + cheque_amount + penalty_amount
    - contra_reversal_amount = -cheque_amount
    """
    c_paid = round_2dp(current_paid)
    c_out = round_2dp(current_outstanding)
    chq_amt = round_2dp(cheque_amount)
    pen_amt = round_2dp(penalty_amount)

    new_paid = max(ZERO, round_2dp(c_paid - chq_amt))
    new_outstanding = round_2dp(c_out + chq_amt + pen_amt)
    contra_reversal = -chq_amt
    return new_paid, new_outstanding, contra_reversal


def calculate_payment_reversal_effect(
    current_paid: Decimal,
    current_outstanding: Decimal,
    reversed_amount: Decimal,
) -> Tuple[Decimal, Decimal, Decimal]:
    """
    Calculates (new_paid, new_outstanding, contra_reversal_amount) when an active payment is reversed:
    - new_paid = max(0.00, current_paid - reversed_amount)
    - new_outstanding = current_outstanding + reversed_amount
    - contra_reversal_amount = -reversed_amount
    """
    c_paid = round_2dp(current_paid)
    c_out = round_2dp(current_outstanding)
    rev_amt = round_2dp(reversed_amount)

    new_paid = max(ZERO, round_2dp(c_paid - rev_amt))
    new_outstanding = round_2dp(c_out + rev_amt)
    contra_reversal = -rev_amt
    return new_paid, new_outstanding, contra_reversal


def evaluate_reconciliation_match(
    net_premium: Decimal,
    booked_gross_comm: Decimal,
    reconciled_grid_percent: Optional[Decimal] = None,
    reconciled_comm_amount: Optional[Decimal] = None,
    allow_partial_match: bool = True,
) -> Tuple[Decimal, Decimal, Decimal, int, Literal["UNRECONCILED", "MATCHED", "PARTIAL_VARIANCE"]]:
    """
    Evaluates insurer brokerage reconciliation against booked commission:
    Returns (eff_rcon_grid, eff_rcon_comm, commission_variance, is_rcon_data_match, match_status).
    """
    net_prem = round_2dp(net_premium)
    booked_comm = round_2dp(booked_gross_comm)

    if reconciled_comm_amount is not None and reconciled_grid_percent is None:
        eff_comm = round_2dp(reconciled_comm_amount)
        eff_grid = round_2dp((eff_comm * HUNDRED) / net_prem) if net_prem > ZERO else ZERO
    elif reconciled_grid_percent is not None and reconciled_comm_amount is None:
        eff_grid = round_2dp(reconciled_grid_percent)
        eff_comm = round_2dp((net_prem * eff_grid) / HUNDRED)
    elif reconciled_grid_percent is not None and reconciled_comm_amount is not None:
        eff_grid = round_2dp(reconciled_grid_percent)
        eff_comm = round_2dp(reconciled_comm_amount)
    else:
        eff_comm = booked_comm
        eff_grid = round_2dp((eff_comm * HUNDRED) / net_prem) if net_prem > ZERO else ZERO

    variance = round_2dp(eff_comm - booked_comm)
    if abs(variance) <= ONE_RUPEE:
        return eff_grid, eff_comm, variance, 1, "MATCHED"

    if not allow_partial_match:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Reconciliation variance rejected: reconciled commission ({eff_comm}) deviates from "
                f"booked gross commission ({booked_comm}) by {variance} (> 1.00 rupee)."
            ),
        )
    return eff_grid, eff_comm, variance, 2, "PARTIAL_VARIANCE"


def map_payment_instrument_response(p: TransactionPayment) -> PaymentInstrumentResponse:
    """Maps a TransactionPayment ORM instance to PaymentInstrumentResponse."""
    p_type = (p.PaymentType or "CASH").strip().upper()
    if p.Extra1 and p.Extra1.strip():
        derived_status = p.Extra1.strip()
    elif p.isdeleted == "1":
        derived_status = "REVERSED"
    elif p_type in {"CHEQUE", "DD"}:
        derived_status = "CLEARED" if (p.AccountantApproval == 1) else "PENDING_CLEARANCE"
    else:
        derived_status = "RECEIVED"

    return PaymentInstrumentResponse(
        payment_id=p.PaymentId,
        transaction_id=p.TransanctionId,
        payment_type=p_type,
        paid_amount=round_2dp(_to_decimal(p.PaidAmount)),
        payment_date=p.PaymentDate,
        docno=p.docno,
        bankname=p.bankname,
        payment_details=p.PaymentDetails,
        status=derived_status,
        extra_reference=p.Extra2,
        is_complete_payment=p.isCompletePayment,
        cashier_approval=p.CashierApproval,
        cashier_approval_date=p.CashierApprovalDate,
        accountant_approval=p.AccountantApproval,
        accountant_approval_date=p.AccountantApprovalDate,
        owner_approval=p.OwnerApproval,
        branch_id=p.BranchId,
        isdeleted=p.isdeleted or "0",
    )


def map_account_entry_response(a: Account, default_branch_id: int = 1) -> AccountingEntryResponse:
    """Maps an Account ORM instance to AccountingEntryResponse."""
    return AccountingEntryResponse(
        account_id=a.AccountId,
        acc_trans_id=a.AccTransId or 0,
        transaction_type=a.Extra1 or "POLICY_ENTRY",
        ledger_m_id=a.LedgerMId or 1,
        amount=round_2dp(_to_decimal(a.amount)),
        narration=a.Narration or "",
        reference_cust_id=a.ReferenceCustId,
        reference_agent_id=a.ReferenceAgentId,
        branch_id=a.BranchId or default_branch_id,
        payment_type=a.PaymentType,
        transaction_id=a.TransactionId,
        cust_veh_id=a.CustVehId,
        is_nill=a.IsNill,
        isdeleted=a.isdeleted or 0,
    )


# ---------------------------------------------------------------------------
# Partner E-Wallet Service (WalletService)
# ---------------------------------------------------------------------------


class WalletService:
    """
    Concurrency-safe Partner E-Wallet & Lock/Release Service backed by
    tbl_ledgermaster (LedgerTypeId 5=Agent, 6=Franchise) and tbl_account (AccTransId 10..14).
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = PaymentEngineRepository(session)
        self.booking_repo = PolicyBookingRepository(session)

    @staticmethod
    def _get_principal(user: User) -> PrincipalContext:
        ctx = getattr(user, "principal_context", None)
        if isinstance(ctx, PrincipalContext):
            return ctx
        return PrincipalContext(
            user_id=user.UserId,
            username=getattr(user, "UserName", None),
            role_id=getattr(user, "UserRoleId", None),
            role_name=getattr(user, "role_name", None),
            branch_id=getattr(user, "BranchId", None),
            agent_id=getattr(user, "agent_id", None),
            emp_id=getattr(user, "emp_id", None),
            employee_id=getattr(user, "employee_id", None),
            franchise_id=getattr(user, "franchise_id", None),
        )

    def _authorize_wallet_access(
        self,
        user: User,
        owner_type: str,
        owner_id: int,
        require_admin_write: bool = False,
    ) -> Tuple[Literal["AGENT", "FRANCHISE"], int, int]:
        """
        Validates that the caller is authorized to access or mutate the target partner E-Wallet.
        Returns (norm_owner_type, owner_id, branch_id).
        """
        ctx = self._get_principal(user)
        norm_role = _normalize(ctx.role_name)
        norm_type: Literal["AGENT", "FRANCHISE"] = (
            "FRANCHISE" if owner_type.strip().upper() == "FRANCHISE" else "AGENT"
        )
        branch_id = ctx.branch_id or 1

        if require_admin_write and norm_role not in _WALLET_ADMIN_NORM:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{ctx.role_name}' is not authorized for administrative wallet top-up.",
            )

        if is_global_admin_role(ctx.role_name) or is_global_read_role(ctx.role_name) or norm_role in _WALLET_ADMIN_NORM:
            return norm_type, owner_id, branch_id

        if norm_role in _AGENT_ROLES_NORM:
            bound_agent = ctx.agent_id or ctx.user_id
            if norm_type != "AGENT" or owner_id != bound_agent:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: Agent principal can only access its own Agent E-Wallet.",
                )
        elif norm_role in _FRANCHISE_ROLES_NORM:
            bound_frn = ctx.franchise_id or ctx.user_id
            if norm_type == "FRANCHISE" and owner_id != bound_frn:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: Franchise principal cannot access another Franchise's E-Wallet.",
                )

        return norm_type, owner_id, branch_id

    @staticmethod
    def _map_wallet_entry(a: Account) -> WalletTransactionEntryResponse:
        return WalletTransactionEntryResponse(
            account_id=a.AccountId,
            acc_trans_id=a.AccTransId or 0,
            entry_type=a.Extra1 or "WALLET_ENTRY",
            ledger_m_id=a.LedgerMId or 0,
            amount=round_2dp(_to_decimal(a.amount)),
            narration=a.Narration or "",
            payment_type=a.PaymentType,
            extra_reference=a.Extra2,
            doc_no=a.Doc_No,
            transaction_id=a.TransactionId or 0,
            proposal_trans_id=a.TransId or 0,
            created_date=a.CreatedDate,
        )

    async def _build_wallet_balance_response(
        self,
        ledger: LedgerMaster,
        owner_type: Literal["AGENT", "FRANCHISE"],
        owner_id: int,
    ) -> WalletBalanceResponse:
        settled, locked, available = await self.repo.compute_wallet_balances(
            ledger.LedgerMId, for_update=True
        )
        return WalletBalanceResponse(
            ledger_m_id=ledger.LedgerMId,
            owner_type=owner_type,
            owner_id=owner_id,
            branch_id=ledger.BranchId or 1,
            ledger_name=ledger.LedgerName or f"EWALLET - {owner_type} #{owner_id}",
            settled_balance=settled,
            locked_balance=locked,
            available_balance=available,
        )

    async def get_wallet_balance(
        self,
        owner_type: str,
        owner_id: int,
        current_user: User,
    ) -> WalletBalanceResponse:
        norm_type, eff_owner_id, branch_id = self._authorize_wallet_access(
            current_user, owner_type, owner_id, require_admin_write=False
        )
        ledger = await self.repo.resolve_or_create_wallet_ledger(
            owner_type=norm_type,
            owner_id=eff_owner_id,
            branch_id=branch_id,
            actor_user_id=current_user.UserId,
            for_update=False,
        )
        await self.session.commit()
        return await self._build_wallet_balance_response(ledger, norm_type, eff_owner_id)

    async def list_wallet_transactions(
        self,
        owner_type: str,
        owner_id: int,
        current_user: User,
        limit: int = 50,
        offset: int = 0,
    ) -> WalletLedgerListResponse:
        norm_type, eff_owner_id, branch_id = self._authorize_wallet_access(
            current_user, owner_type, owner_id, require_admin_write=False
        )
        ledger = await self.repo.resolve_or_create_wallet_ledger(
            owner_type=norm_type,
            owner_id=eff_owner_id,
            branch_id=branch_id,
            actor_user_id=current_user.UserId,
            for_update=False,
        )
        wallet_bal = await self._build_wallet_balance_response(ledger, norm_type, eff_owner_id)
        total, rows = await self.repo.list_wallet_entries(
            ledger_m_id=ledger.LedgerMId,
            limit=limit,
            offset=offset,
        )
        await self.session.commit()
        return WalletLedgerListResponse(
            wallet=wallet_bal,
            total=total,
            limit=limit,
            offset=offset,
            items=[self._map_wallet_entry(r) for r in rows],
        )

    async def topup_wallet(
        self,
        payload: WalletTopupRequest,
        current_user: User,
    ) -> WalletOperationResponse:
        """
        Credits a partner's E-Wallet sub-ledger (`AccTransId = 10`, `Extra1 = 'WALLET_TOPUP'`, `amount = +X`).
        Serialized via _WALLET_WRITE_LOCK and InnoDB SELECT ... FOR UPDATE on tbl_ledgermaster.
        """
        norm_type, eff_owner_id, caller_branch = self._authorize_wallet_access(
            current_user, payload.owner_type, payload.owner_id, require_admin_write=True
        )
        eff_branch = payload.branch_id or caller_branch
        credit_amt = round_2dp(payload.amount)

        async with _WALLET_WRITE_LOCK:
            try:
                ledger = await self.repo.resolve_or_create_wallet_ledger(
                    owner_type=norm_type,
                    owner_id=eff_owner_id,
                    branch_id=eff_branch,
                    actor_user_id=current_user.UserId,
                    for_update=True,
                )

                if payload.idempotency_key:
                    dup = await self.repo.get_wallet_entry_by_idempotency(
                        ledger.LedgerMId, payload.idempotency_key
                    )
                    if dup is not None:
                        raise HTTPException(
                            status_code=status.HTTP_409_CONFLICT,
                            detail=(
                                f"Duplicate wallet top-up: idempotency_key '{payload.idempotency_key}' "
                                f"already processed as AccountId #{dup.AccountId}."
                            ),
                        )

                now_dt = datetime.utcnow()
                extra2_val = (
                    f"IDEMP:{payload.idempotency_key.strip()}"
                    if payload.idempotency_key
                    else (payload.doc_no or f"TOPUP-{eff_owner_id}")
                )
                acc_row = Account(
                    AccTransId=10,
                    AccountDate=now_dt,
                    LedgerMId=ledger.LedgerMId,
                    amount=credit_amt,
                    Narration=payload.narration or f"E-Wallet Top-Up ({payload.payment_mode}) for {norm_type} #{eff_owner_id}",
                    ReferenceCustId=0,
                    ReferenceAgentId=eff_owner_id if norm_type == "AGENT" else 0,
                    BranchId=eff_branch,
                    Extra1="WALLET_TOPUP",
                    Extra2=extra2_val,
                    Doc_No=eff_owner_id,
                    CreatedUser=str(current_user.UserId),
                    CreatedDate=now_dt,
                    UpdatedUser=str(current_user.UserId),
                    UpdatedDate=now_dt,
                    PaymentType=payload.payment_mode.strip().upper(),
                    isdeleted=0,
                    IsNill=0,
                    TransactionId=0,
                    CustVehId=0,
                    MonthId=now_dt.month,
                    EndorsementId=0,
                    TransId=0,
                )
                await self.booking_repo.create_account_entry(acc_row)

                if payload.simulate_failure_at == "BEFORE_COMMIT":
                    raise RuntimeError("Simulated fault BEFORE_COMMIT in topup_wallet")

                wallet_bal = await self._build_wallet_balance_response(ledger, norm_type, eff_owner_id)
                await self.session.commit()
            except HTTPException:
                await self.session.rollback()
                raise
            except Exception as exc:
                await self.session.rollback()
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Atomic wallet top-up rolled back: {exc}",
                ) from exc

        return WalletOperationResponse(
            wallet=wallet_bal,
            ledger_entry=self._map_wallet_entry(acc_row),
        )

    async def lock_wallet_funds(
        self,
        payload: WalletLockRequest,
        current_user: User,
    ) -> WalletOperationResponse:
        """
        Reserves/locks funds in a partner's E-Wallet (`AccTransId = 11`, `Extra1 = 'WALLET_LOCK'`, `amount = -L`).
        Enforces `available_balance >= L` under InnoDB SELECT ... FOR UPDATE on tbl_ledgermaster.
        """
        norm_type, eff_owner_id, eff_branch = self._authorize_wallet_access(
            current_user, payload.owner_type, payload.owner_id, require_admin_write=False
        )
        lock_amt = round_2dp(payload.amount)

        async with _WALLET_WRITE_LOCK:
            try:
                ledger = await self.repo.resolve_or_create_wallet_ledger(
                    owner_type=norm_type,
                    owner_id=eff_owner_id,
                    branch_id=eff_branch,
                    actor_user_id=current_user.UserId,
                    for_update=True,
                )

                if payload.idempotency_key:
                    dup = await self.repo.get_wallet_entry_by_idempotency(
                        ledger.LedgerMId, payload.idempotency_key
                    )
                    if dup is not None:
                        raise HTTPException(
                            status_code=status.HTTP_409_CONFLICT,
                            detail=(
                                f"Duplicate wallet lock: idempotency_key '{payload.idempotency_key}' "
                                f"already locked under AccountId #{dup.AccountId}."
                            ),
                        )

                if payload.proposal_trans_id is not None:
                    existing_lock = await self.repo.get_wallet_lock_for_update(
                        proposal_trans_id=payload.proposal_trans_id,
                        ledger_m_id=ledger.LedgerMId,
                    )
                    if existing_lock is not None and existing_lock.Extra1 == "WALLET_LOCK":
                        raise HTTPException(
                            status_code=status.HTTP_409_CONFLICT,
                            detail=(
                                f"Proposal #{payload.proposal_trans_id} already has an active "
                                f"E-Wallet lock (AccountId #{existing_lock.AccountId})."
                            ),
                        )

                _, _, available = await self.repo.compute_wallet_balances(
                    ledger.LedgerMId, for_update=True
                )
                if lock_amt > available:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail=(
                            f"Insufficient E-Wallet available balance: requested lock ({lock_amt}) "
                            f"exceeds available_balance ({available})."
                        ),
                    )

                now_dt = datetime.utcnow()
                extra2_val = (
                    f"IDEMP:{payload.idempotency_key.strip()}"
                    if payload.idempotency_key
                    else (payload.quotation_code or f"LOCK-{payload.proposal_trans_id or 0}")
                )
                acc_row = Account(
                    AccTransId=11,
                    AccountDate=now_dt,
                    LedgerMId=ledger.LedgerMId,
                    amount=-lock_amt,
                    Narration=payload.narration or f"E-Wallet Lock Reservation for {norm_type} #{eff_owner_id}",
                    ReferenceCustId=0,
                    ReferenceAgentId=eff_owner_id if norm_type == "AGENT" else 0,
                    BranchId=eff_branch,
                    Extra1="WALLET_LOCK",
                    Extra2=extra2_val,
                    Doc_No=payload.proposal_trans_id or eff_owner_id,
                    CreatedUser=str(current_user.UserId),
                    CreatedDate=now_dt,
                    UpdatedUser=str(current_user.UserId),
                    UpdatedDate=now_dt,
                    PaymentType="EWALLET",
                    isdeleted=0,
                    IsNill=0,
                    TransactionId=0,
                    CustVehId=0,
                    MonthId=now_dt.month,
                    EndorsementId=0,
                    TransId=payload.proposal_trans_id or 0,
                )
                await self.booking_repo.create_account_entry(acc_row)

                if payload.proposal_trans_id is not None:
                    prop = await self.booking_repo.get_proposal_by_id(payload.proposal_trans_id)
                    if prop is not None:
                        prop.EwalletStatus = 2  # 2 = Locked/Reserved
                        prop.EWalletUsedamt = lock_amt
                        prop.UpdatedDate = now_dt
                        prop.UpdatedUser = str(current_user.UserId)

                if payload.simulate_failure_at == "BEFORE_COMMIT":
                    raise RuntimeError("Simulated fault BEFORE_COMMIT in lock_wallet_funds")

                wallet_bal = await self._build_wallet_balance_response(ledger, norm_type, eff_owner_id)
                await self.session.commit()
            except HTTPException:
                await self.session.rollback()
                raise
            except Exception as exc:
                await self.session.rollback()
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Atomic wallet lock rolled back: {exc}",
                ) from exc

        return WalletOperationResponse(
            wallet=wallet_bal,
            ledger_entry=self._map_wallet_entry(acc_row),
        )

    async def release_wallet_lock(
        self,
        payload: WalletReleaseRequest,
        current_user: User,
    ) -> WalletOperationResponse:
        """
        Releases an active E-Wallet lock (`AccTransId = 11`, `Extra1 = 'WALLET_LOCK'`),
        updating its state to `'WALLET_LOCK_RELEASED'` and posting an audit release row
        (`AccTransId = 12`, `Extra1 = 'WALLET_RELEASE'`, `amount = +L`).
        Prevents double-release with 409 Conflict.
        """
        async with _WALLET_WRITE_LOCK:
            try:
                lock_row = await self.repo.get_wallet_lock_for_update(
                    lock_account_id=payload.lock_account_id,
                    proposal_trans_id=payload.proposal_trans_id,
                )
                if lock_row is None:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Target E-Wallet lock record not found.",
                    )

                if lock_row.Extra1 == "WALLET_LOCK_RELEASED":
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"E-Wallet lock #{lock_row.AccountId} has already been released.",
                    )
                if lock_row.Extra1 == "WALLET_LOCK_CONSUMED":
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"E-Wallet lock #{lock_row.AccountId} has already been consumed by a policy debit.",
                    )

                # Resolve owning ledger and verify caller authorization
                from sqlalchemy import select as sa_select
                l_res = await self.session.execute(
                    sa_select(LedgerMaster)
                    .where(LedgerMaster.LedgerMId == lock_row.LedgerMId)
                    .with_for_update()
                )
                ledger = l_res.scalars().first()
                if ledger is None:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Wallet sub-ledger #{lock_row.LedgerMId} not found.",
                    )

                inferred_type: Literal["AGENT", "FRANCHISE"] = (
                    "FRANCHISE" if ledger.LedgerTypeId == 6 else "AGENT"
                )
                inferred_owner_id = ledger.ReferenceId or 0
                norm_type, eff_owner_id, eff_branch = self._authorize_wallet_access(
                    current_user,
                    payload.owner_type or inferred_type,
                    payload.owner_id or inferred_owner_id,
                    require_admin_write=False,
                )

                locked_amt = round_2dp(abs(_to_decimal(lock_row.amount)))
                now_dt = datetime.utcnow()

                # Mark lock as released
                lock_row.Extra1 = "WALLET_LOCK_RELEASED"
                lock_row.UpdatedDate = now_dt
                lock_row.UpdatedUser = str(current_user.UserId)

                # Post audit release entry (AccTransId = 12)
                rel_row = Account(
                    AccTransId=12,
                    AccountDate=now_dt,
                    LedgerMId=ledger.LedgerMId,
                    amount=locked_amt,
                    Narration=f"E-Wallet Lock #{lock_row.AccountId} Released: {payload.reason}",
                    ReferenceCustId=0,
                    ReferenceAgentId=eff_owner_id if norm_type == "AGENT" else 0,
                    BranchId=eff_branch,
                    Extra1="WALLET_RELEASE",
                    Extra2=f"REL:{lock_row.AccountId}",
                    Doc_No=lock_row.AccountId,
                    CreatedUser=str(current_user.UserId),
                    CreatedDate=now_dt,
                    UpdatedUser=str(current_user.UserId),
                    UpdatedDate=now_dt,
                    PaymentType="EWALLET",
                    isdeleted=0,
                    IsNill=0,
                    TransactionId=lock_row.TransactionId or 0,
                    CustVehId=0,
                    MonthId=now_dt.month,
                    EndorsementId=0,
                    TransId=lock_row.TransId or 0,
                )
                await self.booking_repo.create_account_entry(rel_row)

                if lock_row.TransId and lock_row.TransId > 0:
                    prop = await self.booking_repo.get_proposal_by_id(lock_row.TransId)
                    if prop is not None:
                        prop.EwalletStatus = 0
                        prop.UpdatedDate = now_dt
                        prop.UpdatedUser = str(current_user.UserId)

                if payload.simulate_failure_at == "BEFORE_COMMIT":
                    raise RuntimeError("Simulated fault BEFORE_COMMIT in release_wallet_lock")

                wallet_bal = await self._build_wallet_balance_response(ledger, norm_type, eff_owner_id)
                await self.session.commit()
            except HTTPException:
                await self.session.rollback()
                raise
            except Exception as exc:
                await self.session.rollback()
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Atomic wallet lock release rolled back: {exc}",
                ) from exc

        return WalletOperationResponse(
            wallet=wallet_bal,
            ledger_entry=self._map_wallet_entry(rel_row),
        )

    async def consume_or_debit_in_session(
        self,
        *,
        owner_type: str,
        owner_id: int,
        amount: Decimal,
        branch_id: int,
        actor_user_id: int,
        transaction_id: int = 0,
        proposal_trans_id: int = 0,
        lock_account_id: Optional[int] = None,
        narration: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> Tuple[LedgerMaster, Account]:
        """
        Executes a concurrency-safe E-Wallet debit (or consumes an active WALLET_LOCK)
        within the caller's active database session/transaction (without calling commit).
        Must be called while holding row locks.
        """
        norm_type: Literal["AGENT", "FRANCHISE"] = (
            "FRANCHISE" if owner_type.strip().upper() == "FRANCHISE" else "AGENT"
        )
        debit_amt = round_2dp(amount)
        if debit_amt <= ZERO:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Wallet debit amount must be greater than 0.00.",
            )

        ledger = await self.repo.resolve_or_create_wallet_ledger(
            owner_type=norm_type,
            owner_id=owner_id,
            branch_id=branch_id,
            actor_user_id=actor_user_id,
            for_update=True,
        )

        if idempotency_key:
            dup = await self.repo.get_wallet_entry_by_idempotency(
                ledger.LedgerMId, idempotency_key
            )
            if dup is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        f"Duplicate wallet debit: idempotency_key '{idempotency_key}' "
                        f"already processed as AccountId #{dup.AccountId}."
                    ),
                )

        now_dt = datetime.utcnow()

        # Check if a held lock is being consumed
        target_lock: Optional[Account] = None
        if lock_account_id is not None or proposal_trans_id > 0:
            target_lock = await self.repo.get_wallet_lock_for_update(
                lock_account_id=lock_account_id,
                proposal_trans_id=proposal_trans_id if lock_account_id is None else None,
                ledger_m_id=ledger.LedgerMId,
            )
            if lock_account_id is not None and target_lock is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"E-Wallet lock #{lock_account_id} not found for {norm_type} #{owner_id}.",
                )
            if target_lock is not None:
                if target_lock.Extra1 == "WALLET_LOCK_CONSUMED":
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"E-Wallet lock #{target_lock.AccountId} has already been consumed.",
                    )
                if target_lock.Extra1 == "WALLET_LOCK_RELEASED":
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"E-Wallet lock #{target_lock.AccountId} was already released and cannot be consumed.",
                    )

        settled, locked, available = await self.repo.compute_wallet_balances(
            ledger.LedgerMId, for_update=True
        )

        if target_lock is not None and target_lock.Extra1 == "WALLET_LOCK":
            lock_held_amt = round_2dp(abs(_to_decimal(target_lock.amount)))
            effective_available = round_2dp(available + lock_held_amt)
            if debit_amt > effective_available:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=(
                        f"Insufficient E-Wallet funds even with lock #{target_lock.AccountId} ({lock_held_amt}): "
                        f"debit ({debit_amt}) exceeds effective available ({effective_available})."
                    ),
                )
            target_lock.Extra1 = "WALLET_LOCK_CONSUMED"
            target_lock.TransactionId = transaction_id
            target_lock.UpdatedDate = now_dt
            target_lock.UpdatedUser = str(actor_user_id)
        else:
            if debit_amt > available:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=(
                        f"Insufficient E-Wallet available balance for {norm_type} #{owner_id}: "
                        f"debit ({debit_amt}) exceeds available_balance ({available})."
                    ),
                )

        extra2_val = (
            f"IDEMP:{idempotency_key.strip()}"
            if idempotency_key
            else (f"LOCK:{target_lock.AccountId}" if target_lock else f"TX:{transaction_id}")
        )
        debit_row = Account(
            AccTransId=13,
            AccountDate=now_dt,
            LedgerMId=ledger.LedgerMId,
            amount=-debit_amt,
            Narration=narration or f"E-Wallet Debit for Policy Transaction #{transaction_id}",
            ReferenceCustId=0,
            ReferenceAgentId=owner_id if norm_type == "AGENT" else 0,
            BranchId=branch_id,
            Extra1="WALLET_DEBIT",
            Extra2=extra2_val,
            Doc_No=transaction_id or proposal_trans_id or owner_id,
            CreatedUser=str(actor_user_id),
            CreatedDate=now_dt,
            UpdatedUser=str(actor_user_id),
            UpdatedDate=now_dt,
            PaymentType="EWALLET",
            isdeleted=0,
            IsNill=0,
            TransactionId=transaction_id,
            CustVehId=0,
            MonthId=now_dt.month,
            EndorsementId=0,
            TransId=proposal_trans_id,
        )
        await self.booking_repo.create_account_entry(debit_row)

        if proposal_trans_id > 0:
            prop = await self.booking_repo.get_proposal_by_id(proposal_trans_id)
            if prop is not None:
                prop.EwalletStatus = 1  # 1 = Debited / Settled
                prop.UpdatedDate = now_dt
                prop.UpdatedUser = str(actor_user_id)

        return ledger, debit_row

    async def refund_wallet_in_session(
        self,
        *,
        owner_type: str,
        owner_id: int,
        amount: Decimal,
        branch_id: int,
        actor_user_id: int,
        transaction_id: int = 0,
        narration: Optional[str] = None,
    ) -> Tuple[LedgerMaster, Account]:
        """
        Credits a partner's E-Wallet on payment reversal or policy cancellation
        (`AccTransId = 14`, `Extra1 = 'WALLET_REFUND'`, `amount = +X`).
        """
        norm_type: Literal["AGENT", "FRANCHISE"] = (
            "FRANCHISE" if owner_type.strip().upper() == "FRANCHISE" else "AGENT"
        )
        refund_amt = round_2dp(amount)
        ledger = await self.repo.resolve_or_create_wallet_ledger(
            owner_type=norm_type,
            owner_id=owner_id,
            branch_id=branch_id,
            actor_user_id=actor_user_id,
            for_update=True,
        )
        now_dt = datetime.utcnow()
        ref_row = Account(
            AccTransId=14,
            AccountDate=now_dt,
            LedgerMId=ledger.LedgerMId,
            amount=refund_amt,
            Narration=narration or f"E-Wallet Refund from Policy Transaction #{transaction_id}",
            ReferenceCustId=0,
            ReferenceAgentId=owner_id if norm_type == "AGENT" else 0,
            BranchId=branch_id,
            Extra1="WALLET_REFUND",
            Extra2=f"REFUND-TX:{transaction_id}",
            Doc_No=transaction_id or owner_id,
            CreatedUser=str(actor_user_id),
            CreatedDate=now_dt,
            UpdatedUser=str(actor_user_id),
            UpdatedDate=now_dt,
            PaymentType="EWALLET",
            isdeleted=0,
            IsNill=0,
            TransactionId=transaction_id,
            CustVehId=0,
            MonthId=now_dt.month,
            EndorsementId=0,
            TransId=0,
        )
        await self.booking_repo.create_account_entry(ref_row)
        return ledger, ref_row

    async def debit_wallet_funds(
        self,
        payload: WalletDebitRequest,
        current_user: User,
    ) -> WalletOperationResponse:
        """
        Standalone endpoint handler for POST /api/v1/wallets/debit.
        """
        norm_type, eff_owner_id, eff_branch = self._authorize_wallet_access(
            current_user, payload.owner_type, payload.owner_id, require_admin_write=False
        )
        async with _WALLET_WRITE_LOCK:
            try:
                ledger, debit_row = await self.consume_or_debit_in_session(
                    owner_type=norm_type,
                    owner_id=eff_owner_id,
                    amount=payload.amount,
                    branch_id=eff_branch,
                    actor_user_id=current_user.UserId,
                    transaction_id=payload.transaction_id or 0,
                    proposal_trans_id=payload.proposal_trans_id or 0,
                    lock_account_id=payload.lock_account_id,
                    narration=payload.narration,
                    idempotency_key=payload.idempotency_key,
                )
                if payload.simulate_failure_at == "BEFORE_COMMIT":
                    raise RuntimeError("Simulated fault BEFORE_COMMIT in debit_wallet_funds")

                wallet_bal = await self._build_wallet_balance_response(ledger, norm_type, eff_owner_id)
                await self.session.commit()
            except HTTPException:
                await self.session.rollback()
                raise
            except Exception as exc:
                await self.session.rollback()
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Atomic wallet debit rolled back: {exc}",
                ) from exc

        return WalletOperationResponse(
            wallet=wallet_bal,
            ledger_entry=self._map_wallet_entry(debit_row),
        )


# ---------------------------------------------------------------------------
# Payment, Cheque & Insurer Reconciliation Service (PaymentEngineService)
# ---------------------------------------------------------------------------


class PaymentEngineService:
    """
    Business logic service for Phase 8 Payment Lifecycle, Cheque Clearance/Bounce/Penalty,
    Payment Reversal, and Insurer Payment/Brokerage Reconciliation.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = PaymentEngineRepository(session)
        self.booking_repo = PolicyBookingRepository(session)
        self.wallet_service = WalletService(session)

    @staticmethod
    def _get_principal(user: User) -> PrincipalContext:
        return WalletService._get_principal(user)

    @staticmethod
    def _is_cross_branch_read_role(role_name: Optional[str]) -> bool:
        norm = _normalize(role_name)
        return is_global_read_role(role_name) or norm == "ALL USER"

    def _assert_can_access_transaction(
        self,
        tx: Transaction,
        user: User,
        for_write: bool = False,
    ) -> None:
        ctx = self._get_principal(user)
        norm_role = _normalize(ctx.role_name)

        if is_global_admin_role(ctx.role_name):
            return

        if not for_write and self._is_cross_branch_read_role(ctx.role_name):
            return

        # Account / Account Head roles have cross-branch authority for payment/reconciliation
        if norm_role in {"ACCOUNT", "ACCOUNT HEAD", "SHREYANSH OWNER"}:
            return

        if ctx.branch_id is not None and tx.BranchId is not None and tx.BranchId != ctx.branch_id:
            if norm_role != "ALL USER":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=(
                        f"Access denied: Transaction #{tx.TransanctionId} belongs to "
                        f"Branch {tx.BranchId}, outside caller Branch {ctx.branch_id}."
                    ),
                )

        if norm_role in _AGENT_ROLES_NORM:
            expected_agent = ctx.agent_id or ctx.user_id
            if tx.AgentId != expected_agent:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: Policy does not belong to your AgentId.",
                )
        elif norm_role in _FRANCHISE_ROLES_NORM:
            expected_frn = str(ctx.franchise_id or ctx.user_id)
            if str(tx.FranchiseCode or "0") != expected_frn:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: Policy does not belong to your Franchise scope.",
                )
        elif norm_role in _EMPLOYEE_ROLES_NORM:
            expected_emp = ctx.emp_id or ctx.user_id
            if tx.SalesEx_id != expected_emp and tx.LocationHeadId != expected_emp:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied: Policy is outside your Sales Executive / Hierarchy scope.",
                )

    async def _build_lifecycle_response(
        self,
        p: TransactionPayment,
        tx: Transaction,
        penalty_applied: Decimal = ZERO,
    ) -> PaymentLifecycleActionResponse:
        acc_rows = await self.booking_repo.get_account_entries_by_tx(
            tx.TransanctionId, include_deleted=False
        )
        p_resp = map_payment_instrument_response(p)
        return PaymentLifecycleActionResponse(
            payment_id=p.PaymentId,
            transaction_id=tx.TransanctionId,
            inward_no=tx.InwardNo or "",
            payment_type=p_resp.payment_type,
            status=p_resp.status or "RECEIVED",
            paid_amount=p_resp.paid_amount,
            policy_paid_amount=round_2dp(_to_decimal(tx.PaidAmount)),
            policy_outstanding_amount=round_2dp(_to_decimal(tx.OutstandingAmount)),
            policy_t_status=tx.TStatus or "Pending",
            policy_pending_status=tx.pendingStatus if tx.pendingStatus is not None else 1,
            is_cheque_clearing=tx.Ischequeclearing or 0,
            is_cheque_cleared=tx.IsChequeCleared or 0,
            cheque_bank_status=tx.ChequeBankStatus or 0,
            commission_paid=tx.CommissionPaid or 0,
            penalty_applied=round_2dp(penalty_applied),
            payment=p_resp,
            accounting_entries=[
                map_account_entry_response(a, tx.BranchId or 1) for a in acc_rows
            ],
        )

    # -----------------------------------------------------------------------
    # 1. Payment Read & List Operations
    # -----------------------------------------------------------------------

    async def get_payment(
        self,
        payment_id: int,
        current_user: User,
    ) -> PaymentInstrumentResponse:
        p = await self.repo.get_payment_by_id(payment_id, include_deleted=True)
        if p is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Payment Instrument #{payment_id} not found.",
            )
        if p.TransanctionId:
            tx = await self.booking_repo.get_transaction_by_id(
                p.TransanctionId, include_deleted=True
            )
            if tx is not None:
                self._assert_can_access_transaction(tx, current_user, for_write=False)
        return map_payment_instrument_response(p)

    async def list_payments(
        self,
        current_user: User,
        *,
        transaction_id: Optional[int] = None,
        payment_type: Optional[str] = None,
        status_filter: Optional[str] = None,
        docno: Optional[str] = None,
        include_deleted: bool = True,
        limit: int = 50,
        offset: int = 0,
    ) -> PaymentListResponse:
        ctx = self._get_principal(current_user)
        branch_filter: Optional[int] = None
        if not is_global_admin_role(ctx.role_name) and not self._is_cross_branch_read_role(ctx.role_name):
            branch_filter = ctx.branch_id or 1

        if transaction_id is not None:
            tx = await self.booking_repo.get_transaction_by_id(
                transaction_id, include_deleted=True
            )
            if tx is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Policy Transaction #{transaction_id} not found.",
                )
            self._assert_can_access_transaction(tx, current_user, for_write=False)

        total, rows = await self.repo.list_payments(
            branch_id=branch_filter,
            transaction_id=transaction_id,
            payment_type=payment_type,
            status_filter=status_filter,
            docno=docno,
            include_deleted=include_deleted,
            limit=limit,
            offset=offset,
        )
        return PaymentListResponse(
            total=total,
            limit=limit,
            offset=offset,
            items=[map_payment_instrument_response(r) for r in rows],
        )

    # -----------------------------------------------------------------------
    # 2. Cheque Lifecycle: Deposit -> Clear -> Bounce (+ Penalty)
    # -----------------------------------------------------------------------

    async def deposit_cheque(
        self,
        payment_id: int,
        payload: ChequeDepositRequest,
        current_user: User,
    ) -> PaymentLifecycleActionResponse:
        """
        Transitions a CHEQUE or DD from PENDING_CLEARANCE -> DEPOSITED.
        """
        async with _PAYMENT_WRITE_LOCK:
            try:
                p = await self.repo.get_payment_by_id(
                    payment_id, include_deleted=True, for_update=True
                )
                if p is None:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Payment Instrument #{payment_id} not found.",
                    )
                p_type = (p.PaymentType or "").strip().upper()
                if p_type not in {"CHEQUE", "DD"}:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail=f"Only CHEQUE or DD instruments can be deposited (found '{p_type}').",
                    )

                tx = await self.repo.get_transaction_for_update(
                    p.TransanctionId or 0, include_deleted=False
                )
                if tx is None:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Linked Policy Transaction #{p.TransanctionId} not found.",
                    )
                self._assert_can_access_transaction(tx, current_user, for_write=True)

                curr_state = map_payment_instrument_response(p).status
                if curr_state != "PENDING_CLEARANCE":
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=(
                            f"Invalid cheque state transition: Cheque #{payment_id} is currently "
                            f"'{curr_state}' and cannot transition to 'DEPOSITED'."
                        ),
                    )

                now_dt = datetime.utcnow()
                dep_dt = (
                    datetime.combine(payload.deposit_date, datetime.min.time())
                    if payload.deposit_date
                    else now_dt
                )
                p.Extra1 = "DEPOSITED"
                if payload.bank_reference:
                    p.Extra2 = payload.bank_reference.strip()
                if payload.remark:
                    p.PaymentDetails = payload.remark.strip()
                p.CashierApproval = 1
                p.CashierApprovalDate = dep_dt
                p.UpdateDate = now_dt
                p.UpdateUser = str(current_user.UserId)

                tx.Ischequeclearing = 1
                tx.IsChequeCleared = 0
                tx.ChequeBankStatus = 0
                tx.CheqBankDate = dep_dt
                tx.UpdateDate = now_dt
                tx.UpdateUser = str(current_user.UserId)

                await self.session.commit()
            except HTTPException:
                await self.session.rollback()
                raise
            except Exception as exc:
                await self.session.rollback()
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to deposit Cheque #{payment_id}: {exc}",
                ) from exc

        return await self._build_lifecycle_response(p, tx)

    async def clear_cheque(
        self,
        payment_id: int,
        payload: ChequeClearRequest,
        current_user: User,
    ) -> PaymentLifecycleActionResponse:
        """
        Transitions a CHEQUE or DD from PENDING_CLEARANCE / DEPOSITED -> CLEARED.
        Updates tbl_transaction (Ischequeclearing=0, IsChequeCleared=1, ChequeBankStatus=1,
        CheqBankDate) and finalizes policy TStatus='Booked' when OutstandingAmount == 0.00.
        """
        async with _PAYMENT_WRITE_LOCK:
            try:
                p = await self.repo.get_payment_by_id(
                    payment_id, include_deleted=True, for_update=True
                )
                if p is None:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Payment Instrument #{payment_id} not found.",
                    )
                p_type = (p.PaymentType or "").strip().upper()
                if p_type not in {"CHEQUE", "DD"}:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail=f"Only CHEQUE or DD instruments can be cleared (found '{p_type}').",
                    )

                tx = await self.repo.get_transaction_for_update(
                    p.TransanctionId or 0, include_deleted=False
                )
                if tx is None:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Linked Policy Transaction #{p.TransanctionId} not found.",
                    )
                self._assert_can_access_transaction(tx, current_user, for_write=True)

                curr_state = map_payment_instrument_response(p).status
                if curr_state not in {"PENDING_CLEARANCE", "DEPOSITED"}:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=(
                            f"Invalid cheque state transition: Cheque #{payment_id} is currently "
                            f"'{curr_state}' and cannot transition to 'CLEARED'."
                        ),
                    )

                now_dt = datetime.utcnow()
                clear_dt = (
                    datetime.combine(payload.clear_date, datetime.min.time())
                    if payload.clear_date
                    else now_dt
                )
                p.Extra1 = "CLEARED"
                if payload.bank_reference:
                    p.Extra2 = payload.bank_reference.strip()
                if payload.remark:
                    p.PaymentDetails = payload.remark.strip()
                p.CashierApproval = 1
                if p.CashierApprovalDate is None:
                    p.CashierApprovalDate = clear_dt
                p.AccountantApproval = 1
                p.AccountantApprovalDate = clear_dt
                p.UpdateDate = now_dt
                p.UpdateUser = str(current_user.UserId)
                await self.session.flush()

                if payload.simulate_failure_at == "AFTER_PAYMENT_UPDATE":
                    raise RuntimeError("Simulated fault AFTER_PAYMENT_UPDATE in clear_cheque")

                # Check if any other active cheque on this policy is still pending clearance
                all_active = await self.repo.get_all_payments_by_tx(
                    tx.TransanctionId, include_deleted=False
                )
                other_pending_cheques = [
                    other
                    for other in all_active
                    if other.PaymentId != p.PaymentId
                    and (other.PaymentType or "").strip().upper() in {"CHEQUE", "DD"}
                    and map_payment_instrument_response(other).status in {"PENDING_CLEARANCE", "DEPOSITED"}
                ]

                if not other_pending_cheques:
                    tx.Ischequeclearing = 0
                    tx.IsChequeCleared = 1
                    tx.ChequeBankStatus = 1
                    tx.CheqBankDate = clear_dt
                    if round_2dp(_to_decimal(tx.OutstandingAmount)) == ZERO:
                        tx.TStatus = "Booked"
                        tx.pendingStatus = 0
                        tx.RAPaymentStatus = "COMPLETE"
                        tx.IsActivePendingCash = 0

                        # Release any cheque-bounce holds on Cut & Pay and Agent Commission rows
                        cnp_rows = await self.booking_repo.get_cutnpay_by_tx(tx.TransanctionId)
                        for cnp in cnp_rows:
                            if (cnp.Flag or "").upper().startswith("HOLD"):
                                cnp.Flag = "CUTNPAY"
                        acp_rows = await self.booking_repo.get_agent_comm_payments_by_tx(tx.TransanctionId)
                        for acp in acp_rows:
                            if (acp.Narration or "").upper().startswith("HOLD:"):
                                adv_v = round_2dp(_to_decimal(acp.AdvAmt))
                                rem_v = round_2dp(_to_decimal(acp.NetAmount))
                                acp.PaymentStatus = (
                                    Decimal("1.00")
                                    if (adv_v > ZERO and rem_v == ZERO)
                                    else (Decimal("2.00") if adv_v > ZERO else ZERO)
                                )
                                acp.Narration = f"Commission Payable Active - {tx.InwardNo}"[:255]

                tx.UpdateDate = now_dt
                tx.UpdateUser = str(current_user.UserId)

                if tx.TransId and tx.TransId > 0:
                    prop = await self.booking_repo.get_proposal_by_id(tx.TransId)
                    if prop is not None:
                        prop.ChequeApprovalStatus = 1
                        prop.IsAccountApproval = 1
                        prop.UpdatedDate = now_dt
                        prop.UpdatedUser = str(current_user.UserId)

                if payload.simulate_failure_at == "BEFORE_COMMIT":
                    raise RuntimeError("Simulated fault BEFORE_COMMIT in clear_cheque")

                await self.session.commit()
            except HTTPException:
                await self.session.rollback()
                raise
            except Exception as exc:
                await self.session.rollback()
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Atomic cheque clearance rolled back: {exc}",
                ) from exc

        return await self._build_lifecycle_response(p, tx)

    async def bounce_cheque(
        self,
        payment_id: int,
        payload: ChequeBounceRequest,
        current_user: User,
    ) -> PaymentLifecycleActionResponse:
        """
        Atomically dishonors/bounces a CHEQUE or DD:
        1. Marks payment row Extra1='BOUNCED', isdeleted='1', isCompletePayment=0.
        2. Reopens tbl_transaction: PaidAmount -= C, OutstandingAmount += C + penalty_amount,
           TStatus='Pending', pendingStatus=1, ChequeBankStatus=2, CommissionPaid=0, RAPaymentStatus='BOUNCED'.
        3. Places CutNPayCommPayable & AgentCommissionPayment on hold.
        4. Posts contra reversal AccTransId=2 (-C) and optional penalty AccTransId=4 (+penalty_amount) in tbl_account.
        """
        async with _PAYMENT_WRITE_LOCK:
            try:
                p = await self.repo.get_payment_by_id(
                    payment_id, include_deleted=True, for_update=True
                )
                if p is None:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Payment Instrument #{payment_id} not found.",
                    )
                p_type = (p.PaymentType or "").strip().upper()
                if p_type not in {"CHEQUE", "DD"}:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail=f"Only CHEQUE or DD instruments can be bounced (found '{p_type}').",
                    )

                tx = await self.repo.get_transaction_for_update(
                    p.TransanctionId or 0, include_deleted=False
                )
                if tx is None:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Linked Policy Transaction #{p.TransanctionId} not found.",
                    )
                self._assert_can_access_transaction(tx, current_user, for_write=True)

                curr_state = map_payment_instrument_response(p).status
                if curr_state in {"BOUNCED", "REVERSED"}:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=(
                            f"Cheque #{payment_id} is already in terminal state '{curr_state}' "
                            f"and cannot be bounced again."
                        ),
                    )

                now_dt = datetime.utcnow()
                bounce_dt = (
                    datetime.combine(payload.bounce_date, datetime.min.time())
                    if payload.bounce_date
                    else now_dt
                )
                chq_amt = round_2dp(_to_decimal(p.PaidAmount))
                penalty_amt = round_2dp(payload.penalty_amount)

                new_paid, new_outstanding, contra_amt = calculate_cheque_bounce_effect(
                    current_paid=_to_decimal(tx.PaidAmount),
                    current_outstanding=_to_decimal(tx.OutstandingAmount),
                    cheque_amount=chq_amt,
                    penalty_amount=penalty_amt,
                )

                # 1. Update payment row to BOUNCED
                p.Extra1 = "BOUNCED"
                p.Extra2 = (
                    f"{payload.bank_reference.strip()} | {payload.bounce_reason.strip()}"
                    if payload.bank_reference
                    else f"BOUNCE:{payload.bounce_reason.strip()}"
                )[:255]
                p.isdeleted = "1"
                p.isCompletePayment = 0
                p.AccountantApproval = 2
                p.AccountantApprovalDate = bounce_dt
                p.UpdateDate = now_dt
                p.UpdateUser = str(current_user.UserId)
                await self.session.flush()

                if payload.simulate_failure_at == "AFTER_PAYMENT_BOUNCE":
                    raise RuntimeError("Simulated fault AFTER_PAYMENT_BOUNCE in bounce_cheque")

                # 2. Reopen policy transaction & hold commission
                tx.PaidAmount = new_paid
                tx.OutstandingAmount = new_outstanding
                tx.Ischequeclearing = 0
                tx.IsChequeCleared = 0
                tx.ChequeBankStatus = 2
                tx.CheqBankDate = bounce_dt
                tx.TStatus = "Pending"
                tx.pendingStatus = 1
                tx.IsActivePendingCash = 1
                tx.CommissionPaid = 0
                tx.RAPaymentStatus = "BOUNCED"
                tx.CorrectionText = f"Cheque #{p.docno} Dishonored: {payload.bounce_reason}"[:300]
                tx.UpdateDate = now_dt
                tx.UpdateUser = str(current_user.UserId)

                # Update other remaining active payment rows' isCompletePayment to 0
                active_payments = await self.repo.get_all_payments_by_tx(
                    tx.TransanctionId, include_deleted=False
                )
                for other_p in active_payments:
                    other_p.isCompletePayment = 0

                # 3. Place Cut & Pay and Agent Commission rows on hold
                cnp_rows = await self.booking_repo.get_cutnpay_by_tx(tx.TransanctionId)
                for cnp in cnp_rows:
                    cnp.Flag = "HOLD_CHEQUE_BOUNCE"

                acp_rows = await self.booking_repo.get_agent_comm_payments_by_tx(tx.TransanctionId)
                for acp in acp_rows:
                    acp.PaymentStatus = ZERO
                    acp.Narration = f"HOLD: Cheque #{p.docno} Bounced"[:255]

                if tx.TransId and tx.TransId > 0:
                    prop = await self.booking_repo.get_proposal_by_id(tx.TransId)
                    if prop is not None:
                        prop.ChequeApprovalStatus = 2
                        prop.CashStatus = "BOUNCED"
                        prop.OutstandingAmt = new_outstanding
                        prop.UpdatedDate = now_dt
                        prop.UpdatedUser = str(current_user.UserId)

                if payload.simulate_failure_at == "AFTER_TRANSACTION_REOPEN":
                    raise RuntimeError("Simulated fault AFTER_TRANSACTION_REOPEN in bounce_cheque")

                # 4. Post contra reversal entry (AccTransId = 2, -C) and optional penalty (AccTransId = 4, +penalty)
                ledger_m_id = await self.booking_repo.resolve_or_create_policy_ledger(
                    branch_id=tx.BranchId or 1,
                    actor_user_id=current_user.UserId,
                )
                reversal_acc = Account(
                    AccTransId=2,
                    AccountDate=bounce_dt,
                    LedgerMId=ledger_m_id,
                    amount=contra_amt,
                    Narration=(
                        f"Cheque Dishonor Reversal #{p.docno} ({payload.bounce_reason}) - {tx.InwardNo}"
                    )[:500],
                    ReferenceCustId=tx.CustomerId,
                    ReferenceAgentId=tx.AgentId,
                    BranchId=tx.BranchId or 1,
                    Extra1="CHEQUE_BOUNCE_REVERSAL",
                    Extra2=tx.InwardNo,
                    Doc_No=p.PaymentId,
                    CreatedUser=str(current_user.UserId),
                    CreatedDate=now_dt,
                    UpdatedUser=str(current_user.UserId),
                    UpdatedDate=now_dt,
                    PaymentType=p_type,
                    isdeleted=0,
                    IsNill=1 if tx.ND == "YES" else 0,
                    TransactionId=tx.TransanctionId,
                    CustVehId=tx.CustVehId or 0,
                    MonthId=bounce_dt.month,
                    EndorsementId=0,
                    TransId=tx.TransId or 0,
                )
                await self.booking_repo.create_account_entry(reversal_acc)

                if payload.simulate_failure_at == "DURING_ACCOUNTING":
                    raise RuntimeError("Simulated fault DURING_ACCOUNTING in bounce_cheque")

                if penalty_amt > ZERO:
                    penalty_acc = Account(
                        AccTransId=4,
                        AccountDate=bounce_dt,
                        LedgerMId=ledger_m_id,
                        amount=penalty_amt,
                        Narration=(
                            f"Cheque Dishonor Penalty Charge #{p.docno} - {tx.InwardNo}"
                        )[:500],
                        ReferenceCustId=tx.CustomerId,
                        ReferenceAgentId=tx.AgentId,
                        BranchId=tx.BranchId or 1,
                        Extra1="CHEQUE_BOUNCE_PENALTY",
                        Extra2=tx.InwardNo,
                        Doc_No=p.PaymentId,
                        CreatedUser=str(current_user.UserId),
                        CreatedDate=now_dt,
                        UpdatedUser=str(current_user.UserId),
                        UpdatedDate=now_dt,
                        PaymentType="PENALTY",
                        isdeleted=0,
                        IsNill=0,
                        TransactionId=tx.TransanctionId,
                        CustVehId=tx.CustVehId or 0,
                        MonthId=bounce_dt.month,
                        EndorsementId=0,
                        TransId=tx.TransId or 0,
                    )
                    await self.booking_repo.create_account_entry(penalty_acc)

                await self.session.commit()
            except HTTPException:
                await self.session.rollback()
                raise
            except Exception as exc:
                await self.session.rollback()
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Atomic cheque bounce rolled back: {exc}",
                ) from exc

        return await self._build_lifecycle_response(p, tx, penalty_applied=penalty_amt)

    # -----------------------------------------------------------------------
    # 3. Payment Reversal & E-Wallet Refund
    # -----------------------------------------------------------------------

    async def reverse_payment(
        self,
        payment_id: int,
        payload: PaymentReversalRequest,
        current_user: User,
    ) -> PaymentLifecycleActionResponse:
        """
        Atomically reverses an active payment instrument:
        1. Marks payment row Extra1='REVERSED', isdeleted='1', isCompletePayment=0.
        2. Updates tbl_transaction PaidAmount -= amt, OutstandingAmount += amt, TStatus='Pending'.
        3. Posts contra AccTransId=2 (-amt) in tbl_account.
        4. If PaymentType == 'EWALLET' and refund_to_wallet=True, credits partner E-Wallet (AccTransId=14).
        """
        async with _PAYMENT_WRITE_LOCK:
            try:
                p = await self.repo.get_payment_by_id(
                    payment_id, include_deleted=True, for_update=True
                )
                if p is None:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Payment Instrument #{payment_id} not found.",
                    )

                tx = await self.repo.get_transaction_for_update(
                    p.TransanctionId or 0, include_deleted=False
                )
                if tx is None:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Linked Policy Transaction #{p.TransanctionId} not found.",
                    )
                self._assert_can_access_transaction(tx, current_user, for_write=True)

                curr_state = map_payment_instrument_response(p).status
                if curr_state in {"BOUNCED", "REVERSED"} or p.isdeleted == "1":
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=(
                            f"Payment #{payment_id} is already in terminal state '{curr_state}' "
                            f"and cannot be reversed again."
                        ),
                    )

                now_dt = datetime.utcnow()
                rev_dt = (
                    datetime.combine(payload.reversal_date, datetime.min.time())
                    if payload.reversal_date
                    else now_dt
                )
                p_type = (p.PaymentType or "CASH").strip().upper()
                rev_amt = round_2dp(_to_decimal(p.PaidAmount))

                new_paid, new_outstanding, contra_amt = calculate_payment_reversal_effect(
                    current_paid=_to_decimal(tx.PaidAmount),
                    current_outstanding=_to_decimal(tx.OutstandingAmount),
                    reversed_amount=rev_amt,
                )

                p.Extra1 = "REVERSED"
                p.Extra2 = f"REV:{payload.reason.strip()}"[:255]
                p.isdeleted = "1"
                p.isCompletePayment = 0
                p.UpdateDate = now_dt
                p.UpdateUser = str(current_user.UserId)
                await self.session.flush()

                if payload.simulate_failure_at == "AFTER_PAYMENT_REVERSE":
                    raise RuntimeError("Simulated fault AFTER_PAYMENT_REVERSE in reverse_payment")

                tx.PaidAmount = new_paid
                tx.OutstandingAmount = new_outstanding
                if new_outstanding > ZERO:
                    tx.TStatus = "Pending"
                    tx.pendingStatus = 1
                    tx.IsActivePendingCash = 1
                    tx.RAPaymentStatus = "PENDING"
                    tx.CommissionPaid = 0
                if p_type == "EWALLET":
                    tx.EWalletAmountUsed = max(
                        ZERO, round_2dp(_to_decimal(tx.EWalletAmountUsed) - rev_amt)
                    )
                tx.UpdateDate = now_dt
                tx.UpdateUser = str(current_user.UserId)

                active_payments = await self.repo.get_all_payments_by_tx(
                    tx.TransanctionId, include_deleted=False
                )
                for other_p in active_payments:
                    if new_outstanding > ZERO:
                        other_p.isCompletePayment = 0

                ledger_m_id = await self.booking_repo.resolve_or_create_policy_ledger(
                    branch_id=tx.BranchId or 1,
                    actor_user_id=current_user.UserId,
                )
                rev_acc = Account(
                    AccTransId=2,
                    AccountDate=rev_dt,
                    LedgerMId=ledger_m_id,
                    amount=contra_amt,
                    Narration=f"Payment Reversal ({payload.reason}) - {tx.InwardNo}"[:500],
                    ReferenceCustId=tx.CustomerId,
                    ReferenceAgentId=tx.AgentId,
                    BranchId=tx.BranchId or 1,
                    Extra1="PAYMENT_REVERSAL",
                    Extra2=tx.InwardNo,
                    Doc_No=p.PaymentId,
                    CreatedUser=str(current_user.UserId),
                    CreatedDate=now_dt,
                    UpdatedUser=str(current_user.UserId),
                    UpdatedDate=now_dt,
                    PaymentType=p_type,
                    isdeleted=0,
                    IsNill=1 if tx.ND == "YES" else 0,
                    TransactionId=tx.TransanctionId,
                    CustVehId=tx.CustVehId or 0,
                    MonthId=rev_dt.month,
                    EndorsementId=0,
                    TransId=tx.TransId or 0,
                )
                await self.booking_repo.create_account_entry(rev_acc)

                if payload.simulate_failure_at == "DURING_ACCOUNTING":
                    raise RuntimeError("Simulated fault DURING_ACCOUNTING in reverse_payment")

                if p_type == "EWALLET" and payload.refund_to_wallet:
                    frn_id = (
                        int(tx.FranchiseCode)
                        if (tx.FranchiseCode and tx.FranchiseCode.isdigit())
                        else 0
                    )
                    w_type = payload.wallet_owner_type or (
                        "FRANCHISE" if (frn_id > 0 and not tx.AgentId) else "AGENT"
                    )
                    w_id = payload.wallet_owner_id or (
                        tx.AgentId if w_type == "AGENT" else frn_id
                    )
                    if w_id and w_id > 0:
                        await self.wallet_service.refund_wallet_in_session(
                            owner_type=w_type,
                            owner_id=w_id,
                            amount=rev_amt,
                            branch_id=tx.BranchId or 1,
                            actor_user_id=current_user.UserId,
                            transaction_id=tx.TransanctionId,
                            narration=f"E-Wallet Refund on Payment #{p.PaymentId} Reversal - {tx.InwardNo}",
                        )

                await self.session.commit()
            except HTTPException:
                await self.session.rollback()
                raise
            except Exception as exc:
                await self.session.rollback()
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Atomic payment reversal rolled back: {exc}",
                ) from exc

        return await self._build_lifecycle_response(p, tx)

    # -----------------------------------------------------------------------
    # 4. Insurer Payment & Brokerage Reconciliation
    # -----------------------------------------------------------------------

    def _map_reconciliation_response(
        self,
        tx: Transaction,
        acc_entry: Optional[Account] = None,
    ) -> ReconciliationMatchResponse:
        final_prem = round_2dp(_to_decimal(tx.Amount))
        net_prem = round_2dp(_to_decimal(tx.NetPermium))
        booked_gross = round_2dp(_to_decimal(tx.AgentCommAmt))
        booked_net = round_2dp(_to_decimal(tx.NetCommission))
        rcon_grid = round_2dp(_to_decimal(tx.RconGrid))
        rcon_comm = round_2dp(_to_decimal(tx.RconComm))
        variance = round_2dp(rcon_comm - booked_gross) if tx.IsRconDataMatch in (1, 2) else ZERO

        if tx.IsRconDataMatch == 1:
            m_status: Literal["UNRECONCILED", "MATCHED", "PARTIAL_VARIANCE"] = "MATCHED"
        elif tx.IsRconDataMatch == 2:
            m_status = "PARTIAL_VARIANCE"
        else:
            m_status = "UNRECONCILED"

        return ReconciliationMatchResponse(
            transaction_id=tx.TransanctionId,
            inward_no=tx.InwardNo or "",
            policy_no=tx.PolicyNo,
            insurance_company_id=tx.InsuranceCompanyId or 1,
            branch_id=tx.BranchId or 1,
            is_rcon_data_match=tx.IsRconDataMatch or 0,
            match_status=m_status,
            final_premium=final_prem,
            net_premium=net_prem,
            booked_gross_commission=booked_gross,
            booked_net_commission=booked_net,
            reconciled_grid_percent=rcon_grid,
            reconciled_comm_amount=rcon_comm,
            commission_variance=variance,
            company_submission_doc_no=tx.CompSubmitionDocNo,
            company_cheque_no=tx.CompanyChequeNo,
            is_company_cheque=tx.IsCompanyChequeNo or 0,
            online_payment_to_company=round_2dp(Decimal(str(tx.OnlinePaymentToCompany or 0))),
            ib_doc_no=tx.IB_Doc_No,
            ib_payment_date=tx.IB_PaymentDate,
            ib_receipt_status=tx.IB_ReceiptStatus or 0,
            ib_payment_by=tx.IB_PaymentBy,
            accounting_period=tx.accounting_period,
            accounting_entry=(
                map_account_entry_response(acc_entry, tx.BranchId or 1)
                if acc_entry is not None
                else None
            ),
        )

    async def reconcile_policy(
        self,
        transaction_id: int,
        payload: ReconciliationMatchRequest,
        current_user: User,
    ) -> ReconciliationMatchResponse:
        """
        Reconciles insurer remittance and brokerage statement against tbl_transaction
        and posts an AccTransId=5 ('INSURER_RECONCILIATION') voucher in tbl_account.
        """
        async with _PAYMENT_WRITE_LOCK:
            try:
                tx = await self.repo.get_transaction_for_update(
                    transaction_id, include_deleted=False
                )
                if tx is None:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Policy Transaction #{transaction_id} not found.",
                    )
                self._assert_can_access_transaction(tx, current_user, for_write=True)

                # Idempotency / duplicate full-match guard
                if tx.IsRconDataMatch == 1 and payload.ib_doc_no is not None and tx.IB_Doc_No == payload.ib_doc_no:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=(
                            f"Policy Transaction #{transaction_id} is already reconciled under "
                            f"IB_Doc_No #{payload.ib_doc_no}."
                        ),
                    )

                net_prem = round_2dp(_to_decimal(tx.NetPermium))
                booked_gross = round_2dp(_to_decimal(tx.AgentCommAmt))

                eff_grid, eff_comm, variance, match_flag, _ = evaluate_reconciliation_match(
                    net_premium=net_prem,
                    booked_gross_comm=booked_gross,
                    reconciled_grid_percent=payload.reconciled_grid_percent,
                    reconciled_comm_amount=payload.reconciled_comm_amount,
                    allow_partial_match=payload.allow_partial_match,
                )

                now_dt = datetime.utcnow()
                ib_dt = (
                    datetime.combine(payload.ib_payment_date, datetime.min.time())
                    if payload.ib_payment_date
                    else now_dt
                )
                acc_period_dt = (
                    datetime.combine(payload.accounting_period, datetime.min.time())
                    if payload.accounting_period
                    else ib_dt
                )

                tx.IsRconDataMatch = match_flag
                tx.RconGrid = eff_grid
                tx.RconComm = eff_comm
                if payload.company_submission_doc_no is not None:
                    tx.CompSubmitionDocNo = payload.company_submission_doc_no.strip()
                if payload.company_cheque_no is not None:
                    tx.CompanyChequeNo = payload.company_cheque_no.strip()
                tx.IsCompanyChequeNo = 1 if (payload.is_company_cheque or payload.company_cheque_no) else 0
                if payload.online_payment_to_company is not None:
                    tx.OnlinePaymentToCompany = int(round_rupee(payload.online_payment_to_company))
                if payload.online_to_company_date is not None:
                    tx.OnlineToCompanyDate = datetime.combine(
                        payload.online_to_company_date, datetime.min.time()
                    )
                if payload.ib_doc_no is not None:
                    tx.IB_Doc_No = payload.ib_doc_no
                tx.IB_PaymentDate = ib_dt
                tx.IB_ReceiptStatus = payload.ib_receipt_status if match_flag == 1 else 2
                tx.IB_PaymentBy = payload.ib_payment_by
                tx.accounting_period = acc_period_dt
                if payload.remark:
                    tx.UpdateEntryRemark = payload.remark.strip()
                tx.UpdateDate = now_dt
                tx.UpdateUser = str(current_user.UserId)
                await self.session.flush()

                if payload.simulate_failure_at == "AFTER_TX_UPDATE":
                    raise RuntimeError("Simulated fault AFTER_TX_UPDATE in reconcile_policy")

                ledger_m_id = await self.booking_repo.resolve_or_create_policy_ledger(
                    branch_id=tx.BranchId or 1,
                    actor_user_id=current_user.UserId,
                )
                rcon_acc = Account(
                    AccTransId=5,
                    AccountDate=ib_dt,
                    LedgerMId=ledger_m_id,
                    amount=eff_comm,
                    Narration=(
                        f"Insurer Reconciliation Match ({'FULL' if match_flag == 1 else 'VARIANCE'}) "
                        f"- {tx.InwardNo} (Variance: {variance})"
                    )[:500],
                    ReferenceCustId=tx.CustomerId,
                    ReferenceAgentId=tx.AgentId,
                    BranchId=tx.BranchId or 1,
                    Extra1="INSURER_RECONCILIATION",
                    Extra2=payload.company_submission_doc_no or tx.InwardNo,
                    Doc_No=payload.ib_doc_no or tx.TransanctionId,
                    CreatedUser=str(current_user.UserId),
                    CreatedDate=now_dt,
                    UpdatedUser=str(current_user.UserId),
                    UpdatedDate=now_dt,
                    PaymentType=payload.ib_payment_by or "INSURER_RECON",
                    isdeleted=0,
                    IsNill=1 if tx.ND == "YES" else 0,
                    TransactionId=tx.TransanctionId,
                    CustVehId=tx.CustVehId or 0,
                    MonthId=acc_period_dt.month,
                    EndorsementId=0,
                    TransId=tx.TransId or 0,
                )
                await self.booking_repo.create_account_entry(rcon_acc)

                if payload.simulate_failure_at == "BEFORE_COMMIT":
                    raise RuntimeError("Simulated fault BEFORE_COMMIT in reconcile_policy")

                await self.session.commit()
            except HTTPException:
                await self.session.rollback()
                raise
            except Exception as exc:
                await self.session.rollback()
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Atomic insurer reconciliation rolled back: {exc}",
                ) from exc

        return self._map_reconciliation_response(tx, rcon_acc)

    async def get_policy_reconciliation(
        self,
        transaction_id: int,
        current_user: User,
    ) -> ReconciliationMatchResponse:
        tx = await self.booking_repo.get_transaction_by_id(
            transaction_id, include_deleted=False
        )
        if tx is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Policy Transaction #{transaction_id} not found.",
            )
        self._assert_can_access_transaction(tx, current_user, for_write=False)
        acc_rows = await self.booking_repo.get_account_entries_by_tx(
            transaction_id, include_deleted=False
        )
        rcon_entries = [a for a in acc_rows if a.AccTransId == 5]
        latest_rcon = rcon_entries[-1] if rcon_entries else None
        return self._map_reconciliation_response(tx, latest_rcon)

    async def list_reconciliations(
        self,
        current_user: User,
        *,
        insurance_company_id: Optional[int] = None,
        is_rcon_data_match: Optional[int] = None,
        ib_receipt_status: Optional[int] = None,
        policy_no: Optional[str] = None,
        inward_no: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> ReconciliationListResponse:
        ctx = self._get_principal(current_user)
        branch_filter: Optional[int] = None
        if not is_global_admin_role(ctx.role_name) and not self._is_cross_branch_read_role(ctx.role_name):
            branch_filter = ctx.branch_id or 1

        total, rows = await self.repo.list_reconciliation_transactions(
            branch_id=branch_filter,
            insurance_company_id=insurance_company_id,
            is_rcon_data_match=is_rcon_data_match,
            ib_receipt_status=ib_receipt_status,
            policy_no=policy_no,
            inward_no=inward_no,
            limit=limit,
            offset=offset,
        )
        return ReconciliationListResponse(
            total=total,
            limit=limit,
            offset=offset,
            items=[self._map_reconciliation_response(r) for r in rows],
        )
