"""
Operational Background Tasks for Phase 15B.
Scheduled jobs for:
- Overdue cheque user login locking (LBR-069)
- Customer & partner birthday greeting dispatch (SendPushNotiForBdayWish.aspx)
- Stale e-wallet reservation release
- Ephemeral storage cleanup
"""
from datetime import datetime, date
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.utility_service import UtilityService


async def enforce_overdue_cheque_locks_task(
    session: AsyncSession, threshold_days: int = 15
) -> Dict[str, Any]:
    """
    Scheduled job: scans for cheques pending > threshold_days and flags user accounts.
    """
    service = UtilityService(session)
    res = await service.enforce_overdue_cheque_locks(threshold_days=threshold_days)
    return res.model_dump()


async def dispatch_birthday_greetings_task(
    session: AsyncSession, target_date: Optional[date] = None
) -> Dict[str, Any]:
    """
    Scheduled job: scans for customers and partners celebrating their birthday today and dispatches greetings.
    """
    service = UtilityService(session)
    res = await service.dispatch_birthday_greetings(target_date=target_date)
    return res.model_dump()


async def cleanup_stale_wallet_locks_task(
    session: AsyncSession,
) -> Dict[str, Any]:
    """
    Scheduled job: releases wallet locks older than 30 minutes.
    """
    service = UtilityService(session)
    res = await service.cleanup_stale_wallet_locks()
    return res.model_dump()


async def cleanup_ephemeral_storage_task(
    session: AsyncSession,
) -> Dict[str, Any]:
    """
    Scheduled job: purges temporary upload files older than 24 hours.
    """
    service = UtilityService(session)
    res = await service.cleanup_ephemeral_storage()
    return res.model_dump()
