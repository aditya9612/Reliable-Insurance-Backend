# Phase 8 — Payment, Cheque, Reconciliation & E-Wallet Legacy Audit

**Repository**: `Reliable-Insurance-Backend`  
**Phase**: `Phase 8 — Payments, Cheques & Reconciliation Engine (Stage A1)`  
**Mode**: Read-Only Legacy Reference Audit → Local FastAPI Migration Design  
**Target Runtime Database**: `localhost:3306/reliable_insurance_dev`

---

## 1. Executive Summary

In the legacy C# / .NET 4.0 (`InsurancefinalNew`) and MySQL (`brahmainsurance`) insurance backend, policy payment collection is not a single-step CRUD operation. It spans a multi-stage financial ecosystem around `tbl_transaction` (166 columns), `tbl_transactionpayment` (23 columns), `tbl_transactionappnew` (116 columns), `tbl_account` (24 columns), `tbl_ledgermaster` (11 columns), and the commission tables (`tbl_agentcommissionpayment`, `tbl_franchisecommission`, `tbl_cutnpaycommpayable`).

This audit catalogs every legacy payment, cheque, approval, reversal, insurer reconciliation, and partner E-Wallet entry point, physical table column, and financial side effect.

---

## 2. Legacy Payment, Cheque, Wallet & Reconciliation Entry Points

| # | Legacy Entry Point | Layer | C# Method / Handler | BLL / DAL Method | Stored Procedure(s) | Primary Tables | Financial Side Effect |
|---:|---|---|---|---|---|---|---|
| 1 | `Clerk/PolicyTransactionNew.aspx.cs` | WebForms UI | `btn_Submit_ServerClick`, `InsertTransaction`, `UpdateTransaction` | `DAL_Operations.InsertTransactionNew`, `InsertTransactionPayment`, `InsertAccountDetails` | `sp_InsertTransactionNew_2026`, `sp_InsertTransactionPayment`, `sp_InsertAccountDetails` | `tbl_transaction`, `tbl_transactionpayment`, `tbl_account`, `tbl_cutnpaycommpayable` | Books policy, records initial split payment instruments, applies Cut & Pay / E-Wallet deduction, posts `AccTransId = 1, 2, 3`. |
| 2 | `Clerk/PE_TransactionEntry.aspx.cs` | WebForms UI | `btn_Submit_ServerClick` | `DAL_Operations.InsertPolicyTransactionEntry`, `InsertTransactionPayment` | `sp_InsertPolicyTransactionEntry`, `sp_InsertTransactionPayment`, `sp_InsertAccountDetails` | `tbl_transaction`, `tbl_transactionpayment`, `tbl_account` | Stage-1 policy booking and initial instrument capture. |
| 3 | `Clerk/PendingTransaction.aspx.cs` | WebForms UI | `gv_Pending_RowCommand` | `DAL_Operations.SelectPendingTransactions`, `InsertTransactionPayment` | `sp_InsertTransactionPayment`, `sp_InsertAccountDetails` | `tbl_transaction`, `tbl_transactionpayment`, `tbl_account` | Collects subsequent shortfall payments (`OutstandingAmount > 0`), promotes `TStatus` from `"Pending"` to `"Booked"`. |
| 4 | `Service.asmx.cs` | ASMX Web Service | `InsertAppTransactionNew`, `InsertAppTransaction_2026` | `DAL_Operations.InsertAppTransactionNew` | `Sp_InsertAppTransctiondetailsNew8` | `tbl_transactionappnew` | Stages mobile proposal with `CashPaidAmt`, `CashShortAmt`, `EWalletUsedamt`, `EwalletStatus`. |
| 5 | `Clerk/CashierApprovalNew.aspx.cs` | WebForms UI | `gv_Approval_RowCommand` | `DAL_Operations.UpdateCashierApproval` | `sp_SelectCashierApprovalGrid`, `sp_UpdateCashierApproval` | `tbl_transactionpayment`, `tbl_transactionappnew` | Verifies cash/cheque/online receipt (`CashierApproval = 1`, `IsChashierApprove = 1`). |
| 6 | `Clerk/AccountantApproval.aspx.cs` | WebForms UI | `gv_Approval_RowCommand` | `DAL_Operations.UpdateAccountantApproval` | `sp_SelectAccountantApproval`, `sp_UpdateAccountantApproval` | `tbl_transactionpayment`, `tbl_transactionappnew`, `tbl_account` | Verifies premium, TDS, and instrument (`AccountantApproval = 1`, `IsAccountApproval = 1`). |
| 7 | `Clerk/OwnerApproval.aspx.cs`, `OwnerPaymentApproval.aspx.cs` | WebForms UI | `gv_Approval_RowCommand` | `DAL_Operations.UpdateOwnerApproval` | `sp_UpdateOwnerApproval`, `sp_UpdateOwnerPaymentApproval` | `tbl_transactionpayment`, `tbl_transactionappnew` | Approves credit/shortfall policies and special overrides (`OwnerApproval = 1`, `IsOwnerApprove = 1`). |
| 8 | `Clerk/ChequeClearance.aspx.cs` | WebForms UI | `btn_Update_ServerClick` | `DAL_Operations.UpdateChequeStatus` | `sp_UpdateChequeStatus` | `tbl_transactionpayment`, `tbl_transaction`, `tbl_account` | Marks cheque cleared (`Ischequeclearing = 0`, `IsChequeCleared = 1`, `ChequeBankStatus = 1`, `CheqBankDate`). |
| 9 | `Clerk/ChequeBounce.aspx.cs` | WebForms UI | `btn_Update_ServerClick` | `DAL_Operations.UpdateChequeStatus`, `InsertChequeBouncePenalty` | `sp_UpdateChequeStatus`, `sp_InsertChequeBouncePenalty` | `tbl_transactionpayment`, `tbl_transaction`, `tbl_account`, `tbl_cutnpaycommpayable` | Marks cheque bounced (`ChequeBankStatus = 2`, `IsChequeCleared = 0`), restores `OutstandingAmount`, reverts `TStatus` to `"Pending"`, posts bounce reversal and penalty in `tbl_account`. |
| 10 | `Clerk/adm_DeletePolicyTransaction.aspx.cs` | WebForms UI | `btn_Delete_ServerClick` | `DAL_Operations.DeleteTransactionByTransId` | `sp_DeleteTransactionByTransId` | `tbl_transaction`, `tbl_transactionpayment`, `tbl_account`, `tbl_agentcommissionpayment`, `tbl_franchisecommission`, `tbl_cutnpaycommpayable` | Soft-deletes policy and reverses all child payment, commission, wallet, and ledger entries. |
| 11 | `Clerk/EWalletApproval.aspx.cs`, `FranchiseWallateApproval.aspx.cs` | WebForms UI | `gv_Wallet_RowCommand` | `DAL_Operations.ApproveEWalletRequest`, `ApproveFranchiseWallet` | `sp_ApproveEWalletRequest`, `sp_ApproveFranchiseWallet`, `sp_UpdateAgentWalletBalance` | `tbl_ledgermaster`, `tbl_account`, `tbl_transactionappnew`, `tbl_transaction` | Credits/debits/locks/releases partner E-Wallet balances and posts ledger rows. |
| 12 | `Service.asmx.cs` | ASMX Web Service | `GetAgentWalletBalance`, `GetWalletLedger` | `DAL_Operations.GetWalletBalance`, `GetWalletLedger` | `sp_GetWalletBalance`, `sp_GetWalletLedger` | `tbl_ledgermaster`, `tbl_account` | Returns live E-Wallet balance and movement ledger for Agent/Franchise. |

---

## 3. Physical Payment, Cheque, Ledger & Reconciliation Table Audit

### 3.1 `tbl_transactionpayment` (`app/models/payment.py` — 23 Verified Columns)
- **Primary Key**: `PaymentId` (`INT AUTO_INCREMENT`)
- **Foreign Key (Logical)**: `TransanctionId` (`INT` $\rightarrow$ `tbl_transaction.TransanctionId`, preserving legacy spelling with extra `n`)
- **Columns**:
  - `PaymentId` (`INT`, PK)
  - `PaymentDate` (`DATETIME`, nullable): Instrument / receipt date
  - `PaymentType` (`VARCHAR(255)`, nullable): `"CASH"`, `"CHEQUE"`, `"DD"`, `"NEFT"`, `"RTGS"`, `"UPI"`, `"ONLINE"`, `"CREDIT_CARD"`, `"DEBIT_CARD"`, `"EWALLET"`
  - `PaymentDetails` (`VARCHAR(255)`, nullable): Narration / UTR / remarks
  - `bankname` (`VARCHAR(255)`, nullable): Issuing bank name (required for `"CHEQUE"` and `"DD"`)
  - `docno` (`VARCHAR(255)`, nullable): Cheque number, DD number, UTR, card auth code, or wallet ref
  - `PaidAmount` (`DOUBLE(asdecimal=True)`, nullable): Instrument payment amount (`Decimal`)
  - `CashierApproval` (`INT`, nullable): `0`=Pending, `1`=Approved, `2`=Rejected
  - `CashierApprovalDate` (`DATETIME`, nullable)
  - `AccountantApproval` (`INT`, nullable): `0`=Pending, `1`=Approved, `2`=Rejected
  - `AccountantApprovalDate` (`DATETIME`, nullable)
  - `OwnerApproval` (`INT`, nullable): `0`=Pending, `1`=Approved, `2`=Rejected
  - `OwnerApprovalDate` (`DATETIME`, nullable)
  - `BranchId` (`INT`, nullable): Branch jurisdiction
  - `TransanctionId` (`INT`, nullable): Parent policy transaction ID
  - `Extra1` (`VARCHAR(255)`, nullable): Instrument lifecycle state (`"RECEIVED"`, `"PENDING_CLEARANCE"`, `"DEPOSITED"`, `"CLEARED"`, `"BOUNCED"`, `"REVERSED"`)
  - `Extra2` (`VARCHAR(255)`, nullable): Bank branch / clearance reference / bounce reason / idempotency tag
  - `isdeleted` (`VARCHAR(255)`, nullable): `"0"` = Active, `"1"` = Reversed / Bounced / Soft-deleted
  - `CreateUser`, `CreateDate`, `UpdateDate`, `UpdateUser`: Audit trail
  - `isCompletePayment` (`INT`, NOT NULL): `1` if completes policy payable requirement, `0` otherwise

### 3.2 `tbl_transaction` (`app/models/transaction.py` — Payment, Cheque, Wallet & Reconciliation Columns)
- **Payment & Shortfall Columns**:
  - `Amount` (`DOUBLE`): Gross payable policy premium (`NetPermium + GST_Amount`)
  - `PaidAmount` (`DOUBLE`): Total active settled instrument + wallet + insurer-direct amount
  - `OutstandingAmount` (`DOUBLE`): Remaining balance (`max(0.00, RequiredPayable - PaidAmount)`)
  - `CutNPay` (`DOUBLE`): Upfront commission deduction amount
  - `EWalletAmountUsed` (`DOUBLE`): Partner E-Wallet amount applied to policy
  - `TStatus` (`VARCHAR(255)`): `"Booked"`, `"Pending"`, `"Cancelled"`
  - `pendingStatus` (`INT`): `0` = Complete, `1` = Pending
  - `RAPaymentStatus` (`VARCHAR(100)`): `"COMPLETE"`, `"PENDING"`, `"BOUNCED"`
  - `IsActivePendingCash` (`INT`): `1` when shortfall pending, `0` when settled
- **Cheque Columns**:
  - `Ischequeclearing` (`INT`): `1` while cheque is pending clearance/deposited, `0` once cleared or bounced
  - `IsChequeCleared` (`INT`): `1` when cleared (or non-cheque settled), `0` while pending or bounced
  - `ChequeBankStatus` (`INT`): `0` = Pending/Deposited, `1` = Cleared, `2` = Bounced
  - `CheqBankDate` (`DATETIME`): Clearance or bounce date
- **Insurer Payment & Reconciliation Columns**:
  - `OnlinePaymentToCompany` (`INT`): Amount paid directly online to insurer
  - `OnlineToCompanyDate` (`DATETIME`): Timestamp of insurer online payment
  - `CompSubmitionDocNo` (`VARCHAR(255)`): Insurer submission receipt/reference number
  - `CompanyChequeNo` (`VARCHAR(255)`): Cheque number issued to insurance company
  - `IsCompanyChequeNo` (`INT`): `1` if paid to insurer via company cheque, `0` otherwise
  - `IsRconDataMatch` (`INT`): `0` = Unreconciled, `1` = Reconciled (Full Match), `2` = Partial / Variance
  - `RconGrid` (`DOUBLE`): Reconciled insurer commission percentage
  - `RconComm` (`DOUBLE`): Reconciled insurer commission amount
  - `accounting_period` (`DATETIME`): Reconciliation accounting period date
  - `IB_Doc_No` (`INT`): Insurer brokerage voucher/document number
  - `IB_PaymentDate` (`DATETIME`): Insurer brokerage settlement date
  - `IB_ReceiptStatus` (`INT`): `0` = Unreconciled, `1` = Reconciled, `2` = Partial
  - `IB_PaymentBy` (`VARCHAR(100)`): Insurer reconciliation mode/actor

### 3.3 `tbl_account` (`app/models/account.py` — 24 Verified Columns) & `tbl_ledgermaster` (`app/models/ledger.py` — 11 Verified Columns)
- `tbl_ledgermaster` defines sub-ledgers by `(LedgerTypeId, ReferenceId, BranchId)`:
  - `LedgerTypeId = 1`: Branch Policy Control Ledger
  - `LedgerTypeId = 4`: Customer Ledger (`ReferenceId = CustomerId`)
  - `LedgerTypeId = 5`: Agent E-Wallet & Commission Ledger (`ReferenceId = AgentId`)
  - `LedgerTypeId = 6`: Franchise E-Wallet & Commission Ledger (`ReferenceId = FranchiseId`)
- `tbl_account` stores signed (`amount` `Decimal`) journal entries discriminated by `AccTransId` and `Extra1`:
  - `AccTransId = 1` (`"POLICY_RECEIVABLE"`): `+FinalPremium`
  - `AccTransId = 2` (`"POLICY_PAYMENT"` / `"PAYMENT_REVERSAL"` / `"CHEQUE_BOUNCE_REVERSAL"`): `+PaidAmount` on receipt, `-PaidAmount` on reversal/bounce
  - `AccTransId = 3` (`"COMMISSION_EXPENSE"`): `-NetCommission`
  - `AccTransId = 4` (`"CHEQUE_BOUNCE_PENALTY"`): `+PenaltyAmount` debit charge on cheque dishonor
  - `AccTransId = 5` (`"INSURER_RECONCILIATION"`): Reconciled insurer commission/remittance entry
  - `AccTransId = 10` (`"WALLET_TOPUP"`): `+TopUpAmount` credit to partner wallet
  - `AccTransId = 11` (`"WALLET_LOCK"`): `-LockAmount` reservation lock on partner wallet
  - `AccTransId = 12` (`"WALLET_RELEASE"`): `+ReleaseAmount` release of prior wallet lock
  - `AccTransId = 13` (`"WALLET_DEBIT"`): `-DebitAmount` consumption of partner wallet for policy payment
  - `AccTransId = 14` (`"WALLET_REFUND"`): `+RefundAmount` credit back to wallet on payment/policy reversal

---

## 4. Refund Scope Verification

In the legacy codebase (`InsurancefinalNew`), there is **no standalone customer bank-refund table or gateway refund stored procedure**. Customer premium adjustments upon cancellation or dishonor are handled exclusively through:
1. **Payment Reversal** (`POST /api/v1/payments/{payment_id}/reverse`) — reverses the payment receipt in `tbl_transactionpayment` and `tbl_account` (and credits back the partner E-Wallet if `PaymentType == "EWALLET"`).
2. **Policy Cancellation** (`DELETE /api/v1/policies/{transaction_id}`) — soft-deletes the policy and reverses all child payment, commission, and accounting entries (`sp_DeleteTransactionByTransId`).

Accordingly, no speculative third-party gateway refund API is invented in Phase 8; payment reversal and wallet refund-on-reversal cover all legacy-supported adjustment flows.
