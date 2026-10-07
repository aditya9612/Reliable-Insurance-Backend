# Phase 10 — Policy Modification & Field Allowlist Rules (`phase_10_policy_modification.md`)

## 1. Overview
This document defines the strict field allowlist, immutable policy field guards, and `before`/`after` audit trail rules when applying an endorsement to `tbl_transaction`, `tbl_customer`, and `tbl_vehicledetails`.

---

## 2. Endorsement Types & Allowed Target Fields Matrix

Any attempt to modify a field not explicitly permitted for the requested `EndorsementType` is rejected with `422 Unprocessable Entity`.

| EndorsementType | Category | Target Table(s) | Allowed Modifiable Fields (`field_changes` keys) | Financial Recalculation (`IsRecalculate`) |
|---|---|---|---|---|
| `NAME_CORRECTION` | `NON_FINANCIAL` | `tbl_customer` | `CustFName`, `CustMName`, `CustLName`, `PanNo`, `GSTNo` | `0` (No premium change) |
| `ADDRESS_CORRECTION` | `NON_FINANCIAL` | `tbl_customer` | `Address` | `0` (No premium change) |
| `CONTACT_CORRECTION` | `NON_FINANCIAL` | `tbl_customer` | `MoblieNo1`, `EMailId` | `0` (No premium change) |
| `VEHICLE_REGISTRATION_CORRECTION` | `NON_FINANCIAL` | `tbl_vehicledetails` | `RegistrationNo`, `MfgYear` | `0` (No premium change) |
| `ENGINE_CHASSIS_CORRECTION` | `NON_FINANCIAL` | `tbl_vehicledetails` | `EngineNo`, `ChaiseNo` | `0` (No premium change) |
| `HYPOTHECATION_CHANGE` | `NON_FINANCIAL` | `tbl_vehicledetails` | `Financer`, `FinancerBranch` | `0` (No premium change) |
| `NOMINEE_CHANGE` | `NON_FINANCIAL` | `tbl_transaction` | `NomineeName`, `NomineeRelation`, `NomineeAge` (stored in `CorrectionText`/`UpdateEntryRemark` & `FieldChangesJson`) | `0` (No premium change) |
| `IDV_CHANGE` | `ADDITIONAL_PREMIUM` / `REFUND_PREMIUM` | `tbl_transaction` | `SumInsured`, `ODPermium`, `NCBPermium` | `1` (Recalculates OD, Net, GST, Final, Commission) |
| `NCB_CORRECTION` | `ADDITIONAL_PREMIUM` / `REFUND_PREMIUM` | `tbl_transaction` | `NCB`, `NCBPermium`, `ODPermium` | `1` (Recalculates NCB discount, OD, Net, GST, Final, Commission) |
| `COVERAGE_ADDON_CHANGE` | `ADDITIONAL_PREMIUM` / `REFUND_PREMIUM` | `tbl_transaction` | `AddOn`, `TowingChargesAmt`, `PACovertoOwner`, `PACoverDriverCleaner`, `LegalLiabilitytoPaidDriver`, `RoadSidePremium`, `ODPermium`, `TPPermium` | `1` (Recalculates AddOn/OD/TP, Net, GST, Final, Commission) |
| `OWNERSHIP_TRANSFER` | `ADDITIONAL_PREMIUM` / `NON_FINANCIAL` | `tbl_customer`, `tbl_transaction` | `CustFName`, `CustMName`, `CustLName`, `MoblieNo1`, `EMailId`, `Address`, `NCB`, `NCBPermium`, `ODPermium` | `0` or `1` (If NCB is recovered on ownership transfer, recalculates OD, Net, GST, Final, Commission) |

---

## 3. Strictly Immutable Fields (Forbidden in Endorsements)
The following core identity and historical fields **cannot** be altered via an endorsement (`422 Unprocessable Entity`):
- `TransanctionId`, `PolicyNo` (Primary key & insurer policy identifier)
- `CustomerId`, `CustVehId` (Entity foreign keys)
- `BranchId`, `AgentId`, `FranchiseId`, `SalesExId` (Ownership & channel hierarchy)
- `InsuranceCompanyId` (Underwriting insurer)
- `PolicyStartDate`, `PolicyEndDate` (Policy coverage term)
- `PolicycancelId`, `isdeleted` (Cancellation/deletion flags)

---

## 4. `tbl_transaction` Audit Stamp Rules
When `apply_endorsement` executes on `tbl_transaction`:
1. `UpdateEntryStatus = 1`
2. `IsRecalculate = 1` if `PremiumDelta != 0.00` or any rating/premium field changed; otherwise preserves existing `IsRecalculate`.
3. `UpdateEntryRemark` is appended/populated with:
   `"{EndorsementNo} [{EndorsementType}]: {Remarks}"`
4. `CorrectionText` (capped at 300 chars) is populated with a deterministic summary of `field: old -> new`.
5. On `reverse_endorsement`, all modified fields in `tbl_customer`, `tbl_vehicledetails`, and `tbl_transaction` are restored from the `before` snapshot stored in `tbl_appendorsement.FieldChangesJson`.
