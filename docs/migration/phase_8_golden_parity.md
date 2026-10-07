# Phase 8 Golden Parity Matrix (`P8-01` through `P8-25`)

## 1. Executive Summary
- **Repository**: `Reliable-Insurance-Backend`
- **Target Database**: `localhost:3306/reliable_insurance_dev` (100% synthetic test fixtures; zero production data or PII).
- **Automated Test Suite**: [`tests/integration/test_phase8_golden_parity.py`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/tests/integration/test_phase8_golden_parity.py)
- **Total Golden Parity Cases**: **25 (`P8-01` .. `P8-25`)**
- **Financial & State Delta**: **`0.00` across all 25 cases**

---

## 2. 25-Case Golden Parity Verification Table

| Case ID | Scenario Description | Instrument / Operation | Expected Paid (`Decimal`) | Expected Outstanding (`Decimal`) | Expected Policy / Instrument State | Accounting / Ledger Verification (`tbl_account`) | Delta |
| :--- | :--- | :--- | :---: | :---: | :--- | :--- | :---: |
| **`P8-01`** | Full Cash Payment on Private Car Comprehensive | `CASH` (`14509.00`) | `14509.00` | `0.00` | `TStatus='Booked'`, `status='RECEIVED'` | `AccTransId = 1 (+14509.00)`, `2 (+14509.00)`, `3 (-1211.25)` | `0.00` |
| **`P8-02`** | Partial Cash Payment at Policy Booking | `CASH` (`5000.00` / `11800.00`) | `5000.00` | `6800.00` | `TStatus='Pending'`, `pendingStatus=1` | `AccTransId = 1 (+11800.00)`, `2 (+5000.00)`, `3 (0.00)` | `0.00` |
| **`P8-03`** | Subsequent UPI Payment Completing Balance | `UPI` (`6800.00`) | `11800.00` | `0.00` | `TStatus='Booked'`, `pendingStatus=0` | Appends `AccTransId = 2 (+6800.00, PaymentType='UPI')` | `0.00` |
| **`P8-04`** | Cheque Payment Received at Booking | `CHEQUE` (`11800.00`, `CHQ-P8-04`) | `11800.00` | `0.00` | `status='PENDING_CLEARANCE'`, `Ischequeclearing=1`, `IsChequeCleared=0` | `AccTransId = 2 (+11800.00, PaymentType='CHEQUE')` | `0.00` |
| **`P8-05`** | Cheque Deposited in Bank | `POST /payments/{id}/deposit` | `11800.00` | `0.00` | `status='DEPOSITED'`, `CashierApproval=1`, `Ischequeclearing=1` | Bank deposit slip reference recorded in `Extra2` | `0.00` |
| **`P8-06`** | Cheque Cleared in Bank | `POST /payments/{id}/clear` | `11800.00` | `0.00` | `status='CLEARED'`, `AccountantApproval=1`, `Ischequeclearing=0`, `IsChequeCleared=1`, `ChequeBankStatus=1` | Finalizes `TStatus='Booked'`, `pendingStatus=0` | `0.00` |
| **`P8-07`** | Cheque Bounced without Dishonor Penalty | `POST /payments/{id}/bounce` (`penalty=0.00`) | `0.00` | `11800.00` | `status='BOUNCED'`, `isdeleted='1'`, `TStatus='Pending'`, `ChequeBankStatus=2` | Posts contra `AccTransId = 2 (-11800.00, Extra1='CHEQUE_BOUNCE_REVERSAL')` | `0.00` |
| **`P8-08`** | Cheque Bounced with Dishonor Penalty (`500.00`) | `POST /payments/{id}/bounce` (`penalty=500.00`) | `1800.00` | `10500.00` | `status='BOUNCED'`, `TStatus='Pending'`, `CommissionPaid=0` | Posts `AccTransId = 2 (-10000.00)` + `AccTransId = 4 (+500.00, Extra1='CHEQUE_BOUNCE_PENALTY')` | `0.00` |
| **`P8-09`** | Replacement NEFT Settlement after Cheque Bounce + Penalty | `NEFT` (`10500.00`) | `12300.00` | `0.00` | `TStatus='Booked'`, `pendingStatus=0` | Appends `AccTransId = 2 (+10500.00, PaymentType='NEFT')` | `0.00` |
| **`P8-10`** | Demand Draft (`DD`) Receipt & Bank Clearance | `DD` (`11800.00`, `DD-P8-10`) | `11800.00` | `0.00` | `PENDING_CLEARANCE` -> `CLEARED`, `IsChequeCleared=1` | `AccTransId = 2 (+11800.00, PaymentType='DD')` | `0.00` |
| **`P8-11`** | Credit Card + Debit Card Split Payment | `CREDIT_CARD` (`6000.00`) + `DEBIT_CARD` (`5800.00`) | `11800.00` | `0.00` | `TStatus='Booked'`, 2 active instrument rows | `AccTransId = 1 (+11800.00)`, `2 (+11800.00)`, `3 (0.00)` | `0.00` |
| **`P8-12`** | RTGS Corporate Public GCV Split-GST Payment | `RTGS` (`52190.00`) | `52190.00` | `0.00` | `TStatus='Booked'`, `status='RECEIVED'` | `AccTransId = 1 (+52190.00)`, `2 (+52190.00)` | `0.00` |
| **`P8-13`** | Cut & Pay Full NetCommission Deduction | `CUTNPAY` (`950.00`) + `ONLINE` (`16750.00`) | `16750.00` | `0.00` | `RequiredPayable=16750.00`, `CommissionPaid=1` | `tbl_cutnpaycommpayable` (`CommPayable=950.00`, `Balance=0.00`) | `0.00` |
| **`P8-14`** | Cut & Pay Partial Custom Deduction (`500.00` of `950.00`) | `CUTNPAY` (`500.00`) + `CASH` (`17200.00`) | `17200.00` | `0.00` | `RequiredPayable=17200.00`, `CommissionPaid=1` | `tbl_cutnpaycommpayable` (`CommPayable=500.00`, `Balance=450.00`) | `0.00` |
| **`P8-15`** | Partner Agent E-Wallet Top-Up | `POST /wallets/topup` (`+25000.00`) | `25000.00` | `0.00` | `settled=25000.00`, `locked=0.00`, `available=25000.00` | `AccTransId = 10 (+25000.00, Extra1='WALLET_TOPUP')` | `0.00` |
| **`P8-16`** | Partner Agent E-Wallet Lock Reservation | `POST /wallets/lock` (`-11800.00`) | `25000.00` | `11800.00` | `settled=25000.00`, `locked=11800.00`, `available=13200.00` | `AccTransId = 11 (-11800.00, Extra1='WALLET_LOCK')` | `0.00` |
| **`P8-17`** | Partner Agent E-Wallet Lock Release | `POST /wallets/release` (`+11800.00`) | `25000.00` | `0.00` | `settled=25000.00`, `locked=0.00`, `available=25000.00` | `AccTransId = 12 (+11800.00, Extra1='WALLET_RELEASE')`, lock marked `WALLET_LOCK_RELEASED` | `0.00` |
| **`P8-18`** | Partner Agent E-Wallet Lock Consumed on Booking | `POST /policies/book` (`wallet_lock_id`) | `11800.00` | `0.00` | `settled=13200.00`, `locked=0.00`, `available=13200.00` | `AccTransId = 13 (-11800.00, Extra1='WALLET_DEBIT')`, lock marked `WALLET_LOCK_CONSUMED` | `0.00` |
| **`P8-19`** | Partner Franchise E-Wallet Top-Up + Split Payment | `EWALLET` (`4000.00`) + `CASH` (`7800.00`) | `11800.00` | `0.00` | Franchise wallet `available=6000.00` (`10000 - 4000`) | `AccTransId = 13 (-4000.00)` on Franchise wallet sub-ledger (`LedgerTypeId=6`) | `0.00` |
| **`P8-20`** | Direct to Insurer Online Remittance + Agent Cash | `online_payment_to_company=5000.00` + `CASH=6800.00` | `11800.00` | `0.00` | `TStatus='Booked'`, `OnlinePaymentToCompany=5000` | `AccTransId = 1 (+11800.00)`, `2 (+11800.00)` | `0.00` |
| **`P8-21`** | Active Cash Payment Reversal | `POST /payments/{id}/reverse` (`6800.00`) | `5000.00` | `6800.00` | `status='REVERSED'`, `isdeleted='1'`, `TStatus='Pending'` | Posts contra `AccTransId = 2 (-6800.00, Extra1='PAYMENT_REVERSAL')` | `0.00` |
| **`P8-22`** | E-Wallet Payment Reversal with Automatic Wallet Refund | `POST /payments/{id}/reverse` (`4000.00`) | `7800.00` | `4000.00` | Franchise wallet restored to `available=10000.00` | Posts `AccTransId = 2 (-4000.00)` + `AccTransId = 14 (+4000.00, Extra1='WALLET_REFUND')` | `0.00` |
| **`P8-23`** | Insurer Payment & Brokerage Reconciliation — Full Match | `POST /reconciliation/policies/{id}/match` (`1275.00`) | `14509.00` | `0.00` | `IsRconDataMatch=1`, `match_status='MATCHED'`, `variance=0.00` | Posts `AccTransId = 5 (+1275.00, Extra1='INSURER_RECONCILIATION')` | `0.00` |
| **`P8-24`** | Insurer Payment & Brokerage Reconciliation — Variance Match | `POST /reconciliation/policies/{id}/match` (`750.00` vs `1000.00`) | `16750.00` | `0.00` | `IsRconDataMatch=2`, `match_status='PARTIAL_VARIANCE'`, `variance=-250.00` | Posts `AccTransId = 5 (+750.00, Extra1='INSURER_RECONCILIATION')` | `0.00` |
| **`P8-25`** | Multi-Instrument Policy Cancellation & Full Reversal | `POST /policies/{id}/cancel` | `11800.00` | `0.00` | `TStatus='Cancelled'`, `isdeleted='1'`, `payments_reversed=2`, `accounting_entries_reversed=3` | Marks all linked payment, commission, and accounting rows deleted | `0.00` |
