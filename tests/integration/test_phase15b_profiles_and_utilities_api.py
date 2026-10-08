"""
Phase 15B Integration Tests — Employee/Agent/Franchise Profiles, IDV Overrides, Health Grid & Bulk MIS.
"""
from datetime import datetime, date, timedelta
from decimal import Decimal
import io
import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.payment import TransactionPayment
from tests.integration.test_phase7_policy_booking_api import create_user_with_role
from tests.integration.test_phase12_search import make_synthetic_tx


@pytest.fixture(autouse=True)
async def cleanup_phase15b_tables(db_session: AsyncSession):
    """Purge synthetic Phase 15B tables before and after test."""
    await db_session.execute(text("DELETE FROM tbl_importagentpolicy;"))
    await db_session.execute(text("DELETE FROM tbl_healthmember;"))
    await db_session.execute(text("DELETE FROM tbl_idvrequest;"))
    await db_session.execute(text("DELETE FROM tbl_franchise;"))
    await db_session.execute(text("DELETE FROM tbl_agent;"))
    await db_session.execute(text("DELETE FROM tbl_employee;"))
    await db_session.commit()
    yield
    await db_session.execute(text("DELETE FROM tbl_importagentpolicy;"))
    await db_session.execute(text("DELETE FROM tbl_healthmember;"))
    await db_session.execute(text("DELETE FROM tbl_idvrequest;"))
    await db_session.execute(text("DELETE FROM tbl_franchise;"))
    await db_session.execute(text("DELETE FROM tbl_agent;"))
    await db_session.execute(text("DELETE FROM tbl_employee;"))
    await db_session.commit()


# ============================================================================
# 1. Employee Profiles API
# ============================================================================

@pytest.mark.asyncio
async def test_employee_crud_api(async_client: AsyncClient, db_session: AsyncSession):
    _, admin_headers = await create_user_with_role(db_session, "ADMIN")

    # 1. Create Employee
    payload = {
        "UserName": "test_emp_01",
        "EmpFName": "Ramesh",
        "EmpLName": "Sharma",
        "EmailId": "ramesh@reliable.com",
        "MoblieNo": "9876543210",
        "BranchId": 1,
        "UserRoleId": 6,
    }
    resp = await async_client.post("/api/v1/employees", json=payload, headers=admin_headers)
    assert resp.status_code == 201, resp.text
    created = resp.json()
    emp_id = created["EmpId"]
    assert created["full_name"] == "Ramesh Sharma"
    assert created["EmpCode"].startswith("EMP")
    assert created["is_active"] is True

    # 2. List Employees
    resp = await async_client.get("/api/v1/employees?branch_id=1", headers=admin_headers)
    assert resp.status_code == 200
    listed = resp.json()
    assert any(e["EmpId"] == emp_id for e in listed)

    # 3. Get Employee by ID
    resp = await async_client.get(f"/api/v1/employees/{emp_id}", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["EmpId"] == emp_id

    # 4. Update Employee
    resp = await async_client.put(
        f"/api/v1/employees/{emp_id}",
        json={"EmpFName": "Ramesh Kumar"},
        headers=admin_headers
    )
    assert resp.status_code == 200
    assert resp.json()["full_name"] == "Ramesh Kumar Sharma"

    # 5. Delete (Soft) Employee
    resp = await async_client.delete(f"/api/v1/employees/{emp_id}", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "SUCCESS"

    # Verify not returned in active list
    resp = await async_client.get("/api/v1/employees", headers=admin_headers)
    assert not any(e["EmpId"] == emp_id for e in resp.json())


# ============================================================================
# 2. POSP Agent Profiles API
# ============================================================================

@pytest.mark.asyncio
async def test_agent_crud_api(async_client: AsyncClient, db_session: AsyncSession):
    _, admin_headers = await create_user_with_role(db_session, "ADMIN")

    # 1. Create Agent
    payload = {
        "AgentFName": "Suresh",
        "AgentLName": "Patil",
        "NickName": "Suru",
        "MobileNo": "9822011223",
        "EmailId": "suresh@posp.com",
        "PANNo": "ABCDE1234F",
        "AadharNo": "123456789012",
        "BranchId": 1,
    }
    resp = await async_client.post("/api/v1/agents", json=payload, headers=admin_headers)
    assert resp.status_code == 201, resp.text
    created = resp.json()
    agent_id = created["AgentId"]
    assert created["full_name"] == "Suresh Patil"
    assert created["AgentCode"].startswith("AGT")

    # 2. List Agents
    resp = await async_client.get("/api/v1/agents?search=Suresh", headers=admin_headers)
    assert resp.status_code == 200
    assert any(a["AgentId"] == agent_id for a in resp.json())

    # 3. Update Agent
    resp = await async_client.put(
        f"/api/v1/agents/{agent_id}",
        json={"NickName": "Suru Bhai"},
        headers=admin_headers
    )
    assert resp.status_code == 200
    assert resp.json()["NickName"] == "Suru Bhai"

    # 4. Deactivate Agent
    resp = await async_client.delete(f"/api/v1/agents/{agent_id}", headers=admin_headers)
    assert resp.status_code == 200


# ============================================================================
# 3. Franchise Profiles API
# ============================================================================

@pytest.mark.asyncio
async def test_franchise_crud_api(async_client: AsyncClient, db_session: AsyncSession):
    _, admin_headers = await create_user_with_role(db_session, "ADMIN")

    # 1. Create Franchise
    payload = {
        "FranFName": "Nashik",
        "FranLName": "Branch Hub",
        "UserName": "nashik_hub",
        "PerAddrLine1": "Main Road",
        "MoblieNo1": "9988776655",
        "BranchId": 1,
        "DateOfBirth": "1988-10-08",
    }
    resp = await async_client.post("/api/v1/franchises", json=payload, headers=admin_headers)
    assert resp.status_code == 201, resp.text
    created = resp.json()
    fran_id = created["FranchiseId"]
    assert created["FranCode"].startswith("FRN")

    # 2. List Franchises
    resp = await async_client.get("/api/v1/franchises?branch_id=1", headers=admin_headers)
    assert resp.status_code == 200
    assert any(f["FranchiseId"] == fran_id for f in resp.json())

    # 3. Update Franchise
    resp = await async_client.put(
        f"/api/v1/franchises/{fran_id}",
        json={"FranFName": "Nashik City"},
        headers=admin_headers
    )
    assert resp.status_code == 200
    assert resp.json()["FranFName"] == "Nashik City"

    # 4. Deactivate Franchise
    resp = await async_client.delete(f"/api/v1/franchises/{fran_id}", headers=admin_headers)
    assert resp.status_code == 200


# ============================================================================
# 4. Special IDV Override Queue API
# ============================================================================

@pytest.mark.asyncio
async def test_idv_override_workflow_api(async_client: AsyncClient, db_session: AsyncSession):
    _, admin_headers = await create_user_with_role(db_session, "ADMIN")

    # 1. Create Special IDV Override Request
    payload = {
        "RegistrationNo": "MH15AB9999",
        "VehicleMake": "HYUNDAI",
        "VehicleModel": "CRETA",
        "RequestedIDV": "950000.00",
        "Note": "Customer installed custom CNG kit and audio setup; requesting higher IDV.",
    }
    resp = await async_client.post("/api/v1/idv-requests", json=payload, headers=admin_headers)
    assert resp.status_code == 201, resp.text
    req = resp.json()
    req_id = req["IDVRequestId"]
    assert req["Status"] == "PENDING"
    assert Decimal(req["RequestedIDV"]) == Decimal("950000.00")

    # 2. List in Pending Queue
    resp = await async_client.get("/api/v1/idv-requests?status=PENDING", headers=admin_headers)
    assert resp.status_code == 200
    assert any(r["IDVRequestId"] == req_id for r in resp.json())

    # 3. Underwriter Approve
    approve_payload = {
        "ApprovedIDV": "920000.00",
        "ApprovedRemark": "Inspected custom accessories, approved up to 9.2 Lakhs.",
    }
    resp = await async_client.put(
        f"/api/v1/idv-requests/{req_id}/approve",
        json=approve_payload,
        headers=admin_headers
    )
    assert resp.status_code == 200, resp.text
    approved = resp.json()
    assert approved["Status"] == "APPROVED"
    assert Decimal(approved["ApprovedIDV"]) == Decimal("920000.00")

    # 4. Reject workflow on another request
    payload2 = {
        "RegistrationNo": "MH12CD1111",
        "VehicleMake": "MARUTI",
        "VehicleModel": "ALTO",
        "RequestedIDV": "300000.00",
        "Note": "Requesting IDV above standard band.",
    }
    resp2 = await async_client.post("/api/v1/idv-requests", json=payload2, headers=admin_headers)
    req2_id = resp2.json()["IDVRequestId"]

    reject_payload = {"ApprovedRemark": "Age of vehicle exceeds limit for requested IDV."}
    resp_reject = await async_client.put(
        f"/api/v1/idv-requests/{req2_id}/reject",
        json=reject_payload,
        headers=admin_headers
    )
    assert resp_reject.status_code == 200
    assert resp_reject.json()["Status"] == "REJECTED"


# ============================================================================
# 5. Non-Motor Health Family Member Grid API
# ============================================================================

@pytest.mark.asyncio
async def test_health_family_grid_api(async_client: AsyncClient, db_session: AsyncSession):
    _, admin_headers = await create_user_with_role(db_session, "ADMIN")

    # 1. Add Family Members
    payload1 = {
        "CustomerId": 101,
        "TransanctionId": 501,
        "MemberName": "Rajesh Kumar",
        "Relationship": "SELF",
        "Gender": "MALE",
        "Age": 40,
        "SumInsured": "500000.00",
        "PreExistingDisease": "None",
    }
    resp1 = await async_client.post("/api/v1/health-members", json=payload1, headers=admin_headers)
    assert resp1.status_code == 201, resp1.text
    m1 = resp1.json()
    assert m1["Relationship"] == "SELF"

    payload2 = {
        "CustomerId": 101,
        "TransanctionId": 501,
        "MemberName": "Anita Kumar",
        "Relationship": "SPOUSE",
        "Gender": "FEMALE",
        "Age": 38,
        "SumInsured": "500000.00",
        "PreExistingDisease": "Thyroid",
    }
    resp2 = await async_client.post("/api/v1/health-members", json=payload2, headers=admin_headers)
    assert resp2.status_code == 201
    m2 = resp2.json()

    # 2. List Members for Policy
    resp_list = await async_client.get("/api/v1/health-members?transaction_id=501", headers=admin_headers)
    assert resp_list.status_code == 200
    members = resp_list.json()
    assert len(members) == 2

    # 3. Update Sum Insured
    resp_up = await async_client.put(
        f"/api/v1/health-members/{m2['MemberId']}",
        json={"SumInsured": "750000.00"},
        headers=admin_headers
    )
    assert resp_up.status_code == 200
    assert Decimal(resp_up.json()["SumInsured"]) == Decimal("750000.00")

    # 4. Remove Member
    resp_del = await async_client.delete(f"/api/v1/health-members/{m2['MemberId']}", headers=admin_headers)
    assert resp_del.status_code == 200


# ============================================================================
# 6. Bulk CSV Policy MIS Upload & Processing API
# ============================================================================

@pytest.mark.asyncio
async def test_bulk_policy_mis_upload_and_process_api(async_client: AsyncClient, db_session: AsyncSession):
    _, admin_headers = await create_user_with_role(db_session, "ADMIN")

    csv_content = (
        "Date Of Insurance,Broker Name,Client Name,Vehicle Type,Vehicle Number,Policy Number,Segments,Insurance Company,Gross Amount,Net Amount,O.D Premium,T.P Premium,Broker Received %,Broker Payout\n"
        "2026-05-01,Broker A,Client One,4W,MH12AA1111,POL_MIS_001,Private Car,Bajaj Allianz,15000.00,12711.86,8000.00,4711.86,15.00,1906.78\n"
        "2026-05-02,Broker B,Client Two,2W,MH14BB2222,POL_MIS_002,Two Wheeler,HDFC ERGO,3500.00,2966.10,1500.00,1466.10,12.00,355.93\n"
    ).encode("utf-8")

    files = {"file": ("test_mis.csv", csv_content, "text/csv")}
    resp = await async_client.post("/api/v1/imports/policy-mis/upload", files=files, headers=admin_headers)
    assert resp.status_code == 201, resp.text
    summary = resp.json()
    batch_id = summary["batch_id"]
    assert summary["total_records"] == 2
    assert summary["pending_records"] == 2
    assert Decimal(summary["total_gross_amount"]) == Decimal("18500.00")

    # List Staged Records
    resp_records = await async_client.get(f"/api/v1/imports/policy-mis/records?batch_id={batch_id}", headers=admin_headers)
    assert resp_records.status_code == 200
    records = resp_records.json()
    assert len(records) == 2
    assert records[0]["IsProcess"] == 0

    # Process Batch
    resp_proc = await async_client.post(
        "/api/v1/imports/policy-mis/process",
        json={"batch_id": batch_id, "remark": "Automated test batch reconciled"},
        headers=admin_headers
    )
    assert resp_proc.status_code == 200
    assert resp_proc.json()["processed_count"] == 2


# ============================================================================
# 7. Operational Batch Tasks API
# ============================================================================

@pytest.mark.asyncio
async def test_operational_batch_tasks_api(async_client: AsyncClient, db_session: AsyncSession):
    _, admin_headers = await create_user_with_role(db_session, "ADMIN")

    # 1. Overdue Cheque Lock Audit (LBR-069)
    resp = await async_client.post(
        "/api/v1/batch-tasks/overdue-cheque-lock/run?threshold_days=15",
        headers=admin_headers
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "overdue_cheques_found" in data
    assert "users_locked" in data

    # 2. Birthday Greetings Dispatch
    resp = await async_client.post(
        "/api/v1/batch-tasks/birthday-greetings/dispatch",
        headers=admin_headers
    )
    assert resp.status_code == 200
    bday_data = resp.json()
    assert "candidates_count" in bday_data
    assert "messages_dispatched" in bday_data

    # 3. Wallet Locks Cleanup
    resp = await async_client.post(
        "/api/v1/batch-tasks/wallet-locks/cleanup",
        headers=admin_headers
    )
    assert resp.status_code == 200
    assert resp.json()["task_name"] == "stale_wallet_lock_cleanup"

    # 4. Ephemeral Storage Cleanup
    resp = await async_client.post(
        "/api/v1/batch-tasks/storage/ephemeral-cleanup",
        headers=admin_headers
    )
    assert resp.status_code == 200
    assert resp.json()["task_name"] == "storage_ephemeral_cleanup"


@pytest.mark.asyncio
async def test_batch_tasks_rbac_enforcement(async_client: AsyncClient, db_session: AsyncSession):
    """
    Finding 4 Verification: Ensure batch-task endpoints strictly require
    canonical roles (OWNER, ADMIN, IT SUPPORT). Unauthenticated returns 401,
    unauthorized roles (AGENT, MANAGER) return 403, and ADMIN returns 200.
    """
    endpoints = [
        "/api/v1/batch-tasks/overdue-cheque-lock/run",
        "/api/v1/batch-tasks/birthday-greetings/dispatch",
        "/api/v1/batch-tasks/wallet-locks/cleanup",
        "/api/v1/batch-tasks/storage/ephemeral-cleanup",
    ]

    # 1. Unauthenticated requests -> 401
    for ep in endpoints:
        resp = await async_client.post(ep)
        assert resp.status_code == 401, f"{ep} did not reject unauthenticated call"

    # 2. Unauthorized roles (AGENT, MANAGER) -> 403
    _, agent_headers = await create_user_with_role(db_session, "AGENT")
    for ep in endpoints:
        resp = await async_client.post(ep, headers=agent_headers)
        assert resp.status_code == 403, f"{ep} allowed AGENT role"

    _, mgr_headers = await create_user_with_role(db_session, "MANAGER")
    for ep in endpoints:
        resp = await async_client.post(ep, headers=mgr_headers)
        assert resp.status_code == 403, f"{ep} allowed MANAGER role"

    # 3. Authorized role (ADMIN) -> 200
    _, admin_headers = await create_user_with_role(db_session, "ADMIN")
    for ep in endpoints:
        resp = await async_client.post(ep, headers=admin_headers)
        assert resp.status_code == 200, f"{ep} failed for ADMIN role: {resp.text}"


@pytest.mark.asyncio
async def test_pii_masking_for_non_privileged_roles(async_client: AsyncClient, db_session: AsyncSession):
    """
    Finding 5 Verification: PII fields (PAN_No/PANNo, AadharNo, accountNo) are masked
    at the response/serialization layer for non-privileged viewers (e.g. MANAGER, AGENT),
    while privileged roles (OWNER, ADMIN, IT SUPPORT, HR) see raw unmasked values.
    Database records remain raw and unmasked.
    """
    _, admin_headers = await create_user_with_role(db_session, "ADMIN")
    _, mgr_headers = await create_user_with_role(db_session, "MANAGER", branch_id=1)

    # 1. Employee PII
    emp_payload = {
        "UserName": "pii_emp_test",
        "EmpFName": "Anil",
        "EmpLName": "Kapoor",
        "PAN_No": "ABCDE1234F",
        "AadharNo": "123456789012",
        "accountNo": "98765432101234",
        "BranchId": 1,
    }
    emp_resp = await async_client.post("/api/v1/employees", json=emp_payload, headers=admin_headers)
    assert emp_resp.status_code == 201
    emp_id = emp_resp.json()["EmpId"]

    # Privileged read (ADMIN)
    get_emp_admin = await async_client.get(f"/api/v1/employees/{emp_id}", headers=admin_headers)
    assert get_emp_admin.status_code == 200
    data_admin = get_emp_admin.json()
    assert data_admin["PAN_No"] == "ABCDE1234F"
    assert data_admin["AadharNo"] == "123456789012"
    assert data_admin["accountNo"] == "98765432101234"

    # Non-privileged read (MANAGER) - Detail
    get_emp_mgr = await async_client.get(f"/api/v1/employees/{emp_id}", headers=mgr_headers)
    assert get_emp_mgr.status_code == 200
    data_mgr = get_emp_mgr.json()
    assert data_mgr["PAN_No"] == "XXXXXX234F"
    assert data_mgr["AadharNo"] == "XXXXXXXX9012"
    assert data_mgr["accountNo"] == "XXXXXXXXXX1234"

    # Non-privileged read (MANAGER) - List
    list_emp_mgr = await async_client.get("/api/v1/employees?search=Anil", headers=mgr_headers)
    assert list_emp_mgr.status_code == 200
    matched = [e for e in list_emp_mgr.json() if e["EmpId"] == emp_id][0]
    assert matched["PAN_No"] == "XXXXXX234F"
    assert matched["AadharNo"] == "XXXXXXXX9012"
    assert matched["accountNo"] == "XXXXXXXXXX1234"

    # 2. Agent PII
    agent_payload = {
        "AgentFName": "Sunil",
        "AgentLName": "Gavaskar",
        "PANNo": "XYZAB5678G",
        "AadharNo": "987654321098",
        "accountNo": "11223344556677",
        "BranchId": 1,
    }
    agent_resp = await async_client.post("/api/v1/agents", json=agent_payload, headers=admin_headers)
    assert agent_resp.status_code == 201
    agent_id = agent_resp.json()["AgentId"]

    # Privileged read (ADMIN)
    get_agent_admin = await async_client.get(f"/api/v1/agents/{agent_id}", headers=admin_headers)
    assert get_agent_admin.json()["PANNo"] == "XYZAB5678G"
    assert get_agent_admin.json()["AadharNo"] == "987654321098"
    assert get_agent_admin.json()["accountNo"] == "11223344556677"

    # Non-privileged read (MANAGER)
    get_agent_mgr = await async_client.get(f"/api/v1/agents/{agent_id}", headers=mgr_headers)
    assert get_agent_mgr.json()["PANNo"] == "XXXXXX678G"
    assert get_agent_mgr.json()["AadharNo"] == "XXXXXXXX1098"
    assert get_agent_mgr.json()["accountNo"] == "XXXXXXXXXX6677"

    # 3. Franchise PII
    fran_payload = {
        "FranFName": "Sachin",
        "FranLName": "Tendulkar",
        "PAN_No": "PQRST9012H",
        "AadharNo": "456789012345",
        "accountNo": "99887766554433",
        "BranchId": 1,
    }
    fran_resp = await async_client.post("/api/v1/franchises", json=fran_payload, headers=admin_headers)
    assert fran_resp.status_code == 201
    fran_id = fran_resp.json()["FranchiseId"]

    # Privileged read (ADMIN)
    get_fran_admin = await async_client.get(f"/api/v1/franchises/{fran_id}", headers=admin_headers)
    assert get_fran_admin.json()["PAN_No"] == "PQRST9012H"
    assert get_fran_admin.json()["AadharNo"] == "456789012345"
    assert get_fran_admin.json()["accountNo"] == "99887766554433"

    # Non-privileged read (MANAGER)
    get_fran_mgr = await async_client.get(f"/api/v1/franchises/{fran_id}", headers=mgr_headers)
    assert get_fran_mgr.json()["PAN_No"] == "XXXXXX012H"
    assert get_fran_mgr.json()["AadharNo"] == "XXXXXXXX2345"
    assert get_fran_mgr.json()["accountNo"] == "XXXXXXXXXX4433"

    # 4. Database Integrity Verification — raw values in database are NOT overwritten
    await db_session.commit()
    res = await db_session.execute(text("SELECT PAN_No, AadharNo, accountNo FROM tbl_employee WHERE EmpId = :eid"), {"eid": emp_id})
    raw_emp = res.first()
    assert raw_emp is not None
    assert raw_emp[0] == "ABCDE1234F"
    assert raw_emp[1] == "123456789012"
    assert raw_emp[2] == "98765432101234"


@pytest.mark.asyncio
async def test_lbr_069_overdue_cheque_lock_behavioral_parity(async_client: AsyncClient, db_session: AsyncSession):
    """
    Finding 3 Verification: LBR-069 Overdue Cheque Login Lock Behavioral Parity.
    When an uncleared cheque exceeds threshold_days, the creating user's account
    is deactivated (isdeleted = '1'), which causes subsequent login attempts
    via AuthService.login to return HTTP 401 with 'User account is inactive or disabled'.
    Subsequent task runs must remain strictly idempotent.
    """
    _, admin_headers = await create_user_with_role(db_session, "ADMIN")

    # Create target operator user
    operator_pass = "SecurePass123!"
    operator_user, _ = await create_user_with_role(
        db_session, "OPERATOR", branch_id=1, password=operator_pass
    )
    operator_name = operator_user.UserName

    # Verify operator can log in before lock
    login_resp = await async_client.post(
        "/api/v1/auth/login",
        json={"username": operator_name, "password": operator_pass}
    )
    assert login_resp.status_code == 200, f"Initial login failed: {login_resp.text}"

    # Insert a synthetic transaction with an overdue cheque created 25 days ago
    past_date = datetime.utcnow() - timedelta(days=25)

    tx = make_synthetic_tx(
        policy_no="POL_LBR069_TEST",
        inward_no="INW_LBR069",
        branch_id=1,
    )
    tx.CreateUser = operator_name
    tx.CreateDate = past_date
    db_session.add(tx)
    await db_session.flush()

    payment = TransactionPayment(
        TransanctionId=tx.TransanctionId,
        PaymentType="Cheque",
        docno="CHQ88991",
        PaidAmount=Decimal("10000.00"),
        CashierApproval=0,
        CreateDate=past_date,
        CreateUser=operator_name,
        isCompletePayment=0,
    )
    db_session.add(payment)
    await db_session.commit()

    try:
        # Run overdue cheque lock batch task with threshold = 15 days
        lock_resp = await async_client.post(
            "/api/v1/batch-tasks/overdue-cheque-lock/run?threshold_days=15",
            headers=admin_headers
        )
        assert lock_resp.status_code == 200, lock_resp.text
        lock_data = lock_resp.json()
        assert lock_data["overdue_cheques_found"] >= 1
        assert any(u["user_name"] == operator_name and u["lock_status"] == "LOCKED" for u in lock_data["users_locked"])

        # Verify database state in tbl_user: isdeleted == '1'
        u_check = await db_session.execute(
            text("SELECT isdeleted, UpdateUser FROM tbl_user WHERE UserName = :uname"),
            {"uname": operator_name}
        )
        u_row = u_check.first()
        assert u_row is not None
        assert u_row[0] == "1"
        assert "LBR-069" in (u_row[1] or "")

        # Verify login is BLOCKED (HTTP 401: inactive user)
        failed_login = await async_client.post(
            "/api/v1/auth/login",
            json={"username": operator_name, "password": operator_pass}
        )
        assert failed_login.status_code == 401
        assert "inactive or disabled" in str(failed_login.json()).lower()

        # Idempotency check: Re-running batch task does not double-lock or crash
        rerun_resp = await async_client.post(
            "/api/v1/batch-tasks/overdue-cheque-lock/run?threshold_days=15",
            headers=admin_headers
        )
        assert rerun_resp.status_code == 200
        rerun_data = rerun_resp.json()
        assert not any(u["user_name"] == operator_name and u["lock_status"] == "LOCKED" for u in rerun_data["users_locked"])

    finally:
        # Cleanup synthetic transaction & payment
        if "tx" in locals() and tx.TransanctionId:
            await db_session.execute(text("DELETE FROM tbl_transactionpayment WHERE TransanctionId = :tid;"), {"tid": tx.TransanctionId})
            await db_session.execute(text("DELETE FROM tbl_transaction WHERE TransanctionId = :tid;"), {"tid": tx.TransanctionId})
        await db_session.execute(text("DELETE FROM tbl_user WHERE UserName = :uname;"), {"uname": operator_name})
        await db_session.commit()
