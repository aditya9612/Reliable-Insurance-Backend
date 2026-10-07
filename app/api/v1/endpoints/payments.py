"""
FastAPI v1 Endpoints for Phase 8 Payments, Cheques, Reconciliation & E-Wallet Engine.
Exposes 3 routers:
- payments_router (mounted at /api/v1/payments)
- reconciliation_router (mounted at /api/v1/reconciliation)
- wallets_router (mounted at /api/v1/wallets)
"""
from typing import Literal, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db, require_roles
from app.core.rbac import (
    PAYMENT_BOUNCE_REVERSAL_ROLES,
    PAYMENT_CLEARANCE_ROLES,
    PAYMENT_READ_ROLES,
    RECONCILIATION_READ_ROLES,
    RECONCILIATION_WRITE_ROLES,
    WALLET_ADMIN_WRITE_ROLES,
    WALLET_PARTNER_ROLES,
)
from app.models.user import User
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
)
from app.schemas.policy import PaymentInstrumentResponse
from app.services.payment_engine import PaymentEngineService, WalletService


payments_router = APIRouter()
reconciliation_router = APIRouter()
wallets_router = APIRouter()


# ===========================================================================
# 1. Payment & Cheque Lifecycle Endpoints (/api/v1/payments)
# ===========================================================================


@payments_router.get(
    "",
    response_model=PaymentListResponse,
    status_code=status.HTTP_200_OK,
    summary="List and filter policy payment instruments",
    description="Lists payment instruments in tbl_transactionpayment with branch and principal scoping.",
)
async def list_payments(
    transaction_id: Optional[int] = Query(None, description="Filter by TransanctionId"),
    payment_type: Optional[str] = Query(None, description="Filter by PaymentType (e.g. CHEQUE, CASH, UPI)"),
    status_filter: Optional[str] = Query(
        None,
        alias="status",
        description="Filter by lifecycle status (RECEIVED, PENDING_CLEARANCE, DEPOSITED, CLEARED, BOUNCED, REVERSED)",
    ),
    docno: Optional[str] = Query(None, description="Filter by Cheque/DD/UTR docno"),
    include_deleted: bool = Query(True, description="Include bounced/reversed instruments"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_roles(*PAYMENT_READ_ROLES)),
    session: AsyncSession = Depends(get_db),
) -> PaymentListResponse:
    service = PaymentEngineService(session)
    return await service.list_payments(
        current_user=current_user,
        transaction_id=transaction_id,
        payment_type=payment_type,
        status_filter=status_filter,
        docno=docno,
        include_deleted=include_deleted,
        limit=limit,
        offset=offset,
    )


@payments_router.get(
    "/{payment_id}",
    response_model=PaymentInstrumentResponse,
    status_code=status.HTTP_200_OK,
    summary="Get payment instrument by PaymentId",
)
async def get_payment(
    payment_id: int,
    current_user: User = Depends(require_roles(*PAYMENT_READ_ROLES)),
    session: AsyncSession = Depends(get_db),
) -> PaymentInstrumentResponse:
    service = PaymentEngineService(session)
    return await service.get_payment(payment_id, current_user)


@payments_router.post(
    "/{payment_id}/deposit",
    response_model=PaymentLifecycleActionResponse,
    status_code=status.HTTP_200_OK,
    summary="Mark a CHEQUE or DD payment instrument as DEPOSITED in bank",
)
async def deposit_cheque(
    payment_id: int,
    payload: ChequeDepositRequest,
    current_user: User = Depends(require_roles(*PAYMENT_CLEARANCE_ROLES)),
    session: AsyncSession = Depends(get_db),
) -> PaymentLifecycleActionResponse:
    service = PaymentEngineService(session)
    return await service.deposit_cheque(payment_id, payload, current_user)


@payments_router.post(
    "/{payment_id}/clear",
    response_model=PaymentLifecycleActionResponse,
    status_code=status.HTTP_200_OK,
    summary="Clear a CHEQUE or DD payment instrument and finalize policy booking state",
)
async def clear_cheque(
    payment_id: int,
    payload: ChequeClearRequest,
    current_user: User = Depends(require_roles(*PAYMENT_CLEARANCE_ROLES)),
    session: AsyncSession = Depends(get_db),
) -> PaymentLifecycleActionResponse:
    service = PaymentEngineService(session)
    return await service.clear_cheque(payment_id, payload, current_user)


@payments_router.post(
    "/{payment_id}/bounce",
    response_model=PaymentLifecycleActionResponse,
    status_code=status.HTTP_200_OK,
    summary="Mark a CHEQUE or DD as BOUNCED, apply optional penalty, reopen policy balance, and hold commission",
)
async def bounce_cheque(
    payment_id: int,
    payload: ChequeBounceRequest,
    current_user: User = Depends(require_roles(*PAYMENT_BOUNCE_REVERSAL_ROLES)),
    session: AsyncSession = Depends(get_db),
) -> PaymentLifecycleActionResponse:
    service = PaymentEngineService(session)
    return await service.bounce_cheque(payment_id, payload, current_user)


@payments_router.post(
    "/{payment_id}/reverse",
    response_model=PaymentLifecycleActionResponse,
    status_code=status.HTTP_200_OK,
    summary="Reverse an active payment instrument, reopen policy balance, and post contra ledger entry",
)
async def reverse_payment(
    payment_id: int,
    payload: PaymentReversalRequest,
    current_user: User = Depends(require_roles(*PAYMENT_BOUNCE_REVERSAL_ROLES)),
    session: AsyncSession = Depends(get_db),
) -> PaymentLifecycleActionResponse:
    service = PaymentEngineService(session)
    return await service.reverse_payment(payment_id, payload, current_user)


# ===========================================================================
# 2. Insurer Payment & Brokerage Reconciliation Endpoints (/api/v1/reconciliation)
# ===========================================================================


@reconciliation_router.get(
    "/policies",
    response_model=ReconciliationListResponse,
    status_code=status.HTTP_200_OK,
    summary="List policies for insurer payment & brokerage reconciliation",
)
async def list_reconciliations(
    insurance_company_id: Optional[int] = Query(None),
    is_rcon_data_match: Optional[int] = Query(
        None,
        description="0 = Unreconciled, 1 = Full Match, 2 = Partial/Variance",
    ),
    ib_receipt_status: Optional[int] = Query(None),
    policy_no: Optional[str] = Query(None),
    inward_no: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_roles(*RECONCILIATION_READ_ROLES)),
    session: AsyncSession = Depends(get_db),
) -> ReconciliationListResponse:
    service = PaymentEngineService(session)
    return await service.list_reconciliations(
        current_user=current_user,
        insurance_company_id=insurance_company_id,
        is_rcon_data_match=is_rcon_data_match,
        ib_receipt_status=ib_receipt_status,
        policy_no=policy_no,
        inward_no=inward_no,
        limit=limit,
        offset=offset,
    )


@reconciliation_router.get(
    "/policies/{transaction_id}",
    response_model=ReconciliationMatchResponse,
    status_code=status.HTTP_200_OK,
    summary="Get insurer reconciliation status for a policy transaction",
)
async def get_policy_reconciliation(
    transaction_id: int,
    current_user: User = Depends(require_roles(*RECONCILIATION_READ_ROLES)),
    session: AsyncSession = Depends(get_db),
) -> ReconciliationMatchResponse:
    service = PaymentEngineService(session)
    return await service.get_policy_reconciliation(transaction_id, current_user)


@reconciliation_router.post(
    "/policies/{transaction_id}/match",
    response_model=ReconciliationMatchResponse,
    status_code=status.HTTP_200_OK,
    summary="Execute insurer payment & brokerage reconciliation match on a policy",
)
async def reconcile_policy(
    transaction_id: int,
    payload: ReconciliationMatchRequest,
    current_user: User = Depends(require_roles(*RECONCILIATION_WRITE_ROLES)),
    session: AsyncSession = Depends(get_db),
) -> ReconciliationMatchResponse:
    service = PaymentEngineService(session)
    return await service.reconcile_policy(transaction_id, payload, current_user)


# ===========================================================================
# 3. Partner E-Wallet & Lock / Release Endpoints (/api/v1/wallets)
# ===========================================================================


@wallets_router.get(
    "/{owner_type}/{owner_id}",
    response_model=WalletBalanceResponse,
    status_code=status.HTTP_200_OK,
    summary="Get partner E-Wallet settled, locked, and available balances",
)
async def get_wallet_balance(
    owner_type: Literal["AGENT", "FRANCHISE"],
    owner_id: int,
    current_user: User = Depends(require_roles(*WALLET_PARTNER_ROLES)),
    session: AsyncSession = Depends(get_db),
) -> WalletBalanceResponse:
    service = WalletService(session)
    return await service.get_wallet_balance(owner_type, owner_id, current_user)


@wallets_router.get(
    "/{owner_type}/{owner_id}/transactions",
    response_model=WalletLedgerListResponse,
    status_code=status.HTTP_200_OK,
    summary="List partner E-Wallet ledger statement",
)
async def list_wallet_transactions(
    owner_type: Literal["AGENT", "FRANCHISE"],
    owner_id: int,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_roles(*WALLET_PARTNER_ROLES)),
    session: AsyncSession = Depends(get_db),
) -> WalletLedgerListResponse:
    service = WalletService(session)
    return await service.list_wallet_transactions(
        owner_type=owner_type,
        owner_id=owner_id,
        current_user=current_user,
        limit=limit,
        offset=offset,
    )


@wallets_router.post(
    "/topup",
    response_model=WalletOperationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Credit / top-up a partner E-Wallet sub-ledger",
)
async def topup_wallet(
    payload: WalletTopupRequest,
    current_user: User = Depends(require_roles(*WALLET_ADMIN_WRITE_ROLES)),
    session: AsyncSession = Depends(get_db),
) -> WalletOperationResponse:
    service = WalletService(session)
    return await service.topup_wallet(payload, current_user)


@wallets_router.post(
    "/lock",
    response_model=WalletOperationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Reserve / lock funds in a partner E-Wallet for a proposal or policy booking",
)
async def lock_wallet_funds(
    payload: WalletLockRequest,
    current_user: User = Depends(require_roles(*WALLET_PARTNER_ROLES)),
    session: AsyncSession = Depends(get_db),
) -> WalletOperationResponse:
    service = WalletService(session)
    return await service.lock_wallet_funds(payload, current_user)


@wallets_router.post(
    "/release",
    response_model=WalletOperationResponse,
    status_code=status.HTTP_200_OK,
    summary="Release an active E-Wallet lock back to available balance",
)
async def release_wallet_lock(
    payload: WalletReleaseRequest,
    current_user: User = Depends(require_roles(*WALLET_PARTNER_ROLES)),
    session: AsyncSession = Depends(get_db),
) -> WalletOperationResponse:
    service = WalletService(session)
    return await service.release_wallet_lock(payload, current_user)


@wallets_router.post(
    "/debit",
    response_model=WalletOperationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Debit partner E-Wallet or consume an active E-Wallet lock",
)
async def debit_wallet_funds(
    payload: WalletDebitRequest,
    current_user: User = Depends(require_roles(*WALLET_PARTNER_ROLES)),
    session: AsyncSession = Depends(get_db),
) -> WalletOperationResponse:
    service = WalletService(session)
    return await service.debit_wallet_funds(payload, current_user)
