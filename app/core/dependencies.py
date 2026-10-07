"""
Core FastAPI Dependency Injection Exports.
Provides unified access to database sessions, security tokens, cache clients,
current authenticated user context, role-based authorization (RBAC), and branch scoping.
"""
from typing import Optional, Dict, Any, Callable, List
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.rbac import PrincipalContext, resolve_principal_context
from app.core.security import get_current_token_payload, oauth2_scheme
from app.core.redis import get_redis_client
from app.models.user import User, UserRole
from app.repositories.user import UserRepository
from app.repositories.role import RoleRepository


async def get_current_user(
    token_payload: Dict[str, Any] = Depends(get_current_token_payload),
    session: AsyncSession = Depends(get_db),
) -> User:
    """
    Extracts authenticated user identity from validated JWT payload,
    fetches the live user record from the local database, confirms active status
    for both the user and their assigned role (GAP-5F-04), and resolves the
    server-side principal context (GAP-5F-03).
    
    Raises:
        HTTPException 401 if user or assigned role does not exist or is inactive / deleted.
    """
    subject = token_payload.get("sub")
    if not subject:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id = int(subject)
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_repo = UserRepository(session)
    user = await user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive or disabled",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Validate assigned role exists and is active (GAP-5F-04: role.isdeleted != '1')
    role_repo = RoleRepository(session)
    role: Optional[UserRole] = None
    if user.UserRoleId is not None:
        role = await role_repo.get_by_id(user.UserRoleId)
        if not role or not role.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Assigned user role is inactive or disabled",
                headers={"WWW-Authenticate": "Bearer"},
            )

    # Resolve full principal context strictly from server-side database relationships (GAP-5F-03)
    await resolve_principal_context(session, user, role)

    return user


async def get_current_principal(
    current_user: User = Depends(get_current_user),
) -> PrincipalContext:
    """
    Returns the server-resolved PrincipalContext for the authenticated user.
    Never trusts client-supplied AgentId, EmpId, FranchiseId, BranchId, or UserId.
    """
    principal = getattr(current_user, "principal_context", None)
    if isinstance(principal, PrincipalContext):
        return principal
    return PrincipalContext(
        user_id=current_user.UserId,
        username=current_user.UserName,
        role_id=current_user.UserRoleId,
        role_name=getattr(current_user, "role_name", None),
        branch_id=current_user.BranchId,
        agent_id=getattr(current_user, "agent_id", None),
        emp_id=getattr(current_user, "emp_id", None),
        employee_id=getattr(current_user, "employee_id", None),
        franchise_id=getattr(current_user, "franchise_id", None),
    )


def require_roles(*allowed_roles: str) -> Callable[[User], User]:
    """
    Factory creating a FastAPI dependency for role-based authorization (RBAC).
    
    Usage:
        @router.get("/admin-only", dependencies=[Depends(require_roles("ADMIN", "OWNER"))])
        async def admin_endpoint(...):
            ...
            
    Behavior:
        - Unauthenticated request: HTTP 401 (handled by get_current_user)
        - Authenticated user lacking allowed role: HTTP 403 Forbidden
    """
    normalized_allowed = [r.strip().upper() for r in allowed_roles if r]

    async def role_checker(
        current_user: User = Depends(get_current_user)
    ) -> User:
        if not normalized_allowed:
            return current_user

        user_role = getattr(current_user, "role_name", None)
        if not user_role or user_role.strip().upper() not in normalized_allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions for this operation",
            )
        return current_user

    return role_checker


async def get_current_branch_id(
    current_user: User = Depends(get_current_user)
) -> Optional[int]:
    """
    Extracts the authenticated user's branch jurisdiction.
    Cannot be overridden by client query params or headers.
    """
    return current_user.BranchId


__all__ = [
    "get_db",
    "get_current_token_payload",
    "oauth2_scheme",
    "get_redis_client",
    "get_current_user",
    "get_current_principal",
    "require_roles",
    "get_current_branch_id",
]
