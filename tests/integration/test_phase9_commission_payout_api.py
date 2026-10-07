"""
Phase 9 Integration Tests — Commission Preview, Policy Commission Evaluation, Payable Queue,
Commission Approval, Agent & Franchise Commission Payouts, Payout Reversal, RBAC & Principal
Isolation, Idempotency, and Atomic Rollback Verification.
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
async def cleanup_phase9_tables(db_session: AsyncSession):
    """Ensure clean policy, payment, commission, and ledger tables before and after each test."""
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
# 1. Authentication (401) & RBAC Role Gate Enforcement (403)
# ===========================================================================


@pytest.mark.asyncio
async def test_unauthenticated_phase9_endpoints_rejected_401(async_client: AsyncClient):
    assert (await async_client.post("/api/v1/commissions/preview", json={})).status_code == 401
    assert (await async_client.get("/api/v1/commissions")).status_code == 401
    assert (await async_client.get("/api/v1/commissions/payables")).status_code == 401
    assert (await async_client.post("/api/v1/commissions/1/approve", json={})).status_code == 401
    assert (
        await async_client.post(
            "/api/v1/commission-payouts",
            json={"partner_type": "AGENT", "partner_id": 101},
        )
    ).status_code == 401
    assert (await async_client.get("/api/v1/accounting/trial-balance")).status_code == 401
    assert (
        await async_client.post(
            "/api/v1/accounting/vouchers",
            json={"narration": "Test", "lines": []},
        )
    ).status_code == 401


@pytest.mark.asyncio
@pytest.mark.parametrize("restricted_role", ["AGENT", "FRANCHISE", "CLAIM", "pOLICY VIEW"])
async def test_unauthorized_roles_rejected_403_on_approval_payout_and_vouchers(
    async_client: AsyncClient,
    db_session: AsyncSession,
    restricted_role: str,
):
    _, headers = await create_user_with_role(
        db_session, role_name=restricted_role, branch_id=101, partner_user_id=701
    )

    r_app = await async_client.post(
        "/api/v1/commissions/1/approve",
        headers=headers,
        json={"partner_type": "AGENT"},
    )
    assert r_app.status_code == 403

    r_pay = await async_client.post(
        "/api/v1/commission-payouts",
        headers=headers,
        json={"partner_type": "AGENT", "partner_id": 701},
    )
    assert r_pay.status_code == 403

    r_rev = await async_client.post(
        "/api/v1/commission-payouts/1001/reverse",
        headers=headers,
        json={"reason": "Unauthorized attempt"},
    )
    assert r_rev.status_code == 403

    r_vch = await async_client.post(
        "/api/v1/accounting/vouchers",
        headers=headers,
        json={
            "narration": "Unauthorized voucher",
            "lines": [
                {"ledger_m_id": 1, "dr_cr": "DR", "amount": "100.00"},
                {"ledger_m_id": 2, "dr_cr": "CR", "amount": "100.00"},
            ],
        },
    )
    assert r_vch.status_code == 403


# ===========================================================================
# 2. Agent & Franchise Commission Lifecycle: Approval, Partial/Full Payout & Reversal
# ===========================================================================


@pytest.mark.asyncio
async def test_agent_and_franchise_commission_approval_payout_and_reversal(
    async_client: AsyncClient,
    db_session: AsyncSession,
):
    _, op_headers = await create_user_with_role(db_session, role_name="OPERATOR", branch_id=101)
    _, acc_headers = await create_user_with_role(db_session, role_name="ACCOUNT", branch_id=101)
    _, agent_701_headers = await create_user_with_role(
        db_session, role_name="AGENT", branch_id=101, partner_user_id=701
    )
    _, agent_702_headers = await create_user_with_role(
        db_session, role_name="AGENT", branch_id=101, partner_user_id=702
    )

    cust, veh = await create_synthetic_customer_and_vehicle(db_session, branch_id=101)

    # 1. Book a settled CASH policy with Agent #701 (10% OD = 1000 gross, 950 net; partial Cut & Pay = 350 -> 600 remaining)
    #    and Franchise #801 (15% OD = 1500 gross, 1425 net -> 475 spread)
    book_resp = await async_client.post(
        "/api/v1/policies/book",
        headers=op_headers,
        json={
            "customer_id": cust.CustomerId,
            "cust_veh_id": veh.CustVehId,
            "policy_no": "TEST_POLICY_P9_001",
            "vehicle_category": "PVT",
            "od_premium": "10000.00",
            "tp_premium": "5000.00",
            "commission": {
                "agent_id": 701,
                "agent_comm_od_percent": "10.00",
                "tds_percent": "5.00",
                "franchise_id": 801,
                "franchise_comm_od_percent": "15.00",
            },
            "cutnpay_enabled": True,
            "cutnpay_amount": "350.00",
            "payments": [
                {
                    "payment_type": "CASH",
                    "paid_amount": "17350.00",
                }
            ],
        },
    )
    assert book_resp.status_code == 201, book_resp.text
    tx_id = book_resp.json()["transaction_id"]

    # 2. Verify Principal Isolation: Agent #701 can view, Agent #702 gets 403
    r_own = await async_client.get(f"/api/v1/commissions/{tx_id}", headers=agent_701_headers)
    assert r_own.status_code == 200
    comm_data = r_own.json()
    assert Decimal(comm_data["agent_net_commission"]) == Decimal("950.00")
    assert Decimal(comm_data["cutnpay_deducted_amount"]) == Decimal("350.00")
    assert Decimal(comm_data["agent_remaining_payable"]) == Decimal("600.00")
    assert Decimal(comm_data["franchise_net_commission"]) == Decimal("1425.00")
    assert Decimal(comm_data["profit_of_net_commission"]) == Decimal("475.00")
    assert comm_data["is_payout_eligible"] is True

    r_other = await async_client.get(f"/api/v1/commissions/{tx_id}", headers=agent_702_headers)
    assert r_other.status_code == 403

    # 3. Approve Commission Payable as ACCOUNT
    app_resp = await async_client.post(
        f"/api/v1/commissions/{tx_id}/approve",
        headers=acc_headers,
        json={"partner_type": "BOTH", "remark": "Verified Q1 Commission"},
    )
    assert app_resp.status_code == 200
    assert Decimal(app_resp.json()["agent_commission_row"]["payment_status"]) == Decimal("3.00")
    assert app_resp.json()["agent_commission_row"]["payment_status_label"] == "APPROVED"

    # 4. Partial Agent Payout of 250.00 (leaving 350.00 remaining)
    pay1_resp = await async_client.post(
        "/api/v1/commission-payouts",
        headers=acc_headers,
        json={
            "partner_type": "AGENT",
            "partner_id": 701,
            "payment_mode": "NEFT",
            "payout_amount": "250.00",
            "transaction_ids": [tx_id],
            "bank_reference": "UTR-P9-001",
            "idempotency_key": "IDEMP-PAYOUT-P9-001",
        },
    )
    assert pay1_resp.status_code == 201, pay1_resp.text
    pay1 = pay1_resp.json()
    assert Decimal(pay1["total_payout_amount"]) == Decimal("250.00")
    assert pay1["allocations"][0]["remaining_payable_amount"] == "350.00"
    assert Decimal(pay1["allocations"][0]["payment_status"]) == Decimal("2.00")
    assert pay1["allocations"][0]["commission_paid_flag"] == 0

    # Duplicate idempotency_key rejected with 409
    dup_resp = await async_client.post(
        "/api/v1/commission-payouts",
        headers=acc_headers,
        json={
            "partner_type": "AGENT",
            "partner_id": 701,
            "payment_mode": "NEFT",
            "payout_amount": "250.00",
            "transaction_ids": [tx_id],
            "idempotency_key": "IDEMP-PAYOUT-P9-001",
        },
    )
    assert dup_resp.status_code == 409

    # Recalculation after partial payout rejected with 409
    recalc_resp = await async_client.post(
        "/api/v1/commissions/calculate",
        headers=acc_headers,
        json={
            "transaction_id": tx_id,
            "recalculate": True,
            "agent_comm_od_pct": "12.00",
        },
    )
    assert recalc_resp.status_code == 409

    # 5. Pay remaining 350.00 Agent commission + full 1425.00 Franchise commission
    pay2_resp = await async_client.post(
        "/api/v1/commission-payouts",
        headers=acc_headers,
        json={
            "partner_type": "AGENT",
            "partner_id": 701,
            "payment_mode": "NEFT",
            "transaction_ids": [tx_id],
        },
    )
    assert pay2_resp.status_code == 201
    pay2 = pay2_resp.json()
    assert Decimal(pay2["total_payout_amount"]) == Decimal("350.00")
    assert Decimal(pay2["allocations"][0]["remaining_payable_amount"]) == Decimal("0.00")
    assert Decimal(pay2["allocations"][0]["payment_status"]) == Decimal("1.00")
    # CommissionPaid is still 0 until Franchise commission (1425.00) is also settled!
    assert pay2["allocations"][0]["commission_paid_flag"] == 0

    pay_frn_resp = await async_client.post(
        "/api/v1/commission-payouts",
        headers=acc_headers,
        json={
            "partner_type": "FRANCHISE",
            "partner_id": 801,
            "payment_mode": "RTGS",
            "transaction_ids": [tx_id],
        },
    )
    assert pay_frn_resp.status_code == 201
    pay_frn = pay_frn_resp.json()
    assert Decimal(pay_frn["total_payout_amount"]) == Decimal("1425.00")
    assert pay_frn["allocations"][0]["commission_paid_flag"] == 1

    # 6. Reverse the second Agent payout (350.00) and verify balance restoration
    rev_resp = await async_client.post(
        f"/api/v1/commission-payouts/{pay2['payout_id']}/reverse",
        headers=acc_headers,
        json={"reason": "NEFT returned by beneficiary bank"},
    )
    assert rev_resp.status_code == 200
    rev_data = rev_resp.json()
    assert rev_data["status"] == "REVERSED"
    assert rev_data["reversal_doc_no"] is not None

    # Duplicate reversal rejected with 409
    dup_rev = await async_client.post(
        f"/api/v1/commission-payouts/{pay2['payout_id']}/reverse",
        headers=acc_headers,
        json={"reason": "Second reversal attempt"},
    )
    assert dup_rev.status_code == 409

    # Verify Policy Commission record has 350.00 remaining Agent payable and CommissionPaid=0
    after_rev = (await async_client.get(f"/api/v1/commissions/{tx_id}", headers=acc_headers)).json()
    assert Decimal(after_rev["agent_remaining_payable"]) == Decimal("350.00")
    assert after_rev["commission_paid_flag"] == 0


# ===========================================================================
# 3. Cheque Clearance / Bounce Eligibility Gate & Atomicity Rollback Tests
# ===========================================================================


@pytest.mark.asyncio
async def test_cheque_pending_and_bounce_blocks_commission_payout_until_cleared(
    async_client: AsyncClient,
    db_session: AsyncSession,
):
    _, op_headers = await create_user_with_role(db_session, role_name="OPERATOR", branch_id=101)
    _, acc_headers = await create_user_with_role(db_session, role_name="ACCOUNT", branch_id=101)
    cust, veh = await create_synthetic_customer_and_vehicle(db_session, branch_id=101)

    # Book policy with a CHEQUE instrument
    book_resp = await async_client.post(
        "/api/v1/policies/book",
        headers=op_headers,
        json={
            "customer_id": cust.CustomerId,
            "cust_veh_id": veh.CustVehId,
            "policy_no": "TEST_POLICY_P9_CHQ_001",
            "vehicle_category": "PVT",
            "od_premium": "10000.00",
            "tp_premium": "0.00",
            "commission": {
                "agent_id": 705,
                "agent_comm_od_percent": "10.00",
                "tds_percent": "5.00",
            },
            "payments": [
                {
                    "payment_type": "CHEQUE",
                    "paid_amount": "11800.00",
                    "docno": "CHQ705001",
                    "bankname": "ICICI BANK",
                }
            ],
        },
    )
    assert book_resp.status_code == 201
    tx_id = book_resp.json()["transaction_id"]
    payment_id = book_resp.json()["payment_summary"]["payments"][0]["payment_id"]

    # Attempt payout while cheque is pending clearance -> 409 Conflict
    early_payout = await async_client.post(
        "/api/v1/commission-payouts",
        headers=acc_headers,
        json={
            "partner_type": "AGENT",
            "partner_id": 705,
            "transaction_ids": [tx_id],
        },
    )
    assert early_payout.status_code == 409
    assert "Ischequeclearing=1" in early_payout.text

    # Clear the cheque -> policy becomes eligible for payout
    clear_resp = await async_client.post(
        f"/api/v1/payments/{payment_id}/clear",
        headers=acc_headers,
        json={"bank_reference": "CLR-705001"},
    )
    assert clear_resp.status_code == 200

    # Test fault injection on payout ("AFTER_COMMISSION_UPDATE") -> rolls back completely
    fail_payout = await async_client.post(
        "/api/v1/commission-payouts",
        headers=acc_headers,
        json={
            "partner_type": "AGENT",
            "partner_id": 705,
            "transaction_ids": [tx_id],
            "simulate_failure_at": "AFTER_COMMISSION_UPDATE",
        },
    )
    assert fail_payout.status_code == 500

    # Verify remaining payable is still 950.00 after rollback
    comm_check = (await async_client.get(f"/api/v1/commissions/{tx_id}", headers=acc_headers)).json()
    assert Decimal(comm_check["agent_remaining_payable"]) == Decimal("950.00")

    # Now execute clean payout -> 201 Created
    ok_payout = await async_client.post(
        "/api/v1/commission-payouts",
        headers=acc_headers,
        json={
            "partner_type": "AGENT",
            "partner_id": 705,
            "transaction_ids": [tx_id],
        },
    )
    assert ok_payout.status_code == 201
    assert Decimal(ok_payout.json()["total_payout_amount"]) == Decimal("950.00")
