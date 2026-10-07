# Phase 7 — Inward Number Generation & Concurrency Specification

**Phase:** 7 — Policy Booking & Transaction Engine  
**Stage:** A4 — Inward Number Format, Sequence & Concurrency Control  
**Target Database:** `localhost:3306/reliable_insurance_dev`

---

## 1. Legacy `InwardNo` Behavior & Race Condition Analysis

In the legacy system (`Clerk/PolicyTransactionNew.aspx.cs` and `Clerk/PE_TransactionEntry.aspx.cs`), every policy transaction booked into `tbl_transaction` receives an `InwardNo` (`VARCHAR(45)`) via stored procedure `sp_generateInwardNo`.

### 1.1 Legacy Pattern
- `sp_generateInwardNo` queried `tbl_transaction` for the current count or maximum sequence within the active `BranchId` and `FinancialYear`, incremented it by `1`, and formatted an inward string before the application later executed `sp_InsertTransactionNew_2026`.
- **Legacy Concurrency Vulnerability:**
  1. `sp_generateInwardNo` was called in a **separate database round-trip** before `sp_InsertTransactionNew_2026`.
  2. No row lock (`FOR UPDATE`) was acquired during sequence calculation.
  3. No `UNIQUE` constraint existed on `tbl_transaction.InwardNo`.
  4. When two operators in the same branch clicked "Submit" within the same second, both received the exact same `InwardNo`.

---

## 2. Canonical FastAPI Inward Number Format

### 2.1 Financial Year Resolution
Indian insurance financial year runs from **April 1 (`04-01`) to March 31 (`03-31`)**:
- For a transaction date $D$:
  - If $D.\text{month} \ge 4$: $\text{FY} = \text{``YYYY-(YYYY+1)''}$ (e.g., `2026-10-06` $\rightarrow$ `"2026-2027"`, short code `"2627"`).
  - If $D.\text{month} < 4$: $\text{FY} = \text{``(YYYY-1)-YYYY''}$ (e.g., `2027-02-15` $\rightarrow$ `"2026-2027"`, short code `"2627"`).

### 2.2 Format Specification
```text
INW-{BranchId:02d}-{FY_SHORT}-{SEQ:06d}
```
- **Prefix:** `INW`
- **`{BranchId:02d}`:** Zero-padded branch identifier (e.g., `01` for Head Office `BranchId = 1`, `04` for `BranchId = 4`).
- **`{FY_SHORT}`:** 4-digit financial year code (e.g., `2627` for `2026-2027`).
- **`{SEQ:06d}`:** 6-digit monotonically increasing integer sequence per `(BranchId, FinancialYear)` starting at `000001` (e.g., `INW-01-2627-000001`, `INW-01-2627-000002`).
- Total length: `18` characters (fits comfortably within `tbl_transaction.InwardNo VARCHAR(45)`).

---

## 3. Concurrency-Safe Allocation Algorithm (`PolicyBookingRepository.allocate_inward_no`)

To guarantee **zero duplicate `InwardNo` allocation** under concurrent async requests without requiring a destructive schema change to legacy tables:

1. **Same Transaction Boundary:** `allocate_inward_no` executes inside the active `AsyncSession` transaction (`BEGIN ... COMMIT`) that immediately inserts the `tbl_transaction` row.
2. **Database-Level Serialization Lock:**
   - First, the allocator acquires a row-level exclusive lock on the branch record in `tbl_branch` (`SELECT BranchId FROM tbl_branch WHERE BranchId = :branch_id FOR UPDATE`) if the branch row exists, AND locks the latest transaction row for `(BranchId, FinancialYear)` in `tbl_transaction`:
     ```sql
     SELECT InwardNo
     FROM tbl_transaction
     WHERE BranchId = :branch_id
       AND FinancialYear = :financial_year
       AND InwardNo LIKE :prefix_pattern
     ORDER BY TransanctionId DESC
     LIMIT 1
     FOR UPDATE
     ```
   - Additionally, for MySQL session-level serialization across branches that may not yet have a row in `tbl_branch` in synthetic test fixtures, the allocator queries the max numeric suffix with `FOR UPDATE` on `tbl_transaction` (or uses MySQL `GET_LOCK('inward_no_{branch_id}_{fy_short}', 10)` scoped and released cleanly or row-locked).
   - **Note on MySQL InnoDB Locking:** Using `SELECT ... FOR UPDATE` on the matching index/rows in `tbl_transaction` combined with parsing the maximum sequence suffix `MAX(CAST(SUBSTRING_INDEX(InwardNo, '-', -1) AS UNSIGNED)) FOR UPDATE` serializes concurrent writers within InnoDB!
3. **Collision Verification:**
   - Before returning `candidate_inward_no`, the repository verifies `SELECT 1 FROM tbl_transaction WHERE InwardNo = :candidate LIMIT 1` returns no row.
   - The `tbl_transaction` row is immediately added and `await session.flush()` is called while the transaction lock is held.
4. **Rollback Safety:**
   - If any subsequent step in `book_policy` (payment validation, commission calculation, or accounting entry) raises an exception, `await session.rollback()` aborts the transaction and releases the lock, leaving no phantom `InwardNo` in `tbl_transaction`.
