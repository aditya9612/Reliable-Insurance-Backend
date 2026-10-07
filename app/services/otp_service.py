"""
Service for Phase 13 Block B — Mobile OTP Generation, Verification & Brute-Force Defense.
Implements the audited OTP lifecycle (5-minute TTL, max 3 attempts, rate limiting).
Replaces legacy USP_UpdateOTP and closes GAP-P5-002 (LBR-002).
"""
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta
from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.config import settings
from app.core.security import create_access_token
from app.models.user import User
from app.repositories.notification import NotificationRepository
from app.services.notification_service import NotificationService
from app.schemas.notifications import OTPResponse, OTPVerifyResponse


class OTPService:
    """Service managing mobile OTP generation, throttling, verification, and token issuance."""

    def __init__(
        self,
        session: AsyncSession,
        notification_service: NotificationService,
    ) -> None:
        self.session = session
        self.repo = NotificationRepository(session)
        self.notification_service = notification_service

    def _hash_otp(self, mobile_number: str, otp_code: str) -> str:
        """Computes salted SHA-256 digest of OTP code."""
        salt = settings.JWT_SECRET_KEY[:16]
        payload = f"{mobile_number}:{otp_code}:{salt}".encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    async def request_otp(
        self,
        mobile_number: str,
        purpose: str = "LOGIN",
    ) -> OTPResponse:
        """
        Generates a 6-digit numeric OTP, enforces rate limiting, stores hashed code,
        and dispatches via SMS.
        """
        clean_mob = mobile_number.strip().replace("+91", "").replace(" ", "")
        if len(clean_mob) < 10:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid mobile number format. Expected 10 digits.",
            )

        # Rate Limiting: Check if active unexpired OTP was requested within cooldown
        existing_active = await self.repo.get_active_otp(clean_mob, purpose=purpose)
        if existing_active:
            elapsed = (datetime.utcnow() - existing_active.created_at).total_seconds()
            cooldown = settings.OTP_RESEND_COOLDOWN_SECONDS
            if elapsed < cooldown:
                wait_secs = int(cooldown - elapsed)
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Please wait {wait_secs} seconds before requesting a new OTP.",
                )

        # Generate cryptographically secure 6-digit OTP
        otp_numeric = f"{secrets.randbelow(900000) + 100000}"
        otp_hash = self._hash_otp(clean_mob, otp_numeric)

        ttl_seconds = settings.OTP_TTL_SECONDS
        expires_at = datetime.utcnow() + timedelta(seconds=ttl_seconds)

        # Save to database log / storage
        await self.repo.save_otp(
            mobile_number=clean_mob,
            otp_hash=otp_hash,
            purpose=purpose,
            expires_at=expires_at,
            max_attempts=settings.OTP_MAX_ATTEMPTS,
        )

        # Dispatch via SMS provider
        sms_body = f"Your Reliable Assurance verification code is {otp_numeric}. Valid for 5 minutes."
        await self.notification_service.send_sms(
            mobile_number=clean_mob,
            message=sms_body,
            template_id="160987",
            variables=[clean_mob, otp_numeric],
        )
        await self.session.commit()

        return OTPResponse(
            success=True,
            message=f"OTP sent to {clean_mob[-4:].rjust(len(clean_mob), '*')}",
            expires_in_seconds=ttl_seconds,
        )

    async def verify_otp(
        self,
        mobile_number: str,
        otp_code: str,
        purpose: str = "LOGIN",
    ) -> OTPVerifyResponse:
        """
        Verifies submitted OTP code with bounded attempts, constant-time comparison,
        and issues JWT access token upon successful authentication.
        """
        clean_mob = mobile_number.strip().replace("+91", "").replace(" ", "")

        active_otp = await self.repo.get_active_otp(clean_mob, purpose=purpose)
        if not active_otp:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired OTP code. Please request a new code.",
            )

        # Check maximum allowed attempts
        if active_otp.attempts_count >= active_otp.max_attempts:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Maximum verification attempts exceeded. This OTP has been invalidated.",
            )

        # Verify hashed code using constant-time comparison
        candidate_hash = self._hash_otp(clean_mob, otp_code.strip())
        is_valid = hmac.compare_digest(active_otp.otp_hash, candidate_hash)

        if not is_valid:
            attempts_now = await self.repo.increment_otp_attempt(active_otp.id)
            await self.session.commit()
            remaining = max(0, active_otp.max_attempts - attempts_now)
            if remaining == 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Maximum verification attempts exceeded. This OTP has been invalidated.",
                )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid OTP code. {remaining} attempt(s) remaining.",
            )

        # Mark OTP consumed
        await self.repo.mark_otp_verified(active_otp.id)
        await self.session.commit()

        # Resolve User by mobile number if exists in tbl_user
        stmt = select(User).where(User.mobile_no == clean_mob)
        user_row = (await self.session.execute(stmt)).scalars().first()

        user_id = user_row.UserId if user_row else 0
        username = user_row.UserName if user_row else f"mobile_{clean_mob}"
        role_name = getattr(user_row, "role_name", "CUSTOMER")

        # Issue JWT Access Token
        token_data = {
            "sub": username,
            "user_id": user_id,
            "role": role_name,
            "mobile": clean_mob,
            "auth_method": "OTP",
        }
        token = create_access_token(data=token_data)

        return OTPVerifyResponse(
            verified=True,
            message="OTP verified successfully.",
            access_token=token,
            token_type="bearer",
            user_id=user_id,
        )
