# Phase 7 — Payment Instrument & Collection Dependencies

**Phase:** 7 — Policy Booking & Transaction Engine  
**Stage:** A5 — Payment Modes, Partial/Full Collection, Cut & Pay, and Cheque Lifecycle  
**Target Database:** `localhost:3306/reliable_insurance_dev`

---

## 1. Payment Architecture Overview

When a policy is booked in `PolicyTransactionNew.aspx.cs` or `PE_TransactionEntry.aspx.cs`, payment collection is tracked across **two levels**:

1. **Header-Level Payment Summary on `tbl_transaction`**:
   - `Amount` (`Decimal`): Total Gross Payable Policy Premium (`NetPermium + GST_Amount`).
   - `CutNPay` (`int`): `1` if the agent/partner deducts their net commission upfront (Cut & Pay mode), `0` if full gross premium is payable.
   - `EWalletAmountUsed` (`Decimal`): Amount debited from the agent/franchise E-Wallet toward the policy premium.
   - `OnlinePaymentToCompany` (`Decimal`): Amount paid directly online by customer/agent to the insurance company portal.
   - `PaidAmount` (`Decimal`): Total amount collected via payment instruments + E-Wallet + Online direct payment.
   - `OutstandingAmount` (`Decimal`): Remaining balance due (`max(0.00, RequiredPayable - PaidAmount)`).
   - `PolicyModeId` (`int`): Payment mode identifier (`1`=Cash, `2`=Cheque, `3`=Online/NEFT/UPI, `4`=Cut & Pay, `5`=E-Wallet, `6`=Credit/Shortfall).
   - `TStatus` (`str`): `"Booked"` (when payment is complete or approved), `"Pending"` (when payment is partial or awaiting clearance/approval), `"Cancelled"` (when soft-deleted).
   - `pendingStatus` (`str`): `"Complete"` when `OutstandingAmount == 0.00`, `"Pending"` when `OutstandingAmount > 0.00`.

2. **Instrument-Level Payment Ledger in `tbl_transactionpayment` (`app/models/payment.py` — 23 Columns)**:
   - **Primary Key:** `PaymentId` (`INT AUTO_INCREMENT`).
   - **Foreign Key:** `TransanctionId` (`INT` -> `tbl_transaction.TransanctionId`).
   - **Key Columns:**
     - `PaymentType` (`VARCHAR(45)`): `"CASH"`, `"CHEQUE"`, `"ONLINE"`, `"NEFT"`, `"RTGS"`, `"UPI"`, `"CUTNPAY"`, `"EWALLET"`, `"DIRECT_TO_INSURER"`.
     - `docno` (`VARCHAR(45)`): Cheque number, UTR, or transaction reference number.
     - `PaymentDate` (`DATE`): Instrument date / cheque date.
     - `PaidAmount` (`DOUBLE` -> `Decimal`): Instrument payment amount.
     - `bankname` (`VARCHAR(100)`): Issuing bank name (required for `"CHEQUE"`, optional for `"NEFT"`/`"ONLINE"`).
     - `IFSCCode` (`VARCHAR(100)`): Bank IFSC code.
     - ` isCompletePayment` (`TINYINT(1)`): `1` if this payment completes the policy's required payable amount, `0` otherwise.
     - `IsChequePass` (`INT`): `1` = Cleared/Passed (default `1` for Cash/Online/E-Wallet; `0` = Pending Clearance for Cheque until cleared, or `2` = Bounced).
     - `Credit` / `Debit` (`DOUBLE` -> `Decimal`): Instrument credit/debit amounts (`Credit = PaidAmount`, `Debit = 0.00` on receipt).
     - `Description` (`VARCHAR(200)`): Payment narration.
     - `CurrentDate` / `UpdateDate` (`DATETIME`): Audit timestamps.
     - `UpdateUser` (`VARCHAR(45)`): Authenticated `UserId`.
     - `BranchId` (`INT`): Scoped `BranchId`.
     - `FinancialYear` (`VARCHAR(45)`): Active financial year (e.g., `"2026-2027"`).
     - `deleted` (`TINYINT(1)`): `0` = Active, `1` = Soft-deleted/reversed.

---

## 2. Deterministic Payment & Balance Formulas

### 2.1 Effective Required Payable Calculation
Let:
- $A = \text{Amount} = \text{NetPermium} + \text{GST\_Amount}$ (Final Payable Policy Premium)
- $C_{\text{net}} = \text{NetCommission}$ (Total Net Agent/Franchise Commission after TDS)
- $\text{CutNPay} \in \{0, 1\}$

1. **Standard Mode (`CutNPay == 0`)**:
   $$\text{RequiredPayable} = A$$
2. **Cut & Pay Mode (`CutNPay == 1`)**:
   - In Cut & Pay mode, the agent remits the policy premium minus their net commission (`NetCommission`), or if an explicit `cutnpay_amount` is specified ($\le C_{\text{net}}$), deducts `cutnpay_amount`:
   $$\text{CutNPayDeduction} = \begin{cases} \text{cutnpay\_amount} & \text{if explicitly provided and } 0 \le \text{cutnpay\_amount} \le C_{\text{net}} \\ C_{\text{net}} & \text{otherwise} \end{cases}$$
   $$\text{RequiredPayable} = \max\left(0.00,\; A - \text{CutNPayDeduction}\right)$$

### 2.2 Total Collected & Outstanding Balance Calculation
Let:
- $P_{\text{instruments}} = \sum_{i} \text{instrument}_i.\text{paid\_amount}$ (sum of active payment instruments in `tbl_transactionpayment`)
- $W = \text{ewallet\_amount\_used}$ (`EWalletAmountUsed`)
- $O_{\text{insurer}} = \text{online\_payment\_to\_company}$ (`OnlinePaymentToCompany`)

Then:
$$\text{TotalPaidAmount} = P_{\text{instruments}} + W + O_{\text{insurer}}$$
$$\text{OutstandingAmount} = \max\left(0.00,\; \text{RequiredPayable} - \text{TotalPaidAmount}\right)$$

### 2.3 Overpayment & Negative Payment Validation
- Every payment instrument `paid_amount` **must** be $\ge 0.00$ (`Decimal`). Negative amounts are rejected with `HTTP 422 Unprocessable Entity`.
- `ewallet_amount_used` and `online_payment_to_company` **must** be $\ge 0.00$.
- If $\text{TotalPaidAmount} > A$ (total collected exceeds gross policy premium $A$), `PolicyBookingService` raises `HTTP 422 Unprocessable Entity` (`"Total paid amount cannot exceed gross policy premium"`).
- For `"CHEQUE"` payments: `docno` (cheque number) and `bankname` are mandatory; omitting either raises `HTTP 422 Unprocessable Entity`.

### 2.4 Subsequent Payment Recording (`POST /api/v1/policies/{transaction_id}/payments`)
- When a policy is initially booked with partial payment (`OutstandingAmount > 0`), additional payment instruments can be posted via `POST /api/v1/policies/{transaction_id}/payments`.
- Each subsequent payment atomically:
  1. Verifies the policy exists (`isdeleted == 0`) and is within the caller's branch/role scope.
  2. Verifies `new_payment.paid_amount <= existing.OutstandingAmount` (prevents overpayment).
  3. Inserts a new row into `tbl_transactionpayment`.
  4. Increments `tbl_transaction.PaidAmount += new_payment.paid_amount` and recomputes `OutstandingAmount`.
  5. If `OutstandingAmount == 0.00`, updates `tbl_transaction.pendingStatus = "Complete"`, `TStatus = "Booked"`, and marks `isCompletePayment = 1`.
  6. Posts a corresponding `AccTransId = 2` payment receipt entry into `tbl_account`.
