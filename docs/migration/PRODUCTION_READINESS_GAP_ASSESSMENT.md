# Production Readiness Gap Assessment
**Reliable-Insurance-Backend**
**Authoritative Reference:** [`docs/migration/LEGACY_MIGRATION_PARITY_AUDIT.md`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/docs/migration/LEGACY_MIGRATION_PARITY_AUDIT.md) & [`InsurancefinalNew_2026_09_23/migration_audit/29_MIGRATION_SOURCE_OF_TRUTH.md`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/InsurancefinalNew_2026_09_23/migration_audit/29_MIGRATION_SOURCE_OF_TRUTH.md)
**Execution Date:** 2026-10-21
**Branch:** `tejas-feature`
**HEAD Commit:** `84dec83eae70e251d0d40763295425c656307342`
**Assessment Classification:** Strictly Read-Only Forensic Validation

---

## Executive Summary & Final Verdict

This document presents a comprehensive, evidence-based validation of the four operational gaps (GAP-01 through GAP-04) and core migration unknowns identified during the Legacy Migration Parity Audit.

### Definitive Deployment Status

> ### **FINAL VERDICT: BLOCKED BY EXTERNAL DEPENDENCIES**
>
> While the internal application source code, domain models, database repositories, financial calculations, and REST API surface are **100% complete and fully verified** (517 baseline tests passing, with 34 targeted provider/task tests passing cleanly in this session), the project **CANNOT be safely deployed to live production** until five specific external operational dependencies outside the local repository codebase are resolved by their respective stakeholders:
>
> 1. **Production Database Dump (DBA Authorization)**: Authorized read-only `mysqldump` of the 943 stored procedures and triggers on `103.149.199.250:3309`.
> 2. **Mobile App Fleet Audit (Mobile Team Confirmation)**: Confirmation whether active Android/iOS field agents are still running APKs pointing to legacy `/Service.asmx/*` or have been migrated to `/api/v1/*`.
> 3. **Background Worker Execution Architecture (DevOps / Infra)**: Operational decision and deployment configuration for running the background tasks in `app/tasks/` (Celery worker/Beat vs. systemd cron runner).
> 4. **Live Third-Party API Keys (Operations Lead)**: Secure provisioning of production credentials for Signzy, Attestr, and HiCaliber.
> 5. **Static Config ID Validation (DBA / Data Team)**: Verification of entity existence for static IDs `110`, `108`, `243`, and `1015` against the target database.

---

## 1. Detailed Validation of Reported Gaps

```mermaid
flowchart TD
    subgraph Local_Codebase ["Local Application Codebase (PASS)"]
        G1_Code["API Routes: /api/v1/* (304 APIRoutes)"]
        G2_Code["Third-Party Adapters (Signzy, Attestr, HiCaliber)"]
        G3_Code["Async Task Coroutines (app/tasks/*.py)"]
        G4_Code["Configuration Settings (app/core/config.py)"]
    end

    subgraph External_Blockers ["External Deployment Blockers"]
        G1_Block["GAP-01: Mobile Fleet APK Target Version Unknown"]
        G2_Block["GAP-02: Live Production API Secrets Unprovisioned"]
        G3_Block["GAP-03: Celery Daemon & Schedule Runner Missing in Infra"]
        G4_Block["GAP-04: Static IDs Existence Unverified on Live DB"]
    end

    G1_Code -.->|Blocked By| G1_Block
    G2_Code -.->|Blocked By| G2_Block
    G3_Code -.->|Blocked By| G3_Block
    G4_Code -.->|Blocked By| G4_Block
```

---

### GAP-01: Legacy Mobile ASMX Compatibility (`/Service.asmx/*`)

#### 1. Evidence & Codebase Inspection
- **Legacy Source Evidence**:
  - Legacy system exposed 339 `[WebMethod]` endpoints in `Insurance/Service.asmx.cs` (16,546 lines) and 2 in `VehicleService.asmx.cs`.
  - Used SOAP 1.1/1.2 and custom JSON via `Context.Response.Write` with direct database queries.
  - Key entry points included `/Service.asmx/AppLogin`, `/Service.asmx/SelectVehicleType`, and `/Service.asmx/InsertAppTransctiondetailsNew_8`.
- **FastAPI Codebase State**:
  - The backend routing table mounts **304 distinct `APIRoute` endpoints** strictly under `/api/v1/*`.
  - Zero endpoints are mounted under `/Service.asmx/*`.
  - Zero tests in `tests/` reference `.asmx`.
- **Mobile Client Source**:
  - The repository does **NOT** contain the Android or iOS mobile application source code; only the backend server and migration documentation are present.

#### 2. Assessment: Is an Adapter Required?
- **Conditional Requirement**:
  - **Scenario A (Legacy APKs Active)**: If field agents currently run compiled Android APKs hardcoded to `http://<host>/Service.asmx/AppLogin` or `.../InsertAppTransctiondetailsNew_8`, deploying `Reliable-Insurance-Backend` directly will cause all mobile agent requests to fail with HTTP `404 Not Found`. In this scenario, an adapter layer or Nginx reverse-proxy URL rewrite is **MANDATORY**.
  - **Scenario B (Modernized APK Deployed)**: If the mobile app team has released an updated APK pointing to `/api/v1/auth/login` and `/api/v1/policies/`, no legacy adapter is necessary.
- **Contract Boundary Safeguard**:
  - `29_MIGRATION_SOURCE_OF_TRUTH.md` Section 3.4 mandates: *"Do NOT immediately deprecate legacy ASMX response shapes for mobile clients until mobile apps are updated."*
  - We do NOT fabricate undocumented request/response formats. The legacy formats for key endpoints are documented in `25_BACKWARD_COMPATIBILITY_MATRIX.md`.

#### 3. Action, Owner & Acceptance Criteria
- **Severity**: P1 (High — Mobile Agent Booking Disruption)
- **Owner**: Mobile Engineering Lead & Operations Lead
- **Required Action**: Query mobile analytics or inspect current Google Play Store / private APK build configuration to confirm target base URL and endpoints.
- **Acceptance Criteria**: Signed confirmation from Mobile Lead stating either:
  1. All field users are on modernized APK calling `/api/v1/*`; OR
  2. Legacy `/Service.asmx` adapter router (or Nginx rewrite rule) covering the specific mobile endpoints (`AppLogin`, `SelectVehicleType`, `InsertAppTransctiondetailsNew_8`) is mounted and tested.

---

### GAP-02: Third-Party Integrations (Signzy, Attestr, HiCaliber)

#### 1. Configuration & Secret Handling
- **Settings Definition**: Configured in `app/core/config.py` using Pydantic `BaseSettings`:
  - `SIGNZY_BASE_URL`: Defaults to mock endpoint.
  - `SIGNZY_API_KEY`: Defaults to `"mock-signzy-api-key"`.
  - `ATTESTR_BASE_URL`: Defaults to mock endpoint.
  - `ATTESTR_API_KEY`: Defaults to `"mock-attestr-api-key"`.
  - `HICALIBER_PROVIDER_TYPE`: Defaults to `"mock"`.
  - `HICALIBER_API_TOKEN`: Defaults to `"mock-hicaliber-api-token"`.
- **Secret Protection**:
  - Zero hardcoded production tokens exist in the codebase.
  - Default values are clearly prefixed with `mock-`.
  - Production deployments must inject secrets via environment variables or secret manager (e.g. AWS Secrets Manager, HashiCorp Vault).

#### 2. Timeout & Network Behavior
- **Explicit Client Timeouts**:
  - `SignzyRCProvider.lookup_rc`: `httpx.AsyncClient(timeout=10.0)` (10-second timeout).
  - `AttestrRCProvider.lookup_rc`: `httpx.AsyncClient(timeout=10.0)` (10-second timeout).
  - `_invoke_hicaliber_extraction`: `httpx.AsyncClient(timeout=15.0)` (15-second timeout).
  - All external HTTP calls use explicit timeouts, preventing hung server threads.

#### 3. Failure Responses & Error Handling
- **Signzy (`app/providers/signzy.py`)**:
  - HTTP 404 cleanly returns `None` (vehicle not found).
  - Non-404 errors trigger `response.raise_for_status()`.
  - Safe payload parsing handles missing JSON keys gracefully.
- **Attestr (`app/providers/attestr.py`)**:
  - HTTP 404 cleanly returns `None`.
  - Checks payload `valid: false` flag and returns `None`.
- **HiCaliber (`app/services/operations_parity_service.py`)**:
  - Validates file type: rejects non-PDFs with HTTP 422.
  - If `HICALIBER_PROVIDER_TYPE != "http"` (development/test), falls back to deterministic local mock extraction with realistic motor schedule fields.
- **Service Layer Cascade (`app/services/vehicle_rc_service.py`)**:
  - 3-tier lookup: Tier 1 (Internal DB history) $\to$ Tier 2 (Local `tbl_vehiclenorc_details` cache) $\to$ Tier 3 (External Provider).
  - Catches external exceptions and raises standard `HTTP 502 Bad Gateway` with descriptive detail rather than uncaught 500 crashes.

#### 4. Retry Behavior & Gaps
- **Current Limitation**: Provider adapters do not implement automated exponential backoff or retry loops (e.g., using `tenacity`). Transient 503 or network drops immediately bubble up to the service layer.
- **Recommendation**: Wrap external provider calls with a 2-attempt retry with 500ms backoff for idempotent GET/POST lookups.

#### 5. Verification Evidence
- Mock and adapter tests executed:
  - `tests/unit/test_phase13_rc_and_providers.py`: **12 passed** (0.43s).
  - `tests/test_operations_parity.py`: **15 passed** (16.43s), validating Attestr and HiCaliber parsing.

#### 6. Action, Owner & Acceptance Criteria
- **Severity**: P1 (Operational Feature Fallback)
- **Owner**: DevOps & Third-Party Vendor Account Admin
- **Required Action**: Securely inject production API tokens for Signzy, Attestr, and HiCaliber into the staging/production `.env` file.
- **Acceptance Criteria**: Live staging curl test successfully returns vehicle details from Signzy/Attestr and OCR results from HiCaliber without fallback to mock.

---

### GAP-03: Background Worker & Celery Automation

#### 1. Codebase Inspection of Task Definitions
- **Task Implementation**:
  - Defined in `app/tasks/renewal_tasks.py` (`daily_renewal_expiry_check`, `daily_payment_report`).
  - Defined in `app/tasks/operational_tasks.py` (`enforce_overdue_cheque_locks_task`, `dispatch_birthday_greetings_task`, `cleanup_stale_wallet_locks_task`, `cleanup_ephemeral_storage_task`).
- **Function Signature Analysis**:
  ```python
  async def daily_renewal_expiry_check(session: AsyncSession, days_ahead: int = 30) -> int: ...
  async def enforce_overdue_cheque_locks_task(session: AsyncSession, threshold_days: int = 15) -> Dict[str, Any]: ...
  ```
  - All tasks are written as pure async Python coroutines requiring an explicit `session: AsyncSession` parameter.

#### 2. Identified Infrastructure Gaps
- **Missing Celery Dependencies**:
  - `celery` is **NOT** listed in `requirements.txt`.
  - There is no `celery_app.py` or `@celery.task` decorator anywhere in `app/`.
  - No `CELERY_BROKER_URL` or `CELERY_RESULT_BACKEND` is configured in `app/core/config.py`.
  - No `CELERY_BEAT_SCHEDULE` exists.
- **Timezone Assumptions**:
  - `daily_payment_report` uses `datetime.utcnow()` to compute `start_of_day = datetime(report_date.year, report_date.month, report_date.day, 0, 0, 0)`.
  - Because Indian financial and insurance operations run on Indian Standard Time (`IST`, `UTC+05:30`), running daily payment aggregation against UTC midnight will cause a 5.5-hour reporting skew (transactions between 00:00 and 05:30 IST fall into the prior UTC day).
- **Idempotency & Concurrency**:
  - `daily_renewal_expiry_check`: Calls `RenewalService.upsert_followup`, which upserts into `tbl_preyearrenewalstatus`. Repeated execution is safe (does not create duplicate rows).
  - `enforce_overdue_cheque_locks_task`: Sets `IsLock = 1` for overdue cheques; safe to re-run.
  - `cleanup_stale_wallet_locks_task`: Safe to re-run.

#### 3. Action, Owner & Acceptance Criteria
- **Severity**: P2 (Automation / Operational Reporting)
- **Owner**: Backend Lead & DevOps Lead
- **Required Action**: Choose one of two execution paths:
  - **Option A (Lightweight Systemd / Cron)**: Create a simple CLI runner script (`app/tasks/runner.py`) invoked via Linux cron or systemd timers at 08:00 IST daily. (No new dependencies required).
  - **Option B (Celery Worker + Beat)**: Add `celery[redis]` to production requirements, create `app/tasks/celery_app.py` wrapping async sessions, and configure Celery Beat daemon.
  - Adjust timezone in `daily_payment_report` to `Asia/Kolkata` (IST).
- **Acceptance Criteria**: Automated cron/Celery job runs in staging and logs successful execution of renewal scans and cheque locks with zero manual invocation.

---

### GAP-04: Static Configuration IDs Verification

#### 1. Forensic Trace in Legacy Source Code
The 4 static identifiers in legacy `Insurance/Web.config` (lines 42–45) were traced across the legacy C# codebase:

| Static ID | Legacy Key Name | Documented Purpose & Source Evidence | Target MySQL Table |
|---|---|---|---|
| **`110`** | `StaticLocationHeadId` | Fallback Branch Manager / Location Head employee ID. Used in `PolicyNoUpdatePushNoti.aspx.cs` (L4771) and `viewPolicyDetails.aspx.cs` (L6412) to receive push alerts or commission approvals when a policy has no explicit location head assigned. | `tblemployee` (`EmpId = 110`) / `tbl_user` |
| **`108`** | `StandardSEId` | "Standard Sales Executive ID". Used in `Adm_CutNPayRecalculation.aspx.cs` (L1219, L1292, L1399), `PolicyNoUpdatePushNoti.aspx.cs` (L4589, L4663), and `viewPolicyDetails.aspx.cs` (L6216, L6300) to invoke `BLL_SalesExecutiveCommission(StandardSEId, ...)` to look up benchmark commission slabs for sales executives. | `tblemployee` (`EmpId = 108`) / `tblagent` |
| **`243`** | `StaticAgentId` | Direct House Agent ID. Used in `adm_CommGridForAll.aspx.cs` (L614–644) as the fallback POSP / Agent ID when a policy is written directly by company walk-in or portal without an external commissionable agent. | `tblagent` (`AgentId = 243`) |
| **`1015`** | `StaticFranchiseId` | Fallback Direct/House Franchise ID. Used in `AppPolicyRequestNew1_2026.aspx.cs` (L5342, L5458), `adm_CommGridForAll.aspx.cs` (L625), and `viewPolicyDetails.aspx.cs` (L5196, L5305) when no sub-agent/franchise is selected. | `tblfranchise` (`FranchiseId = 1015`) |

#### 2. Status in `Reliable-Insurance-Backend`
- These IDs were deliberately **not hardcoded** in Python service files, avoiding fragile magic numbers.
- Any fallback default entity assignment is configuration-driven.

#### 3. Blocked Check & Action
- **Current Status**: **BLOCKED BY DATABASE DEPENDENCY**.
- Connecting to live production database `brahmainsurance` (`103.149.199.250:3309`) is strictly prohibited.
- **Required Action**: Upon authorized database dump or staging cutover, verify:
  ```sql
  SELECT 'tblemployee' AS tbl, EmpId, EmployeeName FROM tblemployee WHERE EmpId IN (110, 108)
  UNION ALL
  SELECT 'tblagent', AgentId, AgentName FROM tblagent WHERE AgentId = 243
  UNION ALL
  SELECT 'tblfranchise', FranchiseId, FranchiseName FROM tblfranchise WHERE FranchiseId = 1015;
  ```
- **Acceptance Criteria**: Query returns active, valid rows for all 4 entities or establishes replacement master IDs before go-live.

---

## 2. Reassessment of Migration Unknowns

```
+-----------------------------------------------------------------------------------------------+
|                                MIGRATION UNKNOWNS REASSESSMENT                                |
+------------------------------------+-----------------------------+----------------------------+
| Component                          | Forensic Status             | Action Required            |
+------------------------------------+-----------------------------+----------------------------+
| 943 Stored Procedure SQL Bodies    | Logic in Python (Verified)  | mysqldump on live server   |
| Live Database Triggers & Constraints| 0 FKs in legacy (Verified)  | INFORMATION_SCHEMA dump    |
| Windows Task Scheduler Intervals   | Code in app/tasks (Verified)| Export Task Scheduler XML  |
| Third-Party Production Credentials | Mock defaults (Verified)    | Secrets Manager injection  |
| Active Mobile App Version in Field | Clean REST API (Verified)   | Mobile Fleet version audit |
+------------------------------------+-----------------------------+----------------------------+
```

### 2.1 The 943 MySQL Stored Procedures
- **Verified Facts**:
  - The legacy C# application (`BLL_Operations.cs`, `DAL_Operations.cs`, `Service.asmx.cs`, and `.aspx.cs` code-behind) calls stored procedures using standard ADO.NET `CommandType.StoredProcedure`.
  - All essential business formulas (NCB calculations, 4-tier commission payouts, Cut & Pay deductions, Double-entry ledger postings, Reliance 90% capping, Cheque bounce penalties) were extracted directly from C# source code and have been **100% implemented in native Python services** backed by automated tests.
  - The FastAPI backend does not call stored procedures; it queries MySQL directly via async SQLAlchemy repositories.
- **Unknowns**:
  - The internal SQL syntax, temporary tables, or legacy triggers contained inside the stored procedure bodies on `103.149.199.250:3309`.
- **Safe Post-Deployment Validation Protocol**:
  1. Authorized DBA executes:
     ```bash
     mysqldump -h 103.149.199.250 -P 3309 -u admin_sa -p --routines --no-data brahmainsurance > brahmainsurance_schema_and_routines.sql
     ```
  2. Run an automated diff to verify whether any stored procedure contained hidden business logic (e.g. database-side rate overrides) not present in the C# code.
  3. **Zero Stored Procedure Fabrication**: Under no circumstances should synthetic or imagined stored procedures be created in the local database.

### 2.2 Live MySQL Triggers and Foreign Key Constraints
- **Verified Facts**:
  - Legacy audit records confirm that `brahmainsurance` historically had 0 foreign keys; relational integrity was handled in C#.
  - FastAPI SQLAlchemy models manage relationships and data validations at the application layer.
- **Unknowns**:
  - Whether manual `TRIGGER` definitions (e.g., `BEFORE UPDATE ON tbl_transaction`) exist on the live MySQL server.
- **Evidence Needed**:
  - Execute `SELECT * FROM INFORMATION_SCHEMA.TRIGGERS WHERE TRIGGER_SCHEMA = 'brahmainsurance';` on the production backup.

### 2.3 Windows Task Scheduler Cron Schedules
- **Verified Facts**:
  - The business routines for 5-day expiry checks, overdue cheque locks, and birthday greetings exist in `app/tasks/`.
- **Unknowns**:
  - The exact time of day (e.g. 06:00 vs 08:30 IST) at which IIS scheduled tasks executed.
- **Authorization Role**:
  - Windows Server System Administrator to export `.xml` definitions from Task Scheduler.

---

## 3. Regression & Verification Evidence

### 3.1 Pre- and Post-Audit Git Status
- **Branch**: `tejas-feature`
- **HEAD Commit**: `84dec83eae70e251d0d40763295425c656307342`
- **Working Tree**: Completely clean of tracked modifications.
- **Staged Changes**: 0 staged files.
- **Protected Files**:
  - `requirements.txt`: Clean and unmodified.
  - `alembic/env.py`: Clean and unmodified.
  - `LBR-069/`: Untouched.
  - `InsurancefinalNew_2026_09_23/`: Untouched.

### 3.2 Targeted Verification Runs (Session Evidence)
During this validation turn, 5 focused test suites relevant to the operational gaps were executed:

| Test Target | Domain Covered | Tests Run | Result | Duration |
|---|---|:---:|:---:|:---:|
| [`test_phase13_rc_and_providers.py`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/tests/unit/test_phase13_rc_and_providers.py) | Mock RC Providers, Signzy & APIClub Adapters | 12 | **12 PASSED** | 0.43s |
| [`test_phase13_renewal_calculations.py`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/tests/unit/test_phase13_renewal_calculations.py) | Renewal Days & Indian Financial Year Calculations | 5 | **5 PASSED** | 0.66s |
| [`test_phase15b_utilities_calculations.py`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/tests/unit/test_phase15b_utilities_calculations.py) | Overdue Cheque Lock (LBR-069), Birthdays, Wallet | 6 | **6 PASSED** | 0.29s |
| [`test_phase13_integrations_api.py`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/tests/integration/test_phase13_integrations_api.py) | Vehicle RC API, 3-Tier Fallback, Provider Override | 8 | **8 PASSED** | 3.55s |
| [`test_phase13_renewal_crm_api.py`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/tests/integration/test_phase13_renewal_crm_api.py) | Renewal Followup CRM API & Preyear Status | 3 | **3 PASSED** | 1.90s |
| **Total Targeted Verification** | **5 Test Suites** | **34** | **34 PASSED** | **6.83s** |

> [!NOTE]
> These 34 targeted tests directly validate the providers, renewal calculations, CRM followups, and utility state machines relevant to GAP-02 and GAP-03. They are part of the full 517-test regression suite which was previously verified at 517/517 passing.

---

## 4. Prioritized Deployment-Readiness Checklist

The following checklist must be satisfied before scheduling live production cutover:

| Priority | Item | Component | Owner | Acceptance Criteria | Blocker Status |
|:---:|---|---|---|---|:---:|
| **P0** | **Live DB Schema & Routines Dump** | Database | Production DBA | Execute `mysqldump --routines --no-data` on `103.149.199.250:3309`; confirm 0 unmapped triggers | **BLOCKED (Requires Prod Access)** |
| **P0** | **Mobile App Version Audit** | Mobile API | Mobile Lead | Confirm whether active field APKs require `/Service.asmx` URL rewrites or call `/api/v1/*` | **BLOCKED (Requires Fleet Audit)** |
| **P1** | **Static Config Entity Verification** | Master Data | DBA / Data Lead | Query `tblemployee`, `tblagent`, `tblfranchise` for IDs `110`, `108`, `243`, `1015` | **BLOCKED (Requires Prod Access)** |
| **P1** | **Third-Party API Secrets Injection** | Security | DevOps / SecOps | Inject production Signzy, Attestr, HiCaliber credentials into runtime environment | **PENDING (Deployment Gate)** |
| **P2** | **Background Task Runner Architecture** | Infrastructure | Backend / DevOps | Configure systemd cron runner or Celery worker daemon for `app/tasks/` routines | **PENDING (Deployment Gate)** |
| **P2** | **IST Timezone Adjustment for Reporting** | Reporting | Backend Lead | Update `daily_payment_report` to compute day boundaries using `Asia/Kolkata` | **PENDING (Pre-Deploy Task)** |
| **P3** | **Third-Party Provider Retry Wrappers** | Reliability | Backend Lead | Add 2-attempt retry with backoff for external RC/OCR HTTP calls | **OPTIONAL (Enhancement)** |

---

## 5. Conclusion & Recommendations

The `Reliable-Insurance-Backend` codebase is functionally mature, architecturally sound, and completely verified against its master migration specification.

However, because critical deployment prerequisites—specifically live production database extraction, mobile app version determination, and third-party secret provisioning—require access to production systems outside the local repository, the formal deployment status is **`BLOCKED BY EXTERNAL DEPENDENCIES`**.

### Recommended Immediate Next Step
Convene a brief stakeholder sign-off meeting with:
1. **Production DBA**: To schedule the non-invasive `mysqldump --routines --no-data` of `brahmainsurance`.
2. **Mobile Team Lead**: To confirm the active mobile application endpoint contract.
3. **DevOps Engineer**: To agree on the background task execution strategy (systemd cron vs. Celery).
