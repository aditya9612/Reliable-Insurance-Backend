# Phase 9 — Golden Parity Verification Matrix (`C9-01` .. `C9-30`)

## 1. Overview
This document records the 30 Golden Parity test scenarios (`C9-01` through `C9-30`) executed in [`tests/integration/test_phase9_golden_parity.py`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/tests/integration/test_phase9_golden_parity.py) against the local development database (`reliable_insurance_dev`). Every scenario compares the verified legacy ASP.NET / MySQL Commission & Accounting behavior against the new FastAPI implementation with **`0.00` discrepancy**.

---

## 2. 30-Case Golden Parity Table (`C9-01` .. `C9-30`)

| Case ID | Scenario | Input / Action Summary | Legacy Expected Outcome | FastAPI Actual Outcome | Discrepancy | Status |
|---|---|---|---|---|---|---|
| `C9-01` | Agent OD commission only | `OD=10000.00`, `TP=5000.00`, `AgentOD%=15.00%`, `TDS=5.00%` | `Gross=1500.00`, `TDS=75.00`, `Net=1425.00`, `Payable=1425.00` | `Gross=1500.00`, `TDS=75.00`, `Net=1425.00`, `Payable=1425.00` | `0.00` | PASS |
| `C9-02` | Agent Net commission only | `OD=10000.00`, `TP=5000.00`, `AgentNet%=10.00%`, `TDS=5.00%` | `Gross=1500.00`, `TDS=75.00`, `Net=1425.00`, `Payable=1425.00` | `Gross=1500.00`, `TDS=75.00`, `Net=1425.00`, `Payable=1425.00` | `0.00` | PASS |
| `C9-03` | Agent Extra commission only | `OD=10000.00`, `TP=5000.00`, `AgentExtra%=3.00%`, `TDS=5.00%` | `Gross=300.00`, `TDS=15.00`, `Net=285.00`, `Payable=285.00` | `Gross=300.00`, `TDS=15.00`, `Net=285.00`, `Payable=285.00` | `0.00` | PASS |
| `C9-04` | Agent OD + Net + Extra combined | `OD=10000`, `TP=5000`, `OD%=12%`, `Net%=2%`, `Extra%=1%`, `TDS=5%` | `Gross=1600.00`, `TDS=80.00`, `Net=1520.00`, `Payable=1520.00` | `Gross=1600.00`, `TDS=80.00`, `Net=1520.00`, `Payable=1520.00` | `0.00` | PASS |
| `C9-05` | Agent commission with `5%` TDS | `OD=20000.00`, `AgentOD%=10.00%`, `TDS=5.00%` | `Gross=2000.00`, `TDS=100.00`, `Net=1900.00` | `Gross=2000.00`, `TDS=100.00`, `Net=1900.00` | `0.00` | PASS |
| `C9-06` | Agent commission with `0%` TDS | `OD=20000.00`, `AgentOD%=10.00%`, `TDS=0.00%` | `Gross=2000.00`, `TDS=0.00`, `Net=2000.00` | `Gross=2000.00`, `TDS=0.00`, `Net=2000.00` | `0.00` | PASS |
| `C9-07` | Franchise OD commission only | `OD=10000.00`, `TP=5000.00`, `FrnOD%=18.00%`, `FrnTDS=5.00%` | `FrnGross=1800.00`, `FrnTDS=90.00`, `FrnNet=1710.00` | `FrnGross=1800.00`, `FrnTDS=90.00`, `FrnNet=1710.00` | `0.00` | PASS |
| `C9-08` | Franchise OD + Net + Extra | `OD=10000`, `TP=5000`, `FrnOD%=15%`, `Net%=3%`, `Extra%=2%`, `TDS=5%` | `FrnGross=2150.00`, `FrnTDS=107.50`, `FrnNet=2042.50` | `FrnGross=2150.00`, `FrnTDS=107.50`, `FrnNet=2042.50` | `0.00` | PASS |
| `C9-09` | Franchise TDS calculation (`10%`) | `OD=20000.00`, `FrnOD%=15.00%`, `FrnTDS=10.00%` | `FrnGross=3000.00`, `FrnTDS=300.00`, `FrnNet=2700.00` | `FrnGross=3000.00`, `FrnTDS=300.00`, `FrnNet=2700.00` | `0.00` | PASS |
| `C9-10` | Franchise `ProfitofNetCommision` spread | `AgentNet=950.00`, `FranchiseNet=1995.00` | `ProfitofNetCommision=1045.00` | `ProfitofNetCommision=1045.00` | `0.00` | PASS |
| `C9-11` | Cut & Pay full deduction | `Final=11800.00`, `AgentNet=950.00`, `CutNPay=950.00` | `CustPayable=10850.00`, `AdvAmt=950.00`, `Rem=0.00`, `Status=1.00` | `CustPayable=10850.00`, `AdvAmt=950.00`, `Rem=0.00`, `Status=1.00` | `0.00` | PASS |
| `C9-12` | Cut & Pay partial deduction | `Final=11800.00`, `AgentNet=950.00`, `CutNPay=400.00` | `CustPayable=11400.00`, `AdvAmt=400.00`, `Rem=550.00`, `Status=2.00` | `CustPayable=11400.00`, `AdvAmt=400.00`, `Rem=550.00`, `Status=2.00` | `0.00` | PASS |
| `C9-13` | Cut & Pay exceeding commission rejected | `AgentNet=950.00`, `CutNPay=951.00` | Rejected (`422 Unprocessable Entity`) | Rejected (`422 Unprocessable Entity`) | `0.00` | PASS |
| `C9-14` | Commission payable creation on policy booking | Book Policy `GOLDEN_C9_14_POL` (`Agent#601`, `Franchise#701`) | `AgentRem=950.00`, `FrnRem=1425.00`, `Spread=475.00` | `AgentRem=950.00`, `FrnRem=1425.00`, `Spread=475.00` | `0.00` | PASS |
| `C9-15` | Commission approval | `POST /api/v1/commissions/{tx_id}/approve` | `PaymentStatus=3.00` (`APPROVED`) | `PaymentStatus=3.00` (`APPROVED`) | `0.00` | PASS |
| `C9-16` | Full Agent commission payout | Disburse remaining `550.00` to `Agent#601` | `AdvAmt=950.00`, `NetAmount=0.00`, `PaymentStatus=1.00` | `AdvAmt=950.00`, `NetAmount=0.00`, `PaymentStatus=1.00` | `0.00` | PASS |
| `C9-17` | Partial Agent commission payout | Disburse `400.00` of `950.00` to `Agent#601` | `AdvAmt=400.00`, `NetAmount=550.00`, `PaymentStatus=2.00` | `AdvAmt=400.00`, `NetAmount=550.00`, `PaymentStatus=2.00` | `0.00` | PASS |
| `C9-18` | Full Franchise commission payout | Disburse remaining `825.00` to `Franchise#701` | `FCommissionPaid=1425.00`, `Rem=0.00`, `CommissionPaid=1` | `FCommissionPaid=1425.00`, `Rem=0.00`, `CommissionPaid=1` | `0.00` | PASS |
| `C9-19` | Partial Franchise commission payout | Disburse `600.00` of `1425.00` to `Franchise#701` | `FCommissionPaid=600.00`, `Rem=825.00`, `CommissionPaid=0` | `FCommissionPaid=600.00`, `Rem=825.00`, `CommissionPaid=0` | `0.00` | PASS |
| `C9-20` | Over-payout rejected | Request `600.00` when `550.00` remains | Rejected (`409 Conflict`) | Rejected (`409 Conflict`) | `0.00` | PASS |
| `C9-21` | Duplicate payout rejected | Replay `idempotency_key="IDEMP-C9-17"` | Rejected (`409 Conflict`) | Rejected (`409 Conflict`) | `0.00` | PASS |
| `C9-22` | Commission reversal on policy cancellation | `POST /api/v1/policies/{tx_id}/cancel` | Contra `+950.00` `AccTransId=3` posted; net commission ledger sum `0.00` | Contra `+950.00` `AccTransId=3` posted; net commission ledger sum `0.00` | `0.00` | PASS |
| `C9-23` | Commission hold on cheque bounce | `POST /api/v1/payments/{id}/bounce` | `Flag="HOLD_CHEQUE_BOUNCE"`, `is_payout_eligible=False` | `Flag="HOLD_CHEQUE_BOUNCE"`, `is_payout_eligible=False` | `0.00` | PASS |
| `C9-24` | Commission payout reversal | `POST /api/v1/commission-payouts/{id}/reverse` | `status="REVERSED"`, `NetAmount` restored, `CommissionPaid=0` | `status="REVERSED"`, `NetAmount` restored, `CommissionPaid=0` | `0.00` | PASS |
| `C9-25` | Accounting entries on policy booking | Check `tbl_account` for booked policy | `AccTransId=1 (+17700.00)`, `AccTransId=2 (+17700.00)`, `AccTransId=3 (-950.00)` | `AccTransId=1 (+17700.00)`, `AccTransId=2 (+17700.00)`, `AccTransId=3 (-950.00)` | `0.00` | PASS |
| `C9-26` | Accounting entries on commission payout | Check `tbl_account` for payout voucher | `AccTransId=6`: DR `+550.00`, CR `-550.00`, `is_balanced=True` | `AccTransId=6`: DR `+550.00`, CR `-550.00`, `is_balanced=True` | `0.00` | PASS |
| `C9-27` | Accounting entries on commission reversal | Check `tbl_account` for reversal voucher | `AccTransId=7`: CR `-550.00`, DR `+550.00`, `is_balanced=True` | `AccTransId=7`: CR `-550.00`, DR `+550.00`, `is_balanced=True` | `0.00` | PASS |
| `C9-28` | Balanced voucher creation | `POST /api/v1/accounting/vouchers` (`DR 1250 == CR 1250`) | `201 Created`, `AccTransId=8`, `is_balanced=True` | `201 Created`, `AccTransId=8`, `is_balanced=True` | `0.00` | PASS |
| `C9-29` | Unbalanced voucher rejected | `POST /api/v1/accounting/vouchers` (`DR 1250 != CR 1200`) | Rejected (`422 Unprocessable Entity`) | Rejected (`422 Unprocessable Entity`) | `0.00` | PASS |
| `C9-30` | Trial Balance balanced after full lifecycle | `GET /api/v1/accounting/trial-balance` | `total_gross_debit == total_gross_credit`, `variance == 0.00`, `is_balanced=True` | `total_gross_debit == total_gross_credit`, `variance == 0.00`, `is_balanced=True` | `0.00` | PASS |
