# Reliable Insurance Backend — Naming & Module Structure Standardization Plan

**Branch**: `tejas-feature`  
**Date**: 2026-10-16  
**Status**: APPROVED FOR EXECUTION  
**Workflow Stage**: PLAN (Pre-Implementation Audit & Mapping)  

---

## 1. Executive Summary & Objective

The `Reliable-Insurance-Backend` has migrated 30 incremental phases of business functionality from legacy ASP.NET/C# into a FastAPI, SQLAlchemy 2.0, and Pydantic architecture. During rapid phased migration, incremental development identifiers (such as `phase18a`, `phase20`, `phase21_nonmotor`, `phase22`, `phase23`, `phase24`, `phase25`, `phase26`, `phase27`, `phase28`, `phase29`) were temporarily used as module and file names.

These development-phase identifiers must not become permanent production-code naming conventions.

### Core Principles
1. **Domain-Oriented Naming**: Every production module name must describe its real business domain (e.g. `temporary_operators.py`, `franchise_margins.py`, `bank_remittances.py`, `claim_assistance.py`, `corporate_clients.py`).
2. **Zero Breaking Changes**:
   - 100% preservation of externally visible route paths, HTTP methods, operation IDs, tags, query parameters, and response status codes.
   - 100% preservation of database schemas, table names, column names, indexes, and legacy data models.
   - 100% preservation of Alembic migration revision history and dependency graphs (`alembic/versions/*` and `alembic/env.py` remain untouched).
   - 100% preservation of business calculations, financial formulas, double-entry accounting, and RBAC authorization.
   - 100% test discovery and regression pass rate.
3. **No Unstaged Git Actions**: No `git add`, `git commit`, `git push`, branch switching, rebasing, or resets.

---

## 2. Refactoring Matrix

### 2.1 Category 1: Rename Now (Production Application & Test Modules)

| # | Current Path | Proposed Path | Responsibility | Reason | References & Affected Files | Risk | Verification Checks |
|---|---|---|---|---|---|---|---|
| 1 | `app/api/v1/endpoints/phase29.py` | `app/api/v1/endpoints/temporary_operators.py` | Temporary operator workload delegation endpoints (`/temporary-operators`) | Phase-numbered router obscures domain purpose | `app/api/v1/router.py`, `app/services/temporary_operator_service.py` | Low | Verify router mount, test suite, OpenAPI route inventory |
| 2 | `app/services/phase29_service.py` | `app/services/temporary_operator_service.py` | Temporary operator delegation business logic, RBAC, anti-circularity & anti-chaining | Phase-numbered service filename | `app/api/v1/endpoints/temporary_operators.py`, tests | Low | Import verification, delegation lifecycle tests |
| 3 | `app/schemas/phase29.py` | `app/schemas/temporary_operator.py` | Pydantic request & response schemas for delegation | Phase-numbered schema filename | `temporary_operators.py`, `temporary_operator_service.py` | Low | Schema validation tests |
| 4 | `app/models/phase29_features.py` | `app/models/temporary_operator.py` | SQLAlchemy model for `tbl_tempararyoperator` | Phase-numbered model filename | `app/models/__init__.py`, `temporary_operator_service.py` | Low | Model registration, Base.metadata parity |
| 5 | `tests/test_phase29_features.py` | `tests/test_temporary_operators.py` | Automated tests for temporary operator delegation | Phase-numbered test file | Pytest test discovery | Low | 20/20 tests passing |
| 6 | `app/api/v1/endpoints/phase28.py` | `app/api/v1/endpoints/franchise_margins.py` | Franchise agent grid margin override endpoints (`/franchise-margins`) | Phase-numbered router obscures domain purpose | `app/api/v1/router.py`, `franchise_margin_service.py` | Low | Verify router mount, test suite, OpenAPI route inventory |
| 7 | `app/services/phase28_service.py` | `app/services/franchise_margin_service.py` | Franchise agent grid margin resolution, upsert, and calculation | Phase-numbered service filename | `app/api/v1/endpoints/franchise_margins.py`, tests | Low | Import verification, margin calculation tests |
| 8 | `app/schemas/phase28.py` | `app/schemas/franchise_margin.py` | Pydantic schemas for franchise agent grid margins | Phase-numbered schema filename | `franchise_margins.py`, `franchise_margin_service.py` | Low | Schema validation tests |
| 9 | `app/models/phase28_features.py` | `app/models/franchise_margin.py` | SQLAlchemy model for `tbl_franchiseagentgridmargin` | Phase-numbered model filename | `app/models/__init__.py`, `app/repositories/policy_booking.py`, `app/repositories/commission_accounting.py` | Low | Model registration, repository imports, Base.metadata parity |
| 10 | `tests/test_phase28_features.py` | `tests/test_franchise_margins.py` | Automated tests for franchise agent grid margins & policy integration | Phase-numbered test file | Pytest test discovery | Low | 14/14 tests passing |
| 11 | `app/api/v1/endpoints/phase27.py` | `app/api/v1/endpoints/bank_remittances.py` | Company outstanding premium remittance & cash-to-bank settlement (`/bank-remittances`) | Phase-numbered router obscures domain purpose | `app/api/v1/router.py`, `bank_remittance_service.py` | Low | Verify router mount, test suite, OpenAPI route inventory |
| 12 | `app/services/phase27_service.py` | `app/services/bank_remittance_service.py` | Bank remittance and deposit business workflows | Phase-numbered service filename | `app/api/v1/endpoints/bank_remittances.py`, tests | Low | Import verification, bank remittance tests |
| 13 | `app/schemas/phase27.py` | `app/schemas/bank_remittance.py` | Pydantic schemas for bank remittances and cash deposits | Phase-numbered schema filename | `bank_remittances.py`, `bank_remittance_service.py` | Low | Schema validation tests |
| 14 | `app/models/phase27_features.py` | `app/models/bank_remittance.py` | SQLAlchemy model for `tbl_debitfrombankaccount` | Phase-numbered model filename | `app/models/__init__.py`, `bank_remittance_service.py` | Low | Model registration, Base.metadata parity |
| 15 | `tests/test_phase27_features.py` | `tests/test_bank_remittances.py` | Automated tests for company bank remittances & deposits | Phase-numbered test file | Pytest test discovery | Low | 6/6 tests passing |
| 16 | `app/api/v1/endpoints/phase26.py` | `app/api/v1/endpoints/claim_assistance.py` | Emergency roadside claim assistance & accident intake (`/claim-assistance`) | Phase-numbered router obscures domain purpose | `app/api/v1/router.py`, `claim_assistance_service.py` | Low | Verify router mount, test suite, OpenAPI route inventory |
| 17 | `app/services/phase26_service.py` | `app/services/claim_assistance_service.py` | Roadside claim assistance service and triage | Phase-numbered service filename | `app/api/v1/endpoints/claim_assistance.py`, tests | Low | Import verification, claim assistance tests |
| 18 | `app/schemas/phase26.py` | `app/schemas/claim_assistance.py` | Pydantic schemas for roadside claim assistance | Phase-numbered schema filename | `claim_assistance.py`, `claim_assistance_service.py` | Low | Schema validation tests |
| 19 | `app/models/phase26_features.py` | `app/models/claim_assistance.py` | SQLAlchemy models for `tbl_claimassistance`, `tbl_claimassistanceimg` | Phase-numbered model filename | `app/models/__init__.py`, `claim_assistance_service.py` | Low | Model registration, Base.metadata parity |
| 20 | `tests/test_phase26_features.py` | `tests/test_claim_assistance.py` | Automated tests for roadside claim assistance | Phase-numbered test file | Pytest test discovery | Low | 10/10 tests passing |
| 21 | `app/api/v1/endpoints/phase25.py` | `app/api/v1/endpoints/corporate_clients.py` | Corporate group clients, commercial sales types, invoicing, sister concern advances | Phase-numbered router obscures domain purpose | `app/api/v1/router.py`, `corporate_client_service.py` | Low | Verify router mount, test suite, OpenAPI route inventory |
| 22 | `app/services/phase25_service.py` | `app/services/corporate_client_service.py` | Corporate clients, commercial invoicing & company advances service | Phase-numbered service filename | `app/api/v1/endpoints/corporate_clients.py`, tests | Low | Import verification, invoicing & advance tests |
| 23 | `app/schemas/phase25.py` | `app/schemas/corporate_client.py` | Pydantic schemas for corporate clients, commercial invoices, company advances | Phase-numbered schema filename | `corporate_clients.py`, `corporate_client_service.py` | Low | Schema validation tests |
| 24 | `app/models/phase25_features.py` | `app/models/corporate_client.py` | SQLAlchemy models for `tbl_salestype`, `tbl_reliablecompanymst`, `tbl_clientmaster`, `tbl_salesregdetails`, `tbl_companyadvancemaster`, `tbl_companyadvdetails`, `tbl_invoicesequence` | Phase-numbered model filename | `app/models/__init__.py`, `app/repositories/commission_accounting.py`, tests | Low | Model registration, repository imports, Base.metadata parity |
| 25 | `tests/test_phase25_features.py` | `tests/test_corporate_clients.py` | Automated tests for corporate clients & commercial invoicing | Phase-numbered test file | Pytest test discovery | Low | 11/11 tests passing |
| 26 | `app/api/v1/endpoints/phase24.py` | `app/api/v1/endpoints/hr_payroll.py` | HR workforce lifecycle, compensation, employee advances, monthly attendance | Phase-numbered router obscures domain purpose | `app/api/v1/router.py`, `hr_payroll_service.py` | Low | Verify router mount, test suite, OpenAPI route inventory |
| 27 | `app/services/phase24_service.py` | `app/services/hr_payroll_service.py` | HR payroll, salary structure, working time, advances service | Phase-numbered service filename | `app/api/v1/endpoints/hr_payroll.py`, tests | Low | Import verification, payroll tests |
| 28 | `app/schemas/phase24.py` | `app/schemas/hr_payroll.py` | Pydantic schemas for HR payroll, salary structure, working time, advances | Phase-numbered schema filename | `hr_payroll.py`, `hr_payroll_service.py` | Low | Schema validation tests |
| 29 | `app/models/phase24_features.py` | `app/models/hr_payroll.py` | SQLAlchemy models for `tbl_hrworkinghistory`, `tbl_hrfamilydetails`, `tbl_hrreferencedetails`, `tbl_hrworkingtime`, `tbl_hrsalarystructuredef`, `tbl_hradvance`, `tbl_hrmonthlyworkingdetails` | Phase-numbered model filename | `app/models/__init__.py`, `hr_payroll_service.py` | Low | Model registration, Base.metadata parity |
| 30 | `tests/test_phase24_features.py` | `tests/test_hr_payroll.py` | Automated tests for HR payroll & attendance | Phase-numbered test file | Pytest test discovery | Low | 5/5 tests passing |
| 31 | `app/api/v1/endpoints/phase23.py` | `app/api/v1/endpoints/hr_management.py` | HR organizations, departments, designations, facilities, holiday calendar, leave management | Phase-numbered router obscures domain purpose | `app/api/v1/router.py`, `hr_management_service.py` | Low | Verify router mount, test suite, OpenAPI route inventory |
| 32 | `app/services/phase23_service.py` | `app/services/hr_management_service.py` | HR master organizational structure and leave approval workflows | Phase-numbered service filename | `app/api/v1/endpoints/hr_management.py`, tests | Low | Import verification, HR management tests |
| 33 | `app/schemas/phase23.py` | `app/schemas/hr_management.py` | Pydantic schemas for HR organizations, departments, leaves | Phase-numbered schema filename | `hr_management.py`, `hr_management_service.py` | Low | Schema validation tests |
| 34 | `app/models/phase23_features.py` | `app/models/hr_management.py` | SQLAlchemy models for `tbl_hrorganization`, `tbl_hrdepartment`, `tbl_hrdesignation`, `tbl_hrfacility`, `tbl_hrholiday`, `tbl_hrleavetype`, `tbl_hrleave`, `tbl_hrcontactperson` | Phase-numbered model filename | `app/models/__init__.py`, `hr_management_service.py` | Low | Model registration, Base.metadata parity |
| 35 | `tests/test_phase23_features.py` | `tests/test_hr_management.py` | Automated tests for HR organizational masters & leaves | Phase-numbered test file | Pytest test discovery | Low | 5/5 tests passing |
| 36 | `app/api/v1/endpoints/phase22.py` | `app/api/v1/endpoints/executive_commissions.py` | Sales Executive & Location Head Commissions, Insurer Portals, App Billing | Phase-numbered router obscures domain purpose | `app/api/v1/router.py`, `executive_commission_service.py` | Low | Verify router mount, test suite, OpenAPI route inventory |
| 37 | `app/services/phase22_service.py` | `app/services/executive_commission_service.py` | Executive & Location Head Commission hierarchy, insurer portals, billing claims service | Phase-numbered service filename | `app/api/v1/endpoints/executive_commissions.py`, tests | Low | Import verification, executive commission tests |
| 38 | `app/schemas/phase22.py` | `app/schemas/executive_commission.py` | Pydantic schemas for executive commissions, insurer portals, billing claims | Phase-numbered schema filename | `executive_commissions.py`, `executive_commission_service.py` | Low | Schema validation tests |
| 39 | `app/models/phase22_features.py` | `app/models/executive_commission.py` | SQLAlchemy models for `tbl_salesexecutivecommission`, `tbl_locationheadcommission`, `tbl_locationheadsalesexmap`, `tbl_insurancecompanyportal`, `tbl_appbillingdetails`, `tbl_appbillingattachment` | Phase-numbered model filename | `app/models/__init__.py`, `executive_commission_service.py` | Low | Model registration, Base.metadata parity |
| 40 | `tests/test_phase22_features.py` | `tests/test_executive_commissions.py` | Automated tests for executive commissions & portals | Phase-numbered test file | Pytest test discovery | Low | 5/5 tests passing |
| 41 | `app/api/v1/endpoints/phase21_nonmotor.py` | `app/api/v1/endpoints/nonmotor.py` | Non-Motor Commercial Insurance Lines of Business & Operations | Phase-numbered router obscures domain purpose | `app/api/v1/router.py`, `nonmotor_service.py` | Low | Verify router mount, test suite, OpenAPI route inventory |
| 42 | `app/services/phase21_nonmotor_service.py` | `app/services/nonmotor_service.py` | Non-motor products, endorsements, commissions, and transaction service | Phase-numbered service filename | `app/api/v1/endpoints/nonmotor.py`, tests | Low | Import verification, nonmotor tests |
| 43 | `app/schemas/phase21_nonmotor.py` | `app/schemas/nonmotor.py` | Pydantic schemas for non-motor insurance classes, products, endorsements, commissions | Phase-numbered schema filename | `nonmotor.py`, `nonmotor_service.py` | Low | Schema validation tests |
| 44 | `app/models/phase21_nonmotor.py` | `app/models/nonmotor.py` | SQLAlchemy models for `tbl_nonmotorclass`, `tbl_nonmotorproduct`, etc. | Phase-numbered model filename | `app/models/__init__.py`, `nonmotor_service.py` | Low | Model registration, Base.metadata parity |
| 45 | `tests/test_phase21_nonmotor_features.py` | `tests/test_nonmotor.py` | Automated tests for non-motor commercial insurance | Phase-numbered test file | Pytest test discovery | Low | 6/6 tests passing |
| 46 | `app/api/v1/endpoints/phase20.py` | `app/api/v1/endpoints/operational_extensions.py` | Circulars, Customer Helpdesk, Web Notifications, Clusters, Decline Rules, Reward Points | Phase-numbered router obscures domain purpose | `app/api/v1/router.py`, `operational_extension_service.py` | Low | Verify router mount, test suite, OpenAPI route inventory |
| 47 | `app/services/phase20_service.py` | `app/services/operational_extension_service.py` | Circulars, helpdesk chat, web alerts, reward points, cluster grids & decline rules service | Phase-numbered service filename | `app/api/v1/endpoints/operational_extensions.py`, tests | Low | Import verification, operational extension tests |
| 48 | `app/schemas/phase20.py` | `app/schemas/operational_extensions.py` | Pydantic schemas for circulars, customer helpdesk, clusters, decline rules | Phase-numbered schema filename | `operational_extensions.py`, `operational_extension_service.py` | Low | Schema validation tests |
| 49 | `app/models/phase20_features.py` | `app/models/operational_extensions.py` | SQLAlchemy models for `tbl_circular`, `tbl_customerhelp`, `tbl_chatboard`, `tbl_webnotification`, `tbl_rewardpoint`, `tbl_clustermaster`, `tbl_clusterdetail`, `tbl_clusterwisebrokergrid`, `tbl_clusterwiseagentgrid`, `tbl_griddeclinemaster`, `tbl_declinemodel` | Phase-numbered model filename | `app/models/__init__.py`, `operational_extension_service.py` | Low | Model registration, Base.metadata parity |
| 50 | `tests/test_phase20_batch1_features.py` | `tests/test_operational_support.py` | Automated tests for circulars, helpdesk, web notifications, reward points | Phase-numbered test file | Pytest test discovery | Low | 4/4 tests passing |
| 51 | `tests/test_phase20_batch2_features.py` | `tests/test_clusters_and_decline_rules.py` | Automated tests for commercial clusters & decline rules | Phase-numbered test file | Pytest test discovery | Low | 2/2 tests passing |
| 52 | `app/api/v1/endpoints/phase18a.py` | `app/api/v1/endpoints/operations_parity.py` | Supplementary parity endpoints for documents, payments, commissions, accounting, renewals, inspections | Phase-numbered router obscures domain purpose | `app/api/v1/router.py`, `operations_parity_service.py` | Low | Verify router mount, test suite, OpenAPI route inventory |
| 53 | `app/services/phase18a_service.py` | `app/services/operations_parity_service.py` | Business logic for parity extensions (ideal receipts, cash locks, tickets, leads) | Phase-numbered service filename | `app/api/v1/endpoints/operations_parity.py`, tests | Low | Import verification, operations parity tests |
| 54 | `app/schemas/phase18a.py` | `app/schemas/operations_parity.py` | Pydantic schemas for operational parity extensions | Phase-numbered schema filename | `operations_parity.py`, `operations_parity_service.py` | Low | Schema validation tests |
| 55 | `app/models/phase18a_features.py` | `app/models/operations_parity.py` | SQLAlchemy models for `tbl_salesregistration`, `tbl_commissionrategrid`, `tbl_idealpaymentreceipt`, `tbl_supportticket`, etc. | Phase-numbered model filename | `app/models/__init__.py`, `app/models/corporate_client.py`, tests | Low | Model registration, Base.metadata parity |
| 56 | `tests/test_phase18a_remaining_features.py` | `tests/test_operations_parity.py` | Automated tests for operations parity extensions | Phase-numbered test file | Pytest test discovery | Low | 15/15 tests passing |

---

### 2.2 Category 2: Keep Unchanged (Appropriate or Must Be Preserved)

| Path / Pattern | Type | Reason for Keeping Unchanged |
|---|---|---|
| `alembic/versions/*.py` | Alembic Migrations | Revision IDs (`m29a0e1f2901`, `l28a0d0e2801`, etc.) and migration filenames are part of the immutable database history chain. Renaming migration files would corrupt revision tracking. |
| `alembic/env.py` | Migration Environment | Protected by strict safety rule 6. |
| `requirements.txt` | Package Dependencies | Protected by strict safety rule 7. |
| `InsurancefinalNew_2026_09_23/` | Legacy Baseline | Protected legacy read-only reference repository. |
| `docs/migration/PHASE_*_EXECUTION_REPORT.md` | Historical Documentation | Audit trails documenting chronological development phases. |
| `app/core/rbac.py` | Core Security Engine | Core RBAC role mappings and principal context resolution. |
| `app/api/v1/endpoints/{policies,quotations,payments,customers,...}.py` | Existing Domain Routers | Already strictly domain-oriented. |
| `app/models/{transaction,customer,vehicle,quotation,...}.py` | Existing Domain Models | Already strictly domain-oriented. |

---

### 2.3 Category 3: Defer (High Risk or External Dependencies)

| Path / Pattern | Responsibility | Reason for Deferral |
|---|---|---|
| `tests/integration/test_phase*.py` (Phases 5G through 16B) | Golden Parity and Integration Suites | 50+ test files pegged to specific numbered sections of `06_BUSINESS_WORKFLOWS.md` and `07_GOLDEN_PARITY_VERIFICATION.md` for historical stored-procedure parity audits. Renaming them provides zero architectural benefit to production application code and risks test traceability divergence. |
| `tests/unit/test_phase*.py` (Phases 5G through 16B) | Unit Calculation Suites | Similar to integration suites, these verify historical calculation matrices (e.g. `test_phase6_rating_engine.py`, `test_phase10_claims_endorsements_calculations.py`). Kept as-is for golden parity traceability. |

---

## 3. Implementation Steps & Verification Protocol

1. **File Moves & Renames**:
   - Move modules using clean domain names in `app/api/v1/endpoints/`, `app/services/`, `app/schemas/`, `app/models/`, and root `tests/`.
2. **Update Module Imports**:
   - In `app/api/v1/router.py`: import new domain modules and include routers with identical prefixes.
   - In `app/models/__init__.py`: update imports from new domain model modules and maintain `__all__`.
   - In `app/repositories/policy_booking.py` and `app/repositories/commission_accounting.py`: update imports from `app.models.franchise_margin` and `app.models.corporate_client`.
   - Inside newly renamed endpoints, services, schemas, and tests: update internal imports to match the new filenames.
   - Retain class aliases where helpful (e.g. `TemporaryOperatorService = Phase29Service`, `FranchiseMarginService = Phase28Service`) to avoid breaking any subtle dynamic references.
3. **Automated Verification**:
   - Verify Python syntax across the entire codebase (`python -m py_compile`).
   - Verify 100% route count and route signature parity (all 524 routes must match `baseline_routes.json`).
   - Verify Alembic revision chain integrity (`alembic heads`).
   - Run pytest test collection (`pytest --collect-only -q`) to ensure exactly 517 tests are collected.
   - Run small-batch test suites (`pytest -q --tb=short`).
   - Verify Git status and diffs.
