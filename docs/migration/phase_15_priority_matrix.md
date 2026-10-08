# PHASE 15 — PRIORITY MATRIX
## Reliable-Insurance-Backend: Post-Phase 14 Priority & Criticality Classification

---

### 1. Executive Summary & Priority Governance
- **Priority Rules**:
  - **P0**: Financial / security / data-integrity / business-critical missing functionality (Immediate Blocker).
  - **P1**: Important operational / business workflow affecting daily primary transactions.
  - **P2**: Supporting operational functionality / bulk data imports / batch jobs / administrative profile utilities.
  - **P3**: Low-value / legacy UI-only / auxiliary communication / non-core ERP / intentionally obsolete modules.
- **Post-Phase 14 Priority Distribution**:
  - **P0 Items**: **0** (All primary financial, rating, booking, ledger, claims, and security engines are 100% complete).
  - **P1 Items**: **0** (All primary transactional business workflows are operational).
  - **P2 Items**: **9 items** (Bulk Excel imports, scheduled batch jobs, IDV queue, health grid, detailed profile management).
  - **P3 Items**: **10 items** (In-app communication, reward points, dynamic menu toggles, HR/payroll, legacy ASMX shim).

---

### 2. Comprehensive Priority Matrix

| Priority | Item Code | Item Description | Legacy Evidence | Business Impact | Proposed Future Phase |
|:---:|---|---|---|---|:---:|
| **P2** | `GAP-P2-01` | Bulk Excel Policy MIS Upload | `adm_ImportTransAgentPolicyMIS.aspx.cs` / `tbl_importagentpolicy` | Enables bulk ingestion of external broker policy sheets into staging | **Candidate A (Batch & Imports)** |
| **P2** | `GAP-P2-02` | Overdue Cheque User Login Lock (`LBR-069`)| `Adm_LockChequeEntry.aspx.cs` / `tbl_user` | Automated Celery task preventing bookings by agents with bounced/aged cheques | **Candidate A (Batch & Imports)** |
| **P2** | `GAP-P2-03` | Customer Birthday Greeting Dispatch | `SendPushNotiForBdayWish.aspx.cs` | Automated Celery task dispatching personalized birthday greetings | **Candidate A (Batch & Imports)** |
| **P2** | `GAP-P2-04` | Stale E-Wallet Lock & Storage Cleanup | Legacy manual database cleanup scripts | Automated Celery maintenance task releasing abandoned locks | **Candidate A (Batch & Imports)** |
| **P2** | `GAP-P2-05` | Special IDV Override Approval Queue | `Service.asmx.cs` L5120 / `tbl_idvrequest` | Allows underwriters to approve vehicle IDVs outside standard ±15% band | **Candidate A (Batch & Imports)** |
| **P2** | `GAP-P2-06` | Non-Motor Health Family Member Grid (`LBR-058`)| `PolicyTransactionNew.aspx.cs` / `tbl_healthmember` | Enables staging family members (Spouse, Child, Parent) on health policies | **Candidate A (Batch & Imports)** |
| **P2** | `GAP-P2-07` | Detailed Employee Staff Directory CRUD | `adm_EmployeeMaster.aspx.cs` / `tbl_employee` | Administrative user directory for internal branch staff and designations | **Candidate B (Admin & Profiles)**|
| **P2** | `GAP-P2-08` | Detailed POSP Agent Profile & KYC CRUD | `adm_AgentMaster.aspx.cs` / `tbl_agent` | Administrative directory for POSP onboarding, certificates, and bank details | **Candidate B (Admin & Profiles)**|
| **P2** | `GAP-P2-09` | Detailed Franchise Hierarchy & Profile CRUD | `adm_FranchiseMaster.aspx.cs` / `tbl_franchise`| Administrative management of franchise master data and wallet rules | **Candidate B (Admin & Profiles)**|
| **P3** | `GAP-P3-01` | Dynamic Role Menu Privileges API | `Adm_RolePrivilege.aspx.cs` / `tbl_role_privilege` | Frontend UI menu tree toggle matrix per role | **Candidate B (Admin & Profiles)**|
| **P3** | `GAP-P3-02` | User Login Audit Trail History | `Log_In.aspx.cs` / `tbl_loginhistory` | Persistent security logging of user login timestamps and IP addresses | **Candidate B (Admin & Profiles)**|
| **P3** | `GAP-P3-03` | POSP Performance Reward Points Engine | `Service.asmx.cs` L5220 / `tbl_rewardpoint` | Agent loyalty point accrual and promotional gift redemption claims | **Candidate B (Admin & Profiles)**|
| **P3** | `GAP-P3-04` | In-App Staff Discussion Forum (Chatboard) | `Service.asmx.cs` L6120 / `tbl_appchatboard` | Internal messaging board for POSP agents and clerks | **Candidate D (Communication)** |
| **P3** | `GAP-P3-05` | Corporate Circular Announcements | `Service.asmx.cs` L6210 / `tbl_circular` | Administrative broadcasting of circular notices and PDF attachments | **Candidate D (Communication)** |
| **P3** | `GAP-P3-06` | Internal System Messaging (Inbox/Sent) | `Service.asmx.cs` L6330 / `tbl_message` | User-to-user direct internal email-like messaging | **Candidate D (Communication)** |
| **P3** | `GAP-P3-07` | Mobile Customer Help Desk Tickets | `Service.asmx.cs` L6450 / `tbl_customerhelp` | In-app customer support issue submission and status tracking | **Candidate D (Communication)** |
| **P3** | `GAP-P3-08` | Mobile Staff GPS Attendance Check-In | `Service.asmx.cs` L4520 / `tbl_appattendance` | Internal employee attendance and location logging (Non-Core ERP) | **Candidate D (Communication)** |
| **P3** | `GAP-P3-09` | Legacy Mobile `/Service.asmx/*` Adapter Shim | `Service.asmx.cs` (339 WebMethods) | Optional SOAP/JSON translation bridge for un-upgraded legacy mobile apps | **Candidate C (Legacy Shim)** |
| **P3** | `GAP-P3-10` | HR, Payroll, Leave & Salary Subsystem | `AllMaster.cs` L2242 / 21 `tbl_hr*` tables | Internal company HR payroll module embedded in legacy monolith | **Candidate E (Out of Scope)** |

---

### 3. Conclusion & Risk Assessment
- **Core Platform Stability**: With 0 P0 and 0 P1 items remaining, the core Reliable Insurance Backend is fully production-ready for policy issuance, payments, claims, endorsements, accounting, and reporting.
- **Recommended Prioritization**: Future work should prioritize **Candidate A (Operational Batch Jobs, Bulk Imports & Staging Utilities)** followed by **Candidate B (Administrative Profiles & Master Directories)**.
