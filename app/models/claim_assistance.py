"""
SQLAlchemy 2.0 Declarative Models for Phase 26 — Emergency Roadside Claim Assistance & Accident Intake.
Physical Tables:
1. tbl_claimassistance (Emergency Accident Intimation & Assistance Requests)
2. tbl_claimassistanceimg (Accident Scene & Vehicle Damage Photographic Evidence)
"""
from datetime import datetime
from typing import Optional, List
from sqlalchemy import Integer, String, Text, DateTime, ForeignKey, Index, text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class ClaimAssistance(Base):
    """
    Emergency Roadside Claim Assistance & Accident Intimation Model.
    Physical Table: tbl_claimassistance
    Primary Key: ClaimAssistanceId
    
    Captures immediate roadside accident details, driver information, towing garage,
    and links to formal claim numbers upon backoffice operator processing.
    """
    __tablename__ = "tbl_claimassistance"
    __table_args__ = (
        Index("ix_tbl_claimassistance_veh_no", "VehNo"),
        Index("ix_tbl_claimassistance_claim_no", "ClaimNo"),
        Index("ix_tbl_claimassistance_company_id", "InsuranceCompanyId"),
        Index("ix_tbl_claimassistance_intimation_date", "IntimationDate"),
        Index("ix_tbl_claimassistance_status", "Status"),
        Index("ix_tbl_claimassistance_read_status", "ReadStatus"),
        Index("ix_tbl_claimassistance_isdeleted", "isdeleted"),
        {
            "mysql_charset": "utf8",
            "mysql_collate": "utf8_general_ci",
            "mysql_row_format": "DYNAMIC",
        },
    )

    ClaimAssistanceId: Mapped[int] = mapped_column(
        "ClaimAssistanceId", Integer, primary_key=True, autoincrement=True
    )
    CustomerId: Mapped[Optional[int]] = mapped_column(
        "CustomerId", Integer, nullable=True, index=True
    )
    InsuranceCompanyId: Mapped[int] = mapped_column(
        "InsuranceCompanyId", Integer, nullable=False, index=True
    )
    IntimationDate: Mapped[datetime] = mapped_column(
        "IntimationDate", DateTime, nullable=False, default=datetime.utcnow
    )
    VehNo: Mapped[str] = mapped_column(
        "VehNo", String(50), nullable=False
    )
    DateofAccident: Mapped[datetime] = mapped_column(
        "DateofAccident", DateTime, nullable=False
    )
    Accidenttime: Mapped[Optional[str]] = mapped_column(
        "Accidenttime", String(50), nullable=True
    )
    spot: Mapped[Optional[str]] = mapped_column(
        "spot", String(255), nullable=True
    )
    Reason: Mapped[Optional[str]] = mapped_column(
        "Reason", Text, nullable=True
    )
    DriverName: Mapped[Optional[str]] = mapped_column(
        "DriverName", String(150), nullable=True
    )
    DriverLicenseNo: Mapped[Optional[str]] = mapped_column(
        "DriverLicenseNo", String(100), nullable=True
    )
    GarageName: Mapped[Optional[str]] = mapped_column(
        "GarageName", String(200), nullable=True
    )
    GarageAddr: Mapped[Optional[str]] = mapped_column(
        "GarageAddr", String(500), nullable=True
    )
    Garagecontact: Mapped[Optional[str]] = mapped_column(
        "Garagecontact", String(50), nullable=True
    )

    # Resolution & formal claim linkage
    ClaimNo: Mapped[Optional[str]] = mapped_column(
        "ClaimNo", String(100), nullable=True
    )
    ClaimNoUpdateDate: Mapped[Optional[datetime]] = mapped_column(
        "ClaimNoUpdateDate", DateTime, nullable=True
    )
    ClaimNoUpdateUser: Mapped[Optional[str]] = mapped_column(
        "ClaimNoUpdateUser", String(100), nullable=True
    )

    # Operational lifecycle and tenancy tracking
    Status: Mapped[str] = mapped_column(
        "Status", String(50), nullable=False, default="INTIMATED"
    )
    ReadStatus: Mapped[int] = mapped_column(
        "ReadStatus", Integer, nullable=False, default=0
    )
    isdeleted: Mapped[int] = mapped_column(
        "isdeleted", Integer, nullable=False, default=0
    )
    BranchId: Mapped[Optional[int]] = mapped_column(
        "BranchId", Integer, nullable=True, default=101, index=True
    )
    AgentId: Mapped[Optional[int]] = mapped_column(
        "AgentId", Integer, nullable=True, default=0, index=True
    )
    SalesExId: Mapped[Optional[int]] = mapped_column(
        "SalesExId", Integer, nullable=True, default=0
    )

    CreatedDate: Mapped[datetime] = mapped_column(
        "CreatedDate", DateTime, nullable=False, default=datetime.utcnow
    )
    CreatedUser: Mapped[Optional[str]] = mapped_column(
        "CreatedUser", String(100), nullable=True
    )
    UpdatedDate: Mapped[Optional[datetime]] = mapped_column(
        "UpdatedDate", DateTime, nullable=True, default=datetime.utcnow, onupdate=datetime.utcnow
    )
    UpdatedUser: Mapped[Optional[str]] = mapped_column(
        "UpdatedUser", String(100), nullable=True
    )

    # Photographic damage evidence relationship
    images: Mapped[List["ClaimAssistanceImg"]] = relationship(
        "ClaimAssistanceImg",
        back_populates="assistance",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class ClaimAssistanceImg(Base):
    """
    Accident Scene & Vehicle Damage Photographic Evidence Model.
    Physical Table: tbl_claimassistanceimg
    Primary Key: ClaimAssistanceImgId
    """
    __tablename__ = "tbl_claimassistanceimg"
    __table_args__ = (
        Index("ix_tbl_claimassistanceimg_assistance_id", "ClaimAssistanceId"),
        {
            "mysql_charset": "utf8",
            "mysql_collate": "utf8_general_ci",
            "mysql_row_format": "DYNAMIC",
        },
    )

    ClaimAssistanceImgId: Mapped[int] = mapped_column(
        "ClaimAssistanceImgId", Integer, primary_key=True, autoincrement=True
    )
    ClaimAssistanceId: Mapped[int] = mapped_column(
        "ClaimAssistanceId",
        Integer,
        ForeignKey("tbl_claimassistance.ClaimAssistanceId", ondelete="CASCADE"),
        nullable=False,
    )
    ImgPath: Mapped[str] = mapped_column(
        "ImgPath", String(500), nullable=False
    )
    CreatedDate: Mapped[datetime] = mapped_column(
        "CreatedDate", DateTime, nullable=False, default=datetime.utcnow
    )

    assistance: Mapped["ClaimAssistance"] = relationship(
        "ClaimAssistance", back_populates="images"
    )
