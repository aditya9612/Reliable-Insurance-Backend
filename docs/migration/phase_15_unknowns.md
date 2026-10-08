# PHASE 15 — CONSOLIDATED UNKNOWNS REGISTER
## Reliable-Insurance-Backend: Master Project Unknowns & Evidence Gap Register

---

### 1. Executive Summary & Governance Rules
In strict compliance with the **No Guessing** and **Production Safety** invariants:
- **No UNKNOWN is fabricated or closed without concrete local source code evidence**.
- **No UNKNOWN may be resolved by connecting to or querying the production database (`brahmainsurance`)**.
- All **14 existing project UNKNOWNs** are fully preserved and carried forward.
- **1 new UNKNOWN (`GAP-UNK-15-001`)** has been cataloged for external payment gateway automated callbacks.
- **Total Cataloged UNKNOWNs**: **15 UNKNOWNs**.

---

### 2. Master Project Unknowns Register

| Unknown ID | Domain | Description of Missing Evidence | Why Unknown | Evidence Checked | What Evidence Would Resolve It | Production Access Required? |
|---|---|---|---|---|---|:---:|
| **`GAP-UNK-001`** | Stored Procedures | Internal SQL bodies of 22 canonical legacy stored procedures (68 call tokens) omitted from offline dump. | `CREATE PROCEDURE` statements absent from offline repository files. | `DAL_Operations.cs`, `Service.asmx.cs`, offline SQL scripts. | Read-only offline `mysqldump --routines --no-data` export. | **NO (Offline DDL dump only)** |
| **`GAP-UNK-002`** | Database Schema | Exact MySQL DDL column types (`DECIMAL(p,s)` vs `FLOAT`) on unextracted auxiliary tables. | No schema DDL file committed for historical auxiliary tables. | `AllMaster.cs`, `DAL_Operations.cs`. | Offline schema DDL export (`SHOW CREATE TABLE`). | **NO (Offline DDL dump only)** |
| **`GAP-UNK-003`** | Rating Engine | Tie-breaking order inside legacy SPs when multiple active discount slabs overlap for identical effective dates. | Absence of explicit `ORDER BY` clause in legacy call site parameters. | `SelfQuotationRequest.aspx.cs`, `tbl_app_oddiscountnew`. | Exact SQL definition of slab lookup stored procedure. | **NO (Offline DDL dump only)** |
| **`GAP-UNK-11-001`** | Documents / Webhook | Exact SQL body of `USP_Insert_CalliberPolicyWebhookData` and physical legacy staging table name. | Routine omitted from legacy database dump snapshot. | `PolicyParserWebhook.aspx.cs`, `DAL_Operations.cs`. | Offline DDL definition for Calliber webhook table. | **NO (Offline DDL dump only)** |
| **`GAP-UNK-11-002`** | Documents / Webhook | External HiCaliber/Calliber caller authentication mechanism and outbound push trigger contract. | Legacy codebase contains only inbound webhook endpoint; outbound push specification uncommitted. | `PolicyParserWebhook.aspx.cs`, `Web.config`. | Official HiCaliber vendor API specification document. | **NO (Vendor Documentation)** |
| **`GAP-UNK-11-003`** | Documents / Storage | Exact IIS virtual directory mapping and physical disk layout of historical `/ArchivePolicy/` files. | Server-level IIS configuration omitted from application repository. | `Web.config`, `DownloadAll.ashx.cs`. | Offline `applicationHost.config` from legacy IIS server. | **NO (Offline Config File)** |
| **`GAP-UNK-13-001`** | External Integrations | Signzy production KYC error response dictionary and rate-limiting headers. | Legacy code handled only standard HTTP 200 JSON payloads. | `RC_CheckVehicleDtl.aspx.cs`, `VehicleService.asmx.cs`.| Official Signzy API v2 production documentation. | **NO (Vendor Documentation)** |
| **`GAP-UNK-13-002`** | External Integrations | Fast2SMS delivery webhook retry intervals and DLT template edge cases. | Legacy implementation used synchronous HTTP GET without webhooks. | `Send_SMS.cs`, `Service.asmx.cs`. | Official Fast2SMS DLT developer documentation. | **NO (Vendor Documentation)** |
| **`GAP-UNK-13-003`** | External Integrations | OneSignal custom notification sound payload formatting for legacy app versions. | Sound payload omitted in legacy REST request strings. | `SendPushNotiRenewal.aspx.cs`. | Legacy mobile app repository source code. | **NO (Mobile App Repository)** |
| **`GAP-UNK-13-004`** | External Integrations | IndiaText DLT Principal Entity (PE) ID validation edge cases. | Only basic authentication parameters present in legacy code. | `App_Code/Send_SMS.cs`. | IndiaText DLT gateway API integration manual. | **NO (Vendor Documentation)** |
| **`GAP-UNK-13-005`** | External Integrations | SMTP TLS renegotiation timeout parameters on legacy mail server. | `System.Net.Mail` used default .NET Framework 4.0 socket timeouts. | `SendMailToAutority.aspx.cs`, `Web.config`. | Legacy corporate SMTP mail server configuration. | **NO (Offline Config File)** |
| **`GAP-UNK-14-001`** | Document Exports | Compiled internal formula bytecode inside 9 legacy Crystal Reports `.rpt` binary files. | Proprietary binary format unreadable without Crystal Reports Designer. | 9 `.rpt` files in `Insurance\Report\`. | Decompiled `.rpt` formula definitions via Crystal Designer. | **NO (Crystal Designer Tool)**|
| **`GAP-UNK-14-002`** | Document Exports | Proprietary bank payout batch flat file format specifications. | Legacy code used string formatting for unknown bank portal. | `AgentCommisionPayment.aspx.cs`. | Bank corporate net-banking batch payout specification. | **NO (Bank Documentation)** |
| **`GAP-UNK-14-003`** | Accounting / TDS | Ledger 2113 TDS account as legacy default rather than universal tenant assumption. | Hardcoded `LedgerMId = 2113` in legacy C# source. | `AgentCommissionPayment.aspx.cs`, `tbl_account`. | Chart of accounts configuration specification. | **NO (Business Policy Doc)** |
| **`GAP-UNK-15-001`** | Payments / Webhook | External payment gateway automated webhook callback schema and signature verification for online wallet top-ups. | Legacy application handled online payments via client-side browser redirect or manual UTR entry; no server-side webhook routine existed in C#. | `InstaPay.aspx.cs`, `WalletTopup.aspx.cs`, `PaymentTransaction.aspx.cs`. | Selected payment gateway provider (e.g. Razorpay / PayU) developer specification. | **NO (Vendor Documentation)** |

---

### 3. Conclusion & Risk Assessment
- **Zero Production Database Requirement**: Resolving any of these 15 UNKNOWN items does **not** require connecting to or querying the production database `brahmainsurance`. They depend strictly on offline DDL dumps, vendor manuals, or third-party documentation.
- **Architectural Isolation**: All 15 items are isolated behind clean provider interfaces, conservative decimal defaults, or documented modernizations, ensuring zero operational risk to the running backend.
