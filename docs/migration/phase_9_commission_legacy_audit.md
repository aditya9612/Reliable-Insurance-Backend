# Phase 9 — Legacy Commission & Accounting Engine Audit

**Repository**: `Reliable-Insurance-Backend`  
**Phase**: `Phase 9 — Commission & Accounting Engine (Stage A1)`  
**Target Runtime Database**: `localhost:3306/reliable_insurance_dev`  
**Production Database (`brahmainsurance`)**: `STRICTLY ISOLATED — ZERO RUNTIME / TEST CONNECTIONS`

---

## 1. Executive Summary of Legacy Commission & Accounting Architecture

In the legacy C# / ASP.NET 4.0 WebForms & ASMX backend, the **Commission & Accounting Engine** spans underwriting commission calculation, statutory TDS deduction, upfront Cut & Pay deduction, cheque-bounce commission holds/releases, individual and bulk commission payout disbursement, commission clawback/reversal, double-entry ledger postings (`tbl_account` + `tbl_ledgermaster`), balanced accounting vouchers, ledger statements with running balances, and branch/company Trial Balance reporting.

All Phase 9 operations use the **7 verified physical tables** already migrated into `reliable_insurance_dev` (zero physical foreign keys, UTF-8 `DYNAMIC` row format):
1. `tbl_transaction` (`166` columns, PK `TransanctionId`)
2. `tbl_agentcommissionpayment` (`20` columns, PK `AgentCommId`)
3. `tbl_franchisecommission` (`29` columns, PK `FranchiseCommId`)
4. `tbl_cutnpaycommpayable` (`11` columns, PK `CutNPayCommPayId`)
5. `tbl_transactionpayment` (`18` columns, PK `PaymentId`)
6. `tbl_account` (`24` columns, PK `AccountId`)
7. `tbl_ledgermaster` (`11` columns, PK `LedgerMId`)

---

## 2. Legacy Entry Points (`Clerk/*.aspx.cs`, `Service.asmx.cs`, `DAL_Operations.cs`)

| # | Legacy File / Class | C# Method / Event Handler | Stored Procedures / SQL Invoked | Target Physical Tables | Business Function & Financial Effect |
|---:|---|---|---|---|---|
| 1 | `Clerk/PolicyTransactionNew.aspx.cs` | `btn_Submit_ServerClick`, `InsertTransaction`, `UpdateTransaction` | `sp_InsertTransactionNew_2026`, `sp_InsertAgentCommissionPayment`, `sp_InsertFranchiseCommission`, `sp_InsertCutNPayCommPayable`, `sp_InsertAccountDetails` | `tbl_transaction`, `tbl_agentcommissionpayment`, `tbl_franchisecommission`, `tbl_cutnpaycommpayable`, `tbl_account`, `tbl_ledgermaster` | Computes multi-bucket Agent Commission (`OD`, `Net`/`TP`, `Extra`), 5% TDS per bucket, Franchise Commission, `ProfitofNetCommision`, and Cut & Pay deduction (`CutNPay`). Inserts commission records and posts `AccTransId = 1, 2, 3` in `tbl_account`. |
| 2 | `Clerk/AgentCommisionApproval.aspx.cs` | `btn_Approve_ServerClick`, `gv_Commission_RowCommand`, `btn_BulkPayout_Click` | `sp_UpdateAgentCommissionApproval`, `sp_InsertAccountDetails` | `tbl_agentcommissionpayment`, `tbl_franchisecommission`, `tbl_transaction`, `tbl_cutnpaycommpayable`, `tbl_account` | Approves pending commissions (`CommProcessSubmit = 1`) and executes individual or bulk commission payouts (`PaymentStatus = 1.00` or `2.00`, `CommissionPaid = 1`, `FranchiseCommPaid = 1`, `FCommissionPaid`), generating payout vouchers (`AccTransId = 6`) in `tbl_account`. |
| 3 | `Clerk/AgentCommissionUseWallet.aspx.cs` | `btn_Approve_ServerClick` | `sp_UpdateAgentWalletBalance`, `sp_InsertAccountDetails` | `tbl_agentcommissionpayment`, `tbl_account`, `tbl_ledgermaster` | Disburses approved net commission directly into the partner's E-Wallet sub-ledger (`LedgerTypeId = 5` or `6`, `AccTransId = 10` credit + `AccTransId = 6` commission settlement). |
| 4 | `Clerk/AccountantApproval.aspx.cs` | `gv_Approval_RowCommand` | `sp_UpdateAccountantApproval`, `sp_SelectAccountantApproval` | `tbl_transaction`, `tbl_transactionappnew`, `tbl_transactionpayment`, `tbl_account` | Accountant verification of premium, TDS %, commission grid, and voucher postings (`IsAccountApproval = 1`, `AccountantApproval = 1`). |
| 5 | `Clerk/OwnerPaymentApproval.aspx.cs` & `Clerk/OwnerApproval.aspx.cs` | `gv_Approval_RowCommand` | `sp_UpdateOwnerApproval` | `tbl_transaction`, `tbl_transactionappnew`, `tbl_agentcommissionpayment` | Owner approval for high-value commission payouts, incentive overrides (`IntensiveAmount`), and self-discount exceptions (`SelfDiscount`). |
| 6 | `Clerk/ChequeBounce.aspx.cs` & `Clerk/ChequeClearance.aspx.cs` | `btn_Update_ServerClick` | `sp_UpdateChequeStatus`, `sp_InsertChequeBouncePenalty` | `tbl_transactionpayment`, `tbl_transaction`, `tbl_cutnpaycommpayable`, `tbl_agentcommissionpayment`, `tbl_account` | On cheque bounce: sets `CommissionPaid = 0`, `tbl_cutnpaycommpayable.Flag = 'HOLD_CHEQUE_BOUNCE'`, `tbl_agentcommissionpayment.PaymentStatus = 0.00`. On clearance/replacement settlement: releases commission hold. |
| 7 | `Clerk/adm_DeletePolicyTransaction.aspx.cs` | `btn_Delete_ServerClick` | `sp_DeleteTransactionByTransId` | `tbl_transaction`, `tbl_franchisecommission`, `tbl_agentcommissionpayment`, `tbl_cutnpaycommpayable`, `tbl_account` | Soft-deletes cancelled policy and reverses/claws back all accrued/paid commissions and ledger entries. |
| 8 | `Clerk/AccountVoucherEntry.aspx.cs` & `Clerk/TrialBalanceReport.aspx.cs` | `btn_SaveVoucher_Click`, `BindTrialBalance`, `BindLedgerStatement` | `sp_InsertAccountDetails`, `sp_GetLedgerStatement`, `sp_GetTrialBalance` | `tbl_account`, `tbl_ledgermaster` | Creates balanced double-entry accounting vouchers (`AccTransId = 8, 9`), computes chronological ledger statements with opening/running/closing balances, and generates Trial Balance reports (`Total Debit == Total Credit`). |
| 9 | `Service.asmx.cs` | `GetCommissionStatement`, `GetWalletLedger`, `AccountPaymentMsg`, `ProcessToInstaPay` | `sp_GetAgentCommission`, `sp_InsertAccountDetails` | `tbl_agentcommissionpayment`, `tbl_franchisecommission`, `tbl_account`, `tbl_ledgermaster` | Partner-facing ASMX endpoints for commission statements, TDS summaries, and payout status notifications. |

---

## 3. Stored Procedure to FastAPI Service Mapping

| Legacy Stored Procedure | FastAPI Service Method (`CommissionAccountingService`) | Primary Tables | Key Improvements Over Legacy |
|---|---|---|---|
| `sp_InsertAgentCommissionPayment` | `PolicyBookingService.book_policy` / `CommissionAccountingService.calculate_commission` | `tbl_agentcommissionpayment` | `Decimal(0.01)` `ROUND_HALF_UP` precision; zero `double` drift |
| `sp_InsertFranchiseCommission` | `PolicyBookingService.book_policy` / `CommissionAccountingService.calculate_commission` | `tbl_franchisecommission` | Deterministic multi-bucket franchise split and `ProfitofNetCommision` |
| `sp_InsertCutNPayCommPayable` | `PolicyBookingService.book_policy` | `tbl_cutnpaycommpayable` | Tracks upfront `CommPayable` and remaining `Balance` |
| `sp_UpdateAgentCommissionApproval` | `approve_commission`, `create_commission_payout`, `create_bulk_commission_payout` | `tbl_agentcommissionpayment`, `tbl_franchisecommission`, `tbl_cutnpaycommpayable`, `tbl_transaction`, `tbl_account` | Row-locked (`SELECT ... FOR UPDATE`), atomic unit-of-work, idempotency key guard, supports full and partial payouts |
| `sp_UpdateAgentWalletBalance` | `create_commission_payout(payout_mode="EWALLET")` | `tbl_account`, `tbl_ledgermaster`, `tbl_agentcommissionpayment` | Atomic commission settlement + partner E-Wallet credit in one transaction |
| `sp_DeleteTransactionByTransId` / Reversal | `reverse_commission_payout`, `reverse_policy_commission` | `tbl_agentcommissionpayment`, `tbl_franchisecommission`, `tbl_cutnpaycommpayable`, `tbl_transaction`, `tbl_account` | Preserves audit trail with contra reversal vouchers (`AccTransId = 7`) |
| `sp_InsertAccountDetails` | `create_voucher`, `reverse_voucher` | `tbl_account`, `tbl_ledgermaster` | Concurrency-safe `Doc_No` & `VCH-{BranchId}-{FY}-{Seq:06d}` numbering; enforces $\sum \text{Debit} == \sum \text{Credit}$ |
| `sp_GetLedgerStatement` | `get_ledger_statement` | `tbl_account`, `tbl_ledgermaster` | Deterministic `opening_balance`, chronological `running_balance`, and `closing_balance` |
| `sp_GetTrialBalance` | `get_trial_balance` | `tbl_account`, `tbl_ledgermaster` | Reconciles single-sided legacy policy postings with control accounts so `Total Debit == Total Credit` (`0.00` variance) |

---

## 4. Legacy Defects Identified & Modernized in Phase 9

1. **Floating-Point (`double`) Rounding Drift in Multi-Bucket Commissions & TDS**:
   - *Legacy Defect*: C# `Convert.ToDouble` and MySQL `DOUBLE` arithmetic produced `0.01` rounding discrepancies between bucket TDS sums and headline TDS.
   - *FastAPI Mitigation*: Strict `Decimal` arithmetic quantized at each intermediate bucket step (`Decimal("0.01")`, `ROUND_HALF_UP`).
2. **Non-Atomic Commission Payout & Duplicate Disbursement Race Condition**:
   - *Legacy Defect*: `Clerk/AgentCommisionApproval.aspx.cs` updated `tbl_agentcommissionpayment` and inserted `tbl_account` in separate ADO.NET calls without `FOR UPDATE` row locks, allowing concurrent clicks to double-pay the same commission row.
   - *FastAPI Mitigation*: Process-level `_COMMISSION_WRITE_LOCK` + InnoDB `SELECT ... FOR UPDATE` on `tbl_agentcommissionpayment` / `tbl_franchisecommission` / `tbl_transaction` + `idempotency_key` deduplication (`409 Conflict`).
3. **Unsafe `MAX(Doc_No) + 1` Voucher Numbering**:
   - *Legacy Defect*: Unsynchronized `SELECT MAX(Doc_No) + 1 FROM tbl_account` generated duplicate voucher numbers under concurrent requests.
   - *FastAPI Mitigation*: Serialized lock + `SELECT ... FOR UPDATE` on branch/FY voucher sequence allocation.
4. **Premature Commission Payout Before Policy Settlement / Cheque Clearance**:
   - *Legacy Defect*: Operators could trigger commission payout on policies with uncleared or dishonored cheques.
   - *FastAPI Mitigation*: Server-side precondition check rejecting payout (`409 Conflict` / `422`) if `tx.OutstandingAmount > 0`, `tx.Ischequeclearing == 1`, `tx.ChequeBankStatus == 2`, or `CutNPayCommPayable.Flag == "HOLD_CHEQUE_BOUNCE"`.
