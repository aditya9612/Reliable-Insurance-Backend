"""
Dashboard Endpoints for Phase 14 — Block A.
Provides executive 12-month performance matrix, accounts summary, owner KPIs,
cut & pay net remittances, and agent outstanding receivables.
"""
from datetime import date
from typing import Optional, Literal
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.dependencies import get_current_principal, require_roles
from app.core.rbac import PrincipalContext
from app.services.report_service import ReportService
from app.schemas.report import (
    AdminDashboardResponse,
    AccountsSummaryResponse,
    OwnerDashboardResponse,
    CutAndPaySummaryResponse,
    AgentOutstandingResponse,
)

router = APIRouter()


@router.get(
    "/admin",
    response_model=AdminDashboardResponse,
    status_code=status.HTTP_200_OK,
    summary="Admin Main Dashboard — 12-Month Performance Matrix",
    dependencies=[Depends(require_roles("OWNER", "ADMIN", "IT SUPPORT", "ACCOUNT", "ACCOUNT HEAD"))],
)
async def get_admin_dashboard(
    financial_year: str = Query(..., description="Indian FY e.g. 2025-2026"),
    broker: Optional[str] = Query(None, description="Optional broker entity filter"),
    date_mode: Literal["T_Date", "R_Date"] = Query("T_Date", description="T_Date: Entry date, R_Date: Risk start date"),
    branch_id: Optional[int] = Query(None, description="Optional branch ID filter"),
    principal: PrincipalContext = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db),
) -> AdminDashboardResponse:
    service = ReportService(session)
    data = await service.get_admin_dashboard(
        financial_year=financial_year,
        broker=broker,
        date_mode=date_mode,
        branch_id=branch_id,
        principal=principal,
    )
    return AdminDashboardResponse(**data)


@router.get(
    "/accounts-summary",
    response_model=AccountsSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Accounts Summary Dashboard — Cash vs Cheque vs Online Collections",
    dependencies=[Depends(require_roles("OWNER", "ADMIN", "ACCOUNT", "ACCOUNT HEAD", "IT SUPPORT"))],
)
async def get_accounts_summary(
    from_date: date = Query(..., description="Start date"),
    to_date: date = Query(..., description="End date"),
    branch_id: Optional[int] = Query(None, description="Optional branch filter"),
    principal: PrincipalContext = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db),
) -> AccountsSummaryResponse:
    service = ReportService(session)
    data = await service.get_accounts_summary(
        from_date=from_date,
        to_date=to_date,
        branch_id=branch_id,
        principal=principal,
    )
    return AccountsSummaryResponse(**data)


@router.get(
    "/owner",
    response_model=OwnerDashboardResponse,
    status_code=status.HTTP_200_OK,
    summary="Owner Dashboard — High-Level Broker & Channel Splits",
    dependencies=[Depends(require_roles("OWNER", "ADMIN"))],
)
async def get_owner_dashboard(
    from_date: date = Query(..., description="Start date"),
    to_date: date = Query(..., description="End date"),
    principal: PrincipalContext = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db),
) -> OwnerDashboardResponse:
    service = ReportService(session)
    data = await service.get_owner_dashboard(from_date=from_date, to_date=to_date, principal=principal)
    return OwnerDashboardResponse(**data)


@router.get(
    "/agent-cut-pay",
    response_model=CutAndPaySummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Agent Cut & Pay Dashboard — Net Remittance Tracker",
    dependencies=[Depends(require_roles("OWNER", "ADMIN", "ACCOUNT", "ACCOUNT HEAD", "LOCATION HEAD", "BRANCH MANAGER"))],
)
async def get_agent_cut_pay(
    financial_year: str = Query(..., description="Indian FY e.g. 2025-2026"),
    month: Optional[str] = Query(None, description="Optional month name"),
    branch_id: Optional[int] = Query(None, description="Optional branch filter"),
    principal: PrincipalContext = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db),
) -> CutAndPaySummaryResponse:
    service = ReportService(session)
    data = await service.get_cut_and_pay_summary(
        financial_year=financial_year,
        month=month,
        branch_id=branch_id,
        principal=principal,
    )
    return CutAndPaySummaryResponse(**data)


@router.get(
    "/agent-outstanding",
    response_model=AgentOutstandingResponse,
    status_code=status.HTTP_200_OK,
    summary="Agent Outstanding Receivables Dashboard with Aging",
    dependencies=[Depends(require_roles("OWNER", "ADMIN", "ACCOUNT", "ACCOUNT HEAD", "LOCATION HEAD", "BRANCH MANAGER"))],
)
async def get_agent_outstanding(
    branch_id: Optional[int] = Query(None, description="Optional branch filter"),
    min_days_overdue: int = Query(0, ge=0, description="Minimum days overdue filter"),
    principal: PrincipalContext = Depends(get_current_principal),
    session: AsyncSession = Depends(get_db),
) -> AgentOutstandingResponse:
    service = ReportService(session)
    data = await service.get_agent_outstanding(
        branch_id=branch_id,
        min_days_overdue=min_days_overdue,
        principal=principal,
    )
    return AgentOutstandingResponse(**data)
