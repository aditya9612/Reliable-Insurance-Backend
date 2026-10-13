"""
Pydantic v2 Schemas for Phase 24 — HR Workforce Lifecycle, Compensation Structure,
Employee Advances & Monthly Attendance Management.
Strictly configured with extra="forbid" and from_attributes=True.
"""
from datetime import datetime, date
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


# ============================================================================
# 1. HR WORKING HISTORY SCHEMAS
# ============================================================================

class HRWorkingHistoryBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    EmployeeID: int = Field(..., description="Employee User / Staff ID")
    DepartMentID: Optional[int] = Field(None, description="Department ID")
    CompanyName: str = Field(..., max_length=255, description="Previous employer organization name")
    CompanyAddres: Optional[str] = Field(None, max_length=500, description="Employer office address")
    CompanyMobileNo: Optional[str] = Field(None, max_length=50, description="Employer phone number")
    PreQualification: Optional[str] = Field(None, max_length=255, description="Degree or qualifications obtained")
    PreExprience: Optional[str] = Field(None, max_length=100, description="Experience tenure (e.g. 2 Years)")
    PreStartDate: Optional[date] = Field(None, description="Employment start date")
    PreEndDate: Optional[date] = Field(None, description="Employment end date")
    HRName: Optional[str] = Field(None, max_length=100, description="Previous HR contact person name")
    HRMobNo: Optional[str] = Field(None, max_length=50, description="Previous HR contact mobile")
    HRMailId: Optional[str] = Field(None, max_length=100, description="Previous HR email address")
    IsActive: int = Field(default=1, description="1=Active, 0=Inactive")


class HRWorkingHistoryCreate(HRWorkingHistoryBase):
    pass


class HRWorkingHistoryUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    CompanyName: Optional[str] = Field(None, max_length=255)
    CompanyAddres: Optional[str] = Field(None, max_length=500)
    CompanyMobileNo: Optional[str] = Field(None, max_length=50)
    PreQualification: Optional[str] = Field(None, max_length=255)
    PreExprience: Optional[str] = Field(None, max_length=100)
    PreStartDate: Optional[date] = None
    PreEndDate: Optional[date] = None
    HRName: Optional[str] = Field(None, max_length=100)
    HRMobNo: Optional[str] = Field(None, max_length=50)
    HRMailId: Optional[str] = Field(None, max_length=100)
    IsActive: Optional[int] = None


class HRWorkingHistoryResponse(HRWorkingHistoryBase):
    WorkingHistoryId: int
    CreatedDate: datetime
    CreateUser: Optional[str] = None
    UpdateDate: Optional[datetime] = None
    UpdateUser: Optional[str] = None


# ============================================================================
# 2. HR FAMILY DETAILS SCHEMAS
# ============================================================================

class HRFamilyDetailsBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    EmployeeID: int = Field(..., description="Employee User ID")
    FName: str = Field(..., max_length=150, description="Full name of family member")
    Relation: str = Field(..., max_length=50, description="Relationship (Spouse, Father, Mother, Child, etc.)")
    Occuption: Optional[str] = Field(None, max_length=100, description="Occupation or profession")
    ContactNo: Optional[str] = Field(None, max_length=50, description="Contact telephone number")
    Designation: Optional[str] = Field(None, max_length=100, description="Designation if employed")
    IsActive: int = Field(default=1, description="1=Active, 0=Inactive")


class HRFamilyDetailsCreate(HRFamilyDetailsBase):
    pass


class HRFamilyDetailsUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    FName: Optional[str] = Field(None, max_length=150)
    Relation: Optional[str] = Field(None, max_length=50)
    Occuption: Optional[str] = Field(None, max_length=100)
    ContactNo: Optional[str] = Field(None, max_length=50)
    Designation: Optional[str] = Field(None, max_length=100)
    IsActive: Optional[int] = None


class HRFamilyDetailsResponse(HRFamilyDetailsBase):
    FamilyId: int
    CreatedDate: datetime
    CreateUser: Optional[str] = None
    UpdateDate: Optional[datetime] = None
    UpdateUser: Optional[str] = None


# ============================================================================
# 3. HR REFERENCE DETAILS SCHEMAS
# ============================================================================

class HRReferenceDetailsBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    EmployeeID: int = Field(..., description="Employee User ID")
    ReferenceName: str = Field(..., max_length=150, description="Full name of professional referee")
    Address: Optional[str] = Field(None, max_length=500, description="Referee address")
    ContactNo: Optional[str] = Field(None, max_length=50, description="Referee phone number")
    Designation: Optional[str] = Field(None, max_length=100, description="Referee professional designation")
    MailId: Optional[str] = Field(None, max_length=100, description="Referee email address")
    IsActive: int = Field(default=1, description="1=Active, 0=Inactive")


class HRReferenceDetailsCreate(HRReferenceDetailsBase):
    pass


class HRReferenceDetailsUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    ReferenceName: Optional[str] = Field(None, max_length=150)
    Address: Optional[str] = Field(None, max_length=500)
    ContactNo: Optional[str] = Field(None, max_length=50)
    Designation: Optional[str] = Field(None, max_length=100)
    MailId: Optional[str] = Field(None, max_length=100)
    IsActive: Optional[int] = None


class HRReferenceDetailsResponse(HRReferenceDetailsBase):
    ReferenceId: int
    CreatedDate: datetime
    CreateUser: Optional[str] = None
    UpdateDate: Optional[datetime] = None
    UpdateUser: Optional[str] = None


# ============================================================================
# 4. HR WORKING TIME SCHEDULE SCHEMAS
# ============================================================================

class HRWorkingTimeBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    EmployeeID: int = Field(..., description="Employee User ID")
    DepartMentID: Optional[int] = Field(None, description="Department ID")
    workingHours: Optional[str] = Field("9.5", max_length=50, description="Shift working hours (e.g. 8.0, 9.5)")
    offday: Optional[str] = Field("Sunday", max_length=50, description="Weekly off day name")
    overtime: Optional[str] = Field("0.0", max_length=50, description="Overtime hourly rate or multiplier")
    ExtraDay: Optional[str] = Field("0", max_length=50, description="Extra compensatory day indicator")
    IsActive: int = Field(default=1, description="1=Active, 0=Inactive")


class HRWorkingTimeCreate(HRWorkingTimeBase):
    pass


class HRWorkingTimeUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    DepartMentID: Optional[int] = None
    workingHours: Optional[str] = Field(None, max_length=50)
    offday: Optional[str] = Field(None, max_length=50)
    overtime: Optional[str] = Field(None, max_length=50)
    ExtraDay: Optional[str] = Field(None, max_length=50)
    IsActive: Optional[int] = None


class HRWorkingTimeResponse(HRWorkingTimeBase):
    timeinfoId: int
    CreatedDate: datetime
    CreateUser: Optional[str] = None
    UpdateDate: Optional[datetime] = None
    UpdateUser: Optional[str] = None


# ============================================================================
# 5. HR SALARY STRUCTURE DEFINITION SCHEMAS
# ============================================================================

class HRSalaryStructureDefBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    OrganizationId: int = Field(..., description="Organization ID")
    salaryStructure: str = Field(..., max_length=255, description="Structure title (Grade A, Officer, etc.)")
    InActive: Optional[str] = Field("0", max_length=10, description="0=Active, 1=Inactive")
    RateOnGross: Optional[str] = Field(None, max_length=50, description="Component percentages or rules")
    Remark: Optional[str] = Field(None, max_length=500, description="Structure notes or details")
    IsActive: int = Field(default=1, description="1=Active, 0=Inactive")


class HRSalaryStructureDefCreate(HRSalaryStructureDefBase):
    pass


class HRSalaryStructureDefUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    salaryStructure: Optional[str] = Field(None, max_length=255)
    InActive: Optional[str] = Field(None, max_length=10)
    RateOnGross: Optional[str] = Field(None, max_length=50)
    Remark: Optional[str] = Field(None, max_length=500)
    IsActive: Optional[int] = None


class HRSalaryStructureDefResponse(HRSalaryStructureDefBase):
    SalaryStructureDefId: int
    CreatedDate: datetime
    CreateUser: Optional[str] = None
    UpdateDate: Optional[datetime] = None
    UpdatedUser: Optional[str] = None


# ============================================================================
# 6. HR ADVANCE & RECOVERY TRACKING SCHEMAS
# ============================================================================

class HRAdvanceBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    EmpId: int = Field(..., description="Employee User ID")
    OrganizationId: int = Field(..., description="Organization ID")
    AdvanceName: str = Field(..., max_length=100, description="Advance purpose (Festival, Emergency, Loan, etc.)")
    AdvanceDate: date = Field(default_factory=date.today, description="Disbursement date")
    Amount: Decimal = Field(..., ge=0, description="Principal advance disbursement amount")
    InterestAmount: Decimal = Field(default=Decimal("0.00"), ge=0, description="Interest amount charged")
    Lumpsum: Optional[str] = Field("No", max_length=10, description="Yes=One-time recovery, No=Installments")
    NoOfInstallment: Optional[str] = Field("1", max_length=10, description="Number of monthly installments")
    RecoverFrom: Optional[str] = Field("Salary", max_length=50, description="Salary, Bonus, Incentive, Cash")
    NoRecovery: Optional[str] = Field("0", max_length=10, description="1=Halt recovery, 0=Active recovery")
    Remark: Optional[str] = Field(None, max_length=500, description="Approval or advance remarks")
    IsActive: int = Field(default=1, description="1=Active, 0=Inactive")


class HRAdvanceCreate(HRAdvanceBase):
    pass


class HRAdvanceUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    AdvanceName: Optional[str] = Field(None, max_length=100)
    Lumpsum: Optional[str] = Field(None, max_length=10)
    NoOfInstallment: Optional[str] = Field(None, max_length=10)
    RecoverFrom: Optional[str] = Field(None, max_length=50)
    NoRecovery: Optional[str] = Field(None, max_length=10)
    Remark: Optional[str] = Field(None, max_length=500)
    IsActive: Optional[int] = None


class HRAdvanceRecoveryRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    RecoveryAmount: Decimal = Field(..., gt=0, description="Amount recovered from salary/cash")
    Remark: Optional[str] = Field(None, max_length=500, description="Recovery notes or voucher reference")


class HRAdvanceResponse(HRAdvanceBase):
    HrAdvanceId: int
    TotalAdvance: Decimal = Field(description="Total principal advance")
    TotalInterest: Decimal = Field(description="Total interest amount")
    TotalReceipts: Decimal = Field(description="Total disbursed amount")
    TotalRecovered: Decimal = Field(description="Total recovered to date")
    TotalDeu: Decimal = Field(description="Remaining balance due")
    Instlamt: Decimal = Field(description="Calculated monthly installment amount")
    CreatedDate: datetime
    CreateUser: Optional[str] = None
    UpdateDate: Optional[datetime] = None
    UpdatedUser: Optional[str] = None


# ============================================================================
# 7. HR MONTHLY WORKING DETAILS & ATTENDANCE SCHEMAS
# ============================================================================

class HRMonthlyWorkingDetailsBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    OrganizationId: int = Field(..., description="Organization ID")
    DeparmentId: int = Field(..., description="Department ID")
    EmpId: int = Field(..., description="Employee User ID")
    Month: int = Field(..., ge=1, le=12, description="Calendar month (1-12)")
    Year: int = Field(..., ge=2000, le=2100, description="Calendar year (e.g. 2026)")
    totalNoOfDays: Decimal = Field(default=Decimal("30.00"), ge=28, le=31, description="Total days in month")
    Sunday: Decimal = Field(default=Decimal("4.00"), ge=0, description="Sundays in month")
    Hoildays: Decimal = Field(default=Decimal("0.00"), ge=0, description="Company/statutory holidays")
    leaves: Decimal = Field(default=Decimal("0.00"), ge=0, description="Approved leaves taken")
    workingDays: Decimal = Field(default=Decimal("26.00"), ge=0, description="Actual working days performed")
    ExtraDays: Decimal = Field(default=Decimal("0.00"), ge=0, description="Extra days or weekend duty")
    overTimeHour: Decimal = Field(default=Decimal("0.00"), ge=0, description="Overtime hours logged")
    PetrolAll: Decimal = Field(default=Decimal("0.00"), ge=0, description="Petrol / travel allowance")
    Incentive: Decimal = Field(default=Decimal("0.00"), ge=0, description="Performance incentive")
    Arrears: Decimal = Field(default=Decimal("0.00"), ge=0, description="Salary arrears or adjustments")
    IsActive: int = Field(default=1, description="1=Active, 0=Inactive")


class HRMonthlyWorkingDetailsCreate(HRMonthlyWorkingDetailsBase):
    pass


class HRMonthlyWorkingDetailsUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    totalNoOfDays: Optional[Decimal] = None
    Sunday: Optional[Decimal] = None
    Hoildays: Optional[Decimal] = None
    leaves: Optional[Decimal] = None
    workingDays: Optional[Decimal] = None
    ExtraDays: Optional[Decimal] = None
    overTimeHour: Optional[Decimal] = None
    PetrolAll: Optional[Decimal] = None
    Incentive: Optional[Decimal] = None
    Arrears: Optional[Decimal] = None
    IsActive: Optional[int] = None


class HRMonthlyWorkingDetailsResponse(HRMonthlyWorkingDetailsBase):
    MonthlyWorkingId: int
    CreatedDate: datetime
    CreateUser: Optional[str] = None
    UpdateDate: Optional[datetime] = None
    UpdatedUser: Optional[str] = None


class HRMonthlyWorkingSummaryReport(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    total_employees_logged: int
    total_working_days: Decimal
    total_leaves_taken: Decimal
    total_overtime_hours: Decimal
    total_petrol_allowances: Decimal
    total_incentives: Decimal
    total_arrears: Decimal
