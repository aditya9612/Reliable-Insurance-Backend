from decimal import Decimal
from datetime import datetime, date
from typing import Optional
from sqlalchemy import Integer, String, Text, DateTime, Date, Double, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class Customer(Base):
    """
    Customer Master Model (Policyholder / Retail Client)
    Physical Table: tbl_customer
    Physical PK: CustomerId
    Verified Column Count: 38
    Physical Foreign Keys: 0 (Enforced at application layer)
    """
    __tablename__ = "tbl_customer"
    __table_args__ = (
        Index("CustomerCode_UNIQUE", "CustomerCode", mysql_length=100, unique=True),
        Index("Fk5_ClientId_idx", "ClientId"),
        Index("Fk18_BranchId_idx", "BranchId"),
        {
            "mysql_charset": "utf8",
            "mysql_collate": "utf8_general_ci",
            "mysql_row_format": "DYNAMIC",
        },
    )

    CustomerId: Mapped[int] = mapped_column("CustomerId", Integer, primary_key=True, autoincrement=True)
    CustomerCode: Mapped[Optional[str]] = mapped_column("CustomerCode", String(255), nullable=True)
    initial: Mapped[Optional[str]] = mapped_column("initial", String(255), nullable=True)
    CustFName: Mapped[Optional[str]] = mapped_column("CustFName", String(300), nullable=True)
    CustMName: Mapped[Optional[str]] = mapped_column("CustMName", String(255), nullable=True)
    CustLName: Mapped[Optional[str]] = mapped_column("CustLName", String(255), nullable=True)
    CustomerType: Mapped[Optional[str]] = mapped_column("CustomerType", String(255), nullable=True)
    ClientId: Mapped[Optional[int]] = mapped_column("ClientId", Integer, nullable=True)
    PerAddrLine1: Mapped[Optional[str]] = mapped_column("PerAddrLine1", String(600), nullable=True)
    PerAddrLine2: Mapped[Optional[str]] = mapped_column("PerAddrLine2", String(600), nullable=True)
    PerTalukaId: Mapped[Optional[int]] = mapped_column("PerTalukaId", Integer, nullable=True)
    PerDistrictId: Mapped[Optional[int]] = mapped_column("PerDistrictId", Integer, nullable=True)
    PerStateId: Mapped[Optional[int]] = mapped_column("PerStateId", Integer, nullable=True)
    PerPinCode: Mapped[Optional[str]] = mapped_column("PerPinCode", String(255), nullable=True)
    ComAddrLine1: Mapped[Optional[str]] = mapped_column("ComAddrLine1", String(600), nullable=True)
    ComAddrLine2: Mapped[Optional[str]] = mapped_column("ComAddrLine2", String(600), nullable=True)
    ComTalukaId: Mapped[Optional[int]] = mapped_column("ComTalukaId", Integer, nullable=True)
    ComDistrictId: Mapped[Optional[int]] = mapped_column("ComDistrictId", Integer, nullable=True)
    ComStateId: Mapped[Optional[int]] = mapped_column("ComStateId", Integer, nullable=True)
    ComPinCode: Mapped[Optional[str]] = mapped_column("ComPinCode", String(255), nullable=True)
    MoblieNo1: Mapped[Optional[str]] = mapped_column("MoblieNo1", String(255), nullable=True)
    MoblieNo2: Mapped[Optional[str]] = mapped_column("MoblieNo2", String(255), nullable=True)
    Gender: Mapped[Optional[str]] = mapped_column("Gender", String(255), nullable=True)
    MaritalStatus: Mapped[Optional[str]] = mapped_column("MaritalStatus", String(255), nullable=True)
    PAN_No: Mapped[Optional[str]] = mapped_column("PAN_No", String(255), nullable=True)
    AadharNo: Mapped[Optional[str]] = mapped_column("AadharNo", String(255), nullable=True)
    DateOfBirth: Mapped[Optional[date]] = mapped_column("DateOfBirth", Date, nullable=True)
    EMailId: Mapped[Optional[str]] = mapped_column("EMailId", String(255), nullable=True)
    NomineeName: Mapped[Optional[str]] = mapped_column("NomineeName", String(255), nullable=True)
    BranchId: Mapped[Optional[int]] = mapped_column("BranchId", Integer, nullable=True)
    CreateDate: Mapped[Optional[datetime]] = mapped_column("CreateDate", DateTime, nullable=True)
    CreateUser: Mapped[Optional[str]] = mapped_column("CreateUser", String(255), nullable=True)
    UpdateDate: Mapped[Optional[datetime]] = mapped_column("UpdateDate", DateTime, nullable=True)
    UpdateUser: Mapped[Optional[str]] = mapped_column("UpdateUser", String(255), nullable=True)
    Extra1: Mapped[Optional[str]] = mapped_column("Extra1", String(255), nullable=True)
    Extra2: Mapped[Optional[str]] = mapped_column("Extra2", String(255), nullable=True)
    CompanyName: Mapped[Optional[str]] = mapped_column("CompanyName", String(255), nullable=True)
    isdeleted: Mapped[Optional[str]] = mapped_column("isdeleted", String(255), nullable=True)
