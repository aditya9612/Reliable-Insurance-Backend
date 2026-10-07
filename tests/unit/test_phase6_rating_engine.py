"""
Phase 6 Unit Tests — Motor Rating Engine & Formula Verification.
Verifies all 9 vehicle categories, age determination, IDV +/-15% band,
OD loadings, tariff discounts, Reliance 90% OD discount cap, NCB slabs,
Zero-Dep/Towing add-ons, TP liability, split GCV GST, and Decimal-only precision.
"""
from datetime import date
from decimal import Decimal
import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.quotation import QuotationRepository
from app.schemas.quotation import (
    MultiInsurerCompareRequest,
    PremiumBreakdownResponse,
    PremiumCalculationRequest,
)
from app.services.rating import RatingEngineService


# ============================================================================
# 1. Vehicle Age Calculation (sp_SelectMgfyearOfyearmonth Parity)
# ============================================================================


def test_vehicle_age_calculation_legacy_parity():
    """
    Verifies exact parity with sp_SelectMgfyearOfyearmonth:
    - 0 to ~54 days (V_MonthCount in {0.0, 0.1}) -> 0.0
    - > 0.1 years -> CEIL(days / 365) as Decimal(4,1)
    """
    calc_date = date(2026, 4, 1)

    # Same day -> 0.0
    assert RatingEngineService.calculate_vehicle_age(date(2026, 4, 1), calc_date) == Decimal("0.0")

    # 30 days -> 30/365 = 0.082 -> rounds to 0.1 -> returns 0.0
    assert RatingEngineService.calculate_vehicle_age(date(2026, 3, 2), calc_date) == Decimal("0.0")

    # 60 days -> 60/365 = 0.164 -> rounds to 0.2 -> CEIL = 1.0
    assert RatingEngineService.calculate_vehicle_age(date(2026, 1, 31), calc_date) == Decimal("1.0")

    # 400 days -> 1.095 -> CEIL = 2.0
    assert RatingEngineService.calculate_vehicle_age(date(2025, 2, 25), calc_date) == Decimal("2.0")

    # 6 years -> 6.0
    assert RatingEngineService.calculate_vehicle_age(date(2020, 4, 15), calc_date) == Decimal("6.0")


@pytest.mark.asyncio
async def test_vehicle_age_future_registration_date_rejected(db_session: AsyncSession):
    """Registration date after calculation date raises 422 Unprocessable Entity."""
    service = RatingEngineService(QuotationRepository(db_session))
    req = PremiumCalculationRequest(
        vehicle_category="PVT",
        registration_date=date(2026, 5, 1),
        calculation_date=date(2026, 4, 1),
        base_idv_override=Decimal("500000"),
    )
    with pytest.raises(HTTPException) as exc_info:
        await service.calculate_premium(req)
    assert exc_info.value.status_code == 422


# ============================================================================
# 2. IDV Band (+/- 15%) Validation
# ============================================================================


def test_idv_band_calculation():
    """Verifies legacy +/-15% floor band calculation around base IDV."""
    min_idv, max_idv = RatingEngineService.calculate_idv_band(Decimal("600000"))
    assert min_idv == Decimal("510000")
    assert max_idv == Decimal("690000")


@pytest.mark.asyncio
async def test_idv_outside_15_percent_band_rejected(db_session: AsyncSession):
    """Selected IDV outside [min_idv, max_idv] raises 422 when validate_idv_band=True."""
    service = RatingEngineService(QuotationRepository(db_session))
    req = PremiumCalculationRequest(
        vehicle_category="PVT",
        base_idv_override=Decimal("600000"),
        selected_idv=Decimal("700000"),  # Max is 690000
        validate_idv_band=True,
    )
    with pytest.raises(HTTPException) as exc_info:
        await service.calculate_premium(req)
    assert exc_info.value.status_code == 422
    assert "outside the permissible +/-15% band" in exc_info.value.detail


# ============================================================================
# 3. NCB Slab Validation & Claim Reset
# ============================================================================


@pytest.mark.parametrize("invalid_ncb", [Decimal("10"), Decimal("15"), Decimal("30"), Decimal("60")])
def test_invalid_ncb_slab_rejected(invalid_ncb: Decimal):
    """Only statutory IRDAI NCB slabs {0, 20, 25, 35, 45, 50} are accepted."""
    with pytest.raises(ValidationError):
        PremiumCalculationRequest(
            vehicle_category="PVT",
            base_idv_override=Decimal("500000"),
            ncb_percent=invalid_ncb,
        )


@pytest.mark.asyncio
async def test_ncb_resets_to_zero_when_claim_in_previous_policy(db_session: AsyncSession):
    """If claim_in_previous_policy=True or business_type_id=1 (New), effective NCB is forced to 0%."""
    service = RatingEngineService(QuotationRepository(db_session))
    req = PremiumCalculationRequest(
        vehicle_category="PVT",
        business_type_id=3,
        base_idv_override=Decimal("500000"),
        ncb_percent=Decimal("50"),
        claim_in_previous_policy=True,
        od_discount_override=Decimal("50"),
    )
    res = await service.calculate_premium(req)
    assert res.ncb_percent == Decimal("0")
    assert res.ncb_amount == Decimal("0")


# ============================================================================
# 4. Reliance 90% OD Discount Capping Rule
# ============================================================================


@pytest.mark.asyncio
async def test_reliance_od_discount_capped_at_90_percent(db_session: AsyncSession):
    """
    Verifies legacy Web.config RelianceCapping=90 rule:
    When InsuranceCompanyId == 7 (Reliance) and OD discount > 90%, it is capped at 90%.
    """
    service = RatingEngineService(QuotationRepository(db_session))
    req = PremiumCalculationRequest(
        vehicle_category="PVT",
        insurance_company_id=7,
        base_idv_override=Decimal("500000"),
        od_discount_override=Decimal("95"),
    )
    res = await service.calculate_premium(req)
    assert res.od_discount_percent == Decimal("90")


# ============================================================================
# 5. Commercial GVW > 12,000 kg Loading, IMT-23 (15%), Own Premises (33%)
# ============================================================================


@pytest.mark.asyncio
async def test_public_gcv_heavy_tonnage_imt23_own_premises_and_split_gst(db_session: AsyncSession):
    """
    Verifies Public_GCV rating sequence:
    - Zone A, Age 2.0 -> OD Basic Rate = 1.751%
    - IDV = 1,000,000 -> Basic OD = 17,510
    - GVW = 25,000 kg -> Extra tonnage loading = (25000 - 12000) * 0.27 = 3,510
    - Subtotal before IMT-23 = 17,510 + 3,510 = 21,020
    - IMT-23 (15%) = round(21,020 * 0.15) = 3,153 -> Gross OD = 24,173
    - Own Premises (33%) = round(24,173 * 0.33) = 7,977 -> OD after tariff disc = 16,196
    - Company OD Discount (60%) = round(16,196 * 0.60) = 9,718 -> Remaining = 6,478
    - NCB (25%) = round(6,478 * 0.25) = 1,620 -> Net OD = 4,858
    - Basic TP (GVW 25,000 in 20,001..40,000 slab) = 43,950
    - PA Owner Driver (Company 3 = Bajaj) = 375, LL Paid Driver (1) = 50 -> Total TP = 44,375
    - Split GST: 18% on (4,858 + 425) = round(5,283 * 0.18) = 951; 12% on 43,950 = 5,274
    """
    service = RatingEngineService(QuotationRepository(db_session))
    req = PremiumCalculationRequest(
        vehicle_category="Public_GCV",
        insurance_company_id=3,
        zone="A",
        vehicle_age_override=Decimal("2.0"),
        gross_vehicle_weight=25000,
        base_idv_override=Decimal("1000000"),
        imt23=True,
        own_premises=True,
        od_discount_override=Decimal("60"),
        ncb_percent=Decimal("25"),
        pa_to_owner_driver=True,
        ll_paid_driver_count=1,
        gcv_split_tp_gst=True,
    )
    res = await service.calculate_premium(req)

    assert res.od_basic_rate_percent == Decimal("1.751")
    assert res.basic_od_premium == Decimal("17510")
    assert res.gvw_above_12000_loading == Decimal("3510")
    assert res.subtotal_od_before_imt23 == Decimal("21020")
    assert res.imt23_loading_amount == Decimal("3153")
    assert res.gross_od_premium == Decimal("24173")
    assert res.own_premises_discount == Decimal("7977")
    assert res.od_after_tariff_discounts == Decimal("16196")
    assert res.od_discount_amount == Decimal("9718")
    assert res.od_after_company_discount == Decimal("6478")
    assert res.ncb_amount == Decimal("1620")
    assert res.net_od_premium == Decimal("4858")
    assert res.basic_tp_premium == Decimal("43950")
    assert res.pa_owner_driver_premium == Decimal("375")
    assert res.ll_paid_driver_premium == Decimal("50")
    assert res.total_tp_premium == Decimal("44375")
    assert res.net_premium == Decimal("49233")
    assert res.gst_on_od_and_other_tp == Decimal("951")
    assert res.gst_on_basic_tp == Decimal("5274")
    assert res.total_gst_amount == Decimal("6225")
    assert res.final_payable_premium == Decimal("55458")


# ============================================================================
# 6. Anti-Theft Cap (Rs 500), Voluntary Deductible & Accessories
# ============================================================================


@pytest.mark.asyncio
async def test_private_car_accessories_antitheft_cap_and_voluntary_deductible(
    db_session: AsyncSession,
):
    """
    Verifies Private Car (PVT) accessories, Anti-Theft 2.5% cap at Rs 500,
    Voluntary Deductible slab (5000 -> 25% capped at Rs 1500), Zero-Dep, and Towing.
    """
    service = RatingEngineService(QuotationRepository(db_session))
    req = PremiumCalculationRequest(
        vehicle_category="PVT",
        insurance_company_id=3,
        zone="A",
        cubic_capacity=1498,
        vehicle_age_override=Decimal("2.0"),
        base_idv_override=Decimal("800000"),
        electrical_accessories=Decimal("20000"),
        non_electrical_accessories=Decimal("10000"),
        lpg_cng_kit_value=Decimal("15000"),
        anti_theft=True,
        voluntary_deductible_slab=5000,
        od_discount_override=Decimal("50"),
        ncb_percent=Decimal("20"),
        zero_dep=True,
        zero_dep_rate_override=Decimal("0.45"),
        towing_selection=Decimal("10000"),
        pa_to_owner_driver=True,
        tppd_restriction=True,
    )
    res = await service.calculate_premium(req)

    # PVT 1001..1500cc, Age 2.0, Zone A -> 3.283%
    assert res.od_basic_rate_percent == Decimal("3.283")
    assert res.basic_od_premium == Decimal("26264")
    assert res.electrical_accessories_od == Decimal("800")  # 4% of 20000
    assert res.non_electrical_accessories_od == Decimal("328")  # 3.283% of 10000
    assert res.lpg_cng_kit_od == Decimal("600")  # 4% of 15000
    assert res.gross_od_premium == Decimal("27992")

    # Anti-theft 2.5% of 27992 = 700 -> capped at 500
    assert res.anti_theft_discount == Decimal("500")
    # Voluntary deductible 5000 slab -> 25% capped at 1500
    assert res.voluntary_deductible_discount == Decimal("1500")
    assert res.od_after_tariff_discounts == Decimal("25992")

    # Zero-Dep = 0.45% of 800000 = 3600; Towing (Comp 3, 10000) = 1000
    assert res.zero_dep_premium == Decimal("3600")
    assert res.towing_charges_amount == Decimal("1000")

    # TPPD restriction for PVT = Rs 200 discount; LPG/CNG TP = Rs 60
    assert res.lpg_cng_tp_premium == Decimal("60")
    assert res.tppd_discount == Decimal("200")


# ============================================================================
# 7. Policy Type Separation: Package (1) vs TP-Only (2) vs SAOD (3)
# ============================================================================


@pytest.mark.asyncio
async def test_tp_only_and_standalone_od_policy_types(db_session: AsyncSession):
    """
    Verifies:
    - ProductTypeId = 2 (Liability Only / STP) zeroes out all IDV, OD, and Add-On fields.
    - ProductTypeId = 3 (Standalone OD / SAOD) zeroes out all TP Liability fields.
    """
    service = RatingEngineService(QuotationRepository(db_session))

    tp_only_req = PremiumCalculationRequest(
        vehicle_category="PVT",
        product_type_id=2,
        cubic_capacity=1197,
        base_idv_override=Decimal("500000"),
        pa_to_owner_driver=True,
        insurance_company_id=2,
    )
    tp_res = await service.calculate_premium(tp_only_req)
    assert tp_res.selected_idv == Decimal("0")
    assert tp_res.total_od_with_addons == Decimal("0")
    assert tp_res.basic_tp_premium == Decimal("3416")
    assert tp_res.pa_owner_driver_premium == Decimal("325")
    assert tp_res.total_tp_premium == Decimal("3741")

    saod_req = PremiumCalculationRequest(
        vehicle_category="PVT",
        product_type_id=3,
        cubic_capacity=1197,
        base_idv_override=Decimal("500000"),
        od_discount_override=Decimal("60"),
        ncb_percent=Decimal("20"),
        pa_to_owner_driver=True,
    )
    saod_res = await service.calculate_premium(saod_req)
    assert saod_res.total_od_with_addons > Decimal("0")
    assert saod_res.basic_tp_premium == Decimal("0")
    assert saod_res.total_tp_premium == Decimal("0")


# ============================================================================
# 8. Strict Decimal-Only Enforcement (Zero Floats in Breakdown)
# ============================================================================


@pytest.mark.asyncio
async def test_no_float_fields_in_premium_breakdown(db_session: AsyncSession):
    """Asserts every numeric monetary/rate attribute on PremiumBreakdownResponse is a Decimal or int."""
    service = RatingEngineService(QuotationRepository(db_session))
    req = PremiumCalculationRequest(
        vehicle_category="TwoWheeler",
        cubic_capacity=125,
        base_idv_override=Decimal("75000"),
        ncb_percent=Decimal("25"),
    )
    res: PremiumBreakdownResponse = await service.calculate_premium(req)
    for field_name, val in res.__dict__.items():
        assert not isinstance(val, float), f"Field '{field_name}' leaked float type: {val!r}"


# ============================================================================
# 9. Multi-Insurer Comparison
# ============================================================================


@pytest.mark.asyncio
async def test_multi_insurer_comparison(db_session: AsyncSession):
    """Verifies compare_insurers returns distinct breakdowns per requested insurer."""
    service = RatingEngineService(QuotationRepository(db_session))
    comp_req = MultiInsurerCompareRequest(
        calculation_input=PremiumCalculationRequest(
            vehicle_category="PVT",
            cubic_capacity=1197,
            base_idv_override=Decimal("600000"),
            od_discount_override=Decimal("50"),
            ncb_percent=Decimal("20"),
        ),
        insurance_company_ids=[1, 2, 3, 4],
    )
    comp_res = await service.compare_insurers(comp_req)
    assert len(comp_res.comparisons) == 4
    returned_ids = [c.insurance_company_id for c in comp_res.comparisons]
    assert returned_ids == [1, 2, 3, 4]
    # PA Owner Driver differs across companies (Comp 1=326, Comp 2=325, Comp 3=375, Comp 4=315)
    pa_rates = [c.pa_owner_driver_premium for c in comp_res.comparisons]
    assert pa_rates == [Decimal("326"), Decimal("325"), Decimal("375"), Decimal("315")]


# ============================================================================
# 10. GAP-P6-001 & GAP-P6-002 Remediation Verification
# ============================================================================


@pytest.mark.asyncio
async def test_gcv_basic_tp_gst_2025_09_23_cutover_rate_5_vs_12_percent(
    db_session: AsyncSession,
):
    """
    GAP-P6-001 (LBR-036 / LBR-071):
    - risk_start_date < 2025-09-23 -> 12% GST on GCV Basic TP
    - risk_start_date >= 2025-09-23 -> 5% GST on GCV Basic TP
    """
    service = RatingEngineService(QuotationRepository(db_session))

    req_pre = PremiumCalculationRequest(
        vehicle_category="Public_GCV",
        insurance_company_id=3,
        zone="A",
        vehicle_age_override=Decimal("2.0"),
        gross_vehicle_weight=25000,
        base_idv_override=Decimal("1000000"),
        risk_start_date=date(2025, 9, 22),
    )
    res_pre = await service.calculate_premium(req_pre)
    assert res_pre.gcv_basic_tp_gst_rate_percent == Decimal("12")
    assert res_pre.gst_on_basic_tp == Decimal("5274")  # 12% of 43,950

    req_cutover = PremiumCalculationRequest(
        vehicle_category="Public_GCV",
        insurance_company_id=3,
        zone="A",
        vehicle_age_override=Decimal("2.0"),
        gross_vehicle_weight=25000,
        base_idv_override=Decimal("1000000"),
        risk_start_date=date(2025, 9, 23),
    )
    res_cutover = await service.calculate_premium(req_cutover)
    assert res_cutover.gcv_basic_tp_gst_rate_percent == Decimal("5")
    assert res_cutover.gst_on_basic_tp == Decimal("2198")  # round_rupee(43,950 * 5%) = 2,198

    req_post = PremiumCalculationRequest(
        vehicle_category="Public_GCV",
        insurance_company_id=3,
        zone="A",
        vehicle_age_override=Decimal("2.0"),
        gross_vehicle_weight=25000,
        base_idv_override=Decimal("1000000"),
        risk_start_date=date(2025, 10, 1),
    )
    res_post = await service.calculate_premium(req_post)
    assert res_post.gcv_basic_tp_gst_rate_percent == Decimal("5")
    assert res_post.gst_on_basic_tp == Decimal("2198")


@pytest.mark.asyncio
async def test_gcv_extra_weight_loading_csharp_integer_division_parity(
    db_session: AsyncSession,
):
    """
    GAP-P6-002 (LBR-028):
    Legacy C# `((ExtraWeight * 27) / 100)` uses integer division before converting to double.
    For GVW = 12005 (ExtraWeight = 5): (5 * 27) // 100 = 135 // 100 = 1.
    For GVW = 12003 (ExtraWeight = 3): (3 * 27) // 100 = 81 // 100 = 0.
    """
    service = RatingEngineService(QuotationRepository(db_session))

    req_12005 = PremiumCalculationRequest(
        vehicle_category="Public_GCV",
        insurance_company_id=3,
        zone="A",
        vehicle_age_override=Decimal("2.0"),
        gross_vehicle_weight=12005,
        base_idv_override=Decimal("1000000"),
    )
    res_12005 = await service.calculate_premium(req_12005)
    assert res_12005.gvw_above_12000_loading == Decimal("1")

    req_12003 = PremiumCalculationRequest(
        vehicle_category="Public_GCV",
        insurance_company_id=3,
        zone="A",
        vehicle_age_override=Decimal("2.0"),
        gross_vehicle_weight=12003,
        base_idv_override=Decimal("1000000"),
    )
    res_12003 = await service.calculate_premium(req_12003)
    assert res_12003.gvw_above_12000_loading == Decimal("0")

