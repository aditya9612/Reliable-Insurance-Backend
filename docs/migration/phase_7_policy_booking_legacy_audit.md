# Phase 7 — Policy Booking & Transaction Engine: Legacy Audit

**Phase:** 7 — Policy Booking & Transaction Engine  
**Stage:** A1 — Legacy Codebase & Database Audit  
**Mode:** Read-Only Legacy Reference → Local FastAPI Migration Design  
**Target Database:** `localhost:3306/reliable_insurance_dev`

---

## 1. Executive Summary

In the legacy C# / ASP.NET WebForms (`InsurancefinalNew`) and MySQL (`brahmainsurance`) architecture, **Policy Booking & Underwriting Transaction Entry** is the central financial operation of the system. It converts customer, vehicle, and quotation/rating data into an authoritative underwriting policy record (`tbl_transaction`), allocates a sequential `InwardNo`, records payment collections (`tbl_transactionpayment`), computes multi-tier agent/franchise commissions (`tbl_franchisecommission`, `tbl_agentcommissionpayment`, `tbl_cutnpaycommpayable`), and posts double-entry accounting ledger rows (`tbl_account`, `tbl_ledgermaster`).

A thorough static audit of the legacy C# source code reveals **two primary booking pathways**:

1. **Pathway A — Two-Stage Mobile / Partner Proposal Intake → Back-Office Issuance**:
   - Mobile POSP Agents (`AGENT`, `FRANCHISE AGENT`), Relationship Managers (`RELATIONSHIP MANAGER`), and Insurance Executives (`Insurance Exective`) submit a policy proposal via `Service.asmx.cs::InsertAppTransactionNew` / `InsertAppTransaction_2026` (`Sp_InsertAppTransctiondetailsNew8`), writing a staging row into **`tbl_transactionappnew`** (`PK: TransId`).
   - Staged proposals optionally reference a Phase 6 Self-Quotation (`SRQ...` in `tbl_app_quatationentry`) or Assisted Quotation Request (`QR...` in `tbl_app_quotationrequest`) via `QuatationCode`, prefilled using `sp_getDataForPolicyEntry`.
   - Depending on payment mode (Cash, Cheque, Cut & Pay, Online, E-Wallet) and discount level, the staging row passes through approval queues (`Clerk/OwnerApproval.aspx.cs`, `Clerk/CashierApprovalNew.aspx.cs`, `Clerk/AccountantApproval.aspx.cs`) before being converted into a final policy in **`tbl_transaction`** (`TransId` foreign key linking back to `tbl_transactionappnew.TransId`).

2. **Pathway B — Direct Back-Office Policy Booking**:
   - Back-office Operators (`OPERATOR`, `OPERATOR HEAD`, `ALL USER`, `Freelancer`), Franchise Operators (`FRANCHISE`, `FRANCHISE TYPE 2`, `FRANCHISE TYPE 3`, `FRANCHISE OPERATOR`), and Administrators (`OWNER`, `ADMIN`, `IT SUPPORT`) book policies directly via **`Clerk/PolicyTransactionNew.aspx.cs`** or **`Clerk/PE_TransactionEntry.aspx.cs`**.
   - Direct booking validates or creates the Customer (`tbl_customer`) and Vehicle (`tbl_vehicledetails`), allocates an `InwardNo` (`sp_generateInwardNo`), inserts the master underwriting row into **`tbl_transaction`** (`PK: TransanctionId`), inserts payment instrument rows into **`tbl_transactionpayment`** (`PK: PaymentId`), computes commission rows, and writes three accounting ledger entries (`AccTransId = 1, 2, 3`) into **`tbl_account`**.

---

## 2. Inventory of Legacy Policy Booking Entry Points

| # | Legacy File / Endpoint | Layer | Entry Method / Handler | Primary Tables Written | Stored Procedures Invoked | Business Purpose |
|---:|---|---|---|---|---|---|
| 1 | `Clerk/PolicyTransactionNew.aspx.cs` | WebForms UI | `btn_Submit_ServerClick`, `InsertTransaction`, `UpdateTransaction` | `tbl_transaction`, `tbl_transactionpayment`, `tbl_account`, `tbl_franchisecommission`, `tbl_cutnpaycommpayable` | `sp_generateInwardNo`, `sp_InsertTransactionNew_2026`, `sp_UpdateTransactionNew_2026`, `sp_InsertTransactionPayment`, `sp_InsertAccountDetails` | Full back-office policy booking, commission calculation, payment entry, and accounting ledger posting. |
| 2 | `Clerk/PE_TransactionEntry.aspx.cs` | WebForms UI | `btn_Submit_ServerClick` | `tbl_transaction`, `tbl_transactionpayment`, `tbl_account` | `sp_InsertPolicyTransactionEntry`, `sp_UpdatePolicyTransactionEntry`, `sp_InsertTransactionPayment`, `sp_InsertAccountDetails` | Quick back-office underwriting policy intake and verification. |
| 3 | `Service.asmx.cs` | ASMX Mobile API | `InsertAppTransactionNew`, `InsertAppTransaction_2026` | `tbl_transactionappnew` | `Sp_InsertAppTransctiondetailsNew8`, `sp_InsertAppTransactionNew` | Mobile app policy proposal submission with payment, Cut & Pay, and quotation link (`QuatationCode`). |
| 4 | `Service.asmx.cs` | ASMX Mobile API | `getDataForPolicyEntry` | Read-only (`tbl_app_quatationentry`, `tbl_app_quotationrequest`) | `sp_getDataForPolicyEntry` | Prefills policy proposal form from a Self-Quotation (`SELFQUO`) or Assisted Quotation Request. |
| 5 | `Clerk/CashierApprovalNew.aspx.cs` | WebForms UI | `gv_Approval_RowCommand` | `tbl_transactionappnew`, `tbl_transaction`, `tbl_transactionpayment` | `sp_UpdateCashierApproval`, `sp_SelectCashierApprovalGrid` | Cashier verification of cash/cheque/online collection (`IsChashierApprove = 1`). |
| 6 | `Clerk/AccountantApproval.aspx.cs` | WebForms UI | `gv_Approval_RowCommand` | `tbl_transactionappnew`, `tbl_transaction`, `tbl_account` | `sp_UpdateAccountantApproval`, `sp_SelectAccountantApproval` | Accountant verification of policy premium, TDS, and commission (`IsAccountApproval = 1`). |
| 7 | `Clerk/OwnerApproval.aspx.cs` | WebForms UI | `gv_Approval_RowCommand` | `tbl_transactionappnew`, `tbl_transaction` | `sp_UpdateOwnerApproval` | Owner approval for special OD discount / credit / Cut & Pay exceptions (`IsOwnerApprove = 1`). |
| 8 | `Clerk/adm_DeletePolicyTransaction.aspx.cs` | WebForms UI | `btn_Delete_ServerClick` | `tbl_transaction`, `tbl_transactionpayment`, `tbl_account` | `sp_DeleteTransactionByTransId` | Soft-deletes policy transaction (`isdeleted = 1`) and reverses payment and accounting entries. |
| 9 | `Clerk/adm_DeleteTransactionEntry.aspx.cs` | WebForms UI | `btn_Delete_ServerClick` | `tbl_transaction`, `tbl_transactionpayment`, `tbl_account` | `sp_DeleteTransactionEntryByTransId` | Soft-deletes quick-entry policy transaction and associated financial rows. |
| 10 | `Clerk/ChequeClearance.aspx.cs` / `ChequeBounce.aspx.cs` | WebForms UI | `btn_Update_ServerClick` | `tbl_transactionpayment`, `tbl_transaction`, `tbl_account` | `sp_UpdateChequeStatus`, `sp_InsertChequeBouncePenalty` | Updates cheque clearance status or reverses payment on dishonor/bounce. |

---

## 3. Physical Schema & Legacy Column Naming Quirks

To guarantee 100% database compatibility with existing local migrations (`b84657b131fa`) and legacy reporting queries, all physical column names and spelling quirks in `reliable_insurance_dev` are strictly preserved:

### 3.1 `tbl_transaction` (`app/models/transaction.py` — 166 Columns)
- **Primary Key:** `TransanctionId` (note the legacy spelling `Transanction` with an extra `n`).
- **Premium Typos Preserved:**
  - `ODPermium` (`DOUBLE` -> `Decimal`): Own Damage Net Premium (including Add-On / IMT-23 as applicable in policy entry).
  - `TPPermium` (`DOUBLE` -> `Decimal`): Third-Party Liability Total Premium.
  - `NetPermium` (`DOUBLE` -> `Decimal`): Total Net Premium before GST (`ODPermium + TPPermium`).
  - `NCBPermium` (`DOUBLE` -> `Decimal`): Monetary NCB deduction amount.
- **Tax & Total Columns:**
  - `GST_Amount` (`DOUBLE` -> `Decimal`): Total GST amount (`18%` standard, or `12%` Basic TP + `18%` OD/Add-On for GCV).
  - `Amount` (`DOUBLE` -> `Decimal`): Final Payable Policy Premium (`NetPermium + GST_Amount`).
  - `ProPosalAmt` (`DOUBLE` -> `Decimal`): Proposal / Gross Premium amount.
- **Payment & Status Columns:**
  - `PaidAmount` (`DOUBLE` -> `Decimal`): Cumulative amount collected across payment instruments.
  - `OutstandingAmount` (`DOUBLE` -> `Decimal`): Remaining balance (`max(0, EffectivePayable - PaidAmount)`).
  - `TStatus` (`VARCHAR(45)`): Underwriting status (`"Booked"`, `"Pending"`, `"Verified"`, `"Issued"`, `"Cancelled"`).
  - `pendingStatus` (`VARCHAR(100)`): Payment/document completion status (`"Complete"`, `"Pending"`).
  - `DeuDate` (`DATE`): Legacy spelling for payment/renewal Due Date.
  - `IsNill` (`INT`): Legacy spelling for Nil-Depreciation (`ZeroDep`) indicator (`1` = Yes, `0` = No).
- **Commission Columns on `tbl_transaction`:**
  - Overall: `AgentComm` (%), `AgentCommAmt`, `TdsAmt`, `NetCommission`, `tdsPercent`.
  - OD Split: `AgentComm_OD` (%), `AgentCommAmt_OD`, `TdsAmt_OD`, `NetCommission_OD`.
  - Net/TP Split: `AgentComm_Net` (%), `AgentCommAmt_Net`, `TdsAmt_Net`, `NetCommission_Net`.
  - Extra Split: `AgentComm_Extra` (%), `AgentCommAmt_Extra`, `TdsAmt_Extra`, `NetCommission_Extra`.
  - Payout Modes: `CutNPay` (`1` = Cut & Pay active, `0` = Normal), `EWalletAmountUsed` (`Decimal`), `CommissionPaid` (`1` = Paid/Settled, `0` = Unpaid).
- **Traceability & Linkage Columns:**
  - `InwardNo` (`VARCHAR(45)`): Sequential branch/financial-year inward number.
  - `CustomerId` (`INT`): Foreign key to `tbl_customer.CustomerId`.
  - `CustVehId` (`INT`): Foreign key to `tbl_vehicledetails.CustVehId`.
  - `QuatationCode` (`VARCHAR(100)`): Links back to `tbl_app_quatationentry.QuatationCode` (`SRQ...`) or `tbl_app_quotationrequest.QuatationCode` (`QR...`).
  - `TransId` (`INT`): Links back to `tbl_transactionappnew.TransId` when booked from a staged proposal.
  - `isdeleted` (`TINYINT(1)`): Soft-delete flag (`0` = Active, `1` = Deleted/Cancelled).

### 3.2 `tbl_transactionappnew` (`app/models/transaction_app.py` — 116 Columns)
- **Primary Key:** `TransId`.
- **Purpose:** Captures mobile/partner policy proposals prior to or during back-office issuance.
- **Key Columns:** `QuatationCode`, `CustomerName`, `VehicleNo`, `MakeId`, `ModelId`, `VariantId`, `VehTypeId`, `SubTypeId`, `ProductType`, `PolicyType`, `InsuranceCompanyId`, `ODPremium`, `TPPremium`, `NetPremium`, `FinalPremium`, `GST`, `IDV`, `NCB`, `NCBPer`, `ODDiscount`, `PaymentMode`, `CashPaidAmt`, `CashShortAmt`, `CutNPay`, `EWalletUsedamt`, `AgentId`, `SalesExecutiveId`, `FranchaiseId`, `BranchId`, `UserId`, `IsOwnerApprove`, `IsChashierApprove`, `IsAccountApproval`, `IsSubmit`, `isdeleted`.

---

## 4. Legacy Defects Identified & Hardened in Phase 7

| Defect ID | Legacy Behavior | Risk | Phase 7 FastAPI Remediation |
|---|---|---|---|
| **DEF-7-01** | `PolicyTransactionNew.aspx.cs` executes `sp_generateInwardNo`, `sp_InsertTransactionNew_2026`, `sp_InsertTransactionPayment`, and `sp_InsertAccountDetails` as **separate ADO.NET connections without a database transaction**. | Partial writes leave orphan `tbl_transaction` rows without `tbl_transactionpayment` or `tbl_account` rows if a later step fails. | Enforced single SQLAlchemy `AsyncSession` transaction boundary (`BEGIN ... COMMIT / ROLLBACK`) across all 5 tables. |
| **DEF-7-02** | `sp_generateInwardNo` uses unlocked `SELECT MAX(...)` / `COUNT(*)`, causing duplicate `InwardNo` values under concurrent submissions. | Duplicate inward numbers corrupt policy tracking and audit trails. | Concurrency-safe inward number generator using row-level locking (`FOR UPDATE`) + collision check within the active transaction. |
| **DEF-7-03** | Legacy C# uses `double` / `Convert.ToDouble()` for premium, GST, TDS, and commission calculations. | Binary floating-point rounding drift (`0.01`–`1.00` ₹ discrepancies). | 100% `Decimal` arithmetic (`ROUND_HALF_UP`) across all schemas, services, repositories, and SQLAlchemy `Double(asdecimal=True)` columns. |
| **DEF-7-04** | No idempotency check on policy booking (`btn_Submit` double-click or retry creates duplicate `tbl_transaction` and double-posts accounting ledger entries). | Duplicate policy bookings and double commission liabilities. | Enforced uniqueness checks on `(PolicyNo, InsuranceCompanyId)` when `PolicyNo` is issued, single-consumption lock on `QuatationCode` / `TransId`, and optional `idempotency_key` deduplication. |
| **DEF-7-05** | `Service.asmx.cs::InsertAppTransactionNew` trusts caller-supplied `AgentId`, `SalesExecutiveId`, `FranchaiseId`, and `BranchId`. | Cross-agent/cross-branch spoofing (IDOR). | Enforced server-resolved `PrincipalContext` (`app/core/rbac.py`) so Agents, RMs, and Franchises are strictly bound to their authenticated identity. |
