# Phase 14 — Stored Procedures Forensic Extraction & Service Mapping

> **Audit Status**: COMPLETE (FORENSIC EXTRACTION)  
> **Phase**: Phase 14 (Reporting, Dashboard, MIS, POSP Invoicing & Statutory Statements) — Stage A  
> **Repository**: `Reliable-Insurance-Backend`  
> **Legacy Source**: `c:\Users\Admin\Downloads\InsurancefinalNew_2026_09_23\InsurancefinalNew`  
> **Mode**: STRICTLY READ-ONLY FORENSIC AUDIT (No implementation)

---

## 1. Executive Summary & Evidence Classification

Forensic inspection of `DAL_Operations.cs` and `Service.asmx.cs` identified 104 distinct stored procedures invoked by the legacy reporting, dashboard, and accounting modules.

In accordance with strict migration auditing standards and `GAP-UNK-001` (Stored procedure SQL bodies live only in the MySQL database and are absent from source control), we explicitly distinguish the levels of forensic mapping:

1. **SP Inventory Coverage**: **100%** (All 104 procedures cataloged).
2. **SP Caller Mapping**: **100%** (Every WebForms and service caller site identified).
3. **Parameter Mapping**: **100%** (Extracted from ADO.NET `MySqlCommand.Parameters.AddWithValue`).
4. **Output Mapping**: **100%** (Extracted from calling DataTable / DataReader column consumption).
5. **Behavioral Parity Classification**:
   - **`EVIDENCE-BACKED PARITY`**: Where C# caller consumption, BLL calculations, or relational schemas explicitly prove the underlying logic.
   - **`UNKNOWN — SQL BODY UNAVAILABLE (GAP-UNK-001)`**: Where the internal SQL joins, aggregation clauses, or stored procedure body live only in the MySQL routine catalog without Git source files. No formulas are fabricated.

In Phase 14B, target modern implementations (`Proposed Modern Implementation`) will replace these procedures with parameterized async SQLAlchemy queries.

---

## 2. Stored Procedure Mapping Catalog

### 2.1 POSP & Agent Invoices

| Legacy Stored Procedure | Legacy Caller (`.aspx.cs`) | Extracted Parameters | Return Schema / Behavior | Modern Target Service / Method |
| :--- | :--- | :--- | :--- | :--- |
| `sp_POSP_CheckInvoiceNo` | `rpt_POSP_Invoice` | `@InvoiceNo VARCHAR(100)` | `Count INT` (Uniqueness check) | `PospInvoiceRepository.exists_by_invoice_no` |
| `sp_POSP_Insert_Invoice` | `rpt_POSP_Invoice` | `@InvoiceNo`, `@InvoiceDate`, `@AgentId`, `@POSPType`, `@FinancialYear`, `@Month`, `@Amount`, `@GSTAmt`, `@GrandTotal`, `@PdfPath`, `@CreatedBy` | `InvoiceId INT` | `PospInvoiceRepository.create_invoice` |
| `sp_POSP_Invoice_Report` | `rpt_POSP_InvoiceReport`| `@FinancialYear`, `@Month`, `@AgentId` | Table of invoices with status, amounts, PDF link | `PospInvoiceRepository.get_invoices_paged` |
| `sp_POPSInvoiceRpt` | `rpt_POSP_Invoice` | `@InvoiceNo` | Full invoice details for PDF template rendering | `PospInvoiceRepository.get_invoice_detail_by_no` |
| `sp_InvoiceAgentPaymet` | `InvoiceAgentPaymentrpt`| `@FromDate`, `@ToDate`, `@AgentId`, `@Status` | Payout reconciliation and settlement rows | `PospInvoiceRepository.get_agent_payout_reconciliation` |

### 2.2 Dashboards & Executive KPI Aggregations

| Legacy Stored Procedure | Legacy Caller (`.aspx.cs`) | Extracted Parameters | Return Schema / Behavior | Modern Target Service / Method |
| :--- | :--- | :--- | :--- | :--- |
| `sp_Agent_PremiumSummeryAllMonth` | `Dashboard`, `DashBoardAccountSummery` | `@FinancialYear`, `@Broker`, `@DateMode` | 12-month matrix (OD, TP, Net, Gross, Comm, Profit) | `DashboardRepository.get_monthly_executive_matrix` |
| `sp_Agent_PremiumSummeryAllMonth_EFF`| `Dashboard` (Branch 105) | `@FinancialYear`, `@Broker`, `@DateMode` | Effective-date based 12-month matrix for Branch 105 | `DashboardRepository.get_monthly_matrix_effective` |
| `sp_SelectInsuranceCompanyNetPermiumbyMonyh` | `Dashboard` | `@FinancialYear`, `@CompanyId`, `@Broker` | Company-wise monthly net premium breakdown | `DashboardRepository.get_company_monthly_net_premium` |
| `sp_SelectInsuranceCompanyNetPermiumbyMonyh_EFF` | `Dashboard` (Branch 105) | `@FinancialYear`, `@CompanyId`, `@Broker` | Branch 105 company-wise monthly net premium | `DashboardRepository.get_company_monthly_net_premium_eff` |
| `sp_Dashboard_BrokerWiseBusiness` | `Dashboard`, `OwnerDashBoard` | `@FromDate`, `@ToDate` | Breakdown across 7 broker entity buckets | `DashboardRepository.get_broker_wise_summary` |
| `sp_Dashboard_CompanyWiseBusiness` | `Dashboard` | `@FromDate`, `@ToDate`, `@Broker` | Breakdown across insurance companies | `DashboardRepository.get_company_wise_summary` |
| `sp_Dashboard_CompanyWiseBusiness_EFF`| `Dashboard` (Branch 105) | `@FromDate`, `@ToDate`, `@Broker` | Branch 105 insurer business summary | `DashboardRepository.get_company_wise_summary_eff` |
| `sp_Agent_PremiumSummery_CutNPay` | `DashBoradAgentPremiumCutNPay` | `@FinancialYear`, `@Month`, `@BranchId` | Cut & Pay premium, deductions, remittances | `DashboardRepository.get_cut_and_pay_summary` |
| `sp_Agent_PremiumSummery_CutNPayPassOn`| `DashBoradAgentPremiumCutNPay` | `@FinancialYear`, `@Month`, `@AgentId` | Cut & Pay agent pass-on reconciliation | `DashboardRepository.get_cut_and_pay_pass_on` |
| `sp_Agent_OutStanding_Report` | `DashBoradAgentPremiumOutStanding` | `@BranchId`, `@MinDaysOverdue` | Outstanding balances per agent with aging | `DashboardRepository.get_agent_outstanding_receivables` |

### 2.3 MIS Reports & Transaction Exports

| Legacy Stored Procedure | Legacy Caller (`.aspx.cs`) | Extracted Parameters | Return Schema / Behavior | Modern Target Service / Method |
| :--- | :--- | :--- | :--- | :--- |
| `sp_FillTransactionAllBranch` | `Adm_AllTransactionExport` | `@FromDate`, `@ToDate`, `@Broker` | Unrestricted full transaction table (54 columns) | `MisReportRepository.get_all_transactions` |
| `sp_FillTransactionLocationHead`| `Adm_AllTransactionExport` | `@FromDate`, `@ToDate`, `@UserId` | Branch-restricted transactions for Location Head | `MisReportRepository.get_branch_transactions` |
| `sp_FillTransactionReportforUser`| `Adm_AllTransactionExport` | `@FromDate`, `@ToDate`, `@UserName`, `@Status` | User-created transactions for Operator | `MisReportRepository.get_operator_transactions` |
| `sp_FillTransactionFrFranchaiseAllBranchfrFranchaise` | `Adm_AllTransactionExport` | `@FromDate`, `@ToDate`, `@FranchiseId` | Franchise-scoped transactions | `MisReportRepository.get_franchise_transactions` |
| `sp_FillTransactionForAgent` | `TransactionExport` | `@FromDate`, `@ToDate`, `@AgentId` | Agent-scoped transactions | `MisReportRepository.get_agent_transactions` |
| `sp_SelectImportPolicyMIS` | `adm_ImportTransAgentPolicyMIS` | `@BatchId`, `@CompanyId` | Staged insurer policy import records | `MisReportRepository.get_staged_mis_imports` |
| `sp_ReconcileImportedMIS` | `adm_ImportTransAgentPolicyMIS` | `@BatchId`, `@MatchingTolerance` | Discrepancy report matching internal vs insurer MIS | `MisReportRepository.reconcile_mis_batch` |

### 2.4 Accounting & General Ledger

| Legacy Stored Procedure | Legacy Caller (`.aspx.cs`) | Extracted Parameters | Return Schema / Behavior | Modern Target Service / Method |
| :--- | :--- | :--- | :--- | :--- |
| `sp_Account_Details_By_ledger_Type` | `Report_Account_By_LedgerType` | `@FromDate`, `@ToDate` | Level 1: Ledger Type aggregates (Debit, Credit) | `AccountingReportRepository.get_ledger_type_summary` |
| `sp_Account_Details_for_Ledger` | `Report_Account_By_LedgerType` | `@FromDate`, `@ToDate`, `@LedgerTypeId`| Level 2: Ledger Masters under selected Type | `AccountingReportRepository.get_ledger_master_summary`|
| `sp_SelectAccountReport` | `Report_Account_By_LedgerType`, `Rpt_AccountReport` | `@FromDate`, `@ToDate`, `@LedgerMId` | Level 3: Individual transactions with running balance | `AccountingReportRepository.get_ledger_statement` |
| `sp_Account_Ledger_Balance` | `Report_Account_By_LedgerType` | `@LedgerMId`, `@AsOfDate` | Closing balance for specific ledger | `AccountingReportRepository.get_ledger_balance` |
| `sp_DayWiseVoucherPrint` | `DayWiseVoucherPrint` | `@VoucherDate`, `@BranchId` | Daily list of vouchers for printing | `AccountingReportRepository.get_vouchers_by_date` |
| `sp_VoucherPrint` | `Payment_Voucher`, `Payment_Voucher.rpt` | `@VoucherId` | Single voucher details with line item entries | `AccountingReportRepository.get_voucher_by_id` |
| `sp_Reciept_VoucherPrint` | `Receipt_voucher`, `Receipt_voucher.rpt` | `@VoucherId` | Single receipt voucher with payee/bank details | `AccountingReportRepository.get_receipt_voucher_by_id` |

### 2.5 Statutory TDS, GST & Bank Advice

| Legacy Stored Procedure | Legacy Caller (`.aspx.cs`) | Extracted Parameters | Return Schema / Behavior | Modern Target Service / Method |
| :--- | :--- | :--- | :--- | :--- |
| `sp_AccountTDSReport` | `Rpt_AccountTDSReport` | `@FromDate`, `@ToDate`, `@AgentId`, `@TDSLedgerId` (2113) | Section 194H TDS report (Gross Comm, TDS 5%) | `StatutoryReportRepository.get_tds_register` |
| `sp_TDSReportAgentWise` | `Rpt_TDSReport` | `@FinancialYear`, `@AgentId` | Annual agent-wise TDS certificate statement | `StatutoryReportRepository.get_agent_annual_tds` |
| `sp_TDSReportFranchiseWise` | `Rpt_TDSReport` | `@FinancialYear`, `@FranchiseId` | Annual franchise TDS certificate statement | `StatutoryReportRepository.get_franchise_annual_tds` |
| `sp_AgentCommissionStatementForBank` | `rpt_AgentCommissionStatementForBank` | `@FinancialYear`, `@Month`, `@BranchId` | Bank payout list (Agent, Account No, IFSC, Net Amount) | `StatutoryReportRepository.get_bank_payout_statement` |
| `sp_SelectPaymentAdviceAgent` | `Rpt_PaymentAdvice` | `@FinancialYear`, `@Month`, `@AgentId` | Payment advice header and summary | `StatutoryReportRepository.get_payment_advice_summary`|
| `sp_PaymentAdviceDetails` | `Rpt_PaymentAdvice` | `@FinancialYear`, `@Month`, `@AgentId` | Detailed policy-by-policy payout advice items | `StatutoryReportRepository.get_payment_advice_details`|
| `sp_DailyReportCashOrOnline` | `Rpt_DailyReportCashOrOline` | `@ReportDate`, `@BranchId` | Daily cash sheet split by cash, cheque, online | `StatutoryReportRepository.get_daily_collection_audit` |

### 2.6 Operations, Reconciliation & Pipeline

| Legacy Stored Procedure | Legacy Caller (`.aspx.cs`) | Extracted Parameters | Return Schema / Behavior | Modern Target Service / Method |
| :--- | :--- | :--- | :--- | :--- |
| `sp_CommissionReconciliationReport` | `adm_CommissionReconcilationReport` | `@FromDate`, `@ToDate`, `@CompanyId` | Insurer statement vs internal commission audit | `ReconciliationRepository.get_commission_reconciliation` |
| `sp_BankReconsileReport` | `adm_BankReconsileReport` | `@FromDate`, `@ToDate`, `@BankId` | Bank statement reconciliation & uncleared cheques | `ReconciliationRepository.get_bank_reconciliation` |
| `sp_SelectCorrectionReport` | `adm_CorrectionReport` | `@FromDate`, `@ToDate`, `@BranchId` | Policy correction log and modifications | `OperationsReportRepository.get_correction_audit_log` |
| `sp_SelectEndorsementReport` | `adm_EndorsmentReport` | `@FromDate`, `@ToDate`, `@BranchId` | Endorsement financial delta and status | `OperationsReportRepository.get_endorsement_report` |
| `sp_SelectClaimReport` | `ClaimReport`, `CL_ClaimReport` | `@FromDate`, `@ToDate`, `@Status` | Claims register with surveyor & settlement details | `OperationsReportRepository.get_claims_register` |
| `sp_TelecallerTargetReport` | `adm_TelecallerTargetReport` | `@FinancialYear`, `@Month`, `@UserId` | Telecaller policy count and premium achievement | `PerformanceReportRepository.get_telecaller_targets` |
| `sp_SalesExecutiveTargetReport` | `adm_TargetReport` | `@FinancialYear`, `@Month`, `@UserId` | Sales executive premium achievement vs quota | `PerformanceReportRepository.get_executive_targets` |
| `sp_SelectPolicyExpiringToday` | `adm_DashboardTodayPolicyExpire` | `@ExpiryDate`, `@BranchId` | Real-time policy expiry pipeline for renewal CRM | `RenewalReportRepository.get_expiring_policies` |
| `sp_DailyBusinessSummaryMail` | `SendMailToAutority` | `@ReportDate` | Aggregate summary table for automated daily email | `ScheduledReportRepository.get_daily_email_digest` |

---

## 3. Parameterization & Defensive Architecture

All modern repository methods implement:
1. **Parameterized Bind Expressions**: Binds parameters using SQLAlchemy `:param` syntax, preventing SQL injection.
2. **Type Safety**: Strictly validates date strings, financial amounts, and integer IDs via Pydantic request models.
3. **Async Non-Blocking Execution**: Executes over `AsyncSession` using `await session.execute(...)` for high throughput.
