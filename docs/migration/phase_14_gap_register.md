# Phase 14 — Gap & Technical Debt Register

> **Audit Status**: COMPLETE (FORENSIC EXTRACTION)  
> **Phase**: Phase 14 (Reporting, Dashboard, MIS, POSP Invoicing & Statutory Statements) — Stage A  
> **Repository**: `Reliable-Insurance-Backend`  
> **Legacy Source**: `c:\Users\Admin\Downloads\InsurancefinalNew_2026_09_23\InsurancefinalNew`  
> **Mode**: STRICTLY READ-ONLY FORENSIC AUDIT (No implementation)

---

## 1. Executive Summary

This register catalogs all functional gaps, security anti-patterns, architectural discrepancies, and technical debts discovered during the forensic audit of legacy reporting, dashboards, MIS, POSP invoicing, and accounting modules.

Items are categorized into 4 priority tiers:
- **`P0` (Critical / Blocker)**: Core reporting parity, statutory compliance, injection vulnerabilities, and role-based data isolation.
- **`P1` (High)**: Financial reconciliation, performance tracking, banking statements, and arithmetic defects.
- **`P2` (Medium)**: Binary document generation modernization (replacing `.rpt` Crystal Reports), headless background scheduling.
- **`P3` (Low)**: Visual styling, color palette matching, and minor non-blocking formatting discrepancies.

---

## 2. Prioritized Gap Matrix

| Gap ID | Priority | Functional Domain | Legacy Source / Defect | Description & Impact | Modernization / Remediation Strategy |
| :--- | :---: | :--- | :--- | :--- | :--- |
| `GAP-14-001` | **`P0`** | **Security / DB** | `Adm_AllTransactionExport.aspx.cs` (`DEF-008`) | Raw SQL string concatenation in transaction search queries exposed database to SQL injection attacks. | Implement 100% parameterized SQLAlchemy async queries with typed Pydantic filter schemas. |
| `GAP-14-002` | **`P0`** | **Security / RBAC** | `Adm_AllTransactionExport.aspx.cs:L48` | Legacy gated export button (`btn_Export.Visible`) only on frontend; raw API endpoint could be bypassed. | Strict backend dependency `require_roles(["ADMIN", "IT SUPPORT", "ACCOUNT"])` on all export endpoints. |
| `GAP-14-003` | **`P0`** | **POSP Invoicing** | `rpt_POSP_Invoice.aspx.cs` | POSP payout invoices generated via iTextSharp XMLWorker without async queueing or atomic storage. | Implement async invoice generation with Jinja2 HTML templates, ReportLab/WeasyPrint, and canonical storage keys. |
| `GAP-14-004` | **`P0`** | **Statutory Accounting**| `Rpt_AccountTDSReport.aspx.cs` | Hardcoded TDS ledger ID `2113` embedded directly in C# codebehind across all financial statements. | Map to configurable `tds_ledger_master_id` setting with default `2113` for full legacy parity. |
| `GAP-14-005` | **`P1`** | **Fiscal Year Math**| `adm_TelecallerTargetReport.aspx.cs` (`DEF-002`) | Erroneous `Month >= 3` logic misclassified March transactions into succeeding fiscal year. | Implement standardized Indian FY arithmetic (`Month <= 3 ? Year - 1 : Year`) across all target services. |
| `GAP-14-006` | **`P1`** | **Commission Math** | `adm_CommissionReconcilationReport.aspx.cs` (`DEF-001`) | NCB recovery deduction incorrectly affected franchise commission calculation basis. | Ensure net premium commission basis strictly preserves clean transaction amounts. |
| `GAP-14-007` | **`P1`** | **Export Architecture**| `Adm_AllTransactionExport.aspx.cs:L120` | HTML tables served with `.xls` MIME type triggering Excel file corruption/security warning popups. | Migrate to true ISO/IEC 29500 OpenXML generation via `openpyxl` with styled headers. |
| `GAP-14-008` | **`P1`** | **Accounting Ledgers**| `Report_Account_By_LedgerType.aspx.cs` | 4-tier drilldown ledgers executed multiple synchronous roundtrips with signed polarity conventions. | Modernize into clean REST endpoints returning structured JSON hierarchies with explicit Debit/Credit amounts. |
| `GAP-14-009` | **`P2`** | **Document Engines** | `Insurance/Report/*.rpt` | 9 compiled Crystal Reports binary templates (`.rpt`) dependent on proprietary Windows runtime. | Reverse-engineer layouts into semantic Jinja2 HTML templates rendered to PDF via WeasyPrint / ReportLab. |
| `GAP-14-010` | **`P2`** | **Scheduled Jobs** | `SendMailToAutority.aspx.cs` (`GAP-UNK-13-004`) | Daily executive digests triggered by HTTP GET on `Page_Load`, vulnerable to denial of service or crawls. | Migrate to headless Celery Beat scheduled tasks running at 21:00 IST and 08:00 IST with Redis queueing. |
| `GAP-14-011` | **`P2`** | **Banking Advice** | `rpt_AgentCommissionStatementForBank.aspx.cs` | Bank payout advice generated as unformatted text/HTML without IFSC format validation. | Implement structured banking payout exports with strict IFSC regex validation and standardized CSV layout. |
| `GAP-14-012` | **`P3`** | **Export Styling** | `GridView1.HeaderStyle.BackColor` | Header background color `#48D1CC` (Medium Turquoise) and Century Gothic typography. | Preserve exact legacy branding palette in OpenPyXL styles for visual parity. |

---

## 3. Remediation Road Map for Phase 14 Implementation

- **Stage B Implementation Block 1**: Core Dashboards & MIS Transactions (Resolves `GAP-14-001`, `GAP-14-002`, `GAP-14-007`).
- **Stage B Implementation Block 2**: POSP & Agent Payout Invoicing (Resolves `GAP-14-003`, `GAP-14-009`).
- **Stage B Implementation Block 3**: Statutory & Accounting Statements (Resolves `GAP-14-004`, `GAP-14-008`, `GAP-14-011`).
- **Stage B Implementation Block 4**: Targets, Operations & Scheduled Tasks (Resolves `GAP-14-005`, `GAP-14-006`, `GAP-14-010`, `GAP-14-012`).
