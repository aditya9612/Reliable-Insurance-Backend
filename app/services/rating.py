"""
Deterministic Motor Insurance Rating Engine Service (Phase 6).

Implements exact legacy stored procedure and WebForm calculation parity:
- sp_SelectMgfyearOfyearmonth (Vehicle age calculation with 0.0 / 0.1 threshold & CEIL)
- sp_SelectIDVDetails / sp_SelectIDVDetailsForGCV (Base IDV & +/-15% band)
- sp_quot_damagepremium & CC rate tables (OD base rate across all 9 vehicle categories)
- GVW > 12000 kg commercial tonnage loading ((GVW - 12000) * 27 / 100)
- Accessories (Electrical 4%, Non-Electrical basic rate%, External LPG/CNG 4%, Inbuilt 5%)
- IMT-23 15% loading on gross OD before discounts
- Own Premises (33%), Anti-Theft (2.5% max 500), Voluntary Deductible slabs
- Company OD Discount lookup (sp_SelectAppDiscWithFueltype / GCV / Fallback) + Reliance 90% cap
- NCB slabs (0, 20, 25, 35, 45, 50%) applied on post-discount OD (reset to 0% on claim/new)
- Zero-Dep & Add-On lookup + Towing slabs
- sp_quot_liabilitypremium & passenger LL + PA Owner-Driver + LL Paid Driver/Cleaner/Coolie/NFPP
- Split GST (18% OD/Add-on + 12% Basic TP for GCV) and uniform 18% GST for non-GCV
"""
from datetime import date
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_UP
from typing import List
from fastapi import HTTPException, status

from app.repositories.quotation import QuotationRepository, _to_decimal
from app.schemas.quotation import (
    MultiInsurerCompareRequest,
    MultiInsurerCompareResponse,
    PremiumBreakdownResponse,
    PremiumCalculationRequest,
)


HUNDRED = Decimal("100")
ZERO = Decimal("0.00")
ONE_RUPEE = Decimal("1")
GCV_TP_GST_CUTOVER_DATE = date(2025, 9, 23)


def round_rupee(val: Decimal) -> Decimal:
    """Rounds a Decimal monetary amount to the nearest whole rupee using ROUND_HALF_UP."""
    return val.quantize(ONE_RUPEE, rounding=ROUND_HALF_UP)


class RatingEngineService:
    """Stateless deterministic rating calculation service."""

    def __init__(self, repo: QuotationRepository) -> None:
        self.repo = repo

    @staticmethod
    def resolve_gcv_basic_tp_gst_rate(
        *,
        risk_start_date: date | None = None,
        calculation_date: date | None = None,
        apply_cutover: bool = False,
        rate_override: Decimal | None = None,
    ) -> Decimal:
        """
        Resolves the GCV Basic TP GST rate:
        - `adm_PolicyDetails.aspx.cs:L636-644` cutover on `2025-09-23`:
          - `>= 2025-09-23` -> `5%`
          - `< 2025-09-23` -> `12%`
        - `SelfQuotationRequest.aspx.cs:L2555-2561` fallback (when `risk_start_date` is omitted
          and `apply_cutover` is False) -> `12%`.
        """
        if rate_override is not None:
            return rate_override
        if risk_start_date is not None or apply_cutover:
            eff_date = risk_start_date or calculation_date or date.today()
            return Decimal("5") if eff_date >= GCV_TP_GST_CUTOVER_DATE else Decimal("12")
        return Decimal("12")

    @staticmethod
    def calculate_vehicle_age(
        registration_date: date,
        calculation_date: date,
    ) -> Decimal:
        """
        Exact parity with legacy MySQL stored procedure sp_SelectMgfyearOfyearmonth:
        V_MonthCount = CONVERT((TIMESTAMPDIFF(DAY, P_Date, CURRENT_DATE) * 1.0 / 365), DECIMAL(4,1))
        If V_MonthCount in (0.0, 0.1) -> 0.0
        Else -> CONVERT(CEIL(TIMESTAMPDIFF(DAY, P_Date, CURRENT_DATE) * 1.0 / 365), DECIMAL(4,1))
        """
        days = max(0, (calculation_date - registration_date).days)
        raw_ratio = Decimal(days) / Decimal("365")
        v_month_count = raw_ratio.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
        if v_month_count in {Decimal("0.0"), Decimal("0.1")}:
            return Decimal("0.0")
        ceil_years = raw_ratio.to_integral_value(rounding=ROUND_CEILING)
        return ceil_years.quantize(Decimal("0.1"))

    @staticmethod
    def calculate_idv_band(base_idv: Decimal) -> tuple[Decimal, Decimal]:
        """
        Calculates legacy +/-15% permissible IDV band around base variant IDV:
        [base_idv - floor(base_idv * 15 / 100), base_idv + floor(base_idv * 15 / 100)]
        """
        if base_idv <= ZERO:
            return ZERO, ZERO
        delta = ((base_idv * Decimal("15")) / HUNDRED).quantize(ONE_RUPEE, rounding=ROUND_FLOOR)
        return base_idv - delta, base_idv + delta

    @staticmethod
    def _calculate_voluntary_deductible(
        category: str,
        slab: int,
        od_base: Decimal,
    ) -> Decimal:
        """Calculates voluntary deductible discount based on IRDAI / legacy slabs."""
        if slab <= 0 or od_base <= ZERO:
            return ZERO
        if category == "PVT":
            slab_map = {
                2500: (Decimal("20"), Decimal("750")),
                5000: (Decimal("25"), Decimal("1500")),
                7500: (Decimal("30"), Decimal("2000")),
                15000: (Decimal("35"), Decimal("2500")),
            }
            if slab in slab_map:
                pct, cap = slab_map[slab]
                return min(round_rupee((od_base * pct) / HUNDRED), cap)
        elif category == "TwoWheeler":
            slab_map_2w = {
                500: (Decimal("5"), Decimal("50")),
                750: (Decimal("10"), Decimal("75")),
                1000: (Decimal("15"), Decimal("125")),
                1500: (Decimal("20"), Decimal("200")),
                3000: (Decimal("25"), Decimal("250")),
            }
            if slab in slab_map_2w:
                pct, cap = slab_map_2w[slab]
                return min(round_rupee((od_base * pct) / HUNDRED), cap)
        return ZERO

    async def calculate_premium(
        self,
        req: PremiumCalculationRequest,
    ) -> PremiumBreakdownResponse:
        """
        Executes the full 9-step deterministic motor rating sequence.
        """
        category = req.vehicle_category
        calc_date = req.calculation_date or date.today()

        # Step 1: Vehicle Age Determination (sp_SelectMgfyearOfyearmonth)
        if req.vehicle_age_override is not None:
            vehicle_age = req.vehicle_age_override.quantize(Decimal("0.1"))
        elif req.registration_date is not None:
            if req.registration_date > calc_date:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="registration_date cannot be after calculation_date.",
                )
            vehicle_age = self.calculate_vehicle_age(req.registration_date, calc_date)
        elif req.business_type_id == 1:
            vehicle_age = Decimal("0.0")
        else:
            vehicle_age = Decimal("1.0")

        # Legacy WebForms cap Age > 10 to 11.0 when querying tbl_quot_damagepremium
        lookup_age = Decimal("11.0") if vehicle_age > Decimal("10.0") else vehicle_age.to_integral_value(rounding=ROUND_CEILING).quantize(Decimal("0.1"))
        if vehicle_age == Decimal("0.0"):
            lookup_age = Decimal("0.0")

        # Step 2: Resolve Base IDV & Permissible +/-15% Band
        body_price = ZERO
        chassis_price = ZERO
        base_idv = req.base_idv_override or ZERO

        if req.variant_id is not None and req.base_idv_override is None:
            variant = await self.repo.get_variant_by_id(req.variant_id)
            if variant is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"VehicleVariant with Variant_ID={req.variant_id} not found.",
                )
            if category in {"Public_GCV", "Private_GCV"} and not req.with_body:
                body_price = _to_decimal(variant.ExMumbai_Body_Price).quantize(ONE_RUPEE, rounding=ROUND_FLOOR)
                chassis_price = _to_decimal(variant.ExMumbai_Chasis_Price).quantize(ONE_RUPEE, rounding=ROUND_FLOOR)
                base_idv = body_price + chassis_price
            else:
                base_idv = _to_decimal(variant.ExMumbai_Model_Price).quantize(ONE_RUPEE, rounding=ROUND_FLOOR)

        if base_idv == ZERO and req.selected_idv is not None and req.product_type_id != 2:
            base_idv = req.selected_idv

        min_idv, max_idv = self.calculate_idv_band(base_idv)

        if req.product_type_id == 2:
            # Liability Only (STP) -> Zero IDV & Zero OD
            selected_idv = ZERO
            total_idv = ZERO
        else:
            selected_idv = req.selected_idv if req.selected_idv is not None else base_idv
            if req.validate_idv_band and base_idv > ZERO:
                if selected_idv < min_idv or selected_idv > max_idv:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail=(
                            f"selected_idv ({selected_idv}) is outside the permissible +/-15% band "
                            f"[{min_idv}, {max_idv}] for base_idv ({base_idv})."
                        ),
                    )
            total_idv = (
                selected_idv
                + req.electrical_accessories
                + req.non_electrical_accessories
                + req.lpg_cng_kit_value
                + req.trailer_idv
            )

        # Resolve Insurer Name if present in DB
        insurer = await self.repo.get_insurer_by_id(req.insurance_company_id)
        insurer_name = insurer.InsuranceCompany if insurer else f"Insurer #{req.insurance_company_id}"

        # Step 3-7: Own Damage (OD) & Add-On Calculation
        if req.product_type_id == 2:
            od_basic_rate_percent = ZERO
            basic_od_premium = ZERO
            gvw_above_12000_loading = ZERO
            electrical_accessories_od = ZERO
            non_electrical_accessories_od = ZERO
            lpg_cng_kit_od = ZERO
            inbuilt_lpg_cng_od = ZERO
            fiber_glass_tank_od = ZERO
            geographical_extension_od = ZERO
            subtotal_od_before_imt23 = ZERO
            imt23_loading_amount = ZERO
            gross_od_premium = ZERO
            own_premises_discount = ZERO
            anti_theft_discount = ZERO
            automobile_association_discount = ZERO
            voluntary_deductible_discount = ZERO
            od_after_tariff_discounts = ZERO
            od_discount_percent = ZERO
            od_discount_amount = ZERO
            od_after_company_discount = ZERO
            effective_ncb_percent = ZERO
            ncb_amount = ZERO
            net_od_premium = ZERO
            zero_dep_rate_percent = ZERO
            zero_dep_extra_amount = ZERO
            zero_dep_premium = ZERO
            towing_charges_amount = ZERO
            total_od_with_addons = ZERO
            is_declined = False
        else:
            od_basic_rate_percent = await self.repo.get_od_base_tariff(
                company_type=category,
                cc=req.cubic_capacity,
                lookup_age=lookup_age,
                zone=req.zone,
            )
            basic_od_premium = round_rupee((selected_idv * od_basic_rate_percent) / HUNDRED)

            if category in {"Public_GCV", "Private_GCV"} and req.gross_vehicle_weight > 12000:
                # C# integer division parity: (((Convert.ToInt32(txt_VehicleWeight.Text) - 12000) * 27) / 100)
                gvw_above_12000_loading = Decimal(((int(req.gross_vehicle_weight) - 12000) * 27) // 100)
            else:
                gvw_above_12000_loading = ZERO

            electrical_accessories_od = round_rupee(
                (req.electrical_accessories * Decimal("4")) / HUNDRED
            )
            non_electrical_accessories_od = round_rupee(
                (req.non_electrical_accessories * od_basic_rate_percent) / HUNDRED
            )
            lpg_cng_kit_od = round_rupee((req.lpg_cng_kit_value * Decimal("4")) / HUNDRED)
            if req.inbuilt_lpg_cng:
                inbuilt_lpg_cng_od = round_rupee(
                    ((basic_od_premium + non_electrical_accessories_od) * Decimal("5")) / HUNDRED
                )
            else:
                inbuilt_lpg_cng_od = ZERO

            if req.fiber_glass_tank:
                fiber_glass_tank_od = (
                    Decimal("100")
                    if category in {"Public_GCV", "Private_GCV", "School_Bus", "Misc-D"}
                    else Decimal("50")
                )
            else:
                fiber_glass_tank_od = ZERO

            geographical_extension_od = Decimal("400") if req.geographical_extension else ZERO

            subtotal_od_before_imt23 = (
                basic_od_premium
                + gvw_above_12000_loading
                + electrical_accessories_od
                + non_electrical_accessories_od
                + lpg_cng_kit_od
                + inbuilt_lpg_cng_od
                + fiber_glass_tank_od
                + geographical_extension_od
            )

            imt23_loading_amount = (
                round_rupee((subtotal_od_before_imt23 * Decimal("15")) / HUNDRED)
                if req.imt23
                else ZERO
            )
            gross_od_premium = subtotal_od_before_imt23 + imt23_loading_amount

            # Step 5: Tariff & Statutory OD Discounts
            own_premises_discount = (
                round_rupee((gross_od_premium * Decimal("33")) / HUNDRED)
                if req.own_premises
                else ZERO
            )
            od_after_own_premises = max(ZERO, gross_od_premium - own_premises_discount)

            anti_theft_discount = (
                min(
                    round_rupee((od_after_own_premises * Decimal("2.5")) / HUNDRED),
                    Decimal("500"),
                )
                if req.anti_theft
                else ZERO
            )
            automobile_association_discount = (
                min(
                    round_rupee((od_after_own_premises * Decimal("5")) / HUNDRED),
                    Decimal("200"),
                )
                if req.automobile_association_discount
                else ZERO
            )
            voluntary_deductible_discount = self._calculate_voluntary_deductible(
                category=category,
                slab=req.voluntary_deductible_slab,
                od_base=od_after_own_premises,
            )

            od_after_tariff_discounts = max(
                ZERO,
                gross_od_premium
                - own_premises_discount
                - anti_theft_discount
                - automobile_association_discount
                - voluntary_deductible_discount,
            )

            # Step 6: Company OD Discount & NCB Sequence
            # Resolve effective NCB first (reset to 0% if claim in prev policy, no prev policy, or new vehicle)
            if (
                req.claim_in_previous_policy
                or not req.prev_policy_available
                or req.business_type_id == 1
            ):
                effective_ncb_percent = Decimal("0")
            else:
                effective_ncb_percent = req.ncb_percent

            db_od_disc, is_declined = await self.repo.get_od_discount_and_decline(
                vehicle_category=category,
                make_id=req.make_id,
                model_id=req.model_id,
                insurance_company_id=req.insurance_company_id,
                age=vehicle_age,
                ncb_percent=effective_ncb_percent,
                cluster_id=req.cluster_id,
                zero_dep=req.zero_dep,
                fuel_type_id=req.fuel_type_id,
                business_type_id=req.business_type_id,
                bus_type=req.bus_type or "SCHOOL BUS",
            )
            od_discount_percent = (
                req.od_discount_override if req.od_discount_override is not None else db_od_disc
            )

            # Reliance OD Discount Cap (RelianceCapping = 90 in Web.config for InsuranceCompanyId == 7)
            if req.insurance_company_id == 7 and od_discount_percent > Decimal("90"):
                od_discount_percent = Decimal("90")

            od_discount_amount = round_rupee(
                (od_after_tariff_discounts * od_discount_percent) / HUNDRED
            )
            od_after_company_discount = max(ZERO, od_after_tariff_discounts - od_discount_amount)

            ncb_amount = round_rupee(
                (od_after_company_discount * effective_ncb_percent) / HUNDRED
            )
            net_od_premium = max(ZERO, od_after_company_discount - ncb_amount)

            # Step 7: Zero-Depreciation & Towing Add-Ons
            if req.zero_dep:
                db_zd_rate, db_zd_extra = await self.repo.get_zero_dep_rates(
                    insurance_company_id=req.insurance_company_id,
                    make_id=req.make_id,
                    model_id=req.model_id,
                    veh_type_id=req.veh_type_id,
                    fuel_type_id=req.fuel_type_id,
                    business_type_id=req.business_type_id,
                    cluster_id=req.cluster_id,
                    ncb_percent=effective_ncb_percent,
                    age=vehicle_age,
                    addon_plan=req.addon_plan,
                )
                zero_dep_rate_percent = (
                    req.zero_dep_rate_override
                    if req.zero_dep_rate_override is not None
                    else db_zd_rate
                )
                zero_dep_extra_amount = db_zd_extra
                zero_dep_premium = round_rupee(
                    ((selected_idv * zero_dep_rate_percent) / HUNDRED) + zero_dep_extra_amount
                )
            else:
                zero_dep_rate_percent = ZERO
                zero_dep_extra_amount = ZERO
                zero_dep_premium = ZERO

            _, db_towing = await self.repo.get_pa_owner_driver_and_towing(
                insurance_company_id=req.insurance_company_id,
                towing_selection=req.towing_selection,
            )
            if req.towing_override is not None:
                towing_charges_amount = round_rupee(req.towing_override)
            elif req.towing_selection > ZERO:
                towing_charges_amount = round_rupee(db_towing)
            else:
                towing_charges_amount = ZERO

            total_od_with_addons = net_od_premium + zero_dep_premium + towing_charges_amount

        # Step 8: Third-Party (TP) Liability Calculation
        if req.product_type_id == 3:
            # Standalone OD (SAOD) -> Zero TP
            basic_tp_premium = ZERO
            passenger_ll_premium = ZERO
            lpg_cng_tp_premium = ZERO
            geographical_extension_tp = ZERO
            pa_owner_driver_premium = ZERO
            ll_paid_driver_premium = ZERO
            ll_cleaner_coolie_premium = ZERO
            ll_employee_premium = ZERO
            nfpp_premium = ZERO
            pa_paid_driver_premium = ZERO
            pa_unnamed_passenger_premium = ZERO
            pa_pillion_rider_premium = ZERO
            trailer_tp_premium = ZERO
            tppd_discount = ZERO
            total_tp_premium = ZERO
        else:
            tp_unit = (
                req.gross_vehicle_weight
                if (
                    category in {"Public_GCV", "Private_GCV", "School_Bus"}
                    and req.gross_vehicle_weight > 0
                )
                else req.cubic_capacity
            )
            basic_tp_raw, per_pass_rate = await self.repo.get_tp_base_tariff(
                company_type=category,
                unit_value=tp_unit,
                bus_type=req.bus_type or "SCHOOL BUS",
                age=vehicle_age,
            )
            basic_tp_premium = round_rupee(basic_tp_raw)

            if category in {"PassengerTaxi(PCV)", "School_Bus", "PublicPCV3W"}:
                passenger_ll_premium = round_rupee(Decimal(req.seating_capacity) * per_pass_rate)
            else:
                passenger_ll_premium = ZERO

            if (
                req.lpg_cng_tp_liability
                or req.lpg_cng_kit_value > ZERO
                or req.inbuilt_lpg_cng
            ):
                lpg_cng_tp_premium = Decimal("60")
            else:
                lpg_cng_tp_premium = ZERO

            geographical_extension_tp = Decimal("100") if req.geographical_extension else ZERO

            if req.pa_to_owner_driver:
                if req.pa_owner_driver_override is not None:
                    pa_owner_driver_premium = round_rupee(req.pa_owner_driver_override)
                else:
                    pa_rate, _ = await self.repo.get_pa_owner_driver_and_towing(
                        insurance_company_id=req.insurance_company_id
                    )
                    pa_owner_driver_premium = round_rupee(pa_rate)
            else:
                pa_owner_driver_premium = ZERO

            ll_paid_driver_premium = Decimal(req.ll_paid_driver_count) * Decimal("50")
            ll_cleaner_coolie_premium = (
                Decimal(req.ll_cleaner_count + req.ll_coolie_count) * Decimal("50")
            )
            ll_employee_premium = Decimal(req.ll_employee_count) * Decimal("50")
            nfpp_premium = Decimal(req.nfpp_count) * Decimal("75")
            pa_paid_driver_premium = round_rupee(req.pa_paid_driver_amount)
            pa_unnamed_passenger_premium = round_rupee(req.pa_unnamed_passenger_amount)
            pa_pillion_rider_premium = round_rupee(req.pa_pillion_rider_amount)
            trailer_tp_premium = Decimal(req.no_of_trailers) * Decimal("2485")

            if req.tppd_restriction:
                if category == "TwoWheeler":
                    tppd_discount = Decimal("50")
                elif category in {"PublicGCV3W", "PublicPCV3W"}:
                    tppd_discount = Decimal("150")
                else:
                    tppd_discount = Decimal("200")
            else:
                tppd_discount = ZERO

            total_tp_premium = max(
                ZERO,
                basic_tp_premium
                + passenger_ll_premium
                + lpg_cng_tp_premium
                + geographical_extension_tp
                + pa_owner_driver_premium
                + ll_paid_driver_premium
                + ll_cleaner_coolie_premium
                + ll_employee_premium
                + nfpp_premium
                + pa_paid_driver_premium
                + pa_unnamed_passenger_premium
                + pa_pillion_rider_premium
                + trailer_tp_premium
                - tppd_discount,
            )

        # Step 9: Net Premium, GST & Final Payable
        net_premium = total_od_with_addons + total_tp_premium

        if (
            category in {"Public_GCV", "Private_GCV", "PublicGCV3W"}
            and req.gcv_split_tp_gst
            and basic_tp_premium > ZERO
        ):
            gcv_tp_gst_rate = self.resolve_gcv_basic_tp_gst_rate(
                risk_start_date=req.risk_start_date,
                calculation_date=req.calculation_date,
                apply_cutover=req.apply_gcv_2025_09_23_tp_gst_cutover,
                rate_override=req.gcv_basic_tp_gst_rate_override,
            )
            gst_on_od_and_other_tp = round_rupee(
                ((net_premium - basic_tp_premium) * Decimal("18")) / HUNDRED
            )
            gst_on_basic_tp = round_rupee((basic_tp_premium * gcv_tp_gst_rate) / HUNDRED)
            total_gst_amount = gst_on_od_and_other_tp + gst_on_basic_tp
        else:
            gcv_tp_gst_rate = ZERO
            gst_on_od_and_other_tp = round_rupee((net_premium * Decimal("18")) / HUNDRED)
            gst_on_basic_tp = ZERO
            total_gst_amount = gst_on_od_and_other_tp

        final_payable_premium = net_premium + total_gst_amount

        return PremiumBreakdownResponse(
            insurance_company_id=req.insurance_company_id,
            insurance_company_name=insurer_name,
            vehicle_category=category,
            product_type_id=req.product_type_id,
            business_type_id=req.business_type_id,
            zone=req.zone,
            vehicle_age=vehicle_age,
            lookup_age=lookup_age,
            base_idv=base_idv,
            min_idv=min_idv,
            max_idv=max_idv,
            selected_idv=selected_idv,
            body_price=body_price,
            chassis_price=chassis_price,
            total_idv=total_idv,
            od_basic_rate_percent=od_basic_rate_percent,
            basic_od_premium=basic_od_premium,
            gvw_above_12000_loading=gvw_above_12000_loading,
            electrical_accessories_od=electrical_accessories_od,
            non_electrical_accessories_od=non_electrical_accessories_od,
            lpg_cng_kit_od=lpg_cng_kit_od,
            inbuilt_lpg_cng_od=inbuilt_lpg_cng_od,
            fiber_glass_tank_od=fiber_glass_tank_od,
            geographical_extension_od=geographical_extension_od,
            subtotal_od_before_imt23=subtotal_od_before_imt23,
            imt23_loading_amount=imt23_loading_amount,
            gross_od_premium=gross_od_premium,
            own_premises_discount=own_premises_discount,
            anti_theft_discount=anti_theft_discount,
            automobile_association_discount=automobile_association_discount,
            voluntary_deductible_discount=voluntary_deductible_discount,
            od_after_tariff_discounts=od_after_tariff_discounts,
            od_discount_percent=od_discount_percent,
            od_discount_amount=od_discount_amount,
            od_after_company_discount=od_after_company_discount,
            ncb_percent=effective_ncb_percent,
            ncb_amount=ncb_amount,
            net_od_premium=net_od_premium,
            zero_dep_rate_percent=zero_dep_rate_percent,
            zero_dep_extra_amount=zero_dep_extra_amount,
            zero_dep_premium=zero_dep_premium,
            towing_charges_amount=towing_charges_amount,
            total_od_with_addons=total_od_with_addons,
            basic_tp_premium=basic_tp_premium,
            passenger_ll_premium=passenger_ll_premium,
            lpg_cng_tp_premium=lpg_cng_tp_premium,
            geographical_extension_tp=geographical_extension_tp,
            pa_owner_driver_premium=pa_owner_driver_premium,
            ll_paid_driver_premium=ll_paid_driver_premium,
            ll_cleaner_coolie_premium=ll_cleaner_coolie_premium,
            ll_employee_premium=ll_employee_premium,
            nfpp_premium=nfpp_premium,
            pa_paid_driver_premium=pa_paid_driver_premium,
            pa_unnamed_passenger_premium=pa_unnamed_passenger_premium,
            pa_pillion_rider_premium=pa_pillion_rider_premium,
            trailer_tp_premium=trailer_tp_premium,
            tppd_discount=tppd_discount,
            total_tp_premium=total_tp_premium,
            net_premium=net_premium,
            gst_on_od_and_other_tp=gst_on_od_and_other_tp,
            gst_on_basic_tp=gst_on_basic_tp,
            gcv_basic_tp_gst_rate_percent=gcv_tp_gst_rate,
            total_gst_amount=total_gst_amount,
            final_payable_premium=final_payable_premium,
            is_declined=is_declined,
        )

    async def compare_insurers(
        self,
        req: MultiInsurerCompareRequest,
    ) -> MultiInsurerCompareResponse:
        """
        Calculates side-by-side premium breakdowns across all requested or eligible
        insurers for the vehicle category (sp_SelectInsuranceCompanyByVehicleType parity).
        """
        company_ids = req.insurance_company_ids
        if not company_ids:
            company_ids = await self.repo.get_eligible_insurers_for_category(
                req.calculation_input.vehicle_category
            )

        comparisons: List[PremiumBreakdownResponse] = []
        for comp_id in company_ids:
            cloned_input = req.calculation_input.model_copy(
                update={"insurance_company_id": comp_id}
            )
            breakdown = await self.calculate_premium(cloned_input)
            comparisons.append(breakdown)

        return MultiInsurerCompareResponse(
            vehicle_category=req.calculation_input.vehicle_category,
            product_type_id=req.calculation_input.product_type_id,
            comparisons=comparisons,
        )
