"""
SQLAlchemy 2.0 Declarative Models for Phase 23 — Complete HR & Workforce Management System.

Physical Tables Added:
1. tbl_hrorganization (HR Organization Master)
2. tbl_hrdepartment (HR Department Master)
3. tbl_hrdesignationmaster (HR Designation Master)
4. tbl_hrfacility (HR Facility Master)
5. tbl_hrholiday (HR Holiday Calendar Master)
6. tbl_hrleavetype (HR Leave Types Master)
7. tbl_hrleave (HR Employee Leave Applications & Approvals)
8. tbl_hrcontactperson (HR Emergency & Reference Contact Persons)
"""
from datetime import datetime, date
from decimal import Decimal
from typing import Optional
from sqlalchemy import Integer, String, DateTime, Date, Numeric, Text, Index, text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


# ============================================================================
# 1. HR ORGANIZATION MASTER (tbl_hrorganization)
# ============================================================================

class HROrganization(Base):
    """
    HR Organization Master Model.
    Physical Table: tbl_hrorganization
    Physical PK: OrganizationId
    Legacy Reference: BLL_HROrganizatione, DAL_HROrganizatione, sp_HRorganizationmaster
    """
    __tablename__ = "tbl_hrorganization"
    __table_args__ = (
        Index("ix_tbl_hrorganization_Name", "OrganizationName"),
        {
            "mysql_charset": "utf8",
            "mysql_collate": "utf8_general_ci",
            "mysql_row_format": "DYNAMIC",
        },
    )

    OrganizationId: Mapped[int] = mapped_column("OrganizationId", Integer, primary_key=True, autoincrement=True)
    OrganizationName: Mapped[str] = mapped_column("OrganizationName", String(255), nullable=False)
    Address: Mapped[Optional[str]] = mapped_column("Address", String(500), nullable=True)
    MobileNo: Mapped[Optional[str]] = mapped_column("MobileNo", String(50), nullable=True)
    CreatedDate: Mapped[datetime] = mapped_column(
        "CreatedDate", DateTime, nullable=False, default=datetime.utcnow
    )
    CreateUser: Mapped[Optional[str]] = mapped_column("CreateUser", String(100), nullable=True)
    UpdateDate: Mapped[Optional[datetime]] = mapped_column("UpdateDate", DateTime, nullable=True)
    UpdatedUser: Mapped[Optional[str]] = mapped_column("UpdatedUser", String(100), nullable=True)
    IsActive: Mapped[int] = mapped_column("IsActive", Integer, nullable=False, server_default=text("1"))

    departments: Mapped[list["HRDepartment"]] = relationship(
        "HRDepartment", back_populates="organization", cascade="all, delete-orphan", lazy="selectin"
    )


# ============================================================================
# 2. HR DEPARTMENT MASTER (tbl_hrdepartment)
# ============================================================================

class HRDepartment(Base):
    """
    HR Department Master Model.
    Physical Table: tbl_hrdepartment
    Physical PK: DeparmentId
    Legacy Reference: BLL_HRdeparmentmaster, DAL_HRdeparmentmaster, sp_HRDepartmentMaster
    """
    __tablename__ = "tbl_hrdepartment"
    __table_args__ = (
        Index("ix_tbl_hrdepartment_OrgId", "OrganizationId"),
        Index("ix_tbl_hrdepartment_DName", "Dname"),
        {
            "mysql_charset": "utf8",
            "mysql_collate": "utf8_general_ci",
            "mysql_row_format": "DYNAMIC",
        },
    )

    DeparmentId: Mapped[int] = mapped_column("DeparmentId", Integer, primary_key=True, autoincrement=True)
    OrganizationId: Mapped[int] = mapped_column(
        "OrganizationId", Integer, ForeignKey("tbl_hrorganization.OrganizationId"), nullable=False
    )
    Dname: Mapped[str] = mapped_column("Dname", String(255), nullable=False)
    Dlocation: Mapped[Optional[str]] = mapped_column("Dlocation", String(255), nullable=True)
    CreatedDate: Mapped[datetime] = mapped_column(
        "CreatedDate", DateTime, nullable=False, default=datetime.utcnow
    )
    CreateUser: Mapped[Optional[str]] = mapped_column("CreateUser", String(100), nullable=True)
    UpdateDate: Mapped[Optional[datetime]] = mapped_column("UpdateDate", DateTime, nullable=True)
    UpdatedUser: Mapped[Optional[str]] = mapped_column("UpdatedUser", String(100), nullable=True)
    IsActive: Mapped[int] = mapped_column("IsActive", Integer, nullable=False, server_default=text("1"))

    organization: Mapped[Optional["HROrganization"]] = relationship("HROrganization", back_populates="departments")


# ============================================================================
# 3. HR DESIGNATION MASTER (tbl_hrdesignationmaster)
# ============================================================================

class HRDesignation(Base):
    """
    HR Designation Master Model.
    Physical Table: tbl_hrdesignationmaster
    Physical PK: DesignationId
    Legacy Reference: BLL_HRDesignationMaster, DAL_HRDesignationMaster, sp_HRDesignationMaster
    """
    __tablename__ = "tbl_hrdesignationmaster"
    __table_args__ = (
        Index("ix_tbl_hrdesignation_Name", "Designation"),
        {
            "mysql_charset": "utf8",
            "mysql_collate": "utf8_general_ci",
            "mysql_row_format": "DYNAMIC",
        },
    )

    DesignationId: Mapped[int] = mapped_column("DesignationId", Integer, primary_key=True, autoincrement=True)
    Designation: Mapped[str] = mapped_column("Designation", String(255), nullable=False)
    CreatedDate: Mapped[datetime] = mapped_column(
        "CreatedDate", DateTime, nullable=False, default=datetime.utcnow
    )
    CreateUser: Mapped[Optional[str]] = mapped_column("CreateUser", String(100), nullable=True)
    UpdateDate: Mapped[Optional[datetime]] = mapped_column("UpdateDate", DateTime, nullable=True)
    UpdatedUser: Mapped[Optional[str]] = mapped_column("UpdatedUser", String(100), nullable=True)
    IsActive: Mapped[int] = mapped_column("IsActive", Integer, nullable=False, server_default=text("1"))


# ============================================================================
# 4. HR FACILITY MASTER (tbl_hrfacility)
# ============================================================================

class HRFacility(Base):
    """
    HR Facility Master Model.
    Physical Table: tbl_hrfacility
    Physical PK: FaciltiyId
    Legacy Reference: BLL_HRfaciltitymaster, DAL_HRfaciltitymaster, sp_HRfaciltitymaster
    """
    __tablename__ = "tbl_hrfacility"
    __table_args__ = (
        Index("ix_tbl_hrfacility_Name", "Name"),
        {
            "mysql_charset": "utf8",
            "mysql_collate": "utf8_general_ci",
            "mysql_row_format": "DYNAMIC",
        },
    )

    FaciltiyId: Mapped[int] = mapped_column("FaciltiyId", Integer, primary_key=True, autoincrement=True)
    Name: Mapped[str] = mapped_column("Name", String(255), nullable=False)
    percentage: Mapped[Optional[str]] = mapped_column("percentage", String(50), nullable=True)
    CreatedDate: Mapped[datetime] = mapped_column(
        "CreatedDate", DateTime, nullable=False, default=datetime.utcnow
    )
    CreateUser: Mapped[Optional[str]] = mapped_column("CreateUser", String(100), nullable=True)
    UpdateDate: Mapped[Optional[datetime]] = mapped_column("UpdateDate", DateTime, nullable=True)
    UpdatedUser: Mapped[Optional[str]] = mapped_column("UpdatedUser", String(100), nullable=True)
    IsActive: Mapped[int] = mapped_column("IsActive", Integer, nullable=False, server_default=text("1"))


# ============================================================================
# 5. HR HOLIDAY MASTER (tbl_hrholiday)
# ============================================================================

class HRHoliday(Base):
    """
    HR Holiday Calendar Master Model.
    Physical Table: tbl_hrholiday
    Physical PK: HolidayId
    Legacy Reference: BLL_HRholidaymaster, DAL_HRholidaymaster, sp_HRholidaymaster
    """
    __tablename__ = "tbl_hrholiday"
    __table_args__ = (
        Index("ix_tbl_hrholiday_Date", "HolidayDate"),
        Index("ix_tbl_hrholiday_EmpId", "EmployeeID"),
        {
            "mysql_charset": "utf8",
            "mysql_collate": "utf8_general_ci",
            "mysql_row_format": "DYNAMIC",
        },
    )

    HolidayId: Mapped[int] = mapped_column("HolidayId", Integer, primary_key=True, autoincrement=True)
    EmployeeID: Mapped[Optional[int]] = mapped_column("EmployeeID", Integer, nullable=True, server_default=text("0"))
    HolidayDesc: Mapped[str] = mapped_column("HolidayDesc", String(255), nullable=False)
    HolidayDate: Mapped[date] = mapped_column("HolidayDate", Date, nullable=False)
    CreatedDate: Mapped[datetime] = mapped_column(
        "CreatedDate", DateTime, nullable=False, default=datetime.utcnow
    )
    CreateUser: Mapped[Optional[str]] = mapped_column("CreateUser", String(100), nullable=True)
    UpdateDate: Mapped[Optional[datetime]] = mapped_column("UpdateDate", DateTime, nullable=True)
    UpdatedUser: Mapped[Optional[str]] = mapped_column("UpdatedUser", String(100), nullable=True)
    IsActive: Mapped[int] = mapped_column("IsActive", Integer, nullable=False, server_default=text("1"))


# ============================================================================
# 6. HR LEAVE TYPE MASTER (tbl_hrleavetype)
# ============================================================================

class HRLeaveType(Base):
    """
    HR Leave Type Master Model (Casual, Sick, Earned, Maternity, Compensatory, etc.).
    Physical Table: tbl_hrleavetype
    Physical PK: LeaveTypeId
    Legacy Reference: BLL_HRLeaveType, DAL_HrLeaveType, sp_HrLeaveType
    """
    __tablename__ = "tbl_hrleavetype"
    __table_args__ = (
        Index("ix_tbl_hrleavetype_Name", "LeaveType"),
        {
            "mysql_charset": "utf8",
            "mysql_collate": "utf8_general_ci",
            "mysql_row_format": "DYNAMIC",
        },
    )

    LeaveTypeId: Mapped[int] = mapped_column("LeaveTypeId", Integer, primary_key=True, autoincrement=True)
    LeaveType: Mapped[str] = mapped_column("LeaveType", String(100), nullable=False)
    CreatedDate: Mapped[datetime] = mapped_column(
        "CreatedDate", DateTime, nullable=False, default=datetime.utcnow
    )
    CreateUser: Mapped[Optional[str]] = mapped_column("CreateUser", String(100), nullable=True)
    UpdateDate: Mapped[Optional[datetime]] = mapped_column("UpdateDate", DateTime, nullable=True)
    UpdatedUser: Mapped[Optional[str]] = mapped_column("UpdatedUser", String(100), nullable=True)
    IsActive: Mapped[int] = mapped_column("IsActive", Integer, nullable=False, server_default=text("1"))


# ============================================================================
# 7. HR LEAVE APPLICATIONS & APPROVALS (tbl_hrleave)
# ============================================================================

class HRLeave(Base):
    """
    HR Employee Leave Application, Tracking & Approval State Machine Model.
    Physical Table: tbl_hrleave
    Physical PK: LeaveId
    Legacy Reference: BLL_HRLeave, DAL_HrLeave, sp_HrLeave, sp_RptApplyLeaveReporting,
                      sp_RptApplyLeaveRemark, sp_RptApplyLeaveReportingCount
    ApprovalStatus: 0 = Pending, 1 = Approved, 2 = Rejected, 3 = Cancelled
    """
    __tablename__ = "tbl_hrleave"
    __table_args__ = (
        Index("ix_tbl_hrleave_EmpId", "EmpId"),
        Index("ix_tbl_hrleave_Org_Dept", "OrganizationId", "DeparmentId"),
        Index("ix_tbl_hrleave_ReportingId", "ReportingId"),
        Index("ix_tbl_hrleave_Status", "ApprovalStatus"),
        Index("ix_tbl_hrleave_DateRange", "FromDate", "ToDate"),
        {
            "mysql_charset": "utf8",
            "mysql_collate": "utf8_general_ci",
            "mysql_row_format": "DYNAMIC",
        },
    )

    LeaveId: Mapped[int] = mapped_column("LeaveId", Integer, primary_key=True, autoincrement=True)
    OrganizationId: Mapped[int] = mapped_column("OrganizationId", Integer, nullable=False)
    DeparmentId: Mapped[int] = mapped_column("DeparmentId", Integer, nullable=False)
    EmpId: Mapped[int] = mapped_column("EmpId", Integer, nullable=False)
    LeaveTypeId: Mapped[int] = mapped_column("LeaveTypeId", Integer, nullable=False)
    ApplicationDate: Mapped[date] = mapped_column("ApplicationDate", Date, nullable=False, default=date.today)
    FromDate: Mapped[date] = mapped_column("FromDate", Date, nullable=False)
    ToDate: Mapped[date] = mapped_column("ToDate", Date, nullable=False)
    NoOfDays: Mapped[Decimal] = mapped_column("NoOfDays", Numeric(5, 2), nullable=False)
    Reason: Mapped[Optional[str]] = mapped_column("Reason", String(500), nullable=True)
    Remark: Mapped[Optional[str]] = mapped_column("Remark", String(500), nullable=True)
    Handover: Mapped[Optional[str]] = mapped_column("Handover", String(255), nullable=True)
    ReportingId: Mapped[Optional[int]] = mapped_column("ReportingId", Integer, nullable=True)
    ApprovalStatus: Mapped[int] = mapped_column("ApprovalStatus", Integer, nullable=False, server_default=text("0"))
    ApprovalDate: Mapped[Optional[datetime]] = mapped_column("ApprovalDate", DateTime, nullable=True)
    CreatedDate: Mapped[datetime] = mapped_column(
        "CreatedDate", DateTime, nullable=False, default=datetime.utcnow
    )
    CreateUser: Mapped[Optional[str]] = mapped_column("CreateUser", String(100), nullable=True)
    UpdateDate: Mapped[Optional[datetime]] = mapped_column("UpdateDate", DateTime, nullable=True)
    UpdatedUser: Mapped[Optional[str]] = mapped_column("UpdatedUser", String(100), nullable=True)


# ============================================================================
# 8. HR CONTACT PERSON MASTER (tbl_hrcontactperson)
# ============================================================================

class HRContactPerson(Base):
    """
    HR Emergency & Reference Contact Persons Model.
    Physical Table: tbl_hrcontactperson
    Physical PK: ContactpersonId
    Legacy Reference: BLL_HRContactPerson, DAL_HRContactPerson, sp_HRContactPerson
    """
    __tablename__ = "tbl_hrcontactperson"
    __table_args__ = (
        Index("ix_tbl_hrcontact_Name", "ContactFName", "ContactLName"),
        Index("ix_tbl_hrcontact_MobileNo", "MobileNo"),
        {
            "mysql_charset": "utf8",
            "mysql_collate": "utf8_general_ci",
            "mysql_row_format": "DYNAMIC",
        },
    )

    ContactpersonId: Mapped[int] = mapped_column("ContactpersonId", Integer, primary_key=True, autoincrement=True)
    ContactFName: Mapped[str] = mapped_column("ContactFName", String(100), nullable=False)
    ContactMName: Mapped[Optional[str]] = mapped_column("ContactMName", String(100), nullable=True)
    ContactLName: Mapped[Optional[str]] = mapped_column("ContactLName", String(100), nullable=True)
    MobileNo: Mapped[Optional[str]] = mapped_column("MobileNo", String(50), nullable=True)
    Address: Mapped[Optional[str]] = mapped_column("Address", String(500), nullable=True)
    CreatedDate: Mapped[datetime] = mapped_column(
        "CreatedDate", DateTime, nullable=False, default=datetime.utcnow
    )
    CreateUser: Mapped[Optional[str]] = mapped_column("CreateUser", String(100), nullable=True)
    UpdateDate: Mapped[Optional[datetime]] = mapped_column("UpdateDate", DateTime, nullable=True)
    UpdatedUser: Mapped[Optional[str]] = mapped_column("UpdatedUser", String(100), nullable=True)
    IsActive: Mapped[int] = mapped_column("IsActive", Integer, nullable=False, server_default=text("1"))
