"""
Pydantic Schemas for Phase 15B — IDV Requests, Health Members, Bulk Policy MIS & Operational Tasks.
"""
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


# ============================================================================
# IDV REQUEST SCHEMAS
# ============================================================================

class IDVRequestCreate(BaseModel):
    InsuranceCompanyId: Optional[int] = None
    VehicleTypeId: Optional[int] = None
    PolicyTypeId: Optional[str] = None
    VehicleMake: Optional[str] = None
    VehicleModel: Optional[str] = None
    RegistrationNo: Optional[str] = None
    Passyear: Optional[str] = None
    RequestedIDV: Decimal = Field(..., gt=0)
    SalesExId: Optional[int] = None
    Note: Optional[str] = None


class IDVRequestApprove(BaseModel):
    ApprovedIDV: Decimal = Field(..., gt=0)
    ApprovedRemark: Optional[str] = None


class IDVRequestReject(BaseModel):
    ApprovedRemark: str = Field(..., min_length=3, description="Mandatory reason for rejection")


class IDVRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    IDVRequestId: int
    RequestDate: datetime
    InsuranceCompanyId: Optional[int] = None
    VehicleTypeId: Optional[int] = None
    PolicyTypeId: Optional[str] = None
    VehicleMake: Optional[str] = None
    VehicleModel: Optional[str] = None
    RegistrationNo: Optional[str] = None
    Passyear: Optional[str] = None
    RequestedIDV: Decimal
    ApprovedIDV: Optional[Decimal] = None
    SalesExId: Optional[int] = None
    RequestedBy: Optional[str] = None
    ApprovedBy: Optional[str] = None
    Status: str
    Note: Optional[str] = None
    ApprovedRemark: Optional[str] = None
    CreateDate: datetime
    UpdateDate: Optional[datetime] = None
    is_active: bool
    isdeleted: str


# ============================================================================
# HEALTH MEMBER SCHEMAS
# ============================================================================

class HealthMemberCreate(BaseModel):
    TransanctionId: Optional[int] = None
    CustomerId: Optional[int] = None
    MemberName: str = Field(..., min_length=2)
    Relationship: str = Field(..., description="SELF, SPOUSE, SON, DAUGHTER, FATHER, MOTHER")
    Gender: str = Field(..., description="MALE, FEMALE, OTHER")
    DOB: Optional[date] = None
    Age: int = Field(..., ge=0, le=120)
    SumInsured: Decimal = Field(..., gt=0)
    PreExistingDisease: Optional[str] = None
    NomineeName: Optional[str] = None


class HealthMemberUpdate(BaseModel):
    MemberName: Optional[str] = None
    Relationship: Optional[str] = None
    Gender: Optional[str] = None
    DOB: Optional[date] = None
    Age: Optional[int] = None
    SumInsured: Optional[Decimal] = None
    PreExistingDisease: Optional[str] = None
    NomineeName: Optional[str] = None
    Status: Optional[str] = None


class HealthMemberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    MemberId: int
    TransanctionId: Optional[int] = None
    CustomerId: Optional[int] = None
    MemberName: str
    Relationship: str
    Gender: str
    DOB: Optional[date] = None
    Age: int
    SumInsured: Decimal
    PreExistingDisease: Optional[str] = None
    NomineeName: Optional[str] = None
    Status: str
    CreateDate: datetime
    CreateUser: Optional[str] = None
    UpdateDate: Optional[datetime] = None
    UpdateUser: Optional[str] = None
    is_active: bool
    isdeleted: str


# ============================================================================
# BULK POLICY MIS SCHEMAS
# ============================================================================

class ImportPolicyMISRow(BaseModel):
    DateOfInsurance: Optional[str] = None
    BrokerName: Optional[str] = None
    ClientName: Optional[str] = None
    VehicleType: Optional[str] = None
    VehicleNumber: Optional[str] = None
    PolicyNumber: Optional[str] = None
    Segments: Optional[str] = None
    InsuranceCompany: Optional[str] = None
    IssuingID: Optional[str] = None
    InceptionDate: Optional[str] = None
    ExpiryDate: Optional[str] = None
    GrossAmount: Optional[Decimal] = None
    NetAmount: Optional[Decimal] = None
    ODPremium: Optional[Decimal] = None
    TPPremium: Optional[Decimal] = None
    BrokerReceivedPct: Optional[Decimal] = None
    BrokerPayout: Optional[Decimal] = None
    PolicyType: Optional[str] = None
    FuelType: Optional[str] = None
    MfgDate: Optional[str] = None
    GVW: Optional[str] = None
    ProductType: Optional[str] = None
    FinancialYear: Optional[str] = None


class ImportPolicyMISResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    Id: int
    DateOfInsurance: Optional[str] = None
    BrokerName: Optional[str] = None
    ClientName: Optional[str] = None
    VehicleType: Optional[str] = None
    VehicleNumber: Optional[str] = None
    PolicyNumber: Optional[str] = None
    Segments: Optional[str] = None
    InsuranceCompany: Optional[str] = None
    IssuingID: Optional[str] = None
    InceptionDate: Optional[str] = None
    ExpiryDate: Optional[str] = None
    GrossAmount: Optional[Decimal] = None
    NetAmount: Optional[Decimal] = None
    ODPremium: Optional[Decimal] = None
    TPPremium: Optional[Decimal] = None
    BrokerReceivedPct: Optional[Decimal] = None
    BrokerPayout: Optional[Decimal] = None
    PolicyType: Optional[str] = None
    FuelType: Optional[str] = None
    MfgDate: Optional[str] = None
    GVW: Optional[str] = None
    ProductType: Optional[str] = None
    CreatedBy: Optional[str] = None
    CreatedDate: datetime
    IsProcess: int
    Remark: Optional[str] = None
    FinancialYear: Optional[str] = None
    BatchId: Optional[str] = None
    is_active: bool


class ImportBatchSummary(BaseModel):
    batch_id: str
    total_records: int
    processed_records: int
    pending_records: int
    total_gross_amount: Decimal
    total_net_amount: Decimal
    created_at: datetime
    created_by: str


class ProcessBatchRequest(BaseModel):
    batch_id: str
    mark_as_processed: bool = True
    remark: Optional[str] = None


# ============================================================================
# OPERATIONAL BATCH TASKS SCHEMAS
# ============================================================================

class OverdueChequeLockResult(BaseModel):
    executed_at: datetime
    threshold_days: int
    overdue_cheques_found: int
    accounts_audited: int
    users_locked: List[Dict[str, Any]]
    total_overdue_amount: Decimal


class BirthdayCandidate(BaseModel):
    entity_type: str  # CUSTOMER, EMPLOYEE, AGENT
    entity_id: int
    name: str
    mobile: Optional[str] = None
    email: Optional[str] = None
    date_of_birth: Optional[date] = None


class BirthdayGreetingDispatchResult(BaseModel):
    executed_at: datetime
    candidates_count: int
    messages_dispatched: int
    sms_logs_created: int
    push_logs_created: int
    details: List[Dict[str, Any]]


class OperationalCleanupResult(BaseModel):
    executed_at: datetime
    task_name: str
    items_inspected: int
    items_cleaned: int
    details: Optional[str] = None
