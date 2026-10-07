from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, Query, Path, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db, get_current_user
from app.models.user import User
from app.services.search_service import SearchService
from app.schemas.search import (
    AutocompleteResponse,
    VehicleDuplicateCheckResponse,
    PendingCountersResponse,
    DashboardChartDataResponse,
    ServerStatusResponse,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# BLOCK 4: Search, Autocomplete & Typeahead
# ---------------------------------------------------------------------------

@router.get(
    "/autocomplete",
    response_model=AutocompleteResponse,
    summary="Unified Autocomplete / Typeahead Search",
    description="Generic autocomplete matching legacy SearchMethods.aspx.cs and AppSearchMethod.aspx.cs.",
)
async def autocomplete(
    q: str = Query("", description="Search term or prefix"),
    category: str = Query("customer", description="Target entity category (customer, vehicle, policy, quotation, agent, posp, employee, rto, make, bank, branch)"),
    limit: int = Query(20, ge=1, le=100, description="Max results limit"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> AutocompleteResponse:
    service = SearchService(session)
    return await service.autocomplete(current_user=current_user, query=q, category=category, limit=limit)


@router.get(
    "/customers",
    response_model=AutocompleteResponse,
    summary="Autocomplete customer name / mobile",
    description="Maps GetCustName and GetCustByVehicleNo.",
)
async def search_customers_typeahead(
    q: str = Query("", description="Customer name, mobile, or code prefix"),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> AutocompleteResponse:
    service = SearchService(session)
    return await service.autocomplete(current_user=current_user, query=q, category="customer", limit=limit)


@router.get(
    "/vehicles",
    response_model=AutocompleteResponse,
    summary="Autocomplete vehicle registration / chassis",
    description="Maps GetCustVehicleNo.",
)
async def search_vehicles_typeahead(
    q: str = Query("", description="Vehicle registration number or chassis prefix"),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> AutocompleteResponse:
    service = SearchService(session)
    return await service.autocomplete(current_user=current_user, query=q, category="vehicle", limit=limit)


@router.get(
    "/policies",
    response_model=AutocompleteResponse,
    summary="Autocomplete policy / inward number",
    description="Maps GetPolicyNo and GetPolicyNoByCheqe.",
)
async def search_policies_typeahead(
    q: str = Query("", description="Policy number or inward prefix"),
    by_cheque_only: bool = Query(False, description="Filter only policies paid via cheque"),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> AutocompleteResponse:
    service = SearchService(session)
    category = "policy_by_cheque" if by_cheque_only else "policy"
    return await service.autocomplete(current_user=current_user, query=q, category=category, limit=limit)


@router.get(
    "/quotations",
    response_model=AutocompleteResponse,
    summary="Autocomplete quotation code",
    description="Maps GetQuatationNo.",
)
async def search_quotations_typeahead(
    q: str = Query("", description="Quotation code prefix"),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> AutocompleteResponse:
    service = SearchService(session)
    return await service.autocomplete(current_user=current_user, query=q, category="quotation", limit=limit)


@router.get(
    "/agents",
    response_model=AutocompleteResponse,
    summary="Autocomplete agent / POSP / franchise name",
    description="Maps GetAgentName, GetPOSPName, GetFranchiseName, GetFranchiseAgentName, SearchtextAgentName.",
)
async def search_agents_typeahead(
    q: str = Query("", description="Agent / POSP name prefix"),
    category: str = Query("agent", description="Specific role category: agent, posp, franchise, franchise_agent"),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> AutocompleteResponse:
    service = SearchService(session)
    return await service.autocomplete(current_user=current_user, query=q, category=category, limit=limit)


@router.get(
    "/employees",
    response_model=AutocompleteResponse,
    summary="Autocomplete employee / sales executive name",
    description="Maps GetSalesExName, SearchtextEmpName, SearchtextEmpCode.",
)
async def search_employees_typeahead(
    q: str = Query("", description="Employee name or code prefix"),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> AutocompleteResponse:
    service = SearchService(session)
    return await service.autocomplete(current_user=current_user, query=q, category="employee", limit=limit)


@router.get(
    "/quick-check/vehicle-no",
    response_model=VehicleDuplicateCheckResponse,
    summary="Check vehicle registration duplicate status",
    description="Maps SearchMethods.aspx.cs::checkVehicleNo and AppSearchMethod.aspx.cs::checkVehicleNo.",
)
async def check_vehicle_duplicate(
    registration_no: str = Query(..., description="Vehicle registration number to verify"),
    financial_year: Optional[str] = Query(None, description="Optional financial year filter (e.g. 2026-2027)"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> VehicleDuplicateCheckResponse:
    service = SearchService(session)
    return await service.check_vehicle_no(registration_no=registration_no, financial_year=financial_year)


@router.get(
    "/counters/pending",
    response_model=PendingCountersResponse,
    summary="Get pending operational inbox counters",
    description="Maps getNewAppEntry, getNewAppEntryOp, getPendingEntryOp, getPendingInwardOp, getNewAppEndorsementEntry, getNewMISAppEntry, getNewAgentAppEntry.",
)
async def get_pending_counters(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> PendingCountersResponse:
    service = SearchService(session)
    return await service.get_pending_counters(current_user=current_user)


@router.get(
    "/dashboard/summary",
    response_model=DashboardChartDataResponse,
    summary="Get dashboard chart & summary metrics",
    description="Maps chart_Premium_Summary, pie_Premium_Summary, pie_ODPremium_Summary, PolicyMode_Premium_Summary, businesstype_Premium_Summary, ProductType_Premium_Summary, pie_ODNetPremium_Summary, pie_ODNetMonthlyPremium, pie_ODNetDailyPremium, DashBoardInsuranceCompany, pie_Premium_Summary_Vehicle.",
)
async def get_dashboard_summary(
    chart_type: str = Query("premium_summary", description="Target chart type or dimension (od_net, insurer, vehicle_type, premium_summary)"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> DashboardChartDataResponse:
    service = SearchService(session)
    return await service.get_dashboard_summary(current_user=current_user, chart_type=chart_type)


@router.get(
    "/server-status",
    response_model=ServerStatusResponse,
    summary="Server operational status heartbeat",
    description="Maps SearchMethods.aspx.cs::getserverInactive.",
)
async def get_server_status(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ServerStatusResponse:
    service = SearchService(session)
    return await service.get_server_status()
