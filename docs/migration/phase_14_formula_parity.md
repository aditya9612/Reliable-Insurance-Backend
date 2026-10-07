# Phase 14 — Mathematical Formula & Financial Metric Parity Catalog

> **Audit Status**: COMPLETE (FORENSIC EXTRACTION)  
> **Phase**: Phase 14 (Reporting, Dashboard, MIS, POSP Invoicing & Statutory Statements) — Stage A  
> **Repository**: `Reliable-Insurance-Backend`  
> **Legacy Source**: `c:\Users\Admin\Downloads\InsurancefinalNew_2026_09_23\InsurancefinalNew`  
> **Mode**: STRICTLY READ-ONLY FORENSIC AUDIT (No implementation)

---

## 1. Executive Summary

Financial reports, executive dashboards, and statutory invoices require absolute mathematical parity with the legacy system. Any discrepancy in rounding, taxation basis, or deduction order can result in severe accounting imbalances or statutory non-compliance.

This catalog formalizes the mathematical formulas extracted from legacy C# business logic classes (`BLL`), WebForms codebehind, and stored procedures.

---

## 2. Core Insurance Underwriting & Premium Formulas

### 2.1 Net Premium Formulation
Net premium forms the underwriting basis upon which brokerages and commissions are computed:

$$\text{Net Premium} = \text{Own Damage (OD) Premium} + \text{Third Party (TP) Premium}$$

- In motor insurance policies with standalone OD or TP:
  - If Policy Type is `STANDALONE_OD`: $\text{TP Premium} = 0.00 \implies \text{Net Premium} = \text{OD Premium}$
  - If Policy Type is `TP_ONLY`: $\text{OD Premium} = 0.00 \implies \text{Net Premium} = \text{TP Premium}$

### 2.2 Goods and Services Tax (GST) & Gross Premium
- The standard statutory GST rate for general insurance products in India is **$18\%$**:
  $$\text{GST Amount} = \text{Round}\left(\text{Net Premium} \times 0.18, 2\right)$$
  $$\text{Gross Premium} = \text{Net Premium} + \text{GST Amount}$$
- In reverse calculation scenarios (where Gross Premium is given):
  $$\text{Net Premium} = \text{Round}\left(\frac{\text{Gross Premium}}{1.18}, 2\right)$$
  $$\text{GST Amount} = \text{Gross Premium} - \text{Net Premium}$$

---

## 3. Commercial Commissions & Payout Formulations

### 3.1 Brokerage Earned from Insurer
$$\text{Gross Brokerage} = \text{Round}\left(\text{Commissionable Premium} \times \frac{\text{Insurer Brokerage Rate \%}}{100}, 2\right)$$
*Note: Commissionable Premium is typically Net Premium, or OD Premium depending on the insurer contract.*

### 3.2 Agent / POSP Commission
$$\text{Agent Commission} = \text{Round}\left(\text{Commissionable Premium} \times \frac{\text{Agent Rate \%}}{100}, 2\right) + \text{Fixed Reward (if any)}$$

### 3.3 Brokerage Net Operating Profit
Discovered in `Dashboard.aspx.cs:L245`:
$$\text{Company Profit} = \text{Gross Brokerage Received} - \text{Agent Commission Paid} - \text{Franchise Share (if any)}$$

---

## 4. POSP Payout Invoice & Statutory Tax Formulations

Extracted from `rpt_POSP_Invoice.aspx.cs:L165-L195`:

### 4.1 Base Taxable Payout
Let $A$ be the base earned commission approved for payout:
$$\text{Base Payout} = A$$

### 4.2 GST on Payout (Reverse Charge / IGST)
$$\text{GSTAmt} = \begin{cases} 
\text{Round}(A \times 0.18, 2) & \text{if } \text{Agent has valid GSTIN} \\ 
0.00 & \text{if } \text{Agent is Unregistered} 
\end{cases}$$

$$\text{Grand Total (Invoice Value)} = A + \text{GSTAmt}$$

### 4.3 Tax Deducted at Source (TDS Section 194H)
TDS is deducted strictly on the **Base Commission Amount ($A$)**, never on the GST component:
$$\text{TDS Amount} = \text{Round}(A \times 0.05, 2)$$

*Exception: If Agent PAN is missing or invalid (Section 206AA), the penal TDS rate applies:*
$$\text{TDS Amount}_{\text{No PAN}} = \text{Round}(A \times 0.20, 2)$$

### 4.4 Net Disbursement Payable
$$\text{Net Payable} = \text{Grand Total} - \text{TDS Amount}$$
$$\text{Net Payable} = A + \text{GSTAmt} - \text{TDS Amount}$$

---

## 5. Cut & Pay and Pass-On Reconciliation Formulas

Extracted from `DashBoradAgentPremiumCutNPay.aspx.cs` and `Rpt_CutNPayAndPassOn.aspx.cs`:

### 5.1 Cut & Pay Remittance
Under the Cut & Pay model, the agent collects payment from the customer and retains their commission:
$$\text{Remittance Due from Agent} = \text{Gross Premium Collected} - \text{Authorized Agent Payout}$$

### 5.2 Pass-On Reconciliation
When an agent passes on a discount or additional margin:
$$\text{Pass-On Net Balance} = \text{Actual Premium Remitted} - (\text{Gross Premium} - \text{Agreed Pass-On})$$

---

## 6. Performance & Target Metrics

Extracted from `adm_TargetReport.aspx.cs` and `adm_TelecallerTargetReport.aspx.cs`:

### 6.1 Target Achievement Percentage
$$\text{Achievement \%} = \begin{cases}
\text{Round}\left(\left(\frac{\text{Actual Premium Sourced}}{\text{Assigned Target Premium}}\right) \times 100, 2\right) & \text{if } \text{Target Premium} > 0 \\
100.00\% & \text{if } \text{Target} = 0 \text{ and } \text{Actual} > 0 \\
0.00\% & \text{otherwise}
\end{cases}$$

### 6.2 Telecaller Conversion Rate
$$\text{Conversion Rate \%} = \text{Round}\left(\left(\frac{\text{Policies Closed}}{\text{Total Leads Assigned}}\right) \times 100, 2\right)$$

---

## 7. Fiscal Calendar Formulation (`DEF-002` Fix)

The standardized Indian Financial Year (April 1 to March 31) calculation:

$$\text{FY Start Year} = \begin{cases}
\text{Year}(D) - 1 & \text{if } \text{Month}(D) \le 3 \\
\text{Year}(D) & \text{if } \text{Month}(D) > 3
\end{cases}$$

$$\text{FY String} = \text{FY Start Year} + \text{"-"} + (\text{FY Start Year} + 1)$$
