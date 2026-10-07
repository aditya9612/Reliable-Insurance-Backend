# Phase 7 — Policy Booking Atomicity, Rollback & Idempotency Specification

**Phase:** 7 — Policy Booking & Transaction Engine  
**Stage:** A9 — Transaction Boundaries, Failure Recovery & Duplicate Booking Prevention  
**Target Database:** `localhost:3306/reliable_insurance_dev`

---

## 1. Single Unit-of-Work Atomicity Guarantee

In legacy `Clerk/PolicyTransactionNew.aspx.cs`, policy creation executed up to 6 independent ADO.NET `MySqlCommand` calls across separate connections. A failure during payment insertion or accounting ledger posting left orphan rows in `tbl_transaction` and consumed `InwardNo` sequences.

In the FastAPI implementation (`PolicyBookingService.book_policy`), **every database write occurs inside a single SQLAlchemy 2.0 `AsyncSession` transaction boundary**:

### 1.1 Atomic Write Sequence
1. **Validation & Revalidation (Read-Only Queries):**
   - Verify Customer (`tbl_customer`) and Vehicle (`tbl_vehicledetails`) exist, are active (`deleted == 0`), belong to the same customer (`vehicle.CustomerId == customer.CustomerId`), and satisfy branch isolation.
   - Verify Insurer (`tbl_insurancecompany`) exists if master records are populated.
   - Check duplicate `PolicyNo`, duplicate `QuatationCode` consumption, duplicate `proposal_trans_id` consumption, and `idempotency_key`.
   - Revalidate Premium, NCB, OD Discount, GST, Commission, and Payment math before acquiring write locks.
2. **Write Phase (Inside Single Transaction):**
   - Step A: Acquire branch/FY sequence lock (`FOR UPDATE`) and allocate `InwardNo`.
   - Step B: `session.add(Transaction)` and `await session.flush()` to obtain auto-increment `TransanctionId`.
   - Step C: `session.add_all(TransactionPayment)` rows referencing `TransanctionId`.
   - Step D: `session.add(FranchiseCommission)` / `session.add(CutNPayCommPayable)` / `session.add(AgentCommissionPayment)` referencing `TransanctionId`.
   - Step E: `session.add_all(Account)` rows (`AccTransId = 1, 2, 3`) referencing `TransanctionId`.
   - Step F: Update `tbl_transactionappnew` (`IsSubmit = 1`, `PolicyNo = ...`) if booked from a staged proposal.
   - Step G: `await session.commit()`.

### 1.2 Deterministic Rollback Behavior
If **any** step between Step A and Step G raises an exception (e.g., database constraint error, simulated downstream fault in payment/commission/accounting, or validation error):
- `await session.rollback()` is executed immediately in the `except` block.
- **Zero Partial State:**
  - `tbl_transaction` has **0** rows written for the failed request.
  - `tbl_transactionpayment` has **0** rows written.
  - `tbl_franchisecommission`, `tbl_cutnpaycommpayable`, and `tbl_agentcommissionpayment` have **0** rows written.
  - `tbl_account` has **0** rows written.
  - The `InwardNo` sequence is automatically rolled back and remains available for the next valid booking.

---

## 2. Idempotency & Duplicate Booking Prevention

To prevent accidental double-booking from network retries, double-clicks, or concurrent operator submissions, `PolicyBookingService` enforces **four layers of duplicate protection**:

### Layer 1 — Quotation Single-Consumption Guard (`QuatationCode`)
- Before booking a policy linked to a `QuatationCode` (either via `quotation_id` or `quotation_code`), the repository executes:
  ```sql
  SELECT TransanctionId, InwardNo
  FROM tbl_transaction
  WHERE QuatationCode = :quotation_code
    AND (isdeleted = 0 OR isdeleted IS NULL)
  LIMIT 1
  FOR UPDATE
  ```
- If an active policy already exists for that `QuatationCode`, `book_policy` raises **`HTTP 409 Conflict`** (`"Quotation '{quotation_code}' has already been booked under Transaction #{tx_id} ({inward_no})"`).
- If that policy is later cancelled (`POST /api/v1/policies/{id}/cancel`, setting `isdeleted = 1`), the quotation becomes eligible for re-booking if needed.

### Layer 2 — Staged Proposal Single-Consumption Guard (`TransId`)
- When booking from a staged proposal (`proposal_trans_id`), the repository locks the `tbl_transactionappnew` row (`FOR UPDATE`) and checks whether `tbl_transaction` already has an active (`isdeleted = 0`) record with `TransId = :proposal_trans_id`.
- If already booked, raises **`HTTP 409 Conflict`**.

### Layer 3 — Active Policy Number Uniqueness Guard (`PolicyNo` + `InsuranceCompanyId`)
- When a non-empty `policy_no` is supplied (excluding placeholder values like `"PENDING"` or `"TBA"`), the repository checks:
  ```sql
  SELECT TransanctionId, InwardNo
  FROM tbl_transaction
  WHERE PolicyNo = :policy_no
    AND InsuranceCompanyId = :insurance_company_id
    AND (isdeleted = 0 OR isdeleted IS NULL)
  LIMIT 1
  FOR UPDATE
  ```
- If an active policy with the same `(PolicyNo, InsuranceCompanyId)` already exists, raises **`HTTP 409 Conflict`**.

### Layer 4 — Client `idempotency_key` Guard
- Callers may pass an optional `idempotency_key: str` in `PolicyBookingCreateRequest`.
- The key is stored in `tbl_transaction.OtherRemark` (tagged `IDEMPOTENCY:{key}`) and checked with `FOR UPDATE` before insertion.
- If a second request arrives with the same `idempotency_key` for an active transaction, raises **`HTTP 409 Conflict`** referencing the existing `TransanctionId` and `InwardNo`.
