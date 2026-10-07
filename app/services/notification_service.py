"""
Service for Phase 13 Blocks B, C & D — Multi-Channel Outbound Notifications & Messaging.
"""
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.repositories.notification import NotificationRepository
from app.models.user import User
from app.models.transaction import Transaction
from app.providers.base import SMSProvider, PushNotificationProvider, EmailProvider
from app.schemas.notifications import (
    SMSResult,
    PushResult,
    EmailResult,
    EmailAttachment,
)


class NotificationService:
    """Service orchestrating SMS, Push, Email, and Internal Inbox messaging."""

    def __init__(
        self,
        session: AsyncSession,
        sms_provider: SMSProvider,
        push_provider: PushNotificationProvider,
        email_provider: EmailProvider,
    ) -> None:
        self.session = session
        self.repo = NotificationRepository(session)
        self.sms_provider = sms_provider
        self.push_provider = push_provider
        self.email_provider = email_provider

    async def send_sms(
        self,
        mobile_number: str,
        message: str,
        template_id: Optional[str] = None,
        variables: Optional[List[str]] = None,
    ) -> SMSResult:
        """Dispatches an outbound SMS and logs the transaction."""
        result = await self.sms_provider.send_sms(
            mobile_number=mobile_number,
            message=message,
            template_id=template_id,
            variables=variables,
        )

        status_str = "SENT" if result.success else "FAILED"
        await self.repo.log_sms(
            mobile_number=mobile_number,
            message_text=message,
            template_id=template_id,
            provider=result.provider,
            status=status_str,
            provider_message_id=result.message_id,
        )
        await self.session.commit()
        return result

    async def send_push_notification(
        self,
        external_user_ids: List[str],
        title: str,
        message: str,
        notification_type: str = "GENERAL",
        data: Optional[Dict[str, Any]] = None,
    ) -> PushResult:
        """
        Dispatches targeted push notifications via OneSignal, logs delivery,
        and performs dual-dispatch into internal inboxes (tbl_messagemaster & tbl_messagedetails).
        """
        result = await self.push_provider.send_push(
            external_user_ids=external_user_ids,
            title=title,
            message=message,
            notification_type=notification_type,
            data=data,
        )

        # 1. Audit log
        status_str = "SUCCESS" if result.success else "FAIL"
        for uid in external_user_ids:
            await self.repo.log_push(
                external_user_id=uid,
                notification_type=notification_type,
                title=title,
                message=message,
                status=status_str,
                provider=result.provider,
                provider_response_id=result.external_id,
            )

        # 2. Dual-dispatch into internal database inboxes
        try:
            msg_master = await self.repo.create_message_master(message)

            # Match external user IDs (e.g. usernames or emp codes) to user IDs
            stmt = select(User).where(User.UserName.in_(external_user_ids))
            users = (await self.session.execute(stmt)).scalars().all()

            flag = "PR" if "RENEWAL" in notification_type.upper() else "PM"
            for u in users:
                await self.repo.create_message_detail(
                    message_id=msg_master.MessageID,
                    user_id=u.UserId,
                    flag=flag,
                    opr="Insert",
                )
        except Exception:
            # Dual-dispatch inbox failure must not crash push response
            pass

        await self.session.commit()
        return result

    async def send_renewal_report_email(
        self,
        agent_id: int,
        month: int,
        year: str,
    ) -> EmailResult:
        """
        Generates renewal spreadsheet report and dispatches via SMTP email.
        Replaces adm_sendExcelTomailRenewal.aspx.cs.
        """
        # Resolve Agent email and user details
        stmt_user = select(User).where(User.UserId == agent_id)
        user_row = (await self.session.execute(stmt_user)).scalars().first()
        recipient_email = getattr(user_row, "EMailId", None) or f"agent_{agent_id}@example.com"
        agent_name = getattr(user_row, "UserName", f"Agent-{agent_id}")

        # Query renewal policies
        stmt_policies = (
            select(Transaction)
            .where(
                Transaction.AgentId == agent_id,
                Transaction.isdeleted == "0",
            )
            .limit(50)
        )
        policies = (await self.session.execute(stmt_policies)).scalars().all()

        # Build in-memory Excel table content (HTML/XML format exactly matching legacy)
        html_table = (
            "<table border='1'>"
            "<tr><th>Sr.No</th><th>Policy No</th><th>Customer ID</th><th>Vehicle ID</th><th>Gross Premium</th><th>Expiry Date</th></tr>"
        )
        for idx, p in enumerate(policies, 1):
            exp_str = p.ExpiryDate.strftime("%d/%m/%Y") if p.ExpiryDate else "N/A"
            prem = float(getattr(p, "Amount", 0.0) or getattr(p, "NetPermium", 0.0) or 0.0)
            html_table += (
                f"<tr><td>{idx}</td><td>{p.PolicyNo or ''}</td><td>{p.CustomerId or ''}</td>"
                f"<td>{p.CustVehId or ''}</td><td>{prem}</td><td>{exp_str}</td></tr>"
            )
        html_table += "</table>"

        excel_bytes = html_table.encode("utf-8")
        excel_filename = f"Renewal_Report_{year}_{month:02d}.xls"

        email_body = f"""<html><body>
        <table style='border-collapse:collapse;font-size:12px;color:#003366'>
        <tr><td><b>Dear {agent_name},</b></td></tr>
        <tr><td>Greetings from Reliable Assurance!</td></tr>
        <tr><td>Please find attached the Renewal Report for Month {month}, Financial Year {year}.</td></tr>
        <tr><td><b>For any query, please contact your Sales Executive.</b></td></tr>
        <tr><td>Regards,</td></tr>
        <tr><td>Reliable Assurance</td></tr>
        <tr><td>Call: 9822166111</td></tr>
        </table>
        </body></html>"""

        attachment = EmailAttachment(
            filename=excel_filename,
            content=excel_bytes,
            mime_type="application/vnd.ms-excel",
        )

        return await self.email_provider.send_email(
            recipients=[recipient_email],
            subject=f"Renewal Report - Month {month} {year}",
            body_html=email_body,
            attachments=[attachment],
        )
