"""
Provider Package Exports and Factory Injections for Phase 13.
"""
from app.core.config import settings
from app.providers.base import (
    VehicleRCProvider,
    SMSProvider,
    PushNotificationProvider,
    EmailProvider,
)
from app.providers.mock_providers import (
    MockVehicleRCProvider,
    MockSMSProvider,
    MockPushNotificationProvider,
    MockEmailProvider,
)
from app.providers.apiclub import APIClubRCProvider
from app.providers.signzy import SignzyRCProvider
from app.providers.attestr import AttestrRCProvider
from app.providers.sms_adapters import Fast2SMSProvider, IndiaTextProvider
from app.providers.onesignal import OneSignalPushProvider
from app.providers.smtp_adapter import SMTPEmailProvider

# Global test-accessible mock singletons
default_mock_rc_provider = MockVehicleRCProvider()
default_mock_sms_provider = MockSMSProvider()
default_mock_push_provider = MockPushNotificationProvider()
default_mock_email_provider = MockEmailProvider()


def get_vehicle_rc_provider() -> VehicleRCProvider:
    """Dependency / factory for Vehicle RC Provider."""
    if settings.RC_PROVIDER_TYPE == "apiclub":
        return APIClubRCProvider()
    elif settings.RC_PROVIDER_TYPE == "signzy":
        return SignzyRCProvider()
    elif settings.RC_PROVIDER_TYPE == "attestr":
        return AttestrRCProvider()
    return default_mock_rc_provider


def resolve_vehicle_rc_provider(provider_name: str | None = None) -> VehicleRCProvider:
    """Resolve explicit RC provider adapter by name or fall back to configured default."""
    selected = (provider_name or settings.RC_PROVIDER_TYPE or "mock").strip().lower()
    if selected == "apiclub":
        return APIClubRCProvider()
    if selected == "signzy":
        return SignzyRCProvider()
    if selected == "attestr":
        return AttestrRCProvider()
    return default_mock_rc_provider


def get_sms_provider() -> SMSProvider:
    """Dependency / factory for SMS Provider."""
    if settings.SMS_PROVIDER_TYPE == "fast2sms":
        return Fast2SMSProvider()
    elif settings.SMS_PROVIDER_TYPE == "indiatext":
        return IndiaTextProvider()
    return default_mock_sms_provider


def get_push_provider() -> PushNotificationProvider:
    """Dependency / factory for Push Notification Provider."""
    if settings.PUSH_PROVIDER_TYPE == "onesignal":
        return OneSignalPushProvider()
    return default_mock_push_provider


def get_email_provider() -> EmailProvider:
    """Dependency / factory for Email Provider."""
    if settings.EMAIL_PROVIDER_TYPE == "smtp":
        return SMTPEmailProvider()
    return default_mock_email_provider


__all__ = [
    "VehicleRCProvider",
    "SMSProvider",
    "PushNotificationProvider",
    "EmailProvider",
    "MockVehicleRCProvider",
    "MockSMSProvider",
    "MockPushNotificationProvider",
    "MockEmailProvider",
    "APIClubRCProvider",
    "SignzyRCProvider",
    "AttestrRCProvider",
    "Fast2SMSProvider",
    "IndiaTextProvider",
    "OneSignalPushProvider",
    "SMTPEmailProvider",
    "default_mock_rc_provider",
    "default_mock_sms_provider",
    "default_mock_push_provider",
    "default_mock_email_provider",
    "get_vehicle_rc_provider",
    "resolve_vehicle_rc_provider",
    "get_sms_provider",
    "get_push_provider",
    "get_email_provider",
]
