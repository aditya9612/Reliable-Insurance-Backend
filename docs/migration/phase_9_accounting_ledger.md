# Phase 9 — Accounting Ledger, Chart of Accounts & Debit/Credit Polarity Specification

**Repository**: `Reliable-Insurance-Backend`  
**Phase**: `Phase 9 — Commission & Accounting Engine (Stage A8)`  
**Target Runtime Database**: `localhost:3306/reliable_insurance_dev`

---

## 1. Chart of Accounts (`tbl_ledgermaster` — 11 Columns)

In `app/models/ledger.py` (`LedgerMaster`), all general and sub-ledger accounts are defined in `tbl_ledgermaster` (`PK: LedgerMId`):

| `LedgerTypeId` | `LedgerGroupId` | Canonical Ledger Category | `ReferenceId` Semantics | Default `LedgerName` Pattern |
|---:|---:|---|---|---|
| `1` | `1` | Policy Underwriting / Receivable Control Ledger | `0` (Branch-level) | `"POLICY UNDERWRITING LEDGER - BRANCH #{BranchId}"` |
| `2` | `1` | Cash / Bank Settlement Control Ledger | `0` (Branch-level) | `"BANK & CASH SETTLEMENT LEDGER - BRANCH #{BranchId}"` |
| `3` | `2` | Commission & TDS Payable Control Ledger | `0` (Branch-level) | `"COMMISSION & TDS PAYABLE LEDGER - BRANCH #{BranchId}"` |
| `4` | `1` | Customer Sub-Ledger | `CustomerId` | `"CUSTOMER LEDGER - #{CustomerId}"` |
| `5` | `2` | Agent E-Wallet / Commission Sub-Ledger | `AgentId` | `"EWALLET - AGENT #{AgentId}"` |
| `6` | `2` | Franchise E-Wallet / Commission Sub-Ledger | `FranchiseId` | `"EWALLET - FRANCHISE #{FranchiseId}"` |
| `7` | `1` | Insurance Company / Brokerage Control Ledger | `InsuranceCompanyId` | `"INSURER BROKERAGE LEDGER - COMPANY #{InsuranceCompanyId}"` |

### Get-or-Create Idempotency Rule
`CommissionAccountingRepository.resolve_or_create_ledger` queries `tbl_ledgermaster` by `(LedgerTypeId, ReferenceId, BranchId, isdeleted='0')` (with `FOR UPDATE` inside write transactions) so duplicate ledgers are never created under concurrent requests.

---

## 2. Explicit Accounting & Polarity Matrix (`tbl_account` — 24 Columns)

In `tbl_account`, `amount` (`Double(asdecimal=True)`) stores a **signed `Decimal(0.01)`**:
- **Positive (`amount > 0.00`)**: **Debit (`DR`)** in standard ledger statements and trial balance (or Credit to Partner E-Wallet sub-ledger for `AccTransId in {10, 12, 14}`).
- **Negative (`amount < 0.00`)**: **Credit (`CR`)** in standard ledger statements and trial balance (`abs(amount)`).

| `AccTransId` | `Extra1` Subtype Tag | Business Event | Signed `amount` in `tbl_account` | Debit (`DR`) Account | Credit (`CR`) Account | Reference Columns |
|---:|---|---|---|---|---|---|
| `1` | `POLICY_BOOKING` | Policy Underwriting Booked | `+FinalPremium` | Policy Receivable (`LedgerTypeId=1`) | Insurer Premium Control (`LedgerTypeId=7`) | `TransactionId`, `Extra2=InwardNo` |
| `2` | `POLICY_PAYMENT` | Customer Payment Instrument Received | `+PaidAmount` | Bank/Cash Settlement (`LedgerTypeId=2`) | Policy Receivable (`LedgerTypeId=1`) | `TransactionId`, `Doc_No=PaymentId` |
| `2` | `CHEQUE_BOUNCE_REVERSAL` / `PAYMENT_REVERSAL` | Cheque Bounce or Payment Reversal | `-ReversedAmount` | Policy Receivable (`LedgerTypeId=1`) | Bank/Cash Settlement (`LedgerTypeId=2`) | `TransactionId`, `Doc_No=PaymentId` |
| `3` | `UNCLEAR_COMMISSION` | Agent Net Commission Accrued at Booking | **`-NetCommission`** *(always $\le 0$)* | Commission Expense (`LedgerTypeId=3`) | Partner Commission Payable (`LedgerTypeId=1/3`) | `TransactionId`, `ReferenceAgentId` |
| `4` | `CHEQUE_BOUNCE_PENALTY` | Cheque Dishonor Penalty Assessed | `+PenaltyAmount` | Policy Receivable (`LedgerTypeId=1`) | Penalty Income Control (`LedgerTypeId=2`) | `TransactionId`, `Doc_No=PaymentId` |
| `5` | `INSURER_RECONCILIATION` | Insurer Brokerage Statement Reconciled | `+RconComm` | Insurer Brokerage (`LedgerTypeId=7`) | Commission Revenue Control (`LedgerTypeId=3`) | `TransactionId`, `Doc_No=ib_doc_no` |
| `6` | `COMMISSION_PAYOUT_DEBIT` | Commission Payout (Payable Settlement Leg) | `+PayoutAmount` | Partner Commission Payable (`LedgerTypeId=3`) | — | `TransactionId`, `Doc_No=VoucherNo`, `Extra2=VCH-...` |
| `6` | `COMMISSION_PAYOUT_CREDIT` | Commission Payout (Bank/Cash/Wallet Outflow Leg) | `-PayoutAmount` | — | Bank/Cash/Partner Ledger (`LedgerTypeId=2/5/6`) | `TransactionId`, `Doc_No=VoucherNo`, `Extra2=VCH-...` |
| `7` | `COMMISSION_PAYOUT_REVERSAL_DEBIT` | Commission Payout Reversal (Bank/Cash Restoration Leg) | `+ReversedAmount` | Bank/Cash/Partner Ledger (`LedgerTypeId=2/5/6`) | — | `TransactionId`, `Doc_No=RevVoucherNo` |
| `7` | `COMMISSION_PAYOUT_REVERSAL_CREDIT` | Commission Payout Reversal (Payable Liability Restoration Leg) | `-ReversedAmount` | — | Partner Commission Payable (`LedgerTypeId=3`) | `TransactionId`, `Doc_No=RevVoucherNo` |
| `7` | `COMMISSION_ACCRUAL_REVERSAL` | Accrued Commission Reversal (Offsets `AccTransId=3`) | `+NetCommission` | Partner Commission Payable (`LedgerTypeId=1/3`) | Commission Expense (`LedgerTypeId=3`) | `TransactionId`, `ReferenceAgentId` |
| `8` | `VOUCHER_DEBIT` | Double-Entry Accounting Voucher (Debit Line) | `+LineAmount` | Target `LedgerMId` | — | `Doc_No=VoucherNo`, `Extra2=VCH-...` |
| `9` | `VOUCHER_CREDIT` | Double-Entry Accounting Voucher (Credit Line) | `-LineAmount` | — | Target `LedgerMId` | `Doc_No=VoucherNo`, `Extra2=VCH-...` |
| `10` | `WALLET_TOPUP` | Partner E-Wallet Top-Up Credit | `+TopupAmount` | Partner E-Wallet (`LedgerTypeId=5/6`) | Bank/Cash Control (`LedgerTypeId=2`) | `LedgerMId`, `Doc_No=OwnerId` |
| `11` | `WALLET_LOCK` | Partner E-Wallet Reservation Hold | `-LockAmount` | — | Partner E-Wallet Hold (`LedgerTypeId=5/6`) | `LedgerMId`, `TransId=ProposalId` |
| `12` | `WALLET_RELEASE` | Partner E-Wallet Reservation Release | `+LockAmount` | Partner E-Wallet Hold (`LedgerTypeId=5/6`) | — | `LedgerMId`, `Doc_No=LockAccountId` |
| `13` | `WALLET_DEBIT` | Partner E-Wallet Policy Debit | `-DebitAmount` | — | Partner E-Wallet (`LedgerTypeId=5/6`) | `LedgerMId`, `TransactionId` |
| `14` | `WALLET_REFUND` | Partner E-Wallet Reversal Refund | `+RefundAmount` | Partner E-Wallet (`LedgerTypeId=5/6`) | — | `LedgerMId`, `TransactionId` |

---

## 3. Chronological Ledger Statement (`GET /api/v1/accounting/ledgers/{ledger_m_id}/statement`)

For a given `ledger_m_id`, optional `from_date`, and optional `to_date`:
1. **Opening Balance (`opening_balance`)**:
   - Sum of `round_2dp(amount)` for all active (`isdeleted == 0`) rows on `ledger_m_id` with `AccountDate < from_date` (excluding released/consumed lock markers `AccTransId == 11 and Extra1 != "WALLET_LOCK"` and audit release rows `AccTransId == 12` when computing wallet sub-ledgers so lock-release pairs never inflate balances).
2. **Chronological Statement Rows**:
   - Ordered deterministically by `(AccountDate ASC, AccountId ASC)`.
   - Each row reports:
     - `debit_amount = round_2dp(amount)` if `amount >= 0.00` else `Decimal("0.00")`
     - `credit_amount = round_2dp(abs(amount))` if `amount < 0.00` else `Decimal("0.00")`
     - `signed_amount = round_2dp(amount)`
     - `running_balance = round_2dp(previous_running_balance + debit_amount - credit_amount)`
3. **Closing Balance Invariant**:
   $$\text{closing\_balance} = \text{round\_2dp}(\text{opening\_balance} + \text{total\_debit} - \text{total\_credit}) == \text{final\_running\_balance}$$
