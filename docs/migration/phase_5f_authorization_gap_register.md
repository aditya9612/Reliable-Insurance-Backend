# Phase 5F — Legacy & FastAPI Authorization Gap Register

**Phase:** 5F — Role / API / Table / CRUD / Branch / Owner Access Audit  
**Mode:** STRICT READ-ONLY AUDIT  
**Date:** 2026-10-06  
**Status:** PARTIALLY REMEDIATED — `GAP-5F-01`, `GAP-5F-02`, `GAP-5F-03`, `GAP-5F-04`, `GAP-5F-09` CLOSED IN PHASE 5G

---

## 1. Gap Summary Matrix

| Gap ID | Domain / Component | Gap Title | Severity | Legacy Status | FastAPI Status | Target Remediation Phase |
|---|---|---|---|---|---|---|
| **GAP-5F-01** | FastAPI Customer & Vehicle APIs (`customers.py`) | Missing Role-Based Restriction (`require_roles`) on Customer & Vehicle Create/Update Endpoints | **HIGH** | Menu-restricted to Underwriting/Admin/Franchise roles | **CLOSED IN PHASE 5G** — `Depends(require_roles(*CUSTOMER_VEHICLE_WRITE_ROLES))` enforced on all 4 write endpoints | **CLOSED IN PHASE 5G** |
| **GAP-5F-02** | FastAPI Role Catalog & Admin Check (`customer.py`, `vehicle.py`, `auth.py`) | Incomplete Role Catalog (`43` Undocumented Roles) & Phantom `"SUPERADMIN"` Role in `_is_admin()` | **HIGH** | `tbl_userrole` has 56 roles (`IT SUPPORT=28`, `ALL USER=33`, etc.); no `SUPERADMIN` role exists | **CLOSED IN PHASE 5G** — 56-role catalog centralized in `app/core/rbac.py`; `SUPERADMIN` and `BranchId in (0, None)` admin checks removed | **CLOSED IN PHASE 5G** |
| **GAP-5F-03** | FastAPI Auth & JWT Context (`auth.py`, `security.py`) | Missing `AgentId`, `EmpId` (`SalesExecutiveId`), and `FranchaiseId` Principal Resolution in JWT / User Context | **HIGH** | Resolved at login via `Sp_CheckloginfrFranchaise`, `sp_CheckLoginForEmployee`, `sp_CheckLoginAppUser` | **CLOSED IN PHASE 5G** — `PrincipalContext` and `resolve_principal_context()` resolve `agent_id`, `emp_id`, `employee_id`, `franchise_id` server-side | **CLOSED IN PHASE 5G** |
| **GAP-5F-04** | FastAPI Auth Service (`auth.py`) | Missing `role_deleted` Check & Portal vs. Mobile (`isappuser`) Channel Separation | **MEDIUM** | `Log_In.aspx.cs` blocks `isappuser=1` from portal login; `RoleId 17, 18` have `role_deleted=1` with active users | **CLOSED IN PHASE 5G** — `AuthService.login` and `get_current_user` reject soft-deleted (`isdeleted=='1'`) or missing roles with `401 Unauthorized` | **CLOSED IN PHASE 5G** |
| **GAP-5F-05** | Legacy Mobile API (`Service.asmx.cs`) | 287 `[WebMethod]` Endpoints Completely Unauthenticated & Vulnerable to Parameter Tampering / IDOR | **CRITICAL** | Zero session/token checks across all 287 `[WebMethod]` endpoints | Must enforce `Depends(get_current_user)` + strict owner scoping on all future mobile endpoints | Phase 15 |
| **GAP-5F-06** | Legacy WebForms (`Clerk/*.aspx.cs`) | UI Menu Hiding (`tbl_role_privilege`) Without Server-Side Page/URL Role Authorization | **CRITICAL** | `Clerk.Master.cs` hides menu items, but any authenticated user can browse directly to any `Clerk/*.aspx` URL (`60` pages lack even a session check) | Must enforce explicit `Depends(require_roles(...))` on every FastAPI router/endpoint | Phase 5G onwards |
| **GAP-5F-07** | Legacy File Handlers (`ImageHandler.ashx.cs`, `DownloadAll.ashx.cs`, `Service.asmx::UploadFile`) | Unauthenticated Arbitrary File Upload, Path Traversal File Read, and Unscoped Document Download | **CRITICAL** | `ImageHandler.ashx` reads arbitrary disk paths; `UploadFile` writes arbitrary files to `~/AppPolicyPDF/`; `DownloadAll.ashx` streams ZIPs without auth | Never replicate raw path handlers; require JWT auth + branch/owner verification in Phase 11 | Phase 11 |
| **GAP-5F-08** | Legacy `AppLogin.aspx.cs` & API Keys | Hardcoded Backdoor Admin Credential (`AppLogin.aspx.cs:40`) & Hardcoded Third-Party Bearer Tokens | **CRITICAL** | Hardcoded admin login in `AppLogin.aspx.cs:40` and third-party tokens in `PE_TransactionEntry.aspx.cs` / `Service.asmx.cs` | Eliminated in FastAPI; all secrets managed via environment variables (`app/core/config.py`) | Resolved in FastAPI |
| **GAP-5F-09** | Legacy AJAX PageMethods (`SearchMethods.aspx.cs`, `AppSearchMethod.aspx.cs`) | Unauthenticated Static `[WebMethod]` Endpoints & Cross-Branch Vehicle Lookup (`BranchId=0`) | **HIGH** | `GetCustByVehicleNo` passes `BranchId=0` without session check; `AppSearchMethod.aspx.cs` methods are unauthenticated | **CLOSED IN PHASE 5G** — Authenticated, branch-scoped `GET /api/v1/customers`, `GET /api/v1/customers/{id}`, `GET /api/v1/customers/{id}/vehicles`, and `GET /api/v1/vehicles` implemented | **CLOSED IN PHASE 5G** |
| **GAP-5F-10** | Legacy Standalone Vehicle Update & Delete (`adm_UpdateVehicleDetails.aspx.cs`, `adm_DeleteCustvehdetails.aspx.cs`) | Missing Branch Scope on Standalone Vehicle Update & Customer/Vehicle Soft-Delete | **HIGH** | `adm_UpdateVehicleDetails.aspx.cs` comments out `BranchId` and searches globally; `adm_DeleteCustvehdetails.aspx.cs` deletes across all branches | FastAPI `VehicleService` already enforces `BranchId` isolation on create/update; keep hardened behavior | Resolved in Phase 5D (Keep in 5G) |
| **GAP-5F-11** | Legacy Customer Update (`adm_UpdateCustomer.aspx.cs`) | Cross-Branch Admin Edit Overwrites Customer's Original `BranchId` and Hardcodes `UpdateUser = "1"` | **MEDIUM** | `adm_UpdateCustomer.aspx.cs` overwrites `Customer.BranchId = Session["BranchId"]` and sets `UpdateUser = "1"` | FastAPI `CustomerService.update_customer` preserves `existing.BranchId` and records `str(current_user.UserId)` | Resolved in Phase 5D |
| **GAP-5F-12** | Legacy Financial Approval Screens (`CashierApprovalNew`, `AccountantApproval`, `OwnerApproval`, `EWalletApproval`) | Missing Server-Side Role Verification on Financial & Commission Approval Mutations | **CRITICAL** | Approval pages only check `Session["UserRole"] != null`; any logged-in staff user can invoke approval postbacks | Must enforce strict role gates (`OWNER`, `ADMIN`, `ACCOUNT`, `ACCOUNT HEAD`, `CASHIER`) in Phase 8 & 9 | Phase 8 / Phase 9 |


---

## 2. Detailed Gap Analysis & Phase 5G Remediation Specifications

### GAP-5F-01: Missing Role-Based Restriction (`require_roles`) on FastAPI Customer & Vehicle Endpoints
- **Severity:** **HIGH**
- **Evidence:**
  - FastAPI [`app/api/v1/endpoints/customers.py`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/app/api/v1/endpoints/customers.py#L22-L120): All 4 endpoints (`POST /api/v1/customers`, `PUT /api/v1/customers/{customer_id}`, `POST /api/v1/customers/{customer_id}/vehicles`, `PUT /api/v1/customers/{customer_id}/vehicles/{vehicle_id}`) only declare `current_user: User = Depends(get_current_user)`.
  - Legacy `tbl_role_privilege`: Only underwriting, franchise, and admin roles (`ADMIN=2`, `OPERATOR=6`, `FRANCHISE=9`, `OPERATOR HEAD=19`, `IT SUPPORT=28`, `ALL USER=33`, `Freelancer=35`, `FRANCHISE TYPE 2=52`, `FRANCHISE TYPE 3=53`, `FRANCHISE OPERATOR=54`, `OTHER=55`, plus `OWNER=1`) have access to Customer/Vehicle creation/update workflows (`PE_TransactionEntry.aspx`, `PolicyTransactionNew.aspx`, `adm_UpdateCustomer.aspx`, `adm_UpdateVehicleDetails.aspx`).
- **Impact:** Currently in FastAPI, a mobile `AGENT (4)` (`2,473` active users), `CLAIM (13)`, `CASHIER (7)`, `QUOT CO-ORDINATOR (14)`, or `pOLICY VIEW (34)` user who belongs to `BranchId = 1` (which includes `3,713` of `3,818` users!) can create or overwrite any Customer or Vehicle record in `BranchId = 1`.
- **Phase 5G Remediation:**
  - Apply explicit role dependencies to `customers.py`:
    - **Customer/Vehicle Create (`POST`):** Allow `OWNER`, `ADMIN`, `IT SUPPORT`, `OPERATOR`, `OPERATOR HEAD`, `ALL USER`, `Freelancer`, `FRANCHISE`, `FRANCHISE TYPE 2`, `FRANCHISE TYPE 3`, `FRANCHISE OPERATOR`, `OTHER`, `ENDORSEMENT`.
    - **Customer/Vehicle Standalone Update (`PUT`):** Allow `OWNER`, `ADMIN`, `IT SUPPORT`, `OPERATOR`, `OPERATOR HEAD`, `ALL USER`, `Freelancer`, `FRANCHISE`, `FRANCHISE OPERATOR`, `ENDORSEMENT`.

---

### GAP-5F-02: Incomplete Role Catalog & Dead `BranchId in (0, None)` / `"SUPERADMIN"` Logic in `_is_admin()`
- **Severity:** **HIGH**
- **Evidence:**
  - FastAPI [`app/services/customer.py`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/app/services/customer.py#L28-L35) and [`app/services/vehicle.py`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/app/services/vehicle.py#L46-L53):
    ```python
    def _is_admin(user: User) -> bool:
        if user.BranchId in (0, None):
            return True
        if user.role and user.role.UserRole:
            return user.role.UserRole.strip().upper() in ("ADMIN", "SUPERADMIN", "OWNER")
        return False
    ```
  - Legacy `brahmainsurance.tbl_user` & `tbl_userrole`:
    1. **Zero rows** in `tbl_user` (`0 / 3,818`) have `BranchId = 0` or `BranchId IS NULL`. Every user has `BranchId >= 1`.
    2. `"SUPERADMIN"` does **not** exist in `tbl_userrole`.
    3. `IT SUPPORT` (`UserRoleId = 28`, `RoleCode = ITS`) has `123` menu screens and cross-branch support responsibilities.
- **Phase 5G Remediation:**
  - Centralize role constants and scope helpers in `app/core/rbac.py` (or `app/core/dependencies.py`) reflecting the actual 56-role `tbl_userrole` catalog.
  - Define explicit role sets (`GLOBAL_ADMIN_ROLES = {"OWNER", "ADMIN", "IT SUPPORT"}`, `CUSTOMER_WRITE_ROLES`, etc.) rather than relying on `BranchId in (0, None)` or `"SUPERADMIN"`.

---

### GAP-5F-03: Missing `AgentId`, `EmpId`, and `FranchaiseId` Principal Resolution
- **Severity:** **HIGH**
- **Evidence:**
  - In legacy `Log_In.aspx.cs` and `Service.asmx.cs::CheckLoginUser`:
    - When `RoleId == 9` (`FRANCHISE`), login queries `tbl_franchaise` (`Sp_CheckloginfrFranchaise`) to resolve `FranchaiseId`.
    - When `RoleId == 5` (`RELATIONSHIP MANAGER`) or `24` (`LOCATION HEAD`), login queries `tbl_employee` (`sp_CheckLoginForEmployee` / `sp_ChkloginEmp`) to resolve `EmpId`.
    - When `RoleId == 4` (`AGENT`) or `16` (`FRANCHISE AGENT`), login queries `tbl_agent` (`sp_CheckLoginAppUser`) to resolve `AgentId` and `FranchaiseId`.
  - In FastAPI [`app/api/v1/endpoints/auth.py`](file:///c:/Users/Admin/Desktop/Reliable-Insurance-Backend/app/api/v1/endpoints/auth.py), login only queries `tbl_user` + `tbl_userrole`.
- **Impact:** Without knowing the authenticated user's `AgentId`, `EmpId`, or `FranchaiseId`, FastAPI services cannot enforce Owner/Agent/Executive/Franchise isolation when those roles access scoped endpoints.
- **Phase 5G Remediation:**
  - Document and prepare principal-context resolution (`agent_id`, `emp_id`, `franchise_id`) so downstream endpoints can enforce owner/franchise isolation without trusting client-supplied IDs.

---

### GAP-5F-04: Missing `role_deleted` Check & `isappuser` Channel Enforcement in `AuthService`
- **Severity:** **MEDIUM**
- **Evidence:**
  - `tbl_userrole` has `role_deleted = 1` on `RoleId = 17` (`POLICY BAZAR`) and `RoleId = 18` (`POLICY BAZAR AGENT`), yet `tbl_user` still has `1` active (`deleted = 0`) user in each role.
  - FastAPI `UserRepository.get_by_username_with_role` filters `User.deleted == 0`, but does not filter `Role.role_deleted == 0`.
- **Phase 5G Remediation:**
  - Reject authentication in `AuthService.authenticate_user` if `user.role is None` or `user.role.role_deleted == 1`.

---

### GAP-5F-05 through GAP-5F-12: Legacy C# Security & Authorization Vulnerabilities (Do Not Replicate)
- **Evidence Summary:**
  - **`Service.asmx.cs` (287 `[WebMethod]` endpoints):** 100% unauthenticated; includes `UploadFile` (arbitrary file write), `AccountPaymentMsg` / `ProcessToInstaPay` (unauthenticated payout trigger), `DeleteCustomerPolicyInfo`, and `GetPolicyPdfByID` (IDOR).
  - **`ImageHandler.ashx.cs:19`:** Unauthenticated arbitrary file read via `context.Request["fileName"]`.
  - **`DownloadAll.ashx.cs`:** Unauthenticated bulk ZIP download of customer/policy/claim documents.
  - **`AppLogin.aspx.cs:40`:** Hardcoded `AppAdmin` / `Admin123` administrative backdoor.
  - **`Clerk/*.aspx.cs`:** UI-only menu hiding via `tbl_role_privilege`; zero server-side page role checks.
- **FastAPI Architectural Guarantee:**
  - FastAPI must **never** replicate UI-only security or unauthenticated ASMX/ASHX handlers. Every endpoint must enforce JWT authentication (`get_current_user`), explicit role authorization (`require_roles`), and server-derived `BranchId` / owner scoping.
