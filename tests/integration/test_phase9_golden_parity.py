"""
Phase 9 Golden Parity Test Suite — 30 Verified Scenarios (C9-01 through C9-30).

Verifies 100% financial and behavioral parity (`0.00` discrepancy) between the legacy
ASP.NET / MySQL commission & accounting engine and the new FastAPI implementation across:
- Agent OD, Net, Extra & Combined Commissions (C9-01 .. C9-04)
- Agent 5% & 0% TDS Deductions (C9-05 .. C9-06)
- Franchise OD, Combined, TDS & Overriding Profit Spread (C9-07 .. C9-10)
- Cut & Pay Full, Partial & Over-Deduction Guard (C9-11 .. C9-13)
- Policy Booking Commission Accrual & Approval Gate (C9-14 .. C9-15)
- Agent & Franchise Full/Partial Payouts, Over-Payout & Duplicate Guards (C9-16 .. C9-21)
- Policy Cancellation Reversal, Cheque Bounce Hold & Payout Reversal (C9-22 .. C9-24)
- Double-Entry Accounting Entries, Vouchers & Trial Balance Zero-Variance (C9-25 .. C9-30)
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
async def cleanup_golden_p9_tables(db_session: AsyncSession):
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


# ===========================================================================
# C9-01 through C9-13: Stateless & Preview Parity Matrix
# ===========================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "case_id,payload,expected",
    [
        (
            "C9-01",
            {
                "od_premium": "10000.00",
                "tp_premium": "5000.00",
                "agent_comm_od_pct": "15.00",
                "agent_tds_pct": "5.00",
            },
            {
                "agent_gross_commission": "1500.00",
                "agent_tds_amount": "75.00",
                "agent_net_commission": "1425.00",
                "agent_remaining_payable_amount": "1425.00",
            },
        ),
        (
            "C9-02",
            {
                "od_premium": "10000.00",
                "tp_premium": "5000.00",
                "agent_comm_net_pct": "10.00",
                "agent_tds_pct": "5.00",
            },
            {
                "agent_gross_commission": "1500.00",
                "agent_tds_amount": "75.00",
                "agent_net_commission": "1425.00",
                "agent_remaining_payable_amount": "1425.00",
            },
        ),
        (
            "C9-03",
            {
                "od_premium": "10000.00",
                "tp_premium": "5000.00",
                "agent_comm_extra_pct": "3.00",
                "agent_tds_pct": "5.00",
            },
            {
                "agent_gross_commission": "300.00",
                "agent_tds_amount": "15.00",
                "agent_net_commission": "285.00",
                "agent_remaining_payable_amount": "285.00",
            },
        ),
        (
            "C9-04",
            {
                "od_premium": "10000.00",
                "tp_premium": "5000.00",
                "agent_comm_od_pct": "12.00",
                "agent_comm_net_pct": "2.00",
                "agent_comm_extra_pct": "1.00",
                "agent_tds_pct": "5.00",
            },
            {
                # OD: 1200 (TDS 60, Net 1140) + Net: 300 (TDS 15, Net 285) + Extra: 100 (TDS 5, Net 95)
                "agent_gross_commission": "1600.00",
                "agent_tds_amount": "80.00",
                "agent_net_commission": "1520.00",
                "agent_remaining_payable_amount": "1520.00",
            },
        ),
        (
            "C9-05",
            {
                "od_premium": "20000.00",
                "tp_premium": "0.00",
                "agent_comm_od_pct": "10.00",
                "agent_tds_pct": "5.00",
            },
            {
                "agent_gross_commission": "2000.00",
                "agent_tds_amount": "100.00",
                "agent_net_commission": "1900.00",
            },
        ),
        (
            "C9-06",
            {
                "od_premium": "20000.00",
                "tp_premium": "0.00",
                "agent_comm_od_pct": "10.00",
                "agent_tds_pct": "0.00",
            },
            {
                "agent_gross_commission": "2000.00",
                "agent_tds_amount": "0.00",
                "agent_net_commission": "2000.00",
            },
        ),
        (
            "C9-07",
            {
                "od_premium": "10000.00",
                "tp_premium": "5000.00",
                "franchise_comm_od_pct": "18.00",
                "franchise_tds_pct": "5.00",
            },
            {
                "franchise_gross_commission": "1800.00",
                "franchise_tds_amount": "90.00",
                "franchise_net_commission": "1710.00",
            },
        ),
        (
            "C9-08",
            {
                "od_premium": "10000.00",
                "tp_premium": "5000.00",
                "franchise_comm_od_pct": "15.00",
                "franchise_comm_net_pct": "3.00",
                "franchise_comm_extra_pct": "2.00",
                "franchise_tds_pct": "5.00",
            },
            {
                # OD: 1500 + Net: 450 + Extra: 200 = 2150 gross; TDS 5% = 107.50; Net = 2042.50
                "franchise_gross_commission": "2150.00",
                "franchise_tds_amount": "107.50",
                "franchise_net_commission": "2042.50",
            },
        ),
        (
            "C9-09",
            {
                "od_premium": "20000.00",
                "tp_premium": "0.00",
                "franchise_comm_od_pct": "15.00",
                "franchise_tds_pct": "10.00",
            },
            {
                "franchise_gross_commission": "3000.00",
                "franchise_tds_amount": "300.00",
                "franchise_net_commission": "2700.00",
            },
        ),
        (
            "C9-10",
            {
                "od_premium": "10000.00",
                "tp_premium": "5000.00",
                "agent_comm_od_pct": "10.00",
                "agent_tds_pct": "5.00",
                "franchise_comm_od_pct": "18.00",
                "franchise_comm_net_pct": "2.00",
                "franchise_tds_pct": "5.00",
            },
            {
                # Franchise Net: 1995.00 - Agent Net: 950.00 = 1045.00
                "agent_net_commission": "950.00",
                "franchise_net_commission": "1995.00",
                "profit_of_net_commission": "1045.00",
            },
        ),
        (
            "C9-11",
            {
                "od_premium": "10000.00",
                "tp_premium": "0.00",
                "final_premium": "11800.00",
                "agent_comm_od_pct": "10.00",
                "agent_tds_pct": "5.00",
                "cutnpay_enabled": True,
            },
            {
                "agent_net_commission": "950.00",
                "cutnpay_deducted_amount": "950.00",
                "customer_required_payable_amount": "10850.00",
                "agent_initial_paid_adv_amt": "950.00",
                "agent_remaining_payable_amount": "0.00",
                "agent_initial_payment_status": "1.00",
            },
        ),
        (
            "C9-12",
            {
                "od_premium": "10000.00",
                "tp_premium": "0.00",
                "final_premium": "11800.00",
                "agent_comm_od_pct": "10.00",
                "agent_tds_pct": "5.00",
                "cutnpay_enabled": True,
                "cutnpay_amount": "400.00",
            },
            {
                "agent_net_commission": "950.00",
                "cutnpay_deducted_amount": "400.00",
                "customer_required_payable_amount": "11400.00",
                "agent_initial_paid_adv_amt": "400.00",
                "agent_remaining_payable_amount": "550.00",
                "agent_initial_payment_status": "2.00",
            },
        ),
    ],
)
async def test_golden_parity_c9_01_to_c9_12(
    async_client: AsyncClient,
    db_session: AsyncSession,
    case_id: str,
    payload: dict,
    expected: dict,
):
    _, headers = await create_user_with_role(db_session, role_name="OPERATOR", branch_id=101)
    resp = await async_client.post("/api/v1/commissions/preview", headers=headers, json=payload)
    assert resp.status_code == 200, f"{case_id} failed: {resp.text}"
    body = resp.json()
    for k, exp_val in expected.items():
        actual_dec = Decimal(str(body[k]))
        exp_dec = Decimal(str(exp_val))
        assert actual_dec - exp_dec == Decimal("0.00"), (
            f"{case_id} discrepancy on {k}: expected {exp_dec}, got {actual_dec}"
        )


@pytest.mark.asyncio
async def test_golden_parity_c9_13_cutnpay_exceeding_commission_rejected(
    async_client: AsyncClient,
    db_session: AsyncSession,
):
    _, headers = await create_user_with_role(db_session, role_name="OPERATOR", branch_id=101)
    resp = await async_client.post(
        "/api/v1/commissions/preview",
        headers=headers,
        json={
            "od_premium": "10000.00",
            "tp_premium": "0.00",
            "agent_comm_od_pct": "10.00",
            "agent_tds_pct": "5.00",
            "cutnpay_enabled": True,
            "cutnpay_amount": "951.00",
        },
    )
    assert resp.status_code == 422


# ===========================================================================
# C9-14 through C9-30: Full Transactional, Payout, Reversal & Trial Balance Parity
# ===========================================================================


@pytest.mark.asyncio
async def test_golden_parity_c9_14_to_c9_30_transactional_and_accounting_matrix(
    async_client: AsyncClient,
    db_session: AsyncSession,
):
    _, op_headers = await create_user_with_role(db_session, role_name="OPERATOR", branch_id=101)
    _, acc_headers = await create_user_with_role(db_session, role_name="ACCOUNT", branch_id=101)
    cust, veh = await create_synthetic_customer_and_vehicle(db_session, branch_id=101)

    # -----------------------------------------------------------------------
    # C9-14 & C9-25: Commission payable creation & accounting entries on policy booking
    # -----------------------------------------------------------------------
    b1 = await async_client.post(
        "/api/v1/policies/book",
        headers=op_headers,
        json={
            "customer_id": cust.CustomerId,
            "cust_veh_id": veh.CustVehId,
            "policy_no": "GOLDEN_C9_14_POL",
            "vehicle_category": "PVT",
            "od_premium": "10000.00",
            "tp_premium": "5000.00",
            "commission": {
                "agent_id": 601,
                "agent_comm_od_percent": "10.00",
                "tds_percent": "5.00",
                "franchise_id": 701,
                "franchise_comm_od_percent": "15.00",
            },
            "payments": [{"payment_type": "CASH", "paid_amount": "17700.00"}],
        },
    )
    assert b1.status_code == 201
    b1_data = b1.json()
    tx1_id = b1_data["transaction_id"]

    # Verify C9-25: AccTransId = 1 (+17700), AccTransId = 2 (+17700), AccTransId = 3 (-950)
    accts_b1 = {e["acc_trans_id"]: Decimal(e["amount"]) for e in b1_data["accounting_entries"]}
    assert accts_b1[1] == Decimal("17700.00")
    assert accts_b1[2] == Decimal("17700.00")
    assert accts_b1[3] == Decimal("-950.00")

    # Verify C9-14: Commission payable row state
    c14 = (await async_client.get(f"/api/v1/commissions/{tx1_id}", headers=acc_headers)).json()
    assert Decimal(c14["agent_remaining_payable"]) == Decimal("950.00")
    assert Decimal(c14["franchise_remaining_payable"]) == Decimal("1425.00")
    assert Decimal(c14["profit_of_net_commission"]) == Decimal("475.00")

    # -----------------------------------------------------------------------
    # C9-15: Commission approval (PaymentStatus = 3.00)
    # -----------------------------------------------------------------------
    c15 = await async_client.post(
        f"/api/v1/commissions/{tx1_id}/approve",
        headers=acc_headers,
        json={"partner_type": "BOTH", "remark": "C9-15 Approval"},
    )
    assert c15.status_code == 200
    assert Decimal(c15.json()["agent_commission_row"]["payment_status"]) == Decimal("3.00")

    # -----------------------------------------------------------------------
    # C9-17: Partial Agent commission payout (400.00 of 950.00 -> 550.00 remaining, status 2.00)
    # -----------------------------------------------------------------------
    c17 = await async_client.post(
        "/api/v1/commission-payouts",
        headers=acc_headers,
        json={
            "partner_type": "AGENT",
            "partner_id": 601,
            "payout_amount": "400.00",
            "transaction_ids": [tx1_id],
            "idempotency_key": "IDEMP-C9-17",
        },
    )
    assert c17.status_code == 201
    c17_data = c17.json()
    assert Decimal(c17_data["total_payout_amount"]) == Decimal("400.00")
    assert Decimal(c17_data["allocations"][0]["remaining_payable_amount"]) == Decimal("550.00")
    assert Decimal(c17_data["allocations"][0]["payment_status"]) == Decimal("2.00")

    # -----------------------------------------------------------------------
    # C9-21: Duplicate payout rejected (409 Conflict)
    # -----------------------------------------------------------------------
    c21 = await async_client.post(
        "/api/v1/commission-payouts",
        headers=acc_headers,
        json={
            "partner_type": "AGENT",
            "partner_id": 601,
            "payout_amount": "400.00",
            "transaction_ids": [tx1_id],
            "idempotency_key": "IDEMP-C9-17",
        },
    )
    assert c21.status_code == 409

    # -----------------------------------------------------------------------
    # C9-20: Over-payout rejected (requesting 600.00 when only 550.00 remains -> 409 Conflict)
    # -----------------------------------------------------------------------
    c20 = await async_client.post(
        "/api/v1/commission-payouts",
        headers=acc_headers,
        json={
            "partner_type": "AGENT",
            "partner_id": 601,
            "payout_amount": "600.00",
            "transaction_ids": [tx1_id],
        },
    )
    assert c20.status_code == 409

    # -----------------------------------------------------------------------
    # C9-16 & C9-26: Full Agent commission payout (remaining 550.00 -> 0.00, status 1.00, AccTransId=6)
    # -----------------------------------------------------------------------
    c16 = await async_client.post(
        "/api/v1/commission-payouts",
        headers=acc_headers,
        json={
            "partner_type": "AGENT",
            "partner_id": 601,
            "payout_amount": "550.00",
            "transaction_ids": [tx1_id],
        },
    )
    assert c16.status_code == 201
    c16_data = c16.json()
    assert Decimal(c16_data["allocations"][0]["remaining_payable_amount"]) == Decimal("0.00")
    assert Decimal(c16_data["allocations"][0]["payment_status"]) == Decimal("1.00")

    # Verify C9-26: Double-entry payout voucher (AccTransId = 6, DR +550.00, CR -550.00)
    vch_c26 = (
        await async_client.get(
            f"/api/v1/accounting/vouchers/{c16_data['payout_id']}", headers=acc_headers
        )
    ).json()
    assert vch_c26["is_balanced"] is True
    assert Decimal(vch_c26["total_debit"]) == Decimal("550.00")
    assert Decimal(vch_c26["total_credit"]) == Decimal("550.00")

    # -----------------------------------------------------------------------
    # C9-19 & C9-18: Partial Franchise payout (600.00) + Full Franchise payout (825.00)
    # -----------------------------------------------------------------------
    c19 = await async_client.post(
        "/api/v1/commission-payouts",
        headers=acc_headers,
        json={
            "partner_type": "FRANCHISE",
            "partner_id": 701,
            "payout_amount": "600.00",
            "transaction_ids": [tx1_id],
        },
    )
    assert c19.status_code == 201
    assert Decimal(c19.json()["allocations"][0]["remaining_payable_amount"]) == Decimal("825.00")
    assert c19.json()["allocations"][0]["commission_paid_flag"] == 0

    c18 = await async_client.post(
        "/api/v1/commission-payouts",
        headers=acc_headers,
        json={
            "partner_type": "FRANCHISE",
            "partner_id": 701,
            "payout_amount": "825.00",
            "transaction_ids": [tx1_id],
        },
    )
    assert c18.status_code == 201
    assert Decimal(c18.json()["allocations"][0]["remaining_payable_amount"]) == Decimal("0.00")
    assert c18.json()["allocations"][0]["commission_paid_flag"] == 1

    # -----------------------------------------------------------------------
    # C9-24 & C9-27: Commission payout reversal & AccTransId = 7 contra entries
    # -----------------------------------------------------------------------
    c24 = await async_client.post(
        f"/api/v1/commission-payouts/{c16_data['payout_id']}/reverse",
        headers=acc_headers,
        json={"reason": "C9-24 Reversal Verification"},
    )
    assert c24.status_code == 200
    c24_data = c24.json()
    assert c24_data["status"] == "REVERSED"
    rev_doc_no = c24_data["reversal_doc_no"]
    assert rev_doc_no is not None

    # Verify C9-27: Contra voucher (AccTransId = 7, DR +550.00, CR -550.00)
    vch_c27 = (
        await async_client.get(f"/api/v1/accounting/vouchers/{rev_doc_no}", headers=acc_headers)
    ).json()
    assert vch_c27["is_balanced"] is True
    assert Decimal(vch_c27["total_debit"]) == Decimal("550.00")
    assert Decimal(vch_c27["total_credit"]) == Decimal("550.00")
    assert all(l["acc_trans_id"] == 7 for l in vch_c27["lines"])

    # -----------------------------------------------------------------------
    # C9-22: Commission reversal on policy cancellation
    # -----------------------------------------------------------------------
    b2 = await async_client.post(
        "/api/v1/policies/book",
        headers=op_headers,
        json={
            "customer_id": cust.CustomerId,
            "cust_veh_id": veh.CustVehId,
            "policy_no": "GOLDEN_C9_22_CANCEL_POL",
            "vehicle_category": "PVT",
            "od_premium": "10000.00",
            "tp_premium": "0.00",
            "commission": {"agent_id": 602, "agent_comm_od_percent": "10.00", "tds_percent": "5.00"},
            "payments": [{"payment_type": "CASH", "paid_amount": "11800.00"}],
        },
    )
    assert b2.status_code == 201
    tx2_id = b2.json()["transaction_id"]

    cancel_resp = await async_client.post(
        f"/api/v1/policies/{tx2_id}/cancel",
        headers=acc_headers,
        json={"reason": "Customer requested cancellation"},
    )
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["agent_comm_payments_reversed"] == 1
    assert cancel_resp.json()["accounting_entries_reversed"] == 3
    # Refresh test session snapshot and verify AccTransId=3 (-950.00) and commission row are reversed (isdeleted=1)
    await db_session.commit()
    res_accts = await db_session.execute(
        text(
            "SELECT amount, isdeleted FROM tbl_account WHERE TransactionId = :tx_id AND AccTransId = 3"
        ),
        {"tx_id": tx2_id},
    )
    row_acc = res_accts.fetchone()
    assert row_acc is not None
    assert Decimal(str(row_acc[0])).quantize(Decimal("0.01")) == Decimal("-950.00")
    assert int(row_acc[1]) == 1

    # -----------------------------------------------------------------------
    # C9-23: Commission hold on cheque bounce
    # -----------------------------------------------------------------------
    b3 = await async_client.post(
        "/api/v1/policies/book",
        headers=op_headers,
        json={
            "customer_id": cust.CustomerId,
            "cust_veh_id": veh.CustVehId,
            "policy_no": "GOLDEN_C9_23_BOUNCE_POL",
            "vehicle_category": "PVT",
            "od_premium": "10000.00",
            "tp_premium": "0.00",
            "commission": {"agent_id": 603, "agent_comm_od_percent": "10.00", "tds_percent": "5.00"},
            "cutnpay_enabled": True,
            "cutnpay_amount": "300.00",
            "payments": [
                {
                    "payment_type": "CHEQUE",
                    "paid_amount": "11500.00",
                    "docno": "CHQ603001",
                    "bankname": "AXIS BANK",
                }
            ],
        },
    )
    assert b3.status_code == 201
    tx3_id = b3.json()["transaction_id"]
    p3_id = b3.json()["payment_summary"]["payments"][0]["payment_id"]

    bounce_resp = await async_client.post(
        f"/api/v1/payments/{p3_id}/bounce",
        headers=acc_headers,
        json={"bounce_reason": "Funds Insufficient", "penalty_amount": "250.00"},
    )
    assert bounce_resp.status_code == 200
    c23 = (await async_client.get(f"/api/v1/commissions/{tx3_id}", headers=acc_headers)).json()
    assert c23["is_payout_eligible"] is False
    assert c23["cutnpay_row"]["flag"] == "HOLD_CHEQUE_BOUNCE"

    # -----------------------------------------------------------------------
    # C9-28 & C9-29: Balanced voucher creation & Unbalanced voucher rejection
    # -----------------------------------------------------------------------
    l_dr = (
        await async_client.post(
            "/api/v1/accounting/ledgers",
            headers=acc_headers,
            json={"ledger_name": "GOLDEN_LEDGER_DR", "ledger_type_id": 4, "ledger_group_id": 40},
        )
    ).json()["ledger_m_id"]
    l_cr = (
        await async_client.post(
            "/api/v1/accounting/ledgers",
            headers=acc_headers,
            json={"ledger_name": "GOLDEN_LEDGER_CR", "ledger_type_id": 1, "ledger_group_id": 10},
        )
    ).json()["ledger_m_id"]

    c28 = await async_client.post(
        "/api/v1/accounting/vouchers",
        headers=acc_headers,
        json={
            "voucher_type": "JOURNAL",
            "narration": "C9-28 Balanced Journal Voucher",
            "lines": [
                {"ledger_m_id": l_dr, "dr_cr": "DR", "amount": "1250.00"},
                {"ledger_m_id": l_cr, "dr_cr": "CR", "amount": "1250.00"},
            ],
        },
    )
    assert c28.status_code == 201
    assert c28.json()["is_balanced"] is True

    c29 = await async_client.post(
        "/api/v1/accounting/vouchers",
        headers=acc_headers,
        json={
            "voucher_type": "JOURNAL",
            "narration": "C9-29 Unbalanced Voucher",
            "lines": [
                {"ledger_m_id": l_dr, "dr_cr": "DR", "amount": "1250.00"},
                {"ledger_m_id": l_cr, "dr_cr": "CR", "amount": "1200.00"},
            ],
        },
    )
    assert c29.status_code == 422

    # -----------------------------------------------------------------------
    # C9-30: Trial Balance balanced after full lifecycle (variance == 0.00)
    # -----------------------------------------------------------------------
    c30 = await async_client.get("/api/v1/accounting/trial-balance", headers=acc_headers)
    assert c30.status_code == 200
    tb = c30.json()
    assert tb["is_balanced"] is True
    assert Decimal(tb["variance"]) == Decimal("0.00")
    assert Decimal(tb["total_gross_debit"]) == Decimal(tb["total_gross_credit"])
    assert Decimal(tb["total_net_debit"]) == Decimal(tb["total_net_credit"])
