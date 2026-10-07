"""
FastAPI Router for Phase 13 Blocks B, C & D — Multi-Channel Outbound Notifications & Messaging.
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.dependencies import get_db, get_current_user, require_roles
from app.core.rbac import (
    NOTIFICATION_ADMIN_ROLES,
    RENEWAL_EMAIL_ROLES,
    GLOBAL_ADMIN_ROLES,
)
from app.models.user import User
from app.providers import (
    get_sms_provider,
    get_push_provider,
    get_email_provider,
)
from app.providers.base import (
    SMSProvider,
    PushNotificationProvider,
    EmailProvider,
)
from app.schemas.notifications import (
    SendSMSRequest,
    SMSResult,
    SendPushRequest,
    PushResult,
    SendRenewalReportEmailRequest,
    EmailResult,
)
from app.services.notification_service import NotificationService

router = APIRouter()


@router.post(
    "/sms/send",
    response_model=SMSResult,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_roles(*NOTIFICATION_ADMIN_ROLES))],
    summary="Dispatch Outbound Transactional SMS",
    description="Dispatches SMS message via configured provider gateway and audits to tbl_sms_log.",
)
async def send_sms(
    payload: SendSMSRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    sms_provider: SMSProvider = Depends(get_sms_provider),
    push_provider: PushNotificationProvider = Depends(get_push_provider),
    email_provider: EmailProvider = Depends(get_email_provider),
) -> SMSResult:
    """Dispatches transactional SMS to recipient mobile number."""
    service = NotificationService(session, sms_provider, push_provider, email_provider)
    return await service.send_sms(
        mobile_number=payload.mobile_number,
        message=payload.message,
        template_id=payload.template_id,
        variables=payload.variables,
    )


@router.post(
    "/push/send",
    response_model=PushResult,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_roles(*NOTIFICATION_ADMIN_ROLES))],
    summary="Dispatch Targeted Push Notification",
    description=(
        "Dispatches push notification via OneSignal and performs dual-dispatch into "
        "internal database message inboxes (tbl_messagemaster & tbl_messagedetails)."
    ),
)
async def send_push_notification(
    payload: SendPushRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    sms_provider: SMSProvider = Depends(get_sms_provider),
    push_provider: PushNotificationProvider = Depends(get_push_provider),
    email_provider: EmailProvider = Depends(get_email_provider),
) -> PushResult:
    """Dispatches targeted push notification to specified external user IDs."""
    service = NotificationService(session, sms_provider, push_provider, email_provider)
    return await service.send_push_notification(
        external_user_ids=payload.user_ids,
        title=payload.title,
        message=payload.message,
        notification_type=payload.notification_type,
        data=payload.data,
    )


@router.post(
    "/email/send-renewal-report",
    response_model=EmailResult,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_roles(*RENEWAL_EMAIL_ROLES))],
    summary="Generate and Email Renewal Report Spreadsheet",
    description=(
        "Queries expiring policies for the specified agent, formats an in-memory "
        "Excel report attachment, and transmits via SMTP email. Replaces legacy adm_sendExcelTomailRenewal."
    ),
)
async def send_renewal_report_email(
    payload: SendRenewalReportEmailRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    sms_provider: SMSProvider = Depends(get_sms_provider),
    push_provider: PushNotificationProvider = Depends(get_push_provider),
    email_provider: EmailProvider = Depends(get_email_provider),
) -> EmailResult:
    """Generates and dispatches renewal policy Excel report via SMTP email."""
    service = NotificationService(session, sms_provider, push_provider, email_provider)
    return await service.send_renewal_report_email(
        agent_id=payload.agent_id,
        month=payload.month,
        year=payload.year,
    )
