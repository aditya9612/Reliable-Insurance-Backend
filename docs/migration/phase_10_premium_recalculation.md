# Phase 10 — Endorsement Premium Recalculation & Delta Engine (`phase_10_premium_recalculation.md`)

## 1. Overview
This document defines the exact arithmetic and rounding rules for recalculating motor policy premiums during financial endorsements (`IDV_CHANGE`, `NCB_CORRECTION`, `COVERAGE_ADDON_CHANGE`, `OWNERSHIP_TRANSFER`) in Phase 10.

In accordance with the Phase 10 Master Prompt, this engine reuses the canonical Phase 6 (`RatingEngineService`) and Phase 7 (`validate_premium_breakdown`) premium equations and `Decimal` `ROUND_HALF_UP` quantization (`0.01`).

---

## 2. Premium Components & Equations

All calculations operate on `Decimal` quantized to `0.01` with `ROUND_HALF_UP`.

### 2.1 Existing Snapshot (`Old*` Values from `tbl_transaction`)
- $\text{OldIDV} = \text{tbl\_transaction.SumInsured}$
- $\text{OldNCBPercent} = \text{tbl\_transaction.NCB}$
- $\text{OldODPremium} = \text{tbl\_transaction.ODPermium}$
- $\text{OldTPPremium} = \text{tbl\_transaction.TPPermium}$
- $\text{OldNetPremium} = \text{tbl\_transaction.NetPermium}$
- $\text{OldGSTAmount} = \text{tbl\_transaction.GST\_Amount}$
- $\text{OldFinalPremium} = \text{tbl\_transaction.Amount}$

### 2.2 Recalculated Snapshot (`New*` Values)
Depending on the `EndorsementType`:

1. **Non-Financial Endorsements** (`NAME_CORRECTION`, `ADDRESS_CORRECTION`, `CONTACT_CORRECTION`, `VEHICLE_REGISTRATION_CORRECTION`, `ENGINE_CHASSIS_CORRECTION`, `HYPOTHECATION_CHANGE`, `NOMINEE_CHANGE`, and `OWNERSHIP_TRANSFER` without NCB recovery):
   - $\text{NewODPremium} = \text{OldODPremium}$
   - $\text{NewTPPremium} = \text{OldTPPremium}$
   - $\text{NewNetPremium} = \text{OldNetPremium}$
   - $\text{NewGSTAmount} = \text{OldGSTAmount}$
   - $\text{NewFinalPremium} = \text{OldFinalPremium}$
   - $\Delta \text{Premium} = \text{Decimal}(\text{"0.00"})$
   - `EndorsementCategory = "NON_FINANCIAL"`

2. **IDV Change (`IDV_CHANGE`)**:
   - If explicit `new_od_premium` is provided in the endorsement payload, it is validated; otherwise, if $\text{OldIDV} > 0$, the base OD scales proportionally with $\frac{\text{NewIDV}}{\text{OldIDV}}$ net of NCB:
     $$\text{NewODPremium} = \text{round\_half\_up}\left(\text{OldODPremium} \times \frac{\text{NewIDV}}{\text{OldIDV}}, 0.01\right)$$
   - Other non-OD components ($\text{AddOn} + \text{TPPermium} + \text{PA/LL covers}$) remain unchanged:
     $$\text{OtherNet} = \text{OldNetPremium} - \text{OldODPremium}$$
     $$\text{NewNetPremium} = \text{NewODPremium} + \text{OtherNet}$$

3. **NCB Correction / NCB Recovery (`NCB_CORRECTION` / `OWNERSHIP_TRANSFER`)**:
   - Let $\text{OldNCB} = \text{OldNCBPercent}$ ($0 \le \text{OldNCB} < 100$) and $\text{NewNCB} = \text{NewNCBPercent}$ ($0 \le \text{NewNCB} < 100$).
   - If explicit `new_od_premium` is not overridden, the pre-NCB gross OD is derived from $\text{OldODPremium}$:
     $$\text{GrossOD} = \frac{\text{OldODPremium}}{1 - \frac{\text{OldNCB}}{100}}$$
     $$\text{NewNCBPremium} = \text{round\_half\_up}\left(\text{GrossOD} \times \frac{\text{NewNCB}}{100}, 0.01\right)$$
     $$\text{NewODPremium} = \text{round\_half\_up}\left(\text{GrossOD} - \text{NewNCBPremium}, 0.01\right)$$
   - $\text{NewNetPremium} = \text{NewODPremium} + (\text{OldNetPremium} - \text{OldODPremium})$.

4. **Coverage / Add-On Change (`COVERAGE_ADDON_CHANGE`)**:
   - Let $\Delta \text{AddOn}, \Delta \text{PA}, \Delta \text{LL}, \Delta \text{OD}, \Delta \text{TP}$ be the delta of modified coverage/add-on fields.
   - $\text{NewODPremium} = \text{OldODPremium} + \Delta \text{OD}$
   - $\text{NewTPPremium} = \text{OldTPPremium} + \Delta \text{TP}$
   - $\text{NewNetPremium} = \text{OldNetPremium} + \Delta \text{OD} + \Delta \text{TP} + \Delta \text{AddOn} + \Delta \text{PA} + \Delta \text{LL}$.

---

## 3. GST & Final Premium Delta Calculation

### 3.1 Effective GST Rate Preservation
To preserve exact parity with the booked policy's GST regime (typically `18.00%` standard motor GST, or component-specific GST on `tbl_transaction`):
- If `new_gst_amount` is explicitly supplied, it is verified against `validate_premium_breakdown`.
- Otherwise, the effective GST rate $r_{\text{gst}}$ from the booked policy (defaulting to `18.00%` if $\text{OldNetPremium} == 0$, or $\frac{\text{OldGSTAmount}}{\text{OldNetPremium}}$ when exact) is applied to the net premium delta:
  $$\Delta \text{Net} = \text{NewNetPremium} - \text{OldNetPremium}$$
  $$\Delta \text{GST} = \text{round\_half\_up}\left(\Delta \text{Net} \times r_{\text{gst}}, 0.01\right)$$
  $$\text{NewGSTAmount} = \text{OldGSTAmount} + \Delta \text{GST}$$
  $$\text{NewFinalPremium} = \text{NewNetPremium} + \text{NewGSTAmount}$$
  $$\text{PremiumDelta} = \text{NewFinalPremium} - \text{OldFinalPremium}$$

### 3.2 Endorsement Category Classification
- If `EndorsementType` is one of the 7 non-financial correction types: `EndorsementCategory = "NON_FINANCIAL"`, $\text{PremiumDelta} = 0.00$.
- Else if $\text{PremiumDelta} > 0.00$: `EndorsementCategory = "ADDITIONAL_PREMIUM"`.
- Else if $\text{PremiumDelta} < 0.00$: `EndorsementCategory = "REFUND_PREMIUM"`.
- Else ($\text{PremiumDelta} == 0.00$): `EndorsementCategory = "ZERO_PREMIUM"`.
