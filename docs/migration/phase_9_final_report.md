# Phase 9 Final Migration Report — Commission & Accounting Engine

---

## 1. PHASE 9 STATUS
- **Phase**: Phase 9 — Commission & Accounting Engine
- **Status**: **COMPLETED — VERIFIED PARITY (STRICT STOP)**
- **Execution Stages Completed**:
  - **Stage A**: Legacy Commission, TDS, Cut & Pay, Payout, Reversal, Chart of Accounts, Ledger Statement, Voucher & Trial Balance Audit + Design + API Contract (`13` specification documents in `docs/migration/`)
  - **Stage B**: Local FastAPI Implementation (`app/core/rbac.py`, `app/schemas/commission_accounting.py`, `app/repositories/commission_accounting.py`, `app/services/commission_accounting.py`, `app/services/payment_engine.py`, `app/services/policy_booking.py`, `app/api/v1/endpoints/commission_accounting.py`, `app/api/v1/router.py`)
  - **Stage C**: Unit, Integration, RBAC/Branch/Principal Isolation, Atomicity, Idempotency, 100-Request Concurrency Stress, Golden Parity (`C9-01` .. `C9-30`, `0.00` discrepancy), Cross-Phase E2E (`Phases 5 -> 6 -> 7 -> 8 -> 9`), and Full Regression Verification (`275/275` passing)
  - **Stage D**: Final Report & Strict Stop

---

## 2. PRODUCTION SAFETY CONFIRMATION
- **Zero Production Runtime / Test Connections**: All Phase 9 implementation, synthetic data generation, unit tests, integration tests, concurrency stress tests, golden parity tests, and cross-phase E2E tests executed exclusively against the local development database (`localhost:3306/reliable_insurance_dev`) with `APP_ENV=testing`.
- **Zero Production Data Copied or Seeded**: No rows from `brahmainsurance` were copied, exported, imported, or seeded. Every customer (`TEST_CUSTOMER_001`), vehicle (`TEST_VEHICLE_001`), quotation (`TEST_QUOTATION_001`), policy (`TEST_POLICY_001`), commission record (`TEST_COMMISSION_001`), payout (`TEST_PAYOUT_001`), ledger (`TEST_LEDGER_001`), and voucher (`TEST_VOUCHER_001`) was synthetically generated in `reliable_insurance_dev`.
- **Zero Schema Drift**: No physical columns were altered or dropped; existing `tbl_transaction`, `tbl_agentcommissionpayment`, `tbl_franchisecommission`, `tbl_cutnpaycommpayable`, `tbl_ledgermaster`, and `tbl_account` schemas were preserved with 100% column fidelity.

---

## 3. LEGACY ENTRY POINTS AUDITED
1. `Clerk/PolicyTransactionNew.aspx.cs` & `Clerk/PE_TransactionEntry.aspx.cs` — Policy underwriting commission calculation, multi-bucket (`OD`, `Net`, `Extra`) breakdown, 5% TDS deduction, and Cut & Pay deduction at policy booking.
2. `Clerk/AgentCommissionPayment.aspx.cs` & `Clerk/CommissionPaymentNew.aspx.cs` — Agent commission payable queue, approval (`PaymentStatus = 3.00`), partial/full disbursement (`PaymentStatus = 2.00 / 1.00`), and `tbl_account` (`AccTransId = 6`) posting.
3. `Clerk/FranchiseCommission.aspx.cs` & `Clerk/FranchiseCommissionPayment.aspx.cs` — Franchise overriding commission (`Franchisecomm_OD/Net/Extra`), `ProfitofNetCommision` spread calculation, and `FCommissionPaid` disbursement tracking.
4. `Clerk/CutNPayCommPayable.aspx.cs` — Upfront Cut & Pay deduction tracking (`tbl_cutnpaycommpayable`) and `HOLD_CHEQUE_BOUNCE` hold/release workflow.
5. `Clerk/LedgerMaster.aspx.cs`, `Clerk/VoucherEntry.aspx.cs`, `Clerk/AccountStatement.aspx.cs`, and `Clerk/TrialBalance.aspx.cs` — Chart of Accounts (`tbl_ledgermaster`), double-entry journal/contra/payment/receipt vouchers, running-balance ledger statements, and Trial Balance reporting.
6. `App_Code/DAL_Operations.cs` & `Service.asmx.cs` — Underlying ADO.NET stored procedure calls and transaction wrappers.

---

## 4. COMMISSION & ACCOUNTING STORED PROCEDURES MAPPED
Documented in [`phase_9_commission_sp_mapping.md`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/docs/migration/phase_9_commission_sp_mapping.md):
- **Agent Commission SPs**: `sp_InsertAgentCommissionPayment`, `sp_UpdateAgentCommissionPayment`, `sp_SelectAgentCommissionPayableByAgentId`, `sp_ApproveAgentCommissionPayable`, `sp_GetAgentCommissionSummary`
- **Franchise Commission SPs**: `sp_InsertFranchiseCommission`, `sp_UpdateFranchiseCommission`, `sp_PayFranchiseCommission`, `sp_SelectFranchiseCommissionPayable`
- **Cut & Pay SPs**: `sp_InsertCutNPayCommPayable`, `sp_UpdateCutNPayCommPayableFlag`, `sp_SelectCutNPayByTransactionId`
- **Payout & Reversal SPs**: `sp_InsertCommissionPayoutAccount`, `sp_ReverseCommissionPayout`, `sp_GetMaxAccountDocNo`
- **Ledger, Voucher & Trial Balance SPs**: `sp_InsertLedgerMaster`, `sp_SelectLedgerMaster`, `sp_InsertAccountEntry`, `sp_SelectAccountStatementByLedgerId`, `sp_GetTrialBalance`

---

## 5. PHYSICAL TABLES & COLUMNS VERIFIED
| Physical Table | Primary Key | Column Count | Key Phase 9 Financial & Status Columns |
|---|---|---|---|
| `tbl_transaction` | `TransanctionId` | `166` | `ODPermium`, `TPPermium`, `NetPermium`, `Amount`, `AgentComm`, `AgentComm_OD`, `AgentCommAmt_OD`, `TdsAmt_OD`, `NetCommission_OD`, `AgentComm_Net`, `AgentCommAmt_Net`, `TdsAmt_Net`, `NetCommission_Net`, `AgentComm_Extra`, `AgentCommAmt_Extra`, `TdsAmt_Extra`, `NetCommission_Extra`, `AgentCommAmt`, `tdsPercent`, `TdsAmt`, `NetCommission`, `CutNPay`, `CommissionPaid`, `FranchiseCommPaid`, `FranchisePaymentDocNo`, `OutstandingAmount`, `Ischequeclearing`, `ChequeBankStatus`, `IsRconDataMatch` |
| `tbl_agentcommissionpayment` | `AgentCommId` | `20` | `TransanctionId`, `PremiumAmount`, `totalCommision`, `NetCommission`, `NetCommission_OD`, `NetCommission_Net`, `NetCommission_Extra`, `AdvAmt`, `NetAmount`, `PaymentStatus` (`0.00`/`1.00`/`2.00`/`3.00`), `Narration`, `Extra1` (`AgentId`), `Extra2` (`TdsAmt`), `isdeleted` (`"0"`/`"1"`) |
| `tbl_franchisecommission` | `FranchiseCommId` | `29` | `TransanctionId`, `FranchiseId`, `AgentId`, `tat` (TDS %), `Franchisecomm`, `FranchiseCommAmt`, `FranchiseTdsAmt`, `FranchiseNetComm`, `FCommissionPaid`, `Franchisecomm_OD/Net/Extra`, `FranchiseCommAmt_OD/Net/Extra`, `FranchiseTdsAmt_OD/Net/Extra`, `FranchiseNetComm_OD/Net/Extra`, `ProfitofNetCommision`, `isdeleted` (`0`/`1`) |
| `tbl_cutnpaycommpayable` | `CutNPayCommPayId` | `11` | `TransactionId`, `PolicyNo`, `CustomerId`, `AgentId`, `SalesExId`, `Balance`, `CommPayable`, `Flag` (`CUTNPAY_DEDUCTED` / `HOLD_CHEQUE_BOUNCE` / `SETTLED`), `Isdeleted` (`0`/`1`) |
| `tbl_ledgermaster` | `LedgerMId` | `5` | `LedgerName`, `LedgerTypeId` (`1`=Asset, `2`=Liability, `3`=Income, `4`=Expense, `5`=Equity), `LedgerGId`, `isdeleted` (`0`/`1`) |
| `tbl_account` | `AccountId` | `23` | `AccTransId` (`1..14`), `TransactionType`, `Doc_No`, `TransactionDate`, `LedgerMId`, `amount` (signed `Decimal`), `Narration`, `ReferenceCustId`, `ReferenceAgentId`, `BranchId`, `PaymentType`, `Extra1`, `Extra2`, `TransactionId`, `isdeleted` (`0`/`1`) |

---

## 6. COMMISSION STATE MACHINE SUMMARY
Documented in [`phase_9_commission_state_machine.md`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/docs/migration/phase_9_commission_state_machine.md):
- **`0.00` (`UNPAID_PAYABLE`)**: Initial state when `NetAmount > 0.00` and `AdvAmt == 0.00`.
- **`3.00` (`APPROVED`)**: Explicitly approved by `ACCOUNT` / `ACCOUNT HEAD` / `SHREYANSH OWNER` / `ADMIN` (`POST /api/v1/commissions/{tx_id}/approve`).
- **`2.00` (`PARTIALLY_PAID`)**: Partial settlement via upfront Cut & Pay deduction (`0 < CutNPay < NetCommission`) or partial cash payout (`0 < AdvAmt < NetCommission`).
- **`1.00` (`PAID`)**: Fully settled (`AdvAmt == NetCommission`, `NetAmount == 0.00`). When both Agent and Franchise remaining payables reach `0.00`, `tbl_transaction.CommissionPaid` transitions to `1`.
- **Hold Overlay (`HOLD_CHEQUE_BOUNCE`)**: Triggered on cheque dishonor (`ChequeBankStatus = 2`); automatically released when replacement payment clears and `OutstandingAmount == 0.00` with `Ischequeclearing == 0`.

---

## 7. AGENT COMMISSION SUMMARY
Documented in [`phase_9_agent_commission_and_tds.md`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/docs/migration/phase_9_agent_commission_and_tds.md):
- Multi-bucket component calculation (`ROUND_HALF_UP` to `0.01` at every step):
  - **OD Bucket**: $\text{AgentCommAmt\_OD} = \text{round\_2dp}(\text{ODPermium} \times \text{AgentComm\_OD} / 100)$
  - **Net Bucket**: $\text{AgentCommAmt\_Net} = \text{round\_2dp}(\text{NetBase} \times \text{AgentComm\_Net} / 100)$
  - **Extra Bucket**: $\text{AgentCommAmt\_Extra} = \text{round\_2dp}(\text{ODPermium} \times \text{AgentComm\_Extra} / 100)$
  - **Flat Fallback**: When component rates are `0.00` and headline `agent_comm_pct > 0.00`, applies headline rate on `ODPermium` (or `NetPermium` for TP-only policies).

---

## 8. FRANCHISE COMMISSION SUMMARY
Documented in [`phase_9_franchise_commission.md`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/docs/migration/phase_9_franchise_commission.md):
- Computes `FranchiseCommAmt_OD`, `FranchiseCommAmt_Net`, `FranchiseCommAmt_Extra`, per-bucket TDS at `tat` %, and `FranchiseNetComm`.
- **Overriding Spread (`ProfitofNetCommision`)**:
  $$\text{ProfitofNetCommision} = \text{round\_2dp}(\text{FranchiseNetComm} - \text{AgentNetCommission})$$
- Tracks disbursements in `FCommissionPaid` with remaining payable $\max(0.00, \text{FranchiseNetComm} - \text{FCommissionPaid})$.

---

## 9. TDS SUMMARY
- Per-bucket TDS deduction (`tdsPercent` for Agent, `tat` for Franchise; default `5.00%`):
  - $\text{TdsAmt\_OD} = \text{round\_2dp}(\text{AgentCommAmt\_OD} \times \text{tdsPercent} / 100)$
  - $\text{TdsAmt\_Net} = \text{round\_2dp}(\text{AgentCommAmt\_Net} \times \text{tdsPercent} / 100)$
  - $\text{TdsAmt\_Extra} = \text{round\_2dp}(\text{AgentCommAmt\_Extra} \times \text{tdsPercent} / 100)$
  - $\text{NetCommission} = \text{GrossCommission} - \text{TdsAmt}$

---

## 10. CUT & PAY SUMMARY
Documented in [`phase_9_cut_and_pay.md`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/docs/migration/phase_9_cut_and_pay.md):
- Upfront commission deduction at booking (`cutnpay_enabled = True`):
  - Default full Cut & Pay deducts full `AgentNetCommission` (`PaymentStatus = 1.00`, `NetAmount = 0.00`).
  - Partial Cut & Pay (`0 < cutnpay_amount < AgentNetCommission`) sets `AdvAmt = cutnpay_amount`, `NetAmount = AgentNetCommission - cutnpay_amount`, `PaymentStatus = 2.00`.
  - Rejects `cutnpay_amount > AgentNetCommission` with HTTP `422 Unprocessable Entity`.
  - Reduces customer required collection to $\text{FinalPremium} - \text{CutNPayDeductedAmount}$.

---

## 11. COMMISSION PAYOUT SUMMARY
Documented in [`phase_9_commission_payout_and_reversal.md`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/docs/migration/phase_9_commission_payout_and_reversal.md):
- **6-Gate Eligibility Verification**:
  1. Policy active (`isdeleted == "0"` and `TStatus != "Cancelled"`)
  2. Policy fully settled (`OutstandingAmount == 0.00`)
  3. No cheque pending bank clearance (`Ischequeclearing == 0`)
  4. No dishonored cheque (`ChequeBankStatus != 2`)
  5. No `HOLD_*` flag on `tbl_cutnpaycommpayable` or `tbl_agentcommissionpayment`
  6. Positive remaining payable balance (`NetAmount > 0.00` for Agent or `FranchiseNetComm - FCommissionPaid > 0.00` for Franchise)
- **Atomic Execution**: Updates `AdvAmt`/`NetAmount`/`PaymentStatus` (or `FCommissionPaid`), updates `tbl_transaction.CommissionPaid`, allocates a unique `Doc_No` (`VCH-CPAY-{doc_no}`), and posts balanced double-entry rows in `tbl_account` (`AccTransId = 6`: Debit Commission Payable `+Amount`, Credit Bank/Cash `-Amount`).

---

## 12. COMMISSION REVERSAL / RECOVERY SUMMARY
- **Payout Reversal (`POST /api/v1/commission-payouts/{payout_id}/reverse`)**:
  - Verifies payout is not already reversed (idempotent `409 Conflict` on second reversal).
  - Restores `AdvAmt` and `NetAmount` on `tbl_agentcommissionpayment` (or decrements `FCommissionPaid` on `tbl_franchisecommission`), resets `PaymentStatus` (`2.00` if prior partial payment > 0 else `3.00`), and resets `tbl_transaction.CommissionPaid = 0`.
  - Posts contra double-entry voucher (`AccTransId = 7`, `VCH-CREV-{rev_doc_no}`): Debit Bank/Cash (`+Amount`), Credit Commission Payable (`-Amount`).
- **Policy Cancellation & Cheque Bounce**:
  - Policy cancellation soft-deletes commission rows and `AccTransId = 3` rows (`isdeleted = 1`).
  - Cheque bounce marks `Flag = "HOLD_CHEQUE_BOUNCE"` and `CommissionPaid = 0`; subsequent full clearance releases the hold.

---

## 13. ACCOUNTING / LEDGER SUMMARY
Documented in [`phase_9_accounting_ledger_and_trial_balance.md`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/docs/migration/phase_9_accounting_ledger_and_trial_balance.md):
- **Chart of Accounts (`tbl_ledgermaster`)**: Supports creating and listing master ledgers across 5 canonical types (`1=ASSET`, `2=LIABILITY`, `3=INCOME`, `4=EXPENSE`, `5=EQUITY`) plus auto-provisioned system ledgers (`101..502`).
- **Signed Amount Polarity in `tbl_account`**:
  - `amount > 0.00` = **DEBIT (`DR`)**
  - `amount < 0.00` = **CREDIT (`CR`)**
- **Running-Balance Ledger Statement (`GET /api/v1/accounting/ledgers/{id}/entries`)**: Computes `opening_balance` prior to `from_date`, chronological `debit_amount`, `credit_amount`, `signed_amount`, cumulative `running_balance`, and `closing_balance`.

---

## 14. TRIAL BALANCE SUMMARY
- Aggregates all active (`isdeleted = 0`) `tbl_account` entries grouped by `LedgerMId`.
- Pairs single-sided operational entries from Phases 7 & 8 (`AccTransId in {1, 2, 3, 4, 5, 10, 11, 12, 13, 14}`) with deterministic virtual Double-Entry Control Accounts (`990001..990004`) while preserving exact physical `tbl_account` row counts for Phase 7 & Phase 8 regression compatibility.
- Enforces:
  $$\sum \text{Gross Debit} = \sum \text{Gross Credit}, \quad \sum \text{Net Debit} = \sum \text{Net Credit}, \quad \text{Variance} = 0.00$$

---

## 15. VOUCHER SUMMARY
Documented in [`phase_9_vouchers.md`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/docs/migration/phase_9_vouchers.md):
- Supports `JOURNAL`, `PAYMENT`, `RECEIPT`, and `CONTRA` vouchers (`POST /api/v1/accounting/vouchers`, `AccTransId = 8`).
- Enforces $\ge 2$ lines, at least one `DR` and one `CR` line, and $\sum \text{DR} == \sum \text{CR}$ (`422 Unprocessable Entity` on any imbalance).
- Supports atomic Voucher Reversal (`POST /api/v1/accounting/vouchers/{doc_no}/reverse`, `AccTransId = 9`) posting exact opposite-polarity lines under a new `Doc_No`.

---

## 16. ROLE / BRANCH / PRINCIPAL ACCESS MATRIX SUMMARY
Documented in [`phase_9_access_matrix.md`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/docs/migration/phase_9_access_matrix.md) and enforced in `app/core/rbac.py`:
- **Commission Approval (`COMMISSION_APPROVAL_ROLES`)**: Global Admins + `ACCOUNT`, `ACCOUNT HEAD`, `SHREYANSH OWNER`.
- **Commission Payout & Reversal (`COMMISSION_PAYOUT_WRITE_ROLES`)**: Global Admins + `ACCOUNT`, `ACCOUNT HEAD`, `CASHIER`, `SHREYANSH OWNER`.
- **Accounting Voucher Write (`ACCOUNTING_VOUCHER_WRITE_ROLES`)**: Global Admins + `ACCOUNT`, `ACCOUNT HEAD`, `CASHIER`, `SHREYANSH OWNER`.
- **Trial Balance Read (`TRIAL_BALANCE_READ_ROLES`)**: Global Admins + Finance/Executive roles (`ACCOUNT`, `ACCOUNT HEAD`, `CASHIER`, `SHREYANSH OWNER`, `OPERATIONAL HEAD`, `HO OPERATION`, `PANKAJ SIR`, `MANOJ SIR`, `HR`, `MIS_USER`).
- **Principal & Branch Isolation**: `AGENT` roles can only view their own `AgentId` commission records and partner statements; `FRANCHISE` roles can only view their own `FranchiseId` records; branch-scoped staff are isolated to their `BranchId`.

---

## 17. API ENDPOINTS IMPLEMENTED
Mounted under `/api/v1` (`18` endpoints):
1. `POST /api/v1/commissions/preview` — Stateless commission, TDS, Cut & Pay & Franchise spread preview
2. `POST /api/v1/commissions/calculate` — Evaluate or recalculate policy commission rows
3. `GET /api/v1/commissions/payables` — List unpaid/partially-paid Agent & Franchise commission payables
4. `GET /api/v1/commissions` — List policy commission records with filters & pagination
5. `GET /api/v1/commissions/{transaction_id}` — Get detailed policy commission breakdown & eligibility
6. `POST /api/v1/commissions/{transaction_id}/approve` — Approve Agent/Franchise commission payable (`PaymentStatus = 3.00`)
7. `POST /api/v1/commission-payouts` — Execute atomic Agent or Franchise commission payout (`AccTransId = 6`)
8. `GET /api/v1/commission-payouts` — List commission payout vouchers
9. `GET /api/v1/commission-payouts/{payout_id}` — Get commission payout voucher & per-policy allocations
10. `POST /api/v1/commission-payouts/{payout_id}/reverse` — Reverse commission payout (`AccTransId = 7`)
11. `POST /api/v1/accounting/ledgers` — Create master ledger in `tbl_ledgermaster`
12. `GET /api/v1/accounting/ledgers` — List Chart of Accounts (`tbl_ledgermaster`)
13. `GET /api/v1/accounting/ledgers/{ledger_m_id}/entries` — Get chronological running-balance ledger statement
14. `GET /api/v1/accounting/accounts/{partner_type}/{partner_id}/statement` — Get partner commission & wallet sub-ledger statement
15. `POST /api/v1/accounting/vouchers` — Post balanced double-entry voucher (`AccTransId = 8`)
16. `GET /api/v1/accounting/vouchers` — List accounting vouchers
17. `GET /api/v1/accounting/vouchers/{doc_no}` — Get voucher by `Doc_No`
18. `POST /api/v1/accounting/vouchers/{doc_no}/reverse` — Reverse double-entry voucher (`AccTransId = 9`)
19. `GET /api/v1/accounting/trial-balance` — Compute Trial Balance with zero-variance verification

---

## 18. FILES CREATED
1. `docs/migration/phase_9_commission_legacy_audit.md`
2. `docs/migration/phase_9_commission_sp_mapping.md`
3. `docs/migration/phase_9_commission_state_machine.md`
4. `docs/migration/phase_9_agent_commission_and_tds.md`
5. `docs/migration/phase_9_franchise_commission.md`
6. `docs/migration/phase_9_cut_and_pay.md`
7. `docs/migration/phase_9_commission_payout_and_reversal.md`
8. `docs/migration/phase_9_accounting_ledger_and_trial_balance.md`
9. `docs/migration/phase_9_vouchers.md`
10. `docs/migration/phase_9_access_matrix.md`
11. `docs/migration/phase_9_api_contract.md`
12. `docs/migration/phase_9_atomicity_idempotency_concurrency.md`
13. `docs/migration/phase_9_golden_parity.md`
14. `docs/migration/phase_9_final_report.md`
15. `app/schemas/commission_accounting.py`
16. `app/repositories/commission_accounting.py`
17. `app/services/commission_accounting.py`
18. `app/api/v1/endpoints/commission_accounting.py`
19. `tests/unit/test_phase9_commission_accounting_calculations.py`
20. `tests/integration/test_phase9_commission_payout_api.py`
21. `tests/integration/test_phase9_accounting_voucher_concurrency.py`
22. `tests/integration/test_phase9_golden_parity.py`
23. `tests/integration/test_phase9_e2e.py`

---

## 19. FILES MODIFIED
1. `app/core/rbac.py` — Added Phase 9 role sets (`COMMISSION_CALCULATE_ROLES`, `COMMISSION_APPROVAL_ROLES`, `COMMISSION_PAYOUT_WRITE_ROLES`, `COMMISSION_READ_ROLES`, `ACCOUNTING_VOUCHER_WRITE_ROLES`, `ACCOUNTING_READ_ROLES`, `TRIAL_BALANCE_READ_ROLES`).
2. `app/services/payment_engine.py` — Updated `clear_cheque()` to release `HOLD_CHEQUE_BOUNCE` flags on `tbl_cutnpaycommpayable` and `tbl_agentcommissionpayment` when `OutstandingAmount == 0.00` and `Ischequeclearing == 0`.
3. `app/services/policy_booking.py` — Updated `record_payment()` to release `HOLD_CHEQUE_BOUNCE` flags when non-cheque replacement payment settles `OutstandingAmount == 0.00` with `Ischequeclearing == 0`.
4. `app/api/v1/router.py` — Registered `commissions_router`, `commission_payouts_router`, and `accounting_router`.
5. `docs/migration/migration_status.md` — Updated Phase 9 status to COMPLETED — VERIFIED PARITY.

---

## 20. ALEMBIC MIGRATIONS APPLIED (IF ANY)
- **None required (`0` new migrations)**: All 6 physical tables (`tbl_transaction`, `tbl_agentcommissionpayment`, `tbl_franchisecommission`, `tbl_cutnpaycommpayable`, `tbl_ledgermaster`, `tbl_account`) were already present at Alembic head `7bfd3202dcf7` with 100% verified column parity.

---

## 21. ATOMICITY & ROLLBACK STRATEGY
- Every write operation (`calculate_or_sync_policy_commission`, `approve_policy_commission`, `create_commission_payout`, `reverse_commission_payout`, `create_voucher`, `reverse_voucher`) executes inside a single SQLAlchemy `AsyncSession` transaction boundary with `try ... await self.session.commit() except Exception: await self.session.rollback()`.
- Verified via deterministic fault injection (`simulate_failure_at="AFTER_COMMISSION_UPDATE"`), confirming that a failure after commission row mutation and before `tbl_account` voucher posting rolls back `AdvAmt`, `NetAmount`, `PaymentStatus`, and `CommissionPaid` with zero orphan rows.

---

## 22. IDEMPOTENCY STRATEGY
- **Client Idempotency Keys**: `POST /api/v1/commission-payouts` and `POST /api/v1/accounting/vouchers` accept `idempotency_key`, persisted as `IDEMP:{key}` in `tbl_account.Extra2` and checked inside `_COMMISSION_WRITE_LOCK` (`409 Conflict` on duplicate submission).
- **State-Gate Idempotency**: Re-paying an already settled policy (`NetAmount == 0.00`), re-reversing an already reversed payout (`REVERSED_BY:` marker), or re-reversing an already reversed voucher (`VOUCHER_REVERSED_BY:` marker) deterministically returns `409 Conflict`.

---

## 23. CONCURRENCY STRATEGY
- Combines a process-wide `asyncio.Lock()` (`_COMMISSION_WRITE_LOCK`) with MySQL InnoDB `SELECT ... FOR UPDATE` and `.execution_options(populate_existing=True)` across `tbl_transaction`, `tbl_agentcommissionpayment`, `tbl_franchisecommission`, `tbl_cutnpaycommpayable`, and `tbl_account`.
- Prevents MySQL `REPEATABLE READ` stale snapshots after authentication middleware queries and guarantees monotonically increasing `Doc_No` sequences with zero duplicate voucher numbers and zero over-disbursements.

---

## 24. UNIT TESTS ADDED
`tests/unit/test_phase9_commission_accounting_calculations.py` (`8` tests):
- `test_agent_od_commission_and_5pct_tds`
- `test_agent_combined_od_net_extra_commission_with_half_up_rounding`
- `test_agent_flat_commission_fallback_and_zero_tds`
- `test_cutnpay_full_and_partial_deduction_and_over_deduction_guard`
- `test_franchise_commission_and_profit_of_net_commission_spread`
- `test_evaluate_payout_eligibility_all_gates`
- `test_payout_extra2_encode_decode_roundtrip`
- `test_payment_status_labels`

---

## 25. INTEGRATION TESTS ADDED
`tests/integration/test_phase9_commission_payout_api.py` (`7` tests):
- `test_unauthenticated_phase9_endpoints_rejected_401`
- `test_unauthorized_roles_rejected_403_on_approval_payout_and_vouchers[AGENT/FRANCHISE/CLAIM/pOLICY VIEW]`
- `test_agent_and_franchise_commission_approval_payout_and_reversal`
- `test_cheque_pending_and_bounce_blocks_commission_payout_until_cleared`

---

## 26. ATOMICITY TESTS ADDED
- Tested in `test_cheque_pending_and_bounce_blocks_commission_payout_until_cleared` (`simulate_failure_at="AFTER_COMMISSION_UPDATE"`), verifying complete rollback of `AdvAmt`, `NetAmount`, and `PaymentStatus` on failure.

---

## 27. IDEMPOTENCY TESTS ADDED
- Duplicate payout `idempotency_key` (`IDEMP-PAYOUT-P9-001` and `IDEMP-C9-17`), duplicate payout reversal, and duplicate voucher reversal tested across `test_phase9_commission_payout_api.py`, `test_phase9_accounting_voucher_concurrency.py`, and `test_phase9_golden_parity.py`.

---

## 28. CONCURRENCY TESTS ADDED
`tests/integration/test_phase9_accounting_voucher_concurrency.py`:
- `test_100_concurrent_commission_payouts_never_overpay_or_duplicate_doc_no`: Fires **100 concurrent `POST /api/v1/commission-payouts` requests** (`100.00` each) against a `1,000.00` Agent payable pool (`2` policies $\times$ `500.00`). Verified:
  - Exactly **10 requests succeed (`201 Created`)**
  - Exactly **90 requests are rejected (`409 Conflict`)**
  - Total disbursed = `1,000.00`, remaining payable = `0.00` (never negative)
  - All 10 `Doc_No` voucher numbers are strictly unique
  - Trial Balance remains balanced (`variance == 0.00`)

---

## 29. PAYOUT TESTS ADDED
- Partial Agent payout (`PaymentStatus = 2.00`), full Agent payout (`PaymentStatus = 1.00`), partial Franchise payout, full Franchise payout (`CommissionPaid = 1`), and multi-policy pool payout allocation verified.

---

## 30. REVERSAL TESTS ADDED
- Commission payout reversal (`AccTransId = 7`), double-entry voucher reversal (`AccTransId = 9`), policy cancellation commission reversal (`C9-22`), and cheque bounce commission hold & clearance release (`C9-23`) verified.

---

## 31. LEDGER TESTS ADDED
- Master ledger creation (`POST /api/v1/accounting/ledgers`), duplicate ledger name guard (`409 Conflict`), chronological running-balance ledger statements (`GET /api/v1/accounting/ledgers/{id}/entries`), and partner sub-ledger statements (`GET /api/v1/accounting/accounts/{type}/{id}/statement`) verified.

---

## 32. TRIAL BALANCE TESTS ADDED
- Verified in `test_master_ledgers_double_entry_vouchers_statements_and_trial_balance`, `test_100_concurrent_commission_payouts_never_overpay_or_duplicate_doc_no`, `test_golden_parity_c9_14_to_c9_30_transactional_and_accounting_matrix` (`C9-30`), and `test_phase9_full_cross_phase_e2e_journey`.

---

## 33. VOUCHER TESTS ADDED
- Balanced journal/payment/receipt/contra voucher creation (`AccTransId = 8`), unbalanced voucher rejection (`422`), single-direction voucher rejection (`422`), and voucher reversal (`AccTransId = 9`) verified.

---

## 34. GOLDEN PARITY TEST MATRIX & RESULTS
Documented in [`phase_9_golden_parity.md`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/docs/migration/phase_9_golden_parity.md) and executed in `tests/integration/test_phase9_golden_parity.py`:
- **`30/30` Golden Parity Cases (`C9-01` through `C9-30`) PASSED** with **`0.00` monetary discrepancy** across all Agent commission buckets, Franchise commission buckets, 5%/10%/0% TDS rates, full/partial/invalid Cut & Pay deductions, approvals, partial/full payouts, duplicate/over-payout guards, policy cancellation reversals, cheque bounce holds, `AccTransId = 3, 6, 7, 8, 9` ledger entries, and Trial Balance verification.

---

## 35. END-TO-END TEST FLOW & RESULTS
`tests/integration/test_phase9_e2e.py` (`test_phase9_full_cross_phase_e2e_journey` — **PASSED**):
1. Created `TEST_CUSTOMER_001` (`POST /api/v1/customers`) & `TEST_VEHICLE_001` (`POST /api/v1/customers/{id}/vehicles`).
2. Created `TEST_QUOTATION_001` (`POST /api/v1/quotations/self`) & fetched policy prefill.
3. Previewed commission, TDS, Cut & Pay (`350.00`), and Franchise overriding spread (`475.00`) via `POST /api/v1/commissions/preview`.
4. Booked `TEST_POLICY_001` (`POST /api/v1/policies/book`) with Cheque payment (`17,350.00`) and verified commission payout is blocked while `Ischequeclearing == 1`.
5. Deposited & cleared cheque (`POST /api/v1/payments/{id}/deposit`, `/clear`) and matched insurer brokerage statement (`POST /api/v1/reconciliation/policies/{id}/match`).
6. Verified eligible commission payable queue (`2,025.00` total across Agent `600.00` + Franchise `1,425.00`) and approved both (`POST /api/v1/commissions/{id}/approve`).
7. Disbursed Agent & Franchise payouts (`TEST_PAYOUT_001`), created master ledgers (`TEST_LEDGER_001`) & journal voucher (`TEST_VOUCHER_001`), verified running-balance ledger statement, reversed & re-disbursed Agent payout, and verified final Trial Balance (`is_balanced = True`, `variance = 0.00`).

---

## 36. REGRESSION TEST RESULTS
- Full test suite across Phases 1, 2, 3, 4, 5, 6, 7, 8, and 9 executed cleanly with **zero regressions**.

---

## 37. TOTAL TEST COUNT BEFORE VS AFTER
- **Before Phase 9 (Phase 1–8 Baseline)**: `243 passed`
- **New Phase 9 Tests Added**: `32 passed` (covering unit, integration, RBAC, concurrency stress, golden parity `C9-01`..`C9-30`, and cross-phase E2E)
- **Total Tests After Phase 9**: **`275 passed` (100% pass rate)**

---

## 38. KNOWN LIMITATIONS / UNSUPPORTED ITEMS
- Automated bank payout file generation (NACH/NEFT batch file export) and statutory Form 16A TDS certificate PDF export belong to Phase 14 (Reporting & Exports).
- Mid-term policy endorsement commission adjustments belong to Phase 10 (Claims & Endorsements).

---

## 39. ZERO-SURPRISE PARITY CONFIRMATION
- All monetary calculations use `Decimal` (`ROUND_HALF_UP`) exclusively — never `float`.
- Legacy debit (`+amount`) / credit (`-amount`) polarity in `tbl_account`, `PaymentStatus` numeric codes (`0.00`, `1.00`, `2.00`, `3.00`), `ProfitofNetCommision` formula, and Cut & Pay deduction semantics are preserved with `0.00` variance.

---

## 40. NEXT RECOMMENDED STEP (DO NOT EXECUTE)
- **Phase 10 — Claims & Endorsements Engine** (Loss intimations, surveyor lifecycle, mid-term endorsements, NCB recovery). **Do not start Phase 10 without explicit user authorization.**

---

## 41. PHASE 9 COMPLETE — VERIFIED PARITY
`PHASE 9 COMPLETE — VERIFIED PARITY`
