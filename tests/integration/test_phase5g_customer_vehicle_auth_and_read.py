import uuid
from typing import Optional
import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash, create_access_token
from app.models.user import User, UserRole
from app.repositories.user import UserRepository
from app.repositories.role import RoleRepository


@pytest.fixture(autouse=True)
async def cleanup_phase5g_tables(db_session: AsyncSession):
    """Ensure clean Customer & Vehicle state for each Phase 5G integration test."""
    await db_session.execute(text("DELETE FROM tbl_vehicledetails;"))
    await db_session.execute(text("DELETE FROM tbl_customer;"))
    await db_session.commit()
    yield
    await db_session.execute(text("DELETE FROM tbl_vehicledetails;"))
    await db_session.execute(text("DELETE FROM tbl_customer;"))
    await db_session.commit()


async def create_user_with_role(
    db_session: AsyncSession,
    role_name: str,
    branch_id: Optional[int] = 101,
    role_isdeleted: str = "0",
    partner_user_id: Optional[int] = None,
    password: str = "Password123!",
) -> tuple[User, dict[str, str]]:
    """Helper to provision a test user, role, and Bearer authorization header."""
    user_repo = UserRepository(db_session)
    role_repo = RoleRepository(db_session)

    role = UserRole(
        UserRole=role_name,
        code=(role_name[:3].upper() if role_name else "ROL"),
        isdeleted=role_isdeleted,
    )
    await role_repo.create(role)

    username = f"u5g_{role_name[:4].strip().lower()}_{uuid.uuid4().hex[:6]}"
    user = User(
        UserName=username,
        UserPassword=get_password_hash(password),
        UserRoleId=role.UserRoleId,
        BranchId=branch_id,
        partner_user_id=partner_user_id,
        isdeleted="0",
        mobile_no="9876543210",
    )
    await user_repo.create(user)
    await db_session.commit()
    await db_session.refresh(user)

    token = create_access_token({
        "sub": str(user.UserId),
        "username": user.UserName,
        "role": role_name,
        "branch_id": branch_id,
    })
    return user, {"Authorization": f"Bearer {token}"}


# ============================================================================
# 16.1 Role Catalog & Active Role Validation (GAP-5F-02, GAP-5F-04)
# ============================================================================


@pytest.mark.asyncio
async def test_superadmin_is_not_treated_as_admin(
    async_client: AsyncClient, db_session: AsyncSession
):
    """
    16.1.1: Phantom 'SUPERADMIN' role is NOT in the verified legacy catalog and is rejected
    on both /api/v1/auth/admin-check and Customer/Vehicle write APIs (403 Forbidden).
    """
    _, headers_superadmin = await create_user_with_role(
        db_session, role_name="SUPERADMIN", branch_id=0
    )

    admin_resp = await async_client.get("/api/v1/auth/admin-check", headers=headers_superadmin)
    assert admin_resp.status_code == 403

    create_resp = await async_client.post(
        "/api/v1/customers",
        headers=headers_superadmin,
        json={"CustFName": "PHANTOM_SUPERADMIN_TEST", "BranchId": 101},
    )
    assert create_resp.status_code == 403


@pytest.mark.asyncio
async def test_non_admin_with_branch_zero_or_none_is_not_admin(
    async_client: AsyncClient, db_session: AsyncSession
):
    """
    16.1.2 & 16.1.3: Non-admin user (OPERATOR) with BranchId == 0 or BranchId is None
    is NOT treated as a global admin and cannot create or update customers in another branch.
    """
    _, headers_admin = await create_user_with_role(
        db_session, role_name="ADMIN", branch_id=1
    )
    _, headers_op_b0 = await create_user_with_role(
        db_session, role_name="OPERATOR", branch_id=0
    )
    _, headers_op_bnone = await create_user_with_role(
        db_session, role_name="OPERATOR", branch_id=None
    )

    # Admin creates a customer in Branch 202
    c_b202_resp = await async_client.post(
        "/api/v1/customers",
        headers=headers_admin,
        json={"CustFName": "BRANCH202_CUST", "BranchId": 202},
    )
    assert c_b202_resp.status_code == 201
    cust_202_id = c_b202_resp.json()["customer_id"]

    # Operator with BranchId == 0 attempts to create customer in Branch 202 -> pinned to BranchId=0, NOT 202
    op_b0_create = await async_client.post(
        "/api/v1/customers",
        headers=headers_op_b0,
        json={"CustFName": "OP_B0_CUST", "BranchId": 202},
    )
    assert op_b0_create.status_code == 201
    assert op_b0_create.json()["branch_id"] == 0

    # Operator with BranchId == 0 attempts to update Branch 202 customer -> 403 Forbidden
    op_b0_update = await async_client.put(
        f"/api/v1/customers/{cust_202_id}",
        headers=headers_op_b0,
        json={"CustFName": "UNAUTHORIZED_MOD"},
    )
    assert op_b0_update.status_code == 403

    # Operator with BranchId is None attempts to update Branch 202 customer -> 403 Forbidden
    op_bnone_update = await async_client.put(
        f"/api/v1/customers/{cust_202_id}",
        headers=headers_op_bnone,
        json={"CustFName": "UNAUTHORIZED_MOD"},
    )
    assert op_bnone_update.status_code == 403


@pytest.mark.asyncio
async def test_owner_admin_it_support_are_global_admins(
    async_client: AsyncClient, db_session: AsyncSession
):
    """
    16.1.4 & 16.2.8: OWNER, ADMIN, and IT SUPPORT are treated as global admin roles
    on /api/v1/auth/admin-check and cross-branch Customer create/update operations.
    """
    for role_name in ("OWNER", "ADMIN", "IT SUPPORT"):
        _, headers = await create_user_with_role(
            db_session, role_name=role_name, branch_id=10
        )
        chk = await async_client.get("/api/v1/auth/admin-check", headers=headers)
        assert chk.status_code == 200

        # Create customer in remote branch 505
        c_resp = await async_client.post(
            "/api/v1/customers",
            headers=headers,
            json={"CustFName": f"{role_name}_GLOBAL", "BranchId": 505},
        )
        assert c_resp.status_code == 201
        cid = c_resp.json()["customer_id"]
        assert c_resp.json()["branch_id"] == 505

        # Update customer in remote branch 505
        u_resp = await async_client.put(
            f"/api/v1/customers/{cid}",
            headers=headers,
            json={"CustMName": "UPDATED_CROSS_BRANCH"},
        )
        assert u_resp.status_code == 200
        assert u_resp.json()["cust_m_name"] == "UPDATED_CROSS_BRANCH"


@pytest.mark.asyncio
async def test_soft_deleted_role_rejected_on_login_and_authenticated_requests(
    async_client: AsyncClient, db_session: AsyncSession
):
    """
    16.1.5 (GAP-5F-04): User mapped to a soft-deleted role (isdeleted == '1', e.g.,
    POLICY BAZAR / POLICY BAZAR AGENT) is rejected with 401 Unauthorized on both
    POST /api/v1/auth/login and token-authenticated endpoints.
    """
    for inactive_role in ("POLICY BAZAR", "POLICY BAZAR AGENT"):
        user, headers = await create_user_with_role(
            db_session,
            role_name=inactive_role,
            branch_id=101,
            role_isdeleted="1",
            password="Password123!",
        )

        # 1. Login attempt must fail with 401 Unauthorized
        login_resp = await async_client.post(
            "/api/v1/auth/login",
            json={"username": user.UserName, "password": "Password123!"},
        )
        assert login_resp.status_code == 401

        # 2. Existing token presentation must fail with 401 Unauthorized on /me and /customers
        me_resp = await async_client.get("/api/v1/auth/me", headers=headers)
        assert me_resp.status_code == 401

        cust_resp = await async_client.get("/api/v1/customers", headers=headers)
        assert cust_resp.status_code == 401


# ============================================================================
# 16.2 Customer Write Role Enforcement (GAP-5F-01)
# ============================================================================


@pytest.mark.asyncio
async def test_operator_customer_write_own_branch_and_cross_branch_rejection(
    async_client: AsyncClient, db_session: AsyncSession
):
    """
    16.2.6 & 16.2.7:
    - OPERATOR can create (201) and update (200) customer in own branch.
    - OPERATOR cannot update customer in another branch (403).
    """
    _, headers_op_101 = await create_user_with_role(
        db_session, role_name="OPERATOR", branch_id=101
    )
    _, headers_op_102 = await create_user_with_role(
        db_session, role_name="OPERATOR", branch_id=102
    )

    create_resp = await async_client.post(
        "/api/v1/customers",
        headers=headers_op_101,
        json={"CustFName": "OP_OWN_BRANCH", "MobileNo": "9811122233"},
    )
    assert create_resp.status_code == 201
    cid = create_resp.json()["customer_id"]
    assert create_resp.json()["branch_id"] == 101

    # Own-branch update -> 200 OK
    own_update = await async_client.put(
        f"/api/v1/customers/{cid}",
        headers=headers_op_101,
        json={"CustLName": "SHARMA"},
    )
    assert own_update.status_code == 200
    assert own_update.json()["cust_l_name"] == "SHARMA"


    # Cross-branch update by Branch 102 operator -> 403 Forbidden
    cross_update = await async_client.put(
        f"/api/v1/customers/{cid}",
        headers=headers_op_102,
        json={"CustLName": "FORBIDDEN"},
    )
    assert cross_update.status_code == 403


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "unauthorized_role",
    [
        "AGENT",
        "CASHIER",
        "CLAIM",
        "RELATIONSHIP MANAGER",
        "ACCOUNT",
    ],
)
async def test_unauthorized_roles_cannot_create_or_update_customer(
    async_client: AsyncClient,
    db_session: AsyncSession,
    unauthorized_role: str,
):
    """
    16.2.9 - 16.2.13 (GAP-5F-01):
    AGENT, CASHIER, CLAIM, RELATIONSHIP MANAGER, and ACCOUNT cannot create or update
    a customer (403 Forbidden).
    """
    _, headers_op = await create_user_with_role(
        db_session, role_name="OPERATOR", branch_id=101
    )
    _, headers_unauth = await create_user_with_role(
        db_session, role_name=unauthorized_role, branch_id=101
    )

    # Seed valid customer in Branch 101 via OPERATOR
    seed_resp = await async_client.post(
        "/api/v1/customers",
        headers=headers_op,
        json={"CustFName": "SEED_FOR_RBAC"},
    )
    assert seed_resp.status_code == 201
    cid = seed_resp.json()["customer_id"]

    # Unauthorized role tries POST /api/v1/customers -> 403
    post_resp = await async_client.post(
        "/api/v1/customers",
        headers=headers_unauth,
        json={"CustFName": f"BLOCKED_{unauthorized_role}"},
    )
    assert post_resp.status_code == 403

    # Unauthorized role tries PUT /api/v1/customers/{id} -> 403
    put_resp = await async_client.put(
        f"/api/v1/customers/{cid}",
        headers=headers_unauth,
        json={"CustFName": "BLOCKED_UPDATE"},
    )
    assert put_resp.status_code == 403


# ============================================================================
# 16.3 Vehicle Write Role Enforcement (GAP-5F-01)
# ============================================================================


@pytest.mark.asyncio
async def test_operator_vehicle_write_own_branch_and_cross_branch_rejection(
    async_client: AsyncClient, db_session: AsyncSession
):
    """
    16.3.14 & 16.3.15:
    - OPERATOR can create (201) and update (200) vehicle for own-branch customer.
    - OPERATOR cannot create or update vehicle for another-branch customer (403).
    """
    _, headers_op_101 = await create_user_with_role(
        db_session, role_name="OPERATOR", branch_id=101
    )
    _, headers_op_102 = await create_user_with_role(
        db_session, role_name="OPERATOR", branch_id=102
    )

    c_resp = await async_client.post(
        "/api/v1/customers",
        headers=headers_op_101,
        json={"CustFName": "VEH_OWNER_101"},
    )
    assert c_resp.status_code == 201
    cid = c_resp.json()["customer_id"]

    # 1. Own-branch OPERATOR creates vehicle -> 201
    v_create = await async_client.post(
        f"/api/v1/customers/{cid}/vehicles",
        headers=headers_op_101,
        json={
            "RegistrationNo": "MH12AB5001",
            "ChaiseNo": "CH5001",
            "EngineNo": "EN5001",
            "FinancialYear": "2025-2026",
        },
    )
    assert v_create.status_code == 201
    vid = v_create.json()["cust_veh_id"]

    # 2. Own-branch OPERATOR updates vehicle -> 200
    v_update = await async_client.put(
        f"/api/v1/customers/{cid}/vehicles/{vid}",
        headers=headers_op_101,
        json={"EngineNo": "EN5001_UPD"},
    )
    assert v_update.status_code == 200
    assert v_update.json()["engine_no"] == "EN5001_UPD"

    # 3. Other-branch OPERATOR tries to create vehicle for Branch 101 customer -> 403
    v_cross_create = await async_client.post(
        f"/api/v1/customers/{cid}/vehicles",
        headers=headers_op_102,
        json={
            "RegistrationNo": "MH12AB5002",
            "FinancialYear": "2025-2026",
        },
    )
    assert v_cross_create.status_code == 403

    # 4. Other-branch OPERATOR tries to update vehicle for Branch 101 customer -> 403
    v_cross_update = await async_client.put(
        f"/api/v1/customers/{cid}/vehicles/{vid}",
        headers=headers_op_102,
        json={"EngineNo": "HACKED"},
    )
    assert v_cross_update.status_code == 403


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "unauthorized_role",
    [
        "AGENT",
        "CASHIER",
        "CLAIM",
        "RELATIONSHIP MANAGER",
        "ACCOUNT",
    ],
)
async def test_unauthorized_roles_cannot_create_or_update_vehicle(
    async_client: AsyncClient,
    db_session: AsyncSession,
    unauthorized_role: str,
):
    """
    16.3.16 (GAP-5F-01):
    AGENT, CASHIER, CLAIM, RELATIONSHIP MANAGER, and ACCOUNT cannot create or update
    a vehicle (403 Forbidden).
    """
    _, headers_op = await create_user_with_role(
        db_session, role_name="OPERATOR", branch_id=101
    )
    _, headers_unauth = await create_user_with_role(
        db_session, role_name=unauthorized_role, branch_id=101
    )

    c_resp = await async_client.post(
        "/api/v1/customers",
        headers=headers_op,
        json={"CustFName": "VEH_RBAC_CUST"},
    )
    cid = c_resp.json()["customer_id"]

    v_resp = await async_client.post(
        f"/api/v1/customers/{cid}/vehicles",
        headers=headers_op,
        json={"RegistrationNo": "MH01XY9001", "FinancialYear": "2025-2026"},
    )
    vid = v_resp.json()["cust_veh_id"]

    # Unauthorized role tries POST /api/v1/customers/{cid}/vehicles -> 403
    post_veh = await async_client.post(
        f"/api/v1/customers/{cid}/vehicles",
        headers=headers_unauth,
        json={"RegistrationNo": "MH01XY9002", "FinancialYear": "2025-2026"},
    )
    assert post_veh.status_code == 403

    # Unauthorized role tries PUT /api/v1/customers/{cid}/vehicles/{vid} -> 403
    put_veh = await async_client.put(
        f"/api/v1/customers/{cid}/vehicles/{vid}",
        headers=headers_unauth,
        json={"EngineNo": "BLOCKED"},
    )
    assert put_veh.status_code == 403


# ============================================================================
# 16.4 Customer Read / Search (GAP-5F-09)
# ============================================================================


@pytest.mark.asyncio
async def test_customer_get_by_id_branch_scope_and_soft_delete(
    async_client: AsyncClient, db_session: AsyncSession
):
    """
    16.4.17, 16.4.18, 16.4.19:
    - GET /api/v1/customers/{customer_id} returns own-branch customer (200).
    - GET /api/v1/customers/{customer_id} rejects cross-branch access for non-global role (403).
    - Global read roles (ADMIN, ACCOUNT) can read across branches (200).
    - GET /api/v1/customers/{customer_id} excludes soft-deleted customer (404).
    """
    _, headers_op_101 = await create_user_with_role(
        db_session, role_name="OPERATOR", branch_id=101
    )
    _, headers_agent_101 = await create_user_with_role(
        db_session, role_name="AGENT", branch_id=101
    )
    _, headers_op_102 = await create_user_with_role(
        db_session, role_name="OPERATOR", branch_id=102
    )
    _, headers_account = await create_user_with_role(
        db_session, role_name="ACCOUNT", branch_id=102
    )

    c_resp = await async_client.post(
        "/api/v1/customers",
        headers=headers_op_101,
        json={"CustFName": "READABLE_CLIENT", "PanNo": "ABCDE1234F"},
    )
    cid = c_resp.json()["customer_id"]

    # 1. Own-branch OPERATOR and AGENT can read -> 200 OK
    r1 = await async_client.get(f"/api/v1/customers/{cid}", headers=headers_op_101)
    assert r1.status_code == 200
    assert r1.json()["customer_id"] == cid

    r2 = await async_client.get(f"/api/v1/customers/{cid}", headers=headers_agent_101)
    assert r2.status_code == 200
    assert r2.json()["customer_id"] == cid

    # 2. Cross-branch non-global role -> 403 Forbidden
    r_cross = await async_client.get(f"/api/v1/customers/{cid}", headers=headers_op_102)
    assert r_cross.status_code == 403

    # 3. Cross-branch global read role (ACCOUNT) -> 200 OK
    r_acct = await async_client.get(f"/api/v1/customers/{cid}", headers=headers_account)
    assert r_acct.status_code == 200

    # 4. Soft-delete the customer and verify 404 Not Found
    await db_session.execute(
        text("UPDATE tbl_customer SET isdeleted = '1' WHERE CustomerId = :cid"),
        {"cid": cid},
    )
    await db_session.commit()

    r_deleted = await async_client.get(f"/api/v1/customers/{cid}", headers=headers_op_101)
    assert r_deleted.status_code == 404


@pytest.mark.asyncio
async def test_customer_search_filters_and_branch_scoping(
    async_client: AsyncClient, db_session: AsyncSession
):
    """
    16.4.20:
    - GET /api/v1/customers filters by name, mobile, pan, customer_code within branch scope.
    - Non-global roles never see customers from another branch even if branch_id query is passed.
    - Soft-deleted customers are excluded.
    """
    _, headers_op_101 = await create_user_with_role(
        db_session, role_name="OPERATOR", branch_id=101
    )
    _, headers_op_102 = await create_user_with_role(
        db_session, role_name="OPERATOR", branch_id=102
    )
    _, headers_admin = await create_user_with_role(
        db_session, role_name="ADMIN", branch_id=0
    )

    # Create 2 customers in Branch 101 and 1 customer in Branch 102
    c1 = (
        await async_client.post(
            "/api/v1/customers",
            headers=headers_op_101,
            json={
                "CustFName": "RAJESH",
                "CustLName": "VERMA",
                "MoblieNo1": "9810011111",
                "PAN_No": "AAAAA1111A",
            },
        )
    ).json()

    c2 = (
        await async_client.post(
            "/api/v1/customers",
            headers=headers_op_101,
            json={
                "CustFName": "SURESH",
                "CustLName": "KUMAR",
                "MoblieNo1": "9810022222",
                "PAN_No": "BBBBB2222B",
            },
        )
    ).json()

    c3_b102 = (
        await async_client.post(
            "/api/v1/customers",
            headers=headers_op_102,
            json={
                "CustFName": "RAJESH",
                "CustLName": "OTHERBRANCH",
                "MoblieNo1": "9810011111",
                "PAN_No": "CCCCC3333C",
            },
        )
    ).json()


    # 1. Search by name="RAJESH" as Branch 101 operator -> only returns Branch 101 RAJESH
    by_name = await async_client.get(
        "/api/v1/customers", params={"name": "RAJESH"}, headers=headers_op_101
    )
    assert by_name.status_code == 200
    items = by_name.json()
    assert len(items) == 1
    assert items[0]["customer_id"] == c1["customer_id"]

    # 2. Search by mobile="9810022222"
    by_mobile = await async_client.get(
        "/api/v1/customers", params={"mobile": "9810022222"}, headers=headers_op_101
    )
    assert by_mobile.status_code == 200
    assert [x["customer_id"] for x in by_mobile.json()] == [c2["customer_id"]]

    # 3. Search by pan="aaaaa1111a" (case-insensitive)
    by_pan = await async_client.get(
        "/api/v1/customers", params={"pan": "aaaaa1111a"}, headers=headers_op_101
    )
    assert by_pan.status_code == 200
    assert [x["customer_id"] for x in by_pan.json()] == [c1["customer_id"]]

    # 4. Search by customer_code
    by_code = await async_client.get(
        "/api/v1/customers",
        params={"customer_code": c2["customer_code"]},
        headers=headers_op_101,
    )
    assert by_code.status_code == 200
    assert [x["customer_id"] for x in by_code.json()] == [c2["customer_id"]]

    # 5. Non-global user passing branch_id=102 still only sees Branch 101
    spoof_branch = await async_client.get(
        "/api/v1/customers", params={"branch_id": 102}, headers=headers_op_101
    )
    assert spoof_branch.status_code == 200
    assert all(x["branch_id"] == 101 for x in spoof_branch.json())

    # 6. Global ADMIN passing branch_id=102 sees Branch 102 customer
    admin_b102 = await async_client.get(
        "/api/v1/customers", params={"branch_id": 102}, headers=headers_admin
    )
    assert admin_b102.status_code == 200
    assert [x["customer_id"] for x in admin_b102.json()] == [c3_b102["customer_id"]]


# ============================================================================
# 16.5 Vehicle Read / Search (GAP-5F-09)
# ============================================================================


@pytest.mark.asyncio
async def test_vehicle_read_and_multi_fy_registration_search(
    async_client: AsyncClient, db_session: AsyncSession
):
    """
    16.5.21, 16.5.22, 16.5.23, 16.5.24:
    - GET /api/v1/customers/{customer_id}/vehicles returns active vehicles for own-branch customer (200)
      and rejects cross-branch non-global role (403).
    - GET /api/v1/vehicles?registration_no=... returns multiple rows when the same registration exists
      across different FinancialYear values.
    - GET /api/v1/vehicles?registration_no=...&financial_year=... narrows to the matching financial year.
    - Soft-deleted vehicles are excluded.
    """
    _, headers_op_101 = await create_user_with_role(
        db_session, role_name="OPERATOR", branch_id=101
    )
    _, headers_op_102 = await create_user_with_role(
        db_session, role_name="OPERATOR", branch_id=102
    )

    c_resp = await async_client.post(
        "/api/v1/customers",
        headers=headers_op_101,
        json={"CustFName": "MULTI_FY_OWNER"},
    )
    cid = c_resp.json()["customer_id"]

    # Register the SAME RegistrationNo across two distinct financial years (2024-2025 and 2025-2026)
    v_fy24 = (
        await async_client.post(
            f"/api/v1/customers/{cid}/vehicles",
            headers=headers_op_101,
            json={"RegistrationNo": "MH14 multi 7777", "FinancialYear": "2024-2025"},
        )
    ).json()
    v_fy25 = (
        await async_client.post(
            f"/api/v1/customers/{cid}/vehicles",
            headers=headers_op_101,
            json={"RegistrationNo": "MH14 MULTI 7777", "FinancialYear": "2025-2026"},
        )
    ).json()
    v_del = (
        await async_client.post(
            f"/api/v1/customers/{cid}/vehicles",
            headers=headers_op_101,
            json={"RegistrationNo": "MH14DEL9999", "FinancialYear": "2025-2026"},
        )
    ).json()

    # Soft-delete v_del
    await db_session.execute(
        text("UPDATE tbl_vehicledetails SET isdeleted = '1' WHERE CustVehId = :vid"),
        {"vid": v_del["cust_veh_id"]},
    )
    await db_session.commit()

    # 1. GET /api/v1/customers/{cid}/vehicles for own branch -> returns 2 active vehicles, excludes soft-deleted
    cust_vehs = await async_client.get(
        f"/api/v1/customers/{cid}/vehicles", headers=headers_op_101
    )
    assert cust_vehs.status_code == 200
    veh_ids = {v["cust_veh_id"] for v in cust_vehs.json()}
    assert veh_ids == {v_fy24["cust_veh_id"], v_fy25["cust_veh_id"]}
    assert v_del["cust_veh_id"] not in veh_ids

    # 2. Cross-branch non-global role rejected on GET /api/v1/customers/{cid}/vehicles -> 403
    cross_vehs = await async_client.get(
        f"/api/v1/customers/{cid}/vehicles", headers=headers_op_102
    )
    assert cross_vehs.status_code == 403

    # 3. GET /api/v1/vehicles?registration_no=MH14 MULTI 7777 without financial_year returns BOTH rows
    search_all_fy = await async_client.get(
        "/api/v1/vehicles",
        params={"registration_no": "mh14 multi 7777"},
        headers=headers_op_101,
    )
    assert search_all_fy.status_code == 200
    assert len(search_all_fy.json()) == 2
    assert {v["financial_year"] for v in search_all_fy.json()} == {"2024-2025", "2025-2026"}

    # 4. GET /api/v1/vehicles?registration_no=MH14 MULTI 7777&financial_year=2025-2026 narrows to 1 row
    search_fy25 = await async_client.get(
        "/api/v1/vehicles",
        params={"registration_no": "MH14 MULTI 7777", "financial_year": "2025-2026"},
        headers=headers_op_101,
    )
    assert search_fy25.status_code == 200
    assert len(search_fy25.json()) == 1
    assert search_fy25.json()[0]["cust_veh_id"] == v_fy25["cust_veh_id"]

    # 5. Soft-deleted vehicle excluded from GET /api/v1/vehicles
    search_deleted = await async_client.get(
        "/api/v1/vehicles",
        params={"registration_no": "MH14DEL9999"},
        headers=headers_op_101,
    )
    assert search_deleted.status_code == 200
    assert search_deleted.json() == []


# ============================================================================
# 16.6 Principal Context Resolution (GAP-5F-03)
# ============================================================================


@pytest.mark.asyncio
async def test_principal_context_resolution_end_to_end(
    async_client: AsyncClient, db_session: AsyncSession
):
    """
    16.6.25 (GAP-5F-03):
    Authenticated user context resolves role_name, branch_id, and verified server-side
    principal IDs (agent_id, emp_id/employee_id, franchise_id) from DB relationships
    without trusting client headers/query parameters.
    """
    # 1. Agent user with partner_user_id=404
    _, headers_agent = await create_user_with_role(
        db_session, role_name="AGENT", branch_id=101, partner_user_id=404
    )
    me_agent = await async_client.get(
        "/api/v1/auth/me?agent_id=9999&emp_id=9999",
        headers={**headers_agent, "X-Agent-Id": "9999", "X-Branch-Id": "9999"},
    )
    assert me_agent.status_code == 200
    agent_data = me_agent.json()
    assert agent_data["role"] == "AGENT"
    assert agent_data["branch_id"] == 101
    assert agent_data["agent_id"] == 404
    assert agent_data["emp_id"] is None
    assert agent_data["employee_id"] is None
    assert agent_data["franchise_id"] is None

    # 2. Employee user (RELATIONSHIP MANAGER) with partner_user_id=808
    _, headers_rm = await create_user_with_role(
        db_session, role_name="RELATIONSHIP MANAGER", branch_id=102, partner_user_id=808
    )
    me_rm = await async_client.get("/api/v1/auth/me", headers=headers_rm)
    assert me_rm.status_code == 200
    rm_data = me_rm.json()
    assert rm_data["role"] == "RELATIONSHIP MANAGER"
    assert rm_data["branch_id"] == 102
    assert rm_data["emp_id"] == 808
    assert rm_data["employee_id"] == 808
    assert rm_data["agent_id"] is None
    assert rm_data["franchise_id"] is None

    # 3. Franchise user (FRANCHISE TYPE 2) with partner_user_id=606
    _, headers_fr = await create_user_with_role(
        db_session, role_name="FRANCHISE TYPE 2", branch_id=103, partner_user_id=606
    )
    me_fr = await async_client.get("/api/v1/auth/me", headers=headers_fr)
    assert me_fr.status_code == 200
    fr_data = me_fr.json()
    assert fr_data["role"] == "FRANCHISE TYPE 2"
    assert fr_data["branch_id"] == 103
    assert fr_data["franchise_id"] == 606
    assert fr_data["agent_id"] is None
    assert fr_data["emp_id"] is None
