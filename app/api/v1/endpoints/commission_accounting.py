"""
FastAPI v1 Endpoints for Phase 9 — Commission & Accounting Engine.

Exposes 3 routers (18 endpoints total):
1. `commissions_router` (mounted at `/api/v1/commissions`):
   - `POST /api/v1/commissions/preview`
   - `POST /api/v1/commissions/calculate`
   - `GET  /api/v1/commissions`
   - `GET  /api/v1/commissions/payables`
   - `GET  /api/v1/commissions/{transaction_id}`
   - `POST /api/v1/commissions/{transaction_id}/approve`
2. `commission_payouts_router` (mounted at `/api/v1/commission-payouts`):
   - `POST /api/v1/commission-payouts`
   - `GET  /api/v1/commission-payouts`
   - `GET  /api/v1/commission-payouts/{payout_id}`
   - `POST /api/v1/commission-payouts/{payout_id}/reverse`
3. `accounting_router` (mounted at `/api/v1/accounting`):
   - `POST /api/v1/accounting/ledgers`
   - `GET  /api/v1/accounting/ledgers`
   - `GET  /api/v1/accounting/ledgers/{ledger_m_id}/entries`
   - `GET  /api/v1/accounting/trial-balance`
   - `POST /api/v1/accounting/vouchers`
   - `GET  /api/v1/accounting/vouchers`
   - `GET  /api/v1/accounting/vouchers/{doc_no}`
   - `POST /api/v1/accounting/vouchers/{doc_no}/reverse`
"""
from datetime import date
from typing import Literal, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db, require_roles
from app.core.rbac import (
    ACCOUNTING_READ_ROLES,
    ACCOUNTING_VOUCHER_WRITE_ROLES,
    COMMISSION_APPROVAL_ROLES,
    COMMISSION_CALCULATE_ROLES,
    COMMISSION_PAYOUT_WRITE_ROLES,
    COMMISSION_READ_ROLES,
    TRIAL_BALANCE_READ_ROLES,
)
from app.models.user import User
from app.schemas.commission_accounting import (
    CommissionApprovalRequest,
    CommissionCalculateRequest,
    CommissionPayableListResponse,
    CommissionPayoutCreateRequest,
    CommissionPayoutListResponse,
    CommissionPayoutResponse,
    CommissionPayoutReverseRequest,
    CommissionPreviewRequest,
    CommissionPreviewResponse,
    LedgerMasterCreateRequest,
    LedgerMasterListResponse,
    LedgerMasterResponse,
    LedgerStatementResponse,
    PolicyCommissionListResponse,
    PolicyCommissionRecordResponse,
    TrialBalanceResponse,
    VoucherCreateRequest,
    VoucherListResponse,
    VoucherResponse,
    VoucherReverseRequest,
)
from app.services.commission_accounting import CommissionAccountingService


commissions_router = APIRouter()
commission_payouts_router = APIRouter()
accounting_router = APIRouter()


# ===========================================================================
# 1. Commission Preview, Calculation, Payable Queue & Approval (/api/v1/commissions)
# ===========================================================================


@commissions_router.post(
    "/preview",
    response_model=CommissionPreviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Stateless commission, TDS, Cut & Pay, and Franchise spread preview",
    description="Computes Agent OD/Net/Extra commission, TDS, Cut & Pay deduction, and Franchise spread without mutating the database.",
)
async def preview_commission(
    payload: CommissionPreviewRequest,
    current_user: User = Depends(require_roles(*COMMISSION_CALCULATE_ROLES)),
    session: AsyncSession = Depends(get_db),
) -> CommissionPreviewResponse:
    service = CommissionAccountingService(session)
    return await service.preview_commission(payload, current_user)


@commissions_router.post(
    "/calculate",
    response_model=PolicyCommissionRecordResponse,
    status_code=status.HTTP_200_OK,
    summary="Evaluate or recalculate commission rows for a booked policy",
    description="Evaluates or updates tbl_agentcommissionpayment and tbl_franchisecommission for a policy prior to payout.",
)
async def calculate_policy_commission(
    payload: CommissionCalculateRequest,
    current_user: User = Depends(require_roles(*COMMISSION_CALCULATE_ROLES)),
    session: AsyncSession = Depends(get_db),
) -> PolicyCommissionRecordResponse:
    service = CommissionAccountingService(session)
    return await service.calculate_or_sync_policy_commission(payload, current_user)


@commissions_router.get(
    "",
    response_model=PolicyCommissionListResponse,
    status_code=status.HTTP_200_OK,
    summary="List policy commission records",
    description="Lists policy commission records with server-side principal and branch scoping.",
)
async def list_commissions(
    agent_id: Optional[int] = Query(None, description="Filter by AgentId"),
    franchise_id: Optional[int] = Query(None, description="Filter by FranchiseId"),
    policy_no: Optional[str] = Query(None, description="Filter by PolicyNo"),
    inward_no: Optional[str] = Query(None, description="Filter by InwardNo"),
    commission_paid: Optional[int] = Query(None, description="Filter by CommissionPaid flag (0 or 1)"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_roles(*COMMISSION_READ_ROLES)),
    session: AsyncSession = Depends(get_db),
) -> PolicyCommissionListResponse:
    service = CommissionAccountingService(session)
    return await service.list_commissions(
        current_user,
        agent_id=agent_id,
        franchise_id=franchise_id,
        policy_no=policy_no,
        inward_no=inward_no,
        commission_paid=commission_paid,
        limit=limit,
        offset=offset,
    )


@commissions_router.get(
    "/payables",
    response_model=CommissionPayableListResponse,
    status_code=status.HTTP_200_OK,
    summary="List unpaid Agent and Franchise commission payables",
    description="Returns unpaid commission payables with payout eligibility evaluation.",
)
async def list_commission_payables(
    partner_type: Optional[Literal["AGENT", "FRANCHISE"]] = Query(
        None, description="Filter by AGENT or FRANCHISE"
    ),
    partner_id: Optional[int] = Query(None, description="Filter by AgentId or FranchiseId"),
    only_eligible: bool = Query(False, description="Only return policies eligible for immediate payout"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_roles(*COMMISSION_READ_ROLES)),
    session: AsyncSession = Depends(get_db),
) -> CommissionPayableListResponse:
    service = CommissionAccountingService(session)
    return await service.list_commission_payables(
        current_user,
        partner_type=partner_type,
        partner_id=partner_id,
        only_eligible=only_eligible,
        limit=limit,
        offset=offset,
    )


@commissions_router.get(
    "/{transaction_id}",
    response_model=PolicyCommissionRecordResponse,
    status_code=status.HTTP_200_OK,
    summary="Get policy commission breakdown and payout eligibility by TransactionId",
)
async def get_policy_commission(
    transaction_id: int,
    current_user: User = Depends(require_roles(*COMMISSION_READ_ROLES)),
    session: AsyncSession = Depends(get_db),
) -> PolicyCommissionRecordResponse:
    service = CommissionAccountingService(session)
    return await service.get_policy_commission(transaction_id, current_user)


@commissions_router.post(
    "/{transaction_id}/approve",
    response_model=PolicyCommissionRecordResponse,
    status_code=status.HTTP_200_OK,
    summary="Approve a policy's unpaid commission payable for disbursement",
)
async def approve_policy_commission(
    transaction_id: int,
    payload: CommissionApprovalRequest,
    current_user: User = Depends(require_roles(*COMMISSION_APPROVAL_ROLES)),
    session: AsyncSession = Depends(get_db),
) -> PolicyCommissionRecordResponse:
    service = CommissionAccountingService(session)
    return await service.approve_policy_commission(
        transaction_id, payload, current_user
    )


# ===========================================================================
# 2. Commission Payout & Payout Reversal (/api/v1/commission-payouts)
# ===========================================================================


@commission_payouts_router.post(
    "",
    response_model=CommissionPayoutResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Execute an atomic Agent or Franchise commission payout",
    description="Disburses eligible commission payables under InnoDB row locks and posts a balanced double-entry payout voucher (AccTransId = 6).",
)
async def create_commission_payout(
    payload: CommissionPayoutCreateRequest,
    current_user: User = Depends(require_roles(*COMMISSION_PAYOUT_WRITE_ROLES)),
    session: AsyncSession = Depends(get_db),
) -> CommissionPayoutResponse:
    service = CommissionAccountingService(session)
    return await service.create_commission_payout(payload, current_user)


@commission_payouts_router.get(
    "",
    response_model=CommissionPayoutListResponse,
    status_code=status.HTTP_200_OK,
    summary="List commission payouts",
)
async def list_commission_payouts(
    partner_type: Optional[Literal["AGENT", "FRANCHISE"]] = Query(None),
    partner_id: Optional[int] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_roles(*COMMISSION_READ_ROLES)),
    session: AsyncSession = Depends(get_db),
) -> CommissionPayoutListResponse:
    service = CommissionAccountingService(session)
    return await service.list_commission_payouts(
        current_user,
        partner_type=partner_type,
        partner_id=partner_id,
        limit=limit,
        offset=offset,
    )


@commission_payouts_router.get(
    "/{payout_id}",
    response_model=CommissionPayoutResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a commission payout by payout_id (Doc_No)",
)
async def get_commission_payout(
    payout_id: int,
    current_user: User = Depends(require_roles(*COMMISSION_READ_ROLES)),
    session: AsyncSession = Depends(get_db),
) -> CommissionPayoutResponse:
    service = CommissionAccountingService(session)
    return await service.get_commission_payout(payout_id, current_user)


@commission_payouts_router.post(
    "/{payout_id}/reverse",
    response_model=CommissionPayoutResponse,
    status_code=status.HTTP_200_OK,
    summary="Atomically reverse a commission payout and restore policy commission payables",
)
async def reverse_commission_payout(
    payout_id: int,
    payload: CommissionPayoutReverseRequest,
    current_user: User = Depends(require_roles(*COMMISSION_PAYOUT_WRITE_ROLES)),
    session: AsyncSession = Depends(get_db),
) -> CommissionPayoutResponse:
    service = CommissionAccountingService(session)
    return await service.reverse_commission_payout(payout_id, payload, current_user)


# ===========================================================================
# 3. Master Ledgers, Statements, Vouchers & Trial Balance (/api/v1/accounting)
# ===========================================================================


@accounting_router.post(
    "/ledgers",
    response_model=LedgerMasterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a Chart of Accounts / Master Ledger entry in tbl_ledgermaster",
)
async def create_ledger(
    payload: LedgerMasterCreateRequest,
    current_user: User = Depends(require_roles(*ACCOUNTING_VOUCHER_WRITE_ROLES)),
    session: AsyncSession = Depends(get_db),
) -> LedgerMasterResponse:
    service = CommissionAccountingService(session)
    return await service.create_ledger(payload, current_user)


@accounting_router.get(
    "/ledgers",
    response_model=LedgerMasterListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Chart of Accounts / Master Ledgers with closing balances",
)
async def list_ledgers(
    branch_id: Optional[int] = Query(None),
    ledger_type_id: Optional[int] = Query(None, ge=1, le=5),
    ledger_group_id: Optional[int] = Query(None, ge=1),
    reference_id: Optional[int] = Query(None, ge=0),
    search: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_roles(*ACCOUNTING_READ_ROLES)),
    session: AsyncSession = Depends(get_db),
) -> LedgerMasterListResponse:
    service = CommissionAccountingService(session)
    return await service.list_ledgers(
        current_user,
        branch_id=branch_id,
        ledger_type_id=ledger_type_id,
        ledger_group_id=ledger_group_id,
        reference_id=reference_id,
        search=search,
        limit=limit,
        offset=offset,
    )


@accounting_router.get(
    "/ledgers/{ledger_m_id}/entries",
    response_model=LedgerStatementResponse,
    status_code=status.HTTP_200_OK,
    summary="Get chronological running-balance ledger statement from tbl_account",
)
async def get_ledger_statement(
    ledger_m_id: int,
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    current_user: User = Depends(require_roles(*ACCOUNTING_READ_ROLES)),
    session: AsyncSession = Depends(get_db),
) -> LedgerStatementResponse:
    service = CommissionAccountingService(session)
    return await service.get_ledger_statement(
        ledger_m_id,
        current_user,
        from_date=from_date,
        to_date=to_date,
    )


@accounting_router.get(
    "/trial-balance",
    response_model=TrialBalanceResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate branch or global Trial Balance report",
    description="Aggregates tbl_account and tbl_ledgermaster and verifies total_debit == total_credit (variance == 0.00).",
)
async def get_trial_balance(
    branch_id: Optional[int] = Query(None),
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    current_user: User = Depends(require_roles(*TRIAL_BALANCE_READ_ROLES)),
    session: AsyncSession = Depends(get_db),
) -> TrialBalanceResponse:
    service = CommissionAccountingService(session)
    return await service.get_trial_balance(
        current_user,
        branch_id=branch_id,
        from_date=from_date,
        to_date=to_date,
    )


@accounting_router.post(
    "/vouchers",
    response_model=VoucherResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a balanced Double-Entry Accounting Voucher in tbl_account",
)
async def create_voucher(
    payload: VoucherCreateRequest,
    current_user: User = Depends(require_roles(*ACCOUNTING_VOUCHER_WRITE_ROLES)),
    session: AsyncSession = Depends(get_db),
) -> VoucherResponse:
    service = CommissionAccountingService(session)
    return await service.create_voucher(payload, current_user)


@accounting_router.get(
    "/vouchers",
    response_model=VoucherListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Double-Entry Accounting Vouchers",
)
async def list_vouchers(
    branch_id: Optional[int] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_roles(*ACCOUNTING_READ_ROLES)),
    session: AsyncSession = Depends(get_db),
) -> VoucherListResponse:
    service = CommissionAccountingService(session)
    return await service.list_vouchers(
        current_user,
        branch_id=branch_id,
        limit=limit,
        offset=offset,
    )


@accounting_router.get(
    "/vouchers/{doc_no}",
    response_model=VoucherResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a Double-Entry Accounting Voucher by Doc_No",
)
async def get_voucher(
    doc_no: int,
    current_user: User = Depends(require_roles(*ACCOUNTING_READ_ROLES)),
    session: AsyncSession = Depends(get_db),
) -> VoucherResponse:
    service = CommissionAccountingService(session)
    return await service.get_voucher(doc_no, current_user)


@accounting_router.post(
    "/vouchers/{doc_no}/reverse",
    response_model=VoucherResponse,
    status_code=status.HTTP_200_OK,
    summary="Atomically reverse a Double-Entry Accounting Voucher",
)
async def reverse_voucher(
    doc_no: int,
    payload: VoucherReverseRequest,
    current_user: User = Depends(require_roles(*ACCOUNTING_VOUCHER_WRITE_ROLES)),
    session: AsyncSession = Depends(get_db),
) -> VoucherResponse:
    service = CommissionAccountingService(session)
    return await service.reverse_voucher(doc_no, payload, current_user)
