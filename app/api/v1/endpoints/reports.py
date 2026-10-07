"""
Reports Endpoints for Phase 14 — Blocks B, C, D, E, F, G.
Provides:
- MIS Transaction Reports & Gated Exports (CSV, XLSX)
- POSP Agent Invoicing, Generation & PDF Retrieval
- Accounting, Ledger Statements, TDS 194H Register & Vouchers
- Operations Reconciliations (Commission & Bank Uncleared)
- Endorsements & Claims Operational Pipeline Reports
- Targets (Telecaller & Executive) and Expiring Renewals
"""
from datetime import date
from typing import Optional, Literal, List, Dict, Any
from fastapi import APIRouter, Depends, Query, Path, status, HTTPException, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.dependencies import get_current_principal, require_roles
from app.core.rbac import PrincipalContext, is_global_read_role
from app.services.report_service import ReportService
from app.schemas.report import (
    # MIS
    PagedTransactionReportResponse,
    # POSP Invoices
    PospInvoiceCreateRequest,
    PospInvoiceDetailResponse,
    PagedPospInvoiceResponse,
    PagedAgentPayoutReconciliationResponse,
    # Accounting & Statutory
    TdsRegisterResponse,
    LedgerTypeSummaryItem,
    LedgerStatementResponse,
    VoucherDetailResponse,
    PaymentAdviceResponse,
    BankCommissionStatementResponse,
    DailyCollectionAuditResponse,
    # Operations
    CommissionReconcileResponse,
    BankReconcileResponse,
    PagedEndorsementReportResponse,
    PagedClaimsReportResponse,
    # Targets & Renewals
    TelecallerTargetResponse,
    ExecutiveTargetResponse,
    ExpiringPoliciesResponse,
)

router = APIRouter()


# ============================================================================
# 1. MIS Transactions & Gated Exports
# ============================================================================

@router.get(
    "/mis/transactions",
    response_model=PagedTransactionReportResponse,
    status_code=status.HTTP_200_OK,
    summary="MIS Transaction Report — Multi-Tenant Row-Scoped with Masking",
)
async def get_mis_transactions(
    from_date: Optional[date] = Query(None, description="Start date filter"),
    to_date: Optional[date] = Query(None, description="End date filter"),
    policy_no: Optional[str] = Query(None, description="Exact or partial policy number"),
    vehicle_no: Optional[str] = Query(None, description="Vehicle registration number"),
    payment_mode: Optional[str] = Query(None, description="Payment mode e.g. CASH, CHEQUE, ONLINE"),
    company_id: Optional[int] = Query(None, description="Insurance company ID"),
    broker: Optional[str] = Query(None, description="Broker entity name"),
    branch_id: Optional[int] = Query(None, description="Branch ID (gated for non-admins)"),
    skip: int = Query(0, ge=0, description="Offset for pagination"),
    limit: int = Query(50, ge=1, le=500, description="Page limit"),
    principal: PrincipalContext = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db),
) -> PagedTransactionReportResponse:
    service = ReportService(session)
    data = await service.get_mis_transactions(
        principal=principal,
        from_date=from_date,
        to_date=to_date,
        policy_no=policy_no,
        vehicle_no=vehicle_no,
        payment_mode=payment_mode,
        company_id=company_id,
        broker=broker,
        branch_id=branch_id,
        skip=skip,
        limit=limit,
    )
    return PagedTransactionReportResponse(**data)


@router.get(
    "/mis/transactions/export",
    summary="MIS Transaction Export — Strictly Gated to Admin/Accounts (CSV/XLSX)",
    dependencies=[Depends(require_roles("OWNER", "ADMIN", "IT SUPPORT", "ACCOUNT", "ACCOUNT HEAD"))],
)
async def export_mis_transactions(
    export_format: Literal["xlsx", "csv"] = Query("xlsx", alias="format", description="Export format: xlsx or csv"),
    from_date: Optional[date] = Query(None, description="Start date filter"),
    to_date: Optional[date] = Query(None, description="End date filter"),
    broker: Optional[str] = Query(None, description="Broker entity filter"),
    branch_id: Optional[int] = Query(None, description="Branch ID filter"),
    principal: PrincipalContext = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db),
):
    service = ReportService(session)
    content, filename, media_type = await service.export_mis_transactions(
        principal=principal,
        export_format=export_format,
        from_date=from_date,
        to_date=to_date,
        broker=broker,
        branch_id=branch_id,
    )

    if export_format.lower() == "csv":
        return StreamingResponse(
            content,
            media_type=media_type,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    else:
        return Response(
            content=content,
            media_type=media_type,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )


# ============================================================================
# 2. POSP Invoicing & Payout Reconciliation
# ============================================================================

@router.get(
    "/posp-invoices",
    response_model=PagedPospInvoiceResponse,
    status_code=status.HTTP_200_OK,
    summary="List POSP Agent Invoices — Scoped to Self for Agents",
)
async def get_posp_invoices(
    financial_year: Optional[str] = Query(None, description="e.g. 2025-2026"),
    month: Optional[str] = Query(None, description="e.g. APRIL, MAY"),
    agent_id: Optional[int] = Query(None, description="Agent ID filter"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    principal: PrincipalContext = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db),
) -> PagedPospInvoiceResponse:
    service = ReportService(session)
    data = await service.get_posp_invoices(
        financial_year=financial_year,
        month=month,
        agent_id=agent_id,
        skip=skip,
        limit=limit,
        principal=principal,
    )
    return PagedPospInvoiceResponse(**data)


@router.post(
    "/posp-invoices/generate",
    response_model=PospInvoiceDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate POSP Payout Invoice with Tax Logic & PDF Rendering",
    dependencies=[Depends(require_roles("OWNER", "ADMIN", "ACCOUNT", "ACCOUNT HEAD"))],
)
async def generate_posp_invoice(
    request: PospInvoiceCreateRequest,
    principal: PrincipalContext = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db),
) -> PospInvoiceDetailResponse:
    service = ReportService(session)
    data = await service.create_posp_invoice(request=request, principal=principal)
    return PospInvoiceDetailResponse(**data)


@router.get(
    "/posp-invoices/{invoice_id}/pdf",
    summary="Download POSP Invoice PDF",
)
async def download_posp_invoice_pdf(
    invoice_id: int = Path(..., description="ID of the invoice"),
    principal: PrincipalContext = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db),
):
    service = ReportService(session)
    pdf_bytes = await service.get_posp_invoice_pdf(invoice_id=invoice_id, principal=principal)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="posp_invoice_{invoice_id}.pdf"'},
    )


@router.get(
    "/posp-invoices/payout-reconciliation",
    response_model=PagedAgentPayoutReconciliationResponse,
    status_code=status.HTTP_200_OK,
    summary="Agent Commission vs Invoiced vs Disbursed Reconciliation",
    dependencies=[Depends(require_roles("OWNER", "ADMIN", "ACCOUNT", "ACCOUNT HEAD"))],
)
async def get_agent_payout_reconciliation(
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    agent_id: Optional[int] = Query(None),
    session: AsyncSession = Depends(get_db),
) -> PagedAgentPayoutReconciliationResponse:
    service = ReportService(session)
    items = await service.get_agent_payout_reconciliation(from_date=from_date, to_date=to_date, agent_id=agent_id)
    return PagedAgentPayoutReconciliationResponse(items=items, total=len(items))


# ============================================================================
# 3. Accounting & Statutory Reports
# ============================================================================

@router.get(
    "/statutory/tds",
    response_model=TdsRegisterResponse,
    status_code=status.HTTP_200_OK,
    summary="Statutory TDS Register (Section 194H) with 2113 Ledger Tracking",
    dependencies=[Depends(require_roles("OWNER", "ADMIN", "ACCOUNT", "ACCOUNT HEAD"))],
)
async def get_tds_register(
    from_date: date = Query(..., description="Start date"),
    to_date: date = Query(..., description="End date"),
    agent_id: Optional[int] = Query(None, description="Optional agent filter"),
    session: AsyncSession = Depends(get_db),
) -> TdsRegisterResponse:
    service = ReportService(session)
    data = await service.get_tds_register(from_date=from_date, to_date=to_date, agent_id=agent_id)
    return TdsRegisterResponse(**data)


@router.get(
    "/statutory/tds/export",
    summary="Export TDS Register as OpenXML Spreadsheet",
    dependencies=[Depends(require_roles("OWNER", "ADMIN", "ACCOUNT", "ACCOUNT HEAD"))],
)
async def export_tds_register(
    from_date: date = Query(..., description="Start date"),
    to_date: date = Query(..., description="End date"),
    agent_id: Optional[int] = Query(None, description="Optional agent filter"),
    session: AsyncSession = Depends(get_db),
):
    service = ReportService(session)
    file_bytes, filename, media_type = await service.export_tds_register(from_date=from_date, to_date=to_date, agent_id=agent_id)
    return Response(
        content=file_bytes,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/accounting/ledger-summary",
    response_model=List[LedgerTypeSummaryItem],
    status_code=status.HTTP_200_OK,
    summary="Tier-1 Ledger Type Summary (Debit vs Credit Balances)",
    dependencies=[Depends(require_roles("OWNER", "ADMIN", "ACCOUNT", "ACCOUNT HEAD"))],
)
async def get_ledger_summary(
    from_date: date = Query(..., description="Start date"),
    to_date: date = Query(..., description="End date"),
    session: AsyncSession = Depends(get_db),
) -> List[LedgerTypeSummaryItem]:
    service = ReportService(session)
    return await service.get_ledger_summary(from_date=from_date, to_date=to_date)


@router.get(
    "/accounting/ledger-statement",
    response_model=LedgerStatementResponse,
    status_code=status.HTTP_200_OK,
    summary="Tier-3 Ledger Statement Drilldown with Running Balances",
    dependencies=[Depends(require_roles("OWNER", "ADMIN", "ACCOUNT", "ACCOUNT HEAD"))],
)
async def get_ledger_statement(
    ledger_m_id: int = Query(..., description="Ledger Master ID"),
    from_date: date = Query(..., description="Start date"),
    to_date: date = Query(..., description="End date"),
    session: AsyncSession = Depends(get_db),
) -> LedgerStatementResponse:
    service = ReportService(session)
    data = await service.get_ledger_statement(ledger_m_id=ledger_m_id, from_date=from_date, to_date=to_date)
    return LedgerStatementResponse(**data)


@router.get(
    "/accounting/vouchers/{voucher_id}",
    response_model=VoucherDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Tier-4 Voucher Detail with Indian Currency Words",
    dependencies=[Depends(require_roles("OWNER", "ADMIN", "ACCOUNT", "ACCOUNT HEAD"))],
)
async def get_voucher_detail(
    voucher_id: int = Path(..., description="Account voucher transaction ID"),
    session: AsyncSession = Depends(get_db),
) -> VoucherDetailResponse:
    service = ReportService(session)
    data = await service.get_voucher(voucher_id=voucher_id)
    return VoucherDetailResponse(**data)


@router.get(
    "/accounting/vouchers/{voucher_id}/pdf",
    summary="Download Payment/Receipt Voucher PDF",
    dependencies=[Depends(require_roles("OWNER", "ADMIN", "ACCOUNT", "ACCOUNT HEAD"))],
)
async def download_voucher_pdf(
    voucher_id: int = Path(..., description="Account voucher transaction ID"),
    session: AsyncSession = Depends(get_db),
):
    service = ReportService(session)
    pdf_bytes = await service.get_voucher_pdf(voucher_id=voucher_id)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="voucher_{voucher_id}.pdf"'},
    )


@router.get(
    "/accounting/payment-advice",
    response_model=PaymentAdviceResponse,
    status_code=status.HTTP_200_OK,
    summary="Monthly Agent Commission Payment Advice Statement",
)
async def get_payment_advice(
    financial_year: str = Query(..., description="e.g. 2025-2026"),
    month: str = Query(..., description="e.g. APRIL, MAY"),
    agent_id: int = Query(..., description="Agent ID"),
    principal: PrincipalContext = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db),
) -> PaymentAdviceResponse:
    service = ReportService(session)
    data = await service.get_payment_advice(
        financial_year=financial_year,
        month=month,
        agent_id=agent_id,
        principal=principal,
    )
    return PaymentAdviceResponse(**data)


@router.get(
    "/accounting/bank-commission-statement",
    response_model=BankCommissionStatementResponse,
    status_code=status.HTTP_200_OK,
    summary="Consolidated Bank Commission Payout Advice for Net Banking",
    dependencies=[Depends(require_roles("OWNER", "ADMIN", "ACCOUNT", "ACCOUNT HEAD"))],
)
async def get_bank_commission_statement(
    financial_year: str = Query(..., description="e.g. 2025-2026"),
    month: str = Query(..., description="e.g. APRIL, MAY"),
    branch_id: Optional[int] = Query(None, description="Optional branch filter"),
    session: AsyncSession = Depends(get_db),
) -> BankCommissionStatementResponse:
    service = ReportService(session)
    data = await service.get_bank_commission_statement(
        financial_year=financial_year,
        month=month,
        branch_id=branch_id,
    )
    return BankCommissionStatementResponse(**data)


@router.get(
    "/accounting/daily-collection",
    response_model=DailyCollectionAuditResponse,
    status_code=status.HTTP_200_OK,
    summary="Branch Daily Cash, Cheque & Online Collection Audit",
    dependencies=[Depends(require_roles("OWNER", "ADMIN", "ACCOUNT", "ACCOUNT HEAD", "LOCATION HEAD", "BRANCH MANAGER"))],
)
async def get_daily_collection_audit(
    report_date: date = Query(..., description="Audit date"),
    branch_id: Optional[int] = Query(None, description="Branch ID"),
    principal: PrincipalContext = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db),
) -> DailyCollectionAuditResponse:
    service = ReportService(session)
    if not is_global_read_role(principal.role_name):
        branch_id = principal.branch_id
    data = await service.get_daily_collection_audit(report_date=report_date, branch_id=branch_id)
    return DailyCollectionAuditResponse(**data)


# ============================================================================
# 4. Operations, Pipeline & Reconciliations
# ============================================================================

@router.get(
    "/operations/commission-reconciliation",
    response_model=CommissionReconcileResponse,
    status_code=status.HTTP_200_OK,
    summary="Company Brokerage / Commission Discrepancy Reconciliation",
    dependencies=[Depends(require_roles("OWNER", "ADMIN", "ACCOUNT", "ACCOUNT HEAD"))],
)
async def get_commission_reconciliation(
    from_date: date = Query(..., description="Start date"),
    to_date: date = Query(..., description="End date"),
    company_id: Optional[int] = Query(None, description="Optional Insurance Company ID"),
    session: AsyncSession = Depends(get_db),
) -> CommissionReconcileResponse:
    service = ReportService(session)
    data = await service.get_commission_reconciliation(from_date=from_date, to_date=to_date, company_id=company_id)
    return CommissionReconcileResponse(**data)


@router.get(
    "/operations/bank-reconciliation",
    response_model=BankReconcileResponse,
    status_code=status.HTTP_200_OK,
    summary="Bank Cheque Clearance Reconciliation & Uncleared Days",
    dependencies=[Depends(require_roles("OWNER", "ADMIN", "ACCOUNT", "ACCOUNT HEAD"))],
)
async def get_bank_reconciliation(
    from_date: date = Query(..., description="Start date"),
    to_date: date = Query(..., description="End date"),
    bank_id: Optional[int] = Query(None, description="Optional Bank ID"),
    session: AsyncSession = Depends(get_db),
) -> BankReconcileResponse:
    service = ReportService(session)
    data = await service.get_bank_reconciliation(from_date=from_date, to_date=to_date, bank_id=bank_id)
    return BankReconcileResponse(**data)


@router.get(
    "/operations/endorsements",
    response_model=PagedEndorsementReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Operational Endorsements Register with Financial Deltas",
    dependencies=[Depends(require_roles("OWNER", "ADMIN", "OPERATOR", "BACK OFFICE", "LOCATION HEAD", "BRANCH MANAGER"))],
)
async def get_endorsements_report(
    from_date: date = Query(..., description="Start date"),
    to_date: date = Query(..., description="End date"),
    branch_id: Optional[int] = Query(None, description="Branch ID"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    principal: PrincipalContext = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db),
) -> PagedEndorsementReportResponse:
    service = ReportService(session)
    if not is_global_read_role(principal.role_name):
        branch_id = principal.branch_id
    data = await service.get_endorsements(from_date=from_date, to_date=to_date, branch_id=branch_id, skip=skip, limit=limit)
    return PagedEndorsementReportResponse(**data)


@router.get(
    "/operations/claims",
    response_model=PagedClaimsReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Operational Claims Pipeline & Settlement Report",
    dependencies=[Depends(require_roles("OWNER", "ADMIN", "OPERATOR", "BACK OFFICE", "LOCATION HEAD", "BRANCH MANAGER"))],
)
async def get_claims_report(
    from_date: date = Query(..., description="Start date"),
    to_date: date = Query(..., description="End date"),
    claim_status: Optional[str] = Query(None, alias="status", description="Claim status filter"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    session: AsyncSession = Depends(get_db),
) -> PagedClaimsReportResponse:
    service = ReportService(session)
    data = await service.get_claims(from_date=from_date, to_date=to_date, status_filter=claim_status, skip=skip, limit=limit)
    return PagedClaimsReportResponse(**data)


# ============================================================================
# 5. Targets & Renewals Reports
# ============================================================================

@router.get(
    "/targets/telecaller",
    response_model=TelecallerTargetResponse,
    status_code=status.HTTP_200_OK,
    summary="Telecaller Target vs Achievement Performance",
    dependencies=[Depends(require_roles("OWNER", "ADMIN", "TELECALLER", "MANAGER", "LOCATION HEAD", "BRANCH MANAGER"))],
)
async def get_telecaller_targets(
    financial_year: str = Query(..., description="e.g. 2025-2026"),
    month: str = Query(..., description="e.g. APRIL, MAY"),
    user_id: Optional[int] = Query(None, description="Optional user ID"),
    principal: PrincipalContext = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db),
) -> TelecallerTargetResponse:
    service = ReportService(session)
    # If authenticated user is TELECALLER, scope to self
    if (principal.role_name or "").upper() == "TELECALLER":
        user_id = principal.user_id
    items = await service.get_telecaller_targets(financial_year=financial_year, month=month, user_id=user_id)
    return TelecallerTargetResponse(financial_year=financial_year, month=month, items=items)


@router.get(
    "/targets/executive",
    response_model=ExecutiveTargetResponse,
    status_code=status.HTTP_200_OK,
    summary="Marketing Executive Target vs Achievement Performance",
    dependencies=[Depends(require_roles("OWNER", "ADMIN", "MANAGER", "LOCATION HEAD", "BRANCH MANAGER"))],
)
async def get_executive_targets(
    financial_year: str = Query(..., description="e.g. 2025-2026"),
    month: str = Query(..., description="e.g. APRIL, MAY"),
    user_id: Optional[int] = Query(None, description="Optional user ID"),
    session: AsyncSession = Depends(get_db),
) -> ExecutiveTargetResponse:
    service = ReportService(session)
    items = await service.get_executive_targets(financial_year=financial_year, month=month, user_id=user_id)
    return ExecutiveTargetResponse(financial_year=financial_year, month=month, items=items)


@router.get(
    "/renewals/expiring-policies",
    response_model=ExpiringPoliciesResponse,
    status_code=status.HTTP_200_OK,
    summary="Expiring Policies Report with Lead Conversion Window",
    dependencies=[Depends(require_roles("OWNER", "ADMIN", "TELECALLER", "OPERATOR", "AGENT", "POSP", "LOCATION HEAD", "BRANCH MANAGER"))],
)
async def get_expiring_policies(
    as_of_date: date = Query(..., description="Reference date for expiry window"),
    window_days: int = Query(30, ge=1, le=365, description="Days ahead to search"),
    branch_id: Optional[int] = Query(None, description="Optional branch ID filter"),
    principal: PrincipalContext = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db),
) -> ExpiringPoliciesResponse:
    service = ReportService(session)
    if not is_global_read_role(principal.role_name):
        branch_id = principal.branch_id
    data = await service.get_expiring_policies(as_of_date=as_of_date, window_days=window_days, branch_id=branch_id)
    return ExpiringPoliciesResponse(**data)
