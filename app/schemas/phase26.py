"""
Pydantic v2 Schemas for Phase 26:
Emergency Roadside Claim Assistance & Accident Intake Lifecycle.
Strictly configured with extra="forbid" and from_attributes=True.
"""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


# Allowed photographic evidence extensions (images and PDF reports)
ALLOWED_PHOTO_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp", ".pdf", ".bmp", ".gif")


# ============================================================================
# 1. CLAIM ASSISTANCE IMAGE SCHEMAS
# ============================================================================

class ClaimAssistanceImgCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    img_path: str = Field(..., min_length=1, max_length=500, description="File path or URL of damage/accident photo", alias="ImgPath")

    @field_validator("img_path")
    @classmethod
    def validate_img_path(cls, v: str) -> str:
        clean = v.strip()
        lower = clean.lower()
        if not any(lower.endswith(ext) or ext in lower for ext in ALLOWED_PHOTO_EXTENSIONS):
            raise ValueError(
                f"Invalid image format for '{clean}'. Allowed formats: {', '.join(ALLOWED_PHOTO_EXTENSIONS)}"
            )
        return clean


class ClaimAssistanceImgResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    claim_assistance_img_id: int = Field(validation_alias="ClaimAssistanceImgId")
    claim_assistance_id: int = Field(validation_alias="ClaimAssistanceId")
    img_path: str = Field(validation_alias="ImgPath")
    created_date: datetime = Field(validation_alias="CreatedDate")


# ============================================================================
# 2. CLAIM ASSISTANCE INTAKE SCHEMAS
# ============================================================================

class ClaimAssistanceCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid", populate_by_name=True)

    veh_no: str = Field(..., min_length=1, max_length=50, description="Vehicle Registration Number", alias="VehNo")
    insurance_company_id: int = Field(..., ge=1, description="Underwriting Insurer ID", alias="InsuranceCompanyId")
    date_of_accident: datetime = Field(..., description="Date and time when accident occurred", alias="DateofAccident")
    customer_id: Optional[int] = Field(None, ge=1, description="Policyholder Customer ID", alias="CustomerId")
    accident_time: Optional[str] = Field(None, max_length=50, description="Time of accident (e.g. 14:30)", alias="Accidenttime")
    spot: Optional[str] = Field(None, max_length=255, description="Accident location / Landmark", alias="spot")
    reason: Optional[str] = Field(None, description="Description / Circumstances of accident", alias="Reason")
    driver_name: Optional[str] = Field(None, max_length=150, description="Name of driver at time of accident", alias="DriverName")
    driver_license_no: Optional[str] = Field(None, max_length=100, description="Driver License Number", alias="DriverLicenseNo")
    garage_name: Optional[str] = Field(None, max_length=200, description="Name of repair garage / towing destination", alias="GarageName")
    garage_addr: Optional[str] = Field(None, max_length=500, description="Address of garage", alias="GarageAddr")
    garage_contact: Optional[str] = Field(None, max_length=50, description="Contact phone for garage / surveyor", alias="Garagecontact")
    branch_id: Optional[int] = Field(101, ge=1, description="Operating Branch ID", alias="BranchId")
    agent_id: Optional[int] = Field(0, ge=0, description="Originating POSP Agent ID", alias="AgentId")
    sales_ex_id: Optional[int] = Field(0, ge=0, description="Servicing Sales Executive ID", alias="SalesExId")
    images: Optional[List[str]] = Field(default=[], description="List of image paths uploaded for vehicle damage")

    @field_validator("images")
    @classmethod
    def validate_images(cls, v: Optional[List[str]]) -> List[str]:
        if not v:
            return []
        if len(v) > 20:
            raise ValueError("Maximum 20 damage photos allowed per intimation.")
        cleaned = []
        for path in v:
            clean = path.strip()
            if not clean:
                continue
            lower = clean.lower()
            if not any(lower.endswith(ext) or ext in lower for ext in ALLOWED_PHOTO_EXTENSIONS):
                raise ValueError(
                    f"Invalid image format for '{clean}'. Allowed formats: {', '.join(ALLOWED_PHOTO_EXTENSIONS)}"
                )
            cleaned.append(clean)
        return cleaned


class ClaimAssistanceUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid", populate_by_name=True)

    driver_name: Optional[str] = Field(None, max_length=150, alias="DriverName")
    driver_license_no: Optional[str] = Field(None, max_length=100, alias="DriverLicenseNo")
    garage_name: Optional[str] = Field(None, max_length=200, alias="GarageName")
    garage_addr: Optional[str] = Field(None, max_length=500, alias="GarageAddr")
    garage_contact: Optional[str] = Field(None, max_length=50, alias="Garagecontact")
    spot: Optional[str] = Field(None, max_length=255, alias="spot")
    reason: Optional[str] = Field(None, alias="Reason")
    status: Optional[str] = Field(None, max_length=50, alias="Status")


class ClaimAssistanceAssignClaimNo(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid", populate_by_name=True)

    claim_no: str = Field(..., min_length=1, max_length=100, description="Formal Insurance Claim Number assigned by Insurer", alias="ClaimNo")
    dispatch_sms: bool = Field(default=True, description="Whether to dispatch SMS confirmation to customer")
    dispatch_inbox: bool = Field(default=True, description="Whether to dispatch message to internal inbox")


class ClaimAssistanceReadStatusUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid", populate_by_name=True)

    read_status: int = Field(..., ge=0, le=1, description="0 = Unread, 1 = Read", alias="ReadStatus")


class ClaimAssistanceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    claim_assistance_id: int = Field(validation_alias="ClaimAssistanceId")
    customer_id: Optional[int] = Field(None, validation_alias="CustomerId")
    insurance_company_id: int = Field(validation_alias="InsuranceCompanyId")
    insurance_company_name: Optional[str] = None
    intimation_date: datetime = Field(validation_alias="IntimationDate")
    veh_no: str = Field(validation_alias="VehNo")
    date_of_accident: datetime = Field(validation_alias="DateofAccident")
    accident_time: Optional[str] = Field(None, validation_alias="Accidenttime")
    spot: Optional[str] = Field(None, validation_alias="spot")
    reason: Optional[str] = Field(None, validation_alias="Reason")
    driver_name: Optional[str] = Field(None, validation_alias="DriverName")
    driver_license_no: Optional[str] = Field(None, validation_alias="DriverLicenseNo")
    garage_name: Optional[str] = Field(None, validation_alias="GarageName")
    garage_addr: Optional[str] = Field(None, validation_alias="GarageAddr")
    garage_contact: Optional[str] = Field(None, validation_alias="Garagecontact")
    claim_no: Optional[str] = Field(None, validation_alias="ClaimNo")
    claim_no_update_date: Optional[datetime] = Field(None, validation_alias="ClaimNoUpdateDate")
    claim_no_update_user: Optional[str] = Field(None, validation_alias="ClaimNoUpdateUser")
    status: str = Field(validation_alias="Status")
    read_status: int = Field(validation_alias="ReadStatus")
    isdeleted: int = Field(validation_alias="isdeleted")
    branch_id: Optional[int] = Field(None, validation_alias="BranchId")
    agent_id: Optional[int] = Field(None, validation_alias="AgentId")
    sales_ex_id: Optional[int] = Field(None, validation_alias="SalesExId")
    created_date: datetime = Field(validation_alias="CreatedDate")
    created_user: Optional[str] = Field(None, validation_alias="CreatedUser")
    updated_date: Optional[datetime] = Field(None, validation_alias="UpdatedDate")
    updated_user: Optional[str] = Field(None, validation_alias="UpdatedUser")
    images: List[ClaimAssistanceImgResponse] = []


class ClaimAssistanceSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total_intimations: int
    unread_intimations: int
    read_intimations: int
    pending_claim_assignment: int
    claim_assigned: int
