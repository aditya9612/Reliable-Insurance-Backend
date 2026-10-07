"""
Operational Background Tasks for Phase 13.
Scheduled renewal scanning and daily executive payment reporting.
"""
from datetime import datetime, timedelta
from typing import Dict, Any, List
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.transaction import Transaction
from app.models.payment import TransactionPayment
from app.services.renewal_service import RenewalService, get_indian_financial_year
from app.schemas.renewal import CreateRenewalFollowupRequest


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
    report_date: datetime = None,
) -> Dict[str, Any]:
    """
    Scheduled task (daily Celery/cron job) to aggregate day's payment instruments
    and booked transactions for executive distribution.
    Replaces legacy InstaPay / daily collection email routines.
    """
    if report_date is None:
        report_date = datetime.utcnow()

    start_of_day = datetime(report_date.year, report_date.month, report_date.day, 0, 0, 0)
    end_of_day = start_of_day + timedelta(days=1)

    # 1. Payments in period
    payment_stmt = (
        select(
            func.count(TransactionPayment.PaymentId),
            func.coalesce(func.sum(TransactionPayment.PaidAmount), 0.0),
        )
        .where(
            TransactionPayment.PaymentDate >= start_of_day,
            TransactionPayment.PaymentDate < end_of_day,
        )
    )
    payment_res = await session.execute(payment_stmt)
    payment_count, payment_total = payment_res.first()

    # 2. Booked transactions in period
    tx_stmt = (
        select(
            func.count(Transaction.TransanctionId),
            func.coalesce(func.sum(Transaction.Amount), 0.0),
        )
        .where(
            Transaction.RiskStartdate >= start_of_day,
            Transaction.RiskStartdate < end_of_day,
            or_(Transaction.isdeleted == "0", Transaction.isdeleted.is_(None)),
        )
    )
    tx_res = await session.execute(tx_stmt)
    tx_count, tx_total = tx_res.first()

    return {
        "report_date": start_of_day.strftime("%Y-%m-%d"),
        "receipts_count": int(payment_count or 0),
        "receipts_total_amount": float(payment_total or 0.0),
        "payments_count": int(payment_count or 0),
        "payments_total_amount": float(payment_total or 0.0),
        "booked_policies_count": int(tx_count or 0),
        "booked_premium_total": float(tx_total or 0.0),
        "generated_at": datetime.utcnow().isoformat(),
    }
