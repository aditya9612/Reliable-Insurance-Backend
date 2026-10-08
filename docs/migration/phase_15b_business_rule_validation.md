# PHASE 15B — BUSINESS RULE VALIDATION & COMPLIANCE
## Forensic Parity of Legacy Business Rules (LBR-058, LBR-069, Underwriting & Profiles)

---

### 1. Executive Summary
Phase 15B validates and enforces crucial legacy business rules that were previously implemented across monolithic C# code-behind files (`.aspx.cs`), database triggers, and stored procedures. This document details the forensic mapping, mathematical formulas, and operational boundaries enforced by Phase 15B.

---

### 2. Business Rule Matrix

| Rule ID | Legacy Identifier | Description | Legacy Source File | Modern Service Enforcement | Status |
|---|---|---|---|---|:---:|
| **`BR-15B-01`** | `LBR-069` | Overdue Cheque Booking User Login Lock | `Adm_LockChequeEntry.aspx.cs` | `UtilityService.enforce_overdue_cheque_locks` | **VERIFIED** |
| **`BR-15B-02`** | `LBR-058` | Non-Motor Health Insurance Multi-Member Grid | `PE_TransactionEntry.aspx.cs` | `UtilityService.create_health_member` | **VERIFIED** |
| **`BR-15B-03`** | `LBR-IDV-01` | Special IDV Underwriter Variance Review | `ViewIDVRequestDetails.aspx.cs` | `UtilityService.review_idv_request` | **VERIFIED** |
| **`BR-15B-04`** | `LBR-PRF-01` | Sequential Employee Staff Code Assignment | `mst_Employee.aspx.cs` | `ProfileService.create_employee` | **VERIFIED** |
| **`BR-15B-05`** | `LBR-PRF-02` | Sequential POSP Agent Code Assignment | `mst_Agent.aspx.cs` | `ProfileService.create_agent` | **VERIFIED** |
| **`BR-15B-06`** | `LBR-PRF-03` | Sequential Franchise Partner Code Assignment | `mst_Franchaise.aspx.cs` | `ProfileService.create_franchise` | **VERIFIED** |
| **`BR-15B-07`** | `LBR-MIS-01` | Bulk MIS Numeric Normalization & Staging Isolation | `adm_ImportTransAgentPolicyMIS.aspx.cs` | `UtilityService.parse_and_stage_policy_mis` | **VERIFIED** |
| **`BR-15B-08`** | `LBR-CRM-01` | Partner Birthday Wish Template Rendering | `SendPushNotiForBdayWish.aspx.cs` | `UtilityService.dispatch_birthday_greetings` | **VERIFIED** |

---

### 3. Detailed Rule Verification

#### 3.1 `LBR-069`: Overdue Cheque Login Lock
- **Legacy Formulation**:
  When a policy is issued with `PaymentType = 'CHEQUE'`, the cheque payment must be cleared (`isclearance = '1'`) or approved by cashier (`CashierApproval = '1'`) within 15 days. If uncleared after 15 days, the user login that created the booking must be automatically suspended (`isactive = 0`).
- **Mathematical / Logical Condition**:
  $$\text{TargetCheques} = \{ p \in \text{tbl\_transactionpayment} \mid p.\text{paymenttype} = \text{'CHEQUE'} \land p.\text{CashierApproval} \neq \text{'1'} \land p.\text{isclearance} \neq \text{'1'} \land p.\text{EntryDate} \le (\text{Now} - 15\,\text{days}) \}$$
  $$\forall p \in \text{TargetCheques}, \quad \text{UserLogin}(p.\text{UserId}).\text{isactive} \leftarrow 0$$
- **Modern Verification**:
  Verified in `tests/unit/test_phase15b_utilities_calculations.py` and `tests/integration/test_phase15b_profiles_and_utilities_api.py`. Uncleared cheques trigger exact login deactivation.

#### 3.2 `LBR-058`: Health Multi-Member Family Grid
- **Legacy Formulation**:
  In health and mediclaim policies, individual family members are insured under a master policy transaction. Each member record in `tbl_healthmember` requires relation identification, age calculation, sum insured allocation, and pre-existing disease tracking.
- **Allowed Relations**:
  `SELF`, `SPOUSE`, `SON`, `DAUGHTER`, `FATHER`, `MOTHER`, `OTHER`.
- **Validation**:
  Member cannot have negative age or Sum Insured $\le 0$. Sum Insured is validated against policy plan limits.

#### 3.3 `LBR-IDV-01`: Underwriter IDV Override Review
- **Legacy Formulation**:
  Vehicular Insured Declared Value (IDV) is typically bounded within standard insurer depreciation guidelines ($\pm 15\%$). When a client or agent requests an IDV outside standard bounds, an IDV request ticket is logged into `tbl_idvrequest`.
- **Variance Formula**:
  $$\text{IDV Variance} = \left( \frac{\text{RequestedIDV} - \text{StandardIDV}}{\text{StandardIDV}} \right) \times 100$$
- **Review Transition**:
  - `PENDING` $\rightarrow$ `APPROVED`: Sets `ApprovedIDV`, records `UnderwriterRemarks`, and stamps approval timestamp.
  - `PENDING` $\rightarrow$ `REJECTED`: Records rejection reason in `UnderwriterRemarks`.

#### 3.4 `LBR-PRF-01/02/03`: Partner & Staff Code Generation
- **Legacy Pattern**:
  Staff, agent, and franchise codes follow a deterministic monthly sequence format:
  - Employee: `EMP{YYYYMM}{Sequence:04d}` (e.g., `EMP2026100001`)
  - Agent: `AGT{YYYYMM}{Sequence:04d}` (e.g., `AGT2026100001`)
  - Franchise: `FRN{YYYYMM}{Sequence:04d}` (e.g., `FRN2026100001`)
- **Modern Implementation**:
  Implemented in `ProfileService._generate_next_code` using atomic count queries within transaction context.

#### 3.5 `LBR-MIS-01`: Bulk MIS Data Ingestion
- **Cleaning & Isolation**:
  - Removes non-numeric artifacts: currency signs (`₹`, `$`), comma thousands separators, percentages.
  - Validates decimal casting.
  - Inserts into isolated staging table `tbl_importagentpolicy` with `IsProcess = '0'`, guaranteeing zero mutation of active transaction ledger `tbl_transaction` until explicitly reconciled.
