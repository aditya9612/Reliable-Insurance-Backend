# 15 — Legacy Atomicity, Idempotency & Concurrency Baseline

> **Forensic Classification**: `CONFIRMED FROM CODE`  
> **Scope**: Database transaction boundaries, multi-step mutation failure modes, duplicate submission protection, and thread/concurrency hazards across `DAL_Operations.cs`, `Service.asmx.cs`, and ASP.NET WebForms pages.

---

## 1. Executive Summary of Transaction Architecture

| Architectural Dimension | Confirmed Legacy Behavior | Code Evidence |
|---|---|---|
| **ADO.NET `MySqlTransaction` (`conn.BeginTransaction()`)** | **0 usages across entire codebase** | `DAL_Operations.cs` (1,896 SP invocations), `Service.asmx.cs` (442 SP invocations) |
| **`System.Transactions.TransactionScope`** | **0 usages across entire codebase** | Entire solution (`*.cs`) |
| **Connection Lifecycle per DAL Method** | Every `DAL_*` method calls `conn.Open()`, executes a single `MySqlCommand`, and calls `conn.Close()` in `finally` | `DAL_Operations.cs` L15–L124758 |
| **Stored Procedure Internal Transactions (`START TRANSACTION` / `COMMIT`)** | `UNKNOWN — EVIDENCE NOT AVAILABLE` (SP SQL bodies reside exclusively in the external MySQL server) | N/A |
| **Static Page-Level Mutable Fields (`static` on `System.Web.UI.Page`)** | **Confirmed Thread-Safety Defect** across multiple WebForms pages (`CL_ClaimNew.aspx.cs`, `adm_VehicleDetails.aspx.cs`, `adm_TransactionEntry.aspx.cs`) | See Section 4 |

---

## 2. Multi-Step Non-Atomic Mutation Chains (Partial Failure Hazards)

Because every `BLL_*` / `DAL_*` call opens and closes its own independent auto-committed MySQL connection, any multi-step workflow in C# code-behind or `Service.asmx.cs` is **non-atomic at the application tier**. If step $k$ fails or throws an exception, steps $1 \dots k-1$ remain permanently committed in MySQL.

### 2.1 Direct Policy Booking (`PolicyTransactionNew.aspx.cs` L1296–L1515)
**Sequence of Independent Auto-Committed DB Calls**:
1. `InsertCustomer()` (`PolicyTransactionNew.aspx.cs:L1401`) $\rightarrow$ `USP_InsertCustomer` (returns `CustomerId`)
2. `InsertCustVehicle()` (`PolicyTransactionNew.aspx.cs:L1458`) $\rightarrow$ `USP_InsertCustVehicle` (returns `VehicleId`)
3. `InsertTransaction()` (`PolicyTransactionNew.aspx.cs:L1515`) $\rightarrow$ `USP_InsertTransactionNew` (returns `TransactionId`)
4. `InsertTransactionDetails()` (`PolicyTransactionNew.aspx.cs:L1640`) $\rightarrow$ `USP_InsertTransationDetails` (inserts row per payment mode in `ViewState["PaymentDetails"]`)
5. `InsertAccount()` (`PolicyTransactionNew.aspx.cs:L1575`) $\rightarrow$ `USP_InsertAccountLedgerEntry` (inserts 6 sequential ledger rows: Customer Dr, Insurer Cr, Agent Cr, Franchise Cr, Company Cr, SubAgent Cr)
6. `InsertFranchiseDetails()` (`PolicyTransactionNew.aspx.cs:L1669`) $\rightarrow$ `USP_InsertFranchiseEwalletTrans` + `USP_UpdateFranchiseDepositBalance` (or `USP_InsertAgentCutandPayTransaction` + `USP_InsertLedgerDetails`)
7. `InsertTransactionPayment()` (`PolicyTransactionNew.aspx.cs:L1793`) $\rightarrow$ `USP_InsertTransactionPayment` + `USP_InsertLedgerDetails`
8. `UpdateTarget()` (`PolicyTransactionNew.aspx.cs:L1877`) $\rightarrow$ `USP_InsertTellyCallerAchievement` / `USP_UpdateTellyCallerAchievement`

**Partial Failure Impact**:
- If `USP_InsertTransactionNew` fails (e.g., timeout or constraint error), `tblcustomer` and `tblcustvehicle` rows are already committed, creating orphan Customer and Vehicle records.
- If the loop in `InsertAccount()` fails on the 4th ledger entry, the ledger is left **unbalanced** (Debits $\neq$ Credits).
- If `InsertFranchiseDetails()` fails after `InsertTransaction()`, the policy is booked with `PaymentMode = "E-Wallet"`, but the franchise wallet balance is never deducted.

---

### 2.2 Detailed Policy Entry (`PE_TransactionEntry.aspx.cs` L2700–L3150)
**Sequence of Independent Auto-Committed DB Calls**:
1. `USP_InsertCustomer_New` / `USP_UpdateCustomer`
2. `USP_InsertCustVehicleNew` / `USP_UpdateCustVehicle`
3. `USP_InsertTransaction` / `USP_UpdateTransaction`
4. `USP_DeleteTransationDetails` + loop of `USP_InsertTransationDetails`
5. `USP_DeleteAccountLedgerEntry` + 6 calls to `USP_InsertAccountLedgerEntry`
6. `USP_InsertTransactionHealthPortability` + `USP_InsertTransactionHealthMemberDetails` (for Health policies)
7. `USP_UpdateTargetAchieved` + `USP_UpdateRenewalPolicyStatus`

**Partial Failure Impact**:
- During an **Update** (`btnUpdate_Click`), `USP_DeleteAccountLedgerEntry` (`PE_TransactionEntry.aspx.cs:L2195`) deletes existing ledger entries *before* re-inserting the 6 new ledger rows. If an exception occurs mid-reinsertion, all prior accounting entries for that transaction are permanently lost or incomplete.

---

### 2.3 Accountant Policy Verification & Cut-and-Pay Approval (`adm_TransactionEntry.aspx.cs` L2009–L2250)
**Sequence of Independent Auto-Committed DB Calls**:
1. `USP_UpdateTransactionVerificationStatus` (`adm_TransactionEntry.aspx.cs:L2015`)
2. `USP_UpdateLedgerDetailsByTransactionId` / `USP_InsertLedgerDetails`
3. `USP_UpdateFranchiseDepositBalance` (if E-Wallet)
4. `USP_InsertAgentCommissionTDS`

**Partial Failure Impact**:
- Verification status (`TStatus = "Verified"`) can be committed even if the downstream TDS or wallet adjustment fails.

---

### 2.4 Voucher Entry (`adm_VoucherEntry.aspx.cs` L850–L1220)
**Sequence of Independent Auto-Committed DB Calls**:
1. `USP_InsertVoucherEntry` (inserts voucher header in `tblvoucherentry`, returns `VoucherId`)
2. `USP_InsertLedgerDetails` (Debit leg)
3. `USP_InsertLedgerDetails` (Credit leg)
4. Loop over checked invoices/policies: `USP_InsertVoucherBillDetails` + `USP_UpdateTransactionPaymentStatus`

**Partial Failure Impact**:
- If the Credit leg or bill allocation fails, a single-sided ledger entry remains in `tblledgerdetails`, corrupting the Trial Balance (`adm_TrialBalance.aspx.cs`).

---

### 2.5 Endorsement Approval (`AppEndorsementforApproval.aspx.cs` L205–L318)
**Sequence of Independent Auto-Committed DB Calls**:
1. `UpdateTransaction()` (`AppEndorsementforApproval.aspx.cs:L231`) $\rightarrow$ switches by `EndorsementId` (1–22) and calls `USP_UpdateCustNameByEndorsment`, `USP_UpdateVehicleRegNoByEndorsment`, `USP_UpdateHypothecationByEndorsment`, etc.
2. `USP_UpdateEndorsementStatus` (`AppEndorsementforApproval.aspx.cs:L302`) $\rightarrow$ sets `Status = "Approved"` on `tblendorsement`.

**Partial Failure Impact**:
- If `UpdateTransaction()` mutates the live policy/customer/vehicle record and `USP_UpdateEndorsementStatus` subsequently fails, the endorsement remains in `"Pending"` status while the underlying policy has already been modified.

---

### 2.6 NCB Recovery Entry (`adm_NcbRecovery.aspx.cs` L1076–L1350)
**Sequence of Independent Auto-Committed DB Calls**:
1. `BLL_InsertNcbTransaction` (`USP_InsertNcbTransaction`)
2. `BLL_UpdateTransByNCB` (`USP_UpdateTransByNCB`) — overwrites live policy premiums & commissions in `tbltransaction`
3. `BLL_InsertNcbTransactionPayment` (`USP_InsertNcbTransactionPayment`)
4. `BLL_InsertLedgerDetails` (`USP_InsertLedgerDetails`) — posts recovery accounting entries

---

## 3. Idempotency & Duplicate Submission Baseline

| Workflow / Endpoint | Legacy Idempotency Mechanism | Duplicate Submission Vulnerability | Evidence |
|---|---|---|---|
| **Direct Policy Booking (`PolicyTransactionNew.aspx.cs`)** | Checks `BLL_CheckPolicyNoExist(txtPolicyNo.Text)` only when `txtPolicyNo` changes or during validation (`L1190`); no unique DB transaction token or idempotency key on `btnSubmit_Click` (`L1296`). | **HIGH**: Double-clicking Submit or browser refresh before redirect can insert duplicate `Customer`, `Vehicle`, `Transaction`, and double-deduct `E-Wallet` balance if `PolicyNo` is blank/pending (`Inward`). | `PolicyTransactionNew.aspx.cs:L1190-L1515` |
| **Detailed Policy Entry (`PE_TransactionEntry.aspx.cs`)** | Checks duplicate PolicyNo via `USP_SelectPolicyNoExist`; no idempotency key on `btnSubmit_Click`. | **HIGH**: Concurrent postbacks can create duplicate inward transactions and duplicate ledger rows. | `PE_TransactionEntry.aspx.cs:L2700` |
| **NCB Recovery (`adm_NcbRecovery.aspx.cs`)** | **Explicit DB Check**: Calls `BLL_selectNcbrecoveryTransId(TransId, "Completed")` (`L1076`). Only inserts if `dt.Rows.Count == 0`. | **LOW/MEDIUM**: Protected against sequential re-submission after completion, though subject to TOCTOU race condition under simultaneous requests. | `adm_NcbRecovery.aspx.cs:L1076-L1085` |
| **Policy Cancellation (`adm_PolicyCancel.aspx.cs`)** | **Explicit DB Check**: Calls `BLL_SelectAccountantApprovalByPolicynoCancel` (`L825`) to block already-cancelled policies. | **LOW/MEDIUM**: Protected against sequential duplicate cancellation; TOCTOU race possible. | `adm_PolicyCancel.aspx.cs:L825-L840` |
| **Endorsement Approval (`AppEndorsementforApproval.aspx.cs`)** | Sets `btnApprove.Enabled = false;` *after* DB execution (`L208`, `L305`), and hides button during `GridView_RowDataBound` if `Status == "Approved"` (`L181`). | **MEDIUM**: Server-side handler `btnApprove_Click` does not re-query DB status before running `UpdateTransaction()`. Replay of POST request will re-run the mutation. | `AppEndorsementforApproval.aspx.cs:L181-L308` |
| **Claim Registration (`CL_ClaimNew.aspx.cs`)** | No uniqueness constraint on `(TransactionId, DateOfIncident)` checked before `USP_InsertClaimNew` (`L145`). | **HIGH**: Submitting the claim form twice creates two separate `ClaimId` records for the same incident. | `CL_ClaimNew.aspx.cs:L135-L215` |
| **ASMX WebMethods (`Service.asmx.cs`)** | Zero idempotency headers (`Idempotency-Key`) or request deduplication tokens across all 416 `[WebMethod]` endpoints. | **HIGH**: Network retries from mobile/web clients on POST mutations (`InsertQuotation`, `InsertEndorsement`, `InsertClaim`, `InsertPosWallet`) create duplicate records. | `Service.asmx.cs` |

---

## 4. Concurrency & Thread-Safety Hazards (`CONFIRMED FROM CODE`)

In ASP.NET WebForms, `static` fields declared on a `System.Web.UI.Page` subclass are shared across **all concurrent HTTP threads/requests** inside the IIS AppDomain worker process (`w3wp.exe`), NOT scoped to a single user or session.

### 4.1 Confirmed Thread-Unsafe `static` Fields in Page Classes

| File | Line(s) | Static Declarations | Concurrency Corruption Impact |
|---|---|---|---|
| `Clerk/CL_ClaimNew.aspx.cs` | L26–L28 | `private static int id, ClaimTypeId, temp_quotId, temp_FBId, tempFBID, TransId, CustId, VehId, InsCompId;` | If Clerk A opens Claim #101 and Clerk B opens Claim #202 concurrently, Clerk A's subsequent "Save Spot Survey" or "Update Claim" postback overwrites/updates **Claim #202** (`id`, `TransId`, `temp_FBId`). |
| `adm_VehicleDetails.aspx.cs` | L15–L17 | `public static int CustomerId, TransactionId, VehicleId;`<br>`public static string rr_Url;` | Concurrent vehicle edits cross-contaminate `CustomerId`, `TransactionId`, and `VehicleId` between different clerks/admins. |
| `adm_TransactionEntry.aspx.cs` | L26–L32 | Static state variables used during accountant verification | Concurrent accountant verifications can read or mutate another transaction's cached IDs. |
| `SelfQuotationRequest.aspx.cs` | L24–L30 | Static fields holding quotation state during multi-step wizard | Concurrent public users requesting quotations can overwrite each other's intermediate calculation state. |

### 4.2 E-Wallet Balance Race Condition (Lost Update / Double Spend)
- **File**: `PolicyTransactionNew.aspx.cs` (L1291–L1294 & L1669–L1695)
- **Mechanism**:
  1. Application reads current balance into `lblWalletBalance.Text` when franchise is selected (`USP_SelectFranchiseDepositBalance`).
  2. On Submit (`L1291`), C# checks `if (balance > Convert.ToInt32(txtPaymentAmt.Value))`.
  3. Later (`L1675`), C# computes the new balance in memory (`double newBal = balance - paymentAmt`) or passes the deduction to `USP_UpdateFranchiseDepositBalance`.
- **Hazard**: No `SELECT ... FOR UPDATE` row lock or optimistic concurrency version check exists at the application layer. Two concurrent policy bookings by the same franchise can both pass the balance check and overdraw the wallet.
