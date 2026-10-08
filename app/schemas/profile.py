"""
Pydantic Schemas for Phase 15B — Employee, Agent & Franchise Profiles.
"""
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


# ============================================================================
# PII MASKING HELPERS (Phase 15B Remediation — Finding 5)
# ============================================================================

def mask_pan(val: Optional[str]) -> Optional[str]:
    """Masks PAN number, showing only the last 4 characters."""
    if not val:
        return val
    s = str(val).strip()
    if len(s) <= 4:
        return "X" * len(s)
    return "X" * (len(s) - 4) + s[-4:]


def mask_aadhar(val: Optional[str]) -> Optional[str]:
    """Masks Aadhaar number, showing only the last 4 digits."""
    if not val:
        return val
    s = str(val).strip()
    if len(s) <= 4:
        return "X" * len(s)
    return "X" * (len(s) - 4) + s[-4:]


def mask_account_number(val: Optional[str]) -> Optional[str]:
    """Masks bank account number, showing only the last 4 digits."""
    if not val:
        return val
    s = str(val).strip()
    if len(s) <= 4:
        return "X" * len(s)
    return "X" * (len(s) - 4) + s[-4:]


# ============================================================================
# EMPLOYEE SCHEMAS
# ============================================================================

class EmployeeBase(BaseModel):
    UserName: Optional[str] = None
    EmpCode: Optional[str] = None
    EmpFName: Optional[str] = None
    EmpMName: Optional[str] = None
    EmpLName: Optional[str] = None
    AddrLine1: Optional[str] = None
    AddrLine2: Optional[str] = None
    TalukaId: Optional[int] = None
    StateId: Optional[int] = None
    DistrictId: Optional[int] = None
    Gender: Optional[str] = None
    MaritalStatus: Optional[str] = None
    MoblieNo: Optional[str] = None
    MoblieNo1: Optional[str] = None
    EmailId: Optional[str] = None
    PAN_No: Optional[str] = None
    AadharNo: Optional[str] = None
    BankId: Optional[int] = None
    BankBranch: Optional[str] = None
    Ifsc_code: Optional[str] = None
    accountNo: Optional[str] = None
    BranchId: Optional[int] = None
    UserRoleId: Optional[int] = None
    UserId: Optional[int] = None


class EmployeeCreate(EmployeeBase):
    UserPassword: Optional[str] = None


class EmployeeUpdate(BaseModel):
    UserName: Optional[str] = None
    UserPassword: Optional[str] = None
    EmpCode: Optional[str] = None
    EmpFName: Optional[str] = None
    EmpMName: Optional[str] = None
    EmpLName: Optional[str] = None
    AddrLine1: Optional[str] = None
    AddrLine2: Optional[str] = None
    TalukaId: Optional[int] = None
    StateId: Optional[int] = None
    DistrictId: Optional[int] = None
    Gender: Optional[str] = None
    MaritalStatus: Optional[str] = None
    MoblieNo: Optional[str] = None
    MoblieNo1: Optional[str] = None
    EmailId: Optional[str] = None
    PAN_No: Optional[str] = None
    AadharNo: Optional[str] = None
    BankId: Optional[int] = None
    BankBranch: Optional[str] = None
    Ifsc_code: Optional[str] = None
    accountNo: Optional[str] = None
    BranchId: Optional[int] = None
    UserRoleId: Optional[int] = None
    UserId: Optional[int] = None


class EmployeeResponse(EmployeeBase):
    model_config = ConfigDict(from_attributes=True)

    EmpId: int
    full_name: str
    is_active: bool
    isdeleted: str
    CreateDate: Optional[datetime] = None
    CreateUser: Optional[str] = None
    UpdateDate: Optional[datetime] = None
    UpdateUser: Optional[str] = None


# ============================================================================
# AGENT SCHEMAS
# ============================================================================

class AgentBase(BaseModel):
    AgentCode: Optional[str] = None
    AgentFName: Optional[str] = None
    AgentMName: Optional[str] = None
    AgentLName: Optional[str] = None
    NickName: Optional[str] = None
    Champanion: Optional[str] = None
    MobileNo: Optional[str] = None
    EmailId: Optional[str] = None
    PANNo: Optional[str] = None
    AadharNo: Optional[str] = None
    SalesExecutiveId: Optional[int] = None
    CoordinatorId: Optional[int] = None
    FranchiseId: Optional[int] = None
    BranchId: Optional[int] = None
    UserId: Optional[int] = None
    BankId: Optional[int] = None
    BankBranch: Optional[str] = None
    Ifsc_code: Optional[str] = None
    accountNo: Optional[str] = None
    IsActive: int = 1


class AgentCreate(AgentBase):
    pass


class AgentUpdate(BaseModel):
    AgentCode: Optional[str] = None
    AgentFName: Optional[str] = None
    AgentMName: Optional[str] = None
    AgentLName: Optional[str] = None
    NickName: Optional[str] = None
    Champanion: Optional[str] = None
    MobileNo: Optional[str] = None
    EmailId: Optional[str] = None
    PANNo: Optional[str] = None
    AadharNo: Optional[str] = None
    SalesExecutiveId: Optional[int] = None
    CoordinatorId: Optional[int] = None
    FranchiseId: Optional[int] = None
    BranchId: Optional[int] = None
    UserId: Optional[int] = None
    BankId: Optional[int] = None
    BankBranch: Optional[str] = None
    Ifsc_code: Optional[str] = None
    accountNo: Optional[str] = None
    IsActive: Optional[int] = None


class AgentKYCUpload(BaseModel):
    document_type: str = Field(..., description="PAN, AADHAR, CANCELLED_CHEQUE, CERTIFICATE")
    document_number: Optional[str] = None
    remarks: Optional[str] = None


class AgentResponse(AgentBase):
    model_config = ConfigDict(from_attributes=True)

    AgentId: int
    full_name: str
    is_active: bool
    isdeleted: str
    CreateDate: Optional[datetime] = None
    CreateUser: Optional[str] = None
    UpdateDate: Optional[datetime] = None
    UpdateUser: Optional[str] = None


# ============================================================================
# FRANCHISE SCHEMAS
# ============================================================================

class FranchiseBase(BaseModel):
    UserName: Optional[str] = None
    initial: Optional[str] = None
    FranFName: Optional[str] = None
    FranMName: Optional[str] = None
    FranLName: Optional[str] = None
    FranCode: Optional[str] = None
    PerAddrLine1: Optional[str] = None
    PerAddrLine2: Optional[str] = None
    PerTalukaId: Optional[int] = None
    PerDistrictId: Optional[int] = None
    PerStateId: Optional[int] = None
    PerPinCode: Optional[str] = None
    MoblieNo1: Optional[str] = None
    MoblieNo2: Optional[str] = None
    Gender: Optional[str] = None
    MaritalStatus: Optional[str] = None
    PAN_No: Optional[str] = None
    AadharNo: Optional[str] = None
    BankId: Optional[int] = None
    NominieeName: Optional[str] = None
    Bank_branch: Optional[str] = None
    Ifsc_code: Optional[str] = None
    accountNo: Optional[str] = None
    DateOfBirth: Optional[date] = None
    EmailId: Optional[str] = None
    BranchId: Optional[int] = None
    ParentFranchiseId: Optional[int] = None
    CoordinatorId: Optional[int] = None
    QuotationCo_Id: Optional[int] = None
    InspectionCo_Id: Optional[int] = None
    EndrosmentCo_Id: Optional[int] = None
    UserRoleId: Optional[int] = None


class FranchiseCreate(FranchiseBase):
    UserPassword: Optional[str] = None


class FranchiseUpdate(BaseModel):
    UserName: Optional[str] = None
    UserPassword: Optional[str] = None
    initial: Optional[str] = None
    FranFName: Optional[str] = None
    FranMName: Optional[str] = None
    FranLName: Optional[str] = None
    FranCode: Optional[str] = None
    PerAddrLine1: Optional[str] = None
    PerAddrLine2: Optional[str] = None
    PerTalukaId: Optional[int] = None
    PerDistrictId: Optional[int] = None
    PerStateId: Optional[int] = None
    PerPinCode: Optional[str] = None
    MoblieNo1: Optional[str] = None
    MoblieNo2: Optional[str] = None
    Gender: Optional[str] = None
    MaritalStatus: Optional[str] = None
    PAN_No: Optional[str] = None
    AadharNo: Optional[str] = None
    BankId: Optional[int] = None
    NominieeName: Optional[str] = None
    Bank_branch: Optional[str] = None
    Ifsc_code: Optional[str] = None
    accountNo: Optional[str] = None
    DateOfBirth: Optional[date] = None
    EmailId: Optional[str] = None
    BranchId: Optional[int] = None
    ParentFranchiseId: Optional[int] = None
    CoordinatorId: Optional[int] = None
    QuotationCo_Id: Optional[int] = None
    InspectionCo_Id: Optional[int] = None
    EndrosmentCo_Id: Optional[int] = None
    UserRoleId: Optional[int] = None


class FranchiseResponse(FranchiseBase):
    model_config = ConfigDict(from_attributes=True)

    FranchiseId: int
    full_name: str
    is_active: bool
    isdeleted: str
    CreateDate: Optional[datetime] = None
    CreateUser: Optional[str] = None
    UpdateDate: Optional[datetime] = None
    UpdateUser: Optional[str] = None


# ============================================================================
# RESPONSE MASKING WRAPPERS
# ============================================================================

def mask_employee_pii(emp: EmployeeResponse) -> EmployeeResponse:
    """Returns a masked copy of EmployeeResponse for non-privileged viewers."""
    return emp.model_copy(update={
        "PAN_No": mask_pan(emp.PAN_No),
        "AadharNo": mask_aadhar(emp.AadharNo),
        "accountNo": mask_account_number(emp.accountNo),
    })


def mask_agent_pii(agent: AgentResponse) -> AgentResponse:
    """Returns a masked copy of AgentResponse for non-privileged viewers."""
    return agent.model_copy(update={
        "PANNo": mask_pan(agent.PANNo),
        "AadharNo": mask_aadhar(agent.AadharNo),
        "accountNo": mask_account_number(agent.accountNo),
    })


def mask_franchise_pii(fran: FranchiseResponse) -> FranchiseResponse:
    """Returns a masked copy of FranchiseResponse for non-privileged viewers."""
    return fran.model_copy(update={
        "PAN_No": mask_pan(fran.PAN_No),
        "AadharNo": mask_aadhar(fran.AadharNo),
        "accountNo": mask_account_number(fran.accountNo),
    })
