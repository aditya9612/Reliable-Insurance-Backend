"""
SQLAlchemy 2.0 Declarative Models for Phase 24 — HR Workforce Lifecycle,
Compensation Structure, Employee Advances & Monthly Attendance Management.

Physical Tables Added:
1. tbl_hrworkinghistory (Employee Previous Employment History)
2. tbl_hrfamilydetails (Employee Family Dependents & Relationships)
3. tbl_hrreferencedetails (Employee Professional Reference Contacts)
4. tbl_hrworkingtime (Employee Daily Shift Hours & Working Schedule)
5. tbl_hrsalarystructuredef (Company Salary Structure Templates)
6. tbl_hradvance (Employee Salary Advance & Recovery Tracking Register)
7. tbl_hrmonthlyworkingdetails (Monthly Attendance, Overtime & Working Days Register)
"""
from datetime import datetime, date
from decimal import Decimal
from typing import Optional
from sqlalchemy import Integer, String, DateTime, Date, Numeric, Text, Index, text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


# ============================================================================
# 1. HR WORKING HISTORY (tbl_hrworkinghistory)
# ============================================================================

class HRWorkingHistory(Base):
    """
    Employee Previous Employment & Experience History Model.
    Physical Table: tbl_hrworkinghistory
    Physical PK: WorkingHistoryId
    Legacy Reference: BLL_HREmployee.BLL_OperationHRInsertworkinghistory,
                      DAL_HREmployee.DAL_OperationHRInsertworkinghistory,
                      sp_HRInsertworkinghistory, API_HRInsertworkinghistory
    """
    __tablename__ = "tbl_hrworkinghistory"
    __table_args__ = (
        Index("ix_tbl_hrworkinghistory_EmployeeID", "EmployeeID"),
        Index("ix_tbl_hrworkinghistory_CompanyName", "CompanyName"),
        {
            "mysql_charset": "utf8",
            "mysql_collate": "utf8_general_ci",
            "mysql_row_format": "DYNAMIC",
        },
    )

    WorkingHistoryId: Mapped[int] = mapped_column(
        "WorkingHistoryId", Integer, primary_key=True, autoincrement=True
    )
    EmployeeID: Mapped[int] = mapped_column("EmployeeID", Integer, nullable=False)
    DepartMentID: Mapped[Optional[int]] = mapped_column("DepartMentID", Integer, nullable=True)
    CompanyName: Mapped[str] = mapped_column("CompanyName", String(255), nullable=False)
    CompanyAddres: Mapped[Optional[str]] = mapped_column("CompanyAddres", String(500), nullable=True)
    CompanyMobileNo: Mapped[Optional[str]] = mapped_column("CompanyMobileNo", String(50), nullable=True)
    PreQualification: Mapped[Optional[str]] = mapped_column("PreQualification", String(255), nullable=True)
    PreExprience: Mapped[Optional[str]] = mapped_column("PreExprience", String(100), nullable=True)
    PreStartDate: Mapped[Optional[date]] = mapped_column("PreStartDate", Date, nullable=True)
    PreEndDate: Mapped[Optional[date]] = mapped_column("PreEndDate", Date, nullable=True)
    HRName: Mapped[Optional[str]] = mapped_column("HRName", String(100), nullable=True)
    HRMobNo: Mapped[Optional[str]] = mapped_column("HRMobNo", String(50), nullable=True)
    HRMailId: Mapped[Optional[str]] = mapped_column("HRMailId", String(100), nullable=True)
    CreatedDate: Mapped[datetime] = mapped_column(
        "CreatedDate", DateTime, nullable=False, default=datetime.utcnow
    )
    CreateUser: Mapped[Optional[str]] = mapped_column("CreateUser", String(100), nullable=True)
    UpdateDate: Mapped[Optional[datetime]] = mapped_column("UpdateDate", DateTime, nullable=True)
    UpdateUser: Mapped[Optional[str]] = mapped_column("UpdateUser", String(100), nullable=True)
    IsActive: Mapped[int] = mapped_column("IsActive", Integer, nullable=False, server_default=text("1"))


# ============================================================================
# 2. HR FAMILY DETAILS (tbl_hrfamilydetails)
# ============================================================================

class HRFamilyDetails(Base):
    """
    Employee Family Dependents & Relationships Model.
    Physical Table: tbl_hrfamilydetails
    Physical PK: FamilyId
    Legacy Reference: BLL_HREmployee.BLL_InsertHrFamilyDetails,
                      DAL_HREmployee.DAL_InsertHrFamilyDetails,
                      sp_InsertHrFamilyDetails, API_HRFamilyDetails
    """
    __tablename__ = "tbl_hrfamilydetails"
    __table_args__ = (
        Index("ix_tbl_hrfamilydetails_EmployeeID", "EmployeeID"),
        Index("ix_tbl_hrfamilydetails_Relation", "Relation"),
        {
            "mysql_charset": "utf8",
            "mysql_collate": "utf8_general_ci",
            "mysql_row_format": "DYNAMIC",
        },
    )

    FamilyId: Mapped[int] = mapped_column("FamilyId", Integer, primary_key=True, autoincrement=True)
    EmployeeID: Mapped[int] = mapped_column("EmployeeID", Integer, nullable=False)
    FName: Mapped[str] = mapped_column("FName", String(150), nullable=False)
    Relation: Mapped[str] = mapped_column("Relation", String(50), nullable=False)
    Occuption: Mapped[Optional[str]] = mapped_column("Occuption", String(100), nullable=True)
    ContactNo: Mapped[Optional[str]] = mapped_column("ContactNo", String(50), nullable=True)
    Designation: Mapped[Optional[str]] = mapped_column("Designation", String(100), nullable=True)
    CreatedDate: Mapped[datetime] = mapped_column(
        "CreatedDate", DateTime, nullable=False, default=datetime.utcnow
    )
    CreateUser: Mapped[Optional[str]] = mapped_column("CreateUser", String(100), nullable=True)
    UpdateDate: Mapped[Optional[datetime]] = mapped_column("UpdateDate", DateTime, nullable=True)
    UpdateUser: Mapped[Optional[str]] = mapped_column("UpdateUser", String(100), nullable=True)
    IsActive: Mapped[int] = mapped_column("IsActive", Integer, nullable=False, server_default=text("1"))


# ============================================================================
# 3. HR REFERENCE DETAILS (tbl_hrreferencedetails)
# ============================================================================

class HRReferenceDetails(Base):
    """
    Employee Professional Reference Contacts Model.
    Physical Table: tbl_hrreferencedetails
    Physical PK: ReferenceId
    Legacy Reference: BLL_HREmployee.BLL_insertHRReferenceDetails,
                      DAL_HREmployee.DAL_insertHRReferenceDetails,
                      sp_insertHRReferenceDetails, API_HRRefernceDetails
    """
    __tablename__ = "tbl_hrreferencedetails"
    __table_args__ = (
        Index("ix_tbl_hrreferencedetails_EmployeeID", "EmployeeID"),
        Index("ix_tbl_hrreferencedetails_ReferenceName", "ReferenceName"),
        {
            "mysql_charset": "utf8",
            "mysql_collate": "utf8_general_ci",
            "mysql_row_format": "DYNAMIC",
        },
    )

    ReferenceId: Mapped[int] = mapped_column("ReferenceId", Integer, primary_key=True, autoincrement=True)
    EmployeeID: Mapped[int] = mapped_column("EmployeeID", Integer, nullable=False)
    ReferenceName: Mapped[str] = mapped_column("ReferenceName", String(150), nullable=False)
    Address: Mapped[Optional[str]] = mapped_column("Address", String(500), nullable=True)
    ContactNo: Mapped[Optional[str]] = mapped_column("ContactNo", String(50), nullable=True)
    Designation: Mapped[Optional[str]] = mapped_column("Designation", String(100), nullable=True)
    MailId: Mapped[Optional[str]] = mapped_column("MailId", String(100), nullable=True)
    CreatedDate: Mapped[datetime] = mapped_column(
        "CreatedDate", DateTime, nullable=False, default=datetime.utcnow
    )
    CreateUser: Mapped[Optional[str]] = mapped_column("CreateUser", String(100), nullable=True)
    UpdateDate: Mapped[Optional[datetime]] = mapped_column("UpdateDate", DateTime, nullable=True)
    UpdateUser: Mapped[Optional[str]] = mapped_column("UpdateUser", String(100), nullable=True)
    IsActive: Mapped[int] = mapped_column("IsActive", Integer, nullable=False, server_default=text("1"))


# ============================================================================
# 4. HR WORKING TIME SCHEDULE (tbl_hrworkingtime)
# ============================================================================

class HRWorkingTime(Base):
    """
    Employee Daily Shift Hours & Working Schedule Model.
    Physical Table: tbl_hrworkingtime
    Physical PK: timeinfoId
    Legacy Reference: BLL_HREmployee.BLL_OperationHRInsertworkingTime,
                      DAL_HREmployee.DAL_OperationHRInsertworkingTime,
                      sp_HRInsertTimeInformation, API_HRworkingTime
    """
    __tablename__ = "tbl_hrworkingtime"
    __table_args__ = (
        Index("ix_tbl_hrworkingtime_EmployeeID", "EmployeeID"),
        Index("ix_tbl_hrworkingtime_DepartMentID", "DepartMentID"),
        {
            "mysql_charset": "utf8",
            "mysql_collate": "utf8_general_ci",
            "mysql_row_format": "DYNAMIC",
        },
    )

    timeinfoId: Mapped[int] = mapped_column("timeinfoId", Integer, primary_key=True, autoincrement=True)
    EmployeeID: Mapped[int] = mapped_column("EmployeeID", Integer, nullable=False)
    DepartMentID: Mapped[Optional[int]] = mapped_column("DepartMentID", Integer, nullable=True)
    workingHours: Mapped[Optional[str]] = mapped_column("workingHours", String(50), nullable=True)
    offday: Mapped[Optional[str]] = mapped_column("offday", String(50), nullable=True, server_default=text("'Sunday'"))
    overtime: Mapped[Optional[str]] = mapped_column("overtime", String(50), nullable=True)
    ExtraDay: Mapped[Optional[str]] = mapped_column("ExtraDay", String(50), nullable=True)
    CreatedDate: Mapped[datetime] = mapped_column(
        "CreatedDate", DateTime, nullable=False, default=datetime.utcnow
    )
    CreateUser: Mapped[Optional[str]] = mapped_column("CreateUser", String(100), nullable=True)
    UpdateDate: Mapped[Optional[datetime]] = mapped_column("UpdateDate", DateTime, nullable=True)
    UpdateUser: Mapped[Optional[str]] = mapped_column("UpdateUser", String(100), nullable=True)
    IsActive: Mapped[int] = mapped_column("IsActive", Integer, nullable=False, server_default=text("1"))


# ============================================================================
# 5. HR SALARY STRUCTURE DEFINITION (tbl_hrsalarystructuredef)
# ============================================================================

class HRSalaryStructureDef(Base):
    """
    Company Salary Structure Templates & Grade Component Ratios Model.
    Physical Table: tbl_hrsalarystructuredef
    Physical PK: SalaryStructureDefId
    Legacy Reference: BLL_Hrsalarystructuredef, DAL_Hrsalarystructuredef,
                      sp_Hrsalarystructuredef, API_Hrsalarystructuredef
    """
    __tablename__ = "tbl_hrsalarystructuredef"
    __table_args__ = (
        Index("ix_tbl_hrsalarystructure_OrgId", "OrganizationId"),
        Index("ix_tbl_hrsalarystructure_Name", "salaryStructure"),
        {
            "mysql_charset": "utf8",
            "mysql_collate": "utf8_general_ci",
            "mysql_row_format": "DYNAMIC",
        },
    )

    SalaryStructureDefId: Mapped[int] = mapped_column(
        "SalaryStructureDefId", Integer, primary_key=True, autoincrement=True
    )
    OrganizationId: Mapped[int] = mapped_column("OrganizationId", Integer, nullable=False)
    salaryStructure: Mapped[str] = mapped_column("salaryStructure", String(255), nullable=False)
    InActive: Mapped[Optional[str]] = mapped_column(
        "InActive", String(10), nullable=True, server_default=text("'0'")
    )
    RateOnGross: Mapped[Optional[str]] = mapped_column("RateOnGross", String(50), nullable=True)
    Remark: Mapped[Optional[str]] = mapped_column("Remark", String(500), nullable=True)
    CreatedDate: Mapped[datetime] = mapped_column(
        "CreatedDate", DateTime, nullable=False, default=datetime.utcnow
    )
    CreateUser: Mapped[Optional[str]] = mapped_column("CreateUser", String(100), nullable=True)
    UpdateDate: Mapped[Optional[datetime]] = mapped_column("UpdateDate", DateTime, nullable=True)
    UpdatedUser: Mapped[Optional[str]] = mapped_column("UpdatedUser", String(100), nullable=True)
    IsActive: Mapped[int] = mapped_column("IsActive", Integer, nullable=False, server_default=text("1"))


# ============================================================================
# 6. HR ADVANCE & RECOVERY TRACKING (tbl_hradvance)
# ============================================================================

class HRAdvance(Base):
    """
    Employee Salary Advance & Monthly Loan Recovery Ledger Model.
    Physical Table: tbl_hradvance
    Physical PK: HrAdvanceId
    Legacy Reference: BLL_HrAdvance, DAL_HrAdvance, SP_HrAdvance,
                      sp_hrinsertEmployeeAdvance, API_HrAdvance
    """
    __tablename__ = "tbl_hradvance"
    __table_args__ = (
        Index("ix_tbl_hradvance_EmpId", "EmpId"),
        Index("ix_tbl_hradvance_OrgId", "OrganizationId"),
        Index("ix_tbl_hradvance_AdvanceDate", "AdvanceDate"),
        {
            "mysql_charset": "utf8",
            "mysql_collate": "utf8_general_ci",
            "mysql_row_format": "DYNAMIC",
        },
    )

    HrAdvanceId: Mapped[int] = mapped_column("HrAdvanceId", Integer, primary_key=True, autoincrement=True)
    EmpId: Mapped[int] = mapped_column("EmpId", Integer, nullable=False)
    OrganizationId: Mapped[int] = mapped_column("OrganizationId", Integer, nullable=False)
    AdvanceName: Mapped[str] = mapped_column("AdvanceName", String(100), nullable=False)
    AdvanceDate: Mapped[date] = mapped_column("AdvanceDate", Date, nullable=False)
    Amount: Mapped[Decimal] = mapped_column(
        "Amount", Numeric(12, 2), nullable=False, server_default=text("0.00")
    )
    InterestAmount: Mapped[Decimal] = mapped_column(
        "InterestAmount", Numeric(12, 2), nullable=False, server_default=text("0.00")
    )
    TotalAdvance: Mapped[Decimal] = mapped_column(
        "TotalAdvance", Numeric(12, 2), nullable=False, server_default=text("0.00")
    )
    TotalInterest: Mapped[Decimal] = mapped_column(
        "TotalInterest", Numeric(12, 2), nullable=False, server_default=text("0.00")
    )
    TotalReceipts: Mapped[Decimal] = mapped_column(
        "TotalReceipts", Numeric(12, 2), nullable=False, server_default=text("0.00")
    )
    TotalRecovered: Mapped[Decimal] = mapped_column(
        "TotalRecovered", Numeric(12, 2), nullable=False, server_default=text("0.00")
    )
    TotalDeu: Mapped[Decimal] = mapped_column(
        "TotalDeu", Numeric(12, 2), nullable=False, server_default=text("0.00")
    )
    Lumpsum: Mapped[Optional[str]] = mapped_column(
        "Lumpsum", String(10), nullable=True, server_default=text("'No'")
    )
    NoOfInstallment: Mapped[Optional[str]] = mapped_column(
        "NoOfInstallment", String(10), nullable=True, server_default=text("'1'")
    )
    Instlamt: Mapped[Decimal] = mapped_column(
        "Instlamt", Numeric(12, 2), nullable=False, server_default=text("0.00")
    )
    RecoverFrom: Mapped[Optional[str]] = mapped_column(
        "RecoverFrom", String(50), nullable=True, server_default=text("'Salary'")
    )
    NoRecovery: Mapped[Optional[str]] = mapped_column(
        "NoRecovery", String(10), nullable=True, server_default=text("'0'")
    )
    Remark: Mapped[Optional[str]] = mapped_column("Remark", String(500), nullable=True)
    CreatedDate: Mapped[datetime] = mapped_column(
        "CreatedDate", DateTime, nullable=False, default=datetime.utcnow
    )
    CreateUser: Mapped[Optional[str]] = mapped_column("CreateUser", String(100), nullable=True)
    UpdateDate: Mapped[Optional[datetime]] = mapped_column("UpdateDate", DateTime, nullable=True)
    UpdatedUser: Mapped[Optional[str]] = mapped_column("UpdatedUser", String(100), nullable=True)
    IsActive: Mapped[int] = mapped_column("IsActive", Integer, nullable=False, server_default=text("1"))


# ============================================================================
# 7. HR MONTHLY WORKING DETAILS & ATTENDANCE (tbl_hrmonthlyworkingdetails)
# ============================================================================

class HRMonthlyWorkingDetails(Base):
    """
    Monthly Attendance, Overtime & Working Days Register Model.
    Physical Table: tbl_hrmonthlyworkingdetails
    Physical PK: MonthlyWorkingId
    Legacy Reference: BLL_HrWorkingDeatils, DAL_HrWorkingDeatils,
                      sp_HrMonthlyWorkingDetails, API_HRWorkingDetails
    """
    __tablename__ = "tbl_hrmonthlyworkingdetails"
    __table_args__ = (
        Index("ix_tbl_hrmonthlyworking_Emp_Period", "EmpId", "Year", "Month"),
        Index("ix_tbl_hrmonthlyworking_Org_Dept", "OrganizationId", "DeparmentId"),
        {
            "mysql_charset": "utf8",
            "mysql_collate": "utf8_general_ci",
            "mysql_row_format": "DYNAMIC",
        },
    )

    MonthlyWorkingId: Mapped[int] = mapped_column(
        "MonthlyWorkingId", Integer, primary_key=True, autoincrement=True
    )
    OrganizationId: Mapped[int] = mapped_column("OrganizationId", Integer, nullable=False)
    DeparmentId: Mapped[int] = mapped_column("DeparmentId", Integer, nullable=False)
    EmpId: Mapped[int] = mapped_column("EmpId", Integer, nullable=False)
    Month: Mapped[int] = mapped_column("Month", Integer, nullable=False)
    Year: Mapped[int] = mapped_column("Year", Integer, nullable=False)
    totalNoOfDays: Mapped[Decimal] = mapped_column(
        "totalNoOfDays", Numeric(5, 2), nullable=False, server_default=text("30.00")
    )
    Sunday: Mapped[Decimal] = mapped_column(
        "Sunday", Numeric(5, 2), nullable=False, server_default=text("4.00")
    )
    Hoildays: Mapped[Decimal] = mapped_column(
        "Hoildays", Numeric(5, 2), nullable=False, server_default=text("0.00")
    )
    leaves: Mapped[Decimal] = mapped_column(
        "leaves", Numeric(5, 2), nullable=False, server_default=text("0.00")
    )
    workingDays: Mapped[Decimal] = mapped_column(
        "workingDays", Numeric(5, 2), nullable=False, server_default=text("26.00")
    )
    ExtraDays: Mapped[Decimal] = mapped_column(
        "ExtraDays", Numeric(5, 2), nullable=False, server_default=text("0.00")
    )
    overTimeHour: Mapped[Decimal] = mapped_column(
        "overTimeHour", Numeric(6, 2), nullable=False, server_default=text("0.00")
    )
    PetrolAll: Mapped[Decimal] = mapped_column(
        "PetrolAll", Numeric(10, 2), nullable=False, server_default=text("0.00")
    )
    Incentive: Mapped[Decimal] = mapped_column(
        "Incentive", Numeric(10, 2), nullable=False, server_default=text("0.00")
    )
    Arrears: Mapped[Decimal] = mapped_column(
        "Arrears", Numeric(10, 2), nullable=False, server_default=text("0.00")
    )
    CreatedDate: Mapped[datetime] = mapped_column(
        "CreatedDate", DateTime, nullable=False, default=datetime.utcnow
    )
    CreateUser: Mapped[Optional[str]] = mapped_column("CreateUser", String(100), nullable=True)
    UpdateDate: Mapped[Optional[datetime]] = mapped_column("UpdateDate", DateTime, nullable=True)
    UpdatedUser: Mapped[Optional[str]] = mapped_column("UpdatedUser", String(100), nullable=True)
    IsActive: Mapped[int] = mapped_column("IsActive", Integer, nullable=False, server_default=text("1"))
