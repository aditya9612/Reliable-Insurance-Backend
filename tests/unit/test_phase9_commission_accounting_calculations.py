"""
Phase 9 Unit Tests — Pure Commission, TDS, Cut & Pay, Franchise Overriding Spread,
Rounding Precision, Eligibility Gate, and Payout Metadata Encoding/Decoding.
"""
from decimal import Decimal
import pytest
from fastapi import HTTPException

from app.models.commission import AgentCommissionPayment, CutNPayCommPayable
from app.models.transaction import Transaction
from app.schemas.commission_accounting import CommissionPreviewRequest
from app.services.commission_accounting import (
    CommissionAccountingService,
    calculate_commission_preview_pure,
    payment_status_to_label,
)


def test_agent_od_commission_and_5pct_tds():
    req = CommissionPreviewRequest(
        od_premium=Decimal("10000.00"),
        tp_premium=Decimal("5000.00"),
        agent_id=101,
        agent_comm_od_pct=Decimal("15.00"),
        agent_tds_pct=Decimal("5.00"),
    )
    res = calculate_commission_preview_pure(req)
    assert res.net_premium == Decimal("15000.00")
    assert res.final_premium == Decimal("17700.00")
    assert res.agent_comm_od_amt == Decimal("1500.00")
    assert res.agent_tds_od_amt == Decimal("75.00")
    assert res.agent_net_od_amt == Decimal("1425.00")
    assert res.agent_gross_commission == Decimal("1500.00")
    assert res.agent_tds_amount == Decimal("75.00")
    assert res.agent_net_commission == Decimal("1425.00")
    assert res.agent_remaining_payable_amount == Decimal("1425.00")
    assert res.agent_initial_payment_status == Decimal("0.00")
    assert res.unclear_commission_account_amount == Decimal("-1425.00")


def test_agent_combined_od_net_extra_commission_with_half_up_rounding():
    req = CommissionPreviewRequest(
        od_premium=Decimal("8333.33"),
        tp_premium=Decimal("4166.67"),
        agent_id=102,
        agent_comm_od_pct=Decimal("12.50"),
        agent_comm_net_pct=Decimal("2.50"),
        agent_comm_extra_pct=Decimal("1.75"),
        agent_tds_pct=Decimal("5.00"),
    )
    res = calculate_commission_preview_pure(req)
    assert res.net_premium == Decimal("12500.00")
    # OD: 8333.33 * 12.50% = 1041.66625 -> 1041.67; TDS 5% = 52.0835 -> 52.08; Net = 989.59
    assert res.agent_comm_od_amt == Decimal("1041.67")
    assert res.agent_tds_od_amt == Decimal("52.08")
    assert res.agent_net_od_amt == Decimal("989.59")
    # Net: 12500 * 2.50% = 312.50; TDS 5% = 15.625 -> 15.63; Net = 296.87
    assert res.agent_comm_net_amt == Decimal("312.50")
    assert res.agent_tds_net_amt == Decimal("15.63")
    assert res.agent_net_net_amt == Decimal("296.87")
    # Extra: 8333.33 * 1.75% = 145.833275 -> 145.83; TDS 5% = 7.2915 -> 7.29; Net = 138.54
    assert res.agent_comm_extra_amt == Decimal("145.83")
    assert res.agent_tds_extra_amt == Decimal("7.29")
    assert res.agent_net_extra_amt == Decimal("138.54")
    # Totals
    assert res.agent_gross_commission == Decimal("1500.00")
    assert res.agent_tds_amount == Decimal("75.00")
    assert res.agent_net_commission == Decimal("1425.00")


def test_agent_flat_commission_fallback_and_zero_tds():
    req = CommissionPreviewRequest(
        od_premium=Decimal("5000.00"),
        tp_premium=Decimal("2000.00"),
        agent_comm_flat_amt=Decimal("650.00"),
        agent_tds_pct=Decimal("0.00"),
    )
    res = calculate_commission_preview_pure(req)
    assert res.agent_gross_commission == Decimal("650.00")
    assert res.agent_tds_amount == Decimal("0.00")
    assert res.agent_net_commission == Decimal("650.00")


def test_cutnpay_full_and_partial_deduction_and_over_deduction_guard():
    # 1. Full Cut & Pay deduction
    req_full = CommissionPreviewRequest(
        od_premium=Decimal("10000.00"),
        tp_premium=Decimal("0.00"),
        final_premium=Decimal("11800.00"),
        agent_comm_od_pct=Decimal("10.00"),
        agent_tds_pct=Decimal("5.00"),
        cutnpay_enabled=True,
    )
    res_full = calculate_commission_preview_pure(req_full)
    assert res_full.agent_net_commission == Decimal("950.00")
    assert res_full.cutnpay_deducted_amount == Decimal("950.00")
    assert res_full.customer_required_payable_amount == Decimal("10850.00")
    assert res_full.agent_initial_paid_adv_amt == Decimal("950.00")
    assert res_full.agent_remaining_payable_amount == Decimal("0.00")
    assert res_full.agent_initial_payment_status == Decimal("1.00")

    # 2. Partial Cut & Pay deduction
    req_part = CommissionPreviewRequest(
        od_premium=Decimal("10000.00"),
        tp_premium=Decimal("0.00"),
        final_premium=Decimal("11800.00"),
        agent_comm_od_pct=Decimal("10.00"),
        agent_tds_pct=Decimal("5.00"),
        cutnpay_enabled=True,
        cutnpay_amount=Decimal("400.00"),
    )
    res_part = calculate_commission_preview_pure(req_part)
    assert res_part.cutnpay_deducted_amount == Decimal("400.00")
    assert res_part.customer_required_payable_amount == Decimal("11400.00")
    assert res_part.agent_initial_paid_adv_amt == Decimal("400.00")
    assert res_part.agent_remaining_payable_amount == Decimal("550.00")
    assert res_part.agent_initial_payment_status == Decimal("2.00")

    # 3. Over-deduction > NetCommission rejected with 422
    req_over = CommissionPreviewRequest(
        od_premium=Decimal("10000.00"),
        tp_premium=Decimal("0.00"),
        final_premium=Decimal("11800.00"),
        agent_comm_od_pct=Decimal("10.00"),
        agent_tds_pct=Decimal("5.00"),
        cutnpay_enabled=True,
        cutnpay_amount=Decimal("950.01"),
    )
    with pytest.raises(HTTPException) as exc_info:
        calculate_commission_preview_pure(req_over)
    assert exc_info.value.status_code == 422


def test_franchise_commission_and_profit_of_net_commission_spread():
    req = CommissionPreviewRequest(
        od_premium=Decimal("10000.00"),
        tp_premium=Decimal("5000.00"),
        agent_id=201,
        agent_comm_od_pct=Decimal("10.00"),
        agent_tds_pct=Decimal("5.00"),
        franchise_id=301,
        franchise_comm_od_pct=Decimal("18.00"),
        franchise_comm_net_pct=Decimal("2.00"),
        franchise_tds_pct=Decimal("5.00"),
    )
    res = calculate_commission_preview_pure(req)
    # Agent: 10000 * 10% = 1000 gross, 50 TDS, 950 net
    assert res.agent_net_commission == Decimal("950.00")
    # Franchise: OD 10000 * 18% = 1800 (TDS 90, Net 1710) + Net 15000 * 2% = 300 (TDS 15, Net 285)
    assert res.franchise_gross_commission == Decimal("2100.00")
    assert res.franchise_tds_amount == Decimal("105.00")
    assert res.franchise_net_commission == Decimal("1995.00")
    # Spread = 1995.00 - 950.00 = 1045.00
    assert res.profit_of_net_commission == Decimal("1045.00")


def test_evaluate_payout_eligibility_all_gates():
    # 1. Eligible settled policy
    tx_ok = Transaction(
        TransanctionId=1,
        TStatus="Booked",
        OutstandingAmount=Decimal("0.00"),
        Ischequeclearing=0,
        ChequeBankStatus=0,
        isdeleted="0",
    )
    ok, reason = CommissionAccountingService.evaluate_payout_eligibility(tx_ok)
    assert ok is True
    assert reason == "ELIGIBLE"

    # 2. Unpaid customer outstanding balance
    tx_unpaid = Transaction(
        TransanctionId=2,
        TStatus="Pending",
        OutstandingAmount=Decimal("500.00"),
        Ischequeclearing=0,
        ChequeBankStatus=0,
        isdeleted="0",
    )
    ok2, r2 = CommissionAccountingService.evaluate_payout_eligibility(tx_unpaid)
    assert ok2 is False
    assert "OutstandingAmount" in r2

    # 3. Cheque pending clearance
    tx_chq = Transaction(
        TransanctionId=3,
        TStatus="Pending",
        OutstandingAmount=Decimal("0.00"),
        Ischequeclearing=1,
        ChequeBankStatus=0,
        isdeleted="0",
    )
    ok3, r3 = CommissionAccountingService.evaluate_payout_eligibility(tx_chq)
    assert ok3 is False
    assert "Ischequeclearing=1" in r3

    # 4. Dishonored cheque hold on CutNPayCommPayable
    cnp_hold = CutNPayCommPayable(CutNPayCommPayId=1, TransactionId=1, Flag="HOLD_CHEQUE_BOUNCE")
    ok4, r4 = CommissionAccountingService.evaluate_payout_eligibility(tx_ok, None, cnp_hold)
    assert ok4 is False
    assert "HOLD_CHEQUE_BOUNCE" in r4

    # 5. AgentCommissionPayment HOLD narration
    acp_hold = AgentCommissionPayment(AgentCommId=1, TransanctionId=1, Narration="HOLD: Cheque Bounced")
    ok5, r5 = CommissionAccountingService.evaluate_payout_eligibility(tx_ok, acp_hold, None)
    assert ok5 is False
    assert "HOLD:" in r5


def test_payout_extra2_encode_decode_roundtrip():
    allocs = [(101, 501, Decimal("950.00")), (102, 502, Decimal("475.50"))]
    encoded = CommissionAccountingService._encode_payout_extra2(
        voucher_no="VCH-CPAY-1001",
        allocations=allocs,
        idempotency_key="IDK-9001",
        bank_reference="UTR123456",
    )
    v_no, idemp, ref, decoded_allocs = CommissionAccountingService._decode_payout_extra2(encoded)
    assert v_no == "VCH-CPAY-1001"
    assert idemp == "IDK-9001"
    assert ref == "UTR123456"
    assert decoded_allocs == allocs


def test_payment_status_labels():
    assert payment_status_to_label(Decimal("0.00")) == "UNPAID"
    assert payment_status_to_label(Decimal("1.00")) == "PAID"
    assert payment_status_to_label(Decimal("2.00")) == "PARTIALLY_PAID"
    assert payment_status_to_label(Decimal("3.00")) == "APPROVED"
