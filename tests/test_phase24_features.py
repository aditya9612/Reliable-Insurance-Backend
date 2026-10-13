"""
Phase 24 Integration Test Suite — HR Workforce Lifecycle, Compensation Structure,
Employee Advances & Monthly Attendance Management.
"""
from datetime import date, datetime, timedelta
from decimal import Decimal
import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from tests.integration.test_phase7_policy_booking_api import create_user_with_role


@pytest.fixture(autouse=True)
async def cleanup_phase24_tables(db_session: AsyncSession):
    """Purge synthetic Phase 24 tables before and after each test."""
    tables = [
        "tbl_hrmonthlyworkingdetails",
        "tbl_hradvance",
        "tbl_hrsalarystructuredef",
        "tbl_hrworkingtime",
        "tbl_hrreferencedetails",
        "tbl_hrfamilydetails",
        "tbl_hrworkinghistory",
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
# 1. HR Working History & Prior Employment Tracking
# ==============================================================================

@pytest.mark.asyncio
async def test_hr_working_history_and_experience_tracking(
    async_client: AsyncClient, db_session: AsyncSession
):
    _, admin_headers = await create_user_with_role(db_session, "ADMIN")
    _, agent_headers = await create_user_with_role(db_session, "AGENT")

    # 1. Admin creates previous employment history
    history_payload = {
        "EmployeeID": 1001,
        "DepartMentID": None,
        "CompanyName": "National Insurance Brokers Ltd",
        "CompanyAddres": "BKC Complex, Bandra East, Mumbai",
        "CompanyMobileNo": "+91 22 66778899",
        "PreQualification": "B.Com, Licentiate III",
        "PreExprience": "3 Years 6 Months",
        "PreStartDate": date(2021, 6, 1).isoformat(),
        "PreEndDate": date(2024, 12, 31).isoformat(),
        "HRName": "Suresh Mehta",
        "HRMobNo": "+91 9820011223",
        "HRMailId": "hr@nationalbrokers.com",
        "IsActive": 1,
    }
    resp = await async_client.post(
        "/api/v1/hr/working-history", json=history_payload, headers=admin_headers
    )
    assert resp.status_code == 201, resp.text
    hist_data = resp.json()
    hist_id = hist_data["WorkingHistoryId"]
    assert hist_data["CompanyName"] == "National Insurance Brokers Ltd"
    assert hist_data["PreExprience"] == "3 Years 6 Months"

    # 2. RBAC check: Unauthorized role (AGENT) cannot record history
    resp_unauth = await async_client.post(
        "/api/v1/hr/working-history", json=history_payload, headers=agent_headers
    )
    assert resp_unauth.status_code == 403

    # 3. Retrieve by ID
    resp_get = await async_client.get(
        f"/api/v1/hr/working-history/{hist_id}", headers=admin_headers
    )
    assert resp_get.status_code == 200
    assert resp_get.json()["HRName"] == "Suresh Mehta"

    # 4. List by employee ID
    resp_list = await async_client.get(
        "/api/v1/hr/working-history?employee_id=1001", headers=admin_headers
    )
    assert resp_list.status_code == 200
    assert len(resp_list.json()) == 1

    # 5. Update working history
    upd_payload = {"PreExprience": "4 Years"}
    resp_upd = await async_client.put(
        f"/api/v1/hr/working-history/{hist_id}", json=upd_payload, headers=admin_headers
    )
    assert resp_upd.status_code == 200
    assert resp_upd.json()["PreExprience"] == "4 Years"

    # 6. Deactivate working history
    resp_del = await async_client.delete(
        f"/api/v1/hr/working-history/{hist_id}", headers=admin_headers
    )
    assert resp_del.status_code == 200
    check = await async_client.get(
        f"/api/v1/hr/working-history/{hist_id}", headers=admin_headers
    )
    assert check.json()["IsActive"] == 0


# ==============================================================================
# 2. HR Family Dependents & Professional Reference Contacts
# ==============================================================================

@pytest.mark.asyncio
async def test_hr_family_and_professional_reference_details(
    async_client: AsyncClient, db_session: AsyncSession
):
    _, admin_headers = await create_user_with_role(db_session, "ADMIN")
    emp_user, emp_headers = await create_user_with_role(db_session, "CLERK")

    # 1. Create Family Dependent
    family_payload = {
        "EmployeeID": emp_user.UserId,
        "FName": "Ananya Sharma",
        "Relation": "Spouse",
        "Occuption": "Software Engineer",
        "ContactNo": "+91 9876501234",
        "Designation": "Senior Developer",
        "IsActive": 1,
    }
    resp_fam = await async_client.post(
        "/api/v1/hr/family-details", json=family_payload, headers=emp_headers
    )
    assert resp_fam.status_code == 201, resp_fam.text
    fam_id = resp_fam.json()["FamilyId"]
    assert resp_fam.json()["Relation"] == "Spouse"

    # 2. List Family members by employee
    resp_fam_list = await async_client.get(
        f"/api/v1/hr/family-details?employee_id={emp_user.UserId}", headers=emp_headers
    )
    assert resp_fam_list.status_code == 200
    assert len(resp_fam_list.json()) == 1

    # 3. Create Professional Reference
    ref_payload = {
        "EmployeeID": emp_user.UserId,
        "ReferenceName": "Dr. Ramesh Kulkarni",
        "Address": "402 Tech Park, Sector 5, Navi Mumbai",
        "ContactNo": "+91 9988776655",
        "Designation": "VP - Underwriting",
        "MailId": "ramesh.kulkarni@refcorp.com",
        "IsActive": 1,
    }
    resp_ref = await async_client.post(
        "/api/v1/hr/references", json=ref_payload, headers=admin_headers
    )
    assert resp_ref.status_code == 201, resp_ref.text
    ref_id = resp_ref.json()["ReferenceId"]
    assert resp_ref.json()["ReferenceName"] == "Dr. Ramesh Kulkarni"

    # 4. Retrieve Reference by ID
    resp_ref_get = await async_client.get(
        f"/api/v1/hr/references/{ref_id}", headers=admin_headers
    )
    assert resp_ref_get.status_code == 200
    assert resp_ref_get.json()["Designation"] == "VP - Underwriting"

    # 5. Deactivate both
    resp_del_fam = await async_client.delete(
        f"/api/v1/hr/family-details/{fam_id}", headers=admin_headers
    )
    assert resp_del_fam.status_code == 200

    resp_del_ref = await async_client.delete(
        f"/api/v1/hr/references/{ref_id}", headers=admin_headers
    )
    assert resp_del_ref.status_code == 200


# ==============================================================================
# 3. HR Working Time Schedule & Shift Assignment
# ==============================================================================

@pytest.mark.asyncio
async def test_hr_working_time_schedule_assignment(
    async_client: AsyncClient, db_session: AsyncSession
):
    _, admin_headers = await create_user_with_role(db_session, "ADMIN")
    emp_user, emp_headers = await create_user_with_role(db_session, "SALES EXECUTIVE")

    # 1. Assign shift schedule
    shift_payload = {
        "EmployeeID": emp_user.UserId,
        "DepartMentID": None,
        "workingHours": "9.5",
        "offday": "Sunday",
        "overtime": "1.5",
        "ExtraDay": "0",
        "IsActive": 1,
    }
    resp_wt = await async_client.post(
        "/api/v1/hr/working-time", json=shift_payload, headers=admin_headers
    )
    assert resp_wt.status_code == 201, resp_wt.text
    wt_data = resp_wt.json()
    assert wt_data["workingHours"] == "9.5"
    assert wt_data["offday"] == "Sunday"

    # 2. Retrieve shift by employee ID endpoint
    resp_emp_wt = await async_client.get(
        f"/api/v1/hr/working-time/employee/{emp_user.UserId}", headers=emp_headers
    )
    assert resp_emp_wt.status_code == 200
    assert resp_emp_wt.json()["workingHours"] == "9.5"

    # 3. Idempotent create_or_update updates existing schedule rather than duplicating
    updated_shift_payload = dict(shift_payload)
    updated_shift_payload["workingHours"] = "8.0"
    updated_shift_payload["overtime"] = "2.0"
    resp_wt_upd = await async_client.post(
        "/api/v1/hr/working-time", json=updated_shift_payload, headers=admin_headers
    )
    assert resp_wt_upd.status_code == 201
    assert resp_wt_upd.json()["timeinfoId"] == wt_data["timeinfoId"]
    assert resp_wt_upd.json()["workingHours"] == "8.0"
    assert resp_wt_upd.json()["overtime"] == "2.0"


# ==============================================================================
# 4. HR Salary Structure Definition Templates & Duplicate Prevention
# ==============================================================================

@pytest.mark.asyncio
async def test_hr_salary_structure_definition_templates(
    async_client: AsyncClient, db_session: AsyncSession
):
    _, admin_headers = await create_user_with_role(db_session, "ADMIN")

    # 1. Setup Organization
    org_resp = await async_client.post(
        "/api/v1/hr/organizations",
        json={"OrganizationName": "Reliable Corporate Group", "IsActive": 1},
        headers=admin_headers,
    )
    org_id = org_resp.json()["OrganizationId"]

    # 2. Create Salary Structure Template
    struct_payload = {
        "OrganizationId": org_id,
        "salaryStructure": "Standard Executive Grade A",
        "InActive": "0",
        "RateOnGross": "Basic:50%, HRA:30%, Conveyance:10%, Special:10%",
        "Remark": "Standard compensation template for executive cadre",
        "IsActive": 1,
    }
    resp = await async_client.post(
        "/api/v1/hr/salary-structures", json=struct_payload, headers=admin_headers
    )
    assert resp.status_code == 201, resp.text
    struct_id = resp.json()["SalaryStructureDefId"]
    assert resp.json()["salaryStructure"] == "Standard Executive Grade A"

    # 3. Duplicate structure name in same organization -> 409 Conflict
    resp_dup = await async_client.post(
        "/api/v1/hr/salary-structures", json=struct_payload, headers=admin_headers
    )
    assert resp_dup.status_code == 409

    # 4. List salary structures for organization
    resp_list = await async_client.get(
        f"/api/v1/hr/salary-structures?org_id={org_id}", headers=admin_headers
    )
    assert resp_list.status_code == 200
    assert len(resp_list.json()) == 1

    # 5. Deactivate salary structure
    resp_del = await async_client.delete(
        f"/api/v1/hr/salary-structures/{struct_id}", headers=admin_headers
    )
    assert resp_del.status_code == 200
    check = await async_client.get(
        f"/api/v1/hr/salary-structures/{struct_id}", headers=admin_headers
    )
    assert check.json()["IsActive"] == 0
    assert check.json()["InActive"] == "1"


# ==============================================================================
# 5. HR Salary Advance Disbursement, Recovery & Monthly Attendance Ledger
# ==============================================================================

@pytest.mark.asyncio
async def test_hr_advance_disbursement_recovery_and_monthly_working(
    async_client: AsyncClient, db_session: AsyncSession
):
    _, admin_headers = await create_user_with_role(db_session, "ADMIN")
    emp_user, emp_headers = await create_user_with_role(db_session, "CLERK")

    # 1. Setup Organization & Department
    org_resp = await async_client.post(
        "/api/v1/hr/organizations",
        json={"OrganizationName": "Reliable Operations Ltd", "IsActive": 1},
        headers=admin_headers,
    )
    org_id = org_resp.json()["OrganizationId"]

    dept_resp = await async_client.post(
        "/api/v1/hr/departments",
        json={"OrganizationId": org_id, "Dname": "Accounts Payable", "IsActive": 1},
        headers=admin_headers,
    )
    dept_id = dept_resp.json()["DeparmentId"]

    # 2. Disburse Salary Advance (Amount: 12000, Interest: 600, 6 Installments)
    adv_payload = {
        "EmpId": emp_user.UserId,
        "OrganizationId": org_id,
        "AdvanceName": "Festival Festival Advance",
        "AdvanceDate": date.today().isoformat(),
        "Amount": "12000.00",
        "InterestAmount": "600.00",
        "Lumpsum": "No",
        "NoOfInstallment": "6",
        "RecoverFrom": "Salary",
        "NoRecovery": "0",
        "Remark": "Diwali festival advance disbursement",
        "IsActive": 1,
    }
    resp_adv = await async_client.post(
        "/api/v1/hr/advances", json=adv_payload, headers=admin_headers
    )
    assert resp_adv.status_code == 201, resp_adv.text
    adv_data = resp_adv.json()
    adv_id = adv_data["HrAdvanceId"]
    assert Decimal(str(adv_data["TotalAdvance"])) == Decimal("12000.00")
    assert Decimal(str(adv_data["TotalInterest"])) == Decimal("600.00")
    assert Decimal(str(adv_data["TotalDeu"])) == Decimal("12600.00")
    assert Decimal(str(adv_data["Instlamt"])) == Decimal("2100.00")  # 12600 / 6 = 2100.00

    # 3. Record First Installment Recovery (2100.00)
    rec_payload1 = {"RecoveryAmount": "2100.00", "Remark": "November salary deduction"}
    resp_rec1 = await async_client.post(
        f"/api/v1/hr/advances/{adv_id}/recovery", json=rec_payload1, headers=admin_headers
    )
    assert resp_rec1.status_code == 200
    rec_data1 = resp_rec1.json()
    assert Decimal(str(rec_data1["TotalRecovered"])) == Decimal("2100.00")
    assert Decimal(str(rec_data1["TotalDeu"])) == Decimal("10500.00")

    # 4. Settle Remaining Balance (10500.00)
    rec_payload2 = {"RecoveryAmount": "10500.00", "Remark": "Lump sum final settlement"}
    resp_rec2 = await async_client.post(
        f"/api/v1/hr/advances/{adv_id}/recovery", json=rec_payload2, headers=admin_headers
    )
    assert resp_rec2.status_code == 200
    assert Decimal(str(resp_rec2.json()["TotalDeu"])) == Decimal("0.00")

    # Additional recovery on zero-balance rejected
    resp_over_rec = await async_client.post(
        f"/api/v1/hr/advances/{adv_id}/recovery", json={"RecoveryAmount": "500.00"}, headers=admin_headers
    )
    assert resp_over_rec.status_code == 400

    # 5. Record Monthly Working & Attendance Details
    # Month: October 2026 (31 days, 4 Sundays, 1 Holiday, 2 Leaves, 1 Extra Day -> 25 working days)
    mwd_payload = {
        "OrganizationId": org_id,
        "DeparmentId": dept_id,
        "EmpId": emp_user.UserId,
        "Month": 10,
        "Year": 2026,
        "totalNoOfDays": "31.00",
        "Sunday": "4.00",
        "Hoildays": "1.00",
        "leaves": "2.00",
        "workingDays": "25.00",
        "ExtraDays": "1.00",
        "overTimeHour": "12.50",
        "PetrolAll": "1500.00",
        "Incentive": "3000.00",
        "Arrears": "0.00",
        "IsActive": 1,
    }
    resp_mwd = await async_client.post(
        "/api/v1/hr/monthly-working", json=mwd_payload, headers=admin_headers
    )
    assert resp_mwd.status_code == 201, resp_mwd.text
    mwd_data = resp_mwd.json()
    assert Decimal(str(mwd_data["workingDays"])) == Decimal("25.00")

    # 6. Query Monthly Summary Report
    resp_summary = await async_client.get(
        f"/api/v1/hr/monthly-working/summary?org_id={org_id}&year=2026&month=10",
        headers=admin_headers,
    )
    assert resp_summary.status_code == 200
    summary = resp_summary.json()
    assert summary["total_employees_logged"] == 1
    assert Decimal(str(summary["total_working_days"])) == Decimal("25.00")
    assert Decimal(str(summary["total_leaves_taken"])) == Decimal("2.00")
    assert Decimal(str(summary["total_overtime_hours"])) == Decimal("12.50")
    assert Decimal(str(summary["total_petrol_allowances"])) == Decimal("1500.00")
    assert Decimal(str(summary["total_incentives"])) == Decimal("3000.00")
