# PHASE 25 EXECUTION REPORT — FULL-SCOPE LEGACY MIGRATION CONTINUATION
## Corporate Group Clients, Commercial Sales Invoicing & Sister Concern Advances

**Repository**: Reliable-Insurance-Backend<br/>
**Branch**: `tejas-feature`<br/>
**Execution Date**: October 14, 2026<br/>
**Status**: COMPLETE — ALL ACCEPTANCE GATES GREEN (BUSINESS DECISIONS APPROVED)

---

## 1. Executive Summary & Verification Metrics

Phase 25 successfully continues the source-grounded migration of the legacy insurance system (`InsurancefinalNew_2026_09_23/`), focusing on **Corporate Group Clients, Commercial Sales Invoicing & Sister Concern Advances**.

| Metric | Pre-Phase 25 Baseline (Phase 24) | Post-Phase 25 Result | Delta / Status |
|---|---|---|---|
| **Alembic Revision Head** | `h24a0c6d2401` | `i25a0c7d2501` | +1 Revision (Upgraded) |
| **Physical MySQL Tables** | 125 tables | **132 tables** | **+7 Physical Tables** |
| **Mounted ASGI Routes** | 471 routes | **489 routes** | **+18 Route Methods** |
| **Automated Tests Passing** | 456 / 456 passing | **467 / 467 passing** | **+11 Passing Tests (0 Regressions)** |
| **LBR-069 Enforcement** | Preserved & Frozen | Preserved & Frozen | VERIFIED UNTOUCHED |
| **Production DB Access** | 0 connections / queries | 0 connections / queries | 100% ISOLATED |
| **Legacy Tree Safety** | Local, untracked, read-only | Local, untracked, read-only | 100% UNMODIFIED |

---

## 2. Approved Business Decisions

The following two core design decisions were explicitly reviewed, validated against legacy source code, and approved:

### 2.1 Multi-Line Financial Aggregation (Sum-of-Line-Totals Invariant)
- **Legacy Context**: In legacy ASP.NET WebForms (`adm_SalesRegistrationNew.aspx.cs` lines 238–245 vs line 362), the UI calculated invoice header total as `Math.Round(totBT + totGST)` where `totBT = sum(row.TaxableAmt)` and `totGST = sum(row.CGSTAmt + row.SGSTAmt + row.IGSTAmt)`. Simultaneously, individual line items were persisted into `tbl_salesregdetails` using per-line Banker's rounding (`Math.Round(line.Taxable + line.Taxes)`). On multi-line invoices with fractional cents, this legacy UI formula could produce an internal ₹1 discrepancy between the invoice header total (`tbl_salesregistration.Total`) and the sum of detail row totals ($\sum \text{tbl\_salesregdetails.Total}$).
- **Approved Business Decision**: **Sum-of-Line-Totals model accepted as an intentional accounting safety improvement**.
  $$\text{LineTotal}_i = \text{round\_bankers\_rupee}(\text{Taxable}_i + \text{CGST}_i + \text{SGST}_i + \text{IGST}_i)$$
  $$\text{Header Total} = \sum_{i} \text{LineTotal}_i$$
  $$\text{tbl\_account.amount} = -\text{Header Total}$$
  This guarantees that detail rows sum identically to the invoice header and the single-leg general ledger credit entry ($\sum \text{details} == \text{header} == |\text{ledger}|$) with zero variance, eliminating accounting and GST reconciliation discrepancies.

### 2.2 Invoice Number Initialization & Deployment Reconciliation
- **Legacy Context**: Stored procedure `sp_generatesalesregistrationInvoice` was invoked without input parameters (`DAL_Operations.cs:42281`), and the company prefix was concatenated in the C# presentation layer (`adm_SalesRegistrationNew.aspx.cs:53-61`). However, the stored procedure SQL definition was located inside the production MySQL database and is absent from all repository dumps (`UNKNOWN — EVIDENCE NOT AVAILABLE`).
- **Approved Business Decision**: **Accepted `1000` as the synthetic initial counter default**, yielding `1001` as the first generated numeric sequence value (e.g., `CRD/1001`).
- **Deployment Requirement**: Because `1000` is a synthetic implementation default, the `'COMMERCIAL_SALES'` counter row in `tbl_invoicesequence` must be reconciled against the highest existing invoice number in the production database prior to production cutover. The built-in atomic collision check (`while True` loop validating candidate numbers against `SalesRegistration.InvoiceNo` under an exclusive row lock) guarantees that any historical invoice numbers are safely detected and bypassed.

---

## 3. Legacy Source Tree Reconciliation

Analysis of `InsurancefinalNew_2026_09_23` identified the exact contracts and tables required for commercial operations:

| Legacy Source File | Legacy Method / Reference | Physical Table | Target Model | Domain Role |
|---|---|---|---|---|
| `adm_salesReliablecompany.aspx.cs` | `BLL_Loan.BLL_selectreliablecompanymst` | `tbl_reliablecompanymst` | `ReliableCompany` | Sister Concern entity configuration with invoice series prefixes (`RCompany`, `Prefix`). |
| `adm_salesClientMaster.aspx.cs` | `BLL_Loan.BLL_selectClientMaster` | `tbl_clientmaster` | `ClientMaster` | Corporate Client registry with Company Link, Address, PAN, GSTIN, and default tax percentages. |
| `adm_SalesRegistration.aspx.cs` | `sp_salesType`, `BLL_selectSalesType` | `tbl_salestype` | `SalesType` | Commercial service classification master (e.g. Brokerage Fee, Advisory). |
| `adm_SalesRegistrationNew.aspx.cs` | `sp_salesregistration` | `tbl_salesregistration` | `SalesRegistration` | Multi-line commercial sales invoice header. |
| `adm_SalesRegistrationNew.aspx.cs` | `sp_InsertSalesRegDetails` | `tbl_salesregdetails` | `SalesRegDetails` | Multi-line commercial sales invoice line item breakdowns. |
| `adm_SalesAdvReport.aspx.cs` | `sp_companyadvancemaster` | `tbl_companyadvancemaster` | `CompanyAdvanceMaster` | Sister concern company advance disbursement and balance tracking. |
| `adm_VoucherEntry.aspx.cs` L343 | `sp_UpdateCompanyAdvMaster` | `tbl_companyadvdetails` | `CompanyAdvDetail` | Advance recovery and accounting voucher audit history log. |
| `DAL_Operations.cs` L42281 | `sp_generatesalesregistrationInvoice` | `tbl_invoicesequence` | `InvoiceSequence` | Atomic monotonic sequential counter for commercial invoicing and coordinated voucher Doc_No allocation. |

---

## 4. Technical Architecture & Concurrency Hardening

### 4.1 Database Models (`app/models/phase25_features.py`)
SQLAlchemy 2.0 declarative models with `Mapped[]`, `mapped_column()`, explicit table arguments (`utf8/utf8_general_ci`, `DYNAMIC`), and foreign keys:
- `SalesType` (`tbl_salestype`): Master classification for commercial invoicing lines.
- `ReliableCompany` (`tbl_reliablecompanymst`): Sister concern group entities and invoice number prefixes.
- `ClientMaster` (`tbl_clientmaster`): B2B corporate client directory with default CGST, SGST, IGST rates and PAN/GSTIN.
- `SalesRegDetails` (`tbl_salesregdetails`): Line item breakdown linked to `InvoiceId` and `InvoiceNo`.
- `CompanyAdvanceMaster` (`tbl_companyadvancemaster`): Advance principal, recovered amount, and balance tracking.
- `CompanyAdvDetail` (`tbl_companyadvdetails`): History log of advance recoveries against invoices or vouchers.
- `InvoiceSequence` (`tbl_invoicesequence`): Monotonic sequential counters for commercial invoices (`COMMERCIAL_SALES`) and accounting vouchers (`ACCOUNT_DOC_NO`).

### 4.2 Concurrency Hardening Implementations
1. **Safe Invoice Sequence Cold-Start**:
   Native MySQL `INSERT ... ON DUPLICATE KEY UPDATE SequenceName = SequenceName` initializes the sequence row atomically without catching `IntegrityError` or corrupting transactions, followed immediately by `SELECT ... FOR UPDATE`.
2. **Coordinated General Ledger `Doc_No` Allocation**:
   Unindexed `MAX(Doc_No) + 1` queries eliminated. All sequential voucher allocations across Phase 9 (`commission_accounting.py`) and Phase 25 (`phase25_service.py`) route through `CommissionAccountingRepository.allocate_next_doc_no()`, coordinating via the locked `ACCOUNT_DOC_NO` row and synchronizing with historical maximums.
3. **Pessimistic Locking on Advance Recoveries**:
   Row-level exclusive lock (`SELECT ... FOR UPDATE`) on `CompanyAdvanceMaster` ensures concurrent recoveries cannot overdraw available balances (`HTTP 422`).
4. **InnoDB Lock-Aware Duplicate Voucher Checks**:
   Voucher deduplication queries execute with `.with_for_update()`, forcing a current locking read that bypasses the MVCC snapshot under `REPEATABLE READ` and guarantees immediate rejection of concurrent duplicate submissions with `HTTP 409 Conflict`.
5. **Multi-Event-Loop Harness Hardening**:
   `_EventLoopBoundLock` in `commission_accounting.py` dynamically provisions mutexes per event loop, preventing `RuntimeError: ... bound to a different event loop` across multi-loop test runners while preserving process serialization in production.

---

## 5. Automated Regression Test Coverage

The Phase 25 test suite (`tests/test_phase25_features.py`) executes 11 comprehensive automated tests against MySQL `reliable_insurance_dev`:

1. `test_bankers_rounding_rupee_parity`: Verifies exact Banker's rounding (`ROUND_HALF_EVEN`) across positive and midpoint tax amounts.
2. `test_commercial_masters_crud_and_validation`: Validates full CRUD, PAN format, and GSTIN format validations across SalesType, ReliableCompany, and ClientMaster.
3. `test_commercial_invoicing_atomicity_and_ledger_posting`: Verifies invoice creation, line items insertion, and single-leg general ledger credit entry (`amount = -Total`, `LedgerMId = 2756`, `AccTransId = 1`, `Narration = "sales Registration Amount"`).
4. `test_sister_concern_advance_booking_and_recovery`: Verifies advance disbursement, recovery against invoice, and balance adjustments.
5. `test_commercial_reports`: Tests sales register summary reporting and advance recovery audit reports with filtering.
6. `test_master_deletion_referential_integrity`: Validates soft-deactivation and foreign key cascade protection.
7. `test_concurrent_invoice_number_cold_start_and_allocation`: 10 concurrent requests allocate 10 strictly sequential, collision-free invoice numbers (`CRD/1001` through `CRD/1010`) on an empty counter table.
8. `test_concurrent_doc_no_coordination_between_phase25_and_accounting_vouchers`: 5 commercial invoices interleaved concurrently with 5 manual accounting vouchers allocate 10 strictly unique, monotonic document numbers.
9. `test_concurrent_advance_recovery_pessimistic_locking`: Deterministic concurrency proof of pessimistic locking (Part A over-recovery 422, Part B boundary balance 0.00, Part C concurrent duplicate voucher 409).
10. `test_invoice_creation_atomic_rollback_on_failure`: Injected failure during flush and Doc_No allocation proves complete database rollback with zero partial records and uncorrupted subsequent requests.
11. `test_financial_line_vs_aggregate_rounding_distinction`: Validates line-item Banker's rounding vs aggregate rounding and verifies exact equality between header total, detail row sums, and posted ledger amount.

---

## 6. Pre-Merge Verification & Sign-Off

- **Full Backend Test Suite**: **467 passed / 467 items (100% pass rate)**.
- **Git State**: Clean working tree on `tejas-feature` at commit `ebccdfc10d445698b3b327d2b3e6f327c7e5a0aa`.
- **Merge Readiness**: Fully verified, concurrency-hardened, documented, and ready for human review and pre-merge staging.
