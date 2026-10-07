"""
OneSignal Targeted Push Notification Provider Adapter.
"""
from typing import Optional, List, Dict, Any
import httpx
from app.core.config import settings
from app.providers.base import PushNotificationProvider
from app.schemas.notifications import PushResult


class OneSignalPushProvider(PushNotificationProvider):
    """Production OneSignal REST API Adapter."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        app_id: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        self.base_url = base_url or settings.ONESIGNAL_BASE_URL
        self.app_id = app_id or settings.ONESIGNAL_APP_ID
        self.api_key = api_key or settings.ONESIGNAL_REST_API_KEY

    async def send_push(
        self,
        external_user_ids: List[str],
        title: str,
        message: str,
        notification_type: str = "GENERAL",
        data: Optional[Dict[str, Any]] = None,
    ) -> PushResult:
        payload = {
            "app_id": self.app_id,
            "include_external_user_ids": external_user_ids,
            "headings": {"en": title},
            "contents": {"en": message},
            "data": {
                "app_name": "Reliable Assurance",
                "notification_type": notification_type,
                **(data or {}),
            },
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Basic {self.api_key}",
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(self.base_url, json=payload, headers=headers)
                resp.raise_for_status()
                res_data = resp.json()

            ext_id = str(res_data.get("id", ""))
            recipients = int(res_data.get("recipients", len(external_user_ids)))
            return PushResult(
                success=True,
                recipients_count=recipients,
                provider="OneSignal",
                external_id=ext_id,
                error_message=None,
            )
        except Exception as e:
            return PushResult(
                success=False,
                recipients_count=0,
                provider="OneSignal",
                external_id=None,
                error_message=str(e),
            )
