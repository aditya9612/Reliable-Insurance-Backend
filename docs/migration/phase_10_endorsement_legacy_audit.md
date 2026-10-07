# Phase 10 — Legacy Endorsement & Policy Modification Audit (`phase_10_endorsement_legacy_audit.md`)

## 1. Executive Summary & Audit Scope
This document records the Stage A read-only audit of the legacy C# / ASP.NET WebForms (`Clerk/`), ASMX (`Service.asmx.cs`), and MySQL stored procedure layer for **Policy Endorsements, Mid-Term Modifications, Premium Recalculations, Commission Adjustments, and Refunds**.

In accordance with **Production Safety — Absolute**, this audit was performed strictly against local repository evidence (`docs/migration/`, `app/models/`) without connecting to or querying `brahmainsurance`.

---

## 2. Legacy Endorsement & Policy Modification Entry Points

| Legacy File / Handler | Method / Event | Legacy Stored Procedure / SQL | Purpose & Business Role |
|---|---|---|---|
| `Clerk/EndorsementEntry.aspx.cs` | `btnSubmitEndorsement_Click` | `sp_InsertEndorsement` | Creates a formal policy endorsement request (`EndorsementNo`, `TransanctionId`, `EndorsementType`, `FieldChangesJson`, old/new premium snapshot, remarks). |
| `Clerk/EndorsementEntry.aspx.cs` | `btnApproveApply_Click` | `sp_UpdateEndorsementStatus`, `sp_UpdateTransactionNew_2026`, `sp_UpdateCustomer`, `Sp_UpdateVehicleDetails` | Approves and applies an endorsement to `tbl_transaction`, `tbl_customer`, and `tbl_vehicledetails`; sets `UpdateEntryStatus = 1`, `UpdateEntryRemark`, `CorrectionText`, and `IsRecalculate = 1` (for financial endorsements). |
| `Clerk/AppEndorsementList.aspx.cs` | `gvEndorsements_RowCommand` | `sp_SelectEndorsementList`, `sp_UpdateEndorsementStatus` | Back-office queue for reviewing, approving, or rejecting endorsement requests stored in `tbl_appendorsement`. |
| `Service.asmx.cs` | `InsertAppEndorsement` | `sp_InsertAppEndorsement` | Mobile/partner portal endpoint allowing Agents, Franchises, and Sales Executives to submit endorsement requests with supporting document keys. |
| `Clerk/PolicyTransactionNew.aspx.cs` | `btnUpdate_Click` | `sp_UpdateTransactionNew_2026` | Underwriting modification of `tbl_transaction` fields (`ODPermium`, `TPPermium`, `NetPermium`, `GST_Amount`, `Amount`, `SumInsured`, `NCB`, `AgentCommAmt_OD`, etc.) and recalculation of commission/accounting rows. |

---

## 3. Physical Schema & Column Audit

### 3.1 Existing Endorsement / Modification Columns on `tbl_transaction` (`app/models/transaction.py`)
The legacy `tbl_transaction` table already contains dedicated columns for tracking policy modifications and endorsements:
- `IsRecalculate` (`INT`, not null, default `0`) — set to `1` whenever an endorsement or underwriting update recalculates policy premium and commission.
- `UpdateEntryStatus` (`INT`, not null, default `0`) — set to `1` when a post-issuance modification/endorsement has been applied to the transaction.
- `UpdateEntryRemark` (`TEXT`, nullable) — audit trail of the endorsement number, type, and summary of modified fields.
- `CorrectionText` (`VARCHAR(300)`, nullable) — concise summary of corrected fields (`before -> after`).
- `PolicycancelId` (`INT`, not null, default `0`) — non-zero if policy is cancelled (cancelled policies cannot be endorsed).

### 3.2 `tbl_appendorsement` (`PolicyEndorsement` Model)
Stores the full lifecycle, before/after field snapshot, before/after premium breakdown, before/after commission breakdown, and refund/additional collection linkage for every policy endorsement.
- **Primary Key**: `EndorsementId` (`INT AUTO_INCREMENT`)
- **Unique Identifier**: `EndorsementNo` (`VARCHAR(50)`, format `END-{BranchId}-{YYYY}-{Seq:06d}`)
- **Foreign Keys**: `TransanctionId`, `PolicyNo`, `CustomerId`, `CustVehId`, `BranchId`, `AgentId`, `FranchiseId`, `SalesExId`
- **Classification & Status**:
  - `EndorsementType`:
    1. `NAME_CORRECTION` (Non-Financial)
    2. `ADDRESS_CORRECTION` (Non-Financial)
    3. `CONTACT_CORRECTION` (Non-Financial)
    4. `VEHICLE_REGISTRATION_CORRECTION` (Non-Financial)
    5. `ENGINE_CHASSIS_CORRECTION` (Non-Financial)
    6. `HYPOTHECATION_CHANGE` (Non-Financial)
    7. `NOMINEE_CHANGE` (Non-Financial)
    8. `IDV_CHANGE` (Financial — Premium Bearing)
    9. `NCB_CORRECTION` (Financial — Premium Bearing)
    10. `COVERAGE_ADDON_CHANGE` (Financial — Premium Bearing)
    11. `OWNERSHIP_TRANSFER` (Financial or Non-Financial — NCB recovery / transfer fee)
  - `EndorsementCategory`: `NON_FINANCIAL`, `ADDITIONAL_PREMIUM`, `REFUND_PREMIUM`, `ZERO_PREMIUM`
  - `EndorsementStatus`: `DRAFT`, `SUBMITTED`, `APPROVED`, `APPLIED`, `REJECTED`, `CANCELLED`, `REVERSED`
- **Field & Financial Audit Snapshot**:
  - `FieldChangesJson` (`TEXT` — JSON object containing `{"before": {...}, "after": {...}}` for every modified field)
  - Premium snapshot: `OldODPremium`, `NewODPremium`, `OldTPPremium`, `NewTPPremium`, `OldNetPremium`, `NewNetPremium`, `OldGSTAmount`, `NewGSTAmount`, `OldFinalPremium`, `NewFinalPremium`, `PremiumDelta`
  - Rating factors snapshot: `OldNCBPercent`, `NewNCBPercent`, `OldIDV`, `NewIDV`
  - Commission snapshot: `OldAgentNetComm`, `NewAgentNetComm`, `AgentCommDelta`, `OldAgentTdsAmt`, `NewAgentTdsAmt`, `OldFranchiseNetComm`, `NewFranchiseNetComm`, `FranchiseCommDelta`, `CommissionRecoveryAmount`
  - Refund / Collection linkage: `RefundId`, `RefundStatus` (`NONE`, `PENDING_APPROVAL`, `APPROVED`, `REFUNDED`, `REVERSED`), `RefundAmount`, `RefundMode`, `RefundDocNo`.

---

## 4. Key Legacy Endorsement Business Rules
1. **No Endorsement on Cancelled or Deleted Policy**:
   - If `tbl_transaction.isdeleted != "0"` or `tbl_transaction.PolicycancelId != 0` or `tbl_transaction.TStatus == "CANCELLED"`, creating or applying an endorsement is strictly rejected (`409 Conflict`).
2. **Single Pending Conflicting Endorsement Guard**:
   - While an endorsement is in `SUBMITTED` or `APPROVED` (unapplied) state for a policy, a conflicting financial endorsement on the same policy cannot be applied out of order.
3. **Immutable Audit Trail**:
   - Every endorsement stores exact `before` and `after` values in `FieldChangesJson` plus explicit old/new numeric columns on `tbl_appendorsement`, and updates `tbl_transaction.UpdateEntryStatus = 1`, `UpdateEntryRemark`, and `CorrectionText`.
