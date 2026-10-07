# Phase 8 — Final Migration Report: Payments, Cheques, Reconciliation & E-Wallet Engine

## 1. Executive Summary
Phase 8 of the **Reliable Insurance Backend Migration** (`C# / ASP.NET 4.0 WebForms & ASMX` $\rightarrow$ `FastAPI / Async SQLAlchemy 2.x / MySQL 8.0`) has been completed with **100% verified parity** (`0.00` monetary discrepancy across all 25 Golden Parity scenarios, `100` concurrent wallet operations verified with `0` negative balance occurrences, and `243/243` automated tests passing across Phases 1–8).

Phase 8 delivers the full **Payments, Cheques, Dishonor/Bounce & Penalty, Reversal/Refund, Insurer Brokerage Reconciliation, and Partner E-Wallet (Top-Up, Lock, Release, Debit)** engine on top of the Phase 7 Policy Booking & Transaction Engine—strictly preserving legacy physical schemas, legacy column names (`TransanctionId`, `Ischequeclearing`, `IsChequeCleared`, `ChequeBankStatus`, `IsRconDataMatch`, `RconGrid`, `RconComm`, `EWalletAmountUsed`), and legacy double-entry accounting polarity in `tbl_account`.

---

## 2. Production Safety Confirmation
- **Target Runtime & Test Database**: `localhost:3306/reliable_insurance_dev` (`APP_ENV=testing` / `development`).
- **Legacy Production Database (`brahmainsurance`)**: **ZERO connections, ZERO queries, ZERO data exports/imports**.
- **Config Guard**: `Settings.enforce_production_isolation` in [`app/core/config.py`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/app/core/config.py) blocks any connection string referencing `brahmainsurance`.
- **Synthetic Test Data Only**: All 38 Phase 8 test cases and 25 Golden Parity cases (`P8-01` .. `P8-25`) generate synthetic customers, vehicles, quotations, policies, cheques, wallets, and reconciliation records exclusively in `reliable_insurance_dev`.

---

## 3. Legacy Payment & Cheque Entry Points Audited
Audited in [`docs/migration/phase_8_payment_legacy_audit.md`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/docs/migration/phase_8_payment_legacy_audit.md):
- `Clerk/PolicyTransactionNew.aspx.cs` & `Clerk/PE_TransactionEntry.aspx.cs` (Initial & split payment collection, Cut & Pay deduction, E-Wallet deduction)
- `Clerk/PendingPolicyPayment.aspx.cs` & `Clerk/CustomerPaymentEntry.aspx.cs` (Subsequent balance settlement against `OutstandingAmount`)
- `Clerk/CashierApproval.aspx.cs` & `Clerk/ChequeDepositEntry.aspx.cs` (Cashier verification and bank deposit of pending cheques/DDs)
- `Clerk/AccountantChequeClearance.aspx.cs` & `Clerk/ChequeBounceEntry.aspx.cs` (Cheque clearance, dishonor/bounce, penalty assessment, policy reopening, commission hold)
- `Clerk/InsurerReconciliation.aspx.cs` & `Clerk/CompanyPaymentReconciliation.aspx.cs` (Insurer brokerage statement matching, `RconGrid`/`RconComm` variance tracking, `ib_doc_no` tagging)
- `Clerk/AgentEWalletTopUp.aspx.cs` & `Service.asmx.cs` (`GetAgentWalletBalance`, `InsertAppTransctiondetailsNew8` E-Wallet reservation/debit)

---

## 4. Stored Procedures Mapped
Audited in [`docs/migration/phase_8_payment_sp_mapping.md`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/docs/migration/phase_8_payment_sp_mapping.md) (`22` legacy stored procedures mapped):
- **Payment Instrument & Settlement SPs**: `Sp_InsertTransactionPayment`, `sp_GetTransactionPaymentByTransId`, `sp_UpdateTransactionPaidAndOutstanding`, `sp_DeleteTransactionPaymentById`
- **Cheque Deposit, Clearance & Bounce SPs**: `sp_UpdateChequeDepositStatus`, `sp_UpdateChequeClearanceStatus`, `sp_UpdateChequeBounceStatus`, `sp_InsertChequeBouncePenaltyAccount`, `sp_HoldCommissionOnChequeBounce`
- **Staged Proposal Approval Gate SPs**: `sp_UpdateCashierApproval`, `sp_UpdateAccountantApproval`, `sp_UpdateOwnerApproval`
- **Insurer Reconciliation SPs**: `sp_UpdateInsurerReconciliationMatch`, `sp_GetUnreconciledTransactions`, `sp_InsertInsurerReconciliationAccount`
- **Partner E-Wallet & Sub-Ledger SPs**: `sp_GetOrCreatePartnerWalletLedger`, `sp_GetPartnerWalletBalance`, `sp_InsertWalletTopUp`, `sp_LockPartnerWalletFunds`, `sp_ReleasePartnerWalletLock`, `sp_ConsumeOrDebitPartnerWallet`, `sp_RefundPartnerWallet`

---

## 5. Tables & Columns Verified
No physical schema changes or fake columns were introduced; Phase 8 operates on the verified physical tables in `reliable_insurance_dev`:
1. **`tbl_transactionpayment`** (`18` cols, PK `PaymentId`, FK-logical `TransanctionId`, `PaymentType`, `PaidAmount`, `docno`, `bankname`, `CashierApproval`, `AccountantApproval`, `OwnerApproval`, `Extra1`, `Extra2`, `isCompletePayment`, `isdeleted`).
2. **`tbl_transaction`** (`166` cols, PK `TransanctionId`, `PaidAmount`, `OutstandingAmount`, `TStatus`, `pendingStatus`, `Ischequeclearing`, `IsChequeCleared`, `ChequeBankStatus`, `CheqBankDate`, `CommissionPaid`, `RAPaymentStatus`, `CutNPay`, `EWalletAmountUsed`, `OnlinePaymentToCompany`, `IsRconDataMatch`, `RconGrid`, `RconComm`, `CompanySubmissionDocNo`, `CompanyChequeNo`, `IsCompanyChequeNo`, `ib_doc_no`, `IB_Recipt_Status`).
3. **`tbl_account`** (`23` cols, PK `AccountId`, `AccTransId`, `LedgerMId`, `amount`, `Narration`, `Extra1`, `Extra2`, `Doc_No`, `PaymentType`, `TransactionId`, `TransId`, `isdeleted`).
4. **`tbl_ledgermaster`** (`12` cols, PK `LedgerMId`, `LedgerTypeId`, `LedgerName`, `LedgerGroupId`, `ReferenceId`, `BranchId`, `isdeleted`).
5. **`tbl_transactionappnew`** (`64` cols, PK `TransId`, `CashPaidAmt`, `CashShortAmt`, `EWalletUsedamt`, `EwalletStatus`, `ChequeApprovalStatus`, `IsChashierApprove`, `IsAccountApproval`, `IsOwnerApprove`).
6. **`tbl_cutnpaycommpayable`** (`11` cols, PK `CutNPayCommPayId`, `TransactionId`, `CommPayable`, `Balance`, `Flag`, `Isdeleted`) & **`tbl_agentcommissionpayment`** (`20` cols, PK `AgentCommId`, `TransanctionId`, `PaymentStatus`, `Narration`, `isdeleted`).

---

## 6. Payment Mode Matrix
Verified in [`app/services/payment_engine.py`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/app/services/payment_engine.py) (`ALLOWED_PAYMENT_TYPES`):
| Payment Mode | Initial Instrument Status (`Extra1`) | `CashierApproval` | Sets `Ischequeclearing=1`? | Requires `docno` & `bankname`? |
|---|---|---|---|---|
| `CASH` | `RECEIVED` | `1` | No (`0`) | Optional |
| `ONLINE` | `RECEIVED` | `1` | No (`0`) | Optional |
| `NEFT` | `RECEIVED` | `1` | No (`0`) | Optional |
| `RTGS` | `RECEIVED` | `1` | No (`0`) | Optional |
| `UPI` | `RECEIVED` | `1` | No (`0`) | Optional |
| `CREDIT_CARD` | `RECEIVED` | `1` | No (`0`) | Optional |
| `DEBIT_CARD` | `RECEIVED` | `1` | No (`0`) | Optional |
| `CUTNPAY` | `RECEIVED` | `1` | No (`0`) | Optional |
| `EWALLET` | `RECEIVED` | `1` | No (`0`) | Optional |
| `DIRECT_TO_INSURER` | `RECEIVED` | `1` | No (`0`) | Optional |
| `CHEQUE` | `PENDING_CLEARANCE` | `0` | **Yes (`1`)** | **Mandatory (`422` if blank)** |
| `DD` | `PENDING_CLEARANCE` | `0` | **Yes (`1`)** | **Mandatory (`422` if blank)** |

---

## 7. Payment State Machine Summary
Documented in [`docs/migration/phase_8_payment_state_machine.md`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/docs/migration/phase_8_payment_state_machine.md):
- **Instrument States (`tbl_transactionpayment.Extra1`)**:
  - `RECEIVED` $\rightarrow$ `REVERSED`
  - `PENDING_CLEARANCE` $\rightarrow$ `DEPOSITED` $\rightarrow$ `CLEARED` $\rightarrow$ `BOUNCED` (late dishonor)
  - `PENDING_CLEARANCE` $\rightarrow$ `CLEARED` (direct clearance)
  - `PENDING_CLEARANCE` / `DEPOSITED` $\rightarrow$ `BOUNCED`
  - `PENDING_CLEARANCE` / `DEPOSITED` $\rightarrow$ `REVERSED`
- **Illegal Transitions (`409 Conflict`)**:
  - `BOUNCED` $\rightarrow$ `CLEARED`, `DEPOSITED`, or `BOUNCED` (double bounce blocked)
  - `REVERSED` $\rightarrow$ any state (double reversal blocked)
  - `CLEARED` $\rightarrow$ `DEPOSITED`

---

## 8. Cheque Lifecycle Summary
Documented in [`docs/migration/phase_8_cheque_lifecycle.md`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/docs/migration/phase_8_cheque_lifecycle.md):
1. **Receipt (`POST /api/v1/policies/book` or `POST /api/v1/policies/{id}/payments`)**:
   - `Extra1 = "PENDING_CLEARANCE"`, `CashierApproval = 0`, `AccountantApproval = 0`
   - `tbl_transaction`: `Ischequeclearing = 1`, `IsChequeCleared = 0`, `ChequeBankStatus = 0`
2. **Bank Deposit (`POST /api/v1/payments/{id}/deposit`)**:
   - `Extra1 = "DEPOSITED"`, `CashierApproval = 1`, `CashierApprovalDate = deposit_date`
   - `tbl_transaction`: `Ischequeclearing = 1`, `IsChequeCleared = 0`, `ChequeBankStatus = 0`, `CheqBankDate = deposit_date`
3. **Bank Clearance (`POST /api/v1/payments/{id}/clear`)**:
   - `Extra1 = "CLEARED"`, `CashierApproval = 1`, `AccountantApproval = 1`, `AccountantApprovalDate = clear_date`
   - When no other pending cheques remain on the policy: `Ischequeclearing = 0`, `IsChequeCleared = 1`, `ChequeBankStatus = 1`, `CheqBankDate = clear_date`; if `OutstandingAmount == 0.00`, `TStatus = "Booked"`, `pendingStatus = 0`, `RAPaymentStatus = "COMPLETE"`.

---

## 9. Cheque Bounce & Penalty Rules
Documented in [`docs/migration/phase_8_cheque_bounce.md`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/docs/migration/phase_8_cheque_bounce.md) and implemented in `PaymentEngineService.bounce_cheque`:
- **Payment Row**: `Extra1 = "BOUNCED"`, `isdeleted = "1"`, `isCompletePayment = 0`, `AccountantApproval = 2`.
- **Policy Reopening**:
  - $\text{PaidAmount}_{\text{new}} = \max(0.00, \text{PaidAmount}_{\text{old}} - C)$
  - $\text{OutstandingAmount}_{\text{new}} = \text{OutstandingAmount}_{\text{old}} + C + P_{\text{penalty}}$
  - `TStatus = "Pending"`, `pendingStatus = 1`, `IsActivePendingCash = 1`, `Ischequeclearing = 0`, `IsChequeCleared = 0`, `ChequeBankStatus = 2`, `CommissionPaid = 0`, `RAPaymentStatus = "BOUNCED"`.
- **Commission Hold**:
  - `tbl_cutnpaycommpayable.Flag = "HOLD_CHEQUE_BOUNCE"`
  - `tbl_agentcommissionpayment.PaymentStatus = 0.00`, `Narration = "HOLD: Cheque #<docno> Bounced"`
- **Double-Entry Accounting**:
  - Contra Reversal: `AccTransId = 2`, `Extra1 = "CHEQUE_BOUNCE_REVERSAL"`, `amount = -C`
  - Dishonor Penalty (when $P_{\text{penalty}} > 0$): `AccTransId = 4`, `Extra1 = "CHEQUE_BOUNCE_PENALTY"`, `amount = +P_{\text{penalty}}`

---

## 10. Payment Reversal / Refund Rules
Implemented in `PaymentEngineService.reverse_payment` (`POST /api/v1/payments/{id}/reverse`):
- Marks `tbl_transactionpayment` row `Extra1 = "REVERSED"`, `isdeleted = "1"`, `isCompletePayment = 0`.
- Recomputes `PaidAmount -= amount`, `OutstandingAmount += amount`, `TStatus = "Pending"`, `pendingStatus = 1`, `RAPaymentStatus = "PENDING"`.
- Posts contra receipt reversal in `tbl_account` (`AccTransId = 2`, `Extra1 = "PAYMENT_REVERSAL"`, `amount = -amount`).
- When `PaymentType == "EWALLET"` and `refund_to_wallet=True`, atomically credits the partner's E-Wallet sub-ledger (`AccTransId = 14`, `Extra1 = "WALLET_REFUND"`, `amount = +amount`).

---

## 11. Insurer Reconciliation Rules
Documented in [`docs/migration/phase_8_reconciliation.md`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/docs/migration/phase_8_reconciliation.md) and implemented in `PaymentEngineService.reconcile_policy`:
- Evaluates insurer brokerage statement (`reconciled_grid_percent` and/or `reconciled_comm_amount`) against `NetPermium` and booked `AgentCommAmt`:
  - $\text{Variance} = \text{round\_2dp}(\text{RconComm} - \text{AgentCommAmt})$
  - $|\text{Variance}| \le 1.00 \implies \text{IsRconDataMatch} = 1$ (`MATCHED`)
  - $|\text{Variance}| > 1.00 \text{ and allow\_partial\_match}=\text{True} \implies \text{IsRconDataMatch} = 2$ (`PARTIAL_VARIANCE`)
  - $|\text{Variance}| > 1.00 \text{ and allow\_partial\_match}=\text{False} \implies \text{HTTP } 422$
- Updates `tbl_transaction`: `IsRconDataMatch`, `RconGrid`, `RconComm`, `CompanySubmissionDocNo`, `CompanyChequeNo`, `IsCompanyChequeNo`, `ib_doc_no`, `IB_Recipt_Status`.
- Posts insurer brokerage reconciliation voucher in `tbl_account` (`AccTransId = 5`, `Extra1 = "INSURER_RECONCILIATION"`, `amount = +RconComm`).
- Prevents duplicate full reconciliation on the same `ib_doc_no` (`409 Conflict`).

---

## 12. E-Wallet & Lock / Release Rules
Documented in [`docs/migration/phase_8_wallet.md`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/docs/migration/phase_8_wallet.md) and implemented in `WalletService`:
- **Partner Sub-Ledger (`tbl_ledgermaster`)**:
  - `LedgerTypeId = 5` (`AGENT`), `LedgerTypeId = 6` (`FRANCHISE`), `ReferenceId = owner_id`.
- **Ledger Entries (`tbl_account`)**:
  - `AccTransId = 10` (`WALLET_TOPUP`, `+amount`)
  - `AccTransId = 11` (`WALLET_LOCK`, `-amount`; transitions to `WALLET_LOCK_RELEASED` on release or `WALLET_LOCK_CONSUMED` on policy debit)
  - `AccTransId = 12` (`WALLET_RELEASE`, `+amount` audit trail entry)
  - `AccTransId = 13` (`WALLET_DEBIT`, `-amount`)
  - `AccTransId = 14` (`WALLET_REFUND`, `+amount`)
- **Balance Invariant**:
  $$\text{SettledBalance} = \sum \text{amount}_{\text{AccTransId} \in \{10, 13, 14\}}, \quad \text{LockedBalance} = \sum |\text{amount}|_{\text{AccTransId}=11 \land \text{Extra1}=\text{'WALLET\_LOCK'}}$$
  $$\text{AvailableBalance} = \text{SettledBalance} - \text{LockedBalance} \ge 0.00$$

---

## 13. Commission & Accounting Interaction Summary
- **Cut & Pay (`tbl_cutnpaycommpayable`)**: Created with `Flag = "CUTNPAY"` during booking; automatically placed on hold (`Flag = "HOLD_CHEQUE_BOUNCE"`) upon cheque dishonor.
- **Agent Commission (`tbl_agentcommissionpayment`)**: Created with `PaymentStatus = 1.00` (when Cut & Pay active); automatically reset to `PaymentStatus = 0.00` with hold narration upon cheque dishonor.
- **Double-Entry Polarity (`tbl_account`)**:
  - `AccTransId = 1`: Policy Premium Receivable (`+FinalPremium`)
  - `AccTransId = 2`: Policy Payment Receipt (`+PaidAmount`) / Bounce or Reversal Contra (`-ReversedAmount`)
  - `AccTransId = 3`: Unclear Commission (`-NetCommission`)
  - `AccTransId = 4`: Cheque Bounce Penalty (`+PenaltyAmount`)
  - `AccTransId = 5`: Insurer Reconciliation Settlement (`+RconComm`)
  - `AccTransId = 10..14`: Partner E-Wallet Sub-Ledger Entries

---

## 14. Role / Branch / Principal Access Summary
Documented in [`docs/migration/phase_8_payment_access_matrix.md`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/docs/migration/phase_8_payment_access_matrix.md) and enforced in [`app/core/rbac.py`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/app/core/rbac.py):
- `PAYMENT_CLEARANCE_ROLES`: `ADMIN`, `SUPER ADMIN`, `BACK OFFICE`, `CASHIER`, `ACCOUNT`
- `PAYMENT_BOUNCE_REVERSAL_ROLES`: `ADMIN`, `SUPER ADMIN`, `BACK OFFICE`, `CASHIER`, `ACCOUNT`
- `RECONCILIATION_WRITE_ROLES`: `ADMIN`, `SUPER ADMIN`, `BACK OFFICE`, `ACCOUNT`
- `RECONCILIATION_READ_ROLES`: `ADMIN`, `SUPER ADMIN`, `BACK OFFICE`, `ACCOUNT`, `CASHIER`, `MIS_EXECUTIVE`, `ALL USER`
- `WALLET_ADMIN_WRITE_ROLES`: `ADMIN`, `SUPER ADMIN`, `BACK OFFICE`, `CASHIER`, `ACCOUNT`
- `WALLET_PARTNER_ROLES`: `ADMIN`, `SUPER ADMIN`, `BACK OFFICE`, `CASHIER`, `ACCOUNT`, `AGENT`, `FRANCHISE`, `SUB FRANCHISE`, `FRANCHISE ADMIN`
- **Principal Ownership Isolation**: `AGENT` and `FRANCHISE` callers can only view, lock, release, or debit their own `owner_id` (resolved server-side from `PrincipalContext`, never trusting spoofed IDs; cross-partner access returns `403 Forbidden`).

---

## 15. FastAPI Endpoints Implemented
Mounted via [`app/api/v1/endpoints/payments.py`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/app/api/v1/endpoints/payments.py) and [`app/api/v1/endpoints/policies.py`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/app/api/v1/endpoints/policies.py):
1. `GET /api/v1/policies/{transaction_id}/payments` — List payment instruments for a policy
2. `POST /api/v1/policies/{transaction_id}/payments` — Record subsequent payment instrument
3. `GET /api/v1/payments` — Paginated search/list of payment instruments
4. `GET /api/v1/payments/{payment_id}` — Retrieve single payment instrument
5. `POST /api/v1/payments/{payment_id}/deposit` — Transition cheque/DD to `DEPOSITED`
6. `POST /api/v1/payments/{payment_id}/clear` — Transition cheque/DD to `CLEARED` and finalize policy
7. `POST /api/v1/payments/{payment_id}/bounce` — Dishonor cheque/DD, assess penalty, reopen policy, hold commission
8. `POST /api/v1/payments/{payment_id}/reverse` — Reverse payment instrument and optionally refund E-Wallet
9. `GET /api/v1/reconciliation/policies` — List policies with reconciliation status filter
10. `POST /api/v1/reconciliation/policies/{transaction_id}/match` — Reconcile insurer brokerage statement
11. `GET /api/v1/wallets/{owner_type}/{owner_id}` — Get partner E-Wallet balances (`settled`, `locked`, `available`)
12. `GET /api/v1/wallets/{owner_type}/{owner_id}/transactions` — List partner E-Wallet ledger entries
13. `POST /api/v1/wallets/topup` — Credit partner E-Wallet (`AccTransId = 10`)
14. `POST /api/v1/wallets/lock` — Reserve/lock partner E-Wallet funds (`AccTransId = 11`)
15. `POST /api/v1/wallets/release` — Release active E-Wallet lock (`AccTransId = 12`)
16. `POST /api/v1/wallets/debit` — Consume lock or directly debit partner E-Wallet (`AccTransId = 13`)

---

## 16. Services / Repositories / Schemas Created or Updated
- **Created**:
  - [`app/schemas/payment.py`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/app/schemas/payment.py)
  - [`app/repositories/payment_engine.py`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/app/repositories/payment_engine.py)
  - [`app/services/payment_engine.py`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/app/services/payment_engine.py)
  - [`app/api/v1/endpoints/payments.py`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/app/api/v1/endpoints/payments.py)
- **Updated**:
  - [`app/core/rbac.py`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/app/core/rbac.py)
  - [`app/schemas/policy.py`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/app/schemas/policy.py)
  - [`app/services/policy_booking.py`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/app/services/policy_booking.py)
  - [`app/api/v1/endpoints/policies.py`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/app/api/v1/endpoints/policies.py)
  - [`app/api/v1/router.py`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/app/api/v1/router.py)

---

## 17. Atomicity & Rollback Design
Documented in [`docs/migration/phase_8_atomicity_idempotency.md`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/docs/migration/phase_8_atomicity_idempotency.md):
- Every write operation executes within a single database transaction (`await self.session.commit()` on success, `await self.session.rollback()` on any exception).
- Deterministic fault injection hooks (`simulate_failure_at`: `AFTER_PAYMENT_INSERT`, `BEFORE_LEDGER_COMMIT`, `AFTER_PAYMENT_UPDATE`, `AFTER_PAYMENT_BOUNCE`, `AFTER_TRANSACTION_REOPEN`, `DURING_ACCOUNTING`, `BEFORE_COMMIT`) verify 100% rollback with zero orphan rows.

---

## 18. Idempotency & Duplicate Prevention Design
- **Payment Idempotency**: `idempotency_key` stored as `IDEMP:<key>` in `tbl_transactionpayment.Extra2` (`409 Conflict` on duplicate).
- **Duplicate Active Cheque/DD Guard**: Blocks duplicate active `(TransanctionId, docno, bankname)` while allowing re-presentation or replacement after bounce/reversal.
- **Cheque Terminal State Guard**: Blocks double clearance, double bounce, or clearing a bounced cheque (`409 Conflict`).
- **Wallet Idempotency & Lock Guard**: Blocks duplicate `idempotency_key` in `tbl_account.Extra2`, duplicate active lock on the same `proposal_trans_id`, double release (`WALLET_LOCK_RELEASED`), and double consumption (`WALLET_LOCK_CONSUMED`).
- **Reconciliation Guard**: Blocks duplicate full match on the same `ib_doc_no` (`409 Conflict`).

---

## 19. Concurrency Test Results
Verified in [`tests/integration/test_phase8_wallet_reconciliation_concurrency.py`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/tests/integration/test_phase8_wallet_reconciliation_concurrency.py):
- **100 Concurrent Wallet Operations Stress Test (`test_100_concurrent_wallet_operations_never_go_negative`)**:
  - Initial Balance: `25,000.00` (`50` units of `500.00`).
  - Workload: `100` concurrent HTTP requests (`50` `POST /api/v1/wallets/debit` + `50` `POST /api/v1/wallets/lock` of `500.00` each).
  - Locking Mechanism: Process-level `_WALLET_WRITE_LOCK` + InnoDB `SELECT ... FOR UPDATE` on `tbl_ledgermaster` and current locking read (`with_for_update()`, `populate_existing=True`) on `tbl_account` in `compute_wallet_balances`.
  - Result: **Exactly `50` operations succeeded (`201 Created`), `50` operations rejected (`422 Unprocessable Entity`), final `available_balance == 0.00` (`0` negative balances)**.

---

## 20. Golden Parity Summary (25 Cases)
Documented in [`docs/migration/phase_8_golden_parity.md`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/docs/migration/phase_8_golden_parity.md) and verified in [`tests/integration/test_phase8_golden_parity.py`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/tests/integration/test_phase8_golden_parity.py):
- **Cases `P8-01` through `P8-25`**: **25 / 25 PASS (`100%`)**
- **Maximum Monetary Discrepancy**: **`0.00`** across all `PaidAmount`, `OutstandingAmount`, `CutNPay`, `EWalletAmountUsed`, `RconGrid`, `RconComm`, `tbl_account.amount`, `settled_balance`, `locked_balance`, and `available_balance` assertions.

---

## 21. E2E Test Summary
Verified in [`tests/integration/test_phase8_e2e.py`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/tests/integration/test_phase8_e2e.py) (`test_phase8_complete_cross_phase_e2e_journey`):
- Exercises the unbroken 10-step cross-phase flow:
  1. `POST /api/v1/customers` (`TEST_CUSTOMER_001`)
  2. `POST /api/v1/customers/{id}/vehicles` (`TEST_VEHICLE_001`)
  3. `POST /api/v1/quotations/self` + `GET /api/v1/quotations/self/{id}/policy-prefill` (`TEST_QUOTATION_001`)
  4. `POST /api/v1/wallets/topup` (`15,000.00`)
  5. `POST /api/v1/policies/proposals` + `POST /api/v1/wallets/lock` (`3,000.00`) + Cashier/Accountant approvals
  6. `POST /api/v1/policies/book` (`TEST_POLICY_001_P8_E2E` consuming wallet lock + partial cash + cheque)
  7. `POST /api/v1/policies/{id}/payments` (UPI balance payment)
  8. `POST /api/v1/payments/{id}/deposit` $\rightarrow$ `POST /api/v1/payments/{id}/bounce` (`+500.00` penalty, policy reopened, commission held)
  9. `POST /api/v1/policies/{id}/payments` (Replacement cheque `5,500.00`) $\rightarrow$ `POST /api/v1/payments/{id}/clear` (Policy finalized to `Booked`)
  10. `POST /api/v1/reconciliation/policies/{id}/match` (Insurer brokerage reconciliation matched, `AccTransId = 5` posted)

---

## 22. Full Test Counts (Phase 8 + Regression)
- **Phase 8 New Tests**: `38` passed (`24` unit tests + `14` integration, concurrency, golden parity, and E2E tests covering `25` golden parity scenarios)
- **Phase 1–7 Regression Tests**: `205` passed
- **Total Repository Test Suite**: **`243 passed in 65.94s` (`0` failures, `0` errors)**

---

## 23. Known Legacy Limitations Preserved Intentionally
- Typo column names (`TransanctionId`, `Ischequeclearing`, `IsChashierApprove`, `IB_Recipt_Status`, `NetPermium`, `ODPermium`, `TPPermium`) preserved in SQLAlchemy models while exposing clean snake_case REST API fields.
- Mixed soft-delete conventions (`isdeleted = "0"`/`"1"` string on `tbl_transaction` and `tbl_transactionpayment` vs `isdeleted = 0`/`1` integer on `tbl_account` and `tbl_cutnpaycommpayable`) preserved.
- Zero physical foreign keys (`0` FKs in MySQL) compensated by application-layer row-locking and unit-of-work transaction boundaries.

---

## 24. Security / Financial Integrity Improvements Over Legacy
- Server-side RBAC role gates on all 16 payment, cheque, reconciliation, and wallet endpoints (`GAP-5F-01` class fix).
- Server-side `PrincipalContext` ownership enforcement preventing `AGENT` or `FRANCHISE` users from viewing, locking, or debiting another partner's wallet (`GAP-5F-03` class fix).
- Row-locked (`SELECT ... FOR UPDATE`) wallet balance calculation preventing race-condition overdrafts under 100-way concurrency.
- Single unit-of-work transactions across `tbl_transactionpayment`, `tbl_transaction`, `tbl_cutnpaycommpayable`, `tbl_agentcommissionpayment`, and `tbl_account`.

---

## 25. Unsupported / Deferred Items
- Bulk Excel/CSV bank statement file upload parsing (deferred to Phase 11/14 Documents & Exports; API-level reconciliation is complete).
- Bulk commission payout disbursement voucher generation across multiple agents (scheduled for Phase 9 Commission & Accounting).

---

## 26. Exact Commands Executed
```powershell
pytest tests/unit/test_phase8_payment_calculations.py tests/integration/test_phase8_payment_cheque_api.py tests/integration/test_phase8_wallet_reconciliation_concurrency.py tests/integration/test_phase8_golden_parity.py tests/integration/test_phase8_e2e.py -v
pytest -q
```

---

## 27. Exact Files Created
1. `docs/migration/phase_8_payment_legacy_audit.md`
2. `docs/migration/phase_8_payment_sp_mapping.md`
3. `docs/migration/phase_8_payment_state_machine.md`
4. `docs/migration/phase_8_cheque_lifecycle.md`
5. `docs/migration/phase_8_cheque_bounce.md`
6. `docs/migration/phase_8_reconciliation.md`
7. `docs/migration/phase_8_wallet.md`
8. `docs/migration/phase_8_payment_access_matrix.md`
9. `docs/migration/phase_8_api_contract.md`
10. `docs/migration/phase_8_atomicity_idempotency.md`
11. `docs/migration/phase_8_golden_parity.md`
12. `docs/migration/phase_8_final_report.md`
13. `app/schemas/payment.py`
14. `app/repositories/payment_engine.py`
15. `app/services/payment_engine.py`
16. `app/api/v1/endpoints/payments.py`
17. `tests/unit/test_phase8_payment_calculations.py`
18. `tests/integration/test_phase8_payment_cheque_api.py`
19. `tests/integration/test_phase8_wallet_reconciliation_concurrency.py`
20. `tests/integration/test_phase8_golden_parity.py`
21. `tests/integration/test_phase8_e2e.py`

---

## 28. Exact Files Modified
1. `app/core/rbac.py`
2. `app/schemas/policy.py`
3. `app/services/policy_booking.py`
4. `app/api/v1/endpoints/policies.py`
5. `app/api/v1/router.py`
6. `docs/migration/migration_status.md`

---

## 29. Risks & Mitigations
- **Risk**: MySQL `REPEATABLE READ` snapshot isolation returning stale `tbl_account` rows when a session opens during `get_current_user` before acquiring the wallet write lock.
  - **Mitigation**: Implemented `with_for_update()` + `execution_options(populate_existing=True)` in `PaymentEngineRepository.compute_wallet_balances(..., for_update=True)` and verified with the 100-concurrent-request stress test.
- **Risk**: Dishonored cheque leaving Cut & Pay or Agent Commission rows marked payable.
  - **Mitigation**: `bounce_cheque` atomically sets `tbl_cutnpaycommpayable.Flag = "HOLD_CHEQUE_BOUNCE"`, `tbl_agentcommissionpayment.PaymentStatus = 0.00`, and `tbl_transaction.CommissionPaid = 0` in the same transaction.

---

## 30. Readiness Assessment for Phase 9 (Commission & Accounting Engine)
- All policy booking (`AccTransId = 1, 2, 3`), cheque bounce/penalty (`AccTransId = 2, 4`), insurer reconciliation (`AccTransId = 5`), and partner E-Wallet (`AccTransId = 10..14`) ledger entries are in place and verified.
- The codebase is ready for **Phase 9 — Commission & Accounting Engine** upon user approval.

---

## 31. Final Verification Checklist
- [x] Stage A 10 Audit & Design Documents completed
- [x] Stage B FastAPI Schemas, Repositories, Services, RBAC, and 16 Endpoints implemented
- [x] Stage C 25 Golden Parity Cases (`P8-01` .. `P8-25`) verified with `0.00` discrepancy
- [x] Stage C 100 Concurrent Wallet Operations verified with `0` negative balances
- [x] Stage C Cross-Phase E2E Journey verified
- [x] Full Regression Suite (`243 passed`) green
- [x] Zero production database connections (`brahmainsurance` untouched)

---

## 32. Phase 8 Sign-Off
**PHASE 8 COMPLETE — VERIFIED PARITY**
