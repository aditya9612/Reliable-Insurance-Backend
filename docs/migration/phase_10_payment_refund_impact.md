# Phase 10 — Endorsement Payment & Refund Impact (`phase_10_payment_refund_impact.md`)

## 1. Overview
This document specifies the financial impact on policy payment status (`PaidAmount`, `OutstandingAmount`, `TStatus`, `pendingStatus`), customer receivables, and customer refunds when an endorsement is applied to a policy in Phase 10.

---

## 2. Three Financial Endorsement Scenarios

Let:
- $\text{OldFinal} = \text{tbl\_transaction.Amount}$ (before endorsement)
- $\text{NewFinal} = \text{NewFinalPremium}$ (after endorsement)
- $\Delta \text{Premium} = \text{NewFinal} - \text{OldFinal}$
- $\text{Paid} = \text{tbl\_transaction.PaidAmount}$ (already cleared/collected premium on the policy)

### Scenario 1: Zero Premium Delta ($\Delta \text{Premium} == 0.00$)
- `EndorsementCategory` $\in \{\text{"NON\_FINANCIAL"}, \text{"ZERO\_PREMIUM"}\}$
- `Amount`, `PaidAmount`, and `OutstandingAmount` on `tbl_transaction` remain unchanged.
- `RefundStatus = "NONE"`, `RefundAmount = 0.00`.

### Scenario 2: Positive Premium Delta ($\Delta \text{Premium} > 0.00$ — Additional Premium Receivable)
- `EndorsementCategory = "ADDITIONAL_PREMIUM"`
- `tbl_transaction.Amount` is updated to $\text{NewFinal}$.
- New outstanding amount on the policy:
  $$\text{NewOutstanding} = \max\left(\text{Decimal}(\text{"0.00"}), \text{NewFinal} - \text{Paid}\right)$$
- `tbl_transaction.OutstandingAmount = NewOutstanding`.
- If $\text{NewOutstanding} > 0.00$, `tbl_transaction.pendingStatus = "PENDING_ENDORSEMENT_PAYMENT"`.
- Subsequent payment collection reuses Phase 8 `PaymentEngineService` (`POST /api/v1/payments`) or Wallet Debit (`WalletService`) to clear the additional `OutstandingAmount`.
- `RefundStatus = "NONE"`, `RefundAmount = 0.00`.

### Scenario 3: Negative Premium Delta ($\Delta \text{Premium} < 0.00$ — Downward Premium / Refund)
- `EndorsementCategory = "REFUND_PREMIUM"`
- `tbl_transaction.Amount` is updated to $\text{NewFinal}$.
- Two sub-cases depend on how much the customer has already paid ($\text{Paid}$):
  1. **Customer Has Paid More Than `NewFinal` ($\text{Paid} > \text{NewFinal}$)**:
     - The excess collected amount is refundable to the customer/agent wallet:
       $$\text{RefundAmount} = \min\left(\left|\Delta \text{Premium}\right|, \text{Paid} - \text{NewFinal}\right)$$
     - `tbl_transaction.OutstandingAmount = Decimal("0.00")`.
     - `tbl_appendorsement.RefundAmount = RefundAmount`.
     - `tbl_appendorsement.RefundStatus = "PENDING_APPROVAL"`.
  2. **Customer Has Not Yet Paid `NewFinal` ($\text{Paid} \le \text{NewFinal}$)**:
     - The downward endorsement simply reduces the unpaid `OutstandingAmount`:
       $$\text{NewOutstanding} = \text{NewFinal} - \text{Paid}$$
     - `tbl_transaction.OutstandingAmount = NewOutstanding`.
     - No cash/wallet refund is due (`RefundAmount = Decimal("0.00")`, `RefundStatus = "NONE"`).

---

## 3. Refund Approval, Disbursement & Reversal Lifecycle

When `RefundStatus == "PENDING_APPROVAL"` and `RefundAmount > 0.00`:

1. **Refund Approval (`POST /api/v1/refunds/{endorsement_id}/approve`)**:
   - Restricted to `REFUND_APPROVE_WRITE_ROLES` (`Admin`, `Managing Director`, `Director`, `VP`, `General Manager`, `HO`, `Manager`, `Accounts`).
   - Transitions `RefundStatus` from `PENDING_APPROVAL` to `APPROVED`.
2. **Refund Disbursement (`POST /api/v1/refunds/{endorsement_id}/disburse`)**:
   - Precondition: `RefundStatus == "APPROVED"`.
   - Supported `RefundMode` values:
     - `NEFT` / `CHEQUE` / `BANK_TRANSFER`:
       - Posts balanced double-entry refund payout rows (`AccTransId = 17`) in `tbl_account`:
         - `DEBIT` (`+RefundAmount`) to Ledger `204` (`Customer Refund Payable / Endorsement Credit`)
         - `CREDIT` (`-RefundAmount`) to Ledger `102` (`Bank / Settlement Clearing Account`)
     - `WALLET`:
       - Credits the agent's E-Wallet via `WalletService` (or updates `tbl_ewallet` + `tbl_wallet_transactions` with `REFUND` credit) and posts balanced double-entry rows (`AccTransId = 17` / `14`) in `tbl_account`.
   - Reduces `tbl_transaction.PaidAmount` by `RefundAmount` so `PaidAmount == NewFinalPremium`.
   - Transitions `RefundStatus` to `REFUNDED` and records `RefundDocNo`.
3. **Refund Reversal (`POST /api/v1/refunds/{endorsement_id}/reverse`)**:
   - Precondition: `RefundStatus == "REFUNDED"`.
   - Posts contra double-entry rows (`AccTransId = 18`) in `tbl_account` (and debits wallet if `RefundMode == "WALLET"`), restores `PaidAmount`, and transitions `RefundStatus` to `REVERSED`.
