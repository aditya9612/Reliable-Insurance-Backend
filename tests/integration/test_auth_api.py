import uuid
from datetime import timedelta
import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash, create_access_token
from app.models.user import User, UserRole
from app.repositories.user import UserRepository
from app.repositories.role import RoleRepository


@pytest.fixture(autouse=True)
async def cleanup_auth_tables(db_session: AsyncSession):
    """Ensures complete test isolation by cleaning tbl_user and tbl_userrole."""
    await db_session.execute(text("DELETE FROM tbl_user;"))
    await db_session.execute(text("DELETE FROM tbl_userrole;"))
    await db_session.commit()
    yield
    await db_session.execute(text("DELETE FROM tbl_user;"))
    await db_session.execute(text("DELETE FROM tbl_userrole;"))
    await db_session.commit()


@pytest.mark.asyncio
async def test_login_success_bcrypt(async_client: AsyncClient, db_session: AsyncSession):
    """Verify login with modern bcrypt password returns valid JWT and safe user context."""
    user_repo = UserRepository(db_session)
    role_repo = RoleRepository(db_session)

    username = f"admin_{uuid.uuid4().hex[:8]}"

    # 1. Create role
    role = UserRole(UserRole="ADMIN", code="ADM", isdeleted="0")
    await role_repo.create(role)

    # 2. Create user with bcrypt password
    user = User(
        UserName=username,
        UserPassword=get_password_hash("AdminPass123!"),
        UserRoleId=role.UserRoleId,
        BranchId=101,
        isdeleted="0",
        mobile_no="9998887770",
    )
    await user_repo.create(user)
    await db_session.commit()

    # 3. Call login endpoint
    response = await async_client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": "AdminPass123!"},
    )
    assert response.status_code == 200
    data = response.json()

    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] > 0
    assert data["user"]["username"] == username
    assert data["user"]["role"] == "ADMIN"
    assert data["user"]["branch_id"] == 101

    # CRITICAL: Verify passwords and hashes are never exposed in login response
    raw_text = response.text
    assert "AdminPass123!" not in raw_text
    assert "$2b$" not in raw_text


@pytest.mark.asyncio
async def test_login_legacy_plaintext_and_auto_upgrade(async_client: AsyncClient, db_session: AsyncSession):
    """
    Verify legacy plaintext password authentication and transparent automatic
    upgrade to bcrypt in the local development database.
    """
    user_repo = UserRepository(db_session)
    role_repo = RoleRepository(db_session)

    username = f"legacy_{uuid.uuid4().hex[:8]}"
    role = UserRole(UserRole="SUPERVISOR", code="SUP", isdeleted="0")
    await role_repo.create(role)

    # 1. Create user with legacy plaintext password
    legacy_plain = "OldPlaintextPassword2026"
    user = User(
        UserName=username,
        UserPassword=legacy_plain,  # PLAINTEXT
        UserRoleId=role.UserRoleId,
        BranchId=102,
        isdeleted="0",
    )
    await user_repo.create(user)
    await db_session.commit()

    # Verify initial password stored is plaintext
    db_user_before = await user_repo.get_by_id(user.UserId)
    assert db_user_before.UserPassword == legacy_plain

    # 2. Login with plaintext password
    response = await async_client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": legacy_plain},
    )
    assert response.status_code == 200
    assert "access_token" in response.json()

    # 3. Verify in local DB that password was upgraded to bcrypt
    await db_session.refresh(user)
    upgraded_pass = user.UserPassword
    assert upgraded_pass != legacy_plain
    assert upgraded_pass.startswith(("$2a$", "$2b$", "$2y$"))

    # 4. Verify subsequent login succeeds with bcrypt
    response2 = await async_client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": legacy_plain},
    )
    assert response2.status_code == 200


@pytest.mark.asyncio
async def test_login_invalid_password(async_client: AsyncClient, db_session: AsyncSession):
    """Verify wrong password returns generic HTTP 401 Unauthorized."""
    user_repo = UserRepository(db_session)
    username = f"user_{uuid.uuid4().hex[:8]}"
    user = User(
        UserName=username,
        UserPassword=get_password_hash("CorrectPassword"),
        isdeleted="0",
    )
    await user_repo.create(user)
    await db_session.commit()

    response = await async_client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": "WrongPassword"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["message"] == "Invalid username or password"


@pytest.mark.asyncio
async def test_login_nonexistent_user(async_client: AsyncClient):
    """Verify non-existent user returns generic HTTP 401 Unauthorized."""
    response = await async_client.post(
        "/api/v1/auth/login",
        json={"username": "non_existent_user_12345", "password": "SomePassword"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["message"] == "Invalid username or password"


@pytest.mark.asyncio
async def test_login_inactive_user_rejected(async_client: AsyncClient, db_session: AsyncSession):
    """Verify inactive/deleted user (isdeleted='1') is rejected with HTTP 401."""
    user_repo = UserRepository(db_session)
    username = f"del_{uuid.uuid4().hex[:8]}"
    user = User(
        UserName=username,
        UserPassword=get_password_hash("SomePassword123!"),
        isdeleted="1",  # INACTIVE / DELETED
    )
    await user_repo.create(user)
    await db_session.commit()

    response = await async_client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": "SomePassword123!"},
    )
    assert response.status_code == 401
    assert "inactive" in response.json()["error"]["message"].lower()


@pytest.mark.asyncio
async def test_login_missing_or_invalid_payload(async_client: AsyncClient):
    """Verify malformed login payloads return 422 Unprocessable Entity."""
    # Missing password
    resp1 = await async_client.post("/api/v1/auth/login", json={"username": "test"})
    assert resp1.status_code == 422

    # Empty payload
    resp2 = await async_client.post("/api/v1/auth/login", json={})
    assert resp2.status_code == 422


@pytest.mark.asyncio
async def test_get_me_endpoint_success_and_safety(async_client: AsyncClient, db_session: AsyncSession):
    """Verify GET /api/v1/auth/me returns safe profile without leaking credentials."""
    user_repo = UserRepository(db_session)
    role_repo = RoleRepository(db_session)

    username = f"mgr_{uuid.uuid4().hex[:8]}"
    role = UserRole(UserRole="MANAGER", code="MGR", isdeleted="0")
    await role_repo.create(role)

    user = User(
        UserName=username,
        UserPassword=get_password_hash("ManagerPass"),
        UserRoleId=role.UserRoleId,
        BranchId=105,
        mobile_no="9876543210",
        isdeleted="0",
    )
    await user_repo.create(user)
    await db_session.commit()

    # Login to obtain token
    login_resp = await async_client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": "ManagerPass"},
    )
    token = login_resp.json()["access_token"]

    # Call /me
    me_resp = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert me_resp.status_code == 200
    data = me_resp.json()

    assert data["username"] == username
    assert data["role"] == "MANAGER"
    assert data["branch_id"] == 105
    assert data["mobile_no"] == "9876543210"
    assert data["is_active"] is True

    # Security verification: never leak password hash
    assert "UserPassword" not in data
    assert "password" not in data


@pytest.mark.asyncio
async def test_get_me_unauthorized_variations(async_client: AsyncClient):
    """Verify missing, invalid, or expired tokens are rejected with 401."""
    # 1. Missing token
    resp1 = await async_client.get("/api/v1/auth/me")
    assert resp1.status_code == 401

    # 2. Invalid token
    resp2 = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid.jwt.token"},
    )
    assert resp2.status_code == 401

    # 3. Expired token
    expired_token = create_access_token({"sub": "1"}, expires_delta=timedelta(minutes=-5))
    resp3 = await async_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert resp3.status_code == 401


@pytest.mark.asyncio
async def test_rbac_authorization_admin_check(async_client: AsyncClient, db_session: AsyncSession):
    """
    Verify RBAC enforcement:
    - ADMIN role -> HTTP 200 OK
    - AGENT role -> HTTP 403 Forbidden
    - Unauthenticated -> HTTP 401 Unauthorized
    """
    user_repo = UserRepository(db_session)
    role_repo = RoleRepository(db_session)

    admin_username = f"admin_{uuid.uuid4().hex[:8]}"
    agent_username = f"agent_{uuid.uuid4().hex[:8]}"

    admin_role = UserRole(UserRole="ADMIN", code="ADM", isdeleted="0")
    agent_role = UserRole(UserRole="AGENT", code="AGT", isdeleted="0")
    await role_repo.create(admin_role)
    await role_repo.create(agent_role)

    admin_user = User(
        UserName=admin_username,
        UserPassword=get_password_hash("Pass123!"),
        UserRoleId=admin_role.UserRoleId,
        isdeleted="0",
    )
    agent_user = User(
        UserName=agent_username,
        UserPassword=get_password_hash("Pass123!"),
        UserRoleId=agent_role.UserRoleId,
        isdeleted="0",
    )
    await user_repo.create(admin_user)
    await user_repo.create(agent_user)
    await db_session.commit()

    # Login as admin
    resp_adm = await async_client.post(
        "/api/v1/auth/login",
        json={"username": admin_username, "password": "Pass123!"},
    )
    admin_token = resp_adm.json()["access_token"]

    # Login as agent
    resp_agt = await async_client.post(
        "/api/v1/auth/login",
        json={"username": agent_username, "password": "Pass123!"},
    )
    agent_token = resp_agt.json()["access_token"]

    # 1. Admin accesses /admin-check -> 200 OK
    check_adm = await async_client.get(
        "/api/v1/auth/admin-check",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert check_adm.status_code == 200
    assert check_adm.json()["status"] == "authorized"

    # 2. Agent accesses /admin-check -> 403 Forbidden
    check_agt = await async_client.get(
        "/api/v1/auth/admin-check",
        headers={"Authorization": f"Bearer {agent_token}"},
    )
    assert check_agt.status_code == 403
    assert check_agt.json()["error"]["message"] == "Insufficient permissions for this operation"

    # 3. Unauthenticated request -> 401 Unauthorized
    check_anon = await async_client.get("/api/v1/auth/admin-check")
    assert check_anon.status_code == 401


@pytest.mark.asyncio
async def test_branch_isolation_context_cannot_be_spoofed(async_client: AsyncClient, db_session: AsyncSession):
    """
    Verify authenticated branch jurisdiction is extracted server-side and
    CANNOT be spoofed or overridden by client parameters or headers.
    """
    user_repo = UserRepository(db_session)
    username = f"officer_{uuid.uuid4().hex[:8]}"
    user = User(
        UserName=username,
        UserPassword=get_password_hash("Pass123!"),
        BranchId=10,  # Assigned to Branch 10 (Pune)
        isdeleted="0",
    )
    await user_repo.create(user)
    await db_session.commit()

    login_resp = await async_client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": "Pass123!"},
    )
    token = login_resp.json()["access_token"]

    # Client attempts to spoof BranchId via query params and headers
    resp = await async_client.get(
        "/api/v1/auth/me?BranchId=99&branch_id=99",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Branch-ID": "99",
            "BranchId": "99",
        },
    )
    assert resp.status_code == 200
    # Server identity strictly preserves assigned BranchId (10)
    assert resp.json()["branch_id"] == 10
