"""
Phase 16B Master End-to-End (E2E) Test Suite.
Flows 1 through 6:
- Flow 1: User Onboarding, Credential Lifecycle, Password Reset, Status Lock/Unlock & Session History
- Flow 2: Agent KYC Lifecycle Verification & 3-State Transition Validation
- Flow 3: Organization & Partner Hierarchy Traversal (Employee & Multi-Tier Franchise)
- Flow 4: Master Directories Synchronization (FuelType, Financier, Surveyor)
- Flow 5: Dynamic Role Privilege Mapping & Menu Presentation Tree Validation
- Flow 6: System Overview Executive Dashboard Metrics Parity
"""
import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from tests.integration.test_phase7_policy_booking_api import create_user_with_role


@pytest.fixture(autouse=True)
async def cleanup_phase16b_e2e(db_session: AsyncSession):
    await db_session.execute(text("DELETE FROM tbl_loginhistory WHERE UserName LIKE 'e2e_%';"))
    await db_session.execute(text("DELETE FROM tbl_role_privilege WHERE ScreenId >= 9100;"))
    await db_session.execute(text("DELETE FROM tbl_menu WHERE MenuId >= 9100;"))
    await db_session.execute(text("DELETE FROM tbl_fueltype WHERE FuelType LIKE 'E2E_%';"))
    await db_session.execute(text("DELETE FROM tbl_financier WHERE FinancierName LIKE 'E2E_%';"))
    await db_session.execute(text("DELETE FROM tbl_surveyor WHERE SurveyorName LIKE 'E2E_%';"))
    await db_session.execute(text("DELETE FROM tbl_agent WHERE NickName LIKE 'e2e_%';"))
    await db_session.execute(text("DELETE FROM tbl_employee WHERE UserName LIKE 'e2e_%';"))
    await db_session.execute(text("DELETE FROM tbl_franchise WHERE UserName LIKE 'e2e_%';"))
    await db_session.execute(text("DELETE FROM tbl_user WHERE UserName LIKE 'e2e_%';"))
    await db_session.commit()
    yield
    await db_session.execute(text("DELETE FROM tbl_loginhistory WHERE UserName LIKE 'e2e_%';"))
    await db_session.execute(text("DELETE FROM tbl_role_privilege WHERE ScreenId >= 9100;"))
    await db_session.execute(text("DELETE FROM tbl_menu WHERE MenuId >= 9100;"))
    await db_session.execute(text("DELETE FROM tbl_fueltype WHERE FuelType LIKE 'E2E_%';"))
    await db_session.execute(text("DELETE FROM tbl_financier WHERE FinancierName LIKE 'E2E_%';"))
    await db_session.execute(text("DELETE FROM tbl_surveyor WHERE SurveyorName LIKE 'E2E_%';"))
    await db_session.execute(text("DELETE FROM tbl_agent WHERE NickName LIKE 'e2e_%';"))
    await db_session.execute(text("DELETE FROM tbl_employee WHERE UserName LIKE 'e2e_%';"))
    await db_session.execute(text("DELETE FROM tbl_franchise WHERE UserName LIKE 'e2e_%';"))
    await db_session.execute(text("DELETE FROM tbl_user WHERE UserName LIKE 'e2e_%';"))
    await db_session.commit()


@pytest.mark.asyncio
async def test_phase16b_master_e2e_flows(async_client: AsyncClient, db_session: AsyncSession):
    """
    Executes Phase 16B End-to-End Flows 1 through 6 sequentially.
    """
    _, admin_headers = await create_user_with_role(db_session, "ADMIN")

    # ========================================================================
    # FLOW 1: User Onboarding, Credential Lifecycle, Password Reset & Session History
    # ========================================================================
    # Step 1.1: Verify username availability
    r_avail = await async_client.get("/api/v1/users/check-username?username=e2e_operator", headers=admin_headers)
    assert r_avail.status_code == 200
    assert r_avail.json()["is_available"] is True

    # Step 1.2: Fetch active role and create user
    r_roles = await async_client.get("/api/v1/users/roles", headers=admin_headers)
    target_role_id = r_roles.json()[0]["UserRoleId"]

    user_payload = {
        "UserName": "e2e_operator",
        "UserPassword": "InitialPassword123!",
        "BranchId": 1,
        "UserRoleId": target_role_id,
        "mobile_no": "9123456780",
    }
    r_u = await async_client.post("/api/v1/users", json=user_payload, headers=admin_headers)
    assert r_u.status_code == 201
    operator_id = r_u.json()["UserId"]

    # Step 1.3: User authenticates with initial password
    r_login = await async_client.post(
        "/api/v1/auth/login",
        json={"username": "e2e_operator", "password": "InitialPassword123!"}
    )
    assert r_login.status_code == 200
    op_token = r_login.json()["access_token"]
    op_headers = {"Authorization": f"Bearer {op_token}"}

    # Step 1.4: User logs out
    r_logout = await async_client.post("/api/v1/auth/logout", headers=op_headers)
    assert r_logout.status_code == 200

    # Step 1.5: Admin resets user's password
    r_reset = await async_client.put(
        f"/api/v1/users/{operator_id}/password",
        json={"new_password": "RotatedPassword456!"},
        headers=admin_headers
    )
    assert r_reset.status_code == 200

    # Step 1.6: User authenticates with new password
    r_login_new = await async_client.post(
        "/api/v1/auth/login",
        json={"username": "e2e_operator", "password": "RotatedPassword456!"}
    )
    assert r_login_new.status_code == 200

    # Step 1.7: Admin locks the user account
    r_lock = await async_client.patch(
        f"/api/v1/users/{operator_id}/status",
        json={"is_active": False},
        headers=admin_headers
    )
    assert r_lock.status_code == 200
    assert r_lock.json()["is_active"] is False

    # Step 1.8: Attempt login while locked -> 401 inactive_user
    r_locked_login = await async_client.post(
        "/api/v1/auth/login",
        json={"username": "e2e_operator", "password": "RotatedPassword456!"}
    )
    assert r_locked_login.status_code == 401

    # Step 1.9: Admin unlocks user via unlock endpoint
    r_unlock = await async_client.post(
        f"/api/v1/auth/unlock-account/{operator_id}",
        headers=admin_headers
    )
    assert r_unlock.status_code == 200
    assert r_unlock.json()["unlocked"] is True

    # Step 1.10: Verify persistent session history logged all actions
    r_hist = await async_client.get(
        f"/api/v1/auth/login-history?user_id={operator_id}",
        headers=admin_headers
    )
    assert r_hist.status_code == 200
    assert r_hist.json()["total"] >= 3

    # ========================================================================
    # FLOW 2: Agent KYC Lifecycle Verification & 3-State Transition Validation
    # ========================================================================
    agent_payload = {
        "AgentFName": "Vikram",
        "AgentLName": "Malhotra",
        "NickName": "e2e_vikram",
        "MobileNo": "9988776600",
        "BranchId": 1,
    }
    r_ag = await async_client.post("/api/v1/agents", json=agent_payload, headers=admin_headers)
    assert r_ag.status_code == 201
    agent_id = r_ag.json()["AgentId"]
    assert r_ag.json()["kyc_status"] == "PENDING"

    # Reject invalid transition attempt
    r_invalid_trans = await async_client.patch(
        f"/api/v1/agents/{agent_id}/kyc",
        json={"kyc_status": "NOT_A_VALID_STATUS"},
        headers=admin_headers
    )
    assert r_invalid_trans.status_code == 400

    # Transition PENDING -> VERIFIED
    r_kyc_ok = await async_client.patch(
        f"/api/v1/agents/{agent_id}/kyc",
        json={"kyc_status": "VERIFIED", "kyc_remarks": "Identity documents verified"},
        headers=admin_headers
    )
    assert r_kyc_ok.status_code == 200
    assert r_kyc_ok.json()["kyc_status"] == "VERIFIED"

    # Terminal state protection: VERIFIED cannot transition again
    r_term = await async_client.patch(
        f"/api/v1/agents/{agent_id}/kyc",
        json={"kyc_status": "REJECTED"},
        headers=admin_headers
    )
    assert r_term.status_code == 400

    # ========================================================================
    # FLOW 3: Organization & Partner Hierarchy Traversal
    # ========================================================================
    # Step 3.1: Staff Hierarchy Strings
    r_staff = await async_client.post(
        "/api/v1/employees",
        json={"UserName": "e2e_officer", "EmpFName": "Pooja", "EmpLName": "Nair", "BranchId": 1},
        headers=admin_headers
    )
    assert r_staff.status_code == 201
    officer_id = r_staff.json()["EmpId"]

    r_staff_hier = await async_client.put(
        f"/api/v1/employees/{officer_id}/hierarchy",
        json={"Hei_Data": "REGION_SOUTH", "Hie_DataSales": "ZONE_KL", "Hie_DataOprn": "OPS_COCHI"},
        headers=admin_headers
    )
    assert r_staff_hier.status_code == 200
    assert r_staff_hier.json()["Hei_Data"] == "REGION_SOUTH"

    # Step 3.2: Multi-Tier Franchise Partner Hierarchy
    r_parent_f = await async_client.post(
        "/api/v1/franchises",
        json={"UserName": "e2e_state_partner", "FranFName": "State Partner", "BranchId": 1},
        headers=admin_headers
    )
    assert r_parent_f.status_code == 201
    parent_fid = r_parent_f.json()["FranchiseId"]

    r_child_f = await async_client.post(
        "/api/v1/franchises",
        json={
            "UserName": "e2e_district_partner",
            "FranFName": "District Partner",
            "BranchId": 1,
            "ParentFranchiseId": parent_fid
        },
        headers=admin_headers
    )
    assert r_child_f.status_code == 201
    child_fid = r_child_f.json()["FranchiseId"]

    r_f_tree = await async_client.get(f"/api/v1/franchises/{parent_fid}/hierarchy", headers=admin_headers)
    assert r_f_tree.status_code == 200
    tree_res = r_f_tree.json()
    assert tree_res["FranchiseId"] == parent_fid
    assert len(tree_res["children"]) == 1
    assert tree_res["children"][0]["FranchiseId"] == child_fid

    # ========================================================================
    # FLOW 4: Master Directories Synchronization
    # ========================================================================
    # Fuel Type
    r_m_fuel = await async_client.post(
        "/api/v1/masters/fuel-types",
        json={"FuelType": "E2E_BIO_DIESEL"},
        headers=admin_headers
    )
    assert r_m_fuel.status_code == 201

    # Financier
    r_m_fin = await async_client.post(
        "/api/v1/masters/financiers",
        json={"FinancierName": "E2E_KOTAK_MAHINDRA", "BranchId": 1},
        headers=admin_headers
    )
    assert r_m_fin.status_code == 201

    # Surveyor
    r_m_surv = await async_client.post(
        "/api/v1/masters/surveyors",
        json={"SurveyorName": "E2E_INSPECTOR_GADGET", "LicenseNo": "E2E_LIC_9999", "BranchId": 1},
        headers=admin_headers
    )
    assert r_m_surv.status_code == 201

    # ========================================================================
    # FLOW 5: Dynamic Role Privilege Mapping & Menu Presentation Tree
    # ========================================================================
    await db_session.execute(text(
        "INSERT INTO tbl_menu (MenuId, MenuName, MenuUrl, ParentMenuId, OrderNo, isdeleted) "
        "VALUES (9150, 'E2E Claims Console', '/claims/console', 0, 1, '0') "
        "ON DUPLICATE KEY UPDATE MenuName=VALUES(MenuName);"
    ))
    await db_session.commit()

    r_priv_set = await async_client.post(
        "/api/v1/admin/privileges",
        json={"role_id": target_role_id, "screen_ids": [9150]},
        headers=admin_headers
    )
    assert r_priv_set.status_code == 200

    r_priv_tree = await async_client.get(f"/api/v1/admin/privileges/role/{target_role_id}", headers=admin_headers)
    assert r_priv_tree.status_code == 200
    p_menus = [m["MenuId"] for m in r_priv_tree.json()["menus"]]
    assert 9150 in p_menus

    # ========================================================================
    # FLOW 6: System Overview Executive Dashboard Metrics Parity
    # ========================================================================
    r_dash = await async_client.get("/api/v1/admin/dashboard/counters", headers=admin_headers)
    assert r_dash.status_code == 200
    dash_data = r_dash.json()
    assert dash_data["total_users"] >= 2
    assert dash_data["total_agents"] >= 1
    assert dash_data["total_employees"] >= 1
    assert dash_data["total_franchises"] >= 2
    assert dash_data["active_users"] >= 2
