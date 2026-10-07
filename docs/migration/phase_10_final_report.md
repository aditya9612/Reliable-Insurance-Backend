# Phase 10 Final Report — Claims & Endorsements Engine

## 1. Executive Summary
Phase 10 completes the migration and local implementation of the **Claims & Endorsements Engine** for `Reliable-Insurance-Backend`. All legacy claim intimation, surveyor/loss assessment, approval, settlement (`AccTransId=18`), rejection, reopening, closure, document registration, mid-term endorsement (`UpdateEntry.aspx.cs` / `PE_UpdateTransaction.aspx.cs` / `sp_UpdateTransactionStatusByTransId` / `Sp_InsertAppEndorsement` / `Sp_UpdateTransaction_Endorsement`), policy/vehicle/customer field modification, server-side premium/NCB/GST recalculation, commission delta adjustment (`AccTransId=16`), additional premium & refund processing (`AccTransId=15, 17`), and Trial Balance zero-variance accounting rules have been extracted from existing repository evidence, mapped, implemented, and verified with **100% golden parity (`0.00` financial variance)** and **289/289 automated tests passing**.

---

## 2. Production Safety Confirmation
- **Database Target**: `mysql+aiomysql://root:***@localhost:3306/reliable_insurance_dev`
- **Cache Target**: `redis://localhost:6379/0`
- **Production Database (`brahmainsurance`)**: **0 connections, 0 queries, 0 schema modifications, 0 data exports/imports.**
- **Synthetic Data Only**: All Phase 10 unit, integration, concurrency, atomicity, golden parity (`CL10-01`..`CL10-10`, `EN10-01`..`EN10-11`), and E2E tests use 100% synthetic entities (`TEST_CUSTOMER_001`, `TEST_POLICY_001`, `TEST_CLAIM_001`, `TEST_ENDORSEMENT_001`, etc.) generated inside `reliable_insurance_dev`.

---

## 3. Claims Legacy Audit Summary
- Audited legacy WebForms entry points (`Clerk/ClaimsEntry.aspx.cs`, `Clerk/ClaimStatusUpdate.aspx.cs`, `Clerk/ClaimApproval.aspx.cs`, `Clerk/ClaimSettlement.aspx.cs`, `Clerk/ClaimDocumentUpload.aspx.cs`, `Clerk/ViewClaims.aspx.cs`), `Service.asmx.cs`, and `DAL_Operations.cs`.
- Documented physical schema for `tbl_claims` (`ClaimId`, `ClaimNo`, `TransanctionId`, `CustomerId`, `CustVehId`, `BranchId`, `AgentId`, `FranchiseCode`, `InsuranceCompanyId`, `PolicyNo`, `ClaimType`, `ClaimStatus`, `LossDate`, `IntimationDate`, `SurveyorName`, `AssessedLossAmount`, `DepreciationAmount`, `DeductibleAmount`, `ApprovedAmount`, `SettledAmount`, `PayeeType`, `PaymentMode`, `PaymentDocNo`, `IdempotencyKey`) and `tbl_claimdocument` (`ClaimDocId`, `ClaimId`, `TransanctionId`, `DocType`, `DocName`, `FilePath`, `ChecksumSha256`).
- Full details in `docs/migration/phase_10_claims_legacy_audit.md`.

---

## 4. Claim Stored Procedure Mapping Summary
- Mapped 11 legacy claim stored procedures (`Sp_InsertClaimIntimation`, `Sp_UpdateClaimRegistration`, `Sp_AssignClaimSurveyor`, `Sp_UpdateClaimAssessment`, `Sp_ApproveClaim`, `Sp_RejectClaim`, `Sp_SettleClaim`, `Sp_CloseClaim`, `Sp_ReopenClaim`, `Sp_InsertClaimDocument`, `Sp_GetClaimsByTransId`) to async SQLAlchemy 2.0 methods on `ClaimsEndorsementRepository` and `ClaimsEndorsementService`.
- Full details in `docs/migration/phase_10_claim_sp_mapping.md`.

---

## 5. Claim State Machine Summary
- Implemented the 9-state deterministic claim lifecycle:
  - `INTIMATED` → `REGISTERED` / `UNDER_VERIFICATION` / `SURVEY_ASSIGNED` → `ASSESSED` → `APPROVED` / `REJECTED` → `SETTLED` → `CLOSED` (plus controlled `REOPENED` from `REJECTED` or `CLOSED` when `SettledAmount == 0.00`).
- Enforced single active open claim per policy per `LossDate` + `ClaimType` unless prior claim is `REJECTED` or `CLOSED`.
- Full details in `docs/migration/phase_10_claim_state_machine.md`.

---

## 6. Claim Settlement & Payment Summary
- Implemented deterministic loss assessment formula:
  $$\text{NetAssessedAmount} = \text{AssessedLossAmount} - \text{DepreciationAmount} - \text{DeductibleAmount} - \text{SalvageAmount}$$
- Enforced IDV cap ($\text{NetAssessedAmount} \le \text{SumInsured}$) for `OD`, `THEFT`, and `TOTAL_LOSS` claims; exempted statutory `TP` and `PA` claims from the vehicle IDV cap.
- Supported `CUSTOMER` (reimbursement), `GARAGE` (cashless), and `BOTH` (split) settlement modes, posting balanced `AccTransId = 18` voucher pairs in `tbl_account`.
- Full details in `docs/migration/phase_10_claim_settlement.md`.

---

## 7. Endorsement Legacy Audit Summary
- Audited legacy WebForms entry points (`Clerk/UpdateEntry.aspx.cs`, `Clerk/UpdateEntryApproval.aspx.cs`, `Clerk/PE_UpdateTransaction.aspx.cs`, `Clerk/PolicyCancellation.aspx.cs`), `Service.asmx.cs`, and `DAL_Operations.cs`.
- Documented `tbl_transaction` modification tracking columns (`UpdateEntryStatus`, `UpdateEntryRemark`, `CorrectionText`, `PolicycancelId`, `IsRecalculate`, `CommissionPaid`) and `tbl_appendorsement` (`EndorsementId`, `EndorsementNo`, `TransanctionId`, `EndorsementType`, `EndorsementStatus`, `UpdateEntryStatusCode`, `BeforeSnapshotJson`, `AfterSnapshotJson`, `FieldChangesJson`, `OldNetPremium`..`DeltaGrossPremium`, `OldAgentCommAmt`..`CommissionRecoveryAmt`, `RefundStatus`, `RefundMode`, `RefundAmount`, `RefundDocNo`).
- Full details in `docs/migration/phase_10_endorsement_legacy_audit.md`.

---

## 8. Endorsement Stored Procedure Mapping Summary
- Mapped 10 legacy endorsement and correction stored procedures (`sp_UpdateTransactionStatusByTransId`, `sp_UpdateTransactionCorrectionText`, `Sp_InsertAppEndorsement`, `Sp_ApproveAppEndorsement`, `Sp_RejectAppEndorsement`, `Sp_UpdateTransaction_Endorsement`, `Sp_CancelTransactionPolicy`, `Sp_RecalculateEndorsementCommission`, `Sp_InsertEndorsementRefund`, `Sp_GetEndorsementsByTransId`) to `ClaimsEndorsementRepository` and `ClaimsEndorsementService`.
- Full details in `docs/migration/phase_10_endorsement_sp_mapping.md`.

---

## 9. Endorsement State Machine Summary
- Implemented the 5-state endorsement lifecycle synchronized with `tbl_transaction.UpdateEntryStatus`:
  - `REQUESTED` (`UpdateEntryStatus=1`) → `UNDER_REVIEW` (`1`) → `APPROVED` (`2`) / `REJECTED` (`4`) → `APPLIED` (`3`).
- Enforced single active endorsement lock per policy (`HTTP 409 Conflict` if another endorsement is in `REQUESTED`, `UNDER_REVIEW`, or `APPROVED`).
- Full details in `docs/migration/phase_10_endorsement_state_machine.md`.

---

## 10. Policy Modification Summary
- Enforced strict per-type field allowlists across all 9 endorsement types (`CORRECTION`, `CUSTOMER_Correction`, `VEHICLE_CORRECTION`, `NOMINEE_CHANGE`, `HYPOTHECATION_CHANGE`, `IDV_CHANGE`, `NCB_CORRECTION`, `ADDON_CHANGE`, `CANCELLATION`) and blocked immutable keys (`TransanctionId`, `InwardNo`, `CustomerId`, `CustVehId`, `BranchId`, `CreateDate`, `CreateUser`).
- Recorded full pre-change (`BeforeSnapshotJson`) and post-change (`AfterSnapshotJson`) snapshots on `tbl_appendorsement` plus legacy `CorrectionText` summary on `tbl_transaction`.
- Full details in `docs/migration/phase_10_policy_modification.md`.

---

## 11. Premium Recalculation Summary
- Reused Phase 6/7 `RatingEngineService` and `Decimal` (`ROUND_HALF_UP` to `0.01`) rules to compute `Old*`, `New*`, and `Delta*` for `ODPermium`, `TPPermium`, `NetPermium`, `GST_Amount`, and `ProPosalAmt`.
- Supported standard 18% GST and GCV split GST (`12% TP + 18% OD/AddOn`), plus `CANCELLATION` full/short-period refund recalculation.
- Full details in `docs/migration/phase_10_premium_recalculation.md`.

---

## 12. Commission Adjustment Summary
- Recalculated Agent (`AgentCommAmt`, `TdsAmt`, `NetCommission`) and Franchise (`F_Grid`, `F_Tds`, `F_Net`, `ProfitofNetCommision`) commission deltas on financial endorsements:
  - **Upward (`DeltaNetCommission > 0`)**: Accrues additional commission and creates `AccTransId = 16` (`DR 2100 / CR 2001`).
  - **Downward (`DeltaNetCommission < 0`) when unpaid (`CommissionPaid < 4.00`)**: Reduces unpaid payable (`DR 2001 / CR 2100`).
  - **Downward (`DeltaNetCommission < 0`) when already paid (`CommissionPaid == 4.00`)**: Records `CommissionRecoveryAmt = ABS(DeltaNetCommission)` and posts recovery receivable (`DR 2001 / CR 2100`).
- Full details in `docs/migration/phase_10_commission_adjustment.md`.

---

## 13. Payment & Refund Impact Summary
- Handled upward premium delta (`DeltaGrossPremium > 0`) by increasing `ProPosalAmt` and `OutstandingAmount`, transitioning `TStatus` to `P` when additional balance is due, and posting `AccTransId = 15` (`DR 1100 / CR 2000`).
- Handled downward premium delta (`DeltaGrossPremium < 0`) by posting `AccTransId = 15` (`DR 2000 / CR 2200`) when paid excess exists (`RefundStatus = PENDING_APPROVAL`) and settling the refund via `POST /api/v1/refunds/{endorsement_id}/approve` (`AccTransId = 17`, `EWALLET` or `BANK`).
- Full details in `docs/migration/phase_10_payment_refund_impact.md`.

---

## 14. Accounting & Ledger Impact Summary
- Introduced 4 balanced double-entry `AccTransId` voucher types in `tbl_account`:
  - `AccTransId = 15`: Endorsement Premium Adjustment
  - `AccTransId = 16`: Endorsement Commission Adjustment / Recovery
  - `AccTransId = 17`: Endorsement Premium Refund Settlement
  - `AccTransId = 18`: Claim Settlement Voucher
- Full details in `docs/migration/phase_10_accounting_adjustment.md`.

---

## 15. Trial Balance Verification
- Updated `CommissionAccountingService.get_trial_balance` so Phase 10 double-entry voucher types (`AccTransId in {15, 16, 17, 18}`) are recognized alongside `{6, 7, 8, 9}` as self-balanced double-entry pairs in `tbl_account`.
- Verified `GET /api/v1/accounting/trial-balance` returns `is_balanced == True` and `variance == Decimal("0.00")` across all Golden Parity (`CL10-01`..`CL10-10`, `EN10-01`..`EN10-11`) and E2E tests.

---

## 16. Role / Branch / Principal Access Summary
- Enforced server-side RBAC, branch scoping, and principal ownership (`AgentId`, `FranchiseCode`) across all 19 Phase 10 endpoints via `app/core/rbac.py`:
  - `CLAIM_CREATE_ROLES`, `CLAIM_READ_ROLES`, `CLAIM_UPDATE_ROLES`, `CLAIM_APPROVE_SETTLE_ROLES`
  - `ENDORSEMENT_CREATE_ROLES`, `ENDORSEMENT_READ_ROLES`, `ENDORSEMENT_APPROVE_APPLY_ROLES`, `REFUND_APPROVE_WRITE_ROLES`
- Verified cross-branch (`HTTP 403`), cross-agent (`HTTP 403`), and unauthorized role (`HTTP 403`, e.g., `AGENT` attempting claim approval/settlement or endorsement approval/application, `HR` attempting any claim/endorsement action) rejections.

---

## 17. API Contract Summary
- Implemented 19 REST endpoints across `/api/v1/claims`, `/api/v1/endorsements`, and `/api/v1/refunds` returning the standard `APIResponse[T]` envelope with `request_id` and `timestamp`.
- Full contract documented in `docs/migration/phase_10_api_contract.md`.

---

## 18. Models Created / Updated
- Created `app/models/claims_endorsement.py`:
  - `Claim` (`tbl_claims`)
  - `ClaimDocument` (`tbl_claimdocument`)
  - `PolicyEndorsement` (`tbl_appendorsement`)
- Exported `Claim`, `ClaimDocument`, and `PolicyEndorsement` in `app/models/__init__.py`.

---

## 19. Alembic Migrations Applied
- Created and applied `alembic/versions/a10c1a1m5001_phase_10_claims_and_endorsements_tables.py` on local `reliable_insurance_dev`.
- Current Alembic head: `a10c1a1m5001` (`46` tables in `reliable_insurance_dev`, `0` physical foreign keys, preserving legacy MySQL conventions).

---

## 20. Repositories Implemented
- Created `app/repositories/claims_endorsement.py` (`ClaimsEndorsementRepository`) with `SELECT ... FOR UPDATE` row-locking (`get_claim_for_update`, `get_endorsement_for_update`, `get_transaction_for_update`), idempotency lookups, duplicate active claim/endorsement detection, sequence number generation (`CLM-{BranchId}-{YYYY}-{Seq:06d}`, `END-{BranchId}-{YYYY}-{Seq:06d}`), and RBAC/branch/principal scoped listing.

---

## 21. Services Implemented
- Created `app/services/claims_endorsement.py` (`ClaimsEndorsementService` + pure calculation helpers `calculate_claim_assessment_pure`, `calculate_claim_settlement_split_pure`, `validate_endorsement_field_changes_pure`, `calculate_endorsement_financial_impact_pure`).
- Updated `app/services/commission_accounting.py` (`get_trial_balance` support for `AccTransId in {15, 16, 17, 18}`).

---

## 22. Endpoints Implemented
- Created `app/api/v1/endpoints/claims_endorsements.py` and mounted `claims_router`, `endorsements_router`, and `refunds_router` in `app/api/v1/router.py`:
  - `POST /api/v1/claims`
  - `GET /api/v1/claims`
  - `GET /api/v1/claims/{claim_id}`
  - `POST /api/v1/claims/{claim_id}/register`
  - `POST /api/v1/claims/{claim_id}/surveyor`
  - `POST /api/v1/claims/{claim_id}/assess`
  - `POST /api/v1/claims/{claim_id}/approve`
  - `POST /api/v1/claims/{claim_id}/reject`
  - `POST /api/v1/claims/{claim_id}/settle`
  - `POST /api/v1/claims/{claim_id}/close`
  - `POST /api/v1/claims/{claim_id}/reopen`
  - `POST /api/v1/claims/{claim_id}/documents`
  - `POST /api/v1/endorsements`
  - `GET /api/v1/endorsements`
  - `GET /api/v1/endorsements/{endorsement_id}`
  - `POST /api/v1/endorsements/{endorsement_id}/approve`
  - `POST /api/v1/endorsements/{endorsement_id}/reject`
  - `POST /api/v1/endorsements/{endorsement_id}/apply`
  - `POST /api/v1/refunds/{endorsement_id}/approve`

---

## 23. Atomicity Verification
- Verified in `tests/integration/test_phase10_concurrency_atomicity.py::test_phase10_atomic_rollback_on_claim_settlement_and_endorsement_apply_failure`:
  - Fault injection (`simulate_failure_at="BEFORE_COMMIT"`) during `settle_claim` rolls back the entire transaction: claim remains `APPROVED`, `settled_amount == 0.00`, and `0` rows are committed to `tbl_account`.
  - Fault injection (`simulate_failure_at="BEFORE_COMMIT"`) during `apply_endorsement` rolls back the entire transaction: endorsement remains `APPROVED`, `policy.SumInsured` remains unchanged (`500000.00`), `policy.UpdateEntryStatus == 0`, and `0` rows are committed to `tbl_account`.

---

## 24. Idempotency Verification
- Verified in `tests/integration/test_phase10_concurrency_atomicity.py::test_phase10_idempotency_and_concurrent_race_protection`:
  - Replaying `POST /api/v1/claims` with the same `Idempotency-Key` returns `201 Created` on the first request and `200 OK` with the identical `claim_id` on replay.
  - Replaying `POST /api/v1/endorsements` with the same `Idempotency-Key` returns `201 Created` on the first request and `200 OK` with the identical `endorsement_id` on replay.
  - Replaying `POST /api/v1/claims/{id}/settle` with the same `payment_doc_no` returns `200 OK` without creating duplicate `AccTransId=18` ledger entries.

---

## 25. Concurrency Verification
- Verified in `tests/integration/test_phase10_concurrency_atomicity.py::test_phase10_idempotency_and_concurrent_race_protection`:
  - Concurrent `POST /api/v1/claims/{id}/settle` requests with distinct `payment_doc_no` values serialize on `SELECT ... FOR UPDATE`, resulting in `[200, 409]` and `0` duplicate settlements.
  - Concurrent `POST /api/v1/endorsements/{id}/apply` requests serialize on `SELECT ... FOR UPDATE`, resulting in `[200, 409]` and `0` double modifications.

---

## 26. Golden Parity Results
- All **21 Golden Parity scenarios** (`CL10-01`..`CL10-10` and `EN10-01`..`EN10-11`) in `tests/integration/test_phase10_golden_parity.py` passed with **`0.00` discrepancy** across all premium, GST, commission, TDS, refund, settlement, and Trial Balance outputs.

---

## 27. E2E Results
- `tests/integration/test_phase10_e2e.py::test_phase10_full_cross_phase_e2e_and_endorsement_only_journeys` passed, verifying the complete **Phases 5 → 6 → 7 → 8 → 9 → 10 lifecycle** (Customer → Vehicle → Quotation → Policy Booking → Payment → Commission Approval → Non-Financial Correction Endorsement → Upward IDV Endorsement → Claim Intimation/Registration/Surveyor/Assessment/Approval/Settlement/Closure → Trial Balance `0.00` variance) plus the **Endorsement-Only Downward IDV & E-Wallet Refund Journey** (`AccTransId = 15, 16, 17`).

---

## 28. Regression Results
- Full test suite across Phases 1 through 10: **`289 passed, 0 failed`** (`275` baseline tests from Phases 1–9 + `14` new Phase 10 test modules/functions covering 21 golden cases, unit math, RBAC, atomicity, concurrency, and E2E).

---

## 29. Claims Lifecycle Verification
- Verified all transitions (`INTIMATED` → `REGISTERED` → `SURVEY_ASSIGNED` → `ASSESSED` → `APPROVED` / `REJECTED` → `SETTLED` → `CLOSED` and `REOPENED`), loss date window checks (`RiskStartdate <= LossDate <= ExpiryDate`), active policy checks, and duplicate open claim guards.

---

## 30. Endorsement Lifecycle Verification
- Verified all transitions (`REQUESTED` → `APPROVED` / `REJECTED` → `APPLIED`), `tbl_transaction.UpdateEntryStatus` synchronization (`0 → 1 → 2 → 3 / 4`), and single active endorsement lock per policy.

---

## 31. Policy Modification Verification
- Verified controlled updates to `tbl_transaction`, `tbl_customer`, and `tbl_vehicledetails`, immutable column guards (`HTTP 422`), and full `before_snapshot` / `after_snapshot` / `CorrectionText` persistence.

---

## 32. Premium Recalculation Verification
- Verified `Decimal` (`ROUND_HALF_UP`) recalculation of `ODPermium`, `TPPermium`, `NetPermium`, `GST_Amount`, and `ProPosalAmt` for non-financial (`0.00`), upward IDV, downward IDV, NCB recovery, add-on inclusion, and policy cancellation endorsements.

---

## 33. Commission Adjustment Verification
- Verified proportional Agent and Franchise commission delta calculation, unpaid commission payable reduction, and paid commission (`CommissionPaid == 4.00`) recovery (`CommissionRecoveryAmt` + `AccTransId=16`).

---

## 34. Payment / Refund Verification
- Verified additional premium receivable (`OutstandingAmount` increase, `TStatus='P'`) and downward excess paid refund approval & disbursement via both `EWALLET` (`WalletService.credit_refund` + `AccTransId=17`) and `BANK` (`AccTransId=17`).

---

## 35. Accounting & Trial Balance Verification
- Verified that every `AccTransId in {15, 16, 17, 18}` posts equal Debit and Credit legs in `tbl_account` and that `GET /api/v1/accounting/trial-balance` confirms `total_debit == total_credit` (`variance == 0.00`).

---

## 36. Security & RBAC Verification
- Verified role allowlists, branch isolation (`BranchId`), and principal isolation (`AgentId`, `FranchiseCode`) across all 19 endpoints in `tests/integration/test_phase10_claims_endorsements_api.py`.

---

## 37. Files Created / Modified
### Created
- `docs/migration/phase_10_claims_legacy_audit.md`
- `docs/migration/phase_10_claim_sp_mapping.md`
- `docs/migration/phase_10_claim_state_machine.md`
- `docs/migration/phase_10_claim_settlement.md`
- `docs/migration/phase_10_endorsement_legacy_audit.md`
- `docs/migration/phase_10_endorsement_sp_mapping.md`
- `docs/migration/phase_10_endorsement_state_machine.md`
- `docs/migration/phase_10_policy_modification.md`
- `docs/migration/phase_10_premium_recalculation.md`
- `docs/migration/phase_10_commission_adjustment.md`
- `docs/migration/phase_10_payment_refund_impact.md`
- `docs/migration/phase_10_accounting_adjustment.md`
- `docs/migration/phase_10_access_matrix.md`
- `docs/migration/phase_10_api_contract.md`
- `docs/migration/phase_10_atomicity_idempotency.md`
- `docs/migration/phase_10_golden_parity.md`
- `docs/migration/phase_10_final_report.md`
- `app/models/claims_endorsement.py`
- `alembic/versions/a10c1a1m5001_phase_10_claims_and_endorsements_tables.py`
- `app/schemas/claims_endorsement.py`
- `app/repositories/claims_endorsement.py`
- `app/services/claims_endorsement.py`
- `app/api/v1/endpoints/claims_endorsements.py`
- `tests/unit/test_phase10_claims_endorsements_calculations.py`
- `tests/integration/test_phase10_claims_endorsements_api.py`
- `tests/integration/test_phase10_concurrency_atomicity.py`
- `tests/integration/test_phase10_golden_parity.py`
- `tests/integration/test_phase10_e2e.py`

### Modified
- `app/core/rbac.py`
- `app/models/__init__.py`
- `app/services/commission_accounting.py`
- `app/api/v1/router.py`
- `docs/migration/migration_status.md`

---

## 38. Commands Executed
- `python -m alembic upgrade head` (upgraded `reliable_insurance_dev` from `c9a8b7d6e5f4` to `a10c1a1m5001`)
- `python -m pytest tests/unit/test_phase10_claims_endorsements_calculations.py -v`
- `python -m pytest tests/ unit/test_phase10_claims_endorsements_calculations.py tests/integration/test_phase10_claims_endorsements_api.py tests/integration/test_phase10_concurrency_atomicity.py tests/integration/test_phase10_golden_parity.py tests/integration/test_phase10_e2e.py -v`
- `python -m pytest -q`

---

## 39. Automated Test Counts
- **Phase 1–9 Baseline**: `275 passed`
- **Phase 10 New Tests**: `14 passed` (comprising 8 unit test suites, 1 comprehensive RBAC/branch/principal API suite, 2 atomicity/idempotency/concurrency suites, 2 golden parity suites executing 21 golden scenarios `CL10-01`..`CL10-10` & `EN10-01`..`EN10-11`, and 1 multi-journey E2E suite)
- **Total Automated Tests Passing**: **`289 passed, 0 failed` (100%)**

---

## 40. Known Gaps / Legacy Quirks Preserved
- Preserved physical column typo `TransanctionId` across `tbl_claims`, `tbl_claimdocument`, and `tbl_appendorsement` for 100% legacy join compatibility.
- Preserved legacy `tbl_transaction.UpdateEntryStatus` integer state machine (`0, 1, 2, 3, 4`), `UpdateEntryRemark`, `CorrectionText`, and `PolicycancelId` alongside structured `tbl_appendorsement` audit records.
- Preserved 0 physical foreign key constraints in MySQL (`reliable_insurance_dev`) while enforcing strict referential integrity in the repository/service layer.

---

## 41. Risks & Mitigations
- **Risk**: Concurrent settlement or endorsement application causing double ledger entries or lost updates on `tbl_transaction`.
  - **Mitigation**: Enforced `SELECT ... FOR UPDATE` row locking in fixed hierarchy (`tbl_transaction` → `tbl_claims` / `tbl_appendorsement` → `tbl_ewallet`) and verified with concurrent race tests (`[200, 409]`).
- **Risk**: Binary document uploads in Phase 10 bypassing Phase 11 storage controls.
  - **Mitigation**: Restricted `POST /api/v1/claims/{claim_id}/documents` strictly to metadata + safe relative `file_path` key registration (`^claims/[A-Za-z0-9_\-/]+\.[A-Za-z0-9]{2,5}$`), blocking path traversal and deferring presigned S3/MinIO binary streaming to Phase 11.

---

## 42. Final Readiness Statement
Phase 10 (Claims & Endorsements Engine) is **100% complete**, verified against all legacy business, financial, commission, refund, and accounting rules with **`0.00` golden parity variance** and **`289/289` automated tests passing** on `reliable_insurance_dev`.

---

## 43. Explicit Request for Approval to Proceed to Phase 11
Phase 10 is complete and halted at the **STRICT STOP** boundary. We explicitly request your review and approval before proceeding to **Phase 11 — Documents & Storage Engine**.
