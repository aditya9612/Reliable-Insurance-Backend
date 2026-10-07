# Phase 13 — Unknowns, Ambiguities & Technical Debt Register

> **Audit Status**: COMPLETE (PRESERVED & FORMALIZED)  
> **Phase**: Phase 13 (External Integrations, Notifications & Renewal) — Stage A  
> **Repository**: `Reliable-Insurance-Backend`  
> **Mode**: STRICTLY READ-ONLY (No assumptions made without legacy code evidence)

---

## 1. Overview

In accordance with strict migration auditing guidelines, all gaps, ambiguities, and missing database DDL files are formally registered with unique identifiers. Agents and engineers must **NEVER GUESS** or fabricate missing behavior.

---

## 2. Cumulative Unknowns Register (Preserved from Phases 0–12)

| Gap ID | Originating Phase | Domain | Description | Remediation / Safety Strategy |
| :--- | :--- | :--- | :--- | :--- |
| `GAP-UNK-001` | Phase 0–10 | Stored Procedures | Zero `.sql` schema files committed to legacy git repository; stored procedure SQL bodies live only in MySQL instance. | Forensic parameter extraction from ADO.NET `MySqlCommand.Parameters.AddWithValue` call sites in C# DAL/BLL. |
| `GAP-UNK-002` | Phase 0–10 | Database DDL | Legacy table foreign keys, indexes, and trigger definitions not committed to source control. | Recreated clean relational schemas in Alembic migrations with explicit foreign keys and indexes. |
| `GAP-UNK-003` | Phase 6 | Rating Masters | Exact legacy commercial vehicle tariff lookup tables across historical insurance companies. | Preserved tariff logic and documented configurable rating lookups in Phase 12. |
| `GAP-UNK-11-001`| Phase 11 | Document Storage | Exact production file system root directory path and legacy S3 bucket names. | Pluggable `StorageBackend` (`LocalStorageBackend` default) using canonical storage keys (`DEF-010`). |
| `GAP-UNK-11-002`| Phase 11 | Document Format | Exact binary internal format of legacy `.callibe` calibration files. | Treated as binary stream attachments; preserves file integrity without mutating bytes. |
| `GAP-UNK-11-003`| Phase 11 | Policy Webhooks | External third-party policy parser webhook authentication scheme. | Supported both open legacy and HMAC-authenticated webhook ingestion with intentional security hardening. |

---

## 3. Phase 13 Specific Unknowns Register

| Gap ID | Domain | Severity | Legacy Finding & Evidence | Modernized FastAPI Remediation Strategy |
| :--- | :--- | :---: | :--- | :--- |
| `GAP-UNK-13-001`| Database Schema | `P2` | **Full physical DDL for `tbl_vehiclenorc_details` and `tbl_preyearrenewalstatus` absent from Git**: No `.sql` files for these tables exist in the repository. | **Inferred from DTOs & Stored Procedures**: Extracted 100% of the 54 fields from `API_vehiclenorc_details` (`sp_InsertRCAPIDetails`) and 14 fields from `API_PreYearRenewalStatus` (`Sp_InsertFollowPreYearRenewalStatus`). |
| `GAP-UNK-13-002`| Security / Push | `P1` | **Client-side OneSignal JavaScript execution**: `SendPushNotiRenewal.aspx` and `PolicyNoUpdatePushNoti.aspx` invoke OneSignal directly in browser JS, exposing API keys. | **Intentional Security Hardening**: Server-side async client (`OneSignalPushProvider`) strictly keeps API keys in server environment variables. |
| `GAP-UNK-13-003`| SMS Gateways | `P2` | **Dual SMS gateways with divergent routes**: Fast2SMS uses DLT templates for payments/credentials; IndiaText uses transactional HTTP GET for policy/general alerts. | **Pluggable Provider Architecture**: Define `SMSProvider` base class with concrete adapters for both gateways, selectable via configuration. |
| `GAP-UNK-13-004`| Job Scheduling | `P2` | **Implicit execution trigger for daily email reports**: `SendMailToAutority.aspx.cs` executes on `Page_Load`, relying on external cron/browser curl or manual administrator clicks. | **Celery Beat Scheduled Tasks**: Modernized into formal scheduled background tasks (`daily_renewal_check`, `daily_report_dispatch`) with audit logging. |
| `GAP-UNK-13-005`| Email Templating | `P3` | **Inline HTML string concatenation in C# codebehind**: `adm_sendExcelTomailRenewal.aspx.cs` builds HTML tables using literal C# strings with hardcoded styling. | **Structured Email Templating**: Standardized into clean Jinja2 HTML templates mirroring the exact legacy layout, colors, and broker contact info. |

---

## 4. Technical Debt & Anti-Patterns Identified in Legacy

1. **Silent Exception Swallowing**:
   - In `Send_SMS.cs:L36` and `VehicleNoDetails.cs:L94`, network exceptions are caught and swallowed (`ex.ToString()`). Failures were completely invisible to administrators.
2. **Hardcoded Vendor Credentials**:
   - Production API keys for APIClub, Signzy, OneSignal, Fast2SMS, IndiaText, and Gmail SMTP were committed directly in source code.
3. **Synchronous Network Blocking**:
   - Outbound HTTP requests blocked the ASP.NET request thread, leading to slow page loads and potential gateway timeouts under high concurrency.
