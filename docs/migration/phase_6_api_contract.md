# Phase 6 — Quotation & Rating Engine FastAPI Contract (`phase_6_api_contract.md`)

**Repository:** `Reliable-Insurance-Backend`  
**Phase:** `6 — Quotation & Rating Engine (Stage A: API Contract Specification)`  
**Base Prefix:** `/api/v1/quotations`  
**Status:** COMPLETE

---

## 1. Design Principles & Non-Negotiable Rules

1. **Strict `Decimal` Arithmetic**: All monetary amounts, IDVs, rates, and percentages in Pydantic schemas (`app/schemas/quotation.py`) use `decimal.Decimal` (never `float`). Float inputs in JSON are rejected or parsed via string-to-Decimal validation without binary float precision loss.
2. **Evidence-Backed Legacy Parity**: Every endpoint maps directly to verified legacy Stored Procedures and WebForm/ASMX workflows documented in `phase_6_quotation_sp_mapping.md`.
3. **Hardened RBAC & Principal Scoping**: Every endpoint enforces `require_roles(...)` and `PrincipalContext` scoping as specified in `phase_6_quotation_access_matrix.md`.

---

## 2. REST API Endpoints (`/api/v1/quotations`)

### 2.1 Stateless Premium Calculation & Multi-Insurer Comparison

#### `POST /api/v1/quotations/calculate`
- **Roles**: `QUOTATION_CALCULATE_ROLES`
- **Purpose**: Performs a full deterministic motor rating calculation for a single insurer and vehicle category (`PVT`, `TwoWheeler`, `Public_GCV`, `Private_GCV`, `PublicGCV3W`, `PublicPCV3W`, `MISC-D`, `PassengerTaxi(PCV)`, `School_Bus`), returning every intermediate line item (`basic_od`, `gvw_loading`, `electrical_acc_od`, `non_electrical_acc_od`, `lpg_od`, `inbuilt_lpg_od`, `fiber_glass_od`, `geo_ext_od`, `imt23_loading`, `gross_od`, `own_premises_discount`, `anti_theft_discount`, `voluntary_discount`, `od_after_tariff_discount`, `od_discount_percent`, `od_discount_amount`, `od_after_company_discount`, `ncb_percent`, `ncb_amount`, `net_od_premium`, `zero_dep_premium`, `consumable_premium`, `engine_gearbox_premium`, `tyre_rim_premium`, `invoice_cover_premium`, `towing_charges`, `total_od_with_addons`, `basic_tp`, `passenger_ll`, `lpg_tp`, `geo_ext_tp`, `pa_owner_driver`, `ll_paid_driver`, `ll_cleaner`, `ll_coolie`, `pa_driver_cleaner`, `nfpp_amount`, `trailer_tp`, `total_tp_premium`, `net_premium`, `gst_amount`, `final_payable_premium`, `vehicle_age`, `base_idv`, `min_idv`, `max_idv`, `total_idv`, `is_declined`).

#### `POST /api/v1/quotations/compare`
- **Roles**: `QUOTATION_CALCULATE_ROLES`
- **Purpose**: Evaluates all eligible insurers for the requested vehicle category (`sp_SelectInsuranceCompanyByVehicleType`) and returns a side-by-side comparison array of `PremiumBreakdownResponse` objects (matching legacy WebForm 10-column insurer comparison sheets).

---

### 2.2 Self-Quotations (`tbl_app_quatationentry`)

#### `POST /api/v1/quotations/self`
- **Roles**: `QUOTATION_WRITE_ROLES`
- **Purpose**: Calculates (or accepts verified rating inputs), generates a canonical `SRQ...` quotation code (`Sp_GetQuotationCodeForSelfRequestedQuotation`), and persists a Self-Quotation record in `tbl_app_quatationentry` (`sp_InsertQuatationEntry1`).
- **Response**: `201 Created` → `SelfQuotationResponse` (including `quatation_id`, `title`, `ref_number`, full vehicle/coverage attributes, and calculated `premium_breakdown`).

#### `GET /api/v1/quotations/self`
- **Roles**: `QUOTATION_READ_ROLES`
- **Query Params**: `from_date`, `to_date`, `registration_no`, `customer_name`, `status`, `limit`, `offset`
- **Purpose**: Lists Self-Quotations scoped by `PrincipalContext` (`sp_ViewQuatationEntry`, `sp_ViewQuatationEntrySaleEx`, `sp_selectSelfQuotation`).

#### `GET /api/v1/quotations/self/{quotation_id}`
- **Roles**: `QUOTATION_READ_ROLES`
- **Purpose**: Retrieves a single Self-Quotation by `QuatationId` (`sp_SelectQuatationEntryById`), enforcing ownership scope (`403 Forbidden` if another agent's quotation, `404 Not Found` if non-existent).

---

### 2.3 Assisted Quotation Requests (`tbl_app_quotationrequest`, `tbl_insurancecompanyquotation`, `tbl_app_quotationremark`)

#### `POST /api/v1/quotations/requests`
- **Roles**: `QUOTATION_WRITE_ROLES`
- **Purpose**: Creates an Assisted Quotation Request in `tbl_app_quotationrequest` (`Sp_InsertQuotation1`), auto-generating `Title` (`Sp_GetQuotationCodeForPolicyEntry1`) if omitted, stamping `BranchId`, `AgentId`, `SalesEx_Id`, `UserRoleId`, `OtherAgentName`, and logging the initial remark in `tbl_app_quotationremark`.
- **Response**: `201 Created` → `QuotationRequestDetailResponse`

#### `GET /api/v1/quotations/requests`
- **Roles**: `QUOTATION_READ_ROLES`
- **Query Params**: `status`, `branch_id`, `registration_no`, `customer_name`, `limit`, `offset`
- **Purpose**: Lists Assisted Quotation Requests scoped by role, branch, and ownership (`Sp_SelectQuotation`, `Sp_selectQuotationbyQuotAdmin`, `Sp_selectQuotationbyQuotCo`).

#### `GET /api/v1/quotations/requests/{quotation_id}`
- **Roles**: `QUOTATION_READ_ROLES`
- **Purpose**: Fetches request header, active insurer quote options (`tbl_insurancecompanyquotation`), and remarks (`tbl_app_quotationremark`) (`Sp_SelectQuotationById1`, `Sp_SelectQuotationRemarks`).

#### `PUT /api/v1/quotations/requests/{quotation_id}`
- **Roles**: `QUOTATION_WRITE_ROLES`
- **Purpose**: Updates/resubmits an Assisted Quotation Request (`Sp_UpdateQuotation1`) and appends an optional remark to `tbl_app_quotationremark`.

#### `POST /api/v1/quotations/requests/{quotation_id}/attend`
- **Roles**: `QUOTATION_COORDINATOR_ROLES`
- **Purpose**: Claims/locks or releases an Assisted Quotation Request in the coordinator queue (`Sp_UpdateQuotationAttendStatus`).

#### `POST /api/v1/quotations/requests/{quotation_id}/status`
- **Roles**: `QUOTATION_COORDINATOR_ROLES`
- **Purpose**: Transitions request status (`Pending`, `Reverted`, `Resubmitted`, `Updated`, `Generated`) and logs a coordinator remark (`Sp_UpdateStatusForQuotation`).

#### `POST /api/v1/quotations/requests/{quotation_id}/quotes`
- **Roles**: `QUOTATION_COORDINATOR_ROLES`
- **Purpose**: Attaches one or more insurer quotation options (`tbl_insurancecompanyquotation`) via `Sp_InsertInsuranceCompanyQuotation` (soft-deleting replaced options if `replace_existing=True` via `Sp_DeleteInsuranceCompanyQuotation`) and transitions request `Status` to `'Generated'`.

#### `POST /api/v1/quotations/requests/{quotation_id}/select-quote`
- **Roles**: `QUOTATION_WRITE_ROLES`
- **Purpose**: Marks a specific `tbl_insurancecompanyquotation` option (`option_id`) as selected (`IsSelected = 1`) for policy issuance.

#### `GET /api/v1/quotations/requests/{quotation_id}/policy-prefill`
- **Roles**: `QUOTATION_READ_ROLES`
- **Purpose**: Returns the pre-filled Phase 7 Policy Proposal data (`Sp_GetQuotationDetailByQuotationCode` parity) for converting a generated quotation into a policy transaction (`tbl_transaction` / `tbl_transactionappnew`).

#### `DELETE /api/v1/quotations/requests/{quotation_id}`
- **Roles**: `QUOTATION_WRITE_ROLES`
- **Purpose**: Soft-deletes an Assisted Quotation Request (`Sp_DeleteQuotation`: `IsDeleted = 1`).

---

## 3. Error Codes & Status Semantics

| HTTP Status | Condition |
|---|---|
| `200 OK` | Calculation, comparison, read, update, status transition, or soft-delete succeeded |
| `201 Created` | Self-quotation or Assisted Quotation Request created |
| `401 Unauthorized` | Missing or invalid JWT bearer token |
| `403 Forbidden` | Role not in permitted role set, or principal attempting to access/modify another agent's/branch's quotation |
| `404 Not Found` | Quotation ID, Variant ID, or Insurer Quote Option ID does not exist (or is soft-deleted) |
| `409 Conflict` | Duplicate `Title` (`QuotationCode`), or coordinator attempting to attend a request already attended by another coordinator |
| `422 Unprocessable Entity` | Invalid NCB slab, IDV outside ±15% band, invalid vehicle category, negative premium input, or invalid state transition |
