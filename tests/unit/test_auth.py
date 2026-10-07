import pytest
import jwt
from fastapi import HTTPException
from app.core.config import settings
from app.core.security import decode_access_token, create_access_token
from app.core.dependencies import require_roles
from app.models.user import User, UserRole
from app.schemas.auth import LoginRequest, LoginResponse, UserRead


def test_user_and_role_models():
    """Verify physical table mappings and column structures for User and UserRole."""
    assert UserRole.__tablename__ == "tbl_userrole"
    assert User.__tablename__ == "tbl_user"

    assert [c.name for c in UserRole.__table__.primary_key.columns] == ["UserRoleId"]
    assert [c.name for c in User.__table__.primary_key.columns] == ["UserId"]

    assert len(UserRole.__table__.columns) == 4
    assert len(User.__table__.columns) == 13

    # Verify physical columns in tbl_user
    user_cols = {c.name for c in User.__table__.columns}
    assert "UserPassword" in user_cols
    assert "UserName" in user_cols
    assert "UserRoleId" in user_cols
    assert "BranchId" in user_cols
    assert "isdeleted" in user_cols
    assert "mobile_no" in user_cols


def test_user_and_role_active_property():
    """Verify is_active property based on isdeleted column."""
    active_role = UserRole(isdeleted="0")
    deleted_role = UserRole(isdeleted="1")
    assert active_role.is_active is True
    assert deleted_role.is_active is False

    active_user = User(isdeleted="0")
    deleted_user = User(isdeleted="1")
    assert active_user.is_active is True
    assert deleted_user.is_active is False


def test_jwt_invalid_signature():
    """Verify decoding a token with an invalid signature raises HTTP 401."""
    token = jwt.encode(
        {"sub": "1"},
        "wrong-secret-key-12345-that-is-at-least-32-bytes-long",
        algorithm=settings.JWT_ALGORITHM,
    )
    with pytest.raises(HTTPException) as exc_info:
        decode_access_token(token)
    assert exc_info.value.status_code == 401


def test_jwt_malformed_token():
    """Verify decoding a malformed token string raises HTTP 401."""
    with pytest.raises(HTTPException) as exc_info:
        decode_access_token("this.is.not.a.valid.jwt")
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_require_roles_checker_logic():
    """Verify require_roles dependency authorizes valid roles and raises 403 on invalid roles."""
    admin_checker = require_roles("ADMIN", "OWNER")

    # User with ADMIN role
    admin_user = User(UserId=1, UserName="admin_user")
    setattr(admin_user, "role_name", "ADMIN")
    result = await admin_checker(admin_user)
    assert result.UserId == 1

    # User with OWNER role (case-insensitive test)
    owner_user = User(UserId=2, UserName="owner_user")
    setattr(owner_user, "role_name", "owner")
    result = await admin_checker(owner_user)
    assert result.UserId == 2

    # User with AGENT role (forbidden)
    agent_user = User(UserId=3, UserName="agent_user")
    setattr(agent_user, "role_name", "AGENT")
    with pytest.raises(HTTPException) as exc_info:
        await admin_checker(agent_user)
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Insufficient permissions for this operation"

    # User with None role (forbidden)
    no_role_user = User(UserId=4, UserName="norole")
    setattr(no_role_user, "role_name", None)
    with pytest.raises(HTTPException) as exc_info:
        await admin_checker(no_role_user)
    assert exc_info.value.status_code == 403


def test_safe_user_schema_never_contains_password():
    """Verify UserRead schema does not have password attributes."""
    schema_fields = UserRead.model_fields.keys()
    assert "password" not in schema_fields
    assert "UserPassword" not in schema_fields
    assert "hashed_password" not in schema_fields
