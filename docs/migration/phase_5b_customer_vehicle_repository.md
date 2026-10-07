# Phase 5B — Customer & Vehicle Schema Parity + Repository Foundation Report

**Target Repository**: `Reliable-Insurance-Backend`  
**Phase**: 5B — Customer & Vehicle Schema Parity + Repository Foundation  
**Execution Environment**: LOCAL DEVELOPMENT ONLY (`localhost:3306/reliable_insurance_dev`)  
**Status**: COMPLETE — STRICT STOP CONDITION ENFORCED  

---

## 1. Executive Summary

Phase 5B has established complete schema parity and foundational async data-access repositories for the core customer and vehicle domain models (`tbl_customer` and `tbl_vehicledetails`), based directly on empirical findings from the Phase 5A audit (`docs/migration/phase_5a_customer_vehicle_audit.md`).

Key achievements:
1. **Schema & Index Parity**:
   - Updated `Customer` model `__table_args__` in `app/models/customer.py` to specify the 3 secondary indexes verified in production: `CustomerCode_UNIQUE` (prefix length 100), `Fk5_ClientId_idx`, and `Fk18_BranchId_idx`.
   - Verified `VehicleDetails` model in `app/models/vehicle.py` maintains exact 32/32 column parity, zero secondary indexes, `FinancialYear` NOT NULL constraint, and preserved legacy typo `ChaiseNo`.
   - Preserved **0 physical foreign keys** in both models, maintaining full compatibility with the legacy MySQL database.
2. **Alembic Additive Migration**:
   - Generated and applied revision `6502a09489d3` (`add_customer_indexes`) with down-revision `cfb1bd63a8ff`.
   - Verified clean upgrade and downgrade against local `reliable_insurance_dev`.
   - Verified physical index definitions in MySQL via `SHOW INDEX FROM tbl_customer`.
3. **Repository Architecture**:
   - `CustomerRepository`: Implemented `get_by_id`, `get_by_code`, `search_by_name`, `list_by_branch`, `get_by_mobile`, and `get_by_pan`.
     - Preserved empirical domain rule: `get_by_mobile` returns `Sequence[Customer]` because `MoblieNo1` is NOT unique (multiple customers share phone numbers).
     - Implemented legacy branch scoping (`branch_id = 0` HQ mode vs. `branch_id > 0` branch-isolated mode).
   - `VehicleRepository`: Implemented `get_by_id`, `list_by_customer_id`, `search_by_registration`, `search_by_chassis`, and `check_registration_in_fy`.
     - Preserved empirical domain rule: `search_by_registration` and `search_by_chassis` return `Sequence[VehicleDetails]` because `RegistrationNo` and `ChaiseNo` are NOT globally unique.
     - Preserved backward compatibility for all prior tests.
4. **Test Verification**:
   - Added 9 unit tests in `tests/unit/test_customer_vehicle_models.py`.
   - Added 8 integration tests in `tests/integration/test_customer_vehicle_repositories.py`.
   - All **85 automated tests** in the repository pass cleanly (100% pass rate, 0 regressions).

---

## 2. Environment & Database Isolation Audit

In strict compliance with architectural safety requirements:
- **Zero remote connections**: No network connections or queries were made to legacy production (`103.149.199.250:3309` / `brahmainsurance`).
- **Target database**: All migrations, schema changes, and integration tests ran exclusively against local MySQL `localhost:3306/reliable_insurance_dev`.
- **Isolation check**: Automated integration test `test_customer_vehicle_db_isolation_safety` asserts that `DATABASE()` is `reliable_insurance_dev` and verifies the absence of production hostnames or credentials.

---

## 3. Physical Schema & Index Parity

### 3.1 `tbl_customer` Index Specification

| Index Name | Indexed Column | Unique | MySQL Options | Purpose / Legacy Origin |
|---|---|---|---|---|
| `PRIMARY` | `CustomerId` | YES | None | Primary Key (`AUTO_INCREMENT`) |
| `CustomerCode_UNIQUE` | `CustomerCode` | YES | Sub-part: 100 | Client business code uniqueness (`UNIQUE KEY CustomerCode_UNIQUE (CustomerCode(100))`) |
| `Fk5_ClientId_idx` | `ClientId` | NO | None | Optimization index for corporate client linkage (`tbl_corporateclient`) |
| `Fk18_BranchId_idx` | `BranchId` | NO | None | Optimization index for branch-level data scoping (`tbl_branch`) |

Physical index verification from `reliable_insurance_dev`:
```text
Table: tbl_customer
- PRIMARY: CustomerId (Non_unique: 0)
- CustomerCode_UNIQUE: CustomerCode (Non_unique: 0, Sub_part: 100)
- Fk18_BranchId_idx: BranchId (Non_unique: 1, Sub_part: None)
- Fk5_ClientId_idx: ClientId (Non_unique: 1, Sub_part: None)
```

### 3.2 `tbl_vehicledetails` Specification

- Total columns: 32 (exact match).
- Primary key: `CustVehId` (`int(11) AUTO_INCREMENT`).
- Secondary indexes: **0** (matches production schema where only PK index exists).
- Nullability: `FinancialYear` is **NOT NULL** (`nullable=False`).
- Preserved legacy spelling quirks: `ChaiseNo` (not `ChassisNo`), `CustVehId` (not `VehicleId`).

### 3.3 Relational Integrity Contract
- Both models have **0 physical foreign keys**. Relational integrity is enforced at the application/repository layer.

---

## 4. Alembic Migration Details

- **Migration File**: `alembic/versions/6502a09489d3_add_customer_indexes.py`
- **Revision ID**: `6502a09489d3`
- **Down Revision**: `cfb1bd63a8ff`
- **Actions**:
  - `op.create_index('CustomerCode_UNIQUE', 'tbl_customer', ['CustomerCode'], unique=True, mysql_length=100)`
  - `op.create_index('Fk18_BranchId_idx', 'tbl_customer', ['BranchId'], unique=False)`
  - `op.create_index('Fk5_ClientId_idx', 'tbl_customer', ['ClientId'], unique=False)`
- **Downgrade verification**: `alembic downgrade -1` dropped all 3 indexes cleanly; `alembic upgrade head` re-applied them successfully.

---

## 5. Repository Implementations

### 5.1 `CustomerRepository` (`app/repositories/customer.py`)

| Method Signature | Return Type | Description & Domain Rules |
|---|---|---|
| `get_by_id(customer_id: int)` | `Optional[Customer]` | Primary key lookup (via `BaseRepository`). |
| `get_by_code(customer_code: str)` | `Optional[Customer]` | Lookup by unique `CustomerCode`. Returns single instance. |
| `search_by_name(search_text: str, branch_id: int = 0, offset: int = 0, limit: int = 50)` | `Sequence[Customer]` | Full/partial name substring search across `CustFName`, `CustMName`, `CustLName`. If `branch_id > 0`, scoped to branch; if `0`, searches all branches. Excludes soft-deleted records (`isdeleted == '1'`). |
| `list_by_branch(branch_id: int, offset: int = 0, limit: int = 50)` | `Sequence[Customer]` | Paginated listing of customers belonging to a branch. |
| `get_by_mobile(mobile_no: str, offset: int = 0, limit: int = 50)` | `Sequence[Customer]` | **Returns collection** matching `MoblieNo1` or `MoblieNo2`. Does NOT assume phone numbers are unique. |
| `get_by_pan(pan_no: str, offset: int = 0, limit: int = 50)` | `Sequence[Customer]` | Lookup by PAN number (returns collection). |

### 5.2 `VehicleRepository` (`app/repositories/vehicle.py`)

| Method Signature | Return Type | Description & Domain Rules |
|---|---|---|
| `get_by_id(cust_veh_id: int)` | `Optional[VehicleDetails]` | Primary key lookup (via `BaseRepository`). |
| `list_by_customer_id(customer_id: int, offset: int = 0, limit: int = 50)` | `Sequence[VehicleDetails]` | Retrieves all vehicles owned by a given customer. Excludes soft-deleted records. |
| `search_by_registration(reg_no: str, branch_id: int = 0, offset: int = 0, limit: int = 50)` | `Sequence[VehicleDetails]` | **Returns collection**. Does NOT assume global registration uniqueness; allows renewals across financial years. Optional branch scoping. |
| `search_by_chassis(chassis_no: str, offset: int = 0, limit: int = 50)` | `Sequence[VehicleDetails]` | **Returns collection**. Matches `ChaiseNo` (physical typo preserved). |
| `check_registration_in_fy(reg_no: str, financial_year: str)` | `Sequence[VehicleDetails]` | Scoped check matching `RegistrationNo` within a specific `FinancialYear` (`sp_CheckRegistrationNoNew` parity). |
| `get_by_registration_no(reg_no: str)` | `Optional[VehicleDetails]` | Backward-compatible helper returning first match. |
| `get_by_chassis_no(chassis_no: str)` | `Optional[VehicleDetails]` | Backward-compatible helper returning first match. |
| `get_by_engine_no(engine_no: str)` | `Optional[VehicleDetails]` | Backward-compatible helper returning first match. |

---

## 6. Test Suite Execution & Verification

### Test Breakdown

1. **Unit Tests (`tests/unit/test_customer_vehicle_models.py`)**:
   - `test_customer_vehicle_table_names`: Physical table names match `tbl_customer` and `tbl_vehicledetails`.
   - `test_customer_vehicle_primary_keys`: `CustomerId` and `CustVehId`.
   - `test_customer_vehicle_column_counts`: 38 and 32 columns.
   - `test_customer_indexes_parity`: `CustomerCode_UNIQUE` (prefix length 100), `Fk5_ClientId_idx`, `Fk18_BranchId_idx`.
   - `test_vehicledetails_indexes_parity`: Exactly 0 secondary indexes on `tbl_vehicledetails`.
   - `test_preserved_spelling_quirks`: `MoblieNo1`, `MoblieNo2`, `CustVehId`, `ChaiseNo` preserved.
   - `test_vehicle_financial_year_not_null`: `FinancialYear` is NOT NULL.
   - `test_zero_physical_foreign_keys`: 0 physical foreign keys on both models.
   - `test_customer_vehicle_mysql_table_args`: Charset `utf8`, collate `utf8_general_ci`, row_format `DYNAMIC`.

2. **Integration Tests (`tests/integration/test_customer_vehicle_repositories.py`)**:
   - `test_customer_vehicle_db_isolation_safety`: Database isolation check against `reliable_insurance_dev`.
   - `test_customer_repository_name_search_and_branch_scoping`: Name substring matching, branch isolation, and soft-delete exclusion.
   - `test_customer_repository_duplicate_mobile_allowed`: Verifies duplicate `MoblieNo1` can be inserted and queried.
   - `test_customer_repository_code_uniqueness_enforced`: Verifies duplicate `CustomerCode` raises `IntegrityError`.
   - `test_customer_repository_list_by_branch`: Verifies branch-scoped customer listing.
   - `test_vehicle_repository_non_unique_registration_allowed`: Verifies identical `RegistrationNo` across different `FinancialYear` can be inserted and queried.
   - `test_vehicle_repository_chassis_search_and_duplicate_allowance`: Verifies duplicate chassis number search.
   - `test_vehicle_repository_list_by_customer_id`: Verifies customer-vehicle ownership linkage and soft-delete filtering.

### Test Results Summary

```text
============================= test session starts =============================
platform win32 -- Python 3.11.2, pytest-9.0.2, pluggy-1.6.0
rootdir: C:\Users\Admin\Desktop\Reliable-Insurance-Backend
configfile: pytest.ini
testpaths: tests
plugins: anyio-4.13.0, failureintel-2.0.0, asyncio-1.3.0, base-url-2.1.0, playwright-0.9.0
asyncio: mode=Mode.AUTO, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collected 85 items

tests\integration\test_auth_api.py ..........                            [ 11%]
tests\integration\test_customer_vehicle_repositories.py ........         [ 21%]
tests\integration\test_db.py ...                                         [ 24%]
tests\integration\test_health.py ...                                     [ 28%]
tests\integration\test_master_repositories.py ........                   [ 37%]
tests\integration\test_repositories.py ..........                        [ 49%]
tests\unit\test_auth.py ......                                           [ 56%]
tests\unit\test_config.py ...                                            [ 60%]
tests\unit\test_customer_vehicle_models.py .........                     [ 70%]
tests\unit\test_master_models.py ........                                [ 80%]
tests\unit\test_middleware.py .....                                      [ 85%]
tests\unit\test_models.py ......                                         [ 92%]
tests\unit\test_security.py ......                                       [100%]

============================= 85 passed in 11.01s =============================
```

- Total Tests: **85**
- Passed: **85** (100%)
- Failed: **0**
- Regressions: **0**

---

## 7. Migration Boundaries & Strict Stop Condition

In strict accordance with Phase 5B boundary rules:
- **No REST CRUD API endpoints** were created (e.g., `/api/v1/customers`, `/api/v1/vehicles`).
- **No Pydantic schemas** or services for customer/vehicle intake were added.
- **No quotation, rating, or booking workflows** were touched.
- **No production connections** were made.

Execution is **COMPLETE and STOPPED**. Awaiting user review and authorization before proceeding to subsequent phases.
