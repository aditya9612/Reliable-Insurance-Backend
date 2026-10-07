# Phase 13 — External Provider Contracts & Abstraction Architecture

> **Audit Status**: COMPLETE (DEFINED FOR FASTAPI MODULAR ARCHITECTURE)  
> **Phase**: Phase 13 (External Integrations, Notifications & Renewal) — Stage A  
> **Repository**: `Reliable-Insurance-Backend`  
> **Mode**: STRICTLY READ-ONLY (No provider code or adapters implemented)

---

## 1. Architectural Motivation

In the legacy .NET system, external third-party services were tightly coupled to ASP.NET codebehind files with hardcoded API keys, unhandled exceptions, and no mechanism to mock or decouple external vendors. This led to:
- Test fragility (inability to run tests without live internet / active vendor credits).
- Security vulnerabilities (API keys exposed in source control and client JavaScript).
- Vendor lock-in (migrating from Signzy to APIClub required rewriting UI pages).

To ensure production safety and zero vendor dependencies during CI/CD, the new backend enforces an **Abstract Provider Pattern** for all 4 external integration domains.

---

## 2. Vehicle Registration (RC) Provider Contract

### 2.1 Interface Definition (`VehicleRCProvider`)
```python
from abc import ABC, abstractmethod
from typing import Optional
from app.schemas.integrations import VehicleRCData

class VehicleRCProvider(ABC):
    """Abstract interface for Vehicle RC & KYC lookup providers."""

    @abstractmethod
    async def lookup_rc(self, registration_number: str) -> Optional[VehicleRCData]:
        """
        Queries external provider for vehicle registration details.
        Returns VehicleRCData if found, None if record does not exist.
        Raises ExternalProviderError on unrecoverable network/vendor errors.
        """
        pass
```

### 2.2 Concrete Implementations
1. **`MockVehicleRCProvider`** (Default for `development` and `testing`):
   - Generates deterministic synthetic vehicle data for known valid test registration numbers (e.g., `MH12AB1234`, `MH14CD5678`).
   - Simulates `"NOT_FOUND"` for registration numbers containing `NOTFOUND`.
   - Simulates vendor timeout/error for numbers containing `ERROR`.
   - **Zero outbound network calls**.
2. **`APIClubRCProvider`** (Production candidate):
   - Invokes APIClub v1 endpoint (`https://prod.apiclub.in/api/v1/rc_info`) via async HTTP client (`httpx.AsyncClient`).
   - Passes `x-api-key` header loaded from `settings.RC_API_KEY`.
   - Maps response fields to canonical `VehicleRCData`.
3. **`SignzyRCProvider`** (Secondary candidate):
   - Invokes Signzy v3 endpoint (`https://api.signzy.app/api/v3/vehicle/detailedsearches`).
   - Passes `Authorization` header loaded from `settings.SIGNZY_API_KEY`.

---

## 3. SMS Gateway Provider Contract

### 3.1 Interface Definition (`SMSProvider`)
```python
from abc import ABC, abstractmethod
from typing import Optional
from app.schemas.notifications import SMSResult

class SMSProvider(ABC):
    """Abstract interface for outbound SMS gateways."""

    @abstractmethod
    async def send_sms(
        self,
        mobile_number: str,
        message: str,
        template_id: Optional[str] = None,
        variables: Optional[list[str]] = None
    ) -> SMSResult:
        """
        Sends an SMS message to a 10-digit Indian mobile number.
        Returns SMSResult with delivery status and provider correlation ID.
        """
        pass
```

### 3.2 Concrete Implementations
1. **`MockSMSProvider`** (Default for `development` and `testing`):
   - Records sent messages into an in-memory test registry (`MockSMSProvider.outbox`).
   - Generates synthetic message IDs (`MOCK-SMS-UUID`).
   - Validates Indian mobile number format (10 digits starting with 6, 7, 8, 9).
2. **`Fast2SMSProvider`** (DLT Production candidate):
   - Dispatches HTTPS request to Fast2SMS Bulk V2 with route `dlt`.
   - Passes template ID and pipe-delimited variable values.
3. **`IndiaTextProvider`** (Transactional legacy candidate):
   - Dispatches HTTP request to IndiaText transactional gateway (`channel=trans`, `route=01`).

---

## 4. Push Notification Provider Contract

### 4.1 Interface Definition (`PushNotificationProvider`)
```python
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from app.schemas.notifications import PushResult

class PushNotificationProvider(ABC):
    """Abstract interface for targeted push notifications."""

    @abstractmethod
    async def send_push(
        self,
        external_user_ids: List[str],
        title: str,
        message: str,
        data: Optional[Dict[str, Any]] = None
    ) -> PushResult:
        """
        Dispatches targeted push notifications to mobile devices.
        Returns PushResult with recipient counts and provider tracking IDs.
        """
        pass
```

### 4.2 Concrete Implementations
1. **`MockPushNotificationProvider`** (Default for `development` and `testing`):
   - Captures targeted external user IDs, title, and body in `MockPushNotificationProvider.dispatched_alerts`.
   - Verifies external user IDs exist in database.
   - Returns mock success with synthetic notification ID.
2. **`OneSignalPushProvider`** (Production candidate):
   - Sends HTTPS POST request to `https://onesignal.com/api/v1/notifications`.
   - Uses `settings.ONESIGNAL_APP_ID` and `settings.ONESIGNAL_REST_API_KEY`.
   - Maps targeted users to `include_external_user_ids`.

---

## 5. SMTP Email Provider Contract

### 5.1 Interface Definition (`EmailProvider`)
```python
from abc import ABC, abstractmethod
from typing import List, Optional
from app.schemas.notifications import EmailResult, EmailAttachment

class EmailProvider(ABC):
    """Abstract interface for outbound email delivery."""

    @abstractmethod
    async def send_email(
        self,
        recipients: List[str],
        subject: str,
        body_html: str,
        cc: Optional[List[str]] = None,
        attachments: Optional[List[EmailAttachment]] = None
    ) -> EmailResult:
        """
        Delivers an HTML email with optional binary attachments.
        """
        pass
```

### 5.2 Concrete Implementations
1. **`MockEmailProvider`** (Default for `development` and `testing`):
   - Stores sent emails and attachment byte streams in `MockEmailProvider.sent_mailbox`.
   - Zero outbound network traffic.
2. **`SMTPEmailProvider`** (Production candidate):
   - Uses `aiosmtplib` for non-blocking asynchronous SMTP delivery.
   - Connects via STARTTLS to `settings.SMTP_HOST` (e.g., `smtp.gmail.com:587`).
   - Authenticates using `settings.SMTP_USER` and `settings.SMTP_PASSWORD`.

---

## 6. Provider Factory & Dependency Injection

The application resolves active providers dynamically via dependency injection in `app/core/dependencies.py`:

```python
def get_rc_provider() -> VehicleRCProvider:
    if settings.RC_PROVIDER_TYPE == "apiclub":
        return APIClubRCProvider()
    elif settings.RC_PROVIDER_TYPE == "signzy":
        return SignzyRCProvider()
    return MockVehicleRCProvider()

def get_sms_provider() -> SMSProvider:
    if settings.SMS_PROVIDER_TYPE == "fast2sms":
        return Fast2SMSProvider()
    elif settings.SMS_PROVIDER_TYPE == "indiatext":
        return IndiaTextProvider()
    return MockSMSProvider()

def get_push_provider() -> PushNotificationProvider:
    if settings.PUSH_PROVIDER_TYPE == "onesignal":
        return OneSignalPushProvider()
    return MockPushNotificationProvider()

def get_email_provider() -> EmailProvider:
    if settings.EMAIL_PROVIDER_TYPE == "smtp":
        return SMTPEmailProvider()
    return MockEmailProvider()
```

---

## 7. Production Isolation & Test Safety Enforcement

1. **Environment Defaults**:
   - In `app/core/config.py`, all provider types default to `"mock"`.
2. **Pytest Protection Guard**:
   - In `tests/conftest.py`, any attempt to instantiate a non-mock provider during automated test execution raises an explicit `RuntimeError("External network access prohibited in test environment")`.
3. **Zero Secrets in Repository**:
   - All production API keys and SMTP credentials remain strictly in external `.env` files, which are excluded by `.gitignore`.
