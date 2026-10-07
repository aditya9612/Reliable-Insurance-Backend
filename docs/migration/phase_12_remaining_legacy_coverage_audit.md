# PHASE 12 — REMAINING LEGACY COVERAGE AUDIT

| Metadata | Value |
| :--- | :--- |
| **Audit Scope** | Complete Post-Phase 11 Legacy Coverage & Remaining Migration Gap Inventory (`Phase 0` → `Phase 11`) |
| **Repository** | `Reliable-Insurance-Backend` |
| **Branch / Checkpoint** | `tejas-feature` @ `e9d041815f127cd0551968f78898ae29d5a23c3f` (`feat(phase-11): implement document storage, DownloadAll ZIP, ImageHandler, policy parser webhook, and DEF-010 fix`) |
| **Database Target** | `localhost:3306/reliable_insurance_dev` (Alembic head: `b11d0c5f1101`, 47 SQLAlchemy tables) |
| **Regression Baseline** | `309 passed` (`pytest`) |
| **Production Isolation** | Verified — Zero production DB (`brahmainsurance`), storage, or webhook access |
| **Audit Mode** | **READ-ONLY PLANNING & COVERAGE AUDIT — ZERO APPLICATION CODE MODIFIED** |
| **Final Audit Verdict** | **GREEN — MIGRATION COVERAGE MAPPED** |

---

## 1. Executive Summary

Following the completion and verification of **Phases 0 through 11** (`e9d0418`, `309 passed`), the core transactional, financial, underwriting, policy lifecycle, payment/wallet, 4-tier commission/TDS/Cut-&-Pay, accounting ledger, claims/endorsement, RBAC/branch-scoping, and document/file/webhook engines of the legacy **InsurancefinalNew** (`.NET Framework 4.0` / `ASP.NET WebForms` / `ASMX` / `ADO.NET` / `MySQL`) backend have been migrated to the new **FastAPI + Async SQLAlchemy 2.0 + Pydantic v2 + Alembic** backend.

This audit provides an exhaustive, evidence-driven accounting of **what has been migrated in Phases 0–11** versus **what remains unmigrated, partially migrated, deferred, or `UNKNOWN`** across all 14 legacy functional and technical dimensions:
1. Legacy API / `[WebMethod]` / Handler / Page Entry Points (`416` `[WebMethod]`s + `2` `.ashx` handlers + `1` webhook + `213` core `.aspx` flows)
2. Legacy Stored Procedures (`1,855` unique SP call tokens in `04_legacy_stored_procedure_map.md` / `943` canonical SP families in `21_legacy_baseline_final_report.md`)
3. Database Schema & `AllMaster.cs` Entities (`188` `API_*` classes + `36` raw-SQL tables vs `47` physical SQLAlchemy models)
4. Legacy Business Rules (`LBR-001` through `LBR-140` — `110 PARITY`, `14 INTENTIONAL HARDENING`, `13 LEGACY DEFECT MITIGATED`, `0 DEVIATION`, `0 MISSING` on core register, `3 UNKNOWN`)
5. Financial, Commission, TDS, Cut & Pay, Wallet & Accounting Workflows
6. RBAC, Branch Isolation, Ownership & Security Enforcement (`56` legacy roles, `DEF-001` through `DEF-011` all mitigated)
7. External Third-Party Integrations (`HiCaliber` inbound webhook completed in Phase 11; `Signzy` Vehicle RC, `SMS` gateways, `OneSignal` push notifications, `SMTP` email, and outbound `HiCaliber` push remaining)
8. Background / Scheduled / Operational Batch Flows (`Celery` / `Celery Beat` renewal reminders, birthday push notifications, overdue cheque locking, stale lock cleanup)
9. Reporting, RDLC Prints, Excel Exports (`ClosedXML`), POSP Invoices & Graphical Dashboards
10. Master Data Dropdowns, Autocomplete Search (`SearchMethods.aspx.cs` / `AppSearchMethod.aspx.cs`) & Redis Caching (`Phase 4C` pending exposure)
11. In-App Communication (Chatboard, Circulars, Help Tickets, Internal Messages)
12. HR / Payroll / Attendance / Employee Target Subsystem (`21` `API_HR*` classes — non-core ERP module)

### Quantitative Coverage Summary (Section 26)

| Metric | Verified Count / Status | Evidence Source |
| :--- | :--- | :--- |
| **Total Legacy Programmatic Entry Points** | **419** (`416` `[WebMethod]`s + `2` `.ashx` handlers + `1` `.aspx` webhook; plus `213` core `.aspx` WebForms code-behind workflows out of `1,240` `.aspx` files) | [`02_legacy_api_inventory.md`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/docs/migration/02_legacy_api_inventory.md), [`21_legacy_baseline_final_report.md`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/docs/migration/21_legacy_baseline_final_report.md) |
| **Migrated Entry Points (Domain Equivalent in `/api/v1/*`)** | **215** (`212` `[WebMethod]` domain behaviors + `2` `.ashx` handlers + `1` Calliber webhook mapped across **119 FastAPI REST endpoints** / **124 total routes**) | `app/api/v1/router.py`, [`phase_10_api_parity_matrix.md`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/docs/migration/phase_10_api_parity_matrix.md), [`phase_11_document_file_engine_report.md`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/docs/migration/phase_11_document_file_engine_report.md) |
| **Partially Migrated Entry Points** | **74** (Master data dropdown & autocomplete `[WebMethod]`s where Phase 4B models/repositories or core search services exist, but dedicated `/api/v1/masters/*` & `/api/v1/search/*` endpoints are not yet exposed) | [`migration_status.md`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/docs/migration/migration_status.md), [`phase_4b_master_models.md`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/docs/migration/phase_4b_master_models.md), `app/repositories/master.py` |
| **Deferred Entry Points** | **114** (Graphical dashboards/charts `48`, in-app chatboard/circulars/messages/help `24`, mobile attendance/targets/cashback/MIS `22`, renewal push/follow-up `18`, external Signzy RC lookup `2`) | [`02_legacy_api_inventory.md`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/docs/migration/02_legacy_api_inventory.md), [`phase_10_api_parity_matrix.md`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/docs/migration/phase_10_api_parity_matrix.md) |
| **Unknown / Empty Legacy Stubs** | **16** (Commented/malformed `[WebMethod]` attribute stubs in `Service.asmx.cs` recorded as `unknown` in `02_legacy_api_inventory.md`) | [`02_legacy_api_inventory.md`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/docs/migration/02_legacy_api_inventory.md) |
| **Total Legacy Stored Procedures** | **1,855** unique SP call tokens in `04_legacy_stored_procedure_map.md` (**943** deduplicated canonical SP names across **2,338** call sites in `21_legacy_baseline_final_report.md`) | [`04_legacy_stored_procedure_map.md`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/docs/migration/04_legacy_stored_procedure_map.md), [`21_legacy_baseline_final_report.md`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/docs/migration/21_legacy_baseline_final_report.md) |
| **Migrated / Replaced Stored Procedures** | **885** SP call tokens (Core Auth, Customer, Vehicle, Rating, Quotation, Policy Booking, Payments, Cheques, Wallet, Commissions, TDS, Cut & Pay, Accounting, Claims, Endorsements, Documents) | [`phase_10_api_parity_matrix.md`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/docs/migration/phase_10_api_parity_matrix.md), [`phase_11_document_file_engine_report.md`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/docs/migration/phase_11_document_file_engine_report.md) |
| **Partially Migrated Stored Procedures** | **188** SP call tokens (Master table CRUD/lookup SPs where SQLAlchemy models & read repositories exist in Phase 4B, awaiting Phase 4C REST exposure) | [`04_legacy_stored_procedure_map.md`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/docs/migration/04_legacy_stored_procedure_map.md), `app/models/master.py` |
| **Deferred Stored Procedures** | **692** SP call tokens (RDLC reports, MIS exports, graphical dashboards, HR/payroll/attendance, chatboard/circulars, telecaller targets, renewal follow-up, Signzy RC cache) | [`04_legacy_stored_procedure_map.md`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/docs/migration/04_legacy_stored_procedure_map.md) |
| **Unknown Stored Procedures** | **90** missing SP definitions from Phase 0 baseline (`09_missing_stored_procedures.md`) + internal SQL bodies of SPs not directly introspected (`GAP-UNK-001`) | [`phase_0_missing_sp_resolution.md`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/docs/migration/phase_0_missing_sp_resolution.md), [`20_legacy_unknowns_and_evidence_gaps.md`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/docs/migration/20_legacy_unknowns_and_evidence_gaps.md) |
| **Total Legacy Tables / Entities** | **188** `API_*` entity/DTO classes in `AllMaster.cs` + **36** raw-SQL physical `tbl_*` tables (exact total physical table count in production MySQL is `COUNT NOT RELIABLY DETERMINABLE FROM AVAILABLE LOCAL EVIDENCE` without live `SHOW TABLES`, estimated ~140–160 physical tables) | [`03_legacy_database_inventory.md`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/docs/migration/03_legacy_database_inventory.md), [`phase_10_database_parity_matrix.md`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/docs/migration/phase_10_database_parity_matrix.md) |
| **Migrated Tables (SQLAlchemy `Base.metadata`)** | **47** physical tables (45 legacy `tbl_*` tables + 2 Phase 11 tables `tbl_documents` and `tbl_calliber_policy_webhook`) | `app/models/__init__.py`, Alembic head `b11d0c5f1101` |
| **Deferred Tables / Entity Classes** | **92** `API_*` classes / tables (Master hierarchy `tbl_branch`/`tbl_employee`/`tbl_agent`/`tbl_franchise`/`tbl_bank`/`tbl_state`/`tbl_district`, Signzy cache `tbl_vehiclenorc_details`, Renewal/Targets/MIS, Chatboard/Circulars, and `21` HR/Payroll tables) + **49** report/view-only `API_*` DTOs | [`03_legacy_database_inventory.md`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/docs/migration/03_legacy_database_inventory.md), [`phase_10_database_parity_matrix.md`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/docs/migration/phase_10_database_parity_matrix.md) |
| **Total Legacy Business Rules (`LBR-001`..`LBR-140`)** | **140** cataloged rules | [`19_legacy_business_rule_master_register.md`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/docs/migration/19_legacy_business_rule_master_register.md) |
| **Implemented / Remediated Business Rules** | **137** (`110 PARITY` + `14 INTENTIONAL HARDENING` + `13 LEGACY DEFECT MITIGATED`; `0 DEVIATION`, `0 MISSING` on core register) | [`phase_10_post_remediation_parity.md`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/docs/migration/phase_10_post_remediation_parity.md), [`phase_11_document_file_engine_report.md`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/docs/migration/phase_11_document_file_engine_report.md) |
| **Deferred / Unknown Business Rules** | **3 UNKNOWN** on `LBR-001`..`LBR-140` (`GAP-UNK-001`, `GAP-UNK-002`, `GAP-UNK-003`) + **3 Phase 11 UNKNOWNs** (`GAP-UNK-11-001`, `GAP-UNK-11-002`, `GAP-UNK-11-003`) + **6 Deferred Auxiliary Domain Rule Families** (Signzy RC, SMS OTP, OneSignal Push, Telecaller Targets, Health Member Grid, Overdue Cheque Lock) | [`phase_10_post_remediation_parity.md`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/docs/migration/phase_10_post_remediation_parity.md), [`phase_11_document_file_engine_report.md`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/docs/migration/phase_11_document_file_engine_report.md) |
| **Known Legacy Defects (`DEF-001`..`DEF-011`)** | **11 / 11 FIXED & MITIGATED** (`0` open defects remaining) | [`18_legacy_known_defects.md`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/docs/migration/18_legacy_known_defects.md), [`phase_11_document_file_engine_report.md`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/docs/migration/phase_11_document_file_engine_report.md) |

---

## 2. Phase 0–11 Completed Coverage Summary

The table below summarizes the verified scope completed across Phases 0 through 11:

| Phase | Domain / Milestone | Key Deliverables in `Reliable-Insurance-Backend` | Tables Added | Endpoints / Services | Status |
| :--- | :--- | :--- | :---: | :--- | :---: |
| **Phase 0** | Legacy Forensics & Missing SP Resolution | Extracted 29 legacy audit documents + 21 baseline documents; cataloged 90 missing SPs and 22 critical missing SPs | 0 | Read-only baseline (`docs/migration/`) | **COMPLETE** |
| **Phase 1** | Core FastAPI Skeleton & Observability | Async SQLAlchemy 2.0, Pydantic v2 settings with production DB guard (`_enforce_dev_db_isolation`), structured logging, request ID middleware, `/api/v1/health`, `/api/v1/ready` | 0 | `2` health/readiness routes | **COMPLETE** |
| **Phase 2** | Core Domain Models & Alembic Baseline | Initial SQLAlchemy models & Alembic revision `ec6cb5f7e9f1` for core customer, vehicle, policy, payment, commission, and accounting tables | 10 | Core repository abstractions (`BaseRepository`) | **COMPLETE** |
| **Phase 3** | Authentication, JWT & Legacy 56-Role RBAC | `/api/v1/auth/login`, `/refresh`, `/me`, `/users`; bcrypt + legacy plaintext fallback migration (`DEF-005`), role/branch/principal dependency guards (`app/core/rbac.py`) | 2 | `6` auth/user endpoints (`AuthService`) | **COMPLETE** |
| **Phase 4A–4B** | Master Data Schema & Read-Only Repositories | Vehicle Type, Sub-Type, Make, Model, Variant (`91` regional pricing columns), RTO, and Insurance Company models (`d4b8e9a12c34`) and repositories (`app/repositories/master.py`) | 7 | `7` read-only master repositories *(Phase 4C API routes deferred)* | **COMPLETE (4A/4B)** |
| **Phase 5** | Customer, Vehicle & Full 56-Role Access Matrix | Customer & Vehicle CRUD, duplicate detection, search, policy history, soft-delete, and branch/principal isolation across all 56 legacy roles (`5f`/`5g`) | 0 (uses Phase 2 tables) | `12` customer & vehicle endpoints (`CustomerService`, `VehicleService`) | **COMPLETE** |
| **Phase 6** | Underwriting, Rating Engine & Quotations | Complete motor rating engine (Two-Wheeler, Private Car, PCV, GCV, Bus, 3W, Misc-D), slab lookup, OD discount hierarchy (`GAP-P6-001`), NCB ladder, add-ons, GST (`18%`/`12%` GCV TP), quotation workflow & PDF generator | 23 | `17` quotation & rating endpoints (`RatingEngineService`, `QuotationService`) | **COMPLETE** |
| **Phase 7** | Policy Booking, Proposals, Inward & Renewals | Full policy booking state machine (`Pending` → `Verified` → `Approved` / `Rejected`), `PolicyLockStatus`, app proposal workflow (`tbl_transactionappnew`), duplicate guard (`GAP-P7-001`), inspection check (`GAP-P7-002`), renewal chain | 0 (uses Phase 2 tables + `a1b2c3d4e5f6`) | `14` policy & proposal endpoints (`PolicyService`) | **COMPLETE** |
| **Phase 8** | Payments, Cheques, Reconciliation & E-Wallet | Multi-mode payment collection, cheque lifecycle (`Pending` → `Deposited` → `Cleared` / `Bounced` with `₹500` penalty & reversal), insurer reconciliation, E-Wallet credit/debit/lock/release, InstaPay (`1.03%` surcharge `GAP-P8-001`) | 0 (uses Phase 2 tables) | `19` payment, reconciliation & wallet endpoints (`PaymentService`, `WalletService`) | **COMPLETE** |
| **Phase 9** | Commissions, TDS, Cut & Pay & Accounting | 4-tier commission calculation (Insurer Receivable, Agent, Franchise, Referral), `5%` TDS deduction (`LBR-083`), Cut & Pay settlement, batch payouts, double-entry vouchers, ledger postings, trial balance | 0 (uses Phase 2 tables) | `16` commission, payout & accounting endpoints (`CommissionService`, `AccountingService`) | **COMPLETE** |
| **Phase 10** | Claims, Endorsements, Refunds & Parity Remediation | Claim intimation, surveyor assignment, stage progression, settlement; Endorsements (NIL/Financial/Cancellation), NCB recovery, pro-rata refund, commission clawback (`GAP-P10-001`); full Phase 0–10 parity remediation (`f910c3a4d5e6`) | 3 | `22` claims, endorsements & refund endpoints (`ClaimService`, `EndorsementService`) | **COMPLETE** |
| **Phase 11** | Document / File Engine, Storage, ZIP, Handlers & Webhook | Pluggable `StorageBackend` (`LocalFilesystemStorageBackend` / `MockMemoryStorageBackend`), canonical `StorageKey` fixing `DEF-010`, streaming `DownloadAll` ZIP, `ImageHandler` preview, `Calliber` policy parser webhook with HMAC hardening (`b11d0c5f1101`) | 2 | `11` document, legacy handler & webhook endpoints (`DocumentService`) | **COMPLETE** |
| **TOTAL** | **Phases 0–11 Combined** | **12 Model Modules, 15 API Routers, 9 Core Services, 6 Alembic Revisions (`309` automated tests)** | **47 Tables** | **119 API Endpoints (124 Total Routes)** | **VERIFIED (`e9d0418`)** |

---

## 3. Legacy API / WebMethod / Handler / Page Coverage

### 3.1 Inventory of All Legacy Entry Point Surfaces

Per [`01_legacy_project_inventory.md`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/docs/migration/01_legacy_project_inventory.md) and [`02_legacy_api_inventory.md`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/docs/migration/02_legacy_api_inventory.md), the legacy `InsurancefinalNew` codebase exposes **5 distinct programmatic/UI entry surfaces**:

| Legacy Surface | Total Count in Legacy | Migrated (REST Equivalent in `/api/v1/*`) | Partially Migrated (DB/Repo Only or Partial Scope) | Deferred (Unmigrated Auxiliary/UI/Report Flows) | Unknown / Blank Stubs |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **`Service.asmx.cs` (`[WebMethod]`s)** | **339** | **196** | **48** | **79** | **16** |
| **`Clerk/SearchMethods.aspx.cs` (`[WebMethod]`s)** | **41** | **8** | **18** | **15** | **0** |
| **`AppSearchMethod.aspx.cs` (`[WebMethod]`s)** | **16** | **6** | **8** | **2** | **0** |
| **`VehicleService.asmx.cs` (`[WebMethod]`s)** | **2** | **0** | **0** | **2** (`GetVehicleDetails` Signzy RC, `HelloWorld`) | **0** |
| **Inline Page `[WebMethod]`s (`10` `.aspx.cs` files)** | **18** | **2** | **0** | **16** | **0** |
| **HTTP Handlers (`.ashx`)** | **2** | **2** (`DownloadAll.ashx`, `ImageHandler.ashx`) | **0** | **0** | **0** |
| **Dedicated Webhook Pages (`.aspx`)** | **1** | **1** (`PolicyParserWebhook.aspx`) | **0** | **0** | **0** |
| **Subtotal — Programmatic Entry Points** | **419** | **215 (51.3%)** | **74 (17.7%)** | **114 (27.2%)** | **16 (3.8%)** |
| **Core WebForms Code-Behind Pages (`.aspx.cs` business flows)** | **213** *(of `1,240` total `.aspx` files across 5 role folders)* | **138** (Core Auth, Customer, Vehicle, Quote, Policy, Payment, Cheque, Wallet, Commission, Accounting, Claim, Endorsement, Document flows) | **19** (Master table maintenance screens with Phase 4B models only) | **56** (RDLC report viewers, graphical dashboards, bulk Excel MIS import, HR/Payroll, Chatboard, Circulars, SMS/Push triggers) | **0** |

### 3.2 Detailed Breakdown of Remaining `[WebMethod]` & Page Entry Points

#### A. Partially Migrated Entry Points (`74` `[WebMethod]`s — Candidate A: Phase 4C Master & Search APIs)
In `Phase 4B` (`d4b8e9a12c34`), the 7 core master tables (`tbl_vehicle_type`, `tbl_vehicle_sub_type`, `tbl_vehicle_make`, `tbl_vehicle_model`, `tbl_vehicle_variants`, `tbl_rto`, `tbl_insurancecompany`) and their read-only repositories (`app/repositories/master.py`) were created, and [`migration_status.md`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/docs/migration/migration_status.md#L121-L133) explicitly scheduled **Phase 4C (Master Read-Only APIs + Redis Cache)** as the next step. However, Phase 5 began before Phase 4C endpoints were mounted. Consequently, the following **74** legacy lookup/autocomplete `[WebMethod]`s have underlying models/repositories or partial service support, but lack dedicated `/api/v1/masters/*` and `/api/v1/search/*` REST endpoints:
- **Vehicle & Underwriting Dropdowns in `Service.asmx.cs` (`32` WebMethods)**:
  - `SelectVehicleType`, `SelectVehicleTypeForQuotation`, `SelectVehicleSubType`, `SelectVehicleMake`, `SelectVehicleModel`, `SelectVehicleVariant`, `SelectVehicleVariantPrice`, `SelectRTO`, `SelectRTOByCode`, `SelectInsuranceCompany`, `SelectInsuranceCompanyByVehicleType`, `SelectFuelType`, `SelectNCBSlab`, `SelectAddonList`, `SelectPAOwnerDriverRate`, `SelectTowingRate`, etc.
- **Hierarchy & Reference Dropdowns in `Service.asmx.cs` (`16` WebMethods)**:
  - `SelectBranch`, `SelectState`, `SelectDistrict`, `SelectBank`, `SelectBankForCheque`, `SelectFranchiseByBranch`, `SelectAgentByBranch`, `SelectEmployeeByBranch`, `SelectTelecallerByBranch`, `SelectSurveyorList`, etc.
- **AJAX Autocomplete WebMethods in `Clerk/SearchMethods.aspx.cs` (`18` WebMethods) & `AppSearchMethod.aspx.cs` (`8` WebMethods)**:
  - `GetCustomerName`, `GetMobileNo`, `GetRegistrationNo`, `GetPolicyNo`, `GetChassisNo`, `GetEngineNo`, `GetMake`, `GetModel`, `GetVariant`, `GetRTO`, `GetAgentName`, `GetFranchiseName`, `GetBankName`, `GetInsuranceCompany`, `GetSubAgent`, `GetEmployee`, `GetReferenceName`, `GetDealerName`. *(Note: `/api/v1/customers` and `/api/v1/vehicles` support query filtering, but lightweight prefix-autocomplete endpoints for UI dropdowns and mobile app typeahead are not yet mounted).*

#### B. Deferred Entry Points (`114` `[WebMethod]`s + `56` `.aspx.cs` Pages)
1. **Graphical Dashboards, Charts & KPI Counters (`48` WebMethods + `8` `.aspx.cs` pages — `DEFERRED`)**:
   - `Clerk/SearchMethods.aspx.cs`: `GetDashboardCount`, `GetMonthlyBusinessChart`, `GetInsurerWiseChart`, `GetBranchWiseChart`, `GetProductWiseChart`, `GetTopAgentChart`, `GetPendingInwardCount`, `GetPendingChequeCount`, `GetPendingClaimCount`, `GetRenewalDueCount`, etc. (`15` WebMethods)
   - `AppSearchMethod.aspx.cs`: `GetAppDashboardSummary`, `GetPosBusinessSummary` (`2` WebMethods)
   - `Clerk/GraphicalDashBoard.aspx.cs` (`3`), `Franchise/GraphicalDashBoard.aspx.cs` (`2`), `Subadmin/GraphicalDashBoard.aspx.cs` (`3`), `Service.asmx.cs` (`AppDashBoard*` — `23` WebMethods).
2. **In-App Chatboard, Circulars, Internal Messages & Help Desk (`24` WebMethods + `9` `.aspx.cs` pages — `DEFERRED`)**:
   - `Service.asmx.cs`: `InsertAppChatboard`, `SelectAppChatboard`, `InsertCircular`, `SelectCircularSubject`, `SelectCircularDetail`, `InsertMessage`, `SelectMessageInbox`, `SelectMessageSent`, `InsertHelpforApp`, `SelectHelpforApp`, `UpdateHelpStatus`, etc.
3. **Mobile App Attendance, Employee Targets, Cashback / Reward Points & MIS Entry (`22` WebMethods + `11` `.aspx.cs` pages — `DEFERRED`)**:
   - `Service.asmx.cs` & `Clerk/LocationDetails.aspx.cs`: `InsertAppAttendance`, `SelectAppAttendance`, `GetEmployeeLocation`, `AppTargetDashBoard`, `SelectEmployeeTarget`, `InsertIDVRequest`, `SelectIDVRequest`, `SelectRewardPoint`, `RedeemRewardPoint`, `InsertAppMISEntry`, `Clerk/MISReport.aspx.cs`.
4. **Renewal Expiry Follow-Up & Push Notification Entry Points (`18` WebMethods + `6` `.aspx.cs` pages — `DEFERRED`)**:
   - `Service.asmx.cs` & `Clerk/SendPushNotiRenewal.aspx.cs`: `SelectPreYaerRenewalExpiryPolicy`, `InsertPreYearRenewalStatus`, `SelectRenewalFollowupHistory`, `InsertPushNotiRenewal`, `SendPushNotiForBdayWish`, `PolicyNoUpdatePushNoti`.
5. **External Signzy Vehicle RC Verification (`2` WebMethods + `1` `.aspx.cs` page — `DEFERRED`)**:
   - `VehicleService.asmx.cs::GetVehicleDetails`, `Service.asmx.cs::GetVehicleDetails`, `Clerk/RC_CheckVehicleDtl.aspx.cs`.
6. **RDLC Report Viewer & Bulk Excel Import Pages (`21` `.aspx.cs` pages + `1` `[WebMethod]` in `rpt_POSP_Invoice.aspx.cs` — `DEFERRED`)**:
   - `Clerk/rpt_*.aspx.cs` (`49` `.rdlc` report templates rendered via `Microsoft.ReportViewer.WebForms`), `Clerk/adm_ImportTransAgentPolicyMIS.aspx.cs` (bulk Excel policy MIS upload via `ClosedXML`).

---

## 4. Stored Procedure Coverage

### 4.1 Quantitative Reconciliation of Legacy Stored Procedures

Per [`04_legacy_stored_procedure_map.md`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/docs/migration/04_legacy_stored_procedure_map.md) and [`21_legacy_baseline_final_report.md`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/docs/migration/21_legacy_baseline_final_report.md):
- **Total Raw SP Name Tokens Extracted (`04_legacy_stored_procedure_map.md`)**: **1,855** (includes case variations and wrapper names across `DAL_Operations.cs` and `AllMaster.cs` across **2,338** call sites).
- **Canonical Deduplicated SP Names (`21_legacy_baseline_final_report.md`)**: **943** unique stored procedures.
- **Missing SP Definitions in Legacy Dump (`09_missing_stored_procedures.md` / `phase_0_missing_sp_resolution.md`)**: **90** stored procedures called in C# code whose `CREATE PROCEDURE` SQL bodies were absent from the legacy SQL dump (22 critical transactional SPs were reconstructed from C# `MySqlParameter` bindings in Phase 0; 68 low-priority report/archive/HR SPs remain `UNKNOWN`).

### 4.2 Stored Procedure Coverage by Functional Domain

| Legacy Domain (`04_legacy_stored_procedure_map.md`) | Total SP Tokens | Migrated / Replaced in FastAPI Services | Partially Migrated (Phase 4B Models Only) | Deferred (Reports, Dashboards, HR, Chat, Aux) | Unknown (Missing SQL Body & Unreconstructable) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Phase 5: Customer, Vehicle & RTO Masters** | 155 | 78 (`CustomerService`, `VehicleService`) | 62 (`app/repositories/master.py` read repos; CRUD/Signzy cache pending) | 12 (Signzy `USP_Insert_VehicleNoRC_Details`, bulk vehicle merge) | 3 |
| **Phase 5: RBAC, Users, Employees & Branches** | 191 | 64 (`AuthService`, `app/core/rbac.py` 56-role guards) | 46 (`tbl_branch`, `tbl_employee` ID scoping implemented; full CRUD deferred) | 73 (Login history `USP_Insert_LoginHistory`, Employee HR/targets) | 8 |
| **Phase 6: Quotation, Rating, Slabs & Underwriting** | 87 | 83 (`RatingEngineService`, `QuotationService`, 23 tables) | 0 | 4 (Special IDV approval override queue `USP_Insert_IDVRequest`) | 0 |
| **Phase 7: Policy Booking, Inward, Renewal & App Tx** | 213 | 164 (`PolicyService`, proposals, inward locking, verification) | 0 | 43 (Renewal telecaller follow-up `USP_Select_PreYearRenewal*`, Health family grid) | 6 |
| **Phase 8: Payments, Cashier, Cheques & E-Wallet** | 142 | 131 (`PaymentService`, `WalletService`, reconciliation, InstaPay) | 0 | 9 (Overdue cheque user-login lock `USP_Lock_UserByPendingCheque`) | 2 |
| **Phase 9: Commission, TDS, Franchise & Accounting** | 320 | 242 (`CommissionService`, `AccountingService`, Cut & Pay, TDS, vouchers) | 0 | 64 (Bulk Excel MIS import `USP_Import_AgentPolicyMIS`, RDLC statements, GST/TDS statutory exports) | 14 |
| **Phase 10: Claims & Survey Management** | 33 | 31 (`ClaimService`, `DocumentService`) | 0 | 2 (Claim register Excel/RDLC summary SPs) | 0 |
| **Phase 10: Endorsements, NCB Recovery & Cancellation** | 51 | 48 (`EndorsementService`, `DocumentService`) | 0 | 3 (Endorsement MIS register report SPs) | 0 |
| **General / Master / Documents / Reports / HR / Chat** | 663 | 44 (Phase 11 `DocumentService`, Calliber webhook, quotation files) | 80 (State/District/Bank/Fuel/Financier lookup SPs) | 482 (RDLC reports `~210`, Dashboards `~85`, HR/Payroll/Attendance `~112`, Chatboard/Circulars/Help `~75`) | 57 |
| **TOTAL** | **1,855** | **885 (47.7%)** | **188 (10.1%)** | **692 (37.3%)** | **90 (4.9%)** |

---

## 5. Database Table / Schema Coverage

### 5.1 Currently Modeled Physical Tables (`47` SQLAlchemy Models in `Base.metadata`)

All **47** tables below are managed by Alembic (`head = b11d0c5f1101`) and verified in `reliable_insurance_dev`:
- **Customer & Vehicle (`2` tables)**: `tbl_customer`, `tbl_vehicledetails`
- **Users & RBAC (`2` tables)**: `tbl_user`, `tbl_userrole`
- **Vehicle, RTO & Insurer Masters (`7` tables)**: `tbl_vehicle_type`, `tbl_vehicle_sub_type`, `tbl_vehicle_make`, `tbl_vehicle_model`, `tbl_vehicle_variants` (full 91 columns), `tbl_rto`, `tbl_insurancecompany`
- **Quotation & Rating Engine (`23` tables)**: `tbl_app_quatationentry`, `tbl_app_quotationrequest`, `tbl_insurancecompanyquotation`, `tbl_app_quotationremark`, `tbl_app_requestedquotationfile`, `tbl_quot_damagepremium`, `tbl_quot_liabilitypremium`, `tbl_app_oddiscountnew`, `tbl_app_oddiscountnew_gcv`, `tbl_appoddiscount`, `tbl_insurancecompanybyvehicletype`, `tbl_patoownerdriver`, `tbl_insurancecompanywisetowingchanges`, `tbl_zerodep`, `tbl_zerodepforsegmentwise`, `tbl_zerodepnewaddonrate`, `tbl_addonextraamt`, `tbl_app_twowheelercc_rate`, `tbl_app_pcv_cc_rate`, `tbl_app_bus_cc_rate`, `tbl_app_threewheeler_cc_rate`, `tbl_quotation_prefix`, `tbl_selfdiscount`
- **Policies & Proposals (`2` tables)**: `tbl_transaction`, `tbl_transactionappnew`
- **Payments (`1` table)**: `tbl_transactionpayment`
- **Commissions, Cut & Pay & Accounting (`5` tables)**: `tbl_account`, `tbl_ledgermaster`, `tbl_franchisecommission`, `tbl_agentcommissionpayment`, `tbl_cutnpaycommpayable`
- **Claims & Endorsements (`3` tables)**: `tbl_claims`, `tbl_claimdocument`, `tbl_appendorsement`
- **Unified Documents & Webhook Audit (`2` tables — Phase 11)**: `tbl_documents`, `tbl_calliber_policy_webhook`

### 5.2 Unmodeled / Deferred Legacy Tables & `AllMaster.cs` Entities

Per [`03_legacy_database_inventory.md`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/docs/migration/03_legacy_database_inventory.md) and [`phase_10_database_parity_matrix.md`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/docs/migration/phase_10_database_parity_matrix.md), the remaining unmodeled legacy tables/entities fall into **5 clear categories**:

| Category | Legacy Tables / `API_*` Classes | Count | Current Status & Rationale |
| :--- | :--- | :---: | :--- |
| **1. Organizational & Reference Master Tables** | `tbl_branch` (`API_Branch`), `tbl_employee` (`API_Employee`), `tbl_agent` (`API_Agent`), `tbl_franchise` (`API_Franchise`), `tbl_bank` (`API_Bank`), `tbl_state` (`API_State`), `tbl_district` (`API_District`), `tbl_fueltype`, `tbl_financier`, `tbl_surveyor`, `tbl_role_privilege` (`API_Privilege`) | **18** tables | **PARTIALLY MIGRATED / DEFERRED (Candidate A)**: Foreign key IDs (`BranchId`, `AgentId`, `FranchiseId`, `TelecallerId`, `StateId`, `DistrictId`, `BankId`) are stored and enforced on `tbl_user`, `tbl_transaction`, `tbl_customer`, and `tbl_account`, and dynamic role privileges are enforced statically in `app/core/rbac.py`, but dedicated SQLAlchemy models for these 18 reference tables are not yet created. |
| **2. External Integration & KYC Cache Tables** | `tbl_vehiclenorc_details` (`API_VehicleNoRC_Details`), `tbl_sms_log`, `tbl_pushnotification_log` | **4** tables | **DEFERRED (Candidate B)**: Used by Signzy Vehicle RC API caching and SMS/OneSignal notification logging. |
| **3. Operational Tracking, Renewal Follow-Up, Targets & Bulk MIS Tables** | `tbl_preyearrenewalstatus` (`API_PreYearRenewalStatus`), `tbl_target` / `tbl_targetnew` (`API_Target`, `API_TargetNew`), `tbl_importagentpolicy` (`API_ImportAgentPolicy`), `tbl_loginhistory` (`API_LoginHistory`), `tbl_idvrequest` (`API_IDVRequest`), `tbl_rewardpoint` (`API_RewardPoint`), `tbl_healthmember` (`API_HealthMember`) | **16** tables | **DEFERRED (Candidates C & D)**: Used for renewal telecaller follow-up tracking, monthly sales targets, bulk Excel policy MIS staging, login audit logs, IDV approval overrides, POSP reward points, and non-motor health family member grids. |
| **4. In-App Communication & Help Desk Tables** | `tbl_appchatboard` (`API_AppChatboard`), `tbl_circular` (`API_Circular`), `tbl_message` (`API_Message`), `tbl_customerhelp` (`API_CustomerHelp`) | **9** tables | **DEFERRED (Low Priority / P3)**: Used for internal POSP/Clerk chatboard, company circulars, internal inbox messages, and app help tickets. |
| **5. HR, Payroll, Leave & Attendance Subsystem** | `API_HROrganization`, `API_HRdeparmentmaster`, `API_HRDesignation`, `API_HREmployee`, `API_HRLeave`, `API_HrAdvance`, `API_HRSalary`, `API_AppAttendance`, `API_EmployeeLocation`, etc. (`AllMaster.cs` L2242–L2703) | **21** classes (`~21` tables) + **24** auxiliary/archive tables | **OUT OF CORE INSURANCE SCOPE / DEFERRED (P3)**: Internal HR/Payroll ERP module embedded inside the legacy monolith; zero coupling to insurance underwriting, policies, payments, commissions, or claims. |
| **6. Non-Table Report / Chart / View DTOs in `AllMaster.cs`** | `API_Dashboard*`, `API_Report*`, `API_AgentPayemtInvoice`, `API_GSTReport`, `API_TDSReport`, etc. | **49** DTO classes | **NOT PHYSICAL TABLES**: Read-only C# projection DTOs populated by reporting stored procedures. |

---

## 6. Business Rule Coverage (`LBR-001` → `LBR-140`)

Per [`19_legacy_business_rule_master_register.md`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/docs/migration/19_legacy_business_rule_master_register.md), [`phase_10_post_remediation_parity.md`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/docs/migration/phase_10_post_remediation_parity.md), and [`phase_11_document_file_engine_report.md`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/docs/migration/phase_11_document_file_engine_report.md), all **140** cataloged business rules (`LBR-001` through `LBR-140`) have been audited and remediated:

| Classification | Count | Rule IDs & Summary |
| :--- | :---: | :--- |
| **PARITY** | **110** | Core Auth/RBAC, Customer/Vehicle, Rating/Slabs/NCB/GST, Quotation lifecycle, Policy booking & inward locking, Payment/Cheque/Bounce/Reconciliation/Wallet, 4-tier Commissions/TDS/Cut-&-Pay/Vouchers/Trial Balance, Claims/Endorsements/Refunds, and Phase 11 Document/ZIP/ImageHandler/Calliber Webhook rules (`LBR-115`..`LBR-122`). |
| **INTENTIONAL HARDENING** | **14** | `LBR-002` (JWT + bcrypt fallback), `LBR-009` (server-side RBAC), `LBR-039` (18% GST default with 12% GCV TP override), `LBR-054` (idempotent booking), `LBR-068` (`SELECT ... FOR UPDATE` wallet locking), `LBR-084` (immutable ledger reversals), `LBR-116` (authenticated document streaming), `LBR-119` (streamed ZIP with traversal defense), `LBR-122` (optional HMAC webhook signature), etc. |
| **LEGACY DEFECT MITIGATED** | **13** | Rules directly associated with `DEF-001` through `DEF-011` (`LBR-001`, `LBR-005`, `LBR-014`, `LBR-047`, `LBR-065`, `LBR-071`, `LBR-078`, `LBR-088`, `LBR-096`, `LBR-117`/`DEF-010`, `LBR-120`, `LBR-121`, `LBR-138`). |
| **DEVIATION** | **0** | All 16 prior deviations identified in the initial Phase 10 audit (`GAP-P5-001`..`GAP-P10-004`) were remediated and verified in `phase_10_post_remediation_parity.md`. |
| **MISSING (on Core Transactional Register)** | **0** | All core transactional gaps were closed in Phase 10 remediation and Phase 11 implementation. *(Note: 6 auxiliary/external rule families referenced in `19_legacy_business_rule_master_register.md` — Signzy RC `LBR-021`/`022`, SMS OTP `LBR-123`..`125`, OneSignal Push `LBR-126`..`128`, Telecaller Targets `LBR-131`, Health Member Grid `LBR-058`, Overdue Cheque Lock `LBR-069` — are tracked as **DEFERRED** in Section 17).* |
| **UNKNOWN** | **3** | `GAP-UNK-001` (internal SQL bodies of unextracted SPs), `GAP-UNK-002` (exact legacy MySQL `DECIMAL`/`FLOAT` column precision on unextracted DDL), `GAP-UNK-003` (legacy implicit behavior when multiple active commission slabs overlap on exact effective dates). |
| **TOTAL** | **140** | **137 Verified (`110` Parity + `14` Hardening + `13` Defect Mitigated) / `3` Unknown / `0` Open Core Deviations** |

---

## 7. Financial / Accounting / Commission / Payment Coverage

| Financial Workflow | Legacy Implementation | New FastAPI Implementation (`app/services/`) | Coverage Status | Remaining / Deferred Items |
| :--- | :--- | :--- | :---: | :--- |
| **Multi-Mode Premium Collection** | `PolicyTransactionNew.aspx.cs`, `PaymentTransaction.aspx.cs` (`Cash`, `Cheque`, `NEFT/RTGS`, `Online`, `Wallet`, `Cut & Pay`) | `PaymentService` (`app/services/payment_service.py`) | **MIGRATED (100%)** | None |
| **Cheque Lifecycle & Bounce Penalty (`₹500`)** | `ChequeStatusUpdate.aspx.cs`, `Adm_BounceCheque.aspx.cs` | `PaymentService.update_cheque_status`, bounce reversal + `₹500` penalty voucher | **MIGRATED (100%)** | Overdue uncleared cheque user-login lock (`Adm_LockChequeEntry.aspx.cs` / `LBR-069`) is **DEFERRED** (background/admin policy rule) |
| **Insurer Payment Reconciliation** | `InsurerPaymentReconciliation.aspx.cs` | `/api/v1/reconciliation/*` (`PaymentService`) | **MIGRATED (100%)** | Bulk Excel insurer reconciliation import is **DEFERRED** |
| **E-Wallet & InstaPay (`1.03%` Surcharge)** | `WalletTopup.aspx.cs`, `InstaPay.aspx.cs` (`GAP-P8-001`) | `WalletService` (`app/services/wallet_service.py`) with row-level locking (`SELECT ... FOR UPDATE`) | **MIGRATED (100%)** | External payment gateway webhook for live online wallet top-up is **DEFERRED / UNKNOWN** (legacy used manual/UTR or external gateway callback) |
| **4-Tier Commission Calculation** | `CommissionCalculation.aspx.cs` (Insurer Receivable, Agent, Franchise, Referral) | `CommissionService` (`app/services/commission_service.py`) | **MIGRATED (100%)** | Bulk Excel policy/commission MIS import (`adm_ImportTransAgentPolicyMIS.aspx.cs`) is **DEFERRED** |
| **TDS Deduction (`5%` under Sec 194D/194H)** | `AgentCommissionPayment.aspx.cs` (`LBR-083`) | `CommissionService` (`5%` standard TDS, PAN/threshold rules) | **MIGRATED (100%)** | Statutory Form 16A / quarterly TDS Excel report export is **DEFERRED** |
| **Cut & Pay Settlement** | `CutAndPaySettlement.aspx.cs` (`tbl_cutnpaycommpayable`) | `CommissionService` + `PaymentService` Cut & Pay net-off | **MIGRATED (100%)** | None |
| **Double-Entry Vouchers, Ledgers & Trial Balance** | `VoucherEntry.aspx.cs`, `LedgerReport.aspx.cs`, `TrialBalance.aspx.cs` | `AccountingService` (`app/services/accounting_service.py`) — Receipt, Payment, Journal, Contra, Trial Balance | **MIGRATED (100%)** | Printable PDF/Excel Account Statement & POSP Commission Invoice (`rpt_POSP_Invoice.aspx.cs`) are **DEFERRED** (Candidate C) |
| **Endorsement Refunds & Commission Clawback** | `EndorsementEntry.aspx.cs` (`GAP-P10-001`) | `EndorsementService` (`app/services/endorsement_service.py`) — proportional clawback & refund lifecycle | **MIGRATED (100%)** | None |

---

## 8. RBAC / Security / Branch / Ownership Coverage

| Security / RBAC Dimension | Legacy Behavior | FastAPI Implementation (`app/core/rbac.py`, `app/services/`) | Coverage Status |
| :--- | :--- | :--- | :---: |
| **56 Legacy User Roles (`tbl_userrole`)** | Hardcoded `RoleId` / `RoleName` checks scattered across 5 folders (`Admin`, `Subadmin`, `Clerk`, `Franchise`, `Agent`, `POSP`, `Telecaller`, `Cashier`, `Accountant`, `Claim`, `Endorsement`, `Customer`, etc.) | Canonical 56-role classifier in `app/core/rbac.py` (`ADMIN_ROLES`, `BRANCH_SCOPED_ROLES`, `FRANCHISE_SCOPED_ROLES`, `AGENT_SCOPED_ROLES`, `CUSTOMER_SCOPED_ROLES`, etc.) | **MIGRATED (100%)** |
| **Branch Isolation (`BranchId`)** | Partial/inconsistent filtering in stored procedures | Enforced at service & repository layer across Customers, Vehicles, Quotations, Policies, Payments, Claims, Endorsements, and Documents | **MIGRATED & HARDENED (100%)** |
| **Principal Ownership (`AgentId`, `FranchiseId`, `TelecallerId`, `CustomerId`)** | Client-side hidden fields (vulnerable to IDOR `DEF-004`) | Server-side principal scoping enforced from JWT `CurrentUser` across all 119 API endpoints | **MIGRATED & HARDENED (100%)** |
| **Authentication & Password Storage** | Plaintext passwords in `tbl_user`, unauthenticated `Service.asmx` (`DEF-001`, `DEF-005`) | OAuth2/JWT Bearer tokens + bcrypt hashing with transparent legacy upgrade | **MIGRATED & HARDENED (100%)** |
| **Dynamic Role-Privilege Matrix UI (`tbl_role_privilege`)** | Admin UI page (`Adm_RolePrivilege.aspx.cs`) toggling menu visibility per role | Static role-permission enforcement in `app/core/rbac.py`; dynamic menu-privilege CRUD API is **DEFERRED** (UI-menu concern) | **PARTIALLY MIGRATED (Core RBAC 100%; UI Menu CRUD Deferred)** |

---

## 9. External Third-Party Integration Coverage

Per [`01_legacy_project_inventory.md`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/docs/migration/01_legacy_project_inventory.md), [`16_legacy_notification_external_integrations.md`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/docs/migration/16_legacy_notification_external_integrations.md), and [`17_legacy_document_file_baseline.md`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/docs/migration/17_legacy_document_file_baseline.md), the legacy system integrates with **5 external third-party platforms**:

| External Integration | Legacy Entry Points & Credentials Risk | Current Status in `Reliable-Insurance-Backend` | Remaining Work (Candidate B) |
| :--- | :--- | :--- | :--- |
| **1. HiCaliber / Calliber Policy PDF Parser (Inbound Webhook)** | `PolicyParserWebhook.aspx.cs` (`USP_Insert_CalliberPolicyWebhookData`) | **MIGRATED IN PHASE 11**: `POST /api/v1/documents/webhooks/policy-parser` with idempotency, optional HMAC (`X-Calliber-Signature`), and local document registration (`tbl_calliber_policy_webhook`). | **Inbound 100% Complete.** Outbound push trigger (sending uploaded PDF to HiCaliber for parsing, if initiated by backend rather than external watcher) is `UNKNOWN` (`GAP-UNK-11-002`) / **DEFERRED**. |
| **2. Signzy Vehicle RC Verification API** | `Clerk/RC_CheckVehicleDtl.aspx.cs`, `VehicleService.asmx.cs::GetVehicleDetails`, `Service.asmx.cs::GetVehicleDetails` (`https://preproduction.signzy.tech/api/v2/patrons/.../vehicle/rc`, cached in `tbl_vehiclenorc_details`) | **DEFERRED (Not Yet Implemented)**: Hardcoded legacy credentials mitigated by exclusion (`DEF-002`), but no `/api/v1/vehicles/rc-lookup` endpoint or `tbl_vehiclenorc_details` cache table exists yet. | Implement pluggable `VehicleRCProvider` interface + `MockSignzyRCProvider` + `tbl_vehiclenorc_details` cache table + `/api/v1/vehicles/rc-lookup` endpoint (**Candidate B**). |
| **3. SMS Gateways (`hspsms.com`, `Fast2SMS`, `IndiaText`)** | `App_Code/Send_SMS.cs`, `Service.asmx.cs` (Mobile OTP login/verification, policy issuance SMS, renewal reminder SMS, cheque bounce SMS) | **DEFERRED (Not Yet Implemented)**: Legacy hardcoded API keys excluded (`DEF-002`), no `SMSProvider` service or OTP verification endpoint exists yet. | Implement pluggable `SMSNotificationProvider` (`MockSMSProvider` in dev/test) + OTP generation/verification flow + transactional SMS hooks (**Candidate B**). |
| **4. OneSignal Push Notifications** | `Clerk/SendPushNotiRenewal.aspx.cs`, `Clerk/PolicyNoUpdatePushNoti.aspx.cs`, `Clerk/SendPushNotiForBdayWish.aspx.cs`, `Service.asmx.cs` (`https://onesignal.com/api/v1/notifications`) | **DEFERRED (Not Yet Implemented)**: Legacy hardcoded OneSignal App ID / REST API Key excluded (`DEF-002`). | Implement pluggable `PushNotificationProvider` (`MockPushProvider` in dev/test) + device token registration (`PlayerId` on `tbl_user`/`tbl_customer`) + push trigger endpoints (**Candidate B**). |
| **5. SMTP Email Dispatch** | `Clerk/SendMailToAutority.aspx.cs`, quotation/policy email sharing (`smtp.gmail.com` / custom SMTP) | **DEFERRED (Not Yet Implemented)** | Implement pluggable `EmailNotificationProvider` (`MockEmailProvider` in dev/test) for authority approval emails, quotation PDFs, and policy attachments (**Candidate B**). |

---

## 10. Background / Scheduled / Operational Flow Coverage

In the legacy ASP.NET WebForms application, scheduled and operational batch tasks were triggered either via manual admin button clicks or external Windows Task Scheduler HTTP hits to `.aspx` pages. While `Celery` and `Redis` are configured in `pyproject.toml` and `app/core/config.py`, **zero Celery tasks or scheduled jobs have been implemented yet**.

| Operational / Batch Flow | Legacy Mechanism | Current Status | Target Architecture (Candidate D) |
| :--- | :--- | :---: | :--- |
| **1. Policy Renewal Expiry Detection & Reminder Queue** | `Clerk/SendPushNotiRenewal.aspx.cs`, `Service.asmx.cs::SelectPreYaerRenewalExpiryPolicy` (queries policies expiring in $T-30, T-15, T-7, T-1$ days) | **DEFERRED** | Celery Beat daily task + `/api/v1/renewals/due` query & follow-up status endpoints (`tbl_preyearrenewalstatus`). |
| **2. Daily Customer Birthday Wish Push / SMS** | `Clerk/SendPushNotiForBdayWish.aspx.cs` | **DEFERRED** | Celery Beat daily task dispatching via `MockPushProvider` / `MockSMSProvider`. |
| **3. Overdue Uncleared Cheque User Lock (`LBR-069`)** | `Clerk/Adm_LockChequeEntry.aspx.cs` (locks agent/POSP login or booking if cheque remains uncleared past grace period) | **DEFERRED** | Celery Beat daily check + configurable policy lock flag on `tbl_user`. |
| **4. Stale E-Wallet Lock & Temporary Upload Cleanup** | Manual DB intervention in legacy | **DEFERRED** | Celery Beat periodic task releasing abandoned wallet locks and cleaning orphaned temporary export files. |
| **5. Async Bulk Excel MIS Import Processing** | Synchronous `ClosedXML` loop in `Clerk/adm_ImportTransAgentPolicyMIS.aspx.cs` (prone to HTTP timeout) | **DEFERRED** | Background task / chunked upload processor (`tbl_importagentpolicy`). |

---

## 11. Reporting / Export / Print / Operational Query Coverage

### 11.1 Legacy Reporting Surface (`49` `.rdlc` Templates & `ClosedXML` Exports)

Per [`01_legacy_project_inventory.md`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/docs/migration/01_legacy_project_inventory.md), the legacy system contains **49 `.rdlc` (Microsoft ReportViewer) templates** and numerous `ClosedXML` Excel export handlers across `Clerk/` and `Subadmin/`:

| Report / Export Category | Legacy Files / Templates | Current Coverage in FastAPI | Gap / Remaining Work (Candidate C) |
| :--- | :--- | :--- | :--- |
| **1. Quotation Comparison PDF** | `QuotationPrint.aspx.cs` / `.rdlc` | **MIGRATED IN PHASE 6 & 11**: `GET /api/v1/quotations/{id}/pdf` and `POST /api/v1/documents/quotations/{id}/generate-pdf` | **100% Complete** |
| **2. POSP / Agent Commission Invoice & Voucher Print** | `Clerk/rpt_POSP_Invoice.aspx.cs`, `rpt_AgentCommission.rdlc`, `rpt_VoucherPrint.rdlc` | **DEFERRED**: JSON data available via `/api/v1/commission-payouts` and `/api/v1/accounting/vouchers`, but printable PDF/HTML invoice & voucher endpoints are not yet implemented. | Implement POSP Commission Tax Invoice PDF/JSON and Voucher Print endpoints (**Candidate C**). |
| **3. Financial & Statutory Reports (Ledger, Trial Balance, TDS, GST, DayBook)** | `rpt_Ledger.rdlc`, `rpt_TrialBalance.rdlc`, `rpt_TDSReport.rdlc`, `rpt_GSTReport.rdlc`, `rpt_DayBook.rdlc` (`~14` `.rdlc` files) | **PARTIALLY MIGRATED**: JSON Ledger (`GET /api/v1/accounting/ledgers/{id}/entries`) and Trial Balance (`GET /api/v1/accounting/trial-balance`) exist; TDS register, GST outward/inward register, DayBook, and CSV/Excel exports are **DEFERRED**. | Add TDS Register, GST Register, DayBook, and streaming CSV/Excel export endpoints (**Candidate C**). |
| **4. Policy, Inward, Cheque & Renewal MIS Reports** | `rpt_PolicyRegister.rdlc`, `rpt_PendingInward.rdlc`, `rpt_ChequeRegister.rdlc`, `rpt_RenewalDue.rdlc`, `Clerk/MISReport.aspx.cs` (`~22` `.rdlc` files) | **PARTIALLY MIGRATED**: Paginated list APIs exist for policies, payments, and claims, but aggregated MIS report endpoints and Excel/CSV downloads are **DEFERRED**. | Add Policy MIS, Cheque Bounce/Pending Register, and Renewal Due export endpoints (**Candidate C**). |
| **5. Graphical Dashboards & Executive KPIs** | `Clerk/GraphicalDashBoard.aspx.cs`, `Subadmin/GraphicalDashBoard.aspx.cs`, `Franchise/GraphicalDashBoard.aspx.cs` (`48` WebMethods) | **DEFERRED**: No `/api/v1/dashboard/*` KPI or chart aggregation endpoints exist yet. | Add role-scoped `/api/v1/dashboard/summary` and chart series endpoints (**Candidate C**). |

---

## 12. Search / Master / Utility API Coverage

As detailed in Section 3.2.A and [`migration_status.md`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/docs/migration/migration_status.md#L121-L133), **Phase 4C (Master Read-Only APIs + Redis Cache)** was designed after Phase 4B (`d4b8e9a12c34`) but has not yet been implemented as FastAPI endpoints:

| Master / Search Capability | Underlying Models & Repositories (`Phase 4B`) | FastAPI Endpoint Status | Remaining Work (Candidate A) |
| :--- | :--- | :--- | :--- |
| **Vehicle Type & Sub-Type Dropdowns** | `VehicleType`, `VehicleSubType` (`app/models/master.py`, `app/repositories/master.py`) | **NOT EXPOSED** (Used internally by `RatingEngineService`, no `/api/v1/masters/vehicle-types` route) | Expose `GET /api/v1/masters/vehicle-types` and `/vehicle-sub-types` with Redis cache. |
| **Vehicle Make, Model & 91-Column Regional Variant Lookup** | `VehicleMake`, `VehicleModel`, `VehicleVariant` (`app/models/master.py`, `app/repositories/master.py`) | **NOT EXPOSED** (No `/api/v1/masters/makes`, `/models`, `/variants`, or regional ex-showroom price lookup endpoint) | Expose cascading Make → Model → Variant & state-wise ex-showroom price lookup APIs. |
| **RTO & Insurance Company Master APIs** | `RTOMaster`, `InsuranceCompany` (`app/models/master.py`, `app/repositories/master.py`) | **NOT EXPOSED** (No `/api/v1/masters/rtos` or `/insurers` route) | Expose `GET /api/v1/masters/rtos` and `/insurers` with search & Redis caching. |
| **Branch, State, District, Bank & Hierarchy Lookups** | Referenced via integer IDs; no dedicated SQLAlchemy models yet | **NOT EXPOSED** | Add read/lookup models & `/api/v1/masters/branches`, `/states`, `/districts`, `/banks` endpoints. |
| **Unified Typeahead / Autocomplete Search (`SearchMethods.aspx.cs` / `AppSearchMethod.aspx.cs`)** | `CustomerService` & `VehicleService` have list filters, but `57` legacy `[WebMethod]` autocomplete endpoints lack direct fast-lookup routes | **PARTIALLY MIGRATED** | Expose `/api/v1/search/autocomplete` (customers, vehicles, policies, chassis, engine, agents, franchises, RTOs, makes/models). |

---

## 13. Notification / Communication Coverage

| Communication Feature | Legacy Implementation | Current Status | Priority / Candidate |
| :--- | :--- | :---: | :--- |
| **Transactional SMS & Mobile OTP** | `App_Code/Send_SMS.cs`, `Service.asmx.cs` | **DEFERRED** | **P1 — Candidate B** (Pluggable provider + local mock) |
| **OneSignal Mobile Push Notifications** | `SendPushNotiRenewal.aspx.cs`, `PolicyNoUpdatePushNoti.aspx.cs`, `SendPushNotiForBdayWish.aspx.cs` | **DEFERRED** | **P1 — Candidate B** (Pluggable provider + local mock) |
| **Authority & Customer SMTP Email** | `SendMailToAutority.aspx.cs` | **DEFERRED** | **P1 — Candidate B** (Pluggable provider + local mock) |
| **In-App Chatboard (`tbl_appchatboard`)** | `Service.asmx.cs` (`InsertAppChatboard`, `SelectAppChatboard`) | **DEFERRED** | **P3 — Later Phase** (Auxiliary internal social/chat feature) |
| **Company Circulars & Internal Inbox (`tbl_circular`, `tbl_message`)** | `Service.asmx.cs` (`SelectCircular*`, `SelectMessage*`) | **DEFERRED** | **P3 — Later Phase** |
| **Mobile App Help Desk Tickets (`tbl_customerhelp`)** | `Service.asmx.cs` (`InsertHelpforApp`, `SelectHelpforApp`) | **DEFERRED** | **P3 — Later Phase** |

---

## 14. Remaining Document / File / Attachment Work

Phase 11 (`e9d0418`) completed the core Document & File Engine (`tbl_documents`, `tbl_calliber_policy_webhook`, `StorageBackend`, `DownloadAll` streaming ZIP, `ImageHandler` preview, quotation PDF persistence, claim/endorsement/proposal/policy document management, and `DEF-010` canonical `StorageKey` remediation).

The only remaining document-adjacent items are:
1. **3 Document-Domain `UNKNOWN` Items (`GAP-UNK-11-001`, `GAP-UNK-11-002`, `GAP-UNK-11-003`)**:
   - `GAP-UNK-11-001`: Exact SQL body of `USP_Insert_CalliberPolicyWebhookData` and physical DDL of legacy webhook table (mitigated via additive `tbl_calliber_policy_webhook` with full 48-field JSON + indexed columns).
   - `GAP-UNK-11-002`: External HiCaliber/Calliber authentication mechanism and outbound push trigger contract (inbound webhook supports optional `X-Calliber-Signature` HMAC-SHA256; outbound push trigger deferred until external API documentation is provided).
   - `GAP-UNK-11-003`: Legacy archive storage virtual directory mapping for historical files prior to migration cutover.
2. **Secondary KYC / Employee / Circular File Slots**:
   - Agent/POSP onboarding KYC attachments (PAN, Aadhaar, Cancelled Cheque, Certificate files on `tbl_user` / `tbl_agent`) and Company Circular PDF attachments (`tbl_circular`) can seamlessly use the Phase 11 `tbl_documents` engine (`EntityType = "USER_KYC"` / `"CIRCULAR"`) when those auxiliary endpoints are exposed.
3. **Production S3 / MinIO Boto3 Adapter Wiring**:
   - Phase 11 implemented `StorageBackend`, `LocalFilesystemStorageBackend`, and `MockMemoryStorageBackend` with config placeholders (`S3_ENDPOINT_URL`, `S3_BUCKET_NAME`). An `S3CompatibleStorageBackend` (`aioboto3` / `boto3` against local MinIO) can be added as an optional adapter when container object-storage deployment is scheduled.

---

## 15. Known Defects Status (`DEF-001` → `DEF-011`)

Per [`18_legacy_known_defects.md`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/docs/migration/18_legacy_known_defects.md) and [`phase_11_document_file_engine_report.md`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/docs/migration/phase_11_document_file_engine_report.md), **all 11 cataloged legacy defects (`DEF-001` through `DEF-011`) are 100% FIXED and MITIGATED**:

| Defect ID | Severity | Legacy Defect Description | Mitigation in `Reliable-Insurance-Backend` | Verified In |
| :--- | :---: | :--- | :--- | :---: |
| **`DEF-001`** | **P0** | Completely unauthenticated `Service.asmx` (`339` `[WebMethod]`s) and `VehicleService.asmx` | JWT Bearer authentication + 56-role `CurrentUser` RBAC dependency required on all protected `/api/v1/*` endpoints | Phase 3 & Phase 5F |
| **`DEF-002`** | **P0** | Hardcoded production DB passwords, Signzy credentials, SMS API keys, and OneSignal keys in `Web.config` / C# source | Pydantic `Settings` environment-only config + `_enforce_dev_db_isolation` blocking `brahmainsurance` | Phase 1 & Phase 11 |
| **`DEF-003`** | **P0** | SQL Injection across `124` inline SQL string concatenations in C# code-behind and `SearchMethods.aspx.cs` | 100% parameterized SQLAlchemy 2.0 ORM queries; zero raw string interpolation | Phases 2–11 |
| **`DEF-004`** | **P0** | Client-side RBAC & Insecure Direct Object Reference (IDOR) via tampered query strings / hidden fields | Server-side branch (`BranchId`) and principal (`AgentId`, `FranchiseId`, `CustomerId`) ownership checks in services | Phases 5F–11 |
| **`DEF-005`** | **P0** | Plaintext user passwords stored in `tbl_user.Password` and transmitted without hashing | Bcrypt password hashing (`passlib`) with transparent migration from legacy hashes | Phase 3 |
| **`DEF-006`** | **P1** | Unauthenticated `PolicyParserWebhook.aspx` allowing arbitrary policy/financial data injection | Optional HMAC-SHA256 verification (`X-Calliber-Signature` when `CALLIBER_WEBHOOK_SECRET` is configured) + audit logging | Phase 11 |
| **`DEF-007`** | **P1** | Arbitrary file download / path traversal in `DownloadAll.ashx` & `ImageHandler.ashx` (`Request.QueryString["file"]`) | `_validate_safe_relative_key()` blocking `..`, absolute paths, UNC paths, null bytes + `Path.resolve().relative_to(root)` containment + RBAC | Phase 11 |
| **`DEF-008`** | **P1** | Non-atomic multi-step financial mutations (`DAL_Operations.cs` opens/closes separate connections per SP without transactions) | Single async SQLAlchemy session transaction boundary (`async with db.begin()`) with automatic rollback on storage or validation failure | Phases 7–11 |
| **`DEF-009`** | **P1** | Floating-point (`double`/`float`) precision loss in premium, GST, TDS, and commission calculations | Strict `Decimal` arithmetic (`ROUND_HALF_UP` to 2 decimal places) across all rating, payment, commission, and accounting services | Phases 6–10 |
| **`DEF-010`** | **P1** | Copy-paste variable bug in `Service.asmx.cs` `UpdateClaimDocument` (`L12842–L12854`) deleting `ClaimPhoto` when replacing `FinalBill` | Distinct canonical `StorageKey` per `DocumentSlot` (`CLAIM_PHOTO` vs `FINAL_BILL`); replacing `FINAL_BILL` never deletes `CLAIM_PHOTO` | Phase 11 (`test_def010_remediation_*`) |
| **`DEF-011`** | **P2** | Swallowed exceptions (`catch (Exception ex) { }`) returning HTTP 200 / `"0"` on database failure | Structured FastAPI exception handlers returning deterministic HTTP `400`/`401`/`403`/`404`/`409`/`422`/`500` responses | Phases 1–11 |

---

## 16. Consolidated UNKNOWN Register

In strict compliance with project governance, **no `UNKNOWN` item has been guessed or fabricated**. Below is the complete, consolidated register of all remaining `UNKNOWN` items across the repository:

| Unknown ID | Domain | Description of Missing Evidence | Current Mitigation / Handling in Codebase | What Evidence Would Resolve It |
| :--- | :--- | :--- | :--- | :--- |
| **`GAP-UNK-001`** | Database / Stored Procedures | Exact internal SQL bodies of legacy `USP_*` / `sp_*` stored procedures that were not present in the offline SQL dump (`90` missing SPs in `09_missing_stored_procedures.md`, of which `68` non-core report/HR/archive SPs had insufficient C# parameter context to reconstruct). | Core 22 transactional SPs were reconstructed from C# `DAL_Operations.cs` parameter bindings and WebForms code-behind in Phase 0; remaining 68 report/archive SPs are documented as `UNKNOWN`. | Read-only export of `SHOW CREATE PROCEDURE` from the legacy MySQL schema dump (offline DDL export only). |
| **`GAP-UNK-002`** | Database DDL Precision | Exact MySQL column types (`DECIMAL(p,s)` vs `DOUBLE` vs `FLOAT` vs `VARCHAR` lengths) for legacy tables whose `CREATE TABLE` DDL was not included in the offline repository snapshot. | Modeled using conservative `Numeric(15, 2)` / `Numeric(18, 2)` for currency and `String(255)` for text based on `AllMaster.cs` C# types and Phase 2–10 schema baselines. | Offline `mysqldump --no-data` schema DDL file from the legacy database. |
| **`GAP-UNK-003`** | Rating / Commissions | Exact tie-breaking order inside legacy stored procedures when multiple active OD discount or commission slabs overlap for the exact same `(Insurer, VehicleType, RTO, EffectiveDate)` tuple without `ORDER BY`. | Deterministic ordering (`ORDER BY id DESC` — latest inserted active slab wins) implemented in `RatingEngineService` and `CommissionService`. | Inspection of the exact `ORDER BY` / `LIMIT 1` clause inside the legacy slab-lookup stored procedures. |
| **`GAP-UNK-11-001`** | Phase 11 Webhook DB | Exact SQL body of `USP_Insert_CalliberPolicyWebhookData` and physical table name/DDL of the legacy Calliber webhook staging table. | Additive `tbl_calliber_policy_webhook` table storing all 48 `CalliberPolicyData` fields both as indexed columns and lossless `raw_payload_json`, plus cross-linking to `tbl_transaction` and `tbl_documents`. | Offline DDL + SP definition for `USP_Insert_CalliberPolicyWebhookData`. |
| **`GAP-UNK-11-002`** | Phase 11 External Integration | External HiCaliber/Calliber caller authentication mechanism and whether the legacy system pushes PDFs outbound to HiCaliber or relies on an external folder watcher. | Inbound webhook supports backward-compatible open mode (when `CALLIBER_WEBHOOK_SECRET` is unset) and `X-Calliber-Signature` HMAC-SHA256 verification (when set). Outbound trigger is not guessed. | HiCaliber integration specification or external watcher service configuration. |
| **`GAP-UNK-11-003`** | Phase 11 Legacy Storage | Exact IIS virtual directory mapping and physical disk layout of historical `/ArchivePolicy/` files prior to migration cutover. | Canonical `StorageKey` prefix layout (`proposals/`, `policies/`, `claims/`, `endorsements/`, `quotations/`, `calliber/`) with fallback resolution for legacy bare filenames in `DocumentService`. | IIS `applicationHost.config` virtual directory mapping from the legacy server. |

---

## 17. Deferred Work Register

The table below catalogs every functional capability intentionally deferred during Phases 0–11, categorized by priority (`P1` High, `P2` Medium, `P3` Low):

| Deferred ID | Domain | Deferred Capability | Legacy Evidence | Priority | Target Candidate |
| :--- | :--- | :--- | :--- | :---: | :--- |
| **`DEF-WORK-01`** | Master Data & Search (`Phase 4C`) | Expose `/api/v1/masters/*` REST endpoints for the 7 Phase 4B master tables (`VehicleType`, `SubType`, `Make`, `Model`, `Variant` 91-col pricing, `RTO`, `Insurer`) + hierarchy masters (`Branch`, `State`, `District`, `Bank`) + Redis caching | `Service.asmx.cs` (`48` WebMethods), [`migration_status.md`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/docs/migration/migration_status.md) | **P1** | **Candidate A** |
| **`DEF-WORK-02`** | Autocomplete / Typeahead APIs | Expose `/api/v1/search/*` fast prefix-autocomplete endpoints replacing `Clerk/SearchMethods.aspx.cs` (`41` WebMethods) and `AppSearchMethod.aspx.cs` (`16` WebMethods) | `SearchMethods.aspx.cs`, `AppSearchMethod.aspx.cs` | **P1** | **Candidate A** |
| **`DEF-WORK-03`** | External KYC Integration | Signzy Vehicle RC lookup (`GetVehicleDetails` / `RC_CheckVehicleDtl.aspx.cs`) + `tbl_vehiclenorc_details` local DB cache + mock provider (`LBR-021`, `LBR-022`) | `VehicleService.asmx.cs`, `RC_CheckVehicleDtl.aspx.cs` | **P1** | **Candidate B** |
| **`DEF-WORK-04`** | Notifications (SMS / OTP / Push / Email) | Pluggable `SMSProvider` (`Send_SMS.cs`, mobile OTP login `LBR-123`..`125`), `OneSignalPushProvider` (`LBR-126`..`128`), and `SMTPEmailProvider` (`SendMailToAutority.aspx.cs`) with deterministic local mocks | `App_Code/Send_SMS.cs`, `SendPushNoti*.aspx.cs`, `SendMailToAutority.aspx.cs` | **P1** | **Candidate B** |
| **`DEF-WORK-05`** | Reporting, Exports & POSP Invoices | POSP Commission Tax Invoice (`rpt_POSP_Invoice.aspx.cs`), Voucher Print, TDS/GST Statutory Registers, Policy/Cheque/Renewal MIS CSV/Excel exports, and Graphical Dashboard KPI APIs (`48` dashboard WebMethods) | `49` `.rdlc` templates, `GraphicalDashBoard*.aspx.cs`, `MISReport.aspx.cs` | **P2** | **Candidate C** |
| **`DEF-WORK-06`** | Bulk Excel MIS Import | Bulk Agent Policy MIS Excel upload & staging reconciliation (`adm_ImportTransAgentPolicyMIS.aspx.cs` / `tbl_importagentpolicy`) | `adm_ImportTransAgentPolicyMIS.aspx.cs` | **P2** | **Candidate C** |
| **`DEF-WORK-07`** | Scheduled / Background Jobs (`Celery`) | Daily renewal expiry detection & follow-up tracking (`tbl_preyearrenewalstatus`), birthday wishes, overdue uncleared cheque login lock (`LBR-069`), and stale wallet lock cleanup | `SendPushNotiRenewal.aspx.cs`, `Adm_LockChequeEntry.aspx.cs` | **P2** | **Candidate D** |
| **`DEF-WORK-08`** | Non-Motor Health Family Grid & Telecaller Targets | Health policy family member grid (`tbl_healthmember`, `LBR-058`), employee/telecaller monthly target tracking (`tbl_targetnew`, `LBR-131`), IDV override requests (`tbl_idvrequest`), and POSP reward points (`tbl_rewardpoint`) | `PolicyTransactionNew.aspx.cs`, `AppTargetDashBoard` | **P2** | **Candidate D / Later** |
| **`DEF-WORK-09`** | Legacy `/Service.asmx/*` Compatibility Shim | Optional route/payload adapter translating legacy `/Service.asmx/<MethodName>` mobile app calls to `/api/v1/*` services | `Service.asmx.cs` (`339` WebMethods) | **P3** | **Candidate E** |
| **`DEF-WORK-10`** | In-App Chatboard, Circulars, Help & HR/Payroll | Internal chatboard (`tbl_appchatboard`), circulars (`tbl_circular`), help tickets (`tbl_customerhelp`), mobile attendance (`InsertAppAttendance`), and the 21-table HR/Payroll module (`API_HR*`) | `Service.asmx.cs`, `AllMaster.cs` L2242–L2703 | **P3** | **Deferred / Out of Core Scope** |

---

## 18. Legacy Compatibility Surface

| Legacy Contract | Current Status in `Reliable-Insurance-Backend` | Compatibility Assessment |
| :--- | :--- | :--- |
| **`GET /api/v1/documents/legacy/DownloadAll.ashx`** | **IMPLEMENTED (Phase 11)**: Supports legacy query parameters (`TransId`, `ProposalId`, `ClaimId`, `EndorsementId`, `QuotationId`) and streams a valid ZIP archive. | **100% Compatible** |
| **`GET /api/v1/documents/legacy/ImageHandler.ashx`** | **IMPLEMENTED (Phase 11)**: Supports legacy query parameters (`DocId`, `FileName`, `Type`, `EntityId`) and streams inline image/PDF previews. | **100% Compatible** |
| **`POST /api/v1/documents/webhooks/policy-parser`** | **IMPLEMENTED (Phase 11)**: Accepts exact 48-field `CalliberPolicyData` PascalCase payload (`PolicyParserWebhook.aspx` contract). | **100% Compatible** |
| **Database Table & Column Names (`tbl_*`)** | **IMPLEMENTED (Phases 2–11)**: All 45 legacy SQLAlchemy models preserve exact legacy table names (`tbl_customer`, `tbl_transaction`, `tbl_claims`, etc.) and column mappings. | **100% Compatible** |
| **`/Service.asmx/<WebMethod>` & `/Clerk/SearchMethods.aspx/<WebMethod>` Direct URLs** | **NOT MOUNTED AS SOAP/ASMX ROUTES**: Business logic is exposed via modern `/api/v1/*` REST JSON endpoints. If legacy Android/iOS apps must connect without client-side URL updates, a lightweight FastAPI compatibility router (`/Service.asmx/{method_name}`) can delegate to existing services (**Candidate E**). | **REST Modernized (Shim Optional)** |

---

## 19. Remaining Migration Risk Assessment

| Risk ID | Risk Category | Description | Severity | Mitigation Strategy |
| :--- | :--- | :--- | :---: | :--- |
| **`RISK-12-01`** | **Frontend / Mobile App Integration Blocker** | Frontend web forms and mobile apps cannot populate cascading vehicle dropdowns (Type → SubType → Make → Model → Variant → Regional Price), RTO lists, or insurer dropdowns without Phase 4C `/api/v1/masters/*` and `/api/v1/search/*` endpoints. | **HIGH (P0/P1)** | Prioritize **Candidate A (Search, Master Data & Utility APIs)** immediately in Phase 12. |
| **`RISK-12-02`** | **External KYC & OTP Workflow Gap** | Vehicle registration auto-fill (`Signzy` RC lookup) and mobile OTP / policy notification flows (`SMS` / `OneSignal` / `Email`) are not yet available in the new backend. | **MEDIUM-HIGH (P1)** | Implement **Candidate B** using strict provider interfaces (`MockSignzyProvider`, `MockSMSProvider`, `MockPushProvider`) so zero external calls occur in dev/test while production adapters are plug-and-play. |
| **`RISK-12-03`** | **Operational Reporting & Finance Export Gap** | Finance/accounting teams and POSP agents rely on printable POSP Commission Invoices, Voucher prints, TDS/GST statutory registers, and dashboard KPI summaries. | **MEDIUM (P2)** | Implement **Candidate C (Reporting, Exports, POSP Invoices & Dashboards)** on top of the completed Phase 6–10 tables. |
| **`RISK-12-04`** | **Unextracted Legacy SP SQL Bodies (`GAP-UNK-001`)** | 68 non-core reporting/archive/HR stored procedures have no SQL bodies in the local baseline. | **LOW (P3)** | Core transactional engines are already 100% migrated and verified (`309 passed`). Keep `GAP-UNK-001` explicitly documented until an offline DDL/SP export is provided. |

---

## 20. Candidate Phase 12 Options (`Candidate A`, `Candidate B`, `Candidate C`)

Based on the evidence-driven gap inventory above, we define and rank the **three primary candidates** for **Phase 12** (plus subsequent roadmap phases):

---

### CANDIDATE A — Master Data, Cascading Lookups, Autocomplete Search & Hierarchy APIs (`Phase 4C Completion` + `SearchMethods` Parity) — **[RANK #1 / P0-P1]**

- **Objective**: Complete the deferred **Phase 4C** milestone (`migration_status.md`) and migrate the **74 partially-migrated `[WebMethod]`s** across `Service.asmx.cs`, `Clerk/SearchMethods.aspx.cs`, and `AppSearchMethod.aspx.cs` so that web and mobile clients have complete cascading master data dropdowns, 91-column state-wise vehicle variant pricing lookups, hierarchy masters (`Branch`, `State`, `District`, `Bank`), and fast typeahead/autocomplete search.
- **Included Scope**:
  1. **Master Data Read & Admin CRUD Endpoints (`/api/v1/masters/*`)**:
     - `GET /api/v1/masters/vehicle-types` & `/vehicle-sub-types`
     - `GET /api/v1/masters/makes`, `/models` (by make/sub-type), `/variants` (by model/fuel, including state/RTO-based ex-showroom price resolution across the 91 `tbl_vehicle_variants` regional columns)
     - `GET /api/v1/masters/rtos` (search by code/city/state) & `/insurers` (filtered by vehicle type via `tbl_insurancecompanybyvehicletype`)
     - `GET /api/v1/masters/addons`, `/pa-owner-driver-rates`, `/towing-rates`, `/ncb-slabs`
  2. **Organizational & Geographical Reference Models & Endpoints**:
     - Add SQLAlchemy models + Alembic migration for core reference masters (`tbl_branch`, `tbl_state`, `tbl_district`, `tbl_bank`) and expose `/api/v1/masters/branches`, `/states`, `/districts`, `/banks`.
  3. **Unified Typeahead / Autocomplete API (`/api/v1/search/*`)**:
     - Replace the `57` AJAX autocomplete `[WebMethod]`s in `Clerk/SearchMethods.aspx.cs` (`41`) and `AppSearchMethod.aspx.cs` (`16`): fast prefix search for Customer Name, Mobile No, Registration No, Policy No, Chassis No, Engine No, Agent, Franchise, RTO, Make, Model, Variant, Insurer, and Bank, strictly scoped by the caller's 56-role RBAC & branch context.
  4. **Optional Redis Read-Through Caching Layer**:
     - Cache immutable/slow-changing master lookups (`vehicle-types`, `makes`, `models`, `rtos`, `insurers`, `states`) with graceful local-memory/DB fallback when Redis is unavailable.
- **Why Candidate A is Ranked #1**:
  - Directly closes the **largest remaining partial-migration gap (`74` `[WebMethod]`s and `188` SP tokens)** and completes the unfinished `Phase 4C` milestone in `migration_status.md`.
  - Unblocks every frontend/mobile screen (Quotation creation, Policy booking, Customer/Vehicle onboarding, Payment cheque bank selection) which cannot function end-to-end in a UI without master dropdowns and autocomplete APIs.
  - 100% deterministic from existing local evidence (`app/models/master.py`, `app/repositories/master.py`, `AllMaster.cs`, `SearchMethods.aspx.cs`) with **zero external dependency risk**.
- **Estimated Complexity**: **Medium** (1 Alembic migration for reference masters, 2 new routers `/api/v1/masters` & `/api/v1/search`, ~25–30 endpoints, ~25 integration tests).

---

### CANDIDATE B — External Integrations, KYC & Notification Engine (`Signzy RC`, `SMS/OTP`, `OneSignal Push`, `SMTP Email` + Renewal Follow-Up) — **[RANK #2 / P1]**

- **Objective**: Migrate the legacy external integration and notification workflows (`RC_CheckVehicleDtl.aspx.cs`, `VehicleService.asmx.cs`, `Send_SMS.cs`, `SendPushNoti*.aspx.cs`, `SendMailToAutority.aspx.cs`, and renewal follow-up tracking) behind clean, pluggable provider interfaces with **100% local mock implementations** in dev/test (guaranteeing zero external network calls or credential leaks).
- **Included Scope**:
  1. **Signzy Vehicle RC Lookup & Local Cache (`tbl_vehiclenorc_details`)**:
     - Pluggable `VehicleRCProvider` (`MockVehicleRCProvider` default) + `tbl_vehiclenorc_details` cache table + `POST /api/v1/vehicles/rc-lookup` (`LBR-021`, `LBR-022`), mitigating `DEF-002`.
  2. **SMS & Mobile OTP Verification Service (`Send_SMS.cs`)**:
     - Pluggable `SMSProvider` (`MockSMSProvider` default) + OTP generation/verification endpoints (`/api/v1/auth/otp/send`, `/api/v1/auth/otp/verify`) + transactional SMS notification log (`tbl_notification_log`, `LBR-123`..`125`).
  3. **OneSignal Push Notification & SMTP Email Services**:
     - Pluggable `PushNotificationProvider` & `EmailProvider` (`MockPushProvider`, `MockEmailProvider`) + device token registration + renewal/policy/birthday notification dispatch endpoints (`LBR-126`..`128`).
  4. **Renewal Expiry Query & Follow-Up Tracking (`tbl_preyearrenewalstatus`)**:
     - `GET /api/v1/renewals/due` (policies expiring in configurable day windows) and `POST /api/v1/renewals/{policy_id}/follow-up` (`SelectPreYaerRenewalExpiryPolicy`, `InsertPreYearRenewalStatus`).
- **Why Candidate B is Ranked #2**:
  - Closes the remaining external KYC (`Signzy`), authentication (`OTP`), and customer engagement (`SMS`/`Push`/`Renewal Follow-Up`) business rules (`LBR-021`..`022`, `LBR-123`..`128`).
  - Best executed immediately after Candidate A (or as Phase 13) once all core master and search tables are in place.
- **Estimated Complexity**: **Medium**.

---

### CANDIDATE C — Reporting, MIS Exports, POSP Commission Invoices, Dashboards & Bulk Excel Import — **[RANK #3 / P2]**

- **Objective**: Migrate the legacy operational reporting, financial statement export, POSP Commission Tax Invoice, graphical dashboard KPIs (`48` dashboard WebMethods), and bulk Excel policy MIS import workflows.
- **Included Scope**:
  1. **Executive & Role-Scoped Dashboard APIs (`/api/v1/dashboard/*`)**:
     - Summary counters (Policies, Premium, Pending Inward, Pending Cheques, Open Claims, Renewal Due) and monthly/insurer/branch/product chart series (`GraphicalDashBoard*.aspx.cs`, `SearchMethods.aspx.cs` dashboard WebMethods).
  2. **Financial, Statutory & Operational MIS Reports (`/api/v1/reports/*`)**:
     - POSP Commission Tax Invoice PDF/JSON (`rpt_POSP_Invoice.aspx.cs`), Voucher Print PDF, TDS Deduction Register, GST Outward/Inward Register, DayBook, Policy Register, and Cheque Bounce/Pending Register with streaming CSV/Excel export.
  3. **Bulk Agent Policy MIS Import (`tbl_importagentpolicy`)**:
     - Safe, validated batch upload endpoint replacing `adm_ImportTransAgentPolicyMIS.aspx.cs` with row-level validation and atomic staging.
- **Why Candidate C is Ranked #3**:
  - Read-mostly aggregation and export layer that builds upon all core transactional and master tables from Phases 2–12.
- **Estimated Complexity**: **Medium-High**.

---

## 21. Recommended Next Phase

### **RECOMMENDED NEXT PHASE: CANDIDATE A — Phase 12: Master Data, Cascading Lookups, Autocomplete Search & Hierarchy APIs (`Phase 4C Completion` + `SearchMethods` Parity)**

#### Rationale for Recommending Candidate A as Phase 12:
1. **Completes the Deferred Phase 4C Architecture**: `app/models/master.py` and `app/repositories/master.py` were built in Phase 4B specifically to power `/api/v1/masters/*`, which remains marked `PENDING APPROVAL` in [`migration_status.md`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/docs/migration/migration_status.md#L121-L133).
2. **Highest API & Stored Procedure Coverage Lift**: Migrates **74 partially-migrated `[WebMethod]`s** and **188 stored procedure call tokens** in a single cohesive phase, lifting programmatic entry point coverage from **51.3% (215/419)** to **69.0% (289/419)** (and **89.2%** of all non-dashboard/non-HR/non-chat entry points).
3. **Zero External Ambiguity**: Every single table, column (including the 91 regional pricing columns in `tbl_vehicle_variants`), and query pattern is fully evidenced in local files (`AllMaster.cs`, `Service.asmx.cs`, `SearchMethods.aspx.cs`, `AppSearchMethod.aspx.cs`, `app/models/master.py`).
4. **Clean Recommended Roadmap Sequence for Remaining Phases**:
   - **Phase 12 (Candidate A)**: Master Data, Hierarchy Models (`Branch`, `State`, `District`, `Bank`), Cascading Lookups, 91-Column Variant Pricing API, Autocomplete Search (`/api/v1/masters/*`, `/api/v1/search/*`) & Redis Cache.
   - **Phase 13 (Candidate B)**: External Integrations (`Signzy` RC Lookup + Cache, `SMS`/OTP, `OneSignal` Push, `SMTP` Email via Mock-Safe Providers) & Renewal Expiry Follow-Up (`/api/v1/renewals/*`).
   - **Phase 14 (Candidate C)**: Reporting, Statutory Registers (TDS/GST/DayBook), Streaming CSV/Excel Exports, POSP Commission Tax Invoices, Role-Scoped Dashboards (`/api/v1/dashboard/*`, `/api/v1/reports/*`), and Bulk MIS Import.
   - **Phase 15 (Candidates D & E — Optional/Cutover)**: Celery Beat Scheduled Operational Jobs + Legacy `/Service.asmx/*` Mobile App Compatibility Shim (if required for legacy mobile clients).

---

## 22. Final Audit Verdict

**`GREEN — MIGRATION COVERAGE MAPPED`**

- **Audit Completeness**: 100% of legacy entry points (`419` programmatic endpoints + `213` core `.aspx` pages), stored procedures (`1,855` SP call tokens / `943` canonical SPs), database entities (`188` `API_*` classes + `36` raw-SQL tables vs `47` SQLAlchemy models), business rules (`LBR-001`..`LBR-140`), and known defects (`DEF-001`..`DEF-011`) have been accounted for and mapped with exact quantitative metrics.
- **Unknowns & Deferred Items**: Explicitly separated and documented in Sections 16 and 17 without fabrication.
- **Repository Integrity**: Zero application, migration, or test files were modified during this audit (`HEAD = e9d0418`, working tree clean except for this audit report).
