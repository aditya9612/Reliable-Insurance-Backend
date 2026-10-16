"""
FastAPI Route Handlers for Phase 25:
Corporate Group Clients, Commercial Sales Invoicing & Sister Concern Advances.
"""
from typing import List, Optional
from datetime import date
from fastapi import APIRouter, Depends, Query, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.dependencies import get_current_user, require_roles
from app.models.user import User
from app.services.corporate_client_service import CorporateClientService, Phase25Service
from app.schemas.corporate_client import (
    SalesTypeCreate,
    SalesTypeUpdate,
    SalesTypeResponse,
    ReliableCompanyCreate,
    ReliableCompanyUpdate,
    ReliableCompanyResponse,
    ClientMasterCreate,
    ClientMasterUpdate,
    ClientMasterResponse,
    CommercialInvoiceCreateRequest,
    CommercialInvoiceResponse,
    CommercialSalesRegisterReportResponse,
    CompanyAdvanceCreateRequest,
    CompanyAdvanceResponse,
    CompanyAdvanceRecoveryRequest,
    CompanyAdvanceRecoveryResponse,
    CompanyAdvanceReportResponse,
)

# Individual APIRouters for Clean Domain Mounts
sales_types_router = APIRouter(prefix="/commercial/sales-types", tags=["Commercial Sales Types"])
reliable_companies_router = APIRouter(prefix="/commercial/reliable-companies", tags=["Reliable Companies"])
corporate_clients_router = APIRouter(prefix="/commercial/corporate-clients", tags=["Corporate Clients"])
commercial_invoices_router = APIRouter(prefix="/commercial/invoices", tags=["Commercial Sales Invoices"])
company_advances_router = APIRouter(prefix="/commercial/advances", tags=["Sister Concern Advances"])


# ============================================================================
# 1. SALES TYPES ENDPOINTS
# ============================================================================

@sales_types_router.post(
    "",
    response_model=SalesTypeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Commercial Sales Classification Type",
)
async def create_sales_type(
    payload: SalesTypeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN", "OWNER")),
) -> SalesTypeResponse:
    service = CorporateClientService(db)
    return await service.create_sales_type(payload)


@sales_types_router.get(
    "",
    response_model=List[SalesTypeResponse],
    summary="List Commercial Sales Classification Types",
)
async def list_sales_types(
    is_active: Optional[bool] = Query(None, description="Filter active/inactive"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[SalesTypeResponse]:
    service = CorporateClientService(db)
    return await service.list_sales_types(is_active=is_active)


@sales_types_router.get(
    "/{sales_type_id}",
    response_model=SalesTypeResponse,
    summary="Get Commercial Sales Type Detail",
)
async def get_sales_type(
    sales_type_id: int = Path(..., ge=1),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SalesTypeResponse:
    service = CorporateClientService(db)
    return await service.get_sales_type(sales_type_id)


@sales_types_router.put(
    "/{sales_type_id}",
    response_model=SalesTypeResponse,
    summary="Update Commercial Sales Type",
)
async def update_sales_type(
    payload: SalesTypeUpdate,
    sales_type_id: int = Path(..., ge=1),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN", "OWNER")),
) -> SalesTypeResponse:
    service = CorporateClientService(db)
    return await service.update_sales_type(sales_type_id, payload)


@sales_types_router.delete(
    "/{sales_type_id}",
    summary="Soft-Deactivate or Hard-Delete Sales Type",
)
async def delete_sales_type(
    sales_type_id: int = Path(..., ge=1),
    hard_delete: bool = Query(False, description="True for physical removal if unreferenced"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN", "OWNER")),
):
    service = CorporateClientService(db)
    return await service.delete_sales_type(sales_type_id, hard_delete=hard_delete)


# ============================================================================
# 2. RELIABLE GROUP COMPANIES ENDPOINTS
# ============================================================================

@reliable_companies_router.post(
    "",
    response_model=ReliableCompanyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Reliable Sister Concern Company & Prefix",
)
async def create_reliable_company(
    payload: ReliableCompanyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN", "OWNER")),
) -> ReliableCompanyResponse:
    service = CorporateClientService(db)
    return await service.create_reliable_company(payload)


@reliable_companies_router.get(
    "",
    response_model=List[ReliableCompanyResponse],
    summary="List Reliable Sister Concern Companies",
)
async def list_reliable_companies(
    is_active: Optional[bool] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[ReliableCompanyResponse]:
    service = CorporateClientService(db)
    return await service.list_reliable_companies(is_active=is_active)


@reliable_companies_router.get(
    "/{r_company_id}",
    response_model=ReliableCompanyResponse,
    summary="Get Reliable Company Detail",
)
async def get_reliable_company(
    r_company_id: int = Path(..., ge=1),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ReliableCompanyResponse:
    service = CorporateClientService(db)
    return await service.get_reliable_company(r_company_id)


@reliable_companies_router.put(
    "/{r_company_id}",
    response_model=ReliableCompanyResponse,
    summary="Update Reliable Company or Invoicing Prefix",
)
async def update_reliable_company(
    payload: ReliableCompanyUpdate,
    r_company_id: int = Path(..., ge=1),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN", "OWNER")),
) -> ReliableCompanyResponse:
    service = CorporateClientService(db)
    return await service.update_reliable_company(r_company_id, payload)


@reliable_companies_router.delete(
    "/{r_company_id}",
    summary="Soft-Deactivate or Hard-Delete Reliable Company",
)
async def delete_reliable_company(
    r_company_id: int = Path(..., ge=1),
    hard_delete: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN", "OWNER")),
):
    service = CorporateClientService(db)
    return await service.delete_reliable_company(r_company_id, hard_delete=hard_delete)


# ============================================================================
# 3. CORPORATE GROUP CLIENTS ENDPOINTS
# ============================================================================

@corporate_clients_router.post(
    "",
    response_model=ClientMasterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register Corporate B2B Group Client",
)
async def create_client_master(
    payload: ClientMasterCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN", "OWNER", "ACCOUNT", "ACCOUNT HEAD", "OPERATOR", "BACK OFFICE")),
) -> ClientMasterResponse:
    service = CorporateClientService(db)
    username = getattr(current_user, "UserName", None) or str(current_user.UserId)
    return await service.create_client_master(payload, user_name=username)


@corporate_clients_router.get(
    "",
    response_model=List[ClientMasterResponse],
    summary="Search & List Corporate Group Clients",
)
async def list_client_masters(
    search: Optional[str] = Query(None, description="Search client name, GSTIN, or PAN"),
    insurance_company_id: Optional[int] = Query(None, ge=1),
    is_active: Optional[bool] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[ClientMasterResponse]:
    service = CorporateClientService(db)
    return await service.list_client_masters(
        search=search,
        insurance_company_id=insurance_company_id,
        is_active=is_active,
        skip=skip,
        limit=limit,
    )


@corporate_clients_router.get(
    "/{client_master_id}",
    response_model=ClientMasterResponse,
    summary="Get Corporate Client Detail & Default Tax Rates",
)
async def get_client_master(
    client_master_id: int = Path(..., ge=1),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ClientMasterResponse:
    service = CorporateClientService(db)
    return await service.get_client_master(client_master_id)


@corporate_clients_router.put(
    "/{client_master_id}",
    response_model=ClientMasterResponse,
    summary="Update Corporate Client Master Information",
)
async def update_client_master(
    payload: ClientMasterUpdate,
    client_master_id: int = Path(..., ge=1),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN", "OWNER", "ACCOUNT", "ACCOUNT HEAD")),
) -> ClientMasterResponse:
    service = CorporateClientService(db)
    return await service.update_client_master(client_master_id, payload)


@corporate_clients_router.delete(
    "/{client_master_id}",
    summary="Soft-Deactivate or Hard-Delete Corporate Client",
)
async def delete_client_master(
    client_master_id: int = Path(..., ge=1),
    hard_delete: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN", "OWNER")),
):
    service = CorporateClientService(db)
    return await service.delete_client_master(client_master_id, hard_delete=hard_delete)


# ============================================================================
# 4. COMMERCIAL SALES INVOICING ENDPOINTS
# ============================================================================

@commercial_invoices_router.get(
    "/next-number",
    summary="Preview Next Sequential Invoice Number for Reliable Company",
)
async def preview_next_invoice_number(
    r_company_id: int = Query(..., ge=1),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = CorporateClientService(db)
    return await service.preview_next_invoice_number(r_company_id)


@commercial_invoices_router.post(
    "",
    response_model=CommercialInvoiceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Multi-Line Commercial B2B Sales Invoice & Revenue Voucher",
)
async def create_commercial_invoice(
    payload: CommercialInvoiceCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN", "OWNER", "ACCOUNT", "ACCOUNT HEAD", "OPERATOR", "BACK OFFICE")),
) -> CommercialInvoiceResponse:
    service = CorporateClientService(db)
    return await service.create_commercial_invoice(payload, current_user=current_user)


@commercial_invoices_router.get(
    "",
    response_model=List[CommercialInvoiceResponse],
    summary="List Commercial Sales Invoices with Filters",
)
async def list_commercial_invoices(
    client_master_id: Optional[int] = Query(None, ge=1),
    r_company_id: Optional[int] = Query(None, ge=1),
    invoice_no: Optional[str] = Query(None),
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[CommercialInvoiceResponse]:
    service = CorporateClientService(db)
    return await service.list_commercial_invoices(
        client_master_id=client_master_id,
        r_company_id=r_company_id,
        invoice_no=invoice_no,
        from_date=from_date,
        to_date=to_date,
        skip=skip,
        limit=limit,
    )


@commercial_invoices_router.get(
    "/report",
    response_model=CommercialSalesRegisterReportResponse,
    summary="Commercial Sales Registration Summary Register Report",
)
async def get_sales_register_report(
    r_company_id: Optional[int] = Query(None, ge=1),
    client_master_id: Optional[int] = Query(None, ge=1),
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    invoice_no: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN", "OWNER", "ACCOUNT", "ACCOUNT HEAD")),
) -> CommercialSalesRegisterReportResponse:
    service = CorporateClientService(db)
    return await service.get_sales_register_report(
        r_company_id=r_company_id,
        client_master_id=client_master_id,
        from_date=from_date,
        to_date=to_date,
        invoice_no=invoice_no,
    )


@commercial_invoices_router.get(
    "/{sales_reg_id}",
    response_model=CommercialInvoiceResponse,
    summary="Get Commercial Sales Invoice with Line Items",
)
async def get_commercial_invoice(
    sales_reg_id: int = Path(..., ge=1),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CommercialInvoiceResponse:
    service = CorporateClientService(db)
    return await service.get_commercial_invoice(sales_reg_id)


# ============================================================================
# 5. SISTER CONCERN ADVANCES ENDPOINTS
# ============================================================================

@company_advances_router.post(
    "",
    response_model=CompanyAdvanceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Disburse & Book Sister Concern Company Advance",
)
async def create_advance(
    payload: CompanyAdvanceCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN", "OWNER", "ACCOUNT", "ACCOUNT HEAD")),
) -> CompanyAdvanceResponse:
    service = CorporateClientService(db)
    return await service.create_advance(payload, current_user=current_user)


@company_advances_router.get(
    "",
    response_model=List[CompanyAdvanceResponse],
    summary="List Sister Concern Advances & Remaining Balances",
)
async def list_advances(
    ledger_m_id: Optional[int] = Query(None, ge=1),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN", "OWNER", "ACCOUNT", "ACCOUNT HEAD")),
) -> List[CompanyAdvanceResponse]:
    service = CorporateClientService(db)
    return await service.list_advances(ledger_m_id=ledger_m_id)


@company_advances_router.post(
    "/{advance_id}/recover",
    response_model=CompanyAdvanceRecoveryResponse,
    summary="Recover Sister Concern Advance against Invoice or Accounting Voucher",
)
async def recover_advance(
    payload: CompanyAdvanceRecoveryRequest,
    advance_id: int = Path(..., ge=1),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN", "OWNER", "ACCOUNT", "ACCOUNT HEAD")),
) -> CompanyAdvanceRecoveryResponse:
    service = CorporateClientService(db)
    return await service.recover_advance(advance_id, payload=payload, current_user=current_user)


@company_advances_router.get(
    "/report",
    response_model=CompanyAdvanceReportResponse,
    summary="Sister Concern Advance Facility Overview & Recovery History Report",
)
async def get_advance_report(
    advance_id: Optional[int] = Query(None, ge=1),
    ledger_m_id: Optional[int] = Query(None, ge=1),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles("ADMIN", "OWNER", "ACCOUNT", "ACCOUNT HEAD")),
) -> CompanyAdvanceReportResponse:
    service = CorporateClientService(db)
    return await service.get_advance_report(advance_id=advance_id, ledger_m_id=ledger_m_id)
