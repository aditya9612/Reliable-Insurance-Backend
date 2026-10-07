# Phase 9 — Commission Reversal & Clawback Specification

**Repository**: `Reliable-Insurance-Backend`  
**Phase**: `Phase 9 — Commission & Accounting Engine (Stage A7)`  
**Target Runtime Database**: `localhost:3306/reliable_insurance_dev`

---

## 1. Commission Reversal Triggers

In legacy operations (`Clerk/adm_DeletePolicyTransaction.aspx.cs`, `Clerk/ChequeBounce.aspx.cs`, `Clerk/AgentCommisionApproval.aspx.cs`), commission reversal or clawback occurs under four distinct business events:
1. **Payout Reversal (`POST /api/v1/commission-payouts/{voucher_doc_no}/reverse`)**:
   - Reverses a previously disbursed Agent or Franchise commission payout voucher (e.g., failed bank NEFT transfer, wrong partner account, or clawback).
2. **Accrued Commission Reversal / Adjustment (`POST /api/v1/commissions/{commission_type}/{commission_id}/reverse`)**:
   - Reverses an accrued Agent (`tbl_agentcommissionpayment`) or Franchise (`tbl_franchisecommission`) commission record while preserving the historical audit trail in `tbl_account`.
3. **Cheque Bounce Commission Hold (`POST /api/v1/payments/{payment_id}/bounce`)**:
   - Places Cut & Pay (`Flag = "HOLD_CHEQUE_BOUNCE"`) and Agent Commission (`PaymentStatus = 0.00`, `Narration = "HOLD: ..."`) on hold and resets `tbl_transaction.CommissionPaid = 0`.
4. **Policy Cancellation Cascade (`POST /api/v1/policies/{transaction_id}/cancel`)**:
   - Soft-deletes the policy (`tbl_transaction.isdeleted = "1"`) and cascades soft-delete/reversal across `tbl_franchisecommission`, `tbl_agentcommissionpayment`, `tbl_cutnpaycommpayable`, and `tbl_account`.

---

## 2. Payout Reversal Mechanics (`POST /api/v1/commission-payouts/{doc_no}/reverse`)

Given a payout voucher identified by `doc_no` (`tbl_account.Doc_No` where `AccTransId == 6` and `Extra1 in ("COMMISSION_PAYOUT_DEBIT", "COMMISSION_PAYOUT_CREDIT")`):
1. **Terminal State & Idempotency Guard**:
   - Locks all `tbl_account` rows for `Doc_No == doc_no` with `SELECT ... FOR UPDATE`.
   - If the payout voucher has already been reversed (`Extra1` contains `"REVERSED"` or a paired `AccTransId == 7` reversal voucher already exists for `doc_no`), raises **`HTTP 409 Conflict`** (`"Commission payout voucher #{doc_no} has already been reversed"`).
2. **Restoring Payable Balances**:
   - For an Agent Commission Payout of amount $P$ on `AgentCommissionPayment` (`acp`):
     - $\text{AdvAmt}_{\text{new}} = \max(0.00,\ \text{round\_2dp}(\text{AdvAmt}_{\text{old}} - P))$
     - $\text{NetAmount}_{\text{new}} = \text{round\_2dp}(\text{NetCommission} - \text{AdvAmt}_{\text{new}})$
     - `acp.PaymentStatus = Decimal("2.00")` if $\text{AdvAmt}_{\text{new}} > 0.00$ else `Decimal("0.00")`.
     - `tx.CommissionPaid = 0`.
     - If a `CutNPayCommPayable` row exists for `tx.TransanctionId`, updates `Balance = NetAmount_new`, `Flag = "CUTNPAY"`.
   - For a Franchise Commission Payout of amount $P$ on `FranchiseCommission` (`fc`):
     - $\text{FCommissionPaid}_{\text{new}} = \max(0.00,\ \text{round\_2dp}(\text{FCommissionPaid}_{\text{old}} - P))$
     - `tx.FranchiseCommPaid = 0`.
   - If the original payout was credited to an E-Wallet (`payout_mode == "EWALLET"`), posts a clawback debit (`AccTransId = 13`, `Extra1 = "WALLET_DEBIT"`, `amount = -P`) on the partner's E-Wallet sub-ledger.
3. **Contra Accounting Voucher (`AccTransId = 7`)**:
   - Preserves the original `AccTransId = 6` rows in `tbl_account` (never silently deleting financial history!) and posts an offsetting reversal voucher pair (`AccTransId = 7`, `Extra1 = "COMMISSION_PAYOUT_REVERSAL_CREDIT"` `-P` on the Commission Payable ledger and `Extra1 = "COMMISSION_PAYOUT_REVERSAL_DEBIT"` `+P` on the Bank/Cash ledger).
   - Net effect on Trial Balance and Ledger Statements: $(+P - P) = 0.00$.

---

## 3. Accrued Commission Reversal (`POST /api/v1/commissions/{commission_type}/{commission_id}/reverse`)

When reversing an accrued commission row (`commission_type in ("AGENT", "FRANCHISE")`):
- If already reversed (`isdeleted == "1"` / `1`), raises **`HTTP 409 Conflict`**.
- Marks the commission row reversed (`isdeleted = "1"` on `tbl_agentcommissionpayment` or `isdeleted = 1` on `tbl_franchisecommission`), updates `tbl_cutnpaycommpayable` (`Flag = "REVERSED"`, `Isdeleted = 1`), resets `tx.CommissionPaid = 0` / `tx.FranchiseCommPaid = 0`, and posts a contra commission reversal entry (`AccTransId = 7`, `Extra1 = "COMMISSION_ACCRUAL_REVERSAL"`, `amount = +NetCommission`) to offset the original `AccTransId = 3` (`-NetCommission`) entry in `tbl_account`.
