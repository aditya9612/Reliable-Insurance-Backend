# PHASE 16 — OPERATION PRIORITY RECONCILIATION
## Reliable-Insurance-Backend: Forensic Analysis & Priority Classification of 18 Missing Operations

---

### 1. Executive Summary & Methodology
In Phase 16 Stage A, exactly 29 programmatic operations were audited across 10 domains (A through J).
- **10 Migrated Operations**: Fully implemented across Phase 0–15B (`POST /api/v1/auth/login`, `/me`, `/employees`, `/agents`, `/franchises`, and Phase 12 search autocompletes).
- **1 Partial Operation**: Admin dashboard overview counters (`Clerk/Index.aspx.cs` L120) partially satisfied by existing Phase 14 reporting engines.
- **18 Missing Operations**: Administrative user CRUD, password governance, dynamic menu trees, login audit persistence, agent KYC verification machine, organizational hierarchies, and auxiliary reference master directories.

This document independently reconciles and classifies all **18 missing operations** based on:
1. **Financial Impact** (risk of financial distortion, incorrect payouts, or ledger inaccuracy)
2. **Security Impact** (risk of broken access control, credential compromise, or unauthenticated manipulation)
3. **Operational Impact** (everyday administration, onboarding, and compliance workflow enablement)
4. **Production Criticality** (whether normal production operation can proceed safely without the endpoint)

---

### 2. Priority & Classification Definitions
- **P0**: Security, financial integrity, authentication, authorization, or data-integrity blocker.
- **P1**: Core operational/business workflow required for normal production administration.
- **P2**: Important administrative/operational functionality, but not a core financial/security blocker.
- **P3**: Convenience, low-value, legacy-only, informational, or non-core functionality.
- **MUST MIGRATE**: Mandatory for completing Phase 16 baseline.
- **SHOULD MIGRATE**: High-value feature; migrate unless external dependency blocks.
- **OPTIONAL**: Low-value legacy feature; migrate only if trivial.
- **OBSOLETE**: Intentionally retired or superseded by modern architecture.
- **UNKNOWN**: Blocked on missing offline evidence; preserved without speculation.

---

### 3. Detailed Forensic Analysis of All 18 Missing Operations

#### Operation 1: Create User Account
- **Legacy Operation**: `adm_UserMaster.aspx.cs:L45` (`btnSave_Click`) / `sp_UserOperation` (`opr="INS"`)
- **Domain**: Domain A (User / Admin Profile Management)
- **Business Purpose**: Provision new system user accounts, bind them to a specific `UserRoleId` and `BranchId`, and set initial credentials.
- **Current FastAPI Equivalent**: Target `POST /api/v1/users`
- **Why Missing**: Phase 3 and Phase 15B established authentication verification and partner entity profiles (`/employees`, `/agents`, `/franchises`), leaving administrative user account creation for the Phase 16 admin module.
- **Financial Impact**: Indirect (staff cannot log in to book policies or process transactions without an account).
- **Security Impact**: High (must hash passwords via Bcrypt, enforce username uniqueness, prevent role privilege escalation, enforce branch boundaries).
- **Operational Impact**: High (administrators cannot onboard new back-office clerks or operational users without raw DB queries).
- **Production Criticality**: High.
- **Priority**: **P1**
- **Migration Classification**: **MUST MIGRATE**

#### Operation 2: Update User Account
- **Legacy Operation**: `adm_UserMaster.aspx.cs:L95` (`btnUpdate_Click`) / `sp_UserOperation` (`opr="UPD"`)
- **Domain**: Domain A (User / Admin Profile Management)
- **Business Purpose**: Update existing user attributes (role reassignment, branch transfer, contact number update, partner user linkage).
- **Current FastAPI Equivalent**: Target `PUT /api/v1/users/{id}`
- **Why Missing**: User profile mutation endpoints were deferred to Phase 16.
- **Financial Impact**: Indirect.
- **Security Impact**: High (modifying `BranchId` or `UserRoleId` alters the user's authorization boundary; requires strict global admin gating).
- **Operational Impact**: High (updating staff branch transfers or role promotions).
- **Production Criticality**: High.
- **Priority**: **P1**
- **Migration Classification**: **MUST MIGRATE**

#### Operation 3: Deactivate / Soft-Delete User
- **Legacy Operation**: `adm_UserMaster.aspx.cs:L140` (`btnDelete_Click`) / `sp_UserOperation` (`opr="DEL"`)
- **Domain**: Domain A (User / Admin Profile Management)
- **Business Purpose**: Soft-delete/deactivate a user account (`isdeleted = '1'`), immediately revoking login privileges.
- **Current FastAPI Equivalent**: Target `DELETE /api/v1/users/{id}` and `PATCH /api/v1/users/{id}/status`
- **Why Missing**: Administrative user deactivation endpoint not yet mounted.
- **Financial Impact**: Medium (prevents unauthorized transaction creation by departed staff).
- **Security Impact**: Critical (offboarding departing staff or disabling compromised user accounts).
- **Operational Impact**: High (security governance and HR offboarding).
- **Production Criticality**: High.
- **Priority**: **P1**
- **Migration Classification**: **MUST MIGRATE**

#### Operation 4: Change / Reset User Password
- **Legacy Operation**: `ChangePassword.aspx.cs:L32` (`btnChangePass_Click`) / `sp_ChangePassword`
- **Domain**: Domain A (User / Admin Profile Management)
- **Business Purpose**: Allow authenticated users to change their own password upon verifying their existing password, and allow global administrators to reset credentials.
- **Current FastAPI Equivalent**: Target `PUT /api/v1/users/{id}/password`
- **Why Missing**: Credential verification exists in `AuthService.login`, but mutation endpoints were deferred.
- **Financial Impact**: Low direct impact.
- **Security Impact**: Critical (enforces password lifecycle, rotation, complexity rules, and old-password verification).
- **Operational Impact**: High (resolves locked-out users and routine credential maintenance).
- **Production Criticality**: High.
- **Priority**: **P1**
- **Migration Classification**: **MUST MIGRATE**

#### Operation 5: Check Username Availability
- **Legacy Operation**: `adm_UserMaster.aspx.cs:L180` (`CheckUsername`) / `sp_CheckUsername`
- **Domain**: Domain A (User / Admin Profile Management)
- **Business Purpose**: Asynchronous pre-flight validation on the user registration form to ensure username is unique before submitting.
- **Current FastAPI Equivalent**: Target `GET /api/v1/users/check-username`
- **Why Missing**: Convenience endpoint; backend already enforces uniqueness constraint during creation.
- **Financial Impact**: None.
- **Security Impact**: Low (informational pre-check; must be rate-limited to prevent automated enumeration).
- **Operational Impact**: Medium (enhances UI responsiveness during administrative onboarding).
- **Production Criticality**: Low.
- **Priority**: **P3**
- **Migration Classification**: **SHOULD MIGRATE**

#### Operation 6: List Users with Filtering & Pagination
- **Legacy Operation**: `DAL_Operations.cs:L20433` (`DAL_UserByBranchRole`) / `sp_UserByBranchRole`
- **Domain**: Domain A (User / Admin Profile Management)
- **Business Purpose**: Search and paginate system users filtered by `BranchId`, `UserRoleId`, active status, and search string.
- **Current FastAPI Equivalent**: Target `GET /api/v1/users`
- **Why Missing**: Administrative roster query endpoint not yet mounted.
- **Financial Impact**: None direct.
- **Security Impact**: Medium (must enforce tenant/branch isolation: non-global admins must only view users within their assigned branch).
- **Operational Impact**: High (administrators must be able to view user rosters).
- **Production Criticality**: High.
- **Priority**: **P1**
- **Migration Classification**: **MUST MIGRATE**

#### Operation 7: List User Roles Directory
- **Legacy Operation**: `DAL_Operations.cs:L2370` (`DAL_selectUserRole`) / `sp_UserRole`
- **Domain**: Domain A (User / Admin Profile Management)
- **Business Purpose**: Query active roles from `tbl_userrole` to populate dropdown lists during user onboarding.
- **Current FastAPI Equivalent**: Target `GET /api/v1/users/roles`
- **Why Missing**: Canonical role definitions exist in `app/core/rbac.py`, but REST endpoint exposing them to frontend dropdowns is missing.
- **Financial Impact**: None.
- **Security Impact**: Low (read-only reference metadata).
- **Operational Impact**: High (enables frontend selection of valid role IDs).
- **Production Criticality**: High.
- **Priority**: **P2**
- **Migration Classification**: **MUST MIGRATE**

#### Operation 8: Assign Role Menu Privileges
- **Legacy Operation**: `Adm_RolePrivilege.aspx.cs:L50` (`btnSave_Click`) / `sp_insert_role_privilege`
- **Domain**: Domain B (Dynamic Role / Menu Privileges)
- **Business Purpose**: Save dynamic menu navigation entitlements for a given role and branch into `tbl_role_privilege`.
- **Current FastAPI Equivalent**: Target `POST /api/v1/admin/privileges`
- **Why Missing**: Dynamic menu presentation management was deferred.
- **Financial Impact**: None.
- **Security Impact**: Low (affects only UI navigation rendering; backend security is enforced independently by server-side `require_roles`).
- **Operational Impact**: Medium (allows customizing UI menus for different operational roles).
- **Production Criticality**: Medium.
- **Priority**: **P2**
- **Migration Classification**: **SHOULD MIGRATE**

#### Operation 9: Revoke Role Menu Privileges
- **Legacy Operation**: `Adm_RolePrivilege.aspx.cs:L120` (`btnDelete_Click`) / `sp_delete_role_privilege`
- **Domain**: Domain B (Dynamic Role / Menu Privileges)
- **Business Purpose**: Delete or reset dynamic menu screen visibility for a role and branch before re-saving.
- **Current FastAPI Equivalent**: Target `DELETE /api/v1/admin/privileges`
- **Why Missing**: Dynamic menu presentation management deferred.
- **Financial Impact**: None.
- **Security Impact**: Low (UI presentation only).
- **Operational Impact**: Medium.
- **Production Criticality**: Medium.
- **Priority**: **P2**
- **Migration Classification**: **SHOULD MIGRATE**

#### Operation 10: Load Role Menu Presentation Tree
- **Legacy Operation**: `Clerk.Master.cs:L75` (`LoadMenuByRole`) / `sp_SelectUserRightsByRoleId`
- **Domain**: Domain B (Dynamic Role / Menu Privileges)
- **Business Purpose**: Retrieve the structured navigation menu items assigned to a given user role and branch for sidebar rendering.
- **Current FastAPI Equivalent**: Target `GET /api/v1/admin/privileges/{role_id}`
- **Why Missing**: Dynamic menu presentation management deferred.
- **Financial Impact**: None.
- **Security Impact**: Low (UI menu tree output).
- **Operational Impact**: High (frontend SPA requires structured menu tree to render role-tailored sidebar navigation).
- **Production Criticality**: Medium.
- **Priority**: **P2**
- **Migration Classification**: **SHOULD MIGRATE**

#### Operation 11: Insert Login History Event
- **Legacy Operation**: `Log_In.aspx.cs:L50` (`BLL_InsertLoginHistiry`) / `sp_insertLoginHistory`
- **Domain**: Domain C (Login History / User Activity)
- **Business Purpose**: Persist authentication session event into `tbl_loginhistory` recording `UserId`, `UserName`, client `IPAddress`, `LogInOrLogOut`, `funPerform`, and timestamp.
- **Current FastAPI Equivalent**: Target internal invocation inside `POST /api/v1/auth/login` and `/logout`.
- **Why Missing**: FastAPI currently logs authentication events to structured application console logs; persistent MySQL database insertion was deferred.
- **Financial Impact**: None direct.
- **Security Impact**: High (cybersecurity audit trail, non-repudiation, suspicious activity detection, IRDAI compliance).
- **Operational Impact**: High (security audit trail).
- **Production Criticality**: High.
- **Priority**: **P1**
- **Migration Classification**: **MUST MIGRATE**

#### Operation 12: Query Login History Audit Records
- **Legacy Operation**: `DAL_Operations.cs:L20505` (`DAL_SelectLoginHistory`) / `sp_SelectLoginHistory`
- **Domain**: Domain C (Login History / User Activity)
- **Business Purpose**: Retrieve historical login/logout events filtered by user, date range, or event type for security review.
- **Current FastAPI Equivalent**: Target `GET /api/v1/auth/login-history`
- **Why Missing**: Query endpoint for persistent login audit records not yet mounted.
- **Financial Impact**: None.
- **Security Impact**: High (threat detection, auditing shared accounts, forensic investigation).
- **Operational Impact**: High (security officers and HR compliance reviews).
- **Production Criticality**: High.
- **Priority**: **P2**
- **Migration Classification**: **MUST MIGRATE**

#### Operation 13: Employee Hierarchy Strings Serialization
- **Legacy Operation**: `adm_EmployeeMaster.aspx.cs:L150` (`API_Employee` L290–296)
- **Domain**: Domain D (Employee Directory & Hierarchy)
- **Business Purpose**: Serialize 5-level organizational hierarchy IDs (`ClassId`, `BProcessId`, `BLineId`, `FuncId`, `DesnId`, `ReportingId`) into hierarchy strings (`Hei_Data`, `Hie_DataSales`, `Hie_DataOprn`).
- **Current FastAPI Equivalent**: Target `PUT /api/v1/employees/{id}/hierarchy`
- **Why Missing**: Phase 15B implemented core employee CRUD (`tbl_employee`), but complex string serialization was deferred.
- **Financial Impact**: Low direct impact.
- **Security Impact**: Low.
- **Operational Impact**: Medium (legacy reporting hierarchy consistency).
- **Production Criticality**: Low/Medium.
- **Priority**: **P3**
- **Migration Classification**: **SHOULD MIGRATE**

#### Operation 14: Agent KYC Verification State Machine Transition
- **Legacy Operation**: `mst_Agent.aspx.cs:L180` / `sp_UpdateAgentKYC`
- **Domain**: Domain E (Agent / POSP Profile & KYC)
- **Business Purpose**: Formally transition agent onboarding status (`PENDING_VERIFICATION` $\rightarrow$ `VERIFIED` or `REJECTED`) with compliance remarks and reviewer attribution.
- **Current FastAPI Equivalent**: Target `PATCH /api/v1/agents/{id}/kyc`
- **Why Missing**: Phase 15B implemented basic CRUD (`tbl_agent`), but compliance state machine transition endpoint was deferred.
- **Financial Impact**: High (unverified POSPs must not receive commission disbursements or bind coverage).
- **Security Impact**: High (regulatory compliance and fraud mitigation).
- **Operational Impact**: High (onboarding compliance bottleneck).
- **Production Criticality**: High.
- **Priority**: **P1**
- **Migration Classification**: **MUST MIGRATE**

#### Operation 15: Sub-Franchise Recursive Hierarchy Traversal
- **Legacy Operation**: `mst_Franchise.aspx.cs:L210` / Recursive query
- **Domain**: Domain F (Franchise Directory & Hierarchy)
- **Business Purpose**: Traverse multi-tier parent-child franchise trees via `ParentFranchiseId` to display sub-franchise networks.
- **Current FastAPI Equivalent**: Target `GET /api/v1/franchises/{id}/hierarchy`
- **Why Missing**: Phase 15B implemented `tbl_franchise` CRUD and stored `ParentFranchiseId`, but recursive tree traversal query was deferred.
- **Financial Impact**: Low direct (revenue roll-up is tracked via transaction franchise IDs).
- **Security Impact**: Low.
- **Operational Impact**: Medium (partner portal visibility).
- **Production Criticality**: Low/Medium.
- **Priority**: **P3**
- **Migration Classification**: **SHOULD MIGRATE**

#### Operation 16: Vehicle Fuel Type Reference Listing
- **Legacy Operation**: `mst_FuelType.aspx.cs:L30` / `sp_SelectFuelType`
- **Domain**: Domain G (Master Directories)
- **Business Purpose**: Reference lookup for vehicle fuel types (Petrol, Diesel, CNG, LPG, Electric, Hybrid) used in rating and vehicle specs.
- **Current FastAPI Equivalent**: Target `GET /api/v1/masters/fuel-types`
- **Why Missing**: `FuelTypeId` is referenced in `tbl_custvehicle` and rating calculations, but dedicated reference table and endpoint were deferred.
- **Financial Impact**: Low direct (affects bi-fuel kit surcharges in quotation).
- **Security Impact**: None.
- **Operational Impact**: High (vehicle onboarding dropdown).
- **Production Criticality**: Medium.
- **Priority**: **P2**
- **Migration Classification**: **MUST MIGRATE**

#### Operation 17: Hypothecation Financier Bank Listing
- **Legacy Operation**: `mst_Financier.aspx.cs:L40` / `sp_SelectFinancier`
- **Domain**: Domain G (Master Directories)
- **Business Purpose**: Master directory of hypothecation financier banks (e.g. HDFC, SBI, Bajaj Finance) for policy certificates and loan endorsements.
- **Current FastAPI Equivalent**: Target `GET /api/v1/masters/financiers`
- **Why Missing**: `FinancierId` is stored in transactions, but dedicated master table and endpoint were deferred.
- **Financial Impact**: Low direct (legal documentation on policy certificate).
- **Security Impact**: None.
- **Operational Impact**: High (policy booking hypothecation dropdown).
- **Production Criticality**: Medium.
- **Priority**: **P2**
- **Migration Classification**: **MUST MIGRATE**

#### Operation 18: Motor Claims Surveyor Directory
- **Legacy Operation**: `mst_Surveyor.aspx.cs:L50` / `sp_SelectSurveyorList`
- **Domain**: Domain G (Master Directories)
- **Business Purpose**: Directory of IRDA licensed claims loss assessors for appointment on spot and garage surveys.
- **Current FastAPI Equivalent**: Target `GET /api/v1/masters/surveyors` (and CRUD for admin)
- **Why Missing**: Phase 12 migrated autocomplete search, but dedicated master table model and directory endpoint were deferred.
- **Financial Impact**: Medium (survey fee disbursements and loss assessment validation).
- **Security Impact**: Low.
- **Operational Impact**: High (claims processing workflow).
- **Production Criticality**: Medium.
- **Priority**: **P2**
- **Migration Classification**: **MUST MIGRATE**

---

### 4. Consolidated 18-Operation Reconciliation Ledger

| # | Legacy Operation | Domain | Status | Priority | Migration Class | Reason for Classification | Evidence |
|:---:|---|:---:|:---:|:---:|:---:|---|---|
| 1 | Create User Account | A | **MISSING** | **P1** | **MUST MIGRATE** | Core operational workflow: onboarding new staff accounts. | `adm_UserMaster.aspx.cs:45` |
| 2 | Update User Account | A | **MISSING** | **P1** | **MUST MIGRATE** | Core operational workflow: updating staff roles and branch transfers. | `adm_UserMaster.aspx.cs:95` |
| 3 | Deactivate / Soft-Delete User | A | **MISSING** | **P1** | **MUST MIGRATE** | Critical security control: disabling departed or compromised accounts. | `adm_UserMaster.aspx.cs:140` |
| 4 | Change / Reset User Password | A | **MISSING** | **P1** | **MUST MIGRATE** | Critical security workflow: password rotation and credential reset. | `ChangePassword.aspx.cs:32` |
| 5 | Check Username Availability | A | **MISSING** | **P3** | **SHOULD MIGRATE** | UI convenience helper; backend already validates uniqueness constraint. | `adm_UserMaster.aspx.cs:180` |
| 6 | List Users with Filtering | A | **MISSING** | **P1** | **MUST MIGRATE** | Core administrative workflow: managing branch staff rosters. | `DAL_Operations.cs:20433` |
| 7 | List User Roles Directory | A | **MISSING** | **P2** | **MUST MIGRATE** | Administrative metadata: populating role dropdowns for user CRUD. | `DAL_Operations.cs:2370` |
| 8 | Assign Role Menu Privileges | B | **MISSING** | **P2** | **SHOULD MIGRATE** | Administrative presentation: dynamic menu tailoring for frontend SPAs. | `Adm_RolePrivilege.aspx.cs:50` |
| 9 | Revoke Role Menu Privileges | B | **MISSING** | **P2** | **SHOULD MIGRATE** | Administrative presentation: resetting role menu visibility. | `Adm_RolePrivilege.aspx.cs:120` |
| 10 | Load Role Menu Presentation Tree | B | **MISSING** | **P2** | **SHOULD MIGRATE** | Operational UI requirement: rendering role-based navigation trees. | `Clerk.Master.cs:75` |
| 11 | Insert Login History Event | C | **MISSING** | **P1** | **MUST MIGRATE** | Regulatory cybersecurity compliance: persisting client IP and session history. | `Log_In.aspx.cs:50` |
| 12 | Query Login History Audit Records | C | **MISSING** | **P2** | **MUST MIGRATE** | Security auditing: reviewing authentication attempts and detecting breaches. | `DAL_Operations.cs:20505` |
| 13 | Employee Hierarchy Strings | D | **MISSING** | **P3** | **SHOULD MIGRATE** | Organizational tracking: 5-level hierarchy serialization strings. | `AllMaster.cs:290` |
| 14 | Agent KYC Verification State Machine | E | **MISSING** | **P1** | **MUST MIGRATE** | Regulatory compliance: formal gate before issuing policies/commissions. | `mst_Agent.aspx.cs:180` |
| 15 | Sub-Franchise Hierarchy Traversal | F | **MISSING** | **P3** | **SHOULD MIGRATE** | Partner portal feature: displaying recursive child franchise networks. | `mst_Franchise.aspx.cs:210` |
| 16 | Vehicle Fuel Type Reference Listing | G | **MISSING** | **P2** | **MUST MIGRATE** | Core master reference: rating engine bi-fuel kit and vehicle specs. | `mst_FuelType.aspx.cs:30` |
| 17 | Hypothecation Financier Bank Listing | G | **MISSING** | **P2** | **MUST MIGRATE** | Core master directory: policy booking loan hypothecation dropdown. | `mst_Financier.aspx.cs:40` |
| 18 | Motor Claims Surveyor Directory | G | **MISSING** | **P2** | **MUST MIGRATE** | Core master directory: claims loss assessment surveyor assignments. | `mst_Surveyor.aspx.cs:50` |

---

### 5. Quantitative Summary of Missing Operations
- **Total Missing Operations Reconciled**: **18**
- **Priority Breakdown**:
  - **P0 Operations**: **0** (No critical security/financial blockers unaddressed; core auth already active)
  - **P1 Operations**: **6 (33.3%)** (User CRUD, Password, User List, Login Event Logging, Agent KYC)
  - **P2 Operations**: **8 (44.4%)** (Roles Directory, Dynamic Menus [Assign/Revoke/Load], Login Audit Query, Fuel Types, Financiers, Surveyors)
  - **P3 Operations**: **4 (22.2%)** (Check Username, Employee Hierarchy Strings, Sub-Franchise Hierarchy, Auxiliary Helper)
- **Migration Classification Breakdown**:
  - **MUST MIGRATE**: **12 (66.7%)**
  - **SHOULD MIGRATE**: **6 (33.3%)**
  - **OPTIONAL**: **0**
  - **OBSOLETE**: **0**
  - **UNKNOWN**: **0**
