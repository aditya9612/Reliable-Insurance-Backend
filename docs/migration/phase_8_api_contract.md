# Phase 8 — FastAPI REST API Contract Specification

**Repository**: `Reliable-Insurance-Backend`  
**Phase**: `Phase 8 — Payments, Cheques & Reconciliation Engine (Stage A9)`  
**Target Runtime Database**: `localhost:3306/reliable_insurance_dev`

---

## 1. Endpoint Overview

Phase 8 extends `/api/v1/policies` and introduces three router namespaces mounted in `app/api/v1/router.py`:
- `/api/v1/policies/{transaction_id}/payments` — Policy-scoped payment instrument collection and listing
- `/api/v1/payments` — Instrument lifecycle operations (list, get, deposit, clear, bounce, reverse, multi-tier approve)
- `/api/v1/reconciliation` — Single and batch insurer payment & brokerage commission reconciliation
- `/api/v1/wallets` — Partner (Agent / Franchise) E-Wallet balance, ledger, top-up, lock, release, and debit

---

## 2. Detailed Endpoint Contracts

### 2.1 Policy Payment Endpoints (`/api/v1/policies`)
1. **`POST /api/v1/policies/{transaction_id}/payments`** (`201 Created` $\rightarrow$ `PolicyBookingResponse`)
   - **Legacy SP**: `sp_InsertTransactionPayment`, `sp_InsertAccountDetails`
   - **Request Body (`PaymentInstrumentCreateRequest`)**:
     - `payment_type`: `"CASH" | "CHEQUE" | "DD" | "NEFT" | "RTGS" | "UPI" | "ONLINE" | "CREDIT_CARD" | "DEBIT_CARD" | "EWALLET"`
     - `paid_amount`: `Decimal > 0.00`
     - `payment_date`: `Optional[date]`
     - `docno`: `Optional[str]` (Required for `"CHEQUE"` and `"DD"`)
     - `bankname`: `Optional[str]` (Required for `"CHEQUE"` and `"DD"`)
     - `payment_details`: `Optional[str]`
     - `wallet_owner_id`: `Optional[int]` (Used when `payment_type == "EWALLET"`)
     - `wallet_owner_type`: `Optional[Literal["AGENT", "FRANCHISE"]]` (Default `"AGENT"`)
     - `wallet_lock_id`: `Optional[int]` (Consumes an existing active wallet lock when `payment_type == "EWALLET"`)
     - `idempotency_key`: `Optional[str]` (Rejects duplicate requests with `409 Conflict`)
2. **`GET /api/v1/policies/{transaction_id}/payments`** (`200 OK` $\rightarrow$ `PolicyPaymentListResponse`)
   - **Legacy SP**: `sp_GetPaymentsByTransactionId`
   - Returns all payment instruments (active and reversed/bounced when `include_deleted=True`) and the policy's `PolicyPaymentSummary`.

### 2.2 Payment & Cheque Lifecycle Endpoints (`/api/v1/payments`)
3. **`GET /api/v1/payments`** (`200 OK` $\rightarrow$ `PaymentInstrumentListResponse`)
   - Filters: `transaction_id`, `payment_type`, `status` (`Extra1`), `docno`, `cashier_approval`, `accountant_approval`, `include_deleted`, `limit`, `offset`.
4. **`GET /api/v1/payments/{payment_id}`** (`200 OK` $\rightarrow$ `PaymentLifecycleResponse`)
   - Returns full payment instrument details + parent policy financial state (`paid_amount`, `outstanding_amount`, `t_status`, `pending_status`, `is_cheque_clearing`, `is_cheque_cleared`, `cheque_bank_status`).
5. **`POST /api/v1/payments/{payment_id}/deposit`** (`200 OK` $\rightarrow$ `PaymentLifecycleResponse`)
   - **Legacy SP**: `sp_UpdateChequeStatus` (Deposit)
   - Request (`ChequeDepositRequest`): `deposit_date`, `deposit_bank`, `deposit_ref_no`, `remark`.
   - Transitions `CHEQUE` / `DD` from `PENDING_CLEARANCE` to `DEPOSITED`.
6. **`POST /api/v1/payments/{payment_id}/clear`** (`200 OK` $\rightarrow$ `PaymentLifecycleResponse`)
   - **Legacy SP**: `sp_UpdateChequeStatus` (Clearance)
   - Request (`ChequeClearanceRequest`): `clearance_date`, `bank_ref_no`, `remark`, `idempotency_key`.
   - Transitions `CHEQUE` / `DD` to `CLEARED`, updates `tbl_transaction` (`Ischequeclearing=0`, `IsChequeCleared=1`, `ChequeBankStatus=1`, `CheqBankDate`), and promotes `TStatus = "Booked"` when `OutstandingAmount == 0.00`.
7. **`POST /api/v1/payments/{payment_id}/bounce`** (`200 OK` $\rightarrow$ `PaymentLifecycleResponse`)
   - **Legacy SP**: `sp_UpdateChequeStatus` + `sp_InsertChequeBouncePenalty`
   - Request (`ChequeBounceRequest`): `bounce_date`, `bounce_reason`, `penalty_amount` (`Decimal >= 0.00`, default `0.00`), `idempotency_key`, `simulate_failure_at`.
   - Atomically marks cheque `BOUNCED` (`isdeleted="1"`), decrements `PaidAmount`, increments `OutstandingAmount` by `cheque_amount + penalty_amount`, sets `TStatus = "Pending"`, `ChequeBankStatus = 2`, suspends `CommissionPaid = 0`, and posts reversal (`AccTransId = 2`, `-cheque_amount`) + penalty (`AccTransId = 4`, `+penalty_amount`) in `tbl_account`.
8. **`POST /api/v1/payments/{payment_id}/reverse`** (`200 OK` $\rightarrow$ `PaymentLifecycleResponse`)
   - **Legacy SP**: `sp_ReverseTransactionPayment`
   - Request (`PaymentReversalRequest`): `reason`, `reversal_date`, `idempotency_key`, `simulate_failure_at`.
   - Atomically marks payment `REVERSED` (`isdeleted="1"`), decrements `PaidAmount`, increments `OutstandingAmount`, reverts `TStatus = "Pending"`, posts contra `AccTransId = 2` (`-paid_amount`), and if `PaymentType == "EWALLET"`, credits `+paid_amount` (`AccTransId = 14`, `"WALLET_REFUND"`) back to the partner's E-Wallet.
9. **`POST /api/v1/payments/{payment_id}/approve`** (`200 OK` $\rightarrow$ `PaymentLifecycleResponse`)
   - **Legacy SP**: `sp_UpdateCashierApproval`, `sp_UpdateAccountantApproval`, `sp_UpdateOwnerPaymentApproval`
   - Request (`PaymentApprovalRequest`): `stage` (`"CASHIER" | "ACCOUNTANT" | "OWNER"`), `approved` (`bool`), `remark`.

### 2.3 Insurer Payment & Commission Reconciliation Endpoints (`/api/v1/reconciliation`)
10. **`POST /api/v1/reconciliation`** (`200 OK` $\rightarrow$ `ReconciliationBatchResponse`)
    - Processes single or batch insurer reconciliation items atomically (or with per-item match reporting).
11. **`GET /api/v1/reconciliation`** (`200 OK` $\rightarrow$ `ReconciliationListResponse`)
    - Lists policy transactions with reconciliation status (`is_rcon_data_match`, `ib_receipt_status`, `insurance_company_id`, `policy_no`).
12. **`POST /api/v1/reconciliation/{transaction_id}/match`** (`200 OK` $\rightarrow$ `ReconciliationItemResponse`)
    - Matches or partially reconciles a single policy transaction (`IsRconDataMatch = 1` or `2`, `RconGrid`, `RconComm`, `IB_ReceiptStatus`, `AccTransId = 5`).
13. **`POST /api/v1/reconciliation/{transaction_id}/reverse`** (`200 OK` $\rightarrow$ `ReconciliationItemResponse`)
    - Reverses reconciliation on `tbl_transaction` and soft-deletes/reverses the `AccTransId = 5` ledger entry.

### 2.4 Partner E-Wallet Endpoints (`/api/v1/wallets`)
14. **`GET /api/v1/wallets/{owner_id}`** (`200 OK` $\rightarrow$ `WalletDetailResponse`)
    - **Legacy SP**: `sp_GetWalletBalance`, `sp_GetWalletLedger`
    - Query parameter: `owner_type` (`"AGENT" | "FRANCHISE"`, default `"AGENT"`).
    - Returns `total_credited`, `total_debited`, `locked_amount`, `total_balance`, `available_balance`, and chronological `ledger_entries`.
15. **`POST /api/v1/wallets/top-up`** (`201 Created` $\rightarrow$ `WalletOperationResponse`)
    - **Legacy SP**: `sp_ApproveEWalletRequest`, `sp_ApproveFranchiseWallet`
    - Credits `amount > 0.00` (`AccTransId = 10`, `"WALLET_TOPUP"`) to `owner_id`'s wallet under `FOR UPDATE` lock.
16. **`POST /api/v1/wallets/{owner_id}/lock`** (`201 Created` $\rightarrow$ `WalletOperationResponse`)
    - Reserves `amount > 0.00` (`AccTransId = 11`, `"WALLET_LOCK"`) under `FOR UPDATE` lock (`422` if `amount > available_balance`).
17. **`POST /api/v1/wallets/{owner_id}/release`** (`200 OK` $\rightarrow$ `WalletOperationResponse`)
    - Releases an active wallet lock (`lock_id`, `AccTransId = 12`, `"WALLET_RELEASE"`), restoring `available_balance`.
18. **`POST /api/v1/wallets/{owner_id}/debit`** (`200 OK` $\rightarrow$ `WalletOperationResponse`)
    - Directly debits `amount > 0.00` or consumes an active `lock_id` (`AccTransId = 13`, `"WALLET_DEBIT"`).
