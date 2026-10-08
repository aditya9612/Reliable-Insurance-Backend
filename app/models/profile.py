"""
SQLAlchemy 2.0 Declarative Models for Phase 15B — Employee, Agent & Franchise Profiles.
Physical Tables:
- tbl_employee (Staff Directory & Hierarchy Master)
- tbl_agent (POSP Agent Profiles & Master)
- tbl_franchise (Franchise Hierarchy & Profiles)
"""
from datetime import datetime, date
from decimal import Decimal
from typing import Optional
from sqlalchemy import Integer, String, DateTime, Date, Numeric, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class Employee(Base):
    """
    Staff Directory & Organization Hierarchy Model.
    Physical Table: tbl_employee
    Physical PK: EmpId
    """
    __tablename__ = "tbl_employee"
    __table_args__ = (
        Index("ix_tbl_employee_EmpCode", "EmpCode"),
        Index("ix_tbl_employee_BranchId", "BranchId"),
        Index("ix_tbl_employee_UserId", "UserId"),
        Index("ix_tbl_employee_UserRoleId", "UserRoleId"),
        Index("ix_tbl_employee_isdeleted", "isdeleted"),
        {
            "mysql_charset": "utf8",
            "mysql_collate": "utf8_general_ci",
            "mysql_row_format": "DYNAMIC",
        },
    )

    EmpId: Mapped[int] = mapped_column("EmpId", Integer, primary_key=True, autoincrement=True)
    UserName: Mapped[Optional[str]] = mapped_column("UserName", String(255), nullable=True)
    UserPassword: Mapped[Optional[str]] = mapped_column("UserPassword", String(255), nullable=True)
    EmpCode: Mapped[Optional[str]] = mapped_column("EmpCode", String(50), nullable=True)
    EmpFName: Mapped[Optional[str]] = mapped_column("EmpFName", String(100), nullable=True)
    EmpMName: Mapped[Optional[str]] = mapped_column("EmpMName", String(100), nullable=True)
    EmpLName: Mapped[Optional[str]] = mapped_column("EmpLName", String(100), nullable=True)
    AddrLine1: Mapped[Optional[str]] = mapped_column("AddrLine1", String(255), nullable=True)
    AddrLine2: Mapped[Optional[str]] = mapped_column("AddrLine2", String(255), nullable=True)
    TalukaId: Mapped[Optional[int]] = mapped_column("TalukaId", Integer, nullable=True)
    StateId: Mapped[Optional[int]] = mapped_column("StateId", Integer, nullable=True)
    DistrictId: Mapped[Optional[int]] = mapped_column("DistrictId", Integer, nullable=True)
    Gender: Mapped[Optional[str]] = mapped_column("Gender", String(20), nullable=True)
    MaritalStatus: Mapped[Optional[str]] = mapped_column("MaritalStatus", String(20), nullable=True)
    MoblieNo: Mapped[Optional[str]] = mapped_column("MoblieNo", String(50), nullable=True)
    MoblieNo1: Mapped[Optional[str]] = mapped_column("MoblieNo1", String(50), nullable=True)
    EmailId: Mapped[Optional[str]] = mapped_column("EmailId", String(100), nullable=True)
    PAN_No: Mapped[Optional[str]] = mapped_column("PAN_No", String(20), nullable=True)
    AadharNo: Mapped[Optional[str]] = mapped_column("AadharNo", String(20), nullable=True)
    BankId: Mapped[Optional[int]] = mapped_column("BankId", Integer, nullable=True)
    BankBranch: Mapped[Optional[str]] = mapped_column("BankBranch", String(100), nullable=True)
    Ifsc_code: Mapped[Optional[str]] = mapped_column("Ifsc_code", String(50), nullable=True)
    accountNo: Mapped[Optional[str]] = mapped_column("accountNo", String(50), nullable=True)
    BranchId: Mapped[Optional[int]] = mapped_column("BranchId", Integer, nullable=True)
    UserRoleId: Mapped[Optional[int]] = mapped_column("UserRoleId", Integer, nullable=True)
    UserId: Mapped[Optional[int]] = mapped_column("UserId", Integer, nullable=True)
    Hei_Data: Mapped[Optional[str]] = mapped_column("Hei_Data", String(255), nullable=True)
    Hie_DataSales: Mapped[Optional[str]] = mapped_column("Hie_DataSales", String(255), nullable=True)
    Hie_DataOprn: Mapped[Optional[str]] = mapped_column("Hie_DataOprn", String(255), nullable=True)
    CreateDate: Mapped[Optional[datetime]] = mapped_column("CreateDate", DateTime, nullable=True, default=datetime.utcnow)
    CreateUser: Mapped[Optional[str]] = mapped_column("CreateUser", String(100), nullable=True)
    UpdateDate: Mapped[Optional[datetime]] = mapped_column("UpdateDate", DateTime, nullable=True, onupdate=datetime.utcnow)
    UpdateUser: Mapped[Optional[str]] = mapped_column("UpdateUser", String(100), nullable=True)
    isdeleted: Mapped[str] = mapped_column("isdeleted", String(10), nullable=False, default="0")

    @property
    def full_name(self) -> str:
        parts = [p for p in [self.EmpFName, self.EmpMName, self.EmpLName] if p]
        return " ".join(parts) if parts else (self.UserName or "")

    @property
    def is_active(self) -> bool:
        return str(self.isdeleted).strip() != "1"


class Agent(Base):
    """
    POSP Agent Master Model.
    Physical Table: tbl_agent
    Physical PK: AgentId
    """
    __tablename__ = "tbl_agent"
    __table_args__ = (
        Index("ix_tbl_agent_AgentCode", "AgentCode"),
        Index("ix_tbl_agent_SalesExecutiveId", "SalesExecutiveId"),
        Index("ix_tbl_agent_CoordinatorId", "CoordinatorId"),
        Index("ix_tbl_agent_FranchiseId", "FranchiseId"),
        Index("ix_tbl_agent_BranchId", "BranchId"),
        Index("ix_tbl_agent_UserId", "UserId"),
        Index("ix_tbl_agent_isdeleted", "isdeleted"),
        {
            "mysql_charset": "utf8",
            "mysql_collate": "utf8_general_ci",
            "mysql_row_format": "DYNAMIC",
        },
    )

    AgentId: Mapped[int] = mapped_column("AgentId", Integer, primary_key=True, autoincrement=True)
    AgentCode: Mapped[Optional[str]] = mapped_column("AgentCode", String(50), nullable=True)
    AgentFName: Mapped[Optional[str]] = mapped_column("AgentFName", String(100), nullable=True)
    AgentMName: Mapped[Optional[str]] = mapped_column("AgentMName", String(100), nullable=True)
    AgentLName: Mapped[Optional[str]] = mapped_column("AgentLName", String(100), nullable=True)
    NickName: Mapped[Optional[str]] = mapped_column("NickName", String(100), nullable=True)
    Champanion: Mapped[Optional[str]] = mapped_column("Champanion", String(100), nullable=True)
    MobileNo: Mapped[Optional[str]] = mapped_column("MobileNo", String(50), nullable=True)
    EmailId: Mapped[Optional[str]] = mapped_column("EmailId", String(100), nullable=True)
    PANNo: Mapped[Optional[str]] = mapped_column("PANNo", String(20), nullable=True)
    AadharNo: Mapped[Optional[str]] = mapped_column("AadharNo", String(20), nullable=True)
    SalesExecutiveId: Mapped[Optional[int]] = mapped_column("SalesExecutiveId", Integer, nullable=True)
    CoordinatorId: Mapped[Optional[int]] = mapped_column("CoordinatorId", Integer, nullable=True)
    FranchiseId: Mapped[Optional[int]] = mapped_column("FranchiseId", Integer, nullable=True)
    BranchId: Mapped[Optional[int]] = mapped_column("BranchId", Integer, nullable=True)
    UserId: Mapped[Optional[int]] = mapped_column("UserId", Integer, nullable=True)
    BankId: Mapped[Optional[int]] = mapped_column("BankId", Integer, nullable=True)
    BankBranch: Mapped[Optional[str]] = mapped_column("BankBranch", String(100), nullable=True)
    Ifsc_code: Mapped[Optional[str]] = mapped_column("Ifsc_code", String(50), nullable=True)
    accountNo: Mapped[Optional[str]] = mapped_column("accountNo", String(50), nullable=True)
    IsActive: Mapped[int] = mapped_column("IsActive", Integer, nullable=False, default=1)
    kyc_status: Mapped[str] = mapped_column("kyc_status", String(20), nullable=False, default="PENDING")
    kyc_remarks: Mapped[Optional[str]] = mapped_column("kyc_remarks", String(255), nullable=True)
    CreateDate: Mapped[Optional[datetime]] = mapped_column("CreateDate", DateTime, nullable=True, default=datetime.utcnow)
    CreateUser: Mapped[Optional[str]] = mapped_column("CreateUser", String(100), nullable=True)
    UpdateDate: Mapped[Optional[datetime]] = mapped_column("UpdateDate", DateTime, nullable=True, onupdate=datetime.utcnow)
    UpdateUser: Mapped[Optional[str]] = mapped_column("UpdateUser", String(100), nullable=True)
    isdeleted: Mapped[str] = mapped_column("isdeleted", String(10), nullable=False, default="0")

    @property
    def full_name(self) -> str:
        parts = [p for p in [self.AgentFName, self.AgentMName, self.AgentLName] if p]
        return " ".join(parts) if parts else (self.NickName or self.AgentCode or "")

    @property
    def is_active(self) -> bool:
        return self.IsActive == 1 and str(self.isdeleted).strip() != "1"


class Franchise(Base):
    """
    Franchise Partner & Hierarchy Model.
    Physical Table: tbl_franchise
    Physical PK: FranchiseId
    """
    __tablename__ = "tbl_franchise"
    __table_args__ = (
        Index("ix_tbl_franchise_FranCode", "FranCode"),
        Index("ix_tbl_franchise_BranchId", "BranchId"),
        Index("ix_tbl_franchise_ParentFranchiseId", "ParentFranchiseId"),
        Index("ix_tbl_franchise_isdeleted", "isdeleted"),
        {
            "mysql_charset": "utf8",
            "mysql_collate": "utf8_general_ci",
            "mysql_row_format": "DYNAMIC",
        },
    )

    FranchiseId: Mapped[int] = mapped_column("FranchiseId", Integer, primary_key=True, autoincrement=True)
    UserName: Mapped[Optional[str]] = mapped_column("UserName", String(255), nullable=True)
    UserPassword: Mapped[Optional[str]] = mapped_column("UserPassword", String(255), nullable=True)
    initial: Mapped[Optional[str]] = mapped_column("initial", String(20), nullable=True)
    FranFName: Mapped[Optional[str]] = mapped_column("FranFName", String(100), nullable=True)
    FranMName: Mapped[Optional[str]] = mapped_column("FranMName", String(100), nullable=True)
    FranLName: Mapped[Optional[str]] = mapped_column("FranLName", String(100), nullable=True)
    FranCode: Mapped[Optional[str]] = mapped_column("FranCode", String(50), nullable=True)
    PerAddrLine1: Mapped[Optional[str]] = mapped_column("PerAddrLine1", String(255), nullable=True)
    PerAddrLine2: Mapped[Optional[str]] = mapped_column("PerAddrLine2", String(255), nullable=True)
    PerTalukaId: Mapped[Optional[int]] = mapped_column("PerTalukaId", Integer, nullable=True)
    PerDistrictId: Mapped[Optional[int]] = mapped_column("PerDistrictId", Integer, nullable=True)
    PerStateId: Mapped[Optional[int]] = mapped_column("PerStateId", Integer, nullable=True)
    PerPinCode: Mapped[Optional[str]] = mapped_column("PerPinCode", String(20), nullable=True)
    MoblieNo1: Mapped[Optional[str]] = mapped_column("MoblieNo1", String(50), nullable=True)
    MoblieNo2: Mapped[Optional[str]] = mapped_column("MoblieNo2", String(50), nullable=True)
    Gender: Mapped[Optional[str]] = mapped_column("Gender", String(20), nullable=True)
    MaritalStatus: Mapped[Optional[str]] = mapped_column("MaritalStatus", String(20), nullable=True)
    PAN_No: Mapped[Optional[str]] = mapped_column("PAN_No", String(20), nullable=True)
    AadharNo: Mapped[Optional[str]] = mapped_column("AadharNo", String(20), nullable=True)
    BankId: Mapped[Optional[int]] = mapped_column("BankId", Integer, nullable=True)
    NominieeName: Mapped[Optional[str]] = mapped_column("NominieeName", String(100), nullable=True)
    Bank_branch: Mapped[Optional[str]] = mapped_column("Bank_branch", String(100), nullable=True)
    Ifsc_code: Mapped[Optional[str]] = mapped_column("Ifsc_code", String(50), nullable=True)
    accountNo: Mapped[Optional[str]] = mapped_column("accountNo", String(50), nullable=True)
    DateOfBirth: Mapped[Optional[date]] = mapped_column("DateOfBirth", Date, nullable=True)
    EmailId: Mapped[Optional[str]] = mapped_column("EmailId", String(100), nullable=True)
    BranchId: Mapped[Optional[int]] = mapped_column("BranchId", Integer, nullable=True)
    ParentFranchiseId: Mapped[Optional[int]] = mapped_column("ParentFranchiseId", Integer, nullable=True)
    CoordinatorId: Mapped[Optional[int]] = mapped_column("CoordinatorId", Integer, nullable=True)
    QuotationCo_Id: Mapped[Optional[int]] = mapped_column("QuotationCo_Id", Integer, nullable=True)
    InspectionCo_Id: Mapped[Optional[int]] = mapped_column("InspectionCo_Id", Integer, nullable=True)
    EndrosmentCo_Id: Mapped[Optional[int]] = mapped_column("EndrosmentCo_Id", Integer, nullable=True)
    UserRoleId: Mapped[Optional[int]] = mapped_column("UserRoleId", Integer, nullable=True)
    CreateDate: Mapped[Optional[datetime]] = mapped_column("CreateDate", DateTime, nullable=True, default=datetime.utcnow)
    CreateUser: Mapped[Optional[str]] = mapped_column("CreateUser", String(100), nullable=True)
    UpdateDate: Mapped[Optional[datetime]] = mapped_column("UpdateDate", DateTime, nullable=True, onupdate=datetime.utcnow)
    UpdateUser: Mapped[Optional[str]] = mapped_column("UpdateUser", String(100), nullable=True)
    isdeleted: Mapped[str] = mapped_column("isdeleted", String(10), nullable=False, default="0")

    @property
    def full_name(self) -> str:
        parts = [p for p in [self.FranFName, self.FranMName, self.FranLName] if p]
        return " ".join(parts) if parts else (self.FranCode or self.UserName or "")

    @property
    def is_active(self) -> bool:
        return str(self.isdeleted).strip() != "1"
