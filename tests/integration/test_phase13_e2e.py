"""
Phase 13 End-to-End (E2E) Integration Lifecycle Test.
Simulates full lifecycle across:
1. Vehicle RC Advisory Pre-fill Lookup (3-tier cascade)
2. Customer Mobile OTP Authentication (request -> SMS -> verify -> JWT)
3. Policy Expiration Detection & Due List
4. Background Scheduled Expiry Scanner
5. Telecaller CRM Outreach & Status Transition (Follow -> Done)
6. Push Notification & Dual Dispatch into Internal Inboxes
7. Executive Dashboard Metrics Aggregation
8. Renewal Spreadsheet Email Dispatch
"""
from datetime import datetime, timedelta
import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transaction import Transaction
from app.models.vehicle import VehicleDetails
from app.models.customer import Customer
from app.models.master import InsuranceCompany
from app.providers import default_mock_sms_provider
from app.tasks.renewal_tasks import daily_renewal_expiry_check
from tests.integration.test_phase7_policy_booking_api import create_user_with_role
from tests.integration.test_phase12_search import make_synthetic_tx


@pytest.fixture(autouse=True)
async def cleanup_e2e_tables(db_session: AsyncSession):
    """Purge all Phase 13 operational tables before and after E2E test."""
    await db_session.execute(text("DELETE FROM tbl_renewal_followup_history;"))
    await db_session.execute(text("DELETE FROM tbl_preyearrenewalstatus;"))
    await db_session.execute(text("DELETE FROM tbl_pushnotification_log;"))
    await db_session.execute(text("DELETE FROM tbl_sms_log;"))
    await db_session.execute(text("DELETE FROM tbl_otp_log;"))
    await db_session.execute(text("DELETE FROM tbl_messagedetails;"))
    await db_session.execute(text("DELETE FROM tbl_messagemaster;"))
    await db_session.execute(text("DELETE FROM tbl_vehiclenorc_details;"))
    await db_session.execute(text("DELETE FROM tbl_transaction;"))
    await db_session.execute(text("DELETE FROM tbl_vehicledetails;"))
    await db_session.execute(text("DELETE FROM tbl_customer;"))
    await db_session.execute(text("DELETE FROM tbl_insurancecompany WHERE InsuranceCompanyId = 999;"))
    await db_session.commit()
    yield
    await db_session.execute(text("DELETE FROM tbl_renewal_followup_history;"))
    await db_session.execute(text("DELETE FROM tbl_preyearrenewalstatus;"))
    await db_session.execute(text("DELETE FROM tbl_pushnotification_log;"))
    await db_session.execute(text("DELETE FROM tbl_sms_log;"))
    await db_session.execute(text("DELETE FROM tbl_otp_log;"))
    await db_session.execute(text("DELETE FROM tbl_messagedetails;"))
    await db_session.execute(text("DELETE FROM tbl_messagemaster;"))
    await db_session.execute(text("DELETE FROM tbl_vehiclenorc_details;"))
    await db_session.execute(text("DELETE FROM tbl_transaction;"))
    await db_session.execute(text("DELETE FROM tbl_vehicledetails;"))
    await db_session.execute(text("DELETE FROM tbl_customer;"))
    await db_session.execute(text("DELETE FROM tbl_insurancecompany WHERE InsuranceCompanyId = 999;"))
    await db_session.commit()


@pytest.mark.asyncio
async def test_phase13_full_e2e_lifecycle(async_client: AsyncClient, db_session: AsyncSession):
    # Setup test actors
    admin_user, admin_headers = await create_user_with_role(db_session, "ADMIN")
    telecaller_user, tele_headers = await create_user_with_role(db_session, "OPERATOR", branch_id=1)
    exec_user, _ = await create_user_with_role(db_session, "SALES", branch_id=1, partner_user_id=15)

    reg_plate = "MH12E2E001"
    customer_mobile = "9850290001"
    now = datetime.utcnow()

    # -----------------------------------------------------------------------
    # Step 1: Vehicle RC Lookup (Advisory pre-fill)
    # -----------------------------------------------------------------------
    rc_resp = await async_client.post(
        "/api/v1/integrations/vehicle-rc/lookup",
        json={"registration_number": reg_plate, "force_refresh": False},
        headers=admin_headers,
    )
    assert rc_resp.status_code == 200
    rc_data = rc_resp.json()
    assert rc_data["source"] == "EXTERNAL_PROVIDER"
    assert rc_data["data"]["license_plate_RegNo"] == reg_plate

    # Verify cached in DB
    await db_session.commit()
    cached = (await db_session.execute(text("SELECT license_plate_RegNo FROM tbl_vehiclenorc_details WHERE license_plate_RegNo = :p"), {"p": reg_plate})).scalar()
    assert cached == reg_plate

    # -----------------------------------------------------------------------
    # Step 2: Customer Mobile OTP Authentication
    # -----------------------------------------------------------------------
    otp_req_resp = await async_client.post(
        "/api/v1/auth/otp/request",
        json={"mobile_number": customer_mobile, "purpose": "LOGIN"},
    )
    assert otp_req_resp.status_code == 200
    assert otp_req_resp.json()["success"] is True

    # Extract code from mock SMS
    last_sms = default_mock_sms_provider.sent_messages[-1]["message"]
    otp_code = last_sms.split("is ")[1].split(".")[0].strip()

    otp_verify_resp = await async_client.post(
        "/api/v1/auth/otp/verify",
        json={"mobile_number": customer_mobile, "otp_code": otp_code, "purpose": "LOGIN"},
    )
    assert otp_verify_resp.status_code == 200
    assert otp_verify_resp.json()["verified"] is True
    assert otp_verify_resp.json()["access_token"] is not None

    # -----------------------------------------------------------------------
    # Step 3: Seed Active Policy Nearing Expiration
    # -----------------------------------------------------------------------
    comp = (await db_session.execute(text("SELECT InsuranceCompanyId FROM tbl_insurancecompany WHERE InsuranceCompany = 'ICICI LOMBARD'"))).scalar()
    if not comp:
        ic = InsuranceCompany(
            InsuranceCompanyId=999,
            InsuranceCompany="ICICI LOMBARD",
            NCB="0",
            Cluster="0",
            ZeroDeep="0",
            IsAppQuotation="0",
            CompImgPath="",
            LedgerMId=0,
            ShortName="ICICI",
            PolicyNo="",
            len=0,
        )
        db_session.add(ic)
        await db_session.flush()
        comp_id = ic.InsuranceCompanyId
    else:
        comp_id = comp

    v = VehicleDetails(RegistrationNo=reg_plate, FinancialYear="2024-2025")
    db_session.add(v)
    await db_session.flush()

    tx = make_synthetic_tx(
        policy_no="POL-E2E-9999",
        cust_veh_id=v.CustVehId,
        agent_id=8,
        branch_id=1,
        insurance_company_id=comp_id,
    )
    tx.ExpiryDate = now + timedelta(days=20)
    tx.SalesEx_id = 15
    db_session.add(tx)
    await db_session.commit()

    # Query /renewals/due
    due_resp = await async_client.get("/api/v1/renewals/due?days_ahead=30", headers=admin_headers)
    assert due_resp.status_code == 200
    due_items = due_resp.json()
    assert any(p["registration_no"] == reg_plate for p in due_items)

    # -----------------------------------------------------------------------
    # Step 4: Scheduled Background Expiry Scan
    # -----------------------------------------------------------------------
    scanned_count = await daily_renewal_expiry_check(db_session, days_ahead=30)
    assert scanned_count >= 1

    # -----------------------------------------------------------------------
    # Step 5: Telecaller Follow-Up CRM Interaction
    # -----------------------------------------------------------------------
    follow_resp = await async_client.get(
        "/api/v1/renewals/followups?status=Follow",
        headers=tele_headers,
    )
    assert follow_resp.status_code == 200
    crm_records = follow_resp.json()
    matching_crm = next(r for r in crm_records if r["registration_number"] == reg_plate)
    crm_id = matching_crm["id"]

    # Telecaller updates interaction notes
    update_note_resp = await async_client.post(
        "/api/v1/renewals/followups",
        json={
            "transaction_id": tx.TransanctionId,
            "registration_number": reg_plate,
            "financial_year": matching_crm["financial_year"],
            "remark": "Customer agreed to renew with ICICI Lombard at standard premium.",
            "followup_date": (now + timedelta(days=2)).isoformat(),
            "insurance_company": "ICICI LOMBARD",
            "total_premium": 19500.0,
        },
        headers=tele_headers,
    )
    assert update_note_resp.status_code == 201

    # -----------------------------------------------------------------------
    # Step 6: Targeted Push Notification & Dual Dispatch
    # -----------------------------------------------------------------------
    push_resp = await async_client.post(
        "/api/v1/notifications/push/send",
        json={
            "user_ids": [admin_user.UserName],
            "title": "Renewal Follow-up Alert",
            "message": f"Customer agreed to renew vehicle {reg_plate}.",
            "notification_type": "RENEWAL",
        },
        headers=admin_headers,
    )
    assert push_resp.status_code == 200
    assert push_resp.json()["success"] is True

    # Verify internal inbox tables
    await db_session.commit()
    msg_count = (await db_session.execute(text("SELECT count(*) FROM tbl_messagemaster WHERE message LIKE :p"), {"p": f"%{reg_plate}%"})) .scalar()
    assert msg_count == 1

    # -----------------------------------------------------------------------
    # Step 7: Transition Renewal Status to Done
    # -----------------------------------------------------------------------
    status_resp = await async_client.put(
        f"/api/v1/renewals/{crm_id}/status",
        json={"status": "Done", "remark": "Payment processed and renewed."},
        headers=tele_headers,
    )
    assert status_resp.status_code == 200
    assert status_resp.json()["status"] == "Done"

    # -----------------------------------------------------------------------
    # Step 8: Executive Management Dashboard Metrics
    # -----------------------------------------------------------------------
    dash_resp = await async_client.get(
        f"/api/v1/renewals/dashboard?financial_year={matching_crm['financial_year']}",
        headers=admin_headers,
    )
    assert dash_resp.status_code == 200
    dash_data = dash_resp.json()
    assert dash_data["summary"]["renewed_done_count"] >= 1

    company_breakdown = dash_data["company_breakdown"]
    icici = next(c for c in company_breakdown if c["insurance_company"] == "ICICI LOMBARD")
    assert icici["renewed_count"] >= 1
    assert icici["retention_rate_pct"] > 0.0

    # -----------------------------------------------------------------------
    # Step 9: Renewal Spreadsheet Email Report Dispatch
    # -----------------------------------------------------------------------
    email_resp = await async_client.post(
        "/api/v1/notifications/email/send-renewal-report",
        json={"agent_id": 8, "month": now.month, "year": matching_crm["financial_year"]},
        headers=admin_headers,
    )
    assert email_resp.status_code == 200
    assert email_resp.json()["success"] is True
