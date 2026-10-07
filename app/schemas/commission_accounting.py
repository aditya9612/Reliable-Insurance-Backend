"""
Pydantic v2 Schemas for Phase 9 — Commission & Accounting Engine.

Covers:
1. Commission Preview & Policy Commission Evaluation (Agent, Franchise, OD/Net/Extra, TDS, Cut & Pay)
2. Commission Payable Queue & Approval Gates
3. Commission Payout Execution & Payout Reversal
4. Chart of Accounts / Master Ledgers (tbl_ledgermaster) & Running-Balance Ledger Statements (tbl_account)
5. Double-Entry Vouchers (tbl_account grouped by Doc_No + Extra2) & Voucher Reversal
6. Trial Balance Aggregation & Balancing Invariants
"""
from datetime import date, datetime
from decimal import Decimal
from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


# ---------------------------------------------------------------------------
# 1. Commission Preview, Evaluation & Policy Commission Schemas
# ---------------------------------------------------------------------------


class CommissionPreviewRequest(BaseModel):
    """
    Stateless commission & TDS calculation request (`POST /api/v1/commissions/preview`).
    All monetary fields are strictly `Decimal` (2-decimal half-up rounding).
    """
    model_config = ConfigDict(extra="forbid")

    od_premium: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    tp_premium: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    net_premium: Optional[Decimal] = Field(default=None, ge=Decimal("0.00"))
    final_premium: Optional[Decimal] = Field(default=None, ge=Decimal("0.00"))

    # Agent commission parameters
    agent_id: Optional[int] = Field(default=None, ge=0)
    agent_comm_od_pct: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"), le=Decimal("100.00"))
    agent_comm_net_pct: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"), le=Decimal("100.00"))
    agent_comm_extra_pct: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"), le=Decimal("100.00"))
    agent_comm_flat_amt: Optional[Decimal] = Field(default=None, ge=Decimal("0.00"))
    agent_tds_pct: Decimal = Field(default=Decimal("5.00"), ge=Decimal("0.00"), le=Decimal("100.00"))

    # Franchise commission parameters
    franchise_id: Optional[int] = Field(default=None, ge=0)
    franchise_comm_od_pct: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"), le=Decimal("100.00"))
    franchise_comm_net_pct: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"), le=Decimal("100.00"))
    franchise_comm_extra_pct: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"), le=Decimal("100.00"))
    franchise_tds_pct: Decimal = Field(default=Decimal("5.00"), ge=Decimal("0.00"), le=Decimal("100.00"))
    broker_id: int = Field(default=0, ge=0)
    self_discount: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))
    intensive_amount: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"))

    # Cut & Pay deduction parameters
    cutnpay_enabled: bool = Field(default=False)
    cutnpay_amount: Optional[Decimal] = Field(default=None, ge=Decimal("0.00"))


class CommissionPreviewResponse(BaseModel):
    """
    Deterministic output of stateless commission, TDS, Cut & Pay, and Franchise spread calculation.
    """
    od_premium: Decimal
    tp_premium: Decimal
    net_premium: Decimal
    final_premium: Decimal

    # Agent commission breakdown
    agent_id: Optional[int] = None
    agent_comm_od_pct: Decimal
    agent_comm_od_amt: Decimal
    agent_tds_od_amt: Decimal
    agent_net_od_amt: Decimal

    agent_comm_net_pct: Decimal
    agent_comm_net_amt: Decimal
    agent_tds_net_amt: Decimal
    agent_net_net_amt: Decimal

    agent_comm_extra_pct: Decimal
    agent_comm_extra_amt: Decimal
    agent_tds_extra_amt: Decimal
    agent_net_extra_amt: Decimal

    agent_tds_pct: Decimal
    agent_gross_commission: Decimal
    agent_tds_amount: Decimal
    agent_net_commission: Decimal

    # Cut & Pay & Remaining Agent Payable
    cutnpay_enabled: bool
    cutnpay_deducted_amount: Decimal
    customer_required_payable_amount: Decimal
    agent_initial_paid_adv_amt: Decimal
    agent_remaining_payable_amount: Decimal
    agent_initial_payment_status: Decimal
    unclear_commission_account_amount: Decimal

    # Franchise commission breakdown
    franchise_id: Optional[int] = None
    franchise_comm_od_pct: Decimal
    franchise_comm_od_amt: Decimal
    franchise_tds_od_amt: Decimal
    franchise_net_od_amt: Decimal

    franchise_comm_net_pct: Decimal
    franchise_comm_net_amt: Decimal
    franchise_tds_net_amt: Decimal
    franchise_net_net_amt: Decimal

    franchise_comm_extra_pct: Decimal
    franchise_comm_extra_amt: Decimal
    franchise_tds_extra_amt: Decimal
    franchise_net_extra_amt: Decimal

    franchise_tds_pct: Decimal
    franchise_gross_commission: Decimal
    franchise_tds_amount: Decimal
    franchise_net_commission: Decimal
    profit_of_net_commission: Decimal
    franchise_remaining_payable_amount: Decimal


class CommissionCalculateRequest(BaseModel):
    """
    Evaluates or synchronizes commission rows (`tbl_agentcommissionpayment`, `tbl_franchisecommission`,
    `tbl_cutnpaycommpayable`) for an existing booked policy (`POST /api/v1/commissions/calculate`).
    If `recalculate=True`, authorized admins can update commission rates prior to payout.
    """
    model_config = ConfigDict(extra="forbid")

    transaction_id: int = Field(..., gt=0)
    recalculate: bool = Field(default=False)

    # Optional overrides when recalculate=True (only allowed when no payout has been disbursed)
    agent_comm_od_pct: Optional[Decimal] = Field(default=None, ge=Decimal("0.00"), le=Decimal("100.00"))
    agent_comm_net_pct: Optional[Decimal] = Field(default=None, ge=Decimal("0.00"), le=Decimal("100.00"))
    agent_comm_extra_pct: Optional[Decimal] = Field(default=None, ge=Decimal("0.00"), le=Decimal("100.00"))
    agent_tds_pct: Optional[Decimal] = Field(default=None, ge=Decimal("0.00"), le=Decimal("100.00"))

    franchise_comm_od_pct: Optional[Decimal] = Field(default=None, ge=Decimal("0.00"), le=Decimal("100.00"))
    franchise_comm_net_pct: Optional[Decimal] = Field(default=None, ge=Decimal("0.00"), le=Decimal("100.00"))
    franchise_comm_extra_pct: Optional[Decimal] = Field(default=None, ge=Decimal("0.00"), le=Decimal("100.00"))
    franchise_tds_pct: Optional[Decimal] = Field(default=None, ge=Decimal("0.00"), le=Decimal("100.00"))

    simulate_failure_at: Optional[str] = Field(default=None)


class CommissionApprovalRequest(BaseModel):
    """
    Approves a policy's commission payable for disbursement (`POST /api/v1/commissions/{transaction_id}/approve`).
    """
    model_config = ConfigDict(extra="forbid")

    partner_type: Literal["AGENT", "FRANCHISE", "BOTH"] = Field(default="BOTH")
    remark: Optional[str] = Field(default=None, max_length=255)


class AgentCommissionRowResponse(BaseModel):
    agent_comm_id: int
    transaction_id: int
    agent_id: Optional[int] = None
    agent_name: Optional[str] = None
    branch_name: Optional[str] = None
    premium_amount: Decimal
    gross_commission: Decimal
    tds_amount: Decimal
    net_commission: Decimal
    net_commission_od: Decimal
    net_commission_net: Decimal
    net_commission_extra: Decimal
    adv_amt_paid: Decimal
    remaining_net_amount: Decimal
    payment_status: Decimal
    payment_status_label: str
    narration: Optional[str] = None
    isdeleted: str
    trans_date: Optional[datetime] = None


class FranchiseCommissionRowResponse(BaseModel):
    franchise_comm_id: int
    transaction_id: int
    franchise_id: Optional[int] = None
    agent_id: Optional[int] = None
    franchise_comm_pct: Decimal
    gross_commission: Decimal
    tds_amount: Decimal
    net_commission: Decimal
    paid_amount: Decimal
    remaining_payable_amount: Decimal
    profit_of_net_commission: Decimal
    franchise_comm_od_pct: Decimal
    franchise_comm_amt_od: Decimal
    franchise_tds_amt_od: Decimal
    franchise_net_comm_od: Decimal
    franchise_comm_net_pct: Decimal
    franchise_comm_amt_net: Decimal
    franchise_tds_amt_net: Decimal
    franchise_net_comm_net: Decimal
    franchise_comm_extra_pct: Decimal
    franchise_comm_amt_extra: Decimal
    franchise_tds_amt_extra: Decimal
    franchise_net_comm_extra: Decimal
    broker_id: int
    self_discount: Decimal
    intensive_amount: Decimal
    isdeleted: int
    franchise_date: Optional[datetime] = None


class CutNPayRowResponse(BaseModel):
    cutnpay_comm_pay_id: int
    transaction_id: int
    policy_no: Optional[str] = None
    customer_id: Optional[int] = None
    agent_id: Optional[int] = None
    sales_ex_id: Optional[int] = None
    balance: Decimal
    comm_payable: Decimal
    flag: str
    isdeleted: int
    created_date: Optional[datetime] = None


class PolicyCommissionRecordResponse(BaseModel):
    """
    Comprehensive commission state for a single policy transaction (`tbl_transaction` +
    `tbl_agentcommissionpayment` + `tbl_franchisecommission` + `tbl_cutnpaycommpayable`).
    """
    transaction_id: int
    inward_no: str
    policy_no: Optional[str] = None
    branch_id: int
    customer_id: int
    agent_id: Optional[int] = None
    franchise_id: Optional[int] = None
    sales_ex_id: Optional[int] = None

    # Policy settlement & eligibility status
    t_status: str
    pending_status: int
    paid_amount: Decimal
    outstanding_amount: Decimal
    is_cheque_clearing: int
    is_cheque_cleared: int
    cheque_bank_status: int
    commission_paid_flag: int
    is_payout_eligible: bool
    eligibility_reason: str

    # Policy-level commission summary
    od_premium: Decimal
    tp_premium: Decimal
    net_premium: Decimal
    final_premium: Decimal
    agent_gross_commission: Decimal
    agent_tds_amount: Decimal
    agent_net_commission: Decimal
    cutnpay_deducted_amount: Decimal
    agent_paid_amount: Decimal
    agent_remaining_payable: Decimal

    franchise_gross_commission: Decimal
    franchise_tds_amount: Decimal
    franchise_net_commission: Decimal
    franchise_paid_amount: Decimal
    franchise_remaining_payable: Decimal
    profit_of_net_commission: Decimal

    agent_commission_row: Optional[AgentCommissionRowResponse] = None
    franchise_commission_row: Optional[FranchiseCommissionRowResponse] = None
    cutnpay_row: Optional[CutNPayRowResponse] = None


class PolicyCommissionListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: List[PolicyCommissionRecordResponse]


class CommissionPayableItemResponse(BaseModel):
    """
    A single payable item in `GET /api/v1/commissions/payables`.
    """
    partner_type: Literal["AGENT", "FRANCHISE"]
    partner_id: int
    transaction_id: int
    inward_no: str
    policy_no: Optional[str] = None
    branch_id: int
    commission_row_id: int
    gross_commission: Decimal
    tds_amount: Decimal
    net_commission: Decimal
    already_settled_amount: Decimal
    remaining_payable_amount: Decimal
    payment_status: Decimal
    payment_status_label: str
    is_payout_eligible: bool
    eligibility_reason: str
    trans_date: Optional[datetime] = None


class CommissionPayableListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    total_payable_amount: Decimal
    eligible_payable_amount: Decimal
    items: List[CommissionPayableItemResponse]


# ---------------------------------------------------------------------------
# 2. Commission Payout & Payout Reversal Schemas
# ---------------------------------------------------------------------------


class CommissionPayoutAllocationInput(BaseModel):
    """
    Explicit per-policy allocation in a commission payout request.
    If `amount` is omitted, the full remaining payable on that policy is disbursed.
    """
    model_config = ConfigDict(extra="forbid")

    transaction_id: int = Field(..., gt=0)
    amount: Optional[Decimal] = Field(default=None, gt=Decimal("0.00"))


class CommissionPayoutCreateRequest(BaseModel):
    """
    Creates an atomic Commission Payout (`POST /api/v1/commission-payouts`).
    Supports:
    - Explicit per-policy `allocations` OR
    - Pool-based FIFO allocation via `transaction_ids` + `payout_amount` (or all eligible payables for `partner_id`).
    """
    model_config = ConfigDict(extra="forbid")

    partner_type: Literal["AGENT", "FRANCHISE"]
    partner_id: int = Field(..., gt=0)
    branch_id: Optional[int] = Field(default=None, gt=0)
    payment_mode: Literal["NEFT", "RTGS", "IMPS", "UPI", "CHEQUE", "BANK_TRANSFER", "EWALLET", "CASH"] = Field(
        default="NEFT"
    )
    payout_amount: Optional[Decimal] = Field(default=None, gt=Decimal("0.00"))
    transaction_ids: Optional[List[int]] = Field(default=None)
    allocations: Optional[List[CommissionPayoutAllocationInput]] = Field(default=None)
    bank_reference: Optional[str] = Field(default=None, max_length=120)
    narration: Optional[str] = Field(default=None, max_length=255)
    idempotency_key: Optional[str] = Field(default=None, min_length=1, max_length=120)
    simulate_failure_at: Optional[str] = Field(default=None)


class CommissionPayoutReverseRequest(BaseModel):
    """
    Reverses an existing Commission Payout (`POST /api/v1/commission-payouts/{payout_id}/reverse`).
    Restores policy commission balances and posts contra double-entry reversal lines (`AccTransId = 7`).
    """
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(..., min_length=3, max_length=255)
    simulate_failure_at: Optional[str] = Field(default=None)


class CommissionPayoutAllocationResponse(BaseModel):
    transaction_id: int
    inward_no: str
    policy_no: Optional[str] = None
    commission_row_id: int
    allocated_amount: Decimal
    previous_paid_amount: Decimal
    new_paid_amount: Decimal
    remaining_payable_amount: Decimal
    payment_status: Decimal
    commission_paid_flag: int


class CommissionPayoutResponse(BaseModel):
    payout_id: int
    voucher_no: str
    partner_type: Literal["AGENT", "FRANCHISE"]
    partner_id: int
    branch_id: int
    payment_mode: str
    total_payout_amount: Decimal
    status: Literal["PAID", "REVERSED"]
    bank_reference: Optional[str] = None
    narration: str
    idempotency_key: Optional[str] = None
    debit_account_id: int
    credit_account_id: int
    debit_ledger_m_id: int
    credit_ledger_m_id: int
    reversal_doc_no: Optional[int] = None
    reversal_reason: Optional[str] = None
    created_user: Optional[str] = None
    created_date: Optional[datetime] = None
    allocations: List[CommissionPayoutAllocationResponse]


class CommissionPayoutListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: List[CommissionPayoutResponse]


# ---------------------------------------------------------------------------
# 3. Accounting Ledgers, Statements, Vouchers & Trial Balance Schemas
# ---------------------------------------------------------------------------


class LedgerMasterCreateRequest(BaseModel):
    """
    Creates a Chart of Accounts / Master Ledger entry in `tbl_ledgermaster`
    (`POST /api/v1/accounting/ledgers`).
    """
    model_config = ConfigDict(extra="forbid")

    ledger_name: str = Field(..., min_length=2, max_length=255)
    ledger_type_id: int = Field(default=1, ge=1, le=5)
    ledger_group_id: int = Field(default=10, ge=1)
    reference_id: int = Field(default=0, ge=0)
    branch_id: Optional[int] = Field(default=None, gt=0)

    @field_validator("ledger_name")
    @classmethod
    def _strip_name(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("ledger_name cannot be blank.")
        return cleaned


class LedgerMasterResponse(BaseModel):
    ledger_m_id: int
    ledger_name: str
    ledger_type_id: int
    ledger_type_label: str
    ledger_group_id: int
    reference_id: int
    branch_id: int
    isdeleted: str
    total_debit: Decimal = Decimal("0.00")
    total_credit: Decimal = Decimal("0.00")
    closing_balance: Decimal = Decimal("0.00")
    closing_polarity: Literal["DR", "CR", "ZERO"] = "ZERO"
    create_date: Optional[datetime] = None


class LedgerMasterListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: List[LedgerMasterResponse]


class LedgerStatementEntryResponse(BaseModel):
    account_id: int
    acc_trans_id: int
    account_date: Optional[datetime] = None
    doc_no: Optional[int] = None
    voucher_no: Optional[str] = None
    entry_type: str
    narration: str
    payment_type: Optional[str] = None
    transaction_id: int
    reference_cust_id: Optional[int] = None
    reference_agent_id: Optional[int] = None
    branch_id: int
    signed_amount: Decimal
    debit_amount: Decimal
    credit_amount: Decimal
    running_balance: Decimal
    running_polarity: Literal["DR", "CR", "ZERO"]


class LedgerStatementResponse(BaseModel):
    ledger: LedgerMasterResponse
    opening_balance: Decimal
    total_debit: Decimal
    total_credit: Decimal
    closing_balance: Decimal
    closing_polarity: Literal["DR", "CR", "ZERO"]
    total_entries: int
    items: List[LedgerStatementEntryResponse]


class VoucherLineInput(BaseModel):
    """
    A single debit (`DR`) or credit (`CR`) leg in a Double-Entry Voucher (`POST /api/v1/accounting/vouchers`).
    """
    model_config = ConfigDict(extra="forbid")

    ledger_m_id: int = Field(..., gt=0)
    dr_cr: Literal["DR", "CR"]
    amount: Decimal = Field(..., gt=Decimal("0.00"))
    narration: Optional[str] = Field(default=None, max_length=500)
    reference_cust_id: Optional[int] = Field(default=None, ge=0)
    reference_agent_id: Optional[int] = Field(default=None, ge=0)
    transaction_id: int = Field(default=0, ge=0)


class VoucherCreateRequest(BaseModel):
    """
    Creates a balanced Double-Entry Accounting Voucher in `tbl_account`
    (`POST /api/v1/accounting/vouchers`).
    """
    model_config = ConfigDict(extra="forbid")

    voucher_type: Literal["JOURNAL", "PAYMENT", "RECEIPT", "CONTRA"] = Field(default="JOURNAL")
    voucher_date: Optional[date] = Field(default=None)
    branch_id: Optional[int] = Field(default=None, gt=0)
    payment_mode: str = Field(default="JOURNAL", max_length=50)
    narration: str = Field(..., min_length=2, max_length=500)
    idempotency_key: Optional[str] = Field(default=None, min_length=1, max_length=120)
    lines: List[VoucherLineInput] = Field(..., min_length=2)
    simulate_failure_at: Optional[str] = Field(default=None)


class VoucherReverseRequest(BaseModel):
    """
    Reverses an existing Double-Entry Voucher (`POST /api/v1/accounting/vouchers/{doc_no}/reverse`).
    """
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(..., min_length=3, max_length=255)
    simulate_failure_at: Optional[str] = Field(default=None)


class VoucherLineResponse(BaseModel):
    account_id: int
    acc_trans_id: int
    ledger_m_id: int
    ledger_name: Optional[str] = None
    dr_cr: Literal["DR", "CR"]
    amount: Decimal
    signed_amount: Decimal
    narration: str
    reference_cust_id: Optional[int] = None
    reference_agent_id: Optional[int] = None
    transaction_id: int


class VoucherResponse(BaseModel):
    doc_no: int
    voucher_no: str
    voucher_type: str
    voucher_date: datetime
    branch_id: int
    payment_mode: str
    narration: str
    total_debit: Decimal
    total_credit: Decimal
    is_balanced: bool
    status: Literal["POSTED", "REVERSED"]
    reversal_doc_no: Optional[int] = None
    created_user: Optional[str] = None
    created_date: Optional[datetime] = None
    lines: List[VoucherLineResponse]


class VoucherListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: List[VoucherResponse]


class TrialBalanceLedgerRowResponse(BaseModel):
    ledger_m_id: int
    ledger_name: str
    ledger_type_id: int
    ledger_type_label: str
    ledger_group_id: int
    branch_id: int
    gross_debit: Decimal
    gross_credit: Decimal
    net_debit: Decimal
    net_credit: Decimal
    closing_balance: Decimal
    closing_polarity: Literal["DR", "CR", "ZERO"]


class TrialBalanceResponse(BaseModel):
    branch_id: Optional[int] = None
    from_date: Optional[date] = None
    to_date: Optional[date] = None
    total_gross_debit: Decimal
    total_gross_credit: Decimal
    total_net_debit: Decimal
    total_net_credit: Decimal
    variance: Decimal
    is_balanced: bool
    ledger_count: int
    items: List[TrialBalanceLedgerRowResponse]
