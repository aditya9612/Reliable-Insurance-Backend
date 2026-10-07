"""
Phase 7 Golden Parity Test Suite — 25 Deterministic Synthetic Golden Cases (G7-01 .. G7-25).

Verifies exact 0.00 financial delta across:
- All 9 vehicle categories (PVT, TwoWheeler, Public_GCV, Private_GCV, PublicGCV3W,
  PublicPCV3W, PassengerTaxi(PCV), School_Bus, Misc-D)
- Comprehensive, Liability-Only (TP), and Standalone OD (SAOD) products
- New Vehicle and Previous-Claim NCB=0% enforcement
- Split GST (12% Basic TP + 18% OD/Other TP for GCV) vs Uniform 18% GST
- Self-Quotation, Assisted Quotation, and Staged Proposal policy conversion
- Multi-bucket Commission (OD, Net, Extra), TDS (5%), Franchise split, Cut & Pay,
  E-Wallet, Partial/Multi-instrument payment, and Double-Entry Accounting (AccTransId = 1, 2, 3)
"""
from decimal import Decimal
import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from tests.integration.test_phase7_policy_booking_api import (
    create_synthetic_customer_and_vehicle,
    create_user_with_role,
)


@pytest.fixture(autouse=True)
async def cleanup_golden_tables(db_session: AsyncSession):
    for tbl in (
        "tbl_account",
        "tbl_transactionpayment",
        "tbl_franchisecommission",
        "tbl_agentcommissionpayment",
        "tbl_cutnpaycommpayable",
        "tbl_transaction",
        "tbl_transactionappnew",
        "tbl_insurancecompanyquotation",
        "tbl_app_quotationremark",
        "tbl_app_quotationrequest",
        "tbl_app_quatationentry",
    ):
        await db_session.execute(text(f"DELETE FROM {tbl};"))
    await db_session.commit()
    yield
    for tbl in (
        "tbl_account",
        "tbl_transactionpayment",
        "tbl_franchisecommission",
        "tbl_agentcommissionpayment",
        "tbl_cutnpaycommpayable",
        "tbl_transaction",
        "tbl_transactionappnew",
        "tbl_insurancecompanyquotation",
        "tbl_app_quotationremark",
        "tbl_app_quotationrequest",
        "tbl_app_quatationentry",
    ):
        await db_session.execute(text(f"DELETE FROM {tbl};"))
    await db_session.commit()


# ============================================================================
# Cases G7-01 to G7-14: 14 Direct & Rating-Revalidated Underwriting Golden Cases
# ============================================================================

DIRECT_GOLDEN_CASES = [
    # G7-01: Private Car (PVT) Comprehensive, 20% NCB, 40% OD Discount, Cash Full Payment
    {
        "case_id": "G7-01",
        "vehicle_category": "PVT",
        "product_type_id": 1,
        "business_type_id": 3,
        "sum_insured_idv": "600000.00",
        "od_premium": "8500.00",
        "tp_premium": "3796.00",
        "basic_tp_premium": "3416.00",
        "pa_owner_driver": "330.00",
        "ll_paid_driver": "50.00",
        "ncb_percent": "20.00",
        "ncb_amount": "2125.00",
        "od_discount_percent": "40.00",
        "agent_comm_od_percent": "15.00",
        "agent_comm_net_percent": "5.00",
        "agent_comm_extra_percent": "0.00",
        "tds_percent": "5.00",
        "payment_type": "CASH",
        "paid_amount": "14509.00",
        # Expected: Net = 8500 + 3796 = 12296.00; GST 18% = 2213.00; Final = 14509.00
        # Comm: OD = 1275.00 (TDS 63.75, Net 1211.25), TP = 3796 * 5% = 189.80 (TDS 9.49, Net 180.31)
        # Gross Comm = 1464.80, TDS = 73.24, NetComm = 1391.56
        "exp_net": Decimal("12296.00"),
        "exp_gst": Decimal("2213.00"),
        "exp_final": Decimal("14509.00"),
        "exp_gross_comm": Decimal("1464.80"),
        "exp_tds": Decimal("73.24"),
        "exp_net_comm": Decimal("1391.56"),
        "exp_outstanding": Decimal("0.00"),
    },
    # G7-02: Private Car (PVT) Liability Only (TP / STP), Zero OD, Zero IDV, Zero NCB
    {
        "case_id": "G7-02",
        "vehicle_category": "PVT",
        "product_type_id": 2,
        "business_type_id": 3,
        "sum_insured_idv": "0.00",
        "od_premium": "0.00",
        "tp_premium": "3796.00",
        "basic_tp_premium": "3416.00",
        "pa_owner_driver": "330.00",
        "ll_paid_driver": "50.00",
        "ncb_percent": "0.00",
        "ncb_amount": "0.00",
        "od_discount_percent": "0.00",
        "agent_comm_od_percent": "0.00",
        "agent_comm_net_percent": "10.00",
        "agent_comm_extra_percent": "0.00",
        "tds_percent": "5.00",
        "payment_type": "ONLINE",
        "paid_amount": "4479.00",
        # Net = 3796.00; GST 18% = 683.00; Final = 4479.00
        # Comm: 3796 * 10% = 379.60; TDS 5% = 18.98; NetComm = 360.62
        "exp_net": Decimal("3796.00"),
        "exp_gst": Decimal("683.00"),
        "exp_final": Decimal("4479.00"),
        "exp_gross_comm": Decimal("379.60"),
        "exp_tds": Decimal("18.98"),
        "exp_net_comm": Decimal("360.62"),
        "exp_outstanding": Decimal("0.00"),
    },
    # G7-03: Private Car (PVT) Standalone OD (SAOD), Zero TP, 25% NCB, Nil-Dep Add-On, Cheque Payment
    {
        "case_id": "G7-03",
        "vehicle_category": "PVT",
        "product_type_id": 3,
        "business_type_id": 2,
        "sum_insured_idv": "500000.00",
        "od_premium": "9200.00",
        "tp_premium": "0.00",
        "basic_tp_premium": "0.00",
        "pa_owner_driver": "0.00",
        "ll_paid_driver": "0.00",
        "ncb_percent": "25.00",
        "ncb_amount": "2300.00",
        "od_discount_percent": "50.00",
        "agent_comm_od_percent": "20.00",
        "agent_comm_net_percent": "0.00",
        "agent_comm_extra_percent": "2.00",
        "tds_percent": "5.00",
        "payment_type": "CHEQUE",
        "paid_amount": "10856.00",
        # Net = 9200.00; GST 18% = 1656.00; Final = 10856.00
        # Comm: OD 20% = 1840.00 (TDS 92.00, Net 1748.00) + Extra 2% = 184.00 (TDS 9.20, Net 174.80)
        # Gross = 2024.00, TDS = 101.20, NetComm = 1922.80
        "exp_net": Decimal("9200.00"),
        "exp_gst": Decimal("1656.00"),
        "exp_final": Decimal("10856.00"),
        "exp_gross_comm": Decimal("2024.00"),
        "exp_tds": Decimal("101.20"),
        "exp_net_comm": Decimal("1922.80"),
        "exp_outstanding": Decimal("0.00"),
    },
    # G7-04: Private Car (PVT) New Vehicle (business_type_id=1), 0% NCB, NEFT Payment
    {
        "case_id": "G7-04",
        "vehicle_category": "PVT",
        "product_type_id": 1,
        "business_type_id": 1,
        "sum_insured_idv": "800000.00",
        "od_premium": "15000.00",
        "tp_premium": "8000.00",
        "basic_tp_premium": "7625.00",
        "pa_owner_driver": "375.00",
        "ll_paid_driver": "0.00",
        "ncb_percent": "0.00",
        "ncb_amount": "0.00",
        "od_discount_percent": "30.00",
        "agent_comm_od_percent": "18.00",
        "agent_comm_net_percent": "0.00",
        "agent_comm_extra_percent": "0.00",
        "tds_percent": "5.00",
        "payment_type": "NEFT",
        "paid_amount": "27140.00",
        # Net = 23000.00; GST 18% = 4140.00; Final = 27140.00
        # Comm: 15000 * 18% = 2700.00; TDS = 135.00; NetComm = 2565.00
        "exp_net": Decimal("23000.00"),
        "exp_gst": Decimal("4140.00"),
        "exp_final": Decimal("27140.00"),
        "exp_gross_comm": Decimal("2700.00"),
        "exp_tds": Decimal("135.00"),
        "exp_net_comm": Decimal("2565.00"),
        "exp_outstanding": Decimal("0.00"),
    },
    # G7-05: Private Car (PVT) Renewal with Previous Claim (claim_in_previous_policy=True) -> 0% NCB
    {
        "case_id": "G7-05",
        "vehicle_category": "PVT",
        "product_type_id": 1,
        "business_type_id": 2,
        "claim_in_previous_policy": True,
        "sum_insured_idv": "450000.00",
        "od_premium": "10000.00",
        "tp_premium": "3416.00",
        "basic_tp_premium": "3416.00",
        "pa_owner_driver": "0.00",
        "ll_paid_driver": "0.00",
        "ncb_percent": "0.00",
        "ncb_amount": "0.00",
        "od_discount_percent": "35.00",
        "agent_comm_od_percent": "15.00",
        "agent_comm_net_percent": "0.00",
        "agent_comm_extra_percent": "0.00",
        "tds_percent": "5.00",
        "payment_type": "CASH",
        "paid_amount": "15831.00",
        # Net = 13416.00; GST 18% = 2415.00; Final = 15831.00
        "exp_net": Decimal("13416.00"),
        "exp_gst": Decimal("2415.00"),
        "exp_final": Decimal("15831.00"),
        "exp_gross_comm": Decimal("1500.00"),
        "exp_tds": Decimal("75.00"),
        "exp_net_comm": Decimal("1425.00"),
        "exp_outstanding": Decimal("0.00"),
    },
    # G7-06: Two-Wheeler Comprehensive, 35% NCB, PA Owner-Driver, Cash Payment
    {
        "case_id": "G7-06",
        "vehicle_category": "TwoWheeler",
        "product_type_id": 1,
        "business_type_id": 3,
        "sum_insured_idv": "65000.00",
        "od_premium": "650.00",
        "tp_premium": "1089.00",
        "basic_tp_premium": "714.00",
        "pa_owner_driver": "375.00",
        "ll_paid_driver": "0.00",
        "ncb_percent": "35.00",
        "ncb_amount": "350.00",
        "od_discount_percent": "50.00",
        "agent_comm_od_percent": "20.00",
        "agent_comm_net_percent": "5.00",
        "agent_comm_extra_percent": "0.00",
        "tds_percent": "5.00",
        "payment_type": "CASH",
        "paid_amount": "2052.00",
        # Net = 1739.00; GST 18% = 313.00; Final = 2052.00
        # Comm: OD = 130.00 (TDS 6.50, Net 123.50), TP = 1089*5% = 54.45 (TDS 2.72, Net 51.73)
        "exp_net": Decimal("1739.00"),
        "exp_gst": Decimal("313.00"),
        "exp_final": Decimal("2052.00"),
        "exp_gross_comm": Decimal("184.45"),
        "exp_tds": Decimal("9.22"),
        "exp_net_comm": Decimal("175.23"),
        "exp_outstanding": Decimal("0.00"),
    },
    # G7-07: Two-Wheeler Liability Only (TP), Zero OD, UPI Payment
    {
        "case_id": "G7-07",
        "vehicle_category": "TwoWheeler",
        "product_type_id": 2,
        "business_type_id": 3,
        "sum_insured_idv": "0.00",
        "od_premium": "0.00",
        "tp_premium": "1089.00",
        "basic_tp_premium": "714.00",
        "pa_owner_driver": "375.00",
        "ll_paid_driver": "0.00",
        "ncb_percent": "0.00",
        "ncb_amount": "0.00",
        "od_discount_percent": "0.00",
        "agent_comm_od_percent": "0.00",
        "agent_comm_net_percent": "10.00",
        "agent_comm_extra_percent": "0.00",
        "tds_percent": "5.00",
        "payment_type": "UPI",
        "paid_amount": "1285.00",
        # Net = 1089.00; GST 18% = 196.00; Final = 1285.00
        "exp_net": Decimal("1089.00"),
        "exp_gst": Decimal("196.00"),
        "exp_final": Decimal("1285.00"),
        "exp_gross_comm": Decimal("108.90"),
        "exp_tds": Decimal("5.45"),
        "exp_net_comm": Decimal("103.45"),
        "exp_outstanding": Decimal("0.00"),
    },
    # G7-08: Public GCV Comprehensive — Split GST (12% Basic TP + 18% OD & Other TP)
    {
        "case_id": "G7-08",
        "vehicle_category": "Public_GCV",
        "product_type_id": 1,
        "business_type_id": 3,
        "gcv_split_tp_gst": True,
        "sum_insured_idv": "1500000.00",
        "od_premium": "20000.00",
        "tp_premium": "25500.00",
        "basic_tp_premium": "25000.00",
        "pa_owner_driver": "375.00",
        "ll_paid_driver": "125.00",
        "ncb_percent": "20.00",
        "ncb_amount": "5000.00",
        "od_discount_percent": "50.00",
        "agent_comm_od_percent": "15.00",
        "agent_comm_net_percent": "4.00",
        "agent_comm_extra_percent": "0.00",
        "tds_percent": "5.00",
        "payment_type": "NEFT",
        "paid_amount": "52190.00",
        # Net = 45500.00; Basic TP = 25000 -> 12% GST = 3000.00;
        # Remaining Net (20500) -> 18% GST = 3690.00; Total GST = 6690.00; Final = 52190.00
        # Comm: OD = 3000.00 (TDS 150.00), TP = 25500*4% = 1020.00 (TDS 51.00) -> Gross 4020, TDS 201, Net 3819
        "exp_net": Decimal("45500.00"),
        "exp_gst": Decimal("6690.00"),
        "exp_final": Decimal("52190.00"),
        "exp_gross_comm": Decimal("4020.00"),
        "exp_tds": Decimal("201.00"),
        "exp_net_comm": Decimal("3819.00"),
        "exp_outstanding": Decimal("0.00"),
    },
    # G7-09: Private GCV Comprehensive — Split GST (12% Basic TP + 18% OD)
    {
        "case_id": "G7-09",
        "vehicle_category": "Private_GCV",
        "product_type_id": 1,
        "business_type_id": 3,
        "gcv_split_tp_gst": True,
        "sum_insured_idv": "1000000.00",
        "od_premium": "12000.00",
        "tp_premium": "15000.00",
        "basic_tp_premium": "15000.00",
        "pa_owner_driver": "0.00",
        "ll_paid_driver": "0.00",
        "ncb_percent": "25.00",
        "ncb_amount": "4000.00",
        "od_discount_percent": "40.00",
        "agent_comm_od_percent": "10.00",
        "agent_comm_net_percent": "0.00",
        "agent_comm_extra_percent": "0.00",
        "tds_percent": "5.00",
        "payment_type": "ONLINE",
        "paid_amount": "30960.00",
        # Net = 27000; Basic TP 15000 * 12% = 1800; OD 12000 * 18% = 2160; GST = 3960; Final = 30960.00
        "exp_net": Decimal("27000.00"),
        "exp_gst": Decimal("3960.00"),
        "exp_final": Decimal("30960.00"),
        "exp_gross_comm": Decimal("1200.00"),
        "exp_tds": Decimal("60.00"),
        "exp_net_comm": Decimal("1140.00"),
        "exp_outstanding": Decimal("0.00"),
    },
    # G7-10: 3-Wheeler GCV (PublicGCV3W) Comprehensive — Split GST (12% Basic TP + 18% OD)
    {
        "case_id": "G7-10",
        "vehicle_category": "PublicGCV3W",
        "product_type_id": 1,
        "business_type_id": 3,
        "gcv_split_tp_gst": True,
        "sum_insured_idv": "250000.00",
        "od_premium": "3000.00",
        "tp_premium": "4500.00",
        "basic_tp_premium": "4500.00",
        "pa_owner_driver": "0.00",
        "ll_paid_driver": "0.00",
        "ncb_percent": "20.00",
        "ncb_amount": "750.00",
        "od_discount_percent": "30.00",
        "agent_comm_od_percent": "12.00",
        "agent_comm_net_percent": "0.00",
        "agent_comm_extra_percent": "0.00",
        "tds_percent": "5.00",
        "payment_type": "CASH",
        "paid_amount": "8580.00",
        # Net = 7500; Basic TP 4500 * 12% = 540; OD 3000 * 18% = 540; GST = 1080; Final = 8580.00
        "exp_net": Decimal("7500.00"),
        "exp_gst": Decimal("1080.00"),
        "exp_final": Decimal("8580.00"),
        "exp_gross_comm": Decimal("360.00"),
        "exp_tds": Decimal("18.00"),
        "exp_net_comm": Decimal("342.00"),
        "exp_outstanding": Decimal("0.00"),
    },
    # G7-11: 3-Wheeler PCV (PublicPCV3W) Comprehensive — 18% Uniform GST
    {
        "case_id": "G7-11",
        "vehicle_category": "PublicPCV3W",
        "product_type_id": 1,
        "business_type_id": 3,
        "sum_insured_idv": "200000.00",
        "od_premium": "2500.00",
        "tp_premium": "6500.00",
        "basic_tp_premium": "6500.00",
        "pa_owner_driver": "0.00",
        "ll_paid_driver": "0.00",
        "ncb_percent": "20.00",
        "ncb_amount": "625.00",
        "od_discount_percent": "20.00",
        "agent_comm_od_percent": "10.00",
        "agent_comm_net_percent": "5.00",
        "agent_comm_extra_percent": "0.00",
        "tds_percent": "5.00",
        "payment_type": "CASH",
        "paid_amount": "10620.00",
        # Net = 9000; GST 18% = 1620; Final = 10620.00
        # Comm: OD = 250 (TDS 12.50), TP = 325 (TDS 16.25) -> Gross 575.00, TDS 28.75, Net 546.25
        "exp_net": Decimal("9000.00"),
        "exp_gst": Decimal("1620.00"),
        "exp_final": Decimal("10620.00"),
        "exp_gross_comm": Decimal("575.00"),
        "exp_tds": Decimal("28.75"),
        "exp_net_comm": Decimal("546.25"),
        "exp_outstanding": Decimal("0.00"),
    },
    # G7-12: Passenger Taxi (PassengerTaxi(PCV)) Comprehensive — 45% NCB, 18% GST
    {
        "case_id": "G7-12",
        "vehicle_category": "PassengerTaxi(PCV)",
        "product_type_id": 1,
        "business_type_id": 3,
        "sum_insured_idv": "550000.00",
        "od_premium": "9000.00",
        "tp_premium": "11000.00",
        "basic_tp_premium": "11000.00",
        "pa_owner_driver": "0.00",
        "ll_paid_driver": "0.00",
        "ncb_percent": "45.00",
        "ncb_amount": "7364.00",
        "od_discount_percent": "30.00",
        "agent_comm_od_percent": "15.00",
        "agent_comm_net_percent": "0.00",
        "agent_comm_extra_percent": "0.00",
        "tds_percent": "5.00",
        "payment_type": "ONLINE",
        "paid_amount": "23600.00",
        # Net = 20000; GST 18% = 3600; Final = 23600.00
        "exp_net": Decimal("20000.00"),
        "exp_gst": Decimal("3600.00"),
        "exp_final": Decimal("23600.00"),
        "exp_gross_comm": Decimal("1350.00"),
        "exp_tds": Decimal("67.50"),
        "exp_net_comm": Decimal("1282.50"),
        "exp_outstanding": Decimal("0.00"),
    },
    # G7-13: School Bus (School_Bus) Comprehensive — 50% NCB, 18% GST
    {
        "case_id": "G7-13",
        "vehicle_category": "School_Bus",
        "product_type_id": 1,
        "business_type_id": 3,
        "sum_insured_idv": "1200000.00",
        "od_premium": "14000.00",
        "tp_premium": "26000.00",
        "basic_tp_premium": "26000.00",
        "pa_owner_driver": "0.00",
        "ll_paid_driver": "0.00",
        "ncb_percent": "50.00",
        "ncb_amount": "14000.00",
        "od_discount_percent": "40.00",
        "agent_comm_od_percent": "10.00",
        "agent_comm_net_percent": "5.00",
        "agent_comm_extra_percent": "0.00",
        "tds_percent": "5.00",
        "payment_type": "NEFT",
        "paid_amount": "47200.00",
        # Net = 40000; GST 18% = 7200; Final = 47200.00
        # Comm: OD = 1400 (TDS 70), TP = 1300 (TDS 65) -> Gross 2700, TDS 135, Net 2565
        "exp_net": Decimal("40000.00"),
        "exp_gst": Decimal("7200.00"),
        "exp_final": Decimal("47200.00"),
        "exp_gross_comm": Decimal("2700.00"),
        "exp_tds": Decimal("135.00"),
        "exp_net_comm": Decimal("2565.00"),
        "exp_outstanding": Decimal("0.00"),
    },
    # G7-14: Miscellaneous / Tractor (Misc-D) Comprehensive — 20% NCB, 18% GST
    {
        "case_id": "G7-14",
        "vehicle_category": "Misc-D",
        "product_type_id": 1,
        "business_type_id": 3,
        "sum_insured_idv": "600000.00",
        "od_premium": "6000.00",
        "tp_premium": "9000.00",
        "basic_tp_premium": "9000.00",
        "pa_owner_driver": "0.00",
        "ll_paid_driver": "0.00",
        "ncb_percent": "20.00",
        "ncb_amount": "1500.00",
        "od_discount_percent": "35.00",
        "agent_comm_od_percent": "15.00",
        "agent_comm_net_percent": "0.00",
        "agent_comm_extra_percent": "0.00",
        "tds_percent": "5.00",
        "payment_type": "CASH",
        "paid_amount": "17700.00",
        # Net = 15000; GST 18% = 2700; Final = 17700.00
        "exp_net": Decimal("15000.00"),
        "exp_gst": Decimal("2700.00"),
        "exp_final": Decimal("17700.00"),
        "exp_gross_comm": Decimal("900.00"),
        "exp_tds": Decimal("45.00"),
        "exp_net_comm": Decimal("855.00"),
        "exp_outstanding": Decimal("0.00"),
    },
]


@pytest.mark.asyncio
@pytest.mark.parametrize("case", DIRECT_GOLDEN_CASES, ids=[c["case_id"] for c in DIRECT_GOLDEN_CASES])
async def test_golden_parity_cases_g7_01_to_g7_14(
    async_client: AsyncClient,
    db_session: AsyncSession,
    case: dict,
):
    """Executes golden cases G7-01 through G7-14 and asserts 0.00 financial delta."""
    _, headers = await create_user_with_role(db_session, role_name="OPERATOR", branch_id=101)
    cust, veh = await create_synthetic_customer_and_vehicle(
        db_session, branch_id=101, reg_no=f"MH12{case['case_id'].replace('-', '')}"
    )

    pay_item = {
        "payment_type": case["payment_type"],
        "paid_amount": case["paid_amount"],
    }
    if case["payment_type"] == "CHEQUE":
        pay_item["docno"] = "CHQ9001"
        pay_item["bankname"] = "SBI"

    resp = await async_client.post(
        "/api/v1/policies/book",
        headers=headers,
        json={
            "customer_id": cust.CustomerId,
            "cust_veh_id": veh.CustVehId,
            "policy_no": f"TEST_POLICY_{case['case_id']}",
            "vehicle_category": case["vehicle_category"],
            "product_type_id": case["product_type_id"],
            "business_type_id": case["business_type_id"],
            "claim_in_previous_policy": case.get("claim_in_previous_policy", False),
            "gcv_split_tp_gst": case.get("gcv_split_tp_gst", True),
            "sum_insured_idv": case["sum_insured_idv"],
            "od_premium": case["od_premium"],
            "tp_premium": case["tp_premium"],
            "basic_tp_premium": case["basic_tp_premium"],
            "pa_owner_driver": case["pa_owner_driver"],
            "ll_paid_driver": case["ll_paid_driver"],
            "ncb_percent": case["ncb_percent"],
            "ncb_amount": case["ncb_amount"],
            "od_discount_percent": case["od_discount_percent"],
            "commission": {
                "agent_id": 101,
                "agent_comm_od_percent": case["agent_comm_od_percent"],
                "agent_comm_net_percent": case["agent_comm_net_percent"],
                "agent_comm_extra_percent": case["agent_comm_extra_percent"],
                "tds_percent": case["tds_percent"],
            },
            "payments": [pay_item],
        },
    )
    assert resp.status_code == 201, f"{case['case_id']} failed: {resp.text}"
    body = resp.json()
    prem = body["premium_summary"]
    comm = body["commission_summary"]
    pay = body["payment_summary"]
    acct = {e["acc_trans_id"]: Decimal(e["amount"]) for e in body["accounting_entries"]}

    assert Decimal(prem["net_premium"]) - case["exp_net"] == Decimal("0.00")
    assert Decimal(prem["gst_amount"]) - case["exp_gst"] == Decimal("0.00")
    assert Decimal(prem["final_premium"]) - case["exp_final"] == Decimal("0.00")

    assert Decimal(comm["total_gross_commission"]) - case["exp_gross_comm"] == Decimal("0.00")
    assert Decimal(comm["total_tds_amount"]) - case["exp_tds"] == Decimal("0.00")
    assert Decimal(comm["total_net_commission"]) - case["exp_net_comm"] == Decimal("0.00")

    assert Decimal(pay["outstanding_amount"]) - case["exp_outstanding"] == Decimal("0.00")

    # Verify double-entry accounting rows (AccTransId = 1, 2, 3)
    assert acct[1] == case["exp_final"]
    assert acct[2] == Decimal(case["paid_amount"])
    assert acct[3] == -case["exp_net_comm"]


# ============================================================================
# Cases G7-15 to G7-25: 11 Workflow, Commission, Payment & Reversal Golden Cases
# ============================================================================


@pytest.mark.asyncio
async def test_golden_parity_cases_g7_15_to_g7_25(
    async_client: AsyncClient,
    db_session: AsyncSession,
):
    """
    Executes golden cases G7-15 through G7-25 covering:
    - G7-15: Self-Quotation Conversion (Zero Double-Counting of NCB/OD Discount/GST)
    - G7-16: Assisted Quotation Request Conversion
    - G7-17: Staged Proposal -> Approval -> Booking
    - G7-18: Multi-Bucket Commission (OD + Net + Extra) with 5% TDS
    - G7-19: Single Headline Agent Commission Fallback
    - G7-20: Franchise Commission Split & Profit Margin (tbl_franchisecommission)
    - G7-21: Cut & Pay Full NetCommission Deduction (tbl_cutnpaycommpayable)
    - G7-22: Cut & Pay Custom Partial Deduction + Remaining Balance
    - G7-23: E-Wallet + Partial Cash -> Subsequent Settlement Payment
    - G7-24: Multi-Instrument Split Payment (Cash + Cheque + Online Direct to Insurer)
    - G7-25: Policy Cancellation & Full Ledger Reversal
    """
    _, admin_headers = await create_user_with_role(db_session, role_name="ADMIN", branch_id=101)
    cust, veh = await create_synthetic_customer_and_vehicle(
        db_session, branch_id=101, reg_no="MH12GOLD1525"
    )

    # ------------------------------------------------------------------------
    # G7-15: Self-Quotation Conversion (Zero Double-Counting)
    # ------------------------------------------------------------------------
    sq_resp = await async_client.post(
        "/api/v1/quotations/self",
        headers=admin_headers,
        json={
            "title": "GOLDEN_G7_15_SELF_QUOT",
            "registration_no": "MH12GOLD1525",
            "calculation_input": {
                "vehicle_category": "PVT",
                "product_type_id": 1,
                "business_type_id": 3,
                "insurance_company_id": 1,
                "cubic_capacity": 1197,
                "zone": "A",
                "vehicle_age_override": "2.0",
                "base_idv_override": "500000",
                "selected_idv": "500000",
                "ncb_percent": "20",
                "od_discount_override": "40",
            },
        },
    )
    assert sq_resp.status_code == 201
    sq = sq_resp.json()

    g15_resp = await async_client.post(
        "/api/v1/policies/book",
        headers=admin_headers,
        json={
            "customer_id": cust.CustomerId,
            "cust_veh_id": veh.CustVehId,
            "quotation_id": sq["quatation_id"],
            "quotation_source_type": "SELF_QUOTATION",
            "policy_no": "TEST_POLICY_G7_15",
            "payments": [{"payment_type": "CASH", "paid_amount": str(sq["final_premium"])}],
        },
    )
    assert g15_resp.status_code == 201
    g15 = g15_resp.json()
    assert Decimal(g15["premium_summary"]["od_premium"]) == Decimal(sq["total_od_premium"])
    assert Decimal(g15["premium_summary"]["tp_premium"]) == Decimal(sq["total_liability_premium"])
    assert Decimal(g15["premium_summary"]["net_premium"]) == Decimal(sq["total_net_premium"])
    assert Decimal(g15["premium_summary"]["gst_amount"]) == Decimal(sq["gst_amount"])
    assert Decimal(g15["premium_summary"]["final_premium"]) == Decimal(sq["final_premium"])

    # ------------------------------------------------------------------------
    # G7-16: Assisted Quotation Request Conversion
    # ------------------------------------------------------------------------
    aq_resp = await async_client.post(
        "/api/v1/quotations/requests",
        headers=admin_headers,
        json={
            "insurance_company_id": "2",
            "mobile_no": "9876543210",
            "ncb": "25",
            "vehicle_no": "MH12GOLD1525",
            "vehicle_type": "PVT",
            "vehicle_make": "MARUTI",
            "vehicle_model": "SWIFT",
            "vehicle_variance": "ZXI",
            "product_type": "1",
        },
    )
    assert aq_resp.status_code == 201
    aq_id = aq_resp.json()["quatation_id"]

    g16_resp = await async_client.post(
        "/api/v1/policies/book",
        headers=admin_headers,
        json={
            "customer_id": cust.CustomerId,
            "cust_veh_id": veh.CustVehId,
            "quotation_id": aq_id,
            "quotation_source_type": "ASSISTED_REQUEST",
            "insurance_company_id": 2,
            "policy_no": "TEST_POLICY_G7_16",
            "vehicle_category": "PVT",
            "od_premium": "7000.00",
            "tp_premium": "3000.00",
            "ncb_percent": "25.00",
            "ncb_amount": "2333.00",
            "payments": [{"payment_type": "ONLINE", "paid_amount": "11800.00"}],
        },
    )
    assert g16_resp.status_code == 201
    assert g16_resp.json()["quotation_code"] == aq_resp.json()["quatation_code"]

    # ------------------------------------------------------------------------
    # G7-17: Staged Proposal -> Approval -> Policy Booking
    # ------------------------------------------------------------------------
    p17 = await async_client.post(
        "/api/v1/policies/proposals",
        headers=admin_headers,
        json={
            "customer_name": "TEST_CUSTOMER_G7_17",
            "contact_no": "9876543210",
            "registration_no": "MH12GOLD1525",
            "insurance_company_id": 1,
            "od_premium": "6000.00",
            "tp_premium": "4000.00",
            "net_premium": "10000.00",
            "final_premium": "11800.00",
            "cash_paid_amount": "11800.00",
        },
    )
    assert p17.status_code == 201
    tid_17 = p17.json()["trans_id"]
    await async_client.post(
        f"/api/v1/policies/proposals/{tid_17}/approve",
        headers=admin_headers,
        json={"stage": "CASHIER", "approved": True},
    )
    g17_resp = await async_client.post(
        "/api/v1/policies/book",
        headers=admin_headers,
        json={
            "customer_id": cust.CustomerId,
            "cust_veh_id": veh.CustVehId,
            "proposal_trans_id": tid_17,
            "policy_no": "TEST_POLICY_G7_17",
            "vehicle_category": "PVT",
            "od_premium": "6000.00",
            "tp_premium": "4000.00",
            "payments": [{"payment_type": "CASH", "paid_amount": "11800.00"}],
        },
    )
    assert g17_resp.status_code == 201
    assert g17_resp.json()["proposal_trans_id"] == tid_17

    # ------------------------------------------------------------------------
    # G7-18: Multi-Bucket Commission (OD 15% + Net 5% + Extra 2.5%, TDS 5%)
    # ------------------------------------------------------------------------
    g18_resp = await async_client.post(
        "/api/v1/policies/book",
        headers=admin_headers,
        json={
            "customer_id": cust.CustomerId,
            "cust_veh_id": veh.CustVehId,
            "policy_no": "TEST_POLICY_G7_18",
            "vehicle_category": "PVT",
            "od_premium": "12000.00",
            "tp_premium": "6000.00",
            "commission": {
                "agent_id": 101,
                "agent_comm_od_percent": "15.00",
                "agent_comm_net_percent": "5.00",
                "agent_comm_extra_percent": "2.50",
                "tds_percent": "5.00",
            },
            "payments": [{"payment_type": "CASH", "paid_amount": "21240.00"}],
        },
    )
    assert g18_resp.status_code == 201
    c18 = g18_resp.json()["commission_summary"]
    assert Decimal(c18["total_gross_commission"]) == Decimal("2400.00")
    assert Decimal(c18["total_tds_amount"]) == Decimal("120.00")
    assert Decimal(c18["total_net_commission"]) == Decimal("2280.00")

    # ------------------------------------------------------------------------
    # G7-19: Single Headline Agent Commission (12% on Net Premium)
    # ------------------------------------------------------------------------
    g19_resp = await async_client.post(
        "/api/v1/policies/book",
        headers=admin_headers,
        json={
            "customer_id": cust.CustomerId,
            "cust_veh_id": veh.CustVehId,
            "policy_no": "TEST_POLICY_G7_19",
            "vehicle_category": "PVT",
            "od_premium": "7000.00",
            "tp_premium": "3000.00",
            "commission": {
                "agent_id": 102,
                "agent_comm_percent": "12.00",
                "tds_percent": "5.00",
            },
            "payments": [{"payment_type": "CASH", "paid_amount": "11800.00"}],
        },
    )
    assert g19_resp.status_code == 201
    c19 = g19_resp.json()["commission_summary"]
    assert Decimal(c19["total_gross_commission"]) == Decimal("1200.00")
    assert Decimal(c19["total_tds_amount"]) == Decimal("60.00")
    assert Decimal(c19["total_net_commission"]) == Decimal("1140.00")
    assert c19["agent_comm_pay_id"] is not None

    # ------------------------------------------------------------------------
    # G7-20: Franchise Commission Split & Profit Margin
    # ------------------------------------------------------------------------
    g20_resp = await async_client.post(
        "/api/v1/policies/book",
        headers=admin_headers,
        json={
            "customer_id": cust.CustomerId,
            "cust_veh_id": veh.CustVehId,
            "policy_no": "TEST_POLICY_G7_20",
            "vehicle_category": "PVT",
            "od_premium": "10000.00",
            "tp_premium": "5000.00",
            "commission": {
                "agent_id": 103,
                "franchise_id": 301,
                "agent_comm_od_percent": "15.00",
                "franchise_comm_od_percent": "20.00",
                "tds_percent": "5.00",
            },
            "payments": [{"payment_type": "CASH", "paid_amount": "17700.00"}],
        },
    )
    assert g20_resp.status_code == 201
    c20 = g20_resp.json()["commission_summary"]
    assert c20["franchise_comm_id"] is not None
    assert Decimal(c20["total_net_commission"]) == Decimal("1425.00")
    assert Decimal(c20["franchise_net_commission"]) == Decimal("1900.00")

    # ------------------------------------------------------------------------
    # G7-21: Cut & Pay Full NetCommission Deduction
    # ------------------------------------------------------------------------
    g21_resp = await async_client.post(
        "/api/v1/policies/book",
        headers=admin_headers,
        json={
            "customer_id": cust.CustomerId,
            "cust_veh_id": veh.CustVehId,
            "policy_no": "TEST_POLICY_G7_21",
            "vehicle_category": "PVT",
            "od_premium": "10000.00",
            "tp_premium": "5000.00",
            "cutnpay_enabled": True,
            "commission": {
                "agent_id": 104,
                "agent_comm_od_percent": "10.00",
                "tds_percent": "5.00",
            },
            # Final = 17700, NetComm = 950 -> RequiredPayable = 16750
            "payments": [{"payment_type": "ONLINE", "paid_amount": "16750.00"}],
        },
    )
    assert g21_resp.status_code == 201
    p21 = g21_resp.json()["payment_summary"]
    assert Decimal(p21["cutnpay_deduction"]) == Decimal("950.00")
    assert Decimal(p21["required_payable_amount"]) == Decimal("16750.00")
    assert Decimal(p21["outstanding_amount"]) == Decimal("0.00")
    assert g21_resp.json()["commission_summary"]["cutnpay_payable_id"] is not None

    # ------------------------------------------------------------------------
    # G7-22: Cut & Pay Partial Custom Deduction (500 out of 950 NetComm)
    # ------------------------------------------------------------------------
    g22_resp = await async_client.post(
        "/api/v1/policies/book",
        headers=admin_headers,
        json={
            "customer_id": cust.CustomerId,
            "cust_veh_id": veh.CustVehId,
            "policy_no": "TEST_POLICY_G7_22",
            "vehicle_category": "PVT",
            "od_premium": "10000.00",
            "tp_premium": "5000.00",
            "cutnpay_enabled": True,
            "cutnpay_amount": "500.00",
            "commission": {
                "agent_id": 104,
                "agent_comm_od_percent": "10.00",
                "tds_percent": "5.00",
            },
            # Final = 17700, CutNPay = 500 -> Required = 17200; Paid = 17000 -> Outstanding = 200.00
            "payments": [{"payment_type": "CASH", "paid_amount": "17000.00"}],
        },
    )
    assert g22_resp.status_code == 201
    p22 = g22_resp.json()["payment_summary"]
    assert Decimal(p22["cutnpay_deduction"]) == Decimal("500.00")
    assert Decimal(p22["required_payable_amount"]) == Decimal("17200.00")
    assert Decimal(p22["outstanding_amount"]) == Decimal("200.00")

    # ------------------------------------------------------------------------
    # G7-23: E-Wallet + Partial Cash -> Subsequent Settlement Payment
    # ------------------------------------------------------------------------
    g23_resp = await async_client.post(
        "/api/v1/policies/book",
        headers=admin_headers,
        json={
            "customer_id": cust.CustomerId,
            "cust_veh_id": veh.CustVehId,
            "policy_no": "TEST_POLICY_G7_23",
            "vehicle_category": "PVT",
            "od_premium": "6000.00",
            "tp_premium": "4000.00",
            "ewallet_amount_used": "2800.00",
            "payments": [{"payment_type": "CASH", "paid_amount": "5000.00"}],
        },
    )
    assert g23_resp.status_code == 201
    tx23_id = g23_resp.json()["transaction_id"]
    assert Decimal(g23_resp.json()["payment_summary"]["outstanding_amount"]) == Decimal("4000.00")

    g23_settle = await async_client.post(
        f"/api/v1/policies/{tx23_id}/payments",
        headers=admin_headers,
        json={"payment_type": "UPI", "paid_amount": "4000.00", "docno": "UPI23"},
    )
    assert g23_settle.status_code == 201
    assert Decimal(g23_settle.json()["payment_summary"]["outstanding_amount"]) == Decimal("0.00")
    assert g23_settle.json()["t_status"] == "Booked"

    # ------------------------------------------------------------------------
    # G7-24: Multi-Instrument Split Payment (Cash + Cheque + Online Direct)
    # ------------------------------------------------------------------------
    g24_resp = await async_client.post(
        "/api/v1/policies/book",
        headers=admin_headers,
        json={
            "customer_id": cust.CustomerId,
            "cust_veh_id": veh.CustVehId,
            "policy_no": "TEST_POLICY_G7_24",
            "vehicle_category": "PVT",
            "od_premium": "6000.00",
            "tp_premium": "4000.00",
            "online_payment_to_company": "3800.00",
            "payments": [
                {"payment_type": "CASH", "paid_amount": "3000.00"},
                {
                    "payment_type": "CHEQUE",
                    "paid_amount": "5000.00",
                    "docno": "CHQ24001",
                    "bankname": "ICICI BANK",
                },
            ],
        },
    )
    assert g24_resp.status_code == 201
    p24 = g24_resp.json()["payment_summary"]
    assert Decimal(p24["paid_amount"]) == Decimal("11800.00")
    assert Decimal(p24["outstanding_amount"]) == Decimal("0.00")
    assert len(p24["payments"]) == 2

    # ------------------------------------------------------------------------
    # G7-25: Policy Cancellation & Full Ledger Reversal
    # ------------------------------------------------------------------------
    tx24_id = g24_resp.json()["transaction_id"]
    g25_cancel = await async_client.post(
        f"/api/v1/policies/{tx24_id}/cancel",
        headers=admin_headers,
        json={"reason": "Golden Case G7-25 Policy Cancellation"},
    )
    assert g25_cancel.status_code == 200
    assert g25_cancel.json()["t_status"] == "Cancelled"
    assert g25_cancel.json()["payments_reversed"] == 2
    assert g25_cancel.json()["accounting_entries_reversed"] == 3
