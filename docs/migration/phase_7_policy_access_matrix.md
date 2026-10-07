# Phase 7 — Policy Booking & Transaction Engine: Role, Branch & Principal Access Matrix

**Phase:** 7 — Policy Booking & Transaction Engine  
**Stage:** A7 — RBAC, Branch Isolation & Server-Side Principal Scope Specification  
**Source of Truth:** Phase 5F Audit (`docs/migration/phase_5f_role_api_table_access_matrix.md`) & `app/core/rbac.py`

---

## 1. Phase 7 Role Sets (`app/core/rbac.py`)

All role checks strictly validate against the 56 verified roles in `VERIFIED_ROLE_CATALOG`. Phantom roles (`SUPERADMIN`) and `BranchId == 0` overrides are prohibited.

| Role Set Constant | Authorized Roles (Exact `tbl_userrole.UserRole` Strings) | Permitted Operations |
|---|---|---|
| **`POLICY_BOOKING_WRITE_ROLES`** | `OWNER`, `ADMIN`, `IT SUPPORT`, `OPERATOR`, `OPERATOR HEAD`, `ALL USER`, `Freelancer`, `FRANCHISE`, `FRANCHISE TYPE 2`, `FRANCHISE TYPE 3`, `FRANCHISE OPERATOR`, `OTHER`, `ENDORSEMENT` | Direct policy booking (`POST /api/v1/policies/book`), underwriting update (`PUT /api/v1/policies/{id}`), and payment recording (`POST /api/v1/policies/{id}/payments`). |
| **`POLICY_PROPOSAL_WRITE_ROLES`** | All `POLICY_BOOKING_WRITE_ROLES` **plus** `AGENT`, `FRANCHISE AGENT`, `RELATIONSHIP MANAGER`, `LOCATION HEAD`, `FRANCHISE SALES EXECUTIVE`, `Insurance Exective`, `SALES`, `CallIng Employee`, `Calling Indivisional`, `Broker partner`, `QUOT CO-ORDINATOR`, `SUPERVISOR`, `MANAGER` | Financial preview (`POST /api/v1/policies/preview`) and mobile/partner proposal submission (`POST /api/v1/policies/proposals`). |
| **`POLICY_CASHIER_APPROVAL_ROLES`** | `OWNER`, `ADMIN`, `IT SUPPORT`, `CASHIER`, `ACCOUNT`, `ACCOUNT HEAD`, `FRANCHISE` | Cashier payment verification (`POST /api/v1/policies/proposals/{id}/approve` with `stage="CASHIER"`). |
| **`POLICY_ACCOUNTANT_APPROVAL_ROLES`** | `OWNER`, `ADMIN`, `IT SUPPORT`, `ACCOUNT`, `ACCOUNT HEAD` | Accountant policy & commission verification (`POST /api/v1/policies/proposals/{id}/approve` with `stage="ACCOUNTANT"`). |
| **`POLICY_OWNER_APPROVAL_ROLES`** | `OWNER`, `ADMIN`, `SHREYANSH OWNER` | Owner discount/credit/payout approval (`POST /api/v1/policies/proposals/{id}/approve` with `stage="OWNER"`). |
| **`POLICY_DELETE_ROLES`** | `OWNER`, `ADMIN`, `IT SUPPORT`, `ACCOUNT`, `ACCOUNT HEAD` | Policy cancellation / soft-delete and ledger reversal (`POST /api/v1/policies/{id}/cancel`). |
| **`POLICY_BOOKING_READ_ROLES`** | All 54 active (non-soft-deleted) roles in `VERIFIED_ROLE_CATALOG` | Scoped read/list of policies (`GET /api/v1/policies`, `GET /api/v1/policies/{id}`) and proposals (`GET /api/v1/policies/proposals`). |

---

## 2. Endpoint → Role → Branch → Principal Isolation Matrix

| FastAPI Endpoint | Method | Role Gate (`require_roles`) | Global Scope Roles | Branch Isolation Rule | Principal (`AgentId` / `EmpId` / `FranchiseId`) Rule |
|---|---|---|---|---|---|
| `/api/v1/policies/preview` | `POST` | `POLICY_PROPOSAL_WRITE_ROLES` | `OWNER`, `ADMIN`, `IT SUPPORT`, `ACCOUNT`, `ACCOUNT HEAD` | Uses caller's `BranchId` | If quotation is referenced, verifies caller has read access to that quotation. |
| `/api/v1/policies/proposals` | `POST` | `POLICY_PROPOSAL_WRITE_ROLES` | `OWNER`, `ADMIN`, `IT SUPPORT` | Forces `BranchId = current_user.BranchId` (unless Global Admin specifies branch) | `AGENT`/`FRANCHISE AGENT`: forces `AgentId = ctx.agent_id or ctx.user_id`. `RSM`/Employee: forces `SalesExecutiveId = ctx.emp_id or ctx.user_id`. `FRANCHISE`: forces `FranchaiseId = ctx.franchise_id or ctx.user_id`. |
| `/api/v1/policies/proposals` | `GET` | `POLICY_BOOKING_READ_ROLES` | `OWNER`, `ADMIN`, `IT SUPPORT`, `ACCOUNT`, `ACCOUNT HEAD` | Non-global roles filtered by `BranchId = current_user.BranchId` | `AGENT` sees only own `AgentId`; `RSM` sees own `SalesExecutiveId`; `FRANCHISE` sees own `FranchaiseId`. |
| `/api/v1/policies/proposals/{trans_id}` | `GET` | `POLICY_BOOKING_READ_ROLES` | `OWNER`, `ADMIN`, `IT SUPPORT`, `ACCOUNT`, `ACCOUNT HEAD` | `403 Forbidden` if `proposal.BranchId != current_user.BranchId` (for non-global roles) | `403 Forbidden` if outside caller's `AgentId` / `SalesExecutiveId` / `FranchaiseId`. |
| `/api/v1/policies/proposals/{trans_id}/approve` | `POST` | Stage-specific (`CASHIER`, `ACCOUNTANT`, `OWNER`) | `OWNER`, `ADMIN`, `IT SUPPORT`, `ACCOUNT`, `ACCOUNT HEAD` | `CASHIER` and `FRANCHISE` must match `proposal.BranchId` | `FRANCHISE` must also match `proposal.FranchaiseId`. |
| `/api/v1/policies/book` | `POST` | `POLICY_BOOKING_WRITE_ROLES` | `OWNER`, `ADMIN`, `IT SUPPORT` | Customer & Vehicle must belong to caller's `BranchId` (unless Global Admin); writes `tbl_transaction.BranchId = customer.BranchId` | `FRANCHISE` roles (`9, 52, 53, 54`) locked to own `FranchiseCode = str(ctx.franchise_id or ctx.user_id)`. Operator/Admin may assign branch `AgentId` and `SalesEx_id`. |
| `/api/v1/policies` | `GET` | `POLICY_BOOKING_READ_ROLES` | `OWNER`, `ADMIN`, `IT SUPPORT`, `ACCOUNT`, `ACCOUNT HEAD`, `ALL USER` | Branch roles filtered by `BranchId = current_user.BranchId` | `AGENT` (`4, 16, 56`) filtered by `AgentId == ctx.agent_id`; `RSM`/Employee (`5, 20, 24, 32`) filtered by `SalesEx_id == ctx.emp_id`; `FRANCHISE` (`9, 52, 53, 54`) filtered by `FranchiseCode == str(ctx.franchise_id)`. |
| `/api/v1/policies/{transaction_id}` | `GET` | `POLICY_BOOKING_READ_ROLES` | `OWNER`, `ADMIN`, `IT SUPPORT`, `ACCOUNT`, `ACCOUNT HEAD`, `ALL USER` | `403 Forbidden` if cross-branch for non-global role | `403 Forbidden` if outside Agent / Employee / Franchise ownership scope. |
| `/api/v1/policies/{transaction_id}` | `PUT` | `POLICY_BOOKING_WRITE_ROLES` | `OWNER`, `ADMIN`, `IT SUPPORT` | `403 Forbidden` if `tx.BranchId != current_user.BranchId` | `FRANCHISE` roles restricted to own `FranchiseCode`. |
| `/api/v1/policies/{transaction_id}/payments` | `POST` | `POLICY_BOOKING_WRITE_ROLES \| CASHIER \| ACCOUNT \| ACCOUNT HEAD` | `OWNER`, `ADMIN`, `IT SUPPORT`, `ACCOUNT`, `ACCOUNT HEAD` | `403 Forbidden` if `tx.BranchId != current_user.BranchId` | `FRANCHISE` roles restricted to own `FranchiseCode`. |
| `/api/v1/policies/{transaction_id}/cancel` | `POST` | `POLICY_DELETE_ROLES` | `OWNER`, `ADMIN`, `IT SUPPORT`, `ACCOUNT`, `ACCOUNT HEAD` | Global for `POLICY_DELETE_ROLES` | Records `UpdateUser = str(current_user.UserId)` and soft-deletes transaction, payments, commission, and accounting rows. |

---

## 3. Anti-Spoofing Guarantees

1. **Zero Trust in Client Principal Fields:**
   - If an `AGENT` calls `POST /api/v1/policies/proposals` and passes `agent_id = 99999` in the payload, `PolicyBookingService` overrides it with `ctx.agent_id or ctx.user_id` (or rejects cross-agent spoofing).
   - If a `FRANCHISE` user calls `POST /api/v1/policies/book`, `PolicyBookingService` locks `franchise_id` / `FranchiseCode` to the server-resolved `ctx.franchise_id or ctx.user_id`. If the payload attempts to book on behalf of a different franchise, `HTTP 403 Forbidden` is raised.
2. **Cross-Branch Customer/Vehicle Guard:**
   - A branch-scoped `OPERATOR` in `BranchId = 1` cannot book a policy for a Customer or Vehicle belonging to `BranchId = 2` (`HTTP 403 Forbidden`).
3. **Customer-Vehicle Ownership Guard:**
   - `tbl_vehicledetails.CustomerId` **must** equal the `customer_id` supplied in the policy booking request (`HTTP 422 Unprocessable Entity` if mismatched).
