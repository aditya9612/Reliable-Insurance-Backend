"""
Pydantic v2 Schemas for Phase 13 Block A — Vehicle RC & KYC Integration.
"""
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class VehicleRCLookupRequest(BaseModel):
    """Request payload for vehicle RC lookup."""
    model_config = ConfigDict(extra="forbid")

    registration_number: str = Field(
        ...,
        min_length=4,
        max_length=25,
        description="Vehicle registration number (e.g. MH12AB1234)",
        examples=["MH12AB1234"],
    )
    force_refresh: bool = Field(
        default=False,
        description="Whether to bypass local cache and force an external provider query",
    )
    provider: Optional[str] = Field(
        default=None,
        description="Optional RC provider override: mock, apiclub, signzy, or attestr",
    )


class VehicleRCData(BaseModel):
    """Canonical DTO representing 54 vehicle RC attributes from providers or DB."""
    model_config = ConfigDict(from_attributes=True, extra="ignore")

    request_id: Optional[str] = None
    license_plate_RegNo: str
    owner_name: Optional[str] = None
    father_name: Optional[str] = None
    is_financed: Optional[str] = None
    financer: Optional[str] = None
    present_address: Optional[str] = None
    permanent_address: Optional[str] = None
    insurance_company: Optional[str] = None
    insurance_policy: Optional[str] = None
    insurance_expiry: Optional[datetime] = None
    rc_class: Optional[str] = None
    category: Optional[str] = None
    registration_date: Optional[datetime] = None
    vehicle_age: Optional[str] = None
    pucc_upto: Optional[datetime] = None
    pucc_number: Optional[str] = None
    chassis_number: Optional[str] = None
    engine_number: Optional[str] = None
    fuel_type: Optional[str] = None
    brand_name: Optional[str] = None
    brand_model: Optional[str] = None
    body_type: Optional[str] = None
    cubic_capacity: Optional[str] = None
    gross_weight: Optional[str] = None
    cylinders: Optional[str] = None
    color: Optional[str] = None
    norms: Optional[str] = None
    fit_up_to: Optional[str] = None
    manufacturing_date: Optional[str] = None
    manufacturing_date_formatted: Optional[str] = None
    rto_name: Optional[str] = None
    latest_by: Optional[str] = None
    sleeper_capacity: Optional[str] = None
    standing_capacity: Optional[str] = None
    wheelbase: Optional[str] = None
    unladen_weight: Optional[str] = None
    noc_details: Optional[str] = None
    seating_capacity: Optional[str] = None
    owner_count: Optional[str] = None
    tax_upto: Optional[str] = None
    tax_paid_upto: Optional[str] = None
    permit_number: Optional[str] = None
    permit_issue_date: Optional[str] = None
    permit_valid_from: Optional[str] = None
    permit_valid_upto: Optional[str] = None
    permit_type: Optional[str] = None
    national_permit_number: Optional[str] = None
    national_permit_upto: Optional[str] = None
    national_permit_issued_by: Optional[str] = None
    rc_status: Optional[str] = None
    CreatedDate: Optional[datetime] = None
    CreatedBy: Optional[str] = None


class VehicleRCLookupResponse(BaseModel):
    """Response payload for vehicle RC lookup."""
    model_config = ConfigDict(from_attributes=True)

    source: str = Field(
        ...,
        description="Source of RC details: INTERNAL_SYSTEM, LOCAL_CACHE, or EXTERNAL_PROVIDER",
        examples=["LOCAL_CACHE"],
    )
    data: VehicleRCData
