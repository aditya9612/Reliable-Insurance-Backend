# Phase 10 — Role, Branch & Principal Access Matrix (`phase_10_access_matrix.md`)

## 1. Overview
This document specifies the canonical Role-Based Access Control (RBAC), Branch Isolation (`BranchId`), and Principal Ownership (`AgentId`, `FranchiseId`, `SalesExId`) enforcement matrix for Phase 10 Claims, Endorsements, and Refunds, aligned with Phase 5F (`phase_5f_role_api_table_access_matrix.md` Module H & Module D).

---

## 2. Canonical Role Sets in `app/core/rbac.py`

| Role Set Constant | Permitted Canonical Roles | Operations Governed |
|---|---|---|
| `CLAIM_CREATE_ROLES` | `Admin`, `Managing Director`, `Director`, `VP`, `General Manager`, `HO`, `Manager`, `Assistant Manager`, `Operations`, `Claims Officer`, `Clerk`, `Operator`, `Employee`, `Agent`, `Franchise`, `Sales Ex`, `Telecaller` | `POST /api/v1/claims` (intimate claim), `POST /api/v1/claims/{id}/documents` (attach claim document) |
| `CLAIM_READ_ROLES` | `Admin`, `Managing Director`, `Director`, `VP`, `General Manager`, `HO`, `Manager`, `Assistant Manager`, `Operations`, `Claims Officer`, `Accounts`, `Clerk`, `Operator`, `Employee`, `Agent`, `Franchise`, `Sales Ex`, `Telecaller` | `GET /api/v1/claims`, `GET /api/v1/claims/{id}`, `GET /api/v1/claims/{id}/documents` |
| `CLAIM_UPDATE_ROLES` | `Admin`, `Managing Director`, `Director`, `VP`, `General Manager`, `HO`, `Manager`, `Assistant Manager`, `Operations`, `Claims Officer`, `Clerk`, `Operator` | `POST /api/v1/claims/{id}/register`, `POST /api/v1/claims/{id}/survey`, `POST /api/v1/claims/{id}/assess`, `POST /api/v1/claims/{id}/cancel` |
| `CLAIM_APPROVE_SETTLE_ROLES` | `Admin`, `Managing Director`, `Director`, `VP`, `General Manager`, `HO`, `Manager`, `Accounts` | `POST /api/v1/claims/{id}/approve`, `POST /api/v1/claims/{id}/settle`, `POST /api/v1/claims/{id}/close`, `POST /api/v1/claims/{id}/reject`, `POST /api/v1/claims/{id}/reopen`, `POST /api/v1/claims/{id}/reverse-settlement` |
| `ENDORSEMENT_CREATE_ROLES` | `Admin`, `Managing Director`, `Director`, `VP`, `General Manager`, `HO`, `Manager`, `Assistant Manager`, `Operations`, `Underwriter`, `Clerk`, `Operator`, `Employee`, `Agent`, `Franchise`, `Sales Ex` | `POST /api/v1/endorsements`, `POST /api/v1/endorsements/preview`, `POST /api/v1/endorsements/{id}/submit`, `POST /api/v1/endorsements/{id}/cancel` |
| `ENDORSEMENT_READ_ROLES` | `Admin`, `Managing Director`, `Director`, `VP`, `General Manager`, `HO`, `Manager`, `Assistant Manager`, `Operations`, `Underwriter`, `Accounts`, `Clerk`, `Operator`, `Employee`, `Agent`, `Franchise`, `Sales Ex`, `Telecaller` | `GET /api/v1/endorsements`, `GET /api/v1/endorsements/{id}` |
| `ENDORSEMENT_APPROVE_APPLY_ROLES` | `Admin`, `Managing Director`, `Director`, `VP`, `General Manager`, `HO`, `Manager`, `Underwriter`, `Operations` | `POST /api/v1/endorsements/{id}/approve`, `POST /api/v1/endorsements/{id}/apply`, `POST /api/v1/endorsements/{id}/reject`, `POST /api/v1/endorsements/{id}/reverse` |
| `REFUND_APPROVE_WRITE_ROLES` | `Admin`, `Managing Director`, `Director`, `VP`, `General Manager`, `HO`, `Manager`, `Accounts` | `POST /api/v1/refunds/{endorsement_id}/approve`, `POST /api/v1/refunds/{endorsement_id}/disburse`, `POST /api/v1/refunds/{endorsement_id}/reverse`, `GET /api/v1/refunds` |

---

## 3. Branch & Principal Ownership Scoping Rules

| Role Category | Branch Scope (`BranchId`) | Principal Ownership Scope | Forbidden Actions (`403 Forbidden`) |
|---|---|---|---|
| **Unrestricted Global Roles** (`Admin`, `Managing Director`, `Director`, `VP`, `General Manager`, `HO`, `Accounts`) | All branches | All principals | None (full cross-branch oversight) |
| **Branch-Scoped Back-Office Roles** (`Manager`, `Assistant Manager`, `Operations`, `Claims Officer`, `Underwriter`, `Clerk`, `Operator`, `Employee`, `Telecaller`) | Restricted to `current_user.branch_id` | All principals within `current_user.branch_id` | Accessing or mutating claims/endorsements belonging to another branch (`BranchId != current_user.branch_id`) returns `403 Forbidden`. |
| **Agent (`Agent`)** | Own branch | `policy.AgentId == current_user.user_id` | Cannot intimate claims, view claims, or submit endorsements for another agent's policy (`403 Forbidden`). Cannot approve/settle claims, approve/apply endorsements, or approve/disburse refunds (`403 Forbidden`). |
| **Franchise (`Franchise`)** | Own branch | `policy.FranchiseCode == str(current_user.user_id)` or `FranchiseId == current_user.user_id` | Cannot access another franchise's policies/claims/endorsements (`403 Forbidden`). Cannot approve/settle/apply/disburse (`403 Forbidden`). |
| **Sales Executive (`Sales Ex`)** | Own branch | `policy.SalesExId == current_user.user_id` | Cannot access another Sales Ex's policies/claims/endorsements (`403 Forbidden`). Cannot approve/settle/apply/disburse (`403 Forbidden`). |
| **HR (`HR`) / Unrelated Roles** | N/A | N/A | Denied access (`403 Forbidden`) to all Phase 10 Claims, Endorsements, and Refund endpoints. |
