"""
Phase 7 Unit Tests — Policy Booking Financial, Commission, Payment & Accounting Math.

Verifies:
- Strict Decimal-only calculations (zero float usage)
- Multi-bucket Commission (OD, Net/TP, Extra) and TDS (5%) rounding (ROUND_HALF_UP)
- Franchise commission split and profit margin math
- Cut & Pay deduction, E-Wallet deduction, and overpayment rejection
- Cheque instrument metadata validation
- Double-entry accounting ledger polarity (AccTransId = 1, 2, 3 where AccTransId=3 is -NetCommission)
- Financial year resolution across April 1 boundary
"""
from datetime import date
from decimal import Decimal
import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.repositories.policy_booking import resolve_financial_year
from app.schemas.policy import (
    CommissionInput,
    PaymentInstrumentCreateRequest,
    PolicyPreviewRequest,
    PolicyPremiumSummary,
)
from app.services.policy_booking import PolicyBookingService


def _make_sample_premium(
    od: Decimal = Decimal("10000.00"),
    tp: Decimal = Decimal("5000.00"),
    gst: Decimal = Decimal("2700.00"),
    pa_owner: Decimal = Decimal("375.00"),
    ncb_pct: Decimal = Decimal("20.00"),
    ncb_amt: Decimal = Decimal("2500.00"),
) -> PolicyPremiumSummary:
    net = od + tp
    final = net + gst
    return PolicyPremiumSummary(
        sum_insured_idv=Decimal("550000.00"),
        gvw=Decimal("0.00"),
        od_premium=od,
        tp_premium=tp,
        basic_tp_premium=tp - pa_owner,
        net_premium=net,
        gst_amount=gst,
        final_premium=final,
        ncb_percent=ncb_pct,
        ncb_amount=ncb_amt,
        od_discount_percent=Decimal("40.00"),
        od_discount_amount=Decimal("6000.00"),
        addon_rate_percent=Decimal("0.45"),
        addon_premium=Decimal("2475.00"),
        is_nill_dep=True,
        pa_owner_driver=pa_owner,
    )


def test_financial_year_resolution_across_april_boundary() -> None:
    fy_oct, short_oct = resolve_financial_year(date(2026, 10, 6))
    assert fy_oct == "2026-2027"
    assert short_oct == "2627"

    fy_feb, short_feb = resolve_financial_year(date(2027, 2, 15))
    assert fy_feb == "2026-2027"
    assert short_feb == "2627"

    fy_apr1, short_apr1 = resolve_financial_year(date(2026, 4, 1))
    assert fy_apr1 == "2026-2027"
    assert short_apr1 == "2627"

    fy_mar31, short_mar31 = resolve_financial_year(date(2026, 3, 31))
    assert fy_mar31 == "2025-2026"
    assert short_mar31 == "2526"


def test_multi_bucket_commission_and_tds_decimal_math() -> None:
    prem = _make_sample_premium(
        od=Decimal("12000.00"),
        tp=Decimal("6000.00"),
        gst=Decimal("3240.00"),
    )
    comm_in = CommissionInput(
        agent_comm_od_percent=Decimal("15.00"),
        agent_comm_net_percent=Decimal("5.00"),
        agent_comm_extra_percent=Decimal("2.50"),
        tds_percent=Decimal("5.00"),
        franchise_comm_od_percent=Decimal("18.00"),
        franchise_comm_net_percent=Decimal("6.00"),
        franchise_comm_extra_percent=Decimal("3.00"),
    )
    res = PolicyBookingService.calculate_commission_summary(
        premium=prem,
        comm_in=comm_in,
        eff_agent_id=101,
        eff_sales_ex_id=202,
        eff_franchise_id=303,
        eff_location_head_id=404,
    )

    # OD: 12000 * 15% = 1800.00; TDS 5% = 90.00; Net = 1710.00
    assert res.agent_comm_od_amount == Decimal("1800.00")
    assert res.tds_od_amount == Decimal("90.00")
    assert res.net_comm_od_amount == Decimal("1710.00")

    # Net/TP: 6000 * 5% = 300.00; TDS 5% = 15.00; Net = 285.00
    assert res.agent_comm_net_amount == Decimal("300.00")
    assert res.tds_net_amount == Decimal("15.00")
    assert res.net_comm_net_amount == Decimal("285.00")

    # Extra (on OD base 12000): 12000 * 2.5% = 300.00; TDS 5% = 15.00; Net = 285.00
    assert res.agent_comm_extra_amount == Decimal("300.00")
    assert res.tds_extra_amount == Decimal("15.00")
    assert res.net_comm_extra_amount == Decimal("285.00")

    # Totals: Gross = 2400.00, TDS = 120.00, Net = 2280.00
    assert res.total_gross_commission == Decimal("2400.00")
    assert res.total_tds_amount == Decimal("120.00")
    assert res.total_net_commission == Decimal("2280.00")

    # Franchise: OD 2160 + Net 360 + Extra 360 = 2880.00; TDS 5% = 144.00; Net = 2736.00
    assert res.franchise_gross_commission == Decimal("2880.00")
    assert res.franchise_tds_amount == Decimal("144.00")
    assert res.franchise_net_commission == Decimal("2736.00")


def test_single_headline_commission_fallback() -> None:
    prem = _make_sample_premium(
        od=Decimal("8000.00"),
        tp=Decimal("2000.00"),
        gst=Decimal("1800.00"),
    )
    comm_in = CommissionInput(
        agent_comm_percent=Decimal("10.00"),
        tds_percent=Decimal("5.00"),
    )
    res = PolicyBookingService.calculate_commission_summary(
        premium=prem,
        comm_in=comm_in,
        eff_agent_id=101,
        eff_sales_ex_id=0,
        eff_franchise_id=0,
        eff_location_head_id=0,
    )
    # Net premium = 10000.00 * 10% = 1000.00; TDS = 50.00; NetComm = 950.00
    assert res.total_gross_commission == Decimal("1000.00")
    assert res.total_tds_amount == Decimal("50.00")
    assert res.total_net_commission == Decimal("950.00")


def test_payment_summary_full_partial_and_cutnpay() -> None:
    prem = _make_sample_premium(
        od=Decimal("10000.00"),
        tp=Decimal("5000.00"),
        gst=Decimal("2700.00"),
    )  # final_premium = 17700.00
    comm_in = CommissionInput(
        agent_comm_od_percent=Decimal("10.00"),
        tds_percent=Decimal("5.00"),
    )
    comm = PolicyBookingService.calculate_commission_summary(
        prem, comm_in, 101, 0, 0, 0
    )
    # Gross comm = 1000, TDS = 50, NetComm = 950.00
    assert comm.total_net_commission == Decimal("950.00")

    # 1. Cut & Pay enabled: Required payable = 17700 - 950 = 16750.00
    pay_cnp = PolicyBookingService.calculate_payment_summary(
        premium=prem,
        commission=comm,
        cutnpay_enabled=True,
        cutnpay_amount=None,
        ewallet_amount_used=Decimal("750.00"),
        online_payment_to_company=Decimal("0.00"),
        payments=[
            PaymentInstrumentCreateRequest(
                payment_type="ONLINE",
                paid_amount=Decimal("16000.00"),
                docno="UTR123456",
            )
        ],
        branch_id=1,
    )
    assert pay_cnp.cutnpay_deduction == Decimal("950.00")
    assert pay_cnp.required_payable_amount == Decimal("16750.00")
    assert pay_cnp.paid_amount == Decimal("16750.00")
    assert pay_cnp.outstanding_amount == Decimal("0.00")
    assert pay_cnp.is_complete_payment == 1

    # 2. Partial payment: Paid 10000 out of 17700 -> Outstanding = 7700.00
    pay_partial = PolicyBookingService.calculate_payment_summary(
        premium=prem,
        commission=comm,
        cutnpay_enabled=False,
        cutnpay_amount=None,
        ewallet_amount_used=Decimal("0.00"),
        online_payment_to_company=Decimal("0.00"),
        payments=[
            PaymentInstrumentCreateRequest(
                payment_type="CASH",
                paid_amount=Decimal("10000.00"),
            )
        ],
        branch_id=1,
    )
    assert pay_partial.required_payable_amount == Decimal("17700.00")
    assert pay_partial.paid_amount == Decimal("10000.00")
    assert pay_partial.outstanding_amount == Decimal("7700.00")
    assert pay_partial.is_complete_payment == 0


def test_overpayment_and_invalid_cutnpay_rejected() -> None:
    prem = _make_sample_premium(
        od=Decimal("10000.00"),
        tp=Decimal("5000.00"),
        gst=Decimal("2700.00"),
    )  # final = 17700.00
    comm_in = CommissionInput(agent_comm_od_percent=Decimal("10.00"))
    comm = PolicyBookingService.calculate_commission_summary(
        prem, comm_in, 101, 0, 0, 0
    )

    # Overpayment > 17700.00 raises 422
    with pytest.raises(HTTPException) as exc_info:
        PolicyBookingService.calculate_payment_summary(
            premium=prem,
            commission=comm,
            cutnpay_enabled=False,
            cutnpay_amount=None,
            ewallet_amount_used=Decimal("0.00"),
            online_payment_to_company=Decimal("0.00"),
            payments=[
                PaymentInstrumentCreateRequest(
                    payment_type="CASH",
                    paid_amount=Decimal("18000.00"),
                )
            ],
            branch_id=1,
        )
    assert exc_info.value.status_code == 422

    # cutnpay_amount > NetCommission (950.00) raises 422
    with pytest.raises(HTTPException) as exc_cnp:
        PolicyBookingService.calculate_payment_summary(
            premium=prem,
            commission=comm,
            cutnpay_enabled=True,
            cutnpay_amount=Decimal("1200.00"),
            ewallet_amount_used=Decimal("0.00"),
            online_payment_to_company=Decimal("0.00"),
            payments=[],
            branch_id=1,
        )
    assert exc_cnp.value.status_code == 422


def test_cheque_instrument_requires_docno_and_bankname() -> None:
    with pytest.raises(ValidationError):
        PaymentInstrumentCreateRequest(
            payment_type="CHEQUE",
            paid_amount=Decimal("5000.00"),
            docno=None,
            bankname="HDFC BANK",
        )

    with pytest.raises(ValidationError):
        PaymentInstrumentCreateRequest(
            payment_type="CHEQUE",
            paid_amount=Decimal("5000.00"),
            docno="CHQ00123",
            bankname=None,
        )

    valid_chq = PaymentInstrumentCreateRequest(
        payment_type="CHEQUE",
        paid_amount=Decimal("5000.00"),
        docno="CHQ00123",
        bankname="HDFC BANK",
    )
    assert valid_chq.payment_type == "CHEQUE"


def test_accounting_entries_polarity_acctransid_1_2_3() -> None:
    prem = _make_sample_premium(
        od=Decimal("10000.00"),
        tp=Decimal("5000.00"),
        gst=Decimal("2700.00"),
    )  # final = 17700.00
    comm_in = CommissionInput(
        agent_comm_od_percent=Decimal("10.00"),
        tds_percent=Decimal("5.00"),
    )
    comm = PolicyBookingService.calculate_commission_summary(
        prem, comm_in, 101, 0, 0, 0
    )  # NetComm = 950.00
    pay = PolicyBookingService.calculate_payment_summary(
        premium=prem,
        commission=comm,
        cutnpay_enabled=False,
        cutnpay_amount=None,
        ewallet_amount_used=Decimal("0.00"),
        online_payment_to_company=Decimal("0.00"),
        payments=[
            PaymentInstrumentCreateRequest(
                payment_type="CASH",
                paid_amount=Decimal("17700.00"),
            )
        ],
        branch_id=1,
    )

    entries = PolicyBookingService.build_accounting_entries(
        premium=prem,
        commission=comm,
        payment=pay,
        branch_id=1,
        ledger_m_id=1,
        customer_id=501,
        cust_veh_id=601,
        transaction_id=701,
        inward_no="INW-01-2627-000001",
    )
    assert len(entries) == 3
    by_type = {e.acc_trans_id: e for e in entries}

    # AccTransId = 1: +17700.00 (Policy Premium Receivable)
    assert by_type[1].amount == Decimal("17700.00")
    assert by_type[1].transaction_type == "POLICY_BOOKING"

    # AccTransId = 2: +17700.00 (Policy Payment Receipt)
    assert by_type[2].amount == Decimal("17700.00")
    assert by_type[2].transaction_type == "POLICY_PAYMENT"

    # AccTransId = 3: -950.00 (Unclear Policy Commission Entry - strictly negative!)
    assert by_type[3].amount == Decimal("-950.00")
    assert by_type[3].transaction_type == "UNCLEAR_COMMISSION"


def test_invalid_ncb_slab_rejected_in_schema() -> None:
    with pytest.raises(ValidationError):
        PolicyPreviewRequest(
            vehicle_category="PVT",
            od_premium=Decimal("5000.00"),
            tp_premium=Decimal("2000.00"),
            ncb_percent=Decimal("15.00"),  # Not in {0, 20, 25, 35, 45, 50}
        )


def test_gap_p7_001_gcv_hdfc_ergo_net_only_commission_branch() -> None:
    """
    GAP-P7-001 (LBR-047):
    When PolicyTypeId > 18 (GCV) and InsuranceCompanyId == 2 (HDFC ERGO),
    commission is calculated on Total Net Premium (OD + TP) using agent_comm_net_percent,
    with OD and Extra commission buckets forced to 0.00.
    """
    prem = _make_sample_premium(
        od=Decimal("12000.00"),
        tp=Decimal("8000.00"),
        gst=Decimal("2560.00"),
    )  # net_premium = 20000.00
    comm_in = CommissionInput(
        agent_comm_od_percent=Decimal("15.00"),
        agent_comm_net_percent=Decimal("10.00"),
        agent_comm_extra_percent=Decimal("2.50"),
        tds_percent=Decimal("5.00"),
        franchise_comm_od_percent=Decimal("18.00"),
        franchise_comm_net_percent=Decimal("12.00"),
        franchise_comm_extra_percent=Decimal("3.00"),
    )
    res = PolicyBookingService.calculate_commission_summary(
        premium=prem,
        comm_in=comm_in,
        eff_agent_id=101,
        eff_sales_ex_id=0,
        eff_franchise_id=303,
        eff_location_head_id=0,
        insurance_company_id=2,
        policy_type_id=19,
    )
    assert res.agent_comm_od_amount == Decimal("0.00")
    assert res.agent_comm_extra_amount == Decimal("0.00")
    # Net = 20000 * 10% = 2000.00; TDS 5% = 100.00; NetComm = 1900.00
    assert res.agent_comm_net_amount == Decimal("2000.00")
    assert res.total_gross_commission == Decimal("2000.00")
    assert res.total_tds_amount == Decimal("100.00")
    assert res.total_net_commission == Decimal("1900.00")
    # Franchise Net = 20000 * 12% = 2400.00; TDS 5% = 120.00; Net = 2280.00
    assert res.franchise_gross_commission == Decimal("2400.00")
    assert res.franchise_tds_amount == Decimal("120.00")
    assert res.franchise_net_commission == Decimal("2280.00")


def test_gap_p7_002_non_motor_default_15_percent_tds() -> None:
    """
    GAP-P7-002 (LBR-107):
    When motor_or_non_motor == 'NONMOTOR', default TDS rate is 15.00% (NonMotorTDS=15).
    """
    prem = _make_sample_premium(
        od=Decimal("10000.00"),
        tp=Decimal("0.00"),
        gst=Decimal("1800.00"),
        pa_owner=Decimal("0.00"),
    )
    comm_in = CommissionInput(
        agent_comm_od_percent=Decimal("10.00"),
    )
    res = PolicyBookingService.calculate_commission_summary(
        premium=prem,
        comm_in=comm_in,
        eff_agent_id=101,
        eff_sales_ex_id=0,
        eff_franchise_id=0,
        eff_location_head_id=0,
        motor_or_non_motor="NONMOTOR",
    )
    # Gross = 1000.00; 15% TDS = 150.00; Net = 850.00
    assert res.tds_percent == Decimal("15.00")
    assert res.total_gross_commission == Decimal("1000.00")
    assert res.total_tds_amount == Decimal("150.00")
    assert res.total_net_commission == Decimal("850.00")

