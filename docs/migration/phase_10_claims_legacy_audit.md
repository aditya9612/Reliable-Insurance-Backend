# Phase 10 — Legacy Claims Audit (`phase_10_claims_legacy_audit.md`)

## 1. Executive Summary & Audit Scope
This document records the Stage A read-only audit of the legacy C# / ASP.NET WebForms (`Clerk/`), ASMX (`Service.asmx.cs`), ASHX (`DownloadAll.ashx.cs`), and MySQL stored procedure layer for **Motor Insurance Claims Management**.

In accordance with **Production Safety — Absolute**, this audit was performed strictly against local repository evidence (`docs/migration/`, `app/models/`) without connecting to or querying `brahmainsurance`.

---

## 2. Legacy Claims Entry Points Inventory

| Legacy File / Handler | Method / Event | Legacy Stored Procedure / SQL | Purpose & Business Role |
|---|---|---|---|
| `Clerk/ClaimEntry.aspx.cs` | `btnSearchPolicy_Click` | `sp_SelectPolicyByNo` / `sp_SelectTransactionById` | Looks up an active/booked motor policy in `tbl_transaction`, `tbl_customer`, and `tbl_vehicledetails` to validate policy eligibility and loss date coverage window (`PolicyStartDate <= LossDate <= PolicyEndDate`). |
| `Clerk/ClaimEntry.aspx.cs` | `btnSubmitClaim_Click` | `sp_InsertClaimDetails` | Creates a new Motor Claim Intimation (`ClaimNo`, `TransanctionId`, `PolicyNo`, `CustomerId`, `CustVehId`, `ClaimType`, `LossDate`, `IntimationDate`, `EstimatedAmount`, `LossLocation`, `LossDescription`). |
| `Clerk/ClaimEntry.aspx.cs` | `btnAssignSurveyor_Click` | `sp_UpdateClaimDetails` | Records surveyor assignment (`SurveyorName`, `SurveyorMobile`, `SurveyorLicenseNo`, `SurveyDate`) and transitions claim status to `UNDER_SURVEY`. |
| `Clerk/ClaimStatusUpdate.aspx.cs` | `btnUpdateAssessment_Click` | `sp_UpdateClaimDetails` | Records loss assessment (`AssessedLossAmount`, `DepreciationAmount`, `DeductibleAmount`, `ExcessAmount`, `SalvageAmount`), calculates `ApprovedAmount`, and transitions status to `ASSESSED` / `APPROVED`. |
| `Clerk/ClaimStatusUpdate.aspx.cs` | `btnSettleClaim_Click` | `sp_UpdateClaimDetails` + `sp_InsertAccountTransaction` | Records claim settlement (`SettledAmount`, `PayeeType`, `PaymentMode`, `PaymentDocNo`, `SettlementDate`, `InsurerClaimRef`), posts accounting entries to `tbl_account`, and transitions status to `SETTLED` / `CLOSED`. |
| `Clerk/ClaimStatusUpdate.aspx.cs` | `btnRejectClaim_Click` / `btnReopenClaim_Click` | `sp_UpdateClaimDetails` | Rejects a claim with mandatory `RejectionReason` or reopens a previously `REJECTED` / `CLOSED` claim with audit remarks. |
| `Service.asmx.cs` | `InsertAppClaim` | `sp_InsertAppClaim` | Mobile/partner portal claim intimation submission by an Agent, Franchise, or Sales Executive for a policy within their ownership scope. |
| `Service.asmx.cs` | `GetClaimListByAgent` | `sp_SelectClaims` | Lists claims scoped to the calling Agent/Franchise/Branch. |
| `DownloadAll.ashx.cs` | `ProcessRequest` | `sp_SelectDocumentsByTransId` | Retrieves supporting claim documents (`FIR`, `RC`, `DL`, `CLAIM_FORM`, `ESTIMATE`, `REPAIR_INVOICE`, `SURVEY_REPORT`, `DISCHARGE_VOUCHER`, `PHOTO`) linked via `tbl_claimdocument`. |

---

## 3. Physical Schema & Entity Mapping

### 3.1 `tbl_claims` (`Claim` Model)
Stores the master lifecycle, loss details, surveyor assessment, financial breakdown, and settlement details for motor insurance claims.
- **Primary Key**: `ClaimId` (`INT AUTO_INCREMENT`)
- **Unique Identifier**: `ClaimNo` (`VARCHAR(50)`, format `CLM-{BranchId}-{YYYY}-{Seq:06d}`)
- **Policy & Entity Foreign Keys**:
  - `TransanctionId` (`INT`, FK to `tbl_transaction.TransanctionId`)
  - `PolicyNo` (`VARCHAR(100)`)
  - `CustomerId` (`INT`, FK to `tbl_customer.CustomerId`)
  - `CustVehId` (`INT`, FK to `tbl_vehicledetails.CustVehId`)
  - `InsuranceCompanyId` (`INT`)
  - `BranchId` (`INT`)
  - `AgentId` (`INT`)
  - `FranchiseId` (`INT`)
  - `SalesExId` (`INT`)
- **Claim Classification & Status**:
  - `ClaimType`: `OD` (Own Damage), `TP` (Third Party), `THEFT`, `TOTAL_LOSS`
  - `ClaimStatus`: `INTIMATED`, `REGISTERED`, `UNDER_SURVEY`, `ASSESSED`, `APPROVED`, `SETTLED`, `CLOSED`, `REJECTED`, `CANCELLED`, `REOPENED`
- **Loss & Intimation Attributes**:
  - `IntimationDate` (`DATETIME`), `LossDate` (`DATETIME`), `LossLocation` (`VARCHAR(255)`), `LossDescription` (`TEXT`), `EstimatedAmount` (`DECIMAL(18,2)`)
- **Survey & Assessment Attributes**:
  - `SurveyorName` (`VARCHAR(150)`), `SurveyorMobile` (`VARCHAR(20)`), `SurveyorLicenseNo` (`VARCHAR(50)`), `SurveyDate` (`DATETIME`)
  - `AssessedLossAmount` (`DECIMAL(18,2)`), `DepreciationAmount` (`DECIMAL(18,2)`), `DeductibleAmount` (`DECIMAL(18,2)`), `ExcessAmount` (`DECIMAL(18,2)`), `SalvageAmount` (`DECIMAL(18,2)`)
- **Approval & Settlement Attributes**:
  - `ApprovedAmount` (`DECIMAL(18,2)`), `SettledAmount` (`DECIMAL(18,2)`), `InsurerPayableAmount` (`DECIMAL(18,2)`), `CustomerPayableAmount` (`DECIMAL(18,2)`), `GaragePayableAmount` (`DECIMAL(18,2)`)
  - `PayeeType` (`CUSTOMER`, `GARAGE`, `INSURER`), `PaymentMode` (`NEFT`, `CHEQUE`, `INSURER_DIRECT`, `CASH`), `PaymentDocNo` (`VARCHAR(100)`), `SettlementDate` (`DATETIME`), `InsurerClaimRef` (`VARCHAR(100)`)
- **Audit & Idempotency**:
  - `RejectionReason` (`VARCHAR(500)`), `Remarks` (`TEXT`), `IdempotencyKey` (`VARCHAR(100)`), `isdeleted` (`VARCHAR(1)` default `"0"`), `CreateDate`, `CreateUser`, `UpdateDate`, `UpdateUser`.

### 3.2 `tbl_claimdocument` (`ClaimDocument` Model)
Stores metadata and safe object storage keys for claim documents.
- **Primary Key**: `ClaimDocId` (`INT AUTO_INCREMENT`)
- **Foreign Keys**: `ClaimId` (`INT`), `TransanctionId` (`INT`)
- **Attributes**: `DocumentType` (`FIR`, `RC`, `DL`, `CLAIM_FORM`, `ESTIMATE`, `REPAIR_INVOICE`, `SURVEY_REPORT`, `DISCHARGE_VOUCHER`, `PHOTO`), `DocumentName` (`VARCHAR(255)`), `StorageKey` (`VARCHAR(500)` — safe storage key; raw disk paths like `D:\Inetpub\...` are strictly rejected), `VerifiedStatus` (`PENDING`, `VERIFIED`, `REJECTED`), `Remarks`, `isdeleted` (`"0"`/`"1"`), `CreateDate`, `CreateUser`.

---

## 4. Legacy Eligibility & Validation Rules

1. **Active Booked Policy Requirement**:
   - Claims can only be intimated against a non-deleted policy (`tbl_transaction.isdeleted == "0"`) with a valid `PolicyNo` that is not cancelled (`PolicycancelId == 0` and `TStatus != "CANCELLED"`).
2. **Coverage Period Check**:
   - `LossDate` must fall within the policy coverage window (`PolicyStartDate <= LossDate <= PolicyEndDate`).
   - `IntimationDate` must be `>= LossDate`.
3. **Policy Type vs Claim Type Compatibility**:
   - A `TP`-only (Liability/Act Only) policy (`ODPermium == 0` and `TPPermium > 0`) cannot accept an `OD` (Own Damage), `THEFT`, or `TOTAL_LOSS` claim (`422 Unprocessable Entity`).
   - An `OD`-only (Standalone Own Damage) policy (`TPPermium == 0` and `ODPermium > 0`) cannot accept a `TP` (Third Party Liability) claim (`422 Unprocessable Entity`).
   - A `Comprehensive` / `Package` policy can accept `OD`, `TP`, `THEFT`, or `TOTAL_LOSS` claims.
4. **Sum Insured (IDV) Cap on Own Damage / Total Loss / Theft**:
   - For `OD`, `THEFT`, and `TOTAL_LOSS` claims, the `ApprovedAmount` and `SettledAmount` cannot exceed the policy's `SumInsured` (IDV) recorded on `tbl_transaction.SumInsured` (when `SumInsured > 0`).
5. **Duplicate Active Claim Guard**:
   - Identical `(TransanctionId, LossDate, ClaimType)` intimations or replays with the same `IdempotencyKey` are deduplicated without creating duplicate `tbl_claims` rows.

---

## 5. Out-of-Scope / Zero-Row Legacy Artifacts
- As established in Phase 6 (`docs/migration/phase_6_quotation_legacy_audit.md` §1.3), `tbl_claim_quotation` and `tbl_claim_quotation_img` had `0` rows in the legacy database snapshot and are unused dead tables. Active claim operations exclusively use `tbl_claims`, `tbl_claimdocument`, `tbl_transaction`, and `tbl_account`.
