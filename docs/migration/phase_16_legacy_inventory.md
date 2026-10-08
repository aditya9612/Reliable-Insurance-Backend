# PHASE 16 — REMAINING LEGACY INVENTORY
## Reliable-Insurance-Backend: Admin, User Profiles, Master Directories & Dynamic Privilege Inventory

---

### 1. Executive Context & Scope
- **Repository**: `Reliable-Insurance-Backend`
- **Branch / Checkpoint**: `tejas-feature` @ `2b3a29a` (`feat(phase-15b): complete operational utilities, batch jobs, imports, and partner profiles`)
- **Alembic Revision Baseline**: `f15b0c3d1501` (68 physical MySQL tables active)
- **Test Suite Baseline**: **399 / 399 passed (100% green)**
- **Audit Mode**: **STAGE A — AUDIT ONLY (READ-ONLY)**.
- **Objective**: Conduct an exhaustive forensic inventory of all legacy C#, ASP.NET WebForms, ASMX WebMethods, DAL/BLL operations, and Stored Procedures governing:
  1. Administrative user accounts (`tbl_user`, `tbl_userrole`)
  2. Dynamic role/menu privileges (`tbl_role_privilege`, `tbluserrights`, `tbl_menu`)
  3. Login audit trail and session tracking (`tbl_loginhistory`)
  4. Employee directory, hierarchy strings, and document attachments (`tbl_employee`, `tbl_employeedocument`)
  5. Agent/POSP profiles, KYC status, and license documents (`tbl_agent`, `tbl_agentdocument`)
  6. Franchise directory, parent-child hierarchy, and coordinator matrix (`tbl_franchise`)
  7. Master reference tables (`tbl_fueltype`, `tbl_financier`, `tbl_surveyor`)
  8. User and role search/directory operations
  9. Administrative security dashboards and account status counters
  10. Remaining administrative stored procedures

---

### 2. Legacy Artifact Inventory Summary

| Artifact Category | Total in Legacy Codebase | Audited in Phase 16 Scope | Fully Migrated (Phases 0–15B) | Target Phase 16 Scope | Intentionally Obsolete / Non-Core | Preserved Unknown |
|---|:---:|:---:|:---:|:---:|:---:|:---:|
| **WebForms Pages (`.aspx.cs`)** | 1,240 | **24** | 12 | **10** | 2 | 0 |
| **ASMX WebMethods (`Service.asmx.cs`)** | 339 | **22** | 11 | **11** | 0 | 0 |
| **AJAX Search Methods (`SearchMethods.aspx.cs`)**| 41 | **8** | 8 | **0** (Search covered in Phase 12) | 0 | 0 |
| **App Search Methods (`AppSearchMethod.aspx.cs`)**| 16 | **4** | 4 | **0** (Search covered in Phase 12) | 0 | 0 |
| **Stored Procedures (Deduplicated)** | 943 | **34** | 16 | **15** | 1 | 2 (`GAP-UNK-001`) |
| **Physical MySQL Tables** | ~140–160 | **11** | 5 | **6** | 0 | 0 |
| **DTO / Entity Classes (`AllMaster.cs`)** | 188 | **18** | 9 | **9** | 0 | 0 |

---

### 3. Detailed Forensic Breakdown by Domain

#### 3.1 Domain A: User & Admin Profile Management
- **Primary Legacy Files**:
  - `Insurance\Log_In.aspx.cs` (Lines 1–194: ERP web login, session state initialization, role-based redirects)
  - `Insurance\Log_Out.aspx.cs` (Lines 1–35: Session termination, audit log)
  - `Insurance\Clerk\adm_UserMaster.aspx.cs` / `mst_User.aspx.cs` (Lines 1–280: User CRUD, password management, role/branch assignment)
  - `Insurance\Clerk\ChangePassword.aspx.cs` (Lines 1–110: Self and admin password change)
- **Key Legacy Operations**:
  - `BLL_User.BLL_CheckLogin(userName, password)`: Plaintext verification against `tbl_user`.
  - `BLL_User.BLL_CheckLoginfrFranchise(userName, password, opr)`: Multi-role franchise login verification.
  - `BLL_User.BLL_UserOperation(userObj, "INS"|"UPD"|"DEL")`: Dispatches `sp_UserOperation` / `usp_UserOperation`.
  - `BLL_User.BLL_CheckUsername(userName, branchId)`: Duplicate username verification via `sp_CheckUsername`.
  - `BLL_User.BLL_ChangePassword(userId, oldPass, newPass)`: Direct password update.
- **Physical Tables**:
  - `tbl_user` (Active in FastAPI: `app/models/user.py`, 13 columns)
  - `tbl_userrole` (Active in FastAPI: `app/models/user.py`, 4 columns)
- **FastAPI Current State**:
  - `AuthService` (`app/services/auth.py`): Supports dual bcrypt/plaintext migration, JWT generation, `/api/v1/auth/login`, `/api/v1/auth/me`.
  - **Gap**: Dedicated administrative User CRUD endpoints (`POST /api/v1/users`, `GET /api/v1/users`, `PUT /api/v1/users/{id}`, `PUT /api/v1/users/{id}/password`, `PATCH /api/v1/users/{id}/status`) are **missing**.

#### 3.2 Domain B: Dynamic Role & Menu Privileges
- **Primary Legacy Files**:
  - `Insurance\Clerk\Adm_RolePrivilege.aspx.cs` (Lines 1–245: Checkbox tree for role-screen visibility)
  - `Insurance\Clerk\Clerk.Master.cs` (Lines 1–320: Menu rendering, reads `tbl_role_privilege` / `tbluserrights`)
  - `Insurance\Clerk\adm_UserRights.aspx.cs` (Lines 1–180: Action-level rights `View`, `Add`, `Edit`, `Delete`)
- **Key Legacy Stored Procedures**:
  - `sp_insert_role_privilege(P_BranchId, P_ROLE_ID, P_SCREEN_ID)` (Call site: `DAL_Menu.DAL_insert_role_privilege`, L20697)
  - `sp_delete_role_privilege(P_BranchId, P_ROLE_ID)` (Call site: `DAL_Menu.DAL_delete_role_privilege`, L20720)
  - `sp_SelectUserRightsByRoleId(P_UserRoleId)`
- **Architectural Security Finding**:
  - In legacy ASP.NET, `tbl_role_privilege` and `tbluserrights` **only control UI navigation visibility** in `Clerk.Master.cs`.
  - WebMethods (`Service.asmx.cs`) and `.aspx.cs` page endpoints **do not enforce** menu-level rights.
  - **Hardening Invariant**: FastAPI route security relies strictly on server-side `require_roles(...)` and principal resolution. Menu privilege endpoints are maintained for admin UI tree customization without compromising backend security.

#### 3.3 Domain C: Login History & Session Activity
- **Primary Legacy Files**:
  - `Insurance\Log_In.aspx.cs` (Lines 50–54: Extracts client IP via `HTTP_X_FORWARDED_FOR` or `REMOTE_ADDR`)
  - `Insurance\Log_Out.aspx.cs` (Line 22: Records logout event)
  - `DAL\DAL_Operations.cs` (L20471: `DAL_InsertLoginHistiry`, L20505: `DAL_SelectLoginHistory`)
  - `Insurance\Service.asmx.cs` (L10967: `InsertLoginHistory`)
- **Stored Procedures**:
  - `sp_insertLoginHistory` (`P_AgentId, P_Extra, P_FromDate, P_IP_add, P_LogInOrLogOut, P_LoginDate, P_Nominee, P_Payment...`)
  - `sp_SelectLoginHistory` (`P_EmpId, P_FromDate, P_IN_DateTime, P_Opr, P_ToDate, P_UserId, P_UserRoleId`)
- **Physical Table**:
  - `tbl_loginhistory` (8 columns: `LoginHistoryId`, `UserId`, `UserName`, `LogInOrLogOut`, `funPerform`, `IPAddress`, `CreateDate`, `Remark`)
- **FastAPI Current State**:
  - Stateless JWT token authorization. Activity logged to structured console/JSON logs; persistent MySQL table logging is **missing**.

#### 3.4 Domain D: Employee Directory & Hierarchy
- **Legacy Files**:
  - `Insurance\Clerk\adm_EmployeeMaster.aspx.cs` (Staff onboarding, branch mapping, bank account, 5-level hierarchy)
  - `API\AllMaster.cs` (`API_Employee` L201–319: 104 fields; `API_Hie_Desn` L322–330)
- **Stored Procedures**:
  - `sp_generateEmpCode(P_BranchId, P_EmpCode, P_EmpId, P_UserName, P_UserPassword, P_UserRoleId)`
  - `sp_SelectPrevYearEmp(P_BranchId)`
- **FastAPI Baseline**:
  - `tbl_employee` modeled in Phase 15B (`app/models/profile.py`, 31 columns) with CRUD at `/api/v1/employees`.
  - **Remaining Gap**: 5-level organizational hierarchy strings (`Hei_Data`, `Hie_DataSales`, `Hie_DataOprn`), coordinator mapping (`QuotationCordinatorId`, `InspectionCordinatorId`, `EndrosmentcordinatorId`), and document attachment tracking (`tbl_employeedocument`).

#### 3.5 Domain E: Agent / POSP Profile & KYC
- **Legacy Files**:
  - `Insurance\Clerk\mst_Agent.aspx.cs` (Agent creation, bank details, PAN/Aadhaar)
  - `API\AllMaster.cs` (`API_Agent` L1250–1278, `API_AgentDocumentList` L1813–1824)
- **FastAPI Baseline**:
  - `tbl_agent` modeled in Phase 15B (`app/models/profile.py`, 25 columns) with CRUD at `/api/v1/agents`.
  - **Remaining Gap**: KYC verification state machine transitions (`PENDING`, `VERIFIED`, `REJECTED`), nominee details, and document upload tracking (`tbl_agentdocument`).

#### 3.6 Domain F: Franchise Directory & Hierarchy
- **Legacy Files**:
  - `Insurance\Clerk\mst_Franchise.aspx.cs` (Franchise partner creation, sub-franchise parent linkage)
  - `API\AllMaster.cs` (`API_franchise` L1536–1599: 52 fields)
- **FastAPI Baseline**:
  - `tbl_franchise` modeled in Phase 15B (`app/models/profile.py`, 24 columns) with CRUD at `/api/v1/franchises`.
  - **Remaining Gap**: Recursive sub-franchise hierarchy resolution (`ParentFranchiseId`), coordinator assignment matrix (`QuotationCo_Id`, `InspectionCo_Id`, `EndrosmentCo_Id`), and wallet account binding.

#### 3.7 Domain G: Master Directories (`tbl_fueltype`, `tbl_financier`, `tbl_surveyor`)
- **Legacy Files**:
  - `Insurance\Clerk\mst_FuelType.aspx.cs` (Vehicle fuel types: Petrol, Diesel, CNG, LPG, Electric)
  - `Insurance\Clerk\mst_Financier.aspx.cs` (Hypothecation financier banks)
  - `Insurance\Clerk\mst_Surveyor.aspx.cs` / `CL_ClaimNew.aspx.cs` (Motor claim surveyor registry)
- **Stored Procedures**:
  - `Sp_GarageSurvey_Operations`, `Sp_Spot_Servey_Operations`
  - `sp_SelectSurveyorList`
- **FastAPI Baseline**:
  - Foreign key IDs (`FuelTypeId`, `FinancierId`, `SurveyorId`) exist across transaction, vehicle, and claim models.
  - Dedicated models and directory lookup endpoints for these 3 reference tables are **missing**.

#### 3.8 Domain H: User & Role Search / Autocomplete
- **Legacy Files**:
  - `SearchMethods.aspx.cs` (41 WebMethods) & `AppSearchMethod.aspx.cs` (16 WebMethods)
- **FastAPI Baseline**:
  - Phase 12 fully migrated all 57 AJAX SearchMethods under `/api/v1/search/*`.
  - Phase 15B implemented directory searches under `/api/v1/employees`, `/api/v1/agents`, and `/api/v1/franchises`.
  - Phase 16 requires administrative user search: `GET /api/v1/users?search=...&branch_id=...&role_id=...`.

#### 3.9 Domain I: Admin Dashboard Counters & Account Statistics
- **Legacy Files**:
  - `Clerk/Index.aspx.cs` (Administrative widget metrics)
- **FastAPI Baseline**:
  - Phase 14 implemented financial and operational dashboards (`/api/v1/dashboards/*`).
  - Phase 16 requires system security and entity counters: total users, active/inactive users, pending KYC, recent login failures, lock status.

#### 3.10 Domain J: Remaining Administrative Stored Procedures
- **Legacy Procedures Audited**:
  - `sp_CheckLogin`: Replaced by `AuthService.login`
  - `Sp_CheckloginfrFranchaise`: Replaced by `AuthService.login` with franchise principal resolution
  - `sp_CheckUsername`: Replaced by `UserRepository.get_by_username`
  - `sp_UserByBranchRole`: Replaced by `UserRepository.list_by_branch_role`
  - `sp_UserRole`: Replaced by `UserRepository.list_roles`
  - `sp_insertLoginHistory`: Target for `LoginHistoryRepository.create`
  - `sp_SelectLoginHistory`: Target for `LoginHistoryRepository.list`
  - `sp_insert_role_privilege`: Target for `PrivilegeRepository.assign_role_privilege`
  - `sp_delete_role_privilege`: Target for `PrivilegeRepository.revoke_role_privileges`
  - `sp_GarageSurvey_Operations`: Target for `SurveyorRepository`
  - `sp_Spot_Servey_Operations`: Target for `SurveyorRepository`

---

### 4. Quantitative Inventory Ledger
- **Total Files Audited**: 36 legacy source files (.aspx.cs, .asmx.cs, .cs)
- **Total WebMethods Audited**: 22 methods
- **Total Stored Procedures Audited**: 34 procedures
- **Total Physical Tables Audited**: 11 tables (5 active, 6 target)
- **Cumulative UNKNOWNs Preserved**: 15 (0 removed, 0 modified)
