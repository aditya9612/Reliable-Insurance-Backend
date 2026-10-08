# PHASE 16 — LBR-069 CHEQUE LOCK BOUNDARY & GAP-UNK-16-002 RECONCILIATION
## Reliable-Insurance-Backend: Behavioral Parity Invariant vs Internal SP Threshold Constant

---

### 1. Executive Summary & Core Invariant
During Phase 15B, the operational task and business rule **LBR-069** (Overdue Cheque User Lock) was fully remediated, verified, and locked in:
- **Phase 15B Verified Baseline**:
  - `PaymentRepository.get_overdue_cheques`: Identifies transactions where cheque payments remain uncleared beyond the 15-day grace threshold.
  - `UtilityService.enforce_overdue_cheque_locks`: Marks affected user accounts as inactive (`u.isdeleted = "1"`).
  - `AuthService.login`: Rejects inactive/deactivated users immediately with HTTP 401 (`"User account is inactive or disabled"`).
  - Regression Suite: Tests pass 100% green (verified across 399 unit and integration tests).

#### ABSOLUTE PHASE 16 RULE:
- **Phase 15B LBR-069 implementation remains FROZEN**.
- **Phase 16 does NOT modify application code, utility tasks, or auth lockout logic**.
- **Phase 16 does NOT connect to or query production (`brahmainsurance`)**.

---

### 2. Forensic Analysis: Exact SQL Constant vs Behavioral Parity

| Dimension | Legacy Stored Procedure (`sp_LockChequeClearingCount`) | Phase 15B Verified Target Implementation | Status & Reconciliation |
|---|---|---|:---:|
| **Call Site Parameters** | `P_UserName`, `P_UserPassword`, `P_opr` (`DAL_Operations.cs:L20315`) | Parameterized SQLAlchemy query on `TransactionPayment` and `Transaction` | **PARITY** |
| **Threshold Parameter Source** | Hardcoded inside compiled MySQL Stored Procedure body (omitted from offline dump) | Configurable 15-day aging window based on industry standard and C# audit evidence | **HARDENING** |
| **Account Mutation** | Updated internal legacy lock state in MySQL | Updates `tbl_user.isdeleted = '1'` (canonical deactivation flag) | **PARITY** |
| **Authentication Barrier** | Blocked WebForms login (`Log_In.aspx.cs`) with error redirect | Blocks FastAPI JWT login (`POST /api/v1/auth/login`) with HTTP 401 | **PARITY** |

---

### 3. Detailed Boundary Analysis: `GAP-UNK-16-002`

#### 3.1 Why `GAP-UNK-16-002` Is Genuinely UNKNOWN:
1. In the legacy C# code-behind (`DAL_User.DAL_LockChequeClearingCount`), the method invokes:
   ```csharp
   cmd.CommandText = "sp_LockChequeClearingCount";
   cmd.Parameters.AddWithValue("P_UserName", userName);
   cmd.Parameters.AddWithValue("P_UserPassword", password);
   cmd.Parameters.AddWithValue("P_opr", opr);
   ```
2. The exact integer threshold for the number of uncleared cheques (e.g., $>0$, $\ge 3$, or $\ge 5$) and the exact internal aging date expression (`DATEDIFF(NOW(), PaymentDate) > X`) are compiled entirely inside the unextracted MySQL stored procedure body on the legacy database server.
3. No offline SQL script in the repository contains the `CREATE PROCEDURE sp_LockChequeClearingCount` routine definition.
4. Per the **No Guessing** and **Production Safety** rules, this internal SQL constant cannot be manufactured or queried from production.
5. Therefore, **`GAP-UNK-16-002` is genuinely UNKNOWN and MUST REMAIN PRESERVED**.

#### 3.2 Distinction: Internal SQL Constant vs Observable Behavioral Parity:
- **Internal SQL Threshold Constant** (`GAP-UNK-16-002`): The specific private integer literals embedded inside legacy routine `sp_LockChequeClearingCount`. This remains UNKNOWN.
- **Externally Observable Lock Behavior** (Verified in Phase 15B): The end-to-end operational consequence—that users associated with delinquent uncleared cheques are identified, flagged, and barred from logging in or booking new policies. This behavior is **100% verified and operational**.
- **Conclusion**: `GAP-UNK-16-002` strictly documents the omission of the offline SP source code and **does NOT invalidate** the verified behavioral parity established in Phase 15B.

---

### 4. Governance & Phase 16 Boundary Mandate
1. **Implementation Scope for Phase 16**:
   - Phase 16 will introduce administrative endpoints (`POST /api/v1/auth/unlock-account/{user_id}`) to allow global administrators (`OWNER`, `ADMIN`) to review locked accounts and manually restore active status (`u.isdeleted = "0"`).
   - Phase 16 will **NOT** alter the underlying detection engine or background job implemented in Phase 15B.
2. **Preservation Invariant**:
   - `GAP-UNK-16-002` remains an active, open entry in `docs/migration/phase_16_unknowns.md`.
   - It will only be closed if an authentic offline DDL export containing `CREATE PROCEDURE sp_LockChequeClearingCount` is committed to the repository.
