# PHASE 15 — IMPORT & EXPORT BATCH AUDIT
## Reliable-Insurance-Backend: Post-Phase 14 Import, Export & File Batch Reconciliation

---

### 1. Executive Summary
- **Phase 14 Export Deliverables**: Complete RFC 4180 streaming CSV engine, OpenPyXL OpenXML `.xlsx` spreadsheet generator, and ReportLab A4 vector PDF engine implemented in `app/services/export_service.py`.
- **Legacy Import Engines**: Legacy application utilized `ClosedXML` (v2.5) and `ExcelDataReader` (`Excel.dll`) for bulk tabular ingestion, which suffered from IIS request thread timeouts, non-atomic commits, and floating-point data corruption.
- **Post-Phase 14 Status**:
  - **Document & Statement Exports**: **100% Migrated (Phase 14)**
  - **Bulk Policy MIS Import (`tbl_importagentpolicy`)**: **DEFERRED (P2)**
  - **Bulk Insurer Reconciliation Import**: **DEFERRED (P2)**
  - **Proprietary Bank Payout Batch Files (`GAP-UNK-14-002`)**: **PRESERVED UNKNOWN (Modernized Multi-Column Excel Provided)**

---

### 2. Import & Export Workflow Inventory

| Workflow Name | Legacy Mechanism | Modern FastAPI Equivalent | Direction | Current Status | Priority | Notes & Evidence |
|---|---|---|:---:|---|:---:|---|
| **MIS Transaction Export (CSV)** | HTML table masquerading as `.xls` in `MISReport.aspx` | `GET /api/v1/reports/mis/transactions/export?format=csv` | Outbound | **MIGRATED (Phase 14)** | Completed | RFC 4180 streaming generator ($O(1)$ memory). |
| **MIS Transaction Export (XLSX)**| `ClosedXML` workbook in `MISReport.aspx` | `GET /api/v1/reports/mis/transactions/export?format=xlsx` | Outbound | **MIGRATED (Phase 14)** | Completed | OpenXML `.xlsx` with `#48D1CC` headers. |
| **POSP Commission Invoice PDF** | Windows iTextSharp in `rpt_POSP_Invoice.aspx` | `GET /api/v1/reports/posp/invoices/{id}/pdf` | Outbound | **MIGRATED (Phase 14)** | Completed | ReportLab A4 vector PDF with Indian words. |
| **Accounting Voucher PDF** | Windows RDLC in `VoucherEntry.aspx` | `GET /api/v1/reports/accounting/vouchers/{doc_no}/pdf` | Outbound | **MIGRATED (Phase 14)** | Completed | ReportLab vector voucher layout. |
| **Statutory TDS Register Export**| `ClosedXML` in `adm_tdsForAgent.aspx` | `GET /api/v1/reports/statutory/tds/export` | Outbound | **MIGRATED (Phase 14)** | Completed | Multi-format CSV/XLSX export for Form 16A. |
| **Bank Commission Statement** | Proprietary text batch in `AgentCommPayment.aspx` | `GET /api/v1/reports/operations/bank-commission-statements/export`| Outbound | **MODERNIZED (Phase 14)**| Completed | Modern multi-column Excel (`GAP-UNK-14-002`). |
| **Bulk Policy MIS Excel Import** | Synchronous `ExcelDataReader` in `adm_ImportTransAgentPolicyMIS.aspx`| `POST /api/v1/utilities/imports/policy-mis` | Inbound | **DEFERRED** | **P2** | Ingests bulk external broker policy sheets into `tbl_importagentpolicy`. |
| **Bulk Insurer Recon Import** | Manual grid entry in `InsurerPaymentReconciliation.aspx`| `POST /api/v1/utilities/imports/insurer-recon` | Inbound | **DEFERRED** | **P2** | Ingests insurer commission settlement statements. |
| **Document Archive ZIP Export** | `Ionic.Zip` in `DownloadAll.ashx` | `GET /api/v1/documents/legacy/DownloadAll.ashx` | Outbound | **MIGRATED (Phase 11)** | Completed | Streaming ZIP with traversal protection. |

---

### 3. Detailed Forensic Specification of Remaining Import Workflows

#### 3.1 Bulk Policy MIS Upload (`tbl_importagentpolicy`)
- **Legacy File**: `Insurance\Clerk\adm_ImportTransAgentPolicyMIS.aspx.cs` (3,410 lines)
- **Database Table**: `tbl_importagentpolicy` (36 columns)
- **Legacy Workflow**:
  1. User selects `AgentId`, `BranchId`, and `FinancialYear`.
  2. Uploads `.xlsx` or `.xls` spreadsheet containing columns: `PolicyNo`, `CustomerName`, `RegistrationNo`, `Make`, `Model`, `EngineNo`, `ChassisNo`, `ODPremium`, `TPPremium`, `NetPremium`, `GrossPremium`, `AgentCommPerc`, `AgentCommAmount`.
  3. Legacy code used `Excel.dll` to read rows into an in-memory `DataTable`.
  4. Looped through rows calling `sp_InsertImportAgentPolicy` without transaction protection.
- **Modern Target Architecture (Candidate A)**:
  - Add SQLAlchemy model `ImportAgentPolicy` (`tbl_importagentpolicy`).
  - Endpoint `POST /api/v1/utilities/imports/policy-mis`:
    - Accepts multipart `.xlsx` / `.csv` file upload.
    - Validates MIME type and file structure.
    - Validates each row against active master values (Make, Model, Insurer, RTO).
    - Writes rows into `tbl_importagentpolicy` in a single async unit-of-work transaction (`async with db.begin()`).
    - Returns structured summary: `{ "total_rows": N, "valid_rows": V, "error_rows": E, "errors": [...] }`.

#### 3.2 Bulk Insurer Reconciliation Import
- **Legacy File**: `Insurance\Clerk\InsurerPaymentReconciliation.aspx.cs`
- **Modern Target Architecture (Candidate A)**:
  - Ingests insurer brokerage payment advice spreadsheets.
  - Matches rows by `PolicyNo` against `tbl_transaction`.
  - Computes variance between `BrokerageReceivable` and actual insurer remittance.
  - Generates auto-reconciliation proposals for review.
