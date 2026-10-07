# Phase 14 — Legacy Reporting, Dashboard, MIS & POSP Inventory

> **Audit Status**: COMPLETE (FORENSIC EXTRACTION)  
> **Phase**: Phase 14 (Reporting, Dashboard, MIS, POSP Invoicing & Statutory Statements) — Stage A  
> **Repository**: `Reliable-Insurance-Backend`  
> **Legacy Source**: `c:\Users\Admin\Downloads\InsurancefinalNew_2026_09_23\InsurancefinalNew`  
> **Mode**: STRICTLY READ-ONLY FORENSIC AUDIT (No implementation)

---

## 1. Executive Summary

A comprehensive forensic audit of the legacy C# ASP.NET monolith (`InsurancefinalNew`) was executed across all 621 WebForms (`.aspx.cs`), DAL operations (`DAL_Operations.cs`), web services (`Service.asmx.cs`), and Crystal Reports (`.rpt`).

This inventory captures every reporting screen, dashboard, MIS transaction export, POSP payout invoice generator, statutory statement, and management report present in the legacy insurance system.

Total Reporting & Dashboard Artefacts Discovered:
- **WebForms Reporting Pages**: 47 distinct `.aspx.cs` pages (100% surface inventory & call sites mapped)
- **Crystal Reports Files**: 9 compiled binary `.rpt` files (100% surface inventory; internal binary formulas UNKNOWN per `GAP-UNK-14-001`)
- **Reporting Stored Procedures**: 104 distinct `sp_*` procedures in DAL (100% caller & parameter mapped; behavioral parity evidence-backed where code/schema available, UNKNOWN where body unavailable per `GAP-UNK-001`)
- **Dashboard Web Methods**: 18 specialized reporting web methods in `Service.asmx.cs` (100% mapped)

---

## 2. Category Inventory Table

The legacy reporting architecture is categorized into 7 functional domains across 21 report groups:

| Category Code | Domain | Legacy Pages / Modules | Stored Procedures | Output Formats | Primary Roles Authorized |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **CAT-01** | **POSP & Agent Invoices** | `rpt_POSP_Invoice.aspx`, `rpt_POSP_InvoiceReport.aspx`, `InvoiceAgentPaymentrpt.aspx` | `sp_POSP_Insert_Invoice`, `sp_POSP_Invoice_Report`, `sp_POPSInvoiceRpt`, `sp_InvoiceAgentPaymet`, `sp_POSP_CheckInvoiceNo` | HTML, PDF (iTextSharp) | `ADMIN`, `ACCOUNT` |
| **CAT-02** | **Executive & Admin Dashboards** | `Dashboard.aspx`, `DashBoardAccountSummery.aspx`, `OwnerDashBoard.aspx` | `sp_Agent_PremiumSummeryAllMonth`, `sp_SelectInsuranceCompanyNetPermiumbyMonyh`, `sp_Dashboard_BrokerWiseBusiness`, `sp_Dashboard_CompanyWiseBusiness` | On-screen Grid, HTML Cards | `ADMIN`, `ACCOUNT`, `IT SUPPORT` |
| **CAT-03** | **Agent Cut & Pay & Outstandings** | `DashBoradAgentPremiumCutNPay.aspx`, `DashBoradAgentPremiumOutStanding.aspx`, `Rpt_CutNPayAndPassOn.aspx` | `sp_Agent_PremiumSummery_CutNPay`, `sp_Agent_PremiumSummery_CutNPayPassOn`, `sp_Agent_OutStanding_Report` | On-screen Grid, HTML Table | `ADMIN`, `ACCOUNT`, `LOCATION HEAD` |
| **CAT-04** | **MIS Transaction Exports** | `Adm_AllTransactionExport.aspx`, `TransactionExport.aspx`, `ViewAppMISTransction.aspx` | `sp_FillTransactionAllBranch`, `sp_FillTransactionLocationHead`, `sp_FillTransactionReportforUser`, `sp_FillTransactionFrFranchaiseAllBranchfrFranchaise` | HTML `.xls` (Century Gothic, `#48D1CC`) | `ADMIN`, `IT SUPPORT`, `ACCOUNT` (Export strictly gated) |
| **CAT-05** | **Bulk Policy MIS Imports** | `adm_ImportTransAgentPolicyMIS.aspx` | `sp_SelectImportPolicyMIS`, `sp_ReconcileImportedMIS` | GridView, Reconcile Summary | `ADMIN`, `IT SUPPORT` |
| **CAT-06** | **Accounting 4-Tier Ledgers** | `Report_Account_By_LedgerType.aspx`, `Rpt_AccountReport.rpt` | `sp_Account_Details_By_ledger_Type`, `sp_Account_Details_for_Ledger`, `sp_SelectAccountReport`, `sp_Account_Ledger_Balance` | Crystal Reports, HTML Grid, PDF | `ADMIN`, `ACCOUNT` |
| **CAT-07** | **TDS Statutory Statements** | `Rpt_AccountTDSReport.aspx`, `Rpt_TDSReport.aspx` | `sp_AccountTDSReport`, `sp_TDSReportAgentWise`, `sp_TDSReportFranchiseWise` | HTML `.xls`, On-screen Grid | `ADMIN`, `ACCOUNT` |
| **CAT-08** | **GST Statements & Taxes** | `rpt_POSP_Invoice.aspx` (GST 18% calculation), Account Ledger Reports | `sp_SelectAccountReport` (Filtered by GST Ledger) | HTML, PDF | `ADMIN`, `ACCOUNT` |
| **CAT-09** | **Bank Commission Statements** | `rpt_AgentCommissionStatementForBank.aspx` | `sp_AgentCommissionStatementForBank`, `sp_SelectBankPaymentList` | HTML Table, CSV / XLS | `ADMIN`, `ACCOUNT` |
| **CAT-10** | **Payment Advice Statements** | `Rpt_PaymentAdvice.aspx` | `sp_SelectPaymentAdviceAgent`, `sp_PaymentAdviceDetails` | HTML Print View, PDF | `ADMIN`, `ACCOUNT` |
| **CAT-11** | **Daily Cash & Online Collections**| `Rpt_DailyReportCashOrOline.aspx` | `sp_DailyReportCashOrOnline`, `sp_SelectCollectionByMode` | GridView, Export to Excel | `ADMIN`, `ACCOUNT`, `BRANCH MANAGER` |
| **CAT-12** | **Vouchers & Day Book** | `DayWiseVoucherPrint.aspx`, `Receipt_voucher.aspx`, `Payment_Voucher.aspx` | `sp_DayWiseVoucherPrint`, `sp_Reciept_VoucherPrint`, `sp_VoucherPrint` | Crystal Reports (`Payment_Voucher.rpt`) | `ADMIN`, `ACCOUNT` |
| **CAT-13** | **Commission Reconciliation** | `adm_CommissionReconcilationReport.aspx` | `sp_CommissionReconciliationReport`, `sp_ReconcileInsurerStatement` | Reconcile Grid, Discrepancy List | `ADMIN`, `ACCOUNT` |
| **CAT-14** | **Bank Reconciliation Statements** | `adm_BankReconsileReport.aspx` | `sp_BankReconsileReport`, `sp_SelectUnmatchedCheques` | GridView, Excel Export | `ADMIN`, `ACCOUNT` |
| **CAT-15** | **Policy Correction & Audit Log** | `adm_CorrectionReport.aspx` | `sp_SelectCorrectionReport`, `sp_AuditTransactionHistory` | GridView, Audit Trail | `ADMIN`, `IT SUPPORT` |
| **CAT-16** | **Endorsement Reports** | `adm_EndorsmentReport.aspx` | `sp_SelectEndorsementReport`, `sp_EndorsementFinancialDelta` | GridView, CSV Export | `ADMIN`, `OPERATOR`, `LOCATION HEAD` |
| **CAT-17** | **Claims Register & Status** | `ClaimReport.aspx`, `CL_ClaimReport.aspx` | `sp_SelectClaimReport`, `sp_ClaimSummaryStatus` | GridView, PDF Export | `ADMIN`, `OPERATOR`, `LOCATION HEAD` |
| **CAT-18** | **Telecaller & Sales Targets** | `adm_TelecallerTargetReport.aspx`, `adm_TargetReport.aspx` | `sp_TelecallerTargetReport`, `sp_SalesExecutiveTargetReport` | Monthly Target Matrix, Progress Bar | `ADMIN`, `SALES`, `LOCATION HEAD` |
| **CAT-19** | **Executive Performance** | `adm_ExecutiveReport.aspx` | `sp_ExecutivePerformanceReport` | Performance Grid, Conversion % | `ADMIN`, `LOCATION HEAD` |
| **CAT-20** | **Renewal CRM & Expiry Tracking** | `adm_DashboardTodayPolicyExpire.aspx`, `rpt_RenewalPolicy.aspx` | `sp_SelectPolicyExpiringToday`, `sp_RenewalNoticeList` | Expiry List, Bulk SMS/Email Dispatch | `ADMIN`, `TELECALLER`, `OPERATOR` |
| **CAT-21** | **Automated Scheduled MIS Dispatches** | `SendMailToAutority.aspx`, `SendMailToAutorityDaily.aspx` | `sp_DailyBusinessSummaryMail`, `sp_MonthlyPerformanceDigest` | Automated HTML Email Digest | `ADMIN` (Automated Background Task) |

---

## 3. Detailed Forensic Page Catalog

### 3.1 POSP & Agent Invoices
- **`rpt_POSP_Invoice.aspx.cs`**:
  - **Purpose**: Generates official payout invoices for POSP agents.
  - **Inputs**: `ddlPOSPType` (Direct / POSP), `ddlAgent` (`AgentId`), `txtInvoiceDate`, `txtInvoiceNo`, `txtAmount`.
  - **Calculation**: Base amount $\rightarrow$ checks agent GST presence. If present: $18\%$ IGST added. If absent: $0\%$ GST. Computes grand total.
  - **Number to Words**: Invokes `BLL_GetNumberIntoWord(GrandTotal)`.
  - **PDF Export**: Generates A4 PDF using iTextSharp `XMLWorkerHelper` and saves to `~/POSP_Invoice/{agentName}-{invoiceNo}.pdf`.
  - **Persistence**: Writes record into `tbl_posp_invoice` using `sp_POSP_Insert_Invoice`.

- **`rpt_POSP_InvoiceReport.aspx.cs`**:
  - **Purpose**: Financial year and month-wise listing of POSP invoices generated.
  - **Inputs**: `ddlFinancialYear`, `ddlMonth`, `ddlAgent`.
  - **Outputs**: Grid listing `InvoiceNo`, `AgentName`, `Amount`, `GSTAmt`, `GrandTotal`, `CreatedDate`, and action link to view/download generated PDF.
  - **SP**: `sp_POSP_Invoice_Report`.

- **`InvoiceAgentPaymentrpt.aspx.cs`**:
  - **Purpose**: Agent payout reconciliation and payment disbursement tracking.
  - **Inputs**: Date range, `AgentId`, `PaymentStatus` (Paid / Unpaid).
  - **SP**: `sp_InvoiceAgentPaymet`.

### 3.2 Dashboards & Executive KPI Summaries
- **`Dashboard.aspx.cs`**:
  - **Purpose**: Primary administrative dashboard showing full Indian Fiscal Year (April to March) 12-month performance matrix.
  - **Inputs**: `ddlYear` (FY YYYY-YYYY), `ddlBroker`, Date mode (`T_Date` vs `R_Date`).
  - **Special Branch Routing**: Branch `105` automatically reroutes queries to `sp_*_EFF` variants.
  - **Aggregations**: Computes 7 broker company business splits, 5 sourcing channel splits (Agent, Direct, Insurance Executive, Self, Franchise), and month-by-month premium volumes.

- **`DashBoardAccountSummery.aspx.cs`**:
  - **Purpose**: Financial health and accounts dashboard showing cash vs online vs cheque collections, daily net premium, and agent payouts.
  - **SP**: `sp_Agent_PremiumSummeryAllMonth`.

- **`DashBoradAgentPremiumCutNPay.aspx.cs`**:
  - **Purpose**: Real-time monitoring of Cut & Pay policies where net premium was deducted before banking.
  - **SP**: `sp_Agent_PremiumSummery_CutNPay`.

### 3.3 MIS & Data Exports
- **`Adm_AllTransactionExport.aspx.cs`**:
  - **Purpose**: Global comprehensive transaction dump with role-based scoping and strict export gating.
  - **Security Gate**: Export button visible ONLY to `ADMIN`, `IT SUPPORT`, `ACCOUNT`.
  - **Column Masking**: 12 sensitive internal columns hidden before rendering.
  - **Formatting**: HTML table exported as `.xls` with header color `#48D1CC` (Medium Turquoise), Century Gothic 10pt font.

- **`TransactionExport.aspx.cs`**:
  - **Purpose**: Agent and Branch-scoped transaction export for non-admin operational users.

### 3.4 Accounting, Statutory & Ledger Drilldowns
- **`Report_Account_By_LedgerType.aspx.cs`**:
  - **Purpose**: 4-tier drilldown accounting statement:
    1. Group by Ledger Type (`sp_Account_Details_By_ledger_Type`)
    2. Ledger Master details (`sp_Account_Details_for_Ledger`)
    3. Transaction statement (`sp_SelectAccountReport`)
    4. Voucher details (`Payment_Voucher.rpt` / `Receipt_voucher.rpt`).

- **`Rpt_AccountTDSReport.aspx.cs`**:
  - **Purpose**: Statutory TDS statement under Income Tax Act Section 194H ($5\%$).
  - **Hardcoded Identifier**: Uses fixed legacy ledger ID `LedgerMId = 2113` for all TDS deductions.
  - **SP**: `sp_AccountTDSReport`.

---

## 4. Defect Impact & Governance

1. **`DEF-001` (NCB Recovery Franchise Commission Basis)**:
   - Impact: In legacy, NCB recovery affected commission calculation basis. Phase 14 reporting services must use clean transactional net premium values without distorted recovery bases.
2. **`DEF-002` (March Month FY Misclassification)**:
   - Impact: Legacy telecaller target reports misclassified March transactions (`Month >= 3` evaluated to next FY). Phase 14 implements standard fiscal year math: `Month <= 3 ? Year - 1 : Year`.
3. **`DEF-008` (SQL Injection in Reporting Filter Strings)**:
   - Impact: Legacy pages concatenated raw user input strings into SQL filter clauses (`txtSearch.Text`). Phase 14 strictly replaces all dynamic SQL with parameterized SQLAlchemy async queries.
