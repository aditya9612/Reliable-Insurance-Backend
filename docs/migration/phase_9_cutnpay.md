# Phase 9 — Cut & Pay Lifecycle, Cheque-Bounce Hold & Release Specification

**Repository**: `Reliable-Insurance-Backend`  
**Phase**: `Phase 9 — Commission & Accounting Engine (Stage A5)`  
**Target Runtime Database**: `localhost:3306/reliable_insurance_dev`

---

## 1. Legacy Cut & Pay Business Semantics

In motor insurance agency operations (`Clerk/PolicyTransactionNew.aspx.cs`), **Cut & Pay** allows an authorized agent or partner to deduct their net commission upfront from the customer's policy premium remittance and remit only the net balance (`FinalPremium - CutNPayDeduction`) to the brokerage.

### 1.1 Physical Columns & Tables
1. **`tbl_transaction`**:
   - `CutNPay` (`Double(asdecimal=True)`, `NOT NULL`): Upfront commission deduction amount.
   - `PaidAmount`: Total instrument/wallet/online amount remitted (excluding `CutNPay`).
   - `OutstandingAmount`: $\max(0.00,\ \text{Amount} - \text{CutNPay} - \text{PaidAmount})$.
   - `CommissionPaid`: `1` when full Cut & Pay (`CutNPay == NetCommission`) is taken on a settled policy; `0` otherwise.
2. **`tbl_cutnpaycommpayable` (`app/models/commission.py` — PK `CutNPayCommPayId`, 11 Columns)**:
   - `CutNPayCommPayId`: Auto-increment PK.
   - `TransactionId`: Policy `TransanctionId`.
   - `PolicyNo`: `PolicyNo` or `InwardNo`.
   - `CustomerId`, `AgentId`, `SalesExId`: Principal references.
   - `CommPayable`: Upfront Cut & Pay deduction (`cutnpay_deduction`).
   - `Balance`: Remaining net commission still payable to the agent (`total_net_commission - cutnpay_deduction`).
   - `Flag`: Lifecycle state tag:
     - `"CUTNPAY"`: Active Cut & Pay record (default at booking; or released after partial Cut & Pay).
     - `"HOLD_CHEQUE_BOUNCE"`: Placed on hold when a customer's cheque/DD on the policy bounces.
     - `"SETTLED"`: Full Cut & Pay settled (`Balance == 0.00` and policy payment cleared) or remaining `Balance` paid out.
     - `"REVERSED"`: Reversed due to policy cancellation or commission clawback.
   - `Isdeleted`: `0` (active) or `1` (soft-deleted).
   - `CreatedDate`: Creation timestamp.
3. **`tbl_agentcommissionpayment`**:
   - `totalCommision`: Gross commission (`AgentCommAmt`).
   - `NetCommission`: Total net commission after TDS.
   - `AdvAmt`: Initialized to `cutnpay_deduction`.
   - `NetAmount`: Initialized to `round_2dp(NetCommission - cutnpay_deduction)` (equals `tbl_cutnpaycommpayable.Balance`).
   - `PaymentStatus`: `Decimal("1.00")` if `cutnpay_enabled` and `NetAmount == 0.00` and policy settled, else `Decimal("0.00")` (or `Decimal("2.00")` if partial Cut & Pay leaves `NetAmount > 0.00`).

---

## 2. Full vs Partial Cut & Pay Math

Given `FinalPremium = 17,700.00`, `AgentCommAmt = 1,000.00`, `TdsAmt (5%) = 50.00`, `NetCommission = 950.00`:

### Case A — Full Cut & Pay (`cutnpay_enabled = True`, `cutnpay_amount = None` or `950.00`)
- `cutnpay_deduction = 950.00`
- `required_payable_amount = 17,700.00 - 950.00 = 16,750.00`
- `tbl_cutnpaycommpayable`: `CommPayable = 950.00`, `Balance = 0.00`, `Flag = "CUTNPAY"`
- `tbl_agentcommissionpayment`: `NetCommission = 950.00`, `AdvAmt = 950.00`, `NetAmount = 0.00`, `PaymentStatus = 1.00`
- Since `NetAmount == 0.00`, no additional payout can be disbursed (`409 Conflict` if payout is attempted).

### Case B — Partial Cut & Pay (`cutnpay_enabled = True`, `cutnpay_amount = 500.00`)
- `cutnpay_deduction = 500.00`
- `required_payable_amount = 17,700.00 - 500.00 = 17,200.00`
- `tbl_cutnpaycommpayable`: `CommPayable = 500.00`, `Balance = 450.00`, `Flag = "CUTNPAY"`
- `tbl_agentcommissionpayment`: `NetCommission = 950.00`, `AdvAmt = 500.00`, `NetAmount = 450.00`, `PaymentStatus = 2.00` (or `1.00` once the remaining `450.00` is disbursed via commission payout!).
- When the remaining `450.00` is later disbursed via `POST /api/v1/commission-payouts`:
  - `tbl_agentcommissionpayment.AdvAmt` becomes `500.00 + 450.00 = 950.00`, `NetAmount = 0.00`, `PaymentStatus = 1.00`.
  - `tbl_cutnpaycommpayable.Balance` becomes `0.00`, `Flag = "SETTLED"`.

---

## 3. Cheque Bounce Hold $\rightarrow$ Replacement Settlement $\rightarrow$ Commission Release

1. **Cheque Dishonor (`POST /api/v1/payments/{payment_id}/bounce`)**:
   - Customer's cheque of `16,750.00` bounces with a `500.00` dishonor penalty.
   - `tbl_transaction`: `PaidAmount = 0.00`, `OutstandingAmount = 17,250.00`, `TStatus = "Pending"`, `pendingStatus = 1`, `ChequeBankStatus = 2`, `CommissionPaid = 0`.
   - `tbl_cutnpaycommpayable.Flag = "HOLD_CHEQUE_BOUNCE"`.
   - `tbl_agentcommissionpayment.PaymentStatus = Decimal("0.00")`, `Narration = "HOLD: Cheque #<docno> Bounced"`.
   - Any attempt to approve or pay out commission while `Flag == "HOLD_CHEQUE_BOUNCE"` or `OutstandingAmount > 0` is rejected with `409 Conflict`.
2. **Automatic & Explicit Release After Replacement Settlement / Clearance**:
   - When a replacement payment (`CASH`, `NEFT`, `UPI`, `ONLINE`, or cleared replacement `CHEQUE`) brings `tx.OutstandingAmount == 0.00` and `tx.Ischequeclearing == 0`:
     - `tbl_cutnpaycommpayable.Flag` is released from `"HOLD_CHEQUE_BOUNCE"` to `"SETTLED"` (if `Balance == 0.00`) or `"CUTNPAY"` (if `Balance > 0.00`).
     - `tbl_agentcommissionpayment`: if `NetAmount == 0.00` (100% Cut & Pay), `PaymentStatus` is restored to `Decimal("1.00")` and `tx.CommissionPaid = 1`; if `NetAmount > 0.00`, `Narration` is updated to `"RELEASED: Policy Payment Settled"` and the remaining `NetAmount` becomes eligible for payout.
   - Back-office/Accounting users can also invoke `POST /api/v1/commissions/transactions/{transaction_id}/release-hold` to verify settlement preconditions and release held commission records explicitly.
