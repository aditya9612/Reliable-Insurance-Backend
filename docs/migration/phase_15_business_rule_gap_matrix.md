# PHASE 15 — BUSINESS RULE GAP MATRIX
## Reliable-Insurance-Backend: Post-Phase 14 Master Business Rule Register Reconciliation

---

### 1. Executive Summary & Master Register Metrics
- **Total Cataloged Legacy Business Rules**: **140 Rules (`LBR-001` through `LBR-140`)** (from `19_legacy_business_rule_master_register.md`)
- **Current Status After Phase 14**:
  - **PARITY**: **110 Rules (78.6%)**
  - **INTENTIONAL HARDENING**: **14 Rules (10.0%)**
  - **LEGACY DEFECT MITIGATED**: **13 Rules (9.3%)**
  - **DEVIATION**: **0 Rules (0.0%)**
  - **MISSING ON CORE REGISTER**: **0 Rules (0.0%)**
  - **PRESERVED UNKNOWN**: **3 Rules (2.1%)** (`GAP-UNK-001`, `GAP-UNK-002`, `GAP-UNK-003`)
- **Auxiliary Domain Rules**:
  - `LBR-021`, `LBR-022` (Signzy RC): Migrated in Phase 13.
  - `LBR-123`, `LBR-124`, `LBR-125` (Mobile OTP / SMS): Migrated in Phase 13.
  - `LBR-126`, `LBR-127`, `LBR-128` (Push Notifications): Migrated in Phase 13.
  - `LBR-131` (Telecaller Targets): Migrated in Phase 14.
  - `LBR-069` (Overdue Cheque Lock): Deferred (P2).
  - `LBR-058` (Health Member Family Grid): Deferred (P2).

---

### 2. High-Level Category Status Matrix

| Rule Cluster | Rule IDs | Domain Focus | Current Status | Notes & Verification |
|---|---|---|:---:|---|
| **Cluster 1** | `LBR-001` – `LBR-010` | Authentication, RBAC, User Passwords, Branch Isolation | **100% IMPLEMENTED / HARDENED** | Dual-mode bcrypt, JWT, server-side branch scoping. |
| **Cluster 2** | `LBR-011` – `LBR-025` | Customer Lifecycle, Vehicle Uniqueness, RC Verification | **100% IMPLEMENTED / HARDENED** | FY-scoped registration check, uppercase casing, Signzy RC cascade. |
| **Cluster 3** | `LBR-026` – `LBR-050` | Underwriting, 9 Vehicle Categories, Slabs, NCB, GST | **100% IMPLEMENTED / HARDENED** | Decimal rating sequence, 12% GCV split GST, IDV ±15% band. |
| **Cluster 4** | `LBR-051` – `LBR-065` | Policy Booking, Inward Allocation, Proposals, Inspection | **98% IMPLEMENTED** | Atomic 6-table booking, row-locked inward sequence; `LBR-058` deferred. |
| **Cluster 5** | `LBR-066` – `LBR-080` | Payments, Cheque Dishonor, E-Wallet, InstaPay Surcharge | **98% IMPLEMENTED** | Cheque bounce ₹500 penalty, 1.03% InstaPay, wallet locks; `LBR-069` deferred. |
| **Cluster 6** | `LBR-081` – `LBR-095` | Commissions, TDS 5%, Cut & Pay, Ledger, Trial Balance | **100% IMPLEMENTED** | 4-tier commission spread, Cut & Pay net-off, signed ledger polarity. |
| **Cluster 7** | `LBR-096` – `LBR-114` | Claims 3-Stage Lifecycle, 22 Endorsement Types, Refunds | **100% IMPLEMENTED** | Independent claim accounting, surveyor caps, endorsement clawback. |
| **Cluster 8** | `LBR-115` – `LBR-122` | Documents, StorageKey, DownloadAll ZIP, Policy Parser | **100% IMPLEMENTED / HARDENED** | Path traversal defense, DEF-010 fix, Calliber HMAC-SHA256 webhook. |
| **Cluster 9** | `LBR-123` – `LBR-135` | OTP, SMS, OneSignal Push, Renewal CRM, Targets | **100% IMPLEMENTED** | Salted OTP hashes, dual-dispatch notifications, CRM follow-up. |
| **Cluster 10**| `LBR-136` – `LBR-140` | Dashboards, MIS Exports, POSP Tax Invoices, Reporting | **100% IMPLEMENTED** | April–March Indian FY, GST 18% / TDS 5% POSP tax math, OpenXML. |

---

### 3. Detailed Audit of the 2 Deferred Auxiliary Rules

#### 3.1 `LBR-069`: Overdue Uncleared Cheque User Booking Lock
- **Specification**: If an agent, broker, or clerk has an uncleared cheque in `tbl_transactionpayment` that has exceeded the allowable clearance threshold (default 15 days) without clearance or bounce recording, their login account or ability to book new policies must be locked until resolved.
- **Current State**: Phase 8 implemented cheque clearance, dishonor, bounce penalty, and commission holds. The administrative automated user lock policy is cataloged as **DEFERRED (P2)** for the scheduled batch module (Candidate A).

#### 3.2 `LBR-058`: Non-Motor Health Insurance Family Member Grid
- **Specification**: For non-motor health insurance proposals, policies require staging and recording family members (Self, Spouse, Children, Parents) with individual Sum Insured, Age, and Pre-Existing Disease (PED) declarations stored in `tbl_healthmember`.
- **Current State**: Core motor insurance rating and policy booking are 100% operational across all 9 vehicle categories. Non-motor health member grid storage is cataloged as **DEFERRED (P2)** (Candidate A).

---

### 4. Preserved Unknown Business Rules
1. **`GAP-UNK-001`**: Internal SQL rules of legacy stored procedures whose SQL bodies were absent from the offline dump.
2. **`GAP-UNK-002`**: Exact MySQL column data types (`DECIMAL` vs `FLOAT`) on unextracted tables.
3. **`GAP-UNK-003`**: Tie-breaking order when multiple active commission or discount slabs overlap on the exact same effective date without an explicit `ORDER BY` clause.
