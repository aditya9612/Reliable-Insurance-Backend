"""
Pydantic v2 Request & Response Schemas for Phase 7 Policy Booking & Transaction Engine.
All monetary, rate, IDV, discount, tax, commission, payment, and ledger fields strictly use Decimal (never float).
"""
from datetime import date, datetime
from decimal import Decimal
from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.quotation import (
    ALLOWED_NCB_SLABS,
    CANONICAL_VEHICLE_CATEGORIES,
    PremiumBreakdownResponse,
    PremiumCalculationRequest,
)


ALLOWED_PAYMENT_TYPES = {
    "CASH",
    "CHEQUE",
    "DD",
    "ONLINE",
    "NEFT",
    "RTGS",
    "UPI",
    "CREDIT_CARD",
    "DEBIT_CARD",
    "CUTNPAY",
    "EWALLET",
    "DIRECT_TO_INSURER",
}


class PaymentInstrumentCreateRequest(BaseModel):
    """
    Input payload for creating a payment instrument row in tbl_transactionpayment.
    """
    model_config = ConfigDict(extra="forbid")

    payment_type: str = Field(
        default="CASH",
        description="CASH, CHEQUE, DD, ONLINE, NEFT, RTGS, UPI, CREDIT_CARD, DEBIT_CARD, CUTNPAY, EWALLET, or DIRECT_TO_INSURER",
    )
    paid_amount: Decimal = Field(
        ...,
        ge=Decimal("0.00"),
        description="Monetary amount paid via this instrument (Decimal >= 0.00)",
    )
    payment_date: Optional[date] = Field(default=None)
    docno: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Cheque number, DD number, UTR, or transaction reference number",
    )
    bankname: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Issuing bank name (mandatory for CHEQUE and DD)",
    )
    payment_details: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Payment narration or remarks",
    )
    idempotency_key: Optional[str] = Field(
        default=None,
        max_length=120,
        description="Optional idempotency key to prevent duplicate payment instrument recording",
    )
    wallet_owner_type: Optional[Literal["AGENT", "FRANCHISE"]] = Field(
        default=None,
        description="Optional E-Wallet owner type when payment_type is EWALLET",
    )
    wallet_owner_id: Optional[int] = Field(
        default=None,
        ge=1,
        description="Optional E-Wallet owner ID when payment_type is EWALLET",
    )
    wallet_lock_id: Optional[int] = Field(
        default=None,
        ge=1,
        description="Optional AccountId of an active E-Wallet lock to consume",
    )
    simulate_failure_at: Optional[
        Literal["AFTER_PAYMENT_INSERT", "BEFORE_LEDGER_COMMIT"]
    ] = Field(
        default=None,
        description="Test-only fault injection trigger for payment rollback verification",
    )

    @field_validator("payment_type")
    @classmethod
    def validate_payment_type(cls, v: str) -> str:
        norm = v.strip().upper()
        if norm not in ALLOWED_PAYMENT_TYPES:
            raise ValueError(
                f"Invalid payment_type '{v}'. Allowed: {sorted(ALLOWED_PAYMENT_TYPES)}"
            )
        return norm

    @model_validator(mode="after")
    def validate_cheque_fields(self) -> "PaymentInstrumentCreateRequest":
        if self.payment_type in {"CHEQUE", "DD"}:
            if not self.docno or not self.docno.strip():
                raise ValueError(
                    f"docno (Cheque/DD Number) is required when payment_type is {self.payment_type}."
                )
            if not self.bankname or not self.bankname.strip():
                raise ValueError(
                    f"bankname is required when payment_type is {self.payment_type}."
                )
        return self


class PaymentInstrumentResponse(BaseModel):
    """Persisted or previewed payment instrument row from tbl_transactionpayment."""
    payment_id: Optional[int] = None
    transaction_id: Optional[int] = None
    payment_type: str
    paid_amount: Decimal
    payment_date: Optional[datetime] = None
    docno: Optional[str] = None
    bankname: Optional[str] = None
    payment_details: Optional[str] = None
    status: Optional[str] = None
    extra_reference: Optional[str] = None
    is_complete_payment: int = 0
    cashier_approval: Optional[int] = None
    cashier_approval_date: Optional[datetime] = None
    accountant_approval: Optional[int] = None
    accountant_approval_date: Optional[datetime] = None
    owner_approval: Optional[int] = None
    branch_id: Optional[int] = None
    isdeleted: str = "0"



class CommissionInput(BaseModel):
    """
    Multi-bucket commission & TDS input parameters for Policy Booking.
    """
    model_config = ConfigDict(extra="forbid")

    agent_id: Optional[int] = Field(default=None, ge=0)
    sales_ex_id: Optional[int] = Field(default=None, ge=0)
    franchise_id: Optional[int] = Field(default=None, ge=0)
    location_head_id: Optional[int] = Field(default=None, ge=0)

    # Headline single commission rate OR component split rates
    agent_comm_percent: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"), le=Decimal("100.00"))
    agent_comm_od_percent: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"), le=Decimal("100.00"))
    agent_comm_net_percent: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"), le=Decimal("100.00"))
    agent_comm_extra_percent: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"), le=Decimal("100.00"))

    # Optional Franchise override rates (defaults to agent component rates if omitted when franchise_id > 0)
    franchise_comm_od_percent: Optional[Decimal] = Field(default=None, ge=Decimal("0.00"), le=Decimal("100.00"))
    franchise_comm_net_percent: Optional[Decimal] = Field(default=None, ge=Decimal("0.00"), le=Decimal("100.00"))
    franchise_comm_extra_percent: Optional[Decimal] = Field(default=None, ge=Decimal("0.00"), le=Decimal("100.00"))

    tds_percent: Decimal = Field(default=Decimal("5.00"), ge=Decimal("0.00"), le=Decimal("100.00"))
    commission_on_full_net: bool = Field(
        default=False,
        description="If True, Net commission bucket uses full NetPermium even when OD commission is also present",
    )
    include_pa_in_tp_comm: bool = Field(
        default=True,
        description="If True, TP commission base uses full TPPermium; if False, subtracts PACovertoOwner",
    )
    enforce_hdfc_gcv_net_only: bool = Field(
        default=False,
        description="If True (or when insurance_company_id=2 and policy_type_id>18 per adm_PolicyDetails.aspx.cs:L1468), forces GCV + HDFC ERGO Net-only commission calculation",
    )
    self_discount: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    incentive_amount: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))


class PolicyPremiumSummary(BaseModel):
    """Revalidated monetary breakdown for tbl_transaction."""
    sum_insured_idv: Decimal
    gvw: Decimal = Decimal("0.00")
    od_premium: Decimal
    tp_premium: Decimal
    basic_tp_premium: Decimal = Decimal("0.00")
    net_premium: Decimal
    gst_amount: Decimal
    final_premium: Decimal
    ncb_percent: Decimal
    ncb_amount: Decimal
    od_discount_percent: Decimal
    od_discount_amount: Decimal = Decimal("0.00")
    addon_rate_percent: Decimal = Decimal("0.00")
    addon_premium: Decimal = Decimal("0.00")
    is_nill_dep: bool = False
    imt23_amount: Decimal = Decimal("0.00")
    towing_amount: Decimal = Decimal("0.00")
    rsa_amount: Decimal = Decimal("0.00")
    pa_owner_driver: Decimal = Decimal("0.00")
    pa_driver_cleaner: Decimal = Decimal("0.00")
    ll_paid_driver: Decimal = Decimal("0.00")


class PolicyCommissionSummary(BaseModel):
    """Deterministic multi-bucket commission and TDS breakdown."""
    agent_id: int = 0
    sales_ex_id: int = 0
    franchise_id: int = 0
    location_head_id: int = 0

    od_commission_base: Decimal = Decimal("0.00")
    agent_comm_od_percent: Decimal = Decimal("0.00")
    agent_comm_od_amount: Decimal = Decimal("0.00")
    tds_od_amount: Decimal = Decimal("0.00")
    net_comm_od_amount: Decimal = Decimal("0.00")

    net_commission_base: Decimal = Decimal("0.00")
    agent_comm_net_percent: Decimal = Decimal("0.00")
    agent_comm_net_amount: Decimal = Decimal("0.00")
    tds_net_amount: Decimal = Decimal("0.00")
    net_comm_net_amount: Decimal = Decimal("0.00")

    extra_commission_base: Decimal = Decimal("0.00")
    agent_comm_extra_percent: Decimal = Decimal("0.00")
    agent_comm_extra_amount: Decimal = Decimal("0.00")
    tds_extra_amount: Decimal = Decimal("0.00")
    net_comm_extra_amount: Decimal = Decimal("0.00")

    headline_agent_comm_percent: Decimal = Decimal("0.00")
    total_gross_commission: Decimal = Decimal("0.00")
    tds_percent: Decimal = Decimal("5.00")
    total_tds_amount: Decimal = Decimal("0.00")
    total_net_commission: Decimal = Decimal("0.00")

    # Franchise Commission Ledger Summary (tbl_franchisecommission)
    franchise_comm_id: Optional[int] = None
    franchise_gross_commission: Decimal = Decimal("0.00")
    franchise_tds_amount: Decimal = Decimal("0.00")
    franchise_net_commission: Decimal = Decimal("0.00")

    # Cut & Pay / Agent Commission Settlement IDs
    cutnpay_payable_id: Optional[int] = None
    agent_comm_pay_id: Optional[int] = None


class PolicyPaymentSummary(BaseModel):
    """Deterministic payment collection, Cut & Pay, E-Wallet, and balance summary."""
    gross_payable_amount: Decimal
    cutnpay_enabled: bool = False
    cutnpay_deduction: Decimal = Decimal("0.00")
    ewallet_amount_used: Decimal = Decimal("0.00")
    online_payment_to_company: Decimal = Decimal("0.00")
    required_payable_amount: Decimal
    instrument_paid_amount: Decimal
    paid_amount: Decimal
    outstanding_amount: Decimal
    is_complete_payment: int
    payments: List[PaymentInstrumentResponse] = Field(default_factory=list)


class AccountingEntryResponse(BaseModel):
    """Double-entry financial ledger row in tbl_account."""
    account_id: Optional[int] = None
    acc_trans_id: int
    transaction_type: str
    ledger_m_id: int
    amount: Decimal
    narration: str
    reference_cust_id: Optional[int] = None
    reference_agent_id: Optional[int] = None
    branch_id: int
    payment_type: Optional[str] = None
    transaction_id: Optional[int] = None
    cust_veh_id: int = 0
    is_nill: int = 0
    isdeleted: int = 0


class PolicyPreviewRequest(BaseModel):
    """
    Request payload for POST /api/v1/policies/preview.
    Evaluates and revalidates premium, NCB, OD discount, GST, commission, payment, and ledger entries
    without writing to the database.
    """
    model_config = ConfigDict(extra="forbid")

    quotation_id: Optional[int] = Field(default=None, ge=1)
    quotation_source_type: Optional[Literal["SELF_QUOTATION", "ASSISTED_REQUEST"]] = Field(default=None)
    calculation_input: Optional[PremiumCalculationRequest] = Field(default=None)

    insurance_company_id: int = Field(default=1, ge=1)
    policy_type_id: int = Field(default=1, ge=1, le=30)
    product_type_id: int = Field(default=1, ge=1, le=3)
    business_type_id: int = Field(default=3, ge=1, le=8)
    vehicle_category: str = Field(default="PVT")
    motor_or_non_motor: Literal["MOTOR", "NONMOTOR"] = Field(
        default="MOTOR",
        description="MOTOR or NONMOTOR (adm_NewEntryForLifeORHelth.aspx.cs parity: NONMOTOR uses 15% default TDS)",
    )
    gcv_split_tp_gst: bool = Field(default=True)
    risk_start_date: Optional[date] = Field(
        default=None,
        description="Policy risk start date; when explicitly provided or apply_gcv_2025_09_23_tp_gst_cutover=True, applies adm_PolicyDetails.aspx.cs:L636-644 GCV Basic TP GST 5% (>= 2025-09-23) vs 12% (< 2025-09-23)",
    )
    apply_gcv_2025_09_23_tp_gst_cutover: bool = Field(
        default=False,
        description="Explicitly apply adm_PolicyDetails.aspx.cs:L636-644 2025-09-23 GCV Basic TP GST cutover (5% vs 12%)",
    )
    gcv_basic_tp_gst_rate_override: Optional[Decimal] = Field(
        default=None,
        ge=Decimal("0.00"),
        le=Decimal("100.00"),
    )
    claim_in_previous_policy: bool = Field(default=False)

    # Direct underwriting figures (optional when calculation_input or quotation_id is supplied)
    sum_insured_idv: Optional[Decimal] = Field(default=None, ge=Decimal("0.00"))
    gvw: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    od_premium: Optional[Decimal] = Field(default=None, ge=Decimal("0.00"))
    tp_premium: Optional[Decimal] = Field(default=None, ge=Decimal("0.00"))
    basic_tp_premium: Optional[Decimal] = Field(default=None, ge=Decimal("0.00"))
    net_premium: Optional[Decimal] = Field(default=None, ge=Decimal("0.00"))
    gst_amount: Optional[Decimal] = Field(default=None, ge=Decimal("0.00"))
    final_premium: Optional[Decimal] = Field(default=None, ge=Decimal("0.00"))

    ncb_percent: Decimal = Field(default=Decimal("0.00"))
    ncb_amount: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    od_discount_percent: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"), le=Decimal("100.00"))
    od_discount_amount: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    addon_rate_percent: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    addon_premium: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    is_nill_dep: bool = Field(default=False)
    imt23_amount: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    towing_amount: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    rsa_amount: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    pa_owner_driver: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    pa_driver_cleaner: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    ll_paid_driver: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))

    allow_underwriting_override: bool = Field(default=False)
    validate_statutory_gst: bool = Field(default=True)

    commission: CommissionInput = Field(default_factory=CommissionInput)
    policy_mode_id: int = Field(default=1, ge=1, le=10)
    cutnpay_enabled: bool = Field(default=False)
    cutnpay_amount: Optional[Decimal] = Field(default=None, ge=Decimal("0.00"))
    ewallet_amount_used: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    online_payment_to_company: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    payments: List[PaymentInstrumentCreateRequest] = Field(default_factory=list)

    @field_validator("vehicle_category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        key = v.strip().upper()
        if key not in CANONICAL_VEHICLE_CATEGORIES:
            raise ValueError(
                f"Unsupported vehicle_category '{v}'. Allowed: {sorted(set(CANONICAL_VEHICLE_CATEGORIES.values()))}"
            )
        return CANONICAL_VEHICLE_CATEGORIES[key]

    @field_validator("ncb_percent")
    @classmethod
    def validate_ncb(cls, v: Decimal) -> Decimal:
        if v not in ALLOWED_NCB_SLABS:
            raise ValueError(f"Invalid NCB slab {v}%. Allowed slabs: 0, 20, 25, 35, 45, 50")
        return v


class PolicyPreviewResponse(BaseModel):
    """Complete stateless/quotation-backed policy financial preview response."""
    source_type: str
    quotation_code: Optional[str] = None
    insurance_company_id: int
    product_type_id: int
    business_type_id: int
    vehicle_category: str
    t_status: str
    pending_status: int
    premium_summary: PolicyPremiumSummary
    commission_summary: PolicyCommissionSummary
    payment_summary: PolicyPaymentSummary
    accounting_entries: List[AccountingEntryResponse]
    rating_breakdown: Optional[PremiumBreakdownResponse] = None


class PolicyBookingCreateRequest(PolicyPreviewRequest):
    """
    Request payload for POST /api/v1/policies/book.
    Executes atomic policy booking across tbl_transaction, tbl_transactionpayment,
    commission tables, and tbl_account.
    """
    customer_id: int = Field(..., ge=1, description="CustomerId from tbl_customer")
    cust_veh_id: int = Field(..., ge=1, description="CustVehId from tbl_vehicledetails")
    proposal_trans_id: Optional[int] = Field(
        default=None,
        ge=1,
        description="Optional staged proposal TransId from tbl_transactionappnew",
    )
    branch_id: Optional[int] = Field(
        default=None,
        ge=1,
        description="Optional BranchId override (honored only for Global Admin roles)",
    )
    idempotency_key: Optional[str] = Field(
        default=None,
        max_length=120,
        description="Optional client idempotency key to prevent duplicate policy booking",
    )
    policy_no: Optional[str] = Field(default=None, max_length=255)
    lead_no: Optional[str] = Field(default=None, max_length=255)
    trans_date: Optional[date] = Field(default=None)
    cn_issue_date: Optional[date] = Field(default=None)
    risk_start_date: date = Field(default_factory=date.today)
    expiry_date: Optional[date] = Field(default=None)
    remark: Optional[str] = Field(default=None, max_length=255)
    wallet_owner_type: Optional[Literal["AGENT", "FRANCHISE"]] = Field(default=None)
    wallet_owner_id: Optional[int] = Field(default=None, ge=1)
    wallet_lock_id: Optional[int] = Field(default=None, ge=1)

    # Fault injection hook strictly for atomicity / rollback verification tests
    simulate_failure_at: Optional[
        Literal[
            "AFTER_TRANSACTION",
            "AFTER_PAYMENT",
            "AFTER_COMMISSION",
            "DURING_ACCOUNTING",
        ]
    ] = Field(
        default=None,
        description="Test-only fault injection trigger to verify single unit-of-work rollback",
    )



class PolicyBookingUpdateRequest(BaseModel):
    """
    Request payload for PUT /api/v1/policies/{transaction_id} (sp_UpdateTransactionNew_2026 parity).
    """
    model_config = ConfigDict(extra="forbid")

    policy_no: Optional[str] = Field(default=None, max_length=255)
    cn_issue_date: Optional[date] = Field(default=None)
    risk_start_date: Optional[date] = Field(default=None)
    expiry_date: Optional[date] = Field(default=None)
    t_status: Optional[str] = Field(default=None, max_length=100)
    remark: Optional[str] = Field(default=None, max_length=255)
    commission: Optional[CommissionInput] = Field(default=None)


class PolicyCancelRequest(BaseModel):
    """
    Request payload for POST /api/v1/policies/{transaction_id}/cancel (sp_DeleteTransactionByTransId parity).
    """
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(..., min_length=3, max_length=255)
    policy_cancel_id: int = Field(default=1, ge=1)
    use_legacy_cust_veh_id_500_sentinel: bool = Field(
        default=False,
        description="If True, sets CustVehId=500 on cancelled transaction per PolicyTransactionNew.aspx.cs",
    )


class PolicyBookingResponse(BaseModel):
    """
    Complete persisted Policy Transaction response (tbl_transaction + downstream tables).
    """
    transaction_id: int
    inward_no: str
    trans_date: datetime
    branch_id: int
    financial_year: str
    customer_id: int
    cust_veh_id: int
    insurance_company_id: int
    policy_type_id: int
    product_type_id: int
    business_type_id: int
    policy_no: Optional[str] = None
    cn_issue_date: Optional[datetime] = None
    risk_start_date: Optional[datetime] = None
    expiry_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    quotation_code: Optional[str] = None
    proposal_trans_id: int = 0
    t_status: str
    pending_status: int
    isdeleted: str = "0"
    remark: Optional[str] = None
    premium_summary: PolicyPremiumSummary
    commission_summary: PolicyCommissionSummary
    payment_summary: PolicyPaymentSummary
    accounting_entries: List[AccountingEntryResponse] = Field(default_factory=list)


class PolicyBookingListResponse(BaseModel):
    """Paginated list of booked policy transactions."""
    total: int
    limit: int
    offset: int
    items: List[PolicyBookingResponse]


class PolicyCancelResponse(BaseModel):
    """Response returned after atomic policy cancellation and ledger reversal."""
    transaction_id: int
    inward_no: str
    t_status: str
    isdeleted: str
    cust_veh_id: int = 0
    payments_reversed: int
    accounting_entries_reversed: int
    franchise_commissions_reversed: int
    cutnpay_reversed: int
    agent_comm_payments_reversed: int
    reason: str


# ---------------------------------------------------------------------------
# Staged Policy Proposal Schemas (tbl_transactionappnew)
# ---------------------------------------------------------------------------


class PolicyProposalCreateRequest(BaseModel):
    """
    Request payload for POST /api/v1/policies/proposals
    (Sp_InsertAppTransctiondetailsNew8 / InsertAppTransactionNew parity).
    """
    model_config = ConfigDict(extra="forbid")

    quotation_id: Optional[int] = Field(default=None, ge=1)
    quotation_source_type: Optional[Literal["SELF_QUOTATION", "ASSISTED_REQUEST"]] = Field(default=None)
    quotation_code: Optional[str] = Field(default=None, max_length=255)

    customer_name: str = Field(..., min_length=2, max_length=255)
    contact_no: str = Field(..., min_length=10, max_length=15)
    email_id: Optional[str] = Field(default=None, max_length=255)
    registration_no: str = Field(..., min_length=4, max_length=50)
    insurance_company_id: int = Field(default=1, ge=1)
    product_type: str = Field(default="Comprehensive", max_length=100)
    business_type: str = Field(default="Roll Over", max_length=100)
    policy_mode: str = Field(default="CASH", max_length=100)
    vehicle_type: str = Field(default="PVT", max_length=100)
    mgf_year: str = Field(default="2024", max_length=20)

    start_date: date = Field(default_factory=date.today)
    expiry_date: Optional[date] = Field(default=None)

    idv_amount: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    od_discount_percent: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"), le=Decimal("100.00"))
    ncb_percent: Decimal = Field(default=Decimal("0.00"))
    ncb_amount: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    od_premium: Decimal = Field(..., ge=Decimal("0.00"))
    tp_premium: Decimal = Field(..., ge=Decimal("0.00"))
    net_premium: Decimal = Field(..., ge=Decimal("0.00"))
    final_premium: Decimal = Field(..., ge=Decimal("0.00"))

    cash_paid_amount: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    ewallet_used_amount: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    payment_details_1: Optional[str] = Field(default=None, max_length=255)
    payment_details_2: Optional[str] = Field(default=None, max_length=255)
    remark: Optional[str] = Field(default=None, max_length=255)

    agent_id: Optional[int] = Field(default=None, ge=0)
    sales_executive_id: Optional[int] = Field(default=None, ge=0)
    franchise_id: Optional[int] = Field(default=None, ge=0)

    @field_validator("ncb_percent")
    @classmethod
    def validate_proposal_ncb(cls, v: Decimal) -> Decimal:
        if v not in ALLOWED_NCB_SLABS:
            raise ValueError(f"Invalid NCB slab {v}%. Allowed slabs: 0, 20, 25, 35, 45, 50")
        return v


class PolicyProposalApprovalRequest(BaseModel):
    """
    Request payload for POST /api/v1/policies/proposals/{trans_id}/approve
    (Cashier, Accountant, and Owner approval gates).
    """
    model_config = ConfigDict(extra="forbid")

    stage: Literal["CASHIER", "ACCOUNTANT", "OWNER"]
    approved: bool = Field(default=True)
    remark: Optional[str] = Field(default=None, max_length=255)


class PolicyProposalResponse(BaseModel):
    """Persisted staged proposal response from tbl_transactionappnew."""
    trans_id: int
    trans_date: Optional[datetime] = None
    quotation_code: Optional[str] = None
    quot_type: str
    customer_name: Optional[str] = None
    contact_no: Optional[str] = None
    registration_no: Optional[str] = None
    insurance_company: Optional[str] = None
    product_type: Optional[str] = None
    business_type: Optional[str] = None
    policy_mode: Optional[str] = None
    start_date: Optional[date] = None
    expiry_date: Optional[date] = None
    idv_amount: Decimal
    od_discount_percent: Decimal
    ncb_percent: Decimal
    ncb_amount: Decimal
    od_premium: Decimal
    tp_premium: Decimal
    net_premium: Decimal
    final_premium: Decimal
    cash_paid_amount: Decimal
    cash_short_amount: Decimal
    ewallet_used_amount: Decimal
    outstanding_amount: Decimal
    is_owner_approve: int = 0
    is_cashier_approve: int = 0
    is_account_approval: int = 0
    is_submit: int = 0
    user_id: Optional[int] = None
    sales_executive_id: Optional[int] = None
    franchise_id: Optional[int] = None
    franchise_code: str = "0"
    approved_by: Optional[str] = None
    account_remark: Optional[str] = None


class PolicyProposalListResponse(BaseModel):
    """Paginated list of staged policy proposals."""
    total: int
    limit: int
    offset: int
    items: List[PolicyProposalResponse]
