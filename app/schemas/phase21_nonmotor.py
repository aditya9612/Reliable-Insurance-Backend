"""
Pydantic v2 Schemas for Phase 21 — Non-Motor Commercial Insurance Lines of Business & Operations.
Covers:
1. Product Classes & Products (tbl_nonmotorclass, tbl_nonmotorproduct)
2. Business Types & Required Document Types (tbl_nonmotorbusinesstype, tbl_nonmotordocumenttype)
3. Endorsement Types & Sub-Types (tbl_nonmotorendorsmenttype, tbl_nonmotorendorsmentsubtype)
4. Insurer Insurance Types & Sub-Types (tbl_nonmotorinsurancetype, tbl_nonmotorinsurancesubtype, tbl_nonmotortypeofinsurancesubtype)
5. Non-Motor Commission Grids & Calculations (tbl_nonmotorcommission)
6. Non-Motor Policy Booking & Proposal Transactions (tbl_nonmotortransaction)
"""
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field


# ============================================================================
# 1. NON-MOTOR PRODUCT CLASS & PRODUCT SCHEMAS
# ============================================================================

class NonMotorClassCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    Class: str = Field(..., min_length=1, max_length=255, description="Product class name (e.g. Fire, Marine Cargo, Engineering)")
    IsActive: Optional[int] = Field(1, ge=0, le=1)


class NonMotorClassUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    Class: Optional[str] = Field(None, min_length=1, max_length=255)
    IsActive: Optional[int] = Field(None, ge=0, le=1)


class NonMotorClassResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    ClassId: int
    Class: str
    IsActive: int
    CreatedDate: datetime
    CreatedBy: Optional[str] = None
    UpdatedDate: Optional[datetime] = None
    UpdatedBy: Optional[str] = None


class NonMotorProductCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ClassId: int = Field(..., ge=1, description="Associated Class ID")
    ProductType: str = Field(..., min_length=1, max_length=255, description="Product name/type")
    ProductCode: Optional[str] = Field(None, max_length=100, description="Product code identifier")
    IsActive: Optional[int] = Field(1, ge=0, le=1)


class NonMotorProductUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    ClassId: Optional[int] = Field(None, ge=1)
    ProductType: Optional[str] = Field(None, min_length=1, max_length=255)
    ProductCode: Optional[str] = Field(None, max_length=100)
    IsActive: Optional[int] = Field(None, ge=0, le=1)


class NonMotorProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    NonMotorProductId: int
    ClassId: int
    ProductType: str
    ProductCode: Optional[str] = None
    IsActive: int
    CreatedDate: datetime
    CreatedBy: Optional[str] = None
    UpdatedDate: Optional[datetime] = None
    UpdatedBy: Optional[str] = None


# ============================================================================
# 2. NON-MOTOR BUSINESS TYPE & DOCUMENT TYPE SCHEMAS
# ============================================================================

class NonMotorBusinessTypeCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    BusinessType: str = Field(..., min_length=1, max_length=255, description="Business type (e.g. New, Renewal, Roll Over, Endorsement)")
    IsActive: Optional[int] = Field(1, ge=0, le=1)


class NonMotorBusinessTypeUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    BusinessType: Optional[str] = Field(None, min_length=1, max_length=255)
    IsActive: Optional[int] = Field(None, ge=0, le=1)


class NonMotorBusinessTypeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    NonBusinessId: int
    BusinessType: str
    IsActive: int
    CreatedDate: datetime
    CreatedBy: Optional[str] = None
    UpdatedDate: Optional[datetime] = None
    UpdatedBy: Optional[str] = None


class NonMotorDocumentTypeCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    DocumentType: str = Field(..., min_length=1, max_length=255, description="Required document type description")
    IsActive: Optional[int] = Field(1, ge=0, le=1)


class NonMotorDocumentTypeUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    DocumentType: Optional[str] = Field(None, min_length=1, max_length=255)
    IsActive: Optional[int] = Field(None, ge=0, le=1)


class NonMotorDocumentTypeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    NonDocumentTypeId: int
    DocumentType: str
    IsActive: int
    CreatedDate: datetime
    CreatedBy: Optional[str] = None
    UpdatedDate: Optional[datetime] = None
    UpdatedBy: Optional[str] = None


# ============================================================================
# 3. NON-MOTOR ENDORSEMENT HIERARCHY SCHEMAS
# ============================================================================

class NonMotorEndorsementTypeCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    EndorsementType: str = Field(..., min_length=1, max_length=255, description="Endorsement category (e.g. Financial, Non-Financial)")
    IsActive: Optional[int] = Field(1, ge=0, le=1)


class NonMotorEndorsementTypeUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    EndorsementType: Optional[str] = Field(None, min_length=1, max_length=255)
    IsActive: Optional[int] = Field(None, ge=0, le=1)


class NonMotorEndorsementTypeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    NonEndorsementId: int
    EndorsementType: str
    IsActive: int
    CreatedDate: datetime
    CreatedBy: Optional[str] = None
    UpdatedDate: Optional[datetime] = None
    UpdatedBy: Optional[str] = None


class NonMotorEndorsementSubTypeCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    NonEndorsementId: int = Field(..., ge=1, description="Associated Endorsement Type ID")
    EndorsementSubType: str = Field(..., min_length=1, max_length=255, description="Specific endorsement alteration")
    IsActive: Optional[int] = Field(1, ge=0, le=1)


class NonMotorEndorsementSubTypeUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    NonEndorsementId: Optional[int] = Field(None, ge=1)
    EndorsementSubType: Optional[str] = Field(None, min_length=1, max_length=255)
    IsActive: Optional[int] = Field(None, ge=0, le=1)


class NonMotorEndorsementSubTypeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    NonEndorsesubId: int
    NonEndorsementId: int
    EndorsementSubType: str
    IsActive: int
    CreatedDate: datetime
    CreatedBy: Optional[str] = None
    UpdatedDate: Optional[datetime] = None
    UpdatedBy: Optional[str] = None


# ============================================================================
# 4. NON-MOTOR INSURER HIERARCHY SCHEMAS
# ============================================================================

class NonMotorInsuranceTypeCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    InsuranceType: str = Field(..., min_length=1, max_length=255)
    InsuranceCompanyId: int = Field(..., ge=1)
    Flag: Optional[str] = Field(None, max_length=50)


class NonMotorInsuranceTypeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    InsuranceTypeId: int
    InsuranceType: str
    InsuranceCompanyId: int
    IsDeleted: int
    Flag: Optional[str] = None
    CreatedDate: datetime
    CreatedBy: Optional[str] = None


class NonMotorInsuranceSubTypeCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    InsuranceSubType: str = Field(..., min_length=1, max_length=255)
    InsuranceTypeId: int = Field(..., ge=1)
    Flag: Optional[str] = Field(None, max_length=50)


class NonMotorInsuranceSubTypeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    InsuranceSubTypeId: int
    InsuranceSubType: str
    InsuranceTypeId: int
    IsDeleted: int
    Flag: Optional[str] = None
    CreatedDate: datetime
    CreatedBy: Optional[str] = None


class NonMotorTypeOfInsuranceSubTypeCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    TypeOfSubType: str = Field(..., min_length=1, max_length=255)
    InsuranceTypeId: int = Field(..., ge=1)
    InsuranceSubTypeId: int = Field(..., ge=1)
    Flag: Optional[str] = Field(None, max_length=50)


class NonMotorTypeOfInsuranceSubTypeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    TypeSubTypeId: int
    TypeOfSubType: str
    InsuranceTypeId: int
    InsuranceSubTypeId: int
    IsDeleted: int
    Flag: Optional[str] = None
    CreatedDate: datetime
    CreatedBy: Optional[str] = None


# ============================================================================
# 5. NON-MOTOR COMMISSION GRID & CALCULATION SCHEMAS
# ============================================================================

class NonMotorCommissionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    InsuranceCompanyId: int = Field(..., ge=1)
    InsuranceTypeId: int = Field(..., ge=1)
    InsuranceSubTypeId: Optional[int] = Field(0, ge=0)
    TypeSubTypeId: Optional[int] = Field(0, ge=0)
    ReferanceId: int = Field(..., ge=1, description="AgentId, BrokerId, FranchiseId")
    ReferenceType: str = Field(..., min_length=1, max_length=50, description="Agent, Broker, Franchise, Self, IE, Franchise Agent")
    Commission: Decimal = Field(..., ge=0, le=100, description="Commission percentage rate")
    CommissionCalculateOn: Optional[str] = Field("NetPremium", max_length=100)
    ValidFromDate: Optional[date] = Field(default_factory=date.today)
    Extra1: Optional[str] = Field(None, max_length=255)
    Extra2: Optional[str] = Field(None, max_length=255)
    IsActive: Optional[int] = Field(1, ge=0, le=1)


class NonMotorCommissionUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    Commission: Optional[Decimal] = Field(None, ge=0, le=100)
    CommissionCalculateOn: Optional[str] = Field(None, max_length=100)
    ValidFromDate: Optional[date] = None
    Extra1: Optional[str] = Field(None, max_length=255)
    Extra2: Optional[str] = Field(None, max_length=255)
    IsActive: Optional[int] = Field(None, ge=0, le=1)


class NonMotorCommissionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    NonMotorCommId: int
    InsuranceCompanyId: int
    InsuranceTypeId: int
    InsuranceSubTypeId: int
    TypeSubTypeId: int
    ReferanceId: int
    ReferenceType: str
    Commission: Decimal
    CommissionCalculateOn: str
    ValidFromDate: date
    Extra1: Optional[str] = None
    Extra2: Optional[str] = None
    IsActive: int
    CreateDate: datetime
    CreateUser: Optional[int] = None
    UpdateDate: Optional[datetime] = None
    UpdateUser: Optional[int] = None


class NonMotorCommissionCalculationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    NetPremium: Decimal = Field(..., ge=0, description="Net premium amount")
    InsuranceCompanyId: int = Field(..., ge=1)
    InsuranceTypeId: int = Field(..., ge=1)
    InsuranceSubTypeId: Optional[int] = Field(0, ge=0)
    ReferanceId: int = Field(..., ge=1, description="Agent / Broker / Franchise ID")
    ReferenceType: str = Field(..., description="Agent, Broker, Franchise, Self, IE")
    TdsRate: Optional[Decimal] = Field(Decimal("5.00"), ge=0, le=50, description="TDS rate % (default 5.0%)")


class NonMotorCommissionCalculationResponse(BaseModel):
    CommissionRate: Decimal
    NetPremium: Decimal
    GrossCommission: Decimal
    TdsRate: Decimal
    TdsAmount: Decimal
    NetCommission: Decimal
    ReferenceType: str
    ReferanceId: int


# ============================================================================
# 6. NON-MOTOR POLICY TRANSACTION SCHEMAS
# ============================================================================

class NonMotorTransactionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    BranchId: int = Field(..., ge=1)
    CustomerId: int = Field(..., ge=1)
    InsuranceCompanyId: int = Field(..., ge=1)
    ClassId: int = Field(..., ge=1)
    ProductTypeId: int = Field(..., ge=1)
    BusinessTypeId: int = Field(..., ge=1)
    AgentId: int = Field(..., ge=1)
    SalesEx_id: Optional[int] = Field(None, ge=1)
    CoverNote: Optional[str] = Field(None, max_length=100)
    PreviousPolicyNo: Optional[str] = Field(None, max_length=100)
    PolicyNo: Optional[str] = Field(None, max_length=100)
    CnIssueDate: Optional[datetime] = None
    NonDocumentTypeId: Optional[int] = Field(None, ge=1)
    NonEndorsementId: Optional[int] = Field(None, ge=1)
    NonEndorsesubId: Optional[int] = Field(None, ge=1)
    EndorsementReason: Optional[str] = Field(None, max_length=500)
    RiskStartdate: Optional[datetime] = None
    ExpiryDate: Optional[datetime] = None
    SumInsured: Decimal = Field(Decimal("0.00"), ge=0)
    NetPermium: Decimal = Field(..., ge=0, description="Net premium amount")
    ProPosalAmt: Optional[Decimal] = Field(Decimal("0.00"), ge=0)
    Remark: Optional[str] = None
    ReferenceType: Optional[str] = Field("Agent", max_length=50)
    ReferenceBy: Optional[str] = Field(None, max_length=100)
    ReferenceRole: Optional[str] = Field(None, max_length=100)
    PersonName: Optional[str] = Field(None, max_length=200)
    tat: Optional[str] = Field(None, max_length=50)
    AgentComm: Optional[Decimal] = Field(Decimal("0.00"), ge=0, le=100)
    TdsRate: Optional[Decimal] = Field(Decimal("5.00"), ge=0, le=50)


class NonMotorTransactionUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    PolicyNo: Optional[str] = Field(None, max_length=100)
    CnIssueDate: Optional[datetime] = None
    CoverNote: Optional[str] = Field(None, max_length=100)
    Remark: Optional[str] = None
    TStatus: Optional[str] = Field(None, max_length=50)


class NonMotorTransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    NonMotorTransactionId: int
    InwardNo: str
    TransDate: datetime
    BranchId: int
    CustomerId: int
    InsuranceCompanyId: int
    CoverNote: Optional[str] = None
    PreviousPolicyNo: Optional[str] = None
    PolicyNo: Optional[str] = None
    CnIssueDate: Optional[datetime] = None
    ClassId: int
    ProductTypeId: int
    BusinessTypeId: int
    NonDocumentTypeId: Optional[int] = None
    NonEndorsementId: Optional[int] = None
    NonEndorsesubId: Optional[int] = None
    EndorsementReason: Optional[str] = None
    AgentId: int
    SalesEx_id: Optional[int] = None
    RiskStartdate: Optional[datetime] = None
    ExpiryDate: Optional[datetime] = None
    SumInsured: Decimal
    NetPermium: Decimal
    ProPosalAmt: Decimal
    Remark: Optional[str] = None
    ReferenceType: Optional[str] = None
    ReferenceBy: Optional[str] = None
    ReferenceRole: Optional[str] = None
    PersonName: Optional[str] = None
    tat: Optional[str] = None
    AgentComm: Decimal
    AgentCommAmt: Decimal
    TdsAmt: Decimal
    NetCommission: Decimal
    Amount: Decimal
    TStatus: str
    CreateDate: datetime
    CreateUser: Optional[str] = None
    UpdateDate: Optional[datetime] = None
    UpdateUser: Optional[str] = None


class NonMotorDashboardSummaryResponse(BaseModel):
    total_policies: int
    total_net_premium: Decimal
    total_commission_paid: Decimal
    by_product_class: List[dict]
