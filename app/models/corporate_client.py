"""
SQLAlchemy 2.0 Declarative Models for Phase 25:
Corporate Group Clients, Commercial Sales Invoicing & Sister Concern Advances.

Physical Tables Added:
1. tbl_salestype (Commercial Sales Classification Master)
2. tbl_reliablecompanymst (Reliable Sister Group Companies & Invoicing Prefixes)
3. tbl_clientmaster (Corporate B2B Client Master Registry, PAN, GSTIN & Tax Defaults)
4. tbl_salesregdetails (Multi-Line Item Commercial Sales Invoicing Breakdown)
5. tbl_companyadvancemaster (Sister Concern & Insurer Advance Disbursement Master)
6. tbl_companyadvdetails (Sister Concern Advance Recovery & Voucher History Log)
7. tbl_invoicesequence (Atomic Monotonic Sequence Counter for Commercial Invoicing)

Pre-existing Table Reused:
- tbl_salesregistration (Physical table created in Alembic revision b18a0c5d1801, mapped in operations_parity.py)
"""
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List
from sqlalchemy import (
    Integer,
    String,
    DateTime,
    Date,
    Numeric,
    Text,
    Boolean,
    Index,
    text,
    ForeignKey,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


# ============================================================================
# 1. COMMERCIAL SALES TYPE MASTER (tbl_salestype)
# ============================================================================

class SalesType(Base):
    """
    Commercial Sales Classification Master Model.
    Physical Table: tbl_salestype
    Physical PK: SalesTypeId
    Legacy Reference: API_SalesType (AllMaster.cs L183),
                      BLL_Loan.BLL_SalesTypeOperation,
                      DAL_Loan.DAL_SalesTypeOperation,
                      sp_SalesType
    """
    __tablename__ = "tbl_salestype"
    __table_args__ = (
        Index("ix_tbl_salestype_Description", "Description"),
        {
            "mysql_charset": "utf8",
            "mysql_collate": "utf8_general_ci",
            "mysql_row_format": "DYNAMIC",
        },
    )

    SalesTypeId: Mapped[int] = mapped_column(
        "SalesTypeId", Integer, primary_key=True, autoincrement=True
    )
    Description: Mapped[str] = mapped_column("Description", String(255), nullable=False)
    IsActive: Mapped[bool] = mapped_column(
        "IsActive", Boolean, nullable=False, default=True, server_default=text("1")
    )
    CreatedDate: Mapped[datetime] = mapped_column(
        "CreatedDate", DateTime, nullable=False, default=datetime.utcnow, server_default=text("CURRENT_TIMESTAMP")
    )


# ============================================================================
# 2. RELIABLE GROUP COMPANY MASTER (tbl_reliablecompanymst)
# ============================================================================

class ReliableCompany(Base):
    """
    Reliable Sister Group Companies & Invoicing Prefixes Master Model.
    Physical Table: tbl_reliablecompanymst
    Physical PK: RCompanyId
    Legacy Reference: API_reliablecompanymst (AllMaster.cs L188),
                      BLL_Loan.BLL_reliablecompanymstOperation,
                      DAL_Loan.DAL_selectreliablecompanymstprefix,
                      sp_reliablecompanymst
    """
    __tablename__ = "tbl_reliablecompanymst"
    __table_args__ = (
        Index("ix_tbl_reliablecompanymst_Prefix", "Prefix"),
        {
            "mysql_charset": "utf8",
            "mysql_collate": "utf8_general_ci",
            "mysql_row_format": "DYNAMIC",
        },
    )

    RCompanyId: Mapped[int] = mapped_column(
        "RCompanyId", Integer, primary_key=True, autoincrement=True
    )
    RCompany: Mapped[str] = mapped_column("RCompany", String(255), nullable=False)
    Prefix: Mapped[str] = mapped_column("Prefix", String(50), nullable=False)
    LedgerMId: Mapped[Optional[int]] = mapped_column("LedgerMId", Integer, nullable=True)
    IsActive: Mapped[bool] = mapped_column(
        "IsActive", Boolean, nullable=False, default=True, server_default=text("1")
    )
    CreatedDate: Mapped[datetime] = mapped_column(
        "CreatedDate", DateTime, nullable=False, default=datetime.utcnow, server_default=text("CURRENT_TIMESTAMP")
    )


# ============================================================================
# 3. CORPORATE GROUP CLIENT MASTER (tbl_clientmaster)
# ============================================================================

class ClientMaster(Base):
    """
    Corporate B2B Client Master Registry Model.
    Physical Table: tbl_clientmaster
    Physical PK: ClientMasterId (legacy _ClientMasterId)
    Legacy Reference: API_ClientMaster (AllMaster.cs L3006),
                      BLL_Loan.BLL_InsertClientMaster,
                      DAL_Loan.DAL_InsertClientMaster,
                      sp_ClientMaster, sp_UpdateClientMaster
    """
    __tablename__ = "tbl_clientmaster"
    __table_args__ = (
        Index("ix_tbl_clientmaster_Description", "Description"),
        Index("ix_tbl_clientmaster_GST", "GST"),
        Index("ix_tbl_clientmaster_PanNo", "PanNo"),
        {
            "mysql_charset": "utf8",
            "mysql_collate": "utf8_general_ci",
            "mysql_row_format": "DYNAMIC",
        },
    )

    ClientMasterId: Mapped[int] = mapped_column(
        "ClientMasterId", Integer, primary_key=True, autoincrement=True
    )
    Description: Mapped[str] = mapped_column("Description", String(255), nullable=False)
    InsuranceCompanyId: Mapped[Optional[int]] = mapped_column(
        "InsuranceCompanyId", Integer, nullable=True
    )
    Address: Mapped[Optional[str]] = mapped_column("Address", String(500), nullable=True)
    PanNo: Mapped[Optional[str]] = mapped_column("PanNo", String(20), nullable=True)
    GST: Mapped[Optional[str]] = mapped_column("GST", String(50), nullable=True)
    CGST: Mapped[Decimal] = mapped_column(
        "CGST", Numeric(6, 2), nullable=False, default=Decimal("0.00"), server_default=text("0.00")
    )
    SGST: Mapped[Decimal] = mapped_column(
        "SGST", Numeric(6, 2), nullable=False, default=Decimal("0.00"), server_default=text("0.00")
    )
    IGST: Mapped[Decimal] = mapped_column(
        "IGST", Numeric(6, 2), nullable=False, default=Decimal("0.00"), server_default=text("0.00")
    )
    IsActive: Mapped[bool] = mapped_column(
        "IsActive", Boolean, nullable=False, default=True, server_default=text("1")
    )
    CreatedUser: Mapped[Optional[str]] = mapped_column("CreatedUser", String(100), nullable=True)
    Createdate: Mapped[datetime] = mapped_column(
        "Createdate", DateTime, nullable=False, default=datetime.utcnow, server_default=text("CURRENT_TIMESTAMP")
    )


# ============================================================================
# 4. MULTI-LINE COMMERCIAL SALES INVOICE DETAILS (tbl_salesregdetails)
# ============================================================================

class SalesRegDetails(Base):
    """
    Multi-Line Item Commercial Sales Invoicing Breakdown Model.
    Physical Table: tbl_salesregdetails
    Physical PK: SalesRegDetailId
    Legacy Reference: BLL_Loan.BLL_InsertSalesRegDetails,
                      DAL_Loan.DAL_InsertSalesRegDetails,
                      sp_InsertSalesRegDetails, adm_SalesRegistrationNew.aspx.cs
    """
    __tablename__ = "tbl_salesregdetails"
    __table_args__ = (
        Index("ix_tbl_salesregdetails_InvoiceId", "InvoiceId"),
        Index("ix_tbl_salesregdetails_InvoiceNo", "InvoiceNo"),
        {
            "mysql_charset": "utf8",
            "mysql_collate": "utf8_general_ci",
            "mysql_row_format": "DYNAMIC",
        },
    )

    SalesRegDetailId: Mapped[int] = mapped_column(
        "SalesRegDetailId", Integer, primary_key=True, autoincrement=True
    )
    InvoiceId: Mapped[int] = mapped_column("InvoiceId", Integer, nullable=False)
    InvoiceNo: Mapped[str] = mapped_column("InvoiceNo", String(100), nullable=False)
    SalesType: Mapped[Optional[str]] = mapped_column("SalesType", String(100), nullable=True)
    SalesTypeId: Mapped[Optional[int]] = mapped_column("SalesTypeId", Integer, nullable=True)
    TaxableAmt: Mapped[Decimal] = mapped_column(
        "TaxableAmt", Numeric(15, 2), nullable=False, default=Decimal("0.00"), server_default=text("0.00")
    )
    CGSTPre: Mapped[Decimal] = mapped_column(
        "CGSTPre", Numeric(6, 2), nullable=False, default=Decimal("0.00"), server_default=text("0.00")
    )
    CGSTAmt: Mapped[Decimal] = mapped_column(
        "CGSTAmt", Numeric(15, 2), nullable=False, default=Decimal("0.00"), server_default=text("0.00")
    )
    SGSTPre: Mapped[Decimal] = mapped_column(
        "SGSTPre", Numeric(6, 2), nullable=False, default=Decimal("0.00"), server_default=text("0.00")
    )
    SGSTAmt: Mapped[Decimal] = mapped_column(
        "SGSTAmt", Numeric(15, 2), nullable=False, default=Decimal("0.00"), server_default=text("0.00")
    )
    IGSTPre: Mapped[Decimal] = mapped_column(
        "IGSTPre", Numeric(6, 2), nullable=False, default=Decimal("0.00"), server_default=text("0.00")
    )
    IGSTAmt: Mapped[Decimal] = mapped_column(
        "IGSTAmt", Numeric(15, 2), nullable=False, default=Decimal("0.00"), server_default=text("0.00")
    )
    Total: Mapped[Decimal] = mapped_column(
        "Total", Numeric(15, 2), nullable=False, default=Decimal("0.00"), server_default=text("0.00")
    )


# ============================================================================
# 5. SISTER CONCERN ADVANCE DISBURSEMENT MASTER (tbl_companyadvancemaster)
# ============================================================================

class CompanyAdvanceMaster(Base):
    """
    Sister Concern & Insurer Advance Disbursement Facility Model.
    Physical Table: tbl_companyadvancemaster (legacy alias: tbl_companyadvmst)
    Physical PK: CompanyAdvId
    Legacy Reference: BLL_Loan.BLL_SelectCompanyAdvMst,
                      DAL_Loan.DAL_SelectCompanyAdvMst,
                      sp_SelectCompanyAdvMst, adm_SalesAdvReport.aspx
    """
    __tablename__ = "tbl_companyadvancemaster"
    __table_args__ = (
        Index("ix_tbl_companyadvancemaster_LedgerMID", "LedgerMID"),
        {
            "mysql_charset": "utf8",
            "mysql_collate": "utf8_general_ci",
            "mysql_row_format": "DYNAMIC",
        },
    )

    CompanyAdvId: Mapped[int] = mapped_column(
        "CompanyAdvId", Integer, primary_key=True, autoincrement=True
    )
    LedgerMID: Mapped[int] = mapped_column("LedgerMID", Integer, nullable=False)
    compAdvDate: Mapped[date] = mapped_column("compAdvDate", Date, nullable=False)
    Amount: Mapped[Decimal] = mapped_column(
        "Amount", Numeric(15, 2), nullable=False, default=Decimal("0.00"), server_default=text("0.00")
    )
    RecivingAmount: Mapped[Decimal] = mapped_column(
        "RecivingAmount", Numeric(15, 2), nullable=False, default=Decimal("0.00"), server_default=text("0.00")
    )
    BalanceAmt: Mapped[Decimal] = mapped_column(
        "BalanceAmt", Numeric(15, 2), nullable=False, default=Decimal("0.00"), server_default=text("0.00")
    )
    Description: Mapped[Optional[str]] = mapped_column("Description", String(500), nullable=True)
    CreatedUser: Mapped[Optional[str]] = mapped_column("CreatedUser", String(100), nullable=True)
    CreatedDate: Mapped[datetime] = mapped_column(
        "CreatedDate", DateTime, nullable=False, default=datetime.utcnow, server_default=text("CURRENT_TIMESTAMP")
    )


# ============================================================================
# 6. SISTER CONCERN ADVANCE RECOVERY HISTORY LOG (tbl_companyadvdetails)
# ============================================================================

class CompanyAdvDetail(Base):
    """
    Sister Concern Advance Recovery & Accounting Voucher History Model.
    Physical Table: tbl_companyadvdetails
    Physical PK: DetailId
    Legacy Reference: BLL_Loan.DAL_UpdateCompanyAdvMaster,
                      DAL_Loan.DAL_UpdateCompanyAdvMaster,
                      sp_UpdateCompanyAdvMaster, adm_VoucherEntry.aspx.cs L343,
                      sp_SelectSalesAdvReport("SelectDetails", id)
    """
    __tablename__ = "tbl_companyadvdetails"
    __table_args__ = (
        Index("ix_tbl_companyadvdetails_CompanyAdvId", "CompanyAdvId"),
        Index("ix_tbl_companyadvdetails_LedgerMID", "LedgerMID"),
        Index("ix_tbl_companyadvdetails_AccDocNo", "AccDocNo"),
        {
            "mysql_charset": "utf8",
            "mysql_collate": "utf8_general_ci",
            "mysql_row_format": "DYNAMIC",
        },
    )

    DetailId: Mapped[int] = mapped_column(
        "DetailId", Integer, primary_key=True, autoincrement=True
    )
    CompanyAdvId: Mapped[int] = mapped_column("CompanyAdvId", Integer, nullable=False)
    LedgerMID: Mapped[int] = mapped_column("LedgerMID", Integer, nullable=False)
    HistoryDate: Mapped[date] = mapped_column("HistoryDate", Date, nullable=False)
    SalesInvoiceId: Mapped[Optional[str]] = mapped_column("SalesInvoiceId", String(100), nullable=True)
    AccDocNo: Mapped[Optional[str]] = mapped_column("AccDocNo", String(100), nullable=True)
    Amount: Mapped[Decimal] = mapped_column(
        "Amount", Numeric(15, 2), nullable=False, default=Decimal("0.00"), server_default=text("0.00")
    )
    CreatedDate: Mapped[datetime] = mapped_column(
        "CreatedDate", DateTime, nullable=False, default=datetime.utcnow, server_default=text("CURRENT_TIMESTAMP")
    )


# ============================================================================
# 7. MONOTONIC SEQUENCE COUNTER FOR COMMERCIAL INVOICING (tbl_invoicesequence)
# ============================================================================

class InvoiceSequence(Base):
    """
    Atomic Monotonic Sequential Counter Generator for Commercial Invoicing.
    Physical Table: tbl_invoicesequence
    Physical PK: SequenceName
    Design Purpose: Replaces missing legacy sp_generatesalesregistrationInvoice
                    and eliminates concurrent collision race conditions.
    """
    __tablename__ = "tbl_invoicesequence"
    __table_args__ = {
        "mysql_charset": "utf8",
        "mysql_collate": "utf8_general_ci",
        "mysql_row_format": "DYNAMIC",
    }

    SequenceName: Mapped[str] = mapped_column("SequenceName", String(50), primary_key=True)
    CurrentValue: Mapped[int] = mapped_column(
        "CurrentValue", Integer, nullable=False, default=1000, server_default=text("1000")
    )
    UpdatedDate: Mapped[datetime] = mapped_column(
        "UpdatedDate", DateTime, nullable=False, default=datetime.utcnow, server_default=text("CURRENT_TIMESTAMP")
    )
