from typing import Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.rbac import resolve_principal_context
from app.core.security import verify_password, get_password_hash, create_access_token
from app.models.user import User, UserRole
from app.repositories.user import UserRepository
from app.repositories.role import RoleRepository
from app.repositories.login_history import LoginHistoryRepository
from app.schemas.auth import LoginResponse, UserRead


class AuthService:
    """
    Authentication & RBAC Domain Service.
    Coordinates credential verification, legacy plaintext compatibility,
    local database bcrypt password upgrades, active-role validation,
    principal context resolution, and JWT issuance.
    
    Contains strictly business authentication rules without HTTP/FastAPI bindings.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.user_repo = UserRepository(session)
        self.role_repo = RoleRepository(session)
        self.history_repo = LoginHistoryRepository(session)

    async def authenticate(
        self, username: str, password: str
    ) -> Tuple[Optional[User], Optional[UserRole], Optional[str]]:
        """
        Authenticates a user by username and password.
        
        Returns:
            Tuple[Optional[User], Optional[UserRole], Optional[str]]:
                (user, role, error_code)
                error_code can be:
                - None: Authentication successful
                - "invalid_credentials": Username not found or password incorrect
                - "inactive_user": User account is inactive / marked deleted
                - "inactive_role": Assigned role does not exist or is marked deleted (GAP-5F-04)
        """
        if not username or not password:
            return None, None, "invalid_credentials"

        user = await self.user_repo.get_by_username(username)
        if not user:
            return None, None, "invalid_credentials"

        # Check user active status (legacy isdeleted != '1')
        if not user.is_active:
            return None, None, "inactive_user"

        # Resolve and validate role active status (GAP-5F-04: role.isdeleted != '1')
        role: Optional[UserRole] = None
        if user.UserRoleId is not None:
            role = await self.role_repo.get_by_id(user.UserRoleId)
            if not role or not role.is_active:
                return None, None, "inactive_role"

        # Verify password (dual-mode bcrypt or legacy plaintext)
        is_valid, needs_upgrade = verify_password(password, user.UserPassword or "")
        if not is_valid:
            return None, None, "invalid_credentials"

        # If legacy plaintext matched, transparently upgrade password in LOCAL development database
        if needs_upgrade:
            new_hash = get_password_hash(password)
            await self.user_repo.update_password(user, new_hash)
            await self.session.commit()

        return user, role, None

    async def login(
        self, username: str, password: str, ip_address: Optional[str] = None
    ) -> Tuple[Optional[LoginResponse], Optional[str]]:
        """
        High-level authentication flow generating JWT access token upon success.
        
        Returns:
            Tuple[Optional[LoginResponse], Optional[str]]:
                (login_response, error_code)
        """
        user, role, error = await self.authenticate(username, password)
        if error or not user:
            try:
                found_user = await self.user_repo.get_by_username(username)
                uid = found_user.UserId if found_user else None
                await self.history_repo.create_log(
                    user_id=uid,
                    username=username,
                    action="FAILED_LOGIN",
                    fun_perform="Login Failed",
                    ip_address=ip_address,
                    remark=f"Failed reason: {error}",
                )
                await self.session.commit()
            except Exception:
                pass
            return None, error

        # Record successful login history
        try:
            await self.history_repo.create_log(
                user_id=user.UserId,
                username=user.UserName,
                action="LOGIN",
                fun_perform="User Logged In",
                ip_address=ip_address,
                remark="Success",
            )
            await self.session.commit()
        except Exception:
            pass

        principal = await resolve_principal_context(self.session, user, role)

        # Build non-sensitive token claims
        token_claims = {
            "sub": str(user.UserId),
            "username": user.UserName,
            "role": principal.role_name,
            "role_id": user.UserRoleId,
            "branch_id": user.BranchId,
            "agent_id": principal.agent_id,
            "emp_id": principal.emp_id,
            "employee_id": principal.employee_id,
            "franchise_id": principal.franchise_id,
        }
        token = create_access_token(token_claims)
        expires_in = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60

        response = LoginResponse(
            access_token=token,
            token_type="bearer",
            expires_in=expires_in,
            user=UserRead(
                user_id=user.UserId,
                username=user.UserName or "",
                role=principal.role_name,
                role_id=user.UserRoleId,
                branch_id=user.BranchId,
                agent_id=principal.agent_id,
                emp_id=principal.emp_id,
                employee_id=principal.employee_id,
                franchise_id=principal.franchise_id,
                mobile_no=user.mobile_no,
                is_active=user.is_active,
            )
        )
        return response, None
