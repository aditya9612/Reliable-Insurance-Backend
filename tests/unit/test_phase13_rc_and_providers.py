"""
Unit tests for Phase 13 Block A, B, C & D: Vehicle RC and Provider Abstractions.
Verifies all mock providers, HTTP adapters with mocked transport, and error cases.
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.providers.mock_providers import (
    MockVehicleRCProvider,
    MockSMSProvider,
    MockPushNotificationProvider,
    MockEmailProvider,
)
from app.providers.apiclub import APIClubRCProvider
from app.providers.signzy import SignzyRCProvider
from app.providers.sms_adapters import Fast2SMSProvider, IndiaTextProvider
from app.providers.onesignal import OneSignalPushProvider
from app.providers.smtp_adapter import SMTPEmailProvider
from app.schemas.notifications import EmailAttachment


# ---------------------------------------------------------------------------
# 1. Mock RC Provider Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_mock_vehicle_rc_provider_success():
    provider = MockVehicleRCProvider()
    data = await provider.lookup_rc("MH12AB1234")
    assert data is not None
    assert data.license_plate_RegNo == "MH12AB1234"
    assert data.brand_name == "MARUTI SUZUKI"
    assert data.owner_name == "RAMESH CHANDRA SHARMA"
    assert data.fuel_type == "PETROL"
    assert data.rc_status == "ACTIVE"


@pytest.mark.asyncio
async def test_mock_vehicle_rc_provider_not_found():
    provider = MockVehicleRCProvider()
    data = await provider.lookup_rc("MH12NOTFOUND")
    assert data is None


@pytest.mark.asyncio
async def test_mock_vehicle_rc_provider_error():
    provider = MockVehicleRCProvider()
    with pytest.raises(RuntimeError, match="Simulated external RC vendor network timeout"):
        await provider.lookup_rc("MH12ERROR9999")


# ---------------------------------------------------------------------------
# 2. APIClub & Signzy HTTP Adapters (Mocked httpx)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_apiclub_rc_provider_success():
    mock_response = {
        "status": "success",
        "response": {
            "regNo": "MH14DE5678",
            "owner": "SURESH PATIL",
            "fatherName": "RAMDAS PATIL",
            "insurance": {"company": "BAJAJ ALLIANZ", "policy": "OG-20-100", "expiry": "2025-05-10"},
            "chassis": "MAT1234",
            "engine": "ENG5678",
            "fuelType": "DIESEL",
            "maker": "HYUNDAI",
            "model": "CRETA",
            "class": "LMV",
        }
    }
    
    provider = APIClubRCProvider(base_url="https://mock.apiclub.in/rc", api_key="test_key")
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_response
        mock_post.return_value = mock_resp

        result = await provider.lookup_rc("MH14DE5678")
        assert result is not None
        assert result.license_plate_RegNo == "MH14DE5678"
        assert result.owner_name == "SURESH PATIL"
        assert result.brand_name == "HYUNDAI"


@pytest.mark.asyncio
async def test_signzy_rc_provider_success():
    mock_response = {
        "result": {
            "regNo": "MH01AB9999",
            "ownerName": "ANIL AGRAWAL",
            "vehicleClassDesc": "MOTOR CAR",
            "vehicleInsuranceCompanyName": "TATA AIG",
            "vehicleInsuranceUpto": "2025-12-31",
            "chassis": "CH123",
            "engine": "EN456",
            "type": "PETROL",
            "makerDescription": "HONDA",
            "makerModel": "CITY",
        }
    }

    provider = SignzyRCProvider(base_url="https://mock.signzy.in/rc", api_key="test_token")
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_response
        mock_post.return_value = mock_resp

        result = await provider.lookup_rc("MH01AB9999")
        assert result is not None
        assert result.license_plate_RegNo == "MH01AB9999"
        assert result.owner_name == "ANIL AGRAWAL"
        assert result.insurance_company == "TATA AIG"


# ---------------------------------------------------------------------------
# 3. SMS Providers Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_mock_sms_provider_dispatch():
    provider = MockSMSProvider()
    res = await provider.send_sms("9850266111", "Test message")
    assert res.success is True
    assert res.provider == "MockSMS"
    assert len(provider.outbox) == 1
    assert provider.outbox[0]["mobile_number"] == "9850266111"


@pytest.mark.asyncio
async def test_fast2sms_adapter():
    provider = Fast2SMSProvider(base_url="https://mock.fast2sms.com/dev/bulkV2", api_key="fast_key")
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"return": True, "request_id": "REQ123"}
        mock_get.return_value = mock_resp

        res = await provider.send_sms("9850266111", "Hello Fast2SMS")
        assert res.success is True
        assert res.provider == "Fast2SMS"


@pytest.mark.asyncio
async def test_indiatext_adapter():
    provider = IndiaTextProvider(base_url="https://mock.indiatext.com/send", user="test_usr", password="pw")
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "MSG_ID: IND888999"
        mock_get.return_value = mock_resp

        res = await provider.send_sms("9850266111", "Hello IndiaText")
        assert res.success is True
        assert res.provider == "IndiaText"


# ---------------------------------------------------------------------------
# 4. Push Notification Providers Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_mock_push_provider():
    provider = MockPushNotificationProvider()
    res = await provider.send_push(["AGT001", "AGT002"], "Renewal Alert", "Expiring soon")
    assert res.success is True
    assert res.recipients_count == 2
    assert res.provider == "MockOneSignal"
    assert len(provider.dispatched_alerts) == 1


@pytest.mark.asyncio
async def test_onesignal_adapter():
    provider = OneSignalPushProvider(base_url="https://mock.onesignal.com/api/v1/notifications", app_id="app_123", api_key="rest_key")
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"id": "OS_NOTIF_789", "recipients": 3}
        mock_post.return_value = mock_resp

        res = await provider.send_push(["U1", "U2", "U3"], "Hello", "World")
        assert res.success is True
        assert res.recipients_count == 3
        assert res.provider == "OneSignal"


# ---------------------------------------------------------------------------
# 5. Email Providers Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_mock_email_provider():
    provider = MockEmailProvider()
    att = EmailAttachment(filename="test.xls", content=b"fake-content")
    res = await provider.send_email(["test@example.com"], "Report", "<h1>Report</h1>", attachments=[att])
    assert res.success is True
    assert res.provider == "MockEmail"
    assert res.recipient_email == "test@example.com"
    assert res.attachment_name == "test.xls"
    assert len(provider.sent_mailbox) == 1


@pytest.mark.asyncio
async def test_smtp_email_provider_dispatch():
    provider = SMTPEmailProvider()
    att = EmailAttachment(filename="renewal.xls", content=b"test-bytes", mime_type="application/vnd.ms-excel")
    with patch("aiosmtplib.send", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = ("250", "OK")
        res = await provider.send_email(
            recipients=["user@example.com"],
            subject="Renewal Notice",
            body_html="<p>Please renew</p>",
            attachments=[att],
        )
        assert res.success is True
        assert res.provider == "SMTP"
        assert res.recipient_email == "user@example.com"
