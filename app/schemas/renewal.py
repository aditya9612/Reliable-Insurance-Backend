"""
Pydantic v2 Schemas for Phase 13 Block E — Renewal Engine & Telecaller CRM.
"""
from datetime import datetime
from typing import Optional, List, Dict
from pydantic import BaseModel, Field, ConfigDict


class ExpiringPolicyResponse(BaseModel):
    """Details of a policy nearing expiration for renewal outreach."""
    model_config = ConfigDict(from_attributes=True)

    transaction_id: int
    policy_no: Optional[str] = None
    registration_no: str
    customer_name: Optional[str] = None
    mobile_no: Optional[str] = None
    insurance_company: Optional[str] = None
    gross_premium: float
    expiry_date: datetime
    days_until_expiry: int
    agent_id: int
    agent_name: Optional[str] = None
    executive_id: int
    branch_id: Optional[int] = None


class CreateRenewalFollowupRequest(BaseModel):
    """Request payload for recording a telecaller follow-up interaction."""
    model_config = ConfigDict(extra="forbid")

    transaction_id: int
    registration_number: str
    financial_year: str
    remark: str = Field(..., min_length=1, max_length=2000)
    followup_date: datetime
    insurance_company: Optional[str] = None
    total_premium: float = 0.0
    mobile_number: Optional[str] = None
    expiry_date: Optional[datetime] = None


class UpdateRenewalStatusRequest(BaseModel):
    """Request to transition renewal status (Follow, Done, Lost, Vehicle)."""
    model_config = ConfigDict(extra="forbid")

    status: str = Field(
        ...,
        pattern="^(Follow|Done|Lost|Vehicle)$",
        description="Target status: Follow, Done, Lost, Vehicle",
    )
    remark: Optional[str] = Field(None, max_length=2000)


class RenewalFollowupResponse(BaseModel):
    """Response representing a renewal CRM follow-up record."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    transaction_id: int
    registration_number: str
    financial_year: str
    status: str
    remark: Optional[str] = None
    followup_date: Optional[datetime] = None
    insurance_company: Optional[str] = None
    total_premium: float
    mobile_no: Optional[str] = None
    expiry_date: datetime
    created_date: datetime
    agent_id: int
    executive_id: int
    branch_id: Optional[int] = None


class ExecutiveRenewalCount(BaseModel):
    """Aggregate renewal counts for an assigned Sales Executive."""
    model_config = ConfigDict(from_attributes=True)

    executive_id: int
    executive_name: str
    follow_up_count: int
    done_count: int
    lost_count: int
    vehicle_count: int
    total_count: int


class InsurerRenewalCount(BaseModel):
    """Aggregate renewal retention metrics per Insurance Company."""
    model_config = ConfigDict(from_attributes=True)

    insurance_company: str
    due_count: int
    renewed_count: int
    retention_rate_pct: float


class RenewalDashboardResponse(BaseModel):
    """Executive renewal dashboard summary metrics."""
    model_config = ConfigDict(from_attributes=True)

    financial_year: str
    month: Optional[int] = None
    summary: Dict[str, int]
    executive_breakdown: List[ExecutiveRenewalCount]
    company_breakdown: List[InsurerRenewalCount]
