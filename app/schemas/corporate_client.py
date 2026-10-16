"""
Pydantic v2 Schemas for Phase 25:
Corporate Group Clients, Commercial Sales Invoicing & Sister Concern Advances.
Strictly configured with extra="forbid" and from_attributes=True.
"""
from datetime import datetime, date
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator
import re


# ============================================================================
# 1. SALES TYPE SCHEMAS
# ============================================================================

class SalesTypeBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    Description: str = Field(..., min_length=1, max_length=255, description="Commercial sales categorization")
    IsActive: bool = Field(default=True, description="Active status for master selection")


class SalesTypeCreate(SalesTypeBase):
    pass


class SalesTypeUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    Description: Optional[str] = Field(None, min_length=1, max_length=255)
    IsActive: Optional[bool] = None


class SalesTypeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    sales_type_id: int = Field(validation_alias="SalesTypeId")
    description: str = Field(validation_alias="Description")
    is_active: bool = Field(validation_alias="IsActive")
    created_date: datetime = Field(validation_alias="CreatedDate")


# ============================================================================
# 2. RELIABLE GROUP COMPANY SCHEMAS
# ============================================================================

class ReliableCompanyBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    RCompany: str = Field(..., min_length=1, max_length=255, description="Sister concern company legal name")
    Prefix: str = Field(..., min_length=1, max_length=50, description="Sequential invoice numbering prefix (e.g. JPB, REL)")
    LedgerMId: Optional[int] = Field(None, ge=1, description="Associated ledger account ID in tbl_ledgermaster")
    IsActive: bool = Field(default=True, description="Active status")


class ReliableCompanyCreate(ReliableCompanyBase):
    pass


class ReliableCompanyUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    RCompany: Optional[str] = Field(None, min_length=1, max_length=255)
    Prefix: Optional[str] = Field(None, min_length=1, max_length=50)
    LedgerMId: Optional[int] = Field(None, ge=1)
    IsActive: Optional[bool] = None


class ReliableCompanyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    r_company_id: int = Field(validation_alias="RCompanyId")
    r_company: str = Field(validation_alias="RCompany")
    prefix: str = Field(validation_alias="Prefix")
    ledger_m_id: Optional[int] = Field(None, validation_alias="LedgerMId")
    is_active: bool = Field(validation_alias="IsActive")
    created_date: datetime = Field(validation_alias="CreatedDate")


# ============================================================================
# 3. CORPORATE GROUP CLIENT SCHEMAS
# ============================================================================

_PAN_REGEX = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]{1}$")
_GST_REGEX = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$")

class ClientMasterBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    Description: str = Field(..., min_length=1, max_length=255, description="Corporate Client / Corporate Customer Name")
    InsuranceCompanyId: Optional[int] = Field(None, ge=1, description="Linked Insurance Company ID if applicable")
    Address: Optional[str] = Field(None, max_length=500, description="Corporate billing address")
    PanNo: Optional[str] = Field(None, max_length=20, description="Corporate Income Tax PAN")
    GST: Optional[str] = Field(None, max_length=50, description="GSTIN Identification Number")
    CGST: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"), le=Decimal("28.00"), description="Default CGST rate %")
    SGST: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"), le=Decimal("28.00"), description="Default SGST rate %")
    IGST: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"), le=Decimal("28.00"), description="Default IGST rate %")
    IsActive: bool = Field(default=True, description="Active status")

    @field_validator("PanNo")
    @classmethod
    def validate_pan(cls, v: Optional[str]) -> Optional[str]:
        if v:
            clean = v.strip().upper()
            if not _PAN_REGEX.match(clean):
                raise ValueError("PanNo must be a valid 10-character Indian PAN format (e.g., ABCDE1234F)")
            return clean
        return v

    @field_validator("GST")
    @classmethod
    def validate_gst(cls, v: Optional[str]) -> Optional[str]:
        if v:
            clean = v.strip().upper()
            if not _GST_REGEX.match(clean) and len(clean) != 15:
                raise ValueError("GST must be a valid 15-character GSTIN format")
            return clean
        return v


class ClientMasterCreate(ClientMasterBase):
    pass


class ClientMasterUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    Description: Optional[str] = Field(None, min_length=1, max_length=255)
    InsuranceCompanyId: Optional[int] = Field(None, ge=1)
    Address: Optional[str] = Field(None, max_length=500)
    PanNo: Optional[str] = Field(None, max_length=20)
    GST: Optional[str] = Field(None, max_length=50)
    CGST: Optional[Decimal] = Field(None, ge=Decimal("0.00"), le=Decimal("28.00"))
    SGST: Optional[Decimal] = Field(None, ge=Decimal("0.00"), le=Decimal("28.00"))
    IGST: Optional[Decimal] = Field(None, ge=Decimal("0.00"), le=Decimal("28.00"))
    IsActive: Optional[bool] = None

    @field_validator("PanNo")
    @classmethod
    def validate_pan(cls, v: Optional[str]) -> Optional[str]:
        if v:
            clean = v.strip().upper()
            if not _PAN_REGEX.match(clean):
                raise ValueError("PanNo must be a valid 10-character Indian PAN format")
            return clean
        return v

    @field_validator("GST")
    @classmethod
    def validate_gst(cls, v: Optional[str]) -> Optional[str]:
        if v:
            clean = v.strip().upper()
            if not _GST_REGEX.match(clean) and len(clean) != 15:
                raise ValueError("GST must be a valid 15-character GSTIN format")
            return clean
        return v


class ClientMasterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    client_master_id: int = Field(validation_alias="ClientMasterId")
    description: str = Field(validation_alias="Description")
    insurance_company_id: Optional[int] = Field(None, validation_alias="InsuranceCompanyId")
    address: Optional[str] = Field(None, validation_alias="Address")
    pan_no: Optional[str] = Field(None, validation_alias="PanNo")
    gst: Optional[str] = Field(None, validation_alias="GST")
    cgst: Decimal = Field(validation_alias="CGST")
    sgst: Decimal = Field(validation_alias="SGST")
    igst: Decimal = Field(validation_alias="IGST")
    is_active: bool = Field(validation_alias="IsActive")
    created_user: Optional[str] = Field(None, validation_alias="CreatedUser")
    created_date: datetime = Field(validation_alias="Createdate")


# ============================================================================
# 4. COMMERCIAL INVOICE & LINE ITEMS SCHEMAS
# ============================================================================

class CommercialInvoiceLineItemCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    sales_type: Optional[str] = Field(None, max_length=100, description="Description/classification label")
    sales_type_id: Optional[int] = Field(None, ge=1, description="Master SalesTypeId")
    taxable_amt: Decimal = Field(..., gt=Decimal("0.00"), description="Base taxable amount (cents preserved)")
    cgst_per: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"), le=Decimal("28.00"))
    sgst_per: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"), le=Decimal("28.00"))
    igst_per: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"), le=Decimal("28.00"))


class CommercialInvoiceLineItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    detail_id: int = Field(validation_alias="SalesRegDetailId")
    invoice_id: int = Field(validation_alias="InvoiceId")
    invoice_no: str = Field(validation_alias="InvoiceNo")
    sales_type: Optional[str] = Field(None, validation_alias="SalesType")
    sales_type_id: Optional[int] = Field(None, validation_alias="SalesTypeId")
    taxable_amt: Decimal = Field(validation_alias="TaxableAmt")
    cgst_per: Decimal = Field(validation_alias="CGSTPre")
    cgst_amt: Decimal = Field(validation_alias="CGSTAmt")
    sgst_per: Decimal = Field(validation_alias="SGSTPre")
    sgst_amt: Decimal = Field(validation_alias="SGSTAmt")
    igst_per: Decimal = Field(validation_alias="IGSTPre")
    igst_amt: Decimal = Field(validation_alias="IGSTAmt")
    total: Decimal = Field(validation_alias="Total")


class CommercialInvoiceCreateRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    r_company_id: int = Field(..., ge=1, description="Reliable Sister Concern Company ID (determines prefix)")
    client_master_id: int = Field(..., ge=1, description="Corporate B2B Client Master ID")
    sales_date: date = Field(..., description="Date of sales invoice")
    sales_type_id: Optional[int] = Field(default=1, ge=1)
    registration_type: str = Field(default="COMMERCIAL_B2B", max_length=100)
    description: Optional[str] = Field(default="Commercial Invoicing", max_length=500)
    ledger_m_id: Optional[int] = Field(None, ge=1, description="Client receiving ledger if applicable")
    invoice_no: Optional[str] = Field(None, max_length=100, description="Optional custom/override invoice number; auto-allocated if omitted")
    items: List[CommercialInvoiceLineItemCreate] = Field(..., min_length=1, description="At least one line item is required")


class CommercialInvoiceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    sales_reg_id: int = Field(validation_alias="salesRegId")
    invoice_no: str = Field(validation_alias="InvoiceNo")
    registration_type: Optional[str] = Field(None, validation_alias="RegistrationType")
    sales_date: date = Field(validation_alias="SalesDate")
    r_company_id: Optional[int] = Field(None, validation_alias="RCompanyId")
    sales_type_id: Optional[int] = Field(None, validation_alias="SalesTypeId")
    sales_type: Optional[str] = Field(None, validation_alias="SalesType")
    client_master_id: int = Field(validation_alias="ClientMasterId")
    ledger_m_id: Optional[int] = Field(None, validation_alias="LedgerMId")
    description: Optional[str] = Field(None, validation_alias="Description")
    amount: Decimal = Field(validation_alias="amount")
    cgst_per: Decimal = Field(validation_alias="CGSTPer")
    cgst_amt: Decimal = Field(validation_alias="CGSTAmt")
    sgst_per: Decimal = Field(validation_alias="SGSTPer")
    sgst_amt: Decimal = Field(validation_alias="SGSTAmt")
    igst_per: Decimal = Field(validation_alias="IGSTPer")
    igst_amt: Decimal = Field(validation_alias="IGSTAmt")
    total: Decimal = Field(validation_alias="Total")
    received_amt: Decimal = Field(validation_alias="ReceivedAmt")
    balance_amt: Decimal = Field(validation_alias="BalanceAmt")
    acc_doc_no: Optional[str] = Field(None, validation_alias="AccDocNo")
    created_user: Optional[int] = Field(None, validation_alias="CreatedUser")
    created_date: Optional[datetime] = Field(None, validation_alias="Createdate")
    items: List[CommercialInvoiceLineItemResponse] = Field(default_factory=list)


# ============================================================================
# 5. COMMERCIAL SALES REGISTER REPORT SCHEMAS
# ============================================================================

class CommercialSalesRegisterReportItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    sales_reg_id: int
    sales_date: date
    r_company: Optional[str] = None
    invoice_no: str
    sales_type: Optional[str] = None
    client_name: Optional[str] = None
    description: Optional[str] = None
    amount: Decimal
    cgst_per: Decimal
    cgst_amt: Decimal
    sgst_per: Decimal
    sgst_amt: Decimal
    igst_per: Decimal
    igst_amt: Decimal
    total: Decimal
    received_amt: Decimal
    balance_amt: Decimal


class CommercialSalesRegisterReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    items: List[CommercialSalesRegisterReportItem]
    total_taxable: Decimal
    total_cgst: Decimal
    total_sgst: Decimal
    total_igst: Decimal
    total_grand: Decimal
    total_received: Decimal
    total_balance: Decimal
    count: int


# ============================================================================
# 6. SISTER CONCERN ADVANCE SCHEMAS
# ============================================================================

class CompanyAdvanceCreateRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    ledger_m_id: int = Field(..., ge=1, description="Sister concern / corporate company ledger ID")
    advance_date: date = Field(..., description="Disbursement date")
    amount: Decimal = Field(..., gt=Decimal("0.00"), description="Principal advance disbursement amount")
    description: Optional[str] = Field(None, max_length=500, description="Disbursement narration/purpose")


class CompanyAdvanceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    company_adv_id: int = Field(validation_alias="CompanyAdvId")
    ledger_m_id: int = Field(validation_alias="LedgerMID")
    advance_date: date = Field(validation_alias="compAdvDate")
    amount: Decimal = Field(validation_alias="Amount")
    receiving_amount: Decimal = Field(validation_alias="RecivingAmount")
    balance_amt: Decimal = Field(validation_alias="BalanceAmt")
    description: Optional[str] = Field(None, validation_alias="Description")
    created_user: Optional[str] = Field(None, validation_alias="CreatedUser")
    created_date: datetime = Field(validation_alias="CreatedDate")


class CompanyAdvanceRecoveryRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    recovery_amount: Decimal = Field(..., gt=Decimal("0.00"), description="Amount to recover (must be > 0.00)")
    recovery_date: date = Field(..., description="Voucher recovery date")
    sales_invoice_id: Optional[str] = Field(None, max_length=100, description="Associated sales invoice number")
    acc_doc_no: Optional[str] = Field(None, max_length=100, description="Accounting voucher Doc_No")
    narration: Optional[str] = Field(None, max_length=500)


class CompanyAdvanceRecoveryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    advance: CompanyAdvanceResponse
    detail_id: int
    recovered_amount: Decimal
    acc_doc_no: Optional[str]
    sales_invoice_id: Optional[str]


class CompanyAdvanceDetailItem(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    detail_id: int = Field(validation_alias="DetailId")
    company_adv_id: int = Field(validation_alias="CompanyAdvId")
    ledger_m_id: int = Field(validation_alias="LedgerMID")
    history_date: date = Field(validation_alias="HistoryDate")
    sales_invoice_id: Optional[str] = Field(None, validation_alias="SalesInvoiceId")
    acc_doc_no: Optional[str] = Field(None, validation_alias="AccDocNo")
    amount: Decimal = Field(validation_alias="Amount")
    created_date: datetime = Field(validation_alias="CreatedDate")


class CompanyAdvanceReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    advances: List[CompanyAdvanceResponse]
    details: List[CompanyAdvanceDetailItem] = Field(default_factory=list)
    total_advance_amount: Decimal
    total_recovered_amount: Decimal
    total_balance_amount: Decimal
