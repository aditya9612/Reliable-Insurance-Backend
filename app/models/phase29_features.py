"""
SQLAlchemy 2.0 Declarative Models for Phase 29:
Temporary Operator Role & Workload Delegation Master.
Physical Tables:
1. tbl_tempararyoperator (Temporary Operator Assignment & Delegation)
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import Integer, String, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class TemporaryOperator(Base):
    """
    Physical Table: tbl_tempararyoperator
    Primary Key: ID
    
    Tracks temporary operator delegations when a permanent data-entry operator
    is on leave, transferring transaction processing rights and queue visibility
    to a designated substitute operator for a specified validity window.
    
    Legacy Reference:
    - API: API_TempararyOperator (AllMaster.cs L2348-L2360)
    - Stored Procedure: Sp_TempararyOperator (DAL_Operations.cs L36511-L36556)
    - BLL: BLL_APPEntries.cs::BLL_TempararyOperator, BLL_selectTempararyOperator
    - UI/Page: Insurance/Clerk/adm_TemporaryOperator.aspx.cs
    """
    __tablename__ = "tbl_tempararyoperator"
    __table_args__ = (
        Index("ix_tbl_tempararyoperator_per_operator_id", "Per_OperatorId"),
        Index("ix_tbl_tempararyoperator_temp_operator_id", "Temp_OperatorId"),
        Index("ix_tbl_tempararyoperator_isdeleted", "isdeleted"),
        Index(
            "ix_tbl_tempararyoperator_active_lookup",
            "Per_OperatorId",
            "Temp_OperatorId",
            "isdeleted",
            "ValidFrom",
            "ValidUpTo",
        ),
        {
            "mysql_charset": "utf8",
            "mysql_collate": "utf8_general_ci",
            "mysql_row_format": "DYNAMIC",
        },
    )

    ID: Mapped[int] = mapped_column(
        "ID", Integer, primary_key=True, autoincrement=True
    )
    Per_OperatorId: Mapped[int] = mapped_column(
        "Per_OperatorId", Integer, nullable=False, index=True
    )
    Temp_OperatorId: Mapped[int] = mapped_column(
        "Temp_OperatorId", Integer, nullable=False, index=True
    )
    ValidFrom: Mapped[Optional[datetime]] = mapped_column(
        "ValidFrom", DateTime, nullable=True
    )
    ValidUpTo: Mapped[Optional[datetime]] = mapped_column(
        "ValidUpTo", DateTime, nullable=True
    )
    CreateUser: Mapped[Optional[str]] = mapped_column(
        "CreateUser", String(100), nullable=True
    )
    CreateDate: Mapped[Optional[datetime]] = mapped_column(
        "CreateDate", DateTime, nullable=True, default=datetime.utcnow
    )
    isdeleted: Mapped[int] = mapped_column(
        "isdeleted", Integer, nullable=False, default=0, index=True
    )
    UpdatedUser: Mapped[Optional[str]] = mapped_column(
        "UpdatedUser", String(100), nullable=True
    )
    UpdatedDate: Mapped[Optional[datetime]] = mapped_column(
        "UpdatedDate", DateTime, nullable=True
    )
