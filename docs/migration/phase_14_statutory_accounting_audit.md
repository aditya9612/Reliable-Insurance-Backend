# Phase 14 — Statutory & Accounting Statements Forensic Audit

> **Audit Status**: COMPLETE (FORENSIC EXTRACTION)  
> **Phase**: Phase 14 (Reporting, Dashboard, MIS, POSP Invoicing & Statutory Statements) — Stage A  
> **Repository**: `Reliable-Insurance-Backend`  
> **Legacy Source**: `c:\Users\Admin\Downloads\InsurancefinalNew_2026_09_23\InsurancefinalNew`  
> **Mode**: STRICTLY READ-ONLY FORENSIC AUDIT (No implementation)

---

## 1. Executive Summary

Statutory compliance and financial accounting integrity form the bedrock of insurance brokerage operations. The legacy codebase contains extensive reporting screens and Crystal Reports governing:
1. 4-Tier Hierarchical Ledger Statements (`Report_Account_By_LedgerType.aspx.cs`, `Rpt_AccountReport.rpt`)
2. Tax Deducted at Source (TDS) Statutory Registers (`Rpt_AccountTDSReport.aspx.cs`, `Rpt_TDSReport.aspx`)
3. Bank Payout Commission Statements (`rpt_AgentCommissionStatementForBank.aspx.cs`)
4. Official Payment Advice Vouchers (`Rpt_PaymentAdvice.aspx.cs`)
5. Cut & Pay / Pass-On Financial Statements (`Rpt_CutNPayAndPassOn.aspx.cs`)
6. Daily Cash & Online Collection Audits (`Rpt_DailyReportCashOrOline.aspx.cs`)
7. Insurer Commission Reconciliation Statements (`adm_CommissionReconcilationReport.aspx.cs`)

This audit documents the hierarchical data structures, signed polarity conventions, hardcoded ledger masters, and statutory reconciliation rules.

---

## 2. 4-Tier Hierarchical Ledger Drilldown Architecture

The core accounting ledger system (`Report_Account_By_LedgerType.aspx.cs`) operates as an interactive 4-level drilldown hierarchy:

```
[Level 1: Ledger Type Grouping]
       │
       ▼  sp_Account_Details_By_ledger_Type
[Level 2: Ledger Master Account]
       │
       ▼  sp_Account_Details_for_Ledger
[Level 3: Detailed Ledger Transactions]
       │
       ▼  sp_SelectAccountReport
[Level 4: Voucher Document / Receipt Print]
          sp_VoucherPrint / sp_Reciept_VoucherPrint
```

### 2.1 Drilldown Levels Breakdown

| Level | Granularity | Legacy Stored Procedure | Inputs | Output Schema |
| :--- | :--- | :--- | :--- | :--- |
| **Level 1** | **Ledger Type** | `sp_Account_Details_By_ledger_Type` | `FromDate`, `ToDate` | `LedgerTypeId`, `LedgerTypeName`, `TotalDebit`, `TotalCredit`, `NetBalance` |
| **Level 2** | **Ledger Master** | `sp_Account_Details_for_Ledger` | `FromDate`, `ToDate`, `LedgerTypeId` | `LedgerMId`, `LedgerName`, `OpeningBalance`, `DebitSum`, `CreditSum`, `ClosingBalance` |
| **Level 3** | **Transaction Statement** | `sp_SelectAccountReport` | `FromDate`, `ToDate`, `LedgerMId` | `VoucherId`, `VoucherNo`, `VoucherDate`, `Particulars`, `DebitAmount`, `CreditAmount`, `RunningBalance` |
| **Level 4** | **Voucher Document** | `sp_VoucherPrint` / `sp_Reciept_VoucherPrint` | `VoucherId` | Line items, Cheque Details, Narration, Approver, Payee Signature Box |

---

## 3. Financial Polarity & Balance Conventions

A critical forensic finding in `Report_Account_By_LedgerType.aspx.cs` and `DAL_Operations.cs`:
The legacy database records financial movements in `tbl_account_transaction` using a **signed single `Amount` column convention**:
- **Positive Value ($+A$)**: Represents a **DEBIT** entry (Assets, Expenses, Cash/Bank Inflow).
- **Negative Value ($-A$)**: Represents a **CREDIT** entry (Liabilities, Incomes, Payables, Retentions).

### Running Balance Formula
For a sequence of transactions $t_1, t_2, \dots, t_n$ under ledger $L$:
$$\text{Opening Balance} = B_0$$
$$\text{Running Balance}_k = B_0 + \sum_{i=1}^{k} \left(\text{DebitAmount}_i - \text{CreditAmount}_i\right)$$
$$\text{Closing Balance} = \text{Running Balance}_n$$

---

## 4. Statutory TDS (Tax Deducted at Source) Register

### 4.1 Income Tax Section 194H Mandate
Commission paid to agents, POSPs, and franchises is subject to statutory TDS under Section 194H of the Indian Income Tax Act at a standard rate of **$5\%$**.

### 4.2 The Hardcoded TDS Ledger: `LedgerMId = 2113`
Forensic analysis of `Rpt_AccountTDSReport.aspx.cs:L74` and `DAL_Operations.cs:sp_AccountTDSReport` reveals a crucial historical constant:
```csharp
// Forensic extraction from Rpt_AccountTDSReport.aspx.cs
int tdsLedgerId = 2113; // Fixed Master ID for TDS on Commission across all branches
DataTable dt = DAL.sp_AccountTDSReport(FromDate, ToDate, agentId, tdsLedgerId);
```

> [!IMPORTANT]
> **TDS Ledger 2113: Verified Legacy Default vs Proposed Tenant Hardening (`GAP-UNK-14-003`)**:
> In legacy source code, `LedgerMId = 2113` is the verified default/evidence for TDS across historical transactions. However, it cannot be assumed that 2113 is universally correct across all future branches or multi-tenant deployments. Therefore, 2113 remains the verified legacy default, while configurable tenant overrides represent a proposed modernization hardening target for Phase 14B.

### 4.3 TDS Report Fields & Output
- `PAN Number` (Validated against Section 206AA: If PAN absent/invalid, higher rate $20\%$ applies)
- `Agent / Franchise Name`
- `Gross Commission Paid`
- `Taxable Base Amount`
- `TDS Deducted (5%)`
- `Challan / BSR Code` (Once deposited to government treasury)
- `Voucher No & Date`

---

## 5. Bank Commission Statements (`rpt_AgentCommissionStatementForBank.aspx.cs`)

### 5.1 Purpose & Verified Legacy Business Scope
Brokerages execute bulk NEFT/RTGS payouts to hundreds of agents at month-end. This module generates the banking disbursement statement.
- Inputs: Financial Year, Month, Payment Mode (`BANK_TRANSFER`), Branch.
- Output Fields (Verified Legacy Grid):
  1. Serial Number
  2. Agent Full Name
  3. Bank Name
  4. Account Number
  5. IFSC Code (11-character Indian Financial System Code)
  6. Net Disbursement Amount (Rupees)
  7. Payment Narration (`COMMISSION FOR [MONTH] [YEAR]`)

### 5.2 Banking Portal Specifications: Known Business Scope vs UNKNOWN Portal Specs (`GAP-UNK-14-002`)
Legacy bank payout behavior is verified at the business/report level (generating a standard tabular payout statement). However, exact proprietary batch-file specifications required by specific banking portals (such as ICICI CMS fixed-width encrypted files or HDFC Corporate Banking upload specs) remain **UNKNOWN** (`GAP-UNK-14-002`). Phase 14B may implement a configurable banking export abstraction, but this is explicitly classified as an **intentional modernization**, not a claim of verified legacy file-format parity.

---

## 6. Daily Cash & Online Collection Audit (`Rpt_DailyReportCashOrOline.aspx.cs`)

### 6.1 Daily Reconciled Collection Register
Operates as the day-end closing cash sheet for branch cashiers:
- Splits transactions strictly by mode:
  - `CASH`: Audited against physical cash in branch safe.
  - `CHEQUE`: Audited against physical cheques received pending bank deposit.
  - `ONLINE / UPI`: Audited against payment gateway settlement alerts.
- Computes:
  $$\text{Total Daily Inflow} = \text{Cash} + \text{Cheques} + \text{Online}$$
- Flags any cash receipts greater than $\text{INR } 1,99,999$ for statutory Section 269ST compliance.
