# Phase 5G — Customer / Vehicle Role, Branch & Principal Authorization Hardening + Read/Search APIs

**Repository:** `Reliable-Insurance-Backend`  
**Phase:** `5G — Customer/Vehicle Read-Search + Role/Branch/Owner Hardening`  
**Target Environment:** Local Development (`localhost:3306/reliable_insurance_dev`)  
**Status:** COMPLETE — VERIFIED

---

## 1. Executive Summary

Phase 5G implements the authorization hardening and read/search API contracts identified in the Phase 5F Role/API/Table/CRUD/Branch/Owner Access Audit (`GAP-5F-01`, `GAP-5F-02`, `GAP-5F-03`, `GAP-5F-04`, and `GAP-5F-09`) while preserving 100% of existing Phase 1–5E contracts and tests:

1. **Verified 56-Role Catalog (`GAP-5F-02`)**: Centralized in [`app/core/rbac.py`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/app/core/rbac.py) matching `tbl_userrole` (`RoleId 1..57`, 56 rows).
2. **Removed Invalid Authorization Assumptions (`GAP-5F-02`)**: Eliminated the phantom `"SUPERADMIN"` role and removed `BranchId in (0, None)` as a primary admin check in [`CustomerService._is_admin`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/app/services/customer.py#L24-L32) and [`VehicleService._is_admin`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/app/services/vehicle.py#L40-L48).
3. **Active-Role Enforcement (`GAP-5F-04`)**: Hardened [`AuthService.login`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/app/services/auth.py#L51-L55) and [`get_current_user`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/app/core/dependencies.py#L61-L72) to reject users mapped to missing or soft-deleted roles (`role.isdeleted == '1'`, e.g., `POLICY BAZAR` RoleId=17 and `POLICY BAZAR AGENT` RoleId=18) with `401 Unauthorized`.
4. **Server-Side Principal Context Resolution (`GAP-5F-03`)**: Implemented [`PrincipalContext`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/app/core/rbac.py#L232-L246) and [`resolve_principal_context`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/app/core/rbac.py#L249-L350) resolving `agent_id`, `emp_id` (`employee_id`), and `franchise_id` strictly from server-side database relationships (`tbl_user.partner_user_id` and transaction/commission records), never from client headers, query params, or request bodies.
5. **Customer & Vehicle Write Role Authorization (`GAP-5F-01`)**: Enforced `Depends(require_roles(*CUSTOMER_VEHICLE_WRITE_ROLES))` on `POST /api/v1/customers`, `PUT /api/v1/customers/{customer_id}`, `POST /api/v1/customers/{customer_id}/vehicles`, and `PUT /api/v1/customers/{customer_id}/vehicles/{vehicle_id}`.
6. **Authenticated Customer & Vehicle Read/Search APIs (`GAP-5F-09`)**: Implemented `GET /api/v1/customers`, `GET /api/v1/customers/{customer_id}`, `GET /api/v1/customers/{customer_id}/vehicles`, and `GET /api/v1/vehicles` with bounded pagination, soft-delete exclusion (`isdeleted != '1'`), branch isolation, and multi-`FinancialYear` registration lookup parity.

---

## 2. Verified Role Catalog & Removed Assumptions (`GAP-5F-02`, `GAP-5F-04`)

### 2.1 Removed Invalid Assumptions
| Legacy / FastAPI Assumption | Phase 5F Audit Finding | Phase 5G Hardened Behavior |
|---|---|---|
| `"SUPERADMIN"` in `_is_admin()` | Does not exist in `tbl_userrole` (phantom role). | Removed from all role constants, services, and endpoints; rejected (`403 Forbidden`). |
| `user.BranchId in (0, None)` in `_is_admin()` | `0 / 3,818` production users have `BranchId = 0` or `NULL`; treating `0`/`None` as admin risks accidental privilege escalation. | Removed from `CustomerService._is_admin` and `VehicleService._is_admin`. Global admin authority is determined strictly by verified role membership (`OWNER`, `ADMIN`, `IT SUPPORT`). |
| Inactive Role Login (`role.isdeleted == '1'`) | `RoleId=17` (`POLICY BAZAR`) and `RoleId=18` (`POLICY BAZAR AGENT`) are soft-deleted (`isdeleted='1'`) in `tbl_userrole`. | Rejected with `401 Unauthorized` in both `AuthService.login` and `get_current_user`. |

### 2.2 Role Groupings in `app/core/rbac.py`
- **`GLOBAL_ADMIN_ROLES`**: `OWNER`, `ADMIN`, `IT SUPPORT`
- **`GLOBAL_READ_ROLES`**: `OWNER`, `ADMIN`, `IT SUPPORT`, `ACCOUNT`, `ACCOUNT HEAD`
- **`CUSTOMER_VEHICLE_WRITE_ROLES`**: `OWNER`, `ADMIN`, `IT SUPPORT`, `OPERATOR`, `OPERATOR HEAD`, `ALL USER`, `Freelancer`, `FRANCHISE`, `FRANCHISE TYPE 2`, `FRANCHISE TYPE 3`, `FRANCHISE OPERATOR`, `OTHER`, `ENDORSEMENT`
- **`CUSTOMER_VEHICLE_READ_ROLES`**: All active (`isdeleted == '0'`) verified roles in `VERIFIED_ROLE_CATALOG`

---

## 3. Customer & Vehicle Write Authorization Matrix (`GAP-5F-01`)

| Role Category | Representative Roles | `POST /api/v1/customers` | `PUT /api/v1/customers/{id}` | `POST /api/v1/customers/{id}/vehicles` | `PUT /api/v1/customers/{id}/vehicles/{vid}` | Branch Scope |
|---|---|---|---|---|---|---|
| **Global Admin** | `OWNER`, `ADMIN`, `IT SUPPORT` | `201 Created` | `200 OK` | `201 Created` | `200 OK` | **All Branches** (can specify `BranchId` on create) |
| **Back-Office / Franchise Write** | `OPERATOR`, `OPERATOR HEAD`, `ALL USER`, `Freelancer`, `FRANCHISE`, `FRANCHISE TYPE 2`, `FRANCHISE TYPE 3`, `FRANCHISE OPERATOR`, `OTHER`, `ENDORSEMENT` | `201 Created` (pinned to `current_user.BranchId`) | `200 OK` (own branch) / `403 Forbidden` (other branch) | `201 Created` (own branch) / `403 Forbidden` (other branch) | `200 OK` (own branch) / `403 Forbidden` (other branch) | **Strict Own-Branch (`current_user.BranchId`)** |
| **Read-Only / Non-Underwriting Roles** | `AGENT`, `CASHIER`, `CLAIM`, `RELATIONSHIP MANAGER`, `ACCOUNT`, `ACCOUNT HEAD`, `pOLICY VIEW`, `QUOT CO-ORDINATOR`, etc. | `403 Forbidden` | `403 Forbidden` | `403 Forbidden` | `403 Forbidden` | Write Prohibited |
| **Soft-Deleted Roles** | `POLICY BAZAR`, `POLICY BAZAR AGENT` | `401 Unauthorized` | `401 Unauthorized` | `401 Unauthorized` | `401 Unauthorized` | Authentication Prohibited |

---

## 4. Customer & Vehicle Read / Search Authorization Matrix (`GAP-5F-09`)

| Endpoint | Method | Query Parameters | Global Read Roles (`OWNER`, `ADMIN`, `IT SUPPORT`, `ACCOUNT`, `ACCOUNT HEAD`) | Non-Global Active Roles (`OPERATOR`, `AGENT`, `CASHIER`, `CLAIM`, `RELATIONSHIP MANAGER`, `FRANCHISE`, etc.) | Soft-Delete Handling |
|---|---|---|---|---|---|
| `/api/v1/customers/{customer_id}` | `GET` | Path: `customer_id` | `200 OK` for any active customer across all branches | `200 OK` if `customer.BranchId == current_user.BranchId`; `403 Forbidden` if cross-branch | `404 Not Found` if `isdeleted == '1'` |
| `/api/v1/customers` | `GET` | `name`/`search`, `mobile`, `pan`, `customer_code`, `branch_id`, `offset` (`>=0`), `limit` (`1..100`, default `20`) | Can filter across all branches or pass `branch_id` | Automatically pinned to `current_user.BranchId` (ignores cross-branch `branch_id`) | Excludes `isdeleted == '1'` |
| `/api/v1/customers/{customer_id}/vehicles` | `GET` | `offset` (`>=0`), `limit` (`1..100`, default `100`) | `200 OK` for any active customer across all branches | `200 OK` if `customer.BranchId == current_user.BranchId`; `403 Forbidden` if cross-branch | `404` if customer deleted; excludes vehicles with `isdeleted == '1'` |
| `/api/v1/vehicles` | `GET` | `registration_no`/`reg_no`, `financial_year`, `branch_id`, `offset` (`>=0`), `limit` (`1..100`, default `20`) | Can search across all branches or filter by `branch_id`; returns multiple rows across `FinancialYear` if `financial_year` is omitted | Automatically restricted to `current_user.BranchId`; returns multiple rows across `FinancialYear` within own branch | Excludes `isdeleted == '1'` |

---

## 5. Principal Context Resolution (`GAP-5F-03`)

[`resolve_principal_context`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/app/core/rbac.py#L249-L350) attaches server-verified principal identifiers to `User` and `PrincipalContext` during `AuthService.login` and `get_current_user`:

- **Base Fields (All Authenticated Users)**:
  - `user_id` (`tbl_user.UserId`)
  - `role_id` (`tbl_user.UserRoleId`)
  - `role_name` (`tbl_userrole.UserRole`)
  - `branch_id` (`tbl_user.BranchId`)
- **Role-Specific Principal Fields**:
  - **Agent Roles (`AGENT`, `FRANCHISE AGENT`, `Broker partner`)**: Resolves `agent_id` from `tbl_user.partner_user_id` (with fallback to `tbl_cutnpaycommpayable.AgentId` / `tbl_transactionappnew.AgentId`).
  - **Employee / Executive Roles (`RELATIONSHIP MANAGER`, `LOCATION HEAD`, `SALES`, etc.)**: Resolves `emp_id` and `employee_id` from `tbl_user.partner_user_id` (with fallback to `tbl_cutnpaycommpayable.SalesExecutiveId` / `tbl_transactionappnew.SalesExecutiveId`).
  - **Franchise Roles (`FRANCHISE`, `FRANCHISE TYPE 2`, `FRANCHISE TYPE 3`, `FRANCHISE OPERATOR`)**: Resolves `franchise_id` from `tbl_user.partner_user_id` (with fallback to `tbl_cutnpaycommpayable.FranchaiseId` / `tbl_transactionappnew.FranchaiseId`).
  - **Non-Partner Roles (`OPERATOR`, `ADMIN`, `OWNER`, etc.)**: Keeps `agent_id = None`, `emp_id = None`, `employee_id = None`, `franchise_id = None`.
- **Zero Client Trust**: Client headers (`X-Agent-Id`, `X-Branch-Id`, etc.), query parameters, and request bodies are never trusted to populate principal context.


---

## 6. Endpoint Contract Summary

| Method | Path | Auth & RBAC Dependency | Description |
|---|---|---|---|
| `GET` | `/api/v1/customers` | `Depends(require_roles(*CUSTOMER_VEHICLE_READ_ROLES))` | Search and list active customers (`name`/`search`, `mobile`, `pan`, `customer_code`, `branch_id`, `offset`, `limit<=100`). Non-global roles pinned to `current_user.BranchId`. |
| `GET` | `/api/v1/customers/{customer_id}` | `Depends(require_roles(*CUSTOMER_VEHICLE_READ_ROLES))` | Retrieve active customer by `CustomerId` (`404` if missing or soft-deleted, `403` if outside caller's branch for non-global roles). |
| `POST` | `/api/v1/customers` | `Depends(require_roles(*CUSTOMER_VEHICLE_WRITE_ROLES))` | Create customer (`201 Created`). Unauthorized roles (`AGENT`, `CASHIER`, `CLAIM`, `RELATIONSHIP MANAGER`, `ACCOUNT`, etc.) receive `403 Forbidden`. |
| `PUT` | `/api/v1/customers/{customer_id}` | `Depends(require_roles(*CUSTOMER_VEHICLE_WRITE_ROLES))` | Update customer (`200 OK`). Enforces write role membership and branch jurisdiction (`403 Forbidden`). |
| `GET` | `/api/v1/customers/{customer_id}/vehicles` | `Depends(require_roles(*CUSTOMER_VEHICLE_READ_ROLES))` | List active vehicles belonging to `customer_id` (`200 OK`, `403` cross-branch for non-global roles, `404` if customer missing/deleted). |
| `POST` | `/api/v1/customers/{customer_id}/vehicles` | `Depends(require_roles(*CUSTOMER_VEHICLE_WRITE_ROLES))` | Register vehicle asset under `customer_id` (`201 Created`). Enforces write role membership, customer branch scope, and FY registration uniqueness. |
| `PUT` | `/api/v1/customers/{customer_id}/vehicles/{vehicle_id}` | `Depends(require_roles(*CUSTOMER_VEHICLE_WRITE_ROLES))` | Update vehicle asset (`200 OK`). Enforces write role membership, customer ownership, branch scope, and FY registration uniqueness. |
| `GET` | `/api/v1/vehicles` | `Depends(require_roles(*CUSTOMER_VEHICLE_READ_ROLES))` | Search active vehicles by `registration_no`/`reg_no`, `financial_year`, `branch_id`, `offset`, `limit<=100`. Preserves multi-row return across distinct `FinancialYear` values. |
| `GET` | `/api/v1/auth/me` | `Depends(get_current_user)` | Returns authenticated `UserRead` profile including `role`, `branch_id`, `agent_id`, `emp_id`, `employee_id`, `franchise_id`. Rejects soft-deleted roles (`401`). |
| `GET` | `/api/v1/auth/admin-check` | `Depends(require_roles(*GLOBAL_ADMIN_ROLES))` | Verifies global administrative role (`OWNER`, `ADMIN`, `IT SUPPORT`). Rejects `SUPERADMIN` (`403`). |

---

## 7. Test Matrix & Verification Results

| Test Suite | Test File | Scenarios Covered | Result |
|---|---|---|---|
| **Phase 5G RBAC Unit Tests** | `tests/unit/test_phase5g_rbac.py` | 5 unit tests: 56-role catalog verification, `SUPERADMIN` exclusion, `GLOBAL_ADMIN_ROLES` / `GLOBAL_READ_ROLES`, `BranchId in (0, None)` non-admin verification in `CustomerService` & `VehicleService`, `CUSTOMER_VEHICLE_WRITE_ROLES` / `READ_ROLES`, server-side `resolve_principal_context` (`agent_id`, `emp_id`, `franchise_id`). | **5 / 5 PASSED** |
| **Phase 5G Auth & Read/Search Integration Tests** | `tests/integration/test_phase5g_customer_vehicle_auth_and_read.py` | 20 integration tests (including parametrized role checks across `AGENT`, `CASHIER`, `CLAIM`, `RELATIONSHIP MANAGER`, `ACCOUNT`): `SUPERADMIN` rejection, `BranchId=0/None` non-admin enforcement, `OWNER`/`ADMIN`/`IT SUPPORT` cross-branch admin, soft-deleted role (`POLICY BAZAR`, `POLICY BAZAR AGENT`) `401` rejection on login & token auth, Customer & Vehicle write role enforcement (`403`), Customer & Vehicle read/search with branch scoping, multi-FY registration search, soft-delete exclusion, and `/api/v1/auth/me` principal resolution. | **20 / 20 PASSED** |
| **Regression Baseline (Phases 1–5E)** | `tests/unit/*`, `tests/integration/*` | All 107 existing unit and integration tests. | **107 / 107 PASSED** |
| **Total Test Suite** | All tests (`pytest -q`) | **132 automated tests** | **132 / 132 PASSED (100%)** |
