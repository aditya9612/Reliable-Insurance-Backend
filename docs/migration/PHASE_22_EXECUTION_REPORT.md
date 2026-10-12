# Phase 22 Execution Report: Sales Executive & Location Head Commission Hierarchy, Insurer Portals Registry & App Billing Claims

## 1. Executive Summary

Phase 22 continues the full-scope legacy functional migration of the Reliable Insurance system from legacy ASP.NET/C# into the modern FastAPI backend on branch `tejas-feature`.

This batch implemented four major operational domains from the legacy system:
1. **Sales Executive Multi-Tier Commission Hierarchy & Grid Matching Engine** (`tbl_salesexcommission` — legacy `BLL_SalesExCommision`, `DAL_SalesExCommision`, `adm_SaleExCommission.aspx.cs`).
2. **Location Head Regional Overrides & Team Hierarchy Assignment** (`tbl_locationheadcommission`, `tbl_locationheadsalesexmap` — legacy `AssignLocationHeadToSalesEx.aspx.cs`, `sp_InsertAssignLocHeadToSalesex`, `sp_getLocationHeadIdFromSalesExecutive`).
3. **Insurer Partner Portals & Direct Underwriting Credentials Registry** (`tbl_insurancecompanyportal` — legacy `BLL_Portal`, `BLL_InsuranceCompanyPortal`, `adm_InsuranceCompanyPortal.aspx.cs`).
4. **App Billing & Field Executive Expense Reimbursement Claims** (`tbl_appbillingdetails`, `tbl_appbillingattachment` — legacy `BLL_AppBillingDetails`, `DAL_AppBillingDetails`, `Service.asmx.cs:InsertAppBillingDetails`, `ViewAppBillingDetails.aspx.cs`).

### Baseline Progression

| Metric | Post-Phase 20 | Post-Phase 21 | Post-Phase 22 | Delta (Phase 22) |
| :--- | :--- | :--- | :--- | :--- |
| **Alembic Head** | `d20b0c2d2002` | `e21a0c3d2101` | `f22a0c4d2201` | +1 revision |
| **Physical MySQL Tables** | 93 | 104 | **110** | **+6 tables** |
| **FastAPI Mounted Routes** | 339 | 369 | **393** | **+24 endpoints** |
| **Automated Tests** | 426 | 438 | **443** | **+5 tests (0 regressions)** |
| **Frozen Rule LBR-069** | Untouched | Untouched | **Untouched** | Zero modification |

---

## 2. Step 1: Verification of Phase 21 Deliverables

Phase 21 implemented Non-Motor Commercial Insurance Lines of Business across 11 physical tables (`tbl_nonmotorclass`, `tbl_nonmotorproduct`, `tbl_nonmotorbusinesstype`, `tbl_nonmotordocumenttype`, `tbl_nonmotorendorsmenttype`, `tbl_nonmotorendorsmentsubtype`, `tbl_nonmotorinsurancetype`, `tbl_nonmotorinsurancesubtype`, `tbl_nonmotortypeofinsurancesubtype`, `tbl_nonmotorcommission`, `tbl_nonmotortransaction`).

Verification findings:
- **Inward Number Sequencing**: Verified inward numbering format conforms to legacy format (`INW-NM-YYYYMMDD-XXXX`) with daily reset and atomic incrementing.
- **TDS Withholding & Commission Math**: Verified formula `NetCommission = NetPremium * Rate%` and `TDSAmount = NetCommission * 5.0%`, with net payable matching legacy DAL semantics.
- **Schema & Migration**: Verified `e21a0c3d2101` created 11 physical tables with strict UTF-8 dynamic collation and explicit foreign key-safe indexing.
- **Route Mounting Order**: Static routes (`/classes`, `/endorsements/types`, `/commissions/grids`, `/calculate`, `/summary`) are registered before parameterized endpoints (`/{id}`), preventing 422 routing collisions.
- **Regression Suite**: All 438 tests passed with zero failures in 166.87s prior to Phase 22 implementation.

---

## 3. Phase 22 Implemented Capabilities & Legacy Traceability

### Capability 1: Sales Executive Commission Matrix (`tbl_salesexcommission`)
- **Legacy Source**: `BLL_SalesExCommision`, `DAL_SalesExCommision`, `adm_SaleExCommission.aspx.cs`, `sp_SelectSalesExecutiveCommissionGridnew2025`, `Sp_InsertMultiplesalesexCommissionnew2025`.
- **Implementation**:
  - Model: `SalesExecutiveCommission` in `app/models/phase22_features.py`.
  - Schema: `SalesExecutiveCommissionCreate`, `SalesExecutiveCommissionUpdate`, `SalesExecutiveCommissionResponse`, `SalesExecutiveCommissionLookupRequest`, `SalesExecutiveCommissionLookupResponse` in `app/schemas/phase22.py`.
  - Service: `Phase22Service.create_sales_ex_commission`, `Phase22Service.list_sales_ex_commissions`, `Phase22Service.lookup_sales_ex_commission`, `Phase22Service.update_sales_ex_commission`, `Phase22Service.delete_sales_ex_commission` in `app/services/phase22_service.py`.
  - Endpoints: Mounted at `/api/v1/commissions/sales-executives/grids` and `/lookup`.
  - Semantics: Preserves multi-tier commission matching across `SalesEx_Id`, `InsuranceCompanyId`, `PolicyType`, `ProductType`, `VehiTypeId`, `FuelTypeId`, `FranchiseCode`, `ncb`, `OD_Discount`, with duplicate conflict rejection (HTTP 409).

### Capability 2: Location Head Commission Overrides & Team Hierarchy (`tbl_locationheadcommission`, `tbl_locationheadsalesexmap`)
- **Legacy Source**: `BLL_SalesExCommision`, `adm_SaleExCommission.aspx.cs`, `AssignLocationHeadToSalesEx.aspx.cs`, `sp_SelectSelectLocationHeadCommissionGrid`, `sp_SelectLocationHeadSalesExWiseComm`, `sp_InsertAssignLocHeadToSalesex`, `sp_getLocationHeadIdFromSalesExecutive`.
- **Implementation**:
  - Models: `LocationHeadCommission`, `LocationHeadSalesExMap` in `app/models/phase22_features.py`.
  - Service: Regional override grid lookups, bulk executive assignment (`Phase22Service.assign_sales_executives_to_location_head`), team listing, and executive-to-head queries.
  - Endpoints: Mounted at `/api/v1/commissions/location-heads/grids`, `/lookup`, `/assignments`, `/sales-executives/{sales_ex_id}`, and `/{location_head_id}/team`.

### Capability 3: Insurer Partner Portals Registry (`tbl_insurancecompanyportal`)
- **Legacy Source**: `BLL_Portal`, `BLL_InsuranceCompanyPortal`, `DAL_InsuranceCompanyPortal`, `adm_InsuranceCompanyPortal.aspx.cs`, `sp_insurancecompanyportal`, `Sp_selectInsuranceCompanyPortal`.
- **Implementation**:
  - Model: `InsuranceCompanyPortal` in `app/models/phase22_features.py`.
  - Service: Secure registry of direct insurer underwriting portal URLs, user identifiers, contact persons, and partner credentials.
  - Endpoints: Mounted at `/api/v1/masters/insurer-portals`.

### Capability 4: App Billing & Field Expense Reimbursement Claims (`tbl_appbillingdetails`, `tbl_appbillingattachment`)
- **Legacy Source**: `BLL_AppBillingDetails`, `DAL_AppBillingDetails`, `Service.asmx.cs` (`InsertAppBillingDetails`), `ViewAppBillingDetails.aspx.cs`, `sp_InsertAppBilling`, `sp_InsertAppBilling_img`, `sp_InsertAppBilling_pdf`, `sp_ViewBillingDetails`, `sp_UpdateAppBillingDetails`.
- **Implementation**:
  - Models: `AppBillingDetails`, `AppBillingAttachment` in `app/models/phase22_features.py`.
  - Service: Claim submission with receipt images (`IMG`) and PDF documents (`PDF`), claim status transitions (`PENDING` -> `APPROVED` -> `PROCESSED`), finance approvals and auditing.
  - Endpoints: Mounted at `/api/v1/billing/claims`.

---

## 4. Physical Database Migrations

### Alembic Revision `f22a0c4d2201`
- **File**: `alembic/versions/f22a0c4d2201_phase_22_sales_exec_commissions_portals_billing.py`
- **Revises**: `e21a0c3d2101`
- **Tables Created**:
  1. `tbl_salesexcommission` (PK: `SalesCommissionId`)
  2. `tbl_locationheadcommission` (PK: `LocationHeadCommId`)
  3. `tbl_locationheadsalesexmap` (PK: `MapId`)
  4. `tbl_insurancecompanyportal` (PK: `tbl_Id`)
  5. `tbl_appbillingdetails` (PK: `BillingId`)
  6. `tbl_appbillingattachment` (PK: `AttachmentId`)
- **Upgrade/Downgrade**: Fully symmetric DDL definitions with explicit index creation and removal.
- **Current Table Count**: **110 physical tables** verified in `reliable_insurance_dev`.

---

## 5. API Endpoint Inventory (24 Endpoints Added)

### Sales Executive Commissions (`/api/v1/commissions/sales-executives`)
- `GET /grids` — List commission grids (filtered by sales executive, insurer, franchise, policy/product).
- `POST /grids` — Create commission grid entry (admin role required, duplicate check).
- `POST /lookup` — Lookup applicable commission rate for a policy transaction.
- `GET /grids/{commission_id}` — Get single commission grid entry.
- `PUT /grids/{commission_id}` — Update commission grid rates.
- `DELETE /grids/{commission_id}` — Soft delete commission grid.

### Location Head Commissions (`/api/v1/commissions/location-heads`)
- `GET /grids` — List Location Head override grids.
- `POST /grids` — Create Location Head override grid.
- `POST /lookup` — Lookup Location Head override rate.
- `POST /assignments` — Bulk assign Sales Executives to Location Head.
- `GET /sales-executives/{sales_ex_id}` — Get active Location Head for a Sales Executive.
- `GET /{location_head_id}/team` — List all Sales Executives reporting to Location Head.
- `GET /grids/{commission_id}` — Get single Location Head commission grid.
- `PUT /grids/{commission_id}` — Update Location Head commission grid.
- `DELETE /grids/{commission_id}` — Soft delete Location Head commission grid.

### Insurer Partner Portals (`/api/v1/masters/insurer-portals`)
- `GET /` — List registered insurer portals.
- `POST /` — Register insurer portal URL and credentials.
- `GET /{portal_id}` — Get single portal details.
- `PUT /{portal_id}` — Update insurer portal details.
- `DELETE /{portal_id}` — Soft delete insurer portal.

### App Billing Claims (`/api/v1/billing/claims`)
- `GET /` — List field expense reimbursement claims.
- `POST /` — Submit reimbursement claim with photo/pdf attachments.
- `GET /{billing_id}` — Get claim details and receipt attachments.
- `PATCH /{billing_id}/status` — Transition claim status (Approve / Reject / Process).

---

## 6. Verification & Test Evidence

### Test Suite Results
- Test file: `tests/test_phase22_features.py`
  - `test_sales_ex_commission_crud_and_rbac` — PASSED
  - `test_sales_ex_commission_lookup_priority` — PASSED
  - `test_location_head_commission_and_assignment_hierarchy` — PASSED
  - `test_insurer_portals_registry_lifecycle` — PASSED
  - `test_app_billing_claims_and_reimbursement_workflow` — PASSED
- Total test count: **443 tests passing** (438 baseline + 5 new integration tests). Zero regressions.

---

## 7. Safety Invariants Checklist

- [x] Legacy folder `./InsurancefinalNew_2026_09_23/` untouched, read-only, and untracked.
- [x] Zero connections/queries to production database `brahmainsurance` (all work strictly on `reliable_insurance_dev`).
- [x] Zero production credentials used.
- [x] Frozen business rule `LBR-069` (`UtilityService.enforce_overdue_cheque_locks`) untouched.
- [x] Working tree clean of staging, commits, or pushes.

---

## 8. Full Project Migration Ledger Update & Phase 23 Candidates

With Phase 22 complete, the following remaining operational areas are identified for Phase 23:
1. **HR Management & Workforce Masters**:
   - Organization master (`BLL_HROrganizatione`, `API_HROrganization`, `tbl_hrorganization`).
   - Department master (`BLL_HRdeparmentmaster`, `API_HRdeparmentmaster`, `tbl_hrdepartment`).
   - Facility / Branch equipment master (`BLL_HRfaciltitymaster`, `API_HRfaciltitymaster`, `tbl_hrfacility`).
   - Holiday calendar master (`BLL_HRholidaymaster`, `API_hrholidaymaster`, `tbl_hrholiday`).
   - Employee onboarding & HR employee details (`BLL_HREmployee`, `API_HREmployee`, `tbl_hremployee`).
2. **App Policy Premium Desk & Field Inward Processing**:
   - Mobile policy premium desk queue (`InsertAppPolicyPremiumDesk`, `sp_insertapppolicypremiumdesk`).
   - Daily MIS submission with policy documentation (`InsertAppMIS1`, `Sp_InsertAppMISEntry1`).
