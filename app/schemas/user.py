"""
Pydantic Schemas for Phase 16B — User Management, Account Lifecycle & Role Directory.
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field


class UserBase(BaseModel):
    UserName: str = Field(..., min_length=3, max_length=255)
    UserRoleId: Optional[int] = None
    BranchId: Optional[int] = None
    isappuser: Optional[str] = "0"
    partner_user_id: Optional[str] = None
    mobile_no: Optional[str] = None


class UserCreate(UserBase):
    UserPassword: str = Field(..., min_length=6, max_length=255)


class UserUpdate(BaseModel):
    UserRoleId: Optional[int] = None
    BranchId: Optional[int] = None
    isappuser: Optional[str] = None
    partner_user_id: Optional[str] = None
    mobile_no: Optional[str] = None


class UserPasswordResetRequest(BaseModel):
    new_password: str = Field(..., min_length=6, max_length=255)


class UserPasswordChangeRequest(BaseModel):
    old_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=6, max_length=255)


class UserStatusUpdateRequest(BaseModel):
    isdeleted: Optional[str] = Field(None, description="'0' for active, '1' for locked/inactive")
    is_active: Optional[bool] = Field(None, description="True for active, False for locked/inactive")


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    UserId: int
    UserName: Optional[str] = None
    UserRoleId: Optional[int] = None
    BranchId: Optional[int] = None
    isappuser: Optional[str] = None
    isdeleted: Optional[str] = None
    is_active: bool
    CreateDate: Optional[datetime] = None
    CreateUser: Optional[str] = None
    UpdateDate: Optional[datetime] = None
    UpdateUser: Optional[str] = None
    partner_user_id: Optional[str] = None
    mobile_no: Optional[str] = None


class UserListResponse(BaseModel):
    items: List[UserResponse]
    total: int
    limit: int
    offset: int


class UserRoleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    UserRoleId: int
    UserRole: Optional[str] = None
    code: Optional[str] = None
    isdeleted: Optional[str] = None
    is_active: bool


class UsernameCheckResponse(BaseModel):
    username: str
    is_available: bool
