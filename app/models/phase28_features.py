"""
SQLAlchemy 2.0 Declarative Models for Phase 28:
Franchise Agent Grid Margin Override Engine.
Physical Tables:
1. tbl_franchisegridmargin (Franchise Agent Custom Commission Margin Overrides)
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional
from sqlalchemy import Integer, String, DateTime, Double, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class FranchiseGridMargin(Base):
    """
    Physical Table: tbl_franchisegridmargin
    Primary Key: Id
    
    Stores commission margin percentages retained by the Franchise for policies
    issued by sub-agents under that franchise for specific insurance companies
    and policy types.
    
    Legacy Reference:
    - API: API_FranchaiseGridMargin (AllMaster.cs L3133-L3142)
    - Stored Procedure: sp_franchsieGridMargin (DAL_Operations.cs L43520-L43577)
    - UI/Page: Insurance/Clerk/adm_FranchiseGridMargin.aspx.cs
    - Commission Calculation: AgentCommissionRecalculation.aspx.cs L1577-L1609, L1869-L1895
    """
    __tablename__ = "tbl_franchisegridmargin"
    __table_args__ = (
        Index("ix_tbl_franchisegridmargin_franchise_id", "FranchiseId"),
        Index("ix_tbl_franchisegridmargin_agent_id", "FranchiseAgentId"),
        Index("ix_tbl_franchisegridmargin_company_id", "InsuranceCompanyId"),
        Index("ix_tbl_franchisegridmargin_policy_type_id", "PolicyTypeId"),
        Index("ix_tbl_franchisegridmargin_isdeleted", "isdeleted"),
        Index(
            "ix_tbl_franchisegridmargin_lookup",
            "FranchiseId",
            "FranchiseAgentId",
            "InsuranceCompanyId",
            "PolicyTypeId",
            "isdeleted",
        ),
        {
            "mysql_charset": "utf8",
            "mysql_collate": "utf8_general_ci",
            "mysql_row_format": "DYNAMIC",
        },
    )

    Id: Mapped[int] = mapped_column(
        "Id", Integer, primary_key=True, autoincrement=True
    )
    FranchiseId: Mapped[int] = mapped_column(
        "FranchiseId", Integer, nullable=False, index=True
    )
    FranchiseAgentId: Mapped[int] = mapped_column(
        "FranchiseAgentId", Integer, nullable=False, index=True
    )
    InsuranceCompanyId: Mapped[int] = mapped_column(
        "InsuranceCompanyId", Integer, nullable=False, index=True
    )
    PolicyTypeId: Mapped[int] = mapped_column(
        "PolicyTypeId", Integer, nullable=False, index=True
    )
    margin: Mapped[Decimal] = mapped_column(
        "margin", Double(asdecimal=True), nullable=False, default=Decimal("0.00")
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
