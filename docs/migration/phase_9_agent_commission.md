# Phase 9 — Agent Commission & Multi-Bucket Calculation Specification

**Repository**: `Reliable-Insurance-Backend`  
**Phase**: `Phase 9 — Commission & Accounting Engine (Stage A2)`  
**Target Runtime Database**: `localhost:3306/reliable_insurance_dev`

---

## 1. Physical Storage of Agent Commissions

Agent commissions are stored across two physical tables in `reliable_insurance_dev`:
1. **`tbl_transaction` (`app/models/transaction.py`)**:
   - Headline fields: `AgentId`, `SalesEx_id`, `GridAgentId`, `AgentComm` (%), `AgentCommAmt` (Gross), `tdsPercent` (%, default `5.00`), `TdsAmt` (TDS), `NetCommission` (`AgentCommAmt - TdsAmt`), `CommissionPaid` (`0` or `1`), `CommProcessSubmit` (`0` or `1`), `CutNPay` (`Decimal`).
   - **OD Bucket**: `AgentComm_OD` (%), `AgentCommAmt_OD` (Gross), `TdsAmt_OD`, `NetCommission_OD`.
   - **Net / TP Bucket**: `AgentComm_Net` (%), `AgentCommAmt_Net` (Gross), `TdsAmt_Net`, `NetCommission_Net`.
   - **Extra Bucket**: `AgentComm_Extra` (%), `AgentCommAmt_Extra` (Gross), `TdsAmt_Extra`, `NetCommission_Extra`.
   - **Adjustments**: `SelfDiscount` (`Decimal`), `IntensiveAmount` (`Decimal`, legacy spelling for Incentive Amount), `IncentiveStatus` (`int`), `IncentiveDoc_No` (`int`).
2. **`tbl_agentcommissionpayment` (`app/models/commission.py` — PK `AgentCommId`, 20 Columns)**:
   - `AgentCommId`: Auto-increment PK.
   - `FromDate`, `ToDate`, `TransDate`: Commission period & transaction timestamps.
   - `TransanctionId`: Policy transaction ID (legacy spelling with extra `n`).
   - `BranchName`: `"BRANCH-{BranchId}"`.
   - `AgentName`: `"AGENT-{AgentId}"`.
   - `PremiumAmount`: Policy `NetPermium` (`ODPermium + TPPermium`).
   - `totalCommision`: Total Gross Agent Commission (`AgentCommAmt`, legacy spelling with single `s`).
   - `NetCommission`: Total Net Agent Commission after TDS (`AgentCommAmt - TdsAmt`).
   - `AdvAmt`: Cumulative amount deducted upfront via Cut & Pay or already disbursed in prior partial payouts.
   - `NetAmount`: Remaining unpaid Net Commission payable to the agent (`NetCommission - AdvAmt`).
   - `PaymentStatus`:
     - `Decimal("0.00")` = Accrued / Pending / Unpaid (or On Hold when `Narration` starts with `"HOLD:"`)
     - `Decimal("1.00")` = Fully Paid / Settled (`NetAmount == 0.00`)
     - `Decimal("2.00")` = Partially Paid (`0.00 < AdvAmt < NetCommission` and `NetAmount > 0.00`)
     - `Decimal("3.00")` = Approved for Payout (`NetAmount > 0.00`, awaiting disbursement)
   - `Narration`: Audit narration, voucher reference, or hold reason.
   - `Extra1`: `str(AgentId)`.
   - `Extra2`: `str(TdsAmt)` or payout voucher reference.
   - `isdeleted`: `"0"` (active) or `"1"` (soft-deleted/reversed).
   - `NetCommission_OD`, `NetCommission_Net`, `NetCommission_Extra`: Bucket-level net commissions after TDS.

---

## 2. Deterministic Multi-Bucket Commission Formulas

All calculations use `Decimal` and round each intermediate monetary value using `ROUND_HALF_UP` to `0.01`:

### 2.1 Premium Bases (GST Never Included in Commission Base)
Commission is **never** calculated on GST (`GST_Amount`) or `FinalPremium` (`ProPosalAmt`). It is strictly calculated on pre-tax underwriting components:
1. **OD Commission Base (`od_commission_base`)**:
   $$\text{ODBase} = \text{round\_2dp}(\text{ODPermium})$$
2. **Net / TP Commission Base (`net_commission_base`)**:
   - **Case A — Full Net Premium Basis** (`commission_on_full_net == True` OR `(AgentComm_OD == 0 and AgentComm_Net > 0)`):
     $$\text{NetBase} = \text{round\_2dp}(\text{NetPermium}) = \text{round\_2dp}(\text{ODPermium} + \text{TPPermium})$$
   - **Case B — TP Inclusive of CPA Owner-Driver** (`include_pa_in_tp_comm == True` and `AgentComm_OD > 0`):
     $$\text{NetBase} = \text{round\_2dp}(\text{TPPermium})$$
   - **Case C — Standard Split OD + Statutory TP Basis (Default when `AgentComm_OD > 0`)**:
     CPA Owner-Driver (`PACovertoOwner`) is excluded from the TP commission base:
     $$\text{NetBase} = \max\left(0.00,\ \text{round\_2dp}(\text{TPPermium} - \text{PACovertoOwner})\right)$$
3. **Extra Commission Base (`extra_commission_base`)**:
   $$\text{ExtraBase} = \begin{cases} \text{ODBase} & \text{if } \text{ODBase} > 0.00 \\ \text{round\_2dp}(\text{NetPermium}) & \text{otherwise (TP-Only Policy)} \end{cases}$$

### 2.2 Bucket Gross, TDS & Net Commission
Given rates $r_{\text{od}} = \text{AgentComm\_OD}$, $r_{\text{net}} = \text{AgentComm\_Net}$, $r_{\text{ext}} = \text{AgentComm\_Extra}$, headline fallback $r_{\text{head}} = \text{AgentComm}$, and TDS rate $r_{\text{tds}} = \text{tdsPercent}$ (default `5.00`):

- **Single Headline Rate Fallback** ($r_{\text{od}} = 0 \land r_{\text{net}} = 0 \land r_{\text{ext}} = 0 \land r_{\text{head}} > 0$):
  $$\text{NetBase} = \text{NetPermium}, \quad r_{\text{net}} = r_{\text{head}}$$
  $$\text{AgentCommAmt\_Net} = \text{round\_2dp}\left(\frac{\text{NetBase} \times r_{\text{head}}}{100}\right)$$
  $$\text{TdsAmt\_Net} = \text{round\_2dp}\left(\frac{\text{AgentCommAmt\_Net} \times r_{\text{tds}}}{100}\right)$$
  $$\text{NetCommission\_Net} = \text{AgentCommAmt\_Net} - \text{TdsAmt\_Net}$$
  *(with OD and Extra buckets equal to `0.00`).*

- **Multi-Bucket Calculation**:
  - **OD Bucket**:
    $$\text{AgentCommAmt\_OD} = \text{round\_2dp}\left(\frac{\text{ODBase} \times r_{\text{od}}}{100}\right)$$
    $$\text{TdsAmt\_OD} = \text{round\_2dp}\left(\frac{\text{AgentCommAmt\_OD} \times r_{\text{tds}}}{100}\right)$$
    $$\text{NetCommission\_OD} = \text{AgentCommAmt\_OD} - \text{TdsAmt\_OD}$$
  - **Net / TP Bucket**:
    $$\text{AgentCommAmt\_Net} = \text{round\_2dp}\left(\frac{\text{NetBase} \times r_{\text{net}}}{100}\right)$$
    $$\text{TdsAmt\_Net} = \text{round\_2dp}\left(\frac{\text{AgentCommAmt\_Net} \times r_{\text{tds}}}{100}\right)$$
    $$\text{NetCommission\_Net} = \text{AgentCommAmt\_Net} - \text{TdsAmt\_Net}$$
  - **Extra Bucket**:
    $$\text{AgentCommAmt\_Extra} = \text{round\_2dp}\left(\frac{\text{ExtraBase} \times r_{\text{ext}}}{100}\right)$$
    $$\text{TdsAmt\_Extra} = \text{round\_2dp}\left(\frac{\text{AgentCommAmt\_Extra} \times r_{\text{tds}}}{100}\right)$$
    $$\text{NetCommission\_Extra} = \text{AgentCommAmt\_Extra} - \text{TdsAmt\_Extra}$$

- **Aggregate Totals**:
  $$\text{AgentCommAmt} = \text{AgentCommAmt\_OD} + \text{AgentCommAmt\_Net} + \text{AgentCommAmt\_Extra}$$
  $$\text{TdsAmt} = \text{TdsAmt\_OD} + \text{TdsAmt\_Net} + \text{TdsAmt\_Extra}$$
  $$\text{NetCommission} = \text{AgentCommAmt} - \text{TdsAmt} = \text{NetCommission\_OD} + \text{NetCommission\_Net} + \text{NetCommission\_Extra}$$

---

## 3. Commission Timing & Lifecycle States

| Stage | Triggering Event | `tbl_transaction.CommissionPaid` | `tbl_agentcommissionpayment.PaymentStatus` | `tbl_agentcommissionpayment.NetAmount` | Payable Eligibility |
|---|---|---:|---|---|---|
| **1. Accrued (Pending Policy Settlement)** | Policy booked with `OutstandingAmount > 0` or uncleared `CHEQUE`/`DD` (`Ischequeclearing == 1`) | `0` | `0.00` | `NetCommission - AdvAmt` | **Not Payable** until policy is fully paid and cheque cleared |
| **2. Payable (Policy Settled)** | Policy `OutstandingAmount == 0.00` and `Ischequeclearing == 0` (`TStatus == 'Booked'`) | `0` (or `1` if 100% Cut & Pay) | `0.00` (if `NetAmount > 0`) or `1.00` (if `NetAmount == 0`) | `NetCommission - AdvAmt` | **Payable** (`NetAmount > 0`) |
| **3. Approved** | `POST /api/v1/commissions/agent/{id}/approve` (`CommProcessSubmit = 1`) | `0` | `3.00` (`APPROVED`) | `NetCommission - AdvAmt` | **Approved for Payout** |
| **4. Partially Paid** | Partial payout disbursed (`0 < payout < NetAmount`) | `0` | `2.00` (`PARTIAL`) | `NetCommission - new_AdvAmt` | **Remaining `NetAmount` Payable** |
| **5. Fully Paid / Settled** | Full payout disbursed (`new_AdvAmt == NetCommission`) or 100% Cut & Pay on settled policy | `1` | `1.00` (`PAID`) | `0.00` | **Terminal Settled** (unless reversed) |
| **6. On Hold (Cheque Bounce)** | Customer cheque dishonored (`POST /api/v1/payments/{id}/bounce`) | `0` | `0.00` (`Narration = 'HOLD: ...'`) | `NetCommission - AdvAmt` | **Blocked (`409 Conflict`)** until replacement payment clears |
| **7. Reversed / Cancelled** | Policy cancelled or commission payout reversed | `0` | `0.00` (`isdeleted = '1'` on cancel) | Restored or `0.00` (cancelled) | **Reversed** |
