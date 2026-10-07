"""
Deterministic Mock Providers for Phase 13 External Integrations.
Guarantees ZERO live external network calls during testing and local development.
"""
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import uuid
from app.providers.base import (
    VehicleRCProvider,
    SMSProvider,
    PushNotificationProvider,
    EmailProvider,
)
from app.schemas.integrations import VehicleRCData
from app.schemas.notifications import SMSResult, PushResult, EmailResult, EmailAttachment


class MockVehicleRCProvider(VehicleRCProvider):
    """
    Deterministic Mock Vehicle RC Provider.
    Returns synthetic vehicle attributes based on registration number.
    """

    def __init__(self):
        self.lookups: List[str] = []

    async def lookup_rc(self, registration_number: str) -> Optional[VehicleRCData]:
        clean_reg = registration_number.strip().upper().replace(" ", "").replace("-", "")
        self.lookups.append(clean_reg)

        if "NOTFOUND" in clean_reg or "INVALID" in clean_reg:
            return None

        if "ERROR" in clean_reg:
            raise RuntimeError(f"Simulated external RC vendor network timeout for {clean_reg}")

        # Deterministic synthetic data
        req_id = f"APICLUB-REQ-{uuid.uuid4().hex[:8].upper()}"
        return VehicleRCData(
            request_id=req_id,
            license_plate_RegNo=clean_reg,
            owner_name="RAMESH CHANDRA SHARMA",
            father_name="SURESH KUMAR SHARMA",
            is_financed="YES",
            financer="STATE BANK OF INDIA",
            present_address="FLAT 402, SHIVAJI NAGAR, PUNE, MAHARASHTRA 411005",
            permanent_address="FLAT 402, SHIVAJI NAGAR, PUNE, MAHARASHTRA 411005",
            insurance_company="ICICI LOMBARD GENERAL INSURANCE CO LTD",
            insurance_policy="3001/20485910/00/000",
            insurance_expiry=datetime.utcnow() + timedelta(days=25),
            rc_class="Motor Car (LMV)",
            category="4W",
            registration_date=datetime(2020, 5, 12, 10, 30),
            vehicle_age="4 years 5 months",
            pucc_upto=datetime.utcnow() + timedelta(days=120),
            pucc_number="MH12PUC20249811",
            chassis_number="MA3EWB43S00192841",
            engine_number="K12MN8492015",
            fuel_type="PETROL",
            brand_name="MARUTI SUZUKI",
            brand_model="SWIFT VXI",
            body_type="SALOON",
            cubic_capacity="1197",
            gross_weight="1335",
            cylinders="4",
            color="METALLIC GREY",
            norms="BHARAT STAGE VI",
            fit_up_to="11/05/2035",
            manufacturing_date="04/2020",
            manufacturing_date_formatted="2020-04-01",
            rto_name="RTO PUNE",
            latest_by="01/01/2024",
            sleeper_capacity="0",
            standing_capacity="0",
            wheelbase="2450",
            unladen_weight="875",
            noc_details="NO NOC ISSUED",
            seating_capacity="5",
            owner_count="1",
            tax_upto="LIFETIME",
            tax_paid_upto="LIFETIME",
            permit_number="N/A",
            permit_issue_date="N/A",
            permit_valid_from="N/A",
            permit_valid_upto="N/A",
            permit_type="PRIVATE",
            national_permit_number="N/A",
            national_permit_upto="N/A",
            national_permit_issued_by="N/A",
            rc_status="ACTIVE",
            CreatedDate=datetime.utcnow(),
            CreatedBy="MOCK_PROVIDER",
        )


class MockSMSProvider(SMSProvider):
    """
    Deterministic Mock SMS Provider.
    Captures dispatched messages in an in-memory outbox.
    """

    def __init__(self):
        self.outbox: List[Dict[str, Any]] = []

    async def send_sms(
        self,
        mobile_number: str,
        message: str,
        template_id: Optional[str] = None,
        variables: Optional[List[str]] = None,
    ) -> SMSResult:
        msg_id = f"MOCK-SMS-{uuid.uuid4().hex[:8].upper()}"

        record = {
            "message_id": msg_id,
            "mobile_number": mobile_number,
            "message": message,
            "template_id": template_id,
            "variables": variables,
            "dispatched_at": datetime.utcnow(),
        }
        self.outbox.append(record)

        if mobile_number.startswith("000"):
            return SMSResult(
                success=False,
                message_id=msg_id,
                provider="MockSMS",
                error_message="Simulated gateway delivery failure for test number",
            )

        return SMSResult(
            success=True,
            message_id=msg_id,
            provider="MockSMS",
            error_message=None,
        )

    @property
    def sent_messages(self) -> List[Dict[str, Any]]:
        return self.outbox


class MockPushNotificationProvider(PushNotificationProvider):
    """
    Deterministic Mock OneSignal Push Notification Provider.
    Captures push alerts in-memory.
    """

    def __init__(self):
        self.dispatched_alerts: List[Dict[str, Any]] = []

    async def send_push(
        self,
        external_user_ids: List[str],
        title: str,
        message: str,
        notification_type: str = "GENERAL",
        data: Optional[Dict[str, Any]] = None,
    ) -> PushResult:
        ext_id = f"MOCK-ONESIGNAL-{uuid.uuid4().hex[:8].upper()}"

        record = {
            "external_id": ext_id,
            "recipients": external_user_ids,
            "title": title,
            "message": message,
            "notification_type": notification_type,
            "data": data or {},
            "sent_at": datetime.utcnow(),
        }
        self.dispatched_alerts.append(record)

        if any("FAIL" in uid for uid in external_user_ids):
            return PushResult(
                success=False,
                recipients_count=0,
                provider="MockOneSignal",
                external_id=ext_id,
                error_message="Simulated push failure for test user ID",
            )

        return PushResult(
            success=True,
            recipients_count=len(external_user_ids),
            provider="MockOneSignal",
            external_id=ext_id,
            error_message=None,
        )

    @property
    def sent_notifications(self) -> List[Dict[str, Any]]:
        return self.dispatched_alerts


class MockEmailProvider(EmailProvider):
    """
    Deterministic Mock SMTP Email Provider.
    Captures transmitted emails in-memory with attachments.
    """

    def __init__(self):
        self.sent_mailbox: List[Dict[str, Any]] = []

    @property
    def sent_emails(self) -> List[Dict[str, Any]]:
        return self.sent_mailbox

    async def send_email(
        self,
        recipients: List[str],
        subject: str,
        body_html: str,
        cc: Optional[List[str]] = None,
        attachments: Optional[List[EmailAttachment]] = None,
    ) -> EmailResult:
        attachment_names = [a.filename for a in (attachments or [])]

        record = {
            "recipients": recipients,
            "cc": cc or [],
            "subject": subject,
            "body_html": body_html,
            "attachment_names": attachment_names,
            "attachments_count": len(attachments or []),
            "sent_at": datetime.utcnow(),
        }
        self.sent_mailbox.append(record)

        if any("fail" in r.lower() for r in recipients):
            return EmailResult(
                success=False,
                recipient_email=recipients[0],
                attachment_name=attachment_names[0] if attachment_names else None,
                provider="MockEmail",
                error_message="Simulated SMTP connection failure",
            )

        return EmailResult(
            success=True,
            recipient_email=recipients[0],
            attachment_name=attachment_names[0] if attachment_names else None,
            provider="MockEmail",
            error_message=None,
        )
