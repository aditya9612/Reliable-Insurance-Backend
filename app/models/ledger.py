from decimal import Decimal
from datetime import datetime, date
from typing import Optional
from sqlalchemy import Integer, String, Text, DateTime, Date, Double, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class LedgerMaster(Base):
    """
    Chart of Accounts / Master Ledger Definition Model
    Physical Table: tbl_ledgermaster
    Physical PK: LedgerMId
    Verified Column Count: 11
    Physical Foreign Keys: 0 (Enforced at application layer)
    """
    __tablename__ = "tbl_ledgermaster"
    __table_args__ = {
        "mysql_charset": "utf8",
        "mysql_collate": "utf8_general_ci",
        "mysql_row_format": "DYNAMIC",
    }

    LedgerMId: Mapped[int] = mapped_column("LedgerMId", Integer, primary_key=True, autoincrement=True)
    LedgerTypeId: Mapped[Optional[int]] = mapped_column("LedgerTypeId", Integer, nullable=True)
    LedgerName: Mapped[Optional[str]] = mapped_column("LedgerName", String(255), nullable=True)
    LedgerGroupId: Mapped[Optional[int]] = mapped_column("LedgerGroupId", Integer, nullable=True)
    ReferenceId: Mapped[Optional[int]] = mapped_column("ReferenceId", Integer, nullable=True)
    BranchId: Mapped[Optional[int]] = mapped_column("BranchId", Integer, nullable=True)
    isdeleted: Mapped[Optional[str]] = mapped_column("isdeleted", String(255), nullable=True)
    CreateUser: Mapped[Optional[str]] = mapped_column("CreateUser", String(255), nullable=True)
    CreateDate: Mapped[Optional[datetime]] = mapped_column("CreateDate", DateTime, nullable=True)
    UpdateUser: Mapped[Optional[str]] = mapped_column("UpdateUser", String(255), nullable=True)
    UpdateDate: Mapped[Optional[datetime]] = mapped_column("UpdateDate", DateTime, nullable=True)
