# Phase 8 — Partner E-Wallet, Lock/Release & Concurrency Specification

**Repository**: `Reliable-Insurance-Backend`  
**Phase**: `Phase 8 — Payments, Cheques & Reconciliation Engine (Stage A7)`  
**Target Runtime Database**: `localhost:3306/reliable_insurance_dev`

---

## 1. Legacy E-Wallet Architecture & Physical Storage

In the legacy system (`Clerk/EWalletApproval.aspx.cs`, `Clerk/FranchiseWallateApproval.aspx.cs`, `Clerk/AgentCommissionUseWallet.aspx.cs`, `Service.asmx.cs::GetAgentWalletBalance`, `GetWalletLedger`), partner (Agent and Franchise) E-Wallet accounts and movements are backed by the verified physical tables in `reliable_insurance_dev`:

1. **Wallet Master Sub-Ledger (`tbl_ledgermaster` — `app/models/ledger.py`)**:
   - `LedgerMId` (`INT PK`): Unique sub-ledger identifier.
   - `LedgerTypeId` (`INT`):
     - `5` = Agent E-Wallet Sub-Ledger (`ReferenceId = agent_id`)
     - `6` = Franchise E-Wallet Sub-Ledger (`ReferenceId = franchise_id`)
   - `ReferenceId` (`INT`): Owner principal ID (`agent_id` or `franchise_id`).
   - `LedgerName` (`VARCHAR(255)`): `"EWALLET-AGENT-{owner_id}"` or `"EWALLET-FRANCHISE-{owner_id}"`.
   - `BranchId` (`INT`): Owner's branch.

2. **Chronological Wallet Movement Ledger (`tbl_account` — `app/models/account.py`)**:
   Every credit, lock, release, debit, and refund is recorded as an immutable row in `tbl_account` tied to `LedgerMId`:
   - **`AccTransId = 10` (`Extra1 = "WALLET_TOPUP"`)**:
     - `amount = +topup_amount` (`Decimal > 0.00`)
     - `Extra2 = f"IDEMP:{idempotency_key}"`
     - `PaymentType = payment_mode` (`"NEFT"`, `"UPI"`, `"CASH"`, `"COMMISSION_CREDIT"`, etc.)
   - **`AccTransId = 11` (`Extra1 = "WALLET_LOCK"` or `"WALLET_LOCK_CONSUMED"` or `"WALLET_LOCK_RELEASED"`)**:
     - `amount = -lock_amount` (`Decimal < 0.00`)
     - `Extra2 = f"LOCK:{lock_id}"`
     - `TransId = proposal_trans_id` (optional), `TransactionId = transaction_id` (optional)
     - When active: `Extra1 == "WALLET_LOCK"` (funds reserved).
     - When released: `Extra1` transitions to `"WALLET_LOCK_RELEASED"` and a paired `AccTransId = 12` row is written.
     - When consumed by policy payment: `Extra1` transitions to `"WALLET_LOCK_CONSUMED"` and a paired `AccTransId = 13` audit confirmation is recorded.
   - **`AccTransId = 12` (`Extra1 = "WALLET_RELEASE"`)**:
     - `amount = +release_amount` (`Decimal > 0.00` — audit record of lock release; pairs with `"WALLET_LOCK_RELEASED"`).
   - **`AccTransId = 13` (`Extra1 = "WALLET_DEBIT"`)**:
     - `amount = -debit_amount` (`Decimal < 0.00` — direct wallet debit or consumed lock debit toward policy `TransactionId`).
   - **`AccTransId = 14` (`Extra1 = "WALLET_REFUND"`)**:
     - `amount = +refund_amount` (`Decimal > 0.00` — credit restored to wallet when an `EWALLET` policy payment or policy is reversed/cancelled).

---

## 2. Deterministic Wallet Balance Formula

For any wallet sub-ledger `LedgerMId` with active (`isdeleted == 0`) rows in `tbl_account`:
- **Total Credited ($C_{\text{tot}}$)**:
  $$C_{\text{tot}} = \sum \text{amount} \quad \text{where } \text{AccTransId} \in \{10, 14\} \text{ and } \text{amount} > 0$$
- **Total Debited ($D_{\text{tot}}$)**:
  $$D_{\text{tot}} = \sum |\text{amount}| \quad \text{where } \text{AccTransId} = 13 \text{ and } \text{Extra1} = \text{"WALLET\_DEBIT"}$$
- **Currently Locked ($L_{\text{act}}$)**:
  $$L_{\text{act}} = \sum |\text{amount}| \quad \text{where } \text{AccTransId} = 11 \text{ and } \text{Extra1} = \text{"WALLET\_LOCK"}$$
- **Total Balance ($B_{\text{tot}}$ — including reserved funds)**:
  $$B_{\text{tot}} = C_{\text{tot}} - D_{\text{tot}}$$
- **Available Balance ($B_{\text{avail}}$ — spendable/lockable funds)**:
  $$B_{\text{avail}} = C_{\text{tot}} - D_{\text{tot}} - L_{\text{act}}$$

Invariant enforced on every operation:
$$B_{\text{avail}} \ge 0.00, \quad L_{\text{act}} \ge 0.00, \quad B_{\text{tot}} = B_{\text{avail}} + L_{\text{act}}$$

---

## 3. Wallet Lock / Release / Consume State Machine

1. **Lock (`POST /api/v1/wallets/{owner_id}/lock`)**:
   - Acquires `SELECT ... FOR UPDATE` on the owner's `tbl_ledgermaster` row.
   - Verifies $B_{\text{avail}} \ge \text{lock\_amount}$ (`422` if insufficient balance).
   - Inserts `AccTransId = 11` (`Extra1 = "WALLET_LOCK"`, `amount = -lock_amount`).
   - If `proposal_trans_id` is provided, updates `tbl_transactionappnew.EWalletUsedamt = lock_amount` and `EwalletStatus = 1`.
   - Reduces $B_{\text{avail}}$ by `lock_amount` and increases $L_{\text{act}}$ by `lock_amount`.
2. **Release (`POST /api/v1/wallets/{owner_id}/release`)**:
   - Acquires `SELECT ... FOR UPDATE` on `tbl_ledgermaster` and the `AccTransId = 11` lock row.
   - If the lock is already `"WALLET_LOCK_RELEASED"` or `"WALLET_LOCK_CONSUMED"`, raises `409 Conflict`.
   - Updates the lock row `Extra1 = "WALLET_LOCK_RELEASED"` and inserts an audit `AccTransId = 12` (`Extra1 = "WALLET_RELEASE"`, `amount = +lock_amount`).
   - If linked to `tbl_transactionappnew`, sets `EwalletStatus = 0`.
   - Restores $B_{\text{avail}}$ by `+lock_amount` and reduces $L_{\text{act}}$ by `lock_amount`.
3. **Consume Lock / Direct Debit**:
   - When a policy payment with `PaymentType == "EWALLET"` (or `POST /api/v1/wallets/{owner_id}/debit`) references an active `lock_id`:
     - Marks the lock row `Extra1 = "WALLET_LOCK_CONSUMED"` and inserts the `AccTransId = 13` (`Extra1 = "WALLET_DEBIT"`, `amount = -lock_amount`) row.
     - $L_{\text{act}}$ decreases by `lock_amount`, $D_{\text{tot}}$ increases by `lock_amount`, and $B_{\text{avail}}$ remains unchanged (no double deduction!).
   - When no `lock_id` is supplied:
     - Verifies $B_{\text{avail}} \ge \text{debit\_amount}$ under `FOR UPDATE` lock (`422` if insufficient) and inserts `AccTransId = 13` (`Extra1 = "WALLET_DEBIT"`, `amount = -debit_amount`).

---

## 4. Concurrency Design (100 Concurrent Operations Guarantee)

All wallet mutating operations (`top-up`, `lock`, `release`, `debit`, `refund`) synchronize through two layers:
1. Process-level async mutex (`_WALLET_WRITE_LOCK`) for same-loop serialization.
2. Database-level InnoDB row lock (`SELECT ... FROM tbl_ledgermaster WHERE LedgerMId = :id FOR UPDATE`) inside an atomic transaction boundary (`session.begin_nested()`).

Under 100 concurrent wallet debit/lock/top-up requests:
- Zero lost updates
- Zero negative balances (`422` returned once available balance is exhausted)
- Zero duplicate transactions when `idempotency_key` is repeated (`409 Conflict`).
