"""
SQLAlchemy 2.0 Declarative Models for Phase 22 — Sales Executive & Location Head Commission Hierarchy,
Insurer Partner Portals Registry, and App Billing & Field Reimbursement Claims.

Physical Tables Added:
1. tbl_salesexcommission (Sales Executive Commission Grids & Overrides)
2. tbl_locationheadcommission (Location Head Regional Commission Overrides)
3. tbl_locationheadsalesexmap (Location Head to Sales Executive Organization Mapping)
4. tbl_insurancecompanyportal (Insurer Partner Portals & Online Credentials Registry)
5. tbl_appbillingdetails (App Billing & Field Executive Expense Reimbursement Claims)
6. tbl_appbillingattachment (App Billing Invoice Photo & PDF Attachments)
"""
from datetime import datetime, date
from decimal import Decimal
from typing import Optional
from sqlalchemy import Integer, String, DateTime, Date, Numeric, Text, Index, text
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


# ============================================================================
# 1. SALES EXECUTIVE COMMISSION MATRIX (tbl_salesexcommission)
# ============================================================================

class SalesExecutiveCommission(Base):
    """
    Sales Executive Commission Grids & Policy Tier Overrides Model.
    Physical Table: tbl_salesexcommission
    Physical PK: SalesCommissionId
    Legacy Reference: BLL_SalesExCommision, DAL_SalesExCommision, adm_SaleExCommission.aspx.cs,
                      sp_SelectSalesExecutiveCommissionGridnew2025, Sp_InsertMultiplesalesexCommissionnew2025
    """
    __tablename__ = "tbl_salesexcommission"
    __table_args__ = (
        Index("ix_tbl_salesexcomm_SalesEx_Id", "SalesEx_Id"),
        Index("ix_tbl_salesexcomm_Company_Policy_Product", "InsuranceCompanyId", "PolicyType", "ProductType"),
        Index("ix_tbl_salesexcomm_FranchiseCode", "FranchiseCode"),
        Index("ix_tbl_salesexcomm_ValidFromDate", "ValidFromDate"),
        {
            "mysql_charset": "utf8",
            "mysql_collate": "utf8_general_ci",
            "mysql_row_format": "DYNAMIC",
        },
    )

    SalesCommissionId: Mapped[int] = mapped_column("SalesCommissionId", Integer, primary_key=True, autoincrement=True)
    SalesEx_Id: Mapped[int] = mapped_column("SalesEx_Id", Integer, nullable=False)
    InsuranceCompanyId: Mapped[int] = mapped_column("InsuranceCompanyId", Integer, nullable=False)
    PolicyType: Mapped[Optional[str]] = mapped_column("PolicyType", String(100), nullable=True)
    ProductType: Mapped[Optional[str]] = mapped_column("ProductType", String(100), nullable=True)
    VehiTypeId: Mapped[Optional[int]] = mapped_column("VehiTypeId", Integer, nullable=True)
    FuelTypeId: Mapped[Optional[int]] = mapped_column("FuelTypeId", Integer, nullable=True)
    Commission: Mapped[Decimal] = mapped_column(
        "Commission", Numeric(10, 2), nullable=False, server_default=text("0.00")
    )
    Commission_OD: Mapped[Decimal] = mapped_column(
        "Commission_OD", Numeric(10, 2), nullable=False, server_default=text("0.00")
    )
    Commission_Net: Mapped[Decimal] = mapped_column(
        "Commission_Net", Numeric(10, 2), nullable=False, server_default=text("0.00")
    )
    CommissionCalculateOn: Mapped[Optional[str]] = mapped_column(
        "CommissionCalculateOn", String(50), nullable=True, server_default=text("'-'")
    )
    ReferenceType: Mapped[Optional[str]] = mapped_column(
        "ReferenceType", String(50), nullable=True, server_default=text("'Self'")
    )
    FlatRate: Mapped[Optional[str]] = mapped_column("FlatRate", String(50), nullable=True)
    OD_Discount: Mapped[Decimal] = mapped_column(
        "OD_Discount", Numeric(10, 2), nullable=False, server_default=text("0.00")
    )
    FranchiseCode: Mapped[Optional[str]] = mapped_column(
        "FranchiseCode", String(50), nullable=True, server_default=text("'RA'")
    )
    ncb: Mapped[Optional[int]] = mapped_column("ncb", Integer, nullable=True, server_default=text("0"))
    CCRange: Mapped[Optional[str]] = mapped_column("CCRange", String(50), nullable=True)
    Slab: Mapped[Optional[str]] = mapped_column("Slab", String(50), nullable=True)
    ND: Mapped[Optional[str]] = mapped_column("ND", String(50), nullable=True)
    MakeId: Mapped[Optional[int]] = mapped_column("MakeId", Integer, nullable=True, server_default=text("0"))
    ModelId: Mapped[Optional[int]] = mapped_column("ModelId", Integer, nullable=True, server_default=text("0"))
    RtoId: Mapped[Optional[int]] = mapped_column("RtoId", Integer, nullable=True, server_default=text("0"))
    StateId: Mapped[Optional[int]] = mapped_column("StateId", Integer, nullable=True, server_default=text("0"))
    ValidFromDate: Mapped[date] = mapped_column("ValidFromDate", Date, nullable=False, default=date.today)
    ValidToDate: Mapped[Optional[date]] = mapped_column("ValidToDate", Date, nullable=True)
    CreateUser: Mapped[Optional[int]] = mapped_column("CreateUser", Integer, nullable=True)
    CreateDate: Mapped[datetime] = mapped_column(
        "CreateDate", DateTime, nullable=False, default=datetime.utcnow
    )
    UpdateUser: Mapped[Optional[int]] = mapped_column("UpdateUser", Integer, nullable=True)
    UpdateDate: Mapped[Optional[datetime]] = mapped_column("UpdateDate", DateTime, nullable=True)
    IsActive: Mapped[int] = mapped_column("IsActive", Integer, nullable=False, server_default=text("1"))


# ============================================================================
# 2. LOCATION HEAD COMMISSION MATRIX (tbl_locationheadcommission)
# ============================================================================

class LocationHeadCommission(Base):
    """
    Location Head Regional Hierarchy Commission Matrix Model.
    Physical Table: tbl_locationheadcommission
    Physical PK: LocationHeadCommId
    Legacy Reference: BLL_SalesExCommision, DAL_SalesExCommision, adm_SaleExCommission.aspx.cs,
                      sp_SelectSelectLocationHeadCommissionGrid, sp_SelectLocationHeadSalesExWiseComm
    """
    __tablename__ = "tbl_locationheadcommission"
    __table_args__ = (
        Index("ix_tbl_lochcomm_LocationHeadId", "LocationHeadId"),
        Index("ix_tbl_lochcomm_Company_Policy_Product", "InsuranceCompanyId", "PolicyType", "ProductType"),
        Index("ix_tbl_lochcomm_FranchiseCode", "FranchiseCode"),
        Index("ix_tbl_lochcomm_ValidFromDate", "ValidFromDate"),
        {
            "mysql_charset": "utf8",
            "mysql_collate": "utf8_general_ci",
            "mysql_row_format": "DYNAMIC",
        },
    )

    LocationHeadCommId: Mapped[int] = mapped_column("LocationHeadCommId", Integer, primary_key=True, autoincrement=True)
    LocationHeadId: Mapped[int] = mapped_column("LocationHeadId", Integer, nullable=False)
    InsuranceCompanyId: Mapped[int] = mapped_column("InsuranceCompanyId", Integer, nullable=False)
    PolicyType: Mapped[Optional[str]] = mapped_column("PolicyType", String(100), nullable=True)
    ProductType: Mapped[Optional[str]] = mapped_column("ProductType", String(100), nullable=True)
    VehiTypeId: Mapped[Optional[int]] = mapped_column("VehiTypeId", Integer, nullable=True)
    FuelTypeId: Mapped[Optional[int]] = mapped_column("FuelTypeId", Integer, nullable=True)
    Commission: Mapped[Decimal] = mapped_column(
        "Commission", Numeric(10, 2), nullable=False, server_default=text("0.00")
    )
    Commission_OD: Mapped[Decimal] = mapped_column(
        "Commission_OD", Numeric(10, 2), nullable=False, server_default=text("0.00")
    )
    Commission_Net: Mapped[Decimal] = mapped_column(
        "Commission_Net", Numeric(10, 2), nullable=False, server_default=text("0.00")
    )
    OD_Discount: Mapped[Decimal] = mapped_column(
        "OD_Discount", Numeric(10, 2), nullable=False, server_default=text("0.00")
    )
    FranchiseCode: Mapped[Optional[str]] = mapped_column(
        "FranchiseCode", String(50), nullable=True, server_default=text("'RA'")
    )
    ReferenceType: Mapped[Optional[str]] = mapped_column(
        "ReferenceType", String(50), nullable=True, server_default=text("'L.Head'")
    )
    ValidFromDate: Mapped[date] = mapped_column("ValidFromDate", Date, nullable=False, default=date.today)
    ValidToDate: Mapped[Optional[date]] = mapped_column("ValidToDate", Date, nullable=True)
    CreateUser: Mapped[Optional[int]] = mapped_column("CreateUser", Integer, nullable=True)
    CreateDate: Mapped[datetime] = mapped_column(
        "CreateDate", DateTime, nullable=False, default=datetime.utcnow
    )
    UpdateUser: Mapped[Optional[int]] = mapped_column("UpdateUser", Integer, nullable=True)
    UpdateDate: Mapped[Optional[datetime]] = mapped_column("UpdateDate", DateTime, nullable=True)
    IsActive: Mapped[int] = mapped_column("IsActive", Integer, nullable=False, server_default=text("1"))


# ============================================================================
# 3. LOCATION HEAD <-> SALES EXECUTIVE HIERARCHY MAP (tbl_locationheadsalesexmap)
# ============================================================================

class LocationHeadSalesExMap(Base):
    """
    Location Head to Sales Executive Mapping Model.
    Physical Table: tbl_locationheadsalesexmap
    Physical PK: MapId
    Legacy Reference: AssignLocationHeadToSalesEx.aspx.cs, BLL_Employee, DAL_Employee,
                      sp_InsertAssignLocHeadToSalesex, sp_getLocationHeadIdFromSalesExecutive
    """
    __tablename__ = "tbl_locationheadsalesexmap"
    __table_args__ = (
        Index("ix_tbl_lhsemap_LocationHeadId", "LocationHeadId"),
        Index("ix_tbl_lhsemap_SalesEx_Id", "SalesEx_Id"),
        {
            "mysql_charset": "utf8",
            "mysql_collate": "utf8_general_ci",
            "mysql_row_format": "DYNAMIC",
        },
    )

    MapId: Mapped[int] = mapped_column("MapId", Integer, primary_key=True, autoincrement=True)
    LocationHeadId: Mapped[int] = mapped_column("LocationHeadId", Integer, nullable=False)
    SalesEx_Id: Mapped[int] = mapped_column("SalesEx_Id", Integer, nullable=False)
    CreatedUser: Mapped[Optional[int]] = mapped_column("CreatedUser", Integer, nullable=True)
    CreatedDate: Mapped[datetime] = mapped_column(
        "CreatedDate", DateTime, nullable=False, default=datetime.utcnow
    )
    IsActive: Mapped[int] = mapped_column("IsActive", Integer, nullable=False, server_default=text("1"))


# ============================================================================
# 4. INSURER PARTNER PORTALS REGISTRY (tbl_insurancecompanyportal)
# ============================================================================

class InsuranceCompanyPortal(Base):
    """
    Insurance Company Direct Portal URL & Partner Credentials Registry.
    Physical Table: tbl_insurancecompanyportal
    Physical PK: tbl_Id
    Legacy Reference: BLL_Portal, BLL_InsuranceCompanyPortal, DAL_InsuranceCompanyPortal,
                      adm_InsuranceCompanyPortal.aspx.cs, API_InsuranceCompanyPortal,
                      sp_insurancecompanyportal, Sp_selectInsuranceCompanyPortal
    """
    __tablename__ = "tbl_insurancecompanyportal"
    __table_args__ = (
        Index("ix_tbl_icp_InsuranceCompanyId", "InsuranceCompanyId"),
        Index("ix_tbl_icp_BrokerId", "BrokerId"),
        {
            "mysql_charset": "utf8",
            "mysql_collate": "utf8_general_ci",
            "mysql_row_format": "DYNAMIC",
        },
    )

    tbl_Id: Mapped[int] = mapped_column("tbl_Id", Integer, primary_key=True, autoincrement=True)
    InsuranceCompanyId: Mapped[int] = mapped_column("InsuranceCompanyId", Integer, nullable=False)
    PortalId: Mapped[Optional[str]] = mapped_column("PortalId", String(200), nullable=True)
    PersonName: Mapped[Optional[str]] = mapped_column("PersonName", String(200), nullable=True)
    BrokerId: Mapped[Optional[int]] = mapped_column("BrokerId", Integer, nullable=True)
    PortalUrl: Mapped[Optional[str]] = mapped_column("PortalUrl", String(500), nullable=True)
    PortalPassword: Mapped[Optional[str]] = mapped_column("PortalPassword", String(255), nullable=True)
    IsActive: Mapped[int] = mapped_column("IsActive", Integer, nullable=False, server_default=text("1"))
    CreatedUser: Mapped[Optional[int]] = mapped_column("CreatedUser", Integer, nullable=True)
    CreatedDate: Mapped[datetime] = mapped_column(
        "CreatedDate", DateTime, nullable=False, default=datetime.utcnow
    )
    UpdatedUser: Mapped[Optional[int]] = mapped_column("UpdatedUser", Integer, nullable=True)
    UpdatedDate: Mapped[Optional[datetime]] = mapped_column("UpdatedDate", DateTime, nullable=True)


# ============================================================================
# 5. APP BILLING & FIELD REIMBURSEMENT (tbl_appbillingdetails)
# ============================================================================

class AppBillingDetails(Base):
    """
    Sales Executive Field Expense Reimbursement & App Billing Model.
    Physical Table: tbl_appbillingdetails
    Physical PK: BillingId
    Legacy Reference: BLL_AppBillingDetails, DAL_AppBillingDetails, Service.asmx.cs (InsertAppBillingDetails),
                      ViewAppBillingDetails.aspx.cs, sp_InsertAppBilling, sp_ViewBillingDetails, sp_UpdateAppBillingDetails
    """
    __tablename__ = "tbl_appbillingdetails"
    __table_args__ = (
        Index("ix_tbl_appbill_SalesExId", "SalesExId"),
        Index("ix_tbl_appbill_Status", "Status"),
        Index("ix_tbl_appbill_FromDate_ToDate", "FromDate", "ToDate"),
        {
            "mysql_charset": "utf8",
            "mysql_collate": "utf8_general_ci",
            "mysql_row_format": "DYNAMIC",
        },
    )

    BillingId: Mapped[int] = mapped_column("BillingId", Integer, primary_key=True, autoincrement=True)
    SalesExId: Mapped[int] = mapped_column("SalesExId", Integer, nullable=False)
    FromDate: Mapped[date] = mapped_column("FromDate", Date, nullable=False)
    ToDate: Mapped[date] = mapped_column("ToDate", Date, nullable=False)
    Remark: Mapped[Optional[str]] = mapped_column("Remark", Text, nullable=True)
    BillingAmount: Mapped[Decimal] = mapped_column(
        "BillingAmount", Numeric(12, 2), nullable=False, server_default=text("0.00")
    )
    ReimbursementTypeId: Mapped[Optional[int]] = mapped_column("ReimbursementTypeId", Integer, nullable=True)
    Destination: Mapped[Optional[str]] = mapped_column("Destination", String(255), nullable=True)
    Status: Mapped[str] = mapped_column("Status", String(50), nullable=False, server_default=text("'PENDING'"))
    CreatedDate: Mapped[datetime] = mapped_column(
        "CreatedDate", DateTime, nullable=False, default=datetime.utcnow
    )
    ProcessedDate: Mapped[Optional[datetime]] = mapped_column("ProcessedDate", DateTime, nullable=True)
    ProcessedBy: Mapped[Optional[int]] = mapped_column("ProcessedBy", Integer, nullable=True)


# ============================================================================
# 6. APP BILLING ATTACHMENTS (tbl_appbillingattachment)
# ============================================================================

class AppBillingAttachment(Base):
    """
    App Billing Receipt Image and PDF Document Attachments Model.
    Physical Table: tbl_appbillingattachment
    Physical PK: AttachmentId
    Legacy Reference: sp_InsertAppBilling_img, sp_InsertAppBilling_pdf, ViewAppBillingDetails.aspx.cs
    """
    __tablename__ = "tbl_appbillingattachment"
    __table_args__ = (
        Index("ix_tbl_appbillatt_BillingId", "BillingId"),
        Index("ix_tbl_appbillatt_FileType", "FileType"),
        {
            "mysql_charset": "utf8",
            "mysql_collate": "utf8_general_ci",
            "mysql_row_format": "DYNAMIC",
        },
    )

    AttachmentId: Mapped[int] = mapped_column("AttachmentId", Integer, primary_key=True, autoincrement=True)
    BillingId: Mapped[int] = mapped_column("BillingId", Integer, nullable=False)
    FileType: Mapped[str] = mapped_column("FileType", String(20), nullable=False)  # "IMG" or "PDF"
    FilePath: Mapped[str] = mapped_column("FilePath", String(500), nullable=False)
    FileName: Mapped[Optional[str]] = mapped_column("FileName", String(255), nullable=True)
    UploadedDate: Mapped[datetime] = mapped_column(
        "UploadedDate", DateTime, nullable=False, default=datetime.utcnow
    )
