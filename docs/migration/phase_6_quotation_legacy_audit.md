# Phase 6 — Quotation & Rating Engine: Legacy Audit

**Repository**: `Reliable-Insurance-Backend`  
**Phase**: `6 — Quotation & Rating Engine (Stage A: Legacy Audit)`  
**Reference Database**: `brahmainsurance` (Read-Only Introspection)  
**Target Runtime Database**: `localhost:3306/reliable_insurance_dev`  
**Status**: **COMPLETE**

---

## 1. Executive Summary

A full read-only audit of the legacy C#/.NET 4.0 codebase (`Insurance`, `BLL`, `DAL`, `API`) and the MySQL 8.0 reference database (`brahmainsurance`) reveals that the legacy system implements **two distinct operational quotation workflows** backed by a shared **Motor Tariff & Discount Rating Engine**:

1. **Subsystem A — Self-Quotation & Instant Motor Rating Engine (`tbl_app_quatationentry`)**:
   - Used by Clerks, Operators, Agents, Sales Executives (Relationship Managers), and Location Heads via WebForms (`Clerk/SelfQuotationFirstPage.aspx`, `Clerk/SelfQuotationRequest*.aspx`) and the Mobile App (`Service.asmx`).
   - Performs deterministic, real-time motor premium calculation (Own Damage Part A + Third-Party Liability Part B + Add-Ons + NCB + GST = Final Payable Premium) using tariff/rate tables (`tbl_quot_damagepremium`, `tbl_quot_liabilitypremium`, `tbl_app_oddiscountnew`, `tbl_app_oddiscountnew_gcv`, `tbl_appoddiscount`, `tbl_zerodep*`, `tbl_addonextraamt`, `tbl_patoownerdriver`, `tbl_insurancecompanywisetowingchanges`, `tbl_app_*_cc_rate`).
   - Persists the itemized 58-column quotation breakdown into **`tbl_app_quatationentry`** (3,135 production rows) via `Sp_InsertAppQuotationEntry`.

2. **Subsystem B — Assisted / Coordinator Quotation Request Workflow (`tbl_app_quotationrequest` + `tbl_insurancecompanyquotation`)**:
   - Used when an Agent, Sales Executive, Franchise, or Location Head requests a multi-insurer quotation from the back-office Quotation Coordinator / Operator team (`Clerk/QuatationRequestSendorPending.aspx`, `Clerk/ViewQuotationAppTransction.aspx`, `Service.asmx/InsertAppQuotationRequest`).
   - Stores the request header in **`tbl_app_quotationrequest`** (1,908 production rows), insurer quote options/files in **`tbl_insurancecompanyquotation`** (2,952 production rows), and audit remarks in **`tbl_app_quotationremark`** (33 rows).
   - Tracks lifecycle states: **Pending (`IsQuotationGenerate=0, AttendedBy IS NULL`)** $\rightarrow$ **Attended (`AttendedBy IS NOT NULL`)** $\rightarrow$ **Reverted (`isPendingRevert=1`)** / **Resubmitted (`isPendingRevert=2`)** $\rightarrow$ **Generated (`IsQuotationGenerate=1`)** $\rightarrow$ **Read/Converted (`ReadStatus=1`)** or **Cancelled/Deleted (`isdeleted=1`)**.

3. **Out-of-Scope Claim Estimate Table (`tbl_claim_quotation`)**:
   - `tbl_claim_quotation` (0 rows) and `tbl_claim_quotation_img` (0 rows) belong to the motor claims repair estimate module (`BLL_Claims.cs`) and are not part of policy underwriting quotation or rating.

---

## 2. Complete Legacy Entry Point Inventory

### 2.1 WebForms Entry Points (`Insurance/Clerk/*.aspx.cs`)

| # | Legacy WebForm File | Business Purpose | Key BLL / DAL / SP Invocations |
|---|---|---|---|
| 1 | `Clerk/SelfQuotationFirstPage.aspx.cs` | Entry dispatcher for Web Self-Quotation. Selects Vehicle Type (`sp_Quot_Vehicle_Type`), Product Type (`sp_Quot_Product_Type`), and Registration No, then redirects based on `Veh_Type_ID`: `2` $\rightarrow$ `SelfQuotationRequest.aspx`, `5` $\rightarrow$ `SelfQuotationRequestMISC_D.aspx`, `7` $\rightarrow$ `SelfQuotationRequest3_W_GCV.aspx`, `8` $\rightarrow$ `SelfQuotationRequest3_W_PCV.aspx`. | `BLL_VehicleType.SelectVehicleType_Quotation`, `BLL_ProductType.SelectProductType_Quotation` |
| 2 | `Clerk/SelfQuotationRequest.aspx.cs` | Instant rating calculator & quotation generator for **Public GCV (`Veh_Type_ID = 2`, `"Public_GCV"`)**. Computes Part A (OD + GVW > 12000 loading - OD Discount - NCB + IMT23 + Towing), Part B (TP + PA Owner + LL Paid Driver + PA Paid Driver + Cleaner + Non-fare Passengers), Dual-Rate GST (12% on basic TP, 18% on OD & other TP), and saves to `tbl_app_quatationentry`. | `sp_selectRTOfromRegistration`, `sp_SelectRTOByID`, `sp_SelectMgfyearOfyearmonth`, `sp_SelectIDVDetailsForGCV`, `sp_quot_damagepremium`, `sp_quot_liabilitypremium`, `sp_AppSelectPAToOwnerDriver`, `Sp_Select_Insurancecompanywisetowingchanges`, `sp_Quot_ODDiscFromCompany`, `sp_GenrateQuatationCode`, `Sp_GetQuotationCodeForSelfRequestedQuotation`, `Sp_InsertAppQuotationEntry`, `sp_Quot_SelectForPDF` |
| 3 | `Clerk/SelfQuotationRequest3_W_GCV.aspx.cs` | Instant rating calculator & quotation generator for **3-Wheeler GCV (`Veh_Type_ID = 7`, `"PublicGCV3W"`)**. Uses `TPrisk = 4492`, `Passengers = 125 * count`, `Cleaner = 50 * count`, `Benefit = 60 * count`, `TPPD = 150` (deduction), and Dual-Rate GST (12% on `TPrisk`, 18% on rest). | `sp_quot_damagepremium("PublicGCV3W")`, `sp_AppSelectPAToOwnerDriver`, `sp_Quot_ODDiscFromCompany("THREE_WHEELER")`, `Sp_InsertAppQuotationEntry` |
| 4 | `Clerk/SelfQuotationRequest3_W_PCV.aspx.cs` | Instant rating calculator & quotation generator for **3-Wheeler PCV (`Veh_Type_ID = 8`, `"PublicPCV3W"`)**. Hardcodes `Zone = "C"`, `TPrisk = 6181`, `Passengers = 1241 * count`, `Cleaner = 50 * count`, `Benefit = 60 * count`, `TPPD = 150` (deduction), and Single-Rate 18% GST. | `sp_quot_damagepremium("PublicPCV3W")`, `sp_AppSelectPAToOwnerDriver`, `sp_Quot_ODDiscFromCompany("THREE_WHEELER")`, `Sp_InsertAppQuotationEntry` |
| 5 | `Clerk/SelfQuotationRequestMISC_D.aspx.cs` | Instant rating calculator & quotation generator for **Miscellaneous-D (`Veh_Type_ID = 5`, `"MISC-D"`)**. Includes Electrical Accessories (`4%`), CNG Fuel Kit (`* 4` OD + `60` TP), Voluntary Excess, ZeroDep (`IDV * rate / 100`), IMT-23 (`15%`), Anti-theft, Automobile Assoc., TPPD (`150`), and Single-Rate 18% GST. | `sp_quot_damagepremium("MISC-D")`, `sp_quot_liabilitypremium("MISC-D")`, `sp_AppSelectPAToOwnerDriver`, `sp_Quot_ODDiscFromCompany("MISC_D")`, `Sp_InsertAppQuotationEntry` |
| 6 | `Clerk/QuatationRequestSendorPending.aspx.cs` | Portal screen for Sales Executives (`UserRoleId=5`) and Location Heads (`UserRoleId=24`) to submit new assisted quotation requests (`InsertAppQuotationRequest`) and view generated/pending requests (`Sp_GetQuotationdata`, `Sp_SelectQuotation`, `sp_selectSelfQuotation`). | `InsertAppQuotationRequest`, `Sp_GetQuotationdata`, `Sp_SelectQuotation`, `sp_selectSelfQuotation`, `sp_SelectQuotationReqDetails`, `sp_UpdateClearSelfQutation` |
| 7 | `Clerk/ViewQuotationAppTransction.aspx.cs` | Back-office Quotation Coordinator (`UserRoleId=14`), Operator (`UserRoleId=6`), and Admin (`UserRoleId=2`) workbench to attend requests (`sp_UpdateAppAttendQuotation1`), upload insurer quotations (`sp_insertInsuranceComponyQuotation`), mark generated (`sp_UpdateAppQuotationRequest`), or revert with remark (`sp_UpdateAppQuotationReopen`, `sp_insert_app_quotationremark`). | `Sp_selectQuotationRequest`, `Sp_selectQuotationbyQuotAdmin`, `Sp_selectQuotationbyQuotCo`, `Sp_selectQuotationbyOPR`, `sp_UpdateAppAttendQuotation1`, `sp_insertInsuranceComponyQuotation`, `sp_UpdateAppQuotationRequest`, `sp_UpdateAppQuotationReopen`, `sp_insert_app_quotationremark` |
| 8 | `Clerk/QuatationRequestPendingReport.aspx.cs` | Coordinator/Admin report of pending & attended quotation requests with cancel capability (`sp_UpdateAppCancelQuotation`). | `Sp_selectQuotationbyQuotAdmin`, `Sp_selectQuotationbyQuotCo`, `Sp_selectQuotationbyOPR`, `sp_UpdateAppCancelQuotation` |
| 9 | `Clerk/QuatationRequestReport.aspx.cs` | Historical report of attended/generated quotation requests (`sp_ReportQuotationRequest`). | `sp_ReportQuotationRequest`, `sp_AppQuotationRequestProcess` |
| 10 | `Clerk/Rpt_Quotationreportvehno.aspx.cs` | Search self-quotations by date range or vehicle registration number (`sp_selectQuotationVehRpt`). | `sp_selectQuotationVehRpt` |
| 11 | `Clerk/Adm_UpdateAppODDiscount.aspx.cs` & `adm_AppOddiscountRpt.aspx.cs` | Admin configuration of model/fuel/NCB/cluster/ZeroDep age-slab (`N`, `Zero`..`Sixteen`) OD discounts in `tbl_app_oddiscountnew`. Enforces `if (compId != 3) ClusterId = 0`. | `sp_AppOddiscountRpt`, `sp_UpdateAPPODDiscountRpt`, `sp_AppUpdateODdiscountRpt` |
| 12 | `Clerk/adm_OdDiscount.aspx.cs` | Admin configuration of simplified age-band OD discounts (`NewVehicle`, `ZerotoFive`, `fivetoTen`, `Greaterthen10`) in `tbl_appoddiscount`. | `Sp_AppOdDiscount` |
| 13 | `Clerk/adm_AddOnExtraAmt.aspx.cs` & `adm_AddonRateforRelianceComp.aspx.cs` | Admin configuration of ZeroDep / Add-On rates (`NillDep`, `SecurePlus`, `SPremium`) in `tbl_addonextraamt` and `tbl_zerodepnewaddonrate`. | `sp_AddOnRateforReliableComp`, `sp_OperationZerodepForSegment`, `Sp_ZeroDep` |
| 14 | `Clerk/adm_SelfDiscount.aspx.cs` | Admin configuration of branch & reference-type `SelfDiscount` percentages in `tbl_selfdiscount`. | `sp_insertSelfDiscount`, `Sp_SelectSelfDiscountForTransaction` |

---

### 2.2 ASMX Web Service Entry Points (`Insurance/Service.asmx.cs`)

| # | WebMethod Name | Purpose | Underlying Stored Procedure |
|---|---|---|---|
| 1 | `InsertAppQuotationEntry` (2 overloads) | Persists a calculated self-quotation into `tbl_app_quatationentry` (and optionally uploads PDF to `tbl_app_requestedquotationfile`). | `Sp_InsertAppQuotationEntry`, `sp_insert_app_requestedquotationfile` |
| 2 | `SelectQuatationEntry` | Fetches a single self-quotation by `QuatationId`. | `sp_SelectQuatationEntry` |
| 3 | `ViewQuatationEntryAgent` | Lists self-quotations for an `AgentId` within a date range. | `sp_ViewQuatationEntry` |
| 4 | `ViewQuatationEntrySaleEx` | Lists self-quotations for a `SaleExId` within a date range. | `sp_ViewQuatationEntrySaleEx` |
| 5 | `GenrateQuatationCode` | Generates next `QuatationCode` from `tbl_app_quatationentry` `AUTO_INCREMENT`. | `sp_GenrateQuatationCode` |
| 6 | `GetQuotationCodeForSelfQuotation` | Generates formatted self-quotation code (`SRQ...`). | `Sp_GetQuotationCodeForSelfRequestedQuotation` |
| 7 | `CheckQuatationTitle` | Checks uniqueness of `tbl_app_quatationentry.Title`. | `sp_CheckQuatationTitle` |
| 8 | `UpdateClearSelfQutation` | Soft-deletes a self-quotation (`Opr='Quatation'`) or quotation request (`Opr='GETData'`). | `sp_UpdateClearSelfQutation` |
| 9 | `SelectIDVDetails` | Fetches default variant IDV (`ExMumbai_Model_Price`) from `tbl_vehicle_variants`. | `sp_SelectIDVDetails` |
| 10 | `SelectIDVDetailsForGCV` | Fetches GCV IDV with (`Yes`) or without (`No` -> `Body + Chasis`) body price. | `sp_SelectIDVDetailsForGCV` |
| 11 | `SelectAppDiscWithFueltype` | Looks up age-band (`N`, `0`..`16`) OD discount from `tbl_app_oddiscountnew`. | `sp_SelectAppDiscWithFueltype` |
| 12 | `SelectAppDiscWithFueltypeGCV` | Looks up age-band (`N`, `0`..`16`) GCV OD discount from `tbl_app_oddiscountnew_gcv`. | `sp_SelectAppDiscWithFueltypeGCV` |
| 13 | `SelectAppDiscDiclineOrNot` | Checks if a Make/Model/Fuel/Company combination is marked `Decline=1`. | `sp_SelectAppDiscDiclineOrNot` |
| 14 | `SelectZeroDep` / `SelectZeroDepSegmentwise` / `SelectZeroDepModelIdwise` / `SelectZeroDepExtraAmount` / `SelectAddOnNEW` | Looks up `NillDep`, `SecurePlus`, `SPremium`, `NO` add-on rates across the 4 ZeroDep tables. | `sp_SelectZeroDep`, `sp_SelectZeroDepsegmentwise`, `sp_selectZeroDepModelIdWise`, `sp_SelectZeroDepExtraAmount`, `sp_SelectZeroDepMultiAddOn_New` |
| 15 | `AppSelectTPRateForTwoWheeler` | Looks up 2-Wheeler TP rate and basic rate by `Veh_Type_ID`, `Age`, `CCValue`. | `sp_AppSelectTPRateForTwoWheeler` |
| 16 | `AppSelectTPRateForPCV` | Looks up PCV TP rate, basic rate, and per-passenger rate by `Veh_Type_ID`, `Age`, `CCValue`. | `sp_AppSelectTPRateForPCV` |
| 17 | `AppSelectTPRateForBUS` | Looks up Bus TP rate, per-passenger rate, and OD discount by `Veh_Type_ID`, `Age`, `Bus_Type`. | `sp_AppSelectTPRateForBUS` |
| 18 | `AppSelectTPRateForThreeWheeler` | Looks up 3-Wheeler TP rate, basic rate, and per-passenger rate by `Veh_Type_ID`, `Age`. | `sp_AppSelectTPRateForThreeWheeler` |
| 19 | `AppSelectPAtoOwnerDriver` | Looks up insurer-specific PA to Owner-Driver rate from `tbl_patoownerdriver`. | `sp_AppSelectPAToOwnerDriver` |
| 20 | `SelectTowingChargesByCompanyId` | Looks up insurer-specific towing charge rate for a selected coverage limit. | `Sp_Select_Insurancecompanywisetowingchanges` |
| 21 | `InsertAppQuotationRequest` | Creates an assisted quotation request in `tbl_app_quotationrequest` + images/PDFs. | `InsertAppQuotationRequest`, `sp_InsertQuotation_Img`, `sp_InsertQuotation_PDF` |
| 22 | `UpdateQuotRequest` / `UpdateQuotRequestNew` | Updates/resubmits an assisted quotation request (`isPendingRevert = 2`). | `Sp_UpdateAppQuotReq`, `Sp_UpdateAppQuotReqNew` |
| 23 | `ReopenQuotationRequest` | Fetches quotation request details for reopening/editing. | `Sp_ReopenQuotRequest` |
| 24 | `SelectQuotation` | Lists pending assisted quotation requests for an Agent, SalesEx, Franchise, or Franchise Agent. | `Sp_SelectQuotation` |
| 25 | `GetQuotationData` | Lists generated insurer quotation options for an Agent, SalesEx, Location Head, Franchise, or Franchise Agent. | `Sp_GetQuotationdata` |
| 26 | `GetDataForPolicyEntry` | Fetches quotation request + insurer option + resolved master IDs for conversion to a policy proposal. | `sp_getDataForPolicyEntry` |
| 27 | `GetQuotationCodeForManualPolicyEntry1` / `GetQuotationCodeForManualPolicyEntry` | Generates role-prefixed `QuatationCode` (`Q...`, `QS...`, `QF...`, `QH...`, `QI...`, `QO...`) for policy conversion. | `Sp_GetQuotationCodeForPolicyEntry1`, `Sp_GetQuotationCodeForPolicyEntry` |

---

## 3. Physical Database Tables & Legacy Schema Quirks

### 3.1 Core Quotation Operational Tables

| Table Name | Prod Rows | PK | Purpose | Key Schema Quirks |
|---|---|---|---|---|
| `tbl_app_quatationentry` | 3,135 | `QuatationId` | Stores calculated Self-Quotations with full Part A, Part B, GST, and Final Premium breakdown (58 columns). | Spelling is `quatation` (with `a`). All monetary columns (`IDV`, `OwnDamagePremium`, `OD`, `BasicPremium`, `LiabilityPremium`, `AtotalOwnDamPremium`, `BtotalLiabilityPremium`, `TotalPremium`, `GST18`, `finalPrmium`) are stored as `VARCHAR(255)` except `BodyPrice` and `ChassisPrice` (`DOUBLE NOT NULL`). Has `UNIQUE KEY Title (Title(200))`. Soft-delete `isdeleted` is `VARCHAR(255)` (`'0'`/`'1'`). |
| `tbl_app_quotationrequest` | 1,908 | `QuatationId` | Stores Assisted Quotation Requests submitted to Coordinators. | `InsuranceCompanyId` (`VARCHAR(255)`) can hold a single ID or comma-separated insurer IDs. `VehicleType` and `policytype` store either numeric IDs as strings or names depending on caller. `isdeleted` is `INT(11) NOT NULL DEFAULT 0`. `IsQuotationGenerate` is `INT(10) UNSIGNED` (`0`=Pending, `1`=Generated). `isPendingRevert` (`0`=Normal, `1`=Reverted by Coordinator, `2`=Resubmitted by Agent). |
| `tbl_insurancecompanyquotation` | 2,952 | `QuotationId` | Stores individual insurer quotation files/options uploaded by a Coordinator for a `tbl_app_quotationrequest` (`TransctionId = QuatationId`). | Foreign key column is misspelled `TransctionId` (referencing `tbl_app_quotationrequest.QuatationId`). `isdeleted` is `VARCHAR(255) NOT NULL`. |
| `tbl_app_quotationremark` | 33 | `QuatRemarkId` | Audit trail of remarks exchanged between Coordinator and Requester on a `QuatationId`. | `isdeleted` is `INT(11) DEFAULT NULL`. |
| `tbl_app_requestedquotationfile` | 1,569 | `Id` | Links generated PDF files to `tbl_app_quatationentry.QuatationId`. | `IsDelete` is `INT(11) DEFAULT 0`. |

### 3.2 Motor Tariff & Rating Master Tables

| Table Name | Prod Rows | PK | Purpose |
|---|---|---|---|
| `tbl_quot_damagepremium` | 216 | `Id` | Basic Own Damage (OD) tariff percentage rates (`OD_premium_Azone`, `OD_premium_Bzone`, `OD_premium_Czone`) by `Company_Type` (`PVT`, `Public_GCV`, `Private_GCV`, `PassengerTaxi(PCV)`, `School_Bus`, `PublicGCV3W`, `TwoWheeler`, `PublicPCV3W`, `Misc-D`), `fromCubicCapacity`..`toCubicCapacity`, and `Age` (`0.0`..`11.0`). |
| `tbl_quot_liabilitypremium` | 28 | `Id` | Basic Third-Party (TP) liability tariff amounts (`Premium`) by `Company_Type`, `UNIT` (`CC` or `Weight`), and `fromunit`..`tounit`. |
| `tbl_app_oddiscountnew` | 29,527 | `AppODDiscountId` | Granular OD discount percentage grid by `MakeID`, `Model_ID`, `InsuranceCompanyId`, `Fueltypeid`, `BusinessTypeId`, `NCB`, `ClusterId`, `ZeroDep`, `PRVDetails`, `Decline`, and age columns (`N`, `Zero`, `One`, ..., `thriteen`, ..., `Sixteen`). |
| `tbl_app_oddiscountnew_gcv` | 785 | `AppODDiscountId` | GCV-specific age-band OD discount grid (`N`, `Zero`..`Sixteen`). |
| `tbl_appoddiscount` | 0 | `AppODDiscount` | Legacy 4-slab OD discount table (`NewVehicle`, `ZerotoFive`, `fivetoTen`, `Greaterthen10`). |
| `tbl_insurancecompanybyvehicletype` | 13 | `Id` | Insurer underwriting eligibility (`0`/`1`) and company default OD discount (`GCV_Disc`, `Misc_D_Disc`, `PCV_Disc`, `PVT_CAR_Disc`, `Two_Wheeler_Disc`, `Bus_Disc`, `Three_Wheeler_Disc`, `Three_Wheeler_PCV_Disc`). |
| `tbl_patoownerdriver` | 10 | `PAToOwnerDriverId` | Insurer-specific Compulsory PA to Owner-Driver premium (`Rate`, e.g., `315`, `325`, `326`, `330`, `331`, `345`, `375`) and default `TowingCharges`. |
| `tbl_insurancecompanywisetowingchanges` | 16 | `Id` | Insurer-specific Towing Charge rate lookup (`Rate`, `GST18`, `Total`) by coverage `Selection` (`0`, `5000`, `10000`, `15000`, `20000`). |
| `tbl_zerodep` | 198 | `ZerodepId` | Make/Insurer/Age ZeroDep add-on rates (`NillDep`, `SecurePlus`, `SPremium`, `NO`). |
| `tbl_zerodepforsegmentwise` | 14,214 | `ZerodepId` | Model/Fuel/Age ZeroDep add-on rates (`NillDep`, `SecurePlus`, `SPremium`, `NO`). |
| `tbl_zerodepnewaddonrate` | 0 | `AddOnId` | Multi-criteria ZeroDep add-on rate table (`NillDep`, `SecurePlus`, `SPremium`, `NO`). |
| `tbl_addonextraamt` | 1,754 | `ExtraAddonId` | Flat/extra add-on amounts by `InsuranceCompanyId`, `VehiceTypeId` (note typo in column name), `makeId`, `ModelId`, `Age`. |
| `tbl_app_twowheelercc_rate` | 4 | `CC_Id` | 2-Wheeler TP & basic rates by CC slab (`0-75`, `76-150`, `151-350`, `351-1000`). |
| `tbl_app_pcv_cc_rate` | 3 | `PCVCC_Id` | PCV Taxi TP, basic, and per-passenger rates (`1110`, `934`, `1067`) by CC slab (`0-1000`, `1001-1500`, `1501-5000`). |
| `tbl_app_bus_cc_rate` | 3 | `BUSCC_Id` | Bus TP (`13874`, `14494`), per-passenger (`848`, `886`), and OD discount (`85`, `80`, `30`) by `Bus_Type` (`SCHOOL BUS`, `STAFF BUS`, `OTHER BUS`). |
| `tbl_app_threewheeler_cc_rate` | 3 | `ThreeWheelerCC_Id` | 3-Wheeler PCV TP (`2595`), basic rate (`1.2`, `1.32`), and per-passenger rate (`1241`) by age band (`0-5`, `6-7`, `8-15`). |
| `tbl_quotation_prefix` | 45 | `Id` | Role-specific quotation code prefixes (`Q` for Role 4/16, `QS` for Role 5, `QF` for Role 9, `QH` for Role 24, `QI` for Role 32, `QO` for Role 6) and zero-padding strings (`NoOfDigit`). |
| `tbl_selfdiscount` | 48 | `SelfDiscId` | Branch and `ReferenceType` (`Agent`, `Franchise`, `Franchise Agent`) self-discount percentages by `BrokerId` and `ValidFrom`. |

---

## 4. Quotation-to-Policy Conversion Contract (Phase 7 Handoff)

In the legacy system, a Quotation does **not** directly book a policy in `tbl_transaction`. Instead, it provides a pre-populated conversion payload for Proposal / Policy Entry (`tbl_transactionappnew`):

1. **Self-Quotation Conversion (`sp_insert_app_requestedquotationfile(..., P_opr='SELFQUO')`)**:
   - Returns `CONCAT('SQ', QuatationCode)` as `QuatationCode`, `'S'` as `QType` (`Quot_Type`), and all vehicle, IDV, NCB, OD, TP, Net, GST, and Final Premium fields from `tbl_app_quatationentry`.
2. **Assisted Quotation Conversion (`sp_getDataForPolicyEntry(P_QuatationId, P_InsuranceCompanyId)` + `Sp_GetQuotationCodeForPolicyEntry1(P_UserRoleId, P_Id)`)**:
   - Verifies `r.IsQuotationGenerate = 1` and `r.isdeleted = 0`.
   - Joins `tbl_app_quotationrequest` with `tbl_insurancecompanyquotation` for the selected `InsuranceCompanyId`.
   - Resolves master IDs (`Veh_Type_ID`, `Make_ID`, `Model_ID`, `Variant_ID`, `PolicyTypeId`) from the request's vehicle/policy names or IDs.
   - Generates a role-prefixed `QuatationCode` (`Q...`, `QS...`, `QF...`, `QH...`, `QI...`, `QO...`) and `QType` (`Substring(QuatationCode, 1, 1)`).
   - Phase 6 exposes this exact read-only contract via `GET /api/v1/quotations/{quotation_id}/conversion-payload` without creating a policy or payment record.
