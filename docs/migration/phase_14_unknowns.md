# Phase 14 — Unknowns, Ambiguities & Preserved Technical Debt Register

> **Audit Status**: COMPLETE (PRESERVED & FORMALIZED)  
> **Phase**: Phase 14 (Reporting, Dashboard, MIS, POSP Invoicing & Statutory Statements) — Stage A  
> **Repository**: `Reliable-Insurance-Backend`  
> **Legacy Source**: `c:\Users\Admin\Downloads\InsurancefinalNew_2026_09_23\InsurancefinalNew`  
> **Mode**: STRICTLY READ-ONLY FORENSIC AUDIT (No assumptions made without legacy code evidence)

---

## 1. Overview & No-Guessing Directives

In accordance with strict migration auditing guidelines, all gaps, ambiguities, and missing database DDL files are formally registered with unique identifiers. 

Migration engineers and AI agents must **NEVER GUESS** or fabricate unproven business logic. Where legacy source code or database schemas do not provide explicit proof, the behavior is formally classified as an **UNKNOWN** with a defensive fallback strategy.

---

## 2. Preserved Cumulative Unknowns Register (Phases 0–13)

All 11 previously cataloged unknowns are strictly preserved intact:

| Gap ID | Originating Phase | Domain | Description | Remediation / Safety Strategy |
| :--- | :--- | :--- | :--- | :--- |
| `GAP-UNK-001` | Phase 0–10 | Stored Procedures | Zero `.sql` schema files committed to legacy git repository; stored procedure SQL bodies live only in MySQL instance. | Forensic parameter extraction from ADO.NET `MySqlCommand.Parameters.AddWithValue` call sites in C# DAL/BLL. |
| `GAP-UNK-002` | Phase 0–10 | Database DDL | Legacy table foreign keys, indexes, and trigger definitions not committed to source control. | Recreated clean relational schemas in Alembic migrations with explicit foreign keys and indexes. |
| `GAP-UNK-003` | Phase 6 | Rating Masters | Exact legacy commercial vehicle tariff lookup tables across historical insurance companies. | Preserved tariff logic and documented configurable rating lookups in Phase 12. |
| `GAP-UNK-11-001`| Phase 11 | Document Storage | Exact production file system root directory path and legacy S3 bucket names. | Pluggable `StorageBackend` (`LocalStorageBackend` default) using canonical storage keys (`DEF-010`). |
| `GAP-UNK-11-002`| Phase 11 | Document Format | Exact binary internal format of legacy `.callibe` calibration files. | Treated as binary stream attachments; preserves file integrity without mutating bytes. |
| `GAP-UNK-11-003`| Phase 11 | Policy Webhooks | External third-party policy parser webhook authentication scheme. | Supported both open legacy and HMAC-authenticated webhook ingestion with intentional security hardening. |
| `GAP-UNK-13-001`| Phase 13 | Database Schema | Full physical DDL for `tbl_vehiclenorc_details` and `tbl_preyearrenewalstatus` absent from Git. | Inferred 100% of the 54 fields from `API_vehiclenorc_details` (`sp_InsertRCAPIDetails`) and 14 fields from `API_PreYearRenewalStatus`. |
| `GAP-UNK-13-002`| Phase 13 | Security / Push | Client-side OneSignal JavaScript execution in browser exposing API keys. | Server-side async client (`OneSignalPushProvider`) strictly keeping API keys in server environment variables. |
| `GAP-UNK-13-003`| Phase 13 | SMS Gateways | Dual SMS gateways with divergent routes (Fast2SMS for DLT OTP, IndiaText for alerts). | Pluggable `SMSProvider` base class with concrete adapters for both gateways. |
| `GAP-UNK-13-004`| Phase 13 | Job Scheduling | Implicit execution trigger for daily email reports on WebForms `Page_Load`. | Modernized into formal scheduled Celery Beat tasks (`daily_renewal_check`, `daily_report_dispatch`). |
| `GAP-UNK-13-005`| Phase 13 | Email Templating | Inline HTML string concatenation in C# codebehind with hardcoded styles. | Standardized into clean Jinja2 HTML templates mirroring exact legacy layout. |

---

## 3. Phase 14 Specific Unknowns Register

Forensic analysis of the reporting and dashboard modules identified 3 new domain-specific unknowns:

| Gap ID | Domain | Severity | Legacy Finding & Evidence | Modernized FastAPI Remediation Strategy |
| :--- | :--- | :---: | :--- | :--- |
| `GAP-UNK-14-001`| Document Rendering | `P2` | **Proprietary Crystal Reports bytecode in `.rpt` files**: The repository contains 9 compiled binary `.rpt` files (e.g. `Rpt_AccountReport.rpt`, `Payment_Voucher.rpt`). The internal formula language expressions, conditional suppressions, and sub-reports cannot be decompiled without SAP Crystal Reports visual designer software. Crystal internal formula parity is UNKNOWN where binary evidence is unavailable. | **Proposed Modern Implementation**: Reconstruct standard payment voucher, receipt voucher, and ledger templates using Jinja2 HTML + WeasyPrint/ReportLab based on the parameter signatures in `DAL_Operations.cs` and runtime sample screenshots. Classified as intentional modernization, not verified 100% binary parity. |
| `GAP-UNK-14-002`| Corporate Banking | `P2` | **Proprietary bank payout batch file specifications**: Legacy bank payout behavior is known at the business/report level (`rpt_AgentCommissionStatementForBank.aspx.cs`), but exact proprietary corporate banking portal file specifications (e.g. fixed-width encrypted text for ICICI CMS or HDFC) remain **UNKNOWN**. | **Intentional Modernization (Not Legacy Parity)**: Phase 14B may implement a configurable banking export abstraction providing standard CSV/Excel output matching legacy business behavior with configurable column mapping for bank portals. Classified as proposed modernization. |
| `GAP-UNK-14-003`| Chart of Accounts | `P3` | **Multi-branch tenancy for hardcoded TDS ledger `2113`**: `LedgerMId = 2113` is verified legacy default/evidence in C# code. However, whether satellite branches share this exact ledger ID in production or if separate sub-ledgers exist across future multi-branch tenants is unconfirmed. | **Verified Legacy Default + Proposed Hardening**: `2113` is retained as verified legacy default/evidence; configurable tenant overrides (`tds_ledger_master_id`) are classified as proposed hardening/modernization. |

---

## 4. Summary & Verification

- Total Preserved Historical Unknowns: **11**
- Total Newly Identified Phase 14 Unknowns: **3**
- Grand Total Active Unknowns Register: **14**
- Ambiguity Rate: **0% Uncontrolled** (All 14 items have documented defensive fallbacks).
