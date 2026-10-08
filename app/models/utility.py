"""
SQLAlchemy 2.0 Declarative Models for Phase 15B — Operational Staging & Utilities.
Physical Tables:
- tbl_idvrequest (Special Underwriter IDV Override Approval Queue)
- tbl_healthmember (Non-Motor Health Family Member Grid)
- tbl_importagentpolicy (Bulk Excel Policy MIS Staging Table)
"""
from datetime import datetime, date
from decimal import Decimal
from typing import Optional
from sqlalchemy import Integer, String, Text, DateTime, Date, Numeric, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class IDVRequest(Base):
    """
    Special IDV Override Approval Queue Model.
    Physical Table: tbl_idvrequest
    Physical PK: IDVRequestId
    """
    __tablename__ = "tbl_idvrequest"
    __table_args__ = (
        Index("ix_tbl_idvrequest_SalesExId", "SalesExId"),
        Index("ix_tbl_idvrequest_Status", "Status"),
        Index("ix_tbl_idvrequest_RegistrationNo", "RegistrationNo"),
        Index("ix_tbl_idvrequest_RequestDate", "RequestDate"),
        Index("ix_tbl_idvrequest_isdeleted", "isdeleted"),
        {
            "mysql_charset": "utf8",
            "mysql_collate": "utf8_general_ci",
            "mysql_row_format": "DYNAMIC",
        },
    )

    IDVRequestId: Mapped[int] = mapped_column("IDVRequestId", Integer, primary_key=True, autoincrement=True)
    RequestDate: Mapped[datetime] = mapped_column("RequestDate", DateTime, nullable=False, default=datetime.utcnow)
    InsuranceCompanyId: Mapped[Optional[int]] = mapped_column("InsuranceCompanyId", Integer, nullable=True)
    VehicleTypeId: Mapped[Optional[int]] = mapped_column("VehicleTypeId", Integer, nullable=True)
    PolicyTypeId: Mapped[Optional[str]] = mapped_column("PolicyTypeId", String(50), nullable=True)
    VehicleMake: Mapped[Optional[str]] = mapped_column("VehicleMake", String(100), nullable=True)
    VehicleModel: Mapped[Optional[str]] = mapped_column("VehicleModel", String(100), nullable=True)
    RegistrationNo: Mapped[Optional[str]] = mapped_column("RegistrationNo", String(50), nullable=True)
    Passyear: Mapped[Optional[str]] = mapped_column("Passyear", String(20), nullable=True)
    RequestedIDV: Mapped[Decimal] = mapped_column("RequestedIDV", Numeric(18, 2), nullable=False)
    ApprovedIDV: Mapped[Optional[Decimal]] = mapped_column("ApprovedIDV", Numeric(18, 2), nullable=True)
    SalesExId: Mapped[Optional[int]] = mapped_column("SalesExId", Integer, nullable=True)
    RequestedBy: Mapped[Optional[str]] = mapped_column("RequestedBy", String(100), nullable=True)
    ApprovedBy: Mapped[Optional[str]] = mapped_column("ApprovedBy", String(100), nullable=True)
    Status: Mapped[str] = mapped_column("Status", String(50), nullable=False, default="PENDING")  # PENDING, APPROVED, REJECTED
    Note: Mapped[Optional[str]] = mapped_column("Note", Text, nullable=True)
    ApprovedRemark: Mapped[Optional[str]] = mapped_column("ApprovedRemark", Text, nullable=True)
    CreateDate: Mapped[datetime] = mapped_column("CreateDate", DateTime, nullable=False, default=datetime.utcnow)
    UpdateDate: Mapped[Optional[datetime]] = mapped_column("UpdateDate", DateTime, nullable=True, onupdate=datetime.utcnow)
    isdeleted: Mapped[str] = mapped_column("isdeleted", String(10), nullable=False, default="0")

    @property
    def is_active(self) -> bool:
        return str(self.isdeleted).strip() != "1"


class HealthMember(Base):
    """
    Non-Motor Health Insurance Family Member Grid Model.
    Physical Table: tbl_healthmember
    Physical PK: MemberId
    """
    __tablename__ = "tbl_healthmember"
    __table_args__ = (
        Index("ix_tbl_healthmember_TransanctionId", "TransanctionId"),
        Index("ix_tbl_healthmember_CustomerId", "CustomerId"),
        Index("ix_tbl_healthmember_Status", "Status"),
        Index("ix_tbl_healthmember_isdeleted", "isdeleted"),
        {
            "mysql_charset": "utf8",
            "mysql_collate": "utf8_general_ci",
            "mysql_row_format": "DYNAMIC",
        },
    )

    MemberId: Mapped[int] = mapped_column("MemberId", Integer, primary_key=True, autoincrement=True)
    TransanctionId: Mapped[Optional[int]] = mapped_column("TransanctionId", Integer, nullable=True)
    CustomerId: Mapped[Optional[int]] = mapped_column("CustomerId", Integer, nullable=True)
    MemberName: Mapped[str] = mapped_column("MemberName", String(255), nullable=False)
    Relationship: Mapped[str] = mapped_column("Relationship", String(50), nullable=False)  # SELF, SPOUSE, SON, DAUGHTER, FATHER, MOTHER
    Gender: Mapped[str] = mapped_column("Gender", String(20), nullable=False)  # MALE, FEMALE, OTHER
    DOB: Mapped[Optional[date]] = mapped_column("DOB", Date, nullable=True)
    Age: Mapped[int] = mapped_column("Age", Integer, nullable=False)
    SumInsured: Mapped[Decimal] = mapped_column("SumInsured", Numeric(18, 2), nullable=False)
    PreExistingDisease: Mapped[Optional[str]] = mapped_column("PreExistingDisease", String(500), nullable=True)
    NomineeName: Mapped[Optional[str]] = mapped_column("NomineeName", String(255), nullable=True)
    Status: Mapped[str] = mapped_column("Status", String(50), nullable=False, default="ACTIVE")
    CreateDate: Mapped[datetime] = mapped_column("CreateDate", DateTime, nullable=False, default=datetime.utcnow)
    CreateUser: Mapped[Optional[str]] = mapped_column("CreateUser", String(100), nullable=True)
    UpdateDate: Mapped[Optional[datetime]] = mapped_column("UpdateDate", DateTime, nullable=True, onupdate=datetime.utcnow)
    UpdateUser: Mapped[Optional[str]] = mapped_column("UpdateUser", String(100), nullable=True)
    isdeleted: Mapped[str] = mapped_column("isdeleted", String(10), nullable=False, default="0")

    @property
    def is_active(self) -> bool:
        return str(self.isdeleted).strip() != "1"


class ImportAgentPolicy(Base):
    """
    Bulk Excel/CSV Policy MIS Staging Table Model.
    Physical Table: tbl_importagentpolicy
    Physical PK: Id
    """
    __tablename__ = "tbl_importagentpolicy"
    __table_args__ = (
        Index("ix_tbl_importagentpolicy_BatchId", "BatchId"),
        Index("ix_tbl_importagentpolicy_PolicyNumber", "PolicyNumber"),
        Index("ix_tbl_importagentpolicy_IsProcess", "IsProcess"),
        Index("ix_tbl_importagentpolicy_isdeleted", "isdeleted"),
        {
            "mysql_charset": "utf8",
            "mysql_collate": "utf8_general_ci",
            "mysql_row_format": "DYNAMIC",
        },
    )

    Id: Mapped[int] = mapped_column("Id", Integer, primary_key=True, autoincrement=True)
    DateOfInsurance: Mapped[Optional[str]] = mapped_column("DateOfInsurance", String(50), nullable=True)
    BrokerName: Mapped[Optional[str]] = mapped_column("BrokerName", String(255), nullable=True)
    ClientName: Mapped[Optional[str]] = mapped_column("ClientName", String(255), nullable=True)
    VehicleType: Mapped[Optional[str]] = mapped_column("VehicleType", String(100), nullable=True)
    VehicleNumber: Mapped[Optional[str]] = mapped_column("VehicleNumber", String(100), nullable=True)
    PolicyNumber: Mapped[Optional[str]] = mapped_column("PolicyNumber", String(100), nullable=True)
    Segments: Mapped[Optional[str]] = mapped_column("Segments", String(100), nullable=True)
    InsuranceCompany: Mapped[Optional[str]] = mapped_column("InsuranceCompany", String(255), nullable=True)
    IssuingID: Mapped[Optional[str]] = mapped_column("IssuingID", String(100), nullable=True)
    InceptionDate: Mapped[Optional[str]] = mapped_column("InceptionDate", String(50), nullable=True)
    ExpiryDate: Mapped[Optional[str]] = mapped_column("ExpiryDate", String(50), nullable=True)
    GrossAmount: Mapped[Optional[Decimal]] = mapped_column("GrossAmount", Numeric(18, 2), nullable=True)
    NetAmount: Mapped[Optional[Decimal]] = mapped_column("NetAmount", Numeric(18, 2), nullable=True)
    ODPremium: Mapped[Optional[Decimal]] = mapped_column("ODPremium", Numeric(18, 2), nullable=True)
    TPPremium: Mapped[Optional[Decimal]] = mapped_column("TPPremium", Numeric(18, 2), nullable=True)
    BrokerReceivedPct: Mapped[Optional[Decimal]] = mapped_column("BrokerReceivedPct", Numeric(10, 2), nullable=True)
    BrokerPayout: Mapped[Optional[Decimal]] = mapped_column("BrokerPayout", Numeric(18, 2), nullable=True)
    PolicyType: Mapped[Optional[str]] = mapped_column("PolicyType", String(100), nullable=True)
    FuelType: Mapped[Optional[str]] = mapped_column("FuelType", String(100), nullable=True)
    MfgDate: Mapped[Optional[str]] = mapped_column("MfgDate", String(50), nullable=True)
    GVW: Mapped[Optional[str]] = mapped_column("GVW", String(50), nullable=True)
    ProductType: Mapped[Optional[str]] = mapped_column("ProductType", String(100), nullable=True)
    CreatedBy: Mapped[Optional[str]] = mapped_column("CreatedBy", String(100), nullable=True)
    CreatedDate: Mapped[datetime] = mapped_column("CreatedDate", DateTime, nullable=False, default=datetime.utcnow)
    IsProcess: Mapped[int] = mapped_column("IsProcess", Integer, nullable=False, default=0)
    Remark: Mapped[Optional[str]] = mapped_column("Remark", String(1000), nullable=True)
    FinancialYear: Mapped[Optional[str]] = mapped_column("FinancialYear", String(50), nullable=True)
    BatchId: Mapped[Optional[str]] = mapped_column("BatchId", String(100), nullable=True)
    isdeleted: Mapped[str] = mapped_column("isdeleted", String(10), nullable=False, default="0")

    @property
    def is_active(self) -> bool:
        return str(self.isdeleted).strip() != "1"
