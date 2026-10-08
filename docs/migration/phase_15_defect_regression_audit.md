# PHASE 15 — DEFECT REGRESSION AUDIT
## Reliable-Insurance-Backend: Post-Phase 14 Legacy Known Defects Reconciliation

---

### 1. Executive Summary & Defect Metrics
- **Total Cataloged Legacy Defects**: **11 Defects (`DEF-001` through `DEF-011`)** (from `18_legacy_known_defects.md`)
- **Current Status After Phase 14**:
  - **FIXED & MITIGATED**: **11 / 11 (100.0%)**
  - **REGRESSION INCIDENTS**: **0**
  - **OPEN DEFECTS**: **0**
- **Cross-Phase Defect Safeguards**:
  - `GAP-P10-001` (claim settlement accounting separation): Strictly verified preserved.
  - Concurrency race conditions: Mitigated via database unique constraints and row-level locking.

---

### 2. Defect Status & Mitigation Verification Matrix

| Defect ID | Severity | Legacy Defect Description & File | FastAPI Mitigation Mechanism | Regression Test Evidence | Status |
|---|:---:|---|---|---|:---:|
| **`DEF-001`** | **P0** | Unauthenticated `Service.asmx` and `VehicleService.asmx` allowing public data access | OAuth2 JWT Bearer tokens + 56-role `CurrentUser` RBAC dependency enforced on all protected endpoints | `tests/integration/test_phase3_auth.py`, `tests/integration/test_phase14_reports_api.py` | **MITIGATED** |
| **`DEF-002`** | **P0** | Hardcoded production DB passwords, SMS keys, and Signzy credentials in `Web.config` | Pydantic v2 `Settings` with strict `_enforce_dev_db_isolation` blocking connection to `brahmainsurance` | `tests/unit/test_config_isolation.py`, `tests/integration/test_phase13_integrations.py` | **MITIGATED** |
| **`DEF-003`** | **P0** | SQL Injection across 124 inline SQL queries in C# code-behind and search handlers | 100% parameterized SQLAlchemy 2.0 ORM queries; zero dynamic raw SQL string interpolation | `tests/integration/test_phase12_search.py`, `tests/unit/test_phase14_reporting_calculations.py`| **MITIGATED** |
| **`DEF-004`** | **P0** | Client-side RBAC & IDOR vulnerability via tampered query parameters (`?agent_id=999`) | Server-side principal scoping overriding untrusted query parameters from JWT claims | `tests/integration/test_phase5g_authorization.py`, `tests/integration/test_phase14_reports_api.py` | **MITIGATED** |
| **`DEF-005`** | **P0** | Plaintext user passwords stored in `tbl_user.Password` | Passlib bcrypt password hashing with transparent, automatic legacy hash upgrade on login | `tests/unit/test_auth_passwords.py`, `tests/integration/test_phase3_auth.py` | **MITIGATED** |
| **`DEF-006`** | **P1** | Unauthenticated `PolicyParserWebhook.aspx` allowing arbitrary policy insertion | HMAC-SHA256 signature verification (`X-Calliber-Signature`) with structured staging | `tests/integration/test_phase11_webhook.py` | **MITIGATED** |
| **`DEF-007`** | **P1** | Path traversal in `DownloadAll.ashx` and `ImageHandler.ashx` via arbitrary query parameters | Canonical `StorageKey` validation, `Path.resolve().relative_to(root)` containment, RBAC guards | `tests/integration/test_phase11_storage.py` | **MITIGATED** |
| **`DEF-008`** | **P1** | Non-atomic multi-step financial mutations opening separate DB connections per SP | Single async SQLAlchemy session transaction boundary (`async with db.begin()`) with auto-rollback | `tests/integration/test_phase7_policy_booking.py`, `tests/integration/test_phase14_e2e.py` | **MITIGATED** |
| **`DEF-009`** | **P1** | Floating-point (`double`/`float`) rounding and precision errors in premium, GST, and TDS | Strict `Decimal` arithmetic (`ROUND_HALF_UP` to 2 decimal places) across rating, finance, and invoicing | `tests/unit/test_phase6_rating.py`, `tests/unit/test_phase14_reporting_calculations.py` | **MITIGATED** |
| **`DEF-010`** | **P1** | Copy-paste bug in `Service.asmx.cs` `UpdateClaimDocument` deleting `ClaimPhoto` on final bill update | Distinct canonical `StorageKey` per `DocumentSlot` preventing cross-slot file deletion | `tests/integration/test_phase11_documents.py` (`test_def010_remediation`) | **MITIGATED** |
| **`DEF-011`** | **P2** | Swallowed exceptions returning HTTP 200 or `"0"` on fatal database failures | Centralized structured FastAPI exception handlers returning deterministic HTTP status codes | `tests/integration/test_phase1_exceptions.py`, `tests/integration/test_phase14_reports_api.py` | **MITIGATED** |

---

### 3. Cross-Phase Defect Regression Verifications
1. **`GAP-P10-001` (Claims Accounting Invariant)**: Verified that Phase 14 reporting queries `tbl_claims` in a strictly read-only manner. Zero journal vouchers or ledger postings (`AccTransId 15/16/18`) are created during report queries or dashboard aggregations.
2. **Duplicate Invoicing Race Condition**: Concurrency test verified that database-level unique constraint on `tbl_posp_invoice.InvoiceNo` rejects concurrent duplicate creation attempts with `HTTP 409 Conflict`.
3. **Zero Regressions in Regression Suite**: All 382 automated test cases pass with zero failures and zero errors.
