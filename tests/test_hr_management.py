"""
Phase 23 Integration Test Suite — Complete HR & Workforce Management System.
Tests Organizations, Departments, Designations, Facilities, Holiday Calendar,
Leave Types, Employee Leave Application & Approvals Workflow, and Contact Persons.
"""
from datetime import date, datetime, timedelta
from decimal import Decimal
import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from tests.integration.test_phase7_policy_booking_api import create_user_with_role


@pytest.fixture(autouse=True)
async def cleanup_phase23_tables(db_session: AsyncSession):
    """Purge synthetic Phase 23 tables before and after each test."""
    tables = [
        "tbl_hrcontactperson",
        "tbl_hrleave",
        "tbl_hrleavetype",
        "tbl_hrholiday",
        "tbl_hrfacility",
        "tbl_hrdesignationmaster",
        "tbl_hrdepartment",
        "tbl_hrorganization",
    ]
    for tbl in tables:
        await db_session.execute(text(f"DELETE FROM {tbl};"))
    await db_session.commit()
    yield
    for tbl in tables:
        await db_session.execute(text(f"DELETE FROM {tbl};"))
    await db_session.commit()


# ==============================================================================
# 1. HR Organization and Department Hierarchy & Org-Wise Filtering
# ==============================================================================

@pytest.mark.asyncio
async def test_hr_organization_and_department_hierarchy(
    async_client: AsyncClient, db_session: AsyncSession
):
    _, admin_headers = await create_user_with_role(db_session, "ADMIN")
    _, agent_headers = await create_user_with_role(db_session, "AGENT")

    # 1. Create Organization as ADMIN
    org_payload = {
        "OrganizationName": "Reliable Insurance Brokers Ltd",
        "Address": "101 Financial Center, Nariman Point, Mumbai",
        "MobileNo": "+91 9876543210",
        "IsActive": 1,
    }
    resp = await async_client.post(
        "/api/v1/hr/organizations", json=org_payload, headers=admin_headers
    )
    assert resp.status_code == 201, resp.text
    org_data = resp.json()
    org_id = org_data["OrganizationId"]
    assert org_data["OrganizationName"] == "Reliable Insurance Brokers Ltd"

    # 2. RBAC check: AGENT cannot create organization
    resp_unauth = await async_client.post(
        "/api/v1/hr/organizations", json=org_payload, headers=agent_headers
    )
    assert resp_unauth.status_code == 403

    # 3. Create Departments under Organization
    dept1_payload = {
        "OrganizationId": org_id,
        "Dname": "Motor Underwriting",
        "Dlocation": "4th Floor, West Wing",
        "IsActive": 1,
    }
    resp_dept1 = await async_client.post(
        "/api/v1/hr/departments", json=dept1_payload, headers=admin_headers
    )
    assert resp_dept1.status_code == 201, resp_dept1.text
    dept1_id = resp_dept1.json()["DeparmentId"]

    dept2_payload = {
        "OrganizationId": org_id,
        "Dname": "Claims Settlement",
        "Dlocation": "4th Floor, East Wing",
        "IsActive": 1,
    }
    resp_dept2 = await async_client.post(
        "/api/v1/hr/departments", json=dept2_payload, headers=admin_headers
    )
    assert resp_dept2.status_code == 201, resp_dept2.text

    # 4. Duplicate Department in same Organization -> 409 Conflict
    resp_dup = await async_client.post(
        "/api/v1/hr/departments", json=dept1_payload, headers=admin_headers
    )
    assert resp_dup.status_code == 409

    # 5. List Departments Org-Wise
    resp_org_depts = await async_client.get(
        f"/api/v1/hr/departments/organization/{org_id}", headers=admin_headers
    )
    assert resp_org_depts.status_code == 200
    depts = resp_org_depts.json()
    assert len(depts) == 2
    dept_names = {d["Dname"] for d in depts}
    assert "Motor Underwriting" in dept_names
    assert "Claims Settlement" in dept_names

    # 6. Update Department
    update_payload = {"Dlocation": "5th Floor, Executive Wing"}
    resp_upd = await async_client.put(
        f"/api/v1/hr/departments/{dept1_id}", json=update_payload, headers=admin_headers
    )
    assert resp_upd.status_code == 200
    assert resp_upd.json()["Dlocation"] == "5th Floor, Executive Wing"


# ==============================================================================
# 2. HR Designation and Facility Masters CRUD & Validation
# ==============================================================================

@pytest.mark.asyncio
async def test_hr_designation_and_facility_masters(
    async_client: AsyncClient, db_session: AsyncSession
):
    _, admin_headers = await create_user_with_role(db_session, "ADMIN")

    # 1. Create Designations
    desg1_payload = {"Designation": "Senior Commercial Underwriter", "IsActive": 1}
    resp_desg = await async_client.post(
        "/api/v1/hr/designations", json=desg1_payload, headers=admin_headers
    )
    assert resp_desg.status_code == 201
    desg1_id = resp_desg.json()["DesignationId"]

    # Duplicate designation -> 409
    resp_dup = await async_client.post(
        "/api/v1/hr/designations", json=desg1_payload, headers=admin_headers
    )
    assert resp_dup.status_code == 409

    # List designations
    resp_list = await async_client.get("/api/v1/hr/designations", headers=admin_headers)
    assert resp_list.status_code == 200
    assert len(resp_list.json()) >= 1

    # 2. Create Facilities
    faci_payload = {
        "Name": "Health Insurance Subsidy",
        "percentage": "80%",
        "IsActive": 1,
    }
    resp_faci = await async_client.post(
        "/api/v1/hr/facilities", json=faci_payload, headers=admin_headers
    )
    assert resp_faci.status_code == 201
    faci_id = resp_faci.json()["FaciltiyId"]
    assert resp_faci.json()["percentage"] == "80%"

    # Deactivate Facility
    resp_del = await async_client.delete(
        f"/api/v1/hr/facilities/{faci_id}", headers=admin_headers
    )
    assert resp_del.status_code == 200
    faci_check = await async_client.get(
        f"/api/v1/hr/facilities/{faci_id}", headers=admin_headers
    )
    assert faci_check.json()["IsActive"] == 0


# ==============================================================================
# 3. HR Holiday Calendar Operations & Filtering
# ==============================================================================

@pytest.mark.asyncio
async def test_hr_holiday_calendar_operations(
    async_client: AsyncClient, db_session: AsyncSession
):
    _, admin_headers = await create_user_with_role(db_session, "ADMIN")

    h1_date = date(2026, 8, 15)
    h2_date = date(2026, 10, 2)

    # 1. Create National Holiday (Company-Wide)
    h1_payload = {
        "HolidayDesc": "Independence Day",
        "HolidayDate": h1_date.isoformat(),
        "EmployeeID": 0,
        "IsActive": 1,
    }
    resp1 = await async_client.post("/api/v1/hr/holidays", json=h1_payload, headers=admin_headers)
    assert resp1.status_code == 201, resp1.text

    # 2. Create Gandhi Jayanti Holiday
    h2_payload = {
        "HolidayDesc": "Gandhi Jayanti",
        "HolidayDate": h2_date.isoformat(),
        "EmployeeID": 0,
        "IsActive": 1,
    }
    resp2 = await async_client.post("/api/v1/hr/holidays", json=h2_payload, headers=admin_headers)
    assert resp2.status_code == 201

    # 3. Prevent Duplicate Holiday on the same date
    resp_dup = await async_client.post("/api/v1/hr/holidays", json=h1_payload, headers=admin_headers)
    assert resp_dup.status_code == 409

    # 4. Filter holidays by year and month
    resp_aug = await async_client.get(
        "/api/v1/hr/holidays?year=2026&month=8", headers=admin_headers
    )
    assert resp_aug.status_code == 200
    aug_holidays = resp_aug.json()
    assert len(aug_holidays) == 1
    assert aug_holidays[0]["HolidayDesc"] == "Independence Day"


# ==============================================================================
# 4. HR Leave Application, Date Validation & Overlap Prevention
# ==============================================================================

@pytest.mark.asyncio
async def test_hr_leave_application_and_overlap_validation(
    async_client: AsyncClient, db_session: AsyncSession
):
    _, admin_headers = await create_user_with_role(db_session, "ADMIN")
    emp_user, emp_headers = await create_user_with_role(db_session, "CLERK")

    # 1. Setup Organization, Department & Leave Type
    org_res = await async_client.post(
        "/api/v1/hr/organizations",
        json={"OrganizationName": "Reliable HQ", "IsActive": 1},
        headers=admin_headers,
    )
    org_id = org_res.json()["OrganizationId"]

    dept_res = await async_client.post(
        "/api/v1/hr/departments",
        json={"OrganizationId": org_id, "Dname": "Policy Operations", "IsActive": 1},
        headers=admin_headers,
    )
    dept_id = dept_res.json()["DeparmentId"]

    lt_res = await async_client.post(
        "/api/v1/hr/leave-types",
        json={"LeaveType": "Earned Leave", "IsActive": 1},
        headers=admin_headers,
    )
    lt_id = lt_res.json()["LeaveTypeId"]

    # 2. Submit Leave Application
    leave_payload = {
        "OrganizationId": org_id,
        "DeparmentId": dept_id,
        "EmpId": emp_user.UserId,
        "LeaveTypeId": lt_id,
        "ApplicationDate": date.today().isoformat(),
        "FromDate": (date.today() + timedelta(days=5)).isoformat(),
        "ToDate": (date.today() + timedelta(days=7)).isoformat(),
        "NoOfDays": "3.00",
        "Reason": "Family vacation",
        "Remark": None,
        "Handover": "Assigned pending queues to Team Lead",
        "ReportingId": 1,
    }
    resp_leave = await async_client.post(
        "/api/v1/hr/leaves", json=leave_payload, headers=emp_headers
    )
    assert resp_leave.status_code == 201, resp_leave.text
    leave_data = resp_leave.json()
    leave_id = leave_data["LeaveId"]
    assert leave_data["ApprovalStatus"] == 0  # 0=Pending

    # 3. Attempt Overlapping Leave for same employee -> 409 Conflict
    overlap_payload = dict(leave_payload)
    overlap_payload["FromDate"] = (date.today() + timedelta(days=6)).isoformat()
    overlap_payload["ToDate"] = (date.today() + timedelta(days=8)).isoformat()
    resp_overlap = await async_client.post(
        "/api/v1/hr/leaves", json=overlap_payload, headers=emp_headers
    )
    assert resp_overlap.status_code == 409

    # 4. Attempt Invalid Date Range (FromDate > ToDate) -> 400 Bad Request
    invalid_payload = dict(leave_payload)
    invalid_payload["FromDate"] = (date.today() + timedelta(days=10)).isoformat()
    invalid_payload["ToDate"] = (date.today() + timedelta(days=5)).isoformat()
    resp_inv = await async_client.post(
        "/api/v1/hr/leaves", json=invalid_payload, headers=emp_headers
    )
    assert resp_inv.status_code == 400

    # 5. Edit details while in Pending status
    update_payload = {"Reason": "Family emergency and travel"}
    resp_edit = await async_client.put(
        f"/api/v1/hr/leaves/{leave_id}", json=update_payload, headers=emp_headers
    )
    assert resp_edit.status_code == 200
    assert resp_edit.json()["Reason"] == "Family emergency and travel"


# ==============================================================================
# 5. Leave Approval Workflow & Emergency Contact Person Management
# ==============================================================================

@pytest.mark.asyncio
async def test_hr_leave_approval_workflow_and_contact_person(
    async_client: AsyncClient, db_session: AsyncSession
):
    mgr_user, mgr_headers = await create_user_with_role(db_session, "MANAGER")
    emp_user, emp_headers = await create_user_with_role(db_session, "CLERK")

    # 1. Setup Masters
    org_res = await async_client.post(
        "/api/v1/hr/organizations",
        json={"OrganizationName": "Reliable Regional Org", "IsActive": 1},
        headers=mgr_headers,
    )
    org_id = org_res.json()["OrganizationId"]

    dept_res = await async_client.post(
        "/api/v1/hr/departments",
        json={"OrganizationId": org_id, "Dname": "Regional Support", "IsActive": 1},
        headers=mgr_headers,
    )
    dept_id = dept_res.json()["DeparmentId"]

    lt_res = await async_client.post(
        "/api/v1/hr/leave-types",
        json={"LeaveType": "Sick Leave", "IsActive": 1},
        headers=mgr_headers,
    )
    lt_id = lt_res.json()["LeaveTypeId"]

    # 2. Apply for Leave with Manager as ReportingId
    leave_payload = {
        "OrganizationId": org_id,
        "DeparmentId": dept_id,
        "EmpId": emp_user.UserId,
        "LeaveTypeId": lt_id,
        "ApplicationDate": date.today().isoformat(),
        "FromDate": (date.today() + timedelta(days=2)).isoformat(),
        "ToDate": (date.today() + timedelta(days=3)).isoformat(),
        "NoOfDays": "2.00",
        "Reason": "Medical appointment",
        "Remark": None,
        "Handover": None,
        "ReportingId": mgr_user.UserId,
    }
    resp_leave = await async_client.post(
        "/api/v1/hr/leaves", json=leave_payload, headers=emp_headers
    )
    assert resp_leave.status_code == 201
    leave_id = resp_leave.json()["LeaveId"]

    # 3. Manager checks pending requests count
    resp_pending_cnt = await async_client.get(
        f"/api/v1/hr/leaves/manager-pending-count?reporting_id={mgr_user.UserId}",
        headers=mgr_headers,
    )
    assert resp_pending_cnt.status_code == 200
    assert resp_pending_cnt.json() == 1

    # 4. Manager Approves Leave
    status_payload = {"ApprovalStatus": 1, "Remark": "Approved by Manager"}
    resp_approve = await async_client.patch(
        f"/api/v1/hr/leaves/{leave_id}/status", json=status_payload, headers=mgr_headers
    )
    assert resp_approve.status_code == 200
    appr_data = resp_approve.json()
    assert appr_data["ApprovalStatus"] == 1
    assert appr_data["Remark"] == "Approved by Manager"
    assert appr_data["ApprovalDate"] is not None

    # Manager's pending count drops to 0
    resp_pending_cnt2 = await async_client.get(
        f"/api/v1/hr/leaves/manager-pending-count?reporting_id={mgr_user.UserId}",
        headers=mgr_headers,
    )
    assert resp_pending_cnt2.json() == 0

    # 5. Check Leave Summary
    resp_summary = await async_client.get(
        f"/api/v1/hr/leaves/summary?emp_id={emp_user.UserId}", headers=emp_headers
    )
    assert resp_summary.status_code == 200
    summary_data = resp_summary.json()
    assert summary_data["total_applications"] == 1
    assert summary_data["pending_count"] == 0
    assert summary_data["approved_count"] == 1
    assert Decimal(str(summary_data["total_approved_days"])) == Decimal("2.00")

    # 6. Cannot edit approved leave
    resp_edit_blocked = await async_client.put(
        f"/api/v1/hr/leaves/{leave_id}",
        json={"Reason": "Cannot alter after approval"},
        headers=emp_headers,
    )
    assert resp_edit_blocked.status_code == 400

    # 7. HR Contact Person CRUD
    contact_payload = {
        "ContactFName": "Rajesh",
        "ContactMName": "K",
        "ContactLName": "Sharma",
        "MobileNo": "+91 9123456789",
        "Address": "Flat 302, Green Meadows, Andheri East, Mumbai",
        "IsActive": 1,
    }
    resp_contact = await async_client.post(
        "/api/v1/hr/contacts", json=contact_payload, headers=mgr_headers
    )
    assert resp_contact.status_code == 201
    contact_id = resp_contact.json()["ContactpersonId"]

    resp_contact_get = await async_client.get(
        f"/api/v1/hr/contacts/{contact_id}", headers=mgr_headers
    )
    assert resp_contact_get.status_code == 200
    assert resp_contact_get.json()["ContactFName"] == "Rajesh"
    assert resp_contact_get.json()["MobileNo"] == "+91 9123456789"
