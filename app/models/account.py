from decimal import Decimal
from datetime import datetime, date
from typing import Optional
from sqlalchemy import Integer, String, Text, DateTime, Date, Double, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class Account(Base):
    """
    Double-Entry Financial Ledger Account Entry Model
    Physical Table: tbl_account
    Physical PK: AccountId
    Verified Column Count: 24
    Physical Foreign Keys: 0 (Enforced at application layer)
    """
    __tablename__ = "tbl_account"
    __table_args__ = {
        "mysql_charset": "utf8",
        "mysql_collate": "utf8_general_ci",
        "mysql_row_format": "DYNAMIC",
    }

    AccountId: Mapped[int] = mapped_column("AccountId", Integer, primary_key=True, autoincrement=True)
    AccTransId: Mapped[Optional[int]] = mapped_column("AccTransId", Integer, nullable=True)
    AccountDate: Mapped[Optional[datetime]] = mapped_column("AccountDate", DateTime, nullable=True)
    LedgerMId: Mapped[Optional[int]] = mapped_column("LedgerMId", Integer, nullable=True)
    amount: Mapped[Optional[Decimal]] = mapped_column("amount", Double(asdecimal=True), nullable=True)
    Narration: Mapped[Optional[str]] = mapped_column("Narration", String(500), nullable=True)
    ReferenceCustId: Mapped[Optional[int]] = mapped_column("ReferenceCustId", Integer, nullable=True)
    ReferenceAgentId: Mapped[Optional[int]] = mapped_column("ReferenceAgentId", Integer, nullable=True)
    BranchId: Mapped[Optional[int]] = mapped_column("BranchId", Integer, nullable=True)
    Extra1: Mapped[Optional[str]] = mapped_column("Extra1", String(255), nullable=True)
    Extra2: Mapped[Optional[str]] = mapped_column("Extra2", String(255), nullable=True)
    Doc_No: Mapped[Optional[int]] = mapped_column("Doc_No", Integer, nullable=True)
    CreatedUser: Mapped[Optional[str]] = mapped_column("CreatedUser", String(255), nullable=True)
    CreatedDate: Mapped[Optional[datetime]] = mapped_column("CreatedDate", DateTime, nullable=True)
    UpdatedUser: Mapped[Optional[str]] = mapped_column("UpdatedUser", String(255), nullable=True)
    UpdatedDate: Mapped[Optional[datetime]] = mapped_column("UpdatedDate", DateTime, nullable=True)
    PaymentType: Mapped[Optional[str]] = mapped_column("PaymentType", String(255), nullable=True)
    isdeleted: Mapped[Optional[int]] = mapped_column("isdeleted", Integer, nullable=True)
    IsNill: Mapped[int] = mapped_column("IsNill", Integer, nullable=False)
    TransactionId: Mapped[int] = mapped_column("TransactionId", Integer, nullable=False)
    CustVehId: Mapped[int] = mapped_column("CustVehId", Integer, nullable=False)
    MonthId: Mapped[int] = mapped_column("MonthId", Integer, nullable=False)
    EndorsementId: Mapped[int] = mapped_column("EndorsementId", Integer, nullable=False)
    TransId: Mapped[int] = mapped_column("TransId", Integer, nullable=False)
