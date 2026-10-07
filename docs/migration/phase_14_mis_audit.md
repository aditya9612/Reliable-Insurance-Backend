# Phase 14 — MIS Reports & Transaction Exports Forensic Audit

> **Audit Status**: COMPLETE (FORENSIC EXTRACTION)  
> **Phase**: Phase 14 (Reporting, Dashboard, MIS, POSP Invoicing & Statutory Statements) — Stage A  
> **Repository**: `Reliable-Insurance-Backend`  
> **Legacy Source**: `c:\Users\Admin\Downloads\InsurancefinalNew_2026_09_23\InsurancefinalNew`  
> **Mode**: STRICTLY READ-ONLY FORENSIC AUDIT (No implementation)

---

## 1. Executive Summary

Management Information System (MIS) reports and data export utilities represent the high-volume operational core of the legacy system. The primary entry point for transactional reporting is `Adm_AllTransactionExport.aspx.cs`, supplemented by `TransactionExport.aspx.cs`, `ViewAppMISTransction.aspx.cs`, and `adm_ImportTransAgentPolicyMIS.aspx.cs`.

This audit documents the row-level data scoping rules by user role, strict export permissions, column masking rules, HTML-table spreadsheet formatting, and insurer bulk import reconciliation.

---

## 2. Role-Based Data Scoping Architecture

The legacy system applies strict multi-tenant row-level filtering based on the caller's role and assigned organizational boundaries:

```csharp
// Forensic extraction from Adm_AllTransactionExport.aspx.cs:L68-L115
if (Session["UserType"].ToString() == "LOCATION HEAD") {
    dt = DAL.sp_FillTransactionLocationHead(FromDate, ToDate, Convert.ToInt32(Session["UserId"]));
}
else if (Session["UserType"].ToString() == "OPERATOR") {
    dt = DAL.sp_FillTransactionReportforUser(FromDate, ToDate, Session["UserName"].ToString(), "PendingAPPnew");
}
else if (Session["UserType"].ToString() == "FRANCHISE OPERATOR") {
    dt = DAL.sp_FillTransactionReportforUser(FromDate, ToDate, Session["UserName"].ToString(), "PendingAPPnewFranchise");
}
else if (Session["UserType"].ToString() == "FRANCHISE") {
    dt = DAL.sp_FillTransactionFrFranchaiseAllBranchfrFranchaise(FromDate, ToDate, Convert.ToInt32(Session["FranchiseId"]));
}
else if (Session["UserType"].ToString() == "ADMIN" || Session["UserType"].ToString() == "ACCOUNT" || Session["UserType"].ToString() == "IT SUPPORT") {
    dt = DAL.sp_FillTransactionAllBranch(FromDate, ToDate, ddlBroker.SelectedValue);
}
```

### 2.1 Scope Rules Matrix

| User Role | Scope Boundary | Legacy Stored Procedure | Security Rule / Isolation |
| :--- | :--- | :--- | :--- |
| **`ADMIN` / `IT SUPPORT`** | Global (All Branches) | `sp_FillTransactionAllBranch(FromDate, ToDate, Broker)` | Unrestricted cross-branch visibility. Can filter by any branch, insurer, agent, or broker entity. |
| **`ACCOUNT`** | Global (Financials) | `sp_FillTransactionAllBranch(FromDate, ToDate, Broker)` | Full transactional view for banking and ledger reconciliation. |
| **`LOCATION HEAD` / `BRANCH MANAGER`** | Single Branch | `sp_FillTransactionLocationHead(FromDate, ToDate, UserId)` | Strictly filtered by the branch assigned to the `UserId`. Cross-branch records invisible. |
| **`OPERATOR`** | Self-Created Records | `sp_FillTransactionReportforUser(FromDate, ToDate, UserName, "PendingAPPnew")` | Restricted to records where `tbl_transaction.CreatedBy == UserName`. |
| **`FRANCHISE OPERATOR`** | Franchise Scope | `sp_FillTransactionReportforUser(FromDate, ToDate, UserName, "PendingAPPnewFranchise")` | Restricted to records created within that specific franchise location. |
| **`FRANCHISE`** | Franchise Entity | `sp_FillTransactionFrFranchaiseAllBranchfrFranchaise(FromDate, ToDate, FranchiseId)` | Bound to all agents and transactions linked to `FranchiseId`. |
| **`AGENT` / `POSP`** | Agent Self | `sp_FillTransactionForAgent(FromDate, ToDate, AgentId)` | Restricted strictly to the authenticated agent's own policies. |

---

## 3. Strict Export Gating Security Rule

A fundamental security requirement discovered in `Adm_AllTransactionExport.aspx.cs:L48`:

```csharp
if (Session["UserType"].ToString() == "ADMIN" || 
    Session["UserType"].ToString() == "IT SUPPORT" || 
    Session["UserType"].ToString() == "ACCOUNT") 
{
    btn_Export.Visible = true;
}
else 
{
    btn_Export.Visible = false;
}
```

> [!WARNING]
> **Strict Export Authorization Rule**:
> While `OPERATOR`, `LOCATION HEAD`, `FRANCHISE`, and `SALES` roles can search and view transactions on-screen within their authorized data scope, **file download / export triggers (`.xlsx`, `.csv`) are strictly prohibited and gated to `ADMIN`, `IT SUPPORT`, and `ACCOUNT`**. Attempted export requests from unauthorized roles must return HTTP 403 Forbidden.

---

## 4. Column Schema & Masking Rules

The transaction report contains 54 distinct fields. In legacy, 12 sensitive internal columns are hidden dynamically prior to display or export based on role permissions:

### 4.1 Internal Masked Columns (12 Hidden Columns)
1. `CompanyCommissionRate` — Insurer gross commission percentage.
2. `TotalCompanyCommission` — Total gross brokerage received from insurer.
3. `CompanyProfit` — Net brokerage profit retained by brokerage.
4. `FranchiseCommissionRate` — Franchise margin rate.
5. `FranchiseCommissionAmount` — Absolute franchise commission payable.
6. `TDSPercentage` — System internal TDS deduction bracket.
7. `CreatedById` — Internal user database primary key.
8. `UpdatedById` — Internal user modification audit ID.
9. `InternalAuditRemarks` — Compliance and audit flagging notes.
10. `InsurerReconciliationId` — Insurer statement reconciliation batch ID.
11. `ChequeBouncePenalty` — Internal penalty allocation amount.
12. `IsLockedForAudit` — Internal record freeze boolean flag.

### 4.2 Standard Visible Columns (42 Columns)
- **Policy Metadata**: Policy No, Transaction ID, Policy Date, Risk Start Date, Risk End Date, Insurance Company, Broker Name, Policy Type (Comprehensive / TP / OD / Standalone).
- **Vehicle Details**: Vehicle Reg No, Make, Model, Variant, Sub-Type, Fuel Type, Manufacturing Year, Engine No, Chassis No, RTO Code, Seating Capacity, GVW/CC.
- **Client Information**: Customer Name, Mobile No, Email ID, Customer City, Customer State, Pincode, Nominee Name, Nominee Relation.
- **Commercial & Payout Figures**: OD Premium, TP Premium, Net Premium, GST Amount, Gross Premium, Payment Mode, Cheque No, Cheque Date, Bank Name, Agent Name, POSP Code, Agent Commission Amount, Net Agent Payable.

---

## 5. File Layout & Styling Specifications

The legacy export mechanism renders an HTML table with an Excel MIME type:

```csharp
Response.Clear();
Response.Buffer = true;
Response.AddHeader("content-disposition", "attachment;filename=TransactionReport_" + DateTime.Now.ToString("yyyyMMdd") + ".xls");
Response.Charset = "";
Response.ContentType = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";
```

### Visual Layout & Formatting Rules:
- **Font Family**: Century Gothic, Arial, or Calibri (10pt regular).
- **Table Header**:
  - Background Color: `#48D1CC` (Medium Turquoise).
  - Text Color: `#000000` (Bold 10pt).
  - Text Alignment: Centered for dates and codes; Left-aligned for text descriptions; Right-aligned for financial amounts.
- **Data Rows**:
  - Row Height: 20pt.
  - Alternating Row Background: `#FFFFFF` and `#F8F9FA`.
  - Number Formatting: Currency columns formatted as `#,##0.00`; Dates formatted as `dd/MM/yyyy`.

---

## 6. Bulk Policy MIS Import Reconciliation (`adm_ImportTransAgentPolicyMIS.aspx.cs`)

### 6.1 Purpose
Insurance companies provide monthly or weekly transactional MIS spreadsheets containing issued policies. The legacy system provides an automated reconciliation page to import these files and match them against internal transactions.

### 6.2 Reconciliation Matching Pipeline
1. **File Ingestion**: Excel file uploaded $\rightarrow$ parsed into staging table.
2. **Key Matching**: Matches on `PolicyNo` and `InsuranceCompanyId`.
3. **Discrepancy Detection**:
   - `PREMIUM_MISMATCH`: Net premium in insurer statement differs from booked net premium by $> \pm 1.00$ INR.
   - `COMMISSION_MISMATCH`: Actual commission remitted by insurer differs from system expected brokerage.
   - `POLICY_NOT_FOUND`: Insurer lists policy that does not exist in local database (orphaned transaction).
   - `STATUS_MISMATCH`: Policy marked Active in insurer MIS but Cancelled / Endorsed locally.
4. **Resolution**: Administrative override allows updating internal policy status or booking commission adjustments.
