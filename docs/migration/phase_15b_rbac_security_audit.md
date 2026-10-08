# PHASE 15B — RBAC & MULTI-TENANT SECURITY AUDIT
## Role-Based Access Control, Branch Scoping, and Principal Boundary Isolation

---

### 1. Executive Summary
Phase 15B enforces strict Role-Based Access Control (RBAC), multi-tenant branch scoping, principal context resolution, and PII masking across all newly implemented profiles, utility modules, and batch triggers.

All security checks leverage:
1. Canonical role definitions from the verified 56-role catalog (`tbl_userrole` / `app/core/rbac.py`).
2. `require_roles("OWNER", "ADMIN", "IT SUPPORT")` dependency injection on operational batch tasks.
3. Multi-tenant branch isolation via `BranchId` query filtering for non-global roles.
4. Server-resolved principal boundaries (`PrincipalContext`) ensuring agents and franchises can only access their authorized portfolio.
5. PII response serialization masking protecting sensitive identity documents (PAN, Aadhaar, Bank Account).

---

### 2. Canonical Role Taxonomy & Administrative Authority

From `app/core/rbac.py`:
- **Global Administrator Roles (`GLOBAL_ADMIN_ROLES`)**:
  - `OWNER` (Role ID 1)
  - `ADMIN` (Role ID 2)
  - `IT SUPPORT` (Role ID 28)
  - Full cross-branch read/write oversight, system configuration, and batch task execution authority.
- **HR Role**:
  - `HR` (Role ID 26): Staff profile management and unmasked PII view authority.
- **Branch Leadership**:
  - `MANAGER` (Role ID 8), `SUPERVISOR` (Role ID 3): Operational leadership strictly bound to `current_user.BranchId`.
- **Field & Partner Roles**:
  - `AGENT` (Role ID 4): POSP insurance agent bound to resolved `agent_id`.
  - `FRANCHISE` (Role ID 9): Franchise partner entity bound to resolved `franchise_id`.

*Note: Phantom role names such as "DIRECTOR" or "SUPERADMIN" do not exist in `tbl_userrole` and have been eliminated from all authorization checks.*

---

### 3. Detailed RBAC Matrix for Phase 15B Endpoints

| Resource Router | Route Path | HTTP Method | Authorized Roles | Tenant / Branch / Principal Isolation Rule |
|---|---|---|---|---|
| **Employees** | `/api/v1/employees` | `GET` | All authenticated staff | Non-admin filtered by `BranchId == user.BranchId`. PII masked for non-admin/HR. |
| **Employees** | `/api/v1/employees/{id}` | `GET` | All authenticated staff | Scoped to user's branch. PII masked for non-admin/HR. |
| **Employees** | `/api/v1/employees` | `POST` | `OWNER`, `ADMIN`, `IT SUPPORT`, `HR` | Admin/HR only. Assignable to branch. |
| **Employees** | `/api/v1/employees/{id}` | `PUT` | `OWNER`, `ADMIN`, `IT SUPPORT`, `HR` | Admin/HR only. |
| **Employees** | `/api/v1/employees/{id}` | `DELETE` | `OWNER`, `ADMIN`, `IT SUPPORT`, `HR` | Soft-deactivation (`isdeleted = '1'`). |
| **Agents** | `/api/v1/agents` | `GET` | Authenticated staff & agents | Filtered by `BranchId`. PII masked for non-admin/HR. |
| **Agents** | `/api/v1/agents/{id}` | `GET` | Authenticated staff & agents | Scoped to branch/principal. PII masked for non-admin/HR. |
| **Agents** | `/api/v1/agents` | `POST` | `OWNER`, `ADMIN`, `IT SUPPORT`, `HR`, `MANAGER` | Registered within caller's branch. |
| **Agents** | `/api/v1/agents/{id}` | `PUT` | `OWNER`, `ADMIN`, `IT SUPPORT`, `HR`, `MANAGER` | Mutation within authorized branch. |
| **Agents** | `/api/v1/agents/{id}` | `DELETE` | `OWNER`, `ADMIN`, `IT SUPPORT`, `HR` | Soft-deactivation (`isdeleted = '1'`). |
| **Franchises** | `/api/v1/franchises` | `GET` | Authenticated staff & franchises | Filtered by `BranchId`. PII masked for non-admin/HR. |
| **Franchises** | `/api/v1/franchises/{id}` | `GET` | Authenticated staff & franchises | Scoped to branch/principal. PII masked for non-admin/HR. |
| **Franchises** | `/api/v1/franchises` | `POST` | `OWNER`, `ADMIN`, `IT SUPPORT`, `MANAGER` | Created within branch scope. |
| **Franchises** | `/api/v1/franchises/{id}` | `PUT` | `OWNER`, `ADMIN`, `IT SUPPORT`, `MANAGER` | Mutation within branch scope. |
| **Franchises** | `/api/v1/franchises/{id}` | `DELETE` | `OWNER`, `ADMIN`, `IT SUPPORT` | Soft-deactivation. |
| **IDV Requests** | `/api/v1/idv-requests` | `POST` | All authenticated sales/agents | Agents can submit custom vehicle valuation proposals. |
| **IDV Requests** | `/api/v1/idv-requests` | `GET` | Authenticated staff & agents | Filtered by `BranchId` (cross-branch for global admins). |
| **IDV Requests** | `/api/v1/idv-requests/{id}` | `GET` | Authenticated staff & agents | Scoped to branch/request ownership. |
| **IDV Requests** | `/api/v1/idv-requests/{id}/approve` | `POST` | `OWNER`, `ADMIN`, `IT SUPPORT`, `QUOT CO-ORDINATOR`, `MANAGER` | Underwriters/Managers only (Agent strictly forbidden). |
| **IDV Requests** | `/api/v1/idv-requests/{id}/reject` | `POST` | `OWNER`, `ADMIN`, `IT SUPPORT`, `QUOT CO-ORDINATOR`, `MANAGER` | Underwriters/Managers only. |
| **Health Members** | `/api/v1/health-members` | `POST` | Authenticated policy creators | Associates family members to health policy. |
| **Health Members** | `/api/v1/health-members` | `GET` | Authenticated policy viewers | Scoped to policy transaction branch/agent. |
| **Health Members** | `/api/v1/health-members/{id}` | `GET` | Authenticated policy viewers | Scoped to policy transaction. |
| **Health Members** | `/api/v1/health-members/{id}` | `PUT` | Authenticated policy creators | Mutation prior to policy lock. |
| **Health Members** | `/api/v1/health-members/{id}` | `DELETE` | Authenticated policy creators | Soft delete. |
| **Bulk Imports** | `/api/v1/imports/policy-mis/upload` | `POST` | `OWNER`, `ADMIN`, `IT SUPPORT`, `MANAGER` | High-privilege CSV/Excel staging. |
| **Bulk Imports** | `/api/v1/imports/policy-mis/records` | `GET` | `OWNER`, `ADMIN`, `IT SUPPORT`, `MANAGER` | Review staged staging rows by `batch_id`. |
| **Bulk Imports** | `/api/v1/imports/policy-mis/process` | `POST` | `OWNER`, `ADMIN`, `IT SUPPORT`, `MANAGER` | Atomically commit staged batch. |
| **Batch Tasks** | `/api/v1/batch-tasks/overdue-cheque-lock/run` | `POST` | `OWNER`, `ADMIN`, `IT SUPPORT` | Global admin only via `require_roles`. LBR-069 account deactivation. |
| **Batch Tasks** | `/api/v1/batch-tasks/birthday-greetings/dispatch` | `POST` | `OWNER`, `ADMIN`, `IT SUPPORT` | Global admin only via `require_roles`. Notification dispatch. |
| **Batch Tasks** | `/api/v1/batch-tasks/wallet-locks/cleanup` | `POST` | `OWNER`, `ADMIN`, `IT SUPPORT` | Global admin only via `require_roles`. Redis distributed lock flush. |
| **Batch Tasks** | `/api/v1/batch-tasks/storage/ephemeral-cleanup` | `POST` | `OWNER`, `ADMIN`, `IT SUPPORT` | Global admin only via `require_roles`. Local export storage hygiene. |

---

### 4. Security Enforcement & Boundary Protections

1. **Unauthenticated Access (HTTP 401)**:
   - All Phase 15B endpoints require valid JWT Bearer tokens; unauthenticated calls are rejected with `401 Unauthorized`.
2. **Batch Tasks Role Barrier (HTTP 403)**:
   - Callers with non-administrative roles (`AGENT`, `MANAGER`, etc.) attempting to trigger batch tasks receive `403 Forbidden`.
3. **IDV Review Protection**:
   - POSP agents are explicitly forbidden from approving their own IDV overrides (`POST /idv-requests/{id}/approve`), preventing adverse selection and unauthorized vehicle valuations.
4. **PII Masking at Response Boundary**:
   - `PAN_No` / `PANNo`, `AadharNo`, and `accountNo` are masked at serialization time for non-privileged viewers.
   - Raw values in database and session are preserved.
