# PHASE 16 — BUSINESS RULE PRIORITY RECONCILIATION
## Reliable-Insurance-Backend: Forensic Analysis & Priority Classification of 6 Missing Business Rules

---

### 1. Executive Summary & Context
In Phase 16 Stage A, exactly 14 business rules were audited across administrative and governance domains:
- **5 Rules at PARITY**: `LBR-001` (User Login), `LBR-002` (Mobile/OTP Login), `LBR-004` (Branch Isolation), `LBR-012` (Hierarchy Cascade), `LBR-141` (User Activation Status).
- **2 Rules at SECURITY HARDENING**: `LBR-003` (Dynamic RBAC Hardened to Server Route Gating), `LBR-142` (Bcrypt Password Hashing).
- **1 Rule at PARTIAL**: `LBR-148` (Cheque Lockout Enforcement via Phase 15B Overdue Job).
- **6 Missing Business Rules**: `LBR-005`, `LBR-143`, `LBR-144`, `LBR-145`, `LBR-146`, `LBR-147`.

This document performs an independent priority reconciliation of the **six missing business rules**, evaluating the security, financial, and operational impact of each rule to determine its exact migration priority and classification.

---

### 2. Forensic Analysis of the Six Missing Business Rules

#### Rule 1: `LBR-005` — Ownership Hierarchy Strings Serialization
- **Legacy Source**: `AllMaster.cs:L290-296` (`API_Employee`), `API_Transaction:L576-577`, `DAL_Operations.cs`
- **Business Purpose**: Serialize 5-level organizational hierarchy IDs (`ClassId`, `BProcessId`, `BLineId`, `FuncId`, `DesnId`, `ReportingId`) into composite strings `Hei_Data`, `Hie_DataSales`, and `Hie_DataOprn` stamped onto employee master records and policy transactions.
- **Affected Tables**: `tbl_employee`, `tbl_transaction`
- **Affected API / Workflow**: Employee onboarding (`PUT /api/v1/employees/{id}/hierarchy`) and transaction metadata stamping.
- **Security Impact**: Low. These are organizational classification strings and do not alter access control boundaries.
- **Financial Impact**: Low. Direct commission payouts and accounting distributions rely on foreign keys (`SalesExecutiveId`, `FranchiseId`, `AgentId`), not on serialized string tokens.
- **Operational Impact**: Medium. Preserves historical reporting consistency for corporate organizational structure reviews.
- **Priority**: **P3**
- **Migration Classification**: **SHOULD MIGRATE**
- **Rationale**: While useful for historical audit trace, it is not a blocker for core production transactions or financial ledgers.

#### Rule 2: `LBR-143` — Self Password Change & Old Password Verification
- **Legacy Source**: `Insurance\Clerk\ChangePassword.aspx.cs:L32-110`, `sp_ChangePassword`, `DAL_Operations.cs`
- **Business Purpose**: Enforce that a user can change their own password only by providing and successfully verifying their existing password. Provide global administrators the ability to reset forgotten user credentials with explicit audit logging.
- **Affected Tables**: `tbl_user`
- **Affected API / Workflow**: Credential maintenance endpoint (`PUT /api/v1/users/{id}/password`).
- **Security Impact**: Critical. Essential credential lifecycle control preventing unauthorized password hijacking, enforcing minimum length/complexity, and logging credential rotation.
- **Financial Impact**: Low direct impact; prevents unauthorized account takeover.
- **Operational Impact**: High. Everyday self-service credential maintenance and administrative unlock workflow.
- **Priority**: **P1**
- **Migration Classification**: **MUST MIGRATE**
- **Rationale**: Mandatory security workflow for production user administration.

#### Rule 3: `LBR-144` — Persistent Login History Audit Logging
- **Legacy Source**: `Insurance\Log_In.aspx.cs:L50-54`, `Insurance\Log_Out.aspx.cs:L22`, `sp_insertLoginHistory`, `sp_SelectLoginHistory`
- **Business Purpose**: Record every successful authentication, failed login attempt, and logout into persistent database storage (`tbl_loginhistory`) capturing client `IPAddress`, `UserId`, `UserName`, `funPerform`, `Remark`, and timestamp.
- **Affected Tables**: `tbl_loginhistory`
- **Affected API / Workflow**: `POST /api/v1/auth/login`, `POST /api/v1/auth/logout`, `GET /api/v1/auth/login-history`.
- **Security Impact**: Critical. Non-repudiation, forensic incident investigation, brute force attack detection, and IRDAI/ISO 27001 regulatory cybersecurity compliance.
- **Financial Impact**: Low direct impact.
- **Operational Impact**: High. Required by compliance officers and system administrators for security audits.
- **Priority**: **P1**
- **Migration Classification**: **MUST MIGRATE**
- **Rationale**: Compliance and security audit trail mandatory for production operation.

#### Rule 4: `LBR-145` — Agent / POSP KYC Verification State Machine
- **Legacy Source**: `Insurance\Clerk\mst_Agent.aspx.cs:L180`, `sp_UpdateAgentKYC`, `API_Agent:L1260`
- **Business Purpose**: Enforce a formal 3-state KYC machine (`PENDING_VERIFICATION` $\rightarrow$ `VERIFIED` or `REJECTED`) with reviewer timestamp and compliance remarks. Prevent unverified agents from booking policies or receiving commission disbursements.
- **Affected Tables**: `tbl_agent`
- **Affected API / Workflow**: Agent compliance review (`PATCH /api/v1/agents/{id}/kyc`).
- **Security Impact**: High. Prevents unvetted or fraudulent POSP onboarding; satisfies regulatory insurance intermediary verification rules.
- **Financial Impact**: High. Prevents commission disbursement to unverified agents and protects against fraud.
- **Operational Impact**: High. Core compliance verification gate before partner goes live.
- **Priority**: **P1**
- **Migration Classification**: **MUST MIGRATE**
- **Rationale**: Direct financial and regulatory compliance blocker.

#### Rule 5: `LBR-146` — Sub-Franchise Recursive Hierarchy Traversal
- **Legacy Source**: `Insurance\Clerk\mst_Franchise.aspx.cs:L210`, `API_franchise`, recursive SQL query
- **Business Purpose**: Support multi-tier franchise partner hierarchies by traversing recursive parent-child associations (`ParentFranchiseId`) to render network tree structures.
- **Affected Tables**: `tbl_franchise`
- **Affected API / Workflow**: Partner network portal (`GET /api/v1/franchises/{id}/hierarchy`).
- **Security Impact**: Low. Tenant isolation must ensure partner users cannot view franchises outside their authorized branch or lineage.
- **Financial Impact**: Low/Medium. Franchise commission calculations already resolve direct parent IDs.
- **Operational Impact**: Medium. Enhances partner portal usability for master franchise operators.
- **Priority**: **P3**
- **Migration Classification**: **SHOULD MIGRATE**
- **Rationale**: Important convenience and network visualization feature, but not a financial or security blocker.

#### Rule 6: `LBR-147` — Reference Master Immutability & Soft-Delete Filtering
- **Legacy Source**: `mst_FuelType.aspx.cs`, `mst_Financier.aspx.cs`, `mst_Surveyor.aspx.cs`
- **Business Purpose**: Reference lookup tables (`tbl_fueltype`, `tbl_financier`, `tbl_surveyor`) must filter queries strictly by `isdeleted = '0'`, prevent accidental hard deletes, and restrict modification to global administrative roles.
- **Affected Tables**: `tbl_fueltype`, `tbl_financier`, `tbl_surveyor`
- **Affected API / Workflow**: `/api/v1/masters/fuel-types`, `/masters/financiers`, `/masters/surveyors`.
- **Security Impact**: Medium. Protects reference integrity and prevents unauthorized mutation of shared dropdown metadata.
- **Financial Impact**: Low direct impact.
- **Operational Impact**: High. Feeds dropdown menus across Rating (Fuel Type), Policy Booking (Financier), and Claims (Surveyor).
- **Priority**: **P2**
- **Migration Classification**: **MUST MIGRATE**
- **Rationale**: Essential reference data integrity for everyday operational workflows.

---

### 3. Consolidated 6-Rule Priority Reconciliation Ledger

| Rule ID | Domain | Business Purpose | Priority | Migration Class | Security Impact | Financial Impact | Operational Impact |
|:---:|:---:|---|:---:|:---:|:---:|:---:|:---:|
| **`LBR-005`** | Employee Hierarchy | 5-level hierarchy serialization strings | **P3** | **SHOULD MIGRATE** | Low | Low | Medium |
| **`LBR-143`** | Credential Lifecycle | Password change with old-password verify | **P1** | **MUST MIGRATE** | Critical | Low | High |
| **`LBR-144`** | Audit Logging | Persistent login/logout/failure DB logs | **P1** | **MUST MIGRATE** | Critical | Low | High |
| **`LBR-145`** | Agent Compliance | Formal 3-state KYC state machine | **P1** | **MUST MIGRATE** | High | High | High |
| **`LBR-146`** | Franchise Hierarchy | Sub-franchise recursive tree traversal | **P3** | **SHOULD MIGRATE** | Low | Low/Med | Medium |
| **`LBR-147`** | Reference Masters | Soft-delete filtering & admin-only write | **P2** | **MUST MIGRATE** | Medium | Low | High |

---

### 4. Quantitative Summary
- **Total Missing Rules Reconciled**: **6**
- **Priority Distribution**:
  - **P0**: **0**
  - **P1**: **3 (50.0%)** (`LBR-143`, `LBR-144`, `LBR-145`)
  - **P2**: **1 (16.7%)** (`LBR-147`)
  - **P3**: **2 (33.3%)** (`LBR-005`, `LBR-146`)
- **Classification Distribution**:
  - **MUST MIGRATE**: **4 (66.7%)**
  - **SHOULD MIGRATE**: **2 (33.3%)**
  - **OPTIONAL / OBSOLETE / UNKNOWN**: **0**
