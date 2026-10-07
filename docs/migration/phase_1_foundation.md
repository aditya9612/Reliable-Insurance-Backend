# Phase 1: FastAPI Foundation Report
## Reliable Assurance Backend Migration
**Target Repository**: `Reliable-Insurance-Backend`  
**Phase**: Phase 1 — FastAPI Foundation  
**Status**: COMPLETE (STOP CONDITION REACHED — AWAITING REVIEW & APPROVAL)

---

## 1. Architectural Overview & Environment Separation Rule

In strict adherence to the **Conditional Approval Instructions**, the new `Reliable-Insurance-Backend` project is built as a completely independent, modern FastAPI backend.

### Strict Environment Separation:
- **Legacy Production Database (`brahmainsurance`)**:
  - Role: **REFERENCE / AUDIT ONLY**.
  - Access Mode: Never accessed at runtime; never targeted by Alembic migrations; no tables, records, or procedures modified.
- **New FastAPI Runtime Database (`reliable_insurance_dev`)**:
  - Role: **LOCAL DEVELOPMENT DATABASE**.
  - Host: `localhost:3306` (Local MySQL 8.0 instance).
  - Credentials and URL managed purely via `.env` (git-ignored) with placeholders in `.env.example`.
  - Built-in Safety Guard: `app/core/config.py` contains an active validator that crashes application startup if `brahmainsurance` or production remote IPs are detected in `DATABASE_URL`.

---

## 2. Phase 0 Findings Preserved

The critical findings from Phase 0 have been recorded and preserved as non-negotiable architectural constraints for subsequent phases:
1. **Transaction Entity**: `tbl_transaction` contains 166 columns with physical PK `TransanctionId`. Physical columns `ODPermium`, `TPPermium`, `NetPermium`, and `TStatus` must be mapped without renaming.
2. **Vehicle Entity**: `tbl_custvehicle` does not exist; vehicle data is stored in `tbl_vehicledetails` (213,334 records) with `RegistrationNo` and `ChaiseNo`.
3. **Foreign Keys**: 0 foreign key constraints exist in the production MySQL schema. All relational integrity must be enforced at the application level.
4. **Commission Architecture**: `tbl_commission` has 0 rows. Real active commission records exist in `tbl_franchisecommission` (198k rows), `tbl_agentcommissionpayment` (98k rows), and `tbl_cutnpaycommpayable` (75k rows).
5. **Two-Stage Proposal-to-Policy Lifecycle**: Proposals are staged in `tbl_transactionappnew` before clerk approval writes the issued policy to `tbl_transaction`.
6. **Stored Procedure Inventory**: 1,855 unique procedure calls in C# vs 1,980 procedures in MySQL. The 90 missing procedures remain classified as `UNKNOWN / REQUIRES PRODUCTION VERIFICATION`.
7. **Inward Number Monotonicity**: `sp_generateInwardNo` reads `AUTO_INCREMENT` without locking, causing concurrency race conditions that must be replaced with atomic sequence locking in future phases.
8. **Password Migration**: Passwords must be transparently upgraded to bcrypt on login without modifying production users during Phase 1. Passwords must never be returned in API responses or logs.

---

## 3. Implementation Details

### 3.1 Application Foundation (`app/main.py`)
- Created application factory with lifespan management.
- Registered CORS middleware (`CORS_ORIGINS`), structured logging middleware, and request ID correlation middleware.
- Registered centralized exception handlers.
- Mounted `/api/v1` routes and root status endpoint.

### 3.2 Configuration (`app/core/config.py`)
- Built with Pydantic `BaseSettings` (`SettingsConfigDict(env_file=".env")`).
- Reads `DATABASE_URL`, `REDIS_URL`, `JWT_SECRET_KEY`, `APP_ENV`, `CORS_ORIGINS`.
- **Enforced Safety Check**: Active `@field_validator("DATABASE_URL")` rejects any URL containing `brahmainsurance`, `103.149.199.250`, `103.7.181.105`, or `103.104.73.198`.

### 3.3 Async Database Layer (`app/db/session.py`, `app/db/base.py`)
- Async SQLAlchemy 2.x engine using `aiomysql`.
- Connection pooling with `pool_size=10`, `max_overflow=5`, `pool_recycle=3600`, and `pool_pre_ping=True`.
- In `APP_ENV=testing`, automatically switches to `NullPool` to prevent event-loop cross-contamination across async test functions on Windows.
- Dependency `get_db()` yielding `AsyncSession` with automatic rollback on unhandled error and guaranteed closure.
- Database health check function `check_db_connection()` executing `SELECT DATABASE(), 1`.
- Declarative Base `app/db/base.py` ready for future model definitions.

### 3.4 Redis Connection Layer (`app/core/redis.py`)
- Async Redis client pool using `redis.asyncio`.
- Initialized in FastAPI lifespan, cleanly disposed on shutdown.
- Safe health check function `check_redis_connection()` returning structured status without crashing when Redis is unavailable.

### 3.5 Security Abstraction (`app/core/security.py`)
- `verify_password(plain, hashed_or_plain) -> Tuple[bool, bool]`: Validates both bcrypt hashes and legacy plaintext via constant-time comparison (`hmac.compare_digest`), returning `(is_valid, needs_upgrade)`.
- `get_password_hash(password) -> str`: Bcrypt hashing with 12 rounds.
- `create_access_token(data, expires_delta) -> str`: Cryptographically signed JWT token (`HS256`). Automatically strips password keys from payload.
- `decode_access_token(token) -> dict`: Validates signature and expiration, raising standardized 401 errors.
- `get_current_token_payload(token)`: Reusable OAuth2 Bearer token dependency.

### 3.6 Middleware & Centralized Exception Handling (`app/middleware/`)
- `RequestIdMiddleware`: Generates or preserves `X-Request-ID` across request and response headers, binding it to async context.
- `StructuredLoggingMiddleware`: Structured access logging with latency, method, path, client IP, and request ID. Masks credentials.
- `register_exception_handlers`:
  - `StarletteHTTPException` $\rightarrow$ Standardized JSON error response.
  - `RequestValidationError` $\rightarrow$ Standardized 422 JSON response with field locations.
  - `SQLAlchemyError` $\rightarrow$ Standardized 500 JSON response; **zero SQL statements, table names, or connection strings leaked**.
  - `Exception` $\rightarrow$ Standardized 500 JSON response; **zero stack traces or internal filenames leaked**.

### 3.7 Health & Readiness Endpoints (`app/api/v1/endpoints/health.py`)
- `GET /api/v1/health`: Liveness probe (200 OK, no auth).
- `GET /api/v1/ready`: Readiness probe verifying local MySQL (`reliable_insurance_dev`) and Redis. Guarantees zero connection to production database.

---

## 4. Test Verification Summary

Automated test suite executed via `pytest`:
- **Total Tests**: 20
- **Passed**: 20
- **Failed**: 0
- **Skipped**: 0

### Test Inventory:
1. `tests/integration/test_db.py::test_local_db_connectivity`: PASS
2. `tests/integration/test_db.py::test_get_db_session_lifecycle`: PASS
3. `tests/integration/test_db.py::test_redis_connection_safe_check`: PASS
4. `tests/integration/test_health.py::test_root_endpoint`: PASS
5. `tests/integration/test_health.py::test_health_liveness_endpoint`: PASS
6. `tests/integration/test_health.py::test_readiness_endpoint_structure_and_safety`: PASS
7. `tests/unit/test_config.py::test_settings_default_values`: PASS
8. `tests/unit/test_config.py::test_safety_check_prevents_production_database`: PASS
9. `tests/unit/test_config.py::test_cors_origins_parsing`: PASS
10. `tests/unit/test_middleware.py::test_request_id_generated_automatically`: PASS
11. `tests/unit/test_middleware.py::test_request_id_preserved_when_supplied`: PASS
12. `tests/unit/test_middleware.py::test_404_error_standardized_json`: PASS
13. `tests/unit/test_middleware.py::test_database_error_does_not_leak_sql_or_secrets`: PASS
14. `tests/unit/test_middleware.py::test_unhandled_error_does_not_leak_stack_traces`: PASS
15. `tests/unit/test_security.py::test_bcrypt_hashing_and_verification`: PASS
16. `tests/unit/test_security.py::test_legacy_plaintext_password_verification`: PASS
17. `tests/unit/test_security.py::test_empty_password_handling`: PASS
18. `tests/unit/test_security.py::test_jwt_creation_and_decoding`: PASS
19. `tests/unit/test_security.py::test_jwt_strips_sensitive_password_keys`: PASS
20. `tests/unit/test_security.py::test_expired_jwt_raises_401`: PASS

---

## 5. Safety Verification Checklist

| Safety Check | Verified Result | Evidence / Details |
|---|---|---|
| Application does NOT contain hardcoded production DB credentials | **VERIFIED** | All configurations read from environment variables; zero production secrets in code. |
| `.env` is ignored by Git | **VERIFIED** | Confirmed present in `.gitignore`; `git status` verifies `.env` is untracked. |
| `.env.example` contains placeholders only | **VERIFIED** | Points to `reliable_insurance_dev` with dummy placeholders. |
| Runtime database configuration points to local dev database | **VERIFIED** | Points strictly to `reliable_insurance_dev` on `localhost:3306`. |
| No Alembic migration was executed | **VERIFIED** | Zero migrations executed; no migration versions created. |
| No legacy production table was modified | **VERIFIED** | Legacy database was untouched. |
| No legacy production record was modified | **VERIFIED** | Zero write/update/delete operations executed against production. |
| No stored procedure was modified | **VERIFIED** | Zero DDL operations executed against production routines. |
| No business module was implemented | **VERIFIED** | Customers, Vehicles, Policies, Payments, Commissions, Ledgers NOT implemented. |
| No production secret was committed | **VERIFIED** | Clean git working tree; secrets excluded. |

---

## 6. Stop Condition & Next Phase

> [!IMPORTANT]
> **PHASE 1 STOP CONDITION REACHED**:
> - The FastAPI foundation layer is complete and fully tested with 20 passing unit/integration tests.
> - The independent local database (`reliable_insurance_dev`) is verified.
> - The security, middleware, configuration, database session, and health layers are operational.
> - In accordance with instructions, execution is stopped. No domain models, Alembic migrations, or business modules will be started until Phase 1 is reviewed and approved.

### Planned for Phase 2 (Pending Approval):
- Detailed SQLAlchemy declarative mapping for core verified tables (`tbl_transaction` with exact 166 physical columns, `tbl_vehicledetails`, `tbl_customer`, `tbl_account`, `tbl_ledgermaster`, `tbl_franchisecommission`, `tbl_agentcommissionpayment`, `tbl_cutnpaycommpayable`).
- Asynchronous repository pattern abstractions for database access.
