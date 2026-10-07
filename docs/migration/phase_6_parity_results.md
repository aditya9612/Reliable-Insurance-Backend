# Phase 6 — Quotation & Rating Engine Parity Verification Results

**Repository:** `Reliable-Insurance-Backend`  
**Phase:** `6 — Quotation & Rating Engine`  
**Target Environment:** Local Development (`localhost:3306/reliable_insurance_dev`)  
**Parity Status:** **100% VERIFIED PARITY (`0.00` Discrepancy Across All 9 Vehicle Categories)**

---

## 1. Executive Summary

Phase 6 verified the new FastAPI `RatingEngineService` and `QuotationService` against the legacy C# WebForms (`Clerk/Quotation*.aspx.cs`), `Service.asmx.cs` WebMethods, and MySQL stored procedures (`sp_quot_damagepremium`, `sp_quot_liabilitypremium`, `sp_SelectMgfyearOfyearmonth`, `sp_SelectIDVDetails`, `sp_SelectIDVDetailsForGCV`, `sp_SelectAppDiscWithFueltype`, `sp_SelectAppDiscWithFueltypeGCV`, `sp_SelectZeroDepMultiAddOn_New`, `Sp_GetQuotationCodeForSelfRequestedQuotation`, `Sp_GetQuotationCodeForPolicyEntry1`, `Sp_InsertAppQuotationEntry`, `InsertAppQuotationRequest`, `Sp_UpdateAppQuotReqNew`, `sp_UpdateAppAttendQuotation1`, `sp_UpdateAppQuotationReopen`, `sp_UpdateAppQuotationRequest`).

All calculations execute in `Decimal` arithmetic (`0` `float` fields in request/response schemas or rating calculations) with intermediate nearest-rupee rounding (`ROUND_HALF_UP`) matching `Math.Round` in the legacy WebForms.

---

## 2. Golden Parity Test Matrix (9 Vehicle Categories)

| Case ID | Vehicle Category | Zone | CC / GVW / Seats | Age | Base IDV (₹) | OD Basic Rate (%) | Gross OD (₹) | OD Disc (%) | OD Disc Amt (₹) | NCB (%) | NCB Amt (₹) | Net OD (₹) | Basic TP (₹) | Total TP (₹) | Net Premium (₹) | Total GST (₹) | Final Payable (₹) | Legacy vs FastAPI Delta |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `GOLDEN-01-PVT` | `PVT` (Private Car) | A | 1197 CC | 3.0 | 600,000 | 3.283% | 19,698 | 60% | 11,819 | 25% | 1,970 | 5,909 | 3,416 | 3,791 | 9,700 | 1,746 (18%) | **11,446** | **`0.00`** |
| `GOLDEN-02-TWOWHEELER` | `TwoWheeler` | B | 125 CC | 2.0 | 70,000 | 1.676% | 1,173 | 50% | 587 | 20% | 117 | 469 | 714 | 1,079 | 1,548 | 279 (18%) | **1,827** | **`0.00`** |
| `GOLDEN-03-PUBLIC-GCV` | `Public_GCV` (+IMT23) | C | 16,000 kg GVW | 4.0 | 1,200,000 | 1.726% | 25,061 | 70% | 17,543 | 20% | 1,504 | 6,014 | 35,313 | 35,938 | 41,952 | 5,433 (Split 18%/12%) | **47,385** | **`0.00`** |
| `GOLDEN-04-PRIVATE-GCV` | `Private_GCV` | A | 7,000 kg GVW | 1.0 | 800,000 | 1.226% | 9,808 | 50% | 4,904 | 0% | 0 | 4,904 | 8,438 | 8,813 | 13,717 | 1,963 (Split 18%/12%) | **15,680** | **`0.00`** |
| `GOLDEN-05-PUBLIC-GCV-3W` | `PublicGCV3W` | B | 500 CC | 2.0 | 200,000 | 1.656% | 3,312 | 40% | 1,325 | 20% | 397 | 1,590 | 4,492 | 4,873 | 6,463 | 894 (Split 18%/12%) | **7,357** | **`0.00`** |
| `GOLDEN-06-PUBLIC-PCV-3W` | `PublicPCV3W` | C | 200 CC / 3 Seats | 3.0 | 180,000 | 1.260% | 2,268 | 30% | 680 | 20% | 318 | 1,270 | 2,595 (+3,723 Pass LL) | 6,743 | 8,013 | 1,442 (18%) | **9,455** | **`0.00`** |
| `GOLDEN-07-MISC-D` | `Misc-D` (+IMT23 +Trailer) | B | 2500 CC | 2.0 | 600,000 | 1.190% | 8,211 | 50% | 4,106 | 20% | 821 | 3,284 | 7,267 (+2,485 Trailer) | 10,177 | 13,461 | 2,423 (18%) | **15,884** | **`0.00`** |
| `GOLDEN-08-PASSENGER-TAXI-PCV` | `PassengerTaxi(PCV)` | A | 1197 CC / 4 Seats | 2.0 | 500,000 | 3.448% | 17,240 | 40% | 6,896 | 20% | 2,069 | 8,275 | 7,584 (+3,736 Pass LL) | 11,745 | 20,020 | 3,604 (18%) | **23,624** | **`0.00`** |
| `GOLDEN-09-SCHOOL-BUS` | `School_Bus` | B | 30 Seats | 3.0 | 1,500,000 | 1.672% | 25,080 | 85% | 21,318 | 25% | 941 | 2,821 | 13,874 (+25,440 Pass LL) | 39,789 | 42,610 | 7,670 (18%) | **50,280** | **`0.00`** |

---

## 3. Stored Procedure & Special Rule Parity Verification

| Legacy Rule / Stored Procedure | FastAPI Implementation | Verification Result |
|---|---|---|
| `sp_SelectMgfyearOfyearmonth` (`0.0`/`0.1` threshold -> `0.0`, else `CEIL(days/365)`) | `RatingEngineService.calculate_vehicle_age` | **VERIFIED (`100%` Match)** |
| `sp_SelectIDVDetails` & `sp_SelectIDVDetailsForGCV` (`±15%` IDV band & `Body + Chassis` sum when `with_body=False`) | `RatingEngineService.calculate_idv_band` & `calculate_premium` | **VERIFIED (`100%` Match)** |
| Commercial Tonnage Loading (`GVW > 12000` -> `round((GVW - 12000) * 27 / 100)`) | `RatingEngineService.calculate_premium` | **VERIFIED (`100%` Match)** |
| `IMT-23` Loading (`15%` on gross OD before discounts) | `RatingEngineService.calculate_premium` | **VERIFIED (`100%` Match)** |
| `Own Premises` Discount (`33%` on gross OD) & `Anti-Theft` (`2.5%` capped at `₹500`) | `RatingEngineService.calculate_premium` | **VERIFIED (`100%` Match)** |
| `RelianceCapping = 90` (`InsuranceCompanyId == 7` OD discount capped at `90%`) | `RatingEngineService.calculate_premium` | **VERIFIED (`100%` Match)** |
| `sp_SelectAppDiscWithFueltype` / `sp_SelectAppDiscDiclineOrNot` (Age columns `N, Zero..Sixteen` including physical typo `thriteen`, and `Decline == 1`) | `QuotationRepository.get_od_discount_and_decline` | **VERIFIED (`100%` Match)** |
| `sp_SelectZeroDepMultiAddOn_New` & `sp_SelectZeroDepExtraAmount` (`NillDep`, `SecurePlus`, `SPremium` + flat extra amount) | `QuotationRepository.get_zero_dep_rates` | **VERIFIED (`100%` Match)** |
| `Sp_GetQuotationCodeForSelfRequestedQuotation` (`SRQ<VehTypeId><CompId><RoleCode><ActorId><ZeroPad><NextId>`) | `QuotationRepository.generate_self_quotation_code` | **VERIFIED (`100%` Match)** |
| `Sp_GetQuotationCodeForPolicyEntry1` (`<RoleCode><ActorId><ZeroPad><NextId>`) | `QuotationRepository.generate_assisted_quotation_code` | **VERIFIED (`100%` Match)** |
| Assisted Request Lifecycle (`IsQuotationGenerate` `0/1`, `isPendingRevert` `0/1/2`, `AttendedBy` lock, `tbl_insurancecompanyquotation`, `tbl_app_quotationremark`) | `QuotationService` | **VERIFIED (`100%` Match)** |
