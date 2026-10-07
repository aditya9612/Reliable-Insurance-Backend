# Phase 10 — Endorsement Commission & TDS Adjustment Engine (`phase_10_commission_adjustment.md`)

## 1. Overview
This document specifies how Agent and Franchise commissions, TDS deductions, and paid-commission recovery/hold balances are recalculated and adjusted when a financial endorsement ($\Delta \text{Premium} \ne 0$) is applied to a policy in Phase 10.

This engine reuses `calculate_commission_preview_pure` from `app/services/commission_accounting.py` (`Phase 9`) so that endorsement commission math is 100% consistent with booking and payout commission math.

---

## 2. Commission & TDS Recalculation Formula

Using the policy's existing commission percentages stored on `tbl_transaction`:
- `od_comm_pct` = `tbl_transaction.AgentComm_OD`
- `tp_comm_pct` = `tbl_transaction.AgentComm`
- `net_comm_pct` = `tbl_transaction.AgentComm_Net`
- `extra_comm_pct` = `tbl_transaction.AgentComm_Extra`
- `tds_pct` = `tbl_transaction.tdsPercent`

### 2.1 Before Endorsement (`Old*` Commission Snapshot)
- $\text{OldAgentGross} = \text{tbl\_transaction.AgentCommAmt\_OD} + \text{AgentCommAmt} + \text{AgentCommAmt\_Net} + \text{AgentCommAmt\_Extra}$
- $\text{OldAgentTdsAmt} = \text{tbl\_transaction.TdsAmt\_OD} + \text{TdsAmt} + \text{TdsAmt\_Net} + \text{TdsAmt\_Extra}$
- $\text{OldAgentNetComm} = \text{tbl\_transaction.NetCommission\_OD} + \text{NetCommission} + \text{NetCommission\_Net} + \text{NetCommission\_Extra}$

### 2.2 After Endorsement (`New*` Commission Snapshot)
Calling `calculate_commission_preview_pure` with:
- `od_premium = NewODPremium`
- `tp_premium = NewTPPremium`
- `net_premium = NewNetPremium`
- `od_comm_pct`, `tp_comm_pct`, `net_comm_pct`, `extra_comm_pct`, `tds_pct`

Yields the new component breakdown (`NewAgentCommAmt_OD`, `NewTdsAmt_OD`, `NewNetCommission_OD`, etc.) and total net commission:
$$\text{NewAgentNetComm} = \text{preview.total\_net\_commission}$$
$$\text{NewAgentTdsAmt} = \text{preview.total\_tds\_amount}$$
$$\text{AgentCommDelta} = \text{NewAgentNetComm} - \text{OldAgentNetComm}$$

Similarly, if a franchise commission row exists in `tbl_franchisecommission` (or `FranchiseCode` is active):
- Franchise commission is recalculated against `NewODPremium`, `NewTPPremium`, `NewNetPremium` using the franchise's existing rates (`FranchiseComm_OD`, `FranchiseComm`, `FranchiseComm_Net`, `tdsPercent`).
- $\text{FranchiseCommDelta} = \text{NewFranchiseNetComm} - \text{OldFranchiseNetComm}$.

---

## 3. Unpaid vs. Already-Paid Commission Adjustment Rules

### Case A: Commission Is Unpaid (`tbl_transaction.CommissionPaid == "0"` and `tbl_agentcommissionpayment.PaidStatus == "UNPAID"`)
1. `tbl_transaction` commission columns (`AgentCommAmt_OD`, `TdsAmt_OD`, `NetCommission_OD`, etc.) are updated in-place to the new recalculated amounts.
2. Any existing `UNPAID` accrual row in `tbl_agentcommissionpayment` (and `tbl_franchisecommission`) is updated to the new gross/TDS/net commission amounts.
3. `CommissionRecoveryAmount = Decimal("0.00")`.
4. In `tbl_account`, an incremental `AccTransId = 3` (`Agent Commission Payable Accrual`) entry is posted for the delta:
   - If $\text{AgentCommDelta} > 0$: posts `CREDIT` (`-AgentCommDelta`) to Ledger `202` (`Agent Commission Payable`), increasing payable balance.
   - If $\text{AgentCommDelta} < 0$: posts `DEBIT` (`+abs(AgentCommDelta)`) to Ledger `202` (`Agent Commission Payable`), reducing payable balance.

### Case B: Commission Was Already Paid (`tbl_transaction.CommissionPaid == "1"` or `tbl_agentcommissionpayment.PaidStatus == "PAID"`)
1. **Paid Payout Rows Are Never Silently Mutated**: The historical `PAID` row in `tbl_agentcommissionpayment` remains immutable for audit integrity.
2. **Positive Delta ($\text{AgentCommDelta} > 0.00$ — Upward Endorsement)**:
   - `tbl_transaction` commission totals are updated to reflect the new policy commission.
   - A new supplemental `UNPAID` accrual row is inserted into `tbl_agentcommissionpayment` for the incremental delta ($\Delta \text{Gross}, \Delta \text{TDS}, \Delta \text{Net}$), and `AccTransId = 3` (`CREDIT -AgentCommDelta`) is posted to `tbl_account`.
3. **Negative Delta ($\text{AgentCommDelta} < 0.00$ — Downward Endorsement After Payout)**:
   - Because the agent has already been paid the higher commission, the excess commission paid is recorded as a recoverable debit balance:
     $$\text{CommissionRecoveryAmount} = \left|\text{AgentCommDelta}\right|$$
   - A recovery adjustment row is inserted into `tbl_agentcommissionpayment` with `PaidStatus = "RECOVERY_PENDING"` (and negative net commission delta), and `AccTransId = 3` (`DEBIT +CommissionRecoveryAmount`) is posted to Ledger `202` in `tbl_account` to record the agent recovery receivable against future payouts.
