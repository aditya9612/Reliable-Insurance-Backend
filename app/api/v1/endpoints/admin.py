"""
FastAPI Endpoints for Phase 16B — Admin Dashboard Counters & Dynamic Menu Privileges.
CRITICAL SECURITY: Dynamic menu privileges are for UI PRESENTATION ONLY.
Backend authorization remains strictly enforced by require_roles / server-side RBAC dependencies.
"""
from typing import Optional
from fastapi import APIRouter, Depends, Query, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db, get_current_user, require_roles
from app.core.rbac import GLOBAL_ADMIN_ROLES
from app.models.user import User
from app.schemas.admin_dashboard import AdminCountersResponse
from app.schemas.privilege import (
    RolePrivilegeAssignRequest,
    RolePrivilegeAssignResponse,
    DynamicMenuTreeResponse,
)
from app.services.admin_dashboard_service import AdminDashboardService
from app.services.privilege_service import PrivilegeService

router = APIRouter()


@router.get(
    "/dashboard/counters",
    response_model=AdminCountersResponse,
    dependencies=[Depends(require_roles(*GLOBAL_ADMIN_ROLES))],
    summary="Get Administrative Overview Counters",
    description="Returns aggregate counts of users, active users, locked users, agents, employees, franchises, and pending KYC.",
)
async def get_dashboard_counters(
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AdminCountersResponse:
    service = AdminDashboardService(session)
    return await service.get_counters()


@router.get(
    "/privileges/role/{role_id}",
    response_model=DynamicMenuTreeResponse,
    dependencies=[Depends(require_roles(*GLOBAL_ADMIN_ROLES))],
    summary="Get Dynamic UI Navigation Tree for Role",
    description="Returns hierarchical UI presentation tree for the specified role. Presentation only.",
)
async def get_role_privilege_tree(
    role_id: int = Path(..., ge=1),
    branch_id: Optional[int] = Query(None, description="Optional Branch ID scope"),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DynamicMenuTreeResponse:
    service = PrivilegeService(session)
    return await service.get_menu_tree_for_role(role_id, branch_id)


@router.post(
    "/privileges",
    response_model=RolePrivilegeAssignResponse,
    dependencies=[Depends(require_roles(*GLOBAL_ADMIN_ROLES))],
    summary="Assign Screen / Menu Privileges to Role",
    description="Sets presentation screen permissions for a role in tbl_role_privilege.",
)
async def assign_role_privileges(
    payload: RolePrivilegeAssignRequest,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> RolePrivilegeAssignResponse:
    service = PrivilegeService(session)
    return await service.assign_privileges(
        role_id=payload.role_id,
        screen_ids=payload.screen_ids,
        branch_id=payload.branch_id,
    )
