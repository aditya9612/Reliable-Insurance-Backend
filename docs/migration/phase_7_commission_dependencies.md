# Phase 7 — Commission Calculation, TDS & Double-Entry Accounting Dependencies

**Phase:** 7 — Policy Booking & Transaction Engine  
**Stage:** A6 — Agent/Franchise/Cut&Pay Commission & `tbl_account` Ledger Specification  
**Target Database:** `localhost:3306/reliable_insurance_dev`

---

## 1. Multi-Component Commission Calculation Model

In `Clerk/PolicyTransactionNew.aspx.cs` and `Clerk/AgentCommisionApproval.aspx.cs`, agent and franchise commissions are calculated across **three component buckets** (`OD`, `Net` / `TP`, and `Extra`) with component-level and aggregate **TDS (Tax Deducted at Source)** deductions.

All percentages and monetary values are computed in `Decimal` and quantized to 2 decimal places (`Decimal("0.01")`, `ROUND_HALF_UP`).

### 1.1 Commission Bases
Given a booked policy with:
- $\text{ODPermium}$: Total Net OD Premium (`tbl_transaction.ODPermium`)
- $\text{TPPermium}$: Total TP Liability Premium (`tbl_transaction.TPPermium`)
- $\text{PACovertoOwner}$: PA Owner-Driver Premium (`tbl_transaction.PACovertoOwner`)
- $\text{NetPermium} = \text{ODPermium} + \text{TPPermium}$

The commission bases are:
1. **OD Commission Base (`od_commission_base`)**:
   $$\text{ODBase} = \text{ODPermium}$$
2. **Net / TP Commission Base (`net_commission_base`)**:
   - By default in legacy underwriting:
     - When `AgentComm_OD > 0` and `AgentComm_Net > 0` are both specified (split OD + TP commission grid): $\text{NetBase} = \max(0.00, \text{TPPermium} - \text{PACovertoOwner})$ (or $\text{TPPermium}$ if `include_pa_in_tp_comm = True`, or $\text{NetPermium}$ when `commission_on_full_net = True`).
     - When `AgentComm_OD == 0` and `AgentComm_Net > 0`: $\text{NetBase} = \text{NetPermium}$ (commission computed on total Net Premium).
3. **Extra / Incentive Commission Base (`extra_commission_base`)**:
   - Defaults to $\text{ODPermium}$ if $\text{ODPermium} > 0$, else $\text{NetPermium}$.

### 1.2 Component Commission & TDS Formulas
Let $r_{\text{tds}} = \text{tdsPercent}$ (default `5.00%` in legacy, configurable `0.00`–`20.00%`):

1. **OD Commission Bucket**:
   $$\text{AgentCommAmt\_OD} = \text{round\_2dp}\left(\frac{\text{ODBase} \times \text{AgentComm\_OD}}{100}\right)$$
   $$\text{TdsAmt\_OD} = \text{round\_2dp}\left(\frac{\text{AgentCommAmt\_OD} \times r_{\text{tds}}}{100}\right)$$
   $$\text{NetCommission\_OD} = \text{AgentCommAmt\_OD} - \text{TdsAmt\_OD}$$

2. **Net / TP Commission Bucket**:
   $$\text{AgentCommAmt\_Net} = \text{round\_2dp}\left(\frac{\text{NetBase} \times \text{AgentComm\_Net}}{100}\right)$$
   $$\text{TdsAmt\_Net} = \text{round\_2dp}\left(\frac{\text{AgentCommAmt\_Net} \times r_{\text{tds}}}{100}\right)$$
   $$\text{NetCommission\_Net} = \text{AgentCommAmt\_Net} - \text{TdsAmt\_Net}$$

3. **Extra Commission Bucket**:
   $$\text{AgentCommAmt\_Extra} = \text{round\_2dp}\left(\frac{\text{ExtraBase} \times \text{AgentComm\_Extra}}{100}\right)$$
   $$\text{TdsAmt\_Extra} = \text{round\_2dp}\left(\frac{\text{AgentCommAmt\_Extra} \times r_{\text{tds}}}{100}\right)$$
   $$\text{NetCommission\_Extra} = \text{AgentCommAmt\_Extra} - \text{TdsAmt\_Extra}$$

4. **Legacy Single-Rate Fallback (`AgentComm > 0` when `OD/Net/Extra == 0`)**:
   - If the caller supplies a single headline `agent_comm_percent` (`AgentComm > 0`) without component splits:
     $$\text{AgentCommAmt} = \text{round\_2dp}\left(\frac{\text{NetPermium} \times \text{AgentComm}}{100}\right)$$
     $$\text{TdsAmt} = \text{round\_2dp}\left(\frac{\text{AgentCommAmt} \times r_{\text{tds}}}{100}\right)$$
     $$\text{NetCommission} = \text{AgentCommAmt} - \text{TdsAmt}$$
   - Otherwise, total commission is the exact sum of the three buckets:
     $$\text{AgentComm} = \text{AgentComm\_OD} + \text{AgentComm\_Net} + \text{AgentComm\_Extra}$$
     $$\text{AgentCommAmt} = \text{AgentCommAmt\_OD} + \text{AgentCommAmt\_Net} + \text{AgentCommAmt\_Extra}$$
     $$\text{TdsAmt} = \text{TdsAmt\_OD} + \text{TdsAmt\_Net} + \text{TdsAmt\_Extra}$$
     $$\text{NetCommission} = \text{AgentCommAmt} - \text{TdsAmt}$$

---

## 2. Downstream Commission Tables

### 2.1 `tbl_franchisecommission` (`app/models/commission.py` — PK `FranchiseCommId`)
When a policy is booked under a Franchise (`franchise_id > 0` or `FranchiseCode` is populated):
- Inserts a row into `tbl_franchisecommission` linking:
  - `TransanctionId` = `transaction.TransanctionId`
  - `FranchaiseId` = `franchise_id`
  - `PolicyNo` = `transaction.PolicyNo`
  - `ODPremium` = `transaction.ODPermium`, `NetPremium` = `transaction.NetPermium`, `TPPremium` = `transaction.TPPermium`
  - `ODPer` = `franchise_od_per` (defaults to `AgentComm_OD`), `ODAmt` = `franchise_od_amt`
  - `NetPer` = `franchise_net_per` (defaults to `AgentComm_Net`), `NetAmt` = `franchise_net_amt`
  - `ExtraPer` = `franchise_extra_per`, `ExtraAmt` = `franchise_extra_amt`
  - `TDSPer` = `tdsPercent`, `TDSAmt` = `franchise_tds_amt`
  - `TotalCommAmt` = `ODAmt + NetAmt + ExtraAmt`
  - `NetCommAmt` = `TotalCommAmt - TDSAmt`
  - `BranchId` = `transaction.BranchId`, `FinancialYear` = `transaction.FinancialYear`, `isdeleted = 0`.

### 2.2 `tbl_cutnpaycommpayable` (`app/models/commission.py` — PK `Id`)
When `CutNPay == 1` (`cutnpay_enabled = True`):
- Inserts a row into `tbl_cutnpaycommpayable`:
  - `TransanctionId` = `transaction.TransanctionId`
  - `AgentId` = `transaction.AgentId`
  - `PolicyPremium` = `transaction.Amount`
  - `PayableCommAmt` = `transaction.NetCommission`
  - `PaidAmt` = `CutNPayDeduction` (amount deducted upfront by the agent)
  - `RemainingAmt` = `transaction.NetCommission - CutNPayDeduction`
  - `TransactionType` = `"CUTNPAY"`
  - `TransactionDate` = `datetime.utcnow()`, `CreatedBy` = `current_user.UserId`.

### 2.3 `tbl_agentcommissionpayment` (`app/models/commission.py` — PK `AgentCommPayId`)
When an agent (`AgentId > 0`) earns commission (`NetCommission > 0`):
- Inserts a commission accrual / tracking row into `tbl_agentcommissionpayment`:
  - `AgentId` = `transaction.AgentId`
  - `TransDate` = `transaction.TransDate`
  - `CommissionAmt` = `transaction.AgentCommAmt`
  - `TdsAmt` = `transaction.TdsAmt`
  - `Amount` = `transaction.NetCommission`
  - `PaidAmount` = `CutNPayDeduction` if `CutNPay == 1` else `Decimal("0.00")`
  - `RemainingAmount` = `transaction.NetCommission - PaidAmount`
  - `PaymentType` = `"CUTNPAY"` if `CutNPay == 1` else `"ACCRUED"`
  - `Remark` = `f"Policy Booking {transaction.InwardNo}"`
  - `BranchId` = `transaction.BranchId`, `FinancialYear` = `transaction.FinancialYear`, `deleted = 0`.

---

## 3. Double-Entry Accounting Journal Posting (`tbl_account` & `tbl_ledgermaster`)

In `Clerk/PolicyTransactionNew.aspx.cs` and `Clerk/AgentCommisionApproval.aspx.cs` (`sp_InsertAccountDetails`), policy booking posts up to **three deterministic accounting rows** in `tbl_account` (`PK: AccountId`), linked to `tbl_ledgermaster` (`PK: LedgerMId`) and `tbl_transaction.TransanctionId`:

| Entry Type | `AccTransId` | `TransactionType` | `Amount` | `Credit` | `Debit` | `FinalBalance` | `Description` | Legacy Polarity Rule |
|---|---:|---|---|---|---|---|---|---|
| **1. Policy Premium Receivable / Booking** | `1` | `"POLICY_BOOKING"` | `+Amount` | `+Amount` | `0.00` | `+Amount` | `"Policy Premium Booking - {InwardNo}"` | Positive Gross Premium (`NetPermium + GST_Amount`) |
| **2. Policy Payment Receipt** | `2` | `"POLICY_PAYMENT"` | `+PaidAmount` | `0.00` | `+PaidAmount` | `Amount - PaidAmount` | `"Policy Payment Receipt - {InwardNo}"` | Posted when `PaidAmount > 0.00` |
| **3. Unclear Policy Commission Entry** | `3` | `"UNCLEAR_COMMISSION"` | **`-NetCommission`** | **`-NetCommission`** | `0.00` | **`-NetCommission`** | `"Unclear Policy Commission Entry - {InwardNo}"` | **CRITICAL LEGACY RULE:** `AccTransId = 3` is ALWAYS posted with negative polarity (`-netcomm`) until cleared/settled! |

### Ledger Master Resolution (`tbl_ledgermaster`)
- Each `tbl_account` row references a `LedgerId` (`tbl_ledgermaster.LedgerMId`) and `SubLedgerId` (`AgentId` or `CustomerId`).
- If a default Policy Ledger (`LedgerName = "POLICY UNDERWRITING LEDGER"`) does not yet exist in `tbl_ledgermaster` for the branch, `PolicyBookingRepository` resolves or auto-provisions the ledger master row within the transaction so foreign/logical references remain intact.
