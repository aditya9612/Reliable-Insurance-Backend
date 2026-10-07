# Phase 9 — Accounting Vouchers & Concurrency-Safe Voucher Numbering Specification

**Repository**: `Reliable-Insurance-Backend`  
**Phase**: `Phase 9 — Commission & Accounting Engine (Stage A10)`  
**Target Runtime Database**: `localhost:3306/reliable_insurance_dev`

---

## 1. Accounting Voucher Architecture (`tbl_account`)

In `tbl_account` (`app/models/account.py`), an **Accounting Voucher** is a multi-line double-entry transaction where all constituent lines share:
- `Doc_No` (`Integer`): Sequential numeric voucher number allocated atomically.
- `Extra2` (`String(255)`): Canonical formatted voucher code:
  $$\text{VCH}-\{\text{BranchId}:02\text{d}\}-\{\text{FinancialYear}\}-\{\text{Doc\_No}:06\text{d}\}$$
  *(e.g., `VCH-101-2026-27-000001`)*
- `AccountDate` (`DateTime`): Voucher effective date.
- `PaymentType` (`String(255)`): Payment/settlement instrument (`"JOURNAL"`, `"NEFT"`, `"RTGS"`, `"CHEQUE"`, `"CASH"`, `"EWALLET"`, etc.).

### 1.1 Supported Voucher Types (`voucher_type`)
1. `COMMISSION_PAYOUT` (`AccTransId = 6`): Generated automatically by `POST /api/v1/commission-payouts` and `POST /api/v1/commission-payouts/bulk`.
2. `COMMISSION_REVERSAL` (`AccTransId = 7`): Generated automatically by `POST /api/v1/commission-payouts/{doc_no}/reverse`.
3. `JOURNAL` (`AccTransId = 8` for Debit lines, `AccTransId = 9` for Credit lines): General double-entry adjustment voucher (`POST /api/v1/accounting/vouchers`).
4. `PAYMENT` (`AccTransId = 8, 9`): Outward payment voucher (`POST /api/v1/accounting/vouchers`).
5. `RECEIPT` (`AccTransId = 8, 9`): Inward receipt voucher (`POST /api/v1/accounting/vouchers`).
6. `CONTRA` (`AccTransId = 8, 9`): Bank-to-Cash or Bank-to-Bank transfer voucher (`POST /api/v1/accounting/vouchers`).

---

## 2. Double-Entry Validation Rules (`POST /api/v1/accounting/vouchers`)

Every voucher creation request must contain at least 2 lines (`lines: List[VoucherLineCreateRequest]`, minimum 1 `DEBIT` and 1 `CREDIT`):
1. **Positive Line Amounts**: Every line must have `amount > Decimal("0.00")` (`422` otherwise).
2. **Valid Active Ledgers**: Every `ledger_m_id` referenced in `lines` must exist and be active (`isdeleted == '0'`) in `tbl_ledgermaster` (`404 Not Found` otherwise).
3. **Strict Double-Entry Balance Invariant**:
   $$\sum_{i \in \text{DEBIT}} \text{round\_2dp}(\text{amount}_i) == \sum_{j \in \text{CREDIT}} \text{round\_2dp}(\text{amount}_j)$$
   If $\text{Total Debit} \ne \text{Total Credit}$, the service raises **`HTTP 422 Unprocessable Entity`** (`"Accounting voucher is unbalanced: total_debit ({total_debit}) != total_credit ({total_credit})"`).
4. **Signed Persistence in `tbl_account`**:
   - Each `DEBIT` line is persisted with `AccTransId = 8`, `Extra1 = f"VOUCHER_{voucher_type}_DEBIT"`, `amount = +line_amount`.
   - Each `CREDIT` line is persisted with `AccTransId = 9`, `Extra1 = f"VOUCHER_{voucher_type}_CREDIT"`, `amount = -line_amount`.

---

## 3. Concurrency-Safe Voucher Number Allocation

To eliminate the legacy `SELECT MAX(Doc_No) + 1 FROM tbl_account` race condition:
1. All voucher-creating operations acquire the process-level `_COMMISSION_WRITE_LOCK` mutex AND execute an InnoDB locking read (`SELECT ... FOR UPDATE`) on `tbl_ledgermaster` and `tbl_account` (`WHERE Extra2 LIKE 'VCH-%' ORDER BY Doc_No DESC LIMIT 1 FOR UPDATE`).
2. Allocates `next_doc_no = (max_vch_doc_no or 0) + 1` (starting at `1` for the first voucher, or `100001` if offset is configured) and formats `voucher_no = f"VCH-{branch_id:02d}-{fy_short}-{next_doc_no:06d}"`.
3. Under concurrent voucher creation requests, every voucher receives a strictly unique, sequential `(Doc_No, voucher_no)` with zero collisions.

---

## 4. Voucher Reversal (`POST /api/v1/accounting/vouchers/{doc_no}/reverse`)

- Locks all active `tbl_account` rows belonging to `doc_no` (`WHERE Doc_No = :doc_no AND Extra2 LIKE 'VCH-%' FOR UPDATE`).
- If the voucher does not exist, raises `404 Not Found`.
- If the voucher has already been reversed (`Extra1` ends with `"_REVERSED"` or a reversal voucher already references `REV-OF:{doc_no}`), raises **`HTTP 409 Conflict`**.
- Allocates a new sequential `rev_doc_no` and `rev_voucher_no` and inserts exact mirror-opposite lines (each original `+X` Debit line produces a `-X` Credit reversal line on the same `LedgerMId`, and each original `-X` Credit line produces a `+X` Debit reversal line on the same `LedgerMId`).
- Preserves full audit history while bringing the net balance effect of the reversed voucher to `0.00`.
