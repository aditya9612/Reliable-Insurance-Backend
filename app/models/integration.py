"""
SQLAlchemy 2.0 Declarative Models for Phase 13 Block A — Vehicle RC & KYC Integration.
Physical Table: tbl_vehiclenorc_details
Preserves all 54 legacy attributes from API_vehiclenorc_details and sp_InsertRCAPIDetails.
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import Integer, String, Text, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class VehicleRCDetails(Base):
    """
    Vehicle Registration Certificate (RC) & KYC Details Local Cache Model.
    Physical Table: tbl_vehiclenorc_details
    Primary Key: VehRcId
    """
    __tablename__ = "tbl_vehiclenorc_details"
    __table_args__ = (
        Index("ix_tbl_vehiclenorc_details_RegNo", "license_plate_RegNo", unique=True),
        Index("ix_tbl_vehiclenorc_details_request_id", "request_id"),
        Index("ix_tbl_vehiclenorc_details_chassis", "chassis_number"),
        Index("ix_tbl_vehiclenorc_details_engine", "engine_number"),
        Index("ix_tbl_vehiclenorc_details_insurance_expiry", "insurance_expiry"),
        {
            "mysql_charset": "utf8",
            "mysql_collate": "utf8_general_ci",
            "mysql_row_format": "DYNAMIC",
        },
    )

    VehRcId: Mapped[int] = mapped_column("VehRcId", Integer, primary_key=True, autoincrement=True)
    request_id: Mapped[Optional[str]] = mapped_column("request_id", String(100), nullable=True)
    license_plate_RegNo: Mapped[str] = mapped_column("license_plate_RegNo", String(50), nullable=False)
    owner_name: Mapped[Optional[str]] = mapped_column("owner_name", String(255), nullable=True)
    father_name: Mapped[Optional[str]] = mapped_column("father_name", String(255), nullable=True)
    is_financed: Mapped[Optional[str]] = mapped_column("is_financed", String(50), nullable=True)
    financer: Mapped[Optional[str]] = mapped_column("financer", String(255), nullable=True)
    present_address: Mapped[Optional[str]] = mapped_column("present_address", Text, nullable=True)
    permanent_address: Mapped[Optional[str]] = mapped_column("permanent_address", Text, nullable=True)
    insurance_company: Mapped[Optional[str]] = mapped_column("insurance_company", String(255), nullable=True)
    insurance_policy: Mapped[Optional[str]] = mapped_column("insurance_policy", String(100), nullable=True)
    insurance_expiry: Mapped[Optional[datetime]] = mapped_column("insurance_expiry", DateTime, nullable=True)
    rc_class: Mapped[Optional[str]] = mapped_column("rc_class", String(100), nullable=True)
    category: Mapped[Optional[str]] = mapped_column("category", String(100), nullable=True)
    registration_date: Mapped[Optional[datetime]] = mapped_column("registration_date", DateTime, nullable=True)
    vehicle_age: Mapped[Optional[str]] = mapped_column("vehicle_age", String(100), nullable=True)
    pucc_upto: Mapped[Optional[datetime]] = mapped_column("pucc_upto", DateTime, nullable=True)
    pucc_number: Mapped[Optional[str]] = mapped_column("pucc_number", String(100), nullable=True)
    chassis_number: Mapped[Optional[str]] = mapped_column("chassis_number", String(100), nullable=True)
    engine_number: Mapped[Optional[str]] = mapped_column("engine_number", String(100), nullable=True)
    fuel_type: Mapped[Optional[str]] = mapped_column("fuel_type", String(50), nullable=True)
    brand_name: Mapped[Optional[str]] = mapped_column("brand_name", String(100), nullable=True)
    brand_model: Mapped[Optional[str]] = mapped_column("brand_model", String(100), nullable=True)
    body_type: Mapped[Optional[str]] = mapped_column("body_type", String(100), nullable=True)
    cubic_capacity: Mapped[Optional[str]] = mapped_column("cubic_capacity", String(50), nullable=True)
    gross_weight: Mapped[Optional[str]] = mapped_column("gross_weight", String(50), nullable=True)
    cylinders: Mapped[Optional[str]] = mapped_column("cylinders", String(50), nullable=True)
    color: Mapped[Optional[str]] = mapped_column("color", String(50), nullable=True)
    norms: Mapped[Optional[str]] = mapped_column("norms", String(50), nullable=True)
    fit_up_to: Mapped[Optional[str]] = mapped_column("fit_up_to", String(50), nullable=True)
    manufacturing_date: Mapped[Optional[str]] = mapped_column("manufacturing_date", String(50), nullable=True)
    manufacturing_date_formatted: Mapped[Optional[str]] = mapped_column("manufacturing_date_formatted", String(50), nullable=True)
    rto_name: Mapped[Optional[str]] = mapped_column("rto_name", String(100), nullable=True)
    latest_by: Mapped[Optional[str]] = mapped_column("latest_by", String(100), nullable=True)
    sleeper_capacity: Mapped[Optional[str]] = mapped_column("sleeper_capacity", String(50), nullable=True)
    standing_capacity: Mapped[Optional[str]] = mapped_column("standing_capacity", String(50), nullable=True)
    wheelbase: Mapped[Optional[str]] = mapped_column("wheelbase", String(50), nullable=True)
    unladen_weight: Mapped[Optional[str]] = mapped_column("unladen_weight", String(50), nullable=True)
    noc_details: Mapped[Optional[str]] = mapped_column("noc_details", String(100), nullable=True)
    seating_capacity: Mapped[Optional[str]] = mapped_column("seating_capacity", String(50), nullable=True)
    owner_count: Mapped[Optional[str]] = mapped_column("owner_count", String(50), nullable=True)
    tax_upto: Mapped[Optional[str]] = mapped_column("tax_upto", String(50), nullable=True)
    tax_paid_upto: Mapped[Optional[str]] = mapped_column("tax_paid_upto", String(50), nullable=True)
    permit_number: Mapped[Optional[str]] = mapped_column("permit_number", String(100), nullable=True)
    permit_issue_date: Mapped[Optional[str]] = mapped_column("permit_issue_date", String(50), nullable=True)
    permit_valid_from: Mapped[Optional[str]] = mapped_column("permit_valid_from", String(50), nullable=True)
    permit_valid_upto: Mapped[Optional[str]] = mapped_column("permit_valid_upto", String(50), nullable=True)
    permit_type: Mapped[Optional[str]] = mapped_column("permit_type", String(100), nullable=True)
    national_permit_number: Mapped[Optional[str]] = mapped_column("national_permit_number", String(100), nullable=True)
    national_permit_upto: Mapped[Optional[str]] = mapped_column("national_permit_upto", String(50), nullable=True)
    national_permit_issued_by: Mapped[Optional[str]] = mapped_column("national_permit_issued_by", String(100), nullable=True)
    rc_status: Mapped[Optional[str]] = mapped_column("rc_status", String(50), nullable=True)
    CreatedDate: Mapped[datetime] = mapped_column("CreatedDate", DateTime, default=datetime.utcnow, nullable=False)
    CreatedBy: Mapped[Optional[str]] = mapped_column("CreatedBy", String(100), nullable=True)
