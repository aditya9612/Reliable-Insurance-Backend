# PHASE 16 — RBAC & AUTHORIZATION GAP MATRIX
## Reliable-Insurance-Backend: Role Capabilities, Principal Scoping & Security Hardening

---

### 1. Architectural Scope & Canonical Roles
All access control mappings in Phase 16 utilize strictly verified legacy roles from `app/core/rbac.py` (`VERIFIED_ROLE_CATALOG`).
- **Global Administrative Roles**: `GLOBAL_ADMIN_ROLES = frozenset({"OWNER", "ADMIN", "IT SUPPORT"})`
- **Location / Branch Administrative Roles**: `LOCATION_ADMIN_ROLES = frozenset({"LOCATION HEAD", "MANAGER", "SUPERVISOR", "HOD", "GENERAL MANAGER"})`
- **Back-Office Operations Roles**: `BACKOFFICE_ROLES = frozenset({"OPERATOR", "OPERATOR HEAD", "BACK OFFICE", "ALL USER", "Freelancer"})`
- **Financial Roles**: `FINANCIAL_ROLES = frozenset({"ACCOUNT", "ACCOUNT HEAD", "CASHIER"})`
- **Partner Roles**: `PARTNER_ROLES = frozenset({"AGENT", "FRANCHISE", "FRANCHISE AGENT", "FRANCHISE SALES EXECUTIVE"})`
- **HR & Governance Roles**: `HR_ROLES = frozenset({"HR"})`

---

### 2. Comprehensive RBAC Gap Matrix

| # | Administrative / Profile Operation | Canonical Roles Permitted | Legacy Access Mechanism | Current FastAPI Access | Branch Scope | Agent Scope | Employee Scope | Franchise Scope | Owner / Global Scope | Security Hardening Applied | RBAC Gap Description |
|---|---|---|---|---|:---:|:---:|:---:|:---:|:---:|---|---|
| 1 | **Create User Account** | `OWNER (1)`, `ADMIN (2)`, `IT SUPPORT (28)` | Unprotected WebForm (`adm_UserMaster.aspx.cs`) checked only `Session["UserRole"]` | Target: `require_roles(*GLOBAL_ADMIN_ROLES)` | Global or assigned Branch | None | Can bind `EmpId` | Can bind `FranchiseId` | Full access across all tenants | Password hashed via Bcrypt (cost 12); prevents plaintext storage | User creation REST endpoint not yet exposed |
| 2 | **Update User Account** | `OWNER (1)`, `ADMIN (2)`, `IT SUPPORT (28)` | UI button click (`adm_UserMaster.aspx.cs`) | Target: `require_roles(*GLOBAL_ADMIN_ROLES)` | Global or assigned Branch | None | Can reassign `EmpId` | Can reassign `FranchiseId` | Full access across all tenants | Cannot escalate role above caller's privilege; audit log entry generated | User update REST endpoint not yet exposed |
| 3 | **Deactivate / Soft-Delete User** | `OWNER (1)`, `ADMIN (2)`, `IT SUPPORT (28)` | WebForm soft-delete toggle | Target: `require_roles(*GLOBAL_ADMIN_ROLES)` | Global or assigned Branch | None | None | None | Full access | Caller cannot deactivate their own active user account | User deactivation REST endpoint not yet exposed |
| 4 | **Reset / Change Password** | `OWNER (1)`, `ADMIN (2)` (Admin override) OR Any authenticated role (Self) | Unprotected WebForm (`ChangePassword.aspx.cs`) compared plaintext passwords | Self or Global Admin override | Self only for non-admin; Global for Admin | Self only | Self only | Self only | Full access | Requires old password verification for self; enforces password complexity | Password modification REST endpoint not yet exposed |
| 5 | **Assign / Revoke Menu Privileges** | `OWNER (1)`, `ADMIN (2)` | Unprotected WebForm (`Adm_RolePrivilege.aspx.cs`) | Target: `require_roles("OWNER", "ADMIN")` | Branch-scoped | None | None | None | Global | Restricted strictly to UI menu presentation; backend route security enforced via server-side dependencies | Dynamic menu privilege management endpoint missing |
| 6 | **View Login History Audit** | `OWNER (1)`, `ADMIN (2)`, `IT SUPPORT (28)`, `HR (26)` | Stored procedure (`sp_SelectLoginHistory`) | Target: `require_roles("OWNER", "ADMIN", "IT SUPPORT", "HR")` | Branch-scoped for HR; Global for Admin | Can filter by Agent's UserId | Can filter by Employee's UserId | Can filter by Franchise's UserId | Full access | Query parameter sanitization; IP address masking for unprivileged viewers | Login history query REST endpoint missing |
| 7 | **Employee Profile CRUD** | `OWNER`, `ADMIN`, `IT SUPPORT`, `HR`, `LOCATION HEAD` | `adm_EmployeeMaster.aspx.cs` | `/api/v1/employees` (`require_roles`) | Enforced to assigned `BranchId` unless Global Admin | None | Full staff management | None | Full access | PII masked for non-privileged roles (`PRIVILEGED_PII_ROLES`); branch isolation enforced | Fully migrated in Phase 15B |
| 8 | **Agent / POSP Profile CRUD** | `OWNER`, `ADMIN`, `IT SUPPORT`, `RELATIONSHIP MANAGER`, `LOCATION HEAD` | `mst_Agent.aspx.cs` | `/api/v1/agents` (`require_roles`) | Enforced to assigned `BranchId` unless Global Admin | Sales Executive can view assigned agents (`SalesExecutiveId = EmpId`) | None | Franchise can view linked agents (`FranchiseId`) | Full access | PII masked for non-privileged roles; branch isolation enforced | Fully migrated in Phase 15B |
| 9 | **Agent KYC State Transition** | `OWNER`, `ADMIN`, `IT SUPPORT`, `COMPLIANCE` | Admin checkbox on `mst_Agent.aspx.cs` | Target: `require_roles("OWNER", "ADMIN", "IT SUPPORT")` | Branch-scoped | None | None | None | Full access | Explicit verification state transitions with audit timestamp | KYC transition PATCH endpoint missing |
| 10 | **Franchise Profile CRUD** | `OWNER`, `ADMIN`, `IT SUPPORT` | `mst_Franchise.aspx.cs` | `/api/v1/franchises` (`require_roles`) | Enforced to assigned `BranchId` unless Global Admin | None | None | Franchise Owner can view own profile | Full access | PII masked for non-privileged roles; branch isolation enforced | Fully migrated in Phase 15B |
| 11 | **Reference Masters (Fuel/Financier/Surveyor)**| `OWNER`, `ADMIN`, `IT SUPPORT` (Write); All Authenticated (Read) | Legacy WebForms (`mst_FuelType.aspx.cs`, etc.) | Target: Read for all, Write for Global Admin | Global for Fuel; Branch-scoped for Financier & Surveyor | Read-only | Read-only | Read-only | Full write access | Prevents unauthorized modification of shared master reference data | Dedicated master lookup endpoints missing |
| 12 | **Admin System Counters** | `OWNER (1)`, `ADMIN (2)`, `IT SUPPORT (28)` | Legacy `Clerk/Index.aspx.cs` dashboard widgets | Target: `require_roles(*GLOBAL_ADMIN_ROLES)` | Branch-scoped or Global | Aggregated | Aggregated | Aggregated | Full visibility | Aggregate counts only; zero individual PII exposure | Dedicated admin security counters endpoint missing |

---

### 3. Critical Security Gaps & Modern Hardening Invariants

1. **Elimination of Broken Access Control (OWASP A01)**:
   - **Legacy Weakness**: The legacy application trusted client-supplied `UserId`, `AgentId`, and `BranchId` parameters across ASMX WebMethods, and used `tbl_role_privilege` exclusively to hide HTML navigation links in `Clerk.Master.cs`. Direct POST/GET requests bypassed all menu security.
   - **Modern Hardening**: Route protection is enforced unconditionally on every FastAPI request by FastAPI dependencies (`require_roles` and `get_current_user`), completely decoupling backend security from frontend navigation trees.
2. **Elimination of Plaintext Password Exposure (OWASP A02)**:
   - **Legacy Weakness**: Passwords were sent and stored in plaintext (`tbl_user.UserPassword`), making database leaks immediately catastrophic.
   - **Modern Hardening**: `AuthService` computes salted bcrypt hashes (cost factor 12) upon user creation and password changes, and performs automatic in-place hash upgrades during login.
3. **Prevention of Privilege Escalation (OWASP A01)**:
   - **Modern Hardening**: A caller with role `ADMIN` or `IT SUPPORT` cannot elevate any user account to `OWNER`, nor can any caller modify their own permissions or deactivate their own active account.
