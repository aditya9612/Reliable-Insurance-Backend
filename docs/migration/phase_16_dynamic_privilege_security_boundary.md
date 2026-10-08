# PHASE 16 — DYNAMIC PRIVILEGE VS BACKEND AUTHORIZATION BOUNDARY
## Reliable-Insurance-Backend: UI Navigation Entitlements vs Zero-Trust Server-Side RBAC

---

### 1. Executive Summary & Problem Statement
In the legacy ASP.NET WebForms system (`InsurancefinalNew`), user rights and privileges were managed via:
- Database tables: `tbl_role_privilege`, `tbluserrights`, `tbl_menu`
- Management screens: `Clerk/Adm_RolePrivilege.aspx.cs`, `Clerk/adm_UserRights.aspx.cs`
- Navigation renderer: `Clerk/Clerk.Master.cs` (`LoadMenuByRole`)

#### The Legacy Architectural Vulnerability:
In legacy C#, the privilege system **only controlled UI menu visibility**. It conditionally hid HTML `<a href="...">` anchor tags in the sidebar or top navigation bar. However:
1. If an unauthorized user navigated directly to a page URL (e.g. `~/Clerk/PE_TransactionEntry.aspx` or `~/Clerk/adm_UpdateCustomer.aspx`), the page executed without checking `tbl_role_privilege` (Forced Browsing / CWE-425).
2. The 339 ASMX WebMethods in `Service.asmx.cs` had **zero** session or menu privilege checks, trusting arbitrary client-supplied IDs (Broken Object Level Authorization / CWE-284).
3. The legacy model conflated *navigation visibility* with *security authorization*.

---

### 2. Modern FastAPI Architectural Boundary

In `Reliable-Insurance-Backend`, dynamic menu privileges and backend authorization are decoupled into two completely separate, non-overlapping concerns:

```
+--------------------------------------------------------------------------------------------------+
|                                    MODERN ARCHITECTURAL BOUNDARY                                 |
+--------------------------------------------------------------------------------------------------+

  CONCERN 1: DYNAMIC PRIVILEGE (PRESENTATION LAYER)
  ------------------------------------------------
    tbl_role_privilege + tbl_menu
              ↓
    Role / Branch Navigation Query (`GET /api/v1/admin/privileges/{role_id}`)
              ↓
    Returns JSON Menu Tree (Route Paths, Display Labels, Icons, Category Groups)
              ↓
    Frontend SPA Sidebar / Navigation Bar (Renders tailored UI menus for the user)
    * Classification: LEGACY BEHAVIOR (Tailors UX without providing security guarantees)


  CONCERN 2: BACKEND RBAC (SECURITY ENFORCEMENT LAYER)
  ----------------------------------------------------
    HTTP Request with Authorization: Bearer <JWT>
              ↓
    `get_current_token_payload` (Cryptographic JWT Signature Verification)
              ↓
    `get_current_user` (Active User `isdeleted!='1'` + Active Role `isdeleted!='1'`)
              ↓
    `resolve_principal_context` (Server-Side DB Resolution of AgentId, EmpId, FranchiseId, BranchId)
              ↓
    `require_roles(*allowed_roles)` (FastAPI Route Dependency Enforcement)
              ↓
    Repository Data Filters (`where(Model.BranchId == principal.branch_id)`)
    * Classification: SECURITY HARDENING (Zero-Trust, Server-Side Authoritative Gate)
```

---

### 3. Absolute Security Invariants Verified in Code

Forensic inspection of [`app/core/dependencies.py`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/app/core/dependencies.py) and [`app/core/rbac.py`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/app/core/rbac.py) confirms the following four non-negotiable invariants:

#### Invariant 1: Dynamic menu privileges NEVER bypass backend authorization
Even if an administrator grants all 250 screens in `tbl_role_privilege` to role `OPERATOR`, that user **cannot** execute financial recalculations, voucher postings, or global exports. Every sensitive route is independently defended by `require_roles("OWNER", "ADMIN", "ACCOUNT")`.

#### Invariant 2: Removing a menu privilege does NOT become the only security mechanism
Revoking a screen ID from `tbl_role_privilege` merely instructs the frontend UI not to render that menu item. The backend does not rely on frontend menu omission to protect endpoints; backend route dependencies reject unauthorized requests regardless of UI state.

#### Invariant 3: Granting a menu privilege does NOT automatically grant API access
Menu entitlements stored in `tbl_role_privilege` are purely navigational metadata. Adding an entry to `tbl_role_privilege` does not modify the declarative Python `require_roles(...)` decorator on the underlying FastAPI endpoint.

#### Invariant 4: Client-supplied role/menu/privilege values cannot elevate authorization
The modern system rejects client-supplied roles, branch IDs, or user IDs. `get_current_user` derives identity strictly from the signed JWT subject, re-verifies the user and role in the database, and loads server-side principal context (`PrincipalContext`). Client request payloads cannot forge authorization claims.

---

### 4. Classification & Parity Reconciliation

| Component | Architecture Level | Responsibility | Classification | Rationale |
|---|---|---|:---:|---|
| **Menu Privileges (`tbl_role_privilege`)** | Presentation / UI | Customizing sidebar navigation menus per role and branch | **LEGACY BEHAVIOR** | Preserves administrative capability to tailor frontend workflows for different user roles. |
| **Route Security (`require_roles`)** | Server-Side / ASGI | Declarative HTTP authorization on every incoming request | **SECURITY HARDENING** | Eliminates OWASP A01 (Broken Access Control) and CWE-425 (Forced Browsing). |
| **Principal Context (`resolve_principal_context`)** | Server-Side / DB | Resolving tenant, branch, and partner ownership boundaries | **SECURITY HARDENING** | Eliminates OWASP A01 / CWE-639 (Insecure Direct Object References). |
| **Password Hashing (Bcrypt)** | Data Storage | Salted cryptographic password storage (work factor 12) | **SECURITY HARDENING** | Eliminates legacy plaintext password storage defect (`DEF-002`). |

---

### 5. Implementation Mandate for Phase 16B
- **Endpoints to Expose**:
  - `GET /api/v1/admin/privileges/{role_id}`: Returns the hierarchical JSON menu tree for that role and branch to drive the frontend SPA navigation.
  - `POST /api/v1/admin/privileges`: Allows administrators to save customized menu items for a role.
  - `DELETE /api/v1/admin/privileges`: Clears role menu custom configurations.
- **Strict Boundary**: These endpoints interact **only** with `tbl_role_privilege` and `tbl_menu`. They **never** mutate role definitions in `app/core/rbac.py` or modify server-side route dependencies.
