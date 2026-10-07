"""
Pydantic v2 Schemas for Phase 13 Blocks B, C & D — SMS, Push, Email & OTP.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


# --- Block B: SMS & OTP Schemas ---

class SendSMSRequest(BaseModel):
    """Request to send an outbound SMS."""
    model_config = ConfigDict(extra="forbid")

    mobile_number: str = Field(..., min_length=10, max_length=15, description="10-digit mobile number")
    message: str = Field(..., min_length=1, max_length=1000, description="SMS text content")
    template_id: Optional[str] = Field(None, description="Optional DLT template ID for Fast2SMS")
    variables: Optional[List[str]] = Field(None, description="Optional template variable values")


class SMSResult(BaseModel):
    """Result of an SMS dispatch operation."""
    model_config = ConfigDict(from_attributes=True)

    success: bool
    message_id: str
    provider: str
    error_message: Optional[str] = None


class OTPRequest(BaseModel):
    """Request to generate and send an authentication OTP."""
    model_config = ConfigDict(extra="forbid")

    mobile_number: str = Field(..., min_length=10, max_length=15, description="10-digit mobile number")
    purpose: str = Field(default="LOGIN", description="Purpose of OTP: LOGIN, REGISTRATION, RESET")


class OTPResponse(BaseModel):
    """Response after generating an OTP."""
    model_config = ConfigDict(from_attributes=True)

    success: bool
    message: str
    expires_in_seconds: int = 300


class OTPVerifyRequest(BaseModel):
    """Request to verify an OTP code."""
    model_config = ConfigDict(extra="forbid")

    mobile_number: str = Field(..., min_length=10, max_length=15)
    otp_code: str = Field(..., min_length=4, max_length=8)
    purpose: str = Field(default="LOGIN")


class OTPVerifyResponse(BaseModel):
    """Response returned upon OTP verification."""
    model_config = ConfigDict(from_attributes=True)

    verified: bool
    message: str
    access_token: Optional[str] = None
    token_type: Optional[str] = None
    user_id: Optional[int] = None


# --- Block C: Push Notification Schemas ---

class SendPushRequest(BaseModel):
    """Request to dispatch a targeted push notification via OneSignal."""
    model_config = ConfigDict(extra="forbid")

    user_ids: List[str] = Field(..., min_length=1, description="List of external user IDs / agent codes")
    title: str = Field(..., min_length=1, max_length=255)
    message: str = Field(..., min_length=1, max_length=2000)
    notification_type: str = Field(default="GENERAL", description="RENEWAL, BIRTHDAY, POLICY_UPDATE, PAYMENT")
    data: Optional[Dict[str, Any]] = Field(None, description="Optional custom key-value payload")


class PushResult(BaseModel):
    """Result of a push notification dispatch."""
    model_config = ConfigDict(from_attributes=True)

    success: bool
    recipients_count: int
    provider: str
    external_id: Optional[str] = None
    error_message: Optional[str] = None


# --- Block D: SMTP Email Schemas ---

class EmailAttachment(BaseModel):
    """Attachment container for email dispatch."""
    filename: str
    content: bytes
    mime_type: str = "application/octet-stream"


class SendRenewalReportEmailRequest(BaseModel):
    """Request to generate and email a renewal report spreadsheet."""
    model_config = ConfigDict(extra="forbid")

    agent_id: int = Field(..., description="Target Agent / POSP ID")
    month: int = Field(..., ge=1, le=12, description="Report month (1-12)")
    year: str = Field(..., description="Financial year or calendar year label")


class EmailResult(BaseModel):
    """Result of an email transmission."""
    model_config = ConfigDict(from_attributes=True)

    success: bool
    recipient_email: str
    attachment_name: Optional[str] = None
    provider: str
    error_message: Optional[str] = None
