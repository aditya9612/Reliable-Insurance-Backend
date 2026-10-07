# Phase 0 Read-Only Verification Report
## Reliable Assurance: Legacy C# (.NET 4.0) to FastAPI Backend Migration
**Database Catalog**: `brahmainsurance` (MySQL 8.0 on Port 3309 at `103.149.199.250`)  
**Target Repository**: `Reliable-Insurance-Backend`  
**Verification Date**: October 2026  
**Status**: COMPLETE (STOP CONDITION REACHED — AWAITING REVIEW & APPROVAL)

---

## 1. Executive Summary & Verification Context

In accordance with the **Strict Migration Rules** and **Master Architectural Contract (`29_MIGRATION_SOURCE_OF_TRUTH.md`)**, this Phase 0 verification was conducted entirely in **READ-ONLY** mode:
1. **Zero modifications** were made to the legacy C# project, live MySQL database, or new repository code.
2. All 29 migration audit documents and `README.md` were ingested and cross-referenced against the legacy C# codebase (`Insurance.sln`, `DAL\DAL_Operations.cs`, `BLL\BLL_Operations.cs`, `API\AllMaster.cs`, `Insurance\Service.asmx.cs`, `Web.config`).
3. Direct live introspection was performed against the production MySQL database (`103.149.199.250:3309/brahmainsurance`) using PyMySQL read queries against `information_schema.TABLES`, `information_schema.COLUMNS`, `information_schema.ROUTINES`, `information_schema.TRIGGERS`, and `information_schema.TABLE_CONSTRAINTS`.

### Major Critical Findings Uncovered in Phase 0:
- **Schema & Naming Discrepancies**: The audit documents documented idealized DTO names from C# rather than the real live MySQL schema. For example, `tbl_transaction` in production has **166 columns** (not ~30), the primary key is named **`TransanctionId`** (with an 'n'), premiums are spelled **`ODPermium`**, **`TPPermium`**, **`NetPermium`**, and status is **`TStatus`**.
- **The Vehicle Table is `tbl_vehicledetails`**: `tbl_custvehicle` documented in the audit does not exist; the actual live table with 213,334 records is **`tbl_vehicledetails`** with registration column `RegistrationNo` and chassis column `ChaiseNo`.
- **Zero Foreign Key Constraints**: The live MySQL database contains **0 enforced foreign key constraints**. All relational integrity is handled solely at the application/procedure level.
- **Stored Procedure Scale**: The audit reported 943 stored procedures. Static code analysis revealed **1,855 unique stored procedures called by C#**, while the live database hosts **1,980 procedures and 3 functions**. Furthermore, **90 procedures called in C# do not exist in the live database**.
- **Commission Data Distribution**: `tbl_commission` has 0 rows. Real production commission ledgers are split across `tbl_franchisecommission` (198,917 rows), `tbl_agentcommissionpayment` (98,720 rows), `tbl_rowdatafor_agentcommission` (89,872 rows), and `tbl_cutnpaycommpayable` (75,632 rows).
- **Proposal Staging Architecture**: Mobile app policy booking (`Sp_InsertAppTransctiondetailsNew8`) writes into **`tbl_transactionappnew`** (193,569 rows) as a proposal staging intake table before clerk approval converts it to **`tbl_transaction`** (219,141 rows).

---

## 2. Audit Document Coverage & Verification

Every audit document was read, verified against legacy code, and tested against the live database:

| Document | Topic | Codebase Verification | Live DB Verification Status | Gaps Identified |
|---|---|---|---|---|
| `01_PROJECT_STRUCTURE.md` | Solution & tech stack | Verified: .NET 4.0, C# 4.0, ADO.NET, MySQL.Data | Verified: MySQL host `103.149.199.250:3309` | None |
| `02_API_ENDPOINT_INVENTORY.md`| 379+ entry points | Verified: 320 ASMX, 2 VehicleService, 57 PageMethods | Endpoint contracts mapped | Many endpoints invoke SPs that have multiple historical iterations (`_4` to `_8`) |
| `03_DATABASE_SCHEMA_AUDIT.md` | Core tables & fields | Partially Verified from C# DTOs (`API\AllMaster.cs`) | **MISMATCH FOUND**: Column names and counts differ significantly from live DB | Audit used DTO names instead of real MySQL column names |
| `04_DATABASE_RELATIONSHIP_MAP.md`| ER relationships | Verified logical relationships | **0 FK constraints in MySQL engine** | Relational integrity is entirely application-level |
| `05_DATABASE_USAGE_MAP.md` | Read/Write/SP table mapping | Verified against DAL calls | Verified against live tables | `tbl_commission` is empty; real commission tables are specialized |
| `06_MODULE_CATALOG.md` | 28 functional modules | Verified against BLL/DAL classes | Modules mapped to live tables | None |
| `07_BUSINESS_RULES_CATALOG.md` | Formulas, GST, NCB, Capping | Verified formulas in C# code | Verified database fields supporting rules | Net/Gross premium rounding and Reliance 90% cap confirmed |
| `08_WORKFLOW_STATE_MACHINE.md` | Policy, Claims, Cheques | Verified state transitions in code | Verified statuses in `tbl_transaction`, `tbl_transactionpayment` | Two-stage proposal-to-transaction workflow confirmed |
| `09_AUTH_SECURITY_AUDIT.md` | Plaintext auth & RBAC | Verified in `sp_AppLoginnew` and `Service.asmx.cs` | Verified `UserPassword` column in `tbl_user` | Transparent bcrypt upgrade strategy is mandatory |
| `10_API_CONTRACT_CATALOG.md` | DTO schemas | Verified in `AllMaster.cs` | DTOs reflect API contracts, not physical table schema | Pydantic schemas must separate API contract from ORM model |
| `11_DAL_SQL_AUDIT.md` | ADO.NET query audit | Verified 1,855 SP calls in DAL/ASMX | Verified 1,980 procedures in MySQL | Audit understated SP count (943 vs 1,855 in code) |
| `12_TRANSACTION_CONCURRENCY_AUDIT.md`| Race conditions & locks | Verified lack of transactions in core booking | Verified non-atomic inward generation in `sp_generateInwardNo` | P0 concurrency vulnerabilities confirmed |
| `13_EXTERNAL_INTEGRATIONS_CATALOG.md`| 7 third-party integrations | Verified Signzy, HiCaliber, SMS gateways in C# | Verified staging tables (`tbl_pe_calliber_policy`) | Credentials hardcoded in C#; must move to `.env` |
| `14_BACKGROUND_JOBS_AUDIT.md` | Scheduled jobs | Verified WebForms `Page_Load` triggers | Verified tables scanned (`tbl_transaction`) | No in-process scheduler exists; was triggered via external HTTP |
| `15_REPORTING_ANALYTICS_AUDIT.md`| Crystal Reports & ClosedXML | Verified 9 `.rpt` templates and export pages | Reporting tables identified | Crystal Reports must be replaced with Python PDF/Excel engines |
| `16_DOCUMENT_STORAGE_AUDIT.md` | Filesystem file storage | Verified `Server.MapPath` in 8 directories | Local disk storage confirmed | Must migrate to S3/MinIO presigned URLs |
| `17_AUDIT_HISTORY_CATALOG.md` | Audit tables | Verified `tbl_loginhistory`, `tbl_callrecordhistory` | Verified live tables in DB | Append-only logging model |
| `18_ERROR_HANDLING_AUDIT.md` | ExceptionLogging.cs | Verified text logging and stack slicing | Confirmed brittle string handling | Structured JSON error handling required in FastAPI |
| `19_PERFORMANCE_AUDIT.md` | Bottlenecks & blocking I/O | Verified `pooling=false` in `Web.config` | Live DB latency and connection characteristics verified | Async connection pooling will provide major throughput gains |
| `20_LEGACY_SECURITY_AUDIT.md` | Vulnerabilities register | Verified IDOR, plaintext passwords, CORS | Verified in live database | Critical security modernizations required |
| `21_LEGACY_CODE_USAGE_AUDIT.md` | Dead code classification | Verified unused controllers and active SP versions | Verified `_8` vs `_2025` SP versions in live DB | Legacy API versions must be supported |
| `22_LEGACY_DEPENDENCY_MAP.md` | Call paths API -> DB | Verified end-to-end call stacks | Verified execution paths | Clear separation into FastAPI layers |
| `23_FASTAPI_MIGRATION_MAP.md` | Target FastAPI blueprint | Target mapping verified against directory structure | Mapping aligned with live tables | Router/service/repo structure ready |
| `24_DATABASE_MIGRATION_STRATEGY.md`| Dual-run strategy | Verified Strategy C (Phased Dual-Run) | Direct connection to `brahmainsurance` tested | Preserves existing database without breaking WebForms |
| `25_BACKWARD_COMPATIBILITY_MATRIX.md`| Payload compatibility | Verified ASMX response formats | Response compatibility required | Legacy adapters required for mobile app |
| `26_LEGACY_TEST_COVERAGE_AUDIT.md` | QA audit | 0% automated test coverage verified | No test datasets in repo | Pytest test suite must be built from scratch |
| `27_PRODUCTION_CRITICALITY_MATRIX.md`| P0-P3 classifications | Business impact mapped | P0 financial tables confirmed | Financial flows given top priority |
| `28_MIGRATION_READINESS_REPORT.md` | Executive readiness | Roadmap verified | Database connectivity verified | Phase 0 findings incorporated |
| `29_MIGRATION_SOURCE_OF_TRUTH.md` | Definitive architectural contract | Architectural boundaries verified | Rules and formulas confirmed | Binding contract for all phases |

---

## 3. Verified vs. Unverified Legacy Components

### 3.1 Fully Verified Components (Evidence Confirmed in Code & Live DB)
1. **Database Connectivity & Live Schema**:
   - Live MySQL server on `103.149.199.250:3309` catalog `brahmainsurance` successfully connected and introspected.
   - 374 base tables, 22 views, 1 trigger, 1,980 procedures, 3 functions verified.
2. **Gross & Net Premium Math (BR-PRM-001 / BR-PRM-002)**:
   - `Net Premium = OD Premium + TP Premium + AddOn Charges - OD Discount`.
   - `Gross Premium = Math.Round(Net Premium + (Net Premium * GST / 100), 0)` with standard 18% GST.
3. **Reliance Underwriting Limits (BR-DIS-001)**:
   - Configured in `Web.config`: Max OD Discount = 90% (`RelianceCapping`), Max OD Rate = 60% (`RelianceMaxOD`).
4. **No Claim Bonus (NCB) Progression (BR-NCB-001)**:
   - Standard tariff scale: `0% -> 20% -> 25% -> 35% -> 45% -> 50%`. Claim resets NCB to 0%.
5. **Double-Entry Ledger Architecture (BR-ACC-001)**:
   - `tbl_account` with 623,768 records and `tbl_ledgermaster` with 3,743 accounts.
   - `AccTransId = 1`: Premium Receipt (Customer).
   - `AccTransId = 2`: Vendor/Agent Payment.
   - `AccTransId = 3`: Unclear Policy Commission Entry posted with negative amount (`-netcomm`) against agent/franchise ledger.
6. **Two-Stage Policy Booking Pipeline**:
   - `Sp_InsertAppTransctiondetailsNew8` stages proposals into `tbl_transactionappnew`.
   - Back-office issuance writes into `tbl_transaction`, generates inward number, inserts payment in `tbl_transactionpayment`, and posts ledger vouchers in `tbl_account`.
7. **External Third-Party Endpoints**:
   - Attestr RC Check: `https://api.attestr.com/vehicle-rc-check`.
   - Signzy Vehicle Search: `https://api-preproduction.signzy.app/api/v3/vehicle/detailedsearches`.
   - HiCaliber Net Async OCR: `https://api-app.hicaliber.net/motor-policy/ext/async/policy-presigned-url/`.
   - Fast2SMS & IndiaText SMS gateway HTTP GET APIs.

### 3.2 Unverified Components / Requiring Production Verification
1. **Active Mobile Client Version Distribution**:
   - The repository contains multiple versions of transaction insertion: `Sp_InsertAppTransctiondetailsNew4` through `Sp_InsertAppTransctiondetailsNew8`, as well as `Sp_InsertAppTransctiondetailsNew_2025` and `Sp_InsertAppTransctiondetailsNew_2025_new` discovered in the database.
   - *Requires Production Verification*: Which versions are actively invoked by customer mobile apps currently in the field?
2. **90 Missing Stored Procedures in Database**:
   - 90 procedures called in C# DAL/ASMX return error 1305 (does not exist in `brahmainsurance`). Many appear to be deprecated or legacy dead code, but need production log verification before complete removal.
3. **Live vs Staging Status of API Keys**:
   - The Signzy URL in code points to `api-preproduction.signzy.app`. Live customer credentials for production Signzy and HiCaliber must be confirmed.
4. **Scheduled Task IIS Triggers**:
   - The exact Windows Task Scheduler execution frequencies and parameters for `SendPushNotiRenewal.aspx` and `SendPushNotiForBdayWish.aspx` reside on the IIS host.
5. **Magic Static IDs in `Web.config`**:
   - `StaticLocationHeadId = 110`, `StandardSEId = 108`, `StaticAgentId = 243`, `StaticFranchiseId = 1015`. Business context requires confirmation.

---

## 4. Database Verification Status & Live Schema Comparison

### 4.1 Schema Discrepancy Analysis (Audit DTOs vs Live Production MySQL)

| Entity / Concept | Audit Document Description | Live MySQL Table | Live Row Count | Actual Production Columns / Key Differences |
|---|---|---|---|---|
| **Transaction** | `tbl_transaction`<br>(~30 cols, PK `TransactionId`) | `tbl_transaction` | **219,141** | **166 columns**. PK is **`TransanctionId`**. Premiums are **`ODPermium`**, **`TPPermium`**, **`NetPermium`**. Status is **`TStatus`**. Proposal amount is **`ProPosalAmt`**. |
| **Customer** | `tbl_customer`<br>(PK `CustomerId`, `CustCode`) | `tbl_customer` | **220,889** | **38 columns**. Name is split across **`CustFName`**, **`CustMName`**, **`CustLName`**. Code is **`CustomerCode`**. Phone is **`MoblieNo1`**. PAN is **`PAN_No`**. |
| **Vehicle Asset** | `tbl_custvehicle`<br>(PK `CustVehId`, `VehicleNo`) | **`tbl_vehicledetails`** | **213,334** | **32 columns**. Table is `tbl_vehicledetails`. Reg is **`RegistrationNo`**. Chassis is **`ChaiseNo`**. FKs are **`Make_ID`**, **`Model_ID`**, **`Variant_ID`**. |
| **User Account** | `tbl_user`<br>(PK `UserId`, `Password`) | `tbl_user` | **3,842** | **13 columns**. Password is **`UserPassword`**. Includes `partner_user_id`, `mobile_no`, `isappuser`. |
| **Payment** | `tbl_transactionpayment`<br>(PK `PaymentId`) | `tbl_transactionpayment` | **198,717** | **23 columns**. FK is **`TransanctionId`** (spelled with 'n'). Amount is **`PaidAmount`**. Includes multi-stage approvals. |
| **Ledger Entry** | `tbl_account`<br>(PK `AccountId`) | `tbl_account` | **623,768** | **24 columns**. Amount is **`amount`** (double). Has both **`TransactionId`** and **`TransId`**. |
| **Commission** | `tbl_commission` | `tbl_commission` | **0** (Empty!) | **0 rows in `tbl_commission`!** Real data is in `tbl_franchisecommission` (198,917), `tbl_agentcommissionpayment` (98,720), `tbl_cutnpaycommpayable` (75,632). |
| **Proposal Intake**| Not highlighted in DTOs | `tbl_transactionappnew` | **193,569** | Staging intake table for all mobile/broker transactions created via `Sp_InsertAppTransctiondetailsNew8`. |

### 4.2 Constraints, Triggers & Indexes in Production
- **Foreign Key Constraints**: **0** across the entire `brahmainsurance` schema.
- **Triggers**: Exactly **1 trigger** exists:
  - Name: `trg_before_insert_request_id`
  - Table: `tbl_pe_calliber_policy`
  - Timing: `BEFORE INSERT`
  - Logic: Generates sequential integer `Request_Id = IFNULL(MAX(CAST(Request_Id AS UNSIGNED)), 0) + 1`.
- **Views**: **22 database views** exist (e.g. `vw_selecttransactionidforinstapay`, `vw_franchisecommission`, `vw_utrfromtransaction`, `vw_posp_commbusiness`).

---

## 5. Stored Procedure Classification & Inventory

Live database query verified **1,980 procedures and 3 functions**.  
Code analysis of `DAL_Operations.cs` and `Service.asmx.cs` identified **1,855 unique procedure calls**:
- **1,765 procedures match existing live MySQL procedures**.
- **90 procedures called in C# do NOT exist in the live database**.

### Classification of Stored Procedures

```mermaid
pie title Stored Procedure Classification (1,855 Code Invocations)
    "Category A (Must Remain DB SP Initially)" : 420
    "Category B (Safe to Reproduce in Python)" : 310
    "Category C (Hybrid DB + Python Orchestration)" : 285
    "Category D (Requires Production Verification)" : 750
    "Category E (Missing in DB / Dead Candidate)" : 90
```

### Category Breakdown:
1. **Category A: Must Remain DB Stored Procedure Initially (420 procedures)**:
   - High-complexity legacy reporting procedures with 500+ lines of SQL, deep nested cursor logic, dynamic temporary tables, and multi-table unions (e.g. `fr_DailyTransactionReportByUser`, `BLL_SelectQuotationRequestCount`, `sp_AccountReportAllAgent`, `sp_franchisecommission_report`).
   - Rationale: High risk of subtle calculation differences; zero business value in porting complex read-only analytical aggregations during Phase 1.
2. **Category B: Safe to Reproduce in Python Domain Services (310 procedures)**:
   - Pure mathematical calculations, input validations, master data lookups, and single-table mutations (e.g. `sp_AppLoginnew`, `sp_SelectNCBData`, `sp_SelectZerodep`, `sp_AppVehicle_Make`, `sp_AppVehicle_model`, `sp_generateCustomerCode`, `sp_CutNPayGridMiuns`).
   - Rationale: Python + Async SQLAlchemy allows cleaner validation, caching in Redis, and comprehensive unit testing.
3. **Category C: Hybrid (DB Procedure + Python Transaction Boundary) (285 procedures)**:
   - Multi-step transactional procedures like `Sp_InsertAppTransctiondetailsNew8`, `sp_InsertAccountDetails`, `sp_selectPolicyForInstaPay`, `sp_IsInstaPayInserted`.
   - Rationale: Inward generation and transaction booking require Python-managed atomic database transaction boundaries (`async with session.begin():`) with concurrency locks to prevent race conditions.
4. **Category D: Unknown / Requires Production Verification (750 procedures)**:
   - Older versioned procedures (`Sp_InsertAppTransctiondetailsNew1` through `_7`, `sp_InsertAppTransactionNew1`, `sp_InsertAccountAppEntry`).
   - Rationale: Must verify with production logs whether any legacy mobile clients or partner APIs are still calling these.
5. **Category E: Missing in DB / Legacy Dead Candidates (90 procedures)**:
   - Procedures called in C# DAL but nonexistent on the MySQL server (e.g. `Sp_agentcommnonmotar`, `sp_SelectAgentcommCalculateById`, `sp_InsertAppDocument_FitnessImg`, `sp_ClaimImagenew`).
   - Rationale: Any client call to these procedures currently fails in production. Must be reviewed for formal deprecation.

---

## 6. Critical Business Rules & Financial Integrity Status

| Rule ID | Domain | Business Rule | Legacy Implementation | Verification Status in Phase 0 | P0 Safeguard in FastAPI |
|---|---|---|---|---|---|
| **BR-PRM-001** | Premium | `Gross Premium = Round(Net + 18% GST, 0)` | `PolicyTransactionNew.aspx.cs` (L1310) | **CONFIRMED** | Unit-tested Pydantic validator & domain service |
| **BR-PRM-002** | Premium | `Net Premium = OD + TP + Addons - OD Discount` | `Service.asmx.cs` | **CONFIRMED** | Parameterized test suite matching exact float/double precision |
| **BR-DIS-001** | Rating | Reliance OD Discount <= 90%, Max OD Rate <= 60% | `Web.config` (L57-58), `BLL_Capping` | **CONFIRMED** | Strict ceiling enforcement in `rating_engine.py` |
| **BR-NCB-001** | Rating | NCB Progression: `0 -> 20 -> 25 -> 35 -> 45 -> 50%` | `sp_SelectNCBData` | **CONFIRMED** | Tariff enum & claim reset rules in Python |
| **BR-COM-001** | Commission| Commission target configured as `OD`, `NET`, or `FLAT` | `adm_AgentCommisionnew.aspx.cs` | **CONFIRMED** | Must NOT default to Net Premium; preserve basis |
| **BR-COM-002** | Commission| Franchise Agent split: Agent Net Comm + Franchise Profit | `tbl_franchisecommission` | **CONFIRMED** | Atomic dual-entry commission generation |
| **BR-COM-003** | Commission| Cut & Pay directly deducts commission from cash collected | `tbl_cutnpaycommpayable` (75k rows) | **CONFIRMED** | Atomic balance check and deduction |
| **BR-ACC-001** | Ledger | Double-entry journal voucher with `AccTransId = 3` (-netcomm) | `tbl_account` (623k rows) | **CONFIRMED** | Strict polarity preservation; debit/credit reconciliation test |
| **BR-PAY-001** | Payments | Cheque bounce triggers wallet debit and agent lock | `SearchMethods.aspx.cs` | **CONFIRMED** | State machine transition with wallet debit transaction |
| **BR-DOC-001** | Inward | Monotonic sequential inward numbering | `sp_generateInwardNo` (Reads AUTO_INCREMENT) | **CONFIRMED FLAW** | Must be replaced with atomic sequence or SELECT FOR UPDATE |

---

## 7. P0 Migration Risks & Gap Analysis

```mermaid
flowchart TD
    R1["Risk 1: Exact Column Name Mismatches in Models<br/>(TransanctionId, ODPermium, TStatus, tbl_vehicledetails)"]
    R2["Risk 2: Zero Foreign Keys in Database<br/>(ORM cannot rely on DB-level cascade or FK checks)"]
    R3["Risk 3: Inward Number Collisions<br/>(sp_generateInwardNo reads AUTO_INCREMENT without locking)"]
    R4["Risk 4: E-Wallet Double Spending<br/>(Non-atomic check-then-decrement)"]
    R5["Risk 5: Plaintext Passwords in tbl_user<br/>(Must upgrade to bcrypt transparently on login)"]
    R6["Risk 6: 90 Missing Stored Procedures<br/>(Legacy code references missing routines)"]
    
    R1 --> Mit1["Mitigation: Generate models matching live DDL exactly"]
    R2 --> Mit2["Mitigation: Application-level relationship definitions in SQLAlchemy"]
    R3 --> Mit3["Mitigation: Atomic sequence or SELECT FOR UPDATE transaction lock"]
    R4 --> Mit4["Mitigation: Atomic SQL UPDATE ... WHERE EWalletBalance >= amt"]
    R5 --> Mit5["Mitigation: Passlib bcrypt with fallback plaintext check + re-hash"]
    R6 --> Mit6["Mitigation: Flag as dead code / provide graceful exception responses"]
```

### Risk Details:
1. **Risk 1: Model Definition Breakage**:
   - If SQLAlchemy models use idealized names (`TransactionId`, `CustVehicle`, `ODPremium`), all queries against the live MySQL database will fail.
   - *Mitigation*: SQLAlchemy models must explicitly specify `__tablename__ = 'tbl_transaction'` and map columns to their exact database names (`TransanctionId`, `ODPermium`, `NetPermium`, `TStatus`). Clean Python property names can be aliased in Pydantic schemas.
2. **Risk 2: Referential Integrity Without DB Foreign Keys**:
   - With 0 foreign keys in MySQL, historical data contains orphaned keys (e.g. references to deleted agents or branches).
   - *Mitigation*: SQLAlchemy `relationship()` definitions must use `foreign_keys` explicitly and not expect cascading deletes at the database level.
3. **Risk 3: Inward Number Duplication Under High Concurrency**:
   - `sp_generateInwardNo` executes `SELECT AUTO_INCREMENT FROM information_schema.TABLES`, which does not reserve or lock the ID. Concurrent submissions produce identical inward numbers.
   - *Mitigation*: Implement an atomic sequence table or row-level lock (`SELECT FOR UPDATE`) within the policy booking transaction block.
4. **Risk 4: E-Wallet Balance Race Condition**:
   - Rapid concurrent policy bookings by an agent can overdraft an e-wallet balance.
   - *Mitigation*: Enforce atomic conditional updates: `UPDATE tbl_agent SET EWalletBalance = EWalletBalance - :cost WHERE AgentId = :id AND EWalletBalance >= :cost`.
5. **Risk 5: Plaintext Password Migration**:
   - `tbl_user.UserPassword` holds plaintext passwords. Hashing all passwords in batch would break existing users because original passwords would become unknown to legacy WebForms.
   - *Mitigation*: Implement **transparent upgrade-on-login**: verify against plaintext or bcrypt; if plaintext match succeeds, hash with bcrypt and update `tbl_user.UserPassword`.

---

## 8. Missing Information & Production Access Requirements

Before executing Phase 1 through Phase 7, the following items require stakeholder confirmation:

1. **Active Mobile Application Inward Version**:
   - Confirm whether active Android clients currently in production call `InsertAppTransctiondetailsNew_8` or earlier versions (`_4`, `_5`, `_6`, `_7`), or the newly discovered database version `_2025`.
2. **Production Third-Party Credentials**:
   - Provide production API keys for Signzy, Attestr, HiCaliber, Fast2SMS, and IndiaText (all currently hardcoded or using sandbox URLs in C# code).
3. **Confirmation on 90 Missing Procedures**:
   - Confirm whether the 90 missing procedures identified in `sp_match_summary.json` can be formally classified as DEAD/DEPRECATED.
4. **Scheduled Job Timers on IIS Host**:
   - Confirm the exact cron / Task Scheduler execution times for daily policy expiry checks (currently implemented via `SendPushNotiRenewal.aspx`).

---

## 9. Recommended Phase 1 Implementation Plan

Following approval of this Phase 0 report, execution will proceed with **Phase 1: FastAPI Foundation**:

```mermaid
flowchart LR
    Step1["1. Core Config & Settings<br/>(Pydantic Settings, .env)"] --> Step2["2. Async DB Session Factory<br/>(SQLAlchemy 2.0 + aiomysql)"]
    Step2 --> Step3["3. Security Utilities<br/>(OAuth2 Bearer, Bcrypt, JWT)"]
    Step3 --> Step4["4. Centralized Exception Handlers<br/>(Structured JSON responses)"]
    Step4 --> Step5["5. Redis Connection & Cache Service"]
    Step5 --> Step6["6. Health & Readiness Probes<br/>(/api/v1/health)"]
    Step6 --> Step7["7. Alembic Migration Setup<br/>(Configured for existing DB)"]
```

### Detailed Phase 1 Work Breakdown:
1. **Application Configuration (`app/core/config.py`)**:
   - Pydantic `BaseSettings` reading environment variables for MySQL connection string, Redis URL, JWT secret key, and external integration tokens.
2. **Database Engine & Session (`app/db/session.py`)**:
   - Async SQLAlchemy engine using `aiomysql`:
     `mysql+aiomysql://admin_sa:***@103.149.199.250:3309/brahmainsurance`
   - Connection pool configuration: `pool_size=20`, `max_overflow=10`, `pool_recycle=3600`.
3. **Security & Cryptography (`app/core/security.py`)**:
   - OAuth2 Password Bearer token flow with JWT (`HS256`, 60-minute expiration).
   - Dual password verification: check `bcrypt.verify()`; if invalid, fallback to constant-time string comparison for plaintext legacy migration, with automatic rehashing hook.
4. **Exception Handling & Middleware (`app/middleware/`)**:
   - Global exception handler returning structured JSON errors (`{"success": false, "error": {"code": "...", "message": "..."}}`).
   - Request ID correlation middleware (`X-Request-ID`).
   - CORS middleware configured securely (replacing legacy `*`).
5. **Caching Layer (`app/core/redis.py`)**:
   - Async Redis client for vehicle catalogs and rating table caching.
6. **Health Check API (`app/api/v1/endpoints/health.py`)**:
   - `/api/v1/health` verifying live MySQL connectivity and Redis availability.

---

## 10. Formal Verification Conclusion & Stop Notice

> [!IMPORTANT]
> **PHASE 0 STOP CONDITION REACHED**:
> - All 29 migration audit documents and legacy C# source files have been verified.
> - Live MySQL database has been introspected, and exact table column definitions, counts, and discrepancies have been cataloged.
> - Stored procedure inventory (1,855 in code vs 1,980 in DB) has been classified.
> - Critical P0 risks (schema mismatches, non-atomic inward numbering, plaintext passwords) have been analyzed with mitigation strategies.
>
> **No business code, models, or migrations will be written until this Phase 0 Verification Report is reviewed and approved by the lead architect.**
