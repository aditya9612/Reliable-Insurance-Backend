# Phase 0 → Phase 10 Legacy Baseline vs Actual Implementation: Forensic Compatibility Final Report

**Audit Date**: 2026-10-07  
**Audited Repository**: `Reliable-Insurance-Backend` (FastAPI / Python / Async SQLAlchemy 2.0 / MySQL 8.0)  
**Legacy Baseline Source**: `docs/migration/01_legacy_project_inventory.md` through `docs/migration/21_legacy_baseline_final_report.md` (extracted from `InsurancefinalNew` C# / .NET Framework 4.0 / ASP.NET WebForms / ASMX / ASHX / ADO.NET)  
**Audit Mode**: **READ-ONLY FORENSIC PARITY AUDIT** (Zero application code, test, migration, or database modifications performed)

---

## 1. Executive Summary

This report presents the findings of an exhaustive, line-by-line forensic compatibility audit comparing the **Legacy Business Behavior Baseline** (`InsurancefinalNew` C#/.NET 4.0) against the **Actual Implementation** of `Reliable-Insurance-Backend` across **Phase 0 through Phase 10**.

### Key Headline Metrics
- **Total Legacy Business Rules Audited (`LBR-001` → `LBR-140`)**: **140 / 140**
  - `PARITY`: **85** (60.7%)
  - `INTENTIONAL HARDENING`: **14** (10.0%)
  - `LEGACY DEFECT MITIGATED`: **13** (9.3% — covering all 11 legacy defects `DEF-001` through `DEF-011`)
  - `DEVIATION`: **16** (11.4% — consolidated into **8 distinct gap items** in the Gap Register: `1 P0`, `3 P1`, `3 P2`, `1 P3`)
  - `MISSING`: **9** (6.4% — consolidated into **7 distinct gap items**: `6 P2`, `1 P3`)
  - `UNKNOWN — EVIDENCE NOT AVAILABLE`: **3** (2.1% — unextracted MySQL stored procedure SQL bodies, DB triggers/DDL, and production tariff/commission rows)
- **Legacy Known Defects (`DEF-001` → `DEF-011`)**: **11 / 11 Mitigated (`100%`)**
- **Legacy Column Typo Compatibility**: **11 / 11 Physical Column Typos Preserved (`100%`)** (`TransanctionId`, `ODPermium`, `TPPermium`, `NetPermium`, `NCBPermium`, `finalPrmium`, `QuatationCode`, `ChaiseNo`, `MoblieNo1`, `ProfitofNetCommision`, `totalCommision`)
- **Automated Test Suite Status**: **289 passed, 0 failed** (verified against local synthetic test harness; however, tests assert the *new* implementation's rules and therefore do not catch the 4 `P0`/`P1` legacy parity deviations below).
- **Overall Forensic Parity Verdict**: **`RED — PARITY FAILURE`** (due to **1 `P0`** and **3 `P1`** confirmed business/financial deviations that must be remediated before production cutover).

---

## 2. Audit Methodology

1. **Evidence Hierarchy**:
   - **Legacy Source of Truth**: The 21 forensic baseline documents in `docs/migration/01_legacy_project_inventory.md` through `docs/migration/21_legacy_baseline_final_report.md` (note: located directly under `docs/migration/` in this repository workspace).
   - **New Implementation Source of Truth**: Actual FastAPI executable Python code in `app/api/v1/endpoints/*`, `app/services/*`, `app/repositories/*`, `app/models/*`, `app/schemas/*`, `app/core/*`, `alembic/versions/*`, and `tests/*`.
2. **No-Assumption Verification**:
   - Every formula, tax rate, commission basis, ledger polarity (`Amount > 0 = DR`, `Amount < 0 = CR`), `AccTransId` code, `LedgerMId` constant, state transition, and column name in `app/` was inspected directly and compared against the C# source extracts in `docs/migration/`.
3. **Strict Read-Only Discipline**:
   - No application code, schemas, migrations, or tests were modified during this audit. Production database `brahmainsurance` was never accessed.

---

## 3. Legacy Baseline Inventory Summary

Per `docs/migration/01_legacy_project_inventory.md` through `04_legacy_stored_procedure_map.md` and `21_legacy_baseline_final_report.md`:

| Legacy Artifact Category | Confirmed Baseline Count | Primary Legacy Source Files |
|---|---|---|
| Solution Projects | 4 (`Insurance`, `BLL_Insurance`, `DAL_Insurance`, `AllMaster`) | `InsurancefinalNew.sln` |
| WebForms Pages (`.aspx`) | 213 (`3` root + `210` in `Clerk/`) | `Log_In.aspx`, `Clerk/*.aspx` |
| ASMX / AJAX `[WebMethod]` Endpoints | 416 (`339` in `Service.asmx.cs`, `41` in `SearchMethods.aspx.cs`, `16` in `AppSearchMethod.aspx.cs`, `2` in `VehicleService.asmx.cs`, `18` across 11 `.aspx.cs` files) | `Service.asmx.cs`, `Clerk/SearchMethods.aspx.cs` |
| HTTP Handlers (`.ashx`) & Webhooks | 3 (`DownloadAll.ashx`, `ImageHandler.ashx`, `PolicyParserWebhook.aspx`) | Root & `Clerk/` |
| BLL Methods | 1,880 | `BLL_Insurance/BLL_Operations.cs` |
| DAL Methods | 1,932 | `DAL_Insurance/DAL_Operations.cs` |
| Unique MySQL Stored Procedures | 943 (across 2,338 call sites) | `DAL_Insurance/DAL_Operations.cs` |
| Inline Raw SQL Queries | 124 (`19` in `DAL_Operations.cs` + `105` in `.aspx.cs`/`.ashx.cs`) | `DAL_Operations.cs`, `Clerk/*.aspx.cs` |
| Entity DTO Classes (`API_*`) | 188 | `AllMaster/AllMaster.cs` |
| Directly Referenced SQL Tables | 36 | `03_legacy_database_inventory.md` |
| Numbered Business Rules | 140 (`LBR-001` – `LBR-140`) | `19_legacy_business_rule_master_register.md` |
| Confirmed Legacy Defects | 11 (`DEF-001` – `DEF-011`) | `18_legacy_known_defects.md` |

---

## 4. Phase 0–4 Foundation Audit

- **Architecture & Configuration (`app/main.py`, `app/core/config.py`, `app/db/session.py`)**: FastAPI application factory, Pydantic settings, async SQLAlchemy 2.0 engine (`aiomysql`/`asyncmy` + SQLite async test compatibility), structured JSON logging with request correlation IDs, global exception handlers (`app/core/exceptions.py`), and health/readiness probes (`/api/v1/health/live`, `/api/v1/health/ready`) are fully implemented.
- **Security & SQL Injection Hardening (`DEF-008`)**: All 124 legacy raw SQL concatenation sites have been replaced by parameterized SQLAlchemy 2.0 ORM queries.
- **Thread Safety (`DEF-007`)**: All 40+ WebForms `public static` cross-request mutable variables have been eliminated in favor of stateless request-scoped dependency injection.
- **Classification**: `INTENTIONAL HARDENING` / `LEGACY DEFECT MITIGATED`.

---

## 5. Phase 5 Customer & Vehicle Audit

- **Verified Parity (`app/services/customer.py`, `app/services/vehicle.py`, `app/services/masters.py`)**:
  - Customer creation, update, soft-delete (`status_id = 2`), mobile deduplication (`LBR-007`), pan/GST/Aadhar validation, and legacy column `MoblieNo1` (`LBR-006`) match legacy `adm_Customer.aspx.cs`.
  - Vehicle creation, update, registration normalization, `"NEW"` unregistered vehicle handling (`LBR-010`), 7 vehicle classes (`1=Two Wheeler` through `7=3W GCV`), Make/Model hierarchy validation, and legacy column `ChaiseNo` (`LBR-009`) match `adm_CustomerVehicle.aspx.cs`.
- **Identified Gaps**:
  - **`GAP-P5-001` (`MISSING`, `P2`)**: Signzy Vehicle RC API integration (`RC_CheckVehicleDtl.aspx.cs`, `LBR-011`) is not implemented (deferred to Phase 12).
  - **`GAP-P5-002` (`MISSING`, `P2`)**: Mobile OTP verification (`USP_UpdateOTP`, `LBR-002`) and `API_LoginHistory` DB table logging (`LBR-024`) are not implemented.
  - **`GAP-P5-003` (`DEVIATION`, `P3`)**: Customer Sundry Debtor ledger account creation (`LBR-008`) is deferred to policy/accounting posting rather than triggered inside `POST /api/v1/customers`.

---

## 6. Phase 6 Quotation & Rating Audit

- **Verified Parity & Defect Mitigations (`app/services/rating.py`, `app/services/quotation.py`)**:
  - Multi-insurer quotation header (`tbl_quotation` with `QuatationCode`) and option lines (`tbl_quotationtransaction`) match `Qt_QuotationRequest.aspx.cs` and `SelfQuotationRequest*.aspx.cs` (`LBR-026`–`LBR-028`).
  - Basic OD, OD Discount, Electrical Accessories (`4%`), Non-Electrical Accessories, Bi-Fuel OD & TP (`60 INR`), IMT-23 (`15%`), NCB deduction strictly before ZeroDep/Add-ons (`LBR-034`), PCV per-passenger TP, CPA, LL Paid Driver, Net Premium, and TP-Only / SAOD zeroing rules (`LBR-029`–`LBR-040`, `LBR-043`) match legacy formulas.
  - Mitigates **`DEF-004`** (includes `ZeroDepPremium` in GCV `TotalA`), **`DEF-005`** (includes `pa_paid_driver_amount` in `TotalB`), and **`DEF-006`** (deterministic vehicle age math).
- **Identified Deviations**:
  - **`GAP-P6-001` (`DEVIATION`, `P1`)**: Legacy `Clerk/adm_PolicyDetails.aspx.cs` (`L636-L644`) applies **5% GST** on Basic TP for GCV (`VehicleTypeId == 2`) and 3W GCV (`VehicleTypeId == 7`) when `RiskStartDate >= 2025-09-23`, and **12% GST** before `2025-09-23`. FastAPI `RatingEngineService` (`app/services/rating.py:L515`) always applies **12% GST** on Basic TP when `gcv_split_tp_gst=True`, overcharging Basic TP GST by 7% for post-`2025-09-23` GCV policies.
  - **`GAP-P6-002` (`DEVIATION`, `P2`)**: Legacy C# uses `double` + `.NET` `Math.Round` (`MidpointRounding.ToEven`) and C# `int` division `(((Weight - 12000) * 27) / 100)` for GCV extra tonnage; FastAPI uses `Decimal` + `ROUND_HALF_UP` (`round_rupee`), which can differ by `±1 INR` on `.50` midpoints or non-100kg GVW increments.

---

## 7. Phase 7 Policy Booking Audit

- **Verified Parity & Defect Mitigations (`app/services/policy_booking.py`)**:
  - Supports direct policy booking, full booking with `OtherPolicyDetails` (`tbl_OtherPolicyDetails`), `PolicyAddOn` (`tbl_policyaddon`), `PolicyDocument` (`tbl_policydocument`), multi-mode payment splits (`tbl_paymentdetails`), and atomic quotation-to-policy conversion (`LBR-056`–`LBR-058`, `LBR-064`–`LBR-069`).
  - Preserves all legacy column typos on `tbl_transaction` (`ODPermium`, `TPPermium`, `NetPermium`, `NCBPermium`, `finalPrmium`, `ProfitofNetCommision`, `totalCommision`).
  - Mitigates **`DEF-002`** (Indian Financial Year `dt.month <= 3` boundary in `resolve_financial_year`) and **`DEF-011`** (single atomic DB transaction across parent and child booking tables).
- **Identified Gaps & Deviations**:
  - **`GAP-P7-001` (`DEVIATION`, `P2`)**: Missing hardcoded GCV + HDFC ERGO (`InsuranceCompanyId == 2 && PolicyTypeId > 18`) special commission calculation (`BLL_FillCommisionPercentForAllGCVHDFCBankCalculatin`) and Insurer `(3, 32)` inward status skip (`PolicyTransactionNew.aspx.cs:L413-L511, L1515`).
  - **`GAP-P7-003` (`MISSING`, `P2`)**: Telecaller target achievement auto-increment (`BLL_Updatetargetachieved`, `LBR-061`) and prior-year policy renewal status update (`BLL_UpdatePreYearRenewalStatus`, `LBR-062`) are not triggered on booking.
  - **`GAP-P7-004` (`MISSING`, `P2`)**: Health Insurance family member grid and portability persistence (`USP_InsertTransactionHealthMemberDetails`, `USP_InsertTransactionHealthPortability`, `LBR-063`) are not implemented.

---

## 8. Phase 8 Payment, Cheque, Reconciliation & Wallet Audit

- **Verified Parity & Defect Mitigations (`app/services/payment_engine.py`)**:
  - Supports all 6 legacy payment modes (`1=Cash`, `2=Cheque`, `3=Online`, `4=Credit`, `5=Cut & Pay`, `6=E-Wallet`) and `PaidBy`/`PayTo` indicators (`LBR-081`, `LBR-082`).
  - Preserves physical column typo `TransanctionId` on `tbl_paymentdetails` and `tbl_CutAndPayPayment` (`LBR-087`).
  - Implements full cheque lifecycle (`RECEIVED/UNCLEAR` $\rightarrow$ `DEPOSITED` $\rightarrow$ `CLEARED` / `BOUNCED` $\rightarrow$ `REPRESENTED`), updating `tbl_transaction.ChequeStatusId` (`1=Clear`, `2=Unclear`, `3=Bounced`), recording `UnclearChequeCharge` (`tbl_unclearchequecharges`), and posting bounce reversal + penalty legs (`LBR-083`, `LBR-088`–`LBR-090`, `LBR-098`, `LBR-099`).
  - Implements Insurer Payment Reconciliation (`tbl_reconciliation`, `tbl_multipletransactions`) with variance calculation (`LBR-092`).
  - Implements Franchise/Agent E-Wallet top-up request (`PENDING`), Admin/Accountant approval credit, reservation lock/release/consume, and policy debit, mitigating **`DEF-009`** (`available_balance >= amount` using `Decimal` instead of `>` with `Convert.ToInt32`) (`LBR-084`, `LBR-085`, `LBR-093`).
- **Identified Gaps**:
  - **`GAP-P8-001` (`MISSING`, `P2`)**: Overdue uncleared cheque login lock (`Adm_LockChequeEntry.aspx.cs` / `BLL_LockChequeClearingCount`, `LBR-091`) is not implemented at login.

---

## 9. Phase 9 Commission, TDS, Cut & Pay, Voucher, Ledger & Trial Balance Audit

- **Verified Parity & Defect Mitigations (`app/services/commission_accounting.py`)**:
  - Implements 4-tier commissions (`Company/RA`, `Agent`, `Franchise`, `Sub-Agent`) across `OD`, `TP`, `NET`, and `OD_ADDON` bases, `ProfitofNetCommision`, TDS deduction, Cut & Pay (`Gross - Comm + TDS`), payout batching (`PENDING` $\rightarrow$ `APPROVED` $\rightarrow$ `PAID`), and commission clawback/reversal (`LBR-101`–`LBR-105`, `LBR-114`–`LBR-117`).
  - Mitigates **`DEF-001`** by evaluating `franchise_cal_on` independently of `agent_cal_on`.
  - Preserves signed single-column `Amount` polarity in `tbl_account` (`Amount > 0 = DR`, `Amount < 0 = CR`, `SUM == 0.00`), Receipt/Payment/Contra/Journal vouchers (`tbl_voucher`), ledger running balance statements, and Trial Balance verification (`LBR-106`–`LBR-111`, `LBR-118`–`LBR-120`).
- **Identified Deviations**:
  - **`GAP-P10-002` (`DEVIATION`, `P1`)**: Legacy `API_Account` uses strictly `AccTransId` codes `1` (Receipt), `2` (Payment), and `3` (Journal) and hardcoded system `LedgerMId` IDs (`1161` Commission/Wallet Control, `2113` TDS Payable, `1930` SalesEx Commission, `1878` Endorsement Income). FastAPI introduces custom `AccTransId` codes `4..18` and synthetic system ledger IDs (`1000..2201`), and omits the `1930` Sales Executive commission journal leg.
  - **`GAP-P7-002` (`DEVIATION`, `P2`)**: Non-Motor fixed 15% TDS rate (`adm_NonMotarTransaction.aspx.cs:L604`) is not automatically selected when `vehicle_type_id == 0` (defaults to `5.00%` unless passed by caller).

---

## 10. Phase 10 Claims, Endorsement, NCB Recovery & Policy Cancellation Audit

- **Verified Parity & Defect Mitigations (`app/services/claims_endorsement.py`)**:
  - Claim eligibility check (`RiskStartDate <= LossDate <= RiskEndDate` on active non-cancelled policy, `LBR-121`), surveyor assignment, document registration (`DEF-010` mitigated), NCB Recovery (`LBR-127`, `LBR-128`, `DEF-001` mitigated), Policy Cancellation premium reversal, commission/TDS clawback, and wallet/bank refund (`LBR-129`, `LBR-134`), 32-bit `endorsement_id` (`DEF-003` mitigated), and atomic transaction rollback (`DEF-011` mitigated) are implemented and verified.
- **Identified Deviations & Missing Capabilities**:
  - **`GAP-P10-001` (`DEVIATION`, `P0` — Critical Financial Deviation)**: In legacy `Clerk/CL_ClaimNew.aspx.cs` (`10_legacy_claims_baseline.md` Sec 3, `LBR-123`), Claims are purely operational records paid by the insurance company to the insured/garage and **never** post entries to the broker's general ledger (`tbl_account`). In FastAPI, `ClaimsEndorsementService.settle_claim` (`app/services/claims_endorsement.py:L255-L315`) posts a double-entry journal (`AccTransId = 18`, `DR 2000 Insurer / CR 2200 Customer or 2201 Garage`) into `tbl_account`, corrupting broker ledger balances and Trial Balance totals with insurer claim settlement amounts.
  - **`GAP-P10-003` (`DEVIATION`, `P1`)**: Legacy `AppEndorsementforApproval.aspx.cs` dispatches **22 integer `EndorsementId` types (`1..22`)**, includes a dedicated `OwnerTransferEndorsement.aspx.cs` workflow that creates a new `CustomerId` (`LBR-130`), and posts a 3-leg endorsement service fee split (`+txtPaidAmount` to Bank/Cash, `-txtCmpAmt` to `1878` Endorsement Income, `-txtCmpAmt` to PayTo Ledger, `LBR-126`). FastAPI consolidates endorsements into 9 string enum types, mutates the existing customer in place on `CUSTOMER_CORRECTION` instead of creating a new `CustomerId` for ownership transfer, and omits the `1878` endorsement service-fee split.
  - **`GAP-P10-004` (`MISSING`, `P2`)**: Legacy claims sub-entities in `CL_ClaimNew.aspx.cs` (`API_SpotServe`, `API_GarageServe`, `API_ClaimQuotation` + `tbl_claim_quotation_img`, `API_FinalBill` `BillAmt`/`ICLAmt`/`ILAmt` fields, and `API_ClaimAudio` `.mp3` recordings in `tbl_claimaudiolist`, `LBR-122`) were simplified into a single `tbl_claims` + `tbl_claimdocument` model.
  - **`GAP-P7-002` (`DEVIATION`, `P2`)**: Non-Motor cancellation sentinel `CustVehId = 500` (`adm_PolicyCancel.aspx.cs:L517`, `LBR-133`) is not set on cancellation.

---

## 11. RBAC, Branch & Ownership Hierarchy Audit

Full details are documented in `docs/migration/phase_10_rbac_parity_matrix.md`.
- **Branch Isolation (`LBR-004`, `LBR-018`, `LBR-019`)**: Global Admin (`RoleId 1, 10`) vs Branch-scoped roles (`Branch Manager`, `Clerk`, `Telecaller`, `Sales Executive`) are strictly enforced across all Phase 5–10 endpoints via `app/core/rbac.py`.
- **Principal Isolation (`LBR-020`, `LBR-021`)**: `Agent` (`agent_id`), `Franchise` (`franchise_id`), and `Customer` (`customer_id`) principals are isolated to their own records and blocked (`HTTP 403`) from privileged approval/settlement actions.
- **6-Actor Hierarchy (`LBR-005`, `LBR-012`)**: All 6 actors (`TelecallerId`, `TeamLeaderId`, `SalesManagerId`, `AgentId`, `SubAgentId`, `FranchiseId`) are persisted and linked on `tbl_transaction`.

---

## 12. Database Schema & Typo Compatibility Audit

Full details are documented in `docs/migration/phase_10_database_parity_matrix.md`.
- All **11 legacy column spelling typos** (`TransanctionId`, `ODPermium`, `TPPermium`, `NetPermium`, `NCBPermium`, `finalPrmium`, `QuatationCode`, `ChaiseNo`, `MoblieNo1`, `ProfitofNetCommision`, `totalCommision`) are preserved in physical SQLAlchemy `mapped_column(...)` definitions while exposing clean Pythonic snake_case attributes and Pydantic aliases.

---

## 13. Stored Procedure Replacement Audit

Full details are documented in `docs/migration/phase_10_database_parity_matrix.md` (Section 4).
- All core CRUD, rating, booking, payment, cheque, reconciliation, wallet, commission, voucher, ledger, trial balance, claim, endorsement, NCB recovery, and policy cancellation SP workflows from Phases 5–10 have been replaced with async SQLAlchemy 2.0 repository/service methods, subject to the specific gaps documented in `phase_10_legacy_vs_new_gap_register.md` and `GAP-UNK-001` (unextracted SQL bodies of the 943 stored procedures).

---

## 14. Legacy Defects `DEF-001` → `DEF-011` Audit

All 11 confirmed legacy defects from `docs/migration/18_legacy_known_defects.md` have been **MITIGATED** in `Reliable-Insurance-Backend`:

| Defect ID | Legacy Defect Summary | New Backend Mitigation | Status |
|---|---|---|---|
| **DEF-001** | `adm_NcbRecovery.aspx.cs:L358, L1268` checks `AgtCalOn` instead of `FRCalOn` when recalculating Franchise commission. | Evaluates `franchise_cal_on` / `franchise_comm_pct` independently in `commission_accounting.py` & `claims_endorsement.py`. | `LEGACY DEFECT MITIGATED` |
| **DEF-002** | `PE_TransactionEntry.aspx.cs:L9823` uses `currentMonth >= 3`, putting March into the wrong Indian Financial Year. | `resolve_financial_year` (`app/repositories/policy_booking.py`) uses `dt.month <= 3`. | `LEGACY DEFECT MITIGATED` |
| **DEF-003** | `AppEndorsementforApproval.aspx.cs:L209` uses `Convert.ToInt16(Endorsement_Id)`, overflowing at `32,767`. | Uses 32-bit SQL `INT` and Python `int`. | `LEGACY DEFECT MITIGATED` |
| **DEF-004** | `SelfQuotationRequest.aspx.cs:L1042` omits `ZeroDepPremium` (`G`) from GCV `TotalA`. | `RatingEngineService.calculate_premium` includes `zero_dep_premium` in `total_od_with_addons` for all vehicle classes. | `LEGACY DEFECT MITIGATED` |
| **DEF-005** | `SelfQuotationRequest.aspx.cs:L1057` hardcodes `PApaiddriver2 = 0` in GCV/PCV self-quote. | `RatingEngineService.calculate_premium` includes `pa_paid_driver_amount` in `total_tp_premium`. | `LEGACY DEFECT MITIGATED` |
| **DEF-006** | `SelfQuotationRequestPCV.aspx.cs:L520-L536` uses uninitialized `parts1`/`slab3` variables in vehicle age calculation. | `RatingEngineService.calculate_vehicle_age` uses deterministic date subtraction. | `LEGACY DEFECT MITIGATED` |
| **DEF-007** | 40+ `public static` mutable fields in WebForms code-behind cause cross-request race conditions. | Stateless request-scoped FastAPI services + `SELECT ... FOR UPDATE` row locking. | `LEGACY DEFECT MITIGATED` |
| **DEF-008** | 124 raw unparameterized SQL string concatenations in `DAL_Operations.cs` & pages. | 100% bound-parameter SQLAlchemy 2.0 ORM queries. | `LEGACY DEFECT MITIGATED` |
| **DEF-009** | `PolicyTransactionNew.aspx.cs:L1669` uses `balance > Convert.ToInt32(amt)` on E-Wallet deduction. | `WalletService` uses `Decimal` comparison `available_balance >= amount`. | `LEGACY DEFECT MITIGATED` |
| **DEF-010** | `CL_ClaimNew.aspx.cs:L415` deletes final bill docs from `~/ClaimPhoto/` instead of `~/Claim_Final_Bill_Doc/`. | `ClaimDocument` stores explicit per-document `file_path` and `document_type`. | `LEGACY DEFECT MITIGATED` |
| **DEF-011** | Multi-step policy, payment, commission, NCB recovery, and cancellation writes execute without DB transactions. | Single atomic `AsyncSession` transaction with full rollback on error across all Phase 7–10 mutations. | `LEGACY DEFECT MITIGATED` |

---

## 15. Business Rules `LBR-001` → `LBR-140` Summary

Every single rule from `LBR-001` through `LBR-140` is audited in `docs/migration/phase_10_business_rule_parity_matrix.md`:
- **85 Rules**: `PARITY`
- **14 Rules**: `INTENTIONAL HARDENING`
- **13 Rules**: `LEGACY DEFECT MITIGATED`
- **16 Rules**: `DEVIATION` (`LBR-008`, `LBR-041`, `LBR-042`, `LBR-047`, `LBR-059`, `LBR-070`, `LBR-071`, `LBR-079`, `LBR-094`, `LBR-104`, `LBR-112`, `LBR-113`, `LBR-123`, `LBR-124`, `LBR-126`, `LBR-133`)
- **9 Rules**: `MISSING` (`LBR-002`, `LBR-011`, `LBR-024`, `LBR-061`, `LBR-062`, `LBR-063`, `LBR-091`, `LBR-122`, `LBR-130`)
- **3 Rules**: `UNKNOWN — EVIDENCE NOT AVAILABLE` (Cross-cutting SP bodies & master table rows in `LBR-055`, `LBR-103`, `LBR-124`).

---

## 16. External Integrations, Reporting & File Handling Scope Audit

Per `docs/migration/15_legacy_integrations_external_services.md`, `16_legacy_reporting_export_baseline.md`, and `17_legacy_document_file_baseline.md`:
- **Deferred to Phases 11–14 (`GAP-P5-001`, `GAP-P11-001`)**:
  - Signzy Vehicle RC API (`RC_CheckVehicleDtl.aspx.cs`)
  - HiCaliber Policy PDF Parser OCR Webhook (`PolicyParserWebhook.aspx.cs`)
  - SMS Gateway (`Send_SMS.cs`) & OneSignal Push Notifications (`Service.asmx.cs`)
  - Binary file upload disk storage, `DownloadAll.ashx` ZIP streaming, `ImageHandler.ashx` image streaming, and iTextSharp PDF binary generation (`CreatePDF`).

---

## 17. Unknown Evidence Register

1. **`GAP-UNK-001` (943 Stored Procedure SQL Bodies)**: The C# repository contains all 943 SP names and parameter lists in `DAL_Operations.cs`, but no `.sql` dump of the MySQL stored procedures is present in the codebase.
2. **`GAP-UNK-002` (Live MySQL DDL Constraints, Indexes & Triggers)**: Physical constraints and triggers for ~152 SP-encapsulated tables not queried via inline SQL in C# are unavailable without a schema dump.
3. **`GAP-UNK-003` (Production Master Data Rows)**: Live tariff slabs (`tbl_tariffmaster`), commission grids (`tbl_CommissionPercentage`), and TDS slabs (`tbl_TDSMaster`) in `brahmainsurance` are off-limits per strict production safety rules.

---

## 18. Test Coverage & Blind Spot Audit

While the repository has **289 passing automated tests** across unit, integration, concurrency, atomicity, golden parity, and E2E suites (`tests/unit/*`, `tests/integration/*`, `tests/e2e/*`), forensic inspection identified the following **test blind spots** where tests validated the *new* code's assumptions rather than the legacy C# baseline:
1. **`tests/unit/test_phase10_unit.py` & `tests/integration/test_phase10_golden_parity.py`**: Explicitly assert that `settle_claim` creates 2 `AccountEntry` rows (`AccTransId = 18`), cementing `GAP-P10-001` instead of asserting legacy `LBR-123` (zero `tbl_account` rows on claim settlement).
2. **`tests/unit/test_phase6_rating_unit.py` & `tests/integration/test_phase6_golden_parity.py`**: Test GCV split GST using `12%` on Basic TP for `2026` dates without testing the legacy `adm_PolicyDetails.aspx.cs:L636-L644` cutover (`RiskStartDate >= 2025-09-23` $\rightarrow$ `5%` Basic TP GST, `GAP-P6-001`).
3. **`tests/integration/test_phase9_golden_parity.py` & `test_phase10_golden_parity.py`**: Assert custom `AccTransId` codes (`4..18`) and synthetic ledger IDs (`1000..2201`) instead of legacy `AccTransId` (`1, 2, 3`) and hardcoded `LedgerMId` (`1161, 2113, 1930, 1878`, `GAP-P10-002`).
4. **`tests/integration/test_phase10_claims_endorsement_api.py`**: Tests the 9 symbolic string endorsement types rather than the 22 legacy integer `EndorsementId` codes (`1..22`), `OwnerTransferEndorsement` new-`CustomerId` flow, or `1878` endorsement fee split (`GAP-P10-003`).

---

## 19. Prioritized Remediation Backlog (No Fixes Applied)

Per strict audit-only instructions, **zero code changes have been made**. To reach `GREEN — FULL PARITY`, the following prioritized remediations are required in a subsequent implementation phase:

1. **[P0 — `GAP-P10-001`] Remove Broker General Ledger Posting from `ClaimsEndorsementService.settle_claim` (`LBR-123`)**:
   - Stop posting `AccTransId = 18` (`DR 2000 Insurer / CR 2200 or 2201`) into `tbl_account` during `settle_claim` (or gate behind an explicit optional flag defaulting to `False`), matching `Clerk/CL_ClaimNew.aspx.cs`.
2. **[P1 — `GAP-P6-001`] Implement GCV `RiskStartDate >= 2025-09-23` 5% Basic TP GST Rule (`LBR-041`)**:
   - In `RatingEngineService.calculate_premium` and `PolicyBookingService`, apply **5% GST** on `BasicTP` for GCV (`VehicleTypeId in (2, 7)`) when `risk_start_date >= date(2025, 9, 23)` and **12% GST** when `risk_start_date < date(2025, 9, 23)`, matching `adm_PolicyDetails.aspx.cs:L636-L644`.
3. **[P1 — `GAP-P10-002`] Align `AccTransId` (`1, 2, 3`) & Hardcoded System `LedgerMId` Constants (`1161, 2113, 1930, 1878`)**:
   - Map all `tbl_account` inserts to legacy `AccTransId` (`1=Receipt`, `2=Payment`, `3=Journal`)—preserving granular event types in a dedicated metadata column or narration—and align system ledger IDs with `1161`, `2113`, `1930`, and `1878`.
4. **[P1 — `GAP-P10-003`] Add 22 Integer `EndorsementId` (`1..22`) Mapping, Owner-Transfer New-`CustomerId` Workflow & `1878` Endorsement Fee Split (`LBR-124`, `LBR-126`, `LBR-130`)**:
   - Support legacy integer `EndorsementId` (`1..22`) dispatch, implement `OwnerTransferEndorsement` new-`CustomerId` creation, and post the 3-leg `1878` endorsement fee journal when endorsement charges are collected.
5. **[P2 — `GAP-P7-001`, `GAP-P7-002`, `GAP-P6-002`, `GAP-P8-001`, `GAP-P10-004`, `GAP-P7-003`, `GAP-P7-004`, `GAP-P5-001`, `GAP-P5-002`]**:
   - Implement GCV+HDFC (`InsuranceCompanyId == 2 && PolicyTypeId > 18`) commission override, Insurer `(3, 32)` inward skip, Non-Motor 15% default TDS & `CustVehId = 500` cancellation sentinel, overdue cheque login lock flag, claims sub-entities (`SpotServe`, `GarageServe`, `ClaimQuotation`, `FinalBill` `ICLAmt`/`ILAmt`, `ClaimAudio`), telecaller target achievement & renewal status hooks, and health family member/portability tables.

---

## 20. Final Verdict

- **Verdict**: **`RED — PARITY FAILURE`**
- **Rationale**: Under Section 38 Verdict Rules (*"RED: Any confirmed material P0/P1 business or financial deviation. Do NOT force GREEN."*), the presence of **1 confirmed `P0` financial/accounting deviation** (`GAP-P10-001`: Claims settlement posting `AccTransId=18` ledger entries into `tbl_account` in violation of `LBR-123`) and **3 confirmed `P1` business/financial deviations** (`GAP-P6-001`: missing GCV post-`2025-09-23` 5% Basic TP GST rule; `GAP-P10-002`: `AccTransId 4..18` & synthetic ledger IDs replacing legacy `AccTransId 1..3` & `1161/2113/1930/1878`; `GAP-P10-003`: 9 symbolic endorsement types vs 22 integer `EndorsementId` codes, missing `OwnerTransferEndorsement` new-`CustomerId` workflow, and missing `1878` endorsement fee split) requires a **`RED — PARITY FAILURE`** classification until those `P0`/`P1` items are remediated.
