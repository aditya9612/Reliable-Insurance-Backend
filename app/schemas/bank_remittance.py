"""
Pydantic v2 Schemas for Phase 27:
Company Outstanding Premium Remittance & Cash-to-Bank Deposit Settlement Engine.
Physical Table: tbl_debitfrombankaccount
Strictly configured with extra="forbid" and from_attributes=True.
"""
from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


# ============================================================================
# 1. REMITTANCE ITEM & BATCH SCHEMAS
# ============================================================================

class CompanyRemittanceBatchRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid", populate_by_name=True)

    company_id: int = Field(..., ge=1, description="Underwriting Insurance Company ID (tbl_insurancecompany)")
    company_ledger_id: int = Field(..., ge=1, description="Insurance Company Chart of Accounts Ledger (tbl_ledgermaster)")
    bank_ledger_id: int = Field(..., ge=1, description="Bank Chart of Accounts Ledger (tbl_ledgermaster)")
    payment_mode: str = Field(default="Cheque", description="Payment Mode: Cheque, Online, NEFT, RTGS, Cash")
    cheque_no: Optional[str] = Field(None, max_length=50, description="Cheque or Bank Reference Number")
    payment_date: Optional[datetime] = Field(None, description="Date of remittance execution (defaults to now)")
    transaction_ids: List[int] = Field(..., min_length=1, description="List of unremitted transaction IDs to clear")
    branch_id: Optional[int] = Field(None, ge=1, description="Branch ID (defaults to user's branch)")
    narration: Optional[str] = Field(None, max_length=500, description="Remittance narration")


class CashToBankDepositRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid", populate_by_name=True)

    from_cash_ledger_id: int = Field(..., ge=1, description="Source Cash in Hand Ledger ID (tbl_ledgermaster)")
    to_bank_ledger_id: int = Field(..., ge=1, description="Destination Bank Account Ledger ID (tbl_ledgermaster)")
    deposit_amount: Decimal = Field(..., gt=0, description="Amount deposited into bank account")
    deposit_date: Optional[datetime] = Field(None, description="Deposit Date (defaults to now)")
    payment_mode: str = Field(default="Cash", max_length=50, description="Payment Mode")
    branch_id: Optional[int] = Field(None, ge=1, description="Branch ID (defaults to user's branch)")
    transaction_ids: Optional[List[int]] = Field(None, description="Optional transaction IDs settled with this deposit")
    narration: Optional[str] = Field(None, max_length=500, description="Deposit narration")


# ============================================================================
# 2. RESPONSE SCHEMAS
# ============================================================================

class DebitRemittanceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    debit_account_id: int = Field(validation_alias="DebitAccountId")
    transaction_id: Optional[int] = Field(None, validation_alias="TransactionId")
    ledger_m_id: Optional[int] = Field(None, validation_alias="LedgerMId")
    branch_id: int = Field(validation_alias="BranchId")
    doc_no: Optional[str] = Field(None, validation_alias="Doc_No")
    amount: Decimal = Field(validation_alias="Amount")
    account_date: datetime = Field(validation_alias="AccountDate")
    narration: Optional[str] = Field(None, validation_alias="Narration")
    flag: str = Field(validation_alias="Flag")
    company_cheque_no: Optional[str] = Field(None, validation_alias="CompanyChequeNo")
    created_user: Optional[str] = Field(None, validation_alias="CreatedUser")
    created_date: Optional[datetime] = Field(None, validation_alias="CreatedDate")


class CompanyRemittanceBatchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    success: bool = True
    message: str
    doc_no: str
    company_id: int
    company_ledger_id: int
    bank_ledger_id: int
    total_remitted_amount: Decimal
    transaction_count: int
    remittance_records: List[DebitRemittanceResponse]


class CashToBankDepositResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    success: bool = True
    message: str
    doc_no: str
    from_cash_ledger_id: int
    to_bank_ledger_id: int
    deposit_amount: Decimal
    remittance_record: DebitRemittanceResponse


class PendingCompanyRemittanceItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    transaction_id: int = Field(validation_alias="TransactionId")
    proposal_no: Optional[str] = Field(None, validation_alias="ProposalNo")
    policy_no: Optional[str] = Field(None, validation_alias="PolicyNo")
    customer_id: Optional[int] = Field(None, validation_alias="CustomerId")
    customer_name: Optional[str] = None
    insurance_company_id: int = Field(validation_alias="InsuranceCompanyId")
    insurance_company_name: Optional[str] = None
    gross_premium: Decimal = Field(validation_alias="GrossPremium")
    net_premium: Decimal = Field(validation_alias="NetPremium")
    proposal_amt: Decimal = Field(validation_alias="ProposalAmt")
    branch_id: int = Field(validation_alias="BranchId")
    created_date: Optional[datetime] = Field(None, validation_alias="CreatedDate")


class CashBalanceSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    branch_id: int
    branch_name: Optional[str] = None
    total_cash_collected: Decimal
    total_cash_deposited_to_bank: Decimal
    current_cash_balance: Decimal
    pending_cash_transactions_count: int


class DebitRemittanceHistoryListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    total: int
    items: List[DebitRemittanceResponse]
