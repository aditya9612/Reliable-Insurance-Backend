# Phase 10 — Golden Parity Scenarios (`phase_10_golden_parity.md`)

## 1. Overview
This document defines the 21 deterministic synthetic Golden Parity scenarios (`CL10-01` through `CL10-10` for Claims, and `EN10-01` through `EN10-11` for Endorsements) verified in `tests/integration/test_phase10_golden_parity.py`.

All scenarios execute exclusively against synthetic test data in `reliable_insurance_dev` (`0.00` tolerance, `ROUND_HALF_UP` to `0.01`).

---

## 2. Claims Golden Parity Matrix (`CL10-01` .. `CL10-10`)

| Scenario ID | Description | Synthetic Inputs | Expected Legacy-Parity Outcome |
|---|---|---|---|
| `CL10-01` | Valid OD Claim Intimation on Active Comprehensive Policy | Policy `OD=10000.00`, `TP=5000.00`, `SumInsured=500000.00`, `LossDate` inside policy period, `EstimatedAmount=45000.00` | `ClaimStatus = "INTIMATED"`, deterministic `ClaimNo = "CLM-1-2026-..."`, `ApprovedAmount = 0.00`, `SettledAmount = 0.00`. |
| `CL10-02` | Surveyor Assignment & Survey Update | `SurveyorName="Rajesh Sharma"`, `SurveyorLicenseNo="SLA-77889"`, `SurveyDate >= IntimationDate` | `ClaimStatus = "UNDER_SURVEY"`, surveyor metadata persisted on `tbl_claims`. |
| `CL10-03` | Claim Assessment with Depreciation, Deductible, Excess & Salvage | `AssessedLossAmount=45000.00`, `DepreciationAmount=5000.00`, `DeductibleAmount=1000.00`, `ExcessAmount=500.00`, `SalvageAmount=1500.00` | `ClaimStatus = "ASSESSED"`, exact `ApprovedAmount = 45000 - 5000 - 1000 - 500 - 1500 = 37000.00`. |
| `CL10-04` | Claim Approval & Customer Reimbursement Settlement | Approve `37000.00`, Settle `SettledAmount=37000.00`, `PayeeType="CUSTOMER"`, `PaymentMode="NEFT"` | `ClaimStatus = "SETTLED"`, `CustomerPayableAmount = 37000.00`, `InsurerPayableAmount = 37000.00`, `tbl_account` has balanced `AccTransId = 15` (`DR 103 +37000.00`, `CR 203 -37000.00`), Trial Balance `variance == 0.00`. |
| `CL10-05` | Cashless Garage Claim Settlement & Closure | `PayeeType="GARAGE"`, `SettledAmount=25000.00`, followed by `close` | `GaragePayableAmount = 25000.00`, `CustomerPayableAmount = 0.00`, `ClaimStatus = "CLOSED"`. |
| `CL10-06` | Claim Rejection & Authorized Reopen | Reject claim with `RejectionReason="Policy exclusion"`, then `reopen` by `Admin`/`HO` | Transitions to `REJECTED`, then `REOPENED` with audit remarks preserved. |
| `CL10-07` | Loss Date Outside Policy Period Rejected | `LossDate < PolicyStartDate` or `LossDate > PolicyEndDate` | Rejected with `422 Unprocessable Entity` (`Loss date outside policy coverage period`). |
| `CL10-08` | Claim on Cancelled Policy Rejected | Policy has `PolicycancelId = 1` or `TStatus = "CANCELLED"` | Rejected with `409 Conflict` (`Cannot intimate claim on cancelled policy`). |
| `CL10-09` | OD Claim on TP-Only Policy Rejected | Policy has `ODPermium = 0.00`, `TPPermium = 5000.00`, `ClaimType = "OD"` | Rejected with `422 Unprocessable Entity` (`OD claim not covered under TP-only policy`). |
| `CL10-10` | Claim Settlement Reversal | Reverse settled claim (`SettledAmount=37000.00`) | Posts contra `AccTransId = 16` (`DR 203 +37000.00`, `CR 103 -37000.00`), resets `SettledAmount = 0.00`, returns `ClaimStatus` to `"APPROVED"`, Trial Balance `variance == 0.00`. |

---

## 3. Endorsements Golden Parity Matrix (`EN10-01` .. `EN10-11`)

| Scenario ID | Description | Synthetic Inputs | Expected Legacy-Parity Outcome |
|---|---|---|---|
| `EN10-01` | Non-Financial Customer Name Correction (`NAME_CORRECTION`) | Change `CustFName` from `"Ramesh"` to `"Rameshwar"` | `EndorsementCategory = "NON_FINANCIAL"`, `PremiumDelta = 0.00`, `AgentCommDelta = 0.00`, `tbl_customer.CustFName == "Rameshwar"`, `UpdateEntryStatus = 1`, `IsRecalculate = 0`. |
| `EN10-02` | Non-Financial Address & Contact Correction (`ADDRESS_CORRECTION` / `CONTACT_CORRECTION`) | Change `Address` and `MoblieNo1` | `PremiumDelta = 0.00`, `tbl_customer` updated, `FieldChangesJson` records exact `before` and `after`. |
| `EN10-03` | Non-Financial Vehicle Registration & Engine/Chassis Correction (`VEHICLE_REGISTRATION_CORRECTION` / `ENGINE_CHASSIS_CORRECTION`) | Change `RegistrationNo` and `EngineNo`/`ChaiseNo` | `PremiumDelta = 0.00`, `tbl_vehicledetails` updated, `CorrectionText` populated on `tbl_transaction`. |
| `EN10-04` | Non-Financial Hypothecation & Nominee Change (`HYPOTHECATION_CHANGE` / `NOMINEE_CHANGE`) | Change `Financer="HDFC Bank"` and Nominee details | `PremiumDelta = 0.00`, `tbl_vehicledetails.Financer == "HDFC Bank"`, `UpdateEntryStatus = 1`. |
| `EN10-05` | Upward IDV Change (`IDV_CHANGE` — Additional Premium) | Increase `SumInsured` from `500000.00` to `600000.00` (`OldOD=10000.00` -> `NewOD=12000.00`, `OldTP=5000.00`, `GST=18%`) | `NewNetPremium = 17000.00`, `NewGSTAmount = 3060.00`, `NewFinalPremium = 20060.00`, `PremiumDelta = +2360.00`, `OutstandingAmount` increased by `2360.00`, `AgentCommDelta > 0`, `IsRecalculate = 1`. |
| `EN10-06` | Downward IDV Change (`IDV_CHANGE` — Refund Premium) | Decrease `SumInsured` from `500000.00` to `400000.00` on fully paid policy (`OldFinal=17700.00`, `PaidAmount=17700.00` -> `NewFinal=15340.00`) | `PremiumDelta = -2360.00`, `RefundAmount = 2360.00`, `RefundStatus = "PENDING_APPROVAL"`, `AgentCommDelta < 0`. |
| `EN10-07` | NCB Correction (`NCB_CORRECTION` — Recovery of Wrongly Claimed NCB) | Reduce `NCB` from `20%` (`OldOD=8000.00`, `GrossOD=10000.00`) to `0%` (`NewOD=10000.00`) | `DeltaNet = +2000.00`, `DeltaGST = +360.00`, `PremiumDelta = +2360.00`, `NewNCBPercent = 0.00`, `OutstandingAmount` increased by `2360.00`. |
| `EN10-08` | Add-On / Coverage Addition & Removal (`COVERAGE_ADDON_CHANGE`) | Add Zero-Dep `AddOn = 1500.00` | `DeltaNet = +1500.00`, `DeltaGST = +270.00`, `PremiumDelta = +1770.00`, `tbl_transaction.AddOn` updated. |
| `EN10-09` | Downward Endorsement on Policy with Already-Paid Agent Commission | Policy has `CommissionPaid = "1"`, `AgentComm_OD = 15%`, `tdsPercent = 5%`; downward `OD` delta `-2000.00` | Gross comm delta `-300.00`, TDS delta `-15.00`, `AgentCommDelta = -285.00`, `CommissionRecoveryAmount = 285.00`, recovery row created in `tbl_agentcommissionpayment` (`PaidStatus = "RECOVERY_PENDING"`), historical `PAID` row untouched. |
| `EN10-10` | Refund Approval, Disbursement & Reversal Lifecycle | Approve & disburse `RefundAmount = 2360.00`, then reverse refund | `RefundStatus`: `PENDING_APPROVAL -> APPROVED -> REFUNDED -> REVERSED`, `AccTransId = 17` and `18` balanced in `tbl_account`, Trial Balance `variance == 0.00`. |
| `EN10-11` | Endorsement Reversal (`reverse_endorsement`) | Reverse applied upward endorsement `EN10-05` | Restores `SumInsured = 500000.00`, `ODPermium = 10000.00`, `Amount = 17700.00`, restores commission and posts contra accounting rows, `EndorsementStatus = "REVERSED"`, Trial Balance `variance == 0.00`. |
