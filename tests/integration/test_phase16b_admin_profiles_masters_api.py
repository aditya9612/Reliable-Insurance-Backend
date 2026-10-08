"""
Phase 16B Integration Tests — User Management, Login History, Dynamic Privileges,
Agent KYC, Hierarchies, Master Directories & Admin Dashboard.
"""
from datetime import datetime, date
import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from tests.integration.test_phase7_policy_booking_api import create_user_with_role


@pytest.fixture(autouse=True)
async def cleanup_phase16b_tables(db_session: AsyncSession):
    """Purge synthetic Phase 16B entries before and after test."""
    await db_session.execute(text("DELETE FROM tbl_loginhistory WHERE UserName LIKE 'test_%' OR UserName LIKE 'p16_%';"))
    await db_session.execute(text("DELETE FROM tbl_role_privilege WHERE ScreenId >= 9000;"))
    await db_session.execute(text("DELETE FROM tbl_menu WHERE MenuId >= 9000;"))
    await db_session.execute(text("DELETE FROM tbl_fueltype WHERE FuelType LIKE 'TEST_%';"))
    await db_session.execute(text("DELETE FROM tbl_financier WHERE FinancierName LIKE 'TEST_%';"))
    await db_session.execute(text("DELETE FROM tbl_surveyor WHERE SurveyorName LIKE 'TEST_%';"))
    await db_session.execute(text("DELETE FROM tbl_agent WHERE NickName LIKE 'test_p16_%' OR NickName LIKE 'p16_%';"))
    await db_session.execute(text("DELETE FROM tbl_employee WHERE UserName LIKE 'test_p16_%' OR UserName LIKE 'p16_%';"))
    await db_session.execute(text("DELETE FROM tbl_franchise WHERE UserName LIKE 'test_p16_%' OR UserName LIKE 'p16_%';"))
    await db_session.execute(text("DELETE FROM tbl_user WHERE UserName LIKE 'test_p16_%' OR UserName LIKE 'p16_%';"))
    await db_session.commit()
    yield
    await db_session.execute(text("DELETE FROM tbl_loginhistory WHERE UserName LIKE 'test_%' OR UserName LIKE 'p16_%';"))
    await db_session.execute(text("DELETE FROM tbl_role_privilege WHERE ScreenId >= 9000;"))
    await db_session.execute(text("DELETE FROM tbl_menu WHERE MenuId >= 9000;"))
    await db_session.execute(text("DELETE FROM tbl_fueltype WHERE FuelType LIKE 'TEST_%';"))
    await db_session.execute(text("DELETE FROM tbl_financier WHERE FinancierName LIKE 'TEST_%';"))
    await db_session.execute(text("DELETE FROM tbl_surveyor WHERE SurveyorName LIKE 'TEST_%';"))
    await db_session.execute(text("DELETE FROM tbl_agent WHERE NickName LIKE 'test_p16_%' OR NickName LIKE 'p16_%';"))
    await db_session.execute(text("DELETE FROM tbl_employee WHERE UserName LIKE 'test_p16_%' OR UserName LIKE 'p16_%';"))
    await db_session.execute(text("DELETE FROM tbl_franchise WHERE UserName LIKE 'test_p16_%' OR UserName LIKE 'p16_%';"))
    await db_session.execute(text("DELETE FROM tbl_user WHERE UserName LIKE 'test_p16_%' OR UserName LIKE 'p16_%';"))
    await db_session.commit()


# ============================================================================
# 1. User Management CRUD, Roles, and Username Check
# ============================================================================

@pytest.mark.asyncio
async def test_user_crud_and_lifecycle(async_client: AsyncClient, db_session: AsyncSession):
    _, admin_headers = await create_user_with_role(db_session, "ADMIN")

    # 1. Check Username
    r_check = await async_client.get(
        "/api/v1/users/check-username?username=p16_new_user",
        headers=admin_headers
    )
    assert r_check.status_code == 200
    assert r_check.json()["is_available"] is True

    # 2. List Roles
    r_roles = await async_client.get("/api/v1/users/roles", headers=admin_headers)
    assert r_roles.status_code == 200
    roles = r_roles.json()
    assert len(roles) > 0

    # 3. Create User
    payload = {
        "UserName": "p16_new_user",
        "UserPassword": "SecurePassword123!",
        "UserRoleId": roles[0]["UserRoleId"],
        "BranchId": 1,
        "mobile_no": "9898989898",
    }
    r_create = await async_client.post("/api/v1/users", json=payload, headers=admin_headers)
    assert r_create.status_code == 201
    user_data = r_create.json()
    user_id = user_data["UserId"]
    assert user_data["UserName"] == "p16_new_user"
    assert "UserPassword" not in user_data  # Password hash never exposed

    # 4. Check Username taken
    r_check2 = await async_client.get(
        "/api/v1/users/check-username?username=p16_new_user",
        headers=admin_headers
    )
    assert r_check2.status_code == 200
    assert r_check2.json()["is_available"] is False

    # 5. Get User by ID
    r_get = await async_client.get(f"/api/v1/users/{user_id}", headers=admin_headers)
    assert r_get.status_code == 200
    assert r_get.json()["mobile_no"] == "9898989898"

    # 6. Update User
    update_payload = {"mobile_no": "9797979797"}
    r_up = await async_client.put(f"/api/v1/users/{user_id}", json=update_payload, headers=admin_headers)
    assert r_up.status_code == 200
    assert r_up.json()["mobile_no"] == "9797979797"

    # 7. Password Reset
    r_pw = await async_client.put(
        f"/api/v1/users/{user_id}/password",
        json={"new_password": "NewSecretPassword123!"},
        headers=admin_headers
    )
    assert r_pw.status_code == 200

    # 8. Status Toggle (Lock)
    r_lock = await async_client.patch(
        f"/api/v1/users/{user_id}/status",
        json={"is_active": False},
        headers=admin_headers
    )
    assert r_lock.status_code == 200
    assert r_lock.json()["is_active"] is False

    # 9. Status Toggle (Unlock)
    r_unlock = await async_client.patch(
        f"/api/v1/users/{user_id}/status",
        json={"is_active": True},
        headers=admin_headers
    )
    assert r_unlock.status_code == 200
    assert r_unlock.json()["is_active"] is True

    # 10. List Users with filter
    r_list = await async_client.get(
        "/api/v1/users?search=p16_new_user",
        headers=admin_headers
    )
    assert r_list.status_code == 200
    assert r_list.json()["total"] >= 1


# ============================================================================
# 2. Login History & Session Audit Tracking
# ============================================================================

@pytest.mark.asyncio
async def test_login_history_and_unlock(async_client: AsyncClient, db_session: AsyncSession):
    _, admin_headers = await create_user_with_role(db_session, "ADMIN")

    # 1. Create a user
    create_payload = {
        "UserName": "p16_audit_user",
        "UserPassword": "Password123!",
        "BranchId": 1,
    }
    r_create = await async_client.post("/api/v1/users", json=create_payload, headers=admin_headers)
    assert r_create.status_code == 201
    target_user_id = r_create.json()["UserId"]

    # 2. Login with valid credentials
    r_login = await async_client.post(
        "/api/v1/auth/login",
        json={"username": "p16_audit_user", "password": "Password123!"}
    )
    assert r_login.status_code == 200
    user_token = r_login.json()["access_token"]
    user_headers = {"Authorization": f"Bearer {user_token}"}

    # 3. Failed login attempt
    await async_client.post(
        "/api/v1/auth/login",
        json={"username": "p16_audit_user", "password": "WrongPassword!"}
    )

    # 4. User logout
    r_logout = await async_client.post("/api/v1/auth/logout", headers=user_headers)
    assert r_logout.status_code == 200
    assert r_logout.json()["status"] == "logged_out"

    # 5. Admin queries login history
    r_hist = await async_client.get(
        f"/api/v1/auth/login-history?user_id={target_user_id}",
        headers=admin_headers
    )
    assert r_hist.status_code == 200
    history = r_hist.json()
    assert history["total"] >= 2  # Login, Failed Login, Logout
    actions = [it["LogInOrLogOut"] for it in history["items"]]
    assert "LOGIN" in actions
    assert "FAILED_LOGIN" in actions
    assert "LOGOUT" in actions

    # 6. User queries own login history
    r_my_hist = await async_client.get(
        "/api/v1/auth/login-history/me",
        headers=user_headers
    )
    assert r_my_hist.status_code == 200
    assert r_my_hist.json()["total"] >= 1

    # 7. Admin unlock account endpoint
    # First lock the user
    await async_client.patch(
        f"/api/v1/users/{target_user_id}/status",
        json={"is_active": False},
        headers=admin_headers
    )
    r_unlock_api = await async_client.post(
        f"/api/v1/auth/unlock-account/{target_user_id}",
        headers=admin_headers
    )
    assert r_unlock_api.status_code == 200
    assert r_unlock_api.json()["unlocked"] is True


# ============================================================================
# 3. Agent KYC 3-State Machine
# ============================================================================

@pytest.mark.asyncio
async def test_agent_kyc_state_machine(async_client: AsyncClient, db_session: AsyncSession):
    _, admin_headers = await create_user_with_role(db_session, "ADMIN")

    # 1. Onboard Agent (initial status PENDING)
    agent_payload = {
        "AgentFName": "Rohan",
        "AgentLName": "Patil",
        "NickName": "p16_rohan",
        "MobileNo": "9811223344",
        "BranchId": 1,
    }
    r_agent = await async_client.post("/api/v1/agents", json=agent_payload, headers=admin_headers)
    assert r_agent.status_code == 201
    agent_id = r_agent.json()["AgentId"]
    assert r_agent.json()["kyc_status"] == "PENDING"

    # 2. Invalid status target -> 400
    r_bad = await async_client.patch(
        f"/api/v1/agents/{agent_id}/kyc",
        json={"kyc_status": "SUPER_VERIFIED"},
        headers=admin_headers
    )
    assert r_bad.status_code == 400

    # 3. Transition PENDING -> VERIFIED
    r_verify = await async_client.patch(
        f"/api/v1/agents/{agent_id}/kyc",
        json={"kyc_status": "VERIFIED", "kyc_remarks": "Aadhaar and PAN authenticated"},
        headers=admin_headers
    )
    assert r_verify.status_code == 200
    assert r_verify.json()["kyc_status"] == "VERIFIED"

    # 4. Attempt transition from VERIFIED -> REJECTED (Forbidden in 3-state machine -> 400)
    r_re_reject = await async_client.patch(
        f"/api/v1/agents/{agent_id}/kyc",
        json={"kyc_status": "REJECTED"},
        headers=admin_headers
    )
    assert r_re_reject.status_code == 400
    assert "Invalid KYC status transition" in str(r_re_reject.json())


# ============================================================================
# 4. Organization & Partner Hierarchies
# ============================================================================

@pytest.mark.asyncio
async def test_hierarchies_api(async_client: AsyncClient, db_session: AsyncSession):
    _, admin_headers = await create_user_with_role(db_session, "ADMIN")

    # 1. Employee Hierarchy Strings Update
    emp_payload = {
        "UserName": "p16_hier_emp",
        "EmpFName": "Suresh",
        "EmpLName": "Kadam",
        "BranchId": 1,
    }
    r_emp = await async_client.post("/api/v1/employees", json=emp_payload, headers=admin_headers)
    assert r_emp.status_code == 201
    emp_id = r_emp.json()["EmpId"]

    hier_payload = {
        "Hei_Data": "REGION_WEST/PUNE_HQ",
        "Hie_DataSales": "ZONE_WEST/DIST_101",
        "Hie_DataOprn": "OPS_CENTRAL_01",
    }
    r_hier = await async_client.put(
        f"/api/v1/employees/{emp_id}/hierarchy",
        json=hier_payload,
        headers=admin_headers
    )
    assert r_hier.status_code == 200
    assert r_hier.json()["Hei_Data"] == "REGION_WEST/PUNE_HQ"
    assert r_hier.json()["Hie_DataSales"] == "ZONE_WEST/DIST_101"
    assert r_hier.json()["Hie_DataOprn"] == "OPS_CENTRAL_01"

    # 2. Franchise Multi-Tier Hierarchy Traversal
    # Create Root Franchise
    r_root = await async_client.post(
        "/api/v1/franchises",
        json={"UserName": "p16_root_fran", "FranFName": "Root Partner", "BranchId": 1},
        headers=admin_headers
    )
    assert r_root.status_code == 201
    root_id = r_root.json()["FranchiseId"]

    # Create Child Franchise
    r_child = await async_client.post(
        "/api/v1/franchises",
        json={
            "UserName": "p16_child_fran",
            "FranFName": "Child Partner",
            "BranchId": 1,
            "ParentFranchiseId": root_id
        },
        headers=admin_headers
    )
    assert r_child.status_code == 201
    child_id = r_child.json()["FranchiseId"]

    # Traversal from Root
    r_tree = await async_client.get(
        f"/api/v1/franchises/{root_id}/hierarchy",
        headers=admin_headers
    )
    assert r_tree.status_code == 200
    tree = r_tree.json()
    assert tree["FranchiseId"] == root_id
    assert len(tree["children"]) >= 1
    assert tree["children"][0]["FranchiseId"] == child_id


# ============================================================================
# 5. Master Directories: FuelType, Financier, Surveyor
# ============================================================================

@pytest.mark.asyncio
async def test_master_directories_api(async_client: AsyncClient, db_session: AsyncSession):
    _, admin_headers = await create_user_with_role(db_session, "ADMIN")

    # 1. Fuel Type
    r_ft = await async_client.post(
        "/api/v1/masters/fuel-types",
        json={"FuelType": "TEST_ELECTRIC_HYBRID"},
        headers=admin_headers
    )
    assert r_ft.status_code == 201
    assert r_ft.json()["FuelType"] == "TEST_ELECTRIC_HYBRID"

    r_ft_list = await async_client.get("/api/v1/masters/fuel-types", headers=admin_headers)
    assert r_ft_list.status_code == 200
    ft_names = [f["FuelType"] for f in r_ft_list.json()]
    assert "TEST_ELECTRIC_HYBRID" in ft_names

    # 2. Financier
    r_fin = await async_client.post(
        "/api/v1/masters/financiers",
        json={
            "FinancierName": "TEST_HDFC_CREDIT_CORP",
            "ContactNo": "0201234567",
            "EmailId": "test_hdfc@example.com",
            "Address": "MG Road, Pune",
        },
        headers=admin_headers
    )
    assert r_fin.status_code == 201
    assert r_fin.json()["FinancierName"] == "TEST_HDFC_CREDIT_CORP"

    r_fin_list = await async_client.get(
        "/api/v1/masters/financiers?search=TEST_HDFC",
        headers=admin_headers
    )
    assert r_fin_list.status_code == 200
    assert len(r_fin_list.json()) >= 1

    # 3. Surveyor
    r_surv = await async_client.post(
        "/api/v1/masters/surveyors",
        json={
            "SurveyorName": "TEST_RAJESH_SURVEYOR",
            "ContactNo": "9988776655",
            "LicenseNo": "TEST_LIC_12345",
            "City": "Mumbai",
        },
        headers=admin_headers
    )
    assert r_surv.status_code == 201
    assert r_surv.json()["SurveyorName"] == "TEST_RAJESH_SURVEYOR"
    assert r_surv.json()["LicenseNo"] == "TEST_LIC_12345"

    r_surv_list = await async_client.get(
        "/api/v1/masters/surveyors?search=TEST_RAJESH",
        headers=admin_headers
    )
    assert r_surv_list.status_code == 200
    assert len(r_surv_list.json()) >= 1


# ============================================================================
# 6. Admin Overview Counters & Dynamic Menu Tree
# ============================================================================

@pytest.mark.asyncio
async def test_admin_dashboard_and_privileges_api(
    async_client: AsyncClient, db_session: AsyncSession
):
    _, admin_headers = await create_user_with_role(db_session, "ADMIN")

    # 1. Admin Counters
    r_counters = await async_client.get("/api/v1/admin/dashboard/counters", headers=admin_headers)
    assert r_counters.status_code == 200
    counters = r_counters.json()
    assert "total_users" in counters
    assert "active_users" in counters
    assert "locked_users" in counters
    assert "pending_kyc_agents" in counters
    assert counters["total_users"] >= 1

    # 2. Dynamic Privileges & Menu Presentation Tree
    r_roles = await async_client.get("/api/v1/users/roles", headers=admin_headers)
    target_role_id = r_roles.json()[0]["UserRoleId"]

    # Seed a synthetic menu item
    await db_session.execute(text(
        "INSERT INTO tbl_menu (MenuId, MenuName, MenuUrl, ParentMenuId, OrderNo, isdeleted) "
        "VALUES (9901, 'Test Admin Portal', '/admin/test', 0, 1, '0') "
        "ON DUPLICATE KEY UPDATE MenuName=VALUES(MenuName);"
    ))
    await db_session.commit()

    # Assign privilege
    r_assign = await async_client.post(
        "/api/v1/admin/privileges",
        json={"role_id": target_role_id, "screen_ids": [9901]},
        headers=admin_headers
    )
    assert r_assign.status_code == 200
    assert 9901 in r_assign.json()["assigned_screen_ids"]

    # Fetch Menu Tree
    r_tree = await async_client.get(f"/api/v1/admin/privileges/role/{target_role_id}", headers=admin_headers)
    assert r_tree.status_code == 200
    tree_data = r_tree.json()
    assert tree_data["role_id"] == target_role_id
    menu_ids = [m["MenuId"] for m in tree_data["menus"]]
    assert 9901 in menu_ids
