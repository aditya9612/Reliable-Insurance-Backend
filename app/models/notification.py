"""
SQLAlchemy 2.0 Declarative Models for Phase 13 Blocks B, C & D — Notifications, Internal Inbox & OTP.
Physical Tables:
- tbl_sms_log
- tbl_pushnotification_log
- tbl_messagemaster
- tbl_messagedetails
- tbl_otp_log
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import Integer, String, Text, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class SMSLog(Base):
    """
    Outbound SMS Dispatch Audit Log.
    Physical Table: tbl_sms_log
    """
    __tablename__ = "tbl_sms_log"
    __table_args__ = (
        Index("ix_tbl_sms_log_mobile", "mobile_number"),
        Index("ix_tbl_sms_log_created_at", "created_at"),
        {
            "mysql_charset": "utf8",
            "mysql_collate": "utf8_general_ci",
            "mysql_row_format": "DYNAMIC",
        },
    )

    id: Mapped[int] = mapped_column("id", Integer, primary_key=True, autoincrement=True)
    mobile_number: Mapped[str] = mapped_column("mobile_number", String(20), nullable=False)
    message_text: Mapped[str] = mapped_column("message_text", Text, nullable=False)
    template_id: Mapped[Optional[str]] = mapped_column("template_id", String(50), nullable=True)
    provider: Mapped[str] = mapped_column("provider", String(50), nullable=False)
    status: Mapped[str] = mapped_column("status", String(50), nullable=False)  # SENT, FAILED
    provider_message_id: Mapped[Optional[str]] = mapped_column("provider_message_id", String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column("created_at", DateTime, default=datetime.utcnow, nullable=False)


class PushNotificationLog(Base):
    """
    OneSignal & Mobile Push Notification Delivery Audit Log.
    Physical Table: tbl_pushnotification_log
    """
    __tablename__ = "tbl_pushnotification_log"
    __table_args__ = (
        Index("ix_tbl_push_log_external_user", "external_user_id"),
        Index("ix_tbl_push_log_type", "notification_type"),
        Index("ix_tbl_push_log_created_at", "created_at"),
        {
            "mysql_charset": "utf8",
            "mysql_collate": "utf8_general_ci",
            "mysql_row_format": "DYNAMIC",
        },
    )

    id: Mapped[int] = mapped_column("id", Integer, primary_key=True, autoincrement=True)
    external_user_id: Mapped[str] = mapped_column("external_user_id", String(100), nullable=False)
    notification_type: Mapped[str] = mapped_column("notification_type", String(50), nullable=False)  # RENEWAL, BIRTHDAY, etc.
    title: Mapped[str] = mapped_column("title", String(255), nullable=False)
    message: Mapped[str] = mapped_column("message", Text, nullable=False)
    status: Mapped[str] = mapped_column("status", String(50), nullable=False)  # SUCCESS, FAIL
    provider: Mapped[str] = mapped_column("provider", String(50), nullable=False)  # OneSignal, Mock
    provider_response_id: Mapped[Optional[str]] = mapped_column("provider_response_id", String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column("created_at", DateTime, default=datetime.utcnow, nullable=False)


class MessageMaster(Base):
    """
    Internal Broker Inbox Message Text Master Model.
    Physical Table: tbl_messagemaster
    Primary Key: MessageID
    """
    __tablename__ = "tbl_messagemaster"
    __table_args__ = (
        {
            "mysql_charset": "utf8",
            "mysql_collate": "utf8_general_ci",
            "mysql_row_format": "DYNAMIC",
        },
    )

    MessageID: Mapped[int] = mapped_column("MessageID", Integer, primary_key=True, autoincrement=True)
    Message: Mapped[str] = mapped_column("Message", Text, nullable=False)
    CreatedDate: Mapped[datetime] = mapped_column("CreatedDate", DateTime, default=datetime.utcnow, nullable=False)


class MessageDetail(Base):
    """
    Internal Broker Inbox Message Recipient & Read State Model.
    Physical Table: tbl_messagedetails
    Primary Key: MessagedetailId
    """
    __tablename__ = "tbl_messagedetails"
    __table_args__ = (
        Index("ix_tbl_messagedetails_MessageID", "MessageID"),
        Index("ix_tbl_messagedetails_userId", "userId"),
        Index("ix_tbl_messagedetails_readStatus", "readStatus"),
        {
            "mysql_charset": "utf8",
            "mysql_collate": "utf8_general_ci",
            "mysql_row_format": "DYNAMIC",
        },
    )

    MessagedetailId: Mapped[int] = mapped_column("MessagedetailId", Integer, primary_key=True, autoincrement=True)
    MessageID: Mapped[int] = mapped_column("MessageID", Integer, nullable=False)
    userId: Mapped[int] = mapped_column("userId", Integer, nullable=False)
    Messagedate: Mapped[datetime] = mapped_column("Messagedate", DateTime, default=datetime.utcnow, nullable=False)
    readStatus: Mapped[int] = mapped_column("readStatus", Integer, default=0, nullable=False)  # 0=unread, 1=read
    Flag: Mapped[Optional[str]] = mapped_column("Flag", String(10), nullable=True)  # PR=Renewal, PM=Payment
    Opr: Mapped[Optional[str]] = mapped_column("Opr", String(50), nullable=True)


class OTPLog(Base):
    """
    Mobile OTP Generation & Verification Audit / Fallback Model.
    Physical Table: tbl_otp_log
    Primary Key: id
    """
    __tablename__ = "tbl_otp_log"
    __table_args__ = (
        Index("ix_tbl_otp_log_mobile", "mobile_number"),
        Index("ix_tbl_otp_log_expires_at", "expires_at"),
        {
            "mysql_charset": "utf8",
            "mysql_collate": "utf8_general_ci",
            "mysql_row_format": "DYNAMIC",
        },
    )

    id: Mapped[int] = mapped_column("id", Integer, primary_key=True, autoincrement=True)
    mobile_number: Mapped[str] = mapped_column("mobile_number", String(20), nullable=False)
    otp_hash: Mapped[str] = mapped_column("otp_hash", String(128), nullable=False)
    purpose: Mapped[str] = mapped_column("purpose", String(50), default="LOGIN", nullable=False)
    attempts_count: Mapped[int] = mapped_column("attempts_count", Integer, default=0, nullable=False)
    max_attempts: Mapped[int] = mapped_column("max_attempts", Integer, default=3, nullable=False)
    expires_at: Mapped[datetime] = mapped_column("expires_at", DateTime, nullable=False)
    is_verified: Mapped[int] = mapped_column("is_verified", Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column("created_at", DateTime, default=datetime.utcnow, nullable=False)
