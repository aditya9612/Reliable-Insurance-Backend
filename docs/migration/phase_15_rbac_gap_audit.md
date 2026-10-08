# PHASE 15 — RBAC & AUTHORIZATION GAP AUDIT
## Reliable-Insurance-Backend: Post-Phase 14 Security, Roles & Ownership Reconciliation

---

### 1. Executive Summary
- **Legacy Security Flaws**:
  - Legacy `Service.asmx` and `VehicleService.asmx` were 100% unauthenticated (`DEF-001`).
  - WebForms pages relied on client-side menu hiding (`Clerk.Master.cs`) with zero server-side authorization guards on URLs (`DEF-004`).
  - Passwords were stored in plaintext (`DEF-005`).
- **FastAPI Modern Hardening**:
  - OAuth2 Password Bearer flow + JWT tokens with Passlib bcrypt hashing and transparent legacy upgrade.
  - All 56 legacy user roles cataloged in `app/core/rbac.py`.
  - Server-side multi-tenant row-scoping enforced across Customers, Vehicles, Quotations, Policies, Payments, Commissions, Claims, Endorsements, Documents, and Reports.
  - Malicious query parameter tampering (`?branch_id=999`, `?agent_id=999`) is strictly overridden by authenticated JWT token context.
  - 12 sensitive internal profit/commission fields dynamically masked for non-finance users.
- **Remaining Post-Phase 14 Authorization Gaps**: **1 administrative utility gap** (Dynamic Menu Privilege CRUD API).

---

### 2. Canonical 56-Role Hierarchy & FastAPI Mapping

| Category | Canonical Roles in `app/core/rbac.py` | Scope & Enforcement | Current FastAPI Status |
|---|---|---|:---:|
| **Global Admin** | `OWNER`, `ADMIN`, `IT SUPPORT` | Unrestricted cross-branch visibility; full financial & export authority | **100% ENFORCED** |
| **Finance & Accounts**| `ACCOUNT`, `ACCOUNT HEAD`, `CASHIER` | Company-wide accounting, voucher creation, ledger inspection, export authority | **100% ENFORCED** |
| **Branch Management** | `LOCATION HEAD`, `OPERATOR`, `SUBADMIN`, `CLERK` | Strictly scoped to caller's `branch_id`; zero cross-branch leakage | **100% ENFORCED** |
| **Agent / POSP** | `AGENT`, `POSP`, `SUB_AGENT` | Strictly scoped to caller's `agent_id`; sensitive profit columns masked | **100% ENFORCED** |
| **Franchise** | `FRANCHISE`, `FRANCHISE_USER` | Strictly scoped to caller's `franchise_id`; wallet & commission restricted | **100% ENFORCED** |
| **Telecaller / Sales** | `TELECALLER`, `SALES EXECUTIVE` | Strictly scoped to caller's `emp_id` / assigned renewal queues | **100% ENFORCED** |
| **Claims & Survey** | `CLAIM HANDLER`, `SURVEYOR` | Scoped to assigned claims; survey reports and loss assessments | **100% ENFORCED** |
| **Customer** | `CUSTOMER` | Strictly scoped to caller's `customer_id`; own policies and vehicles | **100% ENFORCED** |

---

### 3. Detailed Audit of Remaining RBAC Capabilities

#### 3.1 Dynamic Role Menu Privileges (`tbl_role_privilege`)
- **Legacy Behavior**: `Adm_RolePrivilege.aspx.cs` rendered a checkbox grid allowing administrators to toggle visibility of WebForms navigation menu items for each role. Saved state to `tbl_role_privilege`.
- **FastAPI Status**: In FastAPI, backend API security is implemented declaratively via code-level dependencies (`require_roles(...)`), rendering runtime database-driven authorization redundant and unsafe.
- **Remaining Need**: Frontend client applications (React / Angular / Mobile) may still benefit from an API endpoint (`GET /api/v1/utilities/roles/{role_id}/menu-permissions`) to dynamically construct UI navigation sidebars based on assigned privileges.
- **Priority**: **P3 (Candidate B - Admin & Profile Management)**.

#### 3.2 User Login History & Audit Trail (`tbl_loginhistory`)
- **Legacy Behavior**: `Log_In.aspx.cs` inserted a row into `tbl_loginhistory` recording user login timestamp, IP address, and browser agent string.
- **FastAPI Status**: `AuthService` currently performs token issuance and structured logging, but does not write persistent records to `tbl_loginhistory`.
- **Target Design**: Add `LoginHistory` model and record persistent login audit events on successful `/api/v1/auth/login`.
- **Priority**: **P3 (Candidate B - Admin & Profile Management)**.
