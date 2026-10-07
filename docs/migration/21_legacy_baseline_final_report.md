# 21 — Legacy Business Behavior Baseline: Final Forensic Audit Report

> **Forensic Classification**: `CONFIRMED FROM CODE`  
> **Repository Audited**: `c:\Users\Admin\Downloads\InsurancefinalNew_2026_09_23\InsurancefinalNew`  
> **Audit Mode**: 100% Read-Only Static & Forensic Code Extraction (Zero files modified)

---

## 1. Executive Summary & Quantitative Metrics

| Metric | Confirmed Count / Value | Source Evidence |
|---|---|---|
| **Solution Projects** | **4 Projects** (`InsurancefinalNew` WebForms root, `Insurance_Service` DTO/API lib, `Insurance_BLL`, `Insurance_DAL`) | `01_legacy_project_inventory.md` |
| **Target .NET Framework** | `.NET Framework 4.0` (C# 4.0) | `web.config`, `*.csproj` |
| **Total C# Source Files (`.cs`)** | **469 `.cs` files** | Repository scan |
| **Total ASP.NET WebForms Pages (`.aspx`)** | **213 `.aspx` pages** | Repository scan |
| **Total ASMX WebMethods (`[WebMethod]`)** | **416 WebMethods** in `Service.asmx.cs` | `02_legacy_api_inventory.md` |
| **Total HTTP Handlers (`.ashx`)** | **2 Handlers** (`DownloadAll.ashx.cs`, `ImageHandler.ashx.cs`) | `02_legacy_api_inventory.md`, `17_legacy_document_file_baseline.md` |
| **Total DAL Methods (`DAL_Operations.cs`)** | **1,932 methods** across **124,758 lines of code** | `01_legacy_project_inventory.md`, `04_legacy_stored_procedure_map.md` |
| **Total BLL Methods (`BLL_Operations.cs`)** | **1,880 methods** across **27,104 lines of code** | `01_legacy_project_inventory.md` |
| **Unique MySQL Stored Procedures Referenced** | **943 unique `USP_*` / SP names** (invoked across 2,338 call sites) | `04_legacy_stored_procedure_map.md` |
| **Inline Raw SQL Queries** | **124 raw SQL queries** referencing **36 distinct `tbl*` MySQL tables** | `03_legacy_database_inventory.md` |
| **DTO / Model Classes (`Insurance_Service`)** | **172 `API_*` classes** | `03_legacy_database_inventory.md` |
| **Extracted Master Business Rules** | **140 Rules (`LBR-001` – `LBR-140`)** | `19_legacy_business_rule_master_register.md` |
| **Confirmed Legacy Code Defects** | **11 Critical/High/Medium Defects (`DEF-001` – `DEF-011`)** | `18_legacy_known_defects.md` |

---

## 2. Deliverable Index (`docs/migration/legacy_baseline/`)

All 21 baseline specification documents have been generated and verified:

1. [`01_legacy_project_inventory.md`](./01_legacy_project_inventory.md) — Solution topology, projects, assemblies, configs, external integrations.
2. [`02_legacy_api_inventory.md`](./02_legacy_api_inventory.md) — Complete catalog of all 416 `Service.asmx.cs` `[WebMethod]` endpoints, `.ashx` handlers, and WebForms entry points.
3. [`03_legacy_database_inventory.md`](./03_legacy_database_inventory.md) — All 36 raw-SQL tables, 172 `API_*` entity schemas, 124 raw SQL queries, and legacy field typos (`TransanctionId`, `ODPermium`, `ChaiseNo`, `MoblieNo1`).
4. [`04_legacy_stored_procedure_map.md`](./04_legacy_stored_procedure_map.md) — Complete mapping of all 943 unique MySQL stored procedures, their callers, and parameter lists.
5. [`05_legacy_customer_vehicle_baseline.md`](./05_legacy_customer_vehicle_baseline.md) — Customer & Vehicle lifecycle, deduplication, Signzy KYC, and ledger account creation.
6. [`06_legacy_quotation_rating_baseline.md`](./06_legacy_quotation_rating_baseline.md) — Rating formulas for Private Car, Two Wheeler, GCV, PCV, and Misc-D (IDV, OD, IMT-23, NCB, ZeroDep, TP, CPA, LL, PA, 18% vs 12% GCV GST).
7. [`07_legacy_policy_booking_baseline.md`](./07_legacy_policy_booking_baseline.md) — Quick (`PolicyTransactionNew`) vs Detailed (`PE_TransactionEntry`) policy booking, 6-leg ledger posting, targets, and renewals.
8. [`08_legacy_payment_cheque_wallet_baseline.md`](./08_legacy_payment_cheque_wallet_baseline.md) — Multi-mode payments, cheque lifecycle, Franchise E-Wallet top-up/deduction, and Cut & Pay remittance.
9. [`09_legacy_commission_accounting_baseline.md`](./09_legacy_commission_accounting_baseline.md) — 4-tier commissions (Company, Agent, Franchise, Sub-Agent), `CalOn` codes (`1`/`2`/`3`), TDS, Accountant verification, Vouchers, Ledger, and Trial Balance.
10. [`10_legacy_claims_baseline.md`](./10_legacy_claims_baseline.md) — 3-stage Claim workflow (Intimation, Spot Survey, Final Bill), media uploads, and accounting independence.
11. [`11_legacy_endorsement_baseline.md`](./11_legacy_endorsement_baseline.md) — 22 Endorsement types (`EndorsementId` 1–22), approval dispatch, NCB Recovery (`adm_NcbRecovery`), and Policy Cancellation (`adm_PolicyCancel`).
12. [`12_legacy_rbac_branch_ownership_baseline.md`](./12_legacy_rbac_branch_ownership_baseline.md) — Authentication, `tbluserrights` RBAC, `BranchId` isolation, and 6-actor ownership hierarchy.
13. [`13_legacy_state_machine_baseline.md`](./13_legacy_state_machine_baseline.md) — Formal state machines for Quotations, Policy Transactions (`TStatus`), Cheques, E-Wallet Deposits, Endorsements, NCB Recovery, Cancellations, and Claims.
14. [`14_legacy_financial_rules_baseline.md`](./14_legacy_financial_rules_baseline.md) — Consolidated mathematical formulas, rounding rules, and Financial Year derivation logic.
15. [`15_legacy_atomicity_idempotency_concurrency.md`](./15_legacy_atomicity_idempotency_concurrency.md) — Zero-transaction multi-step mutation analysis, idempotency gaps, and `static` page field concurrency bugs.
16. [`16_legacy_error_validation_baseline.md`](./16_legacy_error_validation_baseline.md) — DAL exception patterns, `ExceptionLogging.cs`, `API_Success<T>` envelopes, and field validations.
17. [`17_legacy_document_file_baseline.md`](./17_legacy_document_file_baseline.md) — Upload folders, naming patterns, `DownloadAll.ashx` ZIP streaming, `ImageHandler.ashx`, and `PolicyParserWebhook.aspx`.
18. [`18_legacy_known_defects.md`](./18_legacy_known_defects.md) — Master register of 11 confirmed legacy bugs (`DEF-001` through `DEF-011`) with exact file/line citations.
19. [`19_legacy_business_rule_master_register.md`](./19_legacy_business_rule_master_register.md) — Master numbered register of 140 business rules (`LBR-001` through `LBR-140`).
20. [`20_legacy_phase_5_to_10_baseline.md`](./20_legacy_phase_5_to_10_baseline.md) — Consolidated Phase 5 → Phase 10 parity specification for auditing `Reliable-Insurance-Backend`.
21. [`21_legacy_baseline_final_report.md`](./21_legacy_baseline_final_report.md) — Final synthesis, Unknowns Register, and Phase 0–10 Migration Parity Checklist.

---

## 3. Register of Unknowns (`UNKNOWN — EVIDENCE NOT AVAILABLE`)

In strict adherence to the **No Guessing** rule, the following items are not present in the local source repository and are explicitly marked `UNKNOWN — EVIDENCE NOT AVAILABLE`:

1. **Internal SQL Bodies of the 943 MySQL Stored Procedures**:
   - No `.sql` dump file exists in the workspace. While all 943 SP names, C# callers, parameter names/types, and consumed output columns are 100% confirmed from `DAL_Operations.cs` and `Service.asmx.cs`, any internal SQL `JOIN` filters, triggers, or internal `START TRANSACTION` blocks inside the MySQL server are `UNKNOWN — EVIDENCE NOT AVAILABLE`.
2. **Exact MySQL Table DDL Constraints (Foreign Keys, Unique Indexes, Column Lengths, Triggers)**:
   - Outside the 36 tables directly queried in the 124 raw SQL strings and the columns bound in C# `DataTable` readers, database-level constraints (`UNIQUE`, `FOREIGN KEY`, `ON DELETE CASCADE`, `AUTO_INCREMENT` seeds) are `UNKNOWN — EVIDENCE NOT AVAILABLE`.
3. **Database-Stored Master Tariff & Commission Slab Values**:
   - The mathematical formulas consuming `ODRate`, `BasicTP`, `ComPer`, `AgtPer`, `FRPer`, and `TDSPer` are 100% confirmed in C#, but the live row values inside `tblcommissionmaster`, `tbltdsmaster`, and insurer tariff tables reside in the production MySQL database (`UNKNOWN — EVIDENCE NOT AVAILABLE`).

---

## 4. Critical Parity Decisions for Auditing `Reliable-Insurance-Backend`

When comparing `Reliable-Insurance-Backend` (FastAPI) against this baseline, auditors must verify:
1. **Intentional Bug Fixes vs Legacy Parity**:
   - Does FastAPI fix **DEF-001** (Franchise Commission checking `FRCalOn` instead of `AgtCalOn` during NCB recovery)?
   - Does FastAPI fix **DEF-002** (March Financial Year boundary `Month <= 3` vs `currentMonth >= 3`)?
   - Does FastAPI fix **DEF-003** (`Int16` overflow on `EndorsementId > 32767`)?
   - Does FastAPI fix **DEF-004** & **DEF-005** (GCV `ZeroDepPremium` omission and `PAPaidDriver = 0` in self-quotation)?
   - Does FastAPI fix **DEF-009** (E-Wallet `>` integer check rejecting exact-balance or decimal payments)?
   - Does FastAPI wrap multi-step policy booking, voucher posting, endorsement approval, NCB recovery, and policy cancellation in **atomic database transactions** (**DEF-011**)?
2. **Domain Completeness Across Phases 5–10**:
   - Verify all 22 Endorsement types (`EndorsementId` 1–22), 4 Commission tiers (`Company`, `Agent`, `Franchise`, `Sub-Agent`), 6-leg policy booking ledger postings, GCV split GST ($12\%$ Basic TP / $18\%$ OD & others), NCB Recovery recalculation, and Policy Cancellation clawbacks.
