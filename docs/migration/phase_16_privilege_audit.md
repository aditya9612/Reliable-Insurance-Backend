# PHASE 16 — DYNAMIC PRIVILEGE & ROLE PERMISSION AUDIT
## Reliable-Insurance-Backend: Legacy Menu-Level Visibility vs Modern Server-Side RBAC Hardening

---

### 1. Executive Summary & Core Security Distinction
The legacy ASP.NET WebForms system (`InsurancefinalNew`) featured an administrative privilege configuration module:
- `Clerk/Adm_RolePrivilege.aspx.cs` (Role-to-Screen mapping)
- `Clerk/adm_UserRights.aspx.cs` (Action-level flags: `View`, `Add`, `Edit`, `Delete`)
- Database tables: `tbl_role_privilege` and `tbluserrights`

#### Critical Architectural & Forensic Finding:
1. **Legacy Enforcement Was UI-Only**:
   - In legacy C#, `tbl_role_privilege` and `tbluserrights` **exclusively controlled the visibility of menu hyperlinks** rendered in `Clerk/Clerk.Master.cs` (`LoadMenuByRole`).
   - If a user directly typed an `.aspx` URL into their web browser (Forced Browsing / CWE-425) or called an ASMX WebMethod (`Service.asmx.cs` / CWE-306), the legacy backend **executed the operation without verifying `tbl_role_privilege`**!
   - Zero WebMethods checked `tbluserrights` or `tbl_role_privilege`.
2. **Modern FastAPI Architecture (Zero-Trust Server-Side RBAC)**:
   - Modern FastAPI endpoints do **not** rely on frontend menu states for security.
   - Every single endpoint is protected by declarative dependency injection (`require_roles(...)` and `resolve_principal_context`), verifying cryptographic JWT claims and executing tenant isolation checks.
   - Dynamic menu privileges in Phase 16 serve **exclusively as a frontend navigational presentation schema** (allowing the Admin SPA/portal to tailor its sidebar menu tree dynamically per role and branch), while backend security remains anchored in server-side role dependencies.

---

### 2. Forensic Analysis of Legacy Privilege Tables & Procedures

#### 2.1 Table Schema: `tbl_role_privilege`
- **Columns**:
  - `Id`: `int(11) NOT NULL AUTO_INCREMENT` (PK)
  - `BranchId`: `int(11) NOT NULL` (Branch context where privilege applies)
  - `RoleId`: `int(11) NOT NULL` (Role pointer to `tbl_userrole.UserRoleId`)
  - `ScreenId`: `int(11) NOT NULL` (Screen ID pointer to `tbl_menu.MenuId`)
  - `CreateDate`: `datetime NULL`
  - `isdeleted`: `varchar(10) NOT NULL DEFAULT '0'`
- **Indexes**: `ix_BranchId_RoleId`, `ix_ScreenId`.
- **Stored Procedures**:
  - `sp_insert_role_privilege(P_BranchId, P_ROLE_ID, P_SCREEN_ID)`: Inserts a single role-to-screen entitlement.
  - `sp_delete_role_privilege(P_BranchId, P_ROLE_ID)`: Wipes all entitlements for a given role and branch before bulk re-insertion.

#### 2.2 Table Schema: `tbluserrights` / `tbl_userrights`
- **Columns**:
  - `UserRightsId`: `int(11) NOT NULL AUTO_INCREMENT` (PK)
  - `UserId` / `UserRoleId`: `int(11) NOT NULL`
  - `MenuId`: `int(11) NOT NULL`
  - `IsView`: `varchar(5) NOT NULL DEFAULT '0'`
  - `IsAdd`: `varchar(5) NOT NULL DEFAULT '0'`
  - `IsEdit`: `varchar(5) NOT NULL DEFAULT '0'`
  - `IsDelete`: `varchar(5) NOT NULL DEFAULT '0'`
  - `isdeleted`: `varchar(10) NOT NULL DEFAULT '0'`
- **Stored Procedures**:
  - `sp_SelectUserRightsByRoleId(P_UserRoleId)`: Reads action-level flags.
  - `sp_UpdateUserRights(P_UserRoleId, P_MenuId, P_IsView, P_IsAdd, P_IsEdit, P_IsDelete)`: Updates action flags.

#### 2.3 Table Schema: `tbl_menu` / `tbl_menumaster`
- **Columns**:
  - `MenuId`: `int(11) NOT NULL AUTO_INCREMENT` (PK)
  - `MenuName`: `varchar(100) NOT NULL` (Display label)
  - `MenuUrl`: `varchar(255) NULL` (Legacy relative page path, e.g. `~/Clerk/PE_TransactionEntry.aspx`)
  - `ParentMenuId`: `int(11) NULL DEFAULT 0` (Top-level menu parent pointer)
  - `OrderNo`: `int(11) NULL DEFAULT 0` (Display sequence order)
  - `IconClass`: `varchar(50) NULL` (FontAwesome / CSS icon class)
  - `isdeleted`: `varchar(10) NOT NULL DEFAULT '0'`

---

### 3. Classification of Privilege Mechanisms

| Dimension | Legacy WebForms Behavior | Target FastAPI Implementation | Security Classification | Rationale |
|---|---|---|:---:|---|
| **Enforcement Layer** | Client-Side / UI Only (hides links in master page navigation) | Server-Side HTTP Middleware (`require_roles` on ASGI route) | **SECURITY HARDENING** | Eliminates OWASP A01 (Broken Access Control) and forced browsing attacks. |
| **Granularity** | Screen visibility (`tbl_role_privilege`) + Action checkboxes (`tbluserrights`) | Declarative Route Dependencies + HTTP verbs (GET=Read, POST=Create, PUT=Update, DELETE=Delete) | **SECURITY HARDENING** | Standard REST semantics map directly to CRUD action flags with compile-time type safety. |
| **Dynamic Configuration** | Checkbox grid on `Adm_RolePrivilege.aspx.cs` overwriting rows in `tbl_role_privilege` | Admin REST endpoints (`GET/POST/DELETE /api/v1/admin/privileges`) returning UI navigation trees | **LEGACY PARITY** | Retains administrator ability to customize menu trees per role for frontend SPAs. |
| **API Parameter Trust** | Trusted client-supplied `UserId`, `AgentId`, `BranchId` parameters | Token Claims Injection (`current_user.UserId`, `current_user.BranchId`) | **LEGACY DEFECT MITIGATED** | Legacy defect `DEF-003` / IDOR vulnerability completely prevented. |
| **Screen Catalog Metadata** | Hardcoded `.aspx` hyperlinks in WebForms master file | Structured JSON Menu Tree with routes, labels, icons, and categories | **SECURITY HARDENING** | Modernizes legacy URL paths to clean REST/SPA route paths. |

---

### 4. Target Phase 16B Architecture for Dynamic Privileges

```
+-----------------------------------------------------------------------------------+
|                        MODERN DYNAMIC PRIVILEGE ARCHITECTURE                      |
+-----------------------------------------------------------------------------------+

   [ Admin User ]                                         [ Standard User ]
         |                                                       |
         v                                                       v
  GET /api/v1/admin/privileges                           GET /api/v1/auth/me
  POST /api/v1/admin/privileges                         (Includes accessible
  (Manage Role -> Screen Trees)                           menu tree in response)
         |                                                       |
         v                                                       v
  +---------------------------+                         +---------------------------+
  |  `RolePrivilege` Model    |                         |  Frontend SPA Sidebar     |
  |  `tbl_role_privilege`     |                         |  Renders customized menu  |
  +---------------------------+                         +---------------------------+
                                                                 |
                                                                 v
                                                        HTTP Request (e.g. POST /policies)
                                                                 |
                                                                 v
                                                        +---------------------------+
                                                        |  Server-Side Security Gate|
                                                        |  `require_roles(...)`     |
                                                        |  `resolve_principal(...)` |
                                                        +---------------------------+
                                                                 |
                                                                 +---> Authorize & Execute
```

### 5. Parity & Security Invariant
- **Rule**: No endpoint may rely on `tbl_role_privilege` to make an authorization decision.
- **Enforcement**: Authorization decisions must always be made by `require_roles(...)` and `resolve_principal_context`. `tbl_role_privilege` is strictly consumed for UI menu hierarchy rendering.
