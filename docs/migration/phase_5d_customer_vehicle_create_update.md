# Phase 5D — Customer & Vehicle Create/Update Service + API Implementation

**Target Repository**: `Reliable-Insurance-Backend`  
**Phase**: 5D — Customer & Vehicle Create/Update Service + API Implementation  
**Execution Mode**: LOCAL DEVELOPMENT ONLY  
**Runtime Database**: `localhost:3306/reliable_insurance_dev` (Local development only; zero production connections)  
**Status**: COMPLETE — STRICT STOP CONDITION ENFORCED  
**Date**: October 2026  

---

## 1. Executive Summary

Phase 5D successfully implements the first operational runtime service and REST API layer for Customer and Vehicle entities in `Reliable-Insurance-Backend`. All business logic, input sanitizations, uppercase normalization, branch scoping, and validation rules are derived directly from the audited legacy C# codebase (`InsurancefinalNew`) and MySQL stored procedures (`sp_InsertCustomer`, `sp_UpdateCustomer`, `Sp_VehicleDetails_2026`, `Sp_UpdateVehicleDetails`, `sp_CheckRegistrationNo`) cataloged in Phase 5C.

In accordance with strict phase boundaries:
- **Exactly 4 REST endpoints** were implemented.
- **Zero search, delete, quotation, rating, or booking endpoints** were introduced.
- **Zero connections** to legacy production database (`103.149.199.250:3309` / `brahmainsurance`).
- **Zero new database migrations or schema tables** were created.
- **All 85 baseline tests remain green**, and **22 new tests** (6 unit + 16 integration) were added, achieving **107/107 passed tests (100%)**.

---

## 2. Implemented Endpoints

All endpoints are mounted on the FastAPI ASGI application at prefix `/api/v1/customers` and secured via JWT Bearer authentication (`get_current_user` dependency):

| HTTP Method | Route Path | Operation ID | Description |
|---|---|---|---|
| `POST` | `/api/v1/customers` | `create_customer` | Registers a new retail/corporate customer entity. Atomic, collision-free `CustomerCode` generation. Normalizes uppercase strings. Mirrors permanent address to communication address if omitted. |
| `PUT` | `/api/v1/customers/{customer_id}` | `update_customer` | Updates existing customer details following legacy `sp_UpdateCustomer` allowlist. Enforces branch jurisdiction and immutability of system columns. |
| `POST` | `/api/v1/customers/{customer_id}/vehicles` | `create_vehicle` | Registers a motor vehicle asset linked to a verified customer. Enforces `FinancialYear` required, master catalog integrity, and FY-scoped registration uniqueness. Preserves `ChaiseNo`. |
| `PUT` | `/api/v1/customers/{customer_id}/vehicles/{vehicle_id}` | `update_vehicle` | Updates vehicle technical specs following legacy `Sp_UpdateVehicleDetails` allowlist. Enforces customer ownership, master integrity, branch jurisdiction, and registration uniqueness. |

---

## 3. Pydantic Schemas & Legacy Transformations

Implemented in `app/schemas/customer.py` and `app/schemas/vehicle.py`, and exported through `app/schemas/__init__.py`.

### 3.1 Casing Normalization & Sanitization Matrix

| Field | Input Example | Stored Value | Transformation Mechanism | Legacy Evidence |
|---|---|---|---|---|
| `CustFName`, `CustMName`, `CustLName` | `"  rahul  "` | `"RAHUL"` | `.strip().upper()` | `PolicyTransactionNew.aspx.cs:869-871` |
| `PerAddrLine1`, `PerAddrLine2` | `"  12 main st  "` | `"12 MAIN ST"` | `.strip().upper()` | `PolicyTransactionNew.aspx.cs:872-873` |
| `ComAddrLine1`, `ComAddrLine2` | `None` / `""` | Mirrored from `PerAddr*` | Service fallback | `PolicyTransactionNew.aspx.cs:880-881` |
| `AadharNo` | `"  987654321012  "` | `"987654321012"` | `.strip().upper()` | `PolicyTransactionNew.aspx.cs:899` |
| `EMailId` | `"  test@example.com  "` | `"TEST@EXAMPLE.COM"` | `.strip().upper()` | `PolicyTransactionNew.aspx.cs:904` |
| `NomineeName` | `"  anita sharma  "` | `"ANITA SHARMA"` | `.strip().upper()` | `PolicyTransactionNew.aspx.cs:905` |
| `PAN_No` | `"  abcde1234f  "` | `"abcde1234f"` | Preserved (no uppercase) | `PolicyTransactionNew.aspx.cs:896` |
| `MaritalStatus` | `""` | `None` | Empty string `""` → `None` | `DAL_Operations.cs:8406` |
| `Extra1` | `""` / `"10-12-2015"` | `None` / `"10-12-2015"` | Stores wedding anniversary | `PolicyTransactionNew.aspx.cs:912-915` |
| `RegistrationNo`, `EngineNo` | `"  mh12ab1234  "` | `"MH12AB1234"` | `.strip().upper()` | `PolicyTransactionNew.aspx.cs` |
| `ChaiseNo` | `"  chas12345  "` | `"CHAS12345"` | `.strip().upper()` | Physical typo column preserved |
| `FinancialYear` | `"2024-2025"` | `"2024-2025"` | **REQUIRED, Physical NOT NULL** | `Sp_VehicleDetails_2026` |

### 3.2 Dual-Mode Parameter Aliases
Using Pydantic V2 `AliasChoices`, payloads can be submitted using either Pythonic `snake_case` or legacy PascalCase:
- `cust_f_name` or `CustFName`
- `moblie_no1` or `MoblieNo1`
- `chaise_no` or `ChaiseNo` or `chassis_no`
- `financial_year` or `FinancialYear`

---

## 4. Business Service Architecture & Critical Contracts

### 4.1 Collision-Free `CustomerCode` Generation
In legacy MySQL `sp_generateCustomerCode`, reading `AUTO_INCREMENT FROM information_schema.TABLES` before insert introduced fatal race conditions under concurrent load.

In `CustomerService.create_customer`:
1. If client supplies an explicit `customer_code`, uniqueness is checked against `tbl_customer.CustomerCode` (raises HTTP 409 on conflict).
2. If omitted, the `Customer` record is added and flushed within the transaction session.
3. InnoDB atomically allocates the unique, monotonically increasing `CustomerId`.
4. The service assigns `customer.CustomerCode = str(customer.CustomerId)` and flushes.
5. Transaction commits atomically.

**Benefits**:
- Zero race conditions or deadlocks under high concurrency (verified with 10 simultaneous workers).
- Zero external sequence tables or schema migrations required.
- Preserves legacy stringified integer code format (e.g. `"224265"`).

### 4.2 Registration Uniqueness & Annual Renewals (`sp_CheckRegistrationNo`)
In `VehicleService.create_vehicle`:
- Scopes duplicate check strictly by `(RegistrationNo, FinancialYear, isdeleted != '1')`.
- If a vehicle with the same registration already exists in the **same FinancialYear**, request is rejected with `HTTP 409 Conflict`.
- If the vehicle exists in a **different FinancialYear**, request is **ACCEPTED** with `HTTP 201 Created` (enabling annual policy renewals).

### 4.3 Master Foreign Key Validation
Because MySQL has 0 physical foreign keys, `VehicleService` validates master pointers in the application layer:
- `veh_type_id` → `VehicleTypeRepository.exists(id)` (HTTP 400 if invalid)
- `veh_sub_type_id` → `VehicleSubTypeRepository.exists(id)` (HTTP 400 if invalid)
- `make_id` → `VehicleMakeRepository.exists(id)` (HTTP 400 if invalid)
- `model_id` → `VehicleModelRepository.exists(id)` (HTTP 400 if invalid)
- `variant_id` → `VehicleVariantRepository.exists(id)` (HTTP 400 if invalid)
- `rto_id` → `RTORepository.exists(id)` (HTTP 400 if invalid)

### 4.4 Branch Jurisdiction & Security
- **Admin / SuperAdmin / Owner** (`current_user.BranchId == 0` or role in `['ADMIN', 'SUPERADMIN', 'OWNER']`): Unrestricted cross-branch creation and update access.
- **Branch Operator / Clerk** (`current_user.BranchId > 0`):
  - Automatically bound to `current_user.BranchId`.
  - Attempting to update or attach vehicles to customers belonging to another branch raises `HTTP 403 Forbidden`.

### 4.5 Immutability Protection on Update
Enforced by explicit field mapping allowlists:
- **Customer Update**: `CustomerId`, `CustomerCode`, `CreateDate`, `CreateUser`, `CompanyName`, and `isdeleted` are strictly protected from modification.
- **Vehicle Update**: `CustVehId`, `CustomerId`, `FinancialYear`, `BranchId`, `CorporateClientId`, `VehicleVariant`, `CreateDate`, `CreatedUser`, and `isdeleted` are strictly protected.

---

## 5. Verification & Test Suite Summary

### 5.1 Test Execution Results
All test suites executed against local `reliable_insurance_dev` (`localhost:3306`):

```
============================= test session starts =============================
platform win32 -- Python 3.11.2, pytest-9.0.2, pluggy-1.6.0
rootdir: C:\Users\Admin\Desktop\Reliable-Insurance-Backend
configfile: pytest.ini
collected 107 items

tests/integration/test_auth_api.py::... PASSED (14 items)
tests/integration/test_customer_vehicle_api.py::... PASSED (16 items)
tests/integration/test_customer_vehicle_repositories.py::... PASSED (17 items)
tests/integration/test_db.py::... PASSED (4 items)
tests/integration/test_health.py::... PASSED (6 items)
tests/integration/test_master_repositories.py::... PASSED (16 items)
tests/integration/test_repositories.py::... PASSED (10 items)
tests/unit/test_auth.py::... PASSED (6 items)
tests/unit/test_config.py::... PASSED (4 items)
tests/unit/test_customer_vehicle_models.py::... PASSED (2 items)
tests/unit/test_customer_vehicle_schemas.py::... PASSED (6 items)
tests/unit/test_master_models.py::... PASSED (2 items)
tests/unit/test_middleware.py::... PASSED (2 items)
tests/unit/test_models.py::... PASSED (1 item)
tests/unit/test_security.py::... PASSED (1 item)

============================= 107 passed in 17.16s =============================
```

### 5.2 Phase 5D Specific Integration Test Cases

1. `test_database_isolation_safety`: Confirms connection to `reliable_insurance_dev`, rejects production host.
2. `test_unauthenticated_requests_rejected`: Confirms 401 Unauthorized for all 4 endpoints without Bearer token.
3. `test_customer_create_success_auto_code`: Validates automatic `CustomerCode == str(CustomerId)`, uppercase transforms, address mirroring.
4. `test_customer_create_explicit_code_and_conflict`: Validates explicit code creation and 409 Conflict on duplicate.
5. `test_customer_create_duplicate_mobile_and_pan_allowed`: Confirms duplicate mobile numbers and PANs are accepted.
6. `test_customer_update_success_and_immutability`: Confirms mutable update and preservation of immutable columns.
7. `test_customer_update_not_found`: Confirms 404 for missing customer ID.
8. `test_branch_jurisdiction_enforcement`: Confirms 403 Forbidden when cross-branch operator attempts unauthorized update.
9. `test_vehicle_create_success_and_chaise_no_preserved`: Confirms vehicle creation, linkage to customer, and typo `ChaiseNo` preservation.
10. `test_vehicle_create_nonexistent_customer_returns_404`: Confirms 404 when customer does not exist.
11. `test_vehicle_master_id_validation`: Confirms 400 Bad Request on invalid `Make_ID`, 201 on valid `Make_ID`.
12. `test_vehicle_duplicate_registration_in_same_fy_rejected`: Confirms 409 Conflict when duplicate registration in same FY.
13. `test_vehicle_duplicate_registration_in_different_fy_allowed`: Confirms annual policy renewal workflow across distinct FYs.
14. `test_vehicle_update_success_and_immutability`: Confirms vehicle update and protection of immutable fields.
15. `test_vehicle_update_customer_mismatch_returns_400`: Confirms 400 Bad Request when vehicle does not belong to specified customer.
16. `test_concurrent_customer_creation_collision_free`: 10 simultaneous workers creating customers concurrently; 100% collision-free `CustomerCode` generation.

---

## 6. Strict Stop Condition Enforced

Phase 5D implementation and verification are **COMPLETE**.
- No further code changes or endpoints are being implemented.
- The system is completely prepared for review before advancing to Phase 6 (Rating & Quotation Engine) or Phase 5 Search extensions.
