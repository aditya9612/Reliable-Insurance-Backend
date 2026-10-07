# Phase 8 — Cheque Bounce & Penalty Accounting Specification

**Repository**: `Reliable-Insurance-Backend`  
**Phase**: `Phase 8 — Payments, Cheques & Reconciliation Engine (Stage A5)`  
**Target Runtime Database**: `localhost:3306/reliable_insurance_dev`

---

## 1. Legacy Cheque Bounce & Penalty Architecture (`Clerk/ChequeBounce.aspx.cs`)

In the legacy system, `Clerk/ChequeBounce.aspx.cs` invokes `sp_UpdateChequeStatus` and `sp_InsertChequeBouncePenalty` when a customer or agent cheque is dishonored by the bank.

### 1.1 Exact State & Financial Transitions on Cheque Bounce
Let:
- $C = \text{payment.PaidAmount}$ (the amount of the bounced cheque)
- $P_{\text{pen}} = \text{penalty\_amount} \ge 0.00$ (`Decimal`, manual/configurable dishonor bank charge supplied by Accounts in `ChequeBounce.aspx.cs`; defaults to `0.00` if no charge is levied)

When `POST /api/v1/payments/{payment_id}/bounce` is executed inside an atomic transaction boundary:

1. **Payment Instrument (`tbl_transactionpayment`)**:
   - `Extra1 = "BOUNCED"`
   - `Extra2 = f"BOUNCE:{bounce_reason}"`
   - `isdeleted = "1"` (excluded from active paid instruments)
   - `isCompletePayment = 0`
   - `UpdateDate = now_dt`, `UpdateUser = str(current_user.UserId)`

2. **Policy Transaction (`tbl_transaction`)**:
   - `PaidAmount = round_2dp(max(0.00, tx.PaidAmount - C))`
   - `OutstandingAmount = round_2dp(tx.OutstandingAmount + C + P_pen)`
   - `Ischequeclearing = 0`
   - `IsChequeCleared = 0`
   - `ChequeBankStatus = 2` (`2` = Bounced)
   - `CheqBankDate = bounce_dt`
   - `TStatus = "Pending"`
   - `pendingStatus = 1`
   - `IsActivePendingCash = 1`
   - `RAPaymentStatus = "BOUNCED"`
   - `UpdateEntryRemark = f"Cheque #{payment.docno} Bounced: {bounce_reason}"`

3. **Double-Entry Accounting Ledger (`tbl_account`)**:
   - **Entry A — Cheque Receipt Reversal (`AccTransId = 2`)**:
     - `amount = -round_2dp(C)` (Negative polarity — exact opposite of the original `+C` receipt entry)
     - `Extra1 = "CHEQUE_BOUNCE_REVERSAL"`
     - `Extra2 = tx.InwardNo`
     - `PaymentType = "CHEQUE_BOUNCE"`
     - `Narration = f"Cheque Bounce Reversal - Cheque #{payment.docno} ({bounce_reason}) - {tx.InwardNo}"`
   - **Entry B — Cheque Bounce Penalty Charge (`AccTransId = 4`, only when $P_{\text{pen}} > 0.00$)**:
     - `amount = +round_2dp(P_pen)` (Positive receivable/debit charge added to customer/agent obligation)
     - `Extra1 = "CHEQUE_BOUNCE_PENALTY"`
     - `Extra2 = tx.InwardNo`
     - `PaymentType = "PENALTY"`
     - `Narration = f"Cheque Bounce Penalty Charge - Cheque #{payment.docno} - {tx.InwardNo}"`

4. **Commission & Cut-and-Pay Impact**:
   - Because commission calculations (`AgentCommAmt`, `TdsAmt`, `NetCommission`) are underwriting-formula figures on the policy, the commission amounts themselves are **not** erased on a temporary cheque bounce (only policy cancellation reverses commission).
   - However, commission **payout eligibility** is suspended while the cheque is bounced:
     - `tbl_transaction.CommissionPaid = 0`
     - If a `tbl_cutnpaycommpayable` row exists for the transaction, its `Flag` is updated to `"HOLD_CHEQUE_BOUNCE"` and `Balance` reflects the unpaid shortfall until a replacement payment settles the policy.

---

## 2. Penalty / Charges Rules

- **Source of Penalty Amount**: In `Clerk/ChequeBounce.aspx.cs` (`sp_InsertChequeBouncePenalty`), the bank dishonor penalty is an explicit monetary amount (`Decimal >= 0.00`) entered by the Accountant/Admin based on the bank return memo (e.g., `₹0.00`, `₹250.00`, `₹500.00`), with no GST added to the bank dishonor fee.
- **Validation**: Negative `penalty_amount` (`< 0.00`) is rejected with `422 Unprocessable Entity`.
- **Subsequent Settlement**: Because `OutstandingAmount` is incremented by $C + P_{\text{pen}}$, a subsequent settlement payment of $C + P_{\text{pen}}$ via `POST /api/v1/policies/{transaction_id}/payments` cleanly brings `OutstandingAmount` to `0.00` and restores `TStatus = "Booked"`, `pendingStatus = 0`, and `CutNPayCommPayable.Flag = "CUTNPAY"`.
