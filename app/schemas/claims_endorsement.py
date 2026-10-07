from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Generic, List, Literal, Optional, TypeVar
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    success: bool = True
    message: str = "OK"
    data: T


ClaimTypeLiteral = Literal["OD", "TP", "THEFT", "TOTAL_LOSS"]
ClaimStatusLiteral = Literal[
    "INTIMATED",
    "REGISTERED",
    "UNDER_SURVEY",
    "ASSESSED",
    "APPROVED",
    "SETTLED",
    "CLOSED",
    "REJECTED",
    "CANCELLED",
    "REOPENED",
]
PayeeTypeLiteral = Literal["CUSTOMER", "GARAGE", "INSURER"]
ClaimDocTypeLiteral = Literal[
    "FIR",
    "RC",
    "DL",
    "CLAIM_FORM",
    "ESTIMATE",
    "REPAIR_INVOICE",
    "SURVEY_REPORT",
    "DISCHARGE_VOUCHER",
    "PHOTO",
]

# Complete 22-type Legacy EndorsementId (1..22) Dispatch Mapping (LBR-124)
LEGACY_ENDORSEMENT_TYPE_ID_MAP: Dict[int, str] = {
    1: "NAME_CORRECTION",
    2: "VEHICLE_REGISTRATION_CORRECTION",
    3: "ADDRESS_CORRECTION",
    4: "ENGINE_CHASSIS_CORRECTION",
    5: "MAKE_MODEL_CORRECTION",
    6: "HYPOTHECATION_CHANGE",
    7: "IDV_CHANGE",
    8: "NCB_CORRECTION",
    9: "NOMINEE_CHANGE",
    10: "CC_SEATING_GVW_CORRECTION",
    11: "POLICY_PERIOD_CORRECTION",
    12: "OWNERSHIP_TRANSFER",
    13: "NCB_RECOVERY",
    14: "COVERAGE_ADDON_CHANGE",
    15: "LPG_CNG_KIT_CHANGE",
    16: "ACCESSORIES_CHANGE",
    17: "PA_COVER_CHANGE",
    18: "LL_COVER_CHANGE",
    19: "ZERO_DEP_CHANGE",
    20: "VOLUNTARY_DEDUCTIBLE_CHANGE",
    21: "CONTACT_CORRECTION",
    22: "OTHER_CORRECTION",
}

LEGACY_ENDORSEMENT_TYPE_TO_ID_MAP: Dict[str, int] = {
    v: k for k, v in LEGACY_ENDORSEMENT_TYPE_ID_MAP.items()
}

EndorsementTypeLiteral = Literal[
    "NAME_CORRECTION",
    "ADDRESS_CORRECTION",
    "CONTACT_CORRECTION",
    "VEHICLE_REGISTRATION_CORRECTION",
    "ENGINE_CHASSIS_CORRECTION",
    "MAKE_MODEL_CORRECTION",
    "HYPOTHECATION_CHANGE",
    "NOMINEE_CHANGE",
    "CC_SEATING_GVW_CORRECTION",
    "POLICY_PERIOD_CORRECTION",
    "OTHER_CORRECTION",
    "IDV_CHANGE",
    "NCB_CORRECTION",
    "NCB_RECOVERY",
    "COVERAGE_ADDON_CHANGE",
    "LPG_CNG_KIT_CHANGE",
    "ACCESSORIES_CHANGE",
    "PA_COVER_CHANGE",
    "LL_COVER_CHANGE",
    "ZERO_DEP_CHANGE",
    "VOLUNTARY_DEDUCTIBLE_CHANGE",
    "OWNERSHIP_TRANSFER",
]
EndorsementCategoryLiteral = Literal[
    "NON_FINANCIAL",
    "ADDITIONAL_PREMIUM",
    "REFUND_PREMIUM",
    "ZERO_PREMIUM",
]
EndorsementStatusLiteral = Literal[
    "DRAFT",
    "SUBMITTED",
    "APPROVED",
    "APPLIED",
    "REJECTED",
    "CANCELLED",
    "REVERSED",
]
RefundStatusLiteral = Literal[
    "NONE",
    "PENDING_APPROVAL",
    "APPROVED",
    "REFUNDED",
    "REVERSED",
]


def _validate_safe_storage_key(val: Optional[str]) -> Optional[str]:
    if val is None:
        return None
    cleaned = val.strip()
    if not cleaned:
        raise ValueError("Storage key cannot be empty")
    if ".." in cleaned or "\\" in cleaned or ":" in cleaned:
        raise ValueError(
            "Unsafe storage key: raw filesystem paths, drive letters, backslashes, and '..' traversal are prohibited"
        )
    return cleaned


class ClaimIntimateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    transaction_id: int = Field(..., gt=0, description="Booked policy TransanctionId in tbl_transaction")
    claim_type: ClaimTypeLiteral = Field(default="OD")
    loss_date: datetime
    intimation_date: Optional[datetime] = None
    loss_location: str = Field(..., min_length=2, max_length=255)
    loss_description: str = Field(..., min_length=3, max_length=2000)
    estimated_amount: Decimal = Field(..., gt=Decimal("0.00"))
    insurer_claim_ref: Optional[str] = Field(default=None, max_length=100)
    remarks: Optional[str] = Field(default=None, max_length=1000)
    idempotency_key: Optional[str] = Field(default=None, max_length=100)


class ClaimRegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    insurer_claim_ref: str = Field(..., min_length=2, max_length=100)
    remarks: Optional[str] = Field(default=None, max_length=1000)


class ClaimSurveyUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    surveyor_name: str = Field(..., min_length=2, max_length=150)
    surveyor_mobile: Optional[str] = Field(default=None, max_length=20)
    surveyor_license_no: str = Field(..., min_length=2, max_length=50)
    survey_date: Optional[datetime] = None
    remarks: Optional[str] = Field(default=None, max_length=1000)


class ClaimAssessmentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    assessed_loss_amount: Decimal = Field(..., gt=Decimal("0.00"))
    depreciation_amount: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    deductible_amount: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    excess_amount: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    salvage_amount: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    remarks: Optional[str] = Field(default=None, max_length=1000)


class ClaimApprovalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    approved_amount: Optional[Decimal] = Field(default=None, gt=Decimal("0.00"))
    remarks: Optional[str] = Field(default=None, max_length=1000)


class ClaimSettlementRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    settled_amount: Decimal = Field(..., gt=Decimal("0.00"))
    bill_amount: Optional[Decimal] = Field(default=None, ge=Decimal("0.00"), description="Legacy FinalBill BillAmt")
    icl_amount: Optional[Decimal] = Field(default=None, ge=Decimal("0.00"), description="Legacy FinalBill ICLAmt (Insurer Claim Liability)")
    il_amount: Optional[Decimal] = Field(default=None, ge=Decimal("0.00"), description="Legacy FinalBill ILAmt (Insured Liability)")
    payee_type: PayeeTypeLiteral = Field(default="CUSTOMER")
    payment_mode: str = Field(default="NEFT", min_length=2, max_length=30)
    payment_doc_no: str = Field(..., min_length=2, max_length=100)
    settlement_date: Optional[datetime] = None
    insurer_claim_ref: Optional[str] = Field(default=None, max_length=100)
    remarks: Optional[str] = Field(default=None, max_length=1000)
    idempotency_key: Optional[str] = Field(default=None, max_length=100)


class ClaimRejectionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rejection_reason: str = Field(..., min_length=3, max_length=500)
    remarks: Optional[str] = Field(default=None, max_length=1000)


class ClaimActionRemarksRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    remarks: str = Field(..., min_length=3, max_length=1000)


class ClaimDocumentCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_type: ClaimDocTypeLiteral
    document_name: str = Field(..., min_length=2, max_length=255)
    storage_key: str = Field(..., min_length=3, max_length=500)
    verified_status: Literal["PENDING", "VERIFIED", "REJECTED"] = Field(default="PENDING")
    remarks: Optional[str] = Field(default=None, max_length=500)

    @field_validator("storage_key")
    @classmethod
    def check_safe_storage_key(cls, v: str) -> str:
        res = _validate_safe_storage_key(v)
        assert res is not None
        return res


class ClaimDocumentResponse(BaseModel):
    claim_doc_id: int
    claim_id: int
    transaction_id: int
    document_type: str
    document_name: str
    storage_key: str
    verified_status: str
    remarks: Optional[str] = None
    create_date: datetime


class ClaimResponse(BaseModel):
    claim_id: int
    claim_no: str
    transaction_id: int
    policy_no: Optional[str] = None
    customer_id: Optional[int] = None
    cust_veh_id: Optional[int] = None
    insurance_company_id: Optional[int] = None
    branch_id: Optional[int] = None
    agent_id: Optional[int] = None
    franchise_id: Optional[int] = None
    sales_ex_id: Optional[int] = None
    claim_type: str
    claim_status: str
    intimation_date: datetime
    loss_date: datetime
    loss_location: Optional[str] = None
    loss_description: Optional[str] = None
    estimated_amount: Decimal
    surveyor_name: Optional[str] = None
    surveyor_mobile: Optional[str] = None
    surveyor_license_no: Optional[str] = None
    survey_date: Optional[datetime] = None
    assessed_loss_amount: Decimal
    depreciation_amount: Decimal
    deductible_amount: Decimal
    excess_amount: Decimal
    salvage_amount: Decimal
    approved_amount: Decimal
    settled_amount: Decimal
    bill_amount: Optional[Decimal] = None
    icl_amount: Optional[Decimal] = None
    il_amount: Optional[Decimal] = None
    insurer_payable_amount: Decimal
    customer_payable_amount: Decimal
    garage_payable_amount: Decimal
    payee_type: Optional[str] = None
    payment_mode: Optional[str] = None
    payment_doc_no: Optional[str] = None
    settlement_date: Optional[datetime] = None
    insurer_claim_ref: Optional[str] = None
    rejection_reason: Optional[str] = None
    remarks: Optional[str] = None
    idempotency_key: Optional[str] = None
    create_date: datetime


class ClaimListResponse(BaseModel):
    items: List[ClaimResponse]
    total: int


class EndorsementCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    transaction_id: int = Field(..., gt=0, description="Booked policy TransanctionId")
    endorsement_type: Optional[EndorsementTypeLiteral] = Field(default=None)
    legacy_endorsement_type_id: Optional[int] = Field(
        default=None,
        ge=1,
        le=22,
        description="Legacy integer EndorsementId (1..22) per LBR-124",
    )
    create_new_customer: bool = Field(
        default=False,
        description="When True on OWNERSHIP_TRANSFER, creates a new Customer row and rebinds policy.CustomerId and vehicle.CustomerId per OwnerTransferEndorsement.aspx.cs",
    )
    effective_date: Optional[datetime] = None
    field_changes: Dict[str, Any] = Field(..., min_length=1, description="Map of allowed field names to new values")
    submit: bool = Field(default=True, description="If True, creates in SUBMITTED status; if False, creates in DRAFT")
    supporting_doc_key: Optional[str] = Field(default=None, max_length=500)
    remarks: Optional[str] = Field(default=None, max_length=1000)
    idempotency_key: Optional[str] = Field(default=None, max_length=100)

    @model_validator(mode="before")
    @classmethod
    def resolve_endorsement_type_from_legacy_id(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        out = dict(data)
        legacy_id = out.get("legacy_endorsement_type_id")
        end_type = out.get("endorsement_type")
        if legacy_id is not None:
            mapped = LEGACY_ENDORSEMENT_TYPE_ID_MAP.get(int(legacy_id))
            if mapped is None:
                raise ValueError(f"Unsupported legacy_endorsement_type_id '{legacy_id}'; must be 1..22")
            if end_type is None:
                out["endorsement_type"] = mapped
        if out.get("endorsement_type") is None:
            raise ValueError("Either endorsement_type or legacy_endorsement_type_id (1..22) is required")
        return out

    @field_validator("supporting_doc_key")
    @classmethod
    def check_doc_key(cls, v: Optional[str]) -> Optional[str]:
        return _validate_safe_storage_key(v)


class EndorsementActionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    remarks: Optional[str] = Field(default=None, max_length=1000)


class EndorsementApplyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    remarks: Optional[str] = Field(default=None, max_length=1000)
    idempotency_key: Optional[str] = Field(default=None, max_length=100)
    paid_endorsement_fee: Optional[Decimal] = Field(
        default=None,
        ge=Decimal("0.00"),
        description="Optional endorsement fee received (AppEndorsementforApproval.aspx.cs txtPaidAmount)",
    )
    service_charge_amount: Optional[Decimal] = Field(
        default=None,
        ge=Decimal("0.00"),
        description="Optional service charge deducted before computing company amount (txt_paidAmt)",
    )
    from_ledger_id: Optional[int] = Field(
        default=None,
        gt=0,
        description="Receiving bank/cash LedgerMId for endorsement fee (AccTransId=2)",
    )
    pay_to_ledger_id: Optional[int] = Field(
        default=None,
        gt=0,
        description="PayTo LedgerMId for endorsement company fee (AccTransId=1)",
    )

    @model_validator(mode="before")
    @classmethod
    def _normalize_service_charge_alias(cls, data: Any) -> Any:
        if isinstance(data, dict) and "service_charge" in data:
            out = dict(data)
            val = out.pop("service_charge")
            if out.get("service_charge_amount") is None:
                out["service_charge_amount"] = val
            return out
        return data


class EndorsementRejectRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rejection_reason: str = Field(..., min_length=3, max_length=500)
    remarks: Optional[str] = Field(default=None, max_length=1000)


class RefundActionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    remarks: Optional[str] = Field(default=None, max_length=1000)


class RefundDisburseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    refund_mode: Literal["NEFT", "CHEQUE", "BANK_TRANSFER", "WALLET"] = Field(default="NEFT")
    refund_doc_no: str = Field(..., min_length=2, max_length=100)
    remarks: Optional[str] = Field(default=None, max_length=1000)
    idempotency_key: Optional[str] = Field(default=None, max_length=100)


class EndorsementPreviewResponse(BaseModel):
    transaction_id: int
    policy_no: Optional[str] = None
    endorsement_type: str
    legacy_endorsement_type_id: Optional[int] = None
    endorsement_category: str
    field_changes_snapshot: Dict[str, Dict[str, Any]]
    old_idv: Decimal
    new_idv: Decimal
    old_ncb_percent: Decimal
    new_ncb_percent: Decimal
    old_od_premium: Decimal
    new_od_premium: Decimal
    old_tp_premium: Decimal
    new_tp_premium: Decimal
    old_net_premium: Decimal
    new_net_premium: Decimal
    old_gst_amount: Decimal
    new_gst_amount: Decimal
    old_final_premium: Decimal
    new_final_premium: Decimal
    premium_delta: Decimal
    old_agent_net_comm: Decimal
    new_agent_net_comm: Decimal
    agent_comm_delta: Decimal
    old_agent_tds_amt: Decimal
    new_agent_tds_amt: Decimal
    old_franchise_net_comm: Decimal
    new_franchise_net_comm: Decimal
    franchise_comm_delta: Decimal
    commission_recovery_amount: Decimal
    estimated_refund_amount: Decimal


class EndorsementResponse(BaseModel):
    endorsement_id: int
    endorsement_no: str
    transaction_id: int
    policy_no: Optional[str] = None
    customer_id: Optional[int] = None
    previous_customer_id: Optional[int] = None
    current_customer_id: Optional[int] = None
    cust_veh_id: Optional[int] = None
    branch_id: Optional[int] = None
    agent_id: Optional[int] = None
    franchise_id: Optional[int] = None
    sales_ex_id: Optional[int] = None
    endorsement_type: str
    legacy_endorsement_type_id: Optional[int] = None
    endorsement_category: str
    endorsement_status: str
    effective_date: datetime
    request_date: datetime
    field_changes_snapshot: Dict[str, Dict[str, Any]]
    old_idv: Decimal
    new_idv: Decimal
    old_ncb_percent: Decimal
    new_ncb_percent: Decimal
    old_od_premium: Decimal
    new_od_premium: Decimal
    old_tp_premium: Decimal
    new_tp_premium: Decimal
    old_net_premium: Decimal
    new_net_premium: Decimal
    old_gst_amount: Decimal
    new_gst_amount: Decimal
    old_final_premium: Decimal
    new_final_premium: Decimal
    premium_delta: Decimal
    old_agent_net_comm: Decimal
    new_agent_net_comm: Decimal
    agent_comm_delta: Decimal
    old_agent_tds_amt: Decimal
    new_agent_tds_amt: Decimal
    old_franchise_net_comm: Decimal
    new_franchise_net_comm: Decimal
    franchise_comm_delta: Decimal
    commission_recovery_amount: Decimal
    refund_status: str
    refund_amount: Decimal
    refund_mode: Optional[str] = None
    refund_doc_no: Optional[str] = None
    supporting_doc_key: Optional[str] = None
    remarks: Optional[str] = None
    rejection_reason: Optional[str] = None
    idempotency_key: Optional[str] = None
    create_date: datetime


class EndorsementListResponse(BaseModel):
    items: List[EndorsementResponse]
    total: int
