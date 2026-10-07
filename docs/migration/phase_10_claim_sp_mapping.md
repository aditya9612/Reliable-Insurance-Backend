# Phase 10 — Claim Stored Procedure Mapping (`phase_10_claim_sp_mapping.md`)

## 1. Overview
This document maps every legacy MySQL stored procedure and inline ADO.NET command used in the Claims module (`Clerk/ClaimEntry.aspx.cs`, `Clerk/ClaimStatusUpdate.aspx.cs`, `Service.asmx.cs`, `DownloadAll.ashx.cs`) to the new FastAPI / Async SQLAlchemy 2.x service and repository methods.

---

## 2. Stored Procedure to FastAPI Service Mapping Matrix

| Legacy Stored Procedure | Legacy Caller(s) | Legacy Tables Read / Written | New FastAPI Endpoint | New Service / Repository Method | Parity Behavior & Improvements |
|---|---|---|---|---|---|
| `sp_SelectPolicyByNo` / `sp_SelectTransactionById` | `Clerk/ClaimEntry.aspx.cs` | **R**: `tbl_transaction`, `tbl_customer`, `tbl_vehicledetails` | `POST /api/v1/claims` (pre-validation) | `ClaimsEndorsementRepository.get_policy_for_update` | Validates policy existence, active status (`PolicycancelId == 0`), coverage window (`PolicyStartDate <= LossDate <= PolicyEndDate`), and `ClaimType` compatibility. |
| `sp_InsertClaimDetails` | `Clerk/ClaimEntry.aspx.cs` | **W**: `tbl_claims` | `POST /api/v1/claims` | `ClaimsEndorsementService.intimate_claim` | Generates deterministic `ClaimNo` (`CLM-{BranchId}-{YYYY}-{Seq:06d}`), enforces idempotency via `IdempotencyKey` and `(TransanctionId, LossDate, ClaimType)`, and initializes `ClaimStatus = "INTIMATED"`. |
| `sp_InsertAppClaim` | `Service.asmx.cs::InsertAppClaim` | **W**: `tbl_claims` | `POST /api/v1/claims` | `ClaimsEndorsementService.intimate_claim` | Unified into the same validated claim intimation service with strict principal (`AgentId`/`FranchiseId`/`SalesExId`) and branch (`BranchId`) ownership enforcement. |
| `sp_UpdateClaimDetails` (Register / Survey) | `Clerk/ClaimEntry.aspx.cs`, `Clerk/ClaimStatusUpdate.aspx.cs` | **R/W**: `tbl_claims` | `POST /api/v1/claims/{claim_id}/register`<br>`POST /api/v1/claims/{claim_id}/survey` | `ClaimsEndorsementService.register_claim`<br>`ClaimsEndorsementService.update_survey` | Locks claim row (`SELECT ... FOR UPDATE`), validates state transition (`INTIMATED -> REGISTERED -> UNDER_SURVEY`), and records surveyor details (`SurveyorName`, `SurveyorLicenseNo`, `SurveyDate`). |
| `sp_UpdateClaimDetails` (Assess / Approve) | `Clerk/ClaimStatusUpdate.aspx.cs` | **R/W**: `tbl_claims`, **R**: `tbl_transaction` | `POST /api/v1/claims/{claim_id}/assess`<br>`POST /api/v1/claims/{claim_id}/approve` | `ClaimsEndorsementService.assess_claim`<br>`ClaimsEndorsementService.approve_claim` | Computes exact `ApprovedAmount = max(0, AssessedLossAmount - DepreciationAmount - DeductibleAmount - ExcessAmount - SalvageAmount)`, enforces `ApprovedAmount <= SumInsured` for OD/Theft/Total Loss, and transitions to `ASSESSED` / `APPROVED`. |
| `sp_UpdateClaimDetails` (Reject / Reopen) | `Clerk/ClaimStatusUpdate.aspx.cs` | **R/W**: `tbl_claims` | `POST /api/v1/claims/{claim_id}/reject`<br>`POST /api/v1/claims/{claim_id}/reopen` | `ClaimsEndorsementService.reject_claim`<br>`ClaimsEndorsementService.reopen_claim` | Enforces mandatory `RejectionReason` on rejection and audit `Remarks` on reopen (`REJECTED`/`CLOSED` -> `REOPENED` -> `UNDER_SURVEY`/`ASSESSED`). |
| `sp_UpdateClaimDetails` + `sp_InsertAccountTransaction` (Settle / Close / Reverse) | `Clerk/ClaimStatusUpdate.aspx.cs` | **R/W**: `tbl_claims`, `tbl_account` | `POST /api/v1/claims/{claim_id}/settle`<br>`POST /api/v1/claims/{claim_id}/close`<br>`POST /api/v1/claims/{claim_id}/reverse-settlement` | `ClaimsEndorsementService.settle_claim`<br>`ClaimsEndorsementService.close_claim`<br>`ClaimsEndorsementService.reverse_claim_settlement` | Atomically records settlement payout (`SettledAmount <= ApprovedAmount`), posts balanced double-entry accounting rows (`AccTransId = 15` on settlement, `AccTransId = 16` on reversal) in `tbl_account`, and transitions status (`APPROVED -> SETTLED -> CLOSED`). |
| `sp_SelectClaims` | `Clerk/ClaimStatusUpdate.aspx.cs`, `Service.asmx.cs::GetClaimListByAgent` | **R**: `tbl_claims`, `tbl_transaction`, `tbl_customer`, `tbl_vehicledetails` | `GET /api/v1/claims`<br>`GET /api/v1/claims/{claim_id}` | `ClaimsEndorsementService.list_claims`<br>`ClaimsEndorsementService.get_claim` | Enforces role/branch/principal visibility filters (`BranchId`, `AgentId`, `FranchiseId`, `SalesExId`). |
| `sp_InsertClaimDocument` / `sp_SelectDocumentsByTransId` | `Clerk/ClaimEntry.aspx.cs`, `DownloadAll.ashx.cs` | **R/W**: `tbl_claimdocument` | `POST /api/v1/claims/{claim_id}/documents`<br>`GET /api/v1/claims/{claim_id}/documents` | `ClaimsEndorsementService.attach_claim_document`<br>`ClaimsEndorsementService.list_claim_documents` | Validates safe `StorageKey` (rejects raw filesystem paths and `..` traversal) and records document verification status. |

---

## 3. Parameter-Level Mapping (`sp_InsertClaimDetails` & `sp_UpdateClaimDetails`)

| Legacy SP Parameter | Legacy SQL Type | FastAPI Schema Field | Target Column (`tbl_claims`) | Validation & Transformation Rule |
|---|---|---|---|---|
| `@TransanctionId` | `INT` | `transaction_id` | `TransanctionId` | Must exist in `tbl_transaction` (`isdeleted = "0"`, `PolicycancelId = 0`). |
| `@ClaimType` | `VARCHAR(30)` | `claim_type` | `ClaimType` | Enum: `OD`, `TP`, `THEFT`, `TOTAL_LOSS`. Validated against policy OD/TP coverage. |
| `@LossDate` | `DATETIME` | `loss_date` | `LossDate` | Must satisfy `PolicyStartDate <= LossDate <= PolicyEndDate`. |
| `@IntimationDate` | `DATETIME` | `intimation_date` | `IntimationDate` | Must satisfy `IntimationDate >= LossDate`. |
| `@EstimatedAmount` | `DECIMAL(18,2)` | `estimated_amount` | `EstimatedAmount` | Must be `> 0.00`. Quantized to `0.01` (`ROUND_HALF_UP`). |
| `@AssessedLossAmount` | `DECIMAL(18,2)` | `assessed_loss_amount` | `AssessedLossAmount` | Must be `> 0.00`. |
| `@DepreciationAmount` | `DECIMAL(18,2)` | `depreciation_amount` | `DepreciationAmount` | Must be `>= 0.00`. |
| `@DeductibleAmount` | `DECIMAL(18,2)` | `deductible_amount` | `DeductibleAmount` | Must be `>= 0.00` (compulsory/voluntary deductible). |
| `@ExcessAmount` | `DECIMAL(18,2)` | `excess_amount` | `ExcessAmount` | Must be `>= 0.00` (policy excess). |
| `@SalvageAmount` | `DECIMAL(18,2)` | `salvage_amount` | `SalvageAmount` | Must be `>= 0.00` (wreck/salvage deduction). |
| `@ApprovedAmount` | `DECIMAL(18,2)` | `approved_amount` (computed/validated) | `ApprovedAmount` | `max(0.00, AssessedLossAmount - DepreciationAmount - DeductibleAmount - ExcessAmount - SalvageAmount)`. |
| `@SettledAmount` | `DECIMAL(18,2)` | `settled_amount` | `SettledAmount` | Must be `> 0.00` and `<= ApprovedAmount`. |
| `@PayeeType` | `VARCHAR(30)` | `payee_type` | `PayeeType` | `CUSTOMER` (reimbursement), `GARAGE` (cashless), or `INSURER` (direct insurer settlement). |
