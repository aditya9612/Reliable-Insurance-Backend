# 12 — Legacy RBAC, Authentication, Branch & Ownership Baseline (Phase 5 & Cross-Phase)

> **Audit Status**: CONFIRMED FROM CODE
> **Primary Evidence**:
> - `Insurance\Log_In.aspx.cs` (Lines 1–194 — ERP Web Login & Session Initialization)
> - `Insurance\AppLogin.aspx.cs` & `Insurance\Service.asmx.cs` (Mobile/App Login Endpoints)
> - `Insurance\Clerk\Clerk.Master.cs` (Role-Based Menu Visibility)
> - `Insurance\Clerk\CL_ClaimNew.aspx.cs` (Line 58 — Role Filtering)
> - `Insurance\Clerk\ViewAppTransEwalletApproval.aspx.cs` (Lines 21–24, 53–116)
> - `API\AllMaster.cs` (`API_LoginHistory` L9–21, `API_UserRole` L178–182, `API_Employee` L201–319, `API_Hie_Desn` L322–330)

---

## 1. Authentication Flows & Session State Contract

### 1.1 Web Portal Login (`Insurance\Log_In.aspx.cs` L38–178)
1. **Page Load Session Reset**: On `GET /Log_In.aspx` (`!IsPostBack`), calls `Session.Abandon()` (L27).
2. **Credential Verification**:
   - Calls `BLL_User.BLL_CheckLogin(txtUserName.Value, txtPassword.Value)` (`usp_CheckLogin`).
   - Passwords are sent and compared in **plaintext** (no hashing or salting in C#).
3. **Franchise vs Standard ERP Branching (`dt.Rows[0][4]` = `UserRole`)**:
   - **Branch A: `userrole.Contains("FRANCHISE")`** (L59–106):
     - If `userrole.Contains("OPERATOR")`: calls `BLL_CheckLoginfrFranchise(userName, password, "OPTR")` and populates:
       - `Session["UserId"]`, `Session["UserName"]`, `Session["RoleId"]`, `Session["BranchId"]`, `Session["UserRole"]`, `Session["BranchName"]`, `Session["FranchiseId"]`, `Session["FranchiseTypeId"]`.
     - Else (Franchise Owner): calls `BLL_CheckLoginfrFranchise(userName, password, "FR")` and additionally populates `Session["SalesExecutiveId"] = dt.Rows[0][7].ToString()`.
     - Redirects to `Clerk/Index.aspx`.
   - **Branch B: Standard Internal ERP Users** (L108–170):
     - Populates `Session["UserId"]`, `Session["UserName"]`, `Session["RoleId"]`, `Session["BranchId"]`, `Session["UserRole"]`, `Session["BranchName"]`.
     - **Role-Specific Landing Page Redirects** (L144–167):
       - `userroleid == 30` (Telecaller / Calling Role) -> Redirects to `Clerk/Calling_CallStatusDetails.aspx`.
       - `userroleid == 35` (Quotation Role) -> Redirects to `Clerk/Dashboard_Quotation.aspx`.
       - All other roles -> Redirects to `Clerk/index.aspx`.
4. **Login Audit Trail (`API_LoginHistory`)**:
   - Captures client IP from `Request.ServerVariables["HTTP_X_FORWARDED_FOR"]` or `REMOTE_ADDR` (L50–54).
   - Calls `userObj.BLL_InsertLoginHistiry(logh, "INS")` with `Remark = "ERP"`, `LogInOrLogOut = "LogIn"`, `funPerform = "Login Click"`.

---

## 2. Confirmed Role IDs (`RoleId` / `UserRoleId`) & Role Names (`UserRole`)

**Evidence**: `Log_In.aspx.cs`, `Clerk\Clerk.Master.cs`, `CL_ClaimNew.aspx.cs`, `SelfQuotationRequest.aspx.cs`, `ViewAppTransEwalletApproval.aspx.cs`, `Service.asmx.cs`

| `RoleId` / `UserRole` | Role Description | Confirmed Capabilities & Routing |
| :--- | :--- | :--- |
| `"Admin"` (`RoleId = 1`) | Super Admin / Head Office Admin | Full access to all masters, commission grids, recalculation (`AgentCommissionRecalculation.aspx`), cheque clearing by admin, TDS masters, and all branches. |
| `UserRoleId = 5` | Sales Executive | Bound in `ddl_Sales` (`dv.RowFilter = "(UserRoleId=5) or (UserRole='Location Head')"` in `CL_ClaimNew.aspx.cs` L58). |
| `"Location Head"` (`L.Head`) | Location / Branch Head | Included in Sales Executive dropdowns (`CL_ClaimNew.aspx.cs` L58) and receives commission via Ledger `1930` (`PE_TransactionEntry.aspx.cs` L9735). |
| `"Agent"` / POSP | External Insurance Agent / POSP | Logs in via Mobile App (`Service.asmx.cs`) or Web; submits quotations, app policy requests, and E-Wallet payments. |
| `"FRANCHISE"` / `"FRANCHISE OPERATOR"` | Franchise Partner / Operator | Scoped by `Session["FranchiseId"]` and `Session["FranchiseTypeId"]` (`Log_In.aspx.cs` L59–90). |
| `RoleId = 30` | Telecaller / Calling Executive | Redirected on login to `Clerk/Calling_CallStatusDetails.aspx` (`Log_In.aspx.cs` L144). |
| `RoleId = 35` | Quotation Coordinator / Executive | Redirected on login to `Clerk/Dashboard_Quotation.aspx` (`Log_In.aspx.cs` L149). |
| Cashier / Accountant / Policy Entry / Claim / Inspection / Endorsement Coordinator | Operational Back-Office Roles | Controlled via `Clerk.Master.cs` menu visibility and `API_Employee` coordinator IDs (`QuotationCordinatorId`, `InspectionCordinatorId`, `EndrosmentcordinatorId` in `API\AllMaster.cs` L256–258). |

---

## 3. Branch Scoping & Hierarchy Ownership Rules

1. **Branch Assignment (`Session["BranchId"]`)**:
   - Every Customer (`cust.BranchId`), Vehicle (`CustVehicle.BranchId`), Transaction (`Trans.BranchId`), Payment (`Payment.BranchId`), and Ledger Entry (`cashAccount.BranchId`) records a `BranchId`.
   - **Hardcoded `BranchId = 1` Exceptions**:
     - In `AppEndorsementforApproval.aspx.cs` (L219, L247, L279), endorsement ledger entries hardcode `BranchId = 1` regardless of `Session["BranchId"]`.
     - In `PolicyTransactionNew.aspx.cs`, Reliable Associates head-office franchise commission is hardcoded to `FranchiseId = 1`.
2. **Sales & Operations Hierarchy Strings (`Hie_DataSales`, `Hie_DataOprn`, `Hei_Data`)**:
   - **Evidence**: `API\AllMaster.cs` (`API_Employee` L290–296, `API_Transaction` L576–577)
   - Employees are organized into a 5-level organizational hierarchy (`ClassId`, `BProcessId`, `BLineId`, `FuncId`, `DesnId`, `ReportingId`) serialized into hierarchy strings `Hei_Data`, `Hie_DataSales`, and `Hie_DataOprn` on transactions.

---

## 4. Authorization Enforcement Gaps (Security Baseline)

1. **Unauthenticated ASMX & PageMethod Endpoints**:
   - All 339 `[WebMethod]` endpoints in `Service.asmx.cs`, 2 in `VehicleService.asmx.cs`, 41 in `Clerk\SearchMethods.aspx.cs`, and 16 in `AppSearchMethod.aspx.cs` have **zero session/token authentication attributes**. They trust client-supplied `UserId`, `AgentId`, `RoleId`, and `BranchId` parameters.
2. **Inconsistent `Page_Load` Session Checks**:
   - While pages like `AppEndorsementforApproval.aspx.cs` (L21) and `OwnerTransferEndorsement.aspx.cs` (L17) check `if (Session["UserRole"] == null) Response.Redirect("~/Log_Out.aspx");`, several pages (such as `CL_ClaimNew.aspx.cs` L30 and `adm_NcbRecovery.aspx.cs` L18) do **not** check `Session["UserRole"]` in `Page_Load` until a button click accesses `Session["BranchId"]` or `Session["UserName"]` (causing a `NullReferenceException` if session expired).
3. **UI-Only Role Restriction**:
   - Role permissions are enforced primarily by hiding navigation links in `Clerk.Master.cs`. Direct URL navigation to `.aspx` pages is not blocked by role-permission middleware.
