"""
SQLAlchemy 2.0 Declarative Models for Phase 13 Block E — Renewal Engine & Telecaller CRM.
Physical Table: tbl_preyearrenewalstatus
Preserves all 14 legacy attributes from API_PreYearRenewalStatus and Sp_InsertFollowPreYearRenewalStatus.
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import Integer, String, Text, DateTime, Double, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class PolicyRenewalStatus(Base):
    """
    Policy Renewal Status & Telecaller Follow-Up CRM Model.
    Physical Table: tbl_preyearrenewalstatus
    Primary Key: Id
    """
    __tablename__ = "tbl_preyearrenewalstatus"
    __table_args__ = (
        Index("ix_tbl_preyearrenewalstatus_RegNo_FY", "RegistrationNo", "FinancialYear"),
        Index("ix_tbl_preyearrenewalstatus_TransanctionId", "TransanctionId"),
        Index("ix_tbl_preyearrenewalstatus_ExpiryDate", "ExpiryDate"),
        Index("ix_tbl_preyearrenewalstatus_FollowupDate", "FollowupDate"),
        Index("ix_tbl_preyearrenewalstatus_AgentId", "AgentId"),
        Index("ix_tbl_preyearrenewalstatus_ExecutiveId", "ExecutiveId"),
        Index("ix_tbl_preyearrenewalstatus_BranchId", "BranchId"),
        Index("ix_tbl_preyearrenewalstatus_RenewalStatus", "RenewalStatus"),
        {
            "mysql_charset": "utf8",
            "mysql_collate": "utf8_general_ci",
            "mysql_row_format": "DYNAMIC",
        },
    )

    Id: Mapped[int] = mapped_column("Id", Integer, primary_key=True, autoincrement=True)
    TransanctionId: Mapped[int] = mapped_column("TransanctionId", Integer, nullable=False, index=True)
    Remark: Mapped[Optional[str]] = mapped_column("Remark", Text, nullable=True)
    FinancialYear: Mapped[str] = mapped_column("FinancialYear", String(20), nullable=False, index=True)
    isdeleted: Mapped[int] = mapped_column("isdeleted", Integer, default=0, nullable=False)
    CreatedDate: Mapped[datetime] = mapped_column("CreatedDate", DateTime, default=datetime.utcnow, nullable=False)
    RegistrationNo: Mapped[str] = mapped_column("RegistrationNo", String(50), nullable=False, index=True)
    InsuranceCompany: Mapped[Optional[str]] = mapped_column("InsuranceCompany", String(255), nullable=True)
    TotalPremium: Mapped[float] = mapped_column("TotalPremium", Double, default=0.0, nullable=False)
    MobileNo: Mapped[Optional[str]] = mapped_column("MobileNo", String(50), nullable=True)
    ExpiryDate: Mapped[datetime] = mapped_column("ExpiryDate", DateTime, nullable=False, index=True)
    FollowupDate: Mapped[Optional[datetime]] = mapped_column("FollowupDate", DateTime, nullable=True, index=True)
    UserRoleId: Mapped[int] = mapped_column("UserRoleId", Integer, default=0, nullable=False)
    AgentId: Mapped[int] = mapped_column("AgentId", Integer, default=0, nullable=False, index=True)
    ExecutiveId: Mapped[int] = mapped_column("ExecutiveId", Integer, default=0, nullable=False, index=True)

    # Operational lifecycle and tenancy attributes
    RenewalStatus: Mapped[str] = mapped_column("RenewalStatus", String(50), default="Follow", nullable=False)
    BranchId: Mapped[Optional[int]] = mapped_column("BranchId", Integer, default=0, nullable=True)
    UpdatedDate: Mapped[Optional[datetime]] = mapped_column("UpdatedDate", DateTime, default=datetime.utcnow, nullable=True)
    UpdatedBy: Mapped[Optional[str]] = mapped_column("UpdatedBy", String(100), nullable=True)


class RenewalFollowupHistory(Base):
    """
    Additive audit trail capturing each telecaller remark and scheduled callback timestamp.
    Physical Table: tbl_renewal_followup_history
    """
    __tablename__ = "tbl_renewal_followup_history"
    __table_args__ = (
        Index("ix_tbl_renewal_history_renewal_status_id", "renewal_status_id"),
        {
            "mysql_charset": "utf8",
            "mysql_collate": "utf8_general_ci",
            "mysql_row_format": "DYNAMIC",
        },
    )

    id: Mapped[int] = mapped_column("id", Integer, primary_key=True, autoincrement=True)
    renewal_status_id: Mapped[int] = mapped_column("renewal_status_id", Integer, nullable=False)
    remark: Mapped[str] = mapped_column("remark", Text, nullable=False)
    followup_date: Mapped[Optional[datetime]] = mapped_column("followup_date", DateTime, nullable=True)
    status_at_time: Mapped[str] = mapped_column("status_at_time", String(50), default="Follow", nullable=False)
    recorded_by: Mapped[str] = mapped_column("recorded_by", String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column("created_at", DateTime, default=datetime.utcnow, nullable=False)
