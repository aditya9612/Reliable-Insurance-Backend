"""
Operational Background Tasks for Phase 13.
Scheduled renewal scanning and daily executive payment reporting.
"""
from datetime import datetime, date, time, timedelta, timezone
from zoneinfo import ZoneInfo
from typing import Dict, Any, List, Optional, Union
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.transaction import Transaction
from app.models.payment import TransactionPayment
from app.services.renewal_service import RenewalService, get_indian_financial_year
from app.schemas.renewal import CreateRenewalFollowupRequest

IST = ZoneInfo("Asia/Kolkata")


async def daily_renewal_expiry_check(
    session: AsyncSession,
    days_ahead: int = 30,
) -> int:
    """
    Scheduled task (daily Celery/cron job) to scan policies nearing expiry,
    identify ones needing follow-up, and ensure they exist in tbl_preyearrenewalstatus.
    Returns count of identified expiring policies.
    """
    renewal_service = RenewalService(session)
    expiring_policies, total = await renewal_service.get_due_renewals(
        days_ahead=days_ahead,
        limit=500,
    )

    current_fy = get_indian_financial_year()
    processed_count = 0

    for pol in expiring_policies:
        # Pre-seed follow-up record if not already recorded
        req = CreateRenewalFollowupRequest(
            transaction_id=pol.transaction_id,
            registration_number=pol.registration_no,
            financial_year=current_fy,
            remark=f"Automated expiry reminder: Policy expires in {pol.days_until_expiry} days.",
            followup_date=pol.expiry_date,
            insurance_company=pol.insurance_company,
            total_premium=pol.gross_premium,
            mobile_number=pol.mobile_no,
            expiry_date=pol.expiry_date,
        )
        await renewal_service.record_followup(
            payload=req,
            recorded_by="CELERY_SCHEDULER",
            user_role_id=0,
            agent_id=pol.agent_id,
            executive_id=pol.executive_id,
            branch_id=pol.branch_id,
        )
        processed_count += 1

    return processed_count


async def daily_payment_report(
    session: AsyncSession,
    report_date: Optional[Union[datetime, date]] = None,
) -> Dict[str, Any]:
    """
    Scheduled task (daily Celery/cron job) to aggregate day's payment instruments
    and booked transactions for executive distribution.
    Replaces legacy InstaPay / daily collection email routines.
    Alings day boundaries to Indian Standard Time (IST, Asia/Kolkata).
    """
    if report_date is None:
        target_date = datetime.now(IST).date()
    elif isinstance(report_date, datetime):
        if report_date.tzinfo is not None:
            target_date = report_date.astimezone(IST).date()
        else:
            target_date = report_date.date()
    elif isinstance(report_date, date):
        target_date = report_date
    else:
        raise ValueError(f"Invalid report_date type: {type(report_date)}")

    # 1. Compute IST midnight boundaries and map to UTC for matching naive UTC PaymentDate
    ist_midnight_start = datetime.combine(target_date, time.min, tzinfo=IST)
    ist_midnight_end = ist_midnight_start + timedelta(days=1)
    utc_payment_start = ist_midnight_start.astimezone(timezone.utc).replace(tzinfo=None)
    utc_payment_end = ist_midnight_end.astimezone(timezone.utc).replace(tzinfo=None)

    # 2. Payments in period (matching UTC window for IST day)
    payment_stmt = (
        select(
            func.count(TransactionPayment.PaymentId),
            func.coalesce(func.sum(TransactionPayment.PaidAmount), 0.0),
        )
        .where(
            TransactionPayment.PaymentDate >= utc_payment_start,
            TransactionPayment.PaymentDate < utc_payment_end,
        )
    )
    payment_res = await session.execute(payment_stmt)
    payment_count, payment_total = payment_res.first()

    # 3. Booked transactions in period (calendar date boundary)
    cal_start = datetime.combine(target_date, time.min)
    cal_end = cal_start + timedelta(days=1)
    tx_stmt = (
        select(
            func.count(Transaction.TransanctionId),
            func.coalesce(func.sum(Transaction.Amount), 0.0),
        )
        .where(
            Transaction.RiskStartdate >= cal_start,
            Transaction.RiskStartdate < cal_end,
            or_(Transaction.isdeleted == "0", Transaction.isdeleted.is_(None)),
        )
    )
    tx_res = await session.execute(tx_stmt)
    tx_count, tx_total = tx_res.first()

    return {
        "report_date": target_date.strftime("%Y-%m-%d"),
        "receipts_count": int(payment_count or 0),
        "receipts_total_amount": float(payment_total or 0.0),
        "payments_count": int(payment_count or 0),
        "payments_total_amount": float(payment_total or 0.0),
        "booked_policies_count": int(tx_count or 0),
        "booked_premium_total": float(tx_total or 0.0),
        "generated_at": datetime.now(IST).isoformat(),
        "timezone": "Asia/Kolkata",
        "utc_window_start": utc_payment_start.isoformat(),
        "utc_window_end": utc_payment_end.isoformat(),
    }
