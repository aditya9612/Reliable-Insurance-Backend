# Phase 0 → Phase 10 Legacy Parity Gap Verification & Remediation Report

## 1. Executive Summary

This report documents the independent forensic verification and surgical remediation of all findings raised in the Phase 0 → Phase 10 Forensic Parity Audit (`docs/migration/phase_10_legacy_parity_audit_report.md` and `docs/migration/phase_10_gap_register.md`).

Every finding (`P0`: `GAP-P10-001`; `P1`: `GAP-P6-001`, `GAP-P10-002`, `GAP-P10-003`; `P2`: `GAP-P7-001`, `GAP-P7-002`, `GAP-P6-002`, `GAP-P8-001`, `GAP-P10-004`, `GAP-P7-003`, `GAP-P7-004`, `GAP-P5-001`, `GAP-P5-002`; `P3`: `GAP-P5-003`, `GAP-P11-001`; and `UNKNOWN`: `GAP-UNK-001`, `GAP-UNK-002`, `GAP-UNK-003`) was independently verified against:
1. Legacy baseline evidence (`docs/migration/01_*` through `21_*` and `29_MIGRATION_SOURCE_OF_TRUTH.md`)
2. Legacy stored procedure and WebForms calculation rules (`LBR-001` through `LBR-140`, `DEF-001` through `DEF-011`)
3. Actual FastAPI backend implementation (`app/models/`, `app/schemas/`, `app/repositories/`, `app/services/`, `app/api/v1/`)
4. Automated unit, golden parity, concurrency/atomicity, RBAC, and E2E test suites (`tests/`)

### Production Safety Attestation
- **Zero production connectivity**: All verification, remediation, and test execution ran exclusively against `localhost:3306/reliable_insurance_dev` and synthetic fixtures.
- **No speculative code for `UNKNOWN` items**: `GAP-UNK-001`, `GAP-UNK-002`, and `GAP-UNK-003` remain explicitly documented as `UNKNOWN — EVIDENCE NOT AVAILABLE` with zero fabricated logic.

---

## 2. Independent Verification & Remediation by Priority

### P0 Finding

#### `GAP-P10-001` — Claim Settlement & Reversal Broker Ledger Postings vs Legacy `LBR-123`
- **Legacy Evidence**:
  - `docs/migration/06_BUSINESS_WORKFLOWS.md` (Section 6.1, Claim Workflow) & `docs/migration/19_BUSINESS_RULES_EXTRACTED.md` (`LBR-123`):
    - Legacy `Clerk/CL_ClaimNew.aspx.cs` (`btn_Save_Click` -> `sp_InsertClaimTransaction`, `sp_UpdateClaimTransaction`, `FinalBill` `sp_InsertFinalBill`) records claim intimation, survey, assessment, approval, and settlement metadata only.
    - Insurance claims are settled directly between the Insurance Company (`tbl_insurancecompany`) and the Policyholder/Garage (`PayeeType`).
    - Legacy claim settlement writes **zero rows** to the broker's financial ledger (`tbl_account`).
- **Pre-Remediation New Backend Behavior**:
  - `app/services/claims_endorsement.py:L1363-1404` (`settle_claim`) inserted 2 `tbl_account` rows (`AccTransId = 15`, `LedgerMId = 103` DR `+SettledAmount` and `LedgerMId = 203` CR `-SettledAmount`).
  - `app/services/claims_endorsement.py:L1455-1496` (`reverse_claim_settlement`) inserted 2 contra `tbl_account` rows (`AccTransId = 16`).
- **Independent Verification Classification**: **`VERIFIED GAP`** (`P0`).
- **Remediation Applied**:
  - Updated `ClaimsEndorsementService.settle_claim` and `ClaimsEndorsementService.reverse_claim_settlement` in `app/services/claims_endorsement.py` to remove the non-legacy `AccTransId = 15` and `AccTransId = 16` `tbl_account` postings while preserving atomic state transition (`APPROVED` -> `SETTLED` and `SETTLED` -> `APPROVED`), `calculate_claim_settlement_split_pure` payee split (`InsurerPayableAmount`, `CustomerPayableAmount`, `GaragePayableAmount`), idempotency key protection, and `BEFORE_COMMIT` fault-injection rollback semantics.
- **Post-Remediation Status**: **`CLOSED — VERIFIED PARITY`**.

---

### P1 Findings

#### `GAP-P6-001` — GCV Basic TP GST Rate Cutover (`5%` on/after `2025-09-23` vs `12%` before `2025-09-23`)
- **Legacy Evidence**:
  - `docs/migration/19_BUSINESS_RULES_EXTRACTED.md` (`LBR-023` & `LBR-047`) and `docs/migration/06_BUSINESS_WORKFLOWS.md`:
    - `Clerk/SelfQuotationRequest.aspx.cs:L2555-2561` uses `12%` GST on GCV Basic TP (`LiabilityPremium * 12 / 100`) and `18%` on `(TotalPremium - LiabilityPremium)`.
    - `Clerk/adm_PolicyDetails.aspx.cs:L636-644` introduces a statutory cutover on `2025-09-23` based on `RiskStartdate`:
      - `RiskStartdate >= 2025-09-23`: `5%` GST on Basic TP (`LiabilityPremium * 5 / 100`) + `18%` GST on `(NetPremium - LiabilityPremium)`.
      - `RiskStartdate < 2025-09-23`: `12%` GST on Basic TP + `18%` GST on `(NetPremium - LiabilityPremium)`.
- **Pre-Remediation New Backend Behavior**:
  - `app/services/rating.py:L507-517` and `app/services/policy_booking.py:L514-521` always used `12%` on GCV Basic TP regardless of `risk_start_date`.
- **Independent Verification Classification**: **`VERIFIED GAP`** (`P1`).
- **Remediation Applied**:
  - Added `risk_start_date: Optional[date]`, `apply_gcv_2025_09_23_tp_gst_cutover: bool = False`, and `gcv_basic_tp_gst_rate_override: Optional[Decimal] = None` to `PremiumCalculationRequest` (`app/schemas/quotation.py`) and `PolicyPreviewRequest` / `PolicyBookingCreateRequest` (`app/schemas/policy.py`), plus `gcv_basic_tp_gst_rate_percent: Decimal` to `PremiumBreakdownResponse`.
  - Implemented `RatingEngineService.resolve_gcv_basic_tp_gst_rate` (`app/services/rating.py:L48-70`) and wired it into both `RatingEngineService.calculate_premium` and `PolicyBookingService._resolve_and_revalidate_premiums`:
    - When `risk_start_date` is provided (or `apply_gcv_2025_09_23_tp_gst_cutover=True`): returns `5%` for `>= 2025-09-23` and `12%` for `< 2025-09-23`.
    - When `risk_start_date` is omitted and `apply_gcv_2025_09_23_tp_gst_cutover=False`: preserves `12%` (`SelfQuotationRequest.aspx.cs` quotation parity).
- **Post-Remediation Status**: **`CLOSED — VERIFIED PARITY`**.

#### `GAP-P10-002` — Canonical Legacy `AccTransId` (`1..4`) and System `LedgerMId` (`1161`, `2113`, `1930`, `1878`) Alignment
- **Legacy Evidence**:
  - `docs/migration/19_BUSINESS_RULES_EXTRACTED.md` (`LBR-059`..`LBR-065`, `LBR-115`..`LBR-122`, `LBR-126`):
    - Legacy `tbl_account` uses `AccTransId` `1` (Payment/Receivable), `2` (Receipt/Payable), `3` (Commission), `4` (Contra), and system ledgers:
      - `LedgerMId = 1161`: Unclear Commission Control Ledger (`AccTransId = 3`)
      - `LedgerMId = 2113`: TDS Payable Ledger
      - `LedgerMId = 1930`: Sales Executive Commission Ledger
      - `LedgerMId = 1878`: Endorsement Income Ledger (`AppEndorsementforApproval.aspx.cs:L510-585`)
- **Pre-Remediation New Backend Behavior**:
  - `app/services/claims_endorsement.py:L2440` and `L2626` posted endorsement commission delta (`AccTransId = 3`) to synthetic `LedgerMId = 202` instead of legacy `LedgerMId = 1161`, and did not implement the 3-leg `LedgerMId = 1878` Endorsement Income fee posting.
- **Independent Verification Classification**: **`PARTIAL GAP`** (`P1`) — Extended `AccTransId` codes (`6..14`, `17..18`) are intentional audit-trail discrimination (`INTENTIONAL HARDENING`), whereas `AccTransId = 15/16` were non-legacy (removed in `GAP-P10-001`) and `LedgerMId = 1161` / `1878` were missing on endorsement postings.
- **Remediation Applied**:
  - Added `LEGACY_COMMISSION_CONTROL_LEDGER_ID = 1161`, `LEGACY_TDS_PAYABLE_LEDGER_ID = 2113`, `LEGACY_SALES_EX_COMM_LEDGER_ID = 1930`, and `LEGACY_ENDORSEMENT_INCOME_LEDGER_ID = 1878` in `app/services/claims_endorsement.py` and `LEGACY_SYSTEM_LEDGER_META` / `LEGACY_ACC_TRANS_TYPE_MAP` in `app/services/commission_accounting.py`.
  - Updated `apply_endorsement` and `reverse_endorsement` to post `AccTransId = 3` agent commission delta and reversal rows to `LedgerMId = 1161`.
  - Implemented the 3-leg `AppEndorsementforApproval.aspx.cs` Endorsement Fee posting (`AccTransId = 2` on `FromLedgerId`, `AccTransId = 2` on `LedgerMId = 1878` with `-CmpAmt`, and `AccTransId = 1` on `PayToLedgerId` with `-CmpAmt`, where `CmpAmt = round_rupee(PaidAmt - ServiceChargeAmount)`) and its exact 3-leg reversal in `reverse_endorsement`.
- **Post-Remediation Status**: **`CLOSED — VERIFIED PARITY`**.

#### `GAP-P10-003` — Endorsement Subtype Catalog (`1..22`), `NCB_RECOVERY`, and `OwnerTransferEndorsement.aspx.cs` New Customer Creation
- **Legacy Evidence**:
  - `docs/migration/19_BUSINESS_RULES_EXTRACTED.md` (`LBR-124`..`LBR-129`) and `docs/migration/06_BUSINESS_WORKFLOWS.md`:
    - Legacy `AppEndorsement.aspx.cs` / `AppEndorsementforApproval.aspx.cs` dispatches across 22 endorsement type IDs (`1..22`), including `NCB_RECOVERY` (`11`, `NcbRecovAmt`), `LPG_CNG_KIT_CHANGE` (`14`), `ACCESSORIES_CHANGE` (`15`), `PA_COVER_CHANGE` (`16`), `LL_COVER_CHANGE` (`18`), `ZERO_DEP_CHANGE` (`19`), `VOLUNTARY_DEDUCTIBLE_CHANGE` (`20`), etc.
    - Legacy `Clerk/OwnerTransferEndorsement.aspx.cs` creates a **new** `Customer` row (`NewCustId`) in `tbl_customer` for the transferee and updates `tbl_vehicledetails.CustomerId = NewCustId` and `tbl_transaction.CustomerId = NewCustId`.
- **Pre-Remediation New Backend Behavior**:
  - `EndorsementTypeLiteral` only listed 14 types, lacked `legacy_endorsement_type_id` (`1..22`) mapping, and `OWNERSHIP_TRANSFER` mutated the existing `tbl_customer` row in place instead of creating a new `CustomerId` and rebinding `tbl_transaction.CustomerId` and `tbl_vehicledetails.CustomerId`.
- **Independent Verification Classification**: **`VERIFIED GAP`** (`P1`).
- **Remediation Applied**:
  - Added `LEGACY_ENDORSEMENT_TYPE_ID_MAP` (`1..22`) and `LEGACY_ENDORSEMENT_TYPE_TO_ID_MAP` in `app/schemas/claims_endorsement.py`, expanding `EndorsementTypeLiteral` to all 22 legacy endorsement types and accepting `legacy_endorsement_type_id: Optional[int]` (`1..22`) on `EndorsementCreateRequest`.
  - Updated `validate_endorsement_field_allowlist` and `calculate_endorsement_financial_impact_pure` in `app/services/claims_endorsement.py` to support all 22 types, including `NCB_RECOVERY` (`NcbRecovAmt` override or NCB slab recovery) and all coverage/add-on subtypes.
  - Updated `apply_endorsement` so `OWNERSHIP_TRANSFER` creates a new `Customer` record (`NewCustId`) in `tbl_customer`, rebinds `policy.CustomerId`, `end_obj.CustomerId`, and `vehicle.CustomerId` to `NewCustId` (preserving the original `Customer` record untouched), exposes `previous_customer_id` and `current_customer_id` on `EndorsementResponse`, and restores `previous_customer_id` on `reverse_endorsement`.
- **Post-Remediation Status**: **`CLOSED — VERIFIED PARITY`**.

---

### P2 Findings

#### `GAP-P7-001` — GCV + HDFC ERGO (`InsuranceCompanyId=2, PolicyTypeId>18`) Net-Only Commission & Insurer `(3, 32)` Inward Status Rule
- **Legacy Evidence**:
  - `Clerk/adm_PolicyDetails.aspx.cs:L1468` (`LBR-048`, `LBR-049`):
    - When `InsuranceCompanyId == 2` (HDFC ERGO) and `PolicyTypeId > 18` (GCV), OD Commission and Extra Commission are zeroed and only Net Commission is calculated on `NetPermium`.
    - When `InsuranceCompanyId in {3, 32}` and `PolicyTypeId > 18`, `IsQualityCheck` is initialized to `0` (pending inward check).
- **Independent Verification Classification**: **`VERIFIED GAP`** (`P2`).
- **Remediation Applied**:
  - Expanded `policy_type_id` range to `1..30` and added `enforce_hdfc_gcv_net_only: bool = False` in `app/schemas/policy.py`.
  - Updated `PolicyBookingService.calculate_commission_summary` and `PolicyBookingService.book_policy` in `app/services/policy_booking.py` to enforce the GCV + HDFC ERGO (`insurance_company_id == 2 and policy_type_id > 18`) Net-only commission branch and set `IsQualityCheck = 0` when `insurance_company_id in {3, 32} and policy_type_id > 18`.
- **Post-Remediation Status**: **`CLOSED — VERIFIED PARITY`**.

#### `GAP-P7-002` — Non-Motor (`NONMOTOR`) 15% Default TDS & `CustVehId = 500` Cancellation Sentinel
- **Legacy Evidence**:
  - `Clerk/adm_NewEntryForLifeORHelth.aspx.cs` (`LBR-056`): Non-Motor (`MotorOrNonMotor = "NONMOTOR"`) policies use a default `15%` TDS rate when TDS% is not explicitly overridden.
  - `Clerk/PolicyTransactionNew.aspx.cs` (`LBR-054`): Policy cancellation optionally assigns `CustVehId = 500` sentinel so the vehicle can be re-booked.
- **Independent Verification Classification**: **`PARTIAL GAP`** (`P2`).
- **Remediation Applied**:
  - Added `motor_or_non_motor: Literal["MOTOR", "NONMOTOR"] = "MOTOR"` to `PolicyPreviewRequest` and `use_legacy_cust_veh_id_500_sentinel: bool = False` to `PolicyCancelRequest` (`app/schemas/policy.py`).
  - Updated `PolicyBookingService.calculate_commission_summary`, `book_policy`, and `cancel_policy` (`app/services/policy_booking.py`) to apply `15.00%` default TDS for `NONMOTOR` policies and set `tx.CustVehId = 500` when `use_legacy_cust_veh_id_500_sentinel=True`.
- **Post-Remediation Status**: **`CLOSED — VERIFIED PARITY`**.

#### `GAP-P6-002` — GCV Extra Weight Loading Integer Division (`((GVW - 12000) * 27) // 100`)
- **Legacy Evidence**:
  - `Clerk/SelfQuotationRequest.aspx.cs:L1479` & `Clerk/adm_PolicyDetails.aspx.cs` (`LBR-021`):
    - Legacy C# expression `(((Convert.ToInt32(txt_VehicleWeight.Text) - 12000) * 27) / 100)` uses C# `int` division (truncating toward zero) rather than decimal half-up rounding.
- **Independent Verification Classification**: **`VERIFIED GAP`** (`P2`).
- **Remediation Applied**:
  - Updated `gvw_above_12000_loading` in `app/services/rating.py:L256` to `Decimal(((int(req.gross_vehicle_weight) - 12000) * 27) // 100)`.
- **Post-Remediation Status**: **`CLOSED — VERIFIED PARITY`**.

#### `GAP-P10-004` — Claim `FinalBill` (`BillAmt`, `ICLAmt`, `ILAmt`) Fields on Settlement
- **Legacy Evidence**:
  - `Clerk/CL_ClaimNew.aspx.cs:L1570` (`sp_InsertFinalBill`, `LBR-123`):
    - Records `BillAmt` (total repair bill amount), `ICLAmt` (insurer claim liability amount), and `ILAmt` (final settled amount).
- **Independent Verification Classification**: **`PARTIAL GAP`** (`P2`).
- **Remediation Applied**:
  - Added `bill_amount`, `icl_amount`, and `il_amount` to `ClaimSettlementRequest` and `ClaimResponse` (`app/schemas/claims_endorsement.py`), persisted via `_encode_final_bill_remarks` / `_decode_final_bill_remarks` in `app/services/claims_endorsement.py` without altering physical table columns.
- **Post-Remediation Status**: **`CLOSED — VERIFIED PARITY`**.

#### `GAP-P8-001` — Cheque Bounce Rs. 350 Penalty vs Configurable Penalty Default
- **Legacy Evidence**:
  - `Clerk/ChequeClearence.aspx.cs` (`LBR-089`) and `app/schemas/payment_engine.py:L74`:
    - `ChequeBounceRequest.penalty_amount` already defaults to `Decimal("350.00")` (`Rs. 350.00`) while allowing authorized overrides.
- **Independent Verification Classification**: **`INTENTIONAL HARDENING — NO CODE CHANGE REQUIRED`**.
- **Post-Remediation Status**: **`VERIFIED — DEFAULT 350.00 PRESERVED`**.

#### `GAP-P7-003` — Concurrency-Safe `InwardNo` Sequence vs Legacy `DEF-004` Race Condition
- **Legacy Evidence**:
  - `DEF-004`: Legacy `MAX(InwardNo) + 1` without row locking caused duplicate `InwardNo` under concurrent bookings.
  - `app/repositories/policy_booking.py:allocate_inward_no` uses `SELECT ... FOR UPDATE` + `_BOOKING_WRITE_LOCK`.
- **Independent Verification Classification**: **`LEGACY DEFECT MITIGATED — NO CODE CHANGE REQUIRED`**.

#### `GAP-P7-004` — Decimal `ROUND_HALF_UP` vs Legacy `double` Binary Floating-Point Drift (`DEF-005`)
- **Legacy Evidence**:
  - `DEF-005`: Legacy mixed `double`/`decimal` conversions caused 1-paise float representation drift.
  - New backend uses `Decimal` with `ROUND_HALF_UP` across Phases 6–10.
- **Independent Verification Classification**: **`LEGACY DEFECT MITIGATED — NO CODE CHANGE REQUIRED`**.

#### `GAP-P5-001`, `GAP-P5-002`, `GAP-P5-003` — JWT/Argon2id Auth, Server-Side RBAC & Branch/Principal Isolation (`DEF-001`, `DEF-002`, `DEF-003`)
- **Legacy Evidence**:
  - `DEF-001` (plaintext passwords), `DEF-002` (unauthenticated ASMX endpoints), `DEF-003` (missing server-side branch/agent ownership checks).
- **Independent Verification Classification**: **`LEGACY DEFECT MITIGATED / INTENTIONAL HARDENING — NO CODE CHANGE REQUIRED`**.

#### `GAP-P11-001` — Legacy Reporting & Analytics Dashboards Deferred to Phase 11
- **Legacy Evidence**:
  - Reporting-only stored procedures are explicitly scoped to Phase 11 (`Reporting & Analytics`).
- **Independent Verification Classification**: **`AUDIT FALSE POSITIVE — OUT OF PHASE 0–10 SCOPE`**.

---

### `UNKNOWN` Items (Strict Non-Fabrication Rule)

Per Section 2 of the Master Remediation Prompt, **no speculative code was written** for the 3 `UNKNOWN` items:
1. **`GAP-UNK-001`**: 9 missing stored procedure bodies in the SQL dump (`sp_InsertClaimDocument`, `sp_UpdateEndorsementStatus`, etc.) — `UNKNOWN — EVIDENCE NOT AVAILABLE`.
2. **`GAP-UNK-002`**: External mobile app client binary payload expectations beyond `Service.asmx.cs` — `UNKNOWN — EVIDENCE NOT AVAILABLE`.
3. **`GAP-UNK-003`**: Historical manual SQL scripts executed directly on production outside the C# solution — `UNKNOWN — EVIDENCE NOT AVAILABLE`.
