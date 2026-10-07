# Phase 10 — Atomicity, Idempotency & Concurrency Specification (`phase_10_atomicity_idempotency.md`)

## 1. Overview
This document specifies the database locking, transactional atomicity, idempotency deduplication, and race-condition prevention guarantees for Phase 10 Claims, Endorsements, and Refunds.

---

## 2. Row-Level Pessimistic Locking (`SELECT ... FOR UPDATE`)

All state-mutating operations acquire row-level locks in a deterministic order (`tbl_transaction` -> `tbl_claims` / `tbl_appendorsement` -> `tbl_agentcommissionpayment`) to prevent lost updates and deadlocks:

1. **Claim Intimation (`intimate_claim`)**:
   - Locks parent `tbl_transaction` row (`SELECT ... FOR UPDATE`).
   - Checks `IdempotencyKey` and `(TransanctionId, LossDate, ClaimType)` for existing non-deleted claim before inserting `tbl_claims`.
2. **Claim Assessment, Approval, Settlement & Reversal (`assess_claim`, `approve_claim`, `settle_claim`, `reverse_claim_settlement`)**:
   - Locks `tbl_claims` row (`SELECT ... FOR UPDATE`) and parent `tbl_transaction` row.
   - Verifies exact source `ClaimStatus` after acquiring lock; if a concurrent request already transitioned the claim (e.g., settled or rejected), the second request either returns the idempotent result (if matching `IdempotencyKey`) or raises `409 Conflict`.
3. **Endorsement Creation, Approval, Application & Reversal (`create_endorsement`, `approve_endorsement`, `apply_endorsement`, `reverse_endorsement`)**:
   - Locks parent `tbl_transaction` row (`SELECT ... FOR UPDATE`) and `tbl_appendorsement` row (`SELECT ... FOR UPDATE`).
   - During `apply_endorsement`, also locks `tbl_customer`, `tbl_vehicledetails`, and `tbl_agentcommissionpayment` rows.
   - Prevents two concurrent financial endorsements from applying stale `Old*` snapshots to the same policy.
4. **Refund Approval, Disbursement & Reversal (`approve_refund`, `disburse_refund`, `reverse_refund`)**:
   - Locks `tbl_appendorsement` and `tbl_transaction` (`SELECT ... FOR UPDATE`).
   - Prevents double refund disbursement (`RefundStatus` must be `"APPROVED"` inside lock; transitions atomically to `"REFUNDED"`).

---

## 3. Atomic Multi-Table Transaction Boundary

Every Phase 10 command executes inside the request's single SQLAlchemy `AsyncSession` transaction (`await db.flush()`). If any validation error, business rule conflict, or runtime exception occurs at any step:
- **Claim Settlement Failure**: Neither `tbl_claims.ClaimStatus`/`SettledAmount` nor `tbl_account` (`AccTransId = 15`) is committed.
- **Endorsement Application Failure**: None of `tbl_appendorsement`, `tbl_transaction`, `tbl_customer`, `tbl_vehicledetails`, `tbl_agentcommissionpayment`, `tbl_franchisecommission`, or `tbl_account` is modified.
- **Refund Disbursement Failure**: Neither `tbl_appendorsement.RefundStatus`, `tbl_transaction.PaidAmount`, `tbl_ewallet`, nor `tbl_account` (`AccTransId = 17`) is committed.

---

## 4. Idempotency Guarantees

| Operation | Idempotency Key Mechanism | Replay Behavior |
|---|---|---|
| `POST /api/v1/claims` | `idempotency_key` (header `Idempotency-Key` or body `idempotency_key`) + natural key `(TransanctionId, LossDate, ClaimType)` | Returns existing `ClaimResponse` without inserting a duplicate `tbl_claims` row. |
| `POST /api/v1/claims/{id}/settle` | `idempotency_key` + check on `ClaimStatus == "SETTLED"` and `Doc_No == f"CLM-SET-{claim_id}"` | If already `SETTLED` with matching key/amount, returns existing `ClaimResponse` without duplicating `tbl_account` rows; otherwise raises `409 Conflict`. |
| `POST /api/v1/endorsements` | `idempotency_key` (header `Idempotency-Key` or body `idempotency_key`) | Returns existing `EndorsementResponse` without inserting a duplicate `tbl_appendorsement` row. |
| `POST /api/v1/endorsements/{id}/apply` | `idempotency_key` + check on `EndorsementStatus == "APPLIED"` | If already `APPLIED` with matching key, returns existing `EndorsementResponse` without re-applying deltas; otherwise raises `409 Conflict`. |
| `POST /api/v1/refunds/{id}/disburse` | `idempotency_key` + check on `RefundStatus == "REFUNDED"` | If already `REFUNDED` with matching key, returns existing `EndorsementResponse` without double-paying refund; otherwise raises `409 Conflict`. |
