"""
SQLAlchemy 2.0 Declarative Models for Phase 6 Quotation & Rating Engine.
All models strictly preserve verified physical MySQL table and column names
from legacy brahmainsurance (verified in docs/migration/phase_6_quotation_legacy_audit.md).
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import DateTime, Double, Index, Integer, String, text
from sqlalchemy.dialects.mysql import INTEGER as MYSQL_INTEGER
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class AppQuatationEntry(Base):
    """
    Self-Quotation & Instant Rating Entry Model
    Physical Table: tbl_app_quatationentry
    Physical PK: QuatationId
    Verified Column Count: 60
    """
    __tablename__ = "tbl_app_quatationentry"
    __table_args__ = (
        Index("Title", "Title", unique=True, mysql_length=200),
        {
            "mysql_charset": "utf8",
            "mysql_collate": "utf8_general_ci",
        },
    )

    QuatationId: Mapped[int] = mapped_column("QuatationId", Integer, primary_key=True, autoincrement=True)
    QuatationCode: Mapped[Optional[str]] = mapped_column("QuatationCode", String(255), nullable=True)
    QuatationDate: Mapped[Optional[datetime]] = mapped_column("QuatationDate", DateTime, nullable=True)
    ProductName: Mapped[Optional[str]] = mapped_column("ProductName", String(255), nullable=True)
    Title: Mapped[Optional[str]] = mapped_column("Title", String(1000), nullable=True)
    MgfYear: Mapped[Optional[str]] = mapped_column("MgfYear", String(255), nullable=True)
    RTOId: Mapped[Optional[int]] = mapped_column("RTOId", Integer, nullable=True)
    Zone: Mapped[Optional[str]] = mapped_column("Zone", String(255), nullable=True)
    InsuranceCompanyId: Mapped[Optional[int]] = mapped_column("InsuranceCompanyId", Integer, nullable=True)
    Veh_Type_ID: Mapped[Optional[int]] = mapped_column("Veh_Type_ID", Integer, nullable=True)
    Veh_Sub_Type_ID: Mapped[Optional[int]] = mapped_column("Veh_Sub_Type_ID", Integer, nullable=True)
    Make_ID: Mapped[Optional[int]] = mapped_column("Make_ID", Integer, nullable=True)
    Model_ID: Mapped[Optional[int]] = mapped_column("Model_ID", Integer, nullable=True)
    Variant_ID: Mapped[Optional[int]] = mapped_column("Variant_ID", Integer, nullable=True)
    SeatsCapacity: Mapped[Optional[str]] = mapped_column("SeatsCapacity", String(255), nullable=True)
    CubicCapacity: Mapped[Optional[str]] = mapped_column("CubicCapacity", String(255), nullable=True)
    VehicleWeight: Mapped[Optional[str]] = mapped_column("VehicleWeight", String(255), nullable=True)
    IDV: Mapped[Optional[str]] = mapped_column("IDV", String(255), nullable=True)
    OwnDamagePremium: Mapped[Optional[str]] = mapped_column("OwnDamagePremium", String(255), nullable=True)
    OD: Mapped[Optional[str]] = mapped_column("OD", String(255), nullable=True)
    AddExtra15IMTno23: Mapped[Optional[str]] = mapped_column("AddExtra15IMTno23", String(255), nullable=True)
    ZeroDepreciation: Mapped[Optional[str]] = mapped_column("ZeroDepreciation", String(255), nullable=True)
    NoClaimBonus: Mapped[Optional[str]] = mapped_column("NoClaimBonus", String(255), nullable=True)
    AddLoading: Mapped[Optional[str]] = mapped_column("AddLoading", String(255), nullable=True)
    AddPremiumAbove12000kg: Mapped[Optional[str]] = mapped_column("AddPremiumAbove12000kg", String(255), nullable=True)
    EletricAccessories: Mapped[Optional[str]] = mapped_column("EletricAccessories", String(255), nullable=True)
    CNGFulekits: Mapped[Optional[str]] = mapped_column("CNGFulekits", String(255), nullable=True)
    VehicleBasicRate: Mapped[Optional[str]] = mapped_column("VehicleBasicRate", String(255), nullable=True)
    BasicPremium: Mapped[Optional[str]] = mapped_column("BasicPremium", String(255), nullable=True)
    LiabilityPremium: Mapped[Optional[str]] = mapped_column("LiabilityPremium", String(255), nullable=True)
    TPRisk: Mapped[Optional[str]] = mapped_column("TPRisk", String(255), nullable=True)
    CNGfuleKitLiabilityPremium: Mapped[Optional[str]] = mapped_column("CNGfuleKitLiabilityPremium", String(255), nullable=True)
    PAforOwnerDriver: Mapped[Optional[str]] = mapped_column("PAforOwnerDriver", String(255), nullable=True)
    PAtoUnnamedocc: Mapped[Optional[str]] = mapped_column("PAtoUnnamedocc", String(255), nullable=True)
    LegallibtoEmp: Mapped[Optional[str]] = mapped_column("LegallibtoEmp", String(255), nullable=True)
    legallibtoPaidDriver: Mapped[Optional[str]] = mapped_column("legallibtoPaidDriver", String(255), nullable=True)
    TPPDLimtoRS6000: Mapped[Optional[str]] = mapped_column("TPPDLimtoRS6000", String(255), nullable=True)
    PAToPaidDriver: Mapped[Optional[str]] = mapped_column("PAToPaidDriver", String(255), nullable=True)
    Antitheftacc: Mapped[Optional[str]] = mapped_column("Antitheftacc", String(255), nullable=True)
    Automobaccmemdis: Mapped[Optional[str]] = mapped_column("Automobaccmemdis", String(255), nullable=True)
    LLtoDrCleanerandCoolies: Mapped[Optional[str]] = mapped_column("LLtoDrCleanerandCoolies", String(255), nullable=True)
    LLtoNonfarepayingpass: Mapped[Optional[str]] = mapped_column("LLtoNonfarepayingpass", String(255), nullable=True)
    PABenefits: Mapped[Optional[str]] = mapped_column("PABenefits", String(255), nullable=True)
    PAtoPillionRider: Mapped[Optional[str]] = mapped_column("PAtoPillionRider", String(255), nullable=True)
    AtotalOwnDamPremium: Mapped[Optional[str]] = mapped_column("AtotalOwnDamPremium", String(255), nullable=True)
    BtotalLiabilityPremium: Mapped[Optional[str]] = mapped_column("BtotalLiabilityPremium", String(255), nullable=True)
    TotalPremium: Mapped[Optional[str]] = mapped_column("TotalPremium", String(255), nullable=True)
    GST18: Mapped[Optional[str]] = mapped_column("GST18", String(255), nullable=True)
    finalPrmium: Mapped[Optional[str]] = mapped_column("finalPrmium", String(255), nullable=True)
    AgentId: Mapped[Optional[int]] = mapped_column("AgentId", Integer, nullable=True)
    SaleExId: Mapped[Optional[int]] = mapped_column("SaleExId", Integer, nullable=True)
    isdeleted: Mapped[Optional[str]] = mapped_column("isdeleted", String(255), nullable=True, server_default=text("'0'"))
    NCBPre: Mapped[str] = mapped_column("NCBPre", String(255), nullable=False, server_default=text("'0'"))
    FuelTypeId: Mapped[Optional[int]] = mapped_column("FuelTypeId", Integer, nullable=True)
    UserRoleId: Mapped[Optional[int]] = mapped_column("UserRoleId", Integer, nullable=True)
    BodyPrice: Mapped[float] = mapped_column("BodyPrice", Double, nullable=False, server_default=text("0"))
    ChassisPrice: Mapped[float] = mapped_column("ChassisPrice", Double, nullable=False, server_default=text("0"))
    Mfg_Year: Mapped[Optional[datetime]] = mapped_column("Mfg_Year", DateTime, nullable=True)
    RegistrationNo: Mapped[Optional[str]] = mapped_column("RegistrationNo", String(255), nullable=True)
    ProductType: Mapped[Optional[str]] = mapped_column("ProductType", String(255), nullable=True)


class AppQuotationRequest(Base):
    """
    Assisted / Backoffice Quotation Request Model
    Physical Table: tbl_app_quotationrequest
    Physical PK: QuatationId
    Verified Column Count: 42
    """
    __tablename__ = "tbl_app_quotationrequest"
    __table_args__ = {
        "mysql_charset": "utf8",
        "mysql_collate": "utf8_general_ci",
    }

    QuatationId: Mapped[int] = mapped_column("QuatationId", Integer, primary_key=True, autoincrement=True)
    QuatationDate: Mapped[Optional[datetime]] = mapped_column("QuatationDate", DateTime, nullable=True)
    InsuranceCompanyId: Mapped[Optional[str]] = mapped_column("InsuranceCompanyId", String(255), nullable=True)
    VehicleId: Mapped[Optional[int]] = mapped_column("VehicleId", Integer, nullable=True)
    AgentId: Mapped[Optional[int]] = mapped_column("AgentId", Integer, nullable=True)
    QuotationFile: Mapped[Optional[str]] = mapped_column("QuotationFile", String(1000), nullable=True)
    ProductType: Mapped[Optional[str]] = mapped_column("ProductType", String(255), nullable=True)
    Zerodepth: Mapped[Optional[str]] = mapped_column("Zerodepth", String(255), nullable=True)
    PolicyMode: Mapped[Optional[str]] = mapped_column("PolicyMode", String(255), nullable=True)
    MobileNo: Mapped[Optional[str]] = mapped_column("MobileNo", String(255), nullable=True)
    NCB: Mapped[Optional[str]] = mapped_column("NCB", String(255), nullable=True)
    PolicyImage: Mapped[Optional[str]] = mapped_column("PolicyImage", String(1000), nullable=True)
    IsQuotationGenerate: Mapped[Optional[int]] = mapped_column(
        "IsQuotationGenerate", MYSQL_INTEGER(unsigned=True), nullable=True, server_default=text("0")
    )
    VehicleNo: Mapped[Optional[str]] = mapped_column("VehicleNo", String(255), nullable=True)
    Camera: Mapped[str] = mapped_column("Camera", String(1000), nullable=False, server_default=text("''"))
    UserRoleId: Mapped[Optional[int]] = mapped_column("UserRoleId", Integer, nullable=True)
    SalesEx_Id: Mapped[Optional[int]] = mapped_column("SalesEx_Id", Integer, nullable=True)
    OtherAgentName: Mapped[Optional[str]] = mapped_column("OtherAgentName", String(255), nullable=True)
    VehicleType: Mapped[Optional[str]] = mapped_column("VehicleType", String(255), nullable=True)
    VehicleMake: Mapped[Optional[str]] = mapped_column("VehicleMake", String(255), nullable=True)
    VehicleModel: Mapped[Optional[str]] = mapped_column("VehicleModel", String(255), nullable=True)
    VehicleVariance: Mapped[Optional[str]] = mapped_column("VehicleVariance", String(255), nullable=True)
    policytype: Mapped[Optional[str]] = mapped_column("policytype", String(255), nullable=True)
    FlagForPopup: Mapped[Optional[int]] = mapped_column("FlagForPopup", Integer, nullable=True, server_default=text("0"))
    updatedDate: Mapped[Optional[datetime]] = mapped_column("updatedDate", DateTime, nullable=True)
    LocationHeadId: Mapped[int] = mapped_column("LocationHeadId", Integer, nullable=False, server_default=text("0"))
    QuatationCode: Mapped[Optional[str]] = mapped_column("QuatationCode", String(500), nullable=True)
    ReadStatus: Mapped[int] = mapped_column("ReadStatus", Integer, nullable=False, server_default=text("0"))
    Note: Mapped[str] = mapped_column("Note", String(255), nullable=False, server_default=text("''"))
    isdeleted: Mapped[int] = mapped_column("isdeleted", Integer, nullable=False, server_default=text("0"))
    FranchiseId: Mapped[int] = mapped_column("FranchiseId", Integer, nullable=False, server_default=text("0"))
    Remark: Mapped[Optional[str]] = mapped_column("Remark", String(500), nullable=True)
    UpdateBy: Mapped[Optional[str]] = mapped_column("UpdateBy", String(200), nullable=True)
    isPendingRevert: Mapped[Optional[int]] = mapped_column("isPendingRevert", Integer, nullable=True, server_default=text("0"))
    CancelRemark: Mapped[Optional[str]] = mapped_column("CancelRemark", String(500), nullable=True)
    CancelDate: Mapped[Optional[datetime]] = mapped_column("CancelDate", DateTime, nullable=True)
    CancelBy: Mapped[Optional[str]] = mapped_column("CancelBy", String(100), nullable=True)
    AttendedBy: Mapped[Optional[str]] = mapped_column("AttendedBy", String(100), nullable=True)
    AttendedDate: Mapped[Optional[datetime]] = mapped_column("AttendedDate", DateTime, nullable=True)
    QuotSendDate: Mapped[Optional[datetime]] = mapped_column("QuotSendDate", DateTime, nullable=True)
    AttendedUserId: Mapped[Optional[int]] = mapped_column("AttendedUserId", Integer, nullable=True)


class InsuranceCompanyQuotation(Base):
    """
    Insurer Quote Option / Uploaded Quotation File Model
    Physical Table: tbl_insurancecompanyquotation
    Physical PK: QuotationId
    Verified Column Count: 11
    """
    __tablename__ = "tbl_insurancecompanyquotation"
    __table_args__ = {
        "mysql_charset": "utf8",
        "mysql_collate": "utf8_general_ci",
    }

    QuotationId: Mapped[int] = mapped_column(
        "QuotationId", MYSQL_INTEGER(unsigned=True), primary_key=True, autoincrement=True
    )
    InsuranceCompanyId: Mapped[int] = mapped_column(
        "InsuranceCompanyId", MYSQL_INTEGER(unsigned=True), nullable=False, server_default=text("0")
    )
    TransctionId: Mapped[int] = mapped_column(
        "TransctionId", MYSQL_INTEGER(unsigned=True), nullable=False, server_default=text("0")
    )
    agentId: Mapped[int] = mapped_column(
        "agentId", MYSQL_INTEGER(unsigned=True), nullable=False, server_default=text("0")
    )
    QuotationFile: Mapped[str] = mapped_column("QuotationFile", String(255), nullable=False, server_default=text("''"))
    EmpId: Mapped[int] = mapped_column(
        "EmpId", MYSQL_INTEGER(unsigned=True), nullable=False, server_default=text("0")
    )
    isdeleted: Mapped[str] = mapped_column("isdeleted", String(255), nullable=False, server_default=text("'0'"))
    InsertDate: Mapped[Optional[datetime]] = mapped_column("InsertDate", DateTime, nullable=True)
    Remark: Mapped[Optional[str]] = mapped_column("Remark", String(255), nullable=True)
    Quotationfile_Name: Mapped[Optional[str]] = mapped_column("Quotationfile_Name", String(255), nullable=True)
    ProductId: Mapped[int] = mapped_column("ProductId", Integer, nullable=False, server_default=text("1"))


class AppQuotationRemark(Base):
    """
    Quotation Request Remark / Audit Trail Model
    Physical Table: tbl_app_quotationremark
    Physical PK: QuatRemarkId
    Verified Column Count: 9
    """
    __tablename__ = "tbl_app_quotationremark"
    __table_args__ = {
        "mysql_charset": "utf8",
        "mysql_collate": "utf8_general_ci",
    }

    QuatRemarkId: Mapped[int] = mapped_column("QuatRemarkId", Integer, primary_key=True, autoincrement=True)
    QuatationId: Mapped[Optional[int]] = mapped_column("QuatationId", Integer, nullable=True)
    QuatationDate: Mapped[Optional[datetime]] = mapped_column("QuatationDate", DateTime, nullable=True)
    UserId: Mapped[Optional[int]] = mapped_column("UserId", Integer, nullable=True)
    Remark: Mapped[Optional[str]] = mapped_column("Remark", String(500), nullable=True)
    UpdateBy: Mapped[Optional[str]] = mapped_column("UpdateBy", String(200), nullable=True)
    UpdateDate: Mapped[Optional[datetime]] = mapped_column("UpdateDate", DateTime, nullable=True)
    isdeleted: Mapped[Optional[int]] = mapped_column("isdeleted", Integer, nullable=True, server_default=text("0"))
    RemarkFrom: Mapped[Optional[str]] = mapped_column("RemarkFrom", String(100), nullable=True)


class AppRequestedQuotationFile(Base):
    """
    Generated Self-Quotation PDF File Link Model
    Physical Table: tbl_app_requestedquotationfile
    Physical PK: Id
    Verified Column Count: 7
    """
    __tablename__ = "tbl_app_requestedquotationfile"
    __table_args__ = {
        "mysql_charset": "utf8",
        "mysql_collate": "utf8_general_ci",
    }

    Id: Mapped[int] = mapped_column("Id", Integer, primary_key=True, autoincrement=True)
    QuotationId: Mapped[Optional[int]] = mapped_column("QuotationId", Integer, nullable=True)
    CompanyId: Mapped[Optional[int]] = mapped_column("CompanyId", Integer, nullable=True)
    File_Name: Mapped[Optional[str]] = mapped_column("File_Name", String(255), nullable=True)
    FilePath: Mapped[Optional[str]] = mapped_column("FilePath", String(500), nullable=True)
    IsDelete: Mapped[Optional[int]] = mapped_column("IsDelete", Integer, nullable=True, server_default=text("0"))
    CreatedDate: Mapped[Optional[str]] = mapped_column("CreatedDate", String(255), nullable=True)


class QuotDamagePremium(Base):
    """
    Motor Own Damage Zone-Wise Base Tariff Table
    Physical Table: tbl_quot_damagepremium
    Physical PK: Id
    Verified Column Count: 9
    """
    __tablename__ = "tbl_quot_damagepremium"
    __table_args__ = {
        "mysql_charset": "utf8",
        "mysql_collate": "utf8_general_ci",
    }

    Id: Mapped[int] = mapped_column("Id", Integer, primary_key=True, autoincrement=True)
    Company_Id: Mapped[Optional[int]] = mapped_column("Company_Id", Integer, nullable=True)
    Company_Type: Mapped[Optional[str]] = mapped_column("Company_Type", String(45), nullable=True)
    fromCubicCapacity: Mapped[Optional[int]] = mapped_column("fromCubicCapacity", Integer, nullable=True)
    toCubicCapacity: Mapped[Optional[int]] = mapped_column("toCubicCapacity", Integer, nullable=True)
    Age: Mapped[Optional[float]] = mapped_column("Age", Double, nullable=True)
    OD_premium_Azone: Mapped[Optional[float]] = mapped_column("OD_premium_Azone", Double, nullable=True)
    OD_premium_Bzone: Mapped[Optional[float]] = mapped_column("OD_premium_Bzone", Double, nullable=True)
    OD_premium_Czone: Mapped[Optional[float]] = mapped_column("OD_premium_Czone", Double, nullable=True)


class QuotLiabilityPremium(Base):
    """
    Motor Third-Party Liability Base Tariff Table
    Physical Table: tbl_quot_liabilitypremium
    Physical PK: Id
    Verified Column Count: 7
    """
    __tablename__ = "tbl_quot_liabilitypremium"
    __table_args__ = {
        "mysql_charset": "utf8",
        "mysql_collate": "utf8_general_ci",
    }

    Id: Mapped[int] = mapped_column("Id", Integer, primary_key=True, autoincrement=True)
    Company_Id: Mapped[Optional[int]] = mapped_column("Company_Id", Integer, nullable=True)
    Company_Type: Mapped[Optional[str]] = mapped_column("Company_Type", String(45), nullable=True)
    UNIT: Mapped[Optional[str]] = mapped_column("UNIT", String(45), nullable=True)
    fromunit: Mapped[Optional[int]] = mapped_column("fromunit", Integer, nullable=True)
    tounit: Mapped[Optional[int]] = mapped_column("tounit", Integer, nullable=True)
    Premium: Mapped[Optional[float]] = mapped_column("Premium", Double, nullable=True)


class AppODDiscountNew(Base):
    """
    Passenger / 2W / Misc-D Model-Wise OD Discount Grid
    Physical Table: tbl_app_oddiscountnew
    Physical PK: AppODDiscountId
    Verified Column Count: 29
    """
    __tablename__ = "tbl_app_oddiscountnew"
    __table_args__ = {
        "mysql_charset": "utf8",
        "mysql_collate": "utf8_general_ci",
    }

    AppODDiscountId: Mapped[int] = mapped_column("AppODDiscountId", Integer, primary_key=True, autoincrement=True)
    Model_ID: Mapped[Optional[int]] = mapped_column("Model_ID", Integer, nullable=True)
    MakeID: Mapped[Optional[int]] = mapped_column("MakeID", Integer, nullable=True)
    InsuranceCompanyId: Mapped[Optional[int]] = mapped_column("InsuranceCompanyId", Integer, nullable=True)
    Decline: Mapped[int] = mapped_column("Decline", Integer, nullable=False, server_default=text("0"))
    Fueltypeid: Mapped[Optional[int]] = mapped_column("Fueltypeid", Integer, nullable=True)
    BusinessTypeId: Mapped[Optional[int]] = mapped_column("BusinessTypeId", Integer, nullable=True)
    NCB: Mapped[Optional[str]] = mapped_column("NCB", String(255), nullable=True)
    ClusterId: Mapped[Optional[int]] = mapped_column("ClusterId", Integer, nullable=True)
    ZeroDep: Mapped[Optional[str]] = mapped_column("ZeroDep", String(255), nullable=True)
    PRVDetails: Mapped[int] = mapped_column("PRVDetails", Integer, nullable=False, server_default=text("0"))
    N: Mapped[Optional[str]] = mapped_column("N", String(255), nullable=True)
    Zero: Mapped[Optional[str]] = mapped_column("Zero", String(255), nullable=True)
    One: Mapped[Optional[str]] = mapped_column("One", String(255), nullable=True)
    Two: Mapped[Optional[str]] = mapped_column("Two", String(255), nullable=True)
    Three: Mapped[Optional[str]] = mapped_column("Three", String(255), nullable=True)
    Four: Mapped[Optional[str]] = mapped_column("Four", String(255), nullable=True)
    Five: Mapped[Optional[str]] = mapped_column("Five", String(255), nullable=True)
    Six: Mapped[Optional[str]] = mapped_column("Six", String(255), nullable=True)
    Seven: Mapped[Optional[str]] = mapped_column("Seven", String(255), nullable=True)
    Eight: Mapped[Optional[str]] = mapped_column("Eight", String(255), nullable=True)
    Nine: Mapped[Optional[str]] = mapped_column("Nine", String(255), nullable=True)
    Ten: Mapped[Optional[str]] = mapped_column("Ten", String(255), nullable=True)
    Eleven: Mapped[Optional[str]] = mapped_column("Eleven", String(255), nullable=True)
    Twelve: Mapped[Optional[str]] = mapped_column("Twelve", String(255), nullable=True)
    thriteen: Mapped[Optional[str]] = mapped_column("thriteen", String(255), nullable=True)
    fourteen: Mapped[Optional[str]] = mapped_column("fourteen", String(255), nullable=True)
    fifteen: Mapped[Optional[str]] = mapped_column("fifteen", String(255), nullable=True)
    Sixteen: Mapped[Optional[str]] = mapped_column("Sixteen", String(255), nullable=True)


class AppODDiscountNewGCV(Base):
    """
    GCV Model-Wise OD Discount Grid
    Physical Table: tbl_app_oddiscountnew_gcv
    Physical PK: AppODDiscountId
    Verified Column Count: 27
    """
    __tablename__ = "tbl_app_oddiscountnew_gcv"
    __table_args__ = {
        "mysql_charset": "utf8",
        "mysql_collate": "utf8_general_ci",
    }

    AppODDiscountId: Mapped[int] = mapped_column("AppODDiscountId", Integer, primary_key=True, autoincrement=True)
    Model_ID: Mapped[Optional[int]] = mapped_column("Model_ID", Integer, nullable=True)
    MakeID: Mapped[Optional[int]] = mapped_column("MakeID", Integer, nullable=True)
    InsuranceCompanyId: Mapped[Optional[int]] = mapped_column("InsuranceCompanyId", Integer, nullable=True)
    Fueltypeid: Mapped[Optional[int]] = mapped_column("Fueltypeid", Integer, nullable=True)
    BusinessTypeId: Mapped[Optional[int]] = mapped_column("BusinessTypeId", Integer, nullable=True)
    NCB: Mapped[Optional[str]] = mapped_column("NCB", String(255), nullable=True)
    ClusterId: Mapped[Optional[int]] = mapped_column("ClusterId", Integer, nullable=True)
    ZeroDep: Mapped[Optional[str]] = mapped_column("ZeroDep", String(255), nullable=True)
    N: Mapped[Optional[str]] = mapped_column("N", String(255), nullable=True)
    Zero: Mapped[Optional[str]] = mapped_column("Zero", String(255), nullable=True)
    One: Mapped[Optional[str]] = mapped_column("One", String(255), nullable=True)
    Two: Mapped[Optional[str]] = mapped_column("Two", String(255), nullable=True)
    Three: Mapped[Optional[str]] = mapped_column("Three", String(255), nullable=True)
    Four: Mapped[Optional[str]] = mapped_column("Four", String(255), nullable=True)
    Five: Mapped[Optional[str]] = mapped_column("Five", String(255), nullable=True)
    Six: Mapped[Optional[str]] = mapped_column("Six", String(255), nullable=True)
    Seven: Mapped[Optional[str]] = mapped_column("Seven", String(255), nullable=True)
    Eight: Mapped[Optional[str]] = mapped_column("Eight", String(255), nullable=True)
    Nine: Mapped[Optional[str]] = mapped_column("Nine", String(255), nullable=True)
    Ten: Mapped[Optional[str]] = mapped_column("Ten", String(255), nullable=True)
    Eleven: Mapped[Optional[str]] = mapped_column("Eleven", String(255), nullable=True)
    Twelve: Mapped[Optional[str]] = mapped_column("Twelve", String(255), nullable=True)
    thriteen: Mapped[Optional[str]] = mapped_column("thriteen", String(255), nullable=True)
    fourteen: Mapped[Optional[str]] = mapped_column("fourteen", String(255), nullable=True)
    fifteen: Mapped[Optional[str]] = mapped_column("fifteen", String(255), nullable=True)
    Sixteen: Mapped[Optional[str]] = mapped_column("Sixteen", String(255), nullable=True)


class AppODDiscount(Base):
    """
    Legacy Model-Wise OD Discount Table
    Physical Table: tbl_appoddiscount
    Physical PK: AppODDiscount
    Verified Column Count: 8
    """
    __tablename__ = "tbl_appoddiscount"
    __table_args__ = (
        Index("tbl_vehicle_make", "Make_ID"),
        Index("tbl_vehicle_model", "Model_ID"),
        Index("tbl_insurancecompany", "InsuranceCompanyId"),
        {
            "mysql_charset": "utf8",
            "mysql_collate": "utf8_general_ci",
        },
    )

    AppODDiscount: Mapped[int] = mapped_column("AppODDiscount", Integer, primary_key=True, autoincrement=True)
    Make_ID: Mapped[Optional[int]] = mapped_column("Make_ID", Integer, nullable=True)
    Model_ID: Mapped[Optional[int]] = mapped_column("Model_ID", Integer, nullable=True)
    InsuranceCompanyId: Mapped[Optional[int]] = mapped_column("InsuranceCompanyId", Integer, nullable=True)
    NewVehicle: Mapped[Optional[str]] = mapped_column("NewVehicle", String(255), nullable=True)
    ZerotoFive: Mapped[Optional[str]] = mapped_column("ZerotoFive", String(255), nullable=True)
    fivetoTen: Mapped[Optional[str]] = mapped_column("fivetoTen", String(255), nullable=True)
    Greaterthen10: Mapped[Optional[str]] = mapped_column("Greaterthen10", String(255), nullable=True)


class InsuranceCompanyByVehicleType(Base):
    """
    Insurer Eligibility & Default OD Discount By Vehicle Category
    Physical Table: tbl_insurancecompanybyvehicletype
    Physical PK: Id
    Verified Column Count: 20
    """
    __tablename__ = "tbl_insurancecompanybyvehicletype"
    __table_args__ = {
        "mysql_charset": "utf8",
        "mysql_collate": "utf8_general_ci",
    }

    Id: Mapped[int] = mapped_column("Id", Integer, primary_key=True, autoincrement=True)
    InsuranceCompanyId: Mapped[Optional[int]] = mapped_column("InsuranceCompanyId", Integer, nullable=True)
    GCV: Mapped[Optional[int]] = mapped_column("GCV", Integer, nullable=True)
    GCV_Disc: Mapped[Optional[float]] = mapped_column("GCV_Disc", Double, nullable=True)
    Misc_D: Mapped[Optional[int]] = mapped_column("Misc_D", Integer, nullable=True)
    Misc_D_Disc: Mapped[Optional[float]] = mapped_column("Misc_D_Disc", Double, nullable=True)
    PCV: Mapped[Optional[int]] = mapped_column("PCV", Integer, nullable=True)
    PCV_Disc: Mapped[Optional[float]] = mapped_column("PCV_Disc", Double, nullable=True)
    PVT_CAR: Mapped[Optional[int]] = mapped_column("PVT_CAR", Integer, nullable=True)
    PVT_CAR_Disc: Mapped[Optional[float]] = mapped_column("PVT_CAR_Disc", Double, nullable=True)
    Two_Wheeler: Mapped[Optional[int]] = mapped_column("Two_Wheeler", Integer, nullable=True)
    Two_Wheeler_Disc: Mapped[Optional[float]] = mapped_column("Two_Wheeler_Disc", Double, nullable=True)
    Bus: Mapped[Optional[int]] = mapped_column("Bus", Integer, nullable=True)
    Bus_Disc: Mapped[Optional[float]] = mapped_column("Bus_Disc", Double, nullable=True)
    Three_Wheeler: Mapped[Optional[int]] = mapped_column("Three_Wheeler", Integer, nullable=True)
    Three_Wheeler_Disc: Mapped[Optional[float]] = mapped_column("Three_Wheeler_Disc", Double, nullable=True)
    IsDelete: Mapped[Optional[int]] = mapped_column("IsDelete", Integer, nullable=True, server_default=text("0"))
    Extra: Mapped[Optional[str]] = mapped_column("Extra", String(255), nullable=True)
    Three_Wheeler_PCV: Mapped[Optional[int]] = mapped_column("Three_Wheeler_PCV", Integer, nullable=True, server_default=text("0"))
    Three_Wheeler_PCV_Disc: Mapped[Optional[float]] = mapped_column("Three_Wheeler_PCV_Disc", Double, nullable=True, server_default=text("0"))


class PAToOwnerDriver(Base):
    """
    Insurer-Wise Personal Accident (PA) to Owner-Driver & Default Towing Table
    Physical Table: tbl_patoownerdriver
    Physical PK: PAToOwnerDriverId
    Verified Column Count: 5
    """
    __tablename__ = "tbl_patoownerdriver"
    __table_args__ = {
        "mysql_charset": "utf8",
        "mysql_collate": "utf8_general_ci",
    }

    PAToOwnerDriverId: Mapped[int] = mapped_column("PAToOwnerDriverId", Integer, primary_key=True, autoincrement=True)
    InsuranceCompanyId: Mapped[Optional[int]] = mapped_column("InsuranceCompanyId", Integer, nullable=True)
    Rate: Mapped[Optional[float]] = mapped_column("Rate", Double, nullable=True)
    TowingCharges: Mapped[float] = mapped_column("TowingCharges", Double, nullable=False, server_default=text("0"))
    IsDeleted: Mapped[Optional[int]] = mapped_column("IsDeleted", Integer, nullable=True, server_default=text("0"))


class InsuranceCompanyWiseTowingChanges(Base):
    """
    Insurer-Wise Towing Charges Slab Table
    Physical Table: tbl_insurancecompanywisetowingchanges
    Physical PK: Id
    Verified Column Count: 8
    """
    __tablename__ = "tbl_insurancecompanywisetowingchanges"
    __table_args__ = {
        "mysql_charset": "utf8",
        "mysql_collate": "utf8_general_ci",
    }

    Id: Mapped[int] = mapped_column("Id", Integer, primary_key=True, autoincrement=True)
    InsuranceCompanyId: Mapped[Optional[int]] = mapped_column("InsuranceCompanyId", Integer, nullable=True)
    Selection: Mapped[Optional[float]] = mapped_column("Selection", Double, nullable=True)
    Rate: Mapped[Optional[float]] = mapped_column("Rate", Double, nullable=True)
    GST18: Mapped[Optional[float]] = mapped_column("GST18", Double, nullable=True)
    Total: Mapped[Optional[float]] = mapped_column("Total", Double, nullable=True)
    IsDelete: Mapped[Optional[int]] = mapped_column("IsDelete", Integer, nullable=True, server_default=text("0"))
    Flag: Mapped[Optional[str]] = mapped_column("Flag", String(255), nullable=True)


class ZeroDep(Base):
    """
    Make-Wise Zero-Depreciation Rate Table
    Physical Table: tbl_zerodep
    Physical PK: ZerodepId
    Verified Column Count: 10
    """
    __tablename__ = "tbl_zerodep"
    __table_args__ = (
        Index("tbl_vehicle_make", "Make_ID"),
        Index("tbl_insurancecompany", "InsuranceCompanyId"),
        {
            "mysql_charset": "utf8",
            "mysql_collate": "utf8_general_ci",
        },
    )

    ZerodepId: Mapped[int] = mapped_column("ZerodepId", Integer, primary_key=True, autoincrement=True)
    InsuranceCompanyId: Mapped[Optional[int]] = mapped_column("InsuranceCompanyId", Integer, nullable=True)
    Make_ID: Mapped[Optional[int]] = mapped_column("Make_ID", Integer, nullable=True)
    Type: Mapped[Optional[int]] = mapped_column("Type", Integer, nullable=True)
    Age: Mapped[Optional[int]] = mapped_column("Age", Integer, nullable=True)
    NillDep: Mapped[Optional[str]] = mapped_column("NillDep", String(255), nullable=True)
    SecurePlus: Mapped[Optional[str]] = mapped_column("SecurePlus", String(255), nullable=True)
    SPremium: Mapped[Optional[str]] = mapped_column("SPremium", String(255), nullable=True)
    NO: Mapped[Optional[str]] = mapped_column("NO", String(255), nullable=True)
    Isdelete: Mapped[int] = mapped_column("Isdelete", Integer, nullable=False, server_default=text("0"))


class ZeroDepForSegmentWise(Base):
    """
    Model & Fuel-Wise Zero-Depreciation Rate Table
    Physical Table: tbl_zerodepforsegmentwise
    Physical PK: ZerodepId
    Verified Column Count: 11
    """
    __tablename__ = "tbl_zerodepforsegmentwise"
    __table_args__ = {
        "mysql_charset": "utf8",
        "mysql_collate": "utf8_general_ci",
    }

    ZerodepId: Mapped[int] = mapped_column("ZerodepId", Integer, primary_key=True, autoincrement=True)
    InsuranceCompanyId: Mapped[Optional[int]] = mapped_column("InsuranceCompanyId", Integer, nullable=True)
    Make_ID: Mapped[Optional[int]] = mapped_column("Make_ID", Integer, nullable=True)
    Model_Id: Mapped[Optional[int]] = mapped_column("Model_Id", Integer, nullable=True)
    FuelTypeId: Mapped[int] = mapped_column("FuelTypeId", Integer, nullable=False, server_default=text("1"))
    Age: Mapped[Optional[str]] = mapped_column("Age", String(255), nullable=True)
    NillDep: Mapped[Optional[float]] = mapped_column("NillDep", Double, nullable=True)
    SecurePlus: Mapped[Optional[float]] = mapped_column("SecurePlus", Double, nullable=True)
    SPremium: Mapped[Optional[float]] = mapped_column("SPremium", Double, nullable=True)
    NO: Mapped[Optional[int]] = mapped_column("NO", Integer, nullable=True)
    Isdelete: Mapped[int] = mapped_column("Isdelete", Integer, nullable=False, server_default=text("0"))


class ZeroDepNewAddonRate(Base):
    """
    Multi-AddOn / Zero-Dep Rate Table
    Physical Table: tbl_zerodepnewaddonrate
    Physical PK: AddOnId
    Verified Column Count: 17
    """
    __tablename__ = "tbl_zerodepnewaddonrate"
    __table_args__ = {
        "mysql_charset": "utf8",
        "mysql_collate": "utf8_general_ci",
    }

    AddOnId: Mapped[int] = mapped_column("AddOnId", Integer, primary_key=True, autoincrement=True)
    Model_ID: Mapped[Optional[int]] = mapped_column("Model_ID", Integer, nullable=True)
    MakeID: Mapped[Optional[int]] = mapped_column("MakeID", Integer, nullable=True)
    InsuranceCompanyId: Mapped[Optional[int]] = mapped_column("InsuranceCompanyId", Integer, nullable=True)
    Decline: Mapped[Optional[int]] = mapped_column("Decline", Integer, nullable=True, server_default=text("0"))
    Fueltypeid: Mapped[Optional[int]] = mapped_column("Fueltypeid", Integer, nullable=True)
    BusinessTypeId: Mapped[Optional[int]] = mapped_column("BusinessTypeId", Integer, nullable=True)
    NCB: Mapped[Optional[str]] = mapped_column("NCB", String(255), nullable=True)
    ClusterId: Mapped[Optional[int]] = mapped_column("ClusterId", Integer, nullable=True)
    Breaking: Mapped[Optional[str]] = mapped_column("Breaking", String(255), nullable=True)
    PRVDetails: Mapped[int] = mapped_column("PRVDetails", Integer, nullable=False, server_default=text("0"))
    Age: Mapped[Optional[int]] = mapped_column("Age", Integer, nullable=True)
    NillDep: Mapped[Optional[str]] = mapped_column("NillDep", String(255), nullable=True)
    SecurePlus: Mapped[Optional[str]] = mapped_column("SecurePlus", String(255), nullable=True)
    SPremium: Mapped[Optional[str]] = mapped_column("SPremium", String(255), nullable=True)
    NO: Mapped[Optional[str]] = mapped_column("NO", String(255), nullable=True)
    Isdelete: Mapped[Optional[int]] = mapped_column("Isdelete", Integer, nullable=True, server_default=text("0"))


class AddonExtraAmt(Base):
    """
    Flat Extra Add-On Amount Table
    Physical Table: tbl_addonextraamt
    Physical PK: ExtraAddonId
    Verified Column Count: 11 (Note physical column spelling VehiceTypeId)
    """
    __tablename__ = "tbl_addonextraamt"
    __table_args__ = {
        "mysql_charset": "utf8",
        "mysql_collate": "utf8_general_ci",
    }

    ExtraAddonId: Mapped[int] = mapped_column("ExtraAddonId", Integer, primary_key=True, autoincrement=True)
    InsuranceCompanyId: Mapped[Optional[int]] = mapped_column("InsuranceCompanyId", Integer, nullable=True)
    VehiceTypeId: Mapped[Optional[int]] = mapped_column("VehiceTypeId", Integer, nullable=True)
    makeId: Mapped[Optional[int]] = mapped_column("makeId", Integer, nullable=True, server_default=text("0"))
    ModelId: Mapped[Optional[int]] = mapped_column("ModelId", Integer, nullable=True, server_default=text("0"))
    Age: Mapped[Optional[int]] = mapped_column("Age", Integer, nullable=True, server_default=text("0"))
    NillDep: Mapped[Optional[float]] = mapped_column("NillDep", Double, nullable=True)
    SecurePlus: Mapped[Optional[float]] = mapped_column("SecurePlus", Double, nullable=True)
    SPremium: Mapped[Optional[float]] = mapped_column("SPremium", Double, nullable=True)
    No: Mapped[Optional[float]] = mapped_column("No", Double, nullable=True)
    IsDeleted: Mapped[Optional[int]] = mapped_column("IsDeleted", Integer, nullable=True, server_default=text("0"))


class AppTwoWheelerCCRate(Base):
    """
    Two-Wheeler CC Rate Table
    Physical Table: tbl_app_twowheelercc_rate
    Physical PK: CC_Id
    Verified Column Count: 12
    """
    __tablename__ = "tbl_app_twowheelercc_rate"
    __table_args__ = {
        "mysql_charset": "utf8",
        "mysql_collate": "utf8_general_ci",
    }

    CC_Id: Mapped[int] = mapped_column("CC_Id", Integer, primary_key=True, autoincrement=True)
    Age: Mapped[Optional[int]] = mapped_column("Age", Integer, nullable=True)
    Veh_Type_ID: Mapped[Optional[int]] = mapped_column("Veh_Type_ID", Integer, nullable=True)
    Up_CC: Mapped[Optional[float]] = mapped_column("Up_CC", Double, nullable=True)
    To_CC: Mapped[Optional[float]] = mapped_column("To_CC", Double, nullable=True)
    TP_Rate: Mapped[Optional[float]] = mapped_column("TP_Rate", Double, nullable=True)
    Veh_BasicRate: Mapped[Optional[float]] = mapped_column("Veh_BasicRate", Double, nullable=True)
    CreatedUser: Mapped[Optional[str]] = mapped_column("CreatedUser", String(255), nullable=True)
    CreatedDate: Mapped[Optional[datetime]] = mapped_column("CreatedDate", DateTime, nullable=True)
    UpdatedUser: Mapped[Optional[str]] = mapped_column("UpdatedUser", String(255), nullable=True)
    UpdatedDate: Mapped[Optional[datetime]] = mapped_column("UpdatedDate", DateTime, nullable=True)
    isdeleted: Mapped[Optional[int]] = mapped_column("isdeleted", Integer, nullable=True, server_default=text("0"))


class AppPCVCCRate(Base):
    """
    Passenger Carrying Vehicle (PCV Taxi) CC Rate Table
    Physical Table: tbl_app_pcv_cc_rate
    Physical PK: PCVCC_Id
    Verified Column Count: 13
    """
    __tablename__ = "tbl_app_pcv_cc_rate"
    __table_args__ = {
        "mysql_charset": "utf8",
        "mysql_collate": "utf8_general_ci",
    }

    PCVCC_Id: Mapped[int] = mapped_column("PCVCC_Id", Integer, primary_key=True, autoincrement=True)
    Age: Mapped[Optional[int]] = mapped_column("Age", Integer, nullable=True)
    Veh_Type_ID: Mapped[Optional[int]] = mapped_column("Veh_Type_ID", Integer, nullable=True)
    Up_CC: Mapped[Optional[float]] = mapped_column("Up_CC", Double, nullable=True)
    To_CC: Mapped[Optional[float]] = mapped_column("To_CC", Double, nullable=True)
    TP_Rate: Mapped[Optional[float]] = mapped_column("TP_Rate", Double, nullable=True)
    Veh_BasicRate: Mapped[Optional[float]] = mapped_column("Veh_BasicRate", Double, nullable=True)
    Per_PassengerRate: Mapped[Optional[float]] = mapped_column("Per_PassengerRate", Double, nullable=True)
    CreatedUser: Mapped[Optional[str]] = mapped_column("CreatedUser", String(255), nullable=True)
    CreatedDate: Mapped[Optional[datetime]] = mapped_column("CreatedDate", DateTime, nullable=True)
    UpdatedUser: Mapped[Optional[str]] = mapped_column("UpdatedUser", String(255), nullable=True)
    UpdatedDate: Mapped[Optional[datetime]] = mapped_column("UpdatedDate", DateTime, nullable=True)
    isdeleted: Mapped[Optional[int]] = mapped_column("isdeleted", Integer, nullable=True, server_default=text("0"))


class AppBusCCRate(Base):
    """
    School / Staff / Other Bus Rate Table
    Physical Table: tbl_app_bus_cc_rate
    Physical PK: BUSCC_Id
    Verified Column Count: 13
    """
    __tablename__ = "tbl_app_bus_cc_rate"
    __table_args__ = {
        "mysql_charset": "utf8",
        "mysql_collate": "utf8_general_ci",
    }

    BUSCC_Id: Mapped[int] = mapped_column("BUSCC_Id", Integer, primary_key=True, autoincrement=True)
    Age: Mapped[Optional[int]] = mapped_column("Age", Integer, nullable=True)
    Bus_Type: Mapped[Optional[str]] = mapped_column("Bus_Type", String(255), nullable=True)
    Veh_Type_ID: Mapped[Optional[int]] = mapped_column("Veh_Type_ID", Integer, nullable=True)
    TP_Rate: Mapped[Optional[float]] = mapped_column("TP_Rate", Double, nullable=True)
    Veh_BasicRate: Mapped[Optional[float]] = mapped_column("Veh_BasicRate", Double, nullable=True)
    Per_PassengerRate: Mapped[Optional[float]] = mapped_column("Per_PassengerRate", Double, nullable=True)
    ODDiscount: Mapped[Optional[float]] = mapped_column("ODDiscount", Double, nullable=True)
    CreatedUser: Mapped[Optional[str]] = mapped_column("CreatedUser", String(255), nullable=True)
    CreatedDate: Mapped[Optional[datetime]] = mapped_column("CreatedDate", DateTime, nullable=True)
    UpdatedUser: Mapped[Optional[str]] = mapped_column("UpdatedUser", String(255), nullable=True)
    UpdatedDate: Mapped[Optional[datetime]] = mapped_column("UpdatedDate", DateTime, nullable=True)
    isdeleted: Mapped[Optional[int]] = mapped_column("isdeleted", Integer, nullable=True, server_default=text("0"))


class AppThreeWheelerCCRate(Base):
    """
    Three-Wheeler PCV Rate Table
    Physical Table: tbl_app_threewheeler_cc_rate
    Physical PK: ThreeWheelerCC_Id
    Verified Column Count: 13
    """
    __tablename__ = "tbl_app_threewheeler_cc_rate"
    __table_args__ = {
        "mysql_charset": "utf8",
        "mysql_collate": "utf8_general_ci",
    }

    ThreeWheelerCC_Id: Mapped[int] = mapped_column("ThreeWheelerCC_Id", Integer, primary_key=True, autoincrement=True)
    UpAge: Mapped[Optional[int]] = mapped_column("UpAge", Integer, nullable=True)
    ToAge: Mapped[int] = mapped_column("ToAge", Integer, nullable=False, server_default=text("0"))
    ThreeWheeler_Type: Mapped[Optional[str]] = mapped_column("ThreeWheeler_Type", String(255), nullable=True)
    Veh_Type_ID: Mapped[Optional[int]] = mapped_column("Veh_Type_ID", Integer, nullable=True)
    TP_Rate: Mapped[Optional[float]] = mapped_column("TP_Rate", Double, nullable=True)
    Veh_BasicRate: Mapped[Optional[float]] = mapped_column("Veh_BasicRate", Double, nullable=True)
    Per_PassengerRate: Mapped[Optional[float]] = mapped_column("Per_PassengerRate", Double, nullable=True)
    CreatedUser: Mapped[Optional[str]] = mapped_column("CreatedUser", String(255), nullable=True)
    CreatedDate: Mapped[Optional[datetime]] = mapped_column("CreatedDate", DateTime, nullable=True)
    UpdatedUser: Mapped[Optional[str]] = mapped_column("UpdatedUser", String(255), nullable=True)
    UpdatedDate: Mapped[Optional[datetime]] = mapped_column("UpdatedDate", DateTime, nullable=True)
    isdeleted: Mapped[Optional[int]] = mapped_column("isdeleted", Integer, nullable=True, server_default=text("0"))


class QuotationPrefix(Base):
    """
    Role-Based Quotation Code Prefix & Zero-Padding Configuration Table
    Physical Table: tbl_quotation_prefix
    Physical PK: Id
    Verified Column Count: 6
    """
    __tablename__ = "tbl_quotation_prefix"
    __table_args__ = {
        "mysql_charset": "utf8",
        "mysql_collate": "utf8_general_ci",
    }

    Id: Mapped[int] = mapped_column("Id", MYSQL_INTEGER(unsigned=True), primary_key=True, autoincrement=True)
    Code: Mapped[str] = mapped_column("Code", String(255), nullable=False)
    CodeLength: Mapped[int] = mapped_column("CodeLength", MYSQL_INTEGER(unsigned=True), nullable=False, server_default=text("0"))
    IsDeleted: Mapped[int] = mapped_column("IsDeleted", MYSQL_INTEGER(unsigned=True), nullable=False, server_default=text("0"))
    UserRoleId: Mapped[Optional[int]] = mapped_column("UserRoleId", Integer, nullable=True)
    NoOfDigit: Mapped[Optional[str]] = mapped_column("NoOfDigit", String(255), nullable=True)


class SelfDiscount(Base):
    """
    Branch & Broker Self-Discount Configuration Table
    Physical Table: tbl_selfdiscount
    Physical PK: SelfDiscId
    Verified Column Count: 11
    """
    __tablename__ = "tbl_selfdiscount"
    __table_args__ = {
        "mysql_charset": "utf8",
        "mysql_collate": "utf8_general_ci",
    }

    SelfDiscId: Mapped[int] = mapped_column("SelfDiscId", Integer, primary_key=True, autoincrement=True)
    BranchId: Mapped[Optional[int]] = mapped_column("BranchId", Integer, nullable=True)
    ReferenceType: Mapped[Optional[str]] = mapped_column("ReferenceType", String(255), nullable=True)
    SelfDiscount: Mapped[Optional[float]] = mapped_column("SelfDiscount", Double, nullable=True)
    ValidFrom: Mapped[Optional[datetime]] = mapped_column("ValidFrom", DateTime, nullable=True)
    BrokerId: Mapped[Optional[int]] = mapped_column("BrokerId", Integer, nullable=True)
    IsDelete: Mapped[Optional[int]] = mapped_column("IsDelete", Integer, nullable=True, server_default=text("0"))
    CreatedDate: Mapped[Optional[datetime]] = mapped_column("CreatedDate", DateTime, nullable=True)
    CreatedUser: Mapped[Optional[str]] = mapped_column("CreatedUser", String(255), nullable=True)
    UpdatedDate: Mapped[Optional[datetime]] = mapped_column("UpdatedDate", DateTime, nullable=True)
    UpdatedUser: Mapped[Optional[str]] = mapped_column("UpdatedUser", String(255), nullable=True)
