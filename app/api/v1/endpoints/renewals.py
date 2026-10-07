"""
FastAPI Router for Phase 13 Block E — Policy Renewal Engine & CRM.
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, Query, Path, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.dependencies import get_db, get_current_user, require_roles
from app.core.rbac import (
    GLOBAL_ADMIN_ROLES,
    RENEWAL_TELECALLER_ROLES,
    RENEWAL_DASHBOARD_ROLES,
    _AGENT_ROLES_UPPER,
    _EMPLOYEE_ROLES_UPPER,
    _normalize,
)
from app.models.user import User
from app.schemas.renewal import (
    ExpiringPolicyResponse,
    CreateRenewalFollowupRequest,
    UpdateRenewalStatusRequest,
    RenewalFollowupResponse,
    RenewalDashboardResponse,
)
from app.services.renewal_service import RenewalService

router = APIRouter()


@router.get(
    "/due",
    response_model=List[ExpiringPolicyResponse],
    status_code=status.HTTP_200_OK,
    summary="Query Expiring Policies Due for Renewal",
    description=(
        "Retrieves policies nearing expiration within specified days ahead window. "
        "Strictly scoped by tenancy: Agents see only own policies; Sales Executives see assigned team; "
        "Branch users see own branch; Admins have cross-branch visibility."
    ),
)
async def get_due_renewals(
    days_ahead: int = Query(default=30, ge=1, le=365, description="Number of days ahead to scan"),
    branch_id: Optional[int] = Query(default=None, description="Optional branch filter (Admin only)"),
    agent_id: Optional[int] = Query(default=None, description="Optional agent filter"),
    executive_id: Optional[int] = Query(default=None, description="Optional sales executive filter"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> List[ExpiringPolicyResponse]:
    """Lists expiring policies with role-aware multi-tenant scoping."""
    service = RenewalService(session)
    user_role_str = getattr(current_user, "role_name", None) or ""
    norm_role = _normalize(user_role_str)

    effective_branch = branch_id
    effective_agent = agent_id
    effective_exec = executive_id

    # Enforce scoping for non-global-admin roles
    if norm_role not in GLOBAL_ADMIN_ROLES:
        if norm_role in _AGENT_ROLES_UPPER or getattr(current_user, "agent_id", None) or getattr(current_user, "partner_user_id", None):
            effective_agent = getattr(current_user, "agent_id", None) or getattr(current_user, "partner_user_id", None) or current_user.UserId
        elif norm_role in _EMPLOYEE_ROLES_UPPER or getattr(current_user, "emp_id", None):
            effective_exec = getattr(current_user, "emp_id", None) or current_user.UserId
        
        # Scoped branch enforcement
        if current_user.BranchId and current_user.BranchId > 0:
            effective_branch = current_user.BranchId

    items, _ = await service.get_due_renewals(
        days_ahead=days_ahead,
        branch_id=effective_branch,
        agent_id=effective_agent,
        executive_id=effective_exec,
        offset=skip,
        limit=limit,
    )
    return items


@router.get(
    "/followups",
    response_model=List[RenewalFollowupResponse],
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_roles(*RENEWAL_TELECALLER_ROLES))],
    summary="List Telecaller Follow-Up CRM Records",
    description="Lists active telecaller follow-up entries for expiring policies, filtered by FY or status.",
)
async def list_followups(
    financial_year: Optional[str] = Query(default=None, description="Financial year filter (e.g. 2024-2025)"),
    status: Optional[str] = Query(default=None, description="Status filter: Follow, Done, Lost, Vehicle"),
    branch_id: Optional[int] = Query(default=None, description="Branch filter"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> List[RenewalFollowupResponse]:
    """Lists telecaller follow-ups with branch scoping."""
    service = RenewalService(session)
    user_role_str = getattr(current_user, "role_name", None) or ""
    norm_role = _normalize(user_role_str)

    effective_branch = branch_id
    if norm_role not in GLOBAL_ADMIN_ROLES and current_user.BranchId and current_user.BranchId > 0:
        effective_branch = current_user.BranchId

    items, _ = await service.get_followups(
        financial_year=financial_year,
        status_filter=status,
        branch_id=effective_branch,
        offset=skip,
        limit=limit,
    )
    return items


@router.post(
    "/followups",
    response_model=RenewalFollowupResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(*RENEWAL_TELECALLER_ROLES))],
    summary="Record Telecaller Follow-Up Interaction",
    description=(
        "Records customer callback remark, reschedules followup_date, and logs "
        "audit trail into tbl_renewal_followup_history. Replaces legacy Sp_InsertFollowPreYearRenewalStatus."
    ),
)
async def create_followup(
    payload: CreateRenewalFollowupRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> RenewalFollowupResponse:
    """Records telecaller follow-up note and schedules next callback."""
    service = RenewalService(session)
    recorded_by = current_user.UserName or f"user_{current_user.UserId}"
    return await service.record_followup(
        payload=payload,
        recorded_by=recorded_by,
        user_role_id=current_user.UserRoleId,
        agent_id=getattr(current_user, "agent_id", None) or 0,
        executive_id=getattr(current_user, "emp_id", None) or 0,
        branch_id=current_user.BranchId,
    )


@router.put(
    "/{id}/status",
    response_model=RenewalFollowupResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_roles(*RENEWAL_TELECALLER_ROLES))],
    summary="Update Renewal Status",
    description=(
        "Transitions renewal status to one of: Follow, Done, Lost, Vehicle. "
        "Appends remark to history log. Replaces legacy Sp_UpdatePreYearRenewalStatus."
    ),
)
async def update_renewal_status(
    id: int = Path(..., description="Renewal record primary key ID"),
    payload: UpdateRenewalStatusRequest = ...,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> RenewalFollowupResponse:
    """Updates renewal status lifecycle state."""
    service = RenewalService(session)
    updated_by = current_user.UserName or f"user_{current_user.UserId}"
    return await service.update_renewal_status(
        status_id=id,
        payload=payload,
        updated_by=updated_by,
    )


@router.get(
    "/dashboard",
    response_model=RenewalDashboardResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_roles(*RENEWAL_DASHBOARD_ROLES))],
    summary="Executive Renewal Performance Dashboard",
    description=(
        "Aggregates summary status metrics, Sales Executive distribution breakdown, "
        "and Insurance Company retention rates for the given financial year and optional month. "
        "Replaces legacy Dashboard_PrevYearRenewalStatus."
    ),
)
async def get_renewal_dashboard(
    financial_year: Optional[str] = Query(default=None, description="Financial year (e.g. 2024-2025)"),
    month: Optional[int] = Query(default=None, ge=1, le=12, description="Month filter (1-12)"),
    branch_id: Optional[int] = Query(default=None, description="Branch filter (Admin only)"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> RenewalDashboardResponse:
    """Aggregates executive renewal metrics and breakdown."""
    service = RenewalService(session)
    user_role_str = getattr(current_user, "role_name", None) or ""
    norm_role = _normalize(user_role_str)

    effective_branch = branch_id
    if norm_role not in GLOBAL_ADMIN_ROLES and current_user.BranchId and current_user.BranchId > 0:
        effective_branch = current_user.BranchId

    return await service.get_dashboard(
        financial_year=financial_year,
        month=month,
        branch_id=effective_branch,
    )
