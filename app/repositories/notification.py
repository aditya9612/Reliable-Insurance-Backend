"""
Repository for Phase 13 Blocks B, C & D — Notifications, Messaging and OTP persistence.
"""
from datetime import datetime
from typing import Optional, List, Sequence, Tuple
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.notification import (
    SMSLog,
    PushNotificationLog,
    MessageMaster,
    MessageDetail,
    OTPLog,
)
from app.repositories.base import BaseRepository


class NotificationRepository:
    """Repository handling notification logs, internal inboxes and OTP storage."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def log_sms(
        self,
        mobile_number: str,
        message_text: str,
        template_id: Optional[str],
        provider: str,
        status: str,
        provider_message_id: Optional[str],
    ) -> SMSLog:
        """Records an outbound SMS into tbl_sms_log."""
        entry = SMSLog(
            mobile_number=mobile_number,
            message_text=message_text,
            template_id=template_id,
            provider=provider,
            status=status,
            provider_message_id=provider_message_id,
            created_at=datetime.utcnow(),
        )
        self.session.add(entry)
        await self.session.flush()
        return entry

    async def log_push(
        self,
        external_user_id: str,
        notification_type: str,
        title: str,
        message: str,
        status: str,
        provider: str,
        provider_response_id: Optional[str] = None,
    ) -> PushNotificationLog:
        """
        Records a push notification into tbl_pushnotification_log.
        Replaces sp_InsertRenewalNotiStatus.
        """
        entry = PushNotificationLog(
            external_user_id=external_user_id,
            notification_type=notification_type,
            title=title,
            message=message,
            status=status,
            provider=provider,
            provider_response_id=provider_response_id,
            created_at=datetime.utcnow(),
        )
        self.session.add(entry)
        await self.session.flush()
        return entry

    async def create_message_master(self, message: str) -> MessageMaster:
        """
        Inserts message text into tbl_messagemaster.
        Replaces sp_InsertMessageMaster.
        """
        master = MessageMaster(
            Message=message,
            CreatedDate=datetime.utcnow(),
        )
        self.session.add(master)
        await self.session.flush()
        return master

    async def create_message_detail(
        self,
        message_id: int,
        user_id: int,
        flag: Optional[str] = "PR",
        opr: Optional[str] = "Insert",
    ) -> MessageDetail:
        """
        Dispatches message into user's internal inbox in tbl_messagedetails.
        Replaces Sp_MessageOperation.
        """
        detail = MessageDetail(
            MessageID=message_id,
            userId=user_id,
            Messagedate=datetime.utcnow(),
            readStatus=0,
            Flag=flag,
            Opr=opr,
        )
        self.session.add(detail)
        await self.session.flush()
        return detail

    async def get_user_messages(
        self,
        user_id: int,
        unread_only: bool = False,
    ) -> Sequence[Tuple[MessageDetail, MessageMaster]]:
        """Queries user messages with master text."""
        stmt = (
            select(MessageDetail, MessageMaster)
            .join(MessageMaster, MessageMaster.MessageID == MessageDetail.MessageID)
            .where(MessageDetail.userId == user_id)
        )
        if unread_only:
            stmt = stmt.where(MessageDetail.readStatus == 0)
        stmt = stmt.order_by(MessageDetail.Messagedate.desc())

        result = await self.session.execute(stmt)
        return result.all()

    async def save_otp(
        self,
        mobile_number: str,
        otp_hash: str,
        purpose: str,
        expires_at: datetime,
        max_attempts: int = 3,
    ) -> OTPLog:
        """
        Saves a newly generated OTP into tbl_otp_log.
        Replaces USP_UpdateOTP (GENERATE).
        """
        clean_mob = mobile_number.strip().replace("+91", "").replace(" ", "")
        entry = OTPLog(
            mobile_number=clean_mob,
            otp_hash=otp_hash,
            purpose=purpose,
            attempts_count=0,
            max_attempts=max_attempts,
            expires_at=expires_at,
            is_verified=0,
            created_at=datetime.utcnow(),
        )
        self.session.add(entry)
        await self.session.flush()
        return entry

    async def get_active_otp(
        self,
        mobile_number: str,
        purpose: str = "LOGIN",
    ) -> Optional[OTPLog]:
        """Retrieves latest unverified and unexpired OTP for mobile."""
        clean_mob = mobile_number.strip().replace("+91", "").replace(" ", "")
        now = datetime.utcnow()
        stmt = (
            select(OTPLog)
            .where(
                OTPLog.mobile_number == clean_mob,
                OTPLog.purpose == purpose,
                OTPLog.is_verified == 0,
                OTPLog.expires_at > now,
            )
            .order_by(OTPLog.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def increment_otp_attempt(self, otp_id: int) -> int:
        """Increments failed verification attempts counter."""
        stmt = (
            update(OTPLog)
            .where(OTPLog.id == otp_id)
            .values(attempts_count=OTPLog.attempts_count + 1)
        )
        await self.session.execute(stmt)
        await self.session.flush()
        # Fetch updated
        refetched = await self.session.get(OTPLog, otp_id)
        return refetched.attempts_count if refetched else 0

    async def mark_otp_verified(self, otp_id: int) -> None:
        """
        Marks OTP as verified/consumed.
        Replaces USP_UpdateOTP (VERIFY).
        """
        stmt = (
            update(OTPLog)
            .where(OTPLog.id == otp_id)
            .values(is_verified=1)
        )
        await self.session.execute(stmt)
        await self.session.flush()
