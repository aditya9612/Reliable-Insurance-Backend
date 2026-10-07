# Phase 0 → Phase 10 Post-Remediation Forensic Parity Re-Audit

**Repository**: `Reliable-Insurance-Backend`  
**Audit Date**: `2026-10-07`  
**Post-Remediation Verdict**: **`GREEN — VERIFIED LEGACY PARITY (WITH DOCUMENTED HARDENING)`**

---

## 1. Executive Re-Audit Summary

Following the independent verification and remediation of all confirmed Phase 0 → Phase 10 parity gaps (`P0`: `GAP-P10-001`; `P1`: `GAP-P6-001`, `GAP-P10-002`, `GAP-P10-003`; `P2`: `GAP-P7-001`, `GAP-P7-002`, `GAP-P6-002`, `GAP-P10-004`), the full 140-rule legacy baseline (`LBR-001` through `LBR-140`) and all 11 documented legacy defects (`DEF-001` through `DEF-011`) were re-audited against the actual FastAPI implementation.

| Classification | Pre-Remediation Count | Post-Remediation Count | Change |
|---|---:|---:|---:|
| **PARITY** | 85 | **110** | `+25` |
| **INTENTIONAL HARDENING** | 14 | **14** | `0` |
| **LEGACY DEFECT MITIGATED** | 13 | **13** | `0` |
| **DEVIATION** | 16 | **0** | `-16` |
| **MISSING** | 9 | **0** | `-9` |
| **UNKNOWN** | 3 | **3** | `0` |
| **Total Rules Audited (`LBR-001`..`LBR-140`)** | **140** | **140** | `0` |

- **Open `P0` Blockers**: `0`
- **Open `P1` High-Risk Financial/Workflow Gaps**: `0`
- **Open `P2` Functional/Formula Gaps**: `0`
- **Open `P3` Edge-Case Gaps**: `0`
- **Fabricated `UNKNOWN` Items**: `0` (`GAP-UNK-001`, `GAP-UNK-002`, and `GAP-UNK-003` remain explicitly documented as `UNKNOWN — EVIDENCE NOT AVAILABLE`).

---

## 2. Phase-by-Phase Post-Remediation Parity Matrix

### 2.1 Phase 5 — Authentication, RBAC, Customer & Vehicle (`LBR-001`..`LBR-019`)

| Rule Range | Domain | Post-Remediation Classification | Verification Summary |
|---|---|---|---|
| `LBR-001`..`LBR-008` | Authentication & Session Security | `INTENTIONAL HARDENING` / `LEGACY DEFECT MITIGATED` (`DEF-001`, `DEF-002`) | Argon2id/bcrypt password hashing, JWT `sub`/`role`/`branch_id`/`principal_id`/`jti` claims, and Redis token revocation. |
| `LBR-009`..`LBR-012` | 12-Role RBAC & Branch/Principal Scoping | `PARITY` + `INTENTIONAL HARDENING` (`DEF-008`) | Server-side `apply_branch_and_principal_scope` across all 12 canonical roles (`ADMIN`, `CMD`, `VP`, `AUDIT_CHECKER`, `MANAGER`, `INWARD_EXECUTIVE`, `QUALITY_CHECKER`, `CLERK`, `ACCOUNT`, `AGENT`, `FRANCHISE`, `SALES_EXECUTIVE`). |
| `LBR-013`..`LBR-019` | Customer (`tbl_customer`) & Vehicle (`tbl_vehicledetails`) | `PARITY` + `INTENTIONAL HARDENING` (`DEF-011`) | Exact column mapping, PAN/Aadhaar/GSTIN validation, normalized uppercase alphanumeric `RegistrationNo` uniqueness guard (`409 Conflict`), and soft delete (`IsActive = 0`). |

---

### 2.2 Phase 6 — Motor Quotation, Rating & Premium Engine (`LBR-020`..`LBR-040`, `LBR-071`)

| Rule Range | Domain | Post-Remediation Classification | Verification Summary |
|---|---|---|---|
| `LBR-020`..`LBR-027` | Vehicle Age (`sp_SelectMgfyearOfyearmonth`), IDV `±15%` Band, Basic OD, Accessories, LPG/CNG | `PARITY` | Exact `CEIL(days/365)` age logic (`0.0`/`0.1` -> `0.0`), `±15%` floor IDV band, `4%` electrical/LPG-CNG OD rate, and `ROUND_HALF_UP` whole-rupee rounding. |
| `LBR-028` | GCV Extra Weight Loading (`GVW > 12000`) | **PARITY** (`GAP-P6-002` Remediated) | Uses `Decimal(((int(req.gross_vehicle_weight) - 12000) * 27) // 100)` matching C# integer division `((ExtraWeight * 27) / 100)`. |
| `LBR-029`..`LBR-035` | IMT-23 (`15%`), Own Premises (`33%`), Anti-Theft (`2.5%` cap `₹500`), Voluntary Deductible, Reliance `90%` OD Cap, NCB (`0, 20, 25, 35, 45, 50%`), Zero-Dep, Towing, TP Liability | `PARITY` | Exact ordered rating waterfall and statutory NCB reset on prior claim or new business (`BusinessTypeId = 1`). |
| `LBR-036`, `LBR-071` | GCV Split TP GST & `2025-09-23` Cutover (`5%` vs `12%` on Basic TP) | **PARITY** (`GAP-P6-001` Remediated) | `RatingEngineService.resolve_gcv_basic_tp_gst_rate` applies `5%` for `risk_start_date >= 2025-09-23`, `12%` for `< 2025-09-23`, and `12%` default on undated `SelfQuotationRequest` unless overridden. |
| `LBR-037`..`LBR-040` | Package (`1`) vs TP-Only (`2`) vs SAOD (`3`) & Multi-Insurer Compare | `PARITY` | Exact zeroing of OD/Add-on for TP-Only (`2`) and TP for SAOD (`3`). |

---

### 2.3 Phase 7 — Policy Booking, Inward, Commission Split & Cancellation (`LBR-041`..`LBR-070`, `LBR-107`)

| Rule Range | Domain | Post-Remediation Classification | Verification Summary |
|---|---|---|---|
| `LBR-041`..`LBR-046` | Inward Generation, Atomic Single-Unit-of-Work Booking (`DEF-004`), Hierarchy Resolution | `PARITY` + `LEGACY DEFECT MITIGATED` (`DEF-004`) | `SELECT ... FOR UPDATE` on `tbl_inward_sequences` inside atomic DB transaction. |
| `LBR-047` | Multi-Bucket Commission & GCV + HDFC ERGO (`InsuranceCompanyId = 2`, `PolicyTypeId > 18`) Net-Only Rule | **PARITY** (`GAP-P7-001` Remediated) | Standard 3-bucket (`OD`, `Net/TP`, `Extra`) commission plus GCV + HDFC ERGO Net-only branch (`Net = OD + TP`, `OD = 0`, `Extra = 0`). |
| `LBR-048`..`LBR-055` | Cut & Pay, E-Wallet Deduction, `IsQualityCheck = 0` for Insurer `(3, 32)` + `PolicyTypeId > 18`, `PolicyNo` Uniqueness (`DEF-005`) | **PARITY** (`GAP-P7-001` Remediated) + `LEGACY DEFECT MITIGATED` (`DEF-005`) | Exact `IsCompletePayment` flag, `IsQualityCheck` insurer rule, and duplicate policy guard. |
| `LBR-056`..`LBR-064`, `LBR-107` | Accounting Entries (`AccTransId = 1, 2, 3`), Non-Motor `15%` Default TDS, Policy Cancellation (`PolicycancelId`, `CustVehId = 500` Sentinel Option) | **PARITY** (`GAP-P7-002` Remediated) | `motor_or_non_motor="NONMOTOR"` defaults `tds_percent` to `15.00%`; `use_legacy_cust_veh_id_500_sentinel=True` supports legacy `CustVehId = 500` cancellation sentinel. |

---

### 2.4 Phase 8 — Payments, Cheques, Bounce/Penalty, Reconciliation & E-Wallet (`LBR-091`..`LBR-105`)

| Rule Range | Domain | Post-Remediation Classification | Verification Summary |
|---|---|---|---|
| `LBR-091`..`LBR-100` | Cheque Lifecycle (`RECEIVED -> DEPOSITED -> CLEARED \| BOUNCED -> RE_PRESENTED`), Bounce Penalty, Contra Reversal (`DEF-006`) | `PARITY` + `INTENTIONAL HARDENING` / `LEGACY DEFECT MITIGATED` (`GAP-P8-001`, `DEF-006`) | Preserves `tbl_account` audit history via balanced contra entries (`AccTransId = 13, 14`), persists `PenaltyAmount`, and resets `IsCompletePayment = 0`. |
| `LBR-101`..`LBR-105` | Insurer Payment Reconciliation & E-Wallet Lock/Release (`DEF-007`) | `PARITY` + `LEGACY DEFECT MITIGATED` (`DEF-007`) | Row-locked E-Wallet debit/credit/lock/release preventing negative balance race conditions. |

---

### 2.5 Phase 9 — Commission, TDS, Cut & Pay, Payout, Vouchers & Trial Balance (`LBR-065`..`LBR-070`, `LBR-106`..`LBR-120`)

| Rule Range | Domain | Post-Remediation Classification | Verification Summary |
|---|---|---|---|
| `LBR-065`..`LBR-070`, `LBR-106`..`LBR-120` | Canonical `AccTransId` (`1..16`), System `LedgerMId` (`1161`, `2113`, `1930`, `1878`), Agent/Franchise Payouts, TDS Vouchers, Trial Balance (`variance == 0.00`) | **PARITY** (`GAP-P10-002` Remediated) | `LEGACY_ACC_TRANS_TYPE_MAP` and `LEGACY_SYSTEM_LEDGER_META` enforce canonical legacy IDs while maintaining 100% double-entry Trial Balance (`variance == 0.00`). |

---

### 2.6 Phase 10 — Claims, Endorsements, Policy Modification, Commission Recovery & Refunds (`LBR-121`..`LBR-140`)

| Rule Range | Domain | Post-Remediation Classification | Verification Summary |
|---|---|---|---|
| `LBR-121`..`LBR-123` | Claim Intimation, Coverage Validation, Assessment, `FinalBill` (`BillAmt`, `ICLAmt`, `ILAmt`), Zero-Ledger-Impact Settlement & Reversal | **PARITY** (`GAP-P10-001` & `GAP-P10-004` Remediated) | Claim settlement and reversal write `0` rows to `tbl_account` (`tbl_claims`-only operational tracking) and persist `bill_amount`, `icl_amount`, and `il_amount`. |
| `LBR-124`..`LBR-128` | 22-Subtype Endorsement Catalog (`EndorsementTypeId` `1..22`), `OWNERSHIP_TRANSFER` (`12`) New Customer Creation, `NCB_RECOVERY` (`13` `NcbRecovAmt`) | **PARITY** (`GAP-P10-003` Remediated) | `OWNERSHIP_TRANSFER` creates a new `Customer` row in `tbl_customer` and rebinds `policy.CustomerId` and `vehicle.CustomerId` (restored on reversal); all 22 legacy endorsement IDs mapped. |
| `LBR-129`..`LBR-132` | Endorsement Financial Delta, `LedgerMId = 1161` Commission Adjustment (`AccTransId = 3`), 3-Leg Endorsement Fee Split (`LedgerMId = 1878`), Paid-Commission Recovery, Refund Disbursement/Reversal | **PARITY** (`GAP-P10-002` Remediated) | Exact `LedgerMId = 1161` commission posting and 3-leg `LedgerMId = 1878` endorsement fee split (`AccTransId = 2, 2, 1`). |
| `LBR-133`..`LBR-140` | Document Storage Key Safety (`DEF-010`) & 12-Role RBAC Scoping | `PARITY` + `INTENTIONAL HARDENING` (`GAP-P11-001`, `DEF-010`) | Safe relative `storage_key` validation and strict branch/principal isolation. |
