"""
Phase 8 Golden Parity Test Suite — 25 Deterministic Synthetic Golden Cases (P8-01 .. P8-25).

Verifies exact 0.00 financial delta across all 25 Phase 8 Payment, Cheque, Bounce, Penalty,
Reversal, Refund, Cut & Pay, Partner E-Wallet (Top-Up, Lock, Release, Debit), and Insurer
Reconciliation scenarios.
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
async def cleanup_phase8_golden_tables(db_session: AsyncSession):
    for tbl in (
        "tbl_account",
        "tbl_transactionpayment",
        "tbl_franchisecommission",
        "tbl_agentcommissionpayment",
        "tbl_cutnpaycommpayable",
        "tbl_transaction",
        "tbl_transactionappnew",
        "tbl_ledgermaster",
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
        "tbl_ledgermaster",
    ):
        await db_session.execute(text(f"DELETE FROM {tbl};"))
    await db_session.commit()


@pytest.mark.asyncio
async def test_phase8_golden_parity_cases_p8_01_to_p8_25(
    async_client: AsyncClient,
    db_session: AsyncSession,
):
    """Executes all 25 deterministic Phase 8 Golden Parity cases (P8-01 .. P8-25) with 0.00 delta."""
    _, admin_headers = await create_user_with_role(db_session, role_name="ADMIN", branch_id=101)
    cust, veh = await create_synthetic_customer_and_vehicle(
        db_session, branch_id=101, reg_no="MH12P8GOLD"
    )

    # ------------------------------------------------------------------------
    # P8-01: Full Cash Payment (14,509.00, Outstanding = 0.00, AccTransId = 1, 2, 3)
    # ------------------------------------------------------------------------
    p01 = await async_client.post(
        "/api/v1/policies/book",
        headers=admin_headers,
        json={
            "customer_id": cust.CustomerId,
            "cust_veh_id": veh.CustVehId,
            "policy_no": "TEST_POLICY_P8_01",
            "vehicle_category": "PVT",
            "od_premium": "8500.00",
            "tp_premium": "3796.00",
            "commission": {"agent_id": 101, "agent_comm_od_percent": "15.00", "tds_percent": "5.00"},
            "payments": [{"payment_type": "CASH", "paid_amount": "14509.00"}],
        },
    )
    assert p01.status_code == 201
    d01 = p01.json()
    assert Decimal(d01["payment_summary"]["paid_amount"]) == Decimal("14509.00")
    assert Decimal(d01["payment_summary"]["outstanding_amount"]) == Decimal("0.00")
    assert d01["payment_summary"]["payments"][0]["status"] == "RECEIVED"
    assert d01["t_status"] == "Booked"

    # ------------------------------------------------------------------------
    # P8-02: Partial Cash Payment (5,000.00 of 11,800.00 -> Outstanding = 6,800.00, Pending)
    # ------------------------------------------------------------------------
    p02 = await async_client.post(
        "/api/v1/policies/book",
        headers=admin_headers,
        json={
            "customer_id": cust.CustomerId,
            "cust_veh_id": veh.CustVehId,
            "policy_no": "TEST_POLICY_P8_02",
            "vehicle_category": "PVT",
            "od_premium": "6000.00",
            "tp_premium": "4000.00",
            "payments": [{"payment_type": "CASH", "paid_amount": "5000.00"}],
        },
    )
    assert p02.status_code == 201
    d02 = p02.json()
    tx02_id = d02["transaction_id"]
    assert Decimal(d02["payment_summary"]["paid_amount"]) == Decimal("5000.00")
    assert Decimal(d02["payment_summary"]["outstanding_amount"]) == Decimal("6800.00")
    assert d02["t_status"] == "Pending"
    assert d02["pending_status"] == 1

    # ------------------------------------------------------------------------
    # P8-03: Subsequent UPI Payment Completing Balance (6,800.00 -> Booked)
    # ------------------------------------------------------------------------
    p03 = await async_client.post(
        f"/api/v1/policies/{tx02_id}/payments",
        headers=admin_headers,
        json={"payment_type": "UPI", "paid_amount": "6800.00", "docno": "UPI-P8-03"},
    )
    assert p03.status_code == 201
    d03 = p03.json()
    assert Decimal(d03["payment_summary"]["paid_amount"]) == Decimal("11800.00")
    assert Decimal(d03["payment_summary"]["outstanding_amount"]) == Decimal("0.00")
    assert d03["t_status"] == "Booked"
    assert d03["pending_status"] == 0

    # ------------------------------------------------------------------------
    # P8-04: Cheque Payment Received (PENDING_CLEARANCE, Ischequeclearing=1, IsChequeCleared=0)
    # ------------------------------------------------------------------------
    p04 = await async_client.post(
        "/api/v1/policies/book",
        headers=admin_headers,
        json={
            "customer_id": cust.CustomerId,
            "cust_veh_id": veh.CustVehId,
            "policy_no": "TEST_POLICY_P8_04",
            "vehicle_category": "PVT",
            "od_premium": "6000.00",
            "tp_premium": "4000.00",
            "payments": [
                {
                    "payment_type": "CHEQUE",
                    "paid_amount": "11800.00",
                    "docno": "CHQ-P8-04",
                    "bankname": "HDFC BANK",
                }
            ],
        },
    )
    assert p04.status_code == 201
    pay04_id = p04.json()["payment_summary"]["payments"][0]["payment_id"]
    assert p04.json()["payment_summary"]["payments"][0]["status"] == "PENDING_CLEARANCE"

    # ------------------------------------------------------------------------
    # P8-05: Cheque Deposited in Bank (DEPOSITED, CashierApproval=1)
    # ------------------------------------------------------------------------
    p05 = await async_client.post(
        f"/api/v1/payments/{pay04_id}/deposit",
        headers=admin_headers,
        json={"bank_reference": "DEP-P8-05"},
    )
    assert p05.status_code == 200
    assert p05.json()["status"] == "DEPOSITED"
    assert p05.json()["payment"]["cashier_approval"] == 1

    # ------------------------------------------------------------------------
    # P8-06: Cheque Cleared in Bank (CLEARED, IsChequeCleared=1, ChequeBankStatus=1)
    # ------------------------------------------------------------------------
    p06 = await async_client.post(
        f"/api/v1/payments/{pay04_id}/clear",
        headers=admin_headers,
        json={"bank_reference": "CLR-P8-06"},
    )
    assert p06.status_code == 200
    assert p06.json()["status"] == "CLEARED"
    assert p06.json()["is_cheque_clearing"] == 0
    assert p06.json()["is_cheque_cleared"] == 1
    assert p06.json()["cheque_bank_status"] == 1

    # ------------------------------------------------------------------------
    # P8-07: Cheque Bounced without Penalty (11,800.00 bounced -> Outstanding = 11,800.00)
    # ------------------------------------------------------------------------
    p07_book = await async_client.post(
        "/api/v1/policies/book",
        headers=admin_headers,
        json={
            "customer_id": cust.CustomerId,
            "cust_veh_id": veh.CustVehId,
            "policy_no": "TEST_POLICY_P8_07",
            "vehicle_category": "PVT",
            "od_premium": "6000.00",
            "tp_premium": "4000.00",
            "payments": [
                {
                    "payment_type": "CHEQUE",
                    "paid_amount": "11800.00",
                    "docno": "CHQ-P8-07",
                    "bankname": "ICICI BANK",
                }
            ],
        },
    )
    pay07_id = p07_book.json()["payment_summary"]["payments"][0]["payment_id"]
    p07 = await async_client.post(
        f"/api/v1/payments/{pay07_id}/bounce",
        headers=admin_headers,
        json={"bounce_reason": "Signature Mismatch", "penalty_amount": "0.00"},
    )
    assert p07.status_code == 200
    assert p07.json()["status"] == "BOUNCED"
    assert Decimal(p07.json()["policy_paid_amount"]) == Decimal("0.00")
    assert Decimal(p07.json()["policy_outstanding_amount"]) == Decimal("11800.00")
    assert p07.json()["policy_t_status"] == "Pending"

    # ------------------------------------------------------------------------
    # P8-08: Cheque Bounced with Dishonor Penalty (10,000.00 + 500.00 penalty -> Out = 10,500.00)
    # ------------------------------------------------------------------------
    p08_book = await async_client.post(
        "/api/v1/policies/book",
        headers=admin_headers,
        json={
            "customer_id": cust.CustomerId,
            "cust_veh_id": veh.CustVehId,
            "policy_no": "TEST_POLICY_P8_08",
            "vehicle_category": "PVT",
            "od_premium": "6000.00",
            "tp_premium": "4000.00",
            "payments": [
                {"payment_type": "CASH", "paid_amount": "1800.00"},
                {
                    "payment_type": "CHEQUE",
                    "paid_amount": "10000.00",
                    "docno": "CHQ-P8-08",
                    "bankname": "SBI",
                },
            ],
        },
    )
    tx08_id = p08_book.json()["transaction_id"]
    chq08_id = p08_book.json()["payment_summary"]["payments"][1]["payment_id"]
    p08 = await async_client.post(
        f"/api/v1/payments/{chq08_id}/bounce",
        headers=admin_headers,
        json={"bounce_reason": "Insufficient Funds", "penalty_amount": "500.00"},
    )
    assert p08.status_code == 200
    assert Decimal(p08.json()["policy_paid_amount"]) == Decimal("1800.00")
    assert Decimal(p08.json()["policy_outstanding_amount"]) == Decimal("10500.00")
    assert Decimal(p08.json()["penalty_applied"]) == Decimal("500.00")

    # ------------------------------------------------------------------------
    # P8-09: Replacement NEFT Settlement after Cheque Bounce + Penalty (10,500.00 -> Booked)
    # ------------------------------------------------------------------------
    p09 = await async_client.post(
        f"/api/v1/policies/{tx08_id}/payments",
        headers=admin_headers,
        json={"payment_type": "NEFT", "paid_amount": "10500.00", "docno": "NEFT-P8-09"},
    )
    assert p09.status_code == 201
    assert Decimal(p09.json()["payment_summary"]["paid_amount"]) == Decimal("12300.00")
    assert Decimal(p09.json()["payment_summary"]["outstanding_amount"]) == Decimal("0.00")
    assert p09.json()["t_status"] == "Booked"

    # ------------------------------------------------------------------------
    # P8-10: Demand Draft (DD) Payment Receipt & Bank Clearance
    # ------------------------------------------------------------------------
    p10_book = await async_client.post(
        "/api/v1/policies/book",
        headers=admin_headers,
        json={
            "customer_id": cust.CustomerId,
            "cust_veh_id": veh.CustVehId,
            "policy_no": "TEST_POLICY_P8_10",
            "vehicle_category": "PVT",
            "od_premium": "6000.00",
            "tp_premium": "4000.00",
            "payments": [
                {
                    "payment_type": "DD",
                    "paid_amount": "11800.00",
                    "docno": "DD-P8-10",
                    "bankname": "BANK OF BARODA",
                }
            ],
        },
    )
    assert p10_book.status_code == 201
    dd10_id = p10_book.json()["payment_summary"]["payments"][0]["payment_id"]
    assert p10_book.json()["payment_summary"]["payments"][0]["status"] == "PENDING_CLEARANCE"
    p10_clr = await async_client.post(
        f"/api/v1/payments/{dd10_id}/clear",
        headers=admin_headers,
        json={"bank_reference": "DD-CLR-10"},
    )
    assert p10_clr.status_code == 200
    assert p10_clr.json()["status"] == "CLEARED"

    # ------------------------------------------------------------------------
    # P8-11: Credit Card + Debit Card Split Payment (6,000.00 + 5,800.00 = 11,800.00)
    # ------------------------------------------------------------------------
    p11 = await async_client.post(
        "/api/v1/policies/book",
        headers=admin_headers,
        json={
            "customer_id": cust.CustomerId,
            "cust_veh_id": veh.CustVehId,
            "policy_no": "TEST_POLICY_P8_11",
            "vehicle_category": "PVT",
            "od_premium": "6000.00",
            "tp_premium": "4000.00",
            "payments": [
                {"payment_type": "CREDIT_CARD", "paid_amount": "6000.00", "docno": "CC-P8-11"},
                {"payment_type": "DEBIT_CARD", "paid_amount": "5800.00", "docno": "DC-P8-11"},
            ],
        },
    )
    assert p11.status_code == 201
    assert Decimal(p11.json()["payment_summary"]["paid_amount"]) == Decimal("11800.00")
    assert Decimal(p11.json()["payment_summary"]["outstanding_amount"]) == Decimal("0.00")

    # ------------------------------------------------------------------------
    # P8-12: RTGS Corporate GCV Payment (Split GST 12% Basic TP + 18% OD/Other TP)
    # ------------------------------------------------------------------------
    p12 = await async_client.post(
        "/api/v1/policies/book",
        headers=admin_headers,
        json={
            "customer_id": cust.CustomerId,
            "cust_veh_id": veh.CustVehId,
            "policy_no": "TEST_POLICY_P8_12",
            "vehicle_category": "Public_GCV",
            "gcv_split_tp_gst": True,
            "od_premium": "20000.00",
            "tp_premium": "25500.00",
            "basic_tp_premium": "25000.00",
            "pa_owner_driver": "375.00",
            "ll_paid_driver": "125.00",
            "payments": [{"payment_type": "RTGS", "paid_amount": "52190.00", "docno": "RTGS-P8-12"}],
        },
    )
    assert p12.status_code == 201
    assert Decimal(p12.json()["payment_summary"]["paid_amount"]) == Decimal("52190.00")
    assert Decimal(p12.json()["payment_summary"]["outstanding_amount"]) == Decimal("0.00")

    # ------------------------------------------------------------------------
    # P8-13: Cut & Pay Full NetCommission Deduction (CutNPay = 950.00, Online = 16,750.00)
    # ------------------------------------------------------------------------
    p13 = await async_client.post(
        "/api/v1/policies/book",
        headers=admin_headers,
        json={
            "customer_id": cust.CustomerId,
            "cust_veh_id": veh.CustVehId,
            "policy_no": "TEST_POLICY_P8_13",
            "vehicle_category": "PVT",
            "od_premium": "10000.00",
            "tp_premium": "5000.00",
            "cutnpay_enabled": True,
            "commission": {"agent_id": 113, "agent_comm_od_percent": "10.00", "tds_percent": "5.00"},
            "payments": [{"payment_type": "ONLINE", "paid_amount": "16750.00"}],
        },
    )
    assert p13.status_code == 201
    assert Decimal(p13.json()["payment_summary"]["cutnpay_deduction"]) == Decimal("950.00")
    assert Decimal(p13.json()["payment_summary"]["required_payable_amount"]) == Decimal("16750.00")
    assert Decimal(p13.json()["payment_summary"]["outstanding_amount"]) == Decimal("0.00")

    # ------------------------------------------------------------------------
    # P8-14: Cut & Pay Partial Custom Deduction (500.00 of 950.00 NetComm)
    # ------------------------------------------------------------------------
    p14 = await async_client.post(
        "/api/v1/policies/book",
        headers=admin_headers,
        json={
            "customer_id": cust.CustomerId,
            "cust_veh_id": veh.CustVehId,
            "policy_no": "TEST_POLICY_P8_14",
            "vehicle_category": "PVT",
            "od_premium": "10000.00",
            "tp_premium": "5000.00",
            "cutnpay_enabled": True,
            "cutnpay_amount": "500.00",
            "commission": {"agent_id": 114, "agent_comm_od_percent": "10.00", "tds_percent": "5.00"},
            "payments": [{"payment_type": "CASH", "paid_amount": "17200.00"}],
        },
    )
    assert p14.status_code == 201
    assert Decimal(p14.json()["payment_summary"]["cutnpay_deduction"]) == Decimal("500.00")
    assert Decimal(p14.json()["payment_summary"]["required_payable_amount"]) == Decimal("17200.00")
    assert Decimal(p14.json()["payment_summary"]["outstanding_amount"]) == Decimal("0.00")

    # ------------------------------------------------------------------------
    # P8-15: Partner Agent E-Wallet Top-Up (+25,000.00 -> AccTransId = 10)
    # ------------------------------------------------------------------------
    p15 = await async_client.post(
        "/api/v1/wallets/topup",
        headers=admin_headers,
        json={"owner_type": "AGENT", "owner_id": 515, "amount": "25000.00", "payment_mode": "NEFT"},
    )
    assert p15.status_code == 201
    assert Decimal(p15.json()["wallet"]["settled_balance"]) == Decimal("25000.00")
    assert Decimal(p15.json()["wallet"]["available_balance"]) == Decimal("25000.00")
    assert p15.json()["ledger_entry"]["acc_trans_id"] == 10

    # ------------------------------------------------------------------------
    # P8-16: Partner Agent E-Wallet Lock Reservation (-11,800.00 -> AccTransId = 11)
    # ------------------------------------------------------------------------
    p16 = await async_client.post(
        "/api/v1/wallets/lock",
        headers=admin_headers,
        json={"owner_type": "AGENT", "owner_id": 515, "amount": "11800.00"},
    )
    assert p16.status_code == 201
    lock16_id = p16.json()["ledger_entry"]["account_id"]
    assert Decimal(p16.json()["wallet"]["locked_balance"]) == Decimal("11800.00")
    assert Decimal(p16.json()["wallet"]["available_balance"]) == Decimal("13200.00")
    assert p16.json()["ledger_entry"]["acc_trans_id"] == 11

    # ------------------------------------------------------------------------
    # P8-17: Partner Agent E-Wallet Lock Release (+11,800.00 -> AccTransId = 12)
    # ------------------------------------------------------------------------
    p17 = await async_client.post(
        "/api/v1/wallets/release",
        headers=admin_headers,
        json={"lock_account_id": lock16_id, "reason": "Golden Case P8-17 Release"},
    )
    assert p17.status_code == 200
    assert Decimal(p17.json()["wallet"]["locked_balance"]) == Decimal("0.00")
    assert Decimal(p17.json()["wallet"]["available_balance"]) == Decimal("25000.00")
    assert p17.json()["ledger_entry"]["acc_trans_id"] == 12

    # ------------------------------------------------------------------------
    # P8-18: Partner Agent E-Wallet Lock Consumed on Policy Booking (AccTransId = 13)
    # ------------------------------------------------------------------------
    lock18 = await async_client.post(
        "/api/v1/wallets/lock",
        headers=admin_headers,
        json={"owner_type": "AGENT", "owner_id": 515, "amount": "11800.00"},
    )
    lock18_id = lock18.json()["ledger_entry"]["account_id"]
    p18 = await async_client.post(
        "/api/v1/policies/book",
        headers=admin_headers,
        json={
            "customer_id": cust.CustomerId,
            "cust_veh_id": veh.CustVehId,
            "policy_no": "TEST_POLICY_P8_18",
            "vehicle_category": "PVT",
            "od_premium": "6000.00",
            "tp_premium": "4000.00",
            "ewallet_amount_used": "11800.00",
            "wallet_owner_type": "AGENT",
            "wallet_owner_id": 515,
            "wallet_lock_id": lock18_id,
            "commission": {"agent_id": 515},
        },
    )
    assert p18.status_code == 201
    w18 = await async_client.get("/api/v1/wallets/AGENT/515", headers=admin_headers)
    assert Decimal(w18.json()["settled_balance"]) == Decimal("13200.00")
    assert Decimal(w18.json()["locked_balance"]) == Decimal("0.00")
    assert Decimal(w18.json()["available_balance"]) == Decimal("13200.00")

    # ------------------------------------------------------------------------
    # P8-19: Partner Franchise E-Wallet Top-Up + Split Payment (EWALLET 4000 + CASH 7800)
    # ------------------------------------------------------------------------
    await async_client.post(
        "/api/v1/wallets/topup",
        headers=admin_headers,
        json={"owner_type": "FRANCHISE", "owner_id": 319, "amount": "10000.00", "payment_mode": "UPI"},
    )
    p19 = await async_client.post(
        "/api/v1/policies/book",
        headers=admin_headers,
        json={
            "customer_id": cust.CustomerId,
            "cust_veh_id": veh.CustVehId,
            "policy_no": "TEST_POLICY_P8_19",
            "vehicle_category": "PVT",
            "od_premium": "6000.00",
            "tp_premium": "4000.00",
            "commission": {"franchise_id": 319, "agent_comm_od_percent": "10.00"},
            "payments": [
                {
                    "payment_type": "EWALLET",
                    "paid_amount": "4000.00",
                    "wallet_owner_type": "FRANCHISE",
                    "wallet_owner_id": 319,
                },
                {"payment_type": "CASH", "paid_amount": "7800.00"},
            ],
        },
    )
    assert p19.status_code == 201
    tx19_id = p19.json()["transaction_id"]
    ew19_pay_id = p19.json()["payment_summary"]["payments"][0]["payment_id"]
    w19 = await async_client.get("/api/v1/wallets/FRANCHISE/319", headers=admin_headers)
    assert Decimal(w19.json()["available_balance"]) == Decimal("6000.00")

    # ------------------------------------------------------------------------
    # P8-20: Direct to Insurer Online Remittance (5,000.00) + Agent Cash (6,800.00)
    # ------------------------------------------------------------------------
    p20 = await async_client.post(
        "/api/v1/policies/book",
        headers=admin_headers,
        json={
            "customer_id": cust.CustomerId,
            "cust_veh_id": veh.CustVehId,
            "policy_no": "TEST_POLICY_P8_20",
            "vehicle_category": "PVT",
            "od_premium": "6000.00",
            "tp_premium": "4000.00",
            "online_payment_to_company": "5000.00",
            "payments": [{"payment_type": "CASH", "paid_amount": "6800.00"}],
        },
    )
    assert p20.status_code == 201
    tx20_id = p20.json()["transaction_id"]
    cash20_id = p20.json()["payment_summary"]["payments"][0]["payment_id"]
    assert Decimal(p20.json()["payment_summary"]["paid_amount"]) == Decimal("11800.00")
    assert Decimal(p20.json()["payment_summary"]["outstanding_amount"]) == Decimal("0.00")

    # ------------------------------------------------------------------------
    # P8-21: Active Cash Payment Reversal (-6,800.00 -> Outstanding = 6,800.00)
    # ------------------------------------------------------------------------
    p21 = await async_client.post(
        f"/api/v1/payments/{cash20_id}/reverse",
        headers=admin_headers,
        json={"reason": "Golden Case P8-21 Cash Reversal"},
    )
    assert p21.status_code == 200
    assert p21.json()["status"] == "REVERSED"
    assert Decimal(p21.json()["policy_paid_amount"]) == Decimal("5000.00")
    assert Decimal(p21.json()["policy_outstanding_amount"]) == Decimal("6800.00")

    # ------------------------------------------------------------------------
    # P8-22: E-Wallet Payment Reversal with Automatic Franchise Wallet Refund (+4,000.00)
    # ------------------------------------------------------------------------
    p22 = await async_client.post(
        f"/api/v1/payments/{ew19_pay_id}/reverse",
        headers=admin_headers,
        json={
            "reason": "Golden Case P8-22 Wallet Refund",
            "refund_to_wallet": True,
            "wallet_owner_type": "FRANCHISE",
            "wallet_owner_id": 319,
        },
    )
    assert p22.status_code == 200
    assert Decimal(p22.json()["policy_outstanding_amount"]) == Decimal("4000.00")
    w22 = await async_client.get("/api/v1/wallets/FRANCHISE/319", headers=admin_headers)
    assert Decimal(w22.json()["available_balance"]) == Decimal("10000.00")

    # ------------------------------------------------------------------------
    # P8-23: Insurer Payment & Brokerage Reconciliation — Full Match (IsRconDataMatch = 1)
    # ------------------------------------------------------------------------
    tx01_id = d01["transaction_id"]
    # P8-01 had OD = 8500, 15% OD comm -> booked_gross_comm = 1275.00
    p23 = await async_client.post(
        f"/api/v1/reconciliation/policies/{tx01_id}/match",
        headers=admin_headers,
        json={
            "reconciled_comm_amount": "1275.00",
            "company_submission_doc_no": "RCON-P8-23",
            "ib_doc_no": 8023,
            "ib_receipt_status": 1,
        },
    )
    assert p23.status_code == 200
    assert p23.json()["is_rcon_data_match"] == 1
    assert p23.json()["match_status"] == "MATCHED"
    assert Decimal(p23.json()["commission_variance"]) == Decimal("0.00")
    assert p23.json()["accounting_entry"]["acc_trans_id"] == 5

    # ------------------------------------------------------------------------
    # P8-24: Insurer Payment & Brokerage Reconciliation — Partial/Variance Match (IsRconDataMatch = 2)
    # ------------------------------------------------------------------------
    tx13_id = p13.json()["transaction_id"]
    # P8-13 had OD = 10000, 10% OD comm -> booked_gross_comm = 1000.00; insurer statement = 750.00
    p24 = await async_client.post(
        f"/api/v1/reconciliation/policies/{tx13_id}/match",
        headers=admin_headers,
        json={
            "reconciled_comm_amount": "750.00",
            "company_submission_doc_no": "RCON-P8-24",
            "ib_doc_no": 8024,
            "allow_partial_match": True,
        },
    )
    assert p24.status_code == 200
    assert p24.json()["is_rcon_data_match"] == 2
    assert p24.json()["match_status"] == "PARTIAL_VARIANCE"
    assert Decimal(p24.json()["commission_variance"]) == Decimal("-250.00")

    # ------------------------------------------------------------------------
    # P8-25: Multi-Instrument Policy Cancellation & Full Accounting Reversal
    # ------------------------------------------------------------------------
    tx11_id = p11.json()["transaction_id"]
    p25 = await async_client.post(
        f"/api/v1/policies/{tx11_id}/cancel",
        headers=admin_headers,
        json={"reason": "Golden Case P8-25 Cancellation"},
    )
    assert p25.status_code == 200
    assert p25.json()["t_status"] == "Cancelled"
    assert p25.json()["payments_reversed"] == 2
    assert p25.json()["accounting_entries_reversed"] == 3
