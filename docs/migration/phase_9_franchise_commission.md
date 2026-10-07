# Phase 9 — Franchise Commission, Hierarchy & Profit Margin Specification

**Repository**: `Reliable-Insurance-Backend`  
**Phase**: `Phase 9 — Commission & Accounting Engine (Stage A3)`  
**Target Runtime Database**: `localhost:3306/reliable_insurance_dev`

---

## 1. Physical Storage (`tbl_franchisecommission` — 29 Verified Columns)

In `app/models/commission.py` (`FranchiseCommission`), franchise commission records are persisted in `tbl_franchisecommission`:
- **Primary Key**: `FranchiseCommId` (`Integer`, autoincrement)
- **Linkage**:
  - `TransanctionId` (`Integer`, legacy typo with extra `n`)
  - `FranchiseId` (`Integer`)
  - `AgentId` (`Integer`, sub-agent under the franchise, or `0` if direct franchise policy)
  - `BrokerId` (`Integer`, `NOT NULL`, default `0`)
- **Headline Commission & TDS**:
  - `FranchiseDate` (`DateTime`)
  - `tat` (`Decimal`, default `0.00`)
  - `Franchisecomm` (`Decimal`): Headline franchise commission percentage
  - `FranchiseCommAmt` (`Decimal`): Total franchise gross commission before TDS
  - `FranchiseTdsAmt` (`Decimal`): Total franchise TDS deducted
  - `FranchiseNetComm` (`Decimal`): Total franchise net commission after TDS (`FranchiseCommAmt - FranchiseTdsAmt`)
  - `FCommissionPaid` (`Decimal`): Cumulative franchise commission paid/disbursed so far (`0.00` at booking; updated on payout)
- **Multi-Bucket Breakdown**:
  - **OD Bucket**: `Franchisecomm_OD`, `FranchiseCommAmt_OD`, `FranchiseTdsAmt_OD`, `FranchiseNetComm_OD`
  - **Net / TP Bucket**: `Franchisecomm_Net`, `FranchiseCommAmt_Net`, `FranchiseTdsAmt_Net`, `FranchiseNetComm_Net`
  - **Extra Bucket**: `Franchisecomm_Extra`, `FranchiseCommAmt_Extra`, `FranchiseTdsAmt_Extra`, `FranchiseNetComm_Extra`
- **Franchise Profit Margin & Adjustments**:
  - `ProfitofNetCommision` (`Decimal`, legacy spelling with single `s`): Net differential profit retained by the Franchise over the Agent's net commission
  - `GridValidDate` (`DateTime`)
  - `SelfDiscount` (`Decimal`, `NOT NULL`)
  - `IntensiveAmount` (`Decimal`, `NOT NULL`)
  - `isdeleted` (`Integer`, `0` = active, `1` = soft-deleted)

---

## 2. Deterministic Franchise Commission & Profit Margin Formulas

When `eff_franchise_id > 0`:
1. **Franchise Bucket Rates**:
   - $f_{\text{od}} = \text{franchise\_comm\_od\_percent}$ if provided, else $r_{\text{od}}$ (`agent_comm_od_percent`).
   - $f_{\text{net}} = \text{franchise\_comm\_net\_percent}$ if provided, else $r_{\text{net}}$ (`agent_comm_net_percent`).
   - $f_{\text{ext}} = \text{franchise\_comm\_extra\_percent}$ if provided, else $r_{\text{ext}}$ (`agent_comm_extra_percent`).
   - Headline rate: $f_{\text{head}} = f_{\text{od}} + f_{\text{net}} + f_{\text{ext}}$.
2. **Bucket Gross, TDS (`tds_percent`, default `5.00%`), and Net Calculations**:
   - **OD Bucket**:
     $$\text{FranchiseCommAmt\_OD} = \text{round\_2dp}\left(\frac{\text{ODBase} \times f_{\text{od}}}{100}\right)$$
     $$\text{FranchiseTdsAmt\_OD} = \text{round\_2dp}\left(\frac{\text{FranchiseCommAmt\_OD} \times r_{\text{tds}}}{100}\right)$$
     $$\text{FranchiseNetComm\_OD} = \text{FranchiseCommAmt\_OD} - \text{FranchiseTdsAmt\_OD}$$
   - **Net / TP Bucket**:
     $$\text{FranchiseCommAmt\_Net} = \text{round\_2dp}\left(\frac{\text{NetBase} \times f_{\text{net}}}{100}\right)$$
     $$\text{FranchiseTdsAmt\_Net} = \text{round\_2dp}\left(\frac{\text{FranchiseCommAmt\_Net} \times r_{\text{tds}}}{100}\right)$$
     $$\text{FranchiseNetComm\_Net} = \text{FranchiseCommAmt\_Net} - \text{FranchiseTdsAmt\_Net}$$
   - **Extra Bucket**:
     $$\text{FranchiseCommAmt\_Extra} = \text{round\_2dp}\left(\frac{\text{ExtraBase} \times f_{\text{ext}}}{100}\right)$$
     $$\text{FranchiseTdsAmt\_Extra} = \text{round\_2dp}\left(\frac{\text{FranchiseCommAmt\_Extra} \times r_{\text{tds}}}{100}\right)$$
     $$\text{FranchiseNetComm\_Extra} = \text{FranchiseCommAmt\_Extra} - \text{FranchiseTdsAmt\_Extra}$$
3. **Aggregate Franchise Totals**:
   $$\text{FranchiseCommAmt} = \text{FranchiseCommAmt\_OD} + \text{FranchiseCommAmt\_Net} + \text{FranchiseCommAmt\_Extra}$$
   $$\text{FranchiseTdsAmt} = \text{FranchiseTdsAmt\_OD} + \text{FranchiseTdsAmt\_Net} + \text{FranchiseTdsAmt\_Extra}$$
   $$\text{FranchiseNetComm} = \text{FranchiseCommAmt} - \text{FranchiseTdsAmt}$$
4. **Franchise Differential Profit Margin (`ProfitofNetCommision`)**:
   - Verified in legacy `Clerk/PolicyTransactionNew.aspx.cs` and `PolicyBookingService.book_policy`:
     $$\text{ProfitofNetCommision} = \text{round\_2dp}(\text{FranchiseNetComm} - \text{AgentTotalNetCommission})$$
   - When a policy is booked directly by a Franchise without a sub-agent (`AgentId == 0` or `AgentTotalNetCommission == 0.00`), $\text{ProfitofNetCommision} = \text{FranchiseNetComm}$.
   - When a sub-agent (`AgentId > 0`) earns `AgentTotalNetCommission` (e.g., `15%` OD = `1,425.00` net after 5% TDS) under a Franchise earning `FranchiseNetComm` (e.g., `18%` OD = `1,710.00` net after 5% TDS), the Franchise's override profit margin is:
     $$\text{ProfitofNetCommision} = 1710.00 - 1425.00 = 285.00$$

---

## 3. Ownership Hierarchy & Principal Precedence Rules

1. **Ownership Chain**:
   $$\text{Customer} \rightarrow \text{Policy (`tbl_transaction`)} \rightarrow \text{Agent (`AgentId`)} \rightarrow \text{Franchise (`FranchiseId` / `FranchiseCode`)} \rightarrow \text{Sales Executive (`SalesEx_id`)} \rightarrow \text{Location Head (`LocationHeadId`)}$$
2. **Coexistence of `AgentId`, `FranchiseId`, and `SalesEx_id`**:
   - All three identifiers can coexist on a single policy transaction (`tbl_transaction` and `tbl_franchisecommission`).
   - When an authenticated `AGENT` user submits a request, `eff_agent_id` is strictly bound to `ctx.agent_id or ctx.user_id` from the server-resolved `PrincipalContext` (never trusting client-supplied `agent_id`).
   - When an authenticated `FRANCHISE`, `FRANCHISE TYPE 2`, `FRANCHISE TYPE 3`, or `FRANCHISE OPERATOR` user submits a request, `eff_franchise_id` is strictly bound to `ctx.franchise_id or ctx.user_id` from `PrincipalContext`.
3. **Franchise Commission Payable & Payout Tracking**:
   - Remaining Franchise Commission Payable:
     $$\text{FranchiseRemainingPayable} = \text{round\_2dp}(\text{FranchiseNetComm} - \text{FCommissionPaid})$$
   - On Franchise payout of amount $P$ ($0 < P \le \text{FranchiseRemainingPayable}$):
     - `FCommissionPaid = round_2dp(FCommissionPaid + P)`
     - When `FCommissionPaid == FranchiseNetComm`: `tbl_transaction.FranchiseCommPaid = 1` and `tbl_transaction.FranchisePaymentDocNo = voucher_no`.
