from datetime import datetime, date
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, AliasChoices, field_validator


class CustomerBase(BaseModel):
    """Base schema attributes for Customer."""
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    initial: Optional[str] = Field(None, max_length=255, validation_alias=AliasChoices("initial", "Initial"))
    cust_f_name: str = Field(..., min_length=1, max_length=300, validation_alias=AliasChoices("CustFName", "cust_f_name"))
    cust_m_name: Optional[str] = Field(None, max_length=255, validation_alias=AliasChoices("CustMName", "cust_m_name"))
    cust_l_name: Optional[str] = Field(None, max_length=255, validation_alias=AliasChoices("CustLName", "cust_l_name"))
    customer_type: Optional[str] = Field("Individual", max_length=255, validation_alias=AliasChoices("CustomerType", "customer_type"))
    client_id: Optional[int] = Field(1, validation_alias=AliasChoices("ClientId", "client_id"))
    per_addr_line1: Optional[str] = Field(None, max_length=600, validation_alias=AliasChoices("PerAddrLine1", "per_addr_line1"))
    per_addr_line2: Optional[str] = Field(None, max_length=600, validation_alias=AliasChoices("PerAddrLine2", "per_addr_line2"))
    per_taluka_id: Optional[int] = Field(0, validation_alias=AliasChoices("PerTalukaId", "per_taluka_id"))
    per_district_id: Optional[int] = Field(0, validation_alias=AliasChoices("PerDistrictId", "per_district_id"))
    per_state_id: Optional[int] = Field(0, validation_alias=AliasChoices("PerStateId", "per_state_id"))
    per_pin_code: Optional[str] = Field(None, max_length=255, validation_alias=AliasChoices("PerPinCode", "per_pin_code"))
    com_addr_line1: Optional[str] = Field(None, max_length=600, validation_alias=AliasChoices("ComAddrLine1", "com_addr_line1"))
    com_addr_line2: Optional[str] = Field(None, max_length=600, validation_alias=AliasChoices("ComAddrLine2", "com_addr_line2"))
    com_taluka_id: Optional[int] = Field(0, validation_alias=AliasChoices("ComTalukaId", "com_taluka_id"))
    com_district_id: Optional[int] = Field(0, validation_alias=AliasChoices("ComDistrictId", "com_district_id"))
    com_state_id: Optional[int] = Field(0, validation_alias=AliasChoices("ComStateId", "com_state_id"))
    com_pin_code: Optional[str] = Field(None, max_length=255, validation_alias=AliasChoices("ComPinCode", "com_pin_code"))
    moblie_no1: Optional[str] = Field(None, max_length=255, validation_alias=AliasChoices("MoblieNo1", "moblie_no1", "mobile_no1"))
    moblie_no2: Optional[str] = Field(None, max_length=255, validation_alias=AliasChoices("MoblieNo2", "moblie_no2", "mobile_no2"))
    gender: Optional[str] = Field("Male", max_length=255, validation_alias=AliasChoices("Gender", "gender"))
    marital_status: Optional[str] = Field(None, max_length=255, validation_alias=AliasChoices("MaritalStatus", "marital_status"))
    pan_no: Optional[str] = Field(None, max_length=255, validation_alias=AliasChoices("PAN_No", "pan_no"))
    aadhar_no: Optional[str] = Field(None, max_length=255, validation_alias=AliasChoices("AadharNo", "aadhar_no"))
    date_of_birth: Optional[date] = Field(None, validation_alias=AliasChoices("DateOfBirth", "date_of_birth"))
    email_id: Optional[str] = Field(None, max_length=255, validation_alias=AliasChoices("EMailId", "email_id"))
    nominee_name: Optional[str] = Field(None, max_length=255, validation_alias=AliasChoices("NomineeName", "nominee_name"))
    branch_id: Optional[int] = Field(None, validation_alias=AliasChoices("BranchId", "branch_id"))
    extra1: Optional[str] = Field(None, max_length=255, validation_alias=AliasChoices("Extra1", "extra1"))
    extra2: Optional[str] = Field(None, max_length=255, validation_alias=AliasChoices("Extra2", "extra2"))
    company_name: Optional[str] = Field(None, max_length=255, validation_alias=AliasChoices("CompanyName", "company_name"))

    @field_validator(
        "cust_f_name",
        "cust_m_name",
        "cust_l_name",
        "per_addr_line1",
        "per_addr_line2",
        "com_addr_line1",
        "com_addr_line2",
        "aadhar_no",
        "email_id",
        "nominee_name",
        mode="before",
    )
    @classmethod
    def normalize_uppercase(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and isinstance(v, str):
            v_stripped = v.strip()
            return v_stripped.upper() if v_stripped else None
        return v

    @field_validator("marital_status", "extra1", "extra2", mode="before")
    @classmethod
    def normalize_empty_to_none(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and isinstance(v, str):
            v_stripped = v.strip()
            return v_stripped if v_stripped else None
        return v

    @field_validator("pan_no", "moblie_no1", "moblie_no2", mode="before")
    @classmethod
    def strip_whitespace(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and isinstance(v, str):
            v_stripped = v.strip()
            return v_stripped if v_stripped else None
        return v


class CustomerCreate(CustomerBase):
    """
    Customer creation payload.
    Matches legacy sp_InsertCustomer contract.
    CustomerCode is optional; if omitted, service generates it atomically from AUTO_INCREMENT CustomerId.
    """
    customer_code: Optional[str] = Field(None, max_length=255, validation_alias=AliasChoices("CustomerCode", "customer_code"))


class CustomerUpdate(BaseModel):
    """
    Customer update payload.
    Matches legacy sp_UpdateCustomer allowlist.
    Immutable fields: CustomerId, CustomerCode, CreateDate, CreateUser, CompanyName, isdeleted.
    """
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    initial: Optional[str] = Field(None, max_length=255, validation_alias=AliasChoices("initial", "Initial"))
    cust_f_name: Optional[str] = Field(None, min_length=1, max_length=300, validation_alias=AliasChoices("CustFName", "cust_f_name"))
    cust_m_name: Optional[str] = Field(None, max_length=255, validation_alias=AliasChoices("CustMName", "cust_m_name"))
    cust_l_name: Optional[str] = Field(None, max_length=255, validation_alias=AliasChoices("CustLName", "cust_l_name"))
    customer_type: Optional[str] = Field(None, max_length=255, validation_alias=AliasChoices("CustomerType", "customer_type"))
    client_id: Optional[int] = Field(None, validation_alias=AliasChoices("ClientId", "client_id"))
    per_addr_line1: Optional[str] = Field(None, max_length=600, validation_alias=AliasChoices("PerAddrLine1", "per_addr_line1"))
    per_addr_line2: Optional[str] = Field(None, max_length=600, validation_alias=AliasChoices("PerAddrLine2", "per_addr_line2"))
    per_taluka_id: Optional[int] = Field(None, validation_alias=AliasChoices("PerTalukaId", "per_taluka_id"))
    per_district_id: Optional[int] = Field(None, validation_alias=AliasChoices("PerDistrictId", "per_district_id"))
    per_state_id: Optional[int] = Field(None, validation_alias=AliasChoices("PerStateId", "per_state_id"))
    per_pin_code: Optional[str] = Field(None, max_length=255, validation_alias=AliasChoices("PerPinCode", "per_pin_code"))
    com_addr_line1: Optional[str] = Field(None, max_length=600, validation_alias=AliasChoices("ComAddrLine1", "com_addr_line1"))
    com_addr_line2: Optional[str] = Field(None, max_length=600, validation_alias=AliasChoices("ComAddrLine2", "com_addr_line2"))
    com_taluka_id: Optional[int] = Field(None, validation_alias=AliasChoices("ComTalukaId", "com_taluka_id"))
    com_district_id: Optional[int] = Field(None, validation_alias=AliasChoices("ComDistrictId", "com_district_id"))
    com_state_id: Optional[int] = Field(None, validation_alias=AliasChoices("ComStateId", "com_state_id"))
    com_pin_code: Optional[str] = Field(None, max_length=255, validation_alias=AliasChoices("ComPinCode", "com_pin_code"))
    moblie_no1: Optional[str] = Field(None, max_length=255, validation_alias=AliasChoices("MoblieNo1", "moblie_no1", "mobile_no1"))
    moblie_no2: Optional[str] = Field(None, max_length=255, validation_alias=AliasChoices("MoblieNo2", "moblie_no2", "mobile_no2"))
    gender: Optional[str] = Field(None, max_length=255, validation_alias=AliasChoices("Gender", "gender"))
    marital_status: Optional[str] = Field(None, max_length=255, validation_alias=AliasChoices("MaritalStatus", "marital_status"))
    pan_no: Optional[str] = Field(None, max_length=255, validation_alias=AliasChoices("PAN_No", "pan_no"))
    aadhar_no: Optional[str] = Field(None, max_length=255, validation_alias=AliasChoices("AadharNo", "aadhar_no"))
    date_of_birth: Optional[date] = Field(None, validation_alias=AliasChoices("DateOfBirth", "date_of_birth"))
    email_id: Optional[str] = Field(None, max_length=255, validation_alias=AliasChoices("EMailId", "email_id"))
    nominee_name: Optional[str] = Field(None, max_length=255, validation_alias=AliasChoices("NomineeName", "nominee_name"))
    branch_id: Optional[int] = Field(None, validation_alias=AliasChoices("BranchId", "branch_id"))
    extra1: Optional[str] = Field(None, max_length=255, validation_alias=AliasChoices("Extra1", "extra1"))
    extra2: Optional[str] = Field(None, max_length=255, validation_alias=AliasChoices("Extra2", "extra2"))

    @field_validator(
        "cust_f_name",
        "cust_m_name",
        "cust_l_name",
        "per_addr_line1",
        "per_addr_line2",
        "com_addr_line1",
        "com_addr_line2",
        "aadhar_no",
        "email_id",
        "nominee_name",
        mode="before",
    )
    @classmethod
    def normalize_uppercase(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and isinstance(v, str):
            v_stripped = v.strip()
            return v_stripped.upper() if v_stripped else None
        return v

    @field_validator("marital_status", "extra1", "extra2", mode="before")
    @classmethod
    def normalize_empty_to_none(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and isinstance(v, str):
            v_stripped = v.strip()
            return v_stripped if v_stripped else None
        return v

    @field_validator("pan_no", "moblie_no1", "moblie_no2", mode="before")
    @classmethod
    def strip_whitespace(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and isinstance(v, str):
            v_stripped = v.strip()
            return v_stripped if v_stripped else None
        return v


class CustomerResponse(BaseModel):
    """
    Standard customer response representation.
    Supports attribute access from SQLAlchemy ORM models.
    """
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    customer_id: int = Field(..., validation_alias=AliasChoices("CustomerId", "customer_id"))
    customer_code: Optional[str] = Field(None, validation_alias=AliasChoices("CustomerCode", "customer_code"))
    initial: Optional[str] = Field(None, validation_alias=AliasChoices("initial", "Initial"))
    cust_f_name: Optional[str] = Field(None, validation_alias=AliasChoices("CustFName", "cust_f_name"))
    cust_m_name: Optional[str] = Field(None, validation_alias=AliasChoices("CustMName", "cust_m_name"))
    cust_l_name: Optional[str] = Field(None, validation_alias=AliasChoices("CustLName", "cust_l_name"))
    customer_type: Optional[str] = Field(None, validation_alias=AliasChoices("CustomerType", "customer_type"))
    client_id: Optional[int] = Field(None, validation_alias=AliasChoices("ClientId", "client_id"))
    per_addr_line1: Optional[str] = Field(None, validation_alias=AliasChoices("PerAddrLine1", "per_addr_line1"))
    per_addr_line2: Optional[str] = Field(None, validation_alias=AliasChoices("PerAddrLine2", "per_addr_line2"))
    per_taluka_id: Optional[int] = Field(None, validation_alias=AliasChoices("PerTalukaId", "per_taluka_id"))
    per_district_id: Optional[int] = Field(None, validation_alias=AliasChoices("PerDistrictId", "per_district_id"))
    per_state_id: Optional[int] = Field(None, validation_alias=AliasChoices("PerStateId", "per_state_id"))
    per_pin_code: Optional[str] = Field(None, validation_alias=AliasChoices("PerPinCode", "per_pin_code"))
    com_addr_line1: Optional[str] = Field(None, validation_alias=AliasChoices("ComAddrLine1", "com_addr_line1"))
    com_addr_line2: Optional[str] = Field(None, validation_alias=AliasChoices("ComAddrLine2", "com_addr_line2"))
    com_taluka_id: Optional[int] = Field(None, validation_alias=AliasChoices("ComTalukaId", "com_taluka_id"))
    com_district_id: Optional[int] = Field(None, validation_alias=AliasChoices("ComDistrictId", "com_district_id"))
    com_state_id: Optional[int] = Field(None, validation_alias=AliasChoices("ComStateId", "com_state_id"))
    com_pin_code: Optional[str] = Field(None, validation_alias=AliasChoices("ComPinCode", "com_pin_code"))
    moblie_no1: Optional[str] = Field(None, validation_alias=AliasChoices("MoblieNo1", "moblie_no1", "mobile_no1"))
    moblie_no2: Optional[str] = Field(None, validation_alias=AliasChoices("MoblieNo2", "moblie_no2", "mobile_no2"))
    gender: Optional[str] = Field(None, validation_alias=AliasChoices("Gender", "gender"))
    marital_status: Optional[str] = Field(None, validation_alias=AliasChoices("MaritalStatus", "marital_status"))
    pan_no: Optional[str] = Field(None, validation_alias=AliasChoices("PAN_No", "pan_no"))
    aadhar_no: Optional[str] = Field(None, validation_alias=AliasChoices("AadharNo", "aadhar_no"))
    date_of_birth: Optional[date] = Field(None, validation_alias=AliasChoices("DateOfBirth", "date_of_birth"))
    email_id: Optional[str] = Field(None, validation_alias=AliasChoices("EMailId", "email_id"))
    nominee_name: Optional[str] = Field(None, validation_alias=AliasChoices("NomineeName", "nominee_name"))
    branch_id: Optional[int] = Field(None, validation_alias=AliasChoices("BranchId", "branch_id"))
    create_date: Optional[datetime] = Field(None, validation_alias=AliasChoices("CreateDate", "create_date"))
    create_user: Optional[str] = Field(None, validation_alias=AliasChoices("CreateUser", "create_user"))
    update_date: Optional[datetime] = Field(None, validation_alias=AliasChoices("UpdateDate", "update_date"))
    update_user: Optional[str] = Field(None, validation_alias=AliasChoices("UpdateUser", "update_user"))
    extra1: Optional[str] = Field(None, validation_alias=AliasChoices("Extra1", "extra1"))
    extra2: Optional[str] = Field(None, validation_alias=AliasChoices("Extra2", "extra2"))
    company_name: Optional[str] = Field(None, validation_alias=AliasChoices("CompanyName", "company_name"))
    isdeleted: Optional[str] = Field(None, validation_alias=AliasChoices("isdeleted", "is_deleted"))
