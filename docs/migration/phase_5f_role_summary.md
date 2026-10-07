# Phase 5F — Per-Role Capability, Scope & Authority Summary

**Phase:** 5F — Role / API / Table / CRUD / Branch / Owner Access Audit  
**Mode:** STRICT READ-ONLY AUDIT  
**Date:** 2026-10-06  
**Source of Truth:** `brahmainsurance.tbl_userrole`, `tbl_user`, `tbl_role_privilege`, `tbl_menutable`, and `InsurancefinalNew` C# source

---

## 1. Role Taxonomy Overview

The 56 roles in `tbl_userrole` (plus 3 external identity types) fall into **9 functional role tiers**:

1. **Tier 1 — Executive & Super-Administrative (`OWNER`, `ADMIN`, `IT SUPPORT`, `SHREYANSH OWNER`)**
2. **Tier 2 — Finance, Accounting & Cashier (`ACCOUNT`, `ACCOUNT HEAD`, `CASHIER`, `EMI`)**
3. **Tier 3 — Core Back-Office Underwriting & Operations (`OPERATOR`, `OPERATOR HEAD`, `ALL USER`, `Freelancer`, `OTHER`, `pOLICY VIEW`)**
4. **Tier 4 — Specialized Back-Office Coordinators (`ENDORSEMENT`, `CLAIM`, `QUOT CO-ORDINATOR`, `INSP CO-ORDINATION`, `CallIng Employee`, `HR`)**
5. **Tier 5 — Field Sales & Branch Management (`RELATIONSHIP MANAGER`, `LOCATION HEAD`, `Insurance Exective`)**
6. **Tier 6 — Organizational Sales Hierarchy (`BUSINESS HEAD`, `STATE HEAD`, `REGIONAL HEAD`, `PROCESS HEAD`, `TEAM LEADER SALES`, `DIVISION HEAD`, `PROCESS MANAGER`, `CLUSTER HEAD`, etc.)**
7. **Tier 7 — Franchise Ecosystem (`FRANCHISE`, `FRANCHISE TYPE 2`, `FRANCHISE TYPE 3`, `FRANCHISE OPERATOR`, `FRANCHISE SALES EXECUTIVE`, `FRANCHISE AGENT`)**
8. **Tier 8 — External POSP / Mobile Agents & Partners (`AGENT`, `POLICY BAZAR`, `POLICY BAZAR AGENT`, `Broker partner`)**
9. **Tier 9 — External API Clients & End Customers (`tbl_appclientlogin`, `tbl_customer`, `tbl_appsignupcustomer`)**

---

## 2. Detailed Role Profiles

### 2.1 Tier 1 — Executive & Super-Administrative Roles

#### `1: OWNER` (`OWN`) & `29: SHREYANSH OWNER` (`SHRO`)
- **User Population:** `0` rows in `tbl_user` have `UserRoleId = 1` or `29`; however, `UserId = 202` (`RoleId = 2` in `tbl_user`) is hardcoded in `Log_In.aspx.cs:86` to redirect to `Clerk/OwnerDashBoard.aspx`, and C# code explicitly checks `ROLE == "OWNER"`.
- **Menu Privileges (`tbl_role_privilege`):** `OWNER` = 109 screens (Branch 1) / 192 total entries; `SHREYANSH OWNER` = 16 screens.
- **Primary Responsibilities:** Executive oversight, high-value/override policy approvals (`OwnerApproval.aspx`), payout/commission disbursements (`OwnerPaymentApproval.aspx`), wallet approvals, and global MIS exports.
- **Allowed CRUD:** `C`, `R`, `U`, `D` (Soft) across all operational, accounting, master, and user/role tables.
- **Branch Scope:** **All Branches** (Global).
- **Owner / Agent Scope:** **Global** (Unrestricted).
- **Financial Authority:** Highest (`IsOwnerApprove = 1`, `OwnerPaymentApproval`, `EWalletApproval`, `AgentCommisionApproval`).
- **FastAPI RBAC Recommendation:** Treat `OWNER` as top-level super-role (`_is_admin = True`, cross-branch access enabled).

#### `2: ADMIN` (`ADM`)
- **User Population:** `15` total (`7` active, `8` deleted); `isappuser = 0`; `BranchId` values `1` (10 users), `2, 3, 4, 5, 6` (1 user each).
- **Menu Privileges (`tbl_role_privilege`):** `241` screens on Branch 1 (broadest menu access in the system).
- **Primary Responsibilities:** Full system administration, customer/vehicle/policy CRUD (`PolicyTransactionNew.aspx`, `PE_TransactionEntry.aspx`, `adm_UpdateCustomer.aspx`, `adm_UpdateVehicleDetails.aspx`), soft-deletion of policies and customer/vehicles (`adm_DeletePolicyTransaction.aspx`, `adm_DeleteCustvehdetails.aspx`), master data CRUD (`mst_*`), user/role/privilege management (`mst_User.aspx`, `RolePrivilege.aspx`), and financial approvals.
- **Allowed CRUD:** `C`, `R`, `U`, `D` (Soft) on all tables (`tbl_customer`, `tbl_custvehicle`, `tbl_transaction`, `tbl_transactionpayment`, `tbl_accountdetails`, `tbl_agent`, `tbl_employee`, `tbl_franchaise`, `tbl_user`, `tbl_role_privilege`, and all 7 master tables).
- **Branch Scope:** **All Branches** on global reports/approvals; defaults to `Session["BranchId"]` on data entry screens with ability to filter across branches.
- **Owner / Agent Scope:** **Global** (can assign/modify any `AgentId`, `SalesExecutiveId`, or `FranchaiseId`).
- **Financial Authority:** Full approval authority across Cashier, Accountant, Commission, and E-Wallet workflows.
- **FastAPI RBAC Recommendation:** Primary administrative role (`require_roles("ADMIN", "OWNER", "IT SUPPORT")`); retain cross-branch override in `_is_admin()`.

#### `28: IT SUPPORT` (`ITS`)
- **User Population:** `12` total (`5` active, `7` deleted); `isappuser = 0`; `BranchId = 1`.
- **Menu Privileges (`tbl_role_privilege`):** `123` screens on Branch 1.
- **Primary Responsibilities:** Technical support, correcting policy/customer/vehicle records (`PolicyTransactionNew.aspx`, `PE_TransactionEntry.aspx`, `adm_UpdateVehicleDetails.aspx`), deleting erroneous transactions (`adm_DeletePolicyTransaction.aspx`), maintaining master tables (`mst_VehicleVariant.aspx`, `mst_RTO.aspx`, `mst_Agent.aspx`), and managing users (`mst_User.aspx`).
- **Allowed CRUD:** `C`, `R`, `U`, `D` (Soft) across Customer, Vehicle, Policy, Agent, Employee, User, and Master tables.
- **Branch Scope:** **All Branches** (assigned `BranchId = 1`, operates system-wide).
- **Owner / Agent Scope:** **Global**.
- **Financial Authority:** Has menu access to `CashierApprovalNew.aspx`, `AccountantApproval.aspx`, `AgentCommisionApproval.aspx` for operational support.
- **FastAPI RBAC Recommendation:** Include `IT SUPPORT` in administrative CRUD permissions for Customer, Vehicle, Policy correction, and Master maintenance.

---

### 2.2 Tier 2 — Finance, Accounting & Cashier Roles

#### `11: ACCOUNT` (`ACC`) & `27: ACCOUNT HEAD` (`ACH`)
- **User Population:** `ACCOUNT`: `15` total (`2` active, `13` deleted, `BranchId = 1, 2`); `ACCOUNT HEAD`: `1` (`deleted = 1`, `BranchId = 1`).
- **Menu Privileges (`tbl_role_privilege`):** `ACCOUNT` = `133` screens (Branch 1); `ACCOUNT HEAD` = `51` screens.
- **Primary Responsibilities:** Double-entry ledger management (`tbl_accountdetails`), accountant policy verification (`AccountantApproval.aspx`), cashier verification (`CashierApprovalNew.aspx`), agent commission approval & payout (`AgentCommisionApproval.aspx`), cheque clearance/bounce (`ChequeClearance.aspx`), e-wallet top-up approval (`EWalletApproval.aspx`), TDS/GST reporting, and master table maintenance.
- **Allowed CRUD:**
  - `C`, `R`, `U`, `D` on `tbl_accountdetails`, `tbl_transactionpayment`, `tbl_walletrequest`, `tbl_paymentrequest`.
  - `R`, `U`, `D` (Soft) on `tbl_transaction` (`adm_DeletePolicyTransaction.aspx`).
  - `C`, `R`, `U` on `tbl_agent`, `tbl_employee`, `tbl_franchaise`, and Master tables.
  - `R` on `tbl_customer`, `tbl_custvehicle` (does **not** have `adm_UpdateCustomer.aspx` or `PE_TransactionEntry.aspx` in `tbl_role_privilege`).
- **Branch Scope:** **All Branches** for financial reconciliation and exports (`ROLE == "ACCOUNT"` explicitly granted cross-branch view in `CashierApprovalNew.aspx.cs`).
- **Owner / Agent Scope:** Global across all agents, employees, and franchises.
- **Financial Authority:** Primary financial controller (`IsAccountantApprove`, `IsCashierApprove`, commission calculation, ledger debit/credit, cheque bounce penalty).

#### `7: CASHIER` (`CASH`)
- **User Population:** `1` user (`deleted = 1`, `BranchId = 1`).
- **Menu Privileges (`tbl_role_privilege`):** `1` screen (`Clerk/CashierApprovalNew.aspx`).
- **Primary Responsibilities:** Verifying cash, cheque, and online payment instruments prior to policy issuance (`IsCashierApprove`).
- **Allowed CRUD:** `R`, `U` on `tbl_transaction` (approval flag) and `tbl_transactionpayment`.
- **Branch Scope:** `Own Branch` (`Session["BranchId"]`).
- **Financial Authority:** Cashier stage approval only.

#### `36: EMI` (`EMI`)
- **User Population:** `2` users (`1` active, `1` deleted, `BranchId = 1`).
- **Menu Privileges (`tbl_role_privilege`):** `2` screens (EMI reporting/tracking).
- **Allowed CRUD:** `R`, `U` on EMI-related transaction records.

---

### 2.3 Tier 3 — Core Back-Office Underwriting & Operations Roles

#### `6: OPERATOR` (`OPT`) & `19: OPERATOR HEAD` (`OH`)
- **User Population:** `OPERATOR`: `146` total (`67` active, `79` deleted; `BranchId` across `1..9`); `OPERATOR HEAD`: `1` (`deleted = 1`, `BranchId = 1`).
- **Menu Privileges (`tbl_role_privilege`):** `OPERATOR` = `42` screens (Branch 1); `OPERATOR HEAD` = `30` screens.
- **Primary Responsibilities:** Day-to-day customer creation/updating (`adm_UpdateCustomer.aspx`), vehicle creation/updating (`adm_UpdateVehicleDetails.aspx`), policy intake (`PE_TransactionEntry.aspx`), full policy booking (`PolicyTransactionNew.aspx`), quotation/inspection/endorsement entry, and agent creation (`mst_Agent.aspx`).
- **Allowed CRUD:**
  - `C`, `R`, `U` on `tbl_customer`, `tbl_custvehicle`, `tbl_transaction`, `tbl_transactionpayment`, `tbl_appquotationrequest`, `tbl_appinspection`, `tbl_appendorsement`, `tbl_agent`.
  - `C`, `R`, `U` on select vehicle masters (`mst_VehicleMake`, `mst_VehicleModel`, `mst_VehicleVariant`, `mst_RTO`).
  - **No Delete (`D`)** privileges on customers, vehicles, or policies.
- **Branch Scope:** **Strict Own Branch (`Session["BranchId"]`)** for Customer and Policy CRUD.
- **Owner / Agent Scope:** Within own branch, can book policies on behalf of any branch `AgentId` and `SalesExecutiveId`.
- **Financial Authority:** None (cannot approve Cashier, Accountant, Owner, or Commission screens).

#### `33: ALL USER` (`AUSER`) & `35: Freelancer` (`FRL`) & `55: OTHER` (`OTH`)
- **User Population:** `ALL USER`: `27` (`4` active, `23` deleted, `BranchId = 1`); `Freelancer`: `2` (`2` active, `BranchId = 1`); `OTHER`: `14` (`12` active, `2` deleted, `BranchId = 1`).
- **Menu Privileges (`tbl_role_privilege`):** `ALL USER` = `24` screens; `Freelancer` = `20` screens; `OTHER` = `5` screens.
- **Primary Responsibilities:**
  - `ALL USER (33)` & `Freelancer (35)`: High-throughput policy entry (`PE_TransactionEntry.aspx`, `PolicyTransactionNew.aspx`), customer update (`adm_UpdateCustomer.aspx`), vehicle update (`adm_UpdateVehicleDetails.aspx`), and master lookups.
  - `OTHER (55)`: Restricted to `PE_TransactionEntry.aspx` and endorsement/policy view screens.
- **Allowed CRUD:** `C`, `R`, `U` on `tbl_customer`, `tbl_custvehicle`, `tbl_transaction`, `tbl_transactionpayment` (`OTHER` lacks standalone customer/vehicle update screens).
- **Branch Scope:** `Own Branch` (`Session["BranchId"] = 1`).
- **Financial Authority:** None.

#### `34: pOLICY VIEW` (`PV`)
- **User Population:** `1` (`deleted = 1`).
- **Menu Privileges:** `2` screens (Read-only transaction search/view).
- **Allowed CRUD:** `R` only on `tbl_transaction`, `tbl_customer`, `tbl_custvehicle`.

---

### 2.4 Tier 4 — Specialized Back-Office Coordinators

| Role ID & Name | Active / Total Users | Menu Screens | Primary Responsibilities | Allowed CRUD & Tables | Branch & Owner Scope |
|---|---:|---:|---|---|---|
| `12: ENDORSEMENT (END)` | 1 / 1 | 14 | Processing mid-term policy endorsements (`EndorsementEntry.aspx`, `AppEndorsementList.aspx`) | `C, R, U` on `tbl_appendorsement`; `R, U` on `tbl_transaction`, `tbl_customer`, `tbl_custvehicle` | `Own Branch (`BranchId=1`)`; all agents in branch |
| `13: CLAIM (CLM)` | 1 / 2 | 6 | Motor claim intimation, surveyor tracking, claim settlement (`ClaimEntry.aspx`) | `C, R, U` on `tbl_claims`, `tbl_claimdocument`; `R` on `tbl_transaction`, `tbl_customer`, `tbl_custvehicle` | `Own Branch (`BranchId=1`)`; all agents in branch |
| `14: QUOT CO-ORDINATOR (QUT)` | 0 / 2 | 8 | Replying to mobile app quote requests (`QuotationCoordination.aspx`) | `R, U` on `tbl_appquotationrequest`, `tbl_quotationreply` | `Own Branch (`BranchId=1`)` |
| `15: INSP CO-ORDINATION (INS)` | 1 / 1 | 9 | Coordinating break-in vehicle inspections (`InspectionCoordination.aspx`) | `R, U` on `tbl_appinspection`, `tbl_transaction` | `Own Branch (`BranchId=1`)` |
| `26: HR (HR)` | 0 / 5 | 15 | Employee & POSP onboarding (`mst_Employee.aspx`, `mst_User.aspx`, `mst_Agent.aspx`) | `C, R, U, D` on `tbl_employee`, `tbl_user`, `tbl_agent` | `Own Branch (`BranchId=1`)` / Global HR |
| `30: CallIng Employee (CE)` | 1 / 1 | 2 | Telecalling & renewal follow-up | `R, U` on renewal/calling tracking tables; `R` on `tbl_transaction` | `Own Branch (`BranchId=1`)` |

---

### 2.5 Tier 5 — Field Sales & Branch Management Roles

#### `5: RELATIONSHIP MANAGER` (`RSM` / Sales Executive)
- **User Population:** `312` total (`68` active, `244` deleted); `157` have `isappuser = 1` (mobile app access) and `155` have `isappuser = 0` (web portal access); `BranchId` in `1, 2`. Mapped at login via `sp_CheckLoginForEmployee` / `sp_ChkloginEmp` to `tbl_employee.EmpId`.
- **Menu Privileges (`tbl_role_privilege`):** `20` screens on Branch 1 (`mst_Agent.aspx`, quotation/inspection/endorsement/claim tracking, `Adm_AllTransactionExport.aspx`).
- **Primary Responsibilities:** Managing assigned POSP/Agents (`tbl_agent.SalesExecutiveId = EmpId`), onboarding new agents, submitting/tracking quotations, inspections, and policy proposals via Mobile App (`Service.asmx`) or Web Portal.
- **Allowed CRUD:**
  - `C`, `R`, `U` on `tbl_agent` (locked to `SalesExecutiveId = own EmpId`), `tbl_appquotationrequest`, `tbl_appinspection`, `tbl_appendorsement`, `tbl_claims`, `tbl_transactionappnew`.
  - `R` on `tbl_transaction`, `tbl_accountdetails` (scoped to own `SalesExecutiveId`).
  - **Cannot** directly create/update standalone `tbl_customer` or `tbl_custvehicle` via portal (`PE_TransactionEntry` and `PolicyTransactionNew` are NOT in `RSM` menu privileges).
- **Branch Scope:** `Own Branch` (`Session["BranchId"]`).
- **Owner / Agent Scope:** **Strict Executive Ownership (`SalesExecutiveId == EmpId`)** — enforced in `mst_Agent.aspx.cs`, `Adm_AllTransactionExport.aspx.cs`, and mobile SPs (`sp_SelectAgentBySalesExecId`).

#### `24: LOCATION HEAD` (`LCHD`)
- **User Population:** `8` total (`2` active, `6` deleted, `BranchId = 1`). Mapped via `sp_CheckLoginForEmployee` to `tbl_employee`.
- **Menu Privileges (`tbl_role_privilege`):** `26` screens (Agent onboarding, transaction exports, quotation/inspection/claim views).
- **Allowed CRUD:** `C, R, U` on `tbl_agent`; `R` on `tbl_transaction`, `tbl_appquotationrequest`, `tbl_appinspection`, `tbl_claims`.
- **Branch / Owner Scope:** Scoped to assigned location/branch and subordinate sales executives.

#### `32: Insurance Exective` (`IE`)
- **User Population:** `93` total (`76` active, `17` deleted); `92` have `isappuser = 1`; `0` portal menu screens.
- **Primary Responsibilities:** Mobile-only field executive role using `Service.asmx` for quotations, vehicle inspection uploads, and policy proposal staging.
- **Branch / Owner Scope:** Mobile self-scope (`EmpId` / `UserId`).

---

### 2.6 Tier 6 — Organizational Sales Hierarchy Roles (`RoleId` 21, 37–51, 57)

- **Roles Included:** `21: HOD (HOD)`, `37: BUSINESS HEAD (BSH)`, `38: PRESIDENT`, `39: VICE PRESIDENT`, `40: STATE HEAD (STH)`, `41: TERRITORY HEAD`, `42: AREA HEAD`, `43: ZONAL HEAD`, `44: REGIONAL HEAD (RGH)`, `45: DEPUTY REGIONAL HEAD`, `46: PROCESS HEAD (PRH)`, `47: GENERAL MANAGER`, `48: TEAM LEADER SALES (TLS)`, `49: CIRCLE HEAD`, `50: DIVISION HEAD (DVH)`, `51: PROCESS MANAGER (PRM)`, `57: CLUSTER HEAD (CLH)`.
- **User Population:** Only `CLUSTER HEAD (57)` has active users (`3` active, `2` deleted); `HOD (21)`, `BSH (37)`, `STH (40)`, `PRH (46)`, `TLS (48)`, `PRM (51)` have soft-deleted users; remaining hierarchy roles have `0` users.
- **Menu Privileges (`tbl_role_privilege`):** `1` to `9` screens (primarily `Adm_AllTransactionExportHierarchy.aspx`, quotation coordination, and team reports).
- **Allowed CRUD:** `R` on `tbl_transaction`, `tbl_agent`, `tbl_employee`, `tbl_appquotationrequest`; `U` on quotation coordination where assigned.
- **Branch & Owner Scope:** **Hierarchy-Scoped** (`sp_SelectTransactionExportByHierarchy` traverses the `tbl_employee` reporting hierarchy rooted at the logged-in manager's `EmpId`).

---

### 2.7 Tier 7 — Franchise Ecosystem Roles (`RoleId` 9, 16, 20, 52, 53, 54)

| Role ID & Name | Active / Total Users | `isappuser=1` | Menu Screens | Primary Responsibilities & Allowed CRUD | Branch & Franchise Scope |
|---|---:|---:|---:|---|---|
| `9: FRANCHISE (FRN)` | 31 / 70 | 0 | 18–28 | Franchise Partner portal login (`Sp_CheckloginfrFranchaise` sets `Session["FranchaiseId"]`). `C, R, U` on `tbl_customer`, `tbl_custvehicle`, `tbl_transaction` (`PE_TransactionEntry`, `PolicyTransactionNew`), `tbl_agent` (`mst_FranchiseAgent.aspx`). Also views `CashierApprovalNew.aspx` (scoped to franchise) and franchise wallet ledger. | Scoped to own `BranchId` (`1..11`) **AND** locked to `Session["FranchaiseId"]` |
| `52: FRANCHISE TYPE 2 (FRT2)` | 0 / 2 | 0 | 5 | Tier-2 Franchise partner (`PE_TransactionEntry.aspx`, transaction reports) | Scoped to `BranchId` & `FranchaiseId` |
| `53: FRANCHISE TYPE 3 (FRT3)` | 1 / 3 | 0 | 8 | Tier-3 Franchise partner (`PE_TransactionEntry.aspx`, `mst_FranchiseAgent.aspx`, reports) | Scoped to `BranchId` & `FranchaiseId` |
| `54: FRANCHISE OPERATOR (FOPR)` | 2 / 2 | 0 | 8 | Data-entry operator working for a Franchise (`PE_TransactionEntry.aspx`, `PolicyTransactionNew.aspx`) | Scoped to `BranchId` & `FranchaiseId` |
| `20: FRANCHISE SALES EXECUTIVE (FSE)` | 2 / 4 | 2 | 1 | Sales executive under a franchise (mobile + 1 portal screen) | Scoped to `FranchaiseId` & own `EmpId` |
| `16: FRANCHISE AGENT (FAGT)` | 59 / 60 | 60 | 0 | Mobile sub-agent under a franchise (`isappuser=1`) | Scoped to own `AgentId` under parent `FranchaiseId` |

---

### 2.8 Tier 8 — External POSP / Mobile Agents & Aggregator Partners (`RoleId` 4, 17, 18, 56)

#### `4: AGENT` (`AGT`)
- **User Population:** `3,018` total (`2,473` active, `545` deleted) — **79.0% of all users in `tbl_user`**.
- **Portal vs. App Access:** `100%` (`3,018 / 3,018`) have `isappuser = 1` and `0` web portal menu privileges. `Log_In.aspx.cs` explicitly rejects their login to the web portal (`"Not Permitted to access Portal"`).
- **Primary Responsibilities:** Using the Mobile App (`Service.asmx`) to request quotations (`InsertQuotationRequest`), request break-in inspections (`InsertInspectionRequest`), submit policy proposals (`InsertAppTransactionNew`), view own policy book (`GetPolicyListByAgent`), view own commission/wallet ledger (`GetAgentAccountStatement`), and submit claims/endorsements.
- **Allowed CRUD:**
  - `C`, `R` on `tbl_appquotationrequest`, `tbl_appinspection`, `tbl_transactionappnew`, `tbl_appendorsement`, `tbl_claims`, `tbl_walletrequest`.
  - `R` on own `tbl_transaction`, `tbl_accountdetails`, `tbl_customer`, `tbl_custvehicle`.
  - **MUST NOT** have direct `C/U/D` access to back-office `/api/v1/customers` or `/api/v1/customers/{id}/vehicles` endpoints unless submitted through an agent-scoped proposal workflow.
- **Branch Scope:** Assigned `BranchId` (`1` or `2`).
- **Owner / Agent Scope:** **Strict Self-Ownership (`AgentId == current_user.agent_id`)**.

#### `17: POLICY BAZAR (PBZ)`, `18: POLICY BAZAR AGENT (PBAG)`, `56: Broker partner (Brp)`
- **Status:** Legacy partner/aggregator roles (`17` and `18` have `role_deleted = 1` in `tbl_userrole`, though 1 active user row remains for each; `56` has 1 deleted user).

---

## 3. Consolidated Role Permission & Scope Matrix for FastAPI (Phase 5G Target)

| Role Group | Role IDs | Customer & Vehicle Back-Office CRUD (`/api/v1/customers`) | Policy Intake & Booking (`tbl_transaction`) | Financial & Commission Approvals | Master Data Write (`mst_*`) | Branch Scope Rule | Entity Ownership Rule |
|---|---|---|---|---|---|---|---|
| **Executive / Super-Admin** | `1 (OWNER)`, `2 (ADMIN)`, `28 (IT SUPPORT)` | `C, R, U, D` | `C, R, U, D` | Full (`Cashier`, `Accountant`, `Owner`, `Wallet`, `Commission`) | `C, R, U, D` | **All Branches** | **Global** |
| **Finance / Accounts** | `11 (ACCOUNT)`, `27 (ACCOUNT HEAD)` | `R` only | `R, U (Approve), D (Cancel)` | `Cashier`, `Accountant`, `Wallet`, `Commission`, `Cheque` | `C, R, U` | **All Branches** | **Global** |
| **Cashier** | `7 (CASHIER)` | `R` only | `R, U (Cashier Approve)` | `Cashier` only | `R` only | `Own Branch` | Branch-wide |
| **Underwriting Operators** | `6 (OPERATOR)`, `19 (OPERATOR HEAD)`, `33 (ALL USER)`, `35 (Freelancer)`, `55 (OTHER)`* | `C, R, U` (`55`: `C, R` via Intake) | `C, R, U` | None | `R` (subset `C, U` for `6, 33`) | `Own Branch` | Branch-wide |
| **Franchise Portal Users** | `9 (FRANCHISE)`, `52 (FRT2)`, `53 (FRT3)`, `54 (FOPR)` | `C, R, U` | `C, R, U` | Franchise Cashier view (`9`) | `R` only | `Own Branch` | **Locked to `FranchaiseId`** |
| **Domain Coordinators** | `12 (END)`, `13 (CLM)`, `14 (QUT)`, `15 (INS)` | `R` (`12`: `U` via Endorsement) | `R, U` (Domain-specific) | None | `R` only | `Own Branch` | Branch-wide |
| **Field Sales & Hierarchy** | `5 (RSM)`, `24 (LCHD)`, `32 (IE)`, `21, 37–51, 57` | `R` (via Quote/Policy) | `C (App Staging), R` | None | `R` only | `Own Branch` / Hierarchy | **Locked to `EmpId` / Subordinate Tree** |
| **Mobile Agents** | `4 (AGENT)`, `16 (FRANCHISE AGENT)` | `R` (Own Customers/Vehicles only) | `C (App Staging), R (Own)` | None (Request Wallet only) | `R` only | `Own Branch` | **Locked to `AgentId`** |
