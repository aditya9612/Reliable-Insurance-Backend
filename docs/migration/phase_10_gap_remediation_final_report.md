# Phase 0 → Phase 10 Legacy Parity Gap Remediation Final Report

**Repository**: `Reliable-Insurance-Backend`  
**Audit & Remediation Date**: `2026-10-07`  
**Runtime Target**: `localhost:3306/reliable_insurance_dev` & `localhost:6379` (100% synthetic fixtures; zero production access)  
**Final Post-Remediation Verdict**: **`GREEN — VERIFIED LEGACY PARITY (WITH DOCUMENTED HARDENING)`**

---

## 1. Executive Summary

Following the independent forensic audit of `Reliable-Insurance-Backend` against the read-only `InsurancefinalNew` C#/.NET 4.0 baseline (`docs/migration/legacy_baseline/`), every reported gap across `P0`, `P1`, `P2`, `P3`, and `UNKNOWN` was independently verified against legacy source evidence, stored procedure definitions, and the new FastAPI implementation.

- **Confirmed & Remediated Gaps (`8` total)**:
  - **`P0`**: `GAP-P10-001` (`LBR-123` Zero-Ledger-Impact Claim Settlement & Reversal)
  - **`P1`**: `GAP-P6-001` (`LBR-036`/`LBR-071` `2025-09-23` GCV Basic TP GST `5%` vs `12%` Cutover), `GAP-P10-002` (`LBR-057`, `LBR-065`..`070`, `LBR-096`, `LBR-115`..`119`, `LBR-129` Canonical `AccTransId` & System `LedgerMId` `1161`, `2113`, `1930`, `1878`), `GAP-P10-003` (`LBR-126`..`128` 22-Subtype Endorsement Catalog, `NCB_RECOVERY`, & `OwnerTransferEndorsement.aspx.cs` New Customer Creation)
  - **`P2`**: `GAP-P7-001` (`LBR-047`/`LBR-051` GCV + HDFC ERGO Net-Only Commission & `IsQualityCheck = 0` for Insurer `(3, 32)`), `GAP-P7-002` (`LBR-107`/`LBR-061` Non-Motor `15%` Default TDS & `CustVehId = 500` Cancellation Sentinel Option), `GAP-P6-002` (`LBR-028` GCV Extra Weight Loading C# Integer Division), `GAP-P10-004` (`LBR-123` `FinalBill` `BillAmt`, `ICLAmt`, `ILAmt`)
- **Verified Intentional Hardenings / Mitigated Legacy Defects (`7` total — Preserved Without Regressing Security or Accounting Integrity)**:
  - `GAP-P8-001` (`DEF-006`), `GAP-P7-003` (`DEF-004`), `GAP-P7-004` (`DEF-005`), `GAP-P5-001` (`DEF-001`, `DEF-002`), `GAP-P5-002` (`DEF-008`), `GAP-P5-003` (`DEF-011`), `GAP-P11-001` (`DEF-010`)
- **Explicitly Preserved `UNKNOWN` Items (`3` total — Zero Code Fabricated)**:
  - `GAP-UNK-001` (`sp_InsertSelfQuotation_Missing1`), `GAP-UNK-002` (`sp_Unreconciled_Comm_Report`), `GAP-UNK-003` (External Payment Gateway `PayU`/`Razorpay` Webhook Specification)

---

## 2. Detailed Remediation Summary by Priority

### 2.1 `P0 — GAP-P10-001`: Claim Settlement & Reversal Zero Ledger Impact (`LBR-123`)
- **Root Cause**: `ClaimsEndorsementService.settle_claim` and `reverse_claim_settlement` previously wrote synthetic `AccTransId = 15` (`CLAIM_SETTLEMENT`) and `AccTransId = 16` (`CLAIM_SETTLEMENT_REVERSAL`) rows into `tbl_account`. In legacy `Clerk/Claims.aspx.cs` and `Clerk/FinalBill.aspx.cs` (`Sp_InsertClaim`, `Sp_UpdateClaim`, `sp_UpdateFinalBill`), claims are tracked exclusively in `tbl_claims` (`tbl_claim`) because insurers settle claims directly with customers/garages rather than through the broker's `tbl_account` ledger.
- **Remediation**: Removed `tbl_account` insertions from `settle_claim` and `reverse_claim_settlement` in `app/services/claims_endorsement.py`. Claim settlement and reversal now update `tbl_claims` only (`0` rows written to `tbl_account`).

### 2.2 `P1 — GAP-P6-001`: `2025-09-23` GCV Basic TP GST `5%` vs `12%` Cutover (`LBR-036`, `LBR-071`)
- **Root Cause**: `RatingEngineService.calculate_premium` and `PolicyBookingService._resolve_and_revalidate_premiums` previously applied a flat `12%` GST on GCV Basic TP regardless of `risk_start_date`.
- **Remediation**: Added `RatingEngineService.resolve_gcv_basic_tp_gst_rate` (`5%` when `risk_start_date >= 2025-09-23`, `12%` when `risk_start_date < 2025-09-23`, and `12%` default on undated `SelfQuotationRequest` unless `apply_gcv_2025_09_23_tp_gst_cutover=True` or `gcv_basic_tp_gst_rate_override` is passed) and wired it into both Phase 6 quotation rating and Phase 7 policy preview/booking.

### 2.3 `P1 — GAP-P10-002`: Canonical `AccTransId` & System `LedgerMId` (`1161`, `2113`, `1930`, `1878`) (`LBR-057`, `LBR-065`..`070`, `LBR-129`)
- **Root Cause**: Financial endorsement commission adjustments (`AccTransId = 3`) posted to `policy.LedgerMId` instead of `LedgerMId = 1161` (`LEGACY_COMMISSION_CONTROL_LEDGER_ID`), and `AppEndorsementforApproval.aspx.cs`'s 3-leg Endorsement Fee split involving `LedgerMId = 1878` (`LEGACY_ENDORSEMENT_INCOME_LEDGER_ID`) was not wired into `apply_endorsement` / `reverse_endorsement`.
- **Remediation**:
  - Standardized `LEGACY_ACC_TRANS_TYPE_MAP` (`1..16`) and `LEGACY_SYSTEM_LEDGER_META` (`1161`, `2113`, `1930`, `1878`) in `app/services/commission_accounting.py`.
  - Updated `apply_endorsement` and `reverse_endorsement` in `app/services/claims_endorsement.py` to post `AccTransId = 3` commission delta/contra rows to `LedgerMId = 1161`.
  - Implemented the 3-leg Endorsement Fee split (`AccTransId = 2` on `FromLedger` `+paid_fee`, `AccTransId = 2` on `LedgerMId = 1878` `-cmp_amt`, and `AccTransId = 1` on `PayToLedger` `-cmp_amt`) and its 3-leg contra on reversal while keeping double-entry Trial Balance balanced (`variance == 0.00`).

### 2.4 `P1 — GAP-P10-003`: 22-Subtype Endorsement Catalog (`1..22`), `NCB_RECOVERY`, & `OwnerTransferEndorsement.aspx.cs` New Customer Creation (`LBR-126`..`128`)
- **Root Cause**: `OWNERSHIP_TRANSFER` (`EndorsementTypeId = 12`) mutated the existing `tbl_customer` row in-place rather than creating a new `Customer` row and rebinding `CustomerId` on the policy and vehicle; `legacy_endorsement_type_id` (`1..22`) and `NCB_RECOVERY` (`EndorsementTypeId = 13` with `NcbRecovAmt`) were not exposed on endorsement schemas.
- **Remediation**:
  - Added `LEGACY_ENDORSEMENT_TYPE_ID_MAP` (`1..22`) and `legacy_endorsement_type_id` on `EndorsementCreateRequest`, `EndorsementPreviewResponse`, and `EndorsementResponse`.
  - Added `NCB_RECOVERY` (`NcbRecovAmt`) and all 22 legacy endorsement types to `calculate_endorsement_financial_impact_pure`.
  - Updated `apply_endorsement` so `OWNERSHIP_TRANSFER` creates a new `Customer` row in `tbl_customer` and rebinds `policy.CustomerId`, `end_obj.CustomerId`, and `vehicle.CustomerId` (restoring `previous_customer_id` upon `reverse_endorsement`).

### 2.5 `P2 — GAP-P7-001`, `GAP-P7-002`, `GAP-P6-002`, & `GAP-P10-004`
- **`GAP-P7-001`**: Added GCV + HDFC ERGO (`insurance_company_id == 2 and policy_type_id > 18`) Net-only commission branch in `PolicyBookingService.calculate_commission_summary` and `IsQualityCheck = 0` for Insurer `(3, 32)` with `policy_type_id > 18` in `book_policy`.
- **`GAP-P7-002`**: Added `motor_or_non_motor: Literal["MOTOR", "NONMOTOR"] = "MOTOR"` (`15.00%` default TDS for `NONMOTOR` per `LBR-107`) and `use_legacy_cust_veh_id_500_sentinel: bool = False` (`CustVehId = 500` on cancellation per `LBR-061`).
- **`GAP-P6-002`**: Updated GCV extra weight loading (`gvw_above_12000_loading`) in `app/services/rating.py` to `Decimal(((int(req.gross_vehicle_weight) - 12000) * 27) // 100)` matching C# integer division (`LBR-028`).
- **`GAP-P10-004`**: Added `bill_amount`, `icl_amount`, and `il_amount` to `ClaimSettlementRequest` and `ClaimResponse` (`LBR-123`).

---

## 3. Regression & Golden Parity Verification

All unit, integration, concurrency, RBAC, golden parity, and E2E tests across Phases 0 → 10 were executed against local `reliable_insurance_dev` (`localhost:3306`) and Redis (`localhost:6379`):

- **Total Test Suite**: `295 passed, 0 failed`
- **Trial Balance Integrity**: `is_balanced == True`, `variance == Decimal("0.00")` across all Phase 7, Phase 8, Phase 9, and Phase 10 flows.
- **Production Safety**: `0` connections or queries to `brahmainsurance`; 100% synthetic test fixtures.

---

## 4. Deliverables Index

1. [`docs/migration/phase_10_gap_remediation_report.md`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/docs/migration/phase_10_gap_remediation_report.md)
2. [`docs/migration/phase_10_gap_closure_matrix.md`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/docs/migration/phase_10_gap_closure_matrix.md)
3. [`docs/migration/phase_10_post_remediation_parity.md`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/docs/migration/phase_10_post_remediation_parity.md)
4. [`docs/migration/phase_10_gap_remediation_final_report.md`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/docs/migration/phase_10_gap_remediation_final_report.md)
