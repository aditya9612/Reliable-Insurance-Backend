"""
SQLAlchemy 2.0 Declarative Models for Phase 27 — Company Outstanding Premium Remittance & Cash-to-Bank Deposit Settlement Engine.
Physical Tables:
1. tbl_debitfrombankaccount (Remittance & Cash-to-Bank Settlement Audit Journal)
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional
from sqlalchemy import Integer, String, Text, DateTime, Double, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class BankDebitRemittance(Base):
    """
    Physical Table: tbl_debitfrombankaccount
    Primary Key: Account_Id (mapped to DebitAccountId)
    
    Settlement audit journal recording premium remittances to insurance companies
    and branch cash deposits into company bank accounts.
    """
    __tablename__ = "tbl_debitfrombankaccount"
    __table_args__ = (
        Index("ix_tbl_debitfrombankaccount_trans_id", "TransactionId"),
        Index("ix_tbl_debitfrombankaccount_ledger_m_id", "LedgerMId"),
        Index("ix_tbl_debitfrombankaccount_branch_id", "BranchId"),
        Index("ix_tbl_debitfrombankaccount_doc_no", "Doc_No"),
        Index("ix_tbl_debitfrombankaccount_flag", "Flag"),
        Index("ix_tbl_debitfrombankaccount_account_date", "AccountDate"),
        Index("ix_tbl_debitfrombankaccount_isdeleted", "isdeleted"),
        {
            "mysql_charset": "utf8",
            "mysql_collate": "utf8_general_ci",
            "mysql_row_format": "DYNAMIC",
        },
    )

    DebitAccountId: Mapped[int] = mapped_column(
        "Account_Id", Integer, primary_key=True, autoincrement=True
    )
    TransactionId: Mapped[Optional[int]] = mapped_column(
        "TransactionId", Integer, nullable=True, index=True
    )
    LedgerMId: Mapped[Optional[int]] = mapped_column(
        "LedgerMId", Integer, nullable=True, index=True
    )
    BranchId: Mapped[int] = mapped_column(
        "BranchId", Integer, nullable=False, default=101, index=True
    )
    Doc_No: Mapped[Optional[str]] = mapped_column(
        "Doc_No", String(50), nullable=True, index=True
    )
    Amount: Mapped[Decimal] = mapped_column(
        "Amount", Double(asdecimal=True), nullable=False
    )
    AccountDate: Mapped[datetime] = mapped_column(
        "AccountDate", DateTime, nullable=False, default=datetime.utcnow
    )
    Narration: Mapped[Optional[str]] = mapped_column(
        "Narration", String(500), nullable=True
    )
    Flag: Mapped[str] = mapped_column(
        "Flag", String(50), nullable=False, default="Company", index=True
    )
    CompanyChequeNo: Mapped[Optional[str]] = mapped_column(
        "CompanyChequeNo", String(50), nullable=True
    )
    Extra1: Mapped[Optional[str]] = mapped_column(
        "Extra1", String(255), nullable=True
    )
    Extra2: Mapped[Optional[str]] = mapped_column(
        "Extra2", String(255), nullable=True
    )
    isdeleted: Mapped[int] = mapped_column(
        "isdeleted", Integer, nullable=False, default=0, index=True
    )
    CreatedUser: Mapped[Optional[str]] = mapped_column(
        "CreatedUser", String(100), nullable=True
    )
    CreatedDate: Mapped[Optional[datetime]] = mapped_column(
        "CreatedDate", DateTime, nullable=True, default=datetime.utcnow
    )
    UpdatedUser: Mapped[Optional[str]] = mapped_column(
        "UpdatedUser", String(100), nullable=True
    )
    UpdatedDate: Mapped[Optional[datetime]] = mapped_column(
        "UpdatedDate", DateTime, nullable=True
    )
