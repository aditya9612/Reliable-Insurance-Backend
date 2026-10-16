"""
Pydantic Schemas for Phase 29:
Temporary Operator Role & Workload Delegation Master.
Physical Tables: tbl_tempararyoperator.
"""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict, model_validator


class TemporaryOperatorBase(BaseModel):
    per_operator_id: int = Field(..., gt=0, description="Permanent Operator Employee/User ID")
    temp_operator_id: int = Field(..., gt=0, description="Temporary Operator Employee/User ID")
    valid_from: Optional[datetime] = Field(None, description="Start timestamp of delegation")
    valid_up_to: Optional[datetime] = Field(None, description="End timestamp of delegation")


class TemporaryOperatorCreate(TemporaryOperatorBase):
    @model_validator(mode="after")
    def validate_different_operators_and_dates(self) -> "TemporaryOperatorCreate":
        if self.per_operator_id == self.temp_operator_id:
            raise ValueError("Permanent Operator and Temporary Operator cannot be the same user.")
        if self.valid_from and self.valid_up_to and self.valid_up_to < self.valid_from:
            raise ValueError("valid_up_to cannot be earlier than valid_from.")
        return self


class TemporaryOperatorUpdate(BaseModel):
    valid_from: Optional[datetime] = Field(None, description="Updated start timestamp")
    valid_up_to: Optional[datetime] = Field(None, description="Updated end timestamp")

    @model_validator(mode="after")
    def validate_dates(self) -> "TemporaryOperatorUpdate":
        if self.valid_from and self.valid_up_to and self.valid_up_to < self.valid_from:
            raise ValueError("valid_up_to cannot be earlier than valid_from.")
        return self


class TemporaryOperatorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int = Field(..., validation_alias="ID")
    per_operator_id: int = Field(..., validation_alias="Per_OperatorId")
    per_operator_name: Optional[str] = None
    temp_operator_id: int = Field(..., validation_alias="Temp_OperatorId")
    temp_operator_name: Optional[str] = None
    valid_from: Optional[datetime] = Field(None, validation_alias="ValidFrom")
    valid_up_to: Optional[datetime] = Field(None, validation_alias="ValidUpTo")
    create_user: Optional[str] = Field(None, validation_alias="CreateUser")
    create_date: Optional[datetime] = Field(None, validation_alias="CreateDate")
    isdeleted: int = Field(0)
    updated_user: Optional[str] = Field(None, validation_alias="UpdatedUser")
    updated_date: Optional[datetime] = Field(None, validation_alias="UpdatedDate")
    is_active: bool = True


class TemporaryOperatorListResponse(BaseModel):
    items: List[TemporaryOperatorResponse]
    total: int


class EffectiveOperatorResponse(BaseModel):
    requested_operator_id: int
    effective_operator_id: int
    delegation_active: bool
    delegation_id: Optional[int] = None
    delegation_role: str = "PERMANENT"  # "PERMANENT" or "TEMPORARY"
    permanent_operator_name: Optional[str] = None
    temporary_operator_name: Optional[str] = None
    valid_from: Optional[datetime] = None
    valid_up_to: Optional[datetime] = None


class EligibleOperatorResponse(BaseModel):
    emp_id: int
    emp_name: str
    user_role: str
