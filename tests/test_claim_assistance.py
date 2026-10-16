"""
Phase 26 Comprehensive Test Suite:
Emergency Roadside Claim Assistance & Accident Intake Lifecycle.
Physical Tables: tbl_claimassistance, tbl_claimassistanceimg.
"""
from datetime import datetime, timedelta
import pytest
from httpx import AsyncClient
from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import AsyncSession

from tests.integration.test_phase7_policy_booking_api import create_user_with_role
from app.models.claim_assistance import ClaimAssistance, ClaimAssistanceImg
from app.models.master import InsuranceCompany
from app.models.notification import SMSLog, MessageMaster, MessageDetail


@pytest.fixture(autouse=True)
async def cleanup_phase26_tables(db_session: AsyncSession):
    """Purge synthetic Phase 26 tables and test notification records before and after each test."""
    await db_session.execute(text("DELETE FROM tbl_claimassistanceimg;"))
    await db_session.execute(text("DELETE FROM tbl_claimassistance;"))
    await db_session.execute(text("DELETE FROM tbl_sms_log WHERE template_id = 'CLAIM_NO_GEN';"))
    await db_session.commit()
    yield
    await db_session.execute(text("DELETE FROM tbl_claimassistanceimg;"))
    await db_session.execute(text("DELETE FROM tbl_claimassistance;"))
    await db_session.execute(text("DELETE FROM tbl_sms_log WHERE template_id = 'CLAIM_NO_GEN';"))
    await db_session.commit()


async def get_or_create_test_company(db_session: AsyncSession) -> int:
    """Ensures at least one active InsuranceCompany exists for tests."""
    stmt = select(InsuranceCompany).limit(1)
    comp = (await db_session.execute(stmt)).scalars().first()
    if comp:
        return comp.InsuranceCompanyId
    new_comp = InsuranceCompany(
        InsuranceCompany="TEST_RELIABLE_INSURER",
        BranchName="MUMBAI_HO",
        BranchCode="MUM01",
        NCB="0",
        Cluster="WEST",
        ZeroDeep="YES",
        isdeleted="0",
        IsAppQuotation="1",
        CompImgPath="/logos/test.png",
        LedgerMId=1001,
    )
    db_session.add(new_comp)
    await db_session.commit()
    await db_session.refresh(new_comp)
    return new_comp.InsuranceCompanyId


# ==============================================================================
# 1. EMERGENCY INTAKE & PHOTO EVIDENCE LIFECYCLE
# ==============================================================================

@pytest.mark.asyncio
async def test_claim_assistance_intake_full_lifecycle(
    async_client: AsyncClient, db_session: AsyncSession
):
    admin_user, admin_headers = await create_user_with_role(db_session, "ADMIN")
    company_id = await get_or_create_test_company(db_session)

    payload = {
        "VehNo": "MH02CB1234",
        "InsuranceCompanyId": company_id,
        "DateofAccident": (datetime.utcnow() - timedelta(hours=2)).isoformat(),
        "Accidenttime": "11:30 AM",
        "spot": "Western Express Highway, Goregaon Flyover",
        "Reason": "Rear-end collision due to sudden braking of vehicle ahead",
        "DriverName": "Ramesh Kumar",
        "DriverLicenseNo": "MH-02-2019-0012345",
        "GarageName": "AutoTech Authorized Body Shop",
        "GarageAddr": "Plot 12, MIDC Andheri East, Mumbai",
        "Garagecontact": "9820011223",
        "BranchId": 101,
        "images": [
            "/uploads/claims/mh02cb1234_front_bumper.jpg",
            "/uploads/claims/mh02cb1234_radiator_grill.jpg",
        ],
    }

    # 1. Post Intake Intimation
    response = await async_client.post(
        "/api/v1/claim-assistance",
        json=payload,
        headers=admin_headers,
    )
    assert response.status_code == 201, response.text
    data = response.json()
    assistance_id = data["claim_assistance_id"]

    assert data["veh_no"] == "MH02CB1234"
    assert data["insurance_company_id"] == company_id
    assert data["status"] == "INTIMATED"
    assert data["read_status"] == 0
    assert data["isdeleted"] == 0
    assert len(data["images"]) == 2
    assert data["images"][0]["img_path"] == "/uploads/claims/mh02cb1234_front_bumper.jpg"
    assert data["created_user"] == admin_user.UserName

    # 2. Fetch Intimation Details by ID
    get_res = await async_client.get(
        f"/api/v1/claim-assistance/{assistance_id}",
        headers=admin_headers,
    )
    assert get_res.status_code == 200
    get_data = get_res.json()
    assert get_data["claim_assistance_id"] == assistance_id
    assert get_data["insurance_company_name"] is not None
    assert get_data["spot"] == "Western Express Highway, Goregaon Flyover"


# ==============================================================================
# 2. VALIDATION & ERROR HANDLING
# ==============================================================================

@pytest.mark.asyncio
async def test_claim_assistance_validation_errors(
    async_client: AsyncClient, db_session: AsyncSession
):
    _, admin_headers = await create_user_with_role(db_session, "ADMIN")

    # Invalid Insurance Company ID (non-existent -> 404)
    payload_bad_comp = {
        "VehNo": "MH01AA9999",
        "InsuranceCompanyId": 999999,
        "DateofAccident": datetime.utcnow().isoformat(),
    }
    res_bad_comp = await async_client.post(
        "/api/v1/claim-assistance",
        json=payload_bad_comp,
        headers=admin_headers,
    )
    assert res_bad_comp.status_code == 404

    # Missing required DateofAccident -> 422
    payload_missing_date = {
        "VehNo": "MH01AA9999",
        "InsuranceCompanyId": 1,
    }
    res_missing_date = await async_client.post(
        "/api/v1/claim-assistance",
        json=payload_missing_date,
        headers=admin_headers,
    )
    assert res_missing_date.status_code == 422


# ==============================================================================
# 3. OPERATOR TRIAGE & DETAIL UPDATES
# ==============================================================================

@pytest.mark.asyncio
async def test_claim_assistance_triage_updates(
    async_client: AsyncClient, db_session: AsyncSession
):
    admin_user, admin_headers = await create_user_with_role(db_session, "ADMIN")
    company_id = await get_or_create_test_company(db_session)

    # Create initial intimation
    init_payload = {
        "VehNo": "DL01BC5566",
        "InsuranceCompanyId": company_id,
        "DateofAccident": datetime.utcnow().isoformat(),
        "DriverName": "Initial Driver",
    }
    create_res = await async_client.post(
        "/api/v1/claim-assistance",
        json=init_payload,
        headers=admin_headers,
    )
    assert create_res.status_code == 201
    assistance_id = create_res.json()["claim_assistance_id"]

    # Update driver, towing garage and status during operator triaging
    update_payload = {
        "DriverName": "Verified Driver Suresh",
        "DriverLicenseNo": "DL-04-2015-778899",
        "GarageName": "Metro Prime Bodyshop",
        "GarageAddr": "Connaught Place, New Delhi",
        "Garagecontact": "9811122233",
        "spot": "Ring Road near AIIMS",
        "Reason": "Side impact at roundabout",
        "Status": "UNDER_REVIEW",
    }
    update_res = await async_client.put(
        f"/api/v1/claim-assistance/{assistance_id}",
        json=update_payload,
        headers=admin_headers,
    )
    assert update_res.status_code == 200
    updated_data = update_res.json()
    assert updated_data["driver_name"] == "Verified Driver Suresh"
    assert updated_data["driver_license_no"] == "DL-04-2015-778899"
    assert updated_data["garage_name"] == "Metro Prime Bodyshop"
    assert updated_data["status"] == "UNDER_REVIEW"
    assert updated_data["updated_user"] == admin_user.UserName


# ==============================================================================
# 4. FORMAL CLAIM NUMBER LINKAGE & DUAL-DISPATCH NOTIFICATIONS
# ==============================================================================

@pytest.mark.asyncio
async def test_claim_assistance_assign_claim_number_and_notifications(
    async_client: AsyncClient, db_session: AsyncSession
):
    admin_user, admin_headers = await create_user_with_role(db_session, "ADMIN")
    customer_user, _ = await create_user_with_role(db_session, "CUSTOMER")
    company_id = await get_or_create_test_company(db_session)

    # Create intimation with customer_id and garage contact
    init_payload = {
        "VehNo": "KA03MM4455",
        "InsuranceCompanyId": company_id,
        "DateofAccident": datetime.utcnow().isoformat(),
        "CustomerId": customer_user.UserId,
        "Garagecontact": "9845012345",
    }
    create_res = await async_client.post(
        "/api/v1/claim-assistance",
        json=init_payload,
        headers=admin_headers,
    )
    assert create_res.status_code == 201
    assistance_id = create_res.json()["claim_assistance_id"]

    # Assign formal claim number with SMS and inbox dispatch enabled
    assign_payload = {
        "ClaimNo": "CLM/2026/BLR/9944",
        "dispatch_sms": True,
        "dispatch_inbox": True,
    }
    assign_res = await async_client.post(
        f"/api/v1/claim-assistance/{assistance_id}/assign-claim-no",
        json=assign_payload,
        headers=admin_headers,
    )
    assert assign_res.status_code == 200
    assigned_data = assign_res.json()
    assert assigned_data["claim_no"] == "CLM/2026/BLR/9944"
    assert assigned_data["status"] == "CLAIM_NO_ASSIGNED"
    assert assigned_data["read_status"] == 1
    assert assigned_data["claim_no_update_user"] == admin_user.UserName

    # Commit test session to refresh snapshot under MySQL REPEATABLE READ
    await db_session.commit()

    # Verify SMS audit record logged
    sms_stmt = select(SMSLog).where(
        SMSLog.template_id == "CLAIM_NO_GEN",
        SMSLog.mobile_number == "9845012345",
    )
    sms_entry = (await db_session.execute(sms_stmt)).scalars().first()
    assert sms_entry is not None
    assert "CLM/2026/BLR/9944" in sms_entry.message_text

    # Verify Internal Inbox message created with Flag="CL"
    msg_stmt = (
        select(MessageDetail)
        .where(
            MessageDetail.userId == customer_user.UserId,
            MessageDetail.Flag == "CL",
        )
    )
    msg_detail = (await db_session.execute(msg_stmt)).scalars().first()
    assert msg_detail is not None


# ==============================================================================
# 5. READ STATUS TOGGLE & SOFT DELETION
# ==============================================================================

@pytest.mark.asyncio
async def test_claim_assistance_read_status_and_soft_delete(
    async_client: AsyncClient, db_session: AsyncSession
):
    admin_user, admin_headers = await create_user_with_role(db_session, "ADMIN")
    company_id = await get_or_create_test_company(db_session)

    init_payload = {
        "VehNo": "GJ01XY8899",
        "InsuranceCompanyId": company_id,
        "DateofAccident": datetime.utcnow().isoformat(),
    }
    create_res = await async_client.post(
        "/api/v1/claim-assistance",
        json=init_payload,
        headers=admin_headers,
    )
    assert create_res.status_code == 201
    assistance_id = create_res.json()["claim_assistance_id"]

    # Toggle Read Status: 0 -> 1
    patch_res = await async_client.patch(
        f"/api/v1/claim-assistance/{assistance_id}/read-status",
        json={"ReadStatus": 1},
        headers=admin_headers,
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["read_status"] == 1

    # Soft Delete
    del_res = await async_client.delete(
        f"/api/v1/claim-assistance/{assistance_id}",
        headers=admin_headers,
    )
    assert del_res.status_code == 200
    assert del_res.json()["success"] is True

    # Retrieval after soft deletion returns 404
    get_res = await async_client.get(
        f"/api/v1/claim-assistance/{assistance_id}",
        headers=admin_headers,
    )
    assert get_res.status_code == 404


# ==============================================================================
# 6. DASHBOARD & OPERATIONAL SUMMARY METRICS
# ==============================================================================

@pytest.mark.asyncio
async def test_claim_assistance_summary_metrics(
    async_client: AsyncClient, db_session: AsyncSession
):
    _, admin_headers = await create_user_with_role(db_session, "ADMIN")
    company_id = await get_or_create_test_company(db_session)

    # 1. Unread Intimation without Claim No
    await async_client.post(
        "/api/v1/claim-assistance",
        json={
            "VehNo": "TS09AA1111",
            "InsuranceCompanyId": company_id,
            "DateofAccident": datetime.utcnow().isoformat(),
        },
        headers=admin_headers,
    )

    # 2. Read Intimation without Claim No
    r2 = await async_client.post(
        "/api/v1/claim-assistance",
        json={
            "VehNo": "TS09AA2222",
            "InsuranceCompanyId": company_id,
            "DateofAccident": datetime.utcnow().isoformat(),
        },
        headers=admin_headers,
    )
    r2_id = r2.json()["claim_assistance_id"]
    await async_client.patch(
        f"/api/v1/claim-assistance/{r2_id}/read-status",
        json={"ReadStatus": 1},
        headers=admin_headers,
    )

    # 3. Intimation with Claim Assigned
    r3 = await async_client.post(
        "/api/v1/claim-assistance",
        json={
            "VehNo": "TS09AA3333",
            "InsuranceCompanyId": company_id,
            "DateofAccident": datetime.utcnow().isoformat(),
        },
        headers=admin_headers,
    )
    r3_id = r3.json()["claim_assistance_id"]
    await async_client.post(
        f"/api/v1/claim-assistance/{r3_id}/assign-claim-no",
        json={"ClaimNo": "CLM-TS-3333"},
        headers=admin_headers,
    )

    # Query Summary Metrics
    sum_res = await async_client.get(
        "/api/v1/claim-assistance/summary",
        headers=admin_headers,
    )
    assert sum_res.status_code == 200
    metrics = sum_res.json()
    assert metrics["total_intimations"] == 3
    assert metrics["unread_intimations"] == 1
    assert metrics["read_intimations"] == 2
    assert metrics["pending_claim_assignment"] == 2
    assert metrics["claim_assigned"] == 1


# ==============================================================================
# 7. RBAC PRIVILEGE ENFORCEMENT & GATEKEEPING
# ==============================================================================

@pytest.mark.asyncio
async def test_claim_assistance_rbac_privilege_gates(
    async_client: AsyncClient, db_session: AsyncSession
):
    _, admin_headers = await create_user_with_role(db_session, "ADMIN")
    _, agent_headers = await create_user_with_role(db_session, "AGENT")
    company_id = await get_or_create_test_company(db_session)

    # Create intimation as Admin
    create_res = await async_client.post(
        "/api/v1/claim-assistance",
        json={
            "VehNo": "TN01ZZ9090",
            "InsuranceCompanyId": company_id,
            "DateofAccident": datetime.utcnow().isoformat(),
        },
        headers=admin_headers,
    )
    assert create_res.status_code == 201
    assistance_id = create_res.json()["claim_assistance_id"]

    # Agent cannot assign formal Claim Number (403 Forbidden)
    res_agent_assign = await async_client.post(
        f"/api/v1/claim-assistance/{assistance_id}/assign-claim-no",
        json={"ClaimNo": "UNAUTHORIZED_CLM"},
        headers=agent_headers,
    )
    assert res_agent_assign.status_code == 403

    # Agent cannot delete intimation (403 Forbidden)
    res_agent_del = await async_client.delete(
        f"/api/v1/claim-assistance/{assistance_id}",
        headers=agent_headers,
    )
    assert res_agent_del.status_code == 403


# ==============================================================================
# 8. PHOTO VALIDATION, DUPLICATE CLAIM NO & TENANT ISOLATION
# ==============================================================================

@pytest.mark.asyncio
async def test_claim_assistance_photo_validation(
    async_client: AsyncClient, db_session: AsyncSession
):
    _, admin_headers = await create_user_with_role(db_session, "ADMIN")
    company_id = await get_or_create_test_company(db_session)

    # Invalid image extension (.exe) rejected with 422
    payload_bad_photo = {
        "VehNo": "MH04AB1122",
        "InsuranceCompanyId": company_id,
        "DateofAccident": datetime.utcnow().isoformat(),
        "images": ["/malicious/payload.exe"],
    }
    res = await async_client.post(
        "/api/v1/claim-assistance",
        json=payload_bad_photo,
        headers=admin_headers,
    )
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_claim_assistance_duplicate_and_repeated_assignment(
    async_client: AsyncClient, db_session: AsyncSession
):
    _, admin_headers = await create_user_with_role(db_session, "ADMIN")
    company_id = await get_or_create_test_company(db_session)

    res = await async_client.post(
        "/api/v1/claim-assistance",
        json={
            "VehNo": "KA01ZZ3344",
            "InsuranceCompanyId": company_id,
            "DateofAccident": datetime.utcnow().isoformat(),
        },
        headers=admin_headers,
    )
    aid = res.json()["claim_assistance_id"]

    # Initial assignment
    assign_res = await async_client.post(
        f"/api/v1/claim-assistance/{aid}/assign-claim-no",
        json={"ClaimNo": "CLM-ORIGINAL-100"},
        headers=admin_headers,
    )
    assert assign_res.status_code == 200

    # Repeated identical assignment is idempotent (200 OK)
    repeat_res = await async_client.post(
        f"/api/v1/claim-assistance/{aid}/assign-claim-no",
        json={"ClaimNo": "CLM-ORIGINAL-100"},
        headers=admin_headers,
    )
    assert repeat_res.status_code == 200

    # Conflicting different claim number assignment is rejected with 409 Conflict
    conflict_res = await async_client.post(
        f"/api/v1/claim-assistance/{aid}/assign-claim-no",
        json={"ClaimNo": "CLM-CONFLICT-200"},
        headers=admin_headers,
    )
    assert conflict_res.status_code == 409


@pytest.mark.asyncio
async def test_claim_assistance_cross_branch_isolation(
    async_client: AsyncClient, db_session: AsyncSession
):
    # Admin creates intimation in Branch 101
    _, admin_headers = await create_user_with_role(db_session, "ADMIN", branch_id=101)
    # Clerk in Branch 102
    _, clerk_branch102_headers = await create_user_with_role(db_session, "CLERK", branch_id=102)
    company_id = await get_or_create_test_company(db_session)

    res = await async_client.post(
        "/api/v1/claim-assistance",
        json={
            "VehNo": "MH12AB9988",
            "InsuranceCompanyId": company_id,
            "DateofAccident": datetime.utcnow().isoformat(),
            "BranchId": 101,
        },
        headers=admin_headers,
    )
    aid = res.json()["claim_assistance_id"]

    # Clerk in Branch 102 cannot view detail of Branch 101 intimation (403 Forbidden)
    res_get = await async_client.get(
        f"/api/v1/claim-assistance/{aid}",
        headers=clerk_branch102_headers,
    )
    assert res_get.status_code == 403

    # Clerk in Branch 102 cannot modify Branch 101 intimation (403 Forbidden)
    res_update = await async_client.put(
        f"/api/v1/claim-assistance/{aid}",
        json={"DriverName": "Hacked Driver"},
        headers=clerk_branch102_headers,
    )
    assert res_update.status_code == 403

    # Clerk in Branch 102 cannot assign claim number to Branch 101 intimation (403 Forbidden)
    res_assign = await async_client.post(
        f"/api/v1/claim-assistance/{aid}/assign-claim-no",
        json={"ClaimNo": "CLM-HIJACK"},
        headers=clerk_branch102_headers,
    )
    assert res_assign.status_code == 403

