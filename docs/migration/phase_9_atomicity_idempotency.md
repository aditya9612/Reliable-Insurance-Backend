# Phase 9 — Atomicity, Rollback, Concurrency & Idempotency Specification

**Repository**: `Reliable-Insurance-Backend`  
**Phase**: `Phase 9 — Commission & Accounting Engine (Stage A13)`  
**Target Runtime Database**: `localhost:3306/reliable_insurance_dev`

---

## 1. Single Unit-of-Work Atomicity & Rollback Boundaries

Every mutating operation in `CommissionAccountingService` executes inside a single SQLAlchemy 2.0 `AsyncSession` transaction guarded by `_COMMISSION_WRITE_LOCK` and InnoDB `SELECT ... FOR UPDATE` row locks:

### 1.1 Commission Payout Unit of Work (`create_commission_payout` & `create_bulk_commission_payout`)
1. Acquire `_COMMISSION_WRITE_LOCK` and execute `SELECT ... FOR UPDATE` on:
   - `tbl_agentcommissionpayment` (or `tbl_franchisecommission`)
   - `tbl_transaction`
   - `tbl_cutnpaycommpayable` (if present)
2. Verify idempotency key (`IDEMP:<key>`), policy settlement status (`OutstandingAmount == 0.00`, `Ischequeclearing == 0`, `ChequeBankStatus != 2`), hold status (`Flag != "HOLD_CHEQUE_BOUNCE"`), and remaining payable balance (`0 < payout_amount <= remaining_payable`).
3. Update `tbl_agentcommissionpayment` (`AdvAmt`, `NetAmount`, `PaymentStatus`, `Narration`) or `tbl_franchisecommission` (`FCommissionPaid`), `tbl_cutnpaycommpayable` (`Balance`, `Flag`), and `tbl_transaction` (`CommissionPaid` / `FranchiseCommPaid` / `CommProcessSubmit`).
4. Allocate concurrency-safe sequential `(Doc_No, voucher_no)` and insert balanced double-entry voucher rows (`AccTransId = 6`, `+payout_amount` Debit and `-payout_amount` Credit) into `tbl_account`.
5. If `payout_mode == "EWALLET"`, credit the partner's E-Wallet sub-ledger (`AccTransId = 10`, `+payout_amount`).
6. Commit transaction (`await self.session.commit()`).
7. **On Any Exception (`HTTPException` or `RuntimeError` fault injection)**:
   - Execute `await self.session.rollback()`.
   - Zero partial updates in `tbl_agentcommissionpayment`, `tbl_franchisecommission`, `tbl_cutnpaycommpayable`, `tbl_transaction`, or `tbl_account`.

### 1.2 Deterministic Fault Injection Hooks (`simulate_failure_at`)
Supported on `create_commission_payout`, `reverse_commission_payout`, and `create_voucher`:
- `"AFTER_COMMISSION_UPDATE"`: Raises fault after updating commission/transaction rows and flushing, verifying rollback of commission state and zero `tbl_account` rows.
- `"DURING_VOUCHER"`: Raises fault after inserting the Debit leg of the voucher before the Credit leg, verifying zero orphan single-leg vouchers.
- `"BEFORE_COMMIT"`: Raises fault after all rows are flushed right before `commit()`, verifying complete rollback across all tables.

---

## 2. Multi-Layer Idempotency & Duplicate Prevention

1. **Payout `idempotency_key` Guard**:
   - Stored in `tbl_account.Extra2` (or `Narration` tag `IDEMP:<key>`).
   - Submitting a duplicate `idempotency_key` raises **`HTTP 409 Conflict`** (`"Duplicate commission payout request: idempotency_key '<key>' already processed under Voucher #<doc_no>"`).
2. **Exhausted Payable Balance Guard**:
   - Attempting to pay out a commission row whose `remaining_payable_amount == Decimal("0.00")` (`PaymentStatus == 1.00` or `FCommissionPaid == FranchiseNetComm`) raises **`HTTP 409 Conflict`** (`"Commission is already fully paid"`).
3. **Double Reversal Guard**:
   - Attempting to reverse a payout voucher (`POST /api/v1/commission-payouts/{doc_no}/reverse`) or accounting voucher (`POST /api/v1/accounting/vouchers/{doc_no}/reverse`) that has already been reversed raises **`HTTP 409 Conflict`**.
4. **Voucher `idempotency_key` Guard**:
   - Submitting a duplicate `idempotency_key` to `POST /api/v1/accounting/vouchers` raises **`HTTP 409 Conflict`**.

---

## 3. Concurrency Design (100 Concurrent Payouts & Concurrent Voucher Numbering)

1. **100 Concurrent Payout Attempts Against Shared Payable Pool**:
   - All requests serialize through `_COMMISSION_WRITE_LOCK` and execute `SELECT ... FOR UPDATE` with `execution_options(populate_existing=True)` on the target commission row(s).
   - For a commission payable pool of `25,000.00` subjected to `100` concurrent partial payout attempts of `500.00` each:
     - Exactly `50` requests succeed (`201 Created`), consuming `50 x 500.00 = 25,000.00`.
     - Exactly `50` requests are rejected (`409 Conflict` / `422 Unprocessable Entity`) once `remaining_payable_amount` reaches `0.00`.
     - Final `remaining_payable_amount == Decimal("0.00")` (never negative), with `50` unique voucher numbers and balanced `tbl_account` entries.
2. **Concurrent Voucher Number Allocation**:
   - Parallel calls to `POST /api/v1/accounting/vouchers` and `POST /api/v1/commission-payouts` allocate strictly unique, gap-free sequential `Doc_No` and `VCH-{BranchId:02d}-{FY}-{Doc_No:06d}` codes with zero collisions.
