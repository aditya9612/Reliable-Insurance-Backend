# PHASE 16 — PRIORITY & MIGRATION ROADMAP MATRIX
## Reliable-Insurance-Backend: Priority Classification & Implementation Roadmap

---

### 1. Priority Classification Guidelines
- **P0 (Critical / Blocker)**: Security vulnerability, financial integrity, or data loss prevention. Must be verified before any production rollout.
- **P1 (High / Core)**: Core production operational workflow missing. Direct impact on everyday back-office functions.
- **P2 (Medium / Administrative)**: Important administrative profile, compliance, or operational capability.
- **P3 (Low / Non-Core / Convenience)**: Non-critical master lookups, internal convenience views, or legacy compatibility shims.

---

### 2. Implementation Action Taxonomy
- **MUST MIGRATE**: Mandatory for completing Phase 16 baseline.
- **SHOULD MIGRATE**: High-value feature; migrate unless external dependency blocks.
- **OPTIONAL**: Low-value legacy feature; migrate only if trivial.
- **OBSOLETE**: Intentionally retired or superseded by modern architecture.
- **UNKNOWN**: Blocked on missing offline evidence; preserved without speculation.

---

### 3. Master Priority Matrix

| # | Item / Functional Component | Domain | Severity | Action Classification | Rationale & Impact | Target Implementation Stage |
|---|---|:---:|:---:|:---:|---|:---:|
| 1 | **Admin User Management CRUD** (`POST/PUT/DELETE /api/v1/users`) | A (User) | **P1** | **MUST MIGRATE** | Administrators must be able to create, update, reassign, and deactivate system user accounts without manual SQL queries. | Phase 16B |
| 2 | **User Password Change & Reset** (`PUT /api/v1/users/{id}/password`) | A (User) | **P1** | **MUST MIGRATE** | Users must be able to change passwords with old password verification; admins must be able to reset forgotten credentials. | Phase 16B |
| 3 | **Login History Table & Audit API** (`tbl_loginhistory`, `/api/v1/auth/login-history`) | C (Audit) | **P2** | **MUST MIGRATE** | Regulatory IRDAI cybersecurity audit requirement for tracking client IP, login successes, and authentication failures. | Phase 16B |
| 4 | **Agent KYC Verification Machine** (`PATCH /api/v1/agents/{id}/kyc`) | E (Agent) | **P2** | **MUST MIGRATE** | Enforces compliance lifecycle (`PENDING` $\rightarrow$ `VERIFIED` / `REJECTED`) before permitting policy issuance or commissions. | Phase 16B |
| 5 | **Auxiliary Master Tables** (`tbl_fueltype`, `tbl_financier`, `tbl_surveyor`) | G (Masters) | **P2** | **MUST MIGRATE** | Completes reference lookups required by Motor Rating (Fuel Type), Policy Booking (Financier), and Claims (Surveyor). | Phase 16B |
| 6 | **Dynamic Menu Privilege API** (`tbl_role_privilege`, `/api/v1/admin/privileges`) | B (RBAC) | **P2** | **SHOULD MIGRATE** | Enables frontend SPA to dynamically tailor sidebar navigation trees per user role and branch without compromising backend RBAC. | Phase 16B |
| 7 | **Employee Hierarchy Strings** (`Hie_Data`, `Hie_DataSales`, `Hie_DataOprn`) | D (Emp) | **P3** | **SHOULD MIGRATE** | Supports legacy transaction stamp parity for 5-level organizational hierarchy tracking. | Phase 16B |
| 8 | **Sub-Franchise Recursive Hierarchy** (`GET /api/v1/franchises/{id}/hierarchy`) | F (Fran) | **P3** | **SHOULD MIGRATE** | Allows multi-tier partner portals to traverse child franchise networks and revenue shares. | Phase 16B |
| 9 | **Admin System & Security Counters** (`GET /api/v1/admin/dashboard/counters`) | I (Admin) | **P3** | **SHOULD MIGRATE** | High-level summary metrics (active users, pending KYC, locked accounts) for administrator dashboard overview. | Phase 16B |
| 10 | **Cheque Overdue User Lockout Worker** (`LBR-069`) | C (Lockout) | **P2** | **SHOULD MIGRATE** | Automatically blocks user booking when uncleared cheques exceed threshold. | Phase 16B |
| 11 | **Staff / POSP In-App Chatboard** (`tbl_appchatboard`) | Aux | **P3** | **OPTIONAL** | Internal discussion forum embedded in legacy mobile app; low business priority. | Future / Deferred |
| 12 | **Company Circulars & Notices** (`tbl_circular`) | Aux | **P3** | **OPTIONAL** | Internal broadcast bulletin board; low business priority. | Future / Deferred |
| 13 | **Mobile Employee GPS Tracking** (`API_EmployeeLocation`) | Aux | **P3** | **OBSOLETE** | Monolithic legacy GPS check-in system; superseded by modern mobile HR apps. | Obsolete |
| 14 | **HR & Payroll ERP Module** (`tbl_hr*`, 21 tables) | Non-Core | **P3** | **OBSOLETE** | Internal payroll and leave calculations unrelated to insurance brokerage operations. | Obsolete |
| 15 | **Compiled Crystal Reports Bytecode** (`GAP-UNK-14-001`) | Exports | **P3** | **UNKNOWN** | Unreadable proprietary binary format without Crystal Designer; superseded by Jinja2 HTML/PDF. | Preserved Unknown |
| 16 | **Legacy Menu Screen Catalog** (`GAP-UNK-16-001`) | RBAC | **P3** | **UNKNOWN** | Complete legacy `tbl_menu` text dictionary omitted from offline repository. | Preserved Unknown |
| 17 | **Legacy Cheque Lockout Thresholds** (`GAP-UNK-16-002`) | Lockout | **P2** | **UNKNOWN** | Internal SQL constants inside `sp_LockChequeClearingCount`. | Preserved Unknown |

---

### 4. Implementation Phasing Strategy for Phase 16B

```
+---------------------------------------------------------------------------------------------+
|                          PHASE 16B RECOMMENDED IMPLEMENTATION STAGES                        |
+---------------------------------------------------------------------------------------------+
   |
   +---> STEP 1: DATABASE SCHEMA MIGRATION (Alembic Head Revision)
   |       - Add `tbl_loginhistory` (8 cols, indexes on UserId and CreateDate)
   |       - Add `tbl_role_privilege` (6 cols, indexes on BranchId, RoleId, ScreenId)
   |       - Add `tbl_fueltype` (4 cols, index on isdeleted)
   |       - Add `tbl_financier` (8 cols, indexes on BranchId, isdeleted)
   |       - Add `tbl_surveyor` (16 cols, indexes on LicenseNo, BranchId, isdeleted)
   |
   +---> STEP 2: REPOSITORIES & REUSABLE SERVICE LAYERS
   |       - `UserRepository` & `UserService` (User CRUD, Bcrypt hashing, branch isolation)
   |       - `LoginHistoryRepository` & `LoginHistoryService` (Event logging, IP extraction, lockout)
   |       - `PrivilegeRepository` & `PrivilegeService` (Role menu tree retrieval, assignment)
   |       - `MasterRepository` (Fuel types, financiers, surveyors)
   |       - `ProfileService` Extensions (KYC state transitions, hierarchy strings)
   |
   +---> STEP 3: REST API ROUTERS & PYDANTIC SCHEMAS
   |       - Mount `/api/v1/users` (Admin user management, password updates, status toggles)
   |       - Mount `/api/v1/auth/login-history` (Historical session audit trail)
   |       - Mount `/api/v1/admin/privileges` (Dynamic role menu presentation trees)
   |       - Mount `/api/v1/masters/fuel-types`, `/financiers`, `/surveyors`
   |       - Mount `/api/v1/admin/dashboard/counters`
   |
   +---> STEP 4: VERIFICATION & REGRESSION TESTING
   |       - Unit tests for user CRUD, password hashing, and branch isolation
   |       - Integration tests for login history recording and IP sanitization
   |       - RBAC security tests verifying non-admins cannot access admin endpoints
   |       - Full test suite regression (ensuring 399 + new tests pass 100% green)
```
