"""
Pydantic v2 Schemas for Phase 28:
Franchise Agent Grid Margin Override Engine.
Physical Table: tbl_franchisegridmargin
Strictly configured with extra="forbid" and from_attributes=True.
"""
from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


# ============================================================================
# 1. REQUEST SCHEMAS
# ============================================================================

class FranchiseGridMarginCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid", populate_by_name=True)

    franchise_id: int = Field(..., ge=1, description="Franchise ID (tbl_franchise)")
    franchise_agent_id: int = Field(..., ge=1, description="Franchise Agent ID (tbl_agentcreation)")
    insurance_company_id: int = Field(..., ge=1, description="Underwriting Insurance Company ID (tbl_insurancecompany)")
    policy_type_id: int = Field(..., ge=1, description="Policy Type ID")
    margin: Decimal = Field(..., ge=0, le=100, description="Commission margin percentage retained by franchise (0.0 to 100.0)")


class FranchiseGridMarginBatchCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid", populate_by_name=True)

    franchise_id: int = Field(..., ge=1, description="Franchise ID (tbl_franchise)")
    franchise_agent_id: int = Field(..., ge=1, description="Franchise Agent ID (tbl_agentcreation)")
    insurance_company_id: int = Field(..., ge=1, description="Underwriting Insurance Company ID (tbl_insurancecompany)")
    policy_type_ids: List[int] = Field(..., min_length=1, description="List of Policy Type IDs to apply margin override to")
    margin: Decimal = Field(..., ge=0, le=100, description="Commission margin percentage retained by franchise (0.0 to 100.0)")


class FranchiseGridMarginUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid", populate_by_name=True)

    margin: Decimal = Field(..., ge=0, le=100, description="Updated commission margin percentage retained by franchise")


class FranchiseMarginCalculationRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid", populate_by_name=True)

    franchise_id: int = Field(..., ge=1, description="Franchise ID")
    franchise_agent_id: int = Field(..., ge=1, description="Franchise Agent ID")
    insurance_company_id: int = Field(..., ge=1, description="Underwriting Insurance Company ID")
    policy_type_id: int = Field(..., ge=1, description="Policy Type ID")
    gross_grid_percentage: Decimal = Field(..., ge=0, le=100, description="Gross grid commission percentage from master/broker grid")
    premium_amount: Decimal = Field(..., ge=0, description="Premium basis for commission calculation (TP/OD/Net)")
    is_franchise_as_agent: Optional[bool] = Field(False, description="Flag indicating if franchise itself acts as agent")


# ============================================================================
# 2. RESPONSE SCHEMAS
# ============================================================================

class FranchiseGridMarginResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int = Field(validation_alias="Id")
    franchise_id: int = Field(validation_alias="FranchiseId")
    franchise_agent_id: int = Field(validation_alias="FranchiseAgentId")
    insurance_company_id: int = Field(validation_alias="InsuranceCompanyId")
    policy_type_id: int = Field(validation_alias="PolicyTypeId")
    margin: Decimal = Field(validation_alias="margin")
    isdeleted: int = Field(validation_alias="isdeleted")
    created_user: Optional[str] = Field(None, validation_alias="CreatedUser")
    created_date: Optional[datetime] = Field(None, validation_alias="CreatedDate")
    updated_user: Optional[str] = Field(None, validation_alias="UpdatedUser")
    updated_date: Optional[datetime] = Field(None, validation_alias="UpdatedDate")


class FranchiseGridMarginBatchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    success: bool = True
    count: int
    message: str
    items: List[FranchiseGridMarginResponse]


class FranchiseMarginCalculationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    franchise_id: int
    franchise_agent_id: int
    insurance_company_id: int
    policy_type_id: int
    premium_amount: Decimal
    gross_grid_percentage: Decimal
    retained_margin_percentage: Decimal
    effective_agent_grid_percentage: Decimal
    franchise_retained_amount: Decimal
    agent_payout_amount: Decimal
    is_franchise_as_agent: bool
    has_margin_override: bool


class FranchiseGridMarginListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    total: int
    skip: int
    limit: int
    items: List[FranchiseGridMarginResponse]
