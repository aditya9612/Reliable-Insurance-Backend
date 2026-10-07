# Phase 8 — Insurer Payment & Brokerage Reconciliation Specification

**Repository**: `Reliable-Insurance-Backend`  
**Phase**: `Phase 8 — Payments, Cheques & Reconciliation Engine (Stage A6)`  
**Target Runtime Database**: `localhost:3306/reliable_insurance_dev`

---

## 1. Legacy Insurer Reconciliation Architecture

In `tbl_transaction` (`app/models/transaction.py` — 166 verified columns), insurer payment remittance and brokerage commission reconciliation are tracked directly on the policy transaction record and journaled in `tbl_account`:

### 1.1 Physical Columns on `tbl_transaction`
1. **Outward Remittance to Insurer**:
   - `OnlinePaymentToCompany` (`INT`): Amount remitted directly online to the insurance company.
   - `OnlineToCompanyDate` (`DATETIME`): Timestamp of online payment to insurer.
   - `CompSubmitionDocNo` (`VARCHAR(255)`): Insurer submission document / receipt number.
   - `CompanyChequeNo` (`VARCHAR(255)`): Cheque number issued by broker/customer to the insurance company.
   - `IsCompanyChequeNo` (`INT`): `1` if paid via company cheque, `0` otherwise.
2. **Insurer Statement & Commission Reconciliation**:
   - `IsRconDataMatch` (`INT`):
     - `0` = Unreconciled (Default at policy booking)
     - `1` = Full Reconciliation Match (Insurer statement premium and commission grid match policy booking within `±₹1.00`)
     - `2` = Partial Reconciliation / Variance Match (Partial insurer receipt or commission grid variance recorded)
   - `RconGrid` (`DOUBLE` -> `Decimal`): Reconciled insurer commission percentage (`0.00` to `100.00`).
   - `RconComm` (`DOUBLE` -> `Decimal`): Reconciled insurer commission monetary amount (`Decimal`).
   - `accounting_period` (`DATETIME`): Accounting period date under which the reconciliation is locked.
3. **Insurer Brokerage (IB) Receipt Tracking**:
   - `IB_Doc_No` (`INT`): Insurer brokerage voucher / document number.
   - `IB_PaymentDate` (`DATETIME`): Date insurer brokerage receipt was recorded.
   - `IB_ReceiptStatus` (`INT`): `0` = Unreconciled, `1` = Reconciled (Full), `2` = Partial.
   - `IB_PaymentBy` (`VARCHAR(100)`): Mode/reference of insurer brokerage settlement (e.g., `"NEFT"`, `"RTGS"`, `"CHEQUE"`, `"ONLINE"`).

---

## 2. Deterministic Reconciliation Rules

### 2.1 Full vs Partial Reconciliation (`POST /api/v1/reconciliation` & `POST /api/v1/reconciliation/{transaction_id}/match`)
Given a policy transaction `tx` with `FinalPremium = tx.Amount` and `NetPermium = tx.NetPermium`:
1. **Input Parameters**:
   - `reconciled_premium_amount` (`Decimal`, optional; defaults to `tx.Amount`)
   - `rcon_grid_percent` (`Decimal >= 0.00`)
   - `rcon_commission_amount` (`Decimal`, optional; if omitted, computed as `round_2dp(tx.NetPermium * rcon_grid_percent / 100)`)
   - `comp_submission_doc_no` (`str`, optional)
   - `company_cheque_no` (`str`, optional)
   - `online_payment_to_company` (`Decimal`, optional)
   - `ib_doc_no` (`int`, optional)
   - `ib_payment_by` (`str`, optional)
   - `accounting_period` (`date`, optional)
2. **Match Classification**:
   - Let $\Delta_{\text{prem}} = |\text{reconciled\_premium\_amount} - \text{tx.Amount}|$.
   - If $\Delta_{\text{prem}} \le ₹1.00$ and not explicitly flagged `is_partial = True`:
     - `IsRconDataMatch = 1` (`"MATCHED"`)
     - `IB_ReceiptStatus = 1`
   - If $0 < \text{reconciled\_premium\_amount} < \text{tx.Amount} - ₹1.00$ or `is_partial == True`:
     - `IsRconDataMatch = 2` (`"PARTIAL"`)
     - `IB_ReceiptStatus = 2`
3. **Accounting Ledger Effect (`tbl_account`)**:
   - Posts an insurer reconciliation journal entry (`AccTransId = 5`, `Extra1 = "INSURER_RECONCILIATION"`, `amount = rcon_commission_amount` if `> 0` else `reconciled_premium_amount`, `PaymentType = ib_payment_by or "RECONCILIATION"`).
4. **Idempotency & Duplicate Protection**:
   - If `tx.IsRconDataMatch == 1` and a duplicate full reconciliation request is submitted without `allow_re_reconcile = True`, raises `409 Conflict` (`"Transaction is already fully reconciled"`).
   - Transitioning from `PARTIAL` (`IsRconDataMatch == 2`) to `MATCHED` (`IsRconDataMatch == 1`) is permitted when the remaining balance is reconciled.
5. **Reconciliation Reversal (`POST /api/v1/reconciliation/{transaction_id}/reverse`)**:
   - Resets `IsRconDataMatch = 0`, `IB_ReceiptStatus = 0`, `RconGrid = 0.00`, `RconComm = 0.00`, and soft-deletes/reverses the `AccTransId = 5` ledger entry.
