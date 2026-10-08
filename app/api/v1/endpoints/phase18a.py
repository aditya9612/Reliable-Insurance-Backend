"""
FastAPI Routers for Phase 18A — Complete Remaining Legacy Feature Implementation.
Exposes all 10 SHOULD and 7 ENHANCE legacy business capabilities under their canonical
domain route prefixes (/documents, /batch-tasks, /commission-payouts, /commissions,
/payments, /accounting, /reports, /inspections, /admin, /renewals, /quotations, /agents, /integrations).
"""
from datetime import date
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, File, Form, Path, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db, get_current_user, require_roles
from app.models.user import User
from app.schemas.phase18a import (
    PolicyExtractionUploadResponse,
    PolicyExtractionPrefillResponse,
    PolicyExtractionLinkTransactionRequest,
    PolicyExtractionLinkTransactionResponse,
    PendingCashLockRequest,
    PendingCashLockResponse,
    PendingAppTransactionLockRequest,
    PendingAppTransactionLockResponse,
    OperatorLockStatusResponse,
    IdealPaymentReceiptBulkRequest,
    IdealPaymentReceiptResponse,
    IdealPaymentReceiptBulkResult,
    InstaPayRequestCreate,
    CommissionRateGridCreateRequest,
    CommissionRateGridResponse,
    RelianceCappingEvaluateRequest,
    RelianceCappingEvaluateResponse,
    RemainingPendingCashCreateRequest,
    RemainingPendingCashApproveRequest,
    RemainingPendingCashResponse,
    SalesRegistrationCreateRequest,
    SalesRegistrationAdvanceAdjustRequest,
    SalesRegistrationResponse,
    InstaPayAuthoritySummaryResponse,
    InstaPayAuthorityDispatchRequest,
    InspectionRequestCreate,
    InspectionCoordinatorDecisionRequest,
    InspectionRequestResponse,
    SupportTicketCreateRequest,
    SupportTicketRemarkRequest,
    SupportTicketStatusUpdateRequest,
    SupportTicketResponse,
    CallingLeadBulkImportRequest,
    CallingLeadAssignRequest,
    CallingLeadDispositionRequest,
    CallingLeadResponse,
    RequestedQuotationFileCreateRequest,
    RequestedQuotationFileResponse,
    CashbackCreateRequest,
    CashbackResponse,
    SalesTargetCreateRequest,
    SalesTargetUpdateRequest,
    SalesTargetResponse,
    SubAgentCreateRequest,
    SubAgentSplitCalculateRequest,
    SubAgentSplitCalculateResponse,
    GeoCheckInRequest,
    GeoCheckInResponse,
    OfficeExpenseVoucherCreateRequest,
    OfficeExpenseVoucherResponse,
)
from app.services.phase18a_service import Phase18AService

documents_p18a_router = APIRouter()
batch_tasks_p18a_router = APIRouter()
commission_payouts_p18a_router = APIRouter()
commissions_p18a_router = APIRouter()
payments_p18a_router = APIRouter()
accounting_p18a_router = APIRouter()
reports_p18a_router = APIRouter()
inspections_p18a_router = APIRouter()
admin_p18a_router = APIRouter()
renewals_p18a_router = APIRouter()
quotations_p18a_router = APIRouter()
agents_p18a_router = APIRouter()
integrations_p18a_router = APIRouter()

FINANCE_AND_ADMIN_ROLES = (
    "OWNER",
    "ADMIN",
    "IT SUPPORT",
    "ACCOUNT",
    "ACCOUNT HEAD",
    "CASHIER",
)
BACKOFFICE_WRITE_ROLES = (
    "OWNER",
    "ADMIN",
    "IT SUPPORT",
    "ACCOUNT",
    "ACCOUNT HEAD",
    "CASHIER",
    "OPERATOR",
    "OPERATOR HEAD",
    "SUPERVISOR",
    "MANAGER",
)


# ==============================================================================
# F-17B-083: Outbound HiCaliber Policy PDF Upload & Transaction Pre-Fill
# ==============================================================================
@documents_p18a_router.post(
    "/policy-extraction/upload",
    response_model=PolicyExtractionUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload Policy PDF for HiCaliber Async OCR Extraction & Staging",
)
async def upload_policy_for_extraction(
    file: UploadFile = File(...),
    transaction_id: Optional[int] = Form(default=None),
    policy_no_hint: Optional[str] = Form(default=None),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> PolicyExtractionUploadResponse:
    service = Phase18AService(session)
    return await service.upload_and_extract_policy_pdf(
        file=file,
        current_user=current_user,
        transaction_id=transaction_id,
        policy_no_hint=policy_no_hint,
    )


@documents_p18a_router.get(
    "/policy-extraction/{identifier}/prefill",
    response_model=PolicyExtractionPrefillResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Extracted Policy Pre-Fill Payload & Duplicate Policy Check",
)
async def get_policy_extraction_prefill(
    identifier: str = Path(..., min_length=1),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> PolicyExtractionPrefillResponse:
    service = Phase18AService(session)
    return await service.get_policy_extraction_prefill(identifier)


@documents_p18a_router.post(
    "/policy-extraction/{calliber_policy_id}/link-transaction",
    response_model=PolicyExtractionLinkTransactionResponse,
    status_code=status.HTTP_200_OK,
    summary="Link Extracted Calliber Policy Record to Issued Transaction",
)
async def link_policy_extraction_to_transaction(
    payload: PolicyExtractionLinkTransactionRequest,
    calliber_policy_id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> PolicyExtractionLinkTransactionResponse:
    service = Phase18AService(session)
    return await service.link_extraction_to_transaction(
        calliber_policy_id=calliber_policy_id,
        transaction_id=payload.transaction_id,
        current_user=current_user,
    )


# ==============================================================================
# F-17B-084: Extended Operator Lockouts (Pending Cash & Pending App Trans)
# ==============================================================================
@batch_tasks_p18a_router.post(
    "/enforce-pending-cash-locks",
    response_model=PendingCashLockResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_roles(*FINANCE_AND_ADMIN_ROLES))],
    summary="Enforce Pending Cash Operator Lockout (Mumbai 3-Day / Default 2-Day Window)",
)
async def enforce_pending_cash_locks(
    payload: PendingCashLockRequest = PendingCashLockRequest(),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> PendingCashLockResponse:
    service = Phase18AService(session)
    return await service.enforce_pending_cash_locks(payload)


@batch_tasks_p18a_router.post(
    "/enforce-pending-app-transaction-locks",
    response_model=PendingAppTransactionLockResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_roles(*BACKOFFICE_WRITE_ROLES))],
    summary="Enforce Unapproved App Transaction Operator Lockout",
)
async def enforce_pending_app_transaction_locks(
    payload: PendingAppTransactionLockRequest = PendingAppTransactionLockRequest(),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> PendingAppTransactionLockResponse:
    service = Phase18AService(session)
    return await service.enforce_pending_app_transaction_locks(payload)


@batch_tasks_p18a_router.get(
    "/operator-lock-status",
    response_model=OperatorLockStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Combined Operator Compliance Lock Status",
)
async def get_operator_lock_status(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> OperatorLockStatusResponse:
    service = Phase18AService(session)
    return await service.get_operator_lock_status(current_user)


# ==============================================================================
# F-17B-085: Bulk Ideal / Broker Payment Receipt & Multi-Agent Settlement
# ==============================================================================
@commission_payouts_p18a_router.post(
    "/ideal-payment-receipts/bulk",
    response_model=IdealPaymentReceiptBulkResult,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(*FINANCE_AND_ADMIN_ROLES))],
    summary="Bulk Process Ideal / Broker Payment Receipts & Settle Agent Commissions",
)
async def create_bulk_ideal_payment_receipts(
    payload: IdealPaymentReceiptBulkRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> IdealPaymentReceiptBulkResult:
    service = Phase18AService(session)
    return await service.process_bulk_ideal_payment_receipts(payload.receipts, current_user)


@commission_payouts_p18a_router.get(
    "/ideal-payment-receipts",
    response_model=List[IdealPaymentReceiptResponse],
    status_code=status.HTTP_200_OK,
    summary="List Ideal / Broker Payment Receipts",
)
async def list_ideal_payment_receipts(
    posp_id: Optional[int] = Query(default=None, ge=1),
    receipt_type: Optional[str] = Query(default=None),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> List[IdealPaymentReceiptResponse]:
    service = Phase18AService(session)
    return await service.list_ideal_payment_receipts(posp_id=posp_id, receipt_type=receipt_type)


@commission_payouts_p18a_router.post(
    "/instapay/requests",
    response_model=IdealPaymentReceiptResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit Instant Commission Payout (InstaPay) Request",
)
async def create_instapay_request(
    payload: InstaPayRequestCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> IdealPaymentReceiptResponse:
    service = Phase18AService(session)
    return await service.create_instapay_request(payload, current_user)


# ==============================================================================
# F-17B-086 & F-17B-095: Commission Rate Grids, Reliance Capping & Cashbacks
# ==============================================================================
@commissions_p18a_router.post(
    "/grids",
    response_model=CommissionRateGridResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(*BACKOFFICE_WRITE_ROLES))],
    summary="Create Partner Commission Rate Grid Entry",
)
async def create_commission_rate_grid(
    payload: CommissionRateGridCreateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> CommissionRateGridResponse:
    service = Phase18AService(session)
    return await service.create_commission_rate_grid(payload, current_user)


@commissions_p18a_router.post(
    "/grids/import-csv",
    response_model=List[CommissionRateGridResponse],
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(*FINANCE_AND_ADMIN_ROLES))],
    summary="Bulk Import Partner Commission Rate Grids via CSV",
)
async def import_commission_grids_csv(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> List[CommissionRateGridResponse]:
    service = Phase18AService(session)
    return await service.import_commission_grids_csv(file, current_user)


@commissions_p18a_router.get(
    "/grids/lookup",
    response_model=List[CommissionRateGridResponse],
    status_code=status.HTTP_200_OK,
    summary="Lookup Applicable Partner Commission Rate Grids",
)
async def lookup_commission_rate_grids(
    insurance_company_id: Optional[int] = Query(default=None, ge=1),
    grid_scope: Optional[str] = Query(default=None),
    vehi_type_id: Optional[int] = Query(default=None, ge=1),
    broker_id: Optional[int] = Query(default=None, ge=1),
    franchise_id: Optional[int] = Query(default=None, ge=1),
    agent_id: Optional[int] = Query(default=None, ge=1),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> List[CommissionRateGridResponse]:
    service = Phase18AService(session)
    return await service.lookup_commission_rate_grids(
        insurance_company_id=insurance_company_id,
        grid_scope=grid_scope,
        vehi_type_id=vehi_type_id,
        broker_id=broker_id,
        franchise_id=franchise_id,
        agent_id=agent_id,
    )


@commissions_p18a_router.post(
    "/capping/reliance-evaluate",
    response_model=RelianceCappingEvaluateResponse,
    status_code=status.HTTP_200_OK,
    summary="Evaluate Reliance 90% Total Capping & 60% Max OD Discount Rule",
)
async def evaluate_reliance_capping(
    payload: RelianceCappingEvaluateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> RelianceCappingEvaluateResponse:
    service = Phase18AService(session)
    return service.evaluate_reliance_capping(payload)


@commissions_p18a_router.post(
    "/cashbacks",
    response_model=CashbackResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(*BACKOFFICE_WRITE_ROLES))],
    summary="Create Promotional Cashback Entry",
)
async def create_cashback_entry(
    payload: CashbackCreateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> CashbackResponse:
    service = Phase18AService(session)
    return await service.create_cashback_entry(payload, current_user)


@commissions_p18a_router.get(
    "/cashbacks",
    response_model=List[CashbackResponse],
    status_code=status.HTTP_200_OK,
    summary="List Promotional Cashback Entries",
)
async def list_cashback_entries(
    transaction_id: Optional[int] = Query(default=None, ge=1),
    agent_id: Optional[int] = Query(default=None, ge=1),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> List[CashbackResponse]:
    service = Phase18AService(session)
    return await service.list_cashback_entries(transaction_id=transaction_id, agent_id=agent_id)


# ==============================================================================
# F-17B-087: Remaining / Shortfall Cash Premium Ledger & Cashier Approval
# ==============================================================================
@payments_p18a_router.post(
    "/remaining-cash",
    response_model=RemainingPendingCashResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record Remaining / Shortfall Cash Premium Entry",
)
async def create_remaining_pending_cash(
    payload: RemainingPendingCashCreateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> RemainingPendingCashResponse:
    service = Phase18AService(session)
    return await service.create_remaining_pending_cash(payload, current_user)


@payments_p18a_router.get(
    "/remaining-cash",
    response_model=List[RemainingPendingCashResponse],
    status_code=status.HTTP_200_OK,
    summary="List Remaining / Shortfall Cash Premium Entries",
)
async def list_remaining_pending_cash(
    branch_id: Optional[int] = Query(default=None, ge=1),
    cashier_approval: Optional[int] = Query(default=None, ge=0, le=2),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> List[RemainingPendingCashResponse]:
    service = Phase18AService(session)
    return await service.list_remaining_pending_cash(
        branch_id=branch_id, cashier_approval=cashier_approval
    )


@payments_p18a_router.post(
    "/remaining-cash/{pending_cash_id}/approve",
    response_model=RemainingPendingCashResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_roles(*FINANCE_AND_ADMIN_ROLES))],
    summary="Cashier Approval / Settlement of Remaining Shortfall Cash Entry",
)
async def approve_remaining_pending_cash(
    payload: RemainingPendingCashApproveRequest,
    pending_cash_id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> RemainingPendingCashResponse:
    service = Phase18AService(session)
    return await service.approve_remaining_pending_cash(
        pending_cash_id=pending_cash_id, payload=payload, current_user=current_user
    )


# ==============================================================================
# F-17B-088 & F-17B-099: B2B Sales Registration & Petty Office Expense Vouchers
# ==============================================================================
@accounting_p18a_router.post(
    "/sales-registrations",
    response_model=SalesRegistrationResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(*FINANCE_AND_ADMIN_ROLES))],
    summary="Create Insurer B2B Sales Invoice Registration",
)
async def create_sales_registration(
    payload: SalesRegistrationCreateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> SalesRegistrationResponse:
    service = Phase18AService(session)
    return await service.create_sales_registration(payload, current_user)


@accounting_p18a_router.get(
    "/sales-registrations",
    response_model=List[SalesRegistrationResponse],
    status_code=status.HTTP_200_OK,
    summary="List Insurer B2B Sales Invoice Registrations",
)
async def list_sales_registrations(
    client_master_id: Optional[int] = Query(default=None, ge=1),
    invoice_no: Optional[str] = Query(default=None),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> List[SalesRegistrationResponse]:
    service = Phase18AService(session)
    return await service.list_sales_registrations(
        client_master_id=client_master_id, invoice_no=invoice_no
    )


@accounting_p18a_router.post(
    "/sales-registrations/{sales_reg_id}/adjust-advance",
    response_model=SalesRegistrationResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_roles(*FINANCE_AND_ADMIN_ROLES))],
    summary="Adjust Insurer B2B Sales Invoice against Company Advance Master",
)
async def adjust_sales_registration_advance(
    payload: SalesRegistrationAdvanceAdjustRequest,
    sales_reg_id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> SalesRegistrationResponse:
    service = Phase18AService(session)
    return await service.adjust_sales_registration_advance(
        sales_reg_id=sales_reg_id, payload=payload, current_user=current_user
    )


@accounting_p18a_router.post(
    "/office-expenses",
    response_model=OfficeExpenseVoucherResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(*BACKOFFICE_WRITE_ROLES))],
    summary="Record Petty Office Expense / Stationary Voucher",
)
async def create_office_expense_voucher(
    payload: OfficeExpenseVoucherCreateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> OfficeExpenseVoucherResponse:
    service = Phase18AService(session)
    return await service.create_office_expense_voucher(payload, current_user)


@accounting_p18a_router.get(
    "/office-expenses",
    response_model=List[OfficeExpenseVoucherResponse],
    status_code=status.HTTP_200_OK,
    summary="List Petty Office Expense / Stationary Vouchers",
)
async def list_office_expense_vouchers(
    branch_id: Optional[int] = Query(default=None, ge=1),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> List[OfficeExpenseVoucherResponse]:
    service = Phase18AService(session)
    return await service.list_office_expense_vouchers(branch_id=branch_id)


# ==============================================================================
# F-17B-090 & F-17B-096: Daily InstaPay Authority Summary & Sales Target CRUD
# ==============================================================================
@reports_p18a_router.get(
    "/operations/instapay-authority-summary",
    response_model=InstaPayAuthoritySummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Daily InstaPay Authority Summary Report (NEWSUMMERY, FROMRA, ONLINETORA)",
)
async def get_instapay_authority_summary(
    report_date: Optional[date] = Query(default=None),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> InstaPayAuthoritySummaryResponse:
    service = Phase18AService(session)
    return await service.get_instapay_authority_summary(report_date)


@reports_p18a_router.post(
    "/operations/instapay-authority-summary/dispatch",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_roles(*FINANCE_AND_ADMIN_ROLES))],
    summary="Dispatch Daily InstaPay Authority Summary Email with PDF Attachment",
)
async def dispatch_instapay_authority_summary(
    payload: InstaPayAuthorityDispatchRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = Phase18AService(session)
    return await service.dispatch_instapay_authority_summary(payload)


@reports_p18a_router.post(
    "/targets",
    response_model=SalesTargetResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(*BACKOFFICE_WRITE_ROLES))],
    summary="Create Monthly Employee / Sales Executive Quota Target",
)
async def create_sales_target(
    payload: SalesTargetCreateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> SalesTargetResponse:
    service = Phase18AService(session)
    return await service.create_sales_target(payload, current_user)


@reports_p18a_router.put(
    "/targets/{target_id}",
    response_model=SalesTargetResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_roles(*BACKOFFICE_WRITE_ROLES))],
    summary="Update Sales Target & Achieved Contest Performance",
)
async def update_sales_target(
    payload: SalesTargetUpdateRequest,
    target_id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> SalesTargetResponse:
    service = Phase18AService(session)
    return await service.update_sales_target(target_id, payload, current_user)


@reports_p18a_router.get(
    "/targets",
    response_model=List[SalesTargetResponse],
    status_code=status.HTTP_200_OK,
    summary="List Sales Targets & Contest Achievement Tiers",
)
async def list_sales_targets(
    emp_id: Optional[int] = Query(default=None, ge=1),
    financial_year: Optional[str] = Query(default=None),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> List[SalesTargetResponse]:
    service = Phase18AService(session)
    return await service.list_sales_targets(emp_id=emp_id, financial_year=financial_year)


# ==============================================================================
# F-17B-091: Vehicle Break-In Inspection Coordinator Request Queue
# ==============================================================================
@inspections_p18a_router.post(
    "",
    response_model=InspectionRequestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit Vehicle Break-In Inspection Request",
)
async def create_inspection_request(
    payload: InspectionRequestCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> InspectionRequestResponse:
    service = Phase18AService(session)
    return await service.create_inspection_request(payload, current_user)


@inspections_p18a_router.get(
    "",
    response_model=List[InspectionRequestResponse],
    status_code=status.HTTP_200_OK,
    summary="List Vehicle Break-In Inspection Coordinator Queue",
)
async def list_inspection_requests(
    status_filter: Optional[str] = Query(default=None, alias="status"),
    branch_id: Optional[int] = Query(default=None, ge=1),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> List[InspectionRequestResponse]:
    service = Phase18AService(session)
    return await service.list_inspection_requests(status_filter=status_filter, branch_id=branch_id)


@inspections_p18a_router.get(
    "/pending-count",
    status_code=status.HTTP_200_OK,
    summary="Get Pending Vehicle Break-In Inspection Notification Count",
)
async def get_pending_inspection_count(
    branch_id: Optional[int] = Query(default=None, ge=1),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, int]:
    service = Phase18AService(session)
    return await service.get_pending_inspection_count(branch_id=branch_id)


@inspections_p18a_router.post(
    "/{inspection_id}/decision",
    response_model=InspectionRequestResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_roles(*BACKOFFICE_WRITE_ROLES))],
    summary="Coordinator Approve / Reject / Request Documents on Break-In Inspection",
)
async def decide_inspection_request(
    payload: InspectionCoordinatorDecisionRequest,
    inspection_id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> InspectionRequestResponse:
    service = Phase18AService(session)
    return await service.decide_inspection_request(inspection_id, payload, current_user)


# ==============================================================================
# F-17B-092: Internal IT / Operator / Admin Support Ticketing Portal
# ==============================================================================
@admin_p18a_router.get(
    "/support-tickets/types",
    status_code=status.HTTP_200_OK,
    summary="List Support Ticket Categories",
)
async def list_support_ticket_types(
    current_user: User = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    return [
        {"support_type_id": 1, "support_type": "IT_TECHNICAL"},
        {"support_type_id": 2, "support_type": "POLICY_CORRECTION"},
        {"support_type_id": 3, "support_type": "COMMISSION_QUERY"},
        {"support_type_id": 4, "support_type": "PORTAL_ACCESS"},
    ]


@admin_p18a_router.post(
    "/support-tickets",
    response_model=SupportTicketResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Internal Support Ticket",
)
async def create_support_ticket(
    payload: SupportTicketCreateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> SupportTicketResponse:
    service = Phase18AService(session)
    return await service.create_support_ticket(payload, current_user)


@admin_p18a_router.get(
    "/support-tickets",
    response_model=List[SupportTicketResponse],
    status_code=status.HTTP_200_OK,
    summary="List Internal Support Tickets",
)
async def list_support_tickets(
    status_filter: Optional[str] = Query(default=None, alias="status"),
    user_id: Optional[int] = Query(default=None, ge=1),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> List[SupportTicketResponse]:
    service = Phase18AService(session)
    return await service.list_support_tickets(status_filter=status_filter, user_id=user_id)


@admin_p18a_router.get(
    "/support-tickets/counts",
    status_code=status.HTTP_200_OK,
    summary="Get Support Ticket Role Badge Counts (Admin / IT / Operator)",
)
async def get_support_ticket_counts(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, int]:
    service = Phase18AService(session)
    return await service.get_support_ticket_counts()


@admin_p18a_router.post(
    "/support-tickets/{support_id}/remarks",
    response_model=SupportTicketResponse,
    status_code=status.HTTP_200_OK,
    summary="Add Threaded Remark to Support Ticket",
)
async def add_support_ticket_remark(
    payload: SupportTicketRemarkRequest,
    support_id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> SupportTicketResponse:
    service = Phase18AService(session)
    return await service.add_support_ticket_remark(support_id, payload, current_user)


@admin_p18a_router.patch(
    "/support-tickets/{support_id}/status",
    response_model=SupportTicketResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_roles(*BACKOFFICE_WRITE_ROLES))],
    summary="Attend, Approve or Resolve Internal Support Ticket",
)
async def update_support_ticket_status(
    payload: SupportTicketStatusUpdateRequest,
    support_id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> SupportTicketResponse:
    service = Phase18AService(session)
    return await service.update_support_ticket_status(support_id, payload, current_user)


# ==============================================================================
# F-17B-093: Telecalling Lead Import, Call Disposition & Follow-Up CRM
# ==============================================================================
@renewals_p18a_router.get(
    "/telecalling/statuses",
    status_code=status.HTTP_200_OK,
    summary="List Telecalling Disposition Statuses",
)
async def list_telecalling_statuses(
    current_user: User = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    return [
        {"calling_status_id": 1, "status_name": "NEW"},
        {"calling_status_id": 2, "status_name": "INTERESTED_CALLBACK"},
        {"calling_status_id": 3, "status_name": "QUOTATION_SHARED"},
        {"calling_status_id": 4, "status_name": "CONVERTED"},
        {"calling_status_id": 5, "status_name": "NOT_INTERESTED"},
        {"calling_status_id": 6, "status_name": "RINGING_NO_RESPONSE"},
    ]


@renewals_p18a_router.post(
    "/telecalling/leads/import",
    response_model=List[CallingLeadResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Bulk Import RTO / Telecalling Leads",
)
async def import_telecalling_leads(
    payload: CallingLeadBulkImportRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> List[CallingLeadResponse]:
    service = Phase18AService(session)
    return await service.import_calling_leads(payload.leads, current_user)


@renewals_p18a_router.get(
    "/telecalling/leads",
    response_model=List[CallingLeadResponse],
    status_code=status.HTTP_200_OK,
    summary="List Telecalling Leads by Queue Mode (Refresh, FollowUp, FollowUpToday, FollowUpPrev)",
)
async def list_telecalling_leads(
    mode: str = Query(
        default="Refresh",
        pattern="^(Refresh|FollowUp|FollowUpToday|FollowUpPrev)$",
    ),
    assigned_user_id: Optional[int] = Query(default=None, ge=1),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> List[CallingLeadResponse]:
    service = Phase18AService(session)
    return await service.list_calling_leads(mode=mode, assigned_user_id=assigned_user_id)


@renewals_p18a_router.post(
    "/telecalling/leads/{calling_import_id}/assign",
    response_model=CallingLeadResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_roles(*BACKOFFICE_WRITE_ROLES))],
    summary="Assign Telecalling Lead to Executive / Telecaller",
)
async def assign_telecalling_lead(
    payload: CallingLeadAssignRequest,
    calling_import_id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> CallingLeadResponse:
    service = Phase18AService(session)
    return await service.assign_calling_lead(calling_import_id, payload.assigned_user_id)


@renewals_p18a_router.post(
    "/telecalling/leads/{calling_import_id}/dispositions",
    response_model=CallingLeadResponse,
    status_code=status.HTTP_200_OK,
    summary="Record Call Disposition & Next Follow-Up Date on Telecalling Lead",
)
async def record_telecalling_disposition(
    payload: CallingLeadDispositionRequest,
    calling_import_id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> CallingLeadResponse:
    service = Phase18AService(session)
    return await service.record_calling_disposition(calling_import_id, payload, current_user)


# ==============================================================================
# F-17B-094: Multi-Insurer Quotation Request & PDF File Sharing Workflow
# ==============================================================================
@quotations_p18a_router.post(
    "/requests/{quotation_id}/requested-files",
    response_model=RequestedQuotationFileResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Attach Insurer Quotation PDF File to Quotation Request (tbl_app_requestedquotationfile)",
)
async def attach_requested_quotation_file(
    payload: RequestedQuotationFileCreateRequest,
    quotation_id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> RequestedQuotationFileResponse:
    service = Phase18AService(session)
    return await service.attach_requested_quotation_file(quotation_id, payload, current_user)


@quotations_p18a_router.get(
    "/requests/{quotation_id}/requested-files",
    response_model=List[RequestedQuotationFileResponse],
    status_code=status.HTTP_200_OK,
    summary="List Attached Insurer Quotation PDF Files for Quotation Request",
)
async def list_requested_quotation_files(
    quotation_id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> List[RequestedQuotationFileResponse]:
    service = Phase18AService(session)
    return await service.list_requested_quotation_files(quotation_id, current_user)


# ==============================================================================
# F-17B-097: Sub-Agent Secondary Hierarchy & Split Payout
# ==============================================================================
@agents_p18a_router.post(
    "/{agent_id}/sub-agents",
    status_code=status.HTTP_201_CREATED,
    summary="Create Sub-Agent under Parent POSP Agent with Split Commission Percentage",
)
async def create_sub_agent(
    payload: SubAgentCreateRequest,
    agent_id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = Phase18AService(session)
    return await service.create_sub_agent(agent_id, payload, current_user)


@agents_p18a_router.get(
    "/{agent_id}/sub-agents",
    status_code=status.HTTP_200_OK,
    summary="List Sub-Agents under Parent POSP Agent",
)
async def list_sub_agents(
    agent_id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> List[Dict[str, Any]]:
    service = Phase18AService(session)
    return await service.list_sub_agents(agent_id, current_user)


@agents_p18a_router.post(
    "/{agent_id}/sub-agents/calculate-split",
    response_model=SubAgentSplitCalculateResponse,
    status_code=status.HTTP_200_OK,
    summary="Calculate Commission Split Payout Between Parent Agent and Sub-Agent",
)
async def calculate_sub_agent_split(
    payload: SubAgentSplitCalculateRequest,
    agent_id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> SubAgentSplitCalculateResponse:
    service = Phase18AService(session)
    return await service.calculate_sub_agent_split(agent_id, payload, current_user)


# ==============================================================================
# F-17B-098: Field Executive / Agent GPS Check-In & Reverse Geocoding
# ==============================================================================
@integrations_p18a_router.post(
    "/geo/check-in",
    response_model=GeoCheckInResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record Field Visit GPS Check-In & Resolve Reverse Geocoded Address",
)
async def record_geo_check_in(
    payload: GeoCheckInRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> GeoCheckInResponse:
    service = Phase18AService(session)
    return await service.record_geo_check_in(payload, current_user)


@integrations_p18a_router.get(
    "/geo/check-ins",
    response_model=List[GeoCheckInResponse],
    status_code=status.HTTP_200_OK,
    summary="List Field Executive / Agent GPS Check-Ins",
)
async def list_geo_check_ins(
    user_id: Optional[int] = Query(default=None, ge=1),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> List[GeoCheckInResponse]:
    service = Phase18AService(session)
    return await service.list_geo_check_ins(user_id=user_id)
