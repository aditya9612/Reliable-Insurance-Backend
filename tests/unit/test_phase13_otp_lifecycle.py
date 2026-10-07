"""
Unit tests for Phase 13 Block B: Mobile OTP Generation, Verification & Brute-Force Defense.
Tests hashing, bounded attempts, 5-minute TTL, and resend cooldown.
"""
from datetime import datetime, timedelta
import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.core.config import settings
from app.models.notification import OTPLog
from app.models.user import User, UserRole
from app.providers import default_mock_sms_provider, default_mock_push_provider, default_mock_email_provider
from app.services.notification_service import NotificationService
from app.services.otp_service import OTPService


@pytest.fixture(autouse=True)
async def cleanup_otp_tables(db_session: AsyncSession):
    """Purge test OTP logs before and after test."""
    await db_session.execute(text("DELETE FROM tbl_otp_log;"))
    await db_session.execute(text("DELETE FROM tbl_sms_log;"))
    await db_session.commit()
    yield
    await db_session.execute(text("DELETE FROM tbl_otp_log;"))
    await db_session.execute(text("DELETE FROM tbl_sms_log;"))
    await db_session.commit()


@pytest.mark.asyncio
async def test_otp_generation_and_hashing(db_session: AsyncSession):
    notif_svc = NotificationService(
        db_session,
        default_mock_sms_provider,
        default_mock_push_provider,
        default_mock_email_provider,
    )
    otp_svc = OTPService(db_session, notif_svc)

    mob = "9850211111"
    resp = await otp_svc.request_otp(mob, purpose="LOGIN")
    assert resp.success is True
    assert resp.expires_in_seconds == settings.OTP_TTL_SECONDS

    # Verify database has hashed OTP, never plaintext
    active = await otp_svc.repo.get_active_otp(mob, purpose="LOGIN")
    assert active is not None
    assert len(active.otp_hash) == 64  # SHA-256
    assert active.attempts_count == 0
    assert active.is_verified == 0


@pytest.mark.asyncio
async def test_otp_resend_cooldown_throttling(db_session: AsyncSession):
    notif_svc = NotificationService(
        db_session,
        default_mock_sms_provider,
        default_mock_push_provider,
        default_mock_email_provider,
    )
    otp_svc = OTPService(db_session, notif_svc)

    mob = "9850222222"
    await otp_svc.request_otp(mob, purpose="LOGIN")

    # Immediate second request must trigger 429 Too Many Requests
    with pytest.raises(HTTPException) as exc_info:
        await otp_svc.request_otp(mob, purpose="LOGIN")
    assert exc_info.value.status_code == 429
    assert "Please wait" in exc_info.value.detail


@pytest.mark.asyncio
async def test_otp_verification_success_and_jwt(db_session: AsyncSession):
    notif_svc = NotificationService(
        db_session,
        default_mock_sms_provider,
        default_mock_push_provider,
        default_mock_email_provider,
    )
    otp_svc = OTPService(db_session, notif_svc)

    mob = "9850233333"
    await otp_svc.request_otp(mob, purpose="LOGIN")

    # Inspect mock SMS messages to obtain generated OTP code
    last_msg = default_mock_sms_provider.sent_messages[-1]["message"]
    # Body format: "Your Reliable Assurance verification code is XXXXXX. Valid for 5 minutes."
    otp_code = last_msg.split("is ")[1].split(".")[0].strip()

    verify_res = await otp_svc.verify_otp(mob, otp_code, purpose="LOGIN")
    assert verify_res.verified is True
    assert verify_res.access_token is not None
    assert verify_res.token_type == "bearer"

    # Confirm OTP is now marked consumed and cannot be reused
    with pytest.raises(HTTPException) as exc_info:
        await otp_svc.verify_otp(mob, otp_code, purpose="LOGIN")
    assert exc_info.value.status_code == 400


@pytest.mark.asyncio
async def test_otp_invalid_attempts_and_lockout(db_session: AsyncSession):
    notif_svc = NotificationService(
        db_session,
        default_mock_sms_provider,
        default_mock_push_provider,
        default_mock_email_provider,
    )
    otp_svc = OTPService(db_session, notif_svc)

    mob = "9850244444"
    await otp_svc.request_otp(mob, purpose="LOGIN")

    # Attempt 1: wrong code -> 2 remaining
    with pytest.raises(HTTPException) as exc1:
        await otp_svc.verify_otp(mob, "000000", purpose="LOGIN")
    assert "2 attempt(s) remaining" in exc1.value.detail

    # Attempt 2: wrong code -> 1 remaining
    with pytest.raises(HTTPException) as exc2:
        await otp_svc.verify_otp(mob, "111111", purpose="LOGIN")
    assert "1 attempt(s) remaining" in exc2.value.detail

    # Attempt 3: wrong code -> invalidated
    with pytest.raises(HTTPException) as exc3:
        await otp_svc.verify_otp(mob, "222222", purpose="LOGIN")
    assert "Maximum verification attempts exceeded" in exc3.value.detail

    # Subsequent attempt -> rejected
    with pytest.raises(HTTPException) as exc4:
        await otp_svc.verify_otp(mob, "333333", purpose="LOGIN")
    assert exc4.value.status_code == 400


@pytest.mark.asyncio
async def test_otp_expired_ttl(db_session: AsyncSession):
    notif_svc = NotificationService(
        db_session,
        default_mock_sms_provider,
        default_mock_push_provider,
        default_mock_email_provider,
    )
    otp_svc = OTPService(db_session, notif_svc)

    mob = "9850255555"
    # Seed already-expired record
    expired_time = datetime.utcnow() - timedelta(minutes=10)
    hash_val = otp_svc._hash_otp(mob, "123456")
    log_rec = OTPLog(
        mobile_number=mob,
        otp_hash=hash_val,
        purpose="LOGIN",
        expires_at=expired_time,
        created_at=expired_time - timedelta(minutes=1),
        is_verified=0,
        attempts_count=0,
        max_attempts=3,
    )
    db_session.add(log_rec)
    await db_session.commit()

    with pytest.raises(HTTPException) as exc:
        await otp_svc.verify_otp(mob, "123456", purpose="LOGIN")
    assert "Invalid or expired OTP code" in exc.value.detail
