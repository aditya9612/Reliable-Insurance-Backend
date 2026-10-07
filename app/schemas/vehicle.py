from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, AliasChoices, field_validator


class VehicleBase(BaseModel):
    """Base schema attributes for Vehicle Details."""
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    registration_no: Optional[str] = Field(None, max_length=255, validation_alias=AliasChoices("RegistrationNo", "registration_no"))
    chaise_no: Optional[str] = Field(None, max_length=255, validation_alias=AliasChoices("ChaiseNo", "chaise_no", "chassis_no"))
    engine_no: Optional[str] = Field(None, max_length=500, validation_alias=AliasChoices("EngineNo", "engine_no"))
    mfg_month: Optional[str] = Field(None, max_length=255, validation_alias=AliasChoices("MfgMonth", "mfg_month"))
    mfg_year: Optional[str] = Field(None, max_length=255, validation_alias=AliasChoices("MfgYear", "mfg_year"))
    ex_showroom_price: Optional[str] = Field("", max_length=255, validation_alias=AliasChoices("Ex_ShowroomPrice", "ex_showroom_price"))
    fuel_type_id: Optional[int] = Field(None, validation_alias=AliasChoices("FuelTypeId", "fuel_type_id"))
    veh_type_id: Optional[int] = Field(None, validation_alias=AliasChoices("Veh_Type_ID", "veh_type_id"))
    veh_sub_type_id: Optional[int] = Field(None, validation_alias=AliasChoices("Veh_Sub_Type_ID", "veh_sub_type_id"))
    make_id: Optional[int] = Field(None, validation_alias=AliasChoices("Make_ID", "make_id"))
    model_id: Optional[int] = Field(None, validation_alias=AliasChoices("Model_ID", "model_id"))
    variant_id: Optional[int] = Field(None, validation_alias=AliasChoices("Variant_ID", "variant_id"))
    vehicle_pur_date: Optional[datetime] = Field(None, validation_alias=AliasChoices("VehiclePurDate", "vehicle_pur_date"))
    seats_capacity: Optional[str] = Field(None, max_length=255, validation_alias=AliasChoices("SeatsCapacity", "seats_capacity"))
    engine_power: Optional[str] = Field(None, max_length=500, validation_alias=AliasChoices("EnginePower", "engine_power"))
    trans_tonnage_capacity: Optional[str] = Field("", max_length=255, validation_alias=AliasChoices("TransTonnageCapacity", "trans_tonnage_capacity"))
    vehicle_weight: Optional[str] = Field(None, max_length=255, validation_alias=AliasChoices("VehicleWeight", "vehicle_weight"))
    vehicle_reg_date: Optional[datetime] = Field(None, validation_alias=AliasChoices("VehicleRegDate", "vehicle_reg_date"))
    rto_id: Optional[int] = Field(None, validation_alias=AliasChoices("RTOId", "rto_id"))
    branch_id: Optional[int] = Field(None, validation_alias=AliasChoices("BranchId", "branch_id"))
    corporate_client_id: Optional[int] = Field(1, validation_alias=AliasChoices("CorporateClientId", "corporate_client_id"))
    extra1: Optional[str] = Field(None, max_length=255, validation_alias=AliasChoices("Extra1", "extra1"))
    extra2: Optional[str] = Field(None, max_length=255, validation_alias=AliasChoices("Extra2", "extra2"))
    vehicle_variant: Optional[str] = Field(None, max_length=255, validation_alias=AliasChoices("VehicleVariant", "vehicle_variant"))

    @field_validator(
        "registration_no",
        "chaise_no",
        "engine_no",
        "mfg_year",
        "seats_capacity",
        "engine_power",
        "vehicle_weight",
        mode="before",
    )
    @classmethod
    def normalize_uppercase(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and isinstance(v, str):
            v_stripped = v.strip()
            return v_stripped.upper() if v_stripped else None
        return v

    @field_validator("mfg_month", "extra1", "extra2", "vehicle_variant", mode="before")
    @classmethod
    def normalize_empty_to_none(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and isinstance(v, str):
            v_stripped = v.strip()
            return v_stripped if v_stripped else None
        return v


class VehicleCreate(VehicleBase):
    """
    Vehicle asset creation payload.
    Matches legacy Sp_VehicleDetails_2026 contract.
    FinancialYear is strictly REQUIRED (physical NOT NULL in tbl_vehicledetails).
    """
    financial_year: str = Field(..., min_length=1, max_length=255, validation_alias=AliasChoices("FinancialYear", "financial_year"))

    @field_validator("financial_year", mode="before")
    @classmethod
    def normalize_financial_year(cls, v: str) -> str:
        if isinstance(v, str):
            v_stripped = v.strip()
            if not v_stripped:
                raise ValueError("financial_year cannot be empty")
            return v_stripped
        return v


class VehicleUpdate(BaseModel):
    """
    Vehicle asset update payload.
    Matches legacy Sp_UpdateVehicleDetails allowlist.
    Immutable fields: CustomerId, FinancialYear, BranchId, CorporateClientId, VehicleVariant, CreateDate, CreatedUser, isdeleted.
    """
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    registration_no: Optional[str] = Field(None, max_length=255, validation_alias=AliasChoices("RegistrationNo", "registration_no"))
    chaise_no: Optional[str] = Field(None, max_length=255, validation_alias=AliasChoices("ChaiseNo", "chaise_no", "chassis_no"))
    engine_no: Optional[str] = Field(None, max_length=500, validation_alias=AliasChoices("EngineNo", "engine_no"))
    mfg_month: Optional[str] = Field(None, max_length=255, validation_alias=AliasChoices("MfgMonth", "mfg_month"))
    mfg_year: Optional[str] = Field(None, max_length=255, validation_alias=AliasChoices("MfgYear", "mfg_year"))
    ex_showroom_price: Optional[str] = Field(None, max_length=255, validation_alias=AliasChoices("Ex_ShowroomPrice", "ex_showroom_price"))
    fuel_type_id: Optional[int] = Field(None, validation_alias=AliasChoices("FuelTypeId", "fuel_type_id"))
    veh_type_id: Optional[int] = Field(None, validation_alias=AliasChoices("Veh_Type_ID", "veh_type_id"))
    veh_sub_type_id: Optional[int] = Field(None, validation_alias=AliasChoices("Veh_Sub_Type_ID", "veh_sub_type_id"))
    make_id: Optional[int] = Field(None, validation_alias=AliasChoices("Make_ID", "make_id"))
    model_id: Optional[int] = Field(None, validation_alias=AliasChoices("Model_ID", "model_id"))
    variant_id: Optional[int] = Field(None, validation_alias=AliasChoices("Variant_ID", "variant_id"))
    vehicle_pur_date: Optional[datetime] = Field(None, validation_alias=AliasChoices("VehiclePurDate", "vehicle_pur_date"))
    seats_capacity: Optional[str] = Field(None, max_length=255, validation_alias=AliasChoices("SeatsCapacity", "seats_capacity"))
    engine_power: Optional[str] = Field(None, max_length=500, validation_alias=AliasChoices("EnginePower", "engine_power"))
    trans_tonnage_capacity: Optional[str] = Field(None, max_length=255, validation_alias=AliasChoices("TransTonnageCapacity", "trans_tonnage_capacity"))
    vehicle_weight: Optional[str] = Field(None, max_length=255, validation_alias=AliasChoices("VehicleWeight", "vehicle_weight"))
    vehicle_reg_date: Optional[datetime] = Field(None, validation_alias=AliasChoices("VehicleRegDate", "vehicle_reg_date"))
    rto_id: Optional[int] = Field(None, validation_alias=AliasChoices("RTOId", "rto_id"))
    extra1: Optional[str] = Field(None, max_length=255, validation_alias=AliasChoices("Extra1", "extra1"))
    extra2: Optional[str] = Field(None, max_length=255, validation_alias=AliasChoices("Extra2", "extra2"))

    @field_validator(
        "registration_no",
        "chaise_no",
        "engine_no",
        "mfg_year",
        "seats_capacity",
        "engine_power",
        "vehicle_weight",
        mode="before",
    )
    @classmethod
    def normalize_uppercase(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and isinstance(v, str):
            v_stripped = v.strip()
            return v_stripped.upper() if v_stripped else None
        return v

    @field_validator("mfg_month", "extra1", "extra2", mode="before")
    @classmethod
    def normalize_empty_to_none(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and isinstance(v, str):
            v_stripped = v.strip()
            return v_stripped if v_stripped else None
        return v


class VehicleResponse(BaseModel):
    """
    Standard vehicle response representation.
    Supports attribute access from SQLAlchemy ORM models.
    """
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    cust_veh_id: int = Field(..., validation_alias=AliasChoices("CustVehId", "cust_veh_id"))
    customer_id: Optional[int] = Field(None, validation_alias=AliasChoices("CustomerId", "customer_id"))
    registration_no: Optional[str] = Field(None, validation_alias=AliasChoices("RegistrationNo", "registration_no"))
    chaise_no: Optional[str] = Field(None, validation_alias=AliasChoices("ChaiseNo", "chaise_no", "chassis_no"))
    engine_no: Optional[str] = Field(None, validation_alias=AliasChoices("EngineNo", "engine_no"))
    mfg_month: Optional[str] = Field(None, validation_alias=AliasChoices("MfgMonth", "mfg_month"))
    mfg_year: Optional[str] = Field(None, validation_alias=AliasChoices("MfgYear", "mfg_year"))
    ex_showroom_price: Optional[str] = Field(None, validation_alias=AliasChoices("Ex_ShowroomPrice", "ex_showroom_price"))
    fuel_type_id: Optional[int] = Field(None, validation_alias=AliasChoices("FuelTypeId", "fuel_type_id"))
    veh_type_id: Optional[int] = Field(None, validation_alias=AliasChoices("Veh_Type_ID", "veh_type_id"))
    veh_sub_type_id: Optional[int] = Field(None, validation_alias=AliasChoices("Veh_Sub_Type_ID", "veh_sub_type_id"))
    make_id: Optional[int] = Field(None, validation_alias=AliasChoices("Make_ID", "make_id"))
    model_id: Optional[int] = Field(None, validation_alias=AliasChoices("Model_ID", "model_id"))
    variant_id: Optional[int] = Field(None, validation_alias=AliasChoices("Variant_ID", "variant_id"))
    vehicle_pur_date: Optional[datetime] = Field(None, validation_alias=AliasChoices("VehiclePurDate", "vehicle_pur_date"))
    seats_capacity: Optional[str] = Field(None, validation_alias=AliasChoices("SeatsCapacity", "seats_capacity"))
    engine_power: Optional[str] = Field(None, validation_alias=AliasChoices("EnginePower", "engine_power"))
    trans_tonnage_capacity: Optional[str] = Field(None, validation_alias=AliasChoices("TransTonnageCapacity", "trans_tonnage_capacity"))
    vehicle_weight: Optional[str] = Field(None, validation_alias=AliasChoices("VehicleWeight", "vehicle_weight"))
    vehicle_reg_date: Optional[datetime] = Field(None, validation_alias=AliasChoices("VehicleRegDate", "vehicle_reg_date"))
    rto_id: Optional[int] = Field(None, validation_alias=AliasChoices("RTOId", "rto_id"))
    branch_id: Optional[int] = Field(None, validation_alias=AliasChoices("BranchId", "branch_id"))
    corporate_client_id: Optional[int] = Field(None, validation_alias=AliasChoices("CorporateClientId", "corporate_client_id"))
    create_date: Optional[datetime] = Field(None, validation_alias=AliasChoices("CreateDate", "create_date"))
    created_user: Optional[str] = Field(None, validation_alias=AliasChoices("CreatedUser", "created_user"))
    updated_date: Optional[datetime] = Field(None, validation_alias=AliasChoices("UpdatedDate", "updated_date"))
    updated_user: Optional[str] = Field(None, validation_alias=AliasChoices("UpdatedUser", "updated_user"))
    extra1: Optional[str] = Field(None, validation_alias=AliasChoices("Extra1", "extra1"))
    extra2: Optional[str] = Field(None, validation_alias=AliasChoices("Extra2", "extra2"))
    financial_year: str = Field(..., validation_alias=AliasChoices("FinancialYear", "financial_year"))
    vehicle_variant: Optional[str] = Field(None, validation_alias=AliasChoices("VehicleVariant", "vehicle_variant"))
    isdeleted: Optional[str] = Field(None, validation_alias=AliasChoices("isdeleted", "is_deleted"))
