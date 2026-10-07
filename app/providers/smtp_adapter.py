"""
Production SMTP Email Provider Adapter using aiosmtplib.
"""
from typing import Optional, List
from email.message import EmailMessage
import aiosmtplib
from app.core.config import settings
from app.providers.base import EmailProvider
from app.schemas.notifications import EmailResult, EmailAttachment


class SMTPEmailProvider(EmailProvider):
    """Production SMTP Email Adapter using asynchronous aiosmtplib."""

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        from_email: Optional[str] = None,
    ):
        self.host = host or settings.SMTP_HOST
        self.port = port or settings.SMTP_PORT
        self.username = username or settings.SMTP_USERNAME
        self.password = password or settings.SMTP_PASSWORD
        self.from_email = from_email or settings.SMTP_FROM_EMAIL

    async def send_email(
        self,
        recipients: List[str],
        subject: str,
        body_html: str,
        cc: Optional[List[str]] = None,
        attachments: Optional[List[EmailAttachment]] = None,
    ) -> EmailResult:
        msg = EmailMessage()
        msg["From"] = self.from_email
        msg["To"] = ", ".join(recipients)
        if cc:
            msg["Cc"] = ", ".join(cc)
        msg["Subject"] = subject
        msg.set_content(body_html, subtype="html")

        # Process attachments
        first_attachment_name = None
        if attachments:
            for att in attachments:
                maintype, subtype = att.mime_type.split("/", 1) if "/" in att.mime_type else ("application", "octet-stream")
                msg.add_attachment(
                    att.content,
                    maintype=maintype,
                    subtype=subtype,
                    filename=att.filename,
                )
                if not first_attachment_name:
                    first_attachment_name = att.filename

        try:
            await aiosmtplib.send(
                msg,
                hostname=self.host,
                port=self.port,
                start_tls=True,
                username=self.username,
                password=self.password,
            )
            return EmailResult(
                success=True,
                recipient_email=recipients[0],
                attachment_name=first_attachment_name,
                provider="SMTP",
                error_message=None,
            )
        except Exception as e:
            return EmailResult(
                success=False,
                recipient_email=recipients[0],
                attachment_name=first_attachment_name,
                provider="SMTP",
                error_message=str(e),
            )
