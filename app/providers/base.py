"""
Abstract Base Classes for Phase 13 External Providers.
Enforces decoupling, test isolation, and deterministic mocking.
"""
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from app.schemas.integrations import VehicleRCData
from app.schemas.notifications import SMSResult, PushResult, EmailResult, EmailAttachment


class VehicleRCProvider(ABC):
    """Abstract interface for Vehicle RC & KYC lookup providers."""

    @abstractmethod
    async def lookup_rc(self, registration_number: str) -> Optional[VehicleRCData]:
        """
        Query vehicle registration details from third-party provider.
        Returns VehicleRCData if found, None if record does not exist.
        """
        pass


class SMSProvider(ABC):
    """Abstract interface for outbound SMS gateways."""

    @abstractmethod
    async def send_sms(
        self,
        mobile_number: str,
        message: str,
        template_id: Optional[str] = None,
        variables: Optional[List[str]] = None,
    ) -> SMSResult:
        """
        Dispatches an SMS message.
        Returns SMSResult with status and message ID.
        """
        pass


class PushNotificationProvider(ABC):
    """Abstract interface for targeted push notifications."""

    @abstractmethod
    async def send_push(
        self,
        external_user_ids: List[str],
        title: str,
        message: str,
        notification_type: str = "GENERAL",
        data: Optional[Dict[str, Any]] = None,
    ) -> PushResult:
        """
        Dispatches push notifications to targeted devices.
        Returns PushResult with recipient counts and status.
        """
        pass


class EmailProvider(ABC):
    """Abstract interface for email transmission."""

    @abstractmethod
    async def send_email(
        self,
        recipients: List[str],
        subject: str,
        body_html: str,
        cc: Optional[List[str]] = None,
        attachments: Optional[List[EmailAttachment]] = None,
    ) -> EmailResult:
        """
        Sends an HTML email with optional binary attachments.
        Returns EmailResult.
        """
        pass
