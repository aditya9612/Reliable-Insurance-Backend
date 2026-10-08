"""
Pydantic Schemas for Phase 16B — Dynamic Privilege & Menu Presentation Tree.
UI Presentation ONLY — Backend authorization remains strictly enforced by RBAC dependencies.
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field


class MenuResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    MenuId: int
    MenuName: Optional[str] = None
    MenuUrl: Optional[str] = None
    ParentMenuId: int = 0
    OrderNo: int = 0
    IconClass: Optional[str] = None
    isdeleted: str = "0"
    is_active: bool = True
    children: List["MenuResponse"] = []


class RolePrivilegeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    Id: int
    BranchId: Optional[int] = None
    RoleId: Optional[int] = None
    ScreenId: Optional[int] = None
    CreateDate: Optional[datetime] = None
    isdeleted: str = "0"
    is_active: bool = True


class RolePrivilegeAssignRequest(BaseModel):
    role_id: int = Field(..., gt=0, description="Target Role ID")
    branch_id: Optional[int] = Field(None, description="Optional Branch scope")
    screen_ids: List[int] = Field(..., description="List of Screen / Menu IDs to grant")


class RolePrivilegeAssignResponse(BaseModel):
    role_id: int
    branch_id: Optional[int] = None
    assigned_screen_ids: List[int]
    message: str


class DynamicMenuTreeResponse(BaseModel):
    role_id: int
    role_name: Optional[str] = None
    menus: List[MenuResponse]
