"""
FastAPI Route Handlers for Phase 22 — Sales Executive & Location Head Commission Hierarchy,
Insurer Partner Portals Registry, and App Billing & Field Reimbursement Claims.
"""
from typing import List, Optional
from datetime import date
from fastapi import APIRouter, Depends, Query, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.dependencies import get_current_user, require_roles
from app.models.user import User
from app.services.executive_commission_service import ExecutiveCommissionService, Phase22Service
from app.schemas.executive_commission import (
    SalesExecutiveCommissionCreate,
    SalesExecutiveCommissionUpdate,
    SalesExecutiveCommissionResponse,
    SalesExecutiveCommissionLookupRequest,
    SalesExecutiveCommissionLookupResponse,
    LocationHeadCommissionCreate,
    LocationHeadCommissionUpdate,
    LocationHeadCommissionResponse,
    LocationHeadCommissionLookupRequest,
    LocationHeadCommissionLookupResponse,
    LocationHeadAssignmentRequest,
    LocationHeadSalesExMapResponse,
    InsuranceCompanyPortalCreate,
    InsuranceCompanyPortalUpdate,
    InsuranceCompanyPortalResponse,
    AppBillingDetailsCreate,
    AppBillingStatusUpdateRequest,
    AppBillingDetailsResponse,
)

ADMIN_ROLES = ("OWNER", "ADMIN", "IT SUPPORT", "MANAGER", "SUPERVISOR", "LOCATION HEAD")
SALES_ROLES = (
    "OWNER",
    "ADMIN",
    "IT SUPPORT",
    "MANAGER",
    "SUPERVISOR",
    "LOCATION HEAD",
    "SALES EXECUTIVE",
)
FINANCE_ROLES = (
    "OWNER",
    "ADMIN",
    "IT SUPPORT",
    "MANAGER",
    "ACCOUNTANT",
    "ACCOUNTS HEAD",
    "LOCATION HEAD",
)

sales_exec_commissions_router = APIRouter(prefix="/commissions/sales-executives", tags=["commissions"])
location_head_commissions_router = APIRouter(prefix="/commissions/location-heads", tags=["commissions"])
insurer_portals_router = APIRouter(prefix="/masters/insurer-portals", tags=["masters"])
app_billing_router = APIRouter(prefix="/billing/claims", tags=["billing"])


# ============================================================================
# 1. SALES EXECUTIVE COMMISSION ENDPOINTS
# ============================================================================

@sales_exec_commissions_router.get(
    "/grids",
    response_model=List[SalesExecutiveCommissionResponse],
    summary="List Sales Executive commission grid entries",
)
async def list_sales_ex_commissions(
    sales_ex_id: Optional[int] = Query(None, description="Filter by Sales Executive ID"),
    insurance_company_id: Optional[int] = Query(None, description="Filter by Insurer ID"),
    franchise_code: Optional[str] = Query(None, description="Filter by Franchise Code (e.g. RA)"),
    policy_type: Optional[str] = Query(None, description="Filter by Policy Type"),
    product_type: Optional[str] = Query(None, description="Filter by Product Type"),
    is_active: Optional[int] = Query(1, description="1=Active, 0=Inactive"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*SALES_ROLES)),
):
    service = ExecutiveCommissionService(db)
    return await service.list_sales_ex_commissions(
        sales_ex_id=sales_ex_id,
        insurance_company_id=insurance_company_id,
        franchise_code=franchise_code,
        policy_type=policy_type,
        product_type=product_type,
        is_active=is_active,
        skip=skip,
        limit=limit,
    )


@sales_exec_commissions_router.post(
    "/grids",
    response_model=SalesExecutiveCommissionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Sales Executive commission grid entry",
)
async def create_sales_ex_commission(
    payload: SalesExecutiveCommissionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*ADMIN_ROLES)),
):
    service = ExecutiveCommissionService(db)
    return await service.create_sales_ex_commission(
        payload=payload, current_user_id=current_user.UserId
    )


@sales_exec_commissions_router.post(
    "/lookup",
    response_model=SalesExecutiveCommissionLookupResponse,
    summary="Lookup applicable Sales Executive commission rate for a policy",
)
async def lookup_sales_ex_commission(
    payload: SalesExecutiveCommissionLookupRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*SALES_ROLES)),
):
    service = ExecutiveCommissionService(db)
    return await service.lookup_sales_ex_commission(payload)


@sales_exec_commissions_router.get(
    "/grids/{commission_id}",
    response_model=SalesExecutiveCommissionResponse,
    summary="Get Sales Executive commission grid entry by ID",
)
async def get_sales_ex_commission(
    commission_id: int = Path(..., ge=1),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*SALES_ROLES)),
):
    service = ExecutiveCommissionService(db)
    return await service.get_sales_ex_commission(commission_id)


@sales_exec_commissions_router.put(
    "/grids/{commission_id}",
    response_model=SalesExecutiveCommissionResponse,
    summary="Update Sales Executive commission grid entry",
)
async def update_sales_ex_commission(
    commission_id: int = Path(..., ge=1),
    payload: SalesExecutiveCommissionUpdate = ...,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*ADMIN_ROLES)),
):
    service = ExecutiveCommissionService(db)
    return await service.update_sales_ex_commission(
        commission_id=commission_id,
        payload=payload,
        current_user_id=current_user.UserId,
    )


@sales_exec_commissions_router.delete(
    "/grids/{commission_id}",
    response_model=SalesExecutiveCommissionResponse,
    summary="Soft delete Sales Executive commission grid entry",
)
async def delete_sales_ex_commission(
    commission_id: int = Path(..., ge=1),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*ADMIN_ROLES)),
):
    service = ExecutiveCommissionService(db)
    return await service.delete_sales_ex_commission(
        commission_id=commission_id,
        current_user_id=current_user.UserId,
    )


# ============================================================================
# 2. LOCATION HEAD COMMISSION & HIERARCHY ENDPOINTS
# ============================================================================

@location_head_commissions_router.get(
    "/grids",
    response_model=List[LocationHeadCommissionResponse],
    summary="List Location Head commission grid entries",
)
async def list_location_head_commissions(
    location_head_id: Optional[int] = Query(None, description="Filter by Location Head ID"),
    insurance_company_id: Optional[int] = Query(None, description="Filter by Insurer ID"),
    franchise_code: Optional[str] = Query(None, description="Filter by Franchise Code"),
    is_active: Optional[int] = Query(1),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*ADMIN_ROLES)),
):
    service = ExecutiveCommissionService(db)
    return await service.list_location_head_commissions(
        location_head_id=location_head_id,
        insurance_company_id=insurance_company_id,
        franchise_code=franchise_code,
        is_active=is_active,
        skip=skip,
        limit=limit,
    )


@location_head_commissions_router.post(
    "/grids",
    response_model=LocationHeadCommissionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Location Head commission grid entry",
)
async def create_location_head_commission(
    payload: LocationHeadCommissionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*ADMIN_ROLES)),
):
    service = ExecutiveCommissionService(db)
    return await service.create_location_head_commission(
        payload=payload, current_user_id=current_user.UserId
    )


@location_head_commissions_router.post(
    "/lookup",
    response_model=LocationHeadCommissionLookupResponse,
    summary="Lookup Location Head override rate for a policy",
)
async def lookup_location_head_commission(
    payload: LocationHeadCommissionLookupRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*ADMIN_ROLES)),
):
    service = ExecutiveCommissionService(db)
    return await service.lookup_location_head_commission(payload)


@location_head_commissions_router.post(
    "/assignments",
    response_model=List[LocationHeadSalesExMapResponse],
    summary="Assign Sales Executives to Location Head",
)
async def assign_sales_executives(
    payload: LocationHeadAssignmentRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*ADMIN_ROLES)),
):
    service = ExecutiveCommissionService(db)
    return await service.assign_sales_executives_to_location_head(
        payload=payload, current_user_id=current_user.UserId
    )


@location_head_commissions_router.get(
    "/sales-executives/{sales_ex_id}",
    response_model=Optional[LocationHeadSalesExMapResponse],
    summary="Get active Location Head for a Sales Executive",
)
async def get_location_head_for_sales_ex(
    sales_ex_id: int = Path(..., ge=1),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*SALES_ROLES)),
):
    service = ExecutiveCommissionService(db)
    result = await service.get_location_head_for_sales_executive(sales_ex_id)
    return result


@location_head_commissions_router.get(
    "/{location_head_id}/team",
    response_model=List[LocationHeadSalesExMapResponse],
    summary="List all Sales Executives under a Location Head",
)
async def list_team_under_location_head(
    location_head_id: int = Path(..., ge=1),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*ADMIN_ROLES)),
):
    service = ExecutiveCommissionService(db)
    return await service.list_sales_executives_under_location_head(location_head_id)


@location_head_commissions_router.get(
    "/grids/{commission_id}",
    response_model=LocationHeadCommissionResponse,
    summary="Get Location Head commission grid entry by ID",
)
async def get_location_head_commission(
    commission_id: int = Path(..., ge=1),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*ADMIN_ROLES)),
):
    service = ExecutiveCommissionService(db)
    return await service.get_location_head_commission(commission_id)


@location_head_commissions_router.put(
    "/grids/{commission_id}",
    response_model=LocationHeadCommissionResponse,
    summary="Update Location Head commission grid entry",
)
async def update_location_head_commission(
    commission_id: int = Path(..., ge=1),
    payload: LocationHeadCommissionUpdate = ...,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*ADMIN_ROLES)),
):
    service = ExecutiveCommissionService(db)
    return await service.update_location_head_commission(
        commission_id=commission_id,
        payload=payload,
        current_user_id=current_user.UserId,
    )


@location_head_commissions_router.delete(
    "/grids/{commission_id}",
    response_model=LocationHeadCommissionResponse,
    summary="Soft delete Location Head commission grid entry",
)
async def delete_location_head_commission(
    commission_id: int = Path(..., ge=1),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*ADMIN_ROLES)),
):
    service = ExecutiveCommissionService(db)
    return await service.delete_location_head_commission(
        commission_id=commission_id,
        current_user_id=current_user.UserId,
    )


# ============================================================================
# 3. INSURER PARTNER PORTALS REGISTRY ENDPOINTS
# ============================================================================

@insurer_portals_router.get(
    "",
    response_model=List[InsuranceCompanyPortalResponse],
    summary="List registered insurer portals",
)
async def list_insurer_portals(
    insurance_company_id: Optional[int] = Query(None, description="Filter by Insurer ID"),
    broker_id: Optional[int] = Query(None, description="Filter by Broker ID"),
    is_active: Optional[int] = Query(1),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*SALES_ROLES)),
):
    service = ExecutiveCommissionService(db)
    return await service.list_insurer_portals(
        insurance_company_id=insurance_company_id,
        broker_id=broker_id,
        is_active=is_active,
        skip=skip,
        limit=limit,
    )


@insurer_portals_router.post(
    "",
    response_model=InsuranceCompanyPortalResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register insurer portal credential",
)
async def create_insurer_portal(
    payload: InsuranceCompanyPortalCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*ADMIN_ROLES)),
):
    service = ExecutiveCommissionService(db)
    return await service.create_insurer_portal(
        payload=payload, current_user_id=current_user.UserId
    )


@insurer_portals_router.get(
    "/{portal_id}",
    response_model=InsuranceCompanyPortalResponse,
    summary="Get insurer portal details by ID",
)
async def get_insurer_portal(
    portal_id: int = Path(..., ge=1),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*SALES_ROLES)),
):
    service = ExecutiveCommissionService(db)
    return await service.get_insurer_portal(portal_id)


@insurer_portals_router.put(
    "/{portal_id}",
    response_model=InsuranceCompanyPortalResponse,
    summary="Update insurer portal details",
)
async def update_insurer_portal(
    portal_id: int = Path(..., ge=1),
    payload: InsuranceCompanyPortalUpdate = ...,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*ADMIN_ROLES)),
):
    service = ExecutiveCommissionService(db)
    return await service.update_insurer_portal(
        portal_id=portal_id,
        payload=payload,
        current_user_id=current_user.UserId,
    )


@insurer_portals_router.delete(
    "/{portal_id}",
    response_model=InsuranceCompanyPortalResponse,
    summary="Soft delete insurer portal",
)
async def delete_insurer_portal(
    portal_id: int = Path(..., ge=1),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*ADMIN_ROLES)),
):
    service = ExecutiveCommissionService(db)
    return await service.delete_insurer_portal(
        portal_id=portal_id,
        current_user_id=current_user.UserId,
    )


# ============================================================================
# 4. APP BILLING & FIELD REIMBURSEMENT ENDPOINTS
# ============================================================================

@app_billing_router.get(
    "",
    response_model=List[AppBillingDetailsResponse],
    summary="List Field Executive reimbursement claims",
)
async def list_billing_claims(
    sales_ex_id: Optional[int] = Query(None, description="Filter by Sales Executive ID"),
    status_filter: Optional[str] = Query(None, description="Filter by status (PENDING, APPROVED, etc.)"),
    from_date: Optional[date] = Query(None, description="Claims from date"),
    to_date: Optional[date] = Query(None, description="Claims to date"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*SALES_ROLES)),
):
    service = ExecutiveCommissionService(db)
    return await service.list_billing_claims(
        sales_ex_id=sales_ex_id,
        status_filter=status_filter,
        from_date=from_date,
        to_date=to_date,
        skip=skip,
        limit=limit,
    )


@app_billing_router.post(
    "",
    response_model=AppBillingDetailsResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit field expense reimbursement claim",
)
async def submit_billing_claim(
    payload: AppBillingDetailsCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*SALES_ROLES)),
):
    service = ExecutiveCommissionService(db)
    return await service.submit_billing_claim(
        payload=payload, current_user_id=current_user.UserId
    )


@app_billing_router.get(
    "/{billing_id}",
    response_model=AppBillingDetailsResponse,
    summary="Get billing claim details with photos and pdf attachments",
)
async def get_billing_claim(
    billing_id: int = Path(..., ge=1),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*SALES_ROLES)),
):
    service = ExecutiveCommissionService(db)
    return await service.get_billing_claim_details(billing_id)


@app_billing_router.patch(
    "/{billing_id}/status",
    response_model=AppBillingDetailsResponse,
    summary="Update billing claim status (Approve / Reject / Process)",
)
async def update_billing_status(
    billing_id: int = Path(..., ge=1),
    payload: AppBillingStatusUpdateRequest = ...,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*FINANCE_ROLES)),
):
    service = ExecutiveCommissionService(db)
    return await service.update_billing_status(
        billing_id=billing_id,
        payload=payload,
        current_user_id=current_user.UserId,
    )
