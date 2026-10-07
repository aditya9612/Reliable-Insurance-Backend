# Phase 9 — Commission Approval, Individual/Bulk Payout & Partial Payout Specification

**Repository**: `Reliable-Insurance-Backend`  
**Phase**: `Phase 9 — Commission & Accounting Engine (Stage A6)`  
**Target Runtime Database**: `localhost:3306/reliable_insurance_dev`

---

## 1. Commission Payout Preconditions (Payment-Linked Eligibility)

In legacy `Clerk/AgentCommisionApproval.aspx.cs` and `Clerk/AgentCommissionUseWallet.aspx.cs`, a policy's Agent or Franchise commission becomes eligible for disbursement **only when the underlying policy transaction is active and its customer premium payment is fully settled**:

1. **Policy Active**: `tx.isdeleted == "0"` and `tx.TStatus != "Cancelled"`.
2. **Customer Payment Settled**:
   - `round_2dp(tx.OutstandingAmount) == Decimal("0.00")`
   - `tx.TStatus == "Booked"` and `tx.pendingStatus == 0`
   - No uncleared or bounced cheque (`tx.Ischequeclearing == 0`, `tx.ChequeBankStatus != 2`).
3. **No Active Commission Hold**:
   - Linked `tbl_cutnpaycommpayable` rows must not have `Flag == "HOLD_CHEQUE_BOUNCE"`.
   - Linked `tbl_agentcommissionpayment` row must not have `Narration` starting with `"HOLD:"`.
4. **Remaining Payable Balance $> 0.00$**:
   - For Agent Commission (`tbl_agentcommissionpayment`): `NetAmount > 0.00` (where `NetAmount = round_2dp(NetCommission - AdvAmt)`).
   - For Franchise Commission (`tbl_franchisecommission`): `round_2dp(FranchiseNetComm - FCommissionPaid) > 0.00`.

If any precondition fails, payout is rejected (`409 Conflict` when already paid or on hold; `422 Unprocessable Entity` when policy payment is incomplete or requested payout amount exceeds remaining payable balance).

---

## 2. Individual & Partial Payout Mechanics

### 2.1 Agent Commission Payout (`POST /api/v1/commission-payouts`)
Given `AgentCommissionPayment` row `acp` with `NetCommission`, `AdvAmt`, and `NetAmount = NetCommission - AdvAmt`:
- **Requested Payout Amount ($P$)**:
  - Defaults to full remaining `acp.NetAmount` if omitted.
  - Must satisfy $0.00 < P \le \text{acp.NetAmount}$ (`422` if $P \le 0$ or $P > \text{acp.NetAmount}$).
- **State Transition**:
  $$\text{AdvAmt}_{\text{new}} = \text{round\_2dp}(\text{AdvAmt}_{\text{old}} + P)$$
  $$\text{NetAmount}_{\text{new}} = \text{round\_2dp}(\text{NetCommission} - \text{AdvAmt}_{\text{new}})$$
  - If $\text{NetAmount}_{\text{new}} == 0.00$:
    - `acp.PaymentStatus = Decimal("1.00")` (`PAID`)
    - `tx.CommissionPaid = 1`, `tx.CommProcessSubmit = 1`
    - Any linked `tbl_cutnpaycommpayable` row sets `Balance = Decimal("0.00")`, `Flag = "SETTLED"`.
  - If $\text{NetAmount}_{\text{new}} > 0.00$ (**Partial Payout**):
    - `acp.PaymentStatus = Decimal("2.00")` (`PARTIAL`)
    - `tx.CommissionPaid = 0`, `tx.CommProcessSubmit = 1`
    - Any linked `tbl_cutnpaycommpayable` row sets `Balance = NetAmount_new`.

### 2.2 Franchise Commission Payout (`POST /api/v1/commission-payouts`)
Given `FranchiseCommission` row `fc` with `FranchiseNetComm` and `FCommissionPaid`:
- Remaining payable: $\text{Rem} = \text{round\_2dp}(\text{FranchiseNetComm} - \text{FCommissionPaid})$.
- For payout amount $0.00 < P \le \text{Rem}$:
  $$\text{FCommissionPaid}_{\text{new}} = \text{round\_2dp}(\text{FCommissionPaid}_{\text{old}} + P)$$
  $$\text{Rem}_{\text{new}} = \text{round\_2dp}(\text{FranchiseNetComm} - \text{FCommissionPaid}_{\text{new}})$$
  - If $\text{Rem}_{\text{new}} == 0.00$:
    - `tx.FranchiseCommPaid = 1`
    - `tx.FranchisePaymentDocNo = voucher_no`
  - If $\text{Rem}_{\text{new}} > 0.00$ (**Partial Payout**):
    - `tx.FranchiseCommPaid = 0`
    - `tx.FranchisePaymentDocNo = voucher_no`

### 2.3 Supported Payout Disbursement Modes (`payout_mode`)
- `NEFT`, `RTGS`, `ONLINE`, `UPI`, `CHEQUE`, `CASH`, `EWALLET`.
- When `payout_mode == "EWALLET"`:
  - In addition to the commission payout voucher legs in `tbl_account`, the service atomically credits the partner's E-Wallet sub-ledger (`LedgerTypeId = 5` for `AGENT`, `6` for `FRANCHISE`) with `AccTransId = 10`, `Extra1 = "WALLET_TOPUP"`, `PaymentType = "COMMISSION_PAYOUT"`, `amount = +P`, increasing `settled_balance` and `available_balance` by `+P`.

---

## 3. Double-Entry Payout Voucher Generation (`tbl_account`)

Every commission payout (individual or bulk) allocates a concurrency-safe sequential `Doc_No` (`int`) and voucher number `VCH-{BranchId:02d}-{FY}-{Doc_No:06d}` (`Extra2`) and posts a **balanced double-entry pair** in `tbl_account`:
1. **Debit Leg (`AccTransId = 6`, `Extra1 = "COMMISSION_PAYOUT_DEBIT"`)**:
   - `LedgerMId`: Policy / Commission Payable Ledger (`LedgerTypeId = 1` or `3`)
   - `amount = +P` (`Decimal > 0.00`) — clears `-P` of the `-NetCommission` liability accrued under `AccTransId = 3`.
2. **Credit Leg (`AccTransId = 6`, `Extra1 = "COMMISSION_PAYOUT_CREDIT"`)**:
   - `LedgerMId`: Settlement Bank / Cash / Partner Sub-Ledger (`LedgerTypeId = 2`, `5`, or `6`)
   - `amount = -P` (`Decimal < 0.00`) — records cash/bank outflow or sub-ledger settlement.

Sum of the payout voucher legs: $(+P) + (-P) == 0.00$.

---

## 4. Bulk Multi-Agent / Multi-Policy Payout (`POST /api/v1/commission-payouts/bulk`)

- Accepts a list of payout items (`items: List[CommissionPayoutItemRequest]`) within a single request.
- Acquires `_COMMISSION_WRITE_LOCK` and locks all target commission and policy rows with `SELECT ... FOR UPDATE`.
- Validates every item in the batch before committing. If **any** item is invalid (e.g., already paid, on hold, or policy unpaid), the entire batch rolls back atomically with zero partial changes.
