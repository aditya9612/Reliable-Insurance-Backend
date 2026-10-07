# Phase 8 — Atomicity, Idempotency & Concurrency Specification

**Repository**: `Reliable-Insurance-Backend`  
**Phase**: `Phase 8 — Payments, Cheques & Reconciliation Engine (Stage A10)`  
**Target Runtime Database**: `localhost:3306/reliable_insurance_dev`

---

## 1. Atomic Transaction Boundaries

Every Phase 8 financial mutation executes inside a single SQLAlchemy transaction boundary with `SELECT ... FOR UPDATE` row locking and explicit `await session.rollback()` on any validation or runtime failure:

### 1.1 Subsequent Policy Payment (`POST /api/v1/policies/{transaction_id}/payments`)
```text
BEGIN TRANSACTION
  1. SELECT * FROM tbl_transaction WHERE TransanctionId = :id FOR UPDATE
  2. Validate idempotency_key (409 if duplicate) and paid_amount <= OutstandingAmount (422 if overpayment)
  3. If PaymentType == "EWALLET":
       SELECT * FROM tbl_ledgermaster WHERE LedgerMId = :wallet_lid FOR UPDATE
       Validate available_balance >= paid_amount (or consume active wallet_lock_id)
       INSERT INTO tbl_account (AccTransId = 13, Extra1 = "WALLET_DEBIT", amount = -paid_amount)
  4. INSERT INTO tbl_transactionpayment (...)
  5. UPDATE tbl_transaction SET PaidAmount += paid_amount, OutstandingAmount -= paid_amount, TStatus, pendingStatus, Ischequeclearing, IsChequeCleared
  6. INSERT INTO tbl_account (AccTransId = 2, Extra1 = "POLICY_PAYMENT", amount = +paid_amount)
COMMIT (or ROLLBACK all steps on any failure)
```

### 1.2 Cheque Clearance (`POST /api/v1/payments/{payment_id}/clear`)
```text
BEGIN TRANSACTION
  1. SELECT * FROM tbl_transactionpayment WHERE PaymentId = :pid FOR UPDATE
  2. SELECT * FROM tbl_transaction WHERE TransanctionId = :tid FOR UPDATE
  3. Validate PaymentType in ("CHEQUE", "DD") and state in ("PENDING_CLEARANCE", "DEPOSITED")
  4. UPDATE tbl_transactionpayment SET Extra1 = "CLEARED", CashierApproval = 1, AccountantApproval = 1
  5. If all active cheques on tbl_transaction are CLEARED:
       UPDATE tbl_transaction SET Ischequeclearing = 0, IsChequeCleared = 1, ChequeBankStatus = 1, CheqBankDate = :dt
       If OutstandingAmount == 0.00: SET TStatus = "Booked", pendingStatus = 0
COMMIT (or ROLLBACK on failure)
```

### 1.3 Cheque Bounce & Penalty (`POST /api/v1/payments/{payment_id}/bounce`)
```text
BEGIN TRANSACTION
  1. SELECT * FROM tbl_transactionpayment WHERE PaymentId = :pid FOR UPDATE
  2. SELECT * FROM tbl_transaction WHERE TransanctionId = :tid FOR UPDATE
  3. Validate PaymentType in ("CHEQUE", "DD") and state not in ("BOUNCED", "REVERSED")
  4. UPDATE tbl_transactionpayment SET Extra1 = "BOUNCED", isdeleted = "1", isCompletePayment = 0
  5. UPDATE tbl_transaction SET PaidAmount -= C, OutstandingAmount += (C + penalty),
       Ischequeclearing = 0, IsChequeCleared = 0, ChequeBankStatus = 2,
       TStatus = "Pending", pendingStatus = 1, CommissionPaid = 0
  6. Update tbl_cutnpaycommpayable (if present) Flag = "HOLD_CHEQUE_BOUNCE"
  7. INSERT INTO tbl_account (AccTransId = 2, Extra1 = "CHEQUE_BOUNCE_REVERSAL", amount = -C)
  8. If penalty > 0:
       INSERT INTO tbl_account (AccTransId = 4, Extra1 = "CHEQUE_BOUNCE_PENALTY", amount = +penalty)
COMMIT (or ROLLBACK on failure)
```

### 1.4 Payment Reversal (`POST /api/v1/payments/{payment_id}/reverse`)
```text
BEGIN TRANSACTION
  1. SELECT * FROM tbl_transactionpayment WHERE PaymentId = :pid FOR UPDATE
  2. SELECT * FROM tbl_transaction WHERE TransanctionId = :tid FOR UPDATE
  3. Validate payment is active (isdeleted == "0")
  4. UPDATE tbl_transactionpayment SET Extra1 = "REVERSED", isdeleted = "1", isCompletePayment = 0
  5. UPDATE tbl_transaction SET PaidAmount -= amt, OutstandingAmount += amt, TStatus = "Pending", pendingStatus = 1
  6. INSERT INTO tbl_account (AccTransId = 2, Extra1 = "PAYMENT_REVERSAL", amount = -amt)
  7. If PaymentType == "EWALLET":
       SELECT * FROM tbl_ledgermaster WHERE LedgerMId = :wallet_lid FOR UPDATE
       INSERT INTO tbl_account (AccTransId = 14, Extra1 = "WALLET_REFUND", amount = +amt)
COMMIT (or ROLLBACK on failure)
```

---

## 2. Idempotency Guarantees

| Operation | Idempotency Mechanism | Behavior on Duplicate Retry |
|---|---|---|
| **Subsequent Payment (`POST /policies/{id}/payments`)** | Optional `idempotency_key` stored in `tbl_transactionpayment.Extra2` (`IDEMP:{key}`) + `OutstandingAmount` ceiling | Returns `409 Conflict` (`"Duplicate payment request"`) — zero double settlement |
| **Cheque Clearance (`POST /payments/{id}/clear`)** | Checks `payment.Extra1 == "CLEARED"` under `FOR UPDATE` lock | Returns `409 Conflict` (`"Cheque is already cleared"`) |
| **Cheque Bounce (`POST /payments/{id}/bounce`)** | Checks `payment.Extra1 == "BOUNCED"` under `FOR UPDATE` lock | Returns `409 Conflict` (`"Cheque is already bounced"`) — zero double reversal or double penalty |
| **Payment Reversal (`POST /payments/{id}/reverse`)** | Checks `payment.isdeleted == "1"` / `Extra1 == "REVERSED"` under `FOR UPDATE` lock | Returns `409 Conflict` (`"Payment is already reversed"`) |
| **Wallet Top-Up / Lock / Debit** | Optional `idempotency_key` stored in `tbl_account.Extra2` (`IDEMP:{key}`) under `FOR UPDATE` lock | Returns `409 Conflict` (`"Duplicate wallet operation"`) |
| **Wallet Release (`POST /wallets/{id}/release`)** | Checks lock row `Extra1 == "WALLET_LOCK_RELEASED"` under `FOR UPDATE` lock | Returns `409 Conflict` (`"Wallet lock is already released"`) |
| **Insurer Reconciliation (`POST /reconciliation`)** | Checks `tx.IsRconDataMatch == 1` under `FOR UPDATE` lock | Returns `409 Conflict` (`"Transaction is already fully reconciled"`) |
