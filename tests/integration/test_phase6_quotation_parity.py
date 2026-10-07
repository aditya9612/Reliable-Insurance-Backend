"""
Phase 6 Golden Parity Tests — Legacy Stored Procedure & WebForm Calculation Parity.
Verifies exact 0.00-discrepancy parity across all 9 vehicle categories:
1. PVT (Private Car)
2. TwoWheeler
3. Public_GCV
4. Private_GCV
5. PublicGCV3W (3-Wheeler Goods)
6. PublicPCV3W (3-Wheeler Passenger)
7. Misc-D (Tractor / Crane / JCB)
8. PassengerTaxi(PCV)
9. School_Bus / Staff Bus
Plus DB-backed tariff/discount/zero-dep tables and QuotationCode generators.
"""
from decimal import Decimal
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.master import VehicleVariant
from app.models.quotation import (
    AddonExtraAmt,
    AppODDiscountNew,
    AppODDiscountNewGCV,
    ZeroDepNewAddonRate,
)
from app.repositories.quotation import QuotationRepository
from app.schemas.quotation import PremiumCalculationRequest
from app.services.rating import RatingEngineService


@pytest.fixture(autouse=True)
async def cleanup_parity_tables(db_session: AsyncSession):
    """Ensure clean local rating & quotation tables before and after parity tests."""
    await db_session.execute(text("DELETE FROM tbl_app_oddiscountnew;"))
    await db_session.execute(text("DELETE FROM tbl_app_oddiscountnew_gcv;"))
    await db_session.execute(text("DELETE FROM tbl_zerodepnewaddonrate;"))
    await db_session.execute(text("DELETE FROM tbl_addonextraamt;"))
    await db_session.execute(text("DELETE FROM tbl_vehicle_variants WHERE Variant_ID IN (9901, 9902);"))
    await db_session.commit()
    yield
    await db_session.execute(text("DELETE FROM tbl_app_oddiscountnew;"))
    await db_session.execute(text("DELETE FROM tbl_app_oddiscountnew_gcv;"))
    await db_session.execute(text("DELETE FROM tbl_zerodepnewaddonrate;"))
    await db_session.execute(text("DELETE FROM tbl_addonextraamt;"))
    await db_session.execute(text("DELETE FROM tbl_vehicle_variants WHERE Variant_ID IN (9901, 9902);"))
    await db_session.commit()


# ============================================================================
# 1. Golden Parity Matrix Across All 9 Vehicle Categories
# ============================================================================


GOLDEN_PARITY_CASES = [
    {
        "case_id": "GOLDEN-01-PVT",
        "req": PremiumCalculationRequest(
            vehicle_category="PVT",
            insurance_company_id=2,  # ICICI (PA=325)
            zone="A",
            cubic_capacity=1197,
            vehicle_age_override=Decimal("3.0"),
            base_idv_override=Decimal("600000"),
            od_discount_override=Decimal("60"),
            ncb_percent=Decimal("25"),
            pa_to_owner_driver=True,
            ll_paid_driver_count=1,
        ),
        "expected": {
            "od_basic_rate_percent": Decimal("3.283"),
            "basic_od_premium": Decimal("19698"),
            "gross_od_premium": Decimal("19698"),
            "od_discount_amount": Decimal("11819"),
            "od_after_company_discount": Decimal("7879"),
            "ncb_amount": Decimal("1970"),
            "net_od_premium": Decimal("5909"),
            "basic_tp_premium": Decimal("3416"),
            "pa_owner_driver_premium": Decimal("325"),
            "ll_paid_driver_premium": Decimal("50"),
            "total_tp_premium": Decimal("3791"),
            "net_premium": Decimal("9700"),
            "total_gst_amount": Decimal("1746"),
            "final_payable_premium": Decimal("11446"),
        },
    },
    {
        "case_id": "GOLDEN-02-TWOWHEELER",
        "req": PremiumCalculationRequest(
            vehicle_category="TwoWheeler",
            insurance_company_id=4,  # Tata AIG (PA=315)
            zone="B",
            cubic_capacity=125,
            vehicle_age_override=Decimal("2.0"),
            base_idv_override=Decimal("70000"),
            od_discount_override=Decimal("50"),
            ncb_percent=Decimal("20"),
            pa_to_owner_driver=True,
            pa_pillion_rider_amount=Decimal("50"),
        ),
        "expected": {
            "od_basic_rate_percent": Decimal("1.676"),
            "basic_od_premium": Decimal("1173"),
            "gross_od_premium": Decimal("1173"),
            "od_discount_amount": Decimal("587"),
            "od_after_company_discount": Decimal("586"),
            "ncb_amount": Decimal("117"),
            "net_od_premium": Decimal("469"),
            "basic_tp_premium": Decimal("714"),
            "pa_owner_driver_premium": Decimal("315"),
            "pa_pillion_rider_premium": Decimal("50"),
            "total_tp_premium": Decimal("1079"),
            "net_premium": Decimal("1548"),
            "total_gst_amount": Decimal("279"),
            "final_payable_premium": Decimal("1827"),
        },
    },
    {
        "case_id": "GOLDEN-03-PUBLIC-GCV",
        "req": PremiumCalculationRequest(
            vehicle_category="Public_GCV",
            insurance_company_id=3,  # Bajaj (PA=375)
            zone="C",
            gross_vehicle_weight=16000,
            vehicle_age_override=Decimal("4.0"),
            base_idv_override=Decimal("1200000"),
            imt23=True,
            od_discount_override=Decimal("70"),
            ncb_percent=Decimal("20"),
            pa_to_owner_driver=True,
            ll_paid_driver_count=1,
            ll_cleaner_count=1,
            nfpp_count=2,
            gcv_split_tp_gst=True,
        ),
        "expected": {
            "od_basic_rate_percent": Decimal("1.726"),
            "basic_od_premium": Decimal("20712"),
            "gvw_above_12000_loading": Decimal("1080"),
            "subtotal_od_before_imt23": Decimal("21792"),
            "imt23_loading_amount": Decimal("3269"),
            "gross_od_premium": Decimal("25061"),
            "od_discount_amount": Decimal("17543"),
            "od_after_company_discount": Decimal("7518"),
            "ncb_amount": Decimal("1504"),
            "net_od_premium": Decimal("6014"),
            "basic_tp_premium": Decimal("35313"),
            "pa_owner_driver_premium": Decimal("375"),
            "ll_paid_driver_premium": Decimal("50"),
            "ll_cleaner_coolie_premium": Decimal("50"),
            "nfpp_premium": Decimal("150"),
            "total_tp_premium": Decimal("35938"),
            "net_premium": Decimal("41952"),
            "gst_on_od_and_other_tp": Decimal("1195"),
            "gst_on_basic_tp": Decimal("4238"),
            "total_gst_amount": Decimal("5433"),
            "final_payable_premium": Decimal("47385"),
        },
    },
    {
        "case_id": "GOLDEN-04-PRIVATE-GCV",
        "req": PremiumCalculationRequest(
            vehicle_category="Private_GCV",
            insurance_company_id=14,  # HDFC Ergo (PA=375)
            zone="A",
            gross_vehicle_weight=7000,
            vehicle_age_override=Decimal("1.0"),
            base_idv_override=Decimal("800000"),
            od_discount_override=Decimal("50"),
            ncb_percent=Decimal("0"),
            pa_to_owner_driver=True,
            gcv_split_tp_gst=True,
        ),
        "expected": {
            "od_basic_rate_percent": Decimal("1.226"),
            "basic_od_premium": Decimal("9808"),
            "gross_od_premium": Decimal("9808"),
            "od_discount_amount": Decimal("4904"),
            "net_od_premium": Decimal("4904"),
            "basic_tp_premium": Decimal("8438"),
            "pa_owner_driver_premium": Decimal("375"),
            "total_tp_premium": Decimal("8813"),
            "net_premium": Decimal("13717"),
            "gst_on_od_and_other_tp": Decimal("950"),
            "gst_on_basic_tp": Decimal("1013"),
            "total_gst_amount": Decimal("1963"),
            "final_payable_premium": Decimal("15680"),
        },
    },
    {
        "case_id": "GOLDEN-05-PUBLIC-GCV-3W",
        "req": PremiumCalculationRequest(
            vehicle_category="PublicGCV3W",
            insurance_company_id=18,  # SBI General (PA=331)
            zone="B",
            cubic_capacity=500,
            vehicle_age_override=Decimal("2.0"),
            base_idv_override=Decimal("200000"),
            od_discount_override=Decimal("40"),
            ncb_percent=Decimal("20"),
            pa_to_owner_driver=True,
            ll_paid_driver_count=1,
            gcv_split_tp_gst=True,
        ),
        "expected": {
            "od_basic_rate_percent": Decimal("1.656"),
            "basic_od_premium": Decimal("3312"),
            "od_discount_amount": Decimal("1325"),
            "od_after_company_discount": Decimal("1987"),
            "ncb_amount": Decimal("397"),
            "net_od_premium": Decimal("1590"),
            "basic_tp_premium": Decimal("4492"),
            "pa_owner_driver_premium": Decimal("331"),
            "ll_paid_driver_premium": Decimal("50"),
            "total_tp_premium": Decimal("4873"),
            "net_premium": Decimal("6463"),
            "gst_on_od_and_other_tp": Decimal("355"),
            "gst_on_basic_tp": Decimal("539"),
            "total_gst_amount": Decimal("894"),
            "final_payable_premium": Decimal("7357"),
        },
    },
    {
        "case_id": "GOLDEN-06-PUBLIC-PCV-3W",
        "req": PremiumCalculationRequest(
            vehicle_category="PublicPCV3W",
            insurance_company_id=3,  # Bajaj (PA=375)
            zone="C",
            cubic_capacity=200,
            seating_capacity=3,
            vehicle_age_override=Decimal("3.0"),
            base_idv_override=Decimal("180000"),
            od_discount_override=Decimal("30"),
            ncb_percent=Decimal("20"),
            pa_to_owner_driver=True,
            ll_paid_driver_count=1,
        ),
        "expected": {
            "od_basic_rate_percent": Decimal("1.260"),
            "basic_od_premium": Decimal("2268"),
            "od_discount_amount": Decimal("680"),
            "od_after_company_discount": Decimal("1588"),
            "ncb_amount": Decimal("318"),
            "net_od_premium": Decimal("1270"),
            "basic_tp_premium": Decimal("2595"),
            "passenger_ll_premium": Decimal("3723"),  # 3 * 1241
            "pa_owner_driver_premium": Decimal("375"),
            "ll_paid_driver_premium": Decimal("50"),
            "total_tp_premium": Decimal("6743"),
            "net_premium": Decimal("8013"),
            "total_gst_amount": Decimal("1442"),
            "final_payable_premium": Decimal("9455"),
        },
    },
    {
        "case_id": "GOLDEN-07-MISC-D",
        "req": PremiumCalculationRequest(
            vehicle_category="Misc-D",
            insurance_company_id=3,
            zone="B",
            cubic_capacity=2500,
            vehicle_age_override=Decimal("2.0"),
            base_idv_override=Decimal("600000"),
            imt23=True,
            od_discount_override=Decimal("50"),
            ncb_percent=Decimal("20"),
            pa_to_owner_driver=True,
            ll_paid_driver_count=1,
            no_of_trailers=1,
        ),
        "expected": {
            "od_basic_rate_percent": Decimal("1.190"),
            "basic_od_premium": Decimal("7140"),
            "imt23_loading_amount": Decimal("1071"),
            "gross_od_premium": Decimal("8211"),
            "od_discount_amount": Decimal("4106"),
            "od_after_company_discount": Decimal("4105"),
            "ncb_amount": Decimal("821"),
            "net_od_premium": Decimal("3284"),
            "basic_tp_premium": Decimal("7267"),
            "pa_owner_driver_premium": Decimal("375"),
            "ll_paid_driver_premium": Decimal("50"),
            "trailer_tp_premium": Decimal("2485"),
            "total_tp_premium": Decimal("10177"),
            "net_premium": Decimal("13461"),
            "total_gst_amount": Decimal("2423"),
            "final_payable_premium": Decimal("15884"),
        },
    },
    {
        "case_id": "GOLDEN-08-PASSENGER-TAXI-PCV",
        "req": PremiumCalculationRequest(
            vehicle_category="PassengerTaxi(PCV)",
            insurance_company_id=3,
            zone="A",
            cubic_capacity=1197,
            seating_capacity=4,
            vehicle_age_override=Decimal("2.0"),
            base_idv_override=Decimal("500000"),
            od_discount_override=Decimal("40"),
            ncb_percent=Decimal("20"),
            pa_to_owner_driver=True,
            ll_paid_driver_count=1,
        ),
        "expected": {
            "od_basic_rate_percent": Decimal("3.448"),
            "basic_od_premium": Decimal("17240"),
            "od_discount_amount": Decimal("6896"),
            "od_after_company_discount": Decimal("10344"),
            "ncb_amount": Decimal("2069"),
            "net_od_premium": Decimal("8275"),
            "basic_tp_premium": Decimal("7584"),
            "passenger_ll_premium": Decimal("3736"),  # 4 * 934
            "pa_owner_driver_premium": Decimal("375"),
            "ll_paid_driver_premium": Decimal("50"),
            "total_tp_premium": Decimal("11745"),
            "net_premium": Decimal("20020"),
            "total_gst_amount": Decimal("3604"),
            "final_payable_premium": Decimal("23624"),
        },
    },
    {
        "case_id": "GOLDEN-09-SCHOOL-BUS",
        "req": PremiumCalculationRequest(
            vehicle_category="School_Bus",
            insurance_company_id=3,
            zone="B",
            bus_type="SCHOOL BUS",
            seating_capacity=30,
            vehicle_age_override=Decimal("3.0"),
            base_idv_override=Decimal("1500000"),
            ncb_percent=Decimal("25"),
            pa_to_owner_driver=True,
            ll_paid_driver_count=1,
            ll_cleaner_count=1,
        ),
        "expected": {
            "od_basic_rate_percent": Decimal("1.672"),
            "basic_od_premium": Decimal("25080"),
            "od_discount_percent": Decimal("85"),  # Default SCHOOL BUS discount = 85%
            "od_discount_amount": Decimal("21318"),
            "od_after_company_discount": Decimal("3762"),
            "ncb_amount": Decimal("941"),
            "net_od_premium": Decimal("2821"),
            "basic_tp_premium": Decimal("13874"),
            "passenger_ll_premium": Decimal("25440"),  # 30 * 848
            "pa_owner_driver_premium": Decimal("375"),
            "ll_paid_driver_premium": Decimal("50"),
            "ll_cleaner_coolie_premium": Decimal("50"),
            "total_tp_premium": Decimal("39789"),
            "net_premium": Decimal("42610"),
            "total_gst_amount": Decimal("7670"),
            "final_payable_premium": Decimal("50280"),
        },
    },
]


@pytest.mark.asyncio
@pytest.mark.parametrize("case", GOLDEN_PARITY_CASES, ids=[c["case_id"] for c in GOLDEN_PARITY_CASES])
async def test_golden_parity_across_all_9_vehicle_categories(
    db_session: AsyncSession,
    case: dict,
):
    """
    Executes each golden parity test case and asserts 0.00 discrepancy on every
    expected intermediate and final monetary field.
    """
    service = RatingEngineService(QuotationRepository(db_session))
    res = await service.calculate_premium(case["req"])

    for field_name, expected_val in case["expected"].items():
        actual_val = getattr(res, field_name)
        assert actual_val == expected_val, (
            f"[{case['case_id']}] Parity mismatch on '{field_name}': "
            f"actual={actual_val} vs expected={expected_val}"
        )


# ============================================================================
# 2. DB-Backed OD Discount, Decline Flag, Zero-Dep & Variant Body+Chassis Parity
# ============================================================================


@pytest.mark.asyncio
async def test_db_backed_od_discount_decline_zerodep_and_variant_idv_parity(
    db_session: AsyncSession,
):
    """
    Seeds local tables (tbl_vehicle_variants, tbl_app_oddiscountnew, tbl_app_oddiscountnew_gcv,
    tbl_zerodepnewaddonrate, tbl_addonextraamt) and verifies exact SP lookup parity:
    - sp_SelectIDVDetailsForGCV (with_body=False -> ExMumbai_Body_Price + ExMumbai_Chasis_Price)
    - sp_SelectAppDiscWithFueltype & sp_SelectAppDiscDiclineOrNot (Decline=1 detection)
    - sp_SelectZeroDepMultiAddOn_New & sp_SelectZeroDepExtraAmount
    """
    # Seed Variant 9901 (PVT) and 9902 (GCV Body+Chassis)
    v_pvt = VehicleVariant(
        Variant_ID=9901,
        Model_ID=501,
        Variance="SWIFT ZXI",
        Operated_By="PETROL",
        CC="1197",
        Seating_Capacity="5",
        ExMumbai_Model_Price="600000",
        ExMumbai_Body_Price="0",
        ExMumbai_Chasis_Price="0",
        Make_Id=10,
    )
    v_gcv = VehicleVariant(
        Variant_ID=9902,
        Model_ID=502,
        Variance="EICHER PRO 3015",
        Operated_By="DIESEL",
        CC="3800",
        Seating_Capacity="3",
        ExMumbai_Model_Price="1600000",
        ExMumbai_Body_Price="300000",
        ExMumbai_Chasis_Price="1200000",
        Make_Id=20,
    )
    db_session.add_all([v_pvt, v_gcv])

    # Seed AppODDiscountNew for Model 501 (Age 13 -> physical column 'thriteen' = 65%, Decline = 1)
    od_row = AppODDiscountNew(
        MakeID=10,
        Model_ID=501,
        InsuranceCompanyId=3,
        ClusterId=0,
        NCB="Yes",
        ZeroDep="Yes",
        Fueltypeid=1,
        BusinessTypeId=3,
        thriteen="65",
        Decline=1,
    )
    # Seed AppODDiscountNewGCV for Model 502 (Age 2 -> 'Two' = 72%)
    od_gcv_row = AppODDiscountNewGCV(
        MakeID=20,
        Model_ID=502,
        InsuranceCompanyId=3,
        ClusterId=0,
        NCB="Yes",
        ZeroDep="No",
        Fueltypeid=2,
        BusinessTypeId=3,
        Two="72",
    )
    # Seed ZeroDepNewAddonRate & AddonExtraAmt for Model 501
    zd_row = ZeroDepNewAddonRate(
        InsuranceCompanyId=3,
        MakeID=10,
        Model_ID=501,
        Age=13,
        Fueltypeid=1,
        BusinessTypeId=3,
        ClusterId=0,
        NCB="Yes",
        NillDep="0.50",
        Isdelete=0,
    )
    ext_row = AddonExtraAmt(
        VehiceTypeId=4,
        makeId=10,
        ModelId=501,
        InsuranceCompanyId=3,
        NillDep=500.0,
        IsDeleted=0,
    )
    db_session.add_all([od_row, od_gcv_row, zd_row, ext_row])
    await db_session.commit()

    service = RatingEngineService(QuotationRepository(db_session))

    # 1. Test PVT Variant 9901 at Age 13 (tests physical column 'thriteen', Decline=1, ZeroDep+Extra)
    res_pvt = await service.calculate_premium(
        PremiumCalculationRequest(
            vehicle_category="PVT",
            insurance_company_id=3,
            veh_type_id=4,
            make_id=10,
            model_id=501,
            variant_id=9901,
            fuel_type_id=1,
            business_type_id=3,
            vehicle_age_override=Decimal("13.0"),
            ncb_percent=Decimal("20"),
            zero_dep=True,
        )
    )
    assert res_pvt.base_idv == Decimal("600000")
    assert res_pvt.lookup_age == Decimal("11.0")  # Age > 10 capped to 11.0 for tariff lookup
    assert res_pvt.od_discount_percent == Decimal("65")
    assert res_pvt.is_declined is True
    assert res_pvt.zero_dep_rate_percent == Decimal("0.50")
    assert res_pvt.zero_dep_extra_amount == Decimal("500")
    assert res_pvt.zero_dep_premium == Decimal("3500")  # (600000 * 0.50%) + 500 = 3500

    # 2. Test GCV Variant 9902 with_body=False (Body 300k + Chassis 1200k = 1500k)
    res_gcv = await service.calculate_premium(
        PremiumCalculationRequest(
            vehicle_category="Public_GCV",
            insurance_company_id=3,
            veh_type_id=1,
            make_id=20,
            model_id=502,
            variant_id=9902,
            fuel_type_id=2,
            business_type_id=3,
            with_body=False,
            vehicle_age_override=Decimal("2.0"),
            ncb_percent=Decimal("20"),
            zero_dep=False,
        )
    )
    assert res_gcv.body_price == Decimal("300000")
    assert res_gcv.chassis_price == Decimal("1200000")
    assert res_gcv.base_idv == Decimal("1500000")
    assert res_gcv.od_discount_percent == Decimal("72")
