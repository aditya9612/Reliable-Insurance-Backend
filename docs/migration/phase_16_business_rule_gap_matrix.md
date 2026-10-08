# PHASE 16 — BUSINESS RULE GAP MATRIX
## Reliable-Insurance-Backend: Legacy Business Rules (LBR), Security Hardening & Parity Classification

---

### 1. Executive Summary & Classification Schema
This matrix catalogs all business rules governing administrative user management, authentication lifecycles, dynamic privileges, directory hierarchies, partner profiles, and master lookups.
Every rule is classified into one of six standard statuses:
1. **PARITY**: Exact functional equivalent of legacy C# / SQL behavior.
2. **HARDENING**: Modern security/integrity hardening over insecure legacy behavior.
3. **LEGACY DEFECT MITIGATED**: Legacy bug or architectural flaw intentionally resolved.
4. **PARTIAL**: Partially implemented across existing endpoints.
5. **MISSING**: Required legacy capability not yet exposed in FastAPI.
6. **UNKNOWN**: Speculative or unextractable behavior without offline source evidence.

---

### 2. Master Business Rule Gap Matrix

| Rule ID | Domain | Business Rule Specification | Legacy Source Evidence | Target FastAPI Implementation | Status | Classification Details |
|---|---|---|---|---|:---:|---|
| **LBR-001** | Authentication | User login validates username and password against `tbl_user`, checks active account (`isdeleted != '1'`) and active role (`tbl_userrole.isdeleted != '1'`), resolving `UserId`, `UserName`, `UserRoleId`, `BranchId`. | `Log_In.aspx.cs:38`, `sp_CheckLogin` | `AuthService.login` (`POST /api/v1/auth/login`) | **PARITY** | Fully operational with dual-mode bcrypt and plaintext upgrade. |
| **LBR-002** | Authentication | Mobile agent/customer login authenticates via phone/OTP or password, generating access credentials and logging device information. | `Service.asmx.cs:545`, `AppLogin.aspx.cs` | `OTPService` & `AuthService.login` | **PARITY** | Salted OTP generation with Fast2SMS/IndiaText integration completed in Phase 13. |
| **LBR-003** | RBAC / Privileges | Dynamic menu visibility and screen access configured per role/branch via `tbl_role_privilege` / `tbluserrights`. | `Clerk.Master.cs:75`, `Adm_RolePrivilege.aspx.cs` | Target `PrivilegeService` + server-side `require_roles` | **HARDENING** | In legacy, this only hid UI menus; backend now enforces server-side route RBAC dependencies. UI tree query will serve admin frontend. |
| **LBR-004** | Branch Isolation | All user accounts, employee profiles, agents, and franchises are tagged with `BranchId`. Non-global admin queries are strictly isolated to `current_user.BranchId`. | `Log_In.aspx.cs:50`, `DAL_Operations.cs` | `resolve_principal_context` & repository queries | **PARITY** | Strictly enforced across all Phase 5–15B service layers. |
| **LBR-005** | Ownership Hierarchy | Employee profiles link to a 5-level organizational hierarchy (`ClassId`, `BProcessId`, `BLineId`, `FuncId`, `DesnId`, `ReportingId`) serialized into hierarchy strings (`Hei_Data`, `Hie_DataSales`, `Hie_DataOprn`). | `AllMaster.cs:290-296`, `API_Employee` | Target `ProfileService.update_employee_hierarchy` | **MISSING** | `tbl_employee` modeled in Phase 15B; hierarchy string serialization endpoints missing in REST contract. |
| **LBR-012** | Hierarchy Cascade | Selecting an `AgentId` or `FranchiseId` automatically resolves and cascades their assigned `BranchId`, `SalesExecutiveId`, and coordinators. | `PE_TransactionEntry.aspx.cs`, `PolicyTransactionNew.aspx.cs` | `PolicyService` & `CommissionAccountingService` | **PARITY** | Fully enforced in policy booking and commission spread. |
| **LBR-141** | User Activation | User account activation/deactivation toggles `tbl_user.isdeleted` (`'0'` active, `'1'` inactive). Inactive users are rejected immediately during authentication with 401 Unauthorized. | `adm_UserMaster.aspx.cs:140` | `AuthService.login` checks `user.is_active` | **PARITY** | Enforced in `AuthService`; admin status toggle endpoint missing (`PATCH /api/v1/users/{id}/status`). |
| **LBR-142** | Password Security | Passwords must be hashed using salted Bcrypt (work factor 12). Legacy plaintext passwords must be automatically upgraded to Bcrypt upon successful verification. | Legacy stored plaintext (`Log_In.aspx.cs`) | `AuthService.login` & `verify_password` | **HARDENING** | Completely resolves legacy plaintext password security defect (`DEF-002`). |
| **LBR-143** | Self Password Change | A user can change their own password only by providing and successfully verifying their existing password. New password must meet minimum length (8 chars) and complexity. | `ChangePassword.aspx.cs:32` | Target `UserService.change_password` (`PUT /api/v1/users/{id}/password`) | **MISSING** | Missing dedicated user password update endpoint. |
| **LBR-144** | Login History Audit | Every successful and failed authentication attempt, as well as logout, must record `UserId`, `UserName`, `IPAddress`, `LogInOrLogOut`, `funPerform`, `Remark`, and timestamp in `tbl_loginhistory`. | `Log_In.aspx.cs:50-54`, `sp_insertLoginHistory` | Target `LoginHistoryService.record_login_event` | **MISSING** | Currently logged only to application structured console/JSON logs; persistent MySQL table logging missing. |
| **LBR-145** | Agent KYC State Machine | An agent/POSP onboarding record exists in three discrete KYC states: `PENDING_VERIFICATION` $\rightarrow$ `VERIFIED` or `REJECTED`. Only `VERIFIED` agents may book policies or receive commission disbursements. | `mst_Agent.aspx.cs:180`, `AllMaster.cs:1260` | Target `AgentService.update_kyc_status` | **MISSING** | Basic CRUD in Phase 15B; explicit KYC lifecycle state machine missing. |
| **LBR-146** | Sub-Franchise Hierarchy | Franchises support recursive parent-child associations via `ParentFranchiseId`. Sub-franchise commission splits roll up through the parent franchise. | `mst_Franchise.aspx.cs:210`, `API_Franchise` | Target `FranchiseService.get_hierarchy` | **MISSING** | Model column exists; recursive traversal query missing in REST contract. |
| **LBR-147** | Reference Master Immutability | Master lookup directories (`tbl_fueltype`, `tbl_financier`, `tbl_surveyor`) support active record filtering (`isdeleted = '0'`). Write/modification is restricted strictly to global admin roles. | `mst_FuelType.aspx.cs`, `mst_Financier.aspx.cs` | Target `MasterService` | **MISSING** | Dedicated lookup endpoints missing. |
| **LBR-148** | Cheque Lockout Enforcement | Users with uncleared cheques exceeding the operational grace threshold are blocked from logging in or booking new policies until cheques are cleared or approved by Admin. | `sp_LockChequeClearingCount`, `Adm_LockChequeEntry.aspx.cs` | `PaymentRepository.get_overdue_cheques` | **PARTIAL** | Cheque overdue queries exist in Phase 8/14; automated user login lockout partially deferred to Phase 16B. |

---

### 3. Quantitative Business Rule Summary
- **Total Business Rules Audited**: 14 rules
- **PARITY**: 5 rules (35.7%)
- **HARDENING**: 2 rules (14.3%)
- **PARTIAL**: 1 rule (7.1%)
- **MISSING**: 6 rules (42.9%)
- **LEGACY DEFECT MITIGATED**: 0 additional (carried forward)
- **UNKNOWN**: 0
