"""
Unit tests for Phase 13 Block E: Policy Renewal Engine & Telecaller CRM Calculations.
Tests Indian financial year boundary logic, renewal state machine, and background tasks.
"""
from datetime import datetime, timedelta
from decimal import Decimal
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.models.renewal import PolicyRenewalStatus, RenewalFollowupHistory
from app.models.transaction import Transaction
from app.models.vehicle import VehicleDetails
from app.services.renewal_service import RenewalService, get_indian_financial_year
from app.schemas.renewal import CreateRenewalFollowupRequest, UpdateRenewalStatusRequest
from app.tasks.renewal_tasks import daily_renewal_expiry_check, daily_payment_report
from tests.integration.test_phase12_search import make_synthetic_tx


# ---------------------------------------------------------------------------
# 1. Indian Financial Year Arithmetic Tests
# ---------------------------------------------------------------------------

def test_indian_financial_year_boundaries():
    # April 1st (Start of FY 2024-2025)
    dt_apr = datetime(2024, 4, 1, 10, 0, 0)
    assert get_indian_financial_year(dt_apr) == "2024-2025"

    # December 31st (Inside FY 2024-2025)
    dt_dec = datetime(2024, 12, 31, 23, 59, 59)
    assert get_indian_financial_year(dt_dec) == "2024-2025"

    # January 1st (Falls into FY 2023-2024 because Month <= 3)
    dt_jan = datetime(2024, 1, 1, 0, 0, 0)
    assert get_indian_financial_year(dt_jan) == "2023-2024"

    # March 31st (Last day of FY 2023-2024)
    dt_mar = datetime(2024, 3, 31, 23, 59, 59)
    assert get_indian_financial_year(dt_mar) == "2023-2024"


# ---------------------------------------------------------------------------
# 2. Renewal State Machine & Follow-Up Lifecycle Tests
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
async def cleanup_renewal_tables(db_session: AsyncSession):
    """Purge test renewal tracking tables before and after test."""
    await db_session.execute(text("DELETE FROM tbl_renewal_followup_history;"))
    await db_session.execute(text("DELETE FROM tbl_preyearrenewalstatus;"))
    await db_session.execute(text("DELETE FROM tbl_transaction;"))
    await db_session.execute(text("DELETE FROM tbl_vehicledetails;"))
    await db_session.commit()
    yield
    await db_session.execute(text("DELETE FROM tbl_renewal_followup_history;"))
    await db_session.execute(text("DELETE FROM tbl_preyearrenewalstatus;"))
    await db_session.execute(text("DELETE FROM tbl_transaction;"))
    await db_session.execute(text("DELETE FROM tbl_vehicledetails;"))
    await db_session.commit()


@pytest.mark.asyncio
async def test_renewal_followup_upsert_and_history(db_session: AsyncSession):
    service = RenewalService(db_session)

    # Initial Follow-Up Interaction
    req1 = CreateRenewalFollowupRequest(
        transaction_id=101,
        registration_number="MH12XY1000",
        financial_year="2024-2025",
        remark="Customer requested quote callback after 6 PM.",
        followup_date=datetime.utcnow() + timedelta(days=2),
        insurance_company="BAJAJ ALLIANZ",
        total_premium=12500.0,
        mobile_number="9850299999",
        expiry_date=datetime.utcnow() + timedelta(days=10),
    )
    rec1 = await service.record_followup(req1, recorded_by="TELECALLER_1", user_role_id=6, agent_id=5, executive_id=12, branch_id=1)
    assert rec1.status == "Follow"
    assert rec1.total_premium == 12500.0

    # Reschedule Callback (Upsert on same RegistrationNo & FinancialYear)
    req2 = CreateRenewalFollowupRequest(
        transaction_id=101,
        registration_number="MH12XY1000",
        financial_year="2024-2025",
        remark="Customer compared ICICI vs Bajaj quote; reschedule 1 day.",
        followup_date=datetime.utcnow() + timedelta(days=3),
    )
    rec2 = await service.record_followup(req2, recorded_by="TELECALLER_1", user_role_id=6, agent_id=5, executive_id=12, branch_id=1)
    assert rec2.id == rec1.id
    assert "compared ICICI" in rec2.remark

    # Verify 2 history log entries created in tbl_renewal_followup_history
    history_rows = (await db_session.execute(text("SELECT id, remark FROM tbl_renewal_followup_history WHERE renewal_status_id = :sid ORDER BY id ASC"), {"sid": rec1.id})).all()
    assert len(history_rows) == 2


@pytest.mark.asyncio
async def test_renewal_status_transitions(db_session: AsyncSession):
    service = RenewalService(db_session)

    req = CreateRenewalFollowupRequest(
        transaction_id=102,
        registration_number="MH12XY2000",
        financial_year="2024-2025",
        remark="Initial outreach",
        followup_date=datetime.utcnow() + timedelta(days=1),
        insurance_company="TATA AIG",
        total_premium=15000.0,
    )
    rec = await service.record_followup(req, recorded_by="TELECALLER_2")
    assert rec.status == "Follow"

    # Transition to Done
    done_res = await service.update_renewal_status(
        rec.id,
        UpdateRenewalStatusRequest(status="Done", remark="Policy successfully renewed with Tata AIG"),
        updated_by="TELECALLER_2",
    )
    assert done_res.status == "Done"
    assert "Done" in done_res.remark

    # Transition to Lost
    lost_res = await service.update_renewal_status(
        rec.id,
        UpdateRenewalStatusRequest(status="Lost", remark="Client took policy directly online"),
        updated_by="TELECALLER_2",
    )
    assert lost_res.status == "Lost"


# ---------------------------------------------------------------------------
# 3. Background Tasks Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_daily_renewal_expiry_check_task(db_session: AsyncSession):
    now = datetime.utcnow()
    # Seed 2 vehicles and expiring policies in tbl_transaction
    v1 = VehicleDetails(RegistrationNo="MH12EXP0001", FinancialYear="2024-2025")
    v2 = VehicleDetails(RegistrationNo="MH12EXP0002", FinancialYear="2024-2025")
    db_session.add_all([v1, v2])
    await db_session.flush()

    tx1 = make_synthetic_tx(
        policy_no="POL-EXP-001",
        cust_veh_id=v1.CustVehId,
        gross_premium=Decimal("18000.00"),
        agent_id=10,
        branch_id=1,
    )
    tx1.RiskStartdate = now - timedelta(days=335)
    tx1.ExpiryDate = now + timedelta(days=5)
    tx1.SalesEx_id = 3

    tx2 = make_synthetic_tx(
        policy_no="POL-EXP-002",
        cust_veh_id=v2.CustVehId,
        gross_premium=Decimal("22000.00"),
        agent_id=10,
        branch_id=1,
    )
    tx2.RiskStartdate = now - timedelta(days=335)
    tx2.ExpiryDate = now + timedelta(days=12)
    tx2.SalesEx_id = 3

    db_session.add_all([tx1, tx2])
    await db_session.commit()

    # Run background check for policies expiring in <= 30 days
    processed = await daily_renewal_expiry_check(db_session, days_ahead=30)
    assert processed == 2

    # Verify status records created in tbl_preyearrenewalstatus
    rows = (await db_session.execute(text("SELECT RegistrationNo, RenewalStatus FROM tbl_preyearrenewalstatus WHERE isdeleted = 0"))).all()
    assert len(rows) == 2
    assert all(r[1] == "Follow" for r in rows)


@pytest.mark.asyncio
async def test_daily_payment_report_task(db_session: AsyncSession):
    report = await daily_payment_report(db_session)
    assert "report_date" in report
    assert "receipts_count" in report
    assert "booked_policies_count" in report
    assert "generated_at" in report
