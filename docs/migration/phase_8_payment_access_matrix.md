# Phase 8 — Payment, Cheque, Reconciliation & Wallet Access Control Matrix

**Repository**: `Reliable-Insurance-Backend`  
**Phase**: `Phase 8 — Payments, Cheques & Reconciliation Engine (Stage A8)`  
**Target Runtime Database**: `localhost:3306/reliable_insurance_dev`

---

## 1. Role Catalog & Phase 8 Role Sets (`app/core/rbac.py`)

Extending the verified 56-role catalog from Phase 5F/5G and Phase 7:

| Phase 8 Role Set Constant | Authorized Legacy Roles (`tbl_userrole.UserRole`) | Business Operations Permitted |
|---|---|---|
| `POLICY_PAYMENT_WRITE_ROLES` | `OWNER`, `ADMIN`, `OPERATOR`, `CASHIER`, `FRANCHISE`, `ACCOUNT`, `OPERATOR HEAD`, `LOCATION HEAD`, `ACCOUNT HEAD`, `IT SUPPORT`, `SHREYANSH OWNER`, `ALL USER`, `Freelancer`, `FRANCHISE TYPE 2`, `FRANCHISE TYPE 3`, `FRANCHISE OPERATOR` | Record policy payments (`POST /api/v1/policies/{id}/payments`), update payment metadata, deposit cheques (`POST /api/v1/payments/{id}/deposit`) |
| `PAYMENT_CLEARANCE_ROLES` | `OWNER`, `ADMIN`, `CASHIER`, `ACCOUNT`, `ACCOUNT HEAD`, `IT SUPPORT`, `SHREYANSH OWNER` | Clear cheques/DDs (`POST /api/v1/payments/{id}/clear`) and approve payment stages (`POST /api/v1/payments/{id}/approve`) |
| `PAYMENT_BOUNCE_REVERSAL_ROLES` | `OWNER`, `ADMIN`, `ACCOUNT`, `ACCOUNT HEAD`, `IT SUPPORT`, `SHREYANSH OWNER` | Mark cheque bounced + levy penalty (`POST /api/v1/payments/{id}/bounce`), reverse payments (`POST /api/v1/payments/{id}/reverse`) |
| `RECONCILIATION_WRITE_ROLES` | `OWNER`, `ADMIN`, `ACCOUNT`, `ACCOUNT HEAD`, `IT SUPPORT`, `SHREYANSH OWNER` | Execute single/batch insurer reconciliation (`POST /api/v1/reconciliation`, `POST /api/v1/reconciliation/{id}/match`, `POST /api/v1/reconciliation/{id}/reverse`) |
| `RECONCILIATION_READ_ROLES` | `RECONCILIATION_WRITE_ROLES` + `OPERATOR HEAD`, `LOCATION HEAD`, `ALL USER` | List and inspect insurer reconciliation status (`GET /api/v1/reconciliation`) |
| `WALLET_ADMIN_WRITE_ROLES` | `OWNER`, `ADMIN`, `ACCOUNT`, `ACCOUNT HEAD`, `IT SUPPORT`, `SHREYANSH OWNER` | Approve/credit wallet top-ups (`POST /api/v1/wallets/top-up`) for any Agent/Franchise, release/manage locks across branches |
| `WALLET_PARTNER_ROLES` | `WALLET_ADMIN_WRITE_ROLES` + `AGENT`, `FRANCHISE`, `FRANCHISE AGENT`, `FRANCHISE TYPE 2`, `FRANCHISE TYPE 3`, `FRANCHISE OPERATOR`, `OPERATOR`, `OPERATOR HEAD`, `ALL USER` | Read own wallet balance & ledger (`GET /api/v1/wallets/{owner_id}`), lock/release/debit own wallet funds for policy proposals/bookings |

---

## 2. Branch & Principal Ownership Isolation Rules

| Domain | Global Roles (`OWNER`, `ADMIN`, `ACCOUNT`, `ACCOUNT HEAD`, `IT SUPPORT`, `SHREYANSH OWNER`, `ALL USER`) | Branch Staff Roles (`OPERATOR`, `CASHIER`, `OPERATOR HEAD`, `LOCATION HEAD`, `Freelancer`) | Franchise Roles (`FRANCHISE`, `FRANCHISE TYPE 2/3`, `FRANCHISE OPERATOR`) | Agent / Sales Roles (`AGENT`, `FRANCHISE AGENT`, `RELATIONSHIP MANAGER`, `Insurance Exective`) |
|---|---|---|---|---|
| **Policy Payments (`GET/POST /policies/{id}/payments`)** | All Branches | Restricted to `tx.BranchId == user.BranchId` (`403` on cross-branch) | Restricted to own `FranchiseCode` & `BranchId` | Read-only on own `AgentId` / `SalesEx_id`; `403` on direct write |
| **Cheque Deposit / Clear / Bounce / Reverse** | All Branches | `CASHIER` restricted to `payment.BranchId == user.BranchId` (`403` on bounce/reverse) | `403 Forbidden` on clear/bounce/reverse | `403 Forbidden` |
| **Insurer Reconciliation (`/api/v1/reconciliation`)** | All Branches | Read-only for `OPERATOR HEAD` / `LOCATION HEAD` within `user.BranchId`; `403` for others | `403 Forbidden` | `403 Forbidden` |
| **E-Wallet (`/api/v1/wallets/*`)** | Full read/write across all `owner_id`s | Branch-scoped read/lock/release | Strictly pinned to own `franchise_id` (`403` if accessing another wallet) | Strictly pinned to own `agent_id` (`403` if accessing another wallet; `403` on self-approving `/top-up`) |
