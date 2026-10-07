"""
Phase 13 Integration Tests — Vehicle RC 3-Tier Cascade & Outbound Notifications API.
Tests advisory RC lookup, OTP lifecycle over HTTP, SMS, Push dual-dispatch, and Email report.
"""
from datetime import datetime, timedelta
import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.integration import VehicleRCDetails
from app.models.vehicle import VehicleDetails
from app.models.customer import Customer
from app.models.transaction import Transaction
from app.providers import default_mock_sms_provider
from tests.integration.test_phase7_policy_booking_api import create_user_with_role
from tests.integration.test_phase12_search import make_synthetic_tx


@pytest.fixture(autouse=True)
async def cleanup_phase13_integration_tables(db_session: AsyncSession):
    """Purge synthetic integration and notification records before and after test."""
    await db_session.execute(text("DELETE FROM tbl_pushnotification_log;"))
    await db_session.execute(text("DELETE FROM tbl_sms_log;"))
    await db_session.execute(text("DELETE FROM tbl_otp_log;"))
    await db_session.execute(text("DELETE FROM tbl_messagedetails;"))
    await db_session.execute(text("DELETE FROM tbl_messagemaster;"))
    await db_session.execute(text("DELETE FROM tbl_vehiclenorc_details;"))
    await db_session.execute(text("DELETE FROM tbl_transaction;"))
    await db_session.execute(text("DELETE FROM tbl_vehicledetails;"))
    await db_session.execute(text("DELETE FROM tbl_customer;"))
    await db_session.commit()
    yield
    await db_session.execute(text("DELETE FROM tbl_pushnotification_log;"))
    await db_session.execute(text("DELETE FROM tbl_sms_log;"))
    await db_session.execute(text("DELETE FROM tbl_otp_log;"))
    await db_session.execute(text("DELETE FROM tbl_messagedetails;"))
    await db_session.execute(text("DELETE FROM tbl_messagemaster;"))
    await db_session.execute(text("DELETE FROM tbl_vehiclenorc_details;"))
    await db_session.execute(text("DELETE FROM tbl_transaction;"))
    await db_session.execute(text("DELETE FROM tbl_vehicledetails;"))
    await db_session.execute(text("DELETE FROM tbl_customer;"))
    await db_session.commit()


# ---------------------------------------------------------------------------
# 1. Vehicle RC 3-Tier Cascade Lookup Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_vehicle_rc_lookup_tier1_internal_system(async_client: AsyncClient, db_session: AsyncSession):
    _, auth_headers = await create_user_with_role(db_session, "ADMIN")

    # Seed internal vehicle, customer & transaction
    cust = Customer(CustFName="RAHUL", CustLName="VERMA", MoblieNo1="9850288888")
    db_session.add(cust)
    await db_session.flush()

    veh = VehicleDetails(
        RegistrationNo="MH12INT001",
        CustomerId=cust.CustomerId,
        ChaiseNo="CHAS998877",
        EngineNo="ENG112233",
        FinancialYear="2024-2025",
    )
    db_session.add(veh)
    await db_session.flush()

    tx = make_synthetic_tx(
        policy_no="POL-INT-1234",
        cust_veh_id=veh.CustVehId,
        customer_id=cust.CustomerId,
    )
    tx.ExpiryDate = datetime.utcnow() + timedelta(days=100)
    db_session.add(tx)
    await db_session.commit()

    resp = await async_client.post(
        "/api/v1/integrations/vehicle-rc/lookup",
        json={"registration_number": "MH12INT001", "force_refresh": False},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["source"] == "INTERNAL_SYSTEM"
    assert data["data"]["owner_name"] == "RAHUL VERMA"
    assert data["data"]["chassis_number"] == "CHAS998877"


@pytest.mark.asyncio
async def test_vehicle_rc_lookup_tier2_local_cache(async_client: AsyncClient, db_session: AsyncSession):
    _, auth_headers = await create_user_with_role(db_session, "ADMIN")

    # Seed local cache in tbl_vehiclenorc_details
    cache_row = VehicleRCDetails(
        license_plate_RegNo="MH12CAC002",
        owner_name="AMIT SHINDE",
        brand_name="HYUNDAI",
        brand_model="VERNA",
        fuel_type="DIESEL",
        rc_status="ACTIVE",
    )
    db_session.add(cache_row)
    await db_session.commit()

    resp = await async_client.post(
        "/api/v1/integrations/vehicle-rc/lookup",
        json={"registration_number": "MH12CAC002", "force_refresh": False},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["source"] == "LOCAL_CACHE"
    assert data["data"]["owner_name"] == "AMIT SHINDE"
    assert data["data"]["brand_model"] == "VERNA"


@pytest.mark.asyncio
async def test_vehicle_rc_lookup_tier3_external_provider_and_cache_save(async_client: AsyncClient, db_session: AsyncSession):
    _, auth_headers = await create_user_with_role(db_session, "ADMIN")

    # Query novel vehicle number not in internal system or cache
    plate = "MH12EXT003"
    resp = await async_client.post(
        "/api/v1/integrations/vehicle-rc/lookup",
        json={"registration_number": plate, "force_refresh": False},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["source"] == "EXTERNAL_PROVIDER"
    assert data["data"]["license_plate_RegNo"] == plate
    assert data["data"]["brand_name"] == "MARUTI SUZUKI"

    # Confirm it was persisted into tbl_vehiclenorc_details
    await db_session.commit()
    saved = (await db_session.execute(text("SELECT owner_name FROM tbl_vehiclenorc_details WHERE license_plate_RegNo = :p"), {"p": plate})).scalar()
    assert saved == "RAMESH CHANDRA SHARMA"

    # Second call without force_refresh should hit LOCAL_CACHE
    resp2 = await async_client.post(
        "/api/v1/integrations/vehicle-rc/lookup",
        json={"registration_number": plate, "force_refresh": False},
        headers=auth_headers,
    )
    assert resp2.status_code == 200
    assert resp2.json()["source"] == "LOCAL_CACHE"


@pytest.mark.asyncio
async def test_vehicle_rc_lookup_force_refresh_bypasses_cache(async_client: AsyncClient, db_session: AsyncSession):
    _, auth_headers = await create_user_with_role(db_session, "ADMIN")

    plate = "MH12REFR004"
    cache_row = VehicleRCDetails(
        license_plate_RegNo=plate,
        owner_name="OLD OWNER",
        rc_status="ACTIVE",
    )
    db_session.add(cache_row)
    await db_session.commit()

    resp = await async_client.post(
        "/api/v1/integrations/vehicle-rc/lookup",
        json={"registration_number": plate, "force_refresh": True},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["source"] == "EXTERNAL_PROVIDER"


# ---------------------------------------------------------------------------
# 2. OTP Lifecycle HTTP API Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_auth_otp_flow(async_client: AsyncClient, db_session: AsyncSession):
    mob = "9850277777"

    # 1. Request OTP
    req_resp = await async_client.post(
        "/api/v1/auth/otp/request",
        json={"mobile_number": mob, "purpose": "LOGIN"},
    )
    assert req_resp.status_code == 200
    assert req_resp.json()["success"] is True

    # 2. Extract generated OTP from mock SMS
    last_msg = default_mock_sms_provider.sent_messages[-1]["message"]
    otp_code = last_msg.split("is ")[1].split(".")[0].strip()

    # 3. Verify OTP
    verify_resp = await async_client.post(
        "/api/v1/auth/otp/verify",
        json={"mobile_number": mob, "otp_code": otp_code, "purpose": "LOGIN"},
    )
    assert verify_resp.status_code == 200
    v_data = verify_resp.json()
    assert v_data["verified"] is True
    assert v_data["access_token"] is not None


# ---------------------------------------------------------------------------
# 3. Notifications API Tests (SMS, Push, Email)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_notifications_sms_send_and_rbac(async_client: AsyncClient, db_session: AsyncSession):
    _, admin_headers = await create_user_with_role(db_session, "ADMIN")
    _, agent_headers = await create_user_with_role(db_session, "AGENT")

    # Non-admin forbidden
    bad_resp = await async_client.post(
        "/api/v1/notifications/sms/send",
        json={"mobile_number": "9850288888", "message": "Notice"},
        headers=agent_headers,
    )
    assert bad_resp.status_code == 403

    # Admin authorized
    ok_resp = await async_client.post(
        "/api/v1/notifications/sms/send",
        json={"mobile_number": "9850288888", "message": "Notice"},
        headers=admin_headers,
    )
    assert ok_resp.status_code == 200
    assert ok_resp.json()["success"] is True

    # Check tbl_sms_log
    await db_session.commit()
    cnt = (await db_session.execute(text("SELECT count(*) FROM tbl_sms_log WHERE mobile_number = '9850288888'"))).scalar()
    assert cnt == 1


@pytest.mark.asyncio
async def test_notifications_push_send_and_dual_dispatch(async_client: AsyncClient, db_session: AsyncSession):
    admin_user, admin_headers = await create_user_with_role(db_session, "ADMIN")

    resp = await async_client.post(
        "/api/v1/notifications/push/send",
        json={
            "user_ids": [admin_user.UserName],
            "title": "Renewal Due",
            "message": "Policy due in 3 days",
            "notification_type": "RENEWAL",
        },
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["success"] is True

    # Check tbl_pushnotification_log
    await db_session.commit()
    log_cnt = (await db_session.execute(text("SELECT count(*) FROM tbl_pushnotification_log WHERE title = 'Renewal Due'"))).scalar()
    assert log_cnt == 1

    # Check dual-dispatch to tbl_messagemaster and tbl_messagedetails
    master_cnt = (await db_session.execute(text("SELECT count(*) FROM tbl_messagemaster WHERE message = 'Policy due in 3 days'"))).scalar()
    assert master_cnt == 1


@pytest.mark.asyncio
async def test_notifications_email_renewal_report(async_client: AsyncClient, db_session: AsyncSession):
    _, admin_headers = await create_user_with_role(db_session, "ADMIN")

    resp = await async_client.post(
        "/api/v1/notifications/email/send-renewal-report",
        json={"agent_id": 5, "month": 10, "year": "2024-2025"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "Renewal_Report_2024-2025_10.xls" in data["attachment_name"]
