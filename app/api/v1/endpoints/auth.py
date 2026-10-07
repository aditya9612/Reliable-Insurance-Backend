from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db, get_current_user, require_roles
from app.core.rbac import GLOBAL_ADMIN_ROLES
from app.models.user import User
from app.schemas.auth import LoginRequest, LoginResponse, UserRead
from app.services.auth import AuthService

router = APIRouter()


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Authenticate user and issue JWT token",
    description="Validates credentials against local development database. Supports dual-mode bcrypt and legacy plaintext upgrade.",
)
async def login(
    payload: LoginRequest,
    session: AsyncSession = Depends(get_db),
) -> LoginResponse:
    """
    Authenticate user with username and password.
    Returns signed JWT Bearer access token upon successful authentication.
    """
    service = AuthService(session)
    response, error = await service.login(payload.username, payload.password)
    
    if error == "inactive_user":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive or disabled",
            headers={"WWW-Authenticate": "Bearer"},
        )
    elif error == "inactive_role":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Assigned user role is inactive or disabled",
            headers={"WWW-Authenticate": "Bearer"},
        )
    elif error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    return response


@router.get(
    "/me",
    response_model=UserRead,
    summary="Get current authenticated user profile",
    description="Returns sanitized profile of the currently authenticated user from Bearer token.",
)
async def get_me(
    current_user: User = Depends(get_current_user),
) -> UserRead:
    """
    Retrieve current authenticated user context.
    CRITICAL SECURITY: Never returns passwords, password hashes, or credentials.
    """
    return UserRead(
        user_id=current_user.UserId,
        username=current_user.UserName or "",
        role=getattr(current_user, "role_name", None),
        role_id=current_user.UserRoleId,
        branch_id=current_user.BranchId,
        agent_id=getattr(current_user, "agent_id", None),
        emp_id=getattr(current_user, "emp_id", None),
        employee_id=getattr(current_user, "employee_id", None),
        franchise_id=getattr(current_user, "franchise_id", None),
        mobile_no=current_user.mobile_no,
        is_active=current_user.is_active,
    )


@router.get(
    "/admin-check",
    dependencies=[Depends(require_roles(*GLOBAL_ADMIN_ROLES))],
    summary="RBAC validation endpoint for global administrative roles",
    description="Endpoint restricted strictly to verified global admin roles (OWNER, ADMIN, IT SUPPORT). Returns 403 Forbidden for other authenticated roles.",
)
async def admin_check(current_user: User = Depends(get_current_user)) -> dict:
    """RBAC validation endpoint accessible only to global administrative roles."""
    return {
        "status": "authorized",
        "user_id": current_user.UserId,
        "role": getattr(current_user, "role_name", None),
    }
