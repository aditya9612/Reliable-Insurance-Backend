# Phase 14 — Dashboard & KPI Forensic Audit

> **Audit Status**: COMPLETE (FORENSIC EXTRACTION)  
> **Phase**: Phase 14 (Reporting, Dashboard, MIS, POSP Invoicing & Statutory Statements) — Stage A  
> **Repository**: `Reliable-Insurance-Backend`  
> **Legacy Source**: `c:\Users\Admin\Downloads\InsurancefinalNew_2026_09_23\InsurancefinalNew`  
> **Mode**: STRICTLY READ-ONLY FORENSIC AUDIT (No implementation)

---

## 1. Executive Overview

The legacy application hosts 5 specialized executive dashboards designed to deliver real-time operational and financial visibility:
1. **Admin Main Executive Dashboard** (`Dashboard.aspx.cs`)
2. **Financial Accounts Summary Dashboard** (`DashBoardAccountSummery.aspx.cs`)
3. **Owner High-Level Performance Dashboard** (`OwnerDashBoard.aspx.cs`)
4. **Agent Cut & Pay Dashboard** (`DashBoradAgentPremiumCutNPay.aspx.cs`)
5. **Agent Outstanding Receivables Dashboard** (`DashBoradAgentPremiumOutStanding.aspx.cs`)

This audit documents the mathematical formulations, aggregation queries, fiscal calendar alignment, company groupings, and branch routing behaviors governing these dashboards.

---

## 2. Fiscal Calendar & Date Filtering Logic

### 2.1 Fiscal Year Alignment (Indian FY: April 1 to March 31)
The legacy system defines a financial year as running from April 1 of year $Y$ to March 31 of year $Y+1$.
In `Dashboard.aspx.cs:L88` and `BLL_GetFinancialYear()`:

```csharp
int currentMonth = DateTime.Now.Month;
int currentYear = DateTime.Now.Year;
string financialYear = "";
if (currentMonth <= 3) {
    financialYear = (currentYear - 1).ToString() + "-" + currentYear.ToString();
} else {
    financialYear = currentYear.ToString() + "-" + (currentYear + 1).ToString();
}
```

> [!IMPORTANT]
> **Resolution of DEF-002**:
> In legacy telecaller target pages, an erroneous condition `Month >= 3` caused March to be assigned to the succeeding fiscal year. In Phase 14 dashboards and reports, standard Indian FY logic (`Month <= 3 ? (Year - 1)-(Year) : (Year)-(Year + 1)`) is strictly enforced everywhere.

### 2.2 Date Filtering Mode Toggle: `T_Date` vs `R_Date`
In `Dashboard.aspx.cs:L142`, executive users can toggle how transactions are bucketed into months:
- **`T_Date` (Transaction Date / Entry Date)**: Buckets policies by the date the transaction record was entered into the system (`tbl_transaction.CreatedDate` or `PolicyDate`). Used for operational throughput, clerk incentives, and accounting audits.
- **`R_Date` (Risk Start Date)**: Buckets policies by `tbl_transaction.PolicyStartDate`. Used for underwriting exposure, statutory IRDAI reporting, and risk-period analysis.

---

## 3. Organizational & Channel Groupings

### 3.1 Company Grouping Buckets (Broker Entities)
The legacy system aggregates insurance transactions across 7 primary corporate broker/agency entities:
1. **Reliable Associates** (`lblRABusiness`) — Legacy Core Agency
2. **Oasis Insurance** (`lblOSBusiness`) — Regional Subsidiary
3. **Good Insurance** (`lblGIBusiness`) — Partner Agency
4. **Easy Business** (`lblEBBusiness`) — Sub-broker Network
5. **DigiSafe Insurance** (`lblDGBusiness`) — Digital Distribution Channel
6. **Loan & More** (`lblLMBusiness`) — Allied Financial Products Channel
7. **Ideal Brokers** (`lblIDEALBROKERS`) — Corporate Brokerage Channel

### 3.2 Sourcing Channel Buckets
Every transaction is classified into one of 5 sourcing channels (`tbl_transaction.SourceType` / `tbl_transaction.CreatedBy`):
1. **Agent Business** (`AgentBusiness`): Retail POSP / Direct Agents.
2. **Direct Business** (`DirectBusiness`): Walk-in customers and direct branch walk-ins.
3. **Insurance Executive** (`InsuranceExBusiness`): Sourced by salaried sales executives.
4. **Self Business** (`SelfBusiness`): Back-office / Administrative sourcing.
5. **Franchise Business** (`FranchiseABusiness`): Sourced through independent franchise points of sale.

---

## 4. Special Branch Routing: Branch 105 (`_EFF` Isolation)

A critical legacy business rule discovered in `Dashboard.aspx.cs:L320-L365`:
When the dashboard user selects **Branch ID `105`**, standard stored procedures are diverted to dedicated `_EFF` variants:

| Standard Procedure (Branches $\ne 105$) | Branch 105 Procedure (`BranchId == 105`) | Underlying Behavioral Divergence |
| :--- | :--- | :--- |
| `sp_Agent_PremiumSummeryAllMonth` | `sp_Agent_PremiumSummeryAllMonth_EFF` | Evaluates premium based on *Effective Risk Inception Date* instead of entry date, adjusting for retroactive policy endorsements. |
| `sp_SelectInsuranceCompanyNetPermiumbyMonyh` | `sp_SelectInsuranceCompanyNetPermiumbyMonyh_EFF` | Applies company-specific net premium recognition after cancellation netting. |
| `sp_Dashboard_CompanyWiseBusiness` | `sp_Dashboard_CompanyWiseBusiness_EFF` | Restricts calculation to Branch 105 dedicated insurer binding agreements. |

---

## 5. Dashboard Breakdown & Metrics Formulation

### 5.1 Admin Main Dashboard (`Dashboard.aspx.cs`)
- **12-Month Grid (April to March)**:
  - Columns: Month, No. of Policies, OD Premium, TP Premium, Net Premium, Gross Premium, Agent Commission, Brokerage, Company Profit.
  - Calculations per month $m$:
    $$\text{Net Premium}_m = \text{OD Premium}_m + \text{TP Premium}_m$$
    $$\text{Gross Premium}_m = \text{Net Premium}_m + \text{GST Amount}_m$$
    $$\text{Company Profit}_m = \text{Brokerage Earned}_m - \text{Agent Commission Paid}_m$$
  - Subtotals and Grand Totals: Computed dynamically at the footer of each gridview.

### 5.2 Accounts Summary Dashboard (`DashBoardAccountSummery.aspx.cs`)
- **Collection Mode Splits**:
  - Cash Collections: Sum of transactions where `PaymentMode == 'CASH'` and `IsCashReceived == 1`.
  - Cheque Collections: Sum of transactions where `PaymentMode == 'CHEQUE'` (subdivided into Cleared, In-Transit, and Bounced).
  - Online Collections: Sum of transactions where `PaymentMode IN ('ONLINE', 'UPI', 'NEFT', 'PAYTM')`.
- **Net Flow Metric**:
  $$\text{Net Cash Flow} = (\text{Total Collections}) - (\text{Direct Insurer Payouts}) - (\text{Agent Cut \& Pay Retentions})$$

### 5.3 Agent Cut & Pay Dashboard (`DashBoradAgentPremiumCutNPay.aspx.cs`)
- **Cut & Pay Formulation**:
  Under the "Cut & Pay" commercial arrangement, agents collect gross premium from policyholders, deduct their authorized commission immediately, and remit only the balance to the brokerage:
  $$\text{Remittance Due} = \text{Gross Premium} - \text{Agent Commission}$$
  - The dashboard tracks:
    1. Remittance Due vs Remittance Received.
    2. Outstanding balance per agent per policy.
    3. Aging brackets: 0–7 days, 8–15 days, 16–30 days, $> 30$ days overdue.

### 5.4 Agent Outstanding Dashboard (`DashBoradAgentPremiumOutStanding.aspx.cs`)
- **Receivables Tracking**:
  - Aggregates pending payments across all active agents.
  - Queries `sp_Agent_OutStanding_Report` grouped by `AgentId`.
  - Triggers automated reminder notices via SMS/Email if outstanding balance exceeds authorized credit limit.

---

## 6. Target Modern Architecture (FastAPI + Async SQLAlchemy)

In Phase 14, all dashboard logic is implemented as high-performance async aggregation endpoints:
- Clean SQL window functions and `GROUP BY` rollups replacing legacy in-memory DataTable iteration loops.
- Redis caching for dashboard summary endpoints with 5-minute TTL and automated invalidation upon new policy creation.
- Strict parameterization eliminating all dynamic SQL risks (`DEF-008`).
