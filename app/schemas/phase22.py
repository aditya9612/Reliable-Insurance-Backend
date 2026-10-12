"""
Pydantic v2 Schemas for Phase 22 — Sales Executive & Location Head Commission Hierarchy,
Insurer Partner Portals Registry, and App Billing & Field Reimbursement Claims.
Strictly configured with extra="forbid" and from_attributes=True.
"""
from datetime import datetime, date
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


# ============================================================================
# 1. SALES EXECUTIVE COMMISSION SCHEMAS
# ============================================================================

class SalesExecutiveCommissionBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    SalesEx_Id: int = Field(..., description="Employee ID of the Sales Executive")
    InsuranceCompanyId: int = Field(..., description="Insurance Company ID")
    PolicyType: Optional[str] = Field(None, max_length=100, description="Comprehensive, TP, OD, etc.")
    ProductType: Optional[str] = Field(None, max_length=100, description="Product type ID or category")
    VehiTypeId: Optional[int] = Field(None, description="Vehicle Type ID")
    FuelTypeId: Optional[int] = Field(None, description="Fuel Type ID (Petrol, Diesel, CNG, EV)")
    Commission: Decimal = Field(default=Decimal("0.00"), description="Base / TP Commission rate or amount")
    Commission_OD: Decimal = Field(default=Decimal("0.00"), description="OD Commission rate")
    Commission_Net: Decimal = Field(default=Decimal("0.00"), description="Net Premium Commission rate")
    CommissionCalculateOn: Optional[str] = Field("-", max_length=50, description="Calculation base indicator")
    ReferenceType: Optional[str] = Field("Self", max_length=50, description="Reference type (Self / L.Head)")
    FlatRate: Optional[str] = Field(None, max_length=50, description="Flat rate flag or type")
    OD_Discount: Decimal = Field(default=Decimal("0.00"), description="OD discount threshold or slab")
    FranchiseCode: Optional[str] = Field("RA", max_length=50, description="Franchise / Broker code (RA, ST, PB, etc.)")
    ncb: Optional[int] = Field(0, description="No Claim Bonus percentage (0, 20, 25, 35, 45, 50)")
    CCRange: Optional[str] = Field(None, max_length=50, description="Engine CC Range bracket")
    Slab: Optional[str] = Field(None, max_length=50, description="Commission slab category")
    ND: Optional[str] = Field(None, max_length=50, description="Nil Dep addon qualifier")
    MakeId: Optional[int] = Field(0, description="Vehicle Make ID")
    ModelId: Optional[int] = Field(0, description="Vehicle Model ID")
    RtoId: Optional[int] = Field(0, description="RTO Location ID")
    StateId: Optional[int] = Field(0, description="State ID")
    ValidFromDate: date = Field(default_factory=date.today, description="Grid effective start date")
    ValidToDate: Optional[date] = Field(None, description="Grid expiration date")
    IsActive: int = Field(default=1, description="1=Active, 0=Inactive")


class SalesExecutiveCommissionCreate(SalesExecutiveCommissionBase):
    pass


class SalesExecutiveCommissionUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    Commission: Optional[Decimal] = None
    Commission_OD: Optional[Decimal] = None
    Commission_Net: Optional[Decimal] = None
    CommissionCalculateOn: Optional[str] = None
    ReferenceType: Optional[str] = None
    FlatRate: Optional[str] = None
    OD_Discount: Optional[Decimal] = None
    FranchiseCode: Optional[str] = None
    ncb: Optional[int] = None
    CCRange: Optional[str] = None
    Slab: Optional[str] = None
    ND: Optional[str] = None
    ValidFromDate: Optional[date] = None
    ValidToDate: Optional[date] = None
    IsActive: Optional[int] = None


class SalesExecutiveCommissionResponse(SalesExecutiveCommissionBase):
    SalesCommissionId: int
    CreateUser: Optional[int] = None
    CreateDate: datetime
    UpdateUser: Optional[int] = None
    UpdateDate: Optional[datetime] = None


class SalesExecutiveCommissionLookupRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    SalesEx_Id: int
    InsuranceCompanyId: int
    PolicyType: Optional[str] = None
    ProductType: Optional[str] = None
    VehiTypeId: Optional[int] = None
    FuelTypeId: Optional[int] = None
    FranchiseCode: Optional[str] = "RA"
    OD_Discount: Optional[Decimal] = Decimal("0.00")
    ncb: Optional[int] = 0
    CCRange: Optional[str] = None
    MakeId: Optional[int] = 0
    ModelId: Optional[int] = 0
    RtoId: Optional[int] = 0
    Slab: Optional[str] = None
    ND: Optional[str] = None
    TransDate: Optional[date] = None


class SalesExecutiveCommissionLookupResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    matched: bool
    Commission: Decimal
    Commission_OD: Decimal
    Commission_Net: Decimal
    OD_Discount: Decimal
    ReferenceType: str
    FranchiseCode: str
    grid_id: Optional[int] = None
    message: Optional[str] = None


# ============================================================================
# 2. LOCATION HEAD COMMISSION SCHEMAS
# ============================================================================

class LocationHeadCommissionBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    LocationHeadId: int = Field(..., description="Employee ID of the Location Head (Role 38)")
    InsuranceCompanyId: int = Field(..., description="Insurance Company ID")
    PolicyType: Optional[str] = Field(None, max_length=100)
    ProductType: Optional[str] = Field(None, max_length=100)
    VehiTypeId: Optional[int] = Field(None)
    FuelTypeId: Optional[int] = Field(None)
    Commission: Decimal = Field(default=Decimal("0.00"), description="Location Head override base commission")
    Commission_OD: Decimal = Field(default=Decimal("0.00"), description="Location Head OD override commission")
    Commission_Net: Decimal = Field(default=Decimal("0.00"), description="Location Head Net override commission")
    OD_Discount: Decimal = Field(default=Decimal("0.00"))
    FranchiseCode: Optional[str] = Field("RA", max_length=50)
    ReferenceType: Optional[str] = Field("L.Head", max_length=50)
    ValidFromDate: date = Field(default_factory=date.today)
    ValidToDate: Optional[date] = None
    IsActive: int = Field(default=1)


class LocationHeadCommissionCreate(LocationHeadCommissionBase):
    pass


class LocationHeadCommissionUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    Commission: Optional[Decimal] = None
    Commission_OD: Optional[Decimal] = None
    Commission_Net: Optional[Decimal] = None
    OD_Discount: Optional[Decimal] = None
    FranchiseCode: Optional[str] = None
    ReferenceType: Optional[str] = None
    ValidFromDate: Optional[date] = None
    ValidToDate: Optional[date] = None
    IsActive: Optional[int] = None


class LocationHeadCommissionResponse(LocationHeadCommissionBase):
    LocationHeadCommId: int
    CreateUser: Optional[int] = None
    CreateDate: datetime
    UpdateUser: Optional[int] = None
    UpdateDate: Optional[datetime] = None


class LocationHeadCommissionLookupRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    LocationHeadId: int
    InsuranceCompanyId: int
    PolicyType: Optional[str] = None
    ProductType: Optional[str] = None
    VehiTypeId: Optional[int] = None
    FuelTypeId: Optional[int] = None
    FranchiseCode: Optional[str] = "RA"
    OD_Discount: Optional[Decimal] = Decimal("0.00")
    TransDate: Optional[date] = None


class LocationHeadCommissionLookupResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    matched: bool
    Commission: Decimal
    Commission_OD: Decimal
    Commission_Net: Decimal
    OD_Discount: Decimal
    ReferenceType: str
    FranchiseCode: str
    grid_id: Optional[int] = None
    message: Optional[str] = None


# ============================================================================
# 3. LOCATION HEAD <-> SALES EXECUTIVE MAP SCHEMAS
# ============================================================================

class LocationHeadSalesExMapBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    LocationHeadId: int
    SalesEx_Id: int
    IsActive: int = 1


class LocationHeadSalesExMapCreate(LocationHeadSalesExMapBase):
    pass


class LocationHeadSalesExMapResponse(LocationHeadSalesExMapBase):
    MapId: int
    CreatedUser: Optional[int] = None
    CreatedDate: datetime


class LocationHeadAssignmentRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    LocationHeadId: int = Field(..., description="Target Location Head Employee ID")
    SalesEx_Ids: List[int] = Field(..., description="List of Sales Executive Employee IDs to assign")


# ============================================================================
# 4. INSURER PARTNER PORTALS REGISTRY SCHEMAS
# ============================================================================

class InsuranceCompanyPortalBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    InsuranceCompanyId: int = Field(..., description="Insurance Company ID")
    PortalId: Optional[str] = Field(None, max_length=200, description="Portal ID or internal username")
    PersonName: Optional[str] = Field(None, max_length=200, description="Responsible contact / underwriter name")
    BrokerId: Optional[int] = Field(None, description="Broker / Franchise ID")
    PortalUrl: Optional[str] = Field(None, max_length=500, description="URL of the insurer login portal")
    PortalPassword: Optional[str] = Field(None, max_length=255, description="Portal credential password")
    IsActive: int = Field(default=1, description="1=Active, 0=Inactive")


class InsuranceCompanyPortalCreate(InsuranceCompanyPortalBase):
    pass


class InsuranceCompanyPortalUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    InsuranceCompanyId: Optional[int] = None
    PortalId: Optional[str] = None
    PersonName: Optional[str] = None
    BrokerId: Optional[int] = None
    PortalUrl: Optional[str] = None
    PortalPassword: Optional[str] = None
    IsActive: Optional[int] = None


class InsuranceCompanyPortalResponse(InsuranceCompanyPortalBase):
    tbl_Id: int
    CreatedUser: Optional[int] = None
    CreatedDate: datetime
    UpdatedUser: Optional[int] = None
    UpdatedDate: Optional[datetime] = None


# ============================================================================
# 5. APP BILLING & FIELD EXPENSE REIMBURSEMENT SCHEMAS
# ============================================================================

class AppBillingAttachmentCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    FileType: str = Field(..., max_length=20, description="'IMG' or 'PDF'")
    FilePath: str = Field(..., max_length=500, description="Relative storage path or URI")
    FileName: Optional[str] = Field(None, max_length=255)


class AppBillingAttachmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    AttachmentId: int
    BillingId: int
    FileType: str
    FilePath: str
    FileName: Optional[str] = None
    UploadedDate: datetime


class AppBillingDetailsBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    SalesExId: int = Field(..., description="Sales Executive submitting the reimbursement claim")
    FromDate: date = Field(..., description="Claim start date")
    ToDate: date = Field(..., description="Claim end date")
    Remark: Optional[str] = Field(None, description="Detailed explanation of travel/expense")
    BillingAmount: Decimal = Field(default=Decimal("0.00"), description="Claim amount in INR")
    ReimbursementTypeId: Optional[int] = Field(None, description="Type of expense (Fuel, Travel, Lodging, etc.)")
    Destination: Optional[str] = Field(None, max_length=255, description="Travel destination / territory")


class AppBillingDetailsCreate(AppBillingDetailsBase):
    attachments: Optional[List[AppBillingAttachmentCreate]] = Field(
        default=None, description="Optional photo and PDF receipt attachments"
    )


class AppBillingDetailsUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    FromDate: Optional[date] = None
    ToDate: Optional[date] = None
    Remark: Optional[str] = None
    BillingAmount: Optional[Decimal] = None
    ReimbursementTypeId: Optional[int] = None
    Destination: Optional[str] = None


class AppBillingStatusUpdateRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    Status: str = Field(..., max_length=50, description="New status: 'APPROVED', 'REJECTED', 'PROCESSED'")
    Remark: Optional[str] = Field(None, description="Approval or rejection notes")


class AppBillingDetailsResponse(AppBillingDetailsBase):
    BillingId: int
    Status: str
    CreatedDate: datetime
    ProcessedDate: Optional[datetime] = None
    ProcessedBy: Optional[int] = None
    attachments: List[AppBillingAttachmentResponse] = []
