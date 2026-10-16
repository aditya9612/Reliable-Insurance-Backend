"""
Pydantic v2 Schemas for Phase 20 Features — Batch 1.
Covers:
1. Bulletins & Circulars (F-20-001)
2. Mobile Customer Helpdesk & Support Chat (F-20-002)
3. Web Notification Alerts (F-20-003)
4. Partner Loyalty & Reward Points (F-20-004)
"""
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field


# ============================================================================
# 1. CIRCULARS & BULLETINS SCHEMAS (F-20-001)
# ============================================================================

class CircularCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    subject: str = Field(..., min_length=1, max_length=500, description="Circular subject")
    circulardate: Optional[date] = Field(default_factory=date.today, description="Publication date")
    pdfpath: Optional[str] = Field(None, max_length=1000, description="PDF attachment path")
    is_active: Optional[int] = Field(1, ge=0, le=1, description="Active status (1=active, 0=inactive)")


class CircularUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    subject: Optional[str] = Field(None, min_length=1, max_length=500)
    circulardate: Optional[date] = None
    pdfpath: Optional[str] = Field(None, max_length=1000)
    is_active: Optional[int] = Field(None, ge=0, le=1)


class CircularResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    circularid: int
    circulardate: date
    subject: str
    pdfpath: Optional[str] = None
    is_active: int
    created_by: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


# ============================================================================
# 2. CUSTOMER HELPDESK & CHATBOARD SCHEMAS (F-20-002)
# ============================================================================

class CustomerHelpCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    CustomerId: int = Field(..., ge=1, description="Customer ID")
    HelpId: Optional[int] = Field(None, ge=1, description="Help category ID")
    Subject: str = Field(..., min_length=1, max_length=255, description="Issue subject")
    Message: Optional[str] = Field(None, description="Detailed problem description")
    RegistrationNo: Optional[str] = Field(None, max_length=100, description="Vehicle Registration No")
    PolicyNo: Optional[str] = Field(None, max_length=100, description="Existing Policy No")


class CustomerHelpResolve(BaseModel):
    model_config = ConfigDict(extra="forbid")
    Status: str = Field("RESOLVED", description="Resolution status (RESOLVED, CLOSED)")
    ResolutionRemark: str = Field(..., min_length=1, max_length=1000, description="Resolution notes")


class CustomerHelpResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    CustHelpId: int
    CustomerId: int
    HelpId: Optional[int] = None
    Subject: str
    Message: Optional[str] = None
    RegistrationNo: Optional[str] = None
    PolicyNo: Optional[str] = None
    Status: str
    CustDate: datetime
    ResolvedBy: Optional[int] = None
    ResolvedDate: Optional[datetime] = None
    ResolutionRemark: Optional[str] = None


class ChatBoardMessageCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    CustHelpId: Optional[int] = Field(None, ge=1, description="Associated Customer Help ticket ID")
    ChatText: str = Field(..., min_length=1, description="Chat message text")
    RegistrationNo: Optional[str] = Field(None, max_length=100, description="Vehicle Reg No")
    ReferenceAgentId: Optional[int] = Field(None, ge=1, description="Associated Agent ID")
    CoordinatorId: Optional[int] = Field(None, ge=1, description="Assigned Coordinator ID")
    Remark: Optional[str] = Field(None, max_length=500, description="Internal remark")
    AttachmentPath: Optional[str] = Field(None, max_length=1000, description="Attachment file path")


class ChatBoardReplyCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    Reply: str = Field(..., min_length=1, description="Coordinator/Staff response")
    Remark: Optional[str] = Field(None, max_length=500, description="Staff internal note")


class ChatBoardMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    ChatId: int
    CustHelpId: Optional[int] = None
    UserRoleId: Optional[int] = None
    ReferenceAgentId: Optional[int] = None
    CoordinatorId: Optional[int] = None
    RegistrationNo: Optional[str] = None
    ChatText: str
    ChatByUser: str
    SenderUserId: Optional[int] = None
    Reply: Optional[str] = None
    Remark: Optional[str] = None
    AttachmentPath: Optional[str] = None
    IsRead: int
    CreatedDate: datetime


# ============================================================================
# 3. WEB NOTIFICATION ALERTS SCHEMAS (F-20-003)
# ============================================================================

class WebNotificationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    NotMessage: str = Field(..., min_length=1, max_length=1000, description="Notification message text")
    TargetRole: Optional[str] = Field("ALL", max_length=50, description="Role target (ALL, OPERATOR, AGENT, ADMIN)")
    BranchId: Optional[int] = Field(None, ge=1, description="Specific branch filter")
    Severity: Optional[str] = Field("INFO", max_length=20, description="Severity: INFO, WARNING, URGENT")
    ExpiryDate: Optional[datetime] = Field(None, description="Expiry timestamp")


class WebNotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    NotId: int
    NotMessage: str
    TargetRole: Optional[str] = None
    BranchId: Optional[int] = None
    Severity: str
    IsActive: int
    CreatedBy: Optional[int] = None
    CreatedDate: datetime
    ExpiryDate: Optional[datetime] = None


# ============================================================================
# 4. PARTNER LOYALTY & REWARD POINTS SCHEMAS (F-20-004)
# ============================================================================

class RewardPointCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    PartnerType: str = Field("AGENT", max_length=50, description="Partner type: AGENT, FRANCHISE, EXECUTIVE, CUSTOMER")
    PartnerId: int = Field(..., ge=1, description="Partner identity ID")
    RewardPointGet: Decimal = Field(Decimal("0.00"), ge=0, description="Points earned")
    RewardPointUtilizes: Decimal = Field(Decimal("0.00"), ge=0, description="Points redeemed")
    RefCustId: Optional[int] = Field(None, ge=1, description="Referred customer ID")
    PolicyId: Optional[int] = Field(None, ge=1, description="Associated transaction ID")
    Remarks: Optional[str] = Field(None, max_length=500, description="Audit remarks")


class RewardPointResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    RewardPointId: int
    PartnerType: str
    PartnerId: int
    RefCustId: Optional[int] = None
    PolicyId: Optional[int] = None
    RewardDate: date
    RewardPointGet: Decimal
    RewardPointUtilizes: Decimal
    PointBalance: Decimal
    Remarks: Optional[str] = None
    CreatedDate: datetime


class RewardPointSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    PartnerType: str
    PartnerId: int
    TotalEarned: Decimal
    TotalUtilized: Decimal
    CurrentBalance: Decimal
    TransactionsCount: int


# ============================================================================
# 5. GEOGRAPHIC CLUSTERS & COMMISSION GRIDS SCHEMAS (F-20-005)
# ============================================================================

class ClusterMasterCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ClusterName: str = Field(..., min_length=1, max_length=255, description="Cluster name")
    InsuranceCompanyId: int = Field(..., ge=1, description="Insurance company ID")
    StateId: int = Field(..., ge=1, description="State ID")
    RtoIds: Optional[List[int]] = Field(default_factory=list, description="Initial list of RTO IDs to associate")


class ClusterDetailCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ClusterMId: int = Field(..., ge=1, description="Cluster Master ID")
    InsuranceCompanyId: int = Field(..., ge=1, description="Insurance company ID")
    RtoId: int = Field(..., ge=1, description="RTO ID")


class ClusterDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    ClusterDId: int
    ClusterMId: int
    InsuranceCompanyId: int
    RtoId: int
    CreateUser: Optional[int] = None
    CreateDate: datetime


class ClusterMasterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    ClusterMId: int
    InsuranceCompanyId: int
    ClusterName: str
    StateId: int
    CreateUser: Optional[int] = None
    CreateDate: datetime
    isdeleted: int
    details: Optional[List[ClusterDetailResponse]] = None


class ClusterWiseBrokerGridCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ClusterMId: int = Field(..., ge=1, description="Cluster Master ID")
    BrokerId: int = Field(..., ge=1, description="Broker ID")
    InsuranceCompanyId: int = Field(..., ge=1, description="Insurance Company ID")
    Veh_Type_ID: int = Field(..., ge=1, description="Vehicle Type ID")
    StateId: int = Field(..., ge=1, description="State ID")
    GridValue: Decimal = Field(Decimal("0.00"), ge=0, description="Broker commission rate percentage")
    ODDiscount: Decimal = Field(Decimal("0.00"), ge=0, description="Applicable OD discount percentage")
    ValidFrom: Optional[date] = Field(default_factory=date.today, description="Grid validity start date")
    CalOn: Optional[str] = Field("OD", max_length=50, description="Calculation basis (OD, NET)")
    ReferenceType: Optional[str] = Field(None, max_length=50, description="Reference category")
    FuelTypeId: Optional[int] = Field(None, ge=1)
    ProductTypeId: Optional[int] = Field(None, ge=1)
    PolicyTypeId: Optional[int] = Field(None, ge=1)


class ClusterWiseBrokerGridResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    GridId: int
    GridValue: Decimal
    CalOn: Optional[str] = None
    ODDiscount: Decimal
    ValidFrom: date
    ReferenceType: Optional[str] = None
    BrokerId: int
    InsuranceCompanyId: int
    Veh_Type_ID: int
    StateId: int
    FuelTypeId: Optional[int] = None
    ProductTypeId: Optional[int] = None
    PolicyTypeId: Optional[int] = None
    ClusterMId: int
    CreatedUser: Optional[int] = None
    CreatedDate: datetime
    UpdatedUser: Optional[int] = None
    UpdatedDate: Optional[datetime] = None


class ClusterWiseAgentGridCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ClusterMId: int = Field(..., ge=1, description="Cluster Master ID")
    AgentId: int = Field(..., ge=1, description="Agent ID")
    InsuranceCompanyId: int = Field(..., ge=1, description="Insurance Company ID")
    Veh_Type_ID: int = Field(..., ge=1, description="Vehicle Type ID")
    StateId: int = Field(..., ge=1, description="State ID")
    GridValue: Decimal = Field(Decimal("0.00"), ge=0, description="Agent commission rate percentage")
    ODDiscount: Decimal = Field(Decimal("0.00"), ge=0, description="Applicable OD discount percentage")
    ValidFrom: Optional[date] = Field(default_factory=date.today, description="Grid validity start date")
    CalOn: Optional[str] = Field("OD", max_length=50, description="Calculation basis (OD, NET)")
    ReferenceType: Optional[str] = Field(None, max_length=50, description="Reference category")
    BrokerId: Optional[int] = Field(None, ge=1)
    FuelTypeId: Optional[int] = Field(None, ge=1)
    ProductTypeId: Optional[int] = Field(None, ge=1)
    PolicyTypeId: Optional[int] = Field(None, ge=1)


class ClusterWiseAgentGridResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    GridId: int
    GridValue: Decimal
    CalOn: Optional[str] = None
    ODDiscount: Decimal
    ValidFrom: date
    ReferenceType: Optional[str] = None
    AgentId: int
    BrokerId: Optional[int] = None
    InsuranceCompanyId: int
    Veh_Type_ID: int
    StateId: int
    FuelTypeId: Optional[int] = None
    ProductTypeId: Optional[int] = None
    PolicyTypeId: Optional[int] = None
    ClusterMId: int
    CreatedUser: Optional[int] = None
    CreatedDate: datetime
    UpdatedUser: Optional[int] = None
    UpdatedDate: Optional[datetime] = None


# ============================================================================
# 6. DECLINE MODELS & RESTRICTIONS GRID SCHEMAS (F-20-006)
# ============================================================================

class GridDeclineCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    InsuranceCompanyId: int = Field(..., ge=1, description="Insurance Company ID")
    MakeId: int = Field(..., ge=1, description="Vehicle Make ID")
    PolicyTypeId: int = Field(..., ge=1, description="Policy Type ID")
    ProductTypeId: int = Field(..., ge=1, description="Product Type ID")
    ModelId: Optional[int] = Field(None, ge=1, description="Vehicle Model ID (optional if make-level decline)")
    RtoId: Optional[int] = Field(None, ge=1, description="RTO ID filter")
    FuelTypeId: Optional[int] = Field(None, ge=1, description="Fuel Type ID filter")
    Guide_line: Optional[str] = Field(None, max_length=1000, description="Decline guideline reason")
    active: Optional[int] = Field(1, ge=0, le=1)


class GridDeclineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    DeclineId: int
    DeclineDate: datetime
    InsuranceCompanyId: int
    MakeId: int
    PolicyTypeId: int
    ModelId: Optional[int] = None
    RtoId: Optional[int] = None
    ProductTypeId: int
    FuelTypeId: Optional[int] = None
    Guide_line: Optional[str] = None
    active: int
    CreatedUser: Optional[int] = None


class DeclineModelDetailCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    DeclineId: Optional[int] = Field(None, ge=1, description="Parent Decline Master ID")
    MakeId: int = Field(..., ge=1, description="Make ID")
    ModelId: int = Field(..., ge=1, description="Model ID")
    InsuranceCompanyId: int = Field(..., ge=1, description="Insurance Company ID")
    PolicyTypeId: int = Field(..., ge=1, description="Policy Type ID")
    ProductTypeId: int = Field(..., ge=1, description="Product Type ID")
    RtoId: Optional[int] = Field(None, ge=1, description="RTO ID filter")
    FuelTypeId: Optional[int] = Field(None, ge=1, description="Fuel Type ID filter")
    Remark: Optional[str] = Field(None, max_length=500, description="Specific restriction remark")


class DeclineModelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    Id: int
    DeclineId: Optional[int] = None
    MakeId: int
    ModelId: int
    InsuranceCompanyId: int
    PolicyTypeId: int
    ProductTypeId: int
    RtoId: Optional[int] = None
    FuelTypeId: Optional[int] = None
    Remark: Optional[str] = None
    CreatedDate: datetime
    CreatedBy: Optional[int] = None


class UnderwritingDeclineCheckRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    InsuranceCompanyId: int = Field(..., ge=1)
    MakeId: int = Field(..., ge=1)
    ModelId: int = Field(..., ge=1)
    PolicyTypeId: int = Field(..., ge=1)
    ProductTypeId: int = Field(..., ge=1)
    RtoId: Optional[int] = Field(None, ge=1)
    FuelTypeId: Optional[int] = Field(None, ge=1)


class UnderwritingDeclineCheckResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    is_declined: bool
    reason: Optional[str] = None
    matching_rule_count: int
