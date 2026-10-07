# Phase 6 — Rating Rules & Tariff Reference (`phase_6_rating_rules.md`)

**Repository:** `Reliable-Insurance-Backend`  
**Phase:** `6 — Quotation & Rating Engine (Stage A: Rating Rules, Tariff Tables & Edge Cases)`  
**Database Reference:** Legacy `brahmainsurance` (Read-Only Reference) → Local `reliable_insurance_dev` (`localhost:3306`)  
**Status:** COMPLETE

---

## 1. Executive Summary

This document catalogs all **deterministic business rules, static tariff matrices, validation constraints, and legacy quirks** extracted from the legacy C# codebase and MySQL stored procedures for the Quotation & Rating Engine.

---

## 2. Supported Vehicle Categories & Tariff Routing

The legacy system routes rating calculations across **9 canonical vehicle categories**:

| Category Code | Legacy `tbl_vehicle_type.Veh_Type_ID` | OD Base Tariff Source | TP Base Tariff Source | OD Discount Source |
|---|---|---|---|---|
| `Public_GCV` | `1` (GCV - Public Carrier) | `tbl_quot_damagepremium` (`Company_Type='Public_GCV'`) + GVW > 12000 loading | `tbl_quot_liabilitypremium` (`Company_Type='Public_GCV'`) | `tbl_app_oddiscountnew_gcv` → `tbl_insurancecompanybyvehicletype.Public_GCV_Disc` |
| `Private_GCV` | `2` (GCV - Private Carrier) | `tbl_quot_damagepremium` (`Company_Type='Private_GCV'`) + GVW > 12000 loading | `tbl_quot_liabilitypremium` (`Company_Type='Private_GCV'`) | `tbl_app_oddiscountnew_gcv` → `tbl_insurancecompanybyvehicletype.Private_GCV_Disc` |
| `PublicGCV3W` | `3` (3W Goods Carrying) | `tbl_quot_damagepremium` (`Company_Type='PublicGCV3W'`) | `tbl_quot_liabilitypremium` (`Company_Type='PublicGCV3W'`) | `tbl_app_oddiscountnew_gcv` → `tbl_insurancecompanybyvehicletype.PublicGCV3W_Disc` |
| `PublicPCV3W` | `4` (3W Passenger Carrying) | `tbl_app_threewheeler_cc_rate` | `tbl_quot_liabilitypremium` (`Company_Type='PublicPCV3W'` + `PublicPCV3W_LL`) | `tbl_app_oddiscountnew` → `tbl_insurancecompanybyvehicletype.PublicPCV3W_Disc` |
| `MISC-D` | `5` (Misc-D / Tractor / Crane / Excavator) | `tbl_quot_damagepremium` (`Company_Type='MISC-D'`) | `tbl_quot_liabilitypremium` (`Company_Type='MISC-D'` + `Trailers`) | `tbl_app_oddiscountnew` → `tbl_insurancecompanybyvehicletype.MISC_D_Disc` |
| `PVT` | `6` (Private Car) | `tbl_quot_damagepremium` (`Company_Type='PVT'`) | `tbl_quot_liabilitypremium` (`Company_Type='PVT'`) | `tbl_app_oddiscountnew` → `tbl_appoddiscount` → `tbl_insurancecompanybyvehicletype.PVT_Disc` |
| `TwoWheeler` | `7` (Two Wheeler) | `tbl_app_twowheelercc_rate` | `tbl_quot_liabilitypremium` (`Company_Type='TwoWheeler'`) | `tbl_app_oddiscountnew` → `tbl_appoddiscount` → `tbl_insurancecompanybyvehicletype.TwoWheeler_Disc` |
| `PassengerTaxi(PCV)` | `8` (PCV Taxi / 4W Cab) | `tbl_app_pcv_cc_rate` | `tbl_quot_liabilitypremium` (`Company_Type='PassengerTaxi(PCV)'` + `PassengerTaxi(PCV)_LL`) | `tbl_app_oddiscountnew` → `tbl_insurancecompanybyvehicletype.PassengerTaxi_Disc` |
| `School_Bus` | `9` (School Bus / Staff Bus) | `tbl_app_bus_cc_rate` | `tbl_quot_liabilitypremium` (`Company_Type='School_Bus'` + `School_Bus_LL`) | `tbl_app_oddiscountnew` → `tbl_insurancecompanybyvehicletype.School_Bus_Disc` |

---

## 3. Verified Static Tariff Tables (Exact Values from Legacy DB)

### 3.1 Own Damage Zone Tariff (`tbl_quot_damagepremium` — 216 rows)
- **`PVT` (Private Car)**:
  - `CC <= 1000`:
    - Age `0.0..5.0`: Zone A = `3.127%`, Zone B = `3.039%`, Zone C = `0.000%`
    - Age `5.1..10.0`: Zone A = `3.283%`, Zone B = `3.191%`, Zone C = `0.000%`
    - Age `10.1+` (`11.0`): Zone A = `3.362%`, Zone B = `3.267%`, Zone C = `0.000%`
  - `1001 <= CC <= 1500`:
    - Age `0.0..5.0`: Zone A = `3.283%`, Zone B = `3.191%`, Zone C = `0.000%`
    - Age `5.1..10.0`: Zone A = `3.447%`, Zone B = `3.351%`, Zone C = `0.000%`
    - Age `10.1+` (`11.0`): Zone A = `3.529%`, Zone B = `3.430%`, Zone C = `0.000%`
  - `CC >= 1501`:
    - Age `0.0..5.0`: Zone A = `3.440%`, Zone B = `3.343%`, Zone C = `0.000%`
    - Age `5.1..10.0`: Zone A = `3.612%`, Zone B = `3.510%`, Zone C = `0.000%`
    - Age `10.1+` (`11.0`): Zone A = `3.698%`, Zone B = `3.594%`, Zone C = `0.000%`
- **`Public_GCV`**:
  - Any GVW (`1..999999`):
    - Age `0.0..5.0`: Zone A = `1.751%`, Zone B = `1.743%`, Zone C = `1.726%`
    - Age `5.1..7.0`: Zone A = `1.795%`, Zone B = `1.787%`, Zone C = `1.770%`
    - Age `7.1+`: Zone A = `1.839%`, Zone B = `1.830%`, Zone C = `1.812%`
- **`Private_GCV`**:
  - Any GVW (`1..999999`):
    - Age `0.0..5.0`: Zone A = `1.226%`, Zone B = `1.220%`, Zone C = `1.208%`
    - Age `5.1..7.0`: Zone A = `1.257%`, Zone B = `1.251%`, Zone C = `1.239%`
    - Age `7.1+`: Zone A = `1.287%`, Zone B = `1.281%`, Zone C = `1.268%`
- **`PublicGCV3W`**:
  - Any GVW (`1..999999`):
    - Age `0.0..5.0`: Zone A = `1.664%`, Zone B = `1.656%`, Zone C = `1.640%`
    - Age `5.1..7.0`: Zone A = `1.706%`, Zone B = `1.697%`, Zone C = `1.681%`
    - Age `7.1+`: Zone A = `1.747%`, Zone B = `1.739%`, Zone C = `1.722%`
- **`MISC-D`**:
  - Any CC/GVW (`1..999999`):
    - Age `0.0..5.0`: Zone A = `1.208%`, Zone B = `1.202%`, Zone C = `1.190%`
    - Age `5.1..7.0`: Zone A = `1.238%`, Zone B = `1.232%`, Zone C = `1.220%`
    - Age `7.1+`: Zone A = `1.268%`, Zone B = `1.262%`, Zone C = `1.250%`

### 3.2 Two-Wheeler, PCV, Bus & 3W CC Rate Tables
- **`tbl_app_twowheelercc_rate` (4 rows)**:
  - `1..75 CC`: `Zero=1.708`, `ZeroToFive=1.708`, `FiveToTen=1.793`, `AboveTen=1.836`
  - `76..150 CC`: `Zero=1.708`, `ZeroToFive=1.708`, `FiveToTen=1.793`, `AboveTen=1.836`
  - `151..350 CC`: `Zero=1.793`, `ZeroToFive=1.793`, `FiveToTen=1.883`, `AboveTen=1.928`
  - `351..99999 CC`: `Zero=1.879`, `ZeroToFive=1.879`, `FiveToTen=1.973`, `AboveTen=2.020`
- **`tbl_app_pcv_cc_rate` (3 rows)**:
  - `1..1000 CC`: `Zero=3.19`, `ZeroToFive=3.19`, `FiveToSeven=3.27`, `AboveSeven=3.35`, `ExtraCharge=0`
  - `1001..1500 CC`: `Zero=3.35`, `ZeroToFive=3.35`, `FiveToSeven=3.43`, `AboveSeven=3.52`, `ExtraCharge=0`
  - `1501..99999 CC`: `Zero=3.51`, `ZeroToFive=3.51`, `FiveToSeven=3.60`, `AboveSeven=3.68`, `ExtraCharge=0`
- **`tbl_app_bus_cc_rate` (3 rows)**:
  - `1..18 Seats`: `Zero=1.656`, `ZeroToFive=1.656`, `FiveToSeven=1.697`, `AboveSeven=1.739`, `ExtraCharge=350`
  - `19..36 Seats`: `Zero=1.656`, `ZeroToFive=1.656`, `FiveToSeven=1.697`, `AboveSeven=1.739`, `ExtraCharge=450`
  - `37..99999 Seats`: `Zero=1.656`, `ZeroToFive=1.656`, `FiveToSeven=1.697`, `AboveSeven=1.739`, `ExtraCharge=550`
- **`tbl_app_threewheeler_cc_rate` (3 rows)**:
  - `1..18` / `19..36` / `37..99999`: `Zero=1.280`, `ZeroToFive=1.280`, `FiveToSeven=1.312`, `AboveSeven=1.344`, `ExtraCharge=0`

### 3.3 Third-Party Liability Tariff (`tbl_quot_liabilitypremium` — 28 rows)
- **`PVT`**: `1..1000 CC` = `2094`, `1001..1500 CC` = `3416`, `>1500 CC` = `7897`
- **`TwoWheeler`**: `1..75 CC` = `538`, `76..150 CC` = `714`, `151..350 CC` = `1366`, `>350 CC` = `2804`
- **`Public_GCV`**: `1..7500 GVW` = `16049`, `7501..12000 GVW` = `27186`, `12001..20000 GVW` = `35313`, `20001..40000 GVW` = `43950`, `>40000 GVW` = `44242`
- **`Private_GCV`**: `1..7500 GVW` = `8468`, `7501..12000 GVW` = `17229`, `12001..20000 GVW` = `10963`, `20001..40000 GVW` = `22167`, `>40000 GVW` = `29890`
- **`PublicGCV3W`**: `1..999999` = `4492`
- **`PublicPCV3W`**: `1..999999` = `2539`; `PublicPCV3W_LL` = `1217` per passenger
- **`MISC-D`**: `1..999999` = `7267`; `Trailers` = `2485` per trailer
- **`PassengerTaxi(PCV)`**: `1..1000 CC` = `6040`, `1001..1500 CC` = `7940`, `>1500 CC` = `10523`; `PassengerTaxi(PCV)_LL` (`1..1000`=`1162`, `1001..1500`=`978`, `>1500`=`1117` per passenger)
- **`School_Bus`**: `1..999999` = `12192`; `School_Bus_LL` = `745` per student/passenger

### 3.4 PA to Owner-Driver & Towing Charges (`tbl_patoownerdriver` & `tbl_insurancecompanywisetowingchanges`)
- **`tbl_patoownerdriver`**:
  - Company `2` (Bajaj): `Rate=325`, `Towing=100`
  - Company `3` (Tata AIG): `Rate=375`, `Towing=0`
  - Company `4` (Future Generali): `Rate=330`, `Towing=0`
  - Company `5` (HDFC Ergo): `Rate=375`, `Towing=0`
  - Company `6` (ICICI Lombard): `Rate=375`, `Towing=150`
  - Company `7` (Reliance): `Rate=315`, `Towing=0`
  - Company `8` (Iffco Tokio): `Rate=450`, `Towing=0`
  - Company `9` (Shriram): `Rate=750`, `Towing=0`
  - Company `10` (Royal Sundaram): `Rate=350`, `Towing=0`
  - Company `16` (Kotak): `Rate=275`, `Towing=0`

---

## 4. Business Validation Rules & Edge Cases

1. **NCB Slabs & Reset Rules**:
   - Valid NCB values: `0`, `20`, `25`, `35`, `45`, `50`. Any other percentage is rejected with `422 Unprocessable Entity`.
   - If `claim_in_previous_policy == True` or `prev_policy_available == False` or `business_type_id == 1` (New Business): `NCB` is automatically forced to `0%`.
2. **Product Type / Insurance Type Rules**:
   - `ProductTypeId == 1` (`Package` / Comprehensive): Calculates both OD (+ Add-Ons) and TP.
   - `ProductTypeId == 2` (`Liability Only` / TP Only): Forces `SelectedIDV = 0`, `TotalIDV = 0`, `NetODPremium = 0`, `ZeroDep = 0`, `NCB = 0`. Calculates TP + GST only.
   - `ProductTypeId == 3` (`OD Only` / Standalone OD): Forces `TotalTPPremium = 0`, `PAOwnerDriver = 0`, `LLPaidDriver = 0`. Calculates OD + Add-Ons + GST only.
3. **Reliance OD Discount Cap (`InsuranceCompanyId == 7`)**:
   - Any OD discount exceeding `90%` for Reliance (`InsuranceCompanyId == 7`) is capped at `90%`.
4. **Declined Risk Handling (`tbl_app_oddiscountnew.Decline == 'Yes'`)**:
   - When `sp_SelectAppDiscDiclineOrNot` returns `'Yes'`, the insurer is flagged as `is_declined = True` in multi-insurer comparison results.
5. **Title / Quotation Code Uniqueness**:
   - `tbl_app_quatationentry.Title` has a physical `UNIQUE` index (`Title(200)`), and `Sp_InsertQuotation1` enforces uniqueness on `tbl_app_quotationrequest.Title`. Our service layer guarantees unique code generation and returns `409 Conflict` if an explicit duplicate `Title` is supplied.
