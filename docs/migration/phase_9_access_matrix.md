# Phase 9 — Role, Branch & Principal Access Matrix (Commission & Accounting Engine)

**Repository**: `Reliable-Insurance-Backend`  
**Phase**: `Phase 9 — Commission & Accounting Engine (Stage A11)`  
**Target Runtime Database**: `localhost:3306/reliable_insurance_dev`

---

## 1. Centralized RBAC Role Sets (`app/core/rbac.py`)

Extending the verified 56-role catalog in [`app/core/rbac.py`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/app/core/rbac.py) without introducing a second authorization framework:

| Role Set Constant in `app/core/rbac.py` | Authorized Legacy Roles (`tbl_userrole.UserRole`) | Permitted Phase 9 Operations |
|---|---|---|
| `COMMISSION_CALCULATE_ROLES` | `POLICY_PROPOSAL_WRITE_ROLES` $\cup$ `{"ACCOUNT", "ACCOUNT HEAD", "CASHIER", "BACK OFFICE"}` | Stateless / preview commission, TDS, Cut & Pay, and Franchise margin calculation (`POST /api/v1/commissions/calculate`) |
| `COMMISSION_APPROVAL_ROLES` | `{"OWNER", "ADMIN", "IT SUPPORT", "ACCOUNT", "ACCOUNT HEAD", "SHREYANSH OWNER"}` | Approve agent/franchise commission (`POST /api/v1/commissions/{type}/{id}/approve`), place or release commission hold (`POST /api/v1/commissions/transactions/{tx_id}/release-hold`) |
| `COMMISSION_PAYOUT_WRITE_ROLES` | `{"OWNER", "ADMIN", "IT SUPPORT", "ACCOUNT", "ACCOUNT HEAD", "CASHIER", "SHREYANSH OWNER"}` | Execute individual or bulk commission payout (`POST /api/v1/commission-payouts`, `POST /api/v1/commission-payouts/bulk`) and reverse commission or payout (`POST /api/v1/commission-payouts/{doc_no}/reverse`, `POST /api/v1/commissions/{type}/{id}/reverse`) |
| `COMMISSION_READ_ROLES` | All active verified roles (`CUSTOMER_VEHICLE_READ_ROLES`) | List/get agent, franchise, and Cut & Pay commission records and payout vouchers (strictly scoped by Branch and Principal ownership!) |
| `ACCOUNTING_VOUCHER_WRITE_ROLES` | `{"OWNER", "ADMIN", "IT SUPPORT", "ACCOUNT", "ACCOUNT HEAD", "CASHIER", "SHREYANSH OWNER"}` | Create or reverse double-entry accounting vouchers (`POST /api/v1/accounting/vouchers`, `POST /api/v1/accounting/vouchers/{doc_no}/reverse`) and create/resolve ledgers (`POST /api/v1/accounting/ledgers`) |
| `ACCOUNTING_READ_ROLES` | `{"OWNER", "ADMIN", "IT SUPPORT", "ACCOUNT", "ACCOUNT HEAD", "CASHIER", "OPERATOR HEAD", "SUPERVISOR", "MANAGER", "SHREYANSH OWNER", "ALL USER"}` $\cup$ `AGENT_PRINCIPAL_ROLES` $\cup$ `FRANCHISE_PRINCIPAL_ROLES` | View ledger statements, vouchers, and trial balance (Agents and Franchises are restricted strictly to their own sub-ledger `LedgerMId`!) |
| `TRIAL_BALANCE_READ_ROLES` | `{"OWNER", "ADMIN", "IT SUPPORT", "ACCOUNT", "ACCOUNT HEAD", "CASHIER", "SUPERVISOR", "MANAGER", "SHREYANSH OWNER", "ALL USER"}` | View branch/company Trial Balance (`GET /api/v1/accounting/trial-balance`); `AGENT`, `FRANCHISE`, `CLAIM`, `pOLICY VIEW` receive `403 Forbidden` on company-wide Trial Balance |

---

## 2. Branch & Principal Ownership Isolation Rules

1. **Global Admin & Global Accounting Roles (`OWNER`, `ADMIN`, `IT SUPPORT`, `ACCOUNT`, `ACCOUNT HEAD`)**:
   - Authorized for cross-branch read access across all branches (`BranchId`) and all principals (`AgentId`, `FranchiseId`).
   - Global Admin roles (`OWNER`, `ADMIN`, `IT SUPPORT`) and Accounting roles (`ACCOUNT`, `ACCOUNT HEAD`, `CASHIER`, `SHREYANSH OWNER`) have write authority for commission approval, payout, reversal, and voucher creation within their authorized branch scope (or globally for `OWNER`, `ADMIN`, `IT SUPPORT`, `ACCOUNT`, `ACCOUNT HEAD`).
2. **Branch-Scoped Back-Office Roles (`CASHIER`, `OPERATOR`, `OPERATOR HEAD`, `SUPERVISOR`, `MANAGER`)**:
   - Strictly restricted to `tx.BranchId == ctx.branch_id` (and `ledger.BranchId == ctx.branch_id`).
   - Accessing or paying out a commission or voucher belonging to another `BranchId` raises **`HTTP 403 Forbidden`**.
3. **Agent Principal Roles (`AGENT`, `FRANCHISE AGENT`, `Broker partner`)**:
   - Resolved `eff_agent_id = ctx.agent_id or ctx.user_id` strictly from server-side `PrincipalContext`.
   - Can only view `tbl_agentcommissionpayment`, `tbl_cutnpaycommpayable`, payout vouchers, and `tbl_ledgermaster` statements where `AgentId == eff_agent_id` (`ReferenceId == eff_agent_id` and `LedgerTypeId == 5`).
   - Attempting to view another agent's commission, another agent's ledger statement, or any franchise commission raises **`HTTP 403 Forbidden`**.
   - Attempting to approve or pay out commissions, create vouchers, or view Trial Balance raises **`HTTP 403 Forbidden`**.
4. **Franchise Principal Roles (`FRANCHISE`, `FRANCHISE TYPE 2`, `FRANCHISE TYPE 3`, `FRANCHISE OPERATOR`)**:
   - Resolved `eff_franchise_id = ctx.franchise_id or ctx.user_id` strictly from server-side `PrincipalContext`.
   - Can only view `tbl_franchisecommission`, payout vouchers, and `tbl_ledgermaster` statements where `FranchiseId == eff_franchise_id` (`ReferenceId == eff_franchise_id` and `LedgerTypeId == 6`).
   - Attempting to view another franchise's commission or ledger statement, or execute commission payouts/vouchers, raises **`HTTP 403 Forbidden`**.
