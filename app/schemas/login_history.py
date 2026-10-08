"""
Pydantic Schemas for Phase 16B — Login History, Session Tracking & Account Unlock.
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict


class LoginHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    LoginHistoryId: int
    UserId: Optional[int] = None
    UserName: Optional[str] = None
    LogInOrLogOut: Optional[str] = None
    funPerform: Optional[str] = None
    IPAddress: Optional[str] = None
    CreateDate: Optional[datetime] = None
    Remark: Optional[str] = None


class LoginHistoryListResponse(BaseModel):
    items: List[LoginHistoryResponse]
    total: int
    limit: int
    offset: int


class AccountUnlockResponse(BaseModel):
    user_id: int
    username: str
    unlocked: bool
    message: str
