"""
SQLAlchemy 2.0 Declarative Models for Phase 14 — Reports, Dashboards, MIS, POSP Invoices & Targets.
Physical Tables:
- tbl_posp_invoice (POSP Agent Payout Invoicing & PDF Tracking)
- tbl_target (Employee & Sales Executive Targets & Achievement Tracking)
"""
from datetime import datetime, date
from decimal import Decimal
from typing import Optional
from sqlalchemy import Integer, String, Text, DateTime, Date, Numeric, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class PospInvoice(Base):
    """
    POSP & Agent Payout Invoice Model.
    Physical Table: tbl_posp_invoice
    Primary Key: InvoiceId
    """
    __tablename__ = "tbl_posp_invoice"
    __table_args__ = (
        UniqueConstraint("InvoiceNo", name="uk_tbl_posp_invoice_InvoiceNo"),
        Index("ix_tbl_posp_invoice_Agent_FY_Month", "AgentId", "FinancialYear", "Month"),
        Index("ix_tbl_posp_invoice_InvoiceDate", "InvoiceDate"),
        Index("ix_tbl_posp_invoice_Status", "Status"),
        {
            "mysql_charset": "utf8",
            "mysql_collate": "utf8_general_ci",
            "mysql_row_format": "DYNAMIC",
        },
    )

    InvoiceId: Mapped[int] = mapped_column("InvoiceId", Integer, primary_key=True, autoincrement=True)
    InvoiceNo: Mapped[str] = mapped_column("InvoiceNo", String(100), nullable=False, index=True)
    InvoiceDate: Mapped[date] = mapped_column("InvoiceDate", Date, nullable=False)
    AgentId: Mapped[int] = mapped_column("AgentId", Integer, nullable=False, index=True)
    AgentName: Mapped[str] = mapped_column("AgentName", String(255), nullable=False)
    POSPType: Mapped[str] = mapped_column("POSPType", String(50), nullable=False)  # 'DIRECT' / 'POSP'
    FinancialYear: Mapped[str] = mapped_column("FinancialYear", String(20), nullable=False, index=True)
    Month: Mapped[str] = mapped_column("Month", String(20), nullable=False)
    Amount: Mapped[Decimal] = mapped_column("Amount", Numeric(18, 2), nullable=False)  # Base taxable payout amount
    GSTAmt: Mapped[Decimal] = mapped_column("GSTAmt", Numeric(18, 2), nullable=False, default=Decimal("0.00"))  # 18% IGST if GST registered
    GrandTotal: Mapped[Decimal] = mapped_column("GrandTotal", Numeric(18, 2), nullable=False)  # Amount + GSTAmt
    TDSAmount: Mapped[Decimal] = mapped_column("TDSAmount", Numeric(18, 2), nullable=False, default=Decimal("0.00"))  # Section 194H 5%
    NetPayable: Mapped[Decimal] = mapped_column("NetPayable", Numeric(18, 2), nullable=False)  # GrandTotal - TDSAmount
    PdfPath: Mapped[Optional[str]] = mapped_column("PdfPath", String(500), nullable=True)  # Canonical StorageBackend key
    Status: Mapped[str] = mapped_column("Status", String(50), nullable=False, default="GENERATED")  # GENERATED, APPROVED, PAID, CANCELLED
    CreatedDate: Mapped[datetime] = mapped_column("CreatedDate", DateTime, nullable=False, default=datetime.utcnow)
    CreatedBy: Mapped[str] = mapped_column("CreatedBy", String(100), nullable=False)


class Target(Base):
    """
    Sales Executive & Telecaller Monthly Target and Quota Model.
    Physical Table: tbl_target
    Primary Key: TargetId
    """
    __tablename__ = "tbl_target"
    __table_args__ = (
        Index("ix_tbl_target_Emp_FY_Month", "EmpId", "FinancialYear", "Month"),
        Index("ix_tbl_target_FinancialYear", "FinancialYear"),
        {
            "mysql_charset": "utf8",
            "mysql_collate": "utf8_general_ci",
            "mysql_row_format": "DYNAMIC",
        },
    )

    TargetId: Mapped[int] = mapped_column("TargetId", Integer, primary_key=True, autoincrement=True)
    EmpId: Mapped[int] = mapped_column("EmpId", Integer, nullable=False, index=True)
    FinancialYear: Mapped[str] = mapped_column("FinancialYear", String(20), nullable=False, index=True)
    Month: Mapped[str] = mapped_column("Month", String(20), nullable=False)
    TargetMonth: Mapped[Optional[str]] = mapped_column("TargetMonth", String(20), nullable=True)
    TargetAmount: Mapped[Decimal] = mapped_column("TargetAmount", Numeric(18, 2), nullable=False, default=Decimal("0.00"))  # assignamnt
    AchievedTargetAmount: Mapped[Decimal] = mapped_column("AchievedTargetAmount", Numeric(18, 2), nullable=False, default=Decimal("0.00"))
    HealthInsuranceAmount: Mapped[Decimal] = mapped_column("HealthInsuranceAmount", Numeric(18, 2), nullable=False, default=Decimal("0.00"))
    AnnualAmount: Mapped[Optional[Decimal]] = mapped_column("AnnualAmount", Numeric(18, 2), nullable=True, default=Decimal("0.00"))
    CreatedDate: Mapped[datetime] = mapped_column("CreatedDate", DateTime, nullable=False, default=datetime.utcnow)
    CreatedBy: Mapped[Optional[str]] = mapped_column("CreatedBy", String(100), nullable=True)
    UpdatedDate: Mapped[Optional[datetime]] = mapped_column("UpdatedDate", DateTime, nullable=True)
    UpdatedBy: Mapped[Optional[str]] = mapped_column("UpdatedBy", String(100), nullable=True)
