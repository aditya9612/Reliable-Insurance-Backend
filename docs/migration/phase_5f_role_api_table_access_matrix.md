# Phase 5F — Role → API → Table → CRUD → Branch/Owner Access Matrix

**Phase:** 5F — Role / API / Table / CRUD / Branch / Owner Access Audit  
**Mode:** STRICT READ-ONLY AUDIT  
**Date:** 2026-10-06  
**Legacy Reference:** `InsurancefinalNew` (.NET 4.0 WebForms + ASMX) & `brahmainsurance` MySQL reference schema  
**Target FastAPI Runtime:** `Reliable-Insurance-Backend` (`localhost:3306/reliable_insurance_dev`)

---

## 1. Executive Summary & Architectural Reality

A comprehensive static and schema-level audit of the legacy C# codebase (`574` `Clerk/*.aspx.cs` files, `40` root `*.aspx.cs` files, `287` `[WebMethod]` endpoints in `Service.asmx.cs`, `1,874` `DAL_Operations.cs` methods) and the legacy MySQL role/privilege catalog (`tbl_userrole`, `tbl_user`, `tbl_role_privilege`, `tbl_menutable`, `tbl_appclientlogin`) reveals a fundamental architectural split between **UI Menu Visibility** and **Server-Side Access Control**:

1. **56 Defined Roles vs. 13 Previously Documented:** `tbl_userrole` contains **56 distinct roles** (`UserRoleId` `1` through `57`, with `25` absent), of which **38 roles** are assigned to at least one user in `tbl_user` (`3,818` total users; `2,916` active, `902` soft-deleted) and **37 roles** have menu privileges mapped in `tbl_role_privilege` (`936` active privilege mappings across `267` menu items in `tbl_menutable`). Additionally, three external/non-`tbl_user` identity tables exist: `tbl_appclientlogin` (`sp_AppClientUSer`), `tbl_customer` (`sp_ChkloginCustomer`), and `tbl_appsignupcustomer` (`sp_ChkloginRefCustomer`).
2. **Legacy WebForms (`Clerk/*.aspx.cs`) Enforces Menu Hiding Only — Zero URL Authorization:**
   - `Clerk/Clerk.Master.cs` calls `sp_select_assigned_privileges(ROLE_ID, BranchId)` (`tbl_role_privilege` joined with `tbl_menutable`) solely to populate the HTML navigation bar (`Menu1`).
   - Individual `.aspx.cs` pages in `Clerk/` only check `if (Session["UserRole"] == null) Response.Redirect("~/Log_Out.aspx");` (authentication check), and **60 pages in `Clerk/` omit even the session null check**.
   - **No page in `Clerk/` verifies whether the logged-in user's `RoleId` is granted access to that URL in `tbl_role_privilege`.** Any authenticated staff user who knows the URL (e.g., `Clerk/adm_UpdateCustomer.aspx`, `Clerk/adm_DeletePolicyTransaction.aspx`, `Clerk/CashierApprovalNew.aspx`, `Clerk/OwnerApproval.aspx`) can invoke it directly.
   - Where `Session["UserRole"]` or `Session["RoleId"]` is inspected inside `.aspx.cs` code-behind (`~45` pages), it is used for **data scoping or UI control toggling** (e.g., filtering sales/agent dropdowns, scoping grid queries, or toggling `btn_Export.Visible`), not page-level access denial.
3. **Legacy Mobile API (`Service.asmx.cs`) Has Zero Authentication or Role Enforcement:**
   - All **287 `[WebMethod]` endpoints** in `Service.asmx.cs` are stateless and unauthenticated (`Session` is never checked; no token or header validation exists).
   - Every mobile API trusts caller-supplied `AgentId`, `SalesExecutiveId`, `EmpId`, `UserId`, `UserRoleId`, `FranchaiseId`, `APPCustomerId`, `TransID`, or `QuatationId`.
4. **Zero Users Have `BranchId = 0` or `NULL` in `tbl_user`:**
   - All `3,818` rows in `tbl_user` have `BranchId >= 1` (`BranchId = 1` is Head Office with `3,713` users; `BranchId = 2..11` are regional/franchise branches). Cross-branch privilege in legacy is determined by role or specific page/SP behavior, never by `BranchId = 0`.

---

## 2. Complete Role Catalog (`tbl_userrole` & External Principal Types)

### 2.1 Staff, Agent, Franchise & Hierarchy Roles (`tbl_userrole` + `tbl_user`)

| Role ID | `UserRole` (Exact DB String) | `RoleCode` | `role_deleted` | Total Users (`tbl_user`) | Active (`deleted=0`) | Deleted (`deleted=1`) | App Users (`isappuser=1`) | `BranchId` Range in `tbl_user` | Menu Screens (Branch 1 / All) | Primary Domain Category | Evidence Confidence |
|---:|---|---|---:|---:|---:|---:|---:|---|---:|---|---|
| **1** | `OWNER` | `OWN` | 0 | 0* | 0* | 0 | 0 | N/A (`UserId=202` hardcoded in `Log_In.aspx.cs`) | 109 / 192 | Executive / Owner | `VERIFIED` |
| **2** | `ADMIN` | `ADM` | 0 | 15 | 7 | 8 | 0 | `1` – `6` | 241 / 243 | System / Branch Admin | `VERIFIED` |
| **3** | `SUPERVISOR` | `SUP` | 0 | 0 | 0 | 0 | 0 | — | 7 / 7 | Legacy Unused | `VERIFIED` |
| **4** | `AGENT` | `AGT` | 0 | 3,018 | 2,473 | 545 | 3,018 | `1` – `2` | 0 / 0 | Mobile POSP / Agent (`tbl_agent`) | `VERIFIED` |
| **5** | `RELATIONSHIP MANAGER` | `RSM` | 0 | 312 | 68 | 244 | 157 | `1` – `2` | 20 / 26 | Sales Executive (`tbl_employee`) | `VERIFIED` |
| **6** | `OPERATOR` | `OPT` | 0 | 146 | 67 | 79 | 3 | `1` – `9` | 42 / 49 | Back-Office Policy & Customer Entry | `VERIFIED` |
| **7** | `CASHIER` | `CASH` | 0 | 1 | 0 | 1 | 0 | `1` | 1 / 1 | Cashier Payment Approval | `VERIFIED` |
| **8** | `MANAGER` | `MGR` | 0 | 0 | 0 | 0 | 0 | — | 1 / 1 | Legacy Unused | `VERIFIED` |
| **9** | `FRANCHISE` | `FRN` | 0 | 70 | 31 | 39 | 0 | `1` – `11` | 18 / 28 | Franchise Partner (`tbl_franchaise`) | `VERIFIED` |
| **10** | `SALES` | `SAL` | 0 | 0 | 0 | 0 | 0 | — | 0 / 0 | Legacy Unused | `VERIFIED` |
| **11** | `ACCOUNT` | `ACC` | 0 | 15 | 2 | 13 | 0 | `1` – `2` | 133 / 160 | Accounting, Ledger, Payouts, Masters | `VERIFIED` |
| **12** | `ENDORSEMENT` | `END` | 0 | 1 | 1 | 0 | 0 | `1` | 14 / 14 | Policy Endorsement Processing | `VERIFIED` |
| **13** | `CLAIM` | `CLM` | 0 | 2 | 1 | 1 | 0 | `1` | 6 / 6 | Motor Claims Management | `VERIFIED` |
| **14** | `QUOT CO-ORDINATOR` | `QUT` | 0 | 2 | 0 | 2 | 0 | `1` | 8 / 8 | Mobile Quotation Coordination | `VERIFIED` |
| **15** | `INSP CO-ORDINATION` | `INS` | 0 | 1 | 1 | 0 | 0 | `1` | 9 / 9 | Vehicle Inspection Coordination | `VERIFIED` |
| **16** | `FRANCHISE AGENT` | `FAGT` | 0 | 60 | 59 | 1 | 60 | `1` – `9` | 0 / 0 | Sub-Agent under Franchise | `VERIFIED` |
| **17** | `POLICY BAZAR` | `PBZ` | 1 | 1 | 1 | 0 | 0 | `1` | 1 / 1 | Aggregator Partner (Role Soft-Deleted) | `VERIFIED` |
| **18** | `POLICY BAZAR AGENT` | `PBAG` | 1 | 1 | 1 | 0 | 1 | `1` | 0 / 0 | Aggregator Agent (Role Soft-Deleted) | `VERIFIED` |
| **19** | `OPERATOR HEAD` | `OH` | 0 | 1 | 0 | 1 | 0 | `1` | 30 / 30 | Operations Supervisor | `VERIFIED` |
| **20** | `FRANCHISE SALES EXECUTIVE` | `FSE` | 0 | 4 | 2 | 2 | 2 | `4` – `9` | 1 / 2 | Sales Executive under Franchise | `VERIFIED` |
| **21** | `HOD` | `HOD` | 0 | 2 | 0 | 2 | 0 | `1` | 3 / 3 | Head of Department | `VERIFIED` |
| **22** | `BACK OFFICE` | `BO` | 0 | 0 | 0 | 0 | 0 | — | 0 / 0 | Legacy Unused | `VERIFIED` |
| **23** | `CLAIM` | `CLA` | 0 | 0 | 0 | 0 | 0 | — | 0 / 0 | Duplicate Claim Role (Unused) | `VERIFIED` |
| **24** | `LOCATION HEAD` | `LCHD` | 0 | 8 | 2 | 6 | 0 | `1` | 26 / 26 | Branch / Location Manager (`tbl_employee`) | `VERIFIED` |
| **26** | `HR` | `HR` | 0 | 5 | 0 | 5 | 0 | `1` | 15 / 15 | Human Resources / Employee Onboarding | `VERIFIED` |
| **27** | `ACCOUNT HEAD` | `ACH` | 0 | 1 | 0 | 1 | 0 | `1` | 51 / 51 | Senior Accounting / Approvals | `VERIFIED` |
| **28** | `IT SUPPORT` | `ITS` | 0 | 12 | 5 | 7 | 0 | `1` | 123 / 123 | Technical Support / Master & Policy Admin | `VERIFIED` |
| **29** | `SHREYANSH OWNER` | `SHRO` | 0 | 0 | 0 | 0 | 0 | — | 16 / 16 | Partner Owner View | `VERIFIED` |
| **30** | `CallIng Employee` | `CE` | 0 | 1 | 1 | 0 | 0 | `1` | 2 / 2 | Telecalling / Renewal Follow-up | `VERIFIED` |
| **31** | `Calling Indivisional` | `CI` | 0 | 0 | 0 | 0 | 0 | — | 0 / 0 | Legacy Unused | `VERIFIED` |
| **32** | `Insurance Exective` | `IE` | 0 | 93 | 76 | 17 | 92 | `1` | 0 / 0 | Field / App Insurance Executive | `VERIFIED` |
| **33** | `ALL USER` | `AUSER` | 0 | 27 | 4 | 23 | 0 | `1` | 24 / 24 | Multi-Function Operator / Cross-Branch | `VERIFIED` |
| **34** | `pOLICY VIEW` | `PV` | 0 | 1 | 0 | 1 | 0 | `1` | 2 / 2 | Read-Only Policy / Transaction Viewer | `VERIFIED` |
| **35** | `Freelancer` | `FRL` | 0 | 2 | 2 | 0 | 0 | `1` | 20 / 20 | Freelance Policy Entry Operator | `VERIFIED` |
| **36** | `EMI` | `EMI` | 0 | 2 | 1 | 1 | 0 | `1` | 2 / 2 | EMI / Finance Coordinator | `VERIFIED` |
| **37** | `BUSINESS HEAD` | `BSH` | 0 | 1 | 0 | 1 | 0 | `1` | 9 / 9 | Hierarchy Level: Business Head | `VERIFIED` |
| **38** | `PRESIDENT` | `PRE` | 0 | 0 | 0 | 0 | 0 | — | 0 / 0 | Hierarchy Level: President | `VERIFIED` |
| **39** | `VICE PRESIDENT` | `VPR` | 0 | 0 | 0 | 0 | 0 | — | 0 / 0 | Hierarchy Level: Vice President | `VERIFIED` |
| **40** | `STATE HEAD` | `STH` | 0 | 1 | 0 | 1 | 0 | `1` | 4 / 4 | Hierarchy Level: State Head | `VERIFIED` |
| **41** | `TERRITORY HEAD` | `TRH` | 0 | 0 | 0 | 0 | 0 | — | 0 / 0 | Hierarchy Level: Territory Head | `VERIFIED` |
| **42** | `AREA HEAD` | `ARH` | 0 | 0 | 0 | 0 | 0 | — | 0 / 0 | Hierarchy Level: Area Head | `VERIFIED` |
| **43** | `ZONAL HEAD` | `ZNH` | 0 | 0 | 0 | 0 | 0 | — | 0 / 0 | Hierarchy Level: Zonal Head | `VERIFIED` |
| **44** | `REGIONAL HEAD` | `RGH` | 0 | 0 | 0 | 0 | 0 | — | 1 / 1 | Hierarchy Level: Regional Head | `VERIFIED` |
| **45** | `DEPUTY REGIONAL HEAD` | `DRH` | 0 | 0 | 0 | 0 | 0 | — | 0 / 0 | Hierarchy Level: Deputy Regional Head | `VERIFIED` |
| **46** | `PROCESS  HEAD` | `PRH` | 0 | 3 | 0 | 3 | 0 | `1` | 3 / 3 | Hierarchy Level: Process Head | `VERIFIED` |
| **47** | `GENERAL MANAGER` | `GM` | 0 | 0 | 0 | 0 | 0 | — | 0 / 0 | Hierarchy Level: General Manager | `VERIFIED` |
| **48** | `TEAM LEADER SALES` | `TLS` | 0 | 7 | 0 | 7 | 0 | `1` | 7 / 7 | Hierarchy Level: Team Leader Sales | `VERIFIED` |
| **49** | `CIRCLE HEAD` | `CRH` | 0 | 0 | 0 | 0 | 0 | — | 0 / 0 | Hierarchy Level: Circle Head | `VERIFIED` |
| **50** | `DIVISION HEAD` | `DVH` | 0 | 0 | 0 | 0 | 0 | — | 1 / 1 | Hierarchy Level: Division Head | `VERIFIED` |
| **51** | `PROCESS MANAGER` | `PRM` | 0 | 2 | 0 | 2 | 0 | `1` | 4 / 4 | Hierarchy Level: Process Manager | `VERIFIED` |
| **52** | `FRANCHISE TYPE 2` | `FRT2` | 0 | 2 | 0 | 2 | 0 | `10` | 0 / 5 | Tier-2 Franchise (`tbl_franchaise`) | `VERIFIED` |
| **53** | `FRANCHISE TYPE 3` | `FRT3` | 0 | 3 | 1 | 2 | 0 | `1` – `11` | 8 / 8 | Tier-3 Franchise (`tbl_franchaise`) | `VERIFIED` |
| **54** | `FRANCHISE OPERATOR` | `FOPR` | 0 | 2 | 2 | 0 | 0 | `1` | 8 / 8 | Operator Scoped to Franchise | `VERIFIED` |
| **55** | `OTHER` | `OTH` | 0 | 14 | 12 | 2 | 0 | `1` | 5 / 5 | Limited Policy Entry / Endorsement | `VERIFIED` |
| **56** | `Broker partner` | `Brp` | 0 | 1 | 0 | 1 | 0 | `1` | 1 / 1 | External Broker Partner | `VERIFIED` |
| **57** | `CLUSTER HEAD` | `CLH` | 0 | 5 | 3 | 2 | 0 | `1` | 8 / 8 | Hierarchy Level: Cluster Head | `VERIFIED` |

*\*Note on `OWNER` (`UserRoleId = 1`): While 0 rows in `tbl_user` currently carry `UserRoleId = 1`, `Log_In.aspx.cs` (line 86) explicitly checks `if (UserId == 202) Response.Redirect("~/Clerk/OwnerDashBoard.aspx", false);` (where `UserId = 202` has `UserRoleId = 2` (`ADMIN`) in `tbl_user`), and `CashierApprovalNew.aspx.cs` / `Clerk.Master.cs` contain explicit branches for `ROLE == "OWNER"`.*

### 2.2 Non-`tbl_user` External / Mobile Principals

| Principal Type | Identity Table | Login Entry Point | Stored Procedure | Active Records | Scope Identifier | Evidence Confidence |
|---|---|---|---|---:|---|---|
| **External API Client** | `tbl_appclientlogin` | `Service.asmx.cs::CheckClientUserLogin` | `sp_AppClientUSer` | 1 (`ClientId=1`) | `ClientId` | `VERIFIED` |
| **Mobile Customer** | `tbl_customer` | `Service.asmx.cs::CheckLoginCustomer` | `sp_ChkloginCustomer` | 221,159 | `CustomerId` | `VERIFIED` |
| **Mobile Ref/Signup Customer** | `tbl_appsignupcustomer` | `Service.asmx.cs::CheckLoginRefCustomer` | `sp_ChkloginRefCustomer`, `sp_SignUpAppCustomer` | Dynamic | `APPCustomerId` | `VERIFIED` |

---

## 3. Legacy Authentication & Session Establishment Mechanisms

| Entry Point | Source File | Stored Procedure(s) | Identity Tables Read | Session / Response Context Set | Anomalies & Security Gaps | Evidence Confidence |
|---|---|---|---|---|---|---|
| **Web Portal Login** | `Log_In.aspx.cs` (`btn_logIn_ServerClick`) | `Sp_Checklogin`, `Sp_CheckloginfrFranchaise` (when `RoleId == 9`), `sp_CheckLoginForEmployee` (when `RoleId == 5` or `24`) | `tbl_user`, `tbl_userrole`, `tbl_branch`, `tbl_franchaise`, `tbl_employee` | `Session["UserId"]`, `Session["UserName"]`, `Session["RoleId"]`, `Session["UserRole"]`, `Session["BranchId"]`, `Session["BranchCode"]`, `Session["FranchaiseId"]` (if Franchise) | Rejects login if `IsAppUser == true` (`"Not Permitted to access Portal"`). Hardcodes `if (UserId == 202) Redirect("~/Clerk/OwnerDashBoard.aspx")`. | `VERIFIED` |
| **Web App / Secondary Login** | `AppLogin.aspx.cs` (`Submit1_ServerClick`) | `Sp_Checklogin` | `tbl_user`, `tbl_userrole`, `tbl_branch` | `Session["UserId"]`, `Session["RoleId"]`, `Session["UserRole"]`, `Session["BranchId"]` | **CRITICAL BACKDOOR (`AppLogin.aspx.cs:40`):** Hardcoded `if (txtUserName.Value == "AppAdmin" && txtPassword.Value == "Admin123")` bypasses DB check and sets `UserId=1, RoleId=2 (ADMIN), UserRole="ADMIN", BranchId=1`. | `VERIFIED` |
| **Master Page Menu Loader** | `Clerk/Clerk.Master.cs` (`Page_Load`) | `sp_select_assigned_privileges(ROLE_ID, BranchId)` | `tbl_role_privilege`, `tbl_menutable` | Renders `Menu1` items | **UI-ONLY:** Hides menu links not in `tbl_role_privilege`, but does **not** block direct URL requests to `Clerk/*.aspx`. | `VERIFIED` |
| **Mobile Agent / Staff Login** | `Service.asmx.cs::CheckLoginUser` | `sp_CheckLoginAppUser`, `sp_ChkloginEmp`, `sp_CheckloginforFranchaiseApp` | `tbl_user`, `tbl_agent`, `tbl_employee`, `tbl_franchaise` | Returns JSON (`UserId`, `AgentId`/`EmpId`/`FranchaiseId`, `UserRole`, `BranchId`, `IsWallate`, `IsCutPay`) | **Stateless & Unauthenticated Follow-up:** Returns user profile JSON, but issues **no token or session cookie**; subsequent `Service.asmx` calls trust caller-supplied IDs. | `VERIFIED` |
| **FastAPI JWT Login** | `app/api/v1/endpoints/auth.py` (`POST /api/v1/auth/login`) | SQLAlchemy `UserRepository.get_by_username_with_role` | `tbl_user`, `tbl_userrole` | Issues HS256 JWT (`sub=UserName`, `user_id`, `role`, `branch_id`) | Allows `isappuser=1` and `isappuser=0` to authenticate via JWT; does not yet populate `agent_id`, `emp_id`, or `franchise_id` claims in JWT. | `VERIFIED` |

---

## 4. Master Role → Entry Point → Business Operation → CRUD → Table → Scope Matrix

### Module A: Authentication & Session Management

| Legacy Entry Point / FastAPI Endpoint | Business Operation | CRUD | Table(s) | Stored Procedure(s) | Legacy UI Roles (`tbl_role_privilege`) | Legacy Server-Side Enforcement | Branch Scope | Owner / Agent Scope | FastAPI Status | Confidence |
|---|---|---|---|---|---|---|---|---|---|---|
| `Log_In.aspx.cs` | Portal Staff & Franchise Login | `R` | `tbl_user`, `tbl_userrole`, `tbl_branch`, `tbl_franchaise`, `tbl_employee` | `Sp_Checklogin`, `Sp_CheckloginfrFranchaise`, `sp_CheckLoginForEmployee` | All non-app roles (`isappuser=0`) | Blocks `isappuser=1`, `deleted=1` | Sets `Session["BranchId"]` | Sets `FranchaiseId` (`RoleId=9`) or `EmpId` (`RoleId=5,24`) | `POST /api/v1/auth/login` (Implemented; missing `FranchaiseId`/`EmpId`/`AgentId` lookup) | `VERIFIED` |
| `AppLogin.aspx.cs` | Alternate Portal Login | `R` | `tbl_user`, `tbl_userrole`, `tbl_branch` | `Sp_Checklogin` | All roles + hardcoded `AppAdmin` | Hardcoded backdoor credential (`AppLogin.aspx.cs:40`) | Sets `Session["BranchId"]` (`1` for backdoor) | Global if backdoor used | Eliminated in FastAPI | `VERIFIED` |
| `Service.asmx.cs::CheckLoginUser`, `CheckLoginUserNew` | Mobile App Login (Agent/RSM/IE/Franchise) | `R`, `U` | `tbl_user`, `tbl_agent`, `tbl_employee`, `tbl_franchaise` | `sp_CheckLoginAppUser`, `sp_ChkloginEmp`, `sp_CheckloginforFranchaiseApp`, `sp_UpdateFCMToken` | `AGENT (4)`, `RSM (5)`, `FRANCHISE (9)`, `FAGT (16)`, `FSE (20)`, `IE (32)`, `ADMIN (2)` | Checks `UserName`, `Password`, `deleted=0` | Returns `BranchId` | Returns `AgentId`, `EmpId`, `FranchaiseId` | Partially covered by `POST /api/v1/auth/login` | `VERIFIED` |
| `Service.asmx.cs::CheckLoginCustomer`, `CheckLoginRefCustomer`, `SignUpAppCustomer` | Customer Mobile App Login & Signup | `C`, `R` | `tbl_customer`, `tbl_appsignupcustomer` | `sp_ChkloginCustomer`, `sp_ChkloginRefCustomer`, `sp_SignUpAppCustomer` | Mobile Customer (`tbl_customer` / `tbl_appsignupcustomer`) | Checks mobile/password | Unscoped (`0`) | Scoped to `CustomerId` / `APPCustomerId` | Not Implemented | `VERIFIED` |
| `Service.asmx.cs::ChangePassword`, `ForgetPassword` | Mobile Password Reset / Change | `R`, `U` | `tbl_user`, `tbl_agent` | `sp_ChangePassword`, `sp_ForgetPassword` | Any mobile caller | **Unauthenticated (`Service.asmx`)** | Unscoped | Caller-supplied `UserId` / `Email` | Not Implemented | `VERIFIED` |
| `GET /api/v1/auth/me` | Current Authenticated Profile | `R` | `tbl_user`, `tbl_userrole` | N/A (ORM) | All JWT-authenticated users | `Depends(get_current_user)` | Returns `current_user.BranchId` | Returns `current_user.UserId` | Implemented | `VERIFIED` |
| `GET /api/v1/auth/admin-check` | Admin Role Verification Probe | `R` | `tbl_user`, `tbl_userrole` | N/A (ORM) | `ADMIN`, `OWNER`, `SUPERADMIN` | `Depends(require_roles("ADMIN", "OWNER", "SUPERADMIN"))` | Unscoped | N/A | Implemented | `VERIFIED` |

---

### Module B: Customer Management (`tbl_customer`)

| Legacy Entry Point / FastAPI Endpoint | Business Operation | CRUD | Table(s) | Stored Procedure(s) | Legacy UI Roles (`tbl_role_privilege`) | Legacy Server-Side Enforcement | Branch Scope | Owner / Agent Scope | FastAPI Status | Confidence |
|---|---|---|---|---|---|---|---|---|---|---|
| `Clerk/PolicyTransactionNew.aspx.cs` (`InsertNewCustomer`) | Create Customer during Policy Entry | `C`, `R` | `tbl_customer` | `sp_InsertCustomer`, `sp_generateCustomerCode` | `ADMIN (2)`, `OPERATOR (6)`, `FRANCHISE (9)`, `IT SUPPORT (28)`, `ALL USER (33)`, `Freelancer (35)`, `FRANCHISE OPERATOR (54)` | Session check only (`Session["UserRole"] != null`) | Writes `BranchId = Session["BranchId"]` | Writes `UpdateUser = Session["UserId"]` | `POST /api/v1/customers` (Implemented; **Gap:** allows any authenticated role via `get_current_user`) | `VERIFIED` |
| `Clerk/PE_TransactionEntry.aspx.cs` (`InsertNewCustomer`) | Create Customer during Quick Policy Intake | `C`, `R` | `tbl_customer` | `sp_InsertCustomer`, `sp_generateCustomerCode`, `Sp_GetMaxCustId` | `ADMIN (2)`, `OPERATOR (6)`, `FRANCHISE (9)`, `OPERATOR HEAD (19)`, `IT SUPPORT (28)`, `ALL USER (33)`, `Freelancer (35)`, `FRANCHISE TYPE 2/3 (52,53)`, `FRANCHISE OPERATOR (54)`, `OTHER (55)` | Session check only | Writes `BranchId = Session["BranchId"]` | Writes `UpdateUser = Session["UserId"]` | Covered by `POST /api/v1/customers` | `VERIFIED` |
| `Clerk/adm_UpdateCustomer.aspx.cs` (`btn_Submit_ServerClick`) | Search & Update Existing Customer | `R`, `U` | `tbl_customer` | `sp_SelectByCustomerName`, `sp_UpdateCustomer` | `ADMIN (2)`, `OPERATOR (6)`, `ALL USER (33)`, `Freelancer (35)` | Session check only | Search scoped by `Session["BranchId"]`; Update **overwrites** `BranchId = Session["BranchId"]` | Hardcodes `UpdateUser = "1"` in legacy C#! | `PUT /api/v1/customers/{customer_id}` (Implemented; preserves `BranchId`, sets `UpdateUser = str(current_user.UserId)`) | `VERIFIED` |
| `Clerk/adm_DeleteCustvehdetails.aspx.cs` | Delete Customer & Vehicle Details | `R`, `D` (Soft) | `tbl_customer`, `tbl_custvehicle`, `tbl_vehicledetails` | `sp_SelectCustvehicledetailsfill`, `sp_DeleteCustvehicleDetailsbyCustvehId` | `ADMIN (2)` only in `tbl_role_privilege` | Session check only (any role can browse URL) | **All Branches** (no `BranchId` filter in SP) | None | Not Implemented | `VERIFIED` |
| `Clerk/SearchMethods.aspx.cs::GetCustName`, `GetCustomerName` | Autocomplete Customer Name Search | `R` | `tbl_customer` | `sp_SearchCustName`, `sp_SelectByCustName` | All authenticated portal users | Reads `HttpContext.Current.Session["BranchId"]` (throws NRE if no session) | Strict `Session["BranchId"]` filter | None | Repository method `search_by_name` exists; REST endpoint pending | `VERIFIED` |
| `Clerk/SearchMethods.aspx.cs::GetCustomerDetails` | Fetch Single Customer by `CustomerId` | `R` | `tbl_customer` | `sp_SelectCustomerById` | All authenticated portal users | Reads `Session["BranchId"]` | Strict `Session["BranchId"]` filter | None | Repository `get_by_id` exists; `GET /api/v1/customers/{id}` pending | `VERIFIED` |

---

### Module C: Vehicle Management (`tbl_custvehicle`, `tbl_vehicledetails`)

| Legacy Entry Point / FastAPI Endpoint | Business Operation | CRUD | Table(s) | Stored Procedure(s) | Legacy UI Roles (`tbl_role_privilege`) | Legacy Server-Side Enforcement | Branch Scope | Owner / Agent Scope | FastAPI Status | Confidence |
|---|---|---|---|---|---|---|---|---|---|---|
| `Clerk/PolicyTransactionNew.aspx.cs` (`InsertVehicleDetails` / `UpdateVehicleDetails`) | Create or Update Vehicle during Policy Entry | `C`, `R`, `U` | `tbl_custvehicle` (`tbl_vehicledetails`) | `sp_CheckRegistrationNoNew`, `Sp_VehicleDetails_2026`, `Sp_UpdateVehicleDetails` | `ADMIN (2)`, `OPERATOR (6)`, `FRANCHISE (9)`, `IT SUPPORT (28)`, `ALL USER (33)`, `Freelancer (35)`, `FRANCHISE OPERATOR (54)` | Session check only | Writes `BranchId = Session["BranchId"]` on create/update; `sp_CheckRegistrationNoNew` checks across **all branches** (`deleted=0 AND FinancialYear=@FY`) | Writes `UpdateUser = Session["UserId"]` | `POST /api/v1/customers/{id}/vehicles`, `PUT /api/v1/customers/{id}/vehicles/{veh_id}` (Implemented; enforces branch match + `sp_CheckRegistrationNo` renewal parity) | `VERIFIED` |
| `Clerk/PE_TransactionEntry.aspx.cs` (`InsertVehicleDetails`) | Create or Update Vehicle during Quick Intake | `C`, `R`, `U` | `tbl_custvehicle` | `sp_CheckRegistrationNo`, `Sp_VehicleDetails`, `Sp_UpdateVehicleDetails` | Same as Quick Intake above | Session check only | Writes `BranchId = Session["BranchId"]` | Writes `UpdateUser = Session["UserId"]` | Covered by `POST/PUT /api/v1/customers/{id}/vehicles` | `VERIFIED` |
| `Clerk/adm_UpdateVehicleDetails.aspx.cs` | Standalone Vehicle Search & Update | `R`, `U` | `tbl_custvehicle`, `tbl_customer` | `sp_SelectByVehiclenew`, `sp_UpdateCustVehicleDetails` | `ADMIN (2)`, `OPERATOR (6)`, `IT SUPPORT (28)`, `ALL USER (33)`, `Freelancer (35)` | Session check only | **UNSCOPED IN LEGACY:** `sp_SelectByVehiclenew` has no `BranchId` filter; `CustVehicle.BranchId` assignment is commented out (`adm_UpdateVehicleDetails.aspx.cs:204`) | Hardcodes `UpdateUser = "1"` | FastAPI `PUT /api/v1/customers/{id}/vehicles/{veh_id}` hardens this by enforcing branch isolation (`existing.BranchId == current_user.BranchId` unless admin) | `VERIFIED` |
| `Clerk/SearchMethods.aspx.cs::GetCustByVehicleNo` | Lookup Customer & Vehicle by Reg No | `R` | `tbl_custvehicle`, `tbl_customer` | `sp_SelectByVehicle` | Portal users (intended) | **UNAUTHENTICATED `[WebMethod]`:** Passes hardcoded `BranchId = 0`, never accesses `Session`! | **All Branches (`BranchId = 0`)** | None | Not Implemented as REST endpoint yet | `VERIFIED` |
| `AppSearchMethod.aspx.cs::checkVehicleNo` | Check Vehicle Reg No Duplicate | `R` | `tbl_custvehicle` | `sp_CheckRegistrationNo` | Mobile / Web callers | **UNAUTHENTICATED `[WebMethod]`** | **All Branches** | None | Handled inside `VehicleService` | `VERIFIED` |
| `VehicleService.asmx.cs::GetVehicleDetails` | Third-Party Vahan / Signzy RC Lookup & Cache | `C`, `R` | `tbl_signzyvehicledata` | `sp_InsertSignzyVehicleData`, `sp_GetSignzyVehicleData` | Mobile / Web callers | **UNAUTHENTICATED `[WebMethod]`** | Unscoped | None | Pending Phase 12 | `VERIFIED` |

---

### Module D: Policy & Transaction Lifecycle (`tbl_transaction`, `tbl_transactionappnew`)

| Legacy Entry Point / FastAPI Endpoint | Business Operation | CRUD | Table(s) | Stored Procedure(s) | Legacy UI Roles (`tbl_role_privilege`) | Legacy Server-Side Enforcement | Branch Scope | Owner / Agent Scope | FastAPI Status | Confidence |
|---|---|---|---|---|---|---|---|---|---|---|
| `Clerk/PE_TransactionEntry.aspx.cs` | Stage 1 Policy Intake / Underwriting Entry | `C`, `R`, `U` | `tbl_transaction`, `tbl_transactionpayment`, `tbl_customer`, `tbl_custvehicle`, `tbl_accountdetails` | `sp_InsertPolicyTransactionEntry`, `sp_UpdatePolicyTransactionEntry`, `sp_InsertTransactionPayment`, `sp_InsertAccountDetails` | `ADMIN (2)`, `OPERATOR (6)`, `FRANCHISE (9)`, `OPERATOR HEAD (19)`, `IT SUPPORT (28)`, `ALL USER (33)`, `Freelancer (35)`, `FRANCHISE TYPE 2/3 (52,53)`, `FRANCHISE OPERATOR (54)`, `OTHER (55)` | Session check; checks `RoleId == 9, 52, 53, 54` to lock `FranchaiseId` dropdown | `Session["BranchId"]` | Franchise roles locked to `Session["FranchaiseId"]`; Operator/Admin can select any Agent & Sales Exec in branch | Pending Phase 7 | `VERIFIED` |
| `Clerk/PolicyTransactionNew.aspx.cs` | Full Policy Booking & Verification (`TStatus` progression) | `C`, `R`, `U` | `tbl_transaction`, `tbl_transactionpayment`, `tbl_accountdetails`, `tbl_customer`, `tbl_custvehicle` | `sp_InsertTransactionNew_2026`, `sp_UpdateTransactionNew_2026`, `sp_SelectTransactionById` | `ADMIN (2)`, `OPERATOR (6)`, `FRANCHISE (9)`, `IT SUPPORT (28)`, `ALL USER (33)`, `Freelancer (35)`, `FRANCHISE OPERATOR (54)` | Session check; checks `Session["UserRole"]` for `FRANCHISE` vs `ADMIN`/`OPERATOR` field locking | `Session["BranchId"]` | `UserId = Session["UserId"]`; Franchise locked to own franchise agents | Pending Phase 7 | `VERIFIED` |
| `Clerk/adm_DeletePolicyTransaction.aspx.cs`, `adm_DeleteTransactionEntry.aspx.cs` | Soft-Delete Policy Transaction & Ledger Reversal | `R`, `U`, `D` (Soft) | `tbl_transaction`, `tbl_transactionpayment`, `tbl_accountdetails` | `sp_DeleteTransactionByTransId`, `sp_DeleteTransactionEntryByTransId` | `ADMIN (2)`, `ACCOUNT (11)`, `IT SUPPORT (28)` | Session check only (**Any authenticated user can browse URL**) | `Session["BranchId"]` | Records `DeleteUser = Session["UserId"]` | Pending Phase 7 | `VERIFIED` |
| `Service.asmx.cs::InsertAppTransactionNew`, `InsertAppTransaction_2026` | Mobile App Policy Proposal Submission | `C`, `R`, `U` | `tbl_transactionappnew`, `tbl_transaction`, `tbl_accountdetails` | `sp_InsertAppTransactionNew`, `sp_InsertTransactionFromApp` | Mobile `AGENT (4)`, `RSM (5)`, `FAGT (16)`, `IE (32)` | **UNAUTHENTICATED (`Service.asmx`)** | Derived from Agent/Employee `BranchId` | Caller-supplied `AgentId`, `SalesExecutiveId`, `FranchaiseId` | Pending Phase 7 / 15 | `VERIFIED` |
| `Service.asmx.cs::DeleteCustomerPolicyInfo` | Delete Mobile Customer Policy Record | `D` | `tbl_customerpolicyinfo` | `sp_DeleteCustomerPolicyInfo` | Mobile App user | **UNAUTHENTICATED (`Service.asmx`)** | Unscoped | Caller-supplied `Id` (IDOR) | Pending Phase 7 | `VERIFIED` |

---

### Module E: Financial Approvals, Payments, Cheques, Wallet & InstaPay

| Legacy Entry Point / FastAPI Endpoint | Business Operation | CRUD | Table(s) | Stored Procedure(s) | Legacy UI Roles (`tbl_role_privilege`) | Legacy Server-Side Enforcement | Branch Scope | Owner / Agent Scope | FastAPI Status | Confidence |
|---|---|---|---|---|---|---|---|---|---|---|
| `Clerk/CashierApprovalNew.aspx.cs` | Cashier Payment Verification (`IsCashierApprove`) | `R`, `U` | `tbl_transaction`, `tbl_transactionpayment` | `sp_UpdateCashierApproval`, `sp_SelectCashierApprovalGrid` | `ADMIN (2)`, `CASHIER (7)`, `FRANCHISE (9)`, `ACCOUNT (11)`, `ACCOUNT HEAD (27)`, `IT SUPPORT (28)` | Session check; inspects `ROLE == "OWNER" \| "ADMIN" \| "ACCOUNT"` vs `"FRANCHISE"` for grid filtering | `ADMIN`/`OWNER`/`ACCOUNT` can view all or branch; `FRANCHISE` scoped to `FranchaiseId` | Approver `UserId` logged | Pending Phase 8 | `VERIFIED` |
| `Clerk/AccountantApproval.aspx.cs` | Accountant Policy & Commission Approval (`IsAccountantApprove`) | `R`, `U` | `tbl_transaction`, `tbl_accountdetails` | `sp_UpdateAccountantApproval`, `sp_SelectAccountantApproval` | `ADMIN (2)`, `ACCOUNT (11)`, `ACCOUNT HEAD (27)`, `IT SUPPORT (28)` | Session check only (**No role check in `Page_Load`**) | `Session["BranchId"]` / All Branches | Approver `UserId` logged | Pending Phase 8 / 9 | `VERIFIED` |
| `Clerk/OwnerApproval.aspx.cs`, `OwnerPaymentApproval.aspx.cs` | Owner High-Value / Discount / Payout Approval (`IsOwnerApprove`) | `R`, `U` | `tbl_transaction`, `tbl_accountdetails`, `tbl_paymentrequest` | `sp_UpdateOwnerApproval`, `sp_UpdateOwnerPaymentApproval` | `OWNER (1)`, `ADMIN (2)`, `SHREYANSH OWNER (29)` | Session check only (**No role check in `Page_Load`**) | **All Branches** | Global | Pending Phase 8 / 9 | `VERIFIED` |
| `Clerk/AgentCommisionApproval.aspx.cs`, `AgentCommissionUseWallet.aspx.cs` | Agent Commission Computation, Wallet Credit & Cut-and-Pay | `C`, `R`, `U` | `tbl_transaction`, `tbl_accountdetails`, `tbl_agent`, `tbl_wallettransaction` | `sp_UpdateAgentCommissionApproval`, `sp_InsertAccountDetails`, `sp_UpdateAgentWalletBalance` | `OWNER (1)`, `ADMIN (2)`, `ACCOUNT (11)`, `ACCOUNT HEAD (27)`, `IT SUPPORT (28)` | Session check only | `Session["BranchId"]` / All Branches | Credits/Debits target `AgentId` ledger (`AccTransId = 1, 2, 3`) | Pending Phase 9 | `VERIFIED` |
| `Clerk/EWalletApproval.aspx.cs`, `FranchiseWallateApproval.aspx.cs` | Agent / Franchise E-Wallet Top-up & Withdrawal Approval | `C`, `R`, `U` | `tbl_walletrequest`, `tbl_accountdetails`, `tbl_agent`, `tbl_franchaise` | `sp_ApproveEWalletRequest`, `sp_ApproveFranchiseWallet` | `OWNER (1)`, `ADMIN (2)`, `ACCOUNT (11)`, `ACCOUNT HEAD (27)` | Session check only | **All Branches** | Updates target `AgentId` / `FranchaiseId` | Pending Phase 8 / 9 | `VERIFIED` |
| `Clerk/ChequeClearance.aspx.cs`, `ChequeBounce.aspx.cs` | Cheque Clearance / Bounce Reversal & Penalty | `C`, `R`, `U` | `tbl_transactionpayment`, `tbl_transaction`, `tbl_accountdetails` | `sp_UpdateChequeStatus`, `sp_InsertChequeBouncePenalty` | `ADMIN (2)`, `ACCOUNT (11)`, `ACCOUNT HEAD (27)`, `IT SUPPORT (28)` | Session check only | `Session["BranchId"]` | Impacts `AgentId` ledger | Pending Phase 8 | `VERIFIED` |
| `Service.asmx.cs::AccountPaymentMsg`, `ProcessToInstaPay` | Instant Payout / Bank Transfer Trigger (InstaPay) | `C`, `R`, `U` | `tbl_instapaytransaction`, `tbl_accountdetails`, `tbl_paymentrequest` | `sp_InsertInstaPayLog`, `sp_UpdatePaymentRequestStatus` | Intended for `ADMIN`/`OWNER`/`ACCOUNT` or Agent Request | **CRITICAL: Unauthenticated `[WebMethod]` in `Service.asmx.cs`!** | Unscoped | Caller-supplied parameters | Pending Phase 9 | `VERIFIED` |

---

### Module F: Agent, Franchise, POSP & Employee Management

| Legacy Entry Point / FastAPI Endpoint | Business Operation | CRUD | Table(s) | Stored Procedure(s) | Legacy UI Roles (`tbl_role_privilege`) | Legacy Server-Side Enforcement | Branch Scope | Owner / Agent Scope | FastAPI Status | Confidence |
|---|---|---|---|---|---|---|---|---|---|---|
| `Clerk/mst_Agent.aspx.cs`, `mst_FranchiseAgent.aspx.cs` | Create / Update Agent & Auto-Provision `tbl_user` (`RoleId=4` or `16`) | `C`, `R`, `U`, `D` (Soft) | `tbl_agent`, `tbl_user` | `sp_InsertAgent`, `sp_UpdateAgent`, `sp_InsertUser` | `OWNER (1)`, `ADMIN (2)`, `RELATIONSHIP MANAGER (5)`, `OPERATOR (6)`, `FRANCHISE (9)`, `ACCOUNT (11)`, `OPERATOR HEAD (19)`, `LOCATION HEAD (24)`, `HR (26)`, `IT SUPPORT (28)`, `ALL USER (33)`, `FRANCHISE TYPE 3 (53)` | Session check; if `Session["UserRole"] == "RELATIONSHIP MANAGER"`, locks `SalesExecutiveId` to own `EmpId`; if `FRANCHISE`, locks `FranchaiseId` | `Session["BranchId"]` | `RSM (5)` owns created agents (`SalesExecutiveId`); `FRANCHISE (9)` owns franchise agents (`FranchaiseId`) | Pending (Repository `AgentRepository` exists) | `VERIFIED` |
| `Clerk/mst_Employee.aspx.cs`, `HierarchyEmployee.aspx.cs` | Create / Update Employee & Sales Hierarchy (`tbl_employee`, `tbl_user`) | `C`, `R`, `U`, `D` (Soft) | `tbl_employee`, `tbl_user` | `sp_InsertEmployee`, `sp_UpdateEmployee`, `sp_InsertHierarchyEmployee` | `OWNER (1)`, `ADMIN (2)`, `ACCOUNT (11)`, `HR (26)`, `IT SUPPORT (28)` | Session check only | `Session["BranchId"]` / All Branches | Reporting manager `ParentEmpId` hierarchy | Pending | `VERIFIED` |
| `Clerk/mst_Franchaise.aspx.cs` | Create / Update Franchise Partner (`tbl_franchaise`, `tbl_user`) | `C`, `R`, `U` | `tbl_franchaise`, `tbl_user`, `tbl_branch` | `sp_InsertFranchaise`, `sp_UpdateFranchaise` | `OWNER (1)`, `ADMIN (2)`, `ACCOUNT (11)`, `IT SUPPORT (28)` | Session check only | Assigns dedicated `BranchId` | Creates `RoleId=9, 52, 53` user | Pending | `VERIFIED` |
| `Service.asmx.cs::InsertPOSPRegistration`, `UpdateAgentProfile`, `GetAgentListBySalesExec` | Mobile POSP Onboarding, KYC Upload & RSM Agent Roster | `C`, `R`, `U` | `tbl_agent`, `tbl_user`, `tbl_pospdocument` | `sp_InsertPOSPAgent`, `sp_SelectAgentBySalesExecId` | Mobile `RSM (5)`, `AGENT (4)`, `FRANCHISE (9)`, `FSE (20)`, `IE (32)` | **UNAUTHENTICATED (`Service.asmx`)** | Caller-supplied `BranchId` | Caller-supplied `SalesExecutiveId` / `AgentId` | Pending | `VERIFIED` |

---

### Module G: Quotation, IDV, Inspection & Break-In Coordination

| Legacy Entry Point / FastAPI Endpoint | Business Operation | CRUD | Table(s) | Stored Procedure(s) | Legacy UI Roles (`tbl_role_privilege`) | Legacy Server-Side Enforcement | Branch Scope | Owner / Agent Scope | FastAPI Status | Confidence |
|---|---|---|---|---|---|---|---|---|---|---|
| `Clerk/QuotationCoordination.aspx.cs`, `QuotationReply.aspx.cs` | Review Mobile Quotation Requests & Upload Quote Comparisons | `C`, `R`, `U` | `tbl_appquotationrequest`, `tbl_quotationreply` | `sp_SelectQuotationRequest`, `sp_UpdateQuotationReply` | `OWNER (1)`, `ADMIN (2)`, `RELATIONSHIP MANAGER (5)`, `OPERATOR (6)`, `FRANCHISE (9)`, `QUOT CO-ORDINATOR (14)`, `OPERATOR HEAD (19)`, `LOCATION HEAD (24)`, `IT SUPPORT (28)`, `ALL USER (33)`, `PROCESS HEAD (46)`, `TEAM LEADER SALES (48)`, `PROCESS MANAGER (51)`, `CLUSTER HEAD (57)` | Session check; `RSM (5)` and Hierarchy roles (`37–57`) filtered by `EmpId` / reporting tree | `Session["BranchId"]` or Hierarchy | `RSM` sees own agents' quotes; `QUOT CO-ORDINATOR (14)` & `ADMIN (2)` see all | Pending Phase 6 | `VERIFIED` |
| `Clerk/InspectionCoordination.aspx.cs` | Break-in Vehicle Inspection Scheduling & Status Update | `C`, `R`, `U` | `tbl_appinspection`, `tbl_transaction` | `sp_SelectInspectionRequests`, `sp_UpdateInspectionStatus` | `OWNER (1)`, `ADMIN (2)`, `RELATIONSHIP MANAGER (5)`, `OPERATOR (6)`, `FRANCHISE (9)`, `INSP CO-ORDINATION (15)`, `OPERATOR HEAD (19)`, `LOCATION HEAD (24)`, `IT SUPPORT (28)`, `ALL USER (33)` | Session check; `RSM (5)` scoped to own `EmpId` | `Session["BranchId"]` | `INSP CO-ORDINATION (15)` processes all branch inspections | Pending Phase 6 / 7 | `VERIFIED` |
| `Service.asmx.cs::InsertQuotationRequest`, `GetQuotationByAgentId`, `InsertInspectionRequest` | Mobile App Quote & Inspection Request Submission | `C`, `R`, `U` | `tbl_appquotationrequest`, `tbl_appinspection` | `sp_InsertAppQuotationRequest`, `sp_GetQuotationByAgent`, `sp_InsertAppInspection` | Mobile `AGENT (4)`, `RSM (5)`, `FAGT (16)`, `IE (32)` | **UNAUTHENTICATED (`Service.asmx`)** | Unscoped | Caller-supplied `AgentId` / `EmpId` | Pending Phase 6 | `VERIFIED` |

---

### Module H: Endorsements & Claims (`tbl_appendorsement`, `tbl_claims`)

| Legacy Entry Point / FastAPI Endpoint | Business Operation | CRUD | Table(s) | Stored Procedure(s) | Legacy UI Roles (`tbl_role_privilege`) | Legacy Server-Side Enforcement | Branch Scope | Owner / Agent Scope | FastAPI Status | Confidence |
|---|---|---|---|---|---|---|---|---|---|---|
| `Clerk/EndorsementEntry.aspx.cs`, `AppEndorsementList.aspx.cs` | Policy Endorsement Intake, Correction & Approval | `C`, `R`, `U` | `tbl_appendorsement`, `tbl_transaction`, `tbl_customer`, `tbl_custvehicle` | `sp_InsertEndorsement`, `sp_UpdateEndorsementStatus`, `sp_SelectEndorsementList` | `OWNER (1)`, `ADMIN (2)`, `RELATIONSHIP MANAGER (5)`, `OPERATOR (6)`, `FRANCHISE (9)`, `ACCOUNT (11)`, `ENDORSEMENT (12)`, `OPERATOR HEAD (19)`, `LOCATION HEAD (24)`, `IT SUPPORT (28)`, `ALL USER (33)`, `OTHER (55)` | Session check | `Session["BranchId"]` | `ENDORSEMENT (12)` & `ADMIN (2)` process across branch; `RSM (5)` views own team | Pending Phase 10 | `VERIFIED` |
| `Clerk/ClaimEntry.aspx.cs`, `ClaimStatusUpdate.aspx.cs` | Motor Claim Intimation, Surveyor Assignment & Settlement | `C`, `R`, `U` | `tbl_claims`, `tbl_claimdocument`, `tbl_transaction` | `sp_InsertClaimDetails`, `sp_UpdateClaimDetails`, `sp_SelectClaims` | `OWNER (1)`, `ADMIN (2)`, `RELATIONSHIP MANAGER (5)`, `FRANCHISE (9)`, `ACCOUNT (11)`, `CLAIM (13)`, `OPERATOR HEAD (19)`, `LOCATION HEAD (24)`, `IT SUPPORT (28)` | Session check | `Session["BranchId"]` / All Branches | `CLAIM (13)` manages full claim lifecycle | Pending Phase 10 | `VERIFIED` |
| `Service.asmx.cs::InsertAppEndorsement`, `InsertAppClaim`, `GetClaimListByAgent` | Mobile Endorsement & Claim Submission | `C`, `R` | `tbl_appendorsement`, `tbl_claims` | `sp_InsertAppEndorsement`, `sp_InsertAppClaim` | Mobile `AGENT (4)`, `RSM (5)`, `FAGT (16)`, `IE (32)` | **UNAUTHENTICATED (`Service.asmx`)** | Unscoped | Caller-supplied `AgentId` / `TransID` | Pending Phase 10 | `VERIFIED` |

---

### Module I: Master Data & Role/Privilege Administration

| Legacy Entry Point / FastAPI Endpoint | Business Operation | CRUD | Table(s) | Stored Procedure(s) | Legacy UI Roles (`tbl_role_privilege`) | Legacy Server-Side Enforcement | Branch Scope | Owner / Agent Scope | FastAPI Status | Confidence |
|---|---|---|---|---|---|---|---|---|---|---|
| `Clerk/mst_VehicleType.aspx.cs`, `mst_VehicleMake.aspx.cs`, `mst_VehicleModel.aspx.cs`, `mst_VehicleVariant.aspx.cs`, `mst_RTO.aspx.cs`, `mst_InsuranceCompany.aspx.cs` | Vehicle & Insurer Master CRUD | `C`, `R`, `U`, `D` (Soft) | `tbl_vehicle_type`, `tbl_vehicle_sub_type`, `tbl_vehicle_make`, `tbl_vehicle_model`, `tbl_vehicle_variants`, `tbl_rto`, `tbl_insurancecompany` | `sp_InsertVehicleMake`, `sp_UpdateVehicleMake`, `sp_InsertVehicleModel`, `sp_InsertVehicleVariant`, `sp_InsertRTO`, `sp_InsertInsuranceCompany`, etc. | `OWNER (1)`, `ADMIN (2)`, `OPERATOR (6)` (subset), `ACCOUNT (11)`, `IT SUPPORT (28)`, `ALL USER (33)` | Session check only (**No role check in `Page_Load`**) | Global (`BranchId` recorded as `1` or session branch on some tables, but read globally) | None | Models & Repositories complete (Phase 4B); REST APIs pending Phase 4C | `VERIFIED` |
| `Clerk/mst_User.aspx.cs`, `mst_UserRole.aspx.cs`, `RolePrivilege.aspx.cs` | User Account, Role & Menu Privilege Administration | `C`, `R`, `U`, `D` (Soft) | `tbl_user`, `tbl_userrole`, `tbl_role_privilege`, `tbl_menutable` | `sp_InsertUser`, `sp_UpdateUser`, `sp_InsertUserRole`, `sp_InsertRolePrivilege`, `sp_DeleteRolePrivilege` | `OWNER (1)`, `ADMIN (2)`, `IT SUPPORT (28)` (`mst_User` also in `ACCOUNT (11)`, `HR (26)`) | Session check only | `tbl_role_privilege` is keyed by `(RoleId, MenuId, BranchId)` | Global / Branch Admin | Pending | `VERIFIED` |

---

### Module J: Dashboards, MIS & Bulk Excel Exports

| Legacy Entry Point / FastAPI Endpoint | Business Operation | CRUD | Table(s) | Stored Procedure(s) | Legacy UI Roles (`tbl_role_privilege`) | Legacy Server-Side Enforcement | Branch Scope | Owner / Agent Scope | FastAPI Status | Confidence |
|---|---|---|---|---|---|---|---|---|---|---|
| `Clerk/OwnerDashBoard.aspx.cs`, `AdminDashboard.aspx.cs` | Executive Business & Collection Dashboards | `R` | `tbl_transaction`, `tbl_accountdetails`, `tbl_agent`, `tbl_employee` | `sp_GetOwnerDashboardCount`, `sp_GetAdminDashboardSummary` | `OWNER (1)`, `ADMIN (2)`, `SHREYANSH OWNER (29)` | Session check only | **All Branches** (`OwnerDashBoard`) or `Session["BranchId"]` | Global | Pending Phase 14 | `VERIFIED` |
| `Clerk/Adm_AllTransactionExport.aspx.cs` | Bulk Policy & Commission Excel Export | `R` | `tbl_transaction`, `tbl_customer`, `tbl_custvehicle`, `tbl_agent`, `tbl_employee`, `tbl_insurancecompany` | `sp_SelectAllTransactionExport`, `sp_SelectTransactionByFilter` | `OWNER (1)`, `ADMIN (2)`, `RELATIONSHIP MANAGER (5)`, `OPERATOR (6)`, `FRANCHISE (9)`, `ACCOUNT (11)`, `OPERATOR HEAD (19)`, `LOCATION HEAD (24)`, `ACCOUNT HEAD (27)`, `IT SUPPORT (28)`, `ALL USER (33)` | Inspects `Session["UserRole"]`: hides/shows export buttons or restricts dropdowns for `RSM (5)` and `FRANCHISE (9)` | `ADMIN (2)`/`OWNER (1)`/`ACCOUNT (11)`/`IT SUPPORT (28)`: All/Selected Branch; `FRANCHISE (9)`: own branch/franchise | `RSM (5)` restricted to own `EmpId` | Pending Phase 14 | `VERIFIED` |
| `Clerk/Adm_AllTransactionExportHierarchy.aspx.cs` | Hierarchy-Scoped Policy Export (`RoleId` 37–57) | `R` | `tbl_transaction`, `tbl_employee`, `tbl_agent` | `sp_SelectTransactionExportByHierarchy` | Hierarchy roles: `BUSINESS HEAD (37)`, `STATE HEAD (40)`, `REGIONAL HEAD (44)`, `PROCESS HEAD (46)`, `TEAM LEADER SALES (48)`, `DIVISION HEAD (50)`, `PROCESS MANAGER (51)`, `CLUSTER HEAD (57)` | Inspects `Session["UserId"]` / `EmpId` to traverse reporting hierarchy | Multi-Branch (follows employee reporting tree) | Scoped to subordinate `EmpId` and `AgentId` tree | Pending Phase 14 | `VERIFIED` |

---

### Module K: Document Upload, Image Viewing & ZIP Download

| Legacy Entry Point / FastAPI Endpoint | Business Operation | CRUD | Table(s) | Stored Procedure(s) | Legacy UI Roles (`tbl_role_privilege`) | Legacy Server-Side Enforcement | Branch Scope | Owner / Agent Scope | FastAPI Status | Confidence |
|---|---|---|---|---|---|---|---|---|---|---|
| `DownloadAll.ashx.cs` | Stream Multi-Document Policy/Claim/Vehicle ZIP Archive | `R` | `tbl_transaction`, `tbl_custvehicle`, `tbl_claims`, `tbl_agent` | `sp_SelectDocumentsByTransId` | Portal users | **UNAUTHENTICATED HTTP HANDLER (`DownloadAll.ashx`)**: Accepts `?TransId=...` or `?AgentId=...` with zero session check | Unscoped (IDOR) | Unscoped (IDOR) | Pending Phase 11 | `VERIFIED` |
| `ImageHandler.ashx.cs` | Raw File Read from Server Disk | `R` | File System (`HostingEnvironment.MapPath`) | None | Portal / Mobile users | **CRITICAL PATH TRAVERSAL / UNAUTHENTICATED FILE READ (`ImageHandler.ashx.cs:19`)**: `File.ReadAllBytes(HostingEnvironment.MapPath(context.Request["fileName"]))` with zero authentication | Unscoped | Unscoped | Must NEVER be replicated; use authenticated S3/MinIO presigned URLs in Phase 11 | `VERIFIED` |
| `Service.asmx.cs::UploadFile`, `SaveAppPolicyPDF`, `SaveAppPolicyImg`, `GetImageByID`, `GetPolicyPdfByID` | Mobile Document Upload & Retrieval | `C`, `R`, `U` | `tbl_transaction`, `tbl_appquotationrequest`, Disk (`~/AppPolicyPDF/`) | `sp_UpdatePolicyPDFPath`, `sp_GetPolicyPdfByTransId` | Mobile callers | **CRITICAL UNAUTHENTICATED UPLOAD/READ (`Service.asmx`)**: `UploadFile(byte[] f, string fileName)` writes arbitrary file names/bytes to `~/AppPolicyPDF/` without authentication | Unscoped | Caller-supplied `TransID` | Pending Phase 11 | `VERIFIED` |

---

## 5. Table-Centric CRUD Access Matrix

| Physical Table | Primary Domain | Create (`C`) Roles (Intended Business Scope) | Read (`R`) Roles | Update (`U`) Roles | Delete (`D` - Soft `deleted=1`) Roles | Branch Isolation Rule | Owner / Agent Isolation Rule |
|---|---|---|---|---|---|---|---|
| `tbl_customer` | Customer Master | `ADMIN (2)`, `OPERATOR (6)`, `FRANCHISE (9)`, `OPERATOR HEAD (19)`, `IT SUPPORT (28)`, `ALL USER (33)`, `Freelancer (35)`, `FRANCHISE TYPE 2/3 (52,53)`, `FRANCHISE OPERATOR (54)`, `OTHER (55)` | All Portal & Mobile Roles (scoped) | `ADMIN (2)`, `OPERATOR (6)`, `IT SUPPORT (28)`, `ALL USER (33)`, `Freelancer (35)` | `ADMIN (2)` only (`adm_DeleteCustvehdetails.aspx`) | Scoped to `BranchId` (`ADMIN`/`OWNER`/`IT SUPPORT`/`ALL USER` cross-branch) | Created/Updated by `UpdateUser = UserId`; Mobile customer reads own `CustomerId` |
| `tbl_custvehicle` / `tbl_vehicledetails` | Customer Vehicle | Same as `tbl_customer` Create + Mobile Quote/Policy flows (`4, 5, 16, 32`) | All Portal & Mobile Roles | `ADMIN (2)`, `OPERATOR (6)`, `FRANCHISE (9)`, `IT SUPPORT (28)`, `ALL USER (33)`, `Freelancer (35)`, `FRANCHISE OPERATOR (54)` | `ADMIN (2)` only | `RegistrationNo` uniqueness is global per `FinancialYear`; CRUD scoped to `BranchId` in FastAPI | Linked via `CustomerId`; `UpdateUser = UserId` |
| `tbl_transaction` | Policy Underwriting | `ADMIN (2)`, `OPERATOR (6)`, `FRANCHISE (9)`, `OPERATOR HEAD (19)`, `IT SUPPORT (28)`, `ALL USER (33)`, `Freelancer (35)`, `FRANCHISE TYPE 2/3 (52,53)`, `FRANCHISE OPERATOR (54)`, `OTHER (55)` | All Roles (filtered by Branch, Franchise, RSM, Hierarchy, or Agent) | Same as Create + `CASHIER (7)`, `ACCOUNT (11)`, `ENDORSEMENT (12)`, `ACCOUNT HEAD (27)`, `OWNER (1)` | `ADMIN (2)`, `ACCOUNT (11)`, `IT SUPPORT (28)` | Strict `BranchId` for Branch roles; `FranchaiseId` for Franchise roles; All Branches for `OWNER/ADMIN/ACCOUNT/IT SUPPORT` | `AGENT (4,16)` -> own `AgentId`; `RSM (5)` -> own `SalesExecutiveId`; Hierarchy (`37–57`) -> subordinate tree |
| `tbl_transactionappnew` | Mobile Policy Staging | `AGENT (4)`, `RSM (5)`, `FRANCHISE (9)`, `FAGT (16)`, `FSE (20)`, `IE (32)`, `ADMIN (2)` | Same + `OPERATOR (6)`, `OPERATOR HEAD (19)`, `ALL USER (33)` | `ADMIN (2)`, `OPERATOR (6)`, `OPERATOR HEAD (19)`, `IT SUPPORT (28)` | `ADMIN (2)` | Scoped by `BranchId` | Scoped by `AgentId` / `SalesExecutiveId` / `FranchaiseId` |
| `tbl_transactionpayment` | Policy Split Payments & Cheques | Same as `tbl_transaction` Create | `OWNER (1)`, `ADMIN (2)`, `OPERATOR (6)`, `CASHIER (7)`, `FRANCHISE (9)`, `ACCOUNT (11)`, `ACCOUNT HEAD (27)`, `IT SUPPORT (28)` | `ADMIN (2)`, `CASHIER (7)`, `ACCOUNT (11)`, `ACCOUNT HEAD (27)`, `OWNER (1)` | `ADMIN (2)`, `ACCOUNT (11)` | Follows parent `tbl_transaction.BranchId` | Follows parent `tbl_transaction` |
| `tbl_accountdetails` | Double-Entry Commission & Wallet Ledger | `ADMIN (2)`, `OPERATOR (6)`, `ACCOUNT (11)`, `ACCOUNT HEAD (27)`, `OWNER (1)` (auto-created on policy booking & payouts) | `OWNER (1)`, `ADMIN (2)`, `ACCOUNT (11)`, `ACCOUNT HEAD (27)`, plus self-statement for `AGENT (4,16)`, `RSM (5)`, `FRANCHISE (9,52,53)` | `OWNER (1)`, `ADMIN (2)`, `ACCOUNT (11)`, `ACCOUNT HEAD (27)` | `ADMIN (2)`, `ACCOUNT (11)` | `BranchId` on ledger row | `AgentId` / `FranchaiseId` owns individual statement rows |
| `tbl_agent` | POSP / Agent Master | `OWNER (1)`, `ADMIN (2)`, `RSM (5)`, `OPERATOR (6)`, `FRANCHISE (9)`, `ACCOUNT (11)`, `HR (26)`, `IT SUPPORT (28)`, `ALL USER (33)`, `FRANCHISE TYPE 3 (53)` | Same + Hierarchy Roles (`37–57`) + Self (`AGENT 4, 16`) | `OWNER (1)`, `ADMIN (2)`, `RSM (5)` (own), `FRANCHISE (9)` (own), `ACCOUNT (11)`, `HR (26)`, `IT SUPPORT (28)` | `OWNER (1)`, `ADMIN (2)`, `IT SUPPORT (28)` | Scoped to `BranchId` | `SalesExecutiveId` (`EmpId`) and `FranchaiseId` ownership |
| `tbl_employee` | Staff & Hierarchy Master | `OWNER (1)`, `ADMIN (2)`, `ACCOUNT (11)`, `HR (26)`, `IT SUPPORT (28)` | Same + Hierarchy Roles (`37–57`) + Self (`RSM 5`, `LCHD 24`) | `OWNER (1)`, `ADMIN (2)`, `HR (26)`, `IT SUPPORT (28)` | `OWNER (1)`, `ADMIN (2)`, `HR (26)` | Scoped to `BranchId` | `ParentEmpId` tree defines hierarchy scope |
| `tbl_franchaise` | Franchise Partner Master | `OWNER (1)`, `ADMIN (2)`, `ACCOUNT (11)`, `IT SUPPORT (28)` | Same + `FRANCHISE (9, 52, 53)`, `FRANCHISE OPERATOR (54)` | `OWNER (1)`, `ADMIN (2)`, `ACCOUNT (11)`, `IT SUPPORT (28)` | `OWNER (1)`, `ADMIN (2)` | Assigned `BranchId` | Self (`FranchaiseId`) |
| `tbl_user` & `tbl_userrole` | Identity & Role Master | `OWNER (1)`, `ADMIN (2)`, `HR (26)`, `IT SUPPORT (28)` (plus auto-insert via `mst_Agent` / `mst_Franchaise`) | Authenticated self (`/auth/me`) + `OWNER (1)`, `ADMIN (2)`, `HR (26)`, `IT SUPPORT (28)` | `OWNER (1)`, `ADMIN (2)`, `IT SUPPORT (28)` + self password change | `OWNER (1)`, `ADMIN (2)`, `IT SUPPORT (28)` | `BranchId >= 1` on all rows | `UserId` self-scope |
| `tbl_role_privilege` | Menu RBAC Matrix | `OWNER (1)`, `ADMIN (2)`, `IT SUPPORT (28)` | All Portal Roles (via `Clerk.Master.cs`) | `OWNER (1)`, `ADMIN (2)`, `IT SUPPORT (28)` | `OWNER (1)`, `ADMIN (2)`, `IT SUPPORT (28)` | Keyed by `(RoleId, MenuId, BranchId)` | N/A |
| `tbl_appquotationrequest` | Mobile Quotations | `AGENT (4)`, `RSM (5)`, `FRANCHISE (9)`, `FAGT (16)`, `IE (32)` | Same + `QUOT CO-ORDINATOR (14)`, `OPERATOR (6)`, `ADMIN (2)`, `OWNER (1)`, Hierarchy (`37–57`) | `QUOT CO-ORDINATOR (14)`, `OPERATOR (6)`, `ADMIN (2)`, `IT SUPPORT (28)` | `ADMIN (2)` | `BranchId` | `AgentId` / `SalesExecutiveId` |
| `tbl_appinspection` | Vehicle Inspections | `AGENT (4)`, `RSM (5)`, `OPERATOR (6)`, `FRANCHISE (9)`, `FAGT (16)`, `IE (32)` | Same + `INSP CO-ORDINATION (15)`, `ADMIN (2)`, `OWNER (1)` | `INSP CO-ORDINATION (15)`, `OPERATOR (6)`, `ADMIN (2)` | `ADMIN (2)` | `BranchId` | `AgentId` / `SalesExecutiveId` |
| `tbl_appendorsement` | Policy Endorsements | `ADMIN (2)`, `AGENT (4)`, `RSM (5)`, `OPERATOR (6)`, `FRANCHISE (9)`, `ENDORSEMENT (12)`, `FAGT (16)`, `IE (32)`, `OTHER (55)` | Same + `OWNER (1)`, `ACCOUNT (11)`, `IT SUPPORT (28)` | `ENDORSEMENT (12)`, `ADMIN (2)`, `OPERATOR (6)`, `IT SUPPORT (28)` | `ADMIN (2)` | `BranchId` | `AgentId` / `SalesExecutiveId` / `FranchaiseId` |
| `tbl_claims` | Motor Claims | `ADMIN (2)`, `AGENT (4)`, `RSM (5)`, `FRANCHISE (9)`, `CLAIM (13)`, `FAGT (16)`, `IE (32)` | Same + `OWNER (1)`, `ACCOUNT (11)`, `IT SUPPORT (28)` | `CLAIM (13)`, `ADMIN (2)`, `IT SUPPORT (28)` | `ADMIN (2)` | `BranchId` | `AgentId` / `CustomerId` |
| **7 Master Tables** (`tbl_vehicle_*`, `tbl_rto`, `tbl_insurancecompany`) | Reference Masters | `OWNER (1)`, `ADMIN (2)`, `ACCOUNT (11)`, `IT SUPPORT (28)`, `ALL USER (33)`, `OPERATOR (6)` (subset) | **All Authenticated Roles** (Dropdowns & Lookups) | `OWNER (1)`, `ADMIN (2)`, `ACCOUNT (11)`, `IT SUPPORT (28)`, `ALL USER (33)` | `OWNER (1)`, `ADMIN (2)`, `IT SUPPORT (28)` | Global Read; Write audited by `BranchId` | Global |
