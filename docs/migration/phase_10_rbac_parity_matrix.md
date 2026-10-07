# Phase 0 → Phase 10 Forensic Parity Audit: Authentication, RBAC, Branch & Ownership Hierarchy Parity Matrix

**Audit Date**: 2026-10-07  
**Repository**: `Reliable-Insurance-Backend`  
**Primary Baseline Reference**: `docs/migration/12_legacy_rbac_branch_ownership_baseline.md`, `docs/migration/19_legacy_business_rule_master_register.md` (`LBR-001`–`LBR-005`, `LBR-012`, `LBR-018`–`LBR-025`)  
**Audit Mode**: **READ-ONLY FORENSIC PARITY AUDIT**

---

## 1. Authentication & Session/Token Parity Audit (Section 11)

| Capability | Legacy Implementation (`12_legacy_rbac_branch_ownership_baseline.md`) | New Implementation (`app/api/v1/endpoints/auth.py`, `app/core/rbac.py`) | Status | Evidence & Notes |
|---|---|---|---|---|
| **Web / Portal Credential Login (`LBR-001`)** | `Log_In.aspx.cs::btnLogin_Click` $\rightarrow$ `BLL_CheckLogIn` (`sp_CheckLogIn`) sets `Session["UserId"]`, `Session["RoleId"]`, `Session["BranchId"]`, `Session["EmpId"]`, `Session["TDS"]`. | `POST /api/v1/auth/login` verifies username/password, checks `is_active`, and issues signed JWT access/refresh tokens containing `sub` (`user_id`), `role_id`, `role_name`, `branch_id`, `emp_id`, `agent_id`, `franchise_id`. | `PARITY` / `INTENTIONAL HARDENING` | Legacy plaintext/simple hash upgraded to Bcrypt with legacy hash fallback (`app/core/security.py`). |
| **Mobile / ASMX Login (`CheckLogIn`, `CheckLogIn1`, `CheckLogIn2`)** | `Service.asmx.cs` authenticates mobile app requests and returns JSON user profile (`UserId`, `RoleId`, `BranchId`, `AgentId`, `FranchiseId`). | Unified under `POST /api/v1/auth/login` and `GET /api/v1/auth/me`. | `PARITY` | `app/api/v1/endpoints/auth.py`. |
| **Mobile OTP Verification (`LBR-002`)** | `Service.asmx.cs` generates and verifies mobile OTP codes via `USP_UpdateOTP` and `Send_SMS.cs`. | *Not implemented* | `MISSING` | `GAP-P5-002` (Severity: `P2`). |
| **Overdue Uncleared Cheque Login Lock (`LBR-091`)** | `Log_In.aspx.cs:L97-L115` invokes `BLL_LockChequeClearingCount`; if $> 0$ for non-Admin (`RoleId != 1`), redirects user to `Clerk/Adm_LockChequeEntry.aspx`. | *Not implemented* | `MISSING` | `GAP-P8-001` (Severity: `P2`). |
| **Login Session Audit Table (`LBR-024`)** | `Log_In.aspx.cs` inserts `InTime`, `OutTime`, and `AddressofIP` into `API_LoginHistory` (`BLL_InsertLoginHistory`). | Uses structured JSON application logs with request correlation IDs instead of `tbl_loginhistory` DB inserts. | `MISSING` | `GAP-P5-002` (Severity: `P2`). |
| **Dynamic Menu & Page Rights (`LBR-003`)** | `Clerk/MasterPage.master.cs` (`BLL_GetSubMenuByRoleId`) and `adm_UserRights.aspx.cs` (`tbl_userrights`: `View`, `Add`, `Edit`, `Delete`). | `UserRight` (`tbl_userrights`) model + `app/core/rbac.py` permission matrix enforcing action-level (`view`, `add`, `edit`, `delete`, `approve`) authorization. | `PARITY` | `app/models/user.py`, `app/core/rbac.py`. |

---

## 2. Role Hierarchy & Principal Isolation Matrix (Section 12)

Per `docs/migration/12_legacy_rbac_branch_ownership_baseline.md`, the legacy system defines 56 role rows in `tbl_role` grouped into primary operational role families. Below is the forensic comparison of role-level data scoping and workflow gates across Phases 5–10:

| Legacy Role Family (`RoleId` / `RoleName`) | Legacy Scope & Permissions (`12_legacy_rbac_branch_ownership_baseline.md`) | New Backend RBAC Enforcement (`app/core/rbac.py` & Domain Services) | Status |
|---|---|---|---|
| **Super Admin / Admin (`RoleId = 1`) & Managing Director (`RoleId = 10`)** | Global access across all `BranchId` values; full access to masters, policy verification, cheque clearance/bounce, wallet top-up approval, commission payout approval/disbursement, voucher entry, trial balance, claim settlement, and endorsement approval/application. | `is_global_admin(user)` grants cross-branch read/write access and full approval rights across Phases 5–10. | `PARITY` |
| **Accountant / Accounts Manager (`RoleId = 2` / `ACCOUNTANT`)** | Branch or global financial access: verifies policies (`adm_PolicyDetails.aspx.cs`), clears/bounces cheques (`Adm_UnclearCheque.aspx.cs`), approves wallet top-ups (`Adm_FranchiseWallet.aspx.cs`), processes commission payouts (`Adm_AgentCommissionPayment.aspx.cs`), posts vouchers (`VoucherEntry.aspx.cs`), views Ledger & Trial Balance, processes NCB Recovery & Policy Cancellation. | Authorized for policy verification, payment/cheque clearance & bounce, insurer reconciliation, wallet top-up approval, commission calculation/payout/reversal, vouchers, ledger statements, trial balance, and financial endorsements. | `PARITY` |
| **Branch Manager (`RoleId = 3` / `BRANCH_MANAGER`)** | Restricted to `BranchId == Session["BranchId"]`; manages branch customers, vehicles, quotations, policies, payments, claims, and branch-level endorsements; cannot disburse commission payouts or post cross-branch journals. | Scoped strictly to `user.branch_id` via `enforce_branch_access`; permitted to approve branch-level operational workflows but blocked from cross-branch access. | `PARITY` |
| **Clerk / Data Entry Operator (`RoleId = 6` / `CLERK`)** | Restricted to `BranchId == Session["BranchId"]`; creates customers, vehicles, quotations, inward/issued policies (`TStatus = "Pending"`), payment receipts, claim intimations (`CL_ClaimNew.aspx.cs`), and endorsement requests (`Endorsment_Request.aspx.cs`); **cannot** approve wallet top-ups, disburse commissions, or approve/apply endorsements. | Scoped strictly to `user.branch_id`; allowed to create customers, vehicles, quotations, policies, payments, claim intimations, and endorsement requests; blocked (`HTTP 403`) from wallet approval, commission payout approval/disbursement, and endorsement approval/apply. | `PARITY` |
| **Telecaller (`RoleId = 4`) & Sales Executive / Team Leader (`RoleId = 5`)** | Scoped to own `BranchId` and assigned hierarchy (`TelecallerId == EmpId` or `SalesManagerId == EmpId`); creates/views quotations and policies for assigned customers. | Enforced via `enforce_branch_access` and hierarchy filters (`telecaller_id`, `sales_manager_id`, `team_leader_id`). | `PARITY` |
| **Franchise / RA (`RoleId = 7` / `FRANCHISE`)** | Restricted to `FranchiseId == Session["FranchiseId"]`; submits wallet top-up requests (`Pending`), books policies using own E-Wallet (`PaymentId = 6`) or Cut & Pay (`PaymentId = 5`), views own wallet ledger, own commission statements, own policies, and own claims/endorsement requests; **cannot** self-approve wallet top-ups, self-approve endorsements, or view other franchises' data. | Enforced via `enforce_principal_access` (`user.franchise_id == record.franchise_id`); blocked (`HTTP 403`) from approving wallet top-ups, approving/applying endorsements, settling claims, or accessing other franchises' wallets/policies/commissions. | `PARITY` |
| **Agent / POS (`RoleId = 8` / `AGENT`) & Sub-Agent (`RoleId = 9`)** | Restricted to `AgentId == Session["AgentId"]` (or `SubAgentId`); creates quotations, views own policies, own commissions, own claims, and requests endorsements on own policies; **cannot** view other agents' policies/commissions or execute admin/accountant approvals. | Enforced via `enforce_principal_access` (`user.agent_id == record.agent_id`); blocked (`HTTP 403`) from cross-agent data access and from all financial/endorsement/claim approval gates. | `PARITY` |
| **Customer (`RoleId = 11` / `CUSTOMER`)** | Self-service mobile/portal access restricted to `CustomerId == Session["CustomerId"]` (view own policies, quotations, claims). | Enforced via `enforce_principal_access` (`user.customer_id == record.customer_id`); read-only/request-only access to own records; blocked (`HTTP 403`) from internal broker operations. | `PARITY` |

---

## 3. 6-Actor Organizational Hierarchy Parity (`LBR-005`, `LBR-012`)

| Hierarchy Actor | Legacy Column (`tbl_transaction`) | New Model Attribute (`PolicyTransaction`) | Cascade & Scoping Behavior | Status |
|---|---|---|---|---|
| **1. Telecaller** | `TelecallerId` (`EmpId`) | `telecaller_id` (`TelecallerId`) | Linked to `tbl_employee`; filters telecaller policy/quotation views (`GAP-P7-003` on target achievement counter). | `PARITY` (Scoping) / `MISSING` (Target counter) |
| **2. Team Leader** | `TeamLeaderId` | `team_leader_id` (`TeamLeaderId`) | Linked to `tbl_employee`; cascades from Telecaller/Branch hierarchy. | `PARITY` |
| **3. Sales Manager** | `SalesManagerId` | `sales_manager_id` (`SalesManagerId`) | Linked to `tbl_employee`; cascades from Agent/Franchise selection (`LBR-012`). | `PARITY` |
| **4. Agent (POS)** | `AgentId` | `agent_id` (`AgentId`) | Linked to `tbl_agent`; drives Tier-2 Agent Commission (`AgtCalOn`, `AgtPer`, `AgtAmt`) and Agent RBAC isolation (`LBR-020`). | `PARITY` |
| **5. Sub-Agent** | `SubAgentId` | `sub_agent_id` (`SubAgentId`) | Linked to `tbl_subagent`; drives Tier-4 Sub-Agent Commission (`SubAgtCalOn`, `SubAgtPer`, `SubAgtAmt`). | `PARITY` |
| **6. Franchise (RA)** | `FranchiseId` (`RAId`) | `franchise_id` (`FranchiseId`) | Linked to `tbl_franchise`; drives Tier-3 Franchise Commission (`FRCalOn`, `FRPer`, `FRAmt`), E-Wallet deduction (`LBR-085`), and Franchise RBAC isolation (`LBR-021`). | `PARITY` |
