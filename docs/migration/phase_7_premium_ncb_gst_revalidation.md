# Phase 7 — Policy Booking: Premium, NCB, OD Discount & GST Revalidation Specification

**Phase:** 7 — Policy Booking & Transaction Engine  
**Stage:** A3 — Financial Revalidation & Anti-Double-Counting Specification  
**Target Database:** `localhost:3306/reliable_insurance_dev`

---

## 1. Core Financial Principle: Reuse Phase 6 Rating Engine Without Double-Counting

During Policy Booking, financial values arrive through one of three sources:

1. **Source 1 — Self-Quotation Conversion (`source_type = "SELF_QUOTATION"`, `tbl_app_quatationentry`)**:
   - The quotation was already rated by Phase 6 `RatingEngineService.calculate_premium` and persisted in `tbl_app_quatationentry`.
   - **Critical Legacy Mapping Rule (`sp_getDataForPolicyEntry('SELFQUO')`):**
     - `tbl_app_quatationentry.OwnDamagePremium` = Gross OD before company OD discount and NCB (includes Basic OD + Accessories OD + GVW loading + IMT-23).
     - `tbl_app_quatationentry.OD` = Monetary Company OD Discount amount.
     - `tbl_app_quatationentry.NoClaimBonus` = Monetary NCB deduction amount (`NCBPermium`).
     - `tbl_app_quatationentry.NCBPre` = NCB percentage (`0, 20, 25, 35, 45, 50`).
     - `tbl_app_quatationentry.ZeroDepreciation` = Monetary Add-On / Nil-Dep premium (`AddOn`).
     - `tbl_app_quatationentry.AtotalOwnDamPremium` = **Final OD Premium** (`Net OD after Tariff Discounts, Company OD Discount, and NCB + ZeroDep + Towing`).
     - `tbl_app_quatationentry.BtotalLiabilityPremium` = **Final TP Liability Premium** (`TPPermium`).
     - `tbl_app_quatationentry.TotalPremium` = **Net Premium before GST** (`AtotalOwnDamPremium + BtotalLiabilityPremium` = `NetPermium`).
     - `tbl_app_quatationentry.GST18` = **Total GST Amount** (`GST_Amount`).
     - `tbl_app_quatationentry.finalPrmium` = **Final Payable Premium** (`TotalPremium + GST18` = `Amount`).
   - **Anti-Double-Counting Invariant:**
     - Because `AtotalOwnDamPremium` already has `OD` (Company OD Discount) and `NoClaimBonus` (NCB) subtracted and `ZeroDepreciation` added, `PolicyBookingService` maps:
       $$\text{ODPermium} = \text{AtotalOwnDamPremium}$$
       $$\text{TPPermium} = \text{BtotalLiabilityPremium}$$
       $$\text{NetPermium} = \text{ODPermium} + \text{TPPermium} = \text{TotalPremium}$$
       $$\text{GST\_Amount} = \text{GST18}$$
       $$\text{Amount} = \text{NetPermium} + \text{GST\_Amount} = \text{finalPrmium}$$
     - `NCBPermium` (`NoClaimBonus`), `ODDiscount` (%), and `AddOn` (`ZeroDepreciation`) are stored on `tbl_transaction` as **component breakdown columns** and are **NEVER subtracted or added a second time** to `ODPermium` or `NetPermium`.

2. **Source 2 — Full Rating Input Revalidation (`calculation_input: PremiumCalculationRequest`)**:
   - When the booking request supplies `calculation_input` (either standalone or alongside a quotation to revalidate current tariff rates), `PolicyBookingService` invokes `RatingEngineService.calculate_premium(calculation_input)`.
   - The deterministic `PremiumBreakdownResponse` maps to `tbl_transaction` as follows:

| `PremiumBreakdownResponse` Field | `tbl_transaction` Column | Formula / Invariant |
|---|---|---|
| `total_idv` | `SumInsured` | `selected_idv + electrical_accessories + non_electrical_accessories + lpg_cng_kit_value + trailer_idv` |
| `imt23_loading_amount` | `Imt23` | `round_rupee(subtotal_od_before_imt23 * 15 / 100)` |
| `od_discount_percent` | `ODDiscount` | Company OD discount % (`0`–`100`, capped at `90%` for Reliance) |
| `ncb_percent` | `NCB`, `NCBPer` | Effective NCB % (`0, 20, 25, 35, 45, 50`; forced to `0` if `claim_in_previous_policy` or `business_type_id == 1` or `product_type_id == 2`) |
| `ncb_amount` | `NCBPermium` | `round_rupee(od_after_company_discount * ncb_percent / 100)` |
| `zero_dep_rate_percent` | `AddOnRate` | Zero-Dep rate % |
| `zero_dep_premium` | `AddOn` | `round_rupee(selected_idv * zero_dep_rate_percent / 100) + zero_dep_extra_amount` |
| `towing_charges_amount` | `TowingChargesAmt` | Extra towing coverage premium |
| `total_od_with_addons` | `ODPermium` | `net_od_premium + zero_dep_premium + towing_charges_amount` |
| `pa_owner_driver_premium` | `PACovertoOwner` | PA Owner-Driver premium |
| `ll_paid_driver_premium + ll_cleaner_premium + ll_coolie_premium` | `LegalLiabilitytoPaidDriver`, `PACoverDriverCleaner` | Paid driver / cleaner / coolie legal liability |
| `total_tp_premium` | `TPPermium` | Sum of all Section B Third-Party Liability items |
| `net_premium` | `NetPermium` | `ODPermium + TPPermium` |
| `total_gst` | `GST_Amount` | `gst_on_od_and_addons_18 + gst_on_basic_tp_12 + gst_on_other_tp_18` |
| `final_payable_premium` | `Amount`, `ProPosalAmt` | `NetPermium + GST_Amount` |

3. **Source 3 — Direct Underwriting Figures (`PolicyTransactionNew.aspx.cs` Manual / Assisted Insurer Quote Entry)**:
   - In back-office underwriting (`PolicyTransactionNew.aspx.cs`) or when converting an Assisted Quotation (`tbl_app_quotationrequest` where an insurer PDF quote was uploaded by `QUOT CO-ORDINATOR`), the operator enters the insurer's exact policy schedule figures (`od_premium`, `tp_premium`, `ncb_percent`, `ncb_amount`, `od_discount_percent`, `addon_premium`, `gst_amount`, `final_premium`).
   - `PolicyBookingService` enforces strict mathematical consistency checks on direct underwriting figures:

---

## 2. Mathematical Consistency & Revalidation Rules

### Rule 1 — NCB Slab & Eligibility Validation
- Allowed NCB slabs: `{0, 20, 25, 35, 45, 50}` (`Decimal`). Any other value raises `HTTP 422 Unprocessable Entity`.
- If `product_type_id == 2` (Liability Only / STP):
  - `ODPermium`, `NCB`, `NCBPermium`, `ODDiscount`, `AddOn`, `Imt23`, and `SumInsured` **must** equal `0.00` (automatically zeroed or rejected if non-zero OD is supplied on a TP-only policy).
- If `business_type_id == 1` (New Vehicle) or `claim_in_previous_policy == True`:
  - `NCB` and `NCBPermium` **must** equal `0.00`. Supplying positive NCB on a new vehicle or claimed previous policy raises `HTTP 422`.

### Rule 2 — Net Premium Identity (`NetPermium == ODPermium + TPPermium`)
- Across all policy types:
  $$\text{NetPermium} = \text{ODPermium} + \text{TPPermium}$$
- If caller supplies an explicit `net_premium` that deviates from `od_premium + tp_premium` by more than `₹1.00` (whole-rupee rounding tolerance), `PolicyBookingService` raises `HTTP 422 Unprocessable Entity` with a detailed discrepancy message.

### Rule 3 — GST Revalidation (18% Standard vs. GCV Split 12% / 18%)
- **Standard Categories (`PVT`, `TwoWheeler`, `PublicPCV3W`, `Misc-D`, `PassengerTaxi(PCV)`, `School_Bus`)**:
  $$\text{Expected GST} = \text{round\_rupee}\left(\frac{\text{NetPermium} \times 18}{100}\right)$$
- **Goods Carrying Vehicles (`Public_GCV`, `Private_GCV`, `PublicGCV3W`)**:
  - When `gcv_split_tp_gst = True` and `basic_tp_premium` is known:
    $$\text{GST}_{12} = \text{round\_rupee}\left(\frac{\text{BasicTP} \times 12}{100}\right)$$
    $$\text{GST}_{18} = \text{round\_rupee}\left(\frac{(\text{NetPermium} - \text{BasicTP}) \times 18}{100}\right)$$
    $$\text{Expected GST} = \text{GST}_{12} + \text{GST}_{18}$$
  - When uniform 18% GST is used (`gcv_split_tp_gst = False`):
    $$\text{Expected GST} = \text{round\_rupee}\left(\frac{\text{NetPermium} \times 18}{100}\right)$$
- If the caller supplies an explicit `gst_amount` that conflicts with the expected statutory GST (outside the `₹1.00` rounding band when statutory GST validation is enabled), `HTTP 422` is raised.

### Rule 4 — Final Payable Premium Identity (`Amount == NetPermium + GST_Amount`)
- For every transaction:
  $$\text{Amount} = \text{NetPermium} + \text{GST\_Amount}$$
- If the caller provides an explicit `final_premium` (`Amount`) that does not equal `NetPermium + GST_Amount`, `PolicyBookingService` raises `HTTP 422 Unprocessable Entity`.

### Rule 5 — Quotation Tamper Detection
- When `quotation_id` and `quotation_source_type = "SELF_QUOTATION"` are supplied without an authorized operator override flag (`allow_underwriting_override = False`):
  - If the caller also passes `final_premium` or `net_premium` in the request body that does not match the persisted quotation's `finalPrmium` / `TotalPremium`, `PolicyBookingService` rejects the request with `HTTP 422 Unprocessable Entity` (`"Submitted premium does not match quotation breakdown"`).
