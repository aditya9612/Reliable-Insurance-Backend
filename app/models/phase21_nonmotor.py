"""
SQLAlchemy 2.0 Declarative Models for Phase 21 — Non-Motor Commercial Insurance Lines of Business & Operations.
Physical Tables Added:
1. tbl_nonmotorclass (Commercial Lines Product Classes — Fire, Marine, Engineering, Health, Misc, Liability)
2. tbl_nonmotorproduct (Non-Motor Commercial Products Catalog)
3. tbl_nonmotorbusinesstype (Non-Motor Business Classifications — New, Renewal, Rollover, Endorsement)
4. tbl_nonmotordocumenttype (Non-Motor Underwriting & Verification Required Document Types)
5. tbl_nonmotorendorsmenttype (Non-Motor Policy Endorsement Main Classifications)
6. tbl_nonmotorendorsmentsubtype (Non-Motor Policy Endorsement Specific Sub-Classifications)
7. tbl_nonmotorinsurancetype (Non-Motor Insurer Policy Hierarchy Types)
8. tbl_nonmotorinsurancesubtype (Non-Motor Insurer Policy Hierarchy Sub-Types)
9. tbl_nonmotortypeofinsurancesubtype (Non-Motor Insurer Policy Detailed Sub-Types)
10. tbl_nonmotorcommission (Non-Motor Tiered Agent, Broker & Franchise Commission Grid Matrix)
11. tbl_nonmotortransaction (Non-Motor Policy & Proposal Booking Transactions Register)
"""
from datetime import datetime, date
from decimal import Decimal
from typing import Optional
from sqlalchemy import Integer, String, DateTime, Date, Numeric, Text, Index, text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class NonMotorClass(Base):
    """
    Commercial Product Class Master Model.
    Physical Table: tbl_nonmotorclass
    Physical PK: ClassId
    Legacy Reference: BLL_Class, DAL_Class, API_Class, adm_NonMotorProduct.aspx.cs, Sp_Class
    """
    __tablename__ = "tbl_nonmotorclass"
    __table_args__ = (
        Index("ix_tbl_nonmotorclass_Class", "Class"),
        Index("ix_tbl_nonmotorclass_IsActive", "IsActive"),
        {
            "mysql_charset": "utf8",
            "mysql_collate": "utf8_general_ci",
            "mysql_row_format": "DYNAMIC",
        },
    )

    ClassId: Mapped[int] = mapped_column("ClassId", Integer, primary_key=True, autoincrement=True)
    Class: Mapped[str] = mapped_column("Class", String(255), nullable=False)
    IsActive: Mapped[int] = mapped_column("IsActive", Integer, nullable=False, server_default=text("1"))
    CreatedDate: Mapped[datetime] = mapped_column(
        "CreatedDate", DateTime, nullable=False, default=datetime.utcnow
    )
    CreatedBy: Mapped[Optional[str]] = mapped_column("CreatedBy", String(100), nullable=True)
    UpdatedDate: Mapped[Optional[datetime]] = mapped_column(
        "UpdatedDate", DateTime, nullable=True, onupdate=datetime.utcnow
    )
    UpdatedBy: Mapped[Optional[str]] = mapped_column("UpdatedBy", String(100), nullable=True)

    products: Mapped[list["NonMotorProduct"]] = relationship(
        "NonMotorProduct", back_populates="product_class", cascade="all, delete-orphan"
    )


class NonMotorProduct(Base):
    """
    Non-Motor Commercial Product Master Model.
    Physical Table: tbl_nonmotorproduct
    Physical PK: NonMotorProductId
    Legacy Reference: BLL_NonMotorProductType, DAL_NonMotorProduct, API_NonMotorProduct, adm_NonMotorProduct.aspx.cs, Sp_nonmotarproduct
    """
    __tablename__ = "tbl_nonmotorproduct"
    __table_args__ = (
        Index("ix_tbl_nonmotorproduct_ClassId", "ClassId"),
        Index("ix_tbl_nonmotorproduct_ProductType", "ProductType"),
        Index("ix_tbl_nonmotorproduct_IsActive", "IsActive"),
        {
            "mysql_charset": "utf8",
            "mysql_collate": "utf8_general_ci",
            "mysql_row_format": "DYNAMIC",
        },
    )

    NonMotorProductId: Mapped[int] = mapped_column("NonMotorProductId", Integer, primary_key=True, autoincrement=True)
    ClassId: Mapped[int] = mapped_column("ClassId", Integer, ForeignKey("tbl_nonmotorclass.ClassId"), nullable=False)
    ProductType: Mapped[str] = mapped_column("ProductType", String(255), nullable=False)
    ProductCode: Mapped[Optional[str]] = mapped_column("ProductCode", String(100), nullable=True)
    IsActive: Mapped[int] = mapped_column("IsActive", Integer, nullable=False, server_default=text("1"))
    CreatedDate: Mapped[datetime] = mapped_column(
        "CreatedDate", DateTime, nullable=False, default=datetime.utcnow
    )
    CreatedBy: Mapped[Optional[str]] = mapped_column("CreatedBy", String(100), nullable=True)
    UpdatedDate: Mapped[Optional[datetime]] = mapped_column(
        "UpdatedDate", DateTime, nullable=True, onupdate=datetime.utcnow
    )
    UpdatedBy: Mapped[Optional[str]] = mapped_column("UpdatedBy", String(100), nullable=True)

    product_class: Mapped["NonMotorClass"] = relationship("NonMotorClass", back_populates="products")


class NonMotorBusinessType(Base):
    """
    Non-Motor Business Type Master Model.
    Physical Table: tbl_nonmotorbusinesstype
    Physical PK: NonBusinessId
    Legacy Reference: BLL_NonMotorBusiness, DAL_NonMotorBusinessType, API_BusinessType, adm_NonmotarBusinessType.aspx.cs, Sp_nonmotarbusinesstypeMaster
    """
    __tablename__ = "tbl_nonmotorbusinesstype"
    __table_args__ = (
        Index("ix_tbl_nonmotorbusinesstype_BusinessType", "BusinessType"),
        Index("ix_tbl_nonmotorbusinesstype_IsActive", "IsActive"),
        {
            "mysql_charset": "utf8",
            "mysql_collate": "utf8_general_ci",
            "mysql_row_format": "DYNAMIC",
        },
    )

    NonBusinessId: Mapped[int] = mapped_column("NonBusinessId", Integer, primary_key=True, autoincrement=True)
    BusinessType: Mapped[str] = mapped_column("BusinessType", String(255), nullable=False)
    IsActive: Mapped[int] = mapped_column("IsActive", Integer, nullable=False, server_default=text("1"))
    CreatedDate: Mapped[datetime] = mapped_column(
        "CreatedDate", DateTime, nullable=False, default=datetime.utcnow
    )
    CreatedBy: Mapped[Optional[str]] = mapped_column("CreatedBy", String(100), nullable=True)
    UpdatedDate: Mapped[Optional[datetime]] = mapped_column(
        "UpdatedDate", DateTime, nullable=True, onupdate=datetime.utcnow
    )
    UpdatedBy: Mapped[Optional[str]] = mapped_column("UpdatedBy", String(100), nullable=True)


class NonMotorDocumentType(Base):
    """
    Non-Motor Document Type Master Model.
    Physical Table: tbl_nonmotordocumenttype
    Physical PK: NonDocumentTypeId
    Legacy Reference: BLL_NonMotorDocument, DAL_NonMotorDocumentType, API_Document_type, adm_NonMotorDocumentType.aspx.cs, Sp_nonmotardocumenttype
    """
    __tablename__ = "tbl_nonmotordocumenttype"
    __table_args__ = (
        Index("ix_tbl_nonmotordocumenttype_DocumentType", "DocumentType"),
        Index("ix_tbl_nonmotordocumenttype_IsActive", "IsActive"),
        {
            "mysql_charset": "utf8",
            "mysql_collate": "utf8_general_ci",
            "mysql_row_format": "DYNAMIC",
        },
    )

    NonDocumentTypeId: Mapped[int] = mapped_column("NonDocumentTypeId", Integer, primary_key=True, autoincrement=True)
    DocumentType: Mapped[str] = mapped_column("DocumentType", String(255), nullable=False)
    IsActive: Mapped[int] = mapped_column("IsActive", Integer, nullable=False, server_default=text("1"))
    CreatedDate: Mapped[datetime] = mapped_column(
        "CreatedDate", DateTime, nullable=False, default=datetime.utcnow
    )
    CreatedBy: Mapped[Optional[str]] = mapped_column("CreatedBy", String(100), nullable=True)
    UpdatedDate: Mapped[Optional[datetime]] = mapped_column(
        "UpdatedDate", DateTime, nullable=True, onupdate=datetime.utcnow
    )
    UpdatedBy: Mapped[Optional[str]] = mapped_column("UpdatedBy", String(100), nullable=True)


class NonMotorEndorsementType(Base):
    """
    Non-Motor Endorsement Type Master Model.
    Physical Table: tbl_nonmotorendorsmenttype
    Physical PK: NonEndorsementId
    Legacy Reference: BLL_NonMotorEndorsmentType, DAL_NonMotorEndorsmentType, API_Endorsement, Adm_NonMotorEndorsmentType.aspx.cs, Sp_NonMotorEndorsmentType
    """
    __tablename__ = "tbl_nonmotorendorsmenttype"
    __table_args__ = (
        Index("ix_tbl_nonmotorendorsmenttype_EndorsementType", "EndorsementType"),
        Index("ix_tbl_nonmotorendorsmenttype_IsActive", "IsActive"),
        {
            "mysql_charset": "utf8",
            "mysql_collate": "utf8_general_ci",
            "mysql_row_format": "DYNAMIC",
        },
    )

    NonEndorsementId: Mapped[int] = mapped_column("NonEndorsementId", Integer, primary_key=True, autoincrement=True)
    EndorsementType: Mapped[str] = mapped_column("EndorsementType", String(255), nullable=False)
    IsActive: Mapped[int] = mapped_column("IsActive", Integer, nullable=False, server_default=text("1"))
    CreatedDate: Mapped[datetime] = mapped_column(
        "CreatedDate", DateTime, nullable=False, default=datetime.utcnow
    )
    CreatedBy: Mapped[Optional[str]] = mapped_column("CreatedBy", String(100), nullable=True)
    UpdatedDate: Mapped[Optional[datetime]] = mapped_column(
        "UpdatedDate", DateTime, nullable=True, onupdate=datetime.utcnow
    )
    UpdatedBy: Mapped[Optional[str]] = mapped_column("UpdatedBy", String(100), nullable=True)

    sub_types: Mapped[list["NonMotorEndorsementSubType"]] = relationship(
        "NonMotorEndorsementSubType", back_populates="endorsement_type", cascade="all, delete-orphan"
    )


class NonMotorEndorsementSubType(Base):
    """
    Non-Motor Endorsement Sub Type Master Model.
    Physical Table: tbl_nonmotorendorsmentsubtype
    Physical PK: NonEndorsesubId
    Legacy Reference: BLL_NonMotorEndorsmentSubType, DAL_NonMotorEndorsmentSubType, API_NonMotorEndorsmentSubType, Adm_NonMotorendorsmentSubType.aspx.cs, Sp_nonmotarendorssubType
    """
    __tablename__ = "tbl_nonmotorendorsmentsubtype"
    __table_args__ = (
        Index("ix_tbl_nonmotorendorsmentsubtype_NonEndorsementId", "NonEndorsementId"),
        Index("ix_tbl_nonmotorendorsmentsubtype_EndorsementSubType", "EndorsementSubType"),
        Index("ix_tbl_nonmotorendorsmentsubtype_IsActive", "IsActive"),
        {
            "mysql_charset": "utf8",
            "mysql_collate": "utf8_general_ci",
            "mysql_row_format": "DYNAMIC",
        },
    )

    NonEndorsesubId: Mapped[int] = mapped_column("NonEndorsesubId", Integer, primary_key=True, autoincrement=True)
    NonEndorsementId: Mapped[int] = mapped_column(
        "NonEndorsementId", Integer, ForeignKey("tbl_nonmotorendorsmenttype.NonEndorsementId"), nullable=False
    )
    EndorsementSubType: Mapped[str] = mapped_column("EndorsementSubType", String(255), nullable=False)
    IsActive: Mapped[int] = mapped_column("IsActive", Integer, nullable=False, server_default=text("1"))
    CreatedDate: Mapped[datetime] = mapped_column(
        "CreatedDate", DateTime, nullable=False, default=datetime.utcnow
    )
    CreatedBy: Mapped[Optional[str]] = mapped_column("CreatedBy", String(100), nullable=True)
    UpdatedDate: Mapped[Optional[datetime]] = mapped_column(
        "UpdatedDate", DateTime, nullable=True, onupdate=datetime.utcnow
    )
    UpdatedBy: Mapped[Optional[str]] = mapped_column("UpdatedBy", String(100), nullable=True)

    endorsement_type: Mapped["NonMotorEndorsementType"] = relationship(
        "NonMotorEndorsementType", back_populates="sub_types"
    )


class NonMotorInsuranceType(Base):
    """
    Non-Motor Insurance Type Master Model.
    Physical Table: tbl_nonmotorinsurancetype
    Physical PK: InsuranceTypeId
    Legacy Reference: BLL_NonMotor, DAL_NonMotor, API_nonmotorinsurancetype, NonMotorCommissionGrid.aspx.cs, sp_NonMotorSelectInsuranceTypeAndSubType
    """
    __tablename__ = "tbl_nonmotorinsurancetype"
    __table_args__ = (
        Index("ix_tbl_nonmotorinsurancetype_CompanyId", "InsuranceCompanyId"),
        Index("ix_tbl_nonmotorinsurancetype_Type", "InsuranceType"),
        Index("ix_tbl_nonmotorinsurancetype_IsDeleted", "IsDeleted"),
        {
            "mysql_charset": "utf8",
            "mysql_collate": "utf8_general_ci",
            "mysql_row_format": "DYNAMIC",
        },
    )

    InsuranceTypeId: Mapped[int] = mapped_column("InsuranceTypeId", Integer, primary_key=True, autoincrement=True)
    InsuranceType: Mapped[str] = mapped_column("InsuranceType", String(255), nullable=False)
    InsuranceCompanyId: Mapped[int] = mapped_column("InsuranceCompanyId", Integer, nullable=False)
    IsDeleted: Mapped[int] = mapped_column("IsDeleted", Integer, nullable=False, server_default=text("0"))
    Flag: Mapped[Optional[str]] = mapped_column("Flag", String(50), nullable=True)
    CreatedDate: Mapped[datetime] = mapped_column(
        "CreatedDate", DateTime, nullable=False, default=datetime.utcnow
    )
    CreatedBy: Mapped[Optional[str]] = mapped_column("CreatedBy", String(100), nullable=True)

    sub_types: Mapped[list["NonMotorInsuranceSubType"]] = relationship(
        "NonMotorInsuranceSubType", back_populates="insurance_type", cascade="all, delete-orphan"
    )


class NonMotorInsuranceSubType(Base):
    """
    Non-Motor Insurance Sub-Type Master Model.
    Physical Table: tbl_nonmotorinsurancesubtype
    Physical PK: InsuranceSubTypeId
    Legacy Reference: BLL_NonMotor, DAL_NonMotor, API_nonmotorinsurancesubtype, NonMotorCommissionGrid.aspx.cs, sp_NonMotorSelectInsuranceTypeAndSubType
    """
    __tablename__ = "tbl_nonmotorinsurancesubtype"
    __table_args__ = (
        Index("ix_tbl_nonmotorinsurancesubtype_TypeId", "InsuranceTypeId"),
        Index("ix_tbl_nonmotorinsurancesubtype_SubType", "InsuranceSubType"),
        Index("ix_tbl_nonmotorinsurancesubtype_IsDeleted", "IsDeleted"),
        {
            "mysql_charset": "utf8",
            "mysql_collate": "utf8_general_ci",
            "mysql_row_format": "DYNAMIC",
        },
    )

    InsuranceSubTypeId: Mapped[int] = mapped_column("InsuranceSubTypeId", Integer, primary_key=True, autoincrement=True)
    InsuranceSubType: Mapped[str] = mapped_column("InsuranceSubType", String(255), nullable=False)
    InsuranceTypeId: Mapped[int] = mapped_column(
        "InsuranceTypeId", Integer, ForeignKey("tbl_nonmotorinsurancetype.InsuranceTypeId"), nullable=False
    )
    IsDeleted: Mapped[int] = mapped_column("IsDeleted", Integer, nullable=False, server_default=text("0"))
    Flag: Mapped[Optional[str]] = mapped_column("Flag", String(50), nullable=True)
    CreatedDate: Mapped[datetime] = mapped_column(
        "CreatedDate", DateTime, nullable=False, default=datetime.utcnow
    )
    CreatedBy: Mapped[Optional[str]] = mapped_column("CreatedBy", String(100), nullable=True)

    insurance_type: Mapped["NonMotorInsuranceType"] = relationship(
        "NonMotorInsuranceType", back_populates="sub_types"
    )


class NonMotorTypeOfInsuranceSubType(Base):
    """
    Non-Motor Detailed Type of Sub-Type Model.
    Physical Table: tbl_nonmotortypeofinsurancesubtype
    Physical PK: TypeSubTypeId
    Legacy Reference: BLL_NonMotor, DAL_NonMotor, API_nonmotortypeofinsurancesubtype, NonMotorCommissionGrid.aspx.cs
    """
    __tablename__ = "tbl_nonmotortypeofinsurancesubtype"
    __table_args__ = (
        Index("ix_tbl_nonmotortypeofsub_TypeId", "InsuranceTypeId"),
        Index("ix_tbl_nonmotortypeofsub_SubTypeId", "InsuranceSubTypeId"),
        Index("ix_tbl_nonmotortypeofsub_IsDeleted", "IsDeleted"),
        {
            "mysql_charset": "utf8",
            "mysql_collate": "utf8_general_ci",
            "mysql_row_format": "DYNAMIC",
        },
    )

    TypeSubTypeId: Mapped[int] = mapped_column("TypeSubTypeId", Integer, primary_key=True, autoincrement=True)
    TypeOfSubType: Mapped[str] = mapped_column("TypeOfSubType", String(255), nullable=False)
    InsuranceTypeId: Mapped[int] = mapped_column("InsuranceTypeId", Integer, nullable=False)
    InsuranceSubTypeId: Mapped[int] = mapped_column("InsuranceSubTypeId", Integer, nullable=False)
    IsDeleted: Mapped[int] = mapped_column("IsDeleted", Integer, nullable=False, server_default=text("0"))
    Flag: Mapped[Optional[str]] = mapped_column("Flag", String(50), nullable=True)
    CreatedDate: Mapped[datetime] = mapped_column(
        "CreatedDate", DateTime, nullable=False, default=datetime.utcnow
    )
    CreatedBy: Mapped[Optional[str]] = mapped_column("CreatedBy", String(100), nullable=True)


class NonMotorCommission(Base):
    """
    Non-Motor Tiered Commission Grid Model.
    Physical Table: tbl_nonmotorcommission
    Physical PK: NonMotorCommId
    Legacy Reference: BLL_NonMotor, DAL_NonMotor, API_NonMotorCommission, NonMotorCommissionGrid.aspx.cs, sp_NonMotorInsertCommission
    """
    __tablename__ = "tbl_nonmotorcommission"
    __table_args__ = (
        Index("ix_tbl_nmcomm_company", "InsuranceCompanyId"),
        Index("ix_tbl_nmcomm_ref", "ReferanceId", "ReferenceType"),
        Index("ix_tbl_nmcomm_type_sub", "InsuranceTypeId", "InsuranceSubTypeId"),
        Index("ix_tbl_nmcomm_valid", "ValidFromDate"),
        {
            "mysql_charset": "utf8",
            "mysql_collate": "utf8_general_ci",
            "mysql_row_format": "DYNAMIC",
        },
    )

    NonMotorCommId: Mapped[int] = mapped_column("NonMotorCommId", Integer, primary_key=True, autoincrement=True)
    InsuranceCompanyId: Mapped[int] = mapped_column("InsuranceCompanyId", Integer, nullable=False)
    InsuranceTypeId: Mapped[int] = mapped_column("InsuranceTypeId", Integer, nullable=False)
    InsuranceSubTypeId: Mapped[int] = mapped_column("InsuranceSubTypeId", Integer, nullable=False, server_default=text("0"))
    TypeSubTypeId: Mapped[int] = mapped_column("TypeSubTypeId", Integer, nullable=False, server_default=text("0"))
    ReferanceId: Mapped[int] = mapped_column("ReferanceId", Integer, nullable=False)
    ReferenceType: Mapped[str] = mapped_column("ReferenceType", String(50), nullable=False)  # Agent, Broker, Franchise, Self, IE
    Commission: Mapped[Decimal] = mapped_column("Commission", Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    CommissionCalculateOn: Mapped[str] = mapped_column(
        "CommissionCalculateOn", String(100), nullable=False, server_default=text("'NetPremium'")
    )
    ValidFromDate: Mapped[date] = mapped_column("ValidFromDate", Date, nullable=False, default=date.today)
    Extra1: Mapped[Optional[str]] = mapped_column("Extra1", String(255), nullable=True)
    Extra2: Mapped[Optional[str]] = mapped_column("Extra2", String(255), nullable=True)
    IsActive: Mapped[int] = mapped_column("IsActive", Integer, nullable=False, server_default=text("1"))
    CreateDate: Mapped[datetime] = mapped_column(
        "CreateDate", DateTime, nullable=False, default=datetime.utcnow
    )
    CreateUser: Mapped[Optional[int]] = mapped_column("CreateUser", Integer, nullable=True)
    UpdateDate: Mapped[Optional[datetime]] = mapped_column(
        "UpdateDate", DateTime, nullable=True, onupdate=datetime.utcnow
    )
    UpdateUser: Mapped[Optional[int]] = mapped_column("UpdateUser", Integer, nullable=True)


class NonMotorTransaction(Base):
    """
    Non-Motor Policy Booking & Proposal Transaction Register.
    Physical Table: tbl_nonmotortransaction
    Physical PK: NonMotorTransactionId
    Legacy Reference: BLL_NonMotorTransaction, DAL_NonMotarTransaction, API_NonTransaction,
                      adm_NonMotarTransaction.aspx.cs, NonMotorPolicyDetails.aspx.cs, sp_InsertNonMotarTransaction
    """
    __tablename__ = "tbl_nonmotortransaction"
    __table_args__ = (
        Index("ix_tbl_nmtrans_inward", "InwardNo", unique=True),
        Index("ix_tbl_nmtrans_branch", "BranchId"),
        Index("ix_tbl_nmtrans_customer", "CustomerId"),
        Index("ix_tbl_nmtrans_agent", "AgentId"),
        Index("ix_tbl_nmtrans_date", "TransDate"),
        Index("ix_tbl_nmtrans_policy", "PolicyNo"),
        {
            "mysql_charset": "utf8",
            "mysql_collate": "utf8_general_ci",
            "mysql_row_format": "DYNAMIC",
        },
    )

    NonMotorTransactionId: Mapped[int] = mapped_column("NonMotorTransactionId", Integer, primary_key=True, autoincrement=True)
    InwardNo: Mapped[str] = mapped_column("InwardNo", String(100), nullable=False)
    TransDate: Mapped[datetime] = mapped_column("TransDate", DateTime, nullable=False, default=datetime.utcnow)
    BranchId: Mapped[int] = mapped_column("BranchId", Integer, nullable=False)
    CustomerId: Mapped[int] = mapped_column("CustomerId", Integer, nullable=False)
    InsuranceCompanyId: Mapped[int] = mapped_column("InsuranceCompanyId", Integer, nullable=False)
    CoverNote: Mapped[Optional[str]] = mapped_column("CoverNote", String(100), nullable=True)
    PreviousPolicyNo: Mapped[Optional[str]] = mapped_column("PreviousPolicyNo", String(100), nullable=True)
    PolicyNo: Mapped[Optional[str]] = mapped_column("PolicyNo", String(100), nullable=True)
    CnIssueDate: Mapped[Optional[datetime]] = mapped_column("CnIssueDate", DateTime, nullable=True)
    ClassId: Mapped[int] = mapped_column("ClassId", Integer, nullable=False)
    ProductTypeId: Mapped[int] = mapped_column("ProductTypeId", Integer, nullable=False)
    BusinessTypeId: Mapped[int] = mapped_column("BusinessTypeId", Integer, nullable=False)
    NonDocumentTypeId: Mapped[Optional[int]] = mapped_column("NonDocumentTypeId", Integer, nullable=True)
    NonEndorsementId: Mapped[Optional[int]] = mapped_column("NonEndorsementId", Integer, nullable=True)
    NonEndorsesubId: Mapped[Optional[int]] = mapped_column("NonEndorsesubId", Integer, nullable=True)
    EndorsementReason: Mapped[Optional[str]] = mapped_column("EndorsementReason", String(500), nullable=True)
    AgentId: Mapped[int] = mapped_column("AgentId", Integer, nullable=False)
    SalesEx_id: Mapped[Optional[int]] = mapped_column("SalesEx_id", Integer, nullable=True)
    RiskStartdate: Mapped[Optional[datetime]] = mapped_column("RiskStartdate", DateTime, nullable=True)
    ExpiryDate: Mapped[Optional[datetime]] = mapped_column("ExpiryDate", DateTime, nullable=True)
    SumInsured: Mapped[Decimal] = mapped_column("SumInsured", Numeric(18, 2), nullable=False, default=Decimal("0.00"))
    NetPermium: Mapped[Decimal] = mapped_column("NetPermium", Numeric(18, 2), nullable=False, default=Decimal("0.00"))
    ProPosalAmt: Mapped[Decimal] = mapped_column("ProPosalAmt", Numeric(18, 2), nullable=False, default=Decimal("0.00"))
    Remark: Mapped[Optional[str]] = mapped_column("Remark", Text, nullable=True)
    ReferenceType: Mapped[Optional[str]] = mapped_column("ReferenceType", String(50), nullable=True)
    ReferenceBy: Mapped[Optional[str]] = mapped_column("ReferenceBy", String(100), nullable=True)
    ReferenceRole: Mapped[Optional[str]] = mapped_column("ReferenceRole", String(100), nullable=True)
    PersonName: Mapped[Optional[str]] = mapped_column("PersonName", String(200), nullable=True)
    tat: Mapped[Optional[str]] = mapped_column("tat", String(50), nullable=True)
    AgentComm: Mapped[Decimal] = mapped_column("AgentComm", Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    AgentCommAmt: Mapped[Decimal] = mapped_column("AgentCommAmt", Numeric(18, 2), nullable=False, default=Decimal("0.00"))
    TdsAmt: Mapped[Decimal] = mapped_column("TdsAmt", Numeric(18, 2), nullable=False, default=Decimal("0.00"))
    NetCommission: Mapped[Decimal] = mapped_column("NetCommission", Numeric(18, 2), nullable=False, default=Decimal("0.00"))
    Amount: Mapped[Decimal] = mapped_column("Amount", Numeric(18, 2), nullable=False, default=Decimal("0.00"))
    TStatus: Mapped[str] = mapped_column("TStatus", String(50), nullable=False, server_default=text("'Active'"))
    CreateDate: Mapped[datetime] = mapped_column(
        "CreateDate", DateTime, nullable=False, default=datetime.utcnow
    )
    CreateUser: Mapped[Optional[str]] = mapped_column("CreateUser", String(100), nullable=True)
    UpdateDate: Mapped[Optional[datetime]] = mapped_column(
        "UpdateDate", DateTime, nullable=True, onupdate=datetime.utcnow
    )
    UpdateUser: Mapped[Optional[str]] = mapped_column("UpdateUser", String(100), nullable=True)
