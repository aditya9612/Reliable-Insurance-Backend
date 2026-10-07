"""
Pydantic v2 Schemas for Phase 14 — Reports, Dashboards, MIS, POSP Invoices & Accounting.
All schemas strictly preserve verified legacy data contracts, Decimal financial precision,
and role-based field masking rules.
"""
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field, ConfigDict


# ============================================================================
# 1. Dashboard & KPI Schemas
# ============================================================================

class MonthlyMatrixRow(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    month: str
    month_num: int
    policy_count: int
    od_premium: Decimal
    tp_premium: Decimal
    net_premium: Decimal
    gross_premium: Decimal
    agent_commission: Decimal
    brokerage: Decimal
    company_profit: Decimal


class MonthlyMatrixTotals(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total_policies: int
    total_od_premium: Decimal
    total_tp_premium: Decimal
    total_net_premium: Decimal
    total_gross_premium: Decimal
    total_agent_commission: Decimal
    total_brokerage: Decimal
    total_company_profit: Decimal


class BreakdownItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    key: str
    name: str
    policy_count: int
    net_premium: Decimal


class AdminDashboardResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    financial_year: str
    date_mode: str
    broker: Optional[str] = None
    branch_id: Optional[int] = None
    monthly_matrix: List[MonthlyMatrixRow]
    company_breakdown: List[BreakdownItem]
    broker_breakdown: List[BreakdownItem]
    sourcing_breakdown: List[BreakdownItem]
    totals: MonthlyMatrixTotals


class DailyTrendRow(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    entry_date: date
    policy_count: int
    cash_amount: Decimal
    cheque_amount: Decimal
    online_amount: Decimal
    total_amount: Decimal


class AccountsSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    from_date: date
    to_date: date
    branch_id: Optional[int] = None
    cash_total: Decimal
    cheque_total: Decimal
    online_total: Decimal
    total_collections: Decimal
    payouts_total: Decimal
    net_cash_flow: Decimal
    daily_trends: List[DailyTrendRow]


class OwnerDashboardResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    from_date: date
    to_date: date
    total_policies: int
    total_net_premium: Decimal
    total_gross_premium: Decimal
    total_profit: Decimal
    broker_splits: Dict[str, Decimal]
    source_splits: Dict[str, Decimal]


class CutAndPayRow(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    agent_id: int
    agent_name: str
    policy_count: int
    gross_premium: Decimal
    agent_commission: Decimal
    remittance_due: Decimal
    remittance_received: Decimal
    balance_due: Decimal


class CutAndPaySummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    financial_year: str
    month: Optional[str] = None
    branch_id: Optional[int] = None
    items: List[CutAndPayRow]
    total_remittance_due: Decimal
    total_remittance_received: Decimal
    total_balance_due: Decimal


class AgentOutstandingRow(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    agent_id: int
    agent_name: str
    mobile_no: Optional[str] = None
    total_outstanding: Decimal
    aging_0_7: Decimal
    aging_8_15: Decimal
    aging_16_30: Decimal
    aging_30_plus: Decimal


class AgentOutstandingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    branch_id: Optional[int] = None
    items: List[AgentOutstandingRow]
    total_outstanding: Decimal


# ============================================================================
# 2. MIS Transaction Reports & Exports Schemas
# ============================================================================

class TransactionReportRow(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    trans_id: int
    policy_no: str
    policy_date: Optional[date] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    insurance_company: Optional[str] = None
    company_id: Optional[int] = None
    broker_name: Optional[str] = None
    policy_type: Optional[str] = None

    # Vehicle details
    vehicle_no: Optional[str] = None
    make: Optional[str] = None
    model: Optional[str] = None
    variant: Optional[str] = None
    engine_no: Optional[str] = None
    chassis_no: Optional[str] = None
    mfg_year: Optional[int] = None
    rto_code: Optional[str] = None

    # Customer details
    customer_name: Optional[str] = None
    mobile_no: Optional[str] = None
    city: Optional[str] = None

    # Financial details
    od_premium: Decimal
    tp_premium: Decimal
    net_premium: Decimal
    gst_amount: Decimal
    gross_premium: Decimal
    payment_mode: Optional[str] = None
    cheque_no: Optional[str] = None
    bank_name: Optional[str] = None

    # Agent & Channel
    agent_id: Optional[int] = None
    agent_name: Optional[str] = None
    source_type: Optional[str] = None
    branch_id: Optional[int] = None
    branch_name: Optional[str] = None

    # Internal masked columns (Visible only to ADMIN, IT SUPPORT, ACCOUNT)
    company_commission_rate: Optional[Decimal] = None
    total_company_commission: Optional[Decimal] = None
    company_profit: Optional[Decimal] = None
    franchise_commission_rate: Optional[Decimal] = None
    franchise_commission_amount: Optional[Decimal] = None
    tds_percentage: Optional[Decimal] = None
    agent_commission: Optional[Decimal] = None
    internal_remarks: Optional[str] = None


class PagedTransactionReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    items: List[TransactionReportRow]
    total: int
    page: int
    page_size: int
    total_net_premium: Decimal
    total_gross_premium: Decimal


class MISReconcileRequest(BaseModel):
    batch_id: int
    tolerance: Decimal = Decimal("1.00")


class MISReconcileResponse(BaseModel):
    batch_id: int
    total_imported: int
    matched_count: int
    discrepancy_count: int
    discrepancies: List[Dict[str, Any]]


# ============================================================================
# 3. POSP & Agent Payout Invoicing Schemas
# ============================================================================

class PospInvoiceCreateRequest(BaseModel):
    agent_id: int
    posp_type: Literal["DIRECT", "POSP"] = "POSP"
    financial_year: str = Field(..., pattern=r"^\d{4}-\d{4}$")
    month: str = Field(..., max_length=20)
    amount: Decimal = Field(..., gt=0)
    custom_invoice_no: Optional[str] = None
    invoice_date: Optional[date] = None
    is_gst_registered: bool = False


class PospInvoiceDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    invoice_id: int
    invoice_no: str
    invoice_date: date
    agent_id: int
    agent_name: str
    posp_type: str
    financial_year: str
    month: str
    amount: Decimal
    gst_amt: Decimal
    grand_total: Decimal
    tds_amount: Decimal
    net_payable: Decimal
    pdf_path: Optional[str] = None
    status: str
    created_date: datetime
    created_by: str
    amount_in_words: str


class PagedPospInvoiceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    items: List[PospInvoiceDetailResponse]
    total: int
    page: int
    page_size: int


class AgentPayoutReconciliationItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    agent_id: int
    agent_name: str
    gst_no: Optional[str] = None
    earned_commission: Decimal
    invoiced_amount: Decimal
    disbursed_amount: Decimal
    pending_payable: Decimal


class PagedAgentPayoutReconciliationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    items: List[AgentPayoutReconciliationItem]
    total: int


# ============================================================================
# 4. Accounting & Statutory Reports Schemas
# ============================================================================

class TdsRegisterItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    trans_id: int
    voucher_no: Optional[str] = None
    voucher_date: date
    agent_id: int
    agent_name: str
    pan_no: Optional[str] = None
    gross_commission: Decimal
    tds_rate: Decimal
    tds_amount: Decimal
    net_commission: Decimal
    ledger_m_id: int


class TdsRegisterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    items: List[TdsRegisterItem]
    total_gross_commission: Decimal
    total_tds_deducted: Decimal
    total_net_commission: Decimal


class LedgerTypeSummaryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ledger_type_id: int
    ledger_type_name: str
    total_debit: Decimal
    total_credit: Decimal
    net_balance: Decimal


class LedgerMasterSummaryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ledger_m_id: int
    ledger_name: str
    ledger_type_id: int
    opening_balance: Decimal
    debit_sum: Decimal
    credit_sum: Decimal
    closing_balance: Decimal


class LedgerStatementItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    account_id: int
    voucher_no: str
    voucher_date: date
    particulars: str
    debit_amount: Decimal
    credit_amount: Decimal
    running_balance: Decimal


class LedgerStatementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ledger_m_id: int
    ledger_name: str
    from_date: date
    to_date: date
    opening_balance: Decimal
    closing_balance: Decimal
    transactions: List[LedgerStatementItem]


class VoucherDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    voucher_id: int
    voucher_no: str
    voucher_date: date
    voucher_type: str
    payee_name: str
    payment_mode: str
    amount: Decimal
    amount_in_words: str
    narration: Optional[str] = None
    created_by: str


class PaymentAdviceItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    policy_no: str
    vehicle_no: str
    customer_name: str
    net_premium: Decimal
    commission_rate: Decimal
    commission_amount: Decimal
    tds_amount: Decimal
    net_payable: Decimal


class PaymentAdviceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    agent_id: int
    agent_name: str
    financial_year: str
    month: str
    total_policies: int
    total_gross_commission: Decimal
    total_tds: Decimal
    total_net_payable: Decimal
    items: List[PaymentAdviceItem]


class BankCommissionStatementItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    sr_no: int
    agent_id: int
    agent_name: str
    bank_name: str
    account_no: str
    ifsc_code: str
    net_disbursement_amount: Decimal
    narration: str


class BankCommissionStatementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    financial_year: str
    month: str
    total_records: int
    total_disbursement: Decimal
    items: List[BankCommissionStatementItem]


class DailyCollectionAuditResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    report_date: date
    branch_id: Optional[int] = None
    cash_total: Decimal
    cheque_total: Decimal
    online_total: Decimal
    grand_total: Decimal
    policy_count: int
    items: List[Dict[str, Any]]


# ============================================================================
# 5. Operations, Targets & Renewal CRM Reports Schemas
# ============================================================================

class CommissionReconcileItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    trans_id: int
    policy_no: str
    company_name: str
    net_premium: Decimal
    expected_brokerage: Decimal
    received_brokerage: Decimal
    difference: Decimal
    status: str


class CommissionReconcileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    from_date: date
    to_date: date
    company_id: Optional[int] = None
    items: List[CommissionReconcileItem]
    total_difference: Decimal


class BankReconcileItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    trans_id: int
    cheque_no: str
    cheque_date: date
    bank_name: str
    amount: Decimal
    status: str
    days_uncleared: int


class BankReconcileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    from_date: date
    to_date: date
    bank_id: Optional[int] = None
    items: List[BankReconcileItem]
    total_uncleared_amount: Decimal


class EndorsementReportItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    endorsement_id: int
    endorsement_no: str
    policy_no: str
    endorsement_type_id: int
    endorsement_type: str
    financial_delta: Decimal
    commission_delta: Decimal
    status: str
    created_date: datetime


class PagedEndorsementReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    items: List[EndorsementReportItem]
    total: int


class ClaimsReportItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    claim_id: int
    claim_no: str
    policy_no: str
    customer_name: str
    claim_amount: Decimal
    settlement_amount: Decimal
    claim_status: str
    settlement_status: Optional[str] = None
    intimation_date: datetime


class PagedClaimsReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    items: List[ClaimsReportItem]
    total: int


class TelecallerTargetItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    emp_id: int
    emp_name: str
    financial_year: str
    month: str
    target_amount: Decimal
    achieved_amount: Decimal
    achievement_percentage: Decimal
    policy_count: int


class TelecallerTargetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    financial_year: str
    month: str
    items: List[TelecallerTargetItem]


class ExecutiveTargetItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    emp_id: int
    emp_name: str
    financial_year: str
    month: str
    target_amount: Decimal
    achieved_amount: Decimal
    achievement_percentage: Decimal
    policy_count: int


class ExecutiveTargetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    financial_year: str
    month: str
    items: List[ExecutiveTargetItem]


class ExpiringPoliciesResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    as_of_date: date
    window_days: int
    branch_id: Optional[int] = None
    total_count: int
    items: List[Dict[str, Any]]
