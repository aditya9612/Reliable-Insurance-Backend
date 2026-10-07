# Phase 8 — Cheque Lifecycle Specification

**Repository**: `Reliable-Insurance-Backend`  
**Phase**: `Phase 8 — Payments, Cheques & Reconciliation Engine (Stage A4)`  
**Target Runtime Database**: `localhost:3306/reliable_insurance_dev`

---

## 1. End-to-End Cheque & DD Lifecycle

In the legacy system (`Clerk/PolicyTransactionNew.aspx.cs`, `Clerk/ChequeClearance.aspx.cs`, `Clerk/ChequeBounce.aspx.cs`), `CHEQUE` and `DD` instruments progress through five deterministic stages:

1. **Stage 1 — Cheque Receipt (At Policy Booking or Subsequent Payment)**:
   - Mandatory fields: `docno` (Cheque/DD number), `bankname` (Issuing bank), `paid_amount > 0` (`Decimal`), `payment_date` (Cheque date).
   - `tbl_transactionpayment` row created with:
     - `PaymentType = "CHEQUE"` (or `"DD"`)
     - `CashierApproval = 0`, `AccountantApproval = 0`, `OwnerApproval = 0`
     - `Extra1 = "PENDING_CLEARANCE"`
     - `isdeleted = "0"`
   - `tbl_transaction` updated with:
     - `Ischequeclearing = 1`
     - `IsChequeCleared = 0`
     - `ChequeBankStatus = 0` (`0` = Pending / In Clearing)
     - `CheqBankDate = None`
   - `tbl_account` row created with:
     - `AccTransId = 2`, `amount = +PaidAmount`, `PaymentType = "CHEQUE"`, `Extra1 = "POLICY_PAYMENT"`.

2. **Stage 2 — Cheque Deposit (`POST /api/v1/payments/{payment_id}/deposit`)**:
   - Cashier/Operator records physical bank deposit slip details (`deposit_date`, `deposit_bank`, `deposit_ref_no`).
   - `tbl_transactionpayment` updated:
     - `CashierApproval = 1`, `CashierApprovalDate = deposit_dt`
     - `Extra1 = "DEPOSITED"`
     - `Extra2 = deposit_ref_no`
   - `tbl_transaction` remains `Ischequeclearing = 1`, `IsChequeCleared = 0`, `ChequeBankStatus = 0`.

3. **Stage 3 — Cheque Clearance (`POST /api/v1/payments/{payment_id}/clear`)**:
   - Executed by `ACCOUNT`, `ACCOUNT HEAD`, `CASHIER`, `ADMIN`, `OWNER`, or `IT SUPPORT` (`sp_UpdateChequeStatus` parity).
   - Validations:
     - Instrument must be `"CHEQUE"` or `"DD"`.
     - If already `"CLEARED"`, idempotent if same request or raises `409 Conflict` (`"Cheque is already cleared"`).
     - If `"BOUNCED"` or `"REVERSED"`, raises `409 Conflict` (`"Cannot clear a bounced or reversed cheque"`).
   - `tbl_transactionpayment` updated:
     - `CashierApproval = 1`
     - `AccountantApproval = 1`, `AccountantApprovalDate = clearance_dt`
     - `Extra1 = "CLEARED"`
     - `Extra2 = bank_clearance_ref or "CLEARED"`
   - `tbl_transaction` updated:
     - If no other active cheque on the transaction is still in `PENDING_CLEARANCE` or `DEPOSITED`:
       - `Ischequeclearing = 0`
       - `IsChequeCleared = 1`
       - `ChequeBankStatus = 1` (`1` = Cleared)
       - `CheqBankDate = clearance_dt`
     - If `OutstandingAmount == 0.00` and all cheques are cleared:
       - `TStatus = "Booked"`, `pendingStatus = 0`, `RAPaymentStatus = "COMPLETE"`, `IsActivePendingCash = 0`.

4. **Stage 4 — Cheque Dishonor / Bounce (`POST /api/v1/payments/{payment_id}/bounce`)**:
   - Detailed in `docs/migration/phase_8_cheque_bounce.md`.
   - Marks `tbl_transactionpayment.Extra1 = "BOUNCED"`, `isdeleted = "1"`, `isCompletePayment = 0`.
   - Sets `tbl_transaction.Ischequeclearing = 0`, `IsChequeCleared = 0`, `ChequeBankStatus = 2`, `CheqBankDate = bounce_dt`.
   - Reverses `PaidAmount`, restores `OutstandingAmount` (plus any bounce penalty if applicable), reverts `TStatus = "Pending"`, `pendingStatus = 1`, and posts reversal + penalty vouchers in `tbl_account`.

5. **Stage 5 — Re-Presentation / Replacement Settlement (`POST /api/v1/policies/{transaction_id}/payments`)**:
   - After a cheque bounces, the policy carries `OutstandingAmount > 0.00` and `TStatus = "Pending"`.
   - The customer/agent submits a replacement instrument (`CASH`, `NEFT`, `UPI`, `EWALLET`, or a new `CHEQUE`) via `POST /api/v1/policies/{transaction_id}/payments`.
   - Once the replacement payment settles `OutstandingAmount == 0.00` (and clears if a cheque), `tbl_transaction` transitions back to `TStatus = "Booked"`, `pendingStatus = 0`.
