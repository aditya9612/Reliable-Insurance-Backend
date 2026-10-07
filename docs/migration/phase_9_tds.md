# Phase 9 — Tax Deducted at Source (TDS) Specification

**Repository**: `Reliable-Insurance-Backend`  
**Phase**: `Phase 9 — Commission & Accounting Engine (Stage A4)`  
**Target Runtime Database**: `localhost:3306/reliable_insurance_dev`

---

## 1. Legacy TDS Rules & Physical Storage

In the legacy insurance underwriting and commission settlement engine (`Clerk/PolicyTransactionNew.aspx.cs`, `Clerk/AgentCommisionApproval.aspx.cs`), **Tax Deducted at Source (TDS)** is deducted at accrual/calculation time on every commission bucket (`OD`, `Net`/`TP`, and `Extra`) before arriving at `NetCommission` (`tbl_transaction`, `tbl_agentcommissionpayment`) and `FranchiseNetComm` (`tbl_franchisecommission`).

### 1.1 Physical Columns Storing TDS
1. **`tbl_transaction`**:
   - `tdsPercent` (`Double(asdecimal=True)`, `NOT NULL`, default `5.00`): Applied TDS percentage (`0.00` to `20.00`).
   - `TdsAmt` (`Double(asdecimal=True)`): Total Agent TDS (`TdsAmt_OD + TdsAmt_Net + TdsAmt_Extra`).
   - `TdsAmt_OD` (`Double(asdecimal=True)`): OD bucket TDS.
   - `TdsAmt_Net` (`Double(asdecimal=True)`): Net/TP bucket TDS.
   - `TdsAmt_Extra` (`Double(asdecimal=True)`): Extra bucket TDS.
   - Hierarchy TDS fields: `T_Tds`, `F_Tds`, `M_Tds`.
2. **`tbl_agentcommissionpayment`**:
   - `totalCommision`: Gross commission before TDS (`AgentCommAmt`).
   - `Extra2`: Stores `str(total_tds_amount)` at policy booking.
   - `NetCommission`: Net commission after TDS (`totalCommision - TdsAmt`).
3. **`tbl_franchisecommission`**:
   - `FranchiseTdsAmt`: Total Franchise TDS (`FranchiseTdsAmt_OD + FranchiseTdsAmt_Net + FranchiseTdsAmt_Extra`).
   - `FranchiseTdsAmt_OD`, `FranchiseTdsAmt_Net`, `FranchiseTdsAmt_Extra`: Bucket-level Franchise TDS.
   - `FranchiseNetComm`: Franchise Net Commission after TDS (`FranchiseCommAmt - FranchiseTdsAmt`).

---

## 2. Deterministic TDS Calculation & Rounding Rules

### 2.1 Default & Configurable TDS Rate
- **Default Rate**: `Decimal("5.00")` (`5%`), matching Indian statutory insurance brokerage/commission TDS norms in the legacy system.
- **Custom / Exempt Rate**: `tds_percent` may be set between `Decimal("0.00")` (TDS-exempt certificate) and `Decimal("20.00")` (no-PAN higher TDS rate); any negative rate or rate `> 20.00%` is rejected with `HTTP 422 Unprocessable Entity`.

### 2.2 Per-Bucket Rounding (`ROUND_HALF_UP` to `0.01`)
TDS is computed and rounded to `0.01` (`ROUND_HALF_UP`) **per bucket first**, and total TDS is the sum of the rounded bucket TDS amounts:
$$\text{TdsAmt\_OD} = \text{round\_2dp}\left(\frac{\text{AgentCommAmt\_OD} \times r_{\text{tds}}}{100}\right)$$
$$\text{TdsAmt\_Net} = \text{round\_2dp}\left(\frac{\text{AgentCommAmt\_Net} \times r_{\text{tds}}}{100}\right)$$
$$\text{TdsAmt\_Extra} = \text{round\_2dp}\left(\frac{\text{AgentCommAmt\_Extra} \times r_{\text{tds}}}{100}\right)$$
$$\text{TdsAmt} = \text{TdsAmt\_OD} + \text{TdsAmt\_Net} + \text{TdsAmt\_Extra}$$
$$\text{NetCommission} = \text{AgentCommAmt} - \text{TdsAmt}$$

### 2.3 Exact Rounding Example (`C9-08`)
Suppose `ODPermium = 10,333.00`, `AgentComm_OD = 12.50%`, `tds_percent = 5.00%`:
1. $\text{AgentCommAmt\_OD} = \text{round\_2dp}(10333.00 \times 0.125) = \text{round\_2dp}(1291.625) = 1291.63$
2. $\text{TdsAmt\_OD} = \text{round\_2dp}(1291.63 \times 0.05) = \text{round\_2dp}(64.5815) = 64.58$
3. $\text{NetCommission\_OD} = 1291.63 - 64.58 = 1227.05$

### 2.4 No Double-TDS at Payout Time
- Because `NetCommission` (in `tbl_agentcommissionpayment`) and `FranchiseNetComm` (in `tbl_franchisecommission`) are **already net of TDS**, commission payout disburses `NetAmount` (`NetCommission - AdvAmt`) or `FranchiseNetComm - FCommissionPaid` **without deducting a second 5% TDS** unless an explicit payout-time TDS rate adjustment is requested.
- When a commission is reversed (due to policy cancellation or clawback), the net commission and TDS liability are reversed proportionally.
