"""
Production Outbound SMS Adapters (Fast2SMS & IndiaText).
"""
from typing import Optional, List
import httpx
from app.core.config import settings
from app.providers.base import SMSProvider
from app.schemas.notifications import SMSResult


class Fast2SMSProvider(SMSProvider):
    """
    Fast2SMS Bulk V2 Provider with DLT Template support.
    """

    def __init__(self, base_url: Optional[str] = None, api_key: Optional[str] = None):
        self.base_url = base_url or settings.FAST2SMS_BASE_URL
        self.api_key = api_key or settings.FAST2SMS_API_KEY

    async def send_sms(
        self,
        mobile_number: str,
        message: str,
        template_id: Optional[str] = None,
        variables: Optional[List[str]] = None,
    ) -> SMSResult:
        clean_mob = mobile_number.strip().replace("+91", "").replace(" ", "")
        params = {
            "authorization": self.api_key,
            "route": "dlt" if template_id else "v3",
            "sender_id": "relast",
            "numbers": clean_mob,
            "flash": 0,
        }

        if template_id:
            params["message"] = template_id
            var_str = "|".join(variables or []) + "|" if variables else ""
            params["variables_values"] = var_str
        else:
            params["message"] = message

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(self.base_url, params=params)
                resp.raise_for_status()
                data = resp.json()

            success = data.get("return", False) is True
            req_id = str(data.get("request_id", ""))
            return SMSResult(
                success=success,
                message_id=req_id,
                provider="Fast2SMS",
                error_message=None if success else str(data.get("message", "Fast2SMS error")),
            )
        except Exception as e:
            return SMSResult(
                success=False,
                message_id="",
                provider="Fast2SMS",
                error_message=str(e),
            )


class IndiaTextProvider(SMSProvider):
    """
    IndiaText HTTP Transactional Gateway Provider.
    """

    def __init__(self, base_url: Optional[str] = None, user: Optional[str] = None, password: Optional[str] = None):
        self.base_url = base_url or settings.INDIATEXT_BASE_URL
        self.user = user or settings.INDIATEXT_USER
        self.password = password or settings.INDIATEXT_PASSWORD

    async def send_sms(
        self,
        mobile_number: str,
        message: str,
        template_id: Optional[str] = None,
        variables: Optional[List[str]] = None,
    ) -> SMSResult:
        clean_mob = mobile_number.strip().replace("+91", "").replace(" ", "")
        params = {
            "user": self.user,
            "password": self.password,
            "senderid": "RELIBL",
            "channel": "trans",
            "DCS": 8,
            "flashsms": 8,
            "number": clean_mob,
            "text": message,
            "route": "01",
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(self.base_url, params=params)
                resp.raise_for_status()
                body = resp.text

            return SMSResult(
                success=True,
                message_id=f"INDIATEXT-{clean_mob}",
                provider="IndiaText",
                error_message=None,
            )
        except Exception as e:
            return SMSResult(
                success=False,
                message_id="",
                provider="IndiaText",
                error_message=str(e),
            )
