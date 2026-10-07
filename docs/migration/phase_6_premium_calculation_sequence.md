# Phase 6 — Premium Calculation Sequence (`phase_6_premium_calculation_sequence.md`)

**Repository:** `Reliable-Insurance-Backend`  
**Phase:** `6 — Quotation & Rating Engine (Stage A: Exact Premium Calculation Sequence)`  
**Database Reference:** Legacy `brahmainsurance` (Read-Only Reference) → Local `reliable_insurance_dev` (`localhost:3306`)  
**Status:** COMPLETE

---

## 1. Executive Summary

This document specifies the **exact step-by-step mathematical execution sequence** and **intermediate rounding rules** extracted from the legacy C# WebForms (`SelfQuotationRequest*.aspx.cs`, `QuotationRequestEntry*.aspx.cs`), `Cls_QuatationEntry.cs`, and MySQL stored procedures.

Every calculation in the FastAPI Rating Engine (`app/services/rating.py`) **MUST** use `decimal.Decimal` (never `float`) and follow the exact order of operations and intermediate `ROUND_HALF_UP` / `FLOOR` steps documented here.

---

## 2. Step-by-Step Calculation Sequence

### Step 1: Vehicle Age Determination (`sp_SelectMgfyearOfyearmonth`)
Given `registration_date` (or `manufacture_date` for unregistered vehicles) and `calculation_date` (default `CURRENT_DATE`):
1. Compute elapsed days:
   $$\text{days} = (\text{calculation\_date} - \text{registration\_date}).\text{days}$$
2. Compute raw year-month decimal (rounded to 1 decimal place using `ROUND_HALF_UP`, matching MySQL `CONVERT((days * 1.0 / 365), DECIMAL(4,1))`):
   $$V_{\text{MonthCount}} = \text{round}\left(\frac{\text{days}}{365}, 1\right)$$
3. Apply legacy threshold:
   - If $V_{\text{MonthCount}} \in \{0.0, 0.1\}$:
     $$\text{Age} = \text{Decimal}('0.0')$$
   - Else:
     $$\text{Age} = \text{Decimal}\left(\left\lceil \frac{\text{days}}{365} \right\rceil\right).\text{quantize}(\text{Decimal}('0.1'))$$
4. **Tariff Lookup Age Cap**:
   - When querying `tbl_quot_damagepremium` (`sp_quot_damagepremium`), if $\text{Age} > 10$, set $\text{LookupAge} = \text{Decimal}('11.0')$.

---

### Step 2: Base IDV & Permissible ±15% Band (`sp_SelectIDVDetails`, `sp_SelectIDVDetailsForGCV`)
1. **Standard Vehicles (`PVT`, `TwoWheeler`, `PassengerTaxi`, `School_Bus`, `MISC-D`, `PublicPCV3W`, `PublicGCV3W`)**:
   - Base IDV = `tbl_vehicle_variants.ExMumbai_Model_Price`
2. **Goods Carrying Vehicles (`Public_GCV`, `Private_GCV`)**:
   - If `with_body == True` (`'Yes'`): Base IDV = `ExMumbai_Model_Price`
   - If `with_body == False` (`'No'`): Base IDV = `ExMumbai_Body_Price + ExMumbai_Chasis_Price`
3. **Permissible IDV Band**:
   $$\text{MinIDV} = \text{BaseIDV} - \left\lfloor \frac{\text{BaseIDV} \times 15}{100} \right\rfloor$$
   $$\text{MaxIDV} = \text{BaseIDV} + \left\lfloor \frac{\text{BaseIDV} \times 15}{100} \right\rfloor$$
   - Note: For `Package` / `OD Only` policies, `selected_idv` must be within $[\text{MinIDV}, \text{MaxIDV}]$ (unless `Liability Only`, where `TotalIDV = 0`).
4. **Total IDV Calculation**:
   $$\text{TotalIDV} = \text{SelectedIDV} + \text{ElectricalAccessoriesValue} + \text{NonElectricalAccessoriesValue} + \text{LPGKitValue} + \text{TrailerValue}$$

---

### Step 3: Basic Own Damage (OD) Rate & Base OD Premium
Depending on the `company_type` (vehicle category):

#### Case A: Zone-Tariff Categories (`Public_GCV`, `Private_GCV`, `PublicGCV3W`, `MISC-D`, `PVT`)
1. Query `tbl_quot_damagepremium` for `(Company_Type, CC/GVW bracket, min(Age, 11.0))`.
2. Select rate $R_{\text{OD}}$ based on `Zone`:
   - `Zone == 'A'` → `OD_premium_Azone`
   - `Zone == 'B'` → `OD_premium_Bzone`
   - `Zone == 'C'` → `OD_premium_Czone`
3. Compute Basic Vehicle OD:
   $$\text{BasicOD}_{\text{vehicle}} = \frac{\text{SelectedIDV} \times R_{\text{OD}}}{100}$$
4. **Commercial Tonnage / GVW Loading (`Public_GCV`, `Private_GCV`)**:
   - If $\text{GVW} > 12000$:
     $$\text{GVWLoading} = \frac{(\text{GVW} - 12000) \times 27}{100}$$
     $$\text{BasicOD} = \text{round\_half\_up}(\text{BasicOD}_{\text{vehicle}} + \text{GVWLoading}, 0)$$
   - Else:
     $$\text{BasicOD} = \text{round\_half\_up}(\text{BasicOD}_{\text{vehicle}}, 0)$$

#### Case B: CC-Rate Table Categories (`TwoWheeler`, `PassengerTaxi(PCV)`, `School_Bus`, `PublicPCV3W`)
1. **`TwoWheeler`**: Query `tbl_app_twowheelercc_rate` by CC bracket and age (`0.0→Zero`, `0.1..5.0→ZeroToFive`, `5.1..10.0→FiveToTen`, `>10.0→AboveTen`).
   $$\text{BasicOD} = \text{round\_half\_up}\left(\frac{\text{SelectedIDV} \times R_{\text{2W}}}{100}, 0\right)$$
2. **`PassengerTaxi(PCV)`**: Query `tbl_app_pcv_cc_rate` by CC bracket and age (`0.0→Zero`, `0.1..5.0→ZeroToFive`, `5.1..7.0→FiveToSeven`, `>7.0→AboveSeven`) plus `ExtraCharge`:
   $$\text{BasicOD} = \text{round\_half\_up}\left(\frac{\text{SelectedIDV} \times R_{\text{PCV}}}{100} + \text{ExtraCharge}, 0\right)$$
3. **`School_Bus`**: Query `tbl_app_bus_cc_rate` by CC bracket and age (`0.0→Zero`, `0.1..5.0→ZeroToFive`, `5.1..7.0→FiveToSeven`, `>7.0→AboveSeven`) plus `ExtraCharge` + seating capacity charge:
   $$\text{BasicOD} = \text{round\_half\_up}\left(\frac{\text{SelectedIDV} \times R_{\text{Bus}}}{100} + \text{ExtraCharge}, 0\right)$$
4. **`PublicPCV3W`**: Query `tbl_app_threewheeler_cc_rate` by CC bracket and age (`0.0→Zero`, `0.1..5.0→ZeroToFive`, `5.1..7.0→FiveToSeven`, `>7.0→AboveSeven`) plus `ExtraCharge`:
   $$\text{BasicOD} = \text{round\_half\_up}\left(\frac{\text{SelectedIDV} \times R_{\text{3W}}}{100} + \text{ExtraCharge}, 0\right)$$

---

### Step 4: Accessories, CNG/LPG, IMT-23 & Geographical Extension (OD Additions)
Each OD addition is rounded to integer (`ROUND_HALF_UP`) at each intermediate step:
1. **Electrical Accessories OD**:
   $$\text{ElecAccOD} = \text{round\_half\_up}\left(\frac{\text{ElectricalAccessoriesValue} \times 4}{100}, 0\right)$$
2. **Non-Electrical Accessories OD**:
   $$\text{NonElecAccOD} = \text{round\_half\_up}\left(\frac{\text{NonElectricalAccessoriesValue} \times R_{\text{OD}}}{100}, 0\right)$$
3. **External CNG / LPG Kit OD**:
   - If `lpg_value > 0`:
     $$\text{LPGOD} = \text{round\_half\_up}\left(\frac{\text{LPGValue} \times 4}{100}, 0\right)$$
   - If built-in CNG/LPG (`inbuilt_lpg == True` on `PVT` / `PassengerTaxi`):
     $$\text{InbuiltLPGOD} = \text{round\_half\_up}\left(\frac{\text{BasicOD} \times 5}{100}, 0\right)$$
4. **Fiber Glass Tank**:
   - If `fiber_glass_tank == True`: $\text{FiberGlassOD} = 50$ (or `100` for commercial)
5. **Geographical Extension OD**:
   - If `geographical_extension == True`: $\text{GeoExtOD} = 400$
6. **Gross Basic OD before IMT-23**:
   $$\text{SubTotalOD}_{1} = \text{BasicOD} + \text{ElecAccOD} + \text{NonElecAccOD} + \text{LPGOD} + \text{InbuiltLPGOD} + \text{FiberGlassOD} + \text{GeoExtOD}$$
7. **IMT-23 Loading (Commercial Vehicles / GCV / Misc-D / Tractor)**:
   - If `imt23 == True`:
     $$\text{IMT23Amt} = \text{round\_half\_up}\left(\frac{\text{SubTotalOD}_{1} \times 15}{100}, 0\right)$$
   - Else: $\text{IMT23Amt} = 0$
8. **Gross OD before Discounts**:
   $$\text{GrossOD} = \text{SubTotalOD}_{1} + \text{IMT23Amt}$$

---

### Step 5: Own Premises, Anti-Theft & Voluntary Deductible Discounts
1. **Use Confined to Own Premises (`own_premises == True`)**:
   $$\text{OwnPremisesDisc} = \text{round\_half\_up}\left(\frac{\text{GrossOD} \times 33}{100}, 0\right)$$
2. **Anti-Theft Device (`anti_theft == True`)**:
   $$\text{AntiTheftDisc} = \min\left(\text{round\_half\_up}\left(\frac{(\text{GrossOD} - \text{OwnPremisesDisc}) \times 2.5}{100}, 0\right), 500\right)$$
3. **Voluntary Excess / Deductible (`voluntary_access`)**:
   - For `PVT`:
     - Slab `2500` → $\min(20\% \text{ of OD}, 750)$
     - Slab `5000` → $\min(25\% \text{ of OD}, 1500)$
     - Slab `7500` → $\min(30\% \text{ of OD}, 2000)$
     - Slab `15000` → $\min(35\% \text{ of OD}, 2500)$
   - For `TwoWheeler`:
     - Slab `500` → $\min(5\% \text{ of OD}, 50)$
     - Slab `750` → $\min(10\% \text{ of OD}, 75)$
     - Slab `1000` → $\min(15\% \text{ of OD}, 125)$
     - Slab `1500` → $\min(20\% \text{ of OD}, 200)$
     - Slab `3000` → $\min(25\% \text{ of OD}, 250)$
4. **OD After Tariff Discounts**:
   $$\text{ODAfterTariffDisc} = \text{GrossOD} - \text{OwnPremisesDisc} - \text{AntiTheftDisc} - \text{VoluntaryDisc}$$

---

### Step 6: Company OD Discount & NCB (No Claim Bonus) Sequence
Crucial legacy order of operations verified from `SelfQuotationRequest*.aspx.cs`:
1. **Resolve OD Discount Percentage ($D_{\text{OD}}\%$)**:
   - Priority 1: Explicit user override (if permitted) or `sp_SelectAppDiscWithFueltype` (`tbl_app_oddiscountnew`) / `sp_SelectAppDiscWithFueltypeGCV` (`tbl_app_oddiscountnew_gcv`) using `FLOOR(rate)`.
   - Priority 2: Legacy model discount `sp_SelectAppDiscount` (`tbl_appoddiscount`).
   - Priority 3: Company fallback `sp_Quot_ODDiscFromCompany` (`tbl_insurancecompanybyvehicletype`).
   - **Reliance Cap (`InsuranceCompanyId == 7`)**: If $D_{\text{OD}} > 90$, cap $D_{\text{OD}} = 90$ (`RelianceCapping = 90` in `Web.config`).
2. **Calculate Company OD Discount Amount**:
   $$\text{ODDiscountAmt} = \text{round\_half\_up}\left(\frac{\text{ODAfterTariffDisc} \times D_{\text{OD}}}{100}, 0\right)$$
3. **OD After Company Discount**:
   $$\text{ODAfterCompDisc} = \text{ODAfterTariffDisc} - \text{ODDiscountAmt}$$
4. **Calculate NCB (No Claim Bonus) on Post-Discount OD**:
   - Allowed NCB Slabs: $\{0, 20, 25, 35, 45, 50\}\%$.
   - If `claim_in_previous_policy == True` (`'Yes'`) or `prev_policy_available == False` (`'No'`): $\text{NCB}\% = 0$.
   $$\text{NCBAmt} = \text{round\_half\_up}\left(\frac{\text{ODAfterCompDisc} \times \text{NCB}\%}{100}, 0\right)$$
5. **Net Own Damage Premium (Before Add-Ons)**:
   $$\text{NetODPremium} = \text{ODAfterCompDisc} - \text{NCBAmt}$$
   *(If `InsuranceType == 'Liability Only'` / `ProductTypeId == 2`, $\text{NetODPremium} = 0$.)*

---

### Step 7: Zero-Depreciation & Add-On Covers (`NilDepreciation` / Extra Add-Ons)
1. **Zero-Depreciation (`nd == True` / `zero_dep == 'Yes'`)**:
   - Rate lookup hierarchy:
     1. `sp_SelectZeroDepNewAddonRate` (`tbl_zerodepnewaddonrate` by Make, Model, Company, Age `0..5`, FuelType)
     2. `sp_SelectZeroDepSegRate` (`tbl_zerodepforsegmentwise` by Variant Segment, Company, Age `0..7`)
     3. `sp_SelectZeroDepRate` (`tbl_zerodep` by Make, Model, Company, Age `0..5`)
   - Plus `sp_SelectAddonExtraAmt` (`tbl_addonextraamt` flat extra amount by Company, VehicleTypeId, CC, Age):
     $$\text{ZeroDepPremium} = \text{round\_half\_up}\left(\frac{\text{SelectedIDV} \times R_{\text{ZeroDep}}}{100} + \text{ExtraAddonAmt}, 0\right)$$
2. **Additional Add-Ons from `tbl_zerodepnewaddonrate`** (when selected):
   - `Consumable`: $\text{round\_half\_up}\left(\frac{\text{SelectedIDV} \times R_{\text{Consumable}}}{100}, 0\right)$
   - `Engine_GearBox`: $\text{round\_half\_up}\left(\frac{\text{SelectedIDV} \times R_{\text{Engine}}}{100}, 0\right)$
   - `TYRE_RIM`: $\text{round\_half\_up}\left(\frac{\text{SelectedIDV} \times R_{\text{Tyre}}}{100}, 0\right)$
   - `Invoice_Cover` (Return to Invoice): $\text{round\_half\_up}\left(\frac{\text{SelectedIDV} \times R_{\text{Invoice}}}{100}, 0\right)$
3. **Roadside Assistance / Towing Charges (`towing_charges`)**:
   - Looked up via `sp_SelectTowingCharges` (`tbl_insurancecompanywisetowingchanges.Rate`) or `sp_SelectPaToOwnerDriverRate` (`tbl_patoownerdriver.TowingCharges`).
4. **Total OD + Add-On Component (`TotalODWithAddons`)**:
   $$\text{TotalODWithAddons} = \text{NetODPremium} + \text{ZeroDepPremium} + \text{ConsumableAmt} + \text{EngineGearBoxAmt} + \text{TyreRimAmt} + \text{InvoiceCoverAmt} + \text{TowingAmt}$$

---

### Step 8: Third-Party Liability (TP) Premium Calculation
*(If `InsuranceType == 'OD Only'` / `ProductTypeId == 3`, $\text{TotalTPPremium} = 0$.)*
1. **Basic Liability Premium (`sp_quot_liabilitypremium`)**:
   - Query `tbl_quot_liabilitypremium` by `(Company_Type, CC/GVW bracket)` → $\text{BasicTP}$.
2. **Passenger Legal Liability (`PassengerTaxi`, `School_Bus`, `PublicPCV3W`)**:
   - Looked up from `tbl_quot_liabilitypremium` where `Company_Type = '<Category>_LL'` (`PassengerTaxi(PCV)_LL` = per-passenger rate, `School_Bus_LL` = per-student/passenger rate, `PublicPCV3W_LL` = per-passenger rate):
     $$\text{PassengerLL} = \text{NoOfPassengers} \times R_{\text{PassengerLL}}$$
3. **Bi-Fuel / CNG / LPG Third-Party Liability**:
   - If `lpg_liability == True` or `lpg_value > 0` or `inbuilt_lpg == True`: $\text{LPGTP} = 60$
4. **Geographical Extension TP**:
   - If `geographical_extension == True`: $\text{GeoExtTP} = 100$
5. **PA to Owner-Driver (`pa_to_owner_driver == True`)**:
   - Query `sp_SelectPaToOwnerDriverRate(CompanyId)` from `tbl_patoownerdriver.Rate` (e.g., `275`, `315`, `325`, `330`, `350`, `375`, `450`, or `750`).
6. **Legal Liability to Paid Driver / Cleaner / Coolie**:
   - `LLPaidDriver` = $\text{NoOfLL} \times 50$
   - `LLCleaner` = $\text{NoOfCleaner} \times 50$
   - `LLCoolie` = $\text{NoOfCoolie} \times 50$
7. **PA to Unnamed Passengers / Paid Driver / Cleaner**:
   - `PADriverCleaner` = configured PA amount (`pa_driver_cleaner`)
8. **Non-Fare Paying Passengers (`nfpp`, for GCV)**:
   - $\text{NFPPAmt} = \text{NFPPCount} \times 75$
9. **Trailer Third-Party Liability (`no_of_trailers`)**:
   - $\text{TrailerTP} = \text{NoOfTrailers} \times R_{\text{TrailerTP}}$
10. **Total Third-Party Premium (`TotalTPPremium`)**:
    $$\text{TotalTPPremium} = \text{BasicTP} + \text{PassengerLL} + \text{LPGTP} + \text{GeoExtTP} + \text{PAOwnerDriver} + \text{LLPaidDriver} + \text{LLCleaner} + \text{LLCoolie} + \text{PADriverCleaner} + \text{NFPPAmt} + \text{TrailerTP}$$

---

### Step 9: Net Premium, GST Calculation, and Final Payable Premium
1. **Net Premium (Before Tax)**:
   $$\text{NetPremium} = \text{TotalODWithAddons} + \text{TotalTPPremium}$$
2. **GST Calculation**:
   - **Standard Categories (`PVT`, `TwoWheeler`, `PassengerTaxi`, `School_Bus`, `MISC-D`, `PublicPCV3W`)**:
     - GST is `18%` across both OD and TP:
       $$\text{GST} = \text{round\_half\_up}\left(\frac{\text{NetPremium} \times 18}{100}, 0\right)$$
   - **Goods Carrying Vehicles (`Public_GCV`, `Private_GCV`, `PublicGCV3W`) — Split GST Rule**:
     - Standard 18% GST applies to OD + Add-Ons + Non-Basic TP, while **Basic TP (`BasicTP`) on GCV is taxed at 12%** in legacy GCV worksheets (or 18% when uniform mode is selected; our engine supports both and defaults to the exact legacy GCV formula: `18%` on `TotalODWithAddons + (TotalTPPremium - BasicTP)` and `12%` on `BasicTP`, with a flag `gcv_tp_gst_rate` defaulting to `Decimal('18')` or `Decimal('12')` per legacy sheet mode):
       - In `SelfQuotationRequestPublicGCV.aspx.cs` & `SelfQuotationRequestPrivateGCV.aspx.cs`:
         $$\text{GST}_{\text{OD+OtherTP}} = \text{round\_half\_up}\left(\frac{(\text{NetPremium} - \text{BasicTP}) \times 18}{100}, 0\right)$$
         $$\text{GST}_{\text{BasicTP}} = \text{round\_half\_up}\left(\frac{\text{BasicTP} \times 12}{100}, 0\right)$$
         $$\text{GST} = \text{GST}_{\text{OD+OtherTP}} + \text{GST}_{\text{BasicTP}}$$
3. **Final Gross Payable Premium**:
   $$\text{FinalPayablePremium} = \text{NetPremium} + \text{GST}$$
