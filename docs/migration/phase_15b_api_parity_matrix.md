# PHASE 15B — API PARITY & ENDPOINT MATRIX
## Operational Utilities, Bulk Imports, Background Jobs & Profile Management

---

### 1. Executive Summary
Phase 15B introduces 7 modular FastAPI routers mounted under `/api/v1`, exposing **23 new production-grade endpoints** that replace legacy ASP.NET WebForms pages, ASMX web services, and background batch processing scripts.

All endpoints strictly adhere to:
- FastAPI asynchronous Clean Architecture (`APIRouter`, `Depends`, `AsyncSession`).
- Pydantic v2 DTO validation with descriptive field constraints.
- Strict Role-Based Access Control (RBAC) via `require_roles(...)`.
- Multitenant data isolation (Branch and Principal scoping).
- Audit trail stamping (`CreateUser`, `CreateDate`, `UpdateUser`, `UpdateDate`).

---

### 2. Complete Phase 15B Endpoint Inventory

| # | HTTP Method | Endpoint Route | Legacy ASP.NET Entry Point | Target Service Method | Allowed Roles | Isolation Scoping |
|---|---|---|---|---|---|---|
| **1** | `GET` | `/api/v1/employees` | `mst_Employee.aspx.cs` | `ProfileService.list_employees` | `ADMIN`, `DIRECTOR`, `BRANCH_MANAGER`, `STAFF` | Branch / Tenant Scoped |
| **2** | `GET` | `/api/v1/employees/{emp_id}` | `mst_Employee.aspx.cs` | `ProfileService.get_employee_by_id` | `ADMIN`, `DIRECTOR`, `BRANCH_MANAGER`, `STAFF` | Branch Scoped |
| **3** | `POST` | `/api/v1/employees` | `mst_Employee.aspx.cs` | `ProfileService.create_employee` | `ADMIN`, `DIRECTOR`, `BRANCH_MANAGER` | Branch Scoped |
| **4** | `PUT` | `/api/v1/employees/{emp_id}` | `mst_Employee.aspx.cs` | `ProfileService.update_employee` | `ADMIN`, `DIRECTOR`, `BRANCH_MANAGER` | Branch Scoped |
| **5** | `DELETE` | `/api/v1/employees/{emp_id}` | `mst_Employee.aspx.cs` | `ProfileService.delete_employee` | `ADMIN`, `DIRECTOR` | Branch Scoped (Soft Delete) |
| **6** | `GET` | `/api/v1/agents` | `mst_Agent.aspx.cs` | `ProfileService.list_agents` | `ADMIN`, `DIRECTOR`, `BRANCH_MANAGER`, `STAFF`, `SUPERVISOR` | Branch Scoped |
| **7** | `GET` | `/api/v1/agents/{agent_id}` | `mst_Agent.aspx.cs` | `ProfileService.get_agent_by_id` | `ADMIN`, `DIRECTOR`, `BRANCH_MANAGER`, `STAFF`, `AGENT` | Principal & Branch Scoped |
| **8** | `POST` | `/api/v1/agents` | `mst_Agent.aspx.cs` | `ProfileService.create_agent` | `ADMIN`, `DIRECTOR`, `BRANCH_MANAGER` | Branch Scoped |
| **9** | `PUT` | `/api/v1/agents/{agent_id}` | `mst_Agent.aspx.cs` | `ProfileService.update_agent` | `ADMIN`, `DIRECTOR`, `BRANCH_MANAGER` | Branch Scoped |
| **10** | `GET` | `/api/v1/franchises` | `mst_Franchaise.aspx.cs` | `ProfileService.list_franchises` | `ADMIN`, `DIRECTOR`, `BRANCH_MANAGER`, `STAFF` | Branch Scoped |
| **11** | `GET` | `/api/v1/franchises/{franchise_id}` | `mst_Franchaise.aspx.cs` | `ProfileService.get_franchise_by_id` | `ADMIN`, `DIRECTOR`, `BRANCH_MANAGER`, `STAFF`, `FRANCHISE` | Principal & Branch Scoped |
| **12** | `POST` | `/api/v1/franchises` | `mst_Franchaise.aspx.cs` | `ProfileService.create_franchise` | `ADMIN`, `DIRECTOR`, `BRANCH_MANAGER` | Branch Scoped |
| **13** | `PUT` | `/api/v1/franchises/{franchise_id}` | `mst_Franchaise.aspx.cs` | `ProfileService.update_franchise` | `ADMIN`, `DIRECTOR`, `BRANCH_MANAGER` | Branch Scoped |
| **14** | `GET` | `/api/v1/idv-requests` | `ViewIDVRequestDetails.aspx.cs` | `UtilityService.list_idv_requests` | `ADMIN`, `DIRECTOR`, `BRANCH_MANAGER`, `STAFF`, `SUPERVISOR` | Branch Scoped |
| **15** | `POST` | `/api/v1/idv-requests` | `Service.asmx.cs` (`SubmitIDVRequest`) | `UtilityService.create_idv_request` | `ADMIN`, `DIRECTOR`, `BRANCH_MANAGER`, `STAFF`, `AGENT` | Principal / Agent Scoped |
| **16** | `PUT` | `/api/v1/idv-requests/{request_id}/review` | `ViewIDVRequestDetails.aspx.cs` | `UtilityService.review_idv_request` | `ADMIN`, `DIRECTOR`, `BRANCH_MANAGER` | Branch Scoped |
| **17** | `GET` | `/api/v1/health-members/policy/{transaction_id}` | `PE_TransactionEntry.aspx.cs` | `UtilityService.get_members_by_transaction` | `ADMIN`, `DIRECTOR`, `BRANCH_MANAGER`, `STAFF`, `AGENT` | Transaction Scoped |
| **18** | `POST` | `/api/v1/health-members` | `PE_TransactionEntry.aspx.cs` | `UtilityService.create_health_member` | `ADMIN`, `DIRECTOR`, `BRANCH_MANAGER`, `STAFF`, `AGENT` | Transaction Scoped |
| **19** | `DELETE` | `/api/v1/health-members/{member_id}` | `PE_TransactionEntry.aspx.cs` | `UtilityService.delete_health_member` | `ADMIN`, `DIRECTOR`, `BRANCH_MANAGER`, `STAFF` | Transaction Scoped |
| **20** | `POST` | `/api/v1/imports/policy-mis/upload` | `adm_ImportTransAgentPolicyMIS.aspx.cs` | `UtilityService.parse_and_stage_policy_mis` | `ADMIN`, `DIRECTOR`, `BRANCH_MANAGER` | Global / Branch Scoped |
| **21** | `GET` | `/api/v1/imports/policy-mis/batches/{batch_id}` | `adm_ImportTransAgentPolicyMIS.aspx.cs` | `UtilityService.get_import_batch_status` | `ADMIN`, `DIRECTOR`, `BRANCH_MANAGER` | Global / Branch Scoped |
| **22** | `POST` | `/api/v1/batch-tasks/overdue-cheque-lock/run` | `Adm_LockChequeEntry.aspx.cs` (`LBR-069`) | `UtilityService.enforce_overdue_cheque_locks` | `ADMIN`, `DIRECTOR` | Global Admin Only |
| **23** | `POST` | `/api/v1/batch-tasks/birthday-greetings/dispatch` | `SendPushNotiForBdayWish.aspx.cs` | `UtilityService.dispatch_birthday_greetings` | `ADMIN`, `DIRECTOR` | Global Admin Only |

---

### 3. Detailed Request / Response Schema Parity

#### 3.1 Profile Endpoints (`/api/v1/employees`, `/api/v1/agents`, `/api/v1/franchises`)
- **Employee Creation / Update**:
  - `EmployeeCreate`: `UserName`, `EmpFName`, `EmpMName`, `EmpLName`, `MoblieNo`, `EmailId`, `PAN_No`, `AadharNo`, `BankBranch`, `Ifsc_code`, `accountNo`, `BranchId`, `UserRoleId`.
  - Auto-generated `EmpCode` format: `EMP{YYYYMM}{seq:04d}` (matches legacy sequential staff onboarding format).
  - Soft-delete semantics: `isdeleted = '1'`, excluded from regular listings.
- **Agent Creation / Update**:
  - `AgentCreate`: `AgentFName`, `AgentMName`, `AgentLName`, `MobileNo`, `EmailId`, `PANNo`, `AadharNo`, `SalesExecutiveId`, `CoordinatorId`, `FranchiseId`, `BranchId`.
  - Auto-generated `AgentCode`: `AGT{YYYYMM}{seq:04d}`.
- **Franchise Creation / Update**:
  - `FranchiseCreate`: `FranchiseName`, `ContactPerson`, `MobileNo`, `EmailId`, `PANNo`, `GSTNo`, `Address`, `City`, `BranchId`.
  - Auto-generated `FranchiseCode`: `FRN{YYYYMM}{seq:04d}`.

#### 3.2 IDV Override Review (`/api/v1/idv-requests`)
- **Request Creation**:
  - `IDVRequestCreate`: `VehicleNo`, `CustomerName`, `Make`, `Model`, `Variant`, `RegistrationYear`, `RequestedIDV`, `StandardIDV`, `Remarks`.
  - Auto-calculated IDV variance percentage: `((RequestedIDV - StandardIDV) / StandardIDV) * 100`.
- **Review Workflow**:
  - `IDVRequestReview`: `Status` (`APPROVED` / `REJECTED`), `ApprovedIDV`, `UnderwriterRemarks`.
  - Stamps review date and reviewing underwriter identifier.

#### 3.3 Health Family Member Grid (`/api/v1/health-members`)
- **Member Ingestion**:
  - `HealthMemberCreate`: `TransactionId`, `MemberName`, `Relation` (`SELF`, `SPOUSE`, `SON`, `DAUGHTER`, `FATHER`, `MOTHER`, `OTHER`), `DOB`, `Age`, `SumInsured`, `PreExistingDiseases`.
  - Multi-member association validated against active health policy transaction (`tbl_transaction`).

#### 3.4 Bulk MIS Policy Import (`/api/v1/imports/policy-mis`)
- **File Upload & Ingestion**:
  - Supports multipart upload of `.csv`, `.xlsx`, `.xls`.
  - Dynamic column mapping handles legacy variations (e.g., `Policy No` vs `PolicyNo`, `Net Premium` vs `NetPremium`).
  - Cleans currency symbols, commas, and percentage characters.
  - Staged records stored in `tbl_importagentpolicy` with unique `BatchId` UUID and initial `IsProcess = '0'`.

#### 3.5 Scheduled Batch Tasks (`/api/v1/batch-tasks`)
- **Overdue Cheque User Lock (`LBR-069`)**:
  - Scans `tbl_transactionpayment` for payments where `paymenttype = 'CHEQUE'` and `CashierApproval != '1'` or `isclearance != '1'`.
  - Evaluates age against threshold parameter (default 15 days).
  - Aggregates affected policy booking creators (`CreateUser` / `UserId`).
  - Locks user login access by toggling `isactive = 0` in `tbl_userlogin`.
- **Birthday Greeting Dispatch**:
  - Scans `tbl_customer` and `tbl_franchise` matching current date (`MONTH(dob) = MONTH(now)` and `DAY(dob) = DAY(now)`).
  - Renders personalized SMS / push notification template.
  - Enqueues dispatch via `NotificationService` integration gateway.
