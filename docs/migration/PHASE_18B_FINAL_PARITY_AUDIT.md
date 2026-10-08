# PHASE 18B — INDEPENDENT PRE-COMMIT FORENSIC AUDIT
## FINAL LEGACY $\leftrightarrow$ FASTAPI FEATURE PARITY VERIFICATION

**Project:** `Reliable-Insurance-Backend` (Legacy C#/.NET 4.0 WebForms + ASMX $\rightarrow$ FastAPI Migration)
**Branch:** `tejas-feature`
**Previous Verified Commit:** `481b591db581ffd4225f3b4385ac91fe04101305`
**Phase 18A Alembic Head:** `b18a0c5d1801` (revises `a16b0c4d1601`)
**Physical MySQL Tables (`reliable_insurance_dev`):** `82` (`74` baseline + `8` Phase 18A tables + `2` additive columns on `tbl_agent`)
**Mounted ASGI Routes:** `308` total `app.routes` / `304` `APIRoute` endpoints (`257` baseline + `51` Phase 18A `APIRoute`s; `301` claimed in Phase 18A report)
**Automated Regression Suite:** `423 / 423 PASSED` (`411` baseline + `12` Phase 18A tests in `256.20s`)
**Production Database (`brahmainsurance`) Access:** `0 connections / 0 queries`
**Embedded Legacy Source (`./InsurancefinalNew_2026_09_23/`):** `READ-ONLY / 0 modified / 0 staged`
**`LBR-069` (`UtilityService.enforce_overdue_cheque_locks`):** `UNTOUCHED (0 diff lines)`
**Audit Verdict:** **GREEN — COMMIT READY (WITH DOCUMENTED P3 OBSERVATIONS)**

---

## 1. Executive Summary

This document records the **Phase 18B Independent Pre-Commit Forensic Audit** of the Phase 18A implementation for `Reliable-Insurance-Backend`. Acting as an independent, read-only verifier, this audit cross-examined:
1. The **embedded legacy C#/.NET solution** (`./InsurancefinalNew_2026_09_23/InsurancefinalNew/`: `1,277` `.cs` files, `1,240` `.aspx` files, `621` `.aspx.cs` code-behind files, `394` active WebMethod/Webhook entrypoints, `9` `.rpt` files, and `Web.config`).
2. The **Phase 17B Authoritative Feature Inventory** (`docs/migration/PHASE_17B_FINAL_LEGACY_FEATURE_INVENTORY.md` covering all `120` canonical feature groups `F-17B-001`..`F-17B-120`).
3. The **Phase 18A Implementation Claims** (`docs/migration/PHASE_18A_IMPLEMENTATION_REPORT.md`).
4. The **actual FastAPI working-tree code, Alembic migrations, physical MySQL schema (`reliable_insurance_dev`), and automated test suite**.

### Key Independent Findings
- **Zero `P0` or `P1` Defects (`0 P0`, `0 P1`, `0 P2`, `3 P3`)**:
  - **All `82 / 82` `MUST` features (`F-17B-001`..`082`)** remain 100% intact and regression-verified across `411` baseline tests.
  - **All `10 / 10` `SHOULD` features (`F-17B-083`..`088`, `F-17B-091`..`094`)** are genuinely implemented in `app/services/phase18a_service.py`, `app/api/v1/endpoints/phase18a.py`, `app/models/phase18a_features.py`, and `app/schemas/phase18a.py` with real database persistence, `Decimal` arithmetic (`ROUND_HALF_UP`), RBAC enforcement, and E2E integration tests.
  - **All `7 / 7` `ENHANCE` features (`F-17B-089`..`090`, `F-17B-095`..`099`)** preserve the legacy business rules (including the exact `(0.0, 0.0) -> "No Address Found"` GPS rule in `Clerk/Location.aspx.cs` L49–52 and the `NEWSUMMERY` / `FROMRA` / `ONLINETORA` modes in `SendMailToAutority.aspx.cs` L40–82) while modernizing transport, configuration, and security.
  - **All `15 / 15` `OBSOLETE` items (`F-17B-100`..`113` + `F-17B-118`)** were independently re-audited to confirm that only obsolete technology (`CrystalDecisions.*`, WebForms `ViewState`, unauthenticated ASMX transport, commented-out `InsuranceAppService` SOAP proxy) or dead/non-insurance code (`HR_*`, tutorial calendar, scratch pages) was retired—never an active insurance business capability.
  - **All `6` remaining `UNKNOWN` items (`F-17B-114`, `115`, `116`, `117`, `119`, `120`)** remain strictly preserved with **zero fabricated stored procedure SQL or invented table DDL**.
  - **Route Count Clarification (`FIND-18B-001`, `P3`)**: While `PHASE_18A_IMPLEMENTATION_REPORT.md` claimed `301` routes (`257 + 44`), direct inspection of `app.main:app` proves Phase 18A actually added **`51` new `APIRoute` endpoints** (`50` in `app/api/v1/endpoints/phase18a.py` + `1` in `app/api/v1/endpoints/integrations.py`), bringing total `app.routes` to **`308`** (`304` `APIRoute` endpoints + `4` built-in OpenAPI/docs routes).

---

## 2. Audit Scope

| Audit Dimension | Scope Inspected | Verification Method |
| :--- | :--- | :--- |
| **Legacy Source Code** | `./InsurancefinalNew_2026_09_23/InsurancefinalNew/` (`API`, `BLL`, `DAL`, `Insurance`) | Direct read-only source inspection (`Reference.cs`, `ImageHandler.ashx.cs`, `PE_UploadPolicy.aspx.cs`, `adm_LockCashEntry1.aspx.cs`, `POSP_MultiEntryIdealPayment.aspx.cs`, `SendMailToAutority.aspx.cs`, `View_InspectionCordinatorRequest.aspx.cs`, `Location.aspx.cs`, `VehicleNoDetails.cs`, `DAL_Operations.cs`) |
| **FastAPI Application Code** | `app/models/phase18a_features.py`, `app/models/profile.py`, `app/schemas/phase18a.py`, `app/services/phase18a_service.py`, `app/api/v1/endpoints/phase18a.py`, `app/api/v1/endpoints/integrations.py`, `app/providers/attestr.py`, `app/core/config.py`, `app/api/v1/router.py` | Line-by-line code review & AST/runtime route inspection |
| **Database & Migrations** | `alembic/versions/b18a0c5d1801_phase_18a_remaining_legacy_features.py` & live local MySQL `reliable_insurance_dev` | `alembic current`, `SHOW TABLES`, `SHOW COLUMNS`, `SHOW INDEX` |
| **Automated Test Suite** | `tests/test_phase18a_remaining_features.py` (`12` test suites) + full `tests/` suite (`423` total tests) | Full `python -m pytest -q` execution (`423 passed in 256.20s`) |
| **Safety & Freeze Guards** | `app/services/utility_service.py` (`LBR-069`), `app/core/config.py`, `git status --short` | `git diff` verification & credential/DB isolation checks |

---

## 3. Part 1 — Baseline Verification

Independent runtime and Git verification produced the following exact measurements:

| Baseline Metric | Expected / Claimed (Phase 18A Report) | Independently Observed (Phase 18B Audit) | Match / Explanation |
| :--- | :--- | :--- | :--- |
| **Git Branch** | `tejas-feature` | `tejas-feature` | **EXACT MATCH** |
| **Previous Git Commit** | `481b591db581ffd4225f3b4385ac91fe04101305` | `481b591db581ffd4225f3b4385ac91fe04101305` | **EXACT MATCH** |
| **Alembic Head** | `b18a0c5d1801` | `b18a0c5d1801 (head)` | **EXACT MATCH** |
| **Active Runtime Database** | `reliable_insurance_dev` | `reliable_insurance_dev` | **EXACT MATCH** (`0` connections to `brahmainsurance`) |
| **Physical MySQL Tables** | `82` (`74` baseline + `8` new) | `82` (`74` baseline + `8` new) | **EXACT MATCH** (All 8 new `tbl_*` tables verified in MySQL) |
| **Mounted ASGI Routes** | `301` (`257` + `44` claimed) | **`308` total `app.routes` (`304` `APIRoute` + `4` docs)** | **EXPLAINED (`FIND-18B-001`, `P3`)**: Baseline had `257` total `app.routes` (`253` `APIRoute` + `4` OpenAPI/docs). Phase 18A added **`50` routes** in `phase18a.py` + **`1` route** in `integrations.py` = **`+51` new `APIRoute`s** (`257 + 51 = 308` total `app.routes`). |
| **Automated Tests** | `423 / 423 passing` | **`423 / 423 passed in 256.20s`** | **EXACT MATCH** (`411` baseline + `12` Phase 18A tests) |
| **Legacy Source Status** | Read-only / Unstaged | `?? InsurancefinalNew_2026_09_23/` (`0` modified, `0` staged) | **EXACT MATCH** |
| **`LBR-069` Freeze Status** | Untouched | `0` lines changed in `app/services/utility_service.py` | **EXACT MATCH** |

### Git Working Tree State (`git status --short` Before & After Audit)
```text
 M app/api/v1/endpoints/integrations.py
 M app/api/v1/router.py
 M app/core/config.py
 M app/models/__init__.py
 M app/models/profile.py
 M app/providers/__init__.py
 M app/schemas/integrations.py
?? InsurancefinalNew_2026_09_23/
?? alembic/versions/b18a0c5d1801_phase_18a_remaining_legacy_features.py
?? app/api/v1/endpoints/phase18a.py
?? app/models/phase18a_features.py
?? app/providers/attestr.py
?? app/schemas/phase18a.py
?? app/services/phase18a_service.py
?? docs/migration/PHASE_17A_FINAL_REMAINING_COVERAGE_AUDIT.md
?? docs/migration/PHASE_17B_FINAL_LEGACY_FEATURE_INVENTORY.md
?? docs/migration/PHASE_18A_IMPLEMENTATION_REPORT.md
?? tests/test_phase18a_remaining_features.py
```
*(Plus `?? docs/migration/PHASE_18B_FINAL_PARITY_AUDIT.md` created by this audit).*

---

## 4. Part 2 — Phase 17B $\rightarrow$ Phase 18A Reconciliation Summary

| Phase 17B Disposition | Phase 17B Count | Phase 18A Claimed Status | Phase 18B Independent Final Audit Status | Verified Count |
| :--- | :---: | :--- | :--- | :---: |
| **`MUST` (`F-17B-001`..`082`)** | `82` | `82` Implemented (`36 MATCH` + `46 HARDENED/ENHANCED`) | `29 VERIFIED_MATCH` + `31 VERIFIED_HARDENED` + `22 VERIFIED_ENHANCED` | **`82 / 82`** |
| **`SHOULD` (`F-17B-083`..`088`, `091`..`094`)** | `10` | `10` `HARDENED` | `10 VERIFIED_HARDENED` | **`10 / 10`** |
| **`ENHANCE` (`F-17B-089`..`090`, `095`..`099`)** | `7` | `7` `HARDENED` | `7 VERIFIED_ENHANCED` | **`7 / 7`** |
| **`OBSOLETE` (`F-17B-100`..`113`, `118`)** | `14` (+`1` from `UNKNOWN`) | `15` `OBSOLETE` | `15 OBSOLETE` (Verified technology/dead-code retirement) | **`15 / 15`** |
| **`UNKNOWN` (`F-17B-114`..`117`, `119`, `120`)** | `7` (-`1` resolved to `OBSOLETE`) | `6` `UNKNOWN` | `6 UNKNOWN` (Safely contained, `0` fabricated logic) | **`6 / 6`** |
| **TOTAL** | **`120`** | **`120`** | **100% Independently Reconciled** | **`120 / 120`** |

*(The full 120-row reconciliation matrix with all required columns is presented in **Section 23** below).*

---

## 5. Part 3 — 82 `MUST` Feature Regression Audit (`F-17B-001` .. `F-17B-082`)

All **82 `MUST` features** established in Phase 17B were independently re-verified across their FastAPI routers, services, SQLAlchemy models, RBAC dependencies, and baseline regression tests (`411 / 411 PASSED`):

| Domain | Feature IDs (`MUST`) | Count | Legacy Evidence | FastAPI Routers & Services | Physical Tables | Audit Verification Summary | Final Audit Status |
| :--- | :--- | :---: | :--- | :--- | :--- | :--- | :---: |
| **1. Auth, RBAC, Menus & Cheque Lock** | `F-17B-001`..`007` | `7` | `Log_In.aspx.cs`, `Service.asmx.cs::AppLogin1`, `Adm_LockChequeEntry.aspx.cs`, `Clerk/adm_MenuMaster.aspx.cs`, `Clerk/adm_FormPrivilege.aspx.cs` | `app/api/v1/endpoints/auth.py`, `admin.py`, `app/services/auth_service.py`, `admin_service.py`, `utility_service.py` | `tbl_user`, `tbl_userrole`, `tbl_menumaster`, `tbl_formprivilege`, `tbl_userprivilege` | Multi-principal login, JWT access/refresh tokens, bcrypt/Argon2 password hashing, OTP dispatch/verify, 30+ role RBAC, dynamic menu tree (`my-navigation`), and `LBR-069` cheque clearing lock verified. | `VERIFIED_HARDENED` (`001`..`006`), `VERIFIED_MATCH` (`007`) |
| **2. Master Data & Directories** | `F-17B-008`..`014` | `7` | `Clerk/adm_State.aspx.cs`, `adm_City.aspx.cs`, `adm_RTO.aspx.cs`, `adm_InsuranceCompany.aspx.cs`, `adm_ProductType.aspx.cs`, `adm_Make.aspx.cs`, `adm_PortalLoginId.aspx.cs` | `app/api/v1/endpoints/masters.py`, `admin.py`, `app/services/master_service.py` | `tbl_state`, `tbl_city`, `tbl_rto`, `tbl_insurancecompany`, `tbl_producttype`, `tbl_policytype`, `tbl_vehicletype`, `tbl_make`, `tbl_model`, `tbl_variant`, `tbl_fuel`, `tbl_bank`, `tbl_financer`, `tbl_branch`, `tbl_portallogin` | All geo, insurer, product, vehicle catalog, bank, financier, branch, and portal login masters verified with full CRUD & search. | `VERIFIED_MATCH` (`008`..`013`), `VERIFIED_HARDENED` (`014`) |
| **3. Users & Partner Profiles** | `F-17B-015`..`019`, `072` | `6` | `Clerk/adm_UserMaster.aspx.cs`, `adm_Agent.aspx.cs`, `adm_Franchise.aspx.cs`, `adm_MarketingExecutive.aspx.cs`, `adm_Dealer.aspx.cs`, `Service.asmx.cs::InsertAppAgent1` | `app/api/v1/endpoints/users.py`, `profiles.py`, `admin.py`, `app/services/user_service.py`, `profile_service.py` | `tbl_user`, `tbl_employee`, `tbl_agent`, `tbl_franchise`, `tbl_dealer` | Staff onboarding, POSP/Agent KYC & approval, Franchise commercial terms, Marketing Executive hierarchy, Dealer directory, and self-service profile endpoints verified. | `VERIFIED_HARDENED` (`015`), `VERIFIED_MATCH` (`016`..`019`, `072`) |
| **4. Customers, Proposals & Quotations** | `F-17B-020`, `021` | `2` | `Clerk/Cust_PolicyInfo.aspx.cs`, `ProposalEntry.aspx.cs`, `Service.asmx.cs::InsertCustomerPolicyInfo`, `InsertProposal` | `app/api/v1/endpoints/customers.py`, `quotations.py`, `app/services/customer_service.py`, `quotation_service.py` | `tbl_customer`, `tbl_customervehicle`, `tbl_quotation`, `tbl_app_quotationrequest` | Customer/vehicle registration, motor rating engine (OD/TP/AddOn/NCB/GST), and proposal lifecycle verified. | `VERIFIED_MATCH` (`020`, `021`) |
| **5. Core Policy Transactions** | `F-17B-022`..`028`, `073`, `074` | `9` | `Clerk/NewTranscationEntry.aspx.cs`, `Service.asmx.cs::InsertAppTransctiondetailsNew` (`_1`..`_8`, `_21`, `_NM`), `FindDoubleEntry.aspx.cs`, `VerifyTransaction.aspx.cs` | `app/api/v1/endpoints/policies.py`, `utilities.py`, `app/services/policy_service.py` | `tbl_transaction`, `tbl_transactionappnew`, `tbl_healthmemberdetails`, `tbl_specialidv` | Motor, non-motor (`_NM`), commercial vehicle (`GCV/PCV`), mobile multi-overload booking, duplicate policy check, back-dated audit trail, document attachment, and QC maker-checker verification verified. | `VERIFIED_HARDENED` (`022`, `023`, `025`, `026`), `VERIFIED_MATCH` (`024`, `028`, `073`, `074`), `VERIFIED_ENHANCED` (`027`) |
| **6. Payments, Cheques & E-Wallet** | `F-17B-029`..`035`, `075`, `076` | `9` | `Clerk/PaymentEntry.aspx.cs`, `ChequeClearance.aspx.cs`, `ChequeBounce.aspx.cs`, `CutNPay*.aspx.cs`, `WalletTopup.aspx.cs`, `BLL_Wallet` | `app/api/v1/endpoints/payments.py`, `app/services/payment_service.py`, `wallet_service.py` | `tbl_payment`, `tbl_chequedetails`, `tbl_wallet`, `tbl_wallettransaction`, `tbl_insurer_reconciliation` | Multi-mode collection, cheque lifecycle (`Pending -> Deposited -> Cleared -> Bounced`), bounce penalty (`Rs. 500`), Cut & Pay net settlement, insurer float reconciliation, and `SELECT ... FOR UPDATE` atomic wallet debit/lock/release verified. | `VERIFIED_HARDENED` (`029`..`032`, `034`, `035`), `VERIFIED_MATCH` (`033`, `075`, `076`) |
| **7. Commissions & Accounting** | `F-17B-036`..`042`, `077`..`081` | `12` | `Clerk/Commission*.aspx.cs`, `ExtraPayoutTransaction.aspx.cs`, `InstaPay*.aspx.cs`, `adm_LedgerMaster.aspx.cs`, `AccountVoucher*.aspx.cs`, `BLL_Commission`, `BLL_Account` | `app/api/v1/endpoints/commission_accounting.py`, `reports.py`, `app/services/commission_service.py`, `accounting_service.py` | `tbl_agentcommission`, `tbl_agentcommissionpayment`, `tbl_extrapayout`, `tbl_ledgermaster`, `tbl_account`, `tbl_financialyear` | Agent/Franchise commission math, extra payout workflow, TDS/GST deductions, InstaPay eligibility, double-entry Dr/Cr vouchers, ledger statements, financial year locking, GST register, and TDS Form 16A register verified. | `VERIFIED_HARDENED` (`036`, `038`, `041`), `VERIFIED_MATCH` (`037`, `039`, `040`, `077`..`079`), `VERIFIED_ENHANCED` (`042`, `080`, `081`) |
| **8. Claims & Endorsements** | `F-17B-043`..`047` | `5` | `Clerk/ClaimEntry.aspx.cs`, `SurveyorMaster.aspx.cs`, `EndorsementEntry.aspx.cs`, `UpdateEntry*.aspx.cs`, `PolicyCancel*.aspx.cs` | `app/api/v1/endpoints/claims_endorsements.py`, `app/services/claim_service.py`, `endorsement_service.py` | `tbl_claim`, `tbl_surveyor`, `tbl_endorsement`, `tbl_policycancel` | Claim intimation, surveyor assignment, endorsement workflow, post-issuance `UpdateEntry` premium/commission delta recalculation, and policy cancellation with commission clawback verified. | `VERIFIED_MATCH` (`043`..`045`), `VERIFIED_HARDENED` (`046`, `047`) |
| **9. Webhook, Renewals, Storage & Integrations** | `F-17B-048`..`055` | `8` | `PolicyParserWebhook.aspx.cs`, `ViewExpiryPolicy.aspx.cs`, `UploadHandler.ashx.cs`, `ShowImage.ashx.cs`, `VehicleService.asmx.cs`, `SendMailToAutority.aspx.cs` | `app/api/v1/endpoints/documents.py`, `renewals.py`, `integrations.py`, `notifications.py` | `tbl_calliber_policy_webhook`, `tbl_documents`, `tbl_vehiclenorc_details`, `tbl_customerhelp`, `tbl_notification_log` | Calliber inbound webhook (HMAC/secret hardened), renewal expiry notices, customer helpdesk, path-traversal-safe local/presigned document storage, 3-tier RC lookup, SMS (Fast2SMS/IndiaText), OneSignal push, and SMTP email verified. | `VERIFIED_HARDENED` (`048`, `051`), `VERIFIED_MATCH` (`050`), `VERIFIED_ENHANCED` (`049`, `052`..`055`) |
| **10. Dashboards, MIS & 8 Crystal Reports** | `F-17B-056`..`065` | `10` | `Clerk/Dashboard*.aspx.cs`, `MIS_*.aspx.cs`, and `8` `.rpt` files (`AgentPaymentInvoice.rpt`, `Payment_Voucher.rpt`, `Rpt_AccountReport.rpt`, `Rpt_CommissionPaid.rpt`, `Rpt_CutNPay.rpt`, `Rpt_PaymentAdvice.rpt`, `Rpt_ViewAgentCommPaidUnpaid.rpt`, `SalesInvoiceReport.rpt`) | `app/api/v1/endpoints/dashboards.py`, `reports.py`, `app/services/dashboard_service.py`, `report_service.py` | `tbl_transaction`, `tbl_account`, `tbl_agentcommissionpayment`, `tbl_target` | Role-scoped KPI dashboards, multi-filter MIS analytics, and all 8 financial/commission Crystal Reports migrated to streaming ReportLab PDF & OpenPyXL Excel exports verified. | `VERIFIED_ENHANCED` (`056`..`065`) |
| **11. Batch Ops, Search, Mobile & Audit Log** | `F-17B-066`..`071`, `082` | `7` | `Clerk/ImportTransaction*.aspx.cs`, `SearchMethods.aspx.cs`, `Service.asmx.cs::AppSelectVersion`, `SelectAppBanner` | `app/api/v1/endpoints/utilities.py`, `search.py`, `admin.py` | `tbl_import_staging`, `tbl_banner`, `tbl_audit_log` | Bulk staging imports, scheduled maintenance tasks, global typeahead search (`SearchMethods`), mobile version gate, banner feed, and immutable audit log verified. | `VERIFIED_ENHANCED` (`066`..`068`), `VERIFIED_MATCH` (`069`..`071`), `VERIFIED_HARDENED` (`082`) |

**Result:** **`82 / 82` `MUST` features independently verified (`0` regressions).**

---

## 6. Part 4 — Phase 18A `SHOULD` Feature Audit (`10 / 10`)

Each of the 10 `SHOULD` features was audited directly against the legacy C# code and the Phase 18A FastAPI implementation:

### 6.1 `F-17B-083` — Outbound HiCaliber Async Policy PDF Upload, Pre-Fill & Transaction Linking
- **Legacy Source Inspected:** `Insurance/Clerk/PE_UploadPolicy.aspx.cs` (`L89–190`: `GetPresignedUrl`, `UploadFileToS3`, `ExtractPolicy` calling `/motor-policy/ext/async/policy-presigned-url/` and `/motor-policy/ext/async/extract-policy/ideal/` with `Authorization: Bearer <token>`), `DAL_PE_Transaction` (`DAL/DAL_Operations.cs` `L24050–24220`: `sp_PE_Getpolicy_identifier`, `sp_pe_Select_Import_PolicyPDFById`, `sp_PE_CheckDuplicateEntry`, `sp_PE_UpdateTransId_bycalliber_policyId`).
- **FastAPI Implementation Inspected:**
  - Routes (`app/api/v1/endpoints/phase18a.py` `L107–161`):
    1. `POST /api/v1/documents/policy-extraction/upload`
    2. `GET /api/v1/documents/policy-extraction/{identifier}/prefill`
    3. `POST /api/v1/documents/policy-extraction/{calliber_policy_id}/link-transaction`
  - Service (`app/services/phase18a_service.py` `L114–388`): Validates `.pdf` extension and non-empty bytes, computes SHA-256 checksum, generates `PE-<hex>` `policy_identifier`, calls `_invoke_hicaliber_extraction` (which uses `httpx.AsyncClient` against `HICALIBER_PRESIGNED_URL` and `HICALIBER_EXTRACT_URL` when `HICALIBER_PROVIDER_TYPE == "http"`, or deterministic extraction in `"mock"` mode), persists `DocumentRecord` (`tbl_documents`) + `PolicyParserWebhookRecord` (`tbl_calliber_policy_webhook`), checks duplicate `Transaction.PolicyNo` (`sp_PE_CheckDuplicateEntry`), serves pre-fill fields by `policy_identifier`/`PolicyNo`/`WebhookEventId`/`CalliberPolicyId`, and links `Transaction.calliber_policyId` + `PolicyParserWebhookRecord.LinkedTransanctionId`.
- **Test Evidence:** `test_f17b_083_policy_pdf_extraction_upload_prefill_and_link` (`tests/test_phase18a_remaining_features.py` `L66–127`) tests 422 non-PDF rejection, 201 upload, duplicate policy detection, 200 prefill lookup, and 200 transaction linking.
- **Audit Verdict:** **`VERIFIED_HARDENED`**.

### 6.2 `F-17B-084` — Extended Operator Lockouts: Pending Cash Lock (Mumbai 3-Day / Default 2-Day) & Pending App Transaction Lock
- **Legacy Source Inspected:** `Insurance/adm_LockCashEntry1.aspx.cs` (`L47–90`: checks `if (BRANCH_ID == 105)` $\rightarrow$ `BLL_LockPendingingPremiumPaymentMumbai(UserName)` with 3-day threshold, else `BLL_LockPendingingPremiumPayment(UserName)` with 2-day threshold), `Insurance/adm_LockPendingTansEntry.aspx.cs`.
- **FastAPI Implementation Inspected:**
  - Routes (`app/api/v1/endpoints/phase18a.py` `L167–210`):
    1. `POST /api/v1/batch-tasks/enforce-pending-cash-locks` (protected by `require_roles(*FINANCE_AND_ADMIN_ROLES)`)
    2. `POST /api/v1/batch-tasks/enforce-pending-app-transaction-locks` (protected by `require_roles(*BACKOFFICE_WRITE_ROLES)`)
    3. `GET /api/v1/batch-tasks/operator-lock-status`
  - Service (`app/services/phase18a_service.py` `L393–524`): Evaluates `Transaction` rows with `OutstandingAmount > 0` or `pendingStatus == 1` against `mumbai_branch_id == 105` (`mumbai_threshold_days = 3`) vs default branches (`default_threshold_days = 2`), and evaluates `TransactionAppNew` rows with `IsOwnerApprove == 0` or `IsAccountApproval == 0`. Locks non-admin offending operators (`u.isdeleted = "1"`) when `apply_user_lock=True`, and leaves `LBR-069` (`UtilityService.enforce_overdue_cheque_locks`) completely untouched.
- **Test Evidence:** `test_f17b_084_pending_cash_and_app_transaction_locks` (`L133–186`).
- **Audit Verdict:** **`VERIFIED_HARDENED`**.

### 6.3 `F-17B-085` — Bulk Ideal / Broker Payment Receipt & Multi-Agent Commission Settlement + InstaPay Request
- **Legacy Source Inspected:** `Insurance/POSP_MultiEntryIdealPayment.aspx.cs` (`L75–120`: iterates CSV rows with `Receipt`, `PaymentDate`, `POSPType_Id`, `POSP_Id`, `Ideal_Amount`, `Ideal_NEFTNo`, `Policy no`, `TransanctionId`, `type` = `Regular` | `Insta`; calls `SaveParent` and `SaveChild` to insert into `tbl_idealpaymentreceipt`, update `tbl_transaction.IB_ReceiptStatus = 1`, `CommissionPaid = 1`, and insert into `tbl_agentcommissionpayment`), `BLL_InstaPay` (`BLL_Operations.cs` `L8910`).
- **FastAPI Implementation Inspected:**
  - Routes (`app/api/v1/endpoints/phase18a.py` `L216–260`):
    1. `POST /api/v1/commission-payouts/ideal-payment-receipts/bulk` (`require_roles(*FINANCE_AND_ADMIN_ROLES)`)
    2. `GET /api/v1/commission-payouts/ideal-payment-receipts`
    3. `POST /api/v1/commission-payouts/instapay/requests`
  - Service (`app/services/phase18a_service.py` `L529–691`): Deduplicates by `Ideal_Doc_No` (`IsDelete == 0`), inserts `IdealPaymentReceipt` (`tbl_idealpaymentreceipt`), updates linked `Transaction` (`IB_PaymentDate`, `IB_ReceiptStatus = 1`, `IB_PaymentBy`, `CommissionPaid = 1`), and creates `AgentCommissionPayment` (`tbl_agentcommissionpayment`) using quantized `Decimal` (`_q2`). Also supports idempotent `InstaPay` request creation (`INSTAPAY-{transaction_id}-{agent_id}`).
- **Test Evidence:** `test_f17b_085_and_090_ideal_receipts_instapay_and_authority_summary` (`L192–252`).
- **Audit Verdict:** **`VERIFIED_HARDENED`**.

### 6.4 `F-17B-086` — Partner Commission Rate Grid Lookup, Bulk Grid CSV Upload & Reliance 90%/60% OD Capping
- **Legacy Source Inspected:** `API/AllMaster.cs` (`API_BrokerCommission`, `API_clusterwisebrokergrid`, `API_clusterwiseAgentgrid`), `BLL/BLL_Operations.cs` (`BLL_Grid` `L9025`, `BLL_Capping` `L7121`), `DAL/DAL_Operations.cs` (`DAL_Capping` `L36743`: `sp_CappingForRelianceCompany`), `Insurance/Web.config` (`RelianceCapping=90`, `RelianceMaxOD=60`).
- **FastAPI Implementation Inspected:**
  - Routes (`app/api/v1/endpoints/phase18a.py` `L266–338`):
    1. `POST /api/v1/commissions/grids` (`require_roles(*BACKOFFICE_WRITE_ROLES)`)
    2. `POST /api/v1/commissions/grids/import-csv` (`require_roles(*FINANCE_AND_ADMIN_ROLES)`)
    3. `GET /api/v1/commissions/grids/lookup`
    4. `POST /api/v1/commissions/capping/reliance-evaluate`
  - Service (`app/services/phase18a_service.py` `L696–839`): Persists `CommissionRateGrid` (`tbl_commission_rate_grid`), supports UTF-8 CSV bulk import, multi-criteria filtering, and deterministic `Decimal` evaluation of Reliance capping (`effective_od = min(od_discount, 60.00)`, `effective_grid = min(grid_percent, max(0.00, 90.00 - effective_od))`, `effective_commission_amount = _q2(od_premium * effective_grid / 100)`).
- **Test Evidence:** `test_f17b_086_commission_grids_and_reliance_capping` (`L278–341`).
- **Audit Verdict:** **`VERIFIED_HARDENED`**.

### 6.5 `F-17B-087` — Remaining / Shortfall Cash Premium Ledger & Cashier Approval
- **Legacy Source Inspected:** `Insurance/adm_LockCashEntry1.aspx.cs` (`L227–268`: `BLL_insertRemainingPendingCash`, `BLL_insertRemainingPremiumAmt`), `BLL_RemainingPendingCash` (`BLL/BLL_Operations.cs` `L7769–7825`: `DAL_SelectCashierApprovalforRemainingCash`).
- **FastAPI Implementation Inspected:**
  - Routes (`app/api/v1/endpoints/phase18a.py` `L375–424`):
    1. `POST /api/v1/payments/remaining-cash`
    2. `GET /api/v1/payments/remaining-cash`
    3. `POST /api/v1/payments/remaining-cash/{pending_cash_id}/approve` (`require_roles(*FINANCE_AND_ADMIN_ROLES)`)
  - Service (`app/services/phase18a_service.py` `L844–957`): Validates `paid_premium <= total_premium`, calculates `RemainingPremium = _q2(total_premium - paid_premium)`, sets status `"Short Fall"` or `"Completed"`, and allows Cashier/Finance roles to approve (`CashierApproval = 1`) or reject (`CashierApproval = 2`) and record additional shortfall payments while preventing overpayment (`new_paid > total_p` $\rightarrow$ `422`).
- **Test Evidence:** `test_f17b_087_remaining_pending_cash_lifecycle` (`L347–396`), including `403` RBAC check on `AGENT` attempting cashier approval and `422` overpayment check (`L891–900`).
- **Audit Verdict:** **`VERIFIED_HARDENED`**.

### 6.6 `F-17B-088` — Insurer B2B Sales Invoice Registration & Company Advance Master Adjustment
- **Legacy Source Inspected:** `API/AllMaster.cs` (`API_salesregistration`), `BLL/BLL_Operations.cs` (`BLL_Loan` `L8094–8149`: `BLL_Insertsalesregistration`, `BLL_SelectCompanyAdvMst`, `BLL_UpdateCompanyAdvMaster`).
- **FastAPI Implementation Inspected:**
  - Routes (`app/api/v1/endpoints/phase18a.py` `L430–480`):
    1. `POST /api/v1/accounting/sales-registrations` (`require_roles(*FINANCE_AND_ADMIN_ROLES)`)
    2. `GET /api/v1/accounting/sales-registrations`
    3. `POST /api/v1/accounting/sales-registrations/{sales_reg_id}/adjust-advance` (`require_roles(*FINANCE_AND_ADMIN_ROLES)`)
  - Service (`app/services/phase18a_service.py` `L962–1087`): Computes `CGSTAmt`, `SGSTAmt`, `IGSTAmt`, `Total`, and `BalanceAmt` with `Decimal` `_q2` quantization; persists `SalesRegistration` (`tbl_salesregistration`); and on advance adjustment validates `received_amount <= BalanceAmt`, updates `ReceivedAmt` and `BalanceAmt`, and posts a corresponding accounting entry in `Account` (`tbl_account` with `PaymentType="ADVANCE_ADJUSTMENT"`).
- **Test Evidence:** `test_f17b_088_and_099_sales_registration_and_office_expenses` (`L402–446`).
- **Audit Verdict:** **`VERIFIED_HARDENED`**.

### 6.7 `F-17B-091` — Vehicle Break-In Inspection Coordinator Request Queue
- **Legacy Source Inspected:** `Insurance/View_InspectionCordinatorRequest.aspx.cs` (`L39–195`), `BLL_InspectionRequest` (`BLL/BLL_Operations.cs`: `BLL_SelectInspectionMsgCount`, `BLL_ViewAppTransactionEntryForInespAllUser`).
- **FastAPI Implementation Inspected:**
  - Routes (`app/api/v1/endpoints/phase18a.py` `L599–658`):
    1. `POST /api/v1/inspections`
    2. `GET /api/v1/inspections`
    3. `GET /api/v1/inspections/pending-count`
    4. `POST /api/v1/inspections/{inspection_id}/decision` (`require_roles(*BACKOFFICE_WRITE_ROLES)`)
  - Service (`app/services/phase18a_service.py` `L1183–1298`): Persists `InspectionCoordinatorRequest` (`tbl_inspectionrequest`), normalizes `RegistrationNo` to uppercase, counts `"PENDING"` requests per branch, and records coordinator decisions (`APPROVED` | `REJECTED` | `DOCUMENTS_REQUIRED`) with `LeadNo`, `InspectionPdfPath`, `ImagePathsJson`, and automatic synchronization to `TransactionAppNew` (`LeadNo`, `IsOwnerApprove = 1`).
- **Test Evidence:** `test_f17b_091_inspection_coordinator_queue_and_decision` (`L479–529`).
- **Audit Verdict:** **`VERIFIED_HARDENED`**.

### 6.8 `F-17B-092` — Internal IT / Operator / Admin Support Ticketing Portal
- **Legacy Source Inspected:** `API/AllMaster.cs` (`API_SupportApp`, `API_SupportAPPFile`), `BLL_SupportPortal` (`BLL/BLL_Operations.cs` `L8840`), `DAL_SupportPortal` (`DAL/DAL_Operations.cs` `L44720–45005`: `sp_Insert_SupportAPP`, `sp_insert_app_Supportremark`, `sp_UpdateAppAttendSupport1`), `Insurance/Clerk/Clerk.Master.cs` (`L45–110`: navbar support badge counts).
- **FastAPI Implementation Inspected:**
  - Routes (`app/api/v1/endpoints/phase18a.py` `L664–754`):
    1. `GET /api/v1/admin/support-tickets/types`
    2. `POST /api/v1/admin/support-tickets`
    3. `GET /api/v1/admin/support-tickets`
    4. `GET /api/v1/admin/support-tickets/counts`
    5. `POST /api/v1/admin/support-tickets/{support_id}/remarks`
    6. `PATCH /api/v1/admin/support-tickets/{support_id}/status` (`require_roles(*BACKOFFICE_WRITE_ROLES)`)
  - Service (`app/services/phase18a_service.py` `L1303–1459`): Persists `SupportTicket` (`tbl_supportapp`), maintains JSON remark threads (`RemarksThreadJson`) with actor (`USER`, `ADMIN`, `IT`, `OPTR`) and timestamp, computes status badge counts (`open_count`, `in_progress_count`, `resolved_count`, `admin_pending_approval_count`), and records attendance/approval metadata (`AttendBy`, `isApproved`, `ApprovedBy`, `ApprovedDate`).
- **Test Evidence:** `test_f17b_092_support_ticketing_portal_lifecycle` (`L535–582`).
- **Audit Verdict:** **`VERIFIED_HARDENED`**.

### 6.9 `F-17B-093` — Telecalling Lead Import, Call Disposition & Follow-Up CRM
- **Legacy Source Inspected:** `API/AllMaster.cs` (`API_CallingImportDatat`), `BLL/BLL_Operations.cs` (`BLL_CallStatus`, `BLL_CallRecord`, `BLL_CallingImportToExcel` `L5050–5139`), `Insurance/Clerk/Calling_CallStatusDetails.aspx.cs` (queue modes `Refresh`, `FollowUp`, `FollowUpToday`, `FollowUpPrev`).
- **FastAPI Implementation Inspected:**
  - Routes (`app/api/v1/endpoints/phase18a.py` `L760–842`):
    1. `GET /api/v1/renewals/telecalling/statuses`
    2. `POST /api/v1/renewals/telecalling/leads/import`
    3. `GET /api/v1/renewals/telecalling/leads` (supports `mode=Refresh|FollowUp|FollowUpToday|FollowUpPrev`)
    4. `POST /api/v1/renewals/telecalling/leads/{calling_import_id}/assign` (`require_roles(*BACKOFFICE_WRITE_ROLES)`)
    5. `POST /api/v1/renewals/telecalling/leads/{calling_import_id}/dispositions`
  - Service (`app/services/phase18a_service.py` `L1464–1604`): Bulk-imports leads into `CallingImportLead` (`tbl_callingimportdata`), assigns telecallers (`UserId`), logs call dispositions with `FollowUpDate` and append-only `HistoryJson`, and filters queues by `FollowUpToday` (`FollowUpDate == today`), `FollowUpPrev` (`FollowUpDate < today`), `FollowUp` (`FollowUpDate IS NOT NULL`), and `Refresh`.
- **Test Evidence:** `test_f17b_093_and_098_telecalling_crm_and_gps_check_in` (`L588–632`).
- **Audit Verdict:** **`VERIFIED_HARDENED`**.

### 6.10 `F-17B-094` — Multi-Insurer Quotation Request & PDF File Sharing Workflow
- **Legacy Source Inspected:** `Insurance/Service.asmx.cs` (`InsertAppRequestedQuotation1` `L13550`, `AppSelectRequestedQuotationfile1` `L13500`), `DAL_Quotation`.
- **FastAPI Implementation Inspected:**
  - Routes (`app/api/v1/endpoints/phase18a.py` `L848–876`):
    1. `POST /api/v1/quotations/requests/{quotation_id}/requested-files`
    2. `GET /api/v1/quotations/requests/{quotation_id}/requested-files`
  - Service (`app/services/phase18a_service.py` `L1609–1663`): Verifies `AppQuotationRequest` (`tbl_app_quotationrequest`) exists and is not deleted, inserts insurer comparison PDF records into `AppRequestedQuotationFile` (`tbl_app_requestedquotationfile`), updates `q_req.IsQuotationGenerate = 1` and `QuotSendDate`, and lists active attached files per quotation request.
- **Test Evidence:** `test_f17b_094_requested_quotation_files_workflow` (`L667–706`).
- **Audit Verdict:** **`VERIFIED_HARDENED`**.

---

## 7. Part 5 — Phase 18A `ENHANCE` Feature Audit (`7 / 7`)

Each of the 7 `ENHANCE` features was audited to verify that legacy business behavior was preserved and modernized (not replaced with unrelated behavior):

### 7.1 `F-17B-089` — Multi-Provider Vehicle RC Adapter Extension (`APIClub`, `Signzy`, `Attestr`)
- **Legacy Source Inspected:** `Insurance/VehicleNoDetails.cs` (`L15–100`: `https://prod.apiclub.in/api/v1/rc_info`), `Insurance/VehicleService.asmx.cs` (`Signzy`), `Insurance/Web.config` (`https://api.attestr.com/api/v1/public/checkx/rc`).
- **FastAPI Implementation Inspected:** `app/providers/attestr.py` (`AttestrRCProvider` implementing `VehicleRCProvider` via `httpx.AsyncClient` with `ATTESTR_BASE_URL` and `ATTESTR_API_KEY`), `app/providers/__init__.py` (`resolve_vehicle_rc_provider` supporting `"mock"`, `"apiclub"`, `"signzy"`, `"attestr"`), `app/api/v1/endpoints/integrations.py` (`GET /api/v1/integrations/vehicle-rc/providers` and optional `provider` selector on `POST /api/v1/integrations/vehicle-rc/lookup`).
- **Test Evidence:** `test_f17b_089_095_096_097_attestr_cashback_targets_and_sub_agents` (`L718–767`).
- **Audit Verdict:** **`VERIFIED_ENHANCED`**.

### 7.2 `F-17B-090` — Automated Daily InstaPay Authority Summary Email / Report (`NEWSUMMERY`, `FROMRA`, `ONLINETORA`)
- **Legacy Source Inspected:** `Insurance/SendMailToAutority.aspx.cs` (`L38–89`: calls `sp_InstapayReport` with `P_opr = "NEWSUMMERY"`, `"FROMRA"`, and `"Online_To_Reliable"`, builds HTML summary tables, renders PDF attachment, and emails authority recipients via SMTP).
- **FastAPI Implementation Inspected:**
  - Routes (`app/api/v1/endpoints/phase18a.py` `L517–544`):
    1. `GET /api/v1/reports/operations/instapay-authority-summary`
    2. `POST /api/v1/reports/operations/instapay-authority-summary/dispatch` (`require_roles(*FINANCE_AND_ADMIN_ROLES)`)
  - Service (`app/services/phase18a_service.py` `L1092–1178`): Aggregates `IdealPaymentReceipt` rows into `new_summary` (`NEWSUMMERY`), `from_ra_summary` (`FROMRA` — InstaPay rows), and `online_to_reliable_summary` (`ONLINETORA` — Regular rows), and dispatches HTML + PDF email via injectable `get_email_provider()`.
- **Test Evidence:** `test_f17b_085_and_090_ideal_receipts_instapay_and_authority_summary` (`L253–272`).
- **Audit Verdict:** **`VERIFIED_ENHANCED`**.

### 7.3 `F-17B-095` — Cashback & Promotional Scheme Entry
- **Legacy Source Inspected:** `API/AllMaster.cs` (`API_cashback`), `BLL/BLL_Operations.cs` (`BLL_CashBackAmount` `L7130`, `BLL_OutStandingAmount.BLL_SelectCashBackAmtReport`), `DAL/DAL_Operations.cs` (`DAL_CashBackAmount` `L36775`: `sp_SelectCashBackAmtReport`).
- **FastAPI Implementation Inspected:**
  - Routes (`app/api/v1/endpoints/phase18a.py` `L340–370`):
    1. `POST /api/v1/commissions/cashbacks` (`require_roles(*BACKOFFICE_WRITE_ROLES)`)
    2. `GET /api/v1/commissions/cashbacks`
  - Service (`app/services/phase18a_service.py` `L1668–1717`): Persists `CashbackEntry` (`tbl_cashback`) with quantized `cashbackamount` and filters by `transaction_id` and `agent_id`.
- **Test Evidence:** `test_f17b_089_095_096_097_attestr_cashback_targets_and_sub_agents` (`L768–783`).
- **Audit Verdict:** **`VERIFIED_ENHANCED`**.

### 7.4 `F-17B-096` — Sales Target vs. Achievement & Contest Reward Tracking
- **Legacy Source Inspected:** `API/AllMaster.cs` (`API_Targetnew`), `BLL/BLL_Operations.cs` (`BLL_Target`), `Insurance/Clerk/Target*.aspx.cs`.
- **FastAPI Implementation Inspected:**
  - Routes (`app/api/v1/endpoints/phase18a.py` `L547–593`):
    1. `POST /api/v1/reports/targets` (`require_roles(*BACKOFFICE_WRITE_ROLES)`)
    2. `PUT /api/v1/reports/targets/{target_id}` (`require_roles(*BACKOFFICE_WRITE_ROLES)`)
    3. `GET /api/v1/reports/targets`
  - Service (`app/services/phase18a_service.py` `L1722–1817`): Persists `Target` (`tbl_target`) and computes `achievement_percent = _q2((achieved_amt * 100) / target_amt)` and contest reward tier (`PLATINUM_CHAMPION` $\ge 125\%$, `GOLD_ACHIEVER` $\ge 100\%$, `SILVER_QUALIFIER` $\ge 75\%$, `IN_PROGRESS` $< 75\%$).
- **Test Evidence:** `test_f17b_089_095_096_097_attestr_cashback_targets_and_sub_agents` (`L784–811`).
- **Audit Verdict:** **`VERIFIED_ENHANCED`**.

### 7.5 `F-17B-097` — Sub-Agent Secondary Hierarchy & Split Payout
- **Legacy Source Inspected:** `Insurance/Clerk/Agent*.aspx.cs`, `BLL_Agent`, `Service.asmx.cs` sub-agent hierarchy methods.
- **FastAPI Implementation Inspected:**
  - Routes (`app/api/v1/endpoints/phase18a.py` `L882–925`):
    1. `POST /api/v1/agents/{agent_id}/sub-agents`
    2. `GET /api/v1/agents/{agent_id}/sub-agents`
    3. `POST /api/v1/agents/{agent_id}/sub-agents/calculate-split`
  - Service (`app/services/phase18a_service.py` `L1822–1908`): Verifies parent `Agent` exists, creates child `Agent` (`tbl_agent`) inheriting branch/executive/franchise with `ParentAgentId` and `SubAgentSplitPercent`, lists sub-agents, and computes exact `Decimal` commission split (`sub_payout = _q2(total_comm * split_pct / 100)`, `parent_retained = _q2(total_comm - sub_payout)`).
- **Test Evidence:** `test_f17b_089_095_096_097_attestr_cashback_targets_and_sub_agents` (`L812–853`).
- **Audit Verdict:** **`VERIFIED_ENHANCED`**.

### 7.6 `F-17B-098` — Field Executive / Agent GPS Check-In & Google Maps Reverse Geocoding
- **Legacy Source Inspected:** `Insurance/Clerk/Location.aspx.cs` (`L48–106`: checks `if (coordinate == "0.0,0.0") { addr = "No Address Found"; }`, otherwise queries `https://maps.googleapis.com/maps/api/geocode/json?latlng=...` and extracts `results[0].formatted_address`), `API/GeoLocationClasses.cs`.
- **FastAPI Implementation Inspected:**
  - Routes (`app/api/v1/endpoints/phase18a.py` `L930–957`):
    1. `POST /api/v1/integrations/geo/check-in`
    2. `GET /api/v1/integrations/geo/check-ins`
  - Service (`app/services/phase18a_service.py` `L1913–2018`): Preserves the exact legacy `(0, 0) -> ("No Address Found", "ZERO_COORDINATE_RULE")` check, supports `httpx.AsyncClient` Google Maps reverse geocoding when `GEOCODE_PROVIDER_TYPE == "google_http"` (with `GOOGLE_MAPS_API_KEY` from config) or deterministic local resolution in `"mock"` mode, and persists `Latitude`, `Longitude`, and `GPSLocation` in `CallingImportLead` (`tbl_callingimportdata`).
- **Test Evidence:** `test_f17b_093_and_098_telecalling_crm_and_gps_check_in` (`L633–661`).
- **Audit Verdict:** **`VERIFIED_ENHANCED`**.

### 7.7 `F-17B-099` — Petty Office Expense & Stationary Voucher Register
- **Legacy Source Inspected:** `API/AllMaster.cs` (`API_Account`), `Insurance/Clerk/Expense*.aspx.cs`.
- **FastAPI Implementation Inspected:**
  - Routes (`app/api/v1/endpoints/phase18a.py` `L483–511`):
    1. `POST /api/v1/accounting/office-expenses` (`require_roles(*BACKOFFICE_WRITE_ROLES)`)
    2. `GET /api/v1/accounting/office-expenses`
  - Service (`app/services/phase18a_service.py` `L2023–2084`): Records petty expense vouchers into `Account` (`tbl_account` with `LedgerMId = 999`, `PaymentType = f"OFFICE_EXPENSE_{payment_mode}"`, `Extra1 = f"{voucher_no}|{expense_category}"`, `Extra2 = vendor_or_payee`) and lists them with optional `branch_id` filtering.
- **Test Evidence:** `test_f17b_088_and_099_sales_registration_and_office_expenses` (`L447–473`).
- **Audit Verdict:** **`VERIFIED_ENHANCED`**.

---

## 8. Part 6 — Database Forensic Audit

Independent inspection of Alembic migration `alembic/versions/b18a0c5d1801_phase_18a_remaining_legacy_features.py`, ORM models in `app/models/phase18a_features.py` & `app/models/profile.py`, and live `SHOW COLUMNS` / `SHOW INDEX` queries on `reliable_insurance_dev` confirmed all **8 new physical tables** (`74 + 8 = 82` total tables) and **2 additive columns** on `tbl_agent`:

| # | Physical Table Name | Primary Key | Column Count | Monetary / Rate Precision | Secondary Indexes Verified in MySQL | Soft-Delete / Status Column | Audit Verdict |
| :---: | :--- | :--- | :---: | :--- | :--- | :--- | :---: |
| 1 | `tbl_idealpaymentreceipt` | `Id` (`INT AUTO_INCREMENT`) | `13` | `Ideal_Amount DECIMAL(15,2)` | `ix_tbl_idealpaymentreceipt_Ideal_Doc_No`, `POSP_Id`, `TransactionId` | `IsDelete INT DEFAULT 0` | **VERIFIED** |
| 2 | `tbl_commission_rate_grid` | `GridId` (`INT AUTO_INCREMENT`) | `26` | `Commission_OD`, `Commission_Net`, `Commission_TP`, `OD_Discount DECIMAL(10,2)` | `ix_tbl_commission_rate_grid_InsComp`, `VehiType`, `BrokerId`, `FranchiseId`, `AgentId` | `isdeleted VARCHAR(10) DEFAULT '0'` | **VERIFIED** |
| 3 | `tbl_remainingpendingcash` | `PendingCashId` (`INT AUTO_INCREMENT`) | `18` | `TotalPremium`, `PaidPremium`, `RemainingPremium`, `ShortfallAmt DECIMAL(15,2)` | `ix_tbl_remainingpendingcash_AgentId`, `ExecutiveId`, `BranchId`, `CashierApproval` | `RemainingStatus`, `CashierApproval INT DEFAULT 0` | **VERIFIED** |
| 4 | `tbl_salesregistration` | `salesRegId` (`INT AUTO_INCREMENT`) | `23` | `amount`, `CGSTAmt`, `SGSTAmt`, `IGSTAmt`, `Total`, `ReceivedAmt`, `BalanceAmt DECIMAL(15,2)`; `CGSTPer`, `SGSTPer`, `IGSTPer DECIMAL(6,2)` | `ix_tbl_salesregistration_InvoiceNo`, `ClientMasterId`, `LedgerMId` | `BalanceAmt` tracking | **VERIFIED** |
| 5 | `tbl_inspectionrequest` | `InspectionId` (`INT AUTO_INCREMENT`) | `21` | N/A | `ix_tbl_inspectionrequest_TransId`, `RegistrationNo`, `BranchId`, `FranchiseId`, `AgentId`, `InspectionStatus` | `InspectionStatus VARCHAR(50) DEFAULT 'PENDING'` | **VERIFIED** |
| 6 | `tbl_supportapp` | `SupportId` (`INT AUTO_INCREMENT`) | `18` | N/A | `ix_tbl_supportapp_UserId`, `BranchId`, `Status` | `Status VARCHAR(50) DEFAULT 'OPEN'`, `isApproved INT DEFAULT 0` | **VERIFIED** |
| 7 | `tbl_callingimportdata` | `CallingImportId` (`INT AUTO_INCREMENT`) | `26` | N/A | `ix_tbl_callingimportdata_RegistrationNo`, `MobileNo`, `UserId`, `BranchId`, `FollowUpDate` | `CallingStatusId`, `CallingStatusName` | **VERIFIED** |
| 8 | `tbl_cashback` | `cashbackId` (`INT AUTO_INCREMENT`) | `12` | `cashbackamount DECIMAL(15,2)` | `ix_tbl_cashback_TransactionId`, `CustomerId`, `AgentId`, `BranchId` | `Status VARCHAR(50) DEFAULT 'APPROVED'` | **VERIFIED** |
| + | `tbl_agent` (Additive) | `AgentId` | `+2` cols | `SubAgentSplitPercent DECIMAL(6,2) DEFAULT 0.00` | `ParentAgentId INT NULL` | `isdeleted VARCHAR(10)` | **VERIFIED** |

- **Reversibility:** `downgrade()` in `b18a0c5d1801_phase_18a_remaining_legacy_features.py` (`L291–302`) cleanly drops `SubAgentSplitPercent`, `ParentAgentId`, and all 8 tables in reverse order.
- **No Redundant Tables:** Existing tables (`tbl_calliber_policy_webhook`, `tbl_documents`, `tbl_app_quotationrequest`, `tbl_app_requestedquotationfile`, `tbl_target`, `tbl_account`, `tbl_agent`, `tbl_vehiclenorc_details`) were reused where already present in the 74-table baseline.

---

## 9. Part 7 — Financial Forensic Audit

Every financial and percentage calculation in Phase 18A (`app/services/phase18a_service.py`) was audited against legacy C# formulas and `Decimal` precision rules:

1. **Quantization Helper (`_q2`, `L96–102`)**:
   - Uses `Decimal(str(val)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)`. Zero `float` arithmetic is used in any calculation.
2. **Bulk Ideal Payment Receipts & InstaPay (`F-17B-085`, `L529–691`)**:
   - Deduplicates by `Ideal_Doc_No` (`IsDelete == 0`) to prevent double settlement (`duplicate_skipped_count`).
   - Updates `Transaction.IB_ReceiptStatus = 1`, `Transaction.CommissionPaid = 1`, and writes `AgentCommissionPayment` with `NetAmount = _q2(item.ideal_amount)`.
   - InstaPay request uses deterministic key `INSTAPAY-{transaction_id}-{agent_id}` for idempotency.
3. **Reliance 90%/60% OD Capping (`F-17B-086`, `L780–813`)**:
   - Matches `Web.config` (`RelianceCapping=90`, `RelianceMaxOD=60`) and `sp_CappingForRelianceCompany`:
     $$\text{eff\_od} = \min(\text{od\_discount}, 60.00), \quad \text{eff\_grid} = \min(\text{grid\_pct}, \max(0.00, 90.00 - \text{eff\_od}))$$
     $$\text{comm\_amt} = \text{round\_half\_up}\left(\frac{\text{od\_premium} \times \text{eff\_grid}}{100.00}, 2\right)$$
4. **Remaining / Shortfall Cash Ledger (`F-17B-087`, `L844–916`)**:
   - Enforces `paid_premium <= total_premium` on creation and `PaidPremium + additional_paid_amount <= TotalPremium` on cashier approval (raising `422` on overpayment).
   - Computes `RemainingPremium = _q2(TotalPremium - PaidPremium)` and transitions `RemainingStatus` from `"Short Fall"` to `"Completed"` only when `RemainingPremium == Decimal("0.00")`.
5. **Insurer B2B Sales Invoice Registration & Advance Adjustment (`F-17B-088`, `L962–1050`)**:
   - Computes `CGSTAmt = _q2(base_amt * cgst_per / 100)`, `SGSTAmt = _q2(base_amt * sgst_per / 100)`, `IGSTAmt = _q2(base_amt * igst_per / 100)`, `Total = _q2(base_amt + CGSTAmt + SGSTAmt + IGSTAmt)`, and initializes `BalanceAmt = Total`.
   - On advance adjustment (`adjust_sales_registration_advance`), enforces `received_amount <= BalanceAmt` (`422` if exceeded), increments `ReceivedAmt`, decrements `BalanceAmt`, and posts an `Account` (`tbl_account`) voucher row in the same DB transaction.
6. **Sales Target Achievement % (`F-17B-096`, `L1781–1817`)**:
   - Guards against division by zero (`target_amt > 0`), computes `achievement_percent = _q2((achieved_amt * 100) / target_amt)`.
7. **Sub-Agent Commission Split (`F-17B-097`, `L1884–1908`)**:
   - Computes `sub_payout = _q2(total_comm * split_pct / 100)` and `parent_retained = _q2(total_comm - sub_payout)` so that `sub_payout + parent_retained == total_comm` with zero rounding drift.

---

## 10. Part 8 — Security / RBAC / IDOR Audit

- **Authentication:** 100% of the 51 new Phase 18A endpoints require `current_user: User = Depends(get_current_user)`. Unauthenticated requests return `401 Unauthorized` (verified across 9 endpoints in `test_phase18a_unauthenticated_and_validation_guards`).
- **Role-Based Access Control (RBAC):**
  - **Finance & Admin Only (`FINANCE_AND_ADMIN_ROLES`: `OWNER`, `ADMIN`, `IT SUPPORT`, `ACCOUNT`, `ACCOUNT HEAD`, `CASHIER`)**:
    - `POST /api/v1/batch-tasks/enforce-pending-cash-locks`
    - `POST /api/v1/commission-payouts/ideal-payment-receipts/bulk`
    - `POST /api/v1/commissions/grids/import-csv`
    - `POST /api/v1/payments/remaining-cash/{pending_cash_id}/approve`
    - `POST /api/v1/accounting/sales-registrations`
    - `POST /api/v1/accounting/sales-registrations/{sales_reg_id}/adjust-advance`
    - `POST /api/v1/reports/operations/instapay-authority-summary/dispatch`
  - **Back-Office Write Roles (`BACKOFFICE_WRITE_ROLES`: adds `OPERATOR`, `OPERATOR HEAD`, `SUPERVISOR`, `MANAGER`)**:
    - `POST /api/v1/batch-tasks/enforce-pending-app-transaction-locks`
    - `POST /api/v1/commissions/grids`
    - `POST /api/v1/commissions/cashbacks`
    - `POST /api/v1/accounting/office-expenses`
    - `POST /api/v1/reports/targets`
    - `PUT /api/v1/reports/targets/{target_id}`
    - `POST /api/v1/inspections/{inspection_id}/decision`
    - `PATCH /api/v1/admin/support-tickets/{support_id}/status`
    - `POST /api/v1/renewals/telecalling/leads/{calling_import_id}/assign`
- **Observation (`FIND-18B-002`, `P3`)**: Partner/operator-accessible endpoints such as `POST /api/v1/agents/{agent_id}/sub-agents`, `POST /api/v1/quotations/requests/{quotation_id}/requested-files`, and `POST /api/v1/admin/support-tickets/{support_id}/remarks` require authentication (`get_current_user`) and validate target record existence (`404`), which is already a major security upgrade over legacy's unauthenticated ASMX WebMethods. Adding fine-grained principal ownership checks (e.g., verifying `current_user` owns `agent_id` when called by an `AGENT` role) is documented as a `P3` defense-in-depth item.

---

## 11. Part 9 — Input Validation Audit

All 21 request models in `app/schemas/phase18a.py` and `VehicleRCLookupRequest` in `app/schemas/integrations.py` were inspected:
- **`ConfigDict(extra="forbid")`**: Present on **21 / 21 (`100%`)** request schemas in `app/schemas/phase18a.py`. Unknown payload keys are rejected with `422 Unprocessable Entity` (verified in `test_phase18a_unauthenticated_and_validation_guards` `L879–888`).
- **Monetary & Rate Bounds**:
  - Percentages (`commission_od`, `commission_net`, `commission_tp`, `od_discount`, `grid_percent`, `od_discount_percent`, `split_percent`, `override_split_percent`) enforce `ge=Decimal("0.00"), le=Decimal("100.00")`.
  - Tax rates (`cgst_per`, `sgst_per`, `igst_per`) enforce `ge=Decimal("0.00"), le=Decimal("28.00")`.
  - Monetary amounts enforce `gt=Decimal("0.00")` or `ge=Decimal("0.00")`.
  - Geo coordinates enforce `latitude` in `[-90.0, 90.0]` and `longitude` in `[-180.0, 180.0]` (which explicitly permits `(0.0, 0.0)` so the legacy `"No Address Found"` rule works without breaking valid check-ins).
- **Enum / Pattern Constraints**: `receipt_type` (`^(Regular|Insta)$`), `grid_scope` (`^(BROKER|AGENT|FRANCHISE|CLUSTER)$`), `cal_on` (`^(OD|NET|TP)$`), `decision` (`^(APPROVED|REJECTED|DOCUMENTS_REQUIRED)$`), `remark_from` (`^(USER|ADMIN|IT|OPTR)$`), `status` (`^(OPEN|IN_PROGRESS|RESOLVED|CLOSED)$`), `expense_category`, and `payment_mode` are all pattern-validated.

---

## 12. Part 10 — Integration Forensic Audit

| External Integration | Adapter / Method | Config Settings (`app/core/config.py`) | Default Mode | Timeout & Error Handling | Production Network Calls in Tests? |
| :--- | :--- | :--- | :---: | :--- | :---: |
| **Attestr Vehicle RC (`F-17B-089`)** | `AttestrRCProvider` (`app/providers/attestr.py`) | `ATTESTR_BASE_URL`, `ATTESTR_API_KEY` | `RC_PROVIDER_TYPE="mock"` | `httpx.AsyncClient(timeout=10.0)`, handles `404` $\rightarrow$ `None`, `raise_for_status()` | **ZERO** (Mock provider + monkeypatched `httpx` unit test) |
| **APIClub & Signzy RC (`F-17B-052`, `089`)** | `APIClubRCProvider`, `SignzyRCProvider` | `RC_BASE_URL`, `RC_API_KEY`, `SIGNZY_BASE_URL`, `SIGNZY_API_KEY` | `RC_PROVIDER_TYPE="mock"` | `httpx.AsyncClient`, 3-tier cache fallback in `VehicleRCService` | **ZERO** |
| **HiCaliber Policy OCR (`F-17B-083`)** | `Phase18AService._invoke_hicaliber_extraction` | `HICALIBER_PROVIDER_TYPE`, `HICALIBER_PRESIGNED_URL`, `HICALIBER_EXTRACT_URL`, `HICALIBER_API_TOKEN` | `"mock"` | `httpx.AsyncClient(timeout=15.0)` when `"http"`, deterministic local extraction in `"mock"` | **ZERO** |
| **Google Maps Geocoder (`F-17B-098`)** | `Phase18AService._resolve_reverse_geocode` | `GEOCODE_PROVIDER_TYPE`, `GOOGLE_MAPS_GEOCODE_URL`, `GOOGLE_MAPS_API_KEY` | `"mock"` | `(0,0)` short-circuits before network; `httpx.AsyncClient(timeout=10.0)` when `"google_http"` | **ZERO** |
| **SMTP Authority Email (`F-17B-090`)** | `get_email_provider()` (`MockEmailProvider` / `SMTPEmailProvider`) | `EMAIL_PROVIDER_TYPE="mock"` | `"mock"` | Captures HTML + PDF attachment in memory during tests | **ZERO** |

**Hardcoded Secret Check:** Zero legacy secrets (`SECRET_PRESENT_IN_LEGACY_SOURCE` in `VehicleNoDetails.cs` L24, `Location.aspx.cs` L65, `PE_UploadPolicy.aspx.cs`, `Web.config`) exist anywhere in `app/`, `alembic/`, or `tests/`.

---

## 13. Part 11 — Report / File / Document Audit

- **Policy PDF Upload (`F-17B-083`)**:
  - Validates `.pdf` extension (`L122`) and non-empty payload (`L128`), returning `422` on invalid uploads.
  - Generates UUID-prefixed storage keys (`PolicyPdf/YYYY/MM/DD/PE-<uuid>_<filename>`) and SHA-256 checksums (`ChecksumSha256`), preventing path traversal and duplicate collisions.
  - Links `DocumentRecord.DocumentId` to `PolicyParserWebhookRecord.DocumentId` and `Transaction.calliber_policyId`.
- **Requested Quotation Files (`F-17B-094`)**:
  - Verifies parent `AppQuotationRequest` (`tbl_app_quotationrequest`) exists and is active before recording `AppRequestedQuotationFile` (`tbl_app_requestedquotationfile`).
- **No Legacy PII Exposure**: Zero files from `./InsurancefinalNew_2026_09_23/InsurancefinalNew/Insurance/PolicyDoc/` or other legacy upload folders are exposed or copied.

---

## 14. Part 12 — API Contract Audit

All **51 new `APIRoute` endpoints** (`50` in `app/api/v1/endpoints/phase18a.py` + `1` in `app/api/v1/endpoints/integrations.py`) were inspected:
- **Router Mounting Order (`app/api/v1/router.py`)**: All 13 Phase 18A domain routers (`quotations_p18a_router`, `payments_p18a_router`, `commissions_p18a_router`, `commission_payouts_p18a_router`, `accounting_p18a_router`, `documents_p18a_router`, `integrations_p18a_router`, `renewals_p18a_router`, `reports_p18a_router`, `agents_p18a_router`, `batch_tasks_p18a_router`, `inspections_p18a_router`, `admin_p18a_router`) are mounted before wildcard/parameterized routes in their respective domain prefixes, preventing route shadowing.
- **Status Codes & Response Models**:
  - Resource creation endpoints return `201 Created` (`POST /policy-extraction/upload`, `/ideal-payment-receipts/bulk`, `/instapay/requests`, `/grids`, `/grids/import-csv`, `/cashbacks`, `/remaining-cash`, `/sales-registrations`, `/office-expenses`, `/targets`, `/inspections`, `/support-tickets`, `/telecalling/leads/import`, `/requested-files`, `/{agent_id}/sub-agents`, `/geo/check-in`).
  - Query, evaluation, decision, and status transition endpoints return `200 OK`.
  - Zero duplicate or conflicting `(path, method)` pairs exist across the entire 304-endpoint API surface.

---

## 15. Part 13 — Test Quality Audit

Inspection of `tests/test_phase18a_remaining_features.py` (`902` lines, `12` async test functions):
- **Real HTTP + Real MySQL Persistence**: All 12 tests use `httpx.AsyncClient` against the full FastAPI ASGI app and persist/query rows in `reliable_insurance_dev` via `AsyncSession`.
- **Negative, Validation & RBAC Coverage**:
  - `401 Unauthorized` tested across 9 endpoints (`L863–875`).
  - `403 Forbidden` tested on `AGENT` attempting cashier approval of remaining cash (`L374–379`).
  - `422 Unprocessable Entity` tested on non-PDF upload (`L79–85`), `extra="forbid"` unknown field (`L879–888`), and `paid_premium > total_premium` (`L891–900`).
  - Idempotency / duplicate handling tested on `IdealPaymentReceipt` bulk upload (`L200–236`) and duplicate policy number pre-fill detection (`L70–116`).
- **Test Quality Classification**: **`STRONG`**.

---

## 16. Part 14 — Regression Test Results

Full test suite execution in background task `task-9928` (`python -m pytest -q`):
```text
........................................................................ [ 17%]
........................................................................ [ 34%]
........................................................................ [ 51%]
........................................................................ [ 68%]
........................................................................ [ 85%]
...............................................................          [100%]
423 passed in 256.20s (0:04:16)
```
- **Baseline Tests (Phases 1–16B):** `411 / 411 PASSED`
- **Phase 18A Tests (`tests/test_phase18a_remaining_features.py`):** `12 / 12 PASSED`
- **Total:** **`423 / 423 PASSED` (`0` failed, `0` skipped, `0` errors)**

---

## 17. Part 15 — `LBR-069` Freeze Verification

- **File Inspected:** `app/services/utility_service.py` (`L361–400`: `UtilityService.enforce_overdue_cheque_locks`).
- **Git Diff Verification:** `git diff --stat app/services/utility_service.py` returned **empty (`0` bytes changed)** against baseline commit `481b591db581ffd4225f3b4385ac91fe04101305`.
- **Verdict:** **`UNTOUCHED` (100% compliant with freeze rule).**

---

## 18. Part 16 — `UNKNOWN` Audit (`6` Preserved Groups)

Phase 18A resolved `F-17B-118` (`InsuranceAppService`) to `OBSOLETE` using local `Reference.cs` (`L1–356`), `service.wsdl`, and `ImageHandler.ashx.cs` (`L16`), leaving **6 `UNKNOWN` groups** (`F-17B-114`, `115`, `116`, `117`, `119`, `120`):

| Feature ID | UNKNOWN Description | Evidence Available Locally | Evidence Missing Locally | Fabricated Code in Phase 18A? | Production Workflow Impact |
| :--- | :--- | :--- | :--- | :---: | :--- |
| `F-17B-114` | Exact SQL body of `sp_UpdateTrans` (`GAP-UNK-07-001`) | Full C# parameter list in `DAL_Operations.cs` (`DAL_Transaction`) & `tbl_transaction` DDL | Unexported MySQL `ROUTINE_DEFINITION` | **NONE (`0`)** | **Non-blocking**: Transaction update is implemented from the verified C# DAL parameter contract (`Phase 7`). |
| `F-17B-115` | Unextracted SQL bodies of Wallet/Cheque/Commission helper SPs (`GAP-UNK-08-001`..`09-001`) | C# caller signatures in `DAL_Wallet`, `DAL_ChequeDetails`, `DAL_Commission` + `1,002` unreferenced SP names in `04_STORED_PROCEDURES.md` | Unexported MySQL `ROUTINE_DEFINITION` | **NONE (`0`)** | **Non-blocking**: Active wallet, cheque, and commission workflows are implemented with `SELECT ... FOR UPDATE` (`Phases 8–9`). |
| `F-17B-116` | Unextracted SQL bodies of Endorsement/Claim/Master helper SPs (`GAP-UNK-10-001`..`002`, `UNK-P4-01`..`04`) | C# call sites in `DAL_UpdateEntry`, `DAL_Claims`, `DAL_Operations.cs` | Unexported MySQL `ROUTINE_DEFINITION` | **NONE (`0`)** | **Non-blocking**: Active endorsement, claim, and master CRUD workflows are migrated (`Phases 6, 10`). |
| `F-17B-117` | Exact SQL body of `sp_PE_Update_Extraction_new` (`GAP-UNK-11-001`) & rating helper SPs | Complete 59-parameter C# call site in `PolicyParserWebhook.aspx.cs` (`L20–145`) and `DAL_Operations.cs` (`L24107`) | Unexported MySQL `ROUTINE_DEFINITION` | **NONE (`0`)** | **Non-blocking**: All 59 fields are persisted and linked in `PolicyParserWebhookRecord` (`Phases 11, 18A`). |
| `F-17B-119` | Unextracted SQL bodies of remaining `sp_*` procedures (`GAP-UNK-12-001`..`16-002`) | C# `MySqlCommand` parameter bindings and `P_opr` flags in `DAL_Operations.cs` | Unexported MySQL `ROUTINE_DEFINITION` | **NONE (`0`)** | **Non-blocking**: All active C#-referenced operations are covered by FastAPI services (`Phases 12–18A`). |
| `F-17B-120` | `18` unreferenced auxiliary tables in 92-table legacy catalog (`GAP-UNK-17-002`) | Table names listed in `03_schema_intelligence.md`; **zero** C# references across all `1,277` `.cs` files | `CREATE TABLE` column DDL | **NONE (`0`)** | **Zero impact**: Never queried or written by any C# code in the legacy solution. |

---

## 19. Part 17 — Legacy `OBSOLETE` Audit (`15` Verified Groups)

Each of the **15 `OBSOLETE` feature groups** (`F-17B-100`..`113` + `F-17B-118`) was audited to ensure no active insurance business capability was lost:

| Feature ID | Legacy Artifact | Obsolete Technology / Dead Code vs. Business Capability Analysis | Audit Verdict |
| :--- | :--- | :--- | :---: |
| `F-17B-100` | `Clerk/HR_*.aspx.cs`, `Rpt_SalarySlipMonthly.rpt` | Non-insurance internal HR biometric/wage slip module retired by scope decision. | **`OBSOLETE` (Verified)** |
| `F-17B-101` | `Site.Master.cs`, `Clerk.Master.cs`, `ViewState`, `Session` | Obsolete ASP.NET WebForms UI state technology; navigation & auth capabilities are migrated in `F-17B-001`..`006` & `F-17B-091`..`092`. | **`OBSOLETE` (Verified)** |
| `F-17B-102` | `CrystalDecisions.*` binary `.rpt` runtime | Obsolete reporting engine technology; all **8 active financial/commission reports** are migrated in `F-17B-058`..`065` via ReportLab PDF & OpenPyXL Excel. | **`OBSOLETE` (Verified)** |
| `F-17B-103` | Plaintext passwords & unauthenticated ASMX SOAP transport | Obsolete/insecure transport; all active business operations are migrated with JWT + Argon2/bcrypt in `F-17B-001`..`098`. | **`OBSOLETE` (Verified)** |
| `F-17B-104` | `ShowEventCalender.aspx.cs` (`"Rakhi's bday"`, `"Brazil Vs. France"`) | Copy-pasted C# Corner tutorial sample code with hardcoded strings. | **`OBSOLETE` (Verified)** |
| `F-17B-105` | `adm_renamePolicyDoc.aspx.cs` | 54-line one-off local folder rename script (`"_"` $\rightarrow$ `"B"`). | **`OBSOLETE` (Verified)** |
| `F-17B-106` | `20` commented `[WebMethod]`s in `Service.asmx.cs` + `1` in `MIS_RequestExective.aspx.cs` | Commented-out duplicate methods whose active twins in the same files are 100% migrated (`GAP-UNK-17-001` resolved). | **`OBSOLETE` (Verified)** |
| `F-17B-107` | `WebForm1..5.aspx.cs`, `DemoRC.aspx.cs`, `PDFTesting.aspx.cs` | Developer sandbox/scratch pages. | **`OBSOLETE` (Verified)** |
| `F-17B-108` | `Clerk/rpt_ViewAgentGrid.aspx.cs` (`2,403` commented lines) + `14` empty `Page_Load` stubs | 100% commented-out or empty code-behind files with zero executable logic. | **`OBSOLETE` (Verified)** |
| `F-17B-109` | `pdF_ExtractionDemo_new.aspx.cs` (`permute.in` prototype) | Early OCR prototype superseded by HiCaliber (`F-17B-048`, `F-17B-083`). | **`OBSOLETE` (Verified)** |
| `F-17B-110` | `OpenAI_API_Key` in `Web.config` | Unreferenced config key (`0` occurrences across all `1,277` `.cs` and `1,240` `.aspx` files). | **`OBSOLETE` (Verified)** |
| `F-17B-111` | `vngsms.com` URL in `Web.config` | Deprecated non-DLT SMS gateway superseded by Fast2SMS / IndiaText (`F-17B-053`). | **`OBSOLETE` (Verified)** |
| `F-17B-112` | `BLL_FakeDashBoard` / `sp_FakeDashboard` | Synthetic mock dashboard generator superseded by real KPI dashboards (`F-17B-056`). | **`OBSOLETE` (Verified)** |
| `F-17B-113` | `*_bkp*`, `*_old*`, `temp_*` DB tables | Point-in-time DBA backup and temp tables. | **`OBSOLETE` (Verified)** |
| `F-17B-118` | `InsuranceAppService` (`http://103.76.254.139:85/Service.asmx`) | `Reference.cs` defines `check_login`, `insertPolicy`, `UploadPolicyImages`, `GetImageFile`. Only caller in `ImageHandler.ashx.cs` L16 is commented out (`//InsuranceAppService.Service ws = ...`), and all 4 business operations are superseded by `Service.asmx.cs` and migrated in FastAPI (`F-17B-001`, `022`, `027`, `051`). | **`OBSOLETE` (Verified)** |

---

## 20. Part 18 — Cross-Module Dependency Audit

Phase 18A cross-module interactions with existing Phases 5–16B tables were verified:
1. **`F-17B-083` $\leftrightarrow$ `tbl_documents`, `tbl_calliber_policy_webhook`, `tbl_transaction`**: Uploads create `DocumentRecord` and `PolicyParserWebhookRecord` rows and update `Transaction.calliber_policyId` and `calliber_UpdateBy` without breaking Phase 11 webhook endpoints.
2. **`F-17B-084` $\leftrightarrow$ `tbl_transaction`, `tbl_transactionappnew`, `tbl_user`**: Evaluates pending cash and app transactions and sets `User.isdeleted = "1"` on non-admin users without modifying `LBR-069`.
3. **`F-17B-085` $\leftrightarrow$ `tbl_transaction`, `tbl_agentcommissionpayment`**: Updates `IB_ReceiptStatus = 1`, `CommissionPaid = 1` on `Transaction` and inserts `AgentCommissionPayment` rows compatible with Phase 9 commission reports.
4. **`F-17B-088` & `F-17B-099` $\leftrightarrow$ `tbl_account`**: Inserts `ADVANCE_ADJUSTMENT` and `OFFICE_EXPENSE_*` rows into `tbl_account` with all non-null columns (`isdeleted=0`, `IsNill=0`, `TransactionId=0`, `CustVehId=0`, `EndorsementId=0`, `TransId=0`) populated cleanly.
5. **`F-17B-091` $\leftrightarrow$ `tbl_transactionappnew`**: Coordinator approval syncs `LeadNo` and `IsOwnerApprove = 1` on `TransactionAppNew`.
6. **`F-17B-094` $\leftrightarrow$ `tbl_app_quotationrequest`, `tbl_app_requestedquotationfile`**: Attaching a quotation PDF sets `IsQuotationGenerate = 1` and `QuotSendDate` on `AppQuotationRequest`.
7. **`F-17B-096` $\leftrightarrow$ `tbl_target`**: Reuses the existing `Target` model (`app/models/report.py`) without table duplication.
8. **`F-17B-097` $\leftrightarrow$ `tbl_agent`**: Uses additive nullable columns `ParentAgentId` and `SubAgentSplitPercent` on `Agent` (`app/models/profile.py`), preserving 100% backward compatibility with all existing Phase 15B agent tests.

---

## 21. Part 19 — Route / Model / Service Duplication Audit

- **Routes:** Checked all `304` `APIRoute` endpoints in `app.main:app`. Zero duplicate `(path, http_method)` combinations exist. Phase 18A endpoints extend existing prefixes (`/documents/policy-extraction/*`, `/batch-tasks/enforce-pending-cash-locks`, `/commission-payouts/ideal-payment-receipts/*`, `/commissions/grids/*`, `/payments/remaining-cash/*`, `/accounting/sales-registrations/*`, `/reports/operations/instapay-authority-summary`, `/inspections/*`, `/admin/support-tickets/*`, `/renewals/telecalling/*`, `/quotations/requests/{id}/requested-files`, `/agents/{id}/sub-agents/*`, `/integrations/geo/*`, `/integrations/vehicle-rc/providers`) without colliding with any Phase 5–16B route.
- **Models:** Checked all `82` SQLAlchemy table models in `Base.metadata.tables`. Each of the 8 new models in `app/models/phase18a_features.py` maps to a distinct legacy table not previously modeled, while existing tables (`Target`, `Account`, `Agent`, `AppQuotationRequest`, `AppRequestedQuotationFile`, `DocumentRecord`, `PolicyParserWebhookRecord`) were reused directly.
- **Providers:** `AttestrRCProvider` (`app/providers/attestr.py`) implements the existing `VehicleRCProvider` interface (`app/providers/base.py`) alongside `APIClubRCProvider` and `SignzyRCProvider`.

---

## 22. Part 20 — Source-to-Code Traceability (`17 / 17` Phase 18A Features)

| Feature ID | Type | Legacy Source File(s) & Symbols | Business Rule Extracted | FastAPI Service Method(s) (`Phase18AService`) | FastAPI Route(s) (`/api/v1/...`) | Physical DB Table(s) | Automated Test Function (`tests/test_phase18a_remaining_features.py`) | Traceability Verdict |
| :--- | :---: | :--- | :--- | :--- | :--- | :--- | :--- | :---: |
| **`F-17B-083`** | `SHOULD` | `Clerk/PE_UploadPolicy.aspx.cs` L89–190, `DAL_PE_Transaction` (`sp_PE_Getpolicy_identifier`, `sp_pe_Select_Import_PolicyPDFById`, `sp_PE_CheckDuplicateEntry`, `sp_PE_UpdateTransId_bycalliber_policyId`) | Upload `.pdf` to HiCaliber OCR, stage 59 fields, detect duplicate `PolicyNo` in `tbl_transaction`, serve pre-fill payload, and link `calliber_policyId` to `TransanctionId`. | `upload_and_extract_policy_pdf`, `_invoke_hicaliber_extraction`, `get_policy_extraction_prefill`, `link_extraction_to_transaction` | `POST /documents/policy-extraction/upload`<br>`GET /documents/policy-extraction/{identifier}/prefill`<br>`POST /documents/policy-extraction/{calliber_policy_id}/link-transaction` | `tbl_calliber_policy_webhook`, `tbl_documents`, `tbl_transaction` | `test_f17b_083_policy_pdf_extraction_upload_prefill_and_link` (`L66–127`) | **`VERIFIED_HARDENED`** |
| **`F-17B-084`** | `SHOULD` | `adm_LockCashEntry1.aspx.cs` L47–90 (`BRANCH_ID == 105`), `adm_LockPendingTansEntry.aspx.cs`, `BLL_LockPendingingPremiumPaymentMumbai` | Lock operators with unsettled cash policies older than 3 days (Mumbai Branch `105`) or 2 days (all other branches), or unapproved mobile app transactions. | `enforce_pending_cash_locks`, `enforce_pending_app_transaction_locks`, `get_operator_lock_status` | `POST /batch-tasks/enforce-pending-cash-locks`<br>`POST /batch-tasks/enforce-pending-app-transaction-locks`<br>`GET /batch-tasks/operator-lock-status` | `tbl_transaction`, `tbl_transactionappnew`, `tbl_user` | `test_f17b_084_pending_cash_and_app_transaction_locks` (`L133–186`) | **`VERIFIED_HARDENED`** |
| **`F-17B-085`** | `SHOULD` | `POSP_MultiEntryIdealPayment.aspx.cs` L75–120, `API_IdealPaymentReceipt`, `DAL_IdealPaymentReceipt`, `BLL_InstaPay` | Idempotently import Ideal/broker payment receipts (`Regular` / `Insta`), mark `Transaction.IB_ReceiptStatus=1` & `CommissionPaid=1`, and create `AgentCommissionPayment`. | `process_bulk_ideal_payment_receipts`, `list_ideal_payment_receipts`, `create_instapay_request` | `POST /commission-payouts/ideal-payment-receipts/bulk`<br>`GET /commission-payouts/ideal-payment-receipts`<br>`POST /commission-payouts/instapay/requests` | `tbl_idealpaymentreceipt`, `tbl_agentcommissionpayment`, `tbl_transaction` | `test_f17b_085_and_090_ideal_receipts_instapay_and_authority_summary` (`L192–252`) | **`VERIFIED_HARDENED`** |
| **`F-17B-086`** | `SHOULD` | `API_BrokerCommission`, `BLL_Grid` L9025, `BLL_Capping` L7121, `DAL_Capping` L36743 (`sp_CappingForRelianceCompany`), `Web.config` (`90`/`60`) | Store/import partner commission rate grids by insurer/vehicle/scope and enforce Reliance 60% max OD discount & 90% combined `grid + od_discount` cap. | `create_commission_rate_grid`, `import_commission_grids_csv`, `lookup_commission_rate_grids`, `evaluate_reliance_capping` | `POST /commissions/grids`<br>`POST /commissions/grids/import-csv`<br>`GET /commissions/grids/lookup`<br>`POST /commissions/capping/reliance-evaluate` | `tbl_commission_rate_grid` | `test_f17b_086_commission_grids_and_reliance_capping` (`L278–341`) | **`VERIFIED_HARDENED`** |
| **`F-17B-087`** | `SHOULD` | `adm_LockCashEntry1.aspx.cs` L227–268, `API_RemainingPendingCash`, `BLL_RemainingPendingCash` L7769–7825 | Track partial cash premium collection (`TotalPremium - PaidPremium = RemainingPremium`) and require Cashier approval (`CashierApproval=1`) to settle shortfall. | `create_remaining_pending_cash`, `approve_remaining_pending_cash`, `list_remaining_pending_cash` | `POST /payments/remaining-cash`<br>`GET /payments/remaining-cash`<br>`POST /payments/remaining-cash/{pending_cash_id}/approve` | `tbl_remainingpendingcash` | `test_f17b_087_remaining_pending_cash_lifecycle` (`L347–396`) | **`VERIFIED_HARDENED`** |
| **`F-17B-088`** | `SHOULD` | `API_salesregistration`, `BLL_Loan` L8094–8149 (`BLL_Insertsalesregistration`, `BLL_UpdateCompanyAdvMaster`) | Register B2B insurer brokerage invoice with CGST/SGST/IGST and adjust invoice `BalanceAmt` against insurer advance receipt in `tbl_account`. | `create_sales_registration`, `adjust_sales_registration_advance`, `list_sales_registrations` | `POST /accounting/sales-registrations`<br>`GET /accounting/sales-registrations`<br>`POST /accounting/sales-registrations/{sales_reg_id}/adjust-advance` | `tbl_salesregistration`, `tbl_account` | `test_f17b_088_and_099_sales_registration_and_office_expenses` (`L402–446`) | **`VERIFIED_HARDENED`** |
| **`F-17B-091`** | `SHOULD` | `View_InspectionCordinatorRequest.aspx.cs` L39–195, `BLL_InspectionRequest` (`sp_SelectInspectionMsgCount`) | Queue vehicle break-in inspection requests, expose pending badge count, and record coordinator decision (`APPROVED`/`REJECTED`/`DOCUMENTS_REQUIRED`) syncing `LeadNo` to `TransactionAppNew`. | `create_inspection_request`, `list_inspection_requests`, `get_pending_inspection_count`, `decide_inspection_request` | `POST /inspections`<br>`GET /inspections`<br>`GET /inspections/pending-count`<br>`POST /inspections/{inspection_id}/decision` | `tbl_inspectionrequest`, `tbl_transactionappnew` | `test_f17b_091_inspection_coordinator_queue_and_decision` (`L479–529`) | **`VERIFIED_HARDENED`** |
| **`F-17B-092`** | `SHOULD` | `API_SupportApp`, `BLL_SupportPortal` L8840, `DAL_SupportPortal` L44720 (`sp_Insert_SupportAPP`, `sp_insert_app_Supportremark`, `sp_UpdateAppAttendSupport1`) | Internal IT/Operator/Admin support ticket lifecycle with threaded remarks, role badge counts, and status/approval resolution. | `create_support_ticket`, `add_support_ticket_remark`, `update_support_ticket_status`, `list_support_tickets`, `get_support_ticket_counts` | `GET /admin/support-tickets/types`<br>`POST /admin/support-tickets`<br>`GET /admin/support-tickets`<br>`GET /admin/support-tickets/counts`<br>`POST /admin/support-tickets/{support_id}/remarks`<br>`PATCH /admin/support-tickets/{support_id}/status` | `tbl_supportapp` | `test_f17b_092_support_ticketing_portal_lifecycle` (`L535–582`) | **`VERIFIED_HARDENED`** |
| **`F-17B-093`** | `SHOULD` | `API_CallingImportDatat`, `BLL_CallingImportToExcel` L5050–5139, `Clerk/Calling_CallStatusDetails.aspx.cs` | Bulk import RTO/telecalling leads, assign to telecallers, record dispositions & `FollowUpDate`, and filter by `Refresh`, `FollowUp`, `FollowUpToday`, `FollowUpPrev`. | `import_calling_leads`, `assign_calling_lead`, `record_calling_disposition`, `list_calling_leads` | `GET /renewals/telecalling/statuses`<br>`POST /renewals/telecalling/leads/import`<br>`GET /renewals/telecalling/leads`<br>`POST /renewals/telecalling/leads/{calling_import_id}/assign`<br>`POST /renewals/telecalling/leads/{calling_import_id}/dispositions` | `tbl_callingimportdata` | `test_f17b_093_and_098_telecalling_crm_and_gps_check_in` (`L588–632`) | **`VERIFIED_HARDENED`** |
| **`F-17B-094`** | `SHOULD` | `Service.asmx.cs` (`InsertAppRequestedQuotation1` L13550, `AppSelectRequestedQuotationfile1` L13500), `DAL_Quotation` | Attach insurer quote comparison PDFs to an agent's `AppQuotationRequest` (`IsQuotationGenerate=1`) and list files for mobile download. | `attach_requested_quotation_file`, `list_requested_quotation_files` | `POST /quotations/requests/{quotation_id}/requested-files`<br>`GET /quotations/requests/{quotation_id}/requested-files` | `tbl_app_requestedquotationfile`, `tbl_app_quotationrequest` | `test_f17b_094_requested_quotation_files_workflow` (`L667–706`) | **`VERIFIED_HARDENED`** |
| **`F-17B-089`** | `ENHANCE` | `Insurance/VehicleNoDetails.cs` L15–100, `Web.config` (`Attestr`) | Pluggable RC lookup supporting `mock`, `apiclub`, `signzy`, and `attestr` with per-request provider override. | `AttestrRCProvider.lookup_rc`, `resolve_vehicle_rc_provider`, `VehicleRCService.lookup_vehicle_rc` | `GET /integrations/vehicle-rc/providers`<br>`POST /integrations/vehicle-rc/lookup` | `tbl_vehiclenorc_details` | `test_f17b_089_095_096_097_attestr_cashback_targets_and_sub_agents` (`L718–767`) | **`VERIFIED_ENHANCED`** |
| **`F-17B-090`** | `ENHANCE` | `SendMailToAutority.aspx.cs` L38–120 (`sp_InstapayReport`: `NEWSUMMERY`, `FROMRA`, `Online_To_Reliable`) | Generate daily InstaPay authority summary across all 3 legacy report modes and dispatch HTML + PDF email to authority recipients. | `get_instapay_authority_summary`, `dispatch_instapay_authority_summary` | `GET /reports/operations/instapay-authority-summary`<br>`POST /reports/operations/instapay-authority-summary/dispatch` | `tbl_idealpaymentreceipt` | `test_f17b_085_and_090_ideal_receipts_instapay_and_authority_summary` (`L253–272`) | **`VERIFIED_ENHANCED`** |
| **`F-17B-095`** | `ENHANCE` | `API_cashback`, `BLL_CashBackAmount` L7130, `DAL_CashBackAmount` L36775 | Record and query promotional cashback credits per policy transaction and agent. | `create_cashback_entry`, `list_cashback_entries` | `POST /commissions/cashbacks`<br>`GET /commissions/cashbacks` | `tbl_cashback` | `test_f17b_089_095_096_097_attestr_cashback_targets_and_sub_agents` (`L768–783`) | **`VERIFIED_ENHANCED`** |
| **`F-17B-096`** | `ENHANCE` | `API_Targetnew`, `BLL_Target`, `Clerk/Target*.aspx.cs` | Create/update monthly employee GWP targets and compute achievement percentage and contest reward tiers. | `create_sales_target`, `update_sales_target`, `list_sales_targets` | `POST /reports/targets`<br>`PUT /reports/targets/{target_id}`<br>`GET /reports/targets` | `tbl_target` | `test_f17b_089_095_096_097_attestr_cashback_targets_and_sub_agents` (`L784–811`) | **`VERIFIED_ENHANCED`** |
| **`F-17B-097`** | `ENHANCE` | `Clerk/Agent*.aspx.cs`, `BLL_Agent` | Register sub-agents under a parent POSP agent and calculate commission split between parent and sub-agent. | `create_sub_agent`, `list_sub_agents`, `calculate_sub_agent_split` | `POST /agents/{agent_id}/sub-agents`<br>`GET /agents/{agent_id}/sub-agents`<br>`POST /agents/{agent_id}/sub-agents/calculate-split` | `tbl_agent` (`ParentAgentId`, `SubAgentSplitPercent`) | `test_f17b_089_095_096_097_attestr_cashback_targets_and_sub_agents` (`L812–853`) | **`VERIFIED_ENHANCED`** |
| **`F-17B-098`** | `ENHANCE` | `Clerk/Location.aspx.cs` L48–106, `API/GeoLocationClasses.cs` | Record field visit GPS coordinates, map `(0.0, 0.0)` to `"No Address Found"`, and reverse-geocode non-zero coordinates. | `record_geo_check_in`, `_resolve_reverse_geocode`, `list_geo_check_ins` | `POST /integrations/geo/check-in`<br>`GET /integrations/geo/check-ins` | `tbl_callingimportdata` | `test_f17b_093_and_098_telecalling_crm_and_gps_check_in` (`L633–661`) | **`VERIFIED_ENHANCED`** |
| **`F-17B-099`** | `ENHANCE` | `API_Account`, `Clerk/Expense*.aspx.cs` | Record and list branch petty office expense and stationery vouchers in the accounting ledger. | `create_office_expense_voucher`, `list_office_expense_vouchers` | `POST /accounting/office-expenses`<br>`GET /accounting/office-expenses` | `tbl_account` | `test_f17b_088_and_099_sales_registration_and_office_expenses` (`L447–473`) | **`VERIFIED_ENHANCED`** |

---

## 23. Part 21 — Complete 120-Feature Parity Matrix (`F-17B-001` .. `F-17B-120`)

Every one of the **120 canonical feature groups** is assigned a single final audit status from the permitted set (`VERIFIED_MATCH`, `VERIFIED_HARDENED`, `VERIFIED_ENHANCED`, `PARTIAL`, `MISSING`, `OBSOLETE`, `UNKNOWN`):

| Feature ID | Legacy Capability | Priority | Phase 17B Disposition | Phase 18A Claimed | Legacy Evidence | FastAPI Route(s) & Service(s) | Model / Table(s) | Test Evidence | Biz Rule | Security | Financial | Integration | Final Audit Status | Severity / Finding |
| :--- | :--- | :---: | :---: | :---: | :--- | :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| `F-17B-001` | Multi-Principal Login (Staff, Agent, Franchise, Executive, Customer) | `P0` | `MUST` | `HARDENED` | `Log_In.aspx.cs`, `Service.asmx.cs::AppLogin1` | `POST /api/v1/auth/login`, `AuthService` | `tbl_user`, `tbl_agent`, `tbl_franchise` | `tests/integration/test_phase5_auth.py` | Yes | Yes | N/A | N/A | `VERIFIED_HARDENED` | None |
| `F-17B-002` | JWT Access/Refresh Token Lifecycle & Revocation | `P0` | `MUST` | `HARDENED` | `Log_In.aspx.cs` (`Session`) | `POST /api/v1/auth/refresh`, `/logout`, `security.py` | `tbl_user` | `test_phase5_auth.py` | Yes | Yes | N/A | N/A | `VERIFIED_HARDENED` | None |
| `F-17B-003` | Password Hashing (Argon2/Bcrypt Upgrade) & Reset | `P0` | `MUST` | `HARDENED` | `ChangePassword.aspx.cs`, `ForgotPassword.aspx.cs` | `POST /api/v1/auth/change-password`, `/forgot-password` | `tbl_user` | `test_phase5_auth.py` | Yes | Yes | N/A | N/A | `VERIFIED_HARDENED` | None |
| `F-17B-004` | Mobile OTP Generation, Dispatch & Verification | `P0` | `MUST` | `HARDENED` | `Service.asmx.cs::SendOTP`, `VerifyOTP` | `POST /api/v1/auth/otp/send`, `/otp/verify` | `tbl_otp_verification` | `test_phase5_auth.py`, `test_phase13_notifications.py` | Yes | Yes | N/A | Yes | `VERIFIED_HARDENED` | None |
| `F-17B-005` | Role-Based Access Control (30+ Roles) & Principal Scoping | `P0` | `MUST` | `HARDENED` | `Log_In.aspx.cs` L60–245, `Clerk.Master.cs` | `app/core/dependencies.py` (`require_roles`) | `tbl_userrole`, `tbl_user` | `test_phase5_auth.py`..`test_phase18a_remaining_features.py` | Yes | Yes | N/A | N/A | `VERIFIED_HARDENED` | None |
| `F-17B-006` | Dynamic Menu Tree, Form Privileges & Permission Matrix | `P0` | `MUST` | `HARDENED` | `Clerk/adm_MenuMaster.aspx.cs`, `adm_FormPrivilege.aspx.cs` | `/api/v1/admin/menus/*`, `/privileges/*`, `AdminService` | `tbl_menumaster`, `tbl_formprivilege`, `tbl_userprivilege` | `test_phase16b_admin_users_privileges.py` | Yes | Yes | N/A | N/A | `VERIFIED_HARDENED` | None |
| `F-17B-007` | Operator Cheque Clearing Lockout (`LBR-069` & Mumbai Rule) | `P0` | `MUST` | `MATCH` | `Log_In.aspx.cs` L199–229, `Adm_LockChequeEntry.aspx.cs` | `POST /api/v1/batch-tasks/enforce-overdue-cheque-locks`, `UtilityService` | `tbl_transaction`, `tbl_user` | `test_phase15b_utilities_imports.py` | Yes | Yes | Yes | N/A | `VERIFIED_MATCH` | `LBR-069` Frozen |
| `F-17B-008` | State, City, RTO & Pincode Geo Directory | `P0` | `MUST` | `MATCH` | `Clerk/adm_State.aspx.cs`, `adm_City.aspx.cs`, `adm_RTO.aspx.cs` | `/api/v1/masters/states`, `/cities`, `/rtos`, `MasterService` | `tbl_state`, `tbl_city`, `tbl_rto` | `test_phase12_masters.py` | Yes | Yes | N/A | N/A | `VERIFIED_MATCH` | None |
| `F-17B-009` | Insurance Company & Company Branch Directory | `P0` | `MUST` | `MATCH` | `Clerk/adm_InsuranceCompany.aspx.cs`, `adm_CompanyBranch.aspx.cs` | `/api/v1/masters/insurance-companies`, `/admin/directories/*` | `tbl_insurancecompany`, `tbl_companybranch` | `test_phase12_masters.py`, `test_phase16b_admin_users_privileges.py` | Yes | Yes | N/A | N/A | `VERIFIED_MATCH` | None |
| `F-17B-010` | Product Type, Policy Type & Sub-Product Master | `P0` | `MUST` | `MATCH` | `Clerk/adm_ProductType.aspx.cs`, `adm_PolicyType.aspx.cs` | `/api/v1/masters/product-types`, `/policy-types` | `tbl_producttype`, `tbl_policytype` | `test_phase12_masters.py` | Yes | Yes | N/A | N/A | `VERIFIED_MATCH` | None |
| `F-17B-011` | Vehicle Category, Type, Make, Model, Variant & Fuel Catalog | `P0` | `MUST` | `MATCH` | `Clerk/adm_Make.aspx.cs`, `adm_Model.aspx.cs`, `adm_Make_Variant_2025.aspx.cs` | `/api/v1/masters/vehicle-types`, `/makes`, `/models`, `/variants`, `/fuels` | `tbl_vehicletype`, `tbl_make`, `tbl_model`, `tbl_variant`, `tbl_fuel` | `test_phase12_masters.py` | Yes | Yes | N/A | N/A | `VERIFIED_MATCH` | None |
| `F-17B-012` | Add-On Covers, Hypothecation/Financier & Bank Master | `P0` | `MUST` | `MATCH` | `Clerk/adm_BankMaster.aspx.cs`, `adm_Financer.aspx.cs` | `/api/v1/masters/banks`, `/financiers`, `/addons` | `tbl_bank`, `tbl_financer`, `tbl_addon` | `test_phase12_masters.py` | Yes | Yes | N/A | N/A | `VERIFIED_MATCH` | None |
| `F-17B-013` | Reliable Internal Branch, Category & Designation Master | `P0` | `MUST` | `MATCH` | `Clerk/adm_Branch.aspx.cs`, `adm_Category.aspx.cs` | `/api/v1/masters/branches`, `/categories`, `/designations` | `tbl_branch`, `tbl_category`, `tbl_designation` | `test_phase12_masters.py`, `test_phase16b_admin_users_privileges.py` | Yes | Yes | N/A | N/A | `VERIFIED_MATCH` | None |
| `F-17B-014` | Insurer Portal Login Credentials & Broker Code Directory | `P1` | `MUST` | `HARDENED` | `Clerk/adm_PortalLoginId.aspx.cs`, `adm_BrokerCode.aspx.cs` | `/api/v1/admin/directories/portal-logins`, `/broker-codes` | `tbl_portallogin`, `tbl_brokercode` | `test_phase16b_admin_users_privileges.py` | Yes | Yes | N/A | N/A | `VERIFIED_HARDENED` | None |
| `F-17B-015` | Internal Staff / User Master Onboarding & Profile Management | `P0` | `MUST` | `HARDENED` | `Clerk/adm_UserMaster.aspx.cs`, `BLL_UserMaster` | `/api/v1/users/*`, `UserService` | `tbl_user`, `tbl_employee` | `test_phase16b_admin_users_privileges.py` | Yes | Yes | N/A | N/A | `VERIFIED_HARDENED` | None |
| `F-17B-016` | Agent / POSP Onboarding, KYC Verification & Approval | `P0` | `MUST` | `MATCH` | `Clerk/adm_Agent.aspx.cs`, `Service.asmx.cs::InsertAppAgent1` | `/api/v1/agents/*`, `ProfileService` | `tbl_agent` | `test_phase15b_profiles.py` | Yes | Yes | N/A | N/A | `VERIFIED_MATCH` | None |
| `F-17B-017` | Franchise Partner Onboarding, Commercial Terms & Mapping | `P0` | `MUST` | `MATCH` | `Clerk/adm_Franchise.aspx.cs`, `BLL_Franchise` | `/api/v1/franchises/*`, `ProfileService` | `tbl_franchise` | `test_phase15b_profiles.py` | Yes | Yes | N/A | N/A | `VERIFIED_MATCH` | None |
| `F-17B-018` | Marketing Executive / Team Leader Hierarchy & Mapping | `P0` | `MUST` | `MATCH` | `Clerk/adm_MarketingExecutive.aspx.cs`, `BLL_MarketingExecutive` | `/api/v1/employees/*`, `ProfileService` | `tbl_employee` | `test_phase15b_profiles.py` | Yes | Yes | N/A | N/A | `VERIFIED_MATCH` | None |
| `F-17B-019` | Dealer / Showroom Partner Master & Mapping | `P1` | `MUST` | `MATCH` | `Clerk/adm_Dealer.aspx.cs`, `BLL_Dealer` | `/api/v1/admin/directories/dealers`, `AdminService` | `tbl_dealer` | `test_phase16b_admin_users_privileges.py` | Yes | Yes | N/A | N/A | `VERIFIED_MATCH` | None |
| `F-17B-020` | Customer & Vehicle Registration Master (`tbl_customer`) | `P0` | `MUST` | `MATCH` | `Clerk/Cust_PolicyInfo.aspx.cs`, `Service.asmx.cs::InsertCustomerPolicyInfo` | `/api/v1/customers/*`, `/vehicles/*`, `CustomerService` | `tbl_customer`, `tbl_customervehicle` | `test_phase4_customers_vehicles.py` | Yes | Yes | N/A | N/A | `VERIFIED_MATCH` | None |
| `F-17B-021` | Motor Proposal Entry, Premium Calculation & Approval | `P0` | `MUST` | `MATCH` | `Clerk/ProposalEntry.aspx.cs`, `Service.asmx.cs::InsertProposal` | `/api/v1/quotations/*`, `QuotationService`, `RatingEngineService` | `tbl_quotation`, `tbl_app_quotationrequest` | `test_phase6_quotations_api.py` | Yes | Yes | Yes | N/A | `VERIFIED_MATCH` | None |
| `F-17B-022` | Core Motor Policy Transaction Underwriting (`tbl_transaction`) | `P0` | `MUST` | `HARDENED` | `Clerk/NewTranscationEntry.aspx.cs`, `BLL_NewTransaction` | `POST /api/v1/policies`, `PUT /api/v1/policies/{id}`, `PolicyService` | `tbl_transaction` | `test_phase7_policy_booking_api.py` | Yes | Yes | Yes | N/A | `VERIFIED_HARDENED` | None |
| `F-17B-023` | Mobile App Multi-Overload Policy Submission (`_1`..`_8`, `_21`) | `P0` | `MUST` | `HARDENED` | `Service.asmx.cs` L2075–2890 (`InsertAppTransctiondetailsNew*`) | `POST /api/v1/policies/app-submissions`, `PolicyService` | `tbl_transaction`, `tbl_transactionappnew` | `test_phase7_policy_booking_api.py` | Yes | Yes | Yes | N/A | `VERIFIED_HARDENED` | None |
| `F-17B-024` | Non-Motor & Health Policy Transaction Underwriting (`_NM`) | `P0` | `MUST` | `MATCH` | `Clerk/NonMotorTransaction.aspx.cs`, `HealthTransaction.aspx.cs` | `POST /api/v1/policies`, `/api/v1/health-members/*` | `tbl_transaction`, `tbl_healthmemberdetails` | `test_phase7_policy_booking_api.py`, `test_phase15b_utilities_imports.py` | Yes | Yes | Yes | N/A | `VERIFIED_MATCH` | None |
| `F-17B-025` | Duplicate Policy / Double Entry Detection (`FindDoubleEntry`) | `P0` | `MUST` | `HARDENED` | `Clerk/FindDoubleEntry.aspx.cs`, `CheckPolicyNo` | `GET /api/v1/policies/check-duplicate`, `PolicyService` | `tbl_transaction` | `test_phase7_policy_booking_api.py` | Yes | Yes | N/A | N/A | `VERIFIED_HARDENED` | None |
| `F-17B-026` | Back-Dated Policy Transaction Entry & Admin Audit Trail | `P1` | `MUST` | `HARDENED` | `Clerk/Transaction_BackDate.aspx.cs` | `POST /api/v1/policies` (role & audit guard) | `tbl_transaction`, `tbl_audit_log` | `test_phase7_policy_booking_api.py` | Yes | Yes | Yes | N/A | `VERIFIED_HARDENED` | None |
| `F-17B-027` | Policy Document & Proposal/RC/KYC Attachment Upload | `P0` | `MUST` | `ENHANCED` | `UploadHandler.ashx.cs`, `Clerk/UploadPolicy.aspx.cs` | `POST /api/v1/documents/upload`, `DocumentService` | `tbl_documents` | `test_phase11_documents_webhooks.py` | Yes | Yes | N/A | N/A | `VERIFIED_ENHANCED` | None |
| `F-17B-028` | Operator Transaction Verification, QC & Maker-Checker Approval | `P0` | `MUST` | `MATCH` | `Clerk/VerifyTransaction.aspx.cs`, `ApproveTransaction.aspx.cs` | `POST /api/v1/policies/{id}/verify`, `/approve`, `PolicyService` | `tbl_transaction` | `test_phase7_policy_booking_api.py` | Yes | Yes | Yes | N/A | `VERIFIED_MATCH` | None |
| `F-17B-029` | Multi-Mode Premium Collection (Cash, Cheque, Online, Cut&Pay, Wallet) | `P0` | `MUST` | `HARDENED` | `Clerk/PaymentEntry.aspx.cs`, `BLL_Payment` | `/api/v1/payments/*`, `PaymentService` | `tbl_payment`, `tbl_transaction` | `test_phase8_payments_wallets_api.py` | Yes | Yes | Yes | N/A | `VERIFIED_HARDENED` | None |
| `F-17B-030` | Cheque Receipt, Bank Deposit, Clearance & Realization | `P0` | `MUST` | `HARDENED` | `Clerk/ChequeEntry.aspx.cs`, `ChequeClearance.aspx.cs` | `/api/v1/payments/cheques/*`, `PaymentService` | `tbl_chequedetails`, `tbl_transaction` | `test_phase8_payments_wallets_api.py` | Yes | Yes | Yes | N/A | `VERIFIED_HARDENED` | None |
| `F-17B-031` | Cheque Bounce, Penalty (`Rs. 500`), Reversal & Re-Presentation | `P0` | `MUST` | `HARDENED` | `Clerk/ChequeBounce.aspx.cs`, `ChequePenalty.aspx.cs` | `POST /api/v1/payments/cheques/{id}/bounce`, `/re-present` | `tbl_chequedetails`, `tbl_transaction`, `tbl_wallet` | `test_phase8_payments_wallets_api.py` | Yes | Yes | Yes | N/A | `VERIFIED_HARDENED` | None |
| `F-17B-032` | Cut & Pay (`CutNPay`) Net Premium Deduction Settlement | `P0` | `MUST` | `HARDENED` | `Clerk/CutNPay*.aspx.cs`, `Rpt_CutNPay.rpt` | `PaymentService`, `CommissionService` | `tbl_transaction`, `tbl_payment` | `test_phase8_payments_wallets_api.py` | Yes | Yes | Yes | N/A | `VERIFIED_HARDENED` | None |
| `F-17B-033` | Insurer Credit Card / Portal Float & Payment Reconciliation | `P0` | `MUST` | `MATCH` | `Clerk/CompanyPayment*.aspx.cs`, `InsurerReconciliation.aspx.cs` | `/api/v1/reconciliation/*`, `PaymentService` | `tbl_insurer_reconciliation`, `tbl_transaction` | `test_phase8_payments_wallets_api.py` | Yes | Yes | Yes | N/A | `VERIFIED_MATCH` | None |
| `F-17B-034` | Partner E-Wallet Balance, Top-Up Request & Cashier Approval | `P0` | `MUST` | `HARDENED` | `Clerk/WalletTopup.aspx.cs`, `WalletApproval.aspx.cs`, `BLL_Wallet` | `/api/v1/wallets/*`, `WalletService` | `tbl_wallet`, `tbl_wallettransaction` | `test_phase8_payments_wallets_api.py` | Yes | Yes | Yes | N/A | `VERIFIED_HARDENED` | None |
| `F-17B-035` | Atomic Wallet Debit, Hold/Lock & Release on Cancellation | `P0` | `MUST` | `HARDENED` | `Service.asmx.cs`, `DAL_Wallet` | `WalletService` (`SELECT ... FOR UPDATE`) | `tbl_wallet`, `tbl_wallettransaction` | `test_phase8_payments_wallets_api.py` | Yes | Yes | Yes | N/A | `VERIFIED_HARDENED` | None |
| `F-17B-036` | Agent & Franchise Commission Calculation (OD%, TP%, Net/Gross) | `P0` | `MUST` | `HARDENED` | `Clerk/Commission*.aspx.cs`, `BLL_Commission` | `/api/v1/commissions/*`, `CommissionService` | `tbl_agentcommission`, `tbl_transaction` | `test_phase9_commission_accounting_api.py` | Yes | Yes | Yes | N/A | `VERIFIED_HARDENED` | None |
| `F-17B-037` | Extra Payout / Special Incentive Approval (`ExtraPayoutTransaction`) | `P0` | `MUST` | `MATCH` | `Clerk/ExtraPayoutTransaction.aspx.cs`, `ApproveExtraPayout.aspx.cs` | `/api/v1/commissions/extra-payouts/*`, `CommissionService` | `tbl_extrapayout`, `tbl_transaction` | `test_phase9_commission_accounting_api.py` | Yes | Yes | Yes | N/A | `VERIFIED_MATCH` | None |
| `F-17B-038` | TDS Deduction, GST Input/Output & Net Payout Lot Generation | `P0` | `MUST` | `HARDENED` | `Clerk/CommissionPayment.aspx.cs`, `AgentPayout*.aspx.cs` | `/api/v1/commission-payouts/*`, `CommissionService` | `tbl_agentcommissionpayment` | `test_phase9_commission_accounting_api.py` | Yes | Yes | Yes | N/A | `VERIFIED_HARDENED` | None |
| `F-17B-039` | InstaPay Immediate Commission Disbursement Eligibility & Tracking | `P1` | `MUST` | `MATCH` | `Clerk/InstaPay*.aspx.cs`, `BLL_InstaPay` L8910, `DAL_InstaPay` L45010 | `/api/v1/commission-payouts/*`, `CommissionService` | `tbl_agentcommissionpayment`, `tbl_transaction` | `test_phase9_commission_accounting_api.py` | Yes | Yes | Yes | N/A | `VERIFIED_MATCH` | None |
| `F-17B-040` | Chart of Accounts, Ledger Master (`tbl_ledgermaster`) & Balances | `P0` | `MUST` | `MATCH` | `Clerk/adm_LedgerMaster.aspx.cs`, `BLL_Account` | `/api/v1/accounting/ledgers/*`, `AccountingService` | `tbl_ledgermaster`, `tbl_accountgroup` | `test_phase9_commission_accounting_api.py` | Yes | Yes | Yes | N/A | `VERIFIED_MATCH` | None |
| `F-17B-041` | Double-Entry Vouchers (Receipt, Payment, Contra, Journal, Dr/Cr) | `P0` | `MUST` | `HARDENED` | `Clerk/AccountVoucher*.aspx.cs`, `PaymentVoucher.aspx.cs` | `/api/v1/accounting/vouchers/*`, `AccountingService` | `tbl_account`, `tbl_ledgermaster` | `test_phase9_commission_accounting_api.py` | Yes | Yes | Yes | N/A | `VERIFIED_HARDENED` | None |
| `F-17B-042` | Daybook, Party Ledger Statement, Trial Balance & Reconciliation | `P0` | `MUST` | `ENHANCED` | `Clerk/rpt_AccountReport.aspx.cs`, `Rpt_AccountReport.rpt` | `/api/v1/accounting/*`, `/api/v1/reports/accounting/*` | `tbl_account`, `tbl_ledgermaster` | `test_phase9_commission_accounting_api.py`, `test_phase14_dashboards_reports.py` | Yes | Yes | Yes | N/A | `VERIFIED_ENHANCED` | None |
| `F-17B-043` | Motor & Non-Motor Claim Intimation, Registration & Docs | `P0` | `MUST` | `MATCH` | `Clerk/ClaimEntry.aspx.cs`, `Service.asmx.cs::InsertClaim*` | `/api/v1/claims/*`, `ClaimService` | `tbl_claim`, `tbl_transaction` | `test_phase10_claims_endorsements_api.py` | Yes | Yes | Yes | N/A | `VERIFIED_MATCH` | None |
| `F-17B-044` | Surveyor Assignment, Assessment Tracking & Claim Settlement | `P0` | `MUST` | `MATCH` | `Clerk/ClaimUpdate.aspx.cs`, `SurveyorMaster.aspx.cs` | `/api/v1/claims/*`, `ClaimService` | `tbl_claim`, `tbl_surveyor` | `test_phase10_claims_endorsements_api.py` | Yes | Yes | Yes | N/A | `VERIFIED_MATCH` | None |
| `F-17B-045` | Policy Endorsement Request, Document Upload & Status Workflow | `P0` | `MUST` | `MATCH` | `Clerk/EndorsementEntry.aspx.cs`, `Service.asmx.cs::InsertEndorsement*` | `/api/v1/endorsements/*`, `EndorsementService` | `tbl_endorsement`, `tbl_transaction` | `test_phase10_claims_endorsements_api.py` | Yes | Yes | Yes | N/A | `VERIFIED_MATCH` | None |
| `F-17B-046` | Post-Issuance Policy Correction (`UpdateEntry`) & Recalculation | `P0` | `MUST` | `HARDENED` | `Clerk/UpdateEntry*.aspx.cs`, `PolicyCorrection*.aspx.cs` | `/api/v1/endorsements/*`, `EndorsementService` | `tbl_transaction`, `tbl_agentcommission` | `test_phase10_claims_endorsements_api.py` | Yes | Yes | Yes | N/A | `VERIFIED_HARDENED` | None |
| `F-17B-047` | Policy Cancellation, Insurer Refund & Commission Clawback | `P0` | `MUST` | `HARDENED` | `Clerk/PolicyCancel*.aspx.cs`, `BLL_PolicyCancel` | `/api/v1/refunds/*`, `/endorsements/*`, `EndorsementService` | `tbl_policycancel`, `tbl_transaction`, `tbl_wallet` | `test_phase10_claims_endorsements_api.py` | Yes | Yes | Yes | N/A | `VERIFIED_HARDENED` | None |
| `F-17B-048` | Inbound HiCaliber Policy Extraction Webhook (`PolicyParserWebhook`) | `P0` | `MUST` | `HARDENED` | `PolicyParserWebhook.aspx.cs` L20–145, `sp_PE_Update_Extraction_new` | `POST /api/v1/documents/webhooks/policy-parser`, `DocumentService` | `tbl_calliber_policy_webhook` | `test_phase11_documents_webhooks.py` | Yes | Yes | Yes | Yes | `VERIFIED_HARDENED` | None |
| `F-17B-049` | Policy Expiry Tracking, Renewal Notice Generation & Reminders | `P0` | `MUST` | `ENHANCED` | `Clerk/ViewExpiryPolicy.aspx.cs`, `Service.asmx.cs::AppSelectExpiryPolicy*` | `/api/v1/renewals/*`, `RenewalService` | `tbl_transaction`, `tbl_renewal_followup` | `test_phase13_renewals.py` | Yes | Yes | N/A | Yes | `VERIFIED_ENHANCED` | None |
| `F-17B-050` | Customer Helpdesk / Mobile Support Ticket & Chat (`tbl_customerhelp`) | `P1` | `MUST` | `MATCH` | `Service.asmx.cs::InsertCustomerHelp`, `SelectCustomerHelp` | `/api/v1/renewals/customer-help/*`, `RenewalService` | `tbl_customerhelp` | `test_phase13_renewals.py` | Yes | Yes | N/A | N/A | `VERIFIED_MATCH` | None |
| `F-17B-051` | Authenticated Document Storage, Presigned Download & Streaming | `P0` | `MUST` | `HARDENED` | `UploadHandler.ashx.cs`, `Clerk/ShowImage.ashx.cs` | `/api/v1/documents/*`, `DocumentService` | `tbl_documents` | `test_phase11_documents_webhooks.py` | Yes | Yes | N/A | N/A | `VERIFIED_HARDENED` | None |
| `F-17B-052` | Vehicle RC Lookup Integration (3-Tier Cascade & Caching) | `P0` | `MUST` | `ENHANCED` | `VehicleService.asmx.cs::GetVehicleDetails`, `VehicleNoDetails.cs` | `POST /api/v1/integrations/vehicle-rc/lookup`, `VehicleRCService` | `tbl_vehiclenorc_details` | `test_phase13_vehicle_rc.py` | Yes | Yes | N/A | Yes | `VERIFIED_ENHANCED` | None |
| `F-17B-053` | Transactional SMS Dispatch Adapter (Fast2SMS / IndiaText) | `P0` | `MUST` | `ENHANCED` | `Service.asmx.cs`, `Web.config` (`fast2sms`, `indiatext`) | `/api/v1/notifications/sms/*`, `NotificationService` | `tbl_notification_log` | `test_phase13_notifications.py` | Yes | Yes | N/A | Yes | `VERIFIED_ENHANCED` | None |
| `F-17B-054` | OneSignal Mobile Push Notification Dispatch & Token Registry | `P1` | `MUST` | `ENHANCED` | `Service.asmx.cs::SendPushNotification*`, `BLL_Notification` | `/api/v1/notifications/push/*`, `NotificationService` | `tbl_notification_log`, `tbl_device_token` | `test_phase13_notifications.py` | Yes | Yes | N/A | Yes | `VERIFIED_ENHANCED` | None |
| `F-17B-055` | Outbound SMTP Email Notification & Attachment Dispatch | `P1` | `MUST` | `ENHANCED` | `SendMailToAutority.aspx.cs` L280–340 (`SmtpClient`) | `/api/v1/notifications/email/*`, `SMTPEmailProvider` | `tbl_notification_log` | `test_phase13_notifications.py` | Yes | Yes | N/A | Yes | `VERIFIED_ENHANCED` | None |
| `F-17B-056` | Role-Scoped Executive, Branch, Agent & Admin KPI Dashboards | `P0` | `MUST` | `ENHANCED` | `Clerk/Dashboard*.aspx.cs`, `Service.asmx.cs::AppDashBoard*` | `/api/v1/dashboards/*`, `DashboardService` | `tbl_transaction`, `tbl_chequedetails` | `test_phase14_dashboards_reports.py` | Yes | Yes | Yes | N/A | `VERIFIED_ENHANCED` | None |
| `F-17B-057` | Production, Sales, Branch, Insurer & Executive MIS Reports | `P0` | `MUST` | `ENHANCED` | `Clerk/MIS_*.aspx.cs`, `Clerk/rpt_*.aspx.cs` | `/api/v1/reports/*`, `ReportService` | `tbl_transaction` | `test_phase14_dashboards_reports.py` | Yes | Yes | Yes | N/A | `VERIFIED_ENHANCED` | None |
| `F-17B-058` | Agent Commission Tax Invoice PDF Report (`AgentPaymentInvoice.rpt`) | `P0` | `MUST` | `ENHANCED` | `Insurance/AgentPaymentInvoice.rpt` | `/api/v1/reports/posp-invoice/*`, `ReportService` | `tbl_agentcommissionpayment` | `test_phase14_dashboards_reports.py` | Yes | Yes | Yes | N/A | `VERIFIED_ENHANCED` | None |
| `F-17B-059` | Accounting Payment Voucher PDF Report (`Payment_Voucher.rpt`) | `P0` | `MUST` | `ENHANCED` | `Insurance/Payment_Voucher.rpt` | `/api/v1/reports/accounting/*`, `ReportService` | `tbl_account` | `test_phase14_dashboards_reports.py` | Yes | Yes | Yes | N/A | `VERIFIED_ENHANCED` | None |
| `F-17B-060` | Party Account & Ledger Statement Report (`Rpt_AccountReport.rpt`) | `P0` | `MUST` | `ENHANCED` | `Insurance/Rpt_AccountReport.rpt` | `/api/v1/reports/accounting/*`, `ReportService` | `tbl_account`, `tbl_ledgermaster` | `test_phase14_dashboards_reports.py` | Yes | Yes | Yes | N/A | `VERIFIED_ENHANCED` | None |
| `F-17B-061` | Agent Commission Paid Statement Report (`Rpt_CommissionPaid.rpt`) | `P0` | `MUST` | `ENHANCED` | `Insurance/Rpt_CommissionPaid.rpt` | `/api/v1/reports/commissions/*`, `ReportService` | `tbl_agentcommissionpayment` | `test_phase14_dashboards_reports.py` | Yes | Yes | Yes | N/A | `VERIFIED_ENHANCED` | None |
| `F-17B-062` | Cut & Pay Settlement Register Report (`Rpt_CutNPay.rpt`) | `P0` | `MUST` | `ENHANCED` | `Insurance/Rpt_CutNPay.rpt` | `/api/v1/reports/*`, `ReportService` | `tbl_transaction`, `tbl_payment` | `test_phase14_dashboards_reports.py` | Yes | Yes | Yes | N/A | `VERIFIED_ENHANCED` | None |
| `F-17B-063` | Partner Payout Payment Advice PDF Report (`Rpt_PaymentAdvice.rpt`) | `P0` | `MUST` | `ENHANCED` | `Insurance/Rpt_PaymentAdvice.rpt` | `/api/v1/reports/commissions/*`, `ReportService` | `tbl_agentcommissionpayment` | `test_phase14_dashboards_reports.py` | Yes | Yes | Yes | N/A | `VERIFIED_ENHANCED` | None |
| `F-17B-064` | Agent Commission Paid vs Unpaid Report (`Rpt_ViewAgentCommPaidUnpaid.rpt`) | `P0` | `MUST` | `ENHANCED` | `Insurance/Rpt_ViewAgentCommPaidUnpaid.rpt` | `/api/v1/reports/commissions/*`, `ReportService` | `tbl_transaction`, `tbl_agentcommissionpayment` | `test_phase14_dashboards_reports.py` | Yes | Yes | Yes | N/A | `VERIFIED_ENHANCED` | None |
| `F-17B-065` | Insurer B2B Brokerage Sales Invoice PDF (`SalesInvoiceReport.rpt`) | `P1` | `MUST` | `ENHANCED` | `Insurance/SalesInvoiceReport.rpt` | `/api/v1/reports/accounting/*`, `ReportService` | `tbl_account`, `tbl_salesregistration` | `test_phase14_dashboards_reports.py` | Yes | Yes | Yes | N/A | `VERIFIED_ENHANCED` | None |
| `F-17B-066` | Bulk Excel/CSV Policy & Transaction Staging Import | `P1` | `MUST` | `ENHANCED` | `Clerk/ImportTransaction*.aspx.cs`, `BLL_Import*` | `/api/v1/imports/*`, `UtilityService` | `tbl_import_staging` | `test_phase15b_utilities_imports.py` | Yes | Yes | Yes | N/A | `VERIFIED_ENHANCED` | None |
| `F-17B-067` | Bulk Insurer Commission Dump Import & Auto-Reconciliation | `P1` | `MUST` | `ENHANCED` | `Clerk/ImportCompanyCommission*.aspx.cs` | `/api/v1/imports/*`, `UtilityService` | `tbl_import_staging`, `tbl_transaction` | `test_phase15b_utilities_imports.py` | Yes | Yes | Yes | N/A | `VERIFIED_ENHANCED` | None |
| `F-17B-068` | Scheduled Background Jobs (Expiry, Lock Evaluation, Cleanup) | `P1` | `MUST` | `ENHANCED` | `Global.asax.cs`, `Log_In.aspx.cs` triggers | `/api/v1/batch-tasks/*`, `UtilityService` | `tbl_user`, `tbl_transaction` | `test_phase15b_utilities_imports.py` | Yes | Yes | Yes | N/A | `VERIFIED_ENHANCED` | None |
| `F-17B-069` | Global Typeahead & Multi-Criteria Search (`SearchMethods`) | `P0` | `MUST` | `MATCH` | `SearchMethods.aspx.cs` (`22` WMs), `AppSearchMethod.aspx.cs` (`22` WMs) | `/api/v1/search/*`, `SearchService` | `tbl_transaction`, `tbl_customer`, `tbl_agent` | `test_phase12_search.py` | Yes | Yes | N/A | N/A | `VERIFIED_MATCH` | None |
| `F-17B-070` | Mobile App Version Check & Force-Update Gate (`AppSelectVersion`) | `P1` | `MUST` | `MATCH` | `Service.asmx.cs::AppSelectVersion` L14260 | `/api/v1/admin/*`, `AdminService` | `tbl_appversion` | `test_phase16b_admin_users_privileges.py` | Yes | Yes | N/A | N/A | `VERIFIED_MATCH` | None |
| `F-17B-071` | Mobile Banner, Promotional Slider & Announcement Feed | `P1` | `MUST` | `MATCH` | `Clerk/adm_Banner.aspx.cs`, `Service.asmx.cs::SelectAppBanner` | `/api/v1/admin/banners/*`, `AdminService` | `tbl_banner` | `test_phase16b_admin_users_privileges.py` | Yes | Yes | N/A | N/A | `VERIFIED_MATCH` | None |
| `F-17B-072` | Partner Self-Service Profile, KYC View & Certificate Download | `P1` | `MUST` | `MATCH` | `Service.asmx.cs::AppSelectAgentProfile`, `AppUpdateAgentProfile` | `/api/v1/agents/*`, `/employees/*`, `/franchises/*` | `tbl_agent`, `tbl_franchise`, `tbl_employee` | `test_phase15b_profiles.py` | Yes | Yes | N/A | N/A | `VERIFIED_MATCH` | None |
| `F-17B-073` | Commercial Vehicle (GCV / PCV / Misc-D) Underwriting Fields | `P0` | `MUST` | `MATCH` | `Clerk/NewTranscationEntry.aspx.cs`, `API_Transcation` | `/api/v1/policies/*`, `PolicyService` | `tbl_transaction` | `test_phase7_policy_booking_api.py` | Yes | Yes | Yes | N/A | `VERIFIED_MATCH` | None |
| `F-17B-074` | Fleet / Multiple Policy Batch Underwriting per Customer | `P1` | `MUST` | `MATCH` | `Clerk/MultiPolicy*.aspx.cs`, `BLL_NewTransaction` | `/api/v1/policies/*`, `/imports/*` | `tbl_transaction` | `test_phase7_policy_booking_api.py`, `test_phase15b_utilities_imports.py` | Yes | Yes | Yes | N/A | `VERIFIED_MATCH` | None |
| `F-17B-075` | Agent Advance Deposit & On-Account Payment Adjustment | `P1` | `MUST` | `MATCH` | `Clerk/AgentAdvance*.aspx.cs`, `BLL_Account`, `BLL_Payment` | `/api/v1/payments/*`, `/accounting/vouchers/*` | `tbl_payment`, `tbl_account` | `test_phase8_payments_wallets_api.py`, `test_phase9_commission_accounting_api.py` | Yes | Yes | Yes | N/A | `VERIFIED_MATCH` | None |
| `F-17B-076` | Customer Refund Processing (Excess Premium / Cancelled Policy) | `P1` | `MUST` | `MATCH` | `Clerk/Refund*.aspx.cs`, `BLL_Payment` | `/api/v1/refunds/*`, `EndorsementService`, `PaymentService` | `tbl_payment`, `tbl_policycancel` | `test_phase10_claims_endorsements_api.py` | Yes | Yes | Yes | N/A | `VERIFIED_MATCH` | None |
| `F-17B-077` | Franchise Override Commission & Margin Differential Calculation | `P0` | `MUST` | `MATCH` | `Clerk/FranchiseCommission*.aspx.cs`, `BLL_Franchise` | `/api/v1/commissions/*`, `CommissionService` | `tbl_franchise`, `tbl_agentcommission` | `test_phase9_commission_accounting_api.py` | Yes | Yes | Yes | N/A | `VERIFIED_MATCH` | None |
| `F-17B-078` | Insurer Receivable Brokerage Ageing & Realization Tracking | `P1` | `MUST` | `MATCH` | `Clerk/CompanyCommission*.aspx.cs`, `BLL_Commission` | `/api/v1/commissions/*`, `CommissionService` | `tbl_transaction`, `tbl_agentcommission` | `test_phase9_commission_accounting_api.py` | Yes | Yes | Yes | N/A | `VERIFIED_MATCH` | None |
| `F-17B-079` | Financial Year (`FYear`) Period Locking & Sequence Numbering | `P1` | `MUST` | `MATCH` | `Clerk/adm_FinancialYear.aspx.cs`, `BLL_Account` | `/api/v1/accounting/*`, `AccountingService` | `tbl_financialyear` | `test_phase9_commission_accounting_api.py` | Yes | Yes | Yes | N/A | `VERIFIED_MATCH` | None |
| `F-17B-080` | GST Input/Output Tax Register & GSTR Summary Export | `P1` | `MUST` | `ENHANCED` | `Clerk/rpt_GST*.aspx.cs`, `BLL_Account` | `/api/v1/reports/accounting/*`, `ReportService` | `tbl_transaction`, `tbl_account` | `test_phase14_dashboards_reports.py` | Yes | Yes | Yes | N/A | `VERIFIED_ENHANCED` | None |
| `F-17B-081` | TDS Payable Register & Partner Form 16A Reconciliation | `P1` | `MUST` | `ENHANCED` | `Clerk/rpt_TDS*.aspx.cs`, `BLL_Commission` | `/api/v1/reports/commissions/*`, `ReportService` | `tbl_agentcommissionpayment`, `tbl_agent` | `test_phase14_dashboards_reports.py` | Yes | Yes | Yes | N/A | `VERIFIED_ENHANCED` | None |
| `F-17B-082` | Immutable System Audit Log & Security Event Trail | `P0` | `MUST` | `HARDENED` | `BLL_Login`, `DAL_Operations.cs` (`InsertedBy`, `UpdatedBy`) | `/api/v1/admin/*`, `AdminService`, `UserService` | `tbl_audit_log` | `test_phase16b_admin_users_privileges.py` | Yes | Yes | N/A | N/A | `VERIFIED_HARDENED` | None |
| `F-17B-083` | Outbound HiCaliber Policy PDF Upload Trigger & Pre-Fill Lookup | `P2` | `SHOULD` | `HARDENED` | `Clerk/PE_UploadPolicy.aspx.cs` L89–190, `DAL_PE_Transaction` | `POST /api/v1/documents/policy-extraction/upload`, `GET .../prefill`, `POST .../link-transaction` | `tbl_calliber_policy_webhook`, `tbl_documents`, `tbl_transaction` | `test_f17b_083_policy_pdf_extraction_upload_prefill_and_link` | Yes | Yes | Yes | Yes | `VERIFIED_HARDENED` | None |
| `F-17B-084` | Extended Operator Lockout: Pending Cash (Mumbai 3d / 2d) & App Trans | `P2` | `SHOULD` | `HARDENED` | `adm_LockCashEntry1.aspx.cs` L47–90, `adm_LockPendingTansEntry.aspx.cs` | `POST /api/v1/batch-tasks/enforce-pending-cash-locks`, `POST .../enforce-pending-app-transaction-locks`, `GET .../operator-lock-status` | `tbl_transaction`, `tbl_transactionappnew`, `tbl_user` | `test_f17b_084_pending_cash_and_app_transaction_locks` | Yes | Yes | Yes | N/A | `VERIFIED_HARDENED` | None |
| `F-17B-085` | Bulk Ideal / Broker CSV Payment Receipt & Multi-Agent Settlement | `P2` | `SHOULD` | `HARDENED` | `POSP_MultiEntryIdealPayment.aspx.cs` L75–120, `DAL_IdealPaymentReceipt` | `POST /api/v1/commission-payouts/ideal-payment-receipts/bulk`, `GET .../ideal-payment-receipts`, `POST .../instapay/requests` | `tbl_idealpaymentreceipt`, `tbl_agentcommissionpayment`, `tbl_transaction` | `test_f17b_085_and_090_ideal_receipts_instapay_and_authority_summary` | Yes | Yes | Yes | N/A | `VERIFIED_HARDENED` | None |
| `F-17B-086` | Partner Commission Grid Lookup, CSV Import & Reliance 90%/60% Cap | `P2` | `SHOULD` | `HARDENED` | `BLL_Grid` L9025, `BLL_Capping` L7121, `sp_CappingForRelianceCompany` | `POST /api/v1/commissions/grids`, `POST .../import-csv`, `GET .../lookup`, `POST .../capping/reliance-evaluate` | `tbl_commission_rate_grid` | `test_f17b_086_commission_grids_and_reliance_capping` | Yes | Yes | Yes | N/A | `VERIFIED_HARDENED` | None |
| `F-17B-087` | Remaining / Shortfall Cash Premium Ledger & Cashier Approval | `P2` | `SHOULD` | `HARDENED` | `BLL_RemainingPendingCash` L7769–7825, `adm_LockCashEntry1.aspx.cs` | `POST /api/v1/payments/remaining-cash`, `GET .../remaining-cash`, `POST .../remaining-cash/{id}/approve` | `tbl_remainingpendingcash` | `test_f17b_087_remaining_pending_cash_lifecycle` | Yes | Yes | Yes | N/A | `VERIFIED_HARDENED` | None |
| `F-17B-088` | Insurer B2B Sales Invoice Registration & Advance Adjustment | `P2` | `SHOULD` | `HARDENED` | `BLL_Loan` L8094–8149 (`API_salesregistration`, `BLL_UpdateCompanyAdvMaster`) | `POST /api/v1/accounting/sales-registrations`, `GET .../sales-registrations`, `POST .../{id}/adjust-advance` | `tbl_salesregistration`, `tbl_account` | `test_f17b_088_and_099_sales_registration_and_office_expenses` | Yes | Yes | Yes | N/A | `VERIFIED_HARDENED` | None |
| `F-17B-089` | Multi-Provider Vehicle RC Adapter (`APIClub`, `Signzy`, `Attestr`) | `P3` | `ENHANCE` | `HARDENED` | `VehicleNoDetails.cs` L15–100, `Web.config` (`Attestr`) | `GET /api/v1/integrations/vehicle-rc/providers`, `POST .../vehicle-rc/lookup`, `AttestrRCProvider` | `tbl_vehiclenorc_details` | `test_f17b_089_095_096_097_attestr_cashback_targets_and_sub_agents` | Yes | Yes | N/A | Yes | `VERIFIED_ENHANCED` | None |
| `F-17B-090` | Automated Daily InstaPay Authority Summary Email (`SendMailToAutority`) | `P3` | `ENHANCE` | `HARDENED` | `SendMailToAutority.aspx.cs` L38–120 (`sp_InstapayReport`) | `GET /api/v1/reports/operations/instapay-authority-summary`, `POST .../dispatch` | `tbl_idealpaymentreceipt` | `test_f17b_085_and_090_ideal_receipts_instapay_and_authority_summary` | Yes | Yes | Yes | Yes | `VERIFIED_ENHANCED` | None |
| `F-17B-091` | Vehicle Break-In Inspection Coordinator Request Queue | `P2` | `SHOULD` | `HARDENED` | `View_InspectionCordinatorRequest.aspx.cs` L39–195, `BLL_InspectionRequest` | `POST /api/v1/inspections`, `GET /inspections`, `GET /inspections/pending-count`, `POST /inspections/{id}/decision` | `tbl_inspectionrequest`, `tbl_transactionappnew` | `test_f17b_091_inspection_coordinator_queue_and_decision` | Yes | Yes | N/A | N/A | `VERIFIED_HARDENED` | None |
| `F-17B-092` | Internal IT / Operator / Admin Support Ticketing Portal | `P2` | `SHOULD` | `HARDENED` | `BLL_SupportPortal` L8840, `DAL_SupportPortal` L44720 | `GET /api/v1/admin/support-tickets/types`, `POST .../support-tickets`, `GET .../support-tickets`, `GET .../counts`, `POST .../{id}/remarks`, `PATCH .../{id}/status` | `tbl_supportapp` | `test_f17b_092_support_ticketing_portal_lifecycle` | Yes | Yes | N/A | N/A | `VERIFIED_HARDENED` | `FIND-18B-002` (`P3`) |
| `F-17B-093` | Telecalling Lead Import, Call Disposition & Follow-Up CRM | `P2` | `SHOULD` | `HARDENED` | `BLL_CallingImportToExcel` L5050–5139, `Calling_CallStatusDetails.aspx.cs` | `GET /api/v1/renewals/telecalling/statuses`, `POST .../leads/import`, `GET .../leads`, `POST .../leads/{id}/assign`, `POST .../leads/{id}/dispositions` | `tbl_callingimportdata` | `test_f17b_093_and_098_telecalling_crm_and_gps_check_in` | Yes | Yes | N/A | N/A | `VERIFIED_HARDENED` | None |
| `F-17B-094` | Multi-Insurer Quotation Request & PDF File Sharing Workflow | `P2` | `SHOULD` | `HARDENED` | `Service.asmx.cs` (`InsertAppRequestedQuotation1`, `AppSelectRequestedQuotationfile1`) | `POST /api/v1/quotations/requests/{id}/requested-files`, `GET .../requested-files` | `tbl_app_requestedquotationfile`, `tbl_app_quotationrequest` | `test_f17b_094_requested_quotation_files_workflow` | Yes | Yes | N/A | N/A | `VERIFIED_HARDENED` | `FIND-18B-002` (`P3`) |
| `F-17B-095` | Cashback & Promotional Scheme Entry (`BLL_CashBackAmount`) | `P3` | `ENHANCE` | `HARDENED` | `BLL_CashBackAmount` L7130, `DAL_CashBackAmount` L36775 | `POST /api/v1/commissions/cashbacks`, `GET /api/v1/commissions/cashbacks` | `tbl_cashback` | `test_f17b_089_095_096_097_attestr_cashback_targets_and_sub_agents` | Yes | Yes | Yes | N/A | `VERIFIED_ENHANCED` | None |
| `F-17B-096` | Sales Target vs. Achievement & Contest Reward Tracking | `P3` | `ENHANCE` | `HARDENED` | `API_Targetnew`, `BLL_Target`, `Clerk/Target*.aspx.cs` | `POST /api/v1/reports/targets`, `PUT /api/v1/reports/targets/{id}`, `GET /api/v1/reports/targets` | `tbl_target` | `test_f17b_089_095_096_097_attestr_cashback_targets_and_sub_agents` | Yes | Yes | Yes | N/A | `VERIFIED_ENHANCED` | None |
| `F-17B-097` | Sub-Agent Secondary Hierarchy & Split Payout | `P3` | `ENHANCE` | `HARDENED` | `Clerk/Agent*.aspx.cs`, `BLL_Agent` | `POST /api/v1/agents/{id}/sub-agents`, `GET .../{id}/sub-agents`, `POST .../{id}/sub-agents/calculate-split` | `tbl_agent` (`ParentAgentId`, `SubAgentSplitPercent`) | `test_f17b_089_095_096_097_attestr_cashback_targets_and_sub_agents` | Yes | Yes | Yes | N/A | `VERIFIED_ENHANCED` | `FIND-18B-002` (`P3`) |
| `F-17B-098` | Field Executive GPS Check-In & Google Maps Reverse Geocoding | `P3` | `ENHANCE` | `HARDENED` | `Clerk/Location.aspx.cs` L48–106, `API/GeoLocationClasses.cs` | `POST /api/v1/integrations/geo/check-in`, `GET /api/v1/integrations/geo/check-ins` | `tbl_callingimportdata` | `test_f17b_093_and_098_telecalling_crm_and_gps_check_in` | Yes | Yes | N/A | Yes | `VERIFIED_ENHANCED` | None |
| `F-17B-099` | Petty Office Expense & Stationary Voucher Register | `P3` | `ENHANCE` | `HARDENED` | `API_Account`, `Clerk/Expense*.aspx.cs` | `POST /api/v1/accounting/office-expenses`, `GET /api/v1/accounting/office-expenses` | `tbl_account` | `test_f17b_088_and_099_sales_registration_and_office_expenses` | Yes | Yes | Yes | N/A | `VERIFIED_ENHANCED` | None |
| `F-17B-100` | Internal HR, Attendance, Biometric & Monthly Salary Slip | `P3` | `OBSOLETE` | `OBSOLETE` | `Clerk/HR_*.aspx.cs`, `Rpt_SalarySlipMonthly.rpt` | Intentionally retired non-insurance HR module | None | N/A | Yes | N/A | N/A | N/A | `OBSOLETE` | None |
| `F-17B-101` | Legacy ASP.NET WebForms Server-Side UI State (`ViewState`, `Session`) | `P3` | `OBSOLETE` | `OBSOLETE` | `Site.Master.cs`, `Clerk.Master.cs` | Replaced by stateless JWT REST API | None | N/A | Yes | Yes | N/A | N/A | `OBSOLETE` | None |
| `F-17B-102` | Crystal Reports Binary Runtime Engine (`CrystalDecisions.*`) | `P3` | `OBSOLETE` | `OBSOLETE` | `Web.config`, `.rpt` binary runtime | Engine retired; all 8 business reports migrated in `F-17B-058`..`065` | None | N/A | Yes | Yes | N/A | N/A | `OBSOLETE` | None |
| `F-17B-103` | Plaintext Password Storage & Unauthenticated SOAP/ASMX Transport | `P3` | `OBSOLETE` | `OBSOLETE` | `Service.asmx.cs`, `Log_In.aspx.cs` | Replaced by Argon2/bcrypt + JWT RBAC (`F-17B-001`..`005`) | None | N/A | Yes | Yes | N/A | N/A | `OBSOLETE` | None |
| `F-17B-104` | Hardcoded C# Corner Tutorial Event Calendar (`ShowEventCalender`) | `P3` | `OBSOLETE` | `OBSOLETE` | `ShowEventCalender.aspx.cs` L20–65 | Proven tutorial sample code | None | N/A | Yes | N/A | N/A | N/A | `OBSOLETE` | None |
| `F-17B-105` | One-Off Local Folder File Rename Script (`adm_renamePolicyDoc`) | `P3` | `OBSOLETE` | `OBSOLETE` | `adm_renamePolicyDoc.aspx.cs` L1–54 | Proven one-off developer utility | None | N/A | Yes | N/A | N/A | N/A | `OBSOLETE` | None |
| `F-17B-106` | Commented-Out Duplicate ASMX & Page WebMethods (`21` total) | `P3` | `OBSOLETE` | `OBSOLETE` | `Service.asmx.cs`, `MIS_RequestExective.aspx.cs` | Active twins migrated; commented blocks dead | None | N/A | Yes | N/A | N/A | N/A | `OBSOLETE` | None |
| `F-17B-107` | Developer Scratch, Demo & Test WebForms Pages (`WebForm1..5`) | `P3` | `OBSOLETE` | `OBSOLETE` | `WebForm1..5.aspx.cs`, `DemoRC.aspx.cs` | Proven developer scratch pages | None | N/A | Yes | N/A | N/A | N/A | `OBSOLETE` | None |
| `F-17B-108` | Commented-Out / Empty Code-Behind WebForms Stubs (`24` files) | `P3` | `OBSOLETE` | `OBSOLETE` | `Clerk/rpt_ViewAgentGrid.aspx.cs` (`2,403` commented lines) | Proven dead stubs | None | N/A | Yes | N/A | N/A | N/A | `OBSOLETE` | None |
| `F-17B-109` | Superseded Permute Policy Parser Demo (`pdF_ExtractionDemo_new`) | `P3` | `OBSOLETE` | `OBSOLETE` | `pdF_ExtractionDemo_new.aspx.cs` L30–90 | Superseded by HiCaliber (`F-17B-048`, `083`) | None | N/A | Yes | N/A | N/A | N/A | `OBSOLETE` | None |
| `F-17B-110` | Unreferenced `OpenAI_API_Key` AppSetting in `Web.config` | `P3` | `OBSOLETE` | `OBSOLETE` | `Insurance/Web.config` | `0` C# or `.aspx` references | None | N/A | Yes | Yes | N/A | N/A | `OBSOLETE` | None |
| `F-17B-111` | Legacy VNGSMS HTTP Provider (`vngsms.com`) | `P3` | `OBSOLETE` | `OBSOLETE` | `Insurance/Web.config` | Superseded by Fast2SMS / IndiaText (`F-17B-053`) | None | N/A | Yes | N/A | N/A | N/A | `OBSOLETE` | None |
| `F-17B-112` | Synthetic Demo Dashboard (`BLL_FakeDashBoard`) | `P3` | `OBSOLETE` | `OBSOLETE` | `BLL_Operations.cs` L5009, `DAL_Operations.cs` L20777 | Superseded by real KPI dashboards (`F-17B-056`) | None | N/A | Yes | N/A | N/A | N/A | `OBSOLETE` | None |
| `F-17B-113` | Dated Backup / Duplicate Table Copies & Temp Tables (`*_bkp*`) | `P3` | `OBSOLETE` | `OBSOLETE` | `03_schema_intelligence.md` | Point-in-time DBA backup copies | None | N/A | Yes | N/A | N/A | N/A | `OBSOLETE` | None |
| `F-17B-114` | Unextracted SQL Body of `sp_UpdateTrans` (`GAP-UNK-07-001`) | `P3` | `UNKNOWN` | `UNKNOWN` | `DAL_Operations.cs` (`DAL_Transaction`) | Covered via C# DAL parameter contract (`Phase 7`); `0` fabricated SP logic | `tbl_transaction` | `test_phase7_policy_booking_api.py` | Yes | Yes | Yes | N/A | `UNKNOWN` | Safely contained |
| `F-17B-115` | Unextracted SQL Bodies of Wallet/Cheque/Commission Helper SPs | `P3` | `UNKNOWN` | `UNKNOWN` | `DAL_Wallet`, `DAL_ChequeDetails`, `04_STORED_PROCEDURES.md` | Covered via `SELECT ... FOR UPDATE` (`Phases 8–9`); `0` fabricated SP logic | `tbl_wallet`, `tbl_chequedetails` | `test_phase8_payments_wallets_api.py` | Yes | Yes | Yes | N/A | `UNKNOWN` | Safely contained |
| `F-17B-116` | Unextracted SQL Bodies of Endorsement/Claim/Master Helper SPs | `P3` | `UNKNOWN` | `UNKNOWN` | `DAL_UpdateEntry`, `DAL_Claims` | Covered via `EndorsementService`, `ClaimService`; `0` fabricated SP logic | `tbl_endorsement`, `tbl_claim` | `test_phase10_claims_endorsements_api.py` | Yes | Yes | Yes | N/A | `UNKNOWN` | Safely contained |
| `F-17B-117` | Unextracted SQL Body of `sp_PE_Update_Extraction_new` & Rating SPs | `P3` | `UNKNOWN` | `UNKNOWN` | `DAL_Operations.cs` L24107 | Covered via 59-field `PolicyParserWebhookRecord`; `0` fabricated SP logic | `tbl_calliber_policy_webhook` | `test_phase11_documents_webhooks.py`, `test_phase18a_remaining_features.py` | Yes | Yes | Yes | Yes | `UNKNOWN` | Safely contained |
| `F-17B-118` | External `InsuranceAppService` (`http://103.76.254.139:85/Service.asmx`) | `P3` | `UNKNOWN` | `OBSOLETE` | `Web References/InsuranceAppService/Reference.cs` L1–356, `ImageHandler.ashx.cs` L16 | Commented-out SOAP proxy; all 4 operations (`check_login`, `insertPolicy`, `UploadPolicyImages`, `GetImageFile`) migrated in `F-17B-001`, `022`, `027`, `051` | None | `test_phase5_auth.py`, `test_phase7_policy_booking_api.py`, `test_phase11_documents_webhooks.py` | Yes | Yes | N/A | N/A | `OBSOLETE` | Resolved in Phase 18A |
| `F-17B-119` | Unextracted SQL Bodies of Remaining `sp_*` Procedures | `P3` | `UNKNOWN` | `UNKNOWN` | `DAL_Operations.cs`, `docs/migration/phase_16_unknowns.md` | Covered via C# DAL contracts (`Phases 12–16B`); `0` fabricated SP logic | Existing tables | `test_phase12_*`..`test_phase16b_*` | Yes | Yes | N/A | N/A | `UNKNOWN` | Safely contained |
| `F-17B-120` | `18` Unreferenced Auxiliary Tables Without C# Model or DDL | `P3` | `UNKNOWN` | `UNKNOWN` | `03_DATABASE_SCHEMA_AUDIT.md` L4–6 | `0` C# callers; `0` fabricated tables | None | N/A | N/A | N/A | N/A | N/A | `UNKNOWN` | Safely contained |

---

## 24. Part 22 — Findings Register

| Finding ID | Severity | Category | Location | Description & Evidence | Impact |
| :--- | :---: | :--- | :--- | :--- | :--- |
| **`FIND-18B-001`** | **`P3`** | Documentation Metric Accuracy | `docs/migration/PHASE_18A_IMPLEMENTATION_REPORT.md` (`L8`, `L36`, `L118`) | `PHASE_18A_IMPLEMENTATION_REPORT.md` states `301` mounted ASGI routes (`257` baseline + `44` Phase 18A routes). Independent inspection of `app.main:app` shows Phase 18A actually added **`51` new `APIRoute` endpoints** (`50` in `app/api/v1/endpoints/phase18a.py` + `1` in `app/api/v1/endpoints/integrations.py`), bringing total `app.routes` to **`308`** (`304` `APIRoute`s + `4` built-in OpenAPI/docs routes). | Documentation-only count understatement (`+7` more routes actually implemented than claimed). Zero runtime or functional defect. |
| **`FIND-18B-002`** | **`P3`** | Defense-in-Depth Object Ownership | `app/api/v1/endpoints/phase18a.py` (`L730`, `L854`, `L887`) | Endpoints `POST /api/v1/admin/support-tickets/{support_id}/remarks`, `POST /api/v1/quotations/requests/{quotation_id}/requested-files`, and `POST /api/v1/agents/{agent_id}/sub-agents` enforce JWT authentication (`Depends(get_current_user)`), which hardens legacy's unauthenticated ASMX WebMethods, but do not restrict an `AGENT` role from passing another agent's `agent_id` or `support_id`. | Low risk (`P3`): All high-impact financial/admin mutations already enforce `require_roles(*FINANCE_AND_ADMIN_ROLES)` or `require_roles(*BACKOFFICE_WRITE_ROLES)`. |
| **`FIND-18B-003`** | **`P3`** | Database Schema Convention | `alembic/versions/b18a0c5d1801_phase_18a_remaining_legacy_features.py` | In keeping with the legacy MySQL schema convention across Phases 3–16B, the 8 new Phase 18A tables index foreign-key integer columns (`ix_tbl_*`) and validate parent entity existence in `Phase18AService` rather than enforcing DB-level `FOREIGN KEY` constraints. | Intentional compatibility design (`P3` observation) so legacy/imported rows with `0` or historical IDs do not fail constraint checks. |

- **`P0` Count:** `0`
- **`P1` Count:** `0`
- **`P2` Count:** `0`
- **`P3` Count:** `3`

---

## 25. Risk Register

| Risk ID | Risk Description | Likelihood | Impact | Mitigation Verified |
| :--- | :--- | :---: | :---: | :--- |
| `RISK-18B-01` | Accidental connection to legacy production database (`brahmainsurance`) | Zero | Critical | Blocked by `Settings.validate_database_url_safety` and `validate_storage_safety` in `app/core/config.py` (`L96–141`). Verified `ACTIVE_DB: reliable_insurance_dev`. |
| `RISK-18B-02` | Accidental staging or modification of embedded legacy source (`./InsurancefinalNew_2026_09_23/`) | Low | High | Verified `?? InsurancefinalNew_2026_09_23/` is untracked and unmodified (`0` modified, `0` staged). During commit/release, stage only explicit FastAPI paths (`app/`, `alembic/`, `tests/`, `docs/`). |
| `RISK-18B-03` | External API calls during automated test runs | Zero | Medium | All external providers (`RC_PROVIDER_TYPE`, `HICALIBER_PROVIDER_TYPE`, `GEOCODE_PROVIDER_TYPE`, `SMS_PROVIDER_TYPE`, `PUSH_PROVIDER_TYPE`, `EMAIL_PROVIDER_TYPE`) default to `"mock"` in `app/core/config.py`. |
| `RISK-18B-04` | Unextracted SQL bodies for the 6 preserved `UNKNOWN` groups (`F-17B-114`..`117`, `119`, `120`) | Low | Low | All active C#-referenced workflows are implemented from verified C# DAL parameter contracts; zero behavior was guessed or fabricated. |

---

## 26. Part 24 — Commit Readiness

- **`P0` Blockers:** `0`
- **`P1` Blockers:** `0`
- **`P2` Findings:** `0`
- **`P3` Findings:** `3` (documented in Section 24)
- **All `82 / 82` `MUST` Features Verified:** Yes
- **All `10 / 10` `SHOULD` Features Verified:** Yes
- **All `7 / 7` `ENHANCE` Features Verified:** Yes
- **All `15 / 15` `OBSOLETE` Items Verified:** Yes
- **All `6 / 6` `UNKNOWN` Items Safely Contained:** Yes
- **Automated Test Suite:** `423 / 423 PASSED`
- **`LBR-069` Freeze:** `UNTOUCHED`

**Commit Readiness Decision:** **`COMMIT READY`** *(or `COMMIT READY WITH DOCUMENTED P2/P3` per Section 24)*.
*(In strict compliance with Phase 18B rules, no `git add`, `git commit`, or `git push` was executed during this audit).*

---

## 27. Part 23 — Final Verdict

- **PHASE 18B AUDIT VERDICT:** **`GREEN`**
- **LEGACY $\leftrightarrow$ FASTAPI BUSINESS CAPABILITY PARITY:** **`VERIFIED`** (`99 / 99` actionable capabilities — `82 MUST` + `10 SHOULD` + `7 ENHANCE` — verified in FastAPI; `15 OBSOLETE` retired; `6 UNKNOWN` DB-only artifacts safely preserved with `0` fabrication).

---

## 28. Exact Next Steps (For Release / Commit Checkpoint)

1. **Stage Only FastAPI & Migration Documentation Files (Never Stage `./InsurancefinalNew_2026_09_23/`):**
   ```powershell
   git add app/ alembic/ tests/ docs/migration/
   ```
2. **Verify Staged Tree & Whitespace Cleanliness:**
   ```powershell
   git status --short
   git diff --cached --check
   ```
3. **Commit & Push Phase 18A + 18B Release Checkpoint (Only When Authorized by User):**
   - Commit on branch `tejas-feature` and push to `origin/tejas-feature`.
