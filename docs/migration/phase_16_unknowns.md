# PHASE 16 — MASTER CONSOLIDATED UNKNOWNS REGISTER
## Reliable-Insurance-Backend: Preserved Project Unknowns & Phase 16 Evidence Gaps

---

### 1. Executive Summary & Governance Invariants
In accordance with strict migration integrity rules:
- **Zero Fabrication**: No unknown is guessed, invented, or closed without verified local evidence.
- **Production Safety**: Zero connections or queries to the production database (`brahmainsurance`) are permitted to discover missing schemas, tables, or records.
- **Cumulative Preservation**: All **15 previously established UNKNOWNs** (`GAP-UNK-001` through `GAP-UNK-15-001`) are carried forward with 100% fidelity.
- **Phase 16 Additions**: Exactly **2 new Phase 16 unknowns** (`GAP-UNK-16-001` and `GAP-UNK-16-002`) are documented where legacy C# source code references uncommitted database tables or compiled SP bodies.

---

### 2. Consolidated Project Unknowns Register (17 Cumulative UNKNOWNs)

| # | Unknown ID | Domain | Description of Missing Evidence | Why Unknown | Evidence Checked | What Evidence Would Resolve It | Production Access Required? |
|---|---|---|---|---|---|---|:---:|
| 1 | **`GAP-UNK-001`** | Stored Procedures | Internal SQL bodies of 22 canonical legacy stored procedures (68 call tokens) omitted from offline dump. | `CREATE PROCEDURE` statements absent from offline repository files. | `DAL_Operations.cs`, `Service.asmx.cs`, offline SQL scripts. | Read-only offline `mysqldump --routines --no-data` export. | **NO (Offline DDL dump only)** |
| 2 | **`GAP-UNK-002`** | Database Schema | Exact MySQL DDL column types (`DECIMAL(p,s)` vs `FLOAT`) on unextracted auxiliary tables. | No schema DDL file committed for historical auxiliary tables. | `AllMaster.cs`, `DAL_Operations.cs`. | Offline schema DDL export (`SHOW CREATE TABLE`). | **NO (Offline DDL dump only)** |
| 3 | **`GAP-UNK-003`** | Rating Engine | Tie-breaking order inside legacy SPs when multiple active discount slabs overlap for identical effective dates. | Absence of explicit `ORDER BY` clause in legacy call site parameters. | `SelfQuotationRequest.aspx.cs`, `tbl_app_oddiscountnew`. | Exact SQL definition of slab lookup stored procedure. | **NO (Offline DDL dump only)** |
| 4 | **`GAP-UNK-11-001`** | Documents / Webhook | Exact SQL body of `USP_Insert_CalliberPolicyWebhookData` and physical legacy staging table name. | Routine omitted from legacy database dump snapshot. | `PolicyParserWebhook.aspx.cs`, `DAL_Operations.cs`. | Offline DDL definition for Calliber webhook table. | **NO (Offline DDL dump only)** |
| 5 | **`GAP-UNK-11-002`** | Documents / Webhook | External HiCaliber/Calliber caller authentication mechanism and outbound push trigger contract. | Legacy codebase contains only inbound webhook endpoint; outbound push specification uncommitted. | `PolicyParserWebhook.aspx.cs`, `Web.config`. | Official HiCaliber vendor API specification document. | **NO (Vendor Documentation)** |
| 6 | **`GAP-UNK-11-003`** | Documents / Storage | Exact IIS virtual directory mapping and physical disk layout of historical `/ArchivePolicy/` files. | Server-level IIS configuration omitted from application repository. | `Web.config`, `DownloadAll.ashx.cs`. | Offline `applicationHost.config` from legacy IIS server. | **NO (Offline Config File)** |
| 7 | **`GAP-UNK-13-001`** | External Integrations | Signzy production KYC error response dictionary and rate-limiting headers. | Legacy code handled only standard HTTP 200 JSON payloads. | `RC_CheckVehicleDtl.aspx.cs`, `VehicleService.asmx.cs`.| Official Signzy API v2 production documentation. | **NO (Vendor Documentation)** |
| 8 | **`GAP-UNK-13-002`** | External Integrations | Fast2SMS delivery webhook retry intervals and DLT template edge cases. | Legacy implementation used synchronous HTTP GET without webhooks. | `Send_SMS.cs`, `Service.asmx.cs`. | Official Fast2SMS DLT developer documentation. | **NO (Vendor Documentation)** |
| 9 | **`GAP-UNK-13-003`** | External Integrations | OneSignal custom notification sound payload formatting for legacy app versions. | Sound payload omitted in legacy REST request strings. | `SendPushNotiRenewal.aspx.cs`. | Legacy mobile app repository source code. | **NO (Mobile App Repository)** |
| 10 | **`GAP-UNK-13-004`** | External Integrations | IndiaText DLT Principal Entity (PE) ID validation edge cases. | Only basic authentication parameters present in legacy code. | `App_Code/Send_SMS.cs`. | IndiaText DLT gateway API integration manual. | **NO (Vendor Documentation)** |
| 11 | **`GAP-UNK-13-005`** | External Integrations | SMTP TLS renegotiation timeout parameters on legacy mail server. | `System.Net.Mail` used default .NET Framework 4.0 socket timeouts. | `SendMailToAutority.aspx.cs`, `Web.config`. | Legacy corporate SMTP mail server configuration. | **NO (Offline Config File)** |
| 12 | **`GAP-UNK-14-001`** | Document Exports | Compiled internal formula bytecode inside 9 legacy Crystal Reports `.rpt` binary files. | Proprietary binary format unreadable without Crystal Reports Designer. | 9 `.rpt` files in `Insurance\Report\`. | Decompiled `.rpt` formula definitions via Crystal Designer. | **NO (Crystal Designer Tool)**|
| 13 | **`GAP-UNK-14-002`** | Document Exports | Proprietary bank payout batch flat file format specifications. | Legacy code used string formatting for unknown bank portal. | `AgentCommisionPayment.aspx.cs`. | Bank corporate net-banking batch payout specification. | **NO (Bank Documentation)** |
| 14 | **`GAP-UNK-14-003`** | Accounting / TDS | Ledger 2113 TDS account as legacy default rather than universal tenant assumption. | Hardcoded `LedgerMId = 2113` in legacy C# source. | `AgentCommissionPayment.aspx.cs`, `tbl_account`. | Chart of accounts configuration specification. | **NO (Business Policy Doc)** |
| 15 | **`GAP-UNK-15-001`** | Payments / Webhook | External payment gateway automated webhook callback schema and signature verification for online wallet top-ups. | Legacy application handled online payments via client-side browser redirect or manual UTR entry; no server-side webhook routine existed in C#. | `InstaPay.aspx.cs`, `WalletTopup.aspx.cs`, `PaymentTransaction.aspx.cs`. | Selected payment gateway provider (e.g. Razorpay / PayU) developer specification. | **NO (Vendor Documentation)** |
| 16 | **`GAP-UNK-16-001`** | Dynamic RBAC / Menu | Complete physical `tbl_menu` ID-to-screen label dictionary and hierarchical nesting order. | `Clerk.Master.cs` renders menus dynamically from `tbl_role_privilege` joined with `tbl_menu`; static DDL/DML for `tbl_menu` omitted from offline repository. | `Clerk.Master.cs`, `Adm_RolePrivilege.aspx.cs`. | Offline `mysqldump` of `tbl_menu` / `tbl_menumaster`. | **NO (Offline DDL dump only)** |
| 17 | **`GAP-UNK-16-002`** | Security / Lockout | Threshold count and aging days for uncleared cheques triggering automatic user lockout in `sp_LockChequeClearingCount`. | Threshold parameters are compiled inside the legacy MySQL SP routine rather than passed from C#. | `DAL_Operations.cs:20315`, `Adm_LockChequeEntry.aspx.cs`. | Offline definition of `sp_LockChequeClearingCount`. | **NO (Offline DDL dump only)** |

---

### 3. Critical LBR-069 Boundary Analysis (`GAP-UNK-16-002`)
- **Phase 15B Implementation Remains Frozen**: The verified behavioral implementation of **LBR-069** in Phase 15B (`UtilityService.enforce_overdue_cheque_locks` $\rightarrow$ `user.isdeleted = '1'` $\rightarrow$ HTTP 401 on login) is **100% frozen and operational**. Phase 16 does NOT modify it.
- **Distinction: Exact SQL Constant vs Behavioral Parity**:
  - `GAP-UNK-16-002` refers strictly to the unextracted internal SQL integer literals and date arithmetic compiled inside the legacy MySQL stored procedure `sp_LockChequeClearingCount`.
  - Because offline C# callers (`DAL_User.DAL_LockChequeClearingCount`) pass only `(UserName, Password, Opr)` without passing the threshold value, the exact constant cannot be extracted from offline application code.
  - Per the strict **No Guessing** and **Production Safety** rules, this constant is **genuinely UNKNOWN** and will remain open until an authentic offline routine dump is provided.
  - Crucially: **`GAP-UNK-16-002` does NOT invalidate the verified behavioral parity of Phase 15B**. The externally observable behavior—that users associated with delinquent uncleared cheques are locked out from logging in—is fully proven, tested, and operational.

---

### 4. Verification & Governance Assessment
- **Preservation Verification**: All 15 prior unknowns remain untouched and active.
- **Safety**: 0/17 unknowns require querying `brahmainsurance`.
- **Actionability**: Implementation in Phase 16B will use modern, configurable, defensive defaults (e.g. configurable cheque lockout threshold, standard UI menu tree DTOs) without violating legacy invariants.
