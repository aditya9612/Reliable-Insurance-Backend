# Phase 10 — Claim Assessment, Approval & Settlement Calculation (`phase_10_claim_settlement.md`)

## 1. Overview
This document defines the exact financial formulas, rounding rules, sum-insured limits, payee splits, and accounting entries for Motor Claim Assessment and Settlement in Phase 10.

---

## 2. Claim Assessment Formula

All monetary inputs and outputs use `Decimal` quantized to `0.01` with `ROUND_HALF_UP` (`float` is strictly prohibited).

Given:
- $L_{\text{est}}$ = `EstimatedAmount` (initial loss estimate at intimation, $> 0$)
- $L_{\text{assessed}}$ = `AssessedLossAmount` (surveyor's gross assessed repair/replacement loss, $> 0$)
- $D_{\text{dep}}$ = `DepreciationAmount` (part depreciation deduction, $\ge 0$)
- $D_{\text{ded}}$ = `DeductibleAmount` (compulsory + voluntary deductible, $\ge 0$)
- $D_{\text{exc}}$ = `ExcessAmount` (imposed policy excess, $\ge 0$)
- $S_{\text{salv}}$ = `SalvageAmount` (salvage/wreck value deduction, $\ge 0$)

### 2.1 Net Approved Claim Amount
$$\text{NetAssessed} = L_{\text{assessed}} - D_{\text{dep}} - D_{\text{ded}} - D_{\text{exc}} - S_{\text{salv}}$$

$$\text{ApprovedAmount} = \max\left(\text{Decimal}(\text{"0.00"}), \text{round\_half\_up}(\text{NetAssessed}, 0.01)\right)$$

- If $\text{NetAssessed} \le 0.00$, the claim cannot be approved for positive payout ($\text{ApprovedAmount} = 0.00$, assessment/approval for payout is rejected with `422 Unprocessable Entity` unless rejected).

### 2.2 Sum Insured (IDV) Cap Rule
- For `ClaimType` $\in \{\text{"OD"}, \text{"THEFT"}, \text{"TOTAL\_LOSS"}\}$:
  - Let $\text{IDV} = \text{tbl\_transaction.SumInsured}$.
  - If $\text{IDV} > 0$ and $\text{ApprovedAmount} > \text{IDV}$, the assessment/approval is rejected with `422 Unprocessable Entity` (`ApprovedAmount cannot exceed policy SumInsured (IDV)`), unless capped at $\text{IDV}$ prior to approval.
- For `ClaimType == "TP"` (Third Party Legal Liability):
  - Third Party death/bodily injury awards are statutory/tribunal-determined and are not capped by the vehicle's Own Damage `SumInsured` (IDV).

---

## 3. Claim Settlement & Payee Split Rules

When a claim in `APPROVED` status is settled (`POST /api/v1/claims/{claim_id}/settle`):
1. **Settlement Amount Guard**:
   $$0.00 < \text{SettledAmount} \le \text{ApprovedAmount}$$
   Any attempt to settle for $\text{SettledAmount} > \text{ApprovedAmount}$ or $\text{SettledAmount} \le 0$ fails with `422 Unprocessable Entity`.
2. **Payee Allocation (`PayeeType`)**:
   - `CUSTOMER` (Reimbursement Claim):
     - `InsurerPayableAmount` = `SettledAmount`
     - `CustomerPayableAmount` = `SettledAmount`
     - `GaragePayableAmount` = `0.00`
   - `GARAGE` (Cashless Network Garage Claim):
     - `InsurerPayableAmount` = `SettledAmount`
     - `CustomerPayableAmount` = `0.00`
     - `GaragePayableAmount` = `SettledAmount`
   - `INSURER` (Direct Insurer Settlement Recorded in Broker System):
     - `InsurerPayableAmount` = `SettledAmount`
     - `CustomerPayableAmount` = `SettledAmount`
     - `GaragePayableAmount` = `0.00`

---

## 4. Claim Settlement & Reversal Accounting (`tbl_account`)

To preserve **100% Trial Balance integrity (`total_debit == total_credit`, `variance == 0.00`)** across `CommissionAccountingService.get_trial_balance`:

### 4.1 Claim Settlement Posting (`AccTransId = 15`)
When `settle_claim` executes, a balanced double-entry pair is posted to `tbl_account` under `Doc_No = "CLM-SET-{ClaimId}"`:
- **DEBIT (`+SettledAmount`)**: Ledger `103` (`Insurer Claim Recoverable / Claim Settlement Receivable`)
  - `AccTransId = 15`, `TransactionType = "DEBIT"`, `LedgerMId = 103`, `amount = +SettledAmount`
- **CREDIT (`-SettledAmount`)**: Ledger `203` (`Claim Settlement Payable / Bank Clearing`)
  - `AccTransId = 15`, `TransactionType = "CREDIT"`, `LedgerMId = 203`, `amount = -SettledAmount`

Sum of signed `amount` across the settlement voucher:
$$+\text{SettledAmount} + (-\text{SettledAmount}) = 0.00$$

### 4.2 Claim Settlement Reversal (`AccTransId = 16`)
When `reverse_claim_settlement` executes on a `SETTLED` claim, an offsetting contra double-entry pair is posted under `Doc_No = "CLM-REV-{ClaimId}"`:
- **DEBIT (`+SettledAmount`)**: Ledger `203` (`Claim Settlement Payable / Bank Clearing`)
  - `AccTransId = 16`, `TransactionType = "DEBIT"`, `LedgerMId = 203`, `amount = +SettledAmount`
- **CREDIT (`-SettledAmount`)**: Ledger `103` (`Insurer Claim Recoverable / Claim Settlement Receivable`)
  - `AccTransId = 16`, `TransactionType = "CREDIT"`, `LedgerMId = 103`, `amount = -SettledAmount`

Original `AccTransId = 15` rows are **never deleted or mutated**, preserving an immutable audit trail while bringing net claim ledger impact back to `0.00`.
