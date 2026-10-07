from decimal import Decimal
from datetime import datetime, date
from typing import Optional
from sqlalchemy import Integer, String, Text, DateTime, Date, Double, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class TransactionPayment(Base):
    """
    Policy Transaction Payment Instrument Tracking Model
    Physical Table: tbl_transactionpayment
    Physical PK: PaymentId
    Verified Column Count: 23
    Physical Foreign Keys: 0 (Enforced at application layer)
    """
    __tablename__ = "tbl_transactionpayment"
    __table_args__ = {
        "mysql_charset": "utf8",
        "mysql_collate": "utf8_general_ci",
        "mysql_row_format": "DYNAMIC",
    }

    PaymentId: Mapped[int] = mapped_column("PaymentId", Integer, primary_key=True, autoincrement=True)
    PaymentDate: Mapped[Optional[datetime]] = mapped_column("PaymentDate", DateTime, nullable=True)
    PaymentType: Mapped[Optional[str]] = mapped_column("PaymentType", String(255), nullable=True)
    PaymentDetails: Mapped[Optional[str]] = mapped_column("PaymentDetails", String(255), nullable=True)
    bankname: Mapped[Optional[str]] = mapped_column("bankname", String(255), nullable=True)
    docno: Mapped[Optional[str]] = mapped_column("docno", String(255), nullable=True)
    PaidAmount: Mapped[Optional[Decimal]] = mapped_column("PaidAmount", Double(asdecimal=True), nullable=True)
    CashierApproval: Mapped[Optional[int]] = mapped_column("CashierApproval", Integer, nullable=True)
    CashierApprovalDate: Mapped[Optional[datetime]] = mapped_column("CashierApprovalDate", DateTime, nullable=True)
    AccountantApproval: Mapped[Optional[int]] = mapped_column("AccountantApproval", Integer, nullable=True)
    AccountantApprovalDate: Mapped[Optional[datetime]] = mapped_column("AccountantApprovalDate", DateTime, nullable=True)
    OwnerApproval: Mapped[Optional[int]] = mapped_column("OwnerApproval", Integer, nullable=True)
    OwnerApprovalDate: Mapped[Optional[datetime]] = mapped_column("OwnerApprovalDate", DateTime, nullable=True)
    BranchId: Mapped[Optional[int]] = mapped_column("BranchId", Integer, nullable=True)
    TransanctionId: Mapped[Optional[int]] = mapped_column("TransanctionId", Integer, nullable=True)
    Extra1: Mapped[Optional[str]] = mapped_column("Extra1", String(255), nullable=True)
    Extra2: Mapped[Optional[str]] = mapped_column("Extra2", String(255), nullable=True)
    isdeleted: Mapped[Optional[str]] = mapped_column("isdeleted", String(255), nullable=True)
    CreateUser: Mapped[Optional[str]] = mapped_column("CreateUser", String(255), nullable=True)
    CreateDate: Mapped[Optional[datetime]] = mapped_column("CreateDate", DateTime, nullable=True)
    UpdateDate: Mapped[Optional[datetime]] = mapped_column("UpdateDate", DateTime, nullable=True)
    UpdateUser: Mapped[Optional[str]] = mapped_column("UpdateUser", String(255), nullable=True)
    isCompletePayment: Mapped[int] = mapped_column("isCompletePayment", Integer, nullable=False)
