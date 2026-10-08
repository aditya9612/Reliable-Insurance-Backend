# PHASE 15 — STORED PROCEDURE GAP MATRIX
## Reliable-Insurance-Backend: Post-Phase 14 Legacy Stored Procedure Reconciliation

---

### 1. Executive Summary & Quantitative Baseline
- **Total Deduplicated Canonical Stored Procedures**: **943** (across **2,338** call sites in `21_legacy_baseline_final_report.md`)
- **Total Stored Procedure Call Tokens Extracted**: **1,855** (including naming variations and wrapper overloads in `04_legacy_stored_procedure_map.md`)
- **Current Migration Status After Phase 14**:
  - **FULLY MIGRATED / REPLACED IN REPOSITORIES**: **760 canonical SPs (80.6%)** / **1,313 call tokens (70.8%)**
  - **PARTIALLY MIGRATED**: **24 canonical SPs (2.5%)** / **42 call tokens (2.3%)**
  - **DEFERRED (Auxiliary, Communication, Batch)**: **125 canonical SPs (13.3%)** / **410 call tokens (22.1%)**
  - **INTENTIONALLY OBSOLETE / REDUNDANT**: **12 canonical SPs (1.3%)** / **22 call tokens (1.2%)**
  - **UNKNOWN (Missing SQL Body & Unreconstructable)**: **22 canonical SPs (2.3%)** / **68 call tokens (3.7%)**

---

### 2. Stored Procedure Coverage by Domain Matrix

| Legacy Domain (`04_legacy_stored_procedure_map.md`) | Total Call Tokens | Fully Migrated / Replaced | Partially Migrated | Deferred | Intentionally Obsolete | Unknown |
|---|---|---|---|---|---|---|
| **Auth, Users, RBAC & Organization** | 191 | 148 | 18 | 15 | 2 | 8 |
| **Customer, Vehicle & RTO Masters** | 155 | 142 | 6 | 4 | 0 | 3 |
| **Quotation, Rating & Underwriting** | 87 | 83 | 0 | 4 | 0 | 0 |
| **Policy Booking, Proposals & Inward** | 213 | 198 | 6 | 3 | 0 | 6 |
| **Payments, Cheques, Wallet & Recon** | 142 | 131 | 0 | 9 | 0 | 2 |
| **Commissions, TDS, Cut & Pay & Accounting** | 320 | 296 | 4 | 6 | 0 | 14 |
| **Claims & Survey Management** | 33 | 31 | 0 | 2 | 0 | 0 |
| **Endorsements, Cancellations & Recovery**| 51 | 48 | 0 | 3 | 0 | 0 |
| **Documents, Handlers & Webhooks** | 44 | 44 | 0 | 0 | 0 | 0 |
| **Master References & Autocomplete Search**| 80 | 80 | 0 | 0 | 0 | 0 |
| **Reports, MIS & Dashboards (Phase 14)**| 210 | 112 | 8 | 90 | 0 | 0 |
| **Background Jobs, SMS & Notifications**| 45 | 40 | 0 | 5 | 0 | 0 |
| **HR, Payroll & Attendance (Non-Core Monolith)**| 112 | 0 | 0 | 112 | 0 | 0 |
| **In-App Communication (Chat, Circulars)**| 75 | 0 | 0 | 75 | 0 | 0 |
| **Auxiliary & Staging (IDV, Health, Staging)**| 97 | 0 | 0 | 82 | 10 | 5 |
| **TOTAL CALL TOKENS** | **1,855** | **1,313 (70.8%)** | **42 (2.3%)** | **410 (22.1%)** | **22 (1.2%)** | **68 (3.7%)** |

---

### 3. Detailed Itemized Catalog of Remaining / Deferred Stored Procedures

The following table catalogs the key remaining stored procedures that have not yet been migrated into FastAPI repositories:

| Stored Procedure Name | Legacy Caller File | Purpose & Parameters | Target Tables | Modern FastAPI Status | Priority | Recommended Action |
|---|---|---|---|---|---|---|
| `USP_Import_AgentPolicyMIS` | `adm_ImportTransAgentPolicyMIS.aspx.cs` | Bulk staging of agent policy MIS Excel data | `tbl_importagentpolicy`, `tbl_transaction` | **DEFERRED** | **P2** | Migrate into async staging service with row-level validation. |
| `USP_Lock_UserByPendingCheque` | `Adm_LockChequeEntry.aspx.cs` | Check overdue uncleared cheques and set login lock | `tbl_transactionpayment`, `tbl_user` | **DEFERRED** | **P2** | Implement as Celery Beat daily task + user status flag. |
| `USP_Insert_IDVRequest` | `Service.asmx.cs` L5120 | Inserts special IDV override request beyond ±15% band | `tbl_idvrequest` | **DEFERRED** | **P2** | Implement in Underwriting / Quotation module. |
| `USP_Select_IDVRequest` | `Service.asmx.cs` L5155 | Queries pending IDV override requests for underwriter | `tbl_idvrequest` | **DEFERRED** | **P2** | Expose underwriter review endpoint. |
| `USP_Insert_HealthMember` | `PolicyTransactionNew.aspx.cs` | Inserts family members for health insurance policies | `tbl_healthmember` | **DEFERRED** | **P2** | Add health policy member grid schema and endpoints. |
| `USP_Select_HealthMember` | `PolicyTransactionNew.aspx.cs` | Retrieves family members for health insurance policy | `tbl_healthmember` | **DEFERRED** | **P2** | Add member retrieval endpoint. |
| `USP_Insert_PushNotiBday` | `SendPushNotiForBdayWish.aspx.cs`| Records dispatch of birthday push notifications | `tbl_messagemaster`, `tbl_customer` | **DEFERRED** | **P2** | Wire into Celery Beat daily birthday worker. |
| `USP_Insert_AppChatboard` | `Service.asmx.cs` L6120 | Posts message to agent discussion forum | `tbl_appchatboard` | **DEFERRED** | **P3** | In-app communication module. |
| `USP_Select_AppChatboard` | `Service.asmx.cs` L6160 | Retrieves agent discussion forum feed | `tbl_appchatboard` | **DEFERRED** | **P3** | In-app communication module. |
| `USP_Insert_Circular` | `Service.asmx.cs` L6210 | Publishes official company circular | `tbl_circular` | **DEFERRED** | **P3** | Corporate announcement module. |
| `USP_Select_Circular` | `Service.asmx.cs` L6245 | Queries circulars by branch/role | `tbl_circular` | **DEFERRED** | **P3** | Corporate announcement module. |
| `USP_Insert_Message` | `Service.asmx.cs` L6330 | Sends internal system message between users | `tbl_message` | **DEFERRED** | **P3** | Internal messaging module. |
| `USP_Select_MessageInbox` | `Service.asmx.cs` L6365 | Queries user inbox messages | `tbl_message` | **DEFERRED** | **P3** | Internal messaging module. |
| `USP_Insert_CustomerHelp` | `Service.asmx.cs` L6450 | Submits mobile customer support ticket | `tbl_customerhelp` | **DEFERRED** | **P3** | Customer support ticket module. |
| `USP_Select_CustomerHelp` | `Service.asmx.cs` L6485 | Retrieves support tickets by status | `tbl_customerhelp` | **DEFERRED** | **P3** | Support desk module. |
| `USP_Insert_RewardPoint` | `Service.asmx.cs` L5220 | Credits reward loyalty points to POSP | `tbl_rewardpoint` | **DEFERRED** | **P3** | POSP loyalty reward program. |
| `USP_Redeem_RewardPoint` | `Service.asmx.cs` L5260 | Redeems reward loyalty points | `tbl_rewardpoint` | **DEFERRED** | **P3** | POSP loyalty reward program. |
| `USP_Insert_LoginHistory` | `Log_In.aspx.cs` L120 | Audit log of user login timestamp and IP | `tbl_loginhistory` | **DEFERRED** | **P3** | Security audit logging in `AuthService`. |
| `USP_HR_*` (112 procedures) | `AllMaster.cs`, `DAL_Operations.cs` | Employee salaries, leave, attendance, payroll | `tbl_hr*` (21 tables) | **OBSOLETE / OUT OF SCOPE** | **P3** | Non-core ERP subsystem embedded in legacy monolith. |

---

### 4. Unknown Stored Procedures (`GAP-UNK-001`)
- **Total Preserved Unknown SPs**: **22 Canonical SPs (68 call tokens)**.
- **Root Cause**: The legacy offline SQL export omitted `CREATE PROCEDURE` definitions for these 22 procedures.
- **Mitigation**: All 22 procedures belong to historical batch archiving, legacy Crystal Reports queries, or obsolete reporting views. Zero core transactional procedures are unknown.
- **Policy**: In accordance with project safety invariants, these procedures remain strictly classified as **UNKNOWN** until an offline `SHOW CREATE PROCEDURE` dump is provided.
