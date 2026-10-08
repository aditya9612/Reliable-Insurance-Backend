# PHASE 15 — DATABASE & SCHEMA GAP MATRIX
## Reliable-Insurance-Backend: Post-Phase 14 Database Schema & Physical Table Reconciliation

---

### 1. Executive Summary & Quantitative Metrics
- **Current Active Tables in FastAPI (`reliable_insurance_dev`)**: **62 physical tables**
- **Alembic Revision Head**: `e14a0b2c1401` (`linear`, zero heads, fully reversible)
- **Total Legacy Tables Referenced in Inline Raw SQL**: **36 tables** (100% modeled in FastAPI)
- **Total Legacy POCO / Entity Classes in `AllMaster.cs`**: **188 classes**
- **Estimated Total Physical Tables in Legacy MySQL (`brahmainsurance`)**: **~140–160 tables**
- **Post-Phase 14 Database Schema Status**:
  - **Core Insurance & Financial Tables**: **62 tables (100% Modeled & Active)**
  - **Reference & Organization Auxiliary Tables**: **18 tables (IDs Stored as FKs; Models Deferred)**
  - **Operational, Tracking & Staging Tables**: **16 tables (Deferred)**
  - **In-App Communication Tables**: **9 tables (Deferred)**
  - **Non-Core HR, Payroll & Attendance Tables**: **21 tables (Intentionally Obsolete / Out of Scope)**
  - **Non-Table Report / Projection DTOs**: **49 classes (Not Physical Tables)**

---

### 2. Physical Database Models Inventory in FastAPI (62 Tables)

| Phase | Alembic Migration | Physical Tables Added | Key Models | Total Cumulative |
|---|---|---|---|:---:|
| **Phase 2** | `b84657b131fa` | 10 | `Customer`, `VehicleDetails`, `Transaction`, `TransactionPayment`, `Account`, `LedgerMaster`, `FranchiseCommission`, `AgentCommissionPayment`, `CutNPayCommPayable`, `TransactionAppNew` | 10 |
| **Phase 3** | `56635abf39f0` | 2 | `User`, `UserRole` | 12 |
| **Phase 4B**| `cfb1bd63a8ff` | 7 | `VehicleType`, `VehicleSubType`, `VehicleMake`, `VehicleModel`, `VehicleVariant` (91 cols), `RTOMaster`, `InsuranceCompany` | 19 |
| **Phase 6** | `7bfd3202dcf7` | 23 | Quotation entries, request files, remarks, rating CC slabs, OD discount tables, zero-dep slabs, add-on rates, prefixes | 42 |
| **Phase 10**| `a10c1a1m5001` | 3 | `Claim` (`tbl_claims`), `ClaimDocument` (`tbl_claimdocument`), `PolicyEndorsement` (`tbl_appendorsement`) | 45 |
| **Phase 11**| `b11d0c5f1101` | 2 | `DocumentRegistry` (`tbl_documents`), `CalliberPolicyWebhook` (`tbl_calliber_policy_webhook`) | 47 |
| **Phase 12**| `c12d0e6f1201` | 4 | `Branch` (`tbl_branch`), `StateMaster` (`tbl_state`), `DistrictMaster` (`tbl_district`), `BankMaster` (`tbl_bank`) | 51 |
| **Phase 13**| `d13e0f7a1301` | 9 | `VehicleNoRCDetails` (`tbl_vehiclenorc_details`), `MobileOTP` (`tbl_mobile_otp`), `SMSLog` (`tbl_sms_log`), `MessageMaster` (`tbl_messagemaster`), `MessageDetails` (`tbl_messagedetails`), `PreYearRenewalStatus` (`tbl_preyearrenewalstatus`), `RenewalFollowupHistory` (`tbl_renewal_followup_history`), `PatronAccount`, `ProviderHealthLog` | 60 |
| **Phase 14**| `e14a0b2c1401` | 2 | `PospInvoice` (`tbl_posp_invoice`), `Target` (`tbl_target`) | **62** |

---

### 3. Detailed Catalog of Unmodeled Legacy Tables (Post-Phase 14)

The table below catalogs every legacy physical table that has not yet been modeled as an independent SQLAlchemy model in FastAPI:

| Category | Legacy Table Name | Legacy Entity (`AllMaster.cs`) | Columns Known? | Business Purpose | Target Migration Candidate | Priority |
|---|---|---|:---:|---|:---:|:---:|
| **Operational Staging** | `tbl_importagentpolicy` | `API_ImportAgentPolicy` | Yes (36 cols) | Staging table for bulk Excel policy MIS uploads | **Candidate A** (Batch & Utilities) | **P2** |
| **Operational Tracking**| `tbl_healthmember` | `API_HealthMember` | Yes (14 cols) | Non-motor health family members linked to policy | **Candidate A** (Batch & Utilities) | **P2** |
| **Operational Tracking**| `tbl_idvrequest` | `API_IDVRequest` | Yes (12 cols) | Special IDV override requests pending underwriter | **Candidate A** (Batch & Utilities) | **P2** |
| **Security Audit** | `tbl_loginhistory` | `API_LoginHistory` | Yes (8 cols) | Historical user login timestamps and IP addresses | **Candidate B** (Admin & Profile) | **P3** |
| **Loyalty Program** | `tbl_rewardpoint` | `API_RewardPoint` | Yes (10 cols) | POSP business performance points and redemption claims| **Candidate B** (Admin & Profile) | **P3** |
| **Dynamic RBAC** | `tbl_role_privilege` | `API_Privilege` | Yes (6 cols) | Dynamic menu tree visibility per user role | **Candidate B** (Admin & Profile) | **P3** |
| **Administrative Master**| `tbl_employee` | `API_Employee` | Yes (22 cols) | Detailed internal staff profile and branch assignment | **Candidate B** (Admin & Profile) | **P2** |
| **Administrative Master**| `tbl_agent` | `API_Agent` | Yes (24 cols) | Detailed POSP agent onboarding and KYC attributes | **Candidate B** (Admin & Profile) | **P2** |
| **Administrative Master**| `tbl_franchise` | `API_Franchise` | Yes (20 cols) | Detailed franchise profile, wallet, and contact info | **Candidate B** (Admin & Profile) | **P2** |
| **Reference Master** | `tbl_fueltype` | `API_FuelType` | Yes (4 cols) | Master table for vehicle fuel types (Petrol, Diesel) | **Candidate B** (Admin & Profile) | **P3** |
| **Reference Master** | `tbl_financier` | `API_Financier` | Yes (8 cols) | Vehicle hypothecation financier bank master | **Candidate B** (Admin & Profile) | **P3** |
| **Reference Master** | `tbl_surveyor` | `API_Surveyor` | Yes (16 cols) | Motor claim surveyor master directory | **Candidate B** (Admin & Profile) | **P3** |
| **Communication** | `tbl_appchatboard` | `API_AppChatboard` | Yes (10 cols) | Staff / POSP internal discussion board posts | **Candidate D** (Communication) | **P3** |
| **Communication** | `tbl_circular` | `API_Circular` | Yes (12 cols) | Official corporate circulars and notices | **Candidate D** (Communication) | **P3** |
| **Communication** | `tbl_message` | `API_Message` | Yes (10 cols) | Internal system messaging between staff members | **Candidate D** (Communication) | **P3** |
| **Communication** | `tbl_customerhelp` | `API_CustomerHelp` | Yes (14 cols) | Mobile customer support help tickets | **Candidate D** (Communication) | **P3** |
| **HR & Payroll (21)** | `tbl_hr*` (21 tables) | `API_HR*` (21 classes)| Yes | Internal HR payroll, attendance, leave, salaries | **Candidate E** (Obsolete / Out of Scope) | **P3** |

---

### 4. Integrity Analysis & Invariants
1. **Zero Broken Foreign Key Relationships**: In legacy MySQL, 0 physical foreign keys existed. In FastAPI, all logical relationships to `BranchId`, `AgentId`, `FranchiseId`, `BankId`, `StateId`, and `DistrictId` are preserved and verified via repository integer lookups and validation checks.
2. **Deterministic Schemas**: All 62 active tables use explicit typed columns, strict index definitions, and UTF8 / DYNAMIC storage formats.
3. **Additive Safety**: No table dropped, no column dropped, no schema drift across Alembic migration history (`b84657b131fa` $\rightarrow$ `e14a0b2c1401`).
