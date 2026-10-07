"""
Pydantic v2 Request & Response Schemas for Phase 8 Payments, Cheques, Reconciliation & E-Wallet Engine.
All monetary, rate, penalty, variance, and wallet balance fields strictly use Decimal (never float).
"""
from datetime import date, datetime
from decimal import Decimal
from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.policy import (
    AccountingEntryResponse,
    PaymentInstrumentResponse,
)


# ---------------------------------------------------------------------------
# 1. Payment & Cheque Lifecycle Schemas
# ---------------------------------------------------------------------------


class PaymentListResponse(BaseModel):
    """Paginated list of payment instruments from tbl_transactionpayment."""
    total: int
    limit: int
    offset: int
    items: List[PaymentInstrumentResponse]


class ChequeDepositRequest(BaseModel):
    """Request payload for POST /api/v1/payments/{payment_id}/deposit."""
    model_config = ConfigDict(extra="forbid")

    deposit_date: Optional[date] = Field(default=None)
    bank_reference: Optional[str] = Field(
        default=None,
        max_length=200,
        description="Bank deposit slip or clearing batch reference",
    )
    remark: Optional[str] = Field(default=None, max_length=255)


class ChequeClearRequest(BaseModel):
    """Request payload for POST /api/v1/payments/{payment_id}/clear."""
    model_config = ConfigDict(extra="forbid")

    clear_date: Optional[date] = Field(default=None)
    bank_reference: Optional[str] = Field(
        default=None,
        max_length=200,
        description="Bank clearing reference / UTR",
    )
    remark: Optional[str] = Field(default=None, max_length=255)
    simulate_failure_at: Optional[Literal["AFTER_PAYMENT_UPDATE", "BEFORE_COMMIT"]] = Field(
        default=None,
        description="Test-only fault injection hook for atomic rollback verification",
    )


class ChequeBounceRequest(BaseModel):
    """
    Request payload for POST /api/v1/payments/{payment_id}/bounce.
    Reverses cleared/pending cheque amount, applies optional dishonor penalty,
    reopens policy OutstandingAmount, and holds commission settlement.
    """
    model_config = ConfigDict(extra="forbid")

    bounce_date: Optional[date] = Field(default=None)
    bounce_reason: str = Field(
        ...,
        min_length=3,
        max_length=200,
        description="Bank return reason (e.g. 'Insufficient Funds', 'Signature Mismatch')",
    )
    penalty_amount: Decimal = Field(
        default=Decimal("0.00"),
        ge=Decimal("0.00"),
        description="Optional cheque dishonor / bank bounce penalty charge (Decimal >= 0.00)",
    )
    bank_reference: Optional[str] = Field(
        default=None,
        max_length=150,
        description="Bank return memo reference",
    )
    simulate_failure_at: Optional[
        Literal["AFTER_PAYMENT_BOUNCE", "AFTER_TRANSACTION_REOPEN", "DURING_ACCOUNTING"]
    ] = Field(
        default=None,
        description="Test-only fault injection hook for atomic rollback verification",
    )


class PaymentReversalRequest(BaseModel):
    """
    Request payload for POST /api/v1/payments/{payment_id}/reverse.
    Reverses an active payment instrument, reopens policy OutstandingAmount,
    posts contra AccTransId=2 entry, and optionally refunds Partner E-Wallet.
    """
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(
        ...,
        min_length=3,
        max_length=255,
        description="Audit reason for payment reversal / refund",
    )
    reversal_date: Optional[date] = Field(default=None)
    refund_to_wallet: bool = Field(
        default=True,
        description="When True and payment_type is EWALLET, credits reversed amount back to partner wallet",
    )
    wallet_owner_type: Optional[Literal["AGENT", "FRANCHISE"]] = Field(default=None)
    wallet_owner_id: Optional[int] = Field(default=None, ge=1)
    simulate_failure_at: Optional[
        Literal["AFTER_PAYMENT_REVERSE", "DURING_ACCOUNTING"]
    ] = Field(
        default=None,
        description="Test-only fault injection hook for atomic rollback verification",
    )


class PaymentLifecycleActionResponse(BaseModel):
    """Response returned after a payment or cheque lifecycle transition."""
    payment_id: int
    transaction_id: int
    inward_no: str
    payment_type: str
    status: str
    paid_amount: Decimal
    policy_paid_amount: Decimal
    policy_outstanding_amount: Decimal
    policy_t_status: str
    policy_pending_status: int
    is_cheque_clearing: int
    is_cheque_cleared: int
    cheque_bank_status: int
    commission_paid: int
    penalty_applied: Decimal = Decimal("0.00")
    payment: PaymentInstrumentResponse
    accounting_entries: List[AccountingEntryResponse] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# 2. Insurer Payment & Brokerage Reconciliation Schemas
# ---------------------------------------------------------------------------


class ReconciliationMatchRequest(BaseModel):
    """
    Request payload for POST /api/v1/reconciliation/policies/{transaction_id}/match.
    Reconciles insurer remittance / brokerage statement against tbl_transaction.
    """
    model_config = ConfigDict(extra="forbid")

    reconciled_grid_percent: Optional[Decimal] = Field(
        default=None,
        ge=Decimal("0.00"),
        le=Decimal("100.00"),
        description="Insurer statement brokerage grid percentage (RconGrid)",
    )
    reconciled_comm_amount: Optional[Decimal] = Field(
        default=None,
        ge=Decimal("0.00"),
        description="Insurer statement commission amount (RconComm)",
    )
    company_submission_doc_no: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Insurer submission document reference (CompSubmitionDocNo)",
    )
    company_cheque_no: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Remittance cheque number to insurer (CompanyChequeNo)",
    )
    is_company_cheque: bool = Field(
        default=False,
        description="Whether remittance to insurer was via company cheque (IsCompanyChequeNo)",
    )
    online_payment_to_company: Optional[Decimal] = Field(
        default=None,
        ge=Decimal("0.00"),
        description="Online direct payment remitted to insurer (OnlinePaymentToCompany)",
    )
    online_to_company_date: Optional[date] = Field(default=None)
    ib_doc_no: Optional[int] = Field(
        default=None,
        ge=1,
        description="Insurer billing voucher / receipt number (IB_Doc_No)",
    )
    ib_payment_date: Optional[date] = Field(default=None)
    ib_receipt_status: int = Field(
        default=1,
        ge=0,
        le=2,
        description="0 = Pending, 1 = Full Receipt Matched, 2 = Partial/Variance",
    )
    ib_payment_by: Optional[str] = Field(
        default="INSURER_PORTAL",
        max_length=100,
    )
    accounting_period: Optional[date] = Field(default=None)
    remark: Optional[str] = Field(default=None, max_length=255)
    allow_partial_match: bool = Field(
        default=True,
        description="If False, rejects reconciliation when commission variance exceeds 1.00 rupee",
    )
    idempotency_key: Optional[str] = Field(default=None, max_length=120)
    simulate_failure_at: Optional[Literal["AFTER_TX_UPDATE", "BEFORE_COMMIT"]] = Field(
        default=None,
        description="Test-only fault injection hook for atomic rollback verification",
    )


class ReconciliationMatchResponse(BaseModel):
    """Response returned by insurer reconciliation match."""
    transaction_id: int
    inward_no: str
    policy_no: Optional[str] = None
    insurance_company_id: int
    branch_id: int
    is_rcon_data_match: int
    match_status: Literal["UNRECONCILED", "MATCHED", "PARTIAL_VARIANCE"]
    final_premium: Decimal
    net_premium: Decimal
    booked_gross_commission: Decimal
    booked_net_commission: Decimal
    reconciled_grid_percent: Decimal
    reconciled_comm_amount: Decimal
    commission_variance: Decimal
    company_submission_doc_no: Optional[str] = None
    company_cheque_no: Optional[str] = None
    is_company_cheque: int = 0
    online_payment_to_company: Decimal = Decimal("0.00")
    ib_doc_no: Optional[int] = None
    ib_payment_date: Optional[datetime] = None
    ib_receipt_status: int = 0
    ib_payment_by: Optional[str] = None
    accounting_period: Optional[datetime] = None
    accounting_entry: Optional[AccountingEntryResponse] = None


class ReconciliationListResponse(BaseModel):
    """Paginated list of policy insurer reconciliation records."""
    total: int
    limit: int
    offset: int
    items: List[ReconciliationMatchResponse]


# ---------------------------------------------------------------------------
# 3. Partner E-Wallet & Lock / Release Schemas
# ---------------------------------------------------------------------------


class WalletBalanceResponse(BaseModel):
    """Partner E-Wallet balance breakdown from tbl_ledgermaster + tbl_account."""
    ledger_m_id: int
    owner_type: Literal["AGENT", "FRANCHISE"]
    owner_id: int
    branch_id: int
    ledger_name: str
    settled_balance: Decimal
    locked_balance: Decimal
    available_balance: Decimal


class WalletTopupRequest(BaseModel):
    """Request payload for POST /api/v1/wallets/topup."""
    model_config = ConfigDict(extra="forbid")

    owner_type: Literal["AGENT", "FRANCHISE"] = Field(default="AGENT")
    owner_id: int = Field(..., ge=1, description="AgentId or FranchiseId")
    amount: Decimal = Field(..., gt=Decimal("0.00"), description="Top-up credit amount (> 0.00)")
    payment_mode: str = Field(default="NEFT", max_length=50)
    doc_no: Optional[str] = Field(default=None, max_length=100)
    narration: Optional[str] = Field(default=None, max_length=255)
    branch_id: Optional[int] = Field(default=None, ge=1)
    idempotency_key: Optional[str] = Field(default=None, max_length=120)
    simulate_failure_at: Optional[Literal["BEFORE_COMMIT"]] = Field(default=None)


class WalletLockRequest(BaseModel):
    """
    Request payload for POST /api/v1/wallets/lock.
    Reserves funds in the partner's E-Wallet for a staged proposal or policy booking.
    """
    model_config = ConfigDict(extra="forbid")

    owner_type: Literal["AGENT", "FRANCHISE"] = Field(default="AGENT")
    owner_id: int = Field(..., ge=1, description="AgentId or FranchiseId")
    amount: Decimal = Field(..., gt=Decimal("0.00"), description="Amount to reserve/lock (> 0.00)")
    proposal_trans_id: Optional[int] = Field(
        default=None,
        ge=1,
        description="Optional staged proposal TransId in tbl_transactionappnew",
    )
    quotation_code: Optional[str] = Field(default=None, max_length=100)
    narration: Optional[str] = Field(default=None, max_length=255)
    idempotency_key: Optional[str] = Field(default=None, max_length=120)
    simulate_failure_at: Optional[Literal["BEFORE_COMMIT"]] = Field(default=None)


class WalletReleaseRequest(BaseModel):
    """
    Request payload for POST /api/v1/wallets/release.
    Releases an active E-Wallet lock (by lock_account_id or proposal_trans_id) back to available balance.
    """
    model_config = ConfigDict(extra="forbid")

    lock_account_id: Optional[int] = Field(
        default=None,
        ge=1,
        description="AccountId of the active WALLET_LOCK entry in tbl_account",
    )
    proposal_trans_id: Optional[int] = Field(
        default=None,
        ge=1,
        description="Staged proposal TransId whose active lock should be released",
    )
    owner_type: Optional[Literal["AGENT", "FRANCHISE"]] = Field(default=None)
    owner_id: Optional[int] = Field(default=None, ge=1)
    reason: str = Field(default="Lock released", min_length=2, max_length=255)
    idempotency_key: Optional[str] = Field(default=None, max_length=120)
    simulate_failure_at: Optional[Literal["BEFORE_COMMIT"]] = Field(default=None)

    @model_validator(mode="after")
    def validate_target(self) -> "WalletReleaseRequest":
        if self.lock_account_id is None and self.proposal_trans_id is None:
            raise ValueError(
                "Either lock_account_id or proposal_trans_id must be provided to release a wallet lock."
            )
        return self


class WalletDebitRequest(BaseModel):
    """
    Request payload for POST /api/v1/wallets/debit.
    Executes a direct debit or consumes an active wallet lock for a policy transaction.
    """
    model_config = ConfigDict(extra="forbid")

    owner_type: Literal["AGENT", "FRANCHISE"] = Field(default="AGENT")
    owner_id: int = Field(..., ge=1, description="AgentId or FranchiseId")
    amount: Decimal = Field(..., gt=Decimal("0.00"), description="Debit amount (> 0.00)")
    transaction_id: Optional[int] = Field(default=None, ge=1)
    proposal_trans_id: Optional[int] = Field(default=None, ge=1)
    lock_account_id: Optional[int] = Field(
        default=None,
        ge=1,
        description="Optional AccountId of a held WALLET_LOCK to consume",
    )
    narration: Optional[str] = Field(default=None, max_length=255)
    idempotency_key: Optional[str] = Field(default=None, max_length=120)
    simulate_failure_at: Optional[Literal["BEFORE_COMMIT"]] = Field(default=None)


class WalletTransactionEntryResponse(BaseModel):
    """Single E-Wallet ledger movement row from tbl_account."""
    account_id: int
    acc_trans_id: int
    entry_type: str
    ledger_m_id: int
    amount: Decimal
    narration: str
    payment_type: Optional[str] = None
    extra_reference: Optional[str] = None
    doc_no: Optional[int] = None
    transaction_id: int = 0
    proposal_trans_id: int = 0
    created_date: Optional[datetime] = None


class WalletOperationResponse(BaseModel):
    """Response returned after a wallet top-up, lock, release, or debit."""
    wallet: WalletBalanceResponse
    ledger_entry: WalletTransactionEntryResponse


class WalletLedgerListResponse(BaseModel):
    """Paginated E-Wallet statement and current balance summary."""
    wallet: WalletBalanceResponse
    total: int
    limit: int
    offset: int
    items: List[WalletTransactionEntryResponse]
