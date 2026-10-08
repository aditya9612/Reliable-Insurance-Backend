"""
Phase 15B E2E Lifecycle Test — Master Operational Utilities, Profiles, IDV, Health & Batch Operations.
"""
from decimal import Decimal
import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from tests.integration.test_phase7_policy_booking_api import create_user_with_role


@pytest.fixture(autouse=True)
async def cleanup_phase15b_e2e(db_session: AsyncSession):
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


@pytest.mark.asyncio
async def test_phase15b_full_lifecycle_e2e(async_client: AsyncClient, db_session: AsyncSession):
    """
    Complete Phase 15B Operational Lifecycle:
    Step 1: Admin registers internal staff member (Employee)
    Step 2: Admin onboards field POSP Agent assigned to the staff member
    Step 3: Admin registers regional Franchise partner
    Step 4: Field Agent initiates Special Underwriter IDV Override request
    Step 5: Underwriter reviews and approves the IDV override request
    Step 6: Policy booking stages multi-member Health Insurance Family Grid (LBR-058)
    Step 7: Operator bulk imports external Policy MIS Excel/CSV staging file
    Step 8: Reconciliation marks the imported MIS batch as processed
    Step 9: Scheduled batch jobs execute:
            - Overdue Cheque Lock audit (LBR-069)
            - Partner & Customer Birthday greeting dispatch
            - Wallet locks & ephemeral storage cleanup
    """
    _, admin_headers = await create_user_with_role(db_session, "ADMIN")

    # Step 1: Employee Registration
    emp_payload = {
        "UserName": "e2e_staff",
        "EmpFName": "Anand",
        "EmpLName": "Deshmukh",
        "BranchId": 1,
        "UserRoleId": 10,  # SALES
    }
    r_emp = await async_client.post("/api/v1/employees", json=emp_payload, headers=admin_headers)
    assert r_emp.status_code == 201
    emp = r_emp.json()
    emp_id = emp["EmpId"]
    assert emp["EmpCode"].startswith("EMP")

    # Step 2: POSP Agent Onboarding
    agent_payload = {
        "AgentFName": "Pooja",
        "AgentLName": "Kulkarni",
        "MobileNo": "9811223344",
        "SalesExecutiveId": emp_id,
        "BranchId": 1,
    }
    r_agent = await async_client.post("/api/v1/agents", json=agent_payload, headers=admin_headers)
    assert r_agent.status_code == 201
    agent = r_agent.json()
    assert agent["SalesExecutiveId"] == emp_id

    # Step 3: Franchise Registration
    fran_payload = {
        "FranFName": "Pune",
        "FranLName": "Central",
        "BranchId": 1,
        "DateOfBirth": "1995-10-08",
    }
    r_fran = await async_client.post("/api/v1/franchises", json=fran_payload, headers=admin_headers)
    assert r_fran.status_code == 201
    fran = r_fran.json()
    assert fran["FranCode"].startswith("FRN")

    # Step 4: Special IDV Override Submission
    idv_payload = {
        "RegistrationNo": "MH12E2E001",
        "VehicleMake": "TATA",
        "VehicleModel": "HARRIER",
        "RequestedIDV": "1800000.00",
        "SalesExId": emp_id,
        "Note": "Customer requests top-band IDV with ceramic coating and high-value accessories.",
    }
    r_idv = await async_client.post("/api/v1/idv-requests", json=idv_payload, headers=admin_headers)
    assert r_idv.status_code == 201
    idv_req = r_idv.json()
    req_id = idv_req["IDVRequestId"]
    assert idv_req["Status"] == "PENDING"

    # Step 5: Underwriter Review & Approval
    r_approve = await async_client.put(
        f"/api/v1/idv-requests/{req_id}/approve",
        json={"ApprovedIDV": "1750000.00", "ApprovedRemark": "Inspected invoice, approved 17.5L"},
        headers=admin_headers
    )
    assert r_approve.status_code == 200
    assert r_approve.json()["Status"] == "APPROVED"
    assert Decimal(r_approve.json()["ApprovedIDV"]) == Decimal("1750000.00")

    # Step 6: Non-Motor Health Insurance Family Grid (LBR-058)
    health_payload = {
        "CustomerId": 999,
        "TransanctionId": 8888,
        "MemberName": "Siddharth Verma",
        "Relationship": "SELF",
        "Gender": "MALE",
        "Age": 35,
        "SumInsured": "1000000.00",
        "PreExistingDisease": "None",
    }
    r_health = await async_client.post("/api/v1/health-members", json=health_payload, headers=admin_headers)
    assert r_health.status_code == 201
    assert r_health.json()["Status"] == "ACTIVE"

    # Step 7: Bulk MIS Upload & Staging
    csv_body = (
        "Date Of Insurance,Broker Name,Client Name,Vehicle Type,Vehicle Number,Policy Number,Segments,Insurance Company,Gross Amount,Net Amount,O.D Premium,T.P Premium,Broker Received %,Broker Payout\n"
        "2026-06-01,Test Broker,E2E Client,4W,MH12E2E999,POL_E2E_MIS_1,Private Car,ICICI Lombard,22000.00,18644.07,12000.00,6644.07,16.50,3076.27\n"
    ).encode("utf-8")
    files = {"file": ("e2e_mis.csv", csv_body, "text/csv")}
    r_upload = await async_client.post("/api/v1/imports/policy-mis/upload", files=files, headers=admin_headers)
    assert r_upload.status_code == 201
    batch_info = r_upload.json()
    batch_id = batch_info["batch_id"]
    assert batch_info["total_records"] == 1

    # Step 8: Mark Batch Processed
    r_process = await async_client.post(
        "/api/v1/imports/policy-mis/process",
        json={"batch_id": batch_id, "remark": "E2E batch reconciliation verified"},
        headers=admin_headers
    )
    assert r_process.status_code == 200
    assert r_process.json()["processed_count"] == 1

    # Step 9: Operational Scheduled Batch Tasks Execution
    # 9a. Overdue Cheque Lock Audit
    r_lock = await async_client.post("/api/v1/batch-tasks/overdue-cheque-lock/run?threshold_days=15", headers=admin_headers)
    assert r_lock.status_code == 200
    assert "overdue_cheques_found" in r_lock.json()

    # 9b. Birthday Greeting Dispatch
    r_bday = await async_client.post("/api/v1/batch-tasks/birthday-greetings/dispatch", headers=admin_headers)
    assert r_bday.status_code == 200
    assert "candidates_count" in r_bday.json()

    # 9c. Wallet Cleanup
    r_wallet = await async_client.post("/api/v1/batch-tasks/wallet-locks/cleanup", headers=admin_headers)
    assert r_wallet.status_code == 200

    # 9d. Storage Cleanup
    r_storage = await async_client.post("/api/v1/batch-tasks/storage/ephemeral-cleanup", headers=admin_headers)
    assert r_storage.status_code == 200
