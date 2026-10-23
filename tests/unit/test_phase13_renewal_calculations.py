"""
Unit tests for Phase 13 Block E: Policy Renewal Engine & Telecaller CRM Calculations.
Tests Indian financial year boundary logic, renewal state machine, and background tasks.
"""
from datetime import datetime, date, time, timedelta, timezone
from zoneinfo import ZoneInfo
from decimal import Decimal
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.models.renewal import PolicyRenewalStatus, RenewalFollowupHistory
from app.models.transaction import Transaction
from app.models.payment import TransactionPayment
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
    await db_session.execute(text("DELETE FROM tbl_transactionpayment;"))
    await db_session.execute(text("DELETE FROM tbl_transaction;"))
    await db_session.execute(text("DELETE FROM tbl_vehicledetails;"))
    await db_session.commit()
    yield
    await db_session.execute(text("DELETE FROM tbl_renewal_followup_history;"))
    await db_session.execute(text("DELETE FROM tbl_preyearrenewalstatus;"))
    await db_session.execute(text("DELETE FROM tbl_transactionpayment;"))
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
    assert report.get("timezone") == "Asia/Kolkata"
    assert "utc_window_start" in report
    assert "utc_window_end" in report


@pytest.mark.asyncio
async def test_daily_payment_report_ist_midnight_boundary_inclusion_and_exclusion(db_session: AsyncSession):
    """
    Validates that:
    - 2026-10-21 IST business day runs from 2026-10-20 18:30:00 UTC to 2026-10-21 18:30:00 UTC.
    - Payments just after 18:30 UTC are INCLUDED in 2026-10-21 report.
    - Payments just before 18:30 UTC on previous day are EXCLUDED from 2026-10-21 report.
    - Payments just after 18:30 UTC on target day are EXCLUDED from 2026-10-21 report.
    """
    target = date(2026, 10, 21)

    # 1. Payment 1 min before IST midnight (Oct 20 23:59 IST -> Oct 20 18:29 UTC)
    p_prev_day = TransactionPayment(
        PaymentDate=datetime(2026, 10, 20, 18, 29, 0),
        PaidAmount=Decimal("1500.00"),
        PaymentType="Cash",
        isCompletePayment=1,
        isdeleted="0",
    )
    # 2. Payment exact IST midnight (Oct 21 00:00 IST -> Oct 20 18:30 UTC)
    p_exact_midnight = TransactionPayment(
        PaymentDate=datetime(2026, 10, 20, 18, 30, 0),
        PaidAmount=Decimal("2500.00"),
        PaymentType="Online",
        isCompletePayment=1,
        isdeleted="0",
    )
    # 3. Payment 1 min after IST midnight (Oct 21 00:01 IST -> Oct 20 18:31 UTC)
    p_after_midnight = TransactionPayment(
        PaymentDate=datetime(2026, 10, 20, 18, 31, 0),
        PaidAmount=Decimal("3500.00"),
        PaymentType="Cheque",
        isCompletePayment=1,
        isdeleted="0",
    )
    # 4. Payment 1 min before next IST midnight (Oct 21 23:59 IST -> Oct 21 18:29 UTC)
    p_before_next_midnight = TransactionPayment(
        PaymentDate=datetime(2026, 10, 21, 18, 29, 0),
        PaidAmount=Decimal("4500.00"),
        PaymentType="Online",
        isCompletePayment=1,
        isdeleted="0",
    )
    # 5. Payment 1 min after next IST midnight (Oct 22 00:01 IST -> Oct 21 18:31 UTC)
    p_next_day = TransactionPayment(
        PaymentDate=datetime(2026, 10, 21, 18, 31, 0),
        PaidAmount=Decimal("5500.00"),
        PaymentType="Cash",
        isCompletePayment=1,
        isdeleted="0",
    )

    db_session.add_all([p_prev_day, p_exact_midnight, p_after_midnight, p_before_next_midnight, p_next_day])
    await db_session.commit()

    # Query target day 2026-10-21
    rep_21 = await daily_payment_report(db_session, report_date=target)
    assert rep_21["report_date"] == "2026-10-21"
    assert rep_21["receipts_count"] == 3
    assert Decimal(str(rep_21["receipts_total_amount"])) == Decimal("10500.00")  # 2500 + 3500 + 4500

    # Query previous day 2026-10-20
    rep_20 = await daily_payment_report(db_session, report_date=date(2026, 10, 20))
    assert rep_20["receipts_count"] >= 1

    # Query next day 2026-10-22
    rep_22 = await daily_payment_report(db_session, report_date=date(2026, 10, 22))
    assert rep_22["receipts_count"] >= 1


@pytest.mark.asyncio
async def test_daily_payment_report_december_january_rollover(db_session: AsyncSession):
    """
    Validates clean calendar year boundary partitioning:
    - Dec 31 23:59 IST (Dec 31 18:29 UTC) belongs to Dec 31.
    - Jan 01 00:01 IST (Dec 31 18:31 UTC) belongs to Jan 01 of the next year.
    """
    p_dec31 = TransactionPayment(
        PaymentDate=datetime(2026, 12, 31, 18, 29, 0),
        PaidAmount=Decimal("8000.00"),
        isCompletePayment=1,
        isdeleted="0",
    )
    p_jan01 = TransactionPayment(
        PaymentDate=datetime(2026, 12, 31, 18, 31, 0),
        PaidAmount=Decimal("12000.00"),
        isCompletePayment=1,
        isdeleted="0",
    )
    db_session.add_all([p_dec31, p_jan01])
    await db_session.commit()

    rep_dec = await daily_payment_report(db_session, report_date=date(2026, 12, 31))
    rep_jan = await daily_payment_report(db_session, report_date=date(2027, 1, 1))

    assert rep_dec["report_date"] == "2026-12-31"
    assert Decimal(str(rep_dec["receipts_total_amount"])) == Decimal("8000.00")
    assert rep_dec["receipts_count"] == 1

    assert rep_jan["report_date"] == "2027-01-01"
    assert Decimal(str(rep_jan["receipts_total_amount"])) == Decimal("12000.00")
    assert rep_jan["receipts_count"] == 1


@pytest.mark.asyncio
async def test_daily_payment_report_financial_year_transition(db_session: AsyncSession):
    """
    Validates Indian Financial Year cutover:
    - Mar 31 23:59 IST (Mar 31 18:29 UTC) belongs to FY 2025-2026 last day.
    - Apr 01 00:01 IST (Mar 31 18:31 UTC) belongs to FY 2026-2027 first day.
    """
    p_fy_end = TransactionPayment(
        PaymentDate=datetime(2026, 3, 31, 18, 29, 0),
        PaidAmount=Decimal("50000.00"),
        isCompletePayment=1,
        isdeleted="0",
    )
    p_fy_start = TransactionPayment(
        PaymentDate=datetime(2026, 3, 31, 18, 31, 0),
        PaidAmount=Decimal("60000.00"),
        isCompletePayment=1,
        isdeleted="0",
    )
    db_session.add_all([p_fy_end, p_fy_start])
    await db_session.commit()

    rep_mar31 = await daily_payment_report(db_session, report_date=date(2026, 3, 31))
    rep_apr01 = await daily_payment_report(db_session, report_date=date(2026, 4, 1))

    assert rep_mar31["report_date"] == "2026-03-31"
    assert Decimal(str(rep_mar31["receipts_total_amount"])) == Decimal("50000.00")

    assert rep_apr01["report_date"] == "2026-04-01"
    assert Decimal(str(rep_apr01["receipts_total_amount"])) == Decimal("60000.00")


@pytest.mark.asyncio
async def test_daily_payment_report_datetime_inputs_naive_and_aware(db_session: AsyncSession):
    """
    Validates that report_date accepts date, naive datetime, IST-aware datetime,
    and UTC-aware datetime, all resolving to the correct IST calendar day.
    """
    # 1. Pure date
    r1 = await daily_payment_report(db_session, report_date=date(2026, 8, 15))
    assert r1["report_date"] == "2026-08-15"

    # 2. Naive datetime
    r2 = await daily_payment_report(db_session, report_date=datetime(2026, 8, 15, 14, 30))
    assert r2["report_date"] == "2026-08-15"

    # 3. IST-aware datetime
    r3 = await daily_payment_report(
        db_session,
        report_date=datetime(2026, 8, 15, 14, 30, tzinfo=ZoneInfo("Asia/Kolkata"))
    )
    assert r3["report_date"] == "2026-08-15"

    # 4. UTC-aware datetime (09:00 UTC on Aug 15 is 14:30 IST on Aug 15)
    r4 = await daily_payment_report(
        db_session,
        report_date=datetime(2026, 8, 15, 9, 0, tzinfo=timezone.utc)
    )
    assert r4["report_date"] == "2026-08-15"

    # 5. UTC-aware datetime late evening (20:00 UTC on Aug 14 is 01:30 IST on Aug 15)
    r5 = await daily_payment_report(
        db_session,
        report_date=datetime(2026, 8, 14, 20, 0, tzinfo=timezone.utc)
    )
    assert r5["report_date"] == "2026-08-15"


@pytest.mark.asyncio
async def test_daily_payment_report_booked_policies_risk_start_date(db_session: AsyncSession):
    """
    Validates that Transaction.RiskStartdate query path matches calendar date boundaries
    and does not silently substitute or conflate RiskStartdate with PaymentDate.
    """
    target = date(2026, 11, 10)
    tx_today = make_synthetic_tx(
        policy_no="POL-REP-IST-001",
        gross_premium=Decimal("15000.00"),
        agent_id=1,
        branch_id=1,
    )
    tx_today.RiskStartdate = datetime(2026, 11, 10, 0, 0, 0)
    tx_today.Amount = Decimal("15000.00")

    tx_tomorrow = make_synthetic_tx(
        policy_no="POL-REP-IST-002",
        gross_premium=Decimal("25000.00"),
        agent_id=1,
        branch_id=1,
    )
    tx_tomorrow.RiskStartdate = datetime(2026, 11, 11, 0, 0, 0)
    tx_tomorrow.Amount = Decimal("25000.00")

    db_session.add_all([tx_today, tx_tomorrow])
    await db_session.commit()

    report = await daily_payment_report(db_session, report_date=target)
    assert report["booked_policies_count"] == 1
    assert Decimal(str(report["booked_premium_total"])) == Decimal("15000.00")
