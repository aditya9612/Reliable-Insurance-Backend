# Phase 6 — Quotation & Rating Role, Branch & Principal Access Matrix (`phase_6_quotation_access_matrix.md`)

**Repository:** `Reliable-Insurance-Backend`  
**Phase:** `6 — Quotation & Rating Engine (Stage A: Role, Branch & Principal Access Matrix)`  
**Database Reference:** Legacy `brahmainsurance` (`tbl_userrole` 27 active roles) & Phase 5F/5G Verified RBAC Catalog  
**Status:** COMPLETE

---

## 1. Executive Summary

This document defines the **evidence-backed Role, Branch, and Principal Ownership Matrix** for all Quotation & Rating endpoints in Phase 6. All authorization rules are derived directly from:
1. Legacy WebForms role dispatch (`SelfQuotationRequest*.aspx.cs`, `QuotationRequestEntry*.aspx.cs`, `ViewRequestedQuotations*.aspx.cs`, `Adm_UpdateAppODDiscount*.aspx.cs`)
2. Legacy ASMX WebMethods (`Admin.asmx`, `Agent.asmx`, `SalesExecutive.asmx`, `Clerk.asmx`, `PolicyCordinator.asmx`, `Account.asmx`)
3. Legacy Stored Procedures (`sp_selectSelfQuotation`, `sp_ViewQuatationEntry`, `sp_ViewQuatationEntrySaleEx`, `Sp_SelectQuotation`, `Sp_GetQuotationdata`, `Sp_selectQuotationbyQuotAdmin`, `Sp_selectQuotationbyQuotCo`, `Sp_selectQuotationbyOPR`)
4. Phase 5F / 5G verified `PrincipalContext` and `RoleName` catalog (`app/core/rbac.py`).

---

## 2. Role Group Definitions for Phase 6 (`app/core/rbac.py`)

| Role Constant | Included Verified Roles (`RoleName` / `RoleId`) | Purpose |
|---|---|---|
| `QUOTATION_CALCULATE_ROLES` | `OWNER` (`1`), `ADMIN` (`2`), `AGENT` (`4`), `RELATIONSHIP MANAGER` (`5`), `OPERATOR` (`6`), `FRANCHISE` (`9`), `INSURANCE COMPANY` (`13`), `QUOT CO-ORDINATOR` (`14`), `FRANCHISE AGENT` (`16`), `OPERATOR HEAD` (`19`), `HR HEAD/MANAGER` (`22`), `LOCATION HEAD` (`24`), `TELE SALES EXECUTIVE` (`25`), `IT SUPPORT` (`28`), `TRAINEE` (`30`) | Stateless premium calculation, IDV band calculation, age calculation, and multi-insurer comparison |
| `QUOTATION_WRITE_ROLES` | `OWNER` (`1`), `ADMIN` (`2`), `AGENT` (`4`), `RELATIONSHIP MANAGER` (`5`), `OPERATOR` (`6`), `FRANCHISE` (`9`), `QUOT CO-ORDINATOR` (`14`), `FRANCHISE AGENT` (`16`), `OPERATOR HEAD` (`19`), `LOCATION HEAD` (`24`), `TELE SALES EXECUTIVE` (`25`), `IT SUPPORT` (`28`) | Creating & updating Self-Quotations (`tbl_app_quatationentry`) and Assisted Quotation Requests (`tbl_app_quotationrequest`) |
| `QUOTATION_COORDINATOR_ROLES` | `OWNER` (`1`), `ADMIN` (`2`), `OPERATOR` (`6`), `QUOT CO-ORDINATOR` (`14`), `OPERATOR HEAD` (`19`), `IT SUPPORT` (`28`) | Attending requests (`AttendStatus`), reverting requests (`Status='Reverted'`), generating insurer quotes (`tbl_insurancecompanyquotation`, `Status='Generated'`), and reopening requests |
| `QUOTATION_READ_ROLES` | All `QUOTATION_CALCULATE_ROLES` + `ACCOUNT` (`3`), `POLICY CO-ORDINATOR` (`8`), `DATA ENTRY` (`11`), `RENEWAL` (`12`), `INSPECTION` (`15`), `RECOVERY` (`17`), `CLAIM` (`18`), ` DEALER` (`20`), `CANCELATION` (`26`), `endorsement` (`27`) | Viewing/searching quotations within the principal's permitted branch/ownership scope |
| `RATING_ADMIN_ROLES` | `OWNER` (`1`), `ADMIN` (`2`), `QUOT CO-ORDINATOR` (`14`), `OPERATOR HEAD` (`19`), `IT SUPPORT` (`28`) | Viewing/managing OD discount grids (`tbl_app_oddiscountnew`, `tbl_app_oddiscountnew_gcv`), Zero-Dep rates (`tbl_zerodep*`), and self-discount rules (`tbl_selfdiscount`) |

---

## 3. Endpoint-by-Endpoint Role, Branch & Ownership Matrix

| Operation | HTTP Endpoint | Permitted Roles | Branch Scope (`BranchId`) | Principal Ownership Scope (`AgentId` / `SalesExId` / `UserId`) |
|---|---|---|---|---|
| **Calculate Premium / Multi-Insurer Compare** | `POST /api/v1/quotations/calculate`<br>`POST /api/v1/quotations/compare` | `QUOTATION_CALCULATE_ROLES` | Unrestricted (Tariffs are global; optional `branch_id` used only if `tbl_selfdiscount` is queried) | Any authenticated principal in `QUOTATION_CALCULATE_ROLES` |
| **Create Self-Quotation** | `POST /api/v1/quotations/self` | `QUOTATION_WRITE_ROLES` | Inherited from `principal.branch_id` | - `AGENT` (`4`) / `FRANCHISE AGENT` (`16`): stamps `AgentId = principal.user_id`, `SaleExId = principal.sales_ex_id or 0`, `UserRoleId = role_id`<br>- `RELATIONSHIP MANAGER` (`5`) / `LOCATION HEAD` (`24`) / `TELE SALES EXECUTIVE` (`25`): stamps `SaleExId = principal.user_id`, `AgentId = payload.agent_id or principal.user_id`, `UserRoleId = role_id`<br>- `ADMIN`/`OWNER`/`OPERATOR`/`QUOT CO-ORDINATOR`: may specify `agent_id` & `sale_ex_id` or default to `principal.user_id` |
| **Get / List Self-Quotations** | `GET /api/v1/quotations/self`<br>`GET /api/v1/quotations/self/{quotation_id}` | `QUOTATION_READ_ROLES` | Enforced via principal scope | - `AGENT` (`4`) / `FRANCHISE AGENT` (`16`): **OWN ONLY** (`AgentId == principal.user_id`) — matches `sp_ViewQuatationEntry` & `sp_selectSelfQuotation`<br>- `RELATIONSHIP MANAGER` (`5`) / `LOCATION HEAD` (`24`) / `TELE SALES EXECUTIVE` (`25`): **ASSIGNED/OWN ONLY** (`SaleExId == principal.user_id OR AgentId == principal.user_id`) — matches `sp_ViewQuatationEntrySaleEx`<br>- `FRANCHISE` (`9`): `SaleExId == principal.user_id OR AgentId == principal.user_id`<br>- Global/Coordinator/Backoffice (`1, 2, 3, 6, 8, 11, 12, 14, 15, 17, 18, 19, 26, 27, 28`): Global read |
| **Create Assisted Quotation Request** | `POST /api/v1/quotations/requests` | `QUOTATION_WRITE_ROLES` | Stamps `BranchId = principal.branch_id` (or payload `branch_id` for global roles) | Matches `Sp_InsertQuotation1`:<br>- `AGENT` (`4`): `AgentId = principal.user_id`, `SalesEx_Id = principal.sales_ex_id or 0`, `OtherAgentName = 'Agent'`, `UserRoleId = 4`<br>- `RELATIONSHIP MANAGER` (`5`): `AgentId = payload.agent_id or principal.user_id`, `SalesEx_Id = principal.user_id`, `OtherAgentName = 'Agent'` (if for agent) or `'Self'`/`'Direct'`, `UserRoleId = 5`<br>- `LOCATION HEAD` (`24`): `OtherAgentName = 'L.Head'` (or `'Agent'`), `UserRoleId = 24`<br>- `FRANCHISE` (`9`): `OtherAgentName = 'Franchise'` (or `'Franchise Agent'`), `UserRoleId = 9`<br>- `FRANCHISE AGENT` (`16`): `AgentId = principal.user_id`, `SalesEx_Id = principal.sales_ex_id or 0`, `OtherAgentName = 'Franchise Agent'`, `UserRoleId = 16`<br>- `TELE SALES EXECUTIVE` (`25`): `OtherAgentName = 'Tele Sales'`, `UserRoleId = 25` |
| **Get / List Assisted Quotation Requests** | `GET /api/v1/quotations/requests`<br>`GET /api/v1/quotations/requests/{quotation_id}` | `QUOTATION_READ_ROLES` | Branch-scoped for branch-bound roles; global for `QUOTATION_COORDINATOR_ROLES` | Matches `Sp_SelectQuotation` & `Sp_GetQuotationdata`:<br>- `AGENT` (`4`): `AgentId == principal.user_id`<br>- `FRANCHISE AGENT` (`16`): `AgentId == principal.user_id`<br>- `RELATIONSHIP MANAGER` (`5`) / `LOCATION HEAD` (`24`) / `TELE SALES EXECUTIVE` (`25`): `SalesEx_Id == principal.user_id OR AgentId == principal.user_id OR UserId == principal.user_id`<br>- `FRANCHISE` (`9`): `SalesEx_Id == principal.user_id OR AgentId == principal.user_id OR UserId == principal.user_id`<br>- Coordinator / Operator / Admin (`1, 2, 3, 6, 8, 11, 12, 14, 15, 17, 18, 19, 26, 27, 28`): All active requests (`IsDeleted == 0`), with optional `branch_id` filter |
| **Update / Resubmit Quotation Request** | `PUT /api/v1/quotations/requests/{quotation_id}` | `QUOTATION_WRITE_ROLES` | Must match principal's ownership/branch scope | - Requester (`Agent` / `RM` / `Franchise` / `Location Head`) can update/resubmit their own request when `Status IN ('Pending', 'Reverted', 'Resubmitted', 'Updated')` → transitions to `'Resubmitted'` (if was `'Reverted'`) or `'Updated'`.<br>- `QUOTATION_COORDINATOR_ROLES` can update any active request. |
| **Attend Quotation Request** | `POST /api/v1/quotations/requests/{quotation_id}/attend` | `QUOTATION_COORDINATOR_ROLES` | Global | Matches `Sp_UpdateQuotationAttendStatus`: sets `AttendStatus = 1`, `AttendBy = principal.user_id`. Prevents another coordinator from hijacking an already-attended request (`AttendStatus == 1` and `AttendBy != principal.user_id`) unless `ADMIN` / `OWNER` / `OPERATOR HEAD`. |
| **Revert / Reopen / Status Transition** | `POST /api/v1/quotations/requests/{quotation_id}/status` | `QUOTATION_COORDINATOR_ROLES` | Global | Matches `Sp_UpdateStatusForQuotation`: transitions `Status` to `'Reverted'`, `'Pending'`, or `'Generated'`, and appends an audit trail entry in `tbl_app_quotationremark`. |
| **Upload / Generate Insurer Quote Options** | `POST /api/v1/quotations/requests/{quotation_id}/quotes` | `QUOTATION_COORDINATOR_ROLES` | Global | Matches `Sp_DeleteInsuranceCompanyQuotation` + `Sp_InsertInsuranceCompanyQuotation` + `Sp_UpdateStatusForQuotation('Generated')`. Replaces/adds insurer quote options in `tbl_insurancecompanyquotation` and marks request `'Generated'`. |
| **Select Insurer Quote Option & Convert to Policy Payload** | `POST /api/v1/quotations/requests/{quotation_id}/select-quote`<br>`GET /api/v1/quotations/{quotation_id}/policy-prefill` | `QUOTATION_WRITE_ROLES` | Must match principal's ownership/branch scope | Allows the owning Agent/RM/Franchise or Coordinator/Operator to select the winning `tbl_insurancecompanyquotation` option (`IsSelected = 1`) and retrieve the pre-populated Phase 7 Policy Proposal payload (`QuotationCode`, `VehicleTypeId`, `MakeId`, `ModelId`, `VariantId`, `InsuranceCompanyId`, `PremimumAmt`, `IdvAmount`, `RegistrationNo`, `AgentId`, `SalesEx_Id`, `BranchId`). |
| **Soft-Delete Quotation Request** | `DELETE /api/v1/quotations/requests/{quotation_id}` | `QUOTATION_WRITE_ROLES` | Must match principal's ownership/branch scope | Matches `Sp_DeleteQuotation`: sets `IsDeleted = 1, ModifiedBy = principal.user_id, ModifiedDate = NOW()`. Agents can only delete their own `'Pending'` requests; `QUOTATION_COORDINATOR_ROLES` can soft-delete any request. |

---

## 4. Disallowed Roles (Explicit `403 Forbidden`)

The following legacy roles have **NO** write/create access to Quotations:
- `CUSTOMER` (`7`)
- `SURVEYOR` (`23`)
- `UNASSIGNED` (`21`)
- Read-only backoffice roles (`ACCOUNT` `3`, `POLICY CO-ORDINATOR` `8`, `DATA ENTRY` `11`, `RENEWAL` `12`, `INSPECTION` `15`, `RECOVERY` `17`, `CLAIM` `18`, ` DEALER` `20`, `CANCELATION` `26`, `endorsement` `27`) — permitted `GET` read access within scope, denied `POST`/`PUT`/`DELETE` write access (`403 Forbidden`).
