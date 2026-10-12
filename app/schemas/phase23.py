"""
Pydantic v2 Schemas for Phase 23 — Complete HR & Workforce Management System.
Includes Organizations, Departments, Designations, Facilities, Holidays, Leave Types,
Leave Applications & Approvals, and Emergency Contact Persons.
Strictly configured with extra="forbid" and from_attributes=True.
"""
from datetime import datetime, date
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


# ============================================================================
# 1. HR ORGANIZATION SCHEMAS
# ============================================================================

class HROrganizationBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    OrganizationName: str = Field(..., max_length=255, description="Name of the organization/company entity")
    Address: Optional[str] = Field(None, max_length=500, description="Office address")
    MobileNo: Optional[str] = Field(None, max_length=50, description="Contact phone or mobile number")
    IsActive: int = Field(default=1, description="1=Active, 0=Inactive")


class HROrganizationCreate(HROrganizationBase):
    pass


class HROrganizationUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    OrganizationName: Optional[str] = Field(None, max_length=255)
    Address: Optional[str] = Field(None, max_length=500)
    MobileNo: Optional[str] = Field(None, max_length=50)
    IsActive: Optional[int] = None


class HROrganizationResponse(HROrganizationBase):
    OrganizationId: int
    CreatedDate: datetime
    CreateUser: Optional[str] = None
    UpdateDate: Optional[datetime] = None
    UpdatedUser: Optional[str] = None


# ============================================================================
# 2. HR DEPARTMENT SCHEMAS
# ============================================================================

class HRDepartmentBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    OrganizationId: int = Field(..., description="Parent Organization ID")
    Dname: str = Field(..., max_length=255, description="Department name")
    Dlocation: Optional[str] = Field(None, max_length=255, description="Department branch or floor location")
    IsActive: int = Field(default=1, description="1=Active, 0=Inactive")


class HRDepartmentCreate(HRDepartmentBase):
    pass


class HRDepartmentUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    OrganizationId: Optional[int] = None
    Dname: Optional[str] = Field(None, max_length=255)
    Dlocation: Optional[str] = Field(None, max_length=255)
    IsActive: Optional[int] = None


class HRDepartmentResponse(HRDepartmentBase):
    DeparmentId: int
    CreatedDate: datetime
    CreateUser: Optional[str] = None
    UpdateDate: Optional[datetime] = None
    UpdatedUser: Optional[str] = None


# ============================================================================
# 3. HR DESIGNATION SCHEMAS
# ============================================================================

class HRDesignationBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    Designation: str = Field(..., max_length=255, description="Job title / Designation name")
    IsActive: int = Field(default=1, description="1=Active, 0=Inactive")


class HRDesignationCreate(HRDesignationBase):
    pass


class HRDesignationUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    Designation: Optional[str] = Field(None, max_length=255)
    IsActive: Optional[int] = None


class HRDesignationResponse(HRDesignationBase):
    DesignationId: int
    CreatedDate: datetime
    CreateUser: Optional[str] = None
    UpdateDate: Optional[datetime] = None
    UpdatedUser: Optional[str] = None


# ============================================================================
# 4. HR FACILITY SCHEMAS
# ============================================================================

class HRFacilityBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    Name: str = Field(..., max_length=255, description="Facility / perk / allowance name")
    percentage: Optional[str] = Field(None, max_length=50, description="Percentage rate or value")
    IsActive: int = Field(default=1, description="1=Active, 0=Inactive")


class HRFacilityCreate(HRFacilityBase):
    pass


class HRFacilityUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    Name: Optional[str] = Field(None, max_length=255)
    percentage: Optional[str] = Field(None, max_length=50)
    IsActive: Optional[int] = None


class HRFacilityResponse(HRFacilityBase):
    FaciltiyId: int
    CreatedDate: datetime
    CreateUser: Optional[str] = None
    UpdateDate: Optional[datetime] = None
    UpdatedUser: Optional[str] = None


# ============================================================================
# 5. HR HOLIDAY SCHEMAS
# ============================================================================

class HRHolidayBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    HolidayDesc: str = Field(..., max_length=255, description="Holiday description or event title")
    HolidayDate: date = Field(..., description="Calendar date of holiday")
    EmployeeID: Optional[int] = Field(0, description="Employee ID (0 for general company-wide holiday)")
    IsActive: int = Field(default=1, description="1=Active, 0=Inactive")


class HRHolidayCreate(HRHolidayBase):
    pass


class HRHolidayUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    HolidayDesc: Optional[str] = Field(None, max_length=255)
    HolidayDate: Optional[date] = None
    EmployeeID: Optional[int] = None
    IsActive: Optional[int] = None


class HRHolidayResponse(HRHolidayBase):
    HolidayId: int
    CreatedDate: datetime
    CreateUser: Optional[str] = None
    UpdateDate: Optional[datetime] = None
    UpdatedUser: Optional[str] = None


# ============================================================================
# 6. HR LEAVE TYPE SCHEMAS
# ============================================================================

class HRLeaveTypeBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    LeaveType: str = Field(..., max_length=100, description="Leave type title (Casual, Sick, Earned, etc.)")
    IsActive: int = Field(default=1, description="1=Active, 0=Inactive")


class HRLeaveTypeCreate(HRLeaveTypeBase):
    pass


class HRLeaveTypeUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    LeaveType: Optional[str] = Field(None, max_length=100)
    IsActive: Optional[int] = None


class HRLeaveTypeResponse(HRLeaveTypeBase):
    LeaveTypeId: int
    CreatedDate: datetime
    CreateUser: Optional[str] = None
    UpdateDate: Optional[datetime] = None
    UpdatedUser: Optional[str] = None


# ============================================================================
# 7. HR LEAVE APPLICATION & APPROVAL SCHEMAS
# ============================================================================

class HRLeaveBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    OrganizationId: int = Field(..., description="Organization ID")
    DeparmentId: int = Field(..., description="Department ID")
    EmpId: int = Field(..., description="Employee User ID")
    LeaveTypeId: int = Field(..., description="Leave Type ID")
    ApplicationDate: date = Field(default_factory=date.today, description="Date of leave application")
    FromDate: date = Field(..., description="Start date of leave period")
    ToDate: date = Field(..., description="End date of leave period")
    NoOfDays: Decimal = Field(..., description="Number of days requested (e.g. 1.0, 0.5, 3.0)")
    Reason: Optional[str] = Field(None, max_length=500, description="Employee reason for leave")
    Remark: Optional[str] = Field(None, max_length=500, description="Approver/Manager review remarks")
    Handover: Optional[str] = Field(None, max_length=255, description="Work handover notes or peer coverage")
    ReportingId: Optional[int] = Field(None, description="Reporting Manager / Approver User ID")


class HRLeaveCreate(HRLeaveBase):
    pass


class HRLeaveUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    LeaveTypeId: Optional[int] = None
    FromDate: Optional[date] = None
    ToDate: Optional[date] = None
    NoOfDays: Optional[Decimal] = None
    Reason: Optional[str] = Field(None, max_length=500)
    Handover: Optional[str] = Field(None, max_length=255)
    ReportingId: Optional[int] = None


class HRLeaveStatusUpdateRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    ApprovalStatus: int = Field(
        ..., description="Approval status code: 1=Approved, 2=Rejected, 3=Cancelled"
    )
    Remark: Optional[str] = Field(None, max_length=500, description="Manager decision remarks")


class HRLeaveResponse(HRLeaveBase):
    LeaveId: int
    ApprovalStatus: int = Field(description="0=Pending, 1=Approved, 2=Rejected, 3=Cancelled")
    ApprovalDate: Optional[datetime] = None
    CreatedDate: datetime
    CreateUser: Optional[str] = None
    UpdateDate: Optional[datetime] = None
    UpdatedUser: Optional[str] = None


class HRLeaveSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    total_applications: int
    pending_count: int
    approved_count: int
    rejected_count: int
    cancelled_count: int
    total_approved_days: Decimal


# ============================================================================
# 8. HR CONTACT PERSON SCHEMAS
# ============================================================================

class HRContactPersonBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    ContactFName: str = Field(..., max_length=100, description="First name")
    ContactMName: Optional[str] = Field(None, max_length=100, description="Middle name")
    ContactLName: Optional[str] = Field(None, max_length=100, description="Last name")
    MobileNo: Optional[str] = Field(None, max_length=50, description="Primary mobile phone")
    Address: Optional[str] = Field(None, max_length=500, description="Residential or business address")
    IsActive: int = Field(default=1, description="1=Active, 0=Inactive")


class HRContactPersonCreate(HRContactPersonBase):
    pass


class HRContactPersonUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    ContactFName: Optional[str] = Field(None, max_length=100)
    ContactMName: Optional[str] = Field(None, max_length=100)
    ContactLName: Optional[str] = Field(None, max_length=100)
    MobileNo: Optional[str] = Field(None, max_length=50)
    Address: Optional[str] = Field(None, max_length=500)
    IsActive: Optional[int] = None


class HRContactPersonResponse(HRContactPersonBase):
    ContactpersonId: int
    CreatedDate: datetime
    CreateUser: Optional[str] = None
    UpdateDate: Optional[datetime] = None
    UpdatedUser: Optional[str] = None
