# Phase 9 — Trial Balance & Double-Entry Reconciliation Specification

**Repository**: `Reliable-Insurance-Backend`  
**Phase**: `Phase 9 — Commission & Accounting Engine (Stage A9)`  
**Target Runtime Database**: `localhost:3306/reliable_insurance_dev`

---

## 1. Legacy Single-Entry vs Double-Entry Accounting Nuance

In the legacy system (`Clerk/PolicyTransactionNew.aspx.cs` vs `Clerk/TrialBalanceReport.aspx.cs`), `tbl_account` stores **two categories** of entries:
1. **Explicit Multi-Leg Double-Entry Vouchers (`AccTransId in {6, 7, 8, 9}`)** — where both the Debit leg (`+amount` on Ledger A) and Credit leg (`-amount` on Ledger B) are persisted as paired rows in `tbl_account`, so $\sum \text{Debit} == \sum \text{Credit}$ directly in `tbl_account`.
2. **Single-Sided Operational Sub-Ledger Postings (`AccTransId in {1, 2, 3, 4, 5, 10, 11, 12, 13, 14}`)** — where Phase 7 (`PolicyBookingService`) and Phase 8 (`PaymentEngineService` / `WalletService`) write a single row into `tbl_account` for operational parity (e.g., `AccTransId = 1` `+FinalPremium`, `AccTransId = 2` `+PaidAmount`, `AccTransId = 3` `-NetCommission`, `AccTransId = 4` `+PenaltyAmount`, `AccTransId = 5` `+RconComm`, `AccTransId = 10` `+TopupAmount`), while the contra control leg is implicitly the Insurer Payable Control, Customer Receivable Control, Commission Expense Control, or Bank/Cash Control account.

---

## 2. Deterministic Trial Balance Computation (`GET /api/v1/accounting/trial-balance`)

To preserve **100% compatibility with Phase 7 and Phase 8** (`tbl_account` row counts in existing tests remain untouched!) while guaranteeing the fundamental accounting equation ($\text{Total Debits} == \text{Total Credits}$) in Trial Balance reporting:

1. **Direct Ledger Aggregation**:
   - Groups all active (`isdeleted == 0`) rows in `tbl_account` (filtered by `branch_id`, `from_date`, `to_date`) by `LedgerMId`:
     - If `row.amount >= 0`: adds `round_2dp(row.amount)` to the ledger's `total_debit`.
     - If `row.amount < 0`: adds `round_2dp(abs(row.amount))` to the ledger's `total_credit`.
2. **Automatic Double-Entry Control Account Balancing for Single-Sided Legacy Postings**:
   - For every single-sided operational posting (`AccTransId in {1, 2, 3, 4, 5, 10, 11, 12, 13, 14}`) that does not have an explicit paired contra row sharing its `(Doc_No, Extra2)` voucher key:
     - `AccTransId = 1` (`+FinalPremium` on Policy Receivable): posts the contra Credit (`+FinalPremium` to `total_credit`) on the **Insurer Premium Payable Control** line.
     - `AccTransId = 2` (`+PaidAmount` or `-BounceReversal` on Policy Ledger): posts the contra Credit/Debit on the **Bank & Cash Collection Control** line.
     - `AccTransId = 3` (`-NetCommission` on Policy Commission Payable): posts the contra Debit (`+NetCommission` to `total_debit`) on the **Commission Expense Control** line.
     - `AccTransId = 4` (`+PenaltyAmount` on Policy Receivable): posts the contra Credit on the **Cheque Bounce Penalty Recovery Control** line.
     - `AccTransId = 5` (`+RconComm` on Insurer Reconciliation): posts the contra Credit on the **Brokerage Revenue Control** line.
     - `AccTransId in {10, 11, 12, 13, 14}` (Single-sided E-Wallet movements): posts the contra Credit/Debit on the **Partner E-Wallet Clearing Control** line.
3. **Trial Balance Invariant**:
   Across every combination of:
   - Policy Bookings (`AccTransId = 1, 2, 3`)
   - Subsequent Payments & Reversals (`AccTransId = 2`)
   - Cheque Bounces & Penalties (`AccTransId = 2, 4`)
   - Insurer Reconciliations (`AccTransId = 5`)
   - Commission Payouts & Reversals (`AccTransId = 6, 7`)
   - Manual / Journal Vouchers & Reversals (`AccTransId = 8, 9`)
   - Partner E-Wallet Top-Ups, Locks, Releases, Debits & Refunds (`AccTransId = 10..14`)

   the Trial Balance report satisfies:
   $$\sum_{\text{All Lines}} \text{Total Debit} == \sum_{\text{All Lines}} \text{Total Credit}$$
   $$\sum_{\text{All Lines}} \text{Net Debit Balance} == \sum_{\text{All Lines}} \text{Net Credit Balance}$$
   $$\text{variance} == \text{Decimal("0.00")}, \quad \text{is\_balanced} == \text{True}$$
