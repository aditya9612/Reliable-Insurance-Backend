"""
Pydantic v2 Request & Response Schemas for Phase 18A — Complete Remaining Legacy Feature Implementation.
Enforces strict input validation (extra='forbid'), Decimal arithmetic for financial/percentage fields,
and clean serialization across all 10 SHOULD and 7 ENHANCE legacy capabilities.
"""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


# ==============================================================================
# F-17B-083: Outbound HiCaliber Policy PDF Upload & Transaction Pre-Fill
# ==============================================================================
class PolicyExtractionUploadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    calliber_policy_id: int
    policy_identifier: str
    extraction_id: str
    extraction_status: str
    file_name: str
    storage_key: str
    transaction_id: Optional[int] = None
    duplicate_policy_exists: bool = False
    extracted_fields: Dict[str, Any] = Field(default_factory=dict)


class PolicyExtractionPrefillResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    calliber_policy_id: int
    policy_identifier: str
    extraction_id: Optional[str] = None
    policy_number: Optional[str] = None
    insured_name: Optional[str] = None
    registration_number: Optional[str] = None
    chassis_number: Optional[str] = None
    engine_number: Optional[str] = None
    insurer_name: Optional[str] = None
    vehicle_make: Optional[str] = None
    vehicle_model: Optional[str] = None
    fuel_type: Optional[str] = None
    idv_amount: Decimal = Decimal("0.00")
    od_premium: Decimal = Decimal("0.00")
    tp_premium: Decimal = Decimal("0.00")
    net_premium: Decimal = Decimal("0.00")
    gst_amount: Decimal = Decimal("0.00")
    gross_premium: Decimal = Decimal("0.00")
    policy_start_date: Optional[str] = None
    policy_end_date: Optional[str] = None
    linked_transaction_id: Optional[int] = None
    duplicate_policy_exists: bool = False
    duplicate_transaction_ids: List[int] = Field(default_factory=list)


class PolicyExtractionLinkTransactionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    transaction_id: int = Field(..., gt=0, description="Target policy transaction ID (TransanctionId)")


class PolicyExtractionLinkTransactionResponse(BaseModel):
    calliber_policy_id: int
    transaction_id: int
    policy_number: Optional[str] = None
    status: str


# ==============================================================================
# F-17B-084: Extended Operator Lockouts (Pending Cash & Pending App Transactions)
# ==============================================================================
class PendingCashLockRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    default_threshold_days: int = Field(default=2, ge=1, le=90)
    mumbai_branch_id: int = Field(default=105, ge=1)
    mumbai_threshold_days: int = Field(default=3, ge=1, le=90)
    apply_user_lock: bool = Field(default=True)


class PendingCashLockResponse(BaseModel):
    evaluated_transactions: int
    overdue_default_branch_count: int
    overdue_mumbai_branch_count: int
    locked_user_ids: List[int] = Field(default_factory=list)
    overdue_transaction_ids: List[int] = Field(default_factory=list)


class PendingAppTransactionLockRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    threshold_days: int = Field(default=1, ge=0, le=90)
    apply_user_lock: bool = Field(default=True)


class PendingAppTransactionLockResponse(BaseModel):
    evaluated_app_transactions: int
    overdue_unapproved_count: int
    locked_user_ids: List[int] = Field(default_factory=list)
    overdue_app_transaction_ids: List[int] = Field(default_factory=list)


class OperatorLockStatusResponse(BaseModel):
    user_id: int
    branch_id: Optional[int] = None
    is_mumbai_branch: bool = False
    account_active: bool = True
    cheque_lock_overdue_count: int = 0
    pending_cash_overdue_count: int = 0
    pending_app_trans_overdue_count: int = 0
    is_locked: bool = False
    lock_reasons: List[str] = Field(default_factory=list)


# ==============================================================================
# F-17B-085: Bulk Ideal / Broker Payment Receipt & Multi-Agent Settlement
# ==============================================================================
class IdealPaymentReceiptRowInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ideal_doc_no: str = Field(..., min_length=1, max_length=100)
    payment_date: date
    posp_type_id: int = Field(default=1, ge=1)
    posp_id: int = Field(..., ge=1)
    ideal_amount: Decimal = Field(..., ge=Decimal("0.00"))
    ideal_neft_no: Optional[str] = Field(default=None, max_length=100)
    policy_no: Optional[str] = Field(default=None, max_length=255)
    transaction_id: Optional[int] = Field(default=None, ge=1)
    receipt_type: str = Field(default="Regular", pattern="^(Regular|Insta)$")


class IdealPaymentReceiptBulkRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    receipts: List[IdealPaymentReceiptRowInput] = Field(..., min_length=1)


class IdealPaymentReceiptResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ideal_doc_no: str
    payment_date: Optional[date] = None
    posp_type_id: Optional[int] = None
    posp_id: Optional[int] = None
    ideal_amount: Decimal
    ideal_neft_no: Optional[str] = None
    policy_no: Optional[str] = None
    transaction_id: Optional[int] = None
    receipt_type: str
    created_by: Optional[int] = None
    create_date: Optional[datetime] = None


class IdealPaymentReceiptBulkResult(BaseModel):
    total_submitted: int
    inserted_count: int
    duplicate_skipped_count: int
    total_settled_amount: Decimal
    receipt_ids: List[int] = Field(default_factory=list)


class InstaPayRequestCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    transaction_id: int = Field(..., gt=0)
    agent_id: int = Field(..., gt=0)
    requested_amount: Decimal = Field(..., gt=Decimal("0.00"))
    neft_reference: Optional[str] = Field(default=None, max_length=100)
    remark: Optional[str] = Field(default=None, max_length=255)


# ==============================================================================
# F-17B-086: Partner Commission Rate Grid & Reliance 90%/60% OD Capping
# ==============================================================================
class CommissionRateGridCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    grid_scope: str = Field(default="BROKER", pattern="^(BROKER|AGENT|FRANCHISE|CLUSTER)$")
    insurance_company_id: int = Field(..., gt=0)
    policy_type_id: Optional[int] = Field(default=None, ge=1)
    product_type_id: Optional[int] = Field(default=None, ge=1)
    vehi_type_id: Optional[int] = Field(default=None, ge=1)
    vehi_sub_type_id: Optional[int] = Field(default=None, ge=1)
    fuel_type_id: Optional[int] = Field(default=None, ge=1)
    make_id: Optional[int] = Field(default=None, ge=1)
    model_id: Optional[int] = Field(default=None, ge=1)
    rto_id: Optional[int] = Field(default=None, ge=1)
    state_id: Optional[int] = Field(default=None, ge=1)
    cluster_m_id: Optional[int] = Field(default=None, ge=1)
    broker_id: Optional[int] = Field(default=None, ge=1)
    franchise_id: Optional[int] = Field(default=None, ge=1)
    agent_id: Optional[int] = Field(default=None, ge=1)
    commission_od: Decimal = Field(..., ge=Decimal("0.00"), le=Decimal("100.00"))
    commission_net: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"), le=Decimal("100.00"))
    commission_tp: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"), le=Decimal("100.00"))
    od_discount: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"), le=Decimal("100.00"))
    cal_on: str = Field(default="OD", pattern="^(OD|NET|TP)$")
    valid_from_date: Optional[date] = None
    valid_to_date: Optional[date] = None


class CommissionRateGridResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    grid_id: int
    grid_scope: str
    insurance_company_id: int
    policy_type_id: Optional[int] = None
    product_type_id: Optional[int] = None
    vehi_type_id: Optional[int] = None
    fuel_type_id: Optional[int] = None
    make_id: Optional[int] = None
    model_id: Optional[int] = None
    rto_id: Optional[int] = None
    state_id: Optional[int] = None
    cluster_m_id: Optional[int] = None
    broker_id: Optional[int] = None
    franchise_id: Optional[int] = None
    agent_id: Optional[int] = None
    commission_od: Decimal
    commission_net: Decimal
    commission_tp: Decimal
    od_discount: Decimal
    cal_on: str
    valid_from_date: Optional[date] = None
    valid_to_date: Optional[date] = None


class RelianceCappingEvaluateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    grid_percent: Decimal = Field(..., ge=Decimal("0.00"), le=Decimal("100.00"))
    od_discount_percent: Decimal = Field(..., ge=Decimal("0.00"), le=Decimal("100.00"))
    od_premium: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))


class RelianceCappingEvaluateResponse(BaseModel):
    max_total_capping_percent: Decimal
    max_od_discount_percent: Decimal
    input_grid_percent: Decimal
    input_od_discount_percent: Decimal
    effective_od_discount_percent: Decimal
    effective_grid_percent: Decimal
    is_od_discount_capped: bool
    is_total_capping_applied: bool
    effective_commission_amount: Decimal


# ==============================================================================
# F-17B-087: Remaining / Shortfall Cash Premium Ledger & Cashier Approval
# ==============================================================================
class RemainingPendingCashCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    transaction_ids: List[int] = Field(..., min_length=1)
    total_premium: Decimal = Field(..., gt=Decimal("0.00"))
    paid_premium: Decimal = Field(..., ge=Decimal("0.00"))
    shortfall_amt: Optional[Decimal] = Field(default=None, ge=Decimal("0.00"))
    agent_id: Optional[int] = Field(default=None, ge=1)
    executive_id: Optional[int] = Field(default=None, ge=1)
    branch_id: Optional[int] = Field(default=None, ge=1)
    supporting_file_key: Optional[str] = Field(default=None, max_length=255)
    remark: Optional[str] = Field(default=None, max_length=500)


class RemainingPendingCashApproveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    approved: bool = Field(...)
    additional_paid_amount: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    remark: Optional[str] = Field(default=None, max_length=500)


class RemainingPendingCashResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    pending_cash_id: int
    transaction_ids: List[int]
    total_premium: Decimal
    paid_premium: Decimal
    remaining_premium: Decimal
    shortfall_amt: Decimal
    remaining_status: str
    agent_id: Optional[int] = None
    executive_id: Optional[int] = None
    branch_id: Optional[int] = None
    supporting_file_key: Optional[str] = None
    cashier_approval: int
    approved_by: Optional[int] = None
    approved_date: Optional[datetime] = None
    remark: Optional[str] = None
    create_date: Optional[datetime] = None


# ==============================================================================
# F-17B-088: Insurer B2B Sales Invoice Registration & Advance Adjustment
# ==============================================================================
class SalesRegistrationCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    invoice_no: str = Field(..., min_length=1, max_length=100)
    registration_type: str = Field(default="B2B_INSURER", max_length=100)
    sales_date: date
    r_company_id: Optional[int] = Field(default=None, ge=1)
    sales_type_id: Optional[int] = Field(default=1, ge=1)
    sales_type: Optional[str] = Field(default="COMMISSION_INVOICE", max_length=100)
    client_master_id: int = Field(..., gt=0)
    ledger_m_id: Optional[int] = Field(default=None, ge=1)
    description: Optional[str] = Field(default=None, max_length=500)
    amount: Decimal = Field(..., gt=Decimal("0.00"))
    cgst_per: Decimal = Field(default=Decimal("9.00"), ge=Decimal("0.00"), le=Decimal("28.00"))
    sgst_per: Decimal = Field(default=Decimal("9.00"), ge=Decimal("0.00"), le=Decimal("28.00"))
    igst_per: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"), le=Decimal("28.00"))


class SalesRegistrationAdvanceAdjustRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    received_amount: Decimal = Field(..., gt=Decimal("0.00"))
    history_date: date
    acc_doc_no: Optional[str] = Field(default=None, max_length=100)
    ledger_m_id: Optional[int] = Field(default=None, ge=1)
    narration: Optional[str] = Field(default=None, max_length=255)


class SalesRegistrationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    sales_reg_id: int
    invoice_no: str
    registration_type: Optional[str] = None
    sales_date: date
    r_company_id: Optional[int] = None
    sales_type_id: Optional[int] = None
    sales_type: Optional[str] = None
    client_master_id: int
    ledger_m_id: Optional[int] = None
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
    acc_doc_no: Optional[str] = None


# ==============================================================================
# F-17B-090: Automated Daily InstaPay Authority Summary Email / Report
# ==============================================================================
class InstaPayAuthorityDispatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    report_date: Optional[date] = None
    recipients: List[str] = Field(..., min_length=1)
    cc: Optional[List[str]] = None
    attach_pdf: bool = Field(default=True)


class InstaPayAuthoritySummaryResponse(BaseModel):
    report_date: date
    new_summary: Dict[str, Any]
    from_ra_summary: List[Dict[str, Any]]
    online_to_reliable_summary: List[Dict[str, Any]]
    total_policies: int
    total_gross_premium: Decimal
    total_instapay_payout: Decimal


# ==============================================================================
# F-17B-091: Vehicle Break-In Inspection Coordinator Request Queue
# ==============================================================================
class InspectionRequestCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    trans_id: Optional[int] = Field(default=None, ge=1)
    registration_no: str = Field(..., min_length=4, max_length=50)
    customer_name: Optional[str] = Field(default=None, max_length=255)
    mobile_no: Optional[str] = Field(default=None, max_length=50)
    insurance_company_id: Optional[int] = Field(default=None, ge=1)
    vehicle_type_id: Optional[int] = Field(default=None, ge=1)
    branch_id: Optional[int] = Field(default=None, ge=1)
    franchise_id: Optional[int] = Field(default=None, ge=1)
    agent_id: Optional[int] = Field(default=None, ge=1)
    executive_id: Optional[int] = Field(default=None, ge=1)
    remark: Optional[str] = Field(default=None, max_length=500)


class InspectionCoordinatorDecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: str = Field(..., pattern="^(APPROVED|REJECTED|DOCUMENTS_REQUIRED)$")
    lead_no: Optional[str] = Field(default=None, max_length=100)
    inspection_pdf_path: Optional[str] = Field(default=None, max_length=255)
    image_paths: Optional[List[str]] = None
    remark: Optional[str] = Field(default=None, max_length=500)


class InspectionRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    inspection_id: int
    trans_id: Optional[int] = None
    registration_no: str
    customer_name: Optional[str] = None
    mobile_no: Optional[str] = None
    insurance_company_id: Optional[int] = None
    vehicle_type_id: Optional[int] = None
    branch_id: Optional[int] = None
    franchise_id: Optional[int] = None
    agent_id: Optional[int] = None
    executive_id: Optional[int] = None
    lead_no: Optional[str] = None
    inspection_status: str
    is_owner: int
    inspection_pdf_path: Optional[str] = None
    image_paths: List[str] = Field(default_factory=list)
    remark: Optional[str] = None
    created_date: Optional[datetime] = None


# ==============================================================================
# F-17B-092: Internal IT / Operator / Admin Support Ticketing Portal
# ==============================================================================
class SupportTicketCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    support_type_id: int = Field(default=1, ge=1)
    support_type: str = Field(default="IT_TECHNICAL", min_length=2, max_length=100)
    remark: str = Field(..., min_length=3, max_length=2000)
    attachment_file_name: Optional[str] = Field(default=None, max_length=255)


class SupportTicketRemarkRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    remark: str = Field(..., min_length=1, max_length=2000)
    remark_from: str = Field(default="USER", pattern="^(USER|ADMIN|IT|OPTR)$")


class SupportTicketStatusUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str = Field(..., pattern="^(OPEN|IN_PROGRESS|RESOLVED|CLOSED)$")
    is_approved: Optional[bool] = None
    remark: Optional[str] = Field(default=None, max_length=1000)


class SupportTicketResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    support_id: int
    support_type_id: int
    support_type: str
    support_date: Optional[datetime] = None
    user_id: int
    user_role_id: Optional[int] = None
    branch_id: Optional[int] = None
    remark: str
    remark_from: Optional[str] = None
    remarks_thread: List[Dict[str, Any]] = Field(default_factory=list)
    attachment_file_name: Optional[str] = None
    attend_by: Optional[int] = None
    status: str
    is_approved: int
    approved_by: Optional[int] = None
    approved_date: Optional[datetime] = None


# ==============================================================================
# F-17B-093: Telecalling Lead Import, Call Disposition & Follow-Up CRM
# ==============================================================================
class CallingLeadItemInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    registration_no: str = Field(..., min_length=4, max_length=50)
    registration_type: Optional[str] = Field(default="PRIVATE", max_length=100)
    regn_date: Optional[date] = None
    owner_name: Optional[str] = Field(default=None, max_length=255)
    father_name: Optional[str] = Field(default=None, max_length=255)
    permanent_address: Optional[str] = Field(default=None, max_length=500)
    chassis_no: Optional[str] = Field(default=None, max_length=100)
    eng_no: Optional[str] = Field(default=None, max_length=100)
    vehicle_class: Optional[str] = Field(default=None, max_length=100)
    maker_model: Optional[str] = Field(default=None, max_length=255)
    dealer_name: Optional[str] = Field(default=None, max_length=255)
    mobile_no: Optional[str] = Field(default=None, max_length=50)
    assigned_user_id: Optional[int] = Field(default=None, ge=1)


class CallingLeadBulkImportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    leads: List[CallingLeadItemInput] = Field(..., min_length=1)


class CallingLeadAssignRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    assigned_user_id: int = Field(..., gt=0)


class CallingLeadDispositionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    calling_status_id: int = Field(..., ge=1)
    calling_status_name: Optional[str] = Field(default=None, max_length=100)
    follow_up_date: Optional[date] = None
    note: str = Field(..., min_length=1, max_length=500)


class CallingLeadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    calling_import_id: int
    registration_no: str
    registration_type: Optional[str] = None
    regn_date: Optional[date] = None
    owner_name: Optional[str] = None
    mobile_no: Optional[str] = None
    maker_model: Optional[str] = None
    user_id: Optional[int] = None
    branch_id: Optional[int] = None
    calling_status_id: Optional[int] = None
    calling_status_name: Optional[str] = None
    calling_date: Optional[datetime] = None
    follow_up_date: Optional[date] = None
    note: Optional[str] = None
    history: List[Dict[str, Any]] = Field(default_factory=list)


# ==============================================================================
# F-17B-094: Multi-Insurer Quotation Request & PDF File Sharing Workflow
# ==============================================================================
class RequestedQuotationFileCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    insurance_company_id: int = Field(..., gt=0)
    file_name: str = Field(..., min_length=3, max_length=255)


class RequestedQuotationFileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    quotation_file_id: int
    quotation_id: int
    insurance_company_id: int
    file_name: str


# ==============================================================================
# F-17B-095: Cashback & Promotional Scheme Entry
# ==============================================================================
class CashbackCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    transaction_id: int = Field(..., gt=0)
    customer_id: Optional[int] = Field(default=None, ge=1)
    cust_veh_id: Optional[int] = Field(default=None, ge=1)
    agent_id: Optional[int] = Field(default=None, ge=1)
    cashback_amount: Decimal = Field(..., gt=Decimal("0.00"))
    trans_date: date
    narration: Optional[str] = Field(default=None, max_length=500)


class CashbackResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    cashback_id: int
    transaction_id: int
    customer_id: Optional[int] = None
    cust_veh_id: Optional[int] = None
    agent_id: Optional[int] = None
    branch_id: Optional[int] = None
    cashback_amount: Decimal
    trans_date: date
    narration: Optional[str] = None
    status: str
    created_user: Optional[int] = None
    created_date: Optional[datetime] = None


# ==============================================================================
# F-17B-096: Sales Target vs. Achievement & Contest Reward Tracking
# ==============================================================================
class SalesTargetCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    emp_id: int = Field(..., gt=0)
    financial_year: str = Field(..., min_length=4, max_length=20, examples=["2026-2027"])
    month: str = Field(..., min_length=1, max_length=20, examples=["October"])
    target_month: Optional[date] = None
    target_amount: Decimal = Field(..., gt=Decimal("0.00"))
    achieved_target_amount: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    health_insurance_amount: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    annual_amount: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))


class SalesTargetUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_amount: Optional[Decimal] = Field(default=None, gt=Decimal("0.00"))
    achieved_target_amount: Optional[Decimal] = Field(default=None, ge=Decimal("0.00"))
    health_insurance_amount: Optional[Decimal] = Field(default=None, ge=Decimal("0.00"))
    annual_amount: Optional[Decimal] = Field(default=None, ge=Decimal("0.00"))


class SalesTargetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    target_id: int
    emp_id: int
    financial_year: str
    month: str
    target_month: Optional[date] = None
    target_amount: Decimal
    achieved_target_amount: Decimal
    health_insurance_amount: Decimal
    annual_amount: Decimal
    achievement_percent: Decimal
    contest_reward_tier: str


# ==============================================================================
# F-17B-097: Sub-Agent Secondary Hierarchy & Split Payout
# ==============================================================================
class SubAgentCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent_code: str = Field(..., min_length=2, max_length=50)
    agent_first_name: str = Field(..., min_length=1, max_length=100)
    agent_last_name: Optional[str] = Field(default=None, max_length=100)
    mobile_no: str = Field(..., min_length=10, max_length=20)
    email_id: Optional[str] = Field(default=None, max_length=100)
    pan_no: Optional[str] = Field(default=None, max_length=20)
    split_percent: Decimal = Field(..., ge=Decimal("0.00"), le=Decimal("100.00"))


class SubAgentSplitCalculateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sub_agent_id: int = Field(..., gt=0)
    total_commission_amount: Decimal = Field(..., gt=Decimal("0.00"))
    override_split_percent: Optional[Decimal] = Field(
        default=None, ge=Decimal("0.00"), le=Decimal("100.00")
    )


class SubAgentSplitCalculateResponse(BaseModel):
    parent_agent_id: int
    sub_agent_id: int
    total_commission_amount: Decimal
    sub_agent_split_percent: Decimal
    sub_agent_payout_amount: Decimal
    parent_agent_retained_amount: Decimal


# ==============================================================================
# F-17B-098: Field Executive / Agent GPS Check-In & Reverse Geocoding
# ==============================================================================
class GeoCheckInRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    customer_id: Optional[int] = Field(default=None, ge=1)
    calling_import_id: Optional[int] = Field(default=None, ge=1)
    latitude: Decimal = Field(..., ge=Decimal("-90.0"), le=Decimal("90.0"))
    longitude: Decimal = Field(..., ge=Decimal("-180.0"), le=Decimal("180.0"))
    cust_support_type_id: int = Field(default=1, ge=1)
    visit_note: Optional[str] = Field(default=None, max_length=500)


class GeoCheckInResponse(BaseModel):
    check_in_id: int
    user_id: int
    customer_id: Optional[int] = None
    latitude: str
    longitude: str
    resolved_address: str
    geocode_source: str
    visit_note: Optional[str] = None
    checked_in_at: datetime


# ==============================================================================
# F-17B-099: Petty Office Expense & Stationary Voucher Register
# ==============================================================================
class OfficeExpenseVoucherCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    voucher_no: str = Field(..., min_length=1, max_length=100)
    expense_date: date
    expense_category: str = Field(
        default="STATIONARY",
        pattern="^(STATIONARY|PETTY_CASH|COURIER|REFRESHMENT|OFFICE_MAINTENANCE|OTHER)$",
    )
    vendor_or_payee: str = Field(..., min_length=2, max_length=255)
    amount: Decimal = Field(..., gt=Decimal("0.00"))
    payment_mode: str = Field(default="CASH", pattern="^(CASH|UPI|NEFT|CHEQUE)$")
    branch_id: Optional[int] = Field(default=None, ge=1)
    narration: Optional[str] = Field(default=None, max_length=500)


class OfficeExpenseVoucherResponse(BaseModel):
    account_id: int
    voucher_no: str
    expense_date: date
    expense_category: str
    vendor_or_payee: str
    amount: Decimal
    payment_mode: str
    branch_id: Optional[int] = None
    narration: Optional[str] = None
