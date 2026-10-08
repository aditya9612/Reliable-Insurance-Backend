"""
FastAPI Endpoints for Phase 16B — User Management, Password Lifecycle & Roles Directory.
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, Query, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db, get_current_user, require_roles
from app.core.rbac import GLOBAL_ADMIN_ROLES
from app.models.user import User
from app.schemas.user import (
    UserCreate,
    UserUpdate,
    UserResponse,
    UserListResponse,
    UserPasswordResetRequest,
    UserPasswordChangeRequest,
    UserStatusUpdateRequest,
    UserRoleResponse,
    UsernameCheckResponse,
)
from app.services.user_service import UserService

router = APIRouter()


@router.get(
    "",
    response_model=UserListResponse,
    summary="List users with branch scoping and role filtering",
)
async def list_users(
    search: Optional[str] = Query(None, description="Search by username or mobile"),
    branch_id: Optional[int] = Query(None, description="Filter by Branch ID"),
    role_id: Optional[int] = Query(None, description="Filter by Role ID"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> UserListResponse:
    service = UserService(session)
    items, total = await service.list_users(
        current_user=current_user,
        search=search,
        branch_id=branch_id,
        role_id=role_id,
        is_active=is_active,
        offset=offset,
        limit=limit,
    )
    return UserListResponse(
        items=[UserResponse.model_validate(u) for u in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/check-username",
    response_model=UsernameCheckResponse,
    summary="Check username availability",
)
async def check_username(
    username: str = Query(..., min_length=1),
    session: AsyncSession = Depends(get_db),
) -> UsernameCheckResponse:
    service = UserService(session)
    return await service.check_username(username)


@router.get(
    "/roles",
    response_model=List[UserRoleResponse],
    summary="List available user roles",
)
async def list_roles(
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[UserRoleResponse]:
    service = UserService(session)
    roles = await service.list_roles()
    return [UserRoleResponse.model_validate(r) for r in roles]


@router.get(
    "/{id}",
    response_model=UserResponse,
    summary="Get user details by ID",
)
async def get_user(
    id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> UserResponse:
    service = UserService(session)
    user = await service.get_user_by_id(id, current_user)
    return UserResponse.model_validate(user)


@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(*GLOBAL_ADMIN_ROLES, "HR"))],
    summary="Create system user account",
)
async def create_user(
    payload: UserCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> UserResponse:
    service = UserService(session)
    user = await service.create_user(payload, current_user)
    return UserResponse.model_validate(user)


@router.put(
    "/{id}",
    response_model=UserResponse,
    dependencies=[Depends(require_roles(*GLOBAL_ADMIN_ROLES, "HR"))],
    summary="Update system user account",
)
async def update_user(
    payload: UserUpdate,
    id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> UserResponse:
    service = UserService(session)
    user = await service.update_user(id, payload, current_user)
    return UserResponse.model_validate(user)


@router.put(
    "/{id}/password",
    response_model=UserResponse,
    summary="Reset user password (admin reset or self change)",
)
async def reset_password(
    payload: UserPasswordResetRequest,
    id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> UserResponse:
    service = UserService(session)
    user = await service.reset_password(id, payload.new_password, current_user)
    return UserResponse.model_validate(user)


@router.patch(
    "/{id}/status",
    response_model=UserResponse,
    dependencies=[Depends(require_roles(*GLOBAL_ADMIN_ROLES))],
    summary="Toggle user active / lock status",
)
async def update_user_status(
    payload: UserStatusUpdateRequest,
    id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> UserResponse:
    service = UserService(session)
    user = await service.update_status(id, payload, current_user)
    return UserResponse.model_validate(user)
