"""
Phase 8 Integration Tests — Payment & Cheque Lifecycle APIs, Cheque Deposit/Clearance/Bounce,
Dishonor Penalty, Commission Hold, Replacement Instrument Re-Presentation, Payment Reversal,
RBAC Role Gates, Branch/Principal Isolation, Idempotency, and Atomic Rollback Verification.
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
async def cleanup_phase8_tables(db_session: AsyncSession):
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
async def test_unauthenticated_phase8_endpoints_rejected_401(async_client: AsyncClient):
    r1 = await async_client.get("/api/v1/payments")
    assert r1.status_code == 401

    r2 = await async_client.post("/api/v1/payments/1/clear", json={})
    assert r2.status_code == 401

    r3 = await async_client.post("/api/v1/payments/1/bounce", json={"bounce_reason": "NSF"})
    assert r3.status_code == 401

    r4 = await async_client.get("/api/v1/reconciliation/policies")
    assert r4.status_code == 401

    r5 = await async_client.get("/api/v1/wallets/AGENT/101")
    assert r5.status_code == 401


@pytest.mark.asyncio
@pytest.mark.parametrize("restricted_role", ["AGENT", "RELATIONSHIP MANAGER", "CLAIM", "pOLICY VIEW"])
async def test_unauthorized_roles_rejected_403_on_cheque_clear_bounce_and_wallet_topup(
    async_client: AsyncClient,
    db_session: AsyncSession,
    restricted_role: str,
):
    _, headers = await create_user_with_role(
        db_session, role_name=restricted_role, branch_id=101, partner_user_id=555
    )

    r_clear = await async_client.post("/api/v1/payments/1/clear", headers=headers, json={})
    assert r_clear.status_code == 403

    r_bounce = await async_client.post(
        "/api/v1/payments/1/bounce",
        headers=headers,
        json={"bounce_reason": "Insufficient Funds"},
    )
    assert r_bounce.status_code == 403

    r_rcon = await async_client.post(
        "/api/v1/reconciliation/policies/1/match",
        headers=headers,
        json={},
    )
    assert r_rcon.status_code == 403

    r_topup = await async_client.post(
        "/api/v1/wallets/topup",
        headers=headers,
        json={"owner_type": "AGENT", "owner_id": 555, "amount": "5000.00"},
    )
    assert r_topup.status_code == 403


# ===========================================================================
# 2. Cheque Lifecycle: PENDING_CLEARANCE -> DEPOSITED -> CLEARED
# ===========================================================================


@pytest.mark.asyncio
async def test_cheque_deposit_and_clearance_lifecycle(
    async_client: AsyncClient,
    db_session: AsyncSession,
):
    _, op_headers = await create_user_with_role(db_session, role_name="OPERATOR", branch_id=101)
    _, cashier_headers = await create_user_with_role(db_session, role_name="CASHIER", branch_id=101)
    _, acc_headers = await create_user_with_role(db_session, role_name="ACCOUNT", branch_id=101)

    cust, veh = await create_synthetic_customer_and_vehicle(db_session, branch_id=101)

    # 1. Book policy with a CHEQUE instrument
    book_resp = await async_client.post(
        "/api/v1/policies/book",
        headers=op_headers,
        json={
            "customer_id": cust.CustomerId,
            "cust_veh_id": veh.CustVehId,
            "policy_no": "TEST_POL_CHQ_CLEAR_01",
            "vehicle_category": "PVT",
            "od_premium": "6000.00",
            "tp_premium": "4000.00",
            "payments": [
                {
                    "payment_type": "CHEQUE",
                    "paid_amount": "11800.00",
                    "docno": "CHQ900101",
                    "bankname": "HDFC BANK",
                }
            ],
        },
    )
    assert book_resp.status_code == 201
    b_data = book_resp.json()
    tx_id = b_data["transaction_id"]
    pay_id = b_data["payment_summary"]["payments"][0]["payment_id"]
    assert b_data["payment_summary"]["payments"][0]["status"] == "PENDING_CLEARANCE"
    assert b_data["payment_summary"]["payments"][0]["cashier_approval"] == 0

    # 2. Deposit cheque via CASHIER
    dep_resp = await async_client.post(
        f"/api/v1/payments/{pay_id}/deposit",
        headers=cashier_headers,
        json={"bank_reference": "DEP-SLIP-2026-01", "remark": "Deposited at HDFC Pune"},
    )
    assert dep_resp.status_code == 200
    dep_body = dep_resp.json()
    assert dep_body["status"] == "DEPOSITED"
    assert dep_body["is_cheque_clearing"] == 1
    assert dep_body["is_cheque_cleared"] == 0
    assert dep_body["payment"]["cashier_approval"] == 1

    # Duplicate deposit rejected with 409 Conflict
    dup_dep = await async_client.post(
        f"/api/v1/payments/{pay_id}/deposit",
        headers=cashier_headers,
        json={"bank_reference": "DEP-SLIP-2026-01"},
    )
    assert dup_dep.status_code == 409

    # 3. Clear cheque via ACCOUNT
    clr_resp = await async_client.post(
        f"/api/v1/payments/{pay_id}/clear",
        headers=acc_headers,
        json={"bank_reference": "CLR-UTR-888999", "remark": "Cleared in bank statement"},
    )
    assert clr_resp.status_code == 200
    clr_body = clr_resp.json()
    assert clr_body["status"] == "CLEARED"
    assert clr_body["is_cheque_clearing"] == 0
    assert clr_body["is_cheque_cleared"] == 1
    assert clr_body["cheque_bank_status"] == 1
    assert clr_body["policy_t_status"] == "Booked"
    assert clr_body["policy_pending_status"] == 0
    assert Decimal(clr_body["policy_outstanding_amount"]) == Decimal("0.00")
    assert clr_body["payment"]["accountant_approval"] == 1

    # Duplicate clear rejected with 409 Conflict
    dup_clr = await async_client.post(
        f"/api/v1/payments/{pay_id}/clear",
        headers=acc_headers,
        json={},
    )
    assert dup_clr.status_code == 409


# ===========================================================================
# 3. Cheque Bounce + Dishonor Penalty + Commission Hold + Replacement Settlement
# ===========================================================================


@pytest.mark.asyncio
async def test_cheque_bounce_with_penalty_commission_hold_and_replacement_settlement(
    async_client: AsyncClient,
    db_session: AsyncSession,
):
    _, admin_headers = await create_user_with_role(db_session, role_name="ADMIN", branch_id=101)
    cust, veh = await create_synthetic_customer_and_vehicle(
        db_session, branch_id=101, reg_no="MH12BNC001"
    )

    # 1. Book policy with Cut & Pay (950.00) + Cheque (16750.00) -> Final = 17700.00
    book_resp = await async_client.post(
        "/api/v1/policies/book",
        headers=admin_headers,
        json={
            "customer_id": cust.CustomerId,
            "cust_veh_id": veh.CustVehId,
            "policy_no": "TEST_POL_BOUNCE_01",
            "vehicle_category": "PVT",
            "od_premium": "10000.00",
            "tp_premium": "5000.00",
            "cutnpay_enabled": True,
            "commission": {
                "agent_id": 401,
                "agent_comm_od_percent": "10.00",
                "tds_percent": "5.00",
            },
            "payments": [
                {
                    "payment_type": "CHEQUE",
                    "paid_amount": "16750.00",
                    "docno": "CHQ777001",
                    "bankname": "ICICI BANK",
                }
            ],
        },
    )
    assert book_resp.status_code == 201
    tx_id = book_resp.json()["transaction_id"]
    chq_id = book_resp.json()["payment_summary"]["payments"][0]["payment_id"]

    # 2. Bounce the cheque with a 500.00 dishonor penalty charge
    bnc_resp = await async_client.post(
        f"/api/v1/payments/{chq_id}/bounce",
        headers=admin_headers,
        json={
            "bounce_reason": "Funds Insufficient",
            "penalty_amount": "500.00",
            "bank_reference": "RET-MEMO-901",
        },
    )
    assert bnc_resp.status_code == 200
    bnc = bnc_resp.json()
    assert bnc["status"] == "BOUNCED"
    assert bnc["payment"]["isdeleted"] == "1"
    assert Decimal(bnc["policy_paid_amount"]) == Decimal("0.00")
    assert Decimal(bnc["policy_outstanding_amount"]) == Decimal("17250.00")  # 16750 + 500 penalty
    assert bnc["policy_t_status"] == "Pending"
    assert bnc["policy_pending_status"] == 1
    assert bnc["cheque_bank_status"] == 2
    assert bnc["commission_paid"] == 0
    assert Decimal(bnc["penalty_applied"]) == Decimal("500.00")

    # Verify accounting entries include contra reversal (-16750.00) and penalty (+500.00)
    acc_types = {
        (e["acc_trans_id"], e["transaction_type"], Decimal(e["amount"]))
        for e in bnc["accounting_entries"]
    }
    assert (2, "CHEQUE_BOUNCE_REVERSAL", Decimal("-16750.00")) in acc_types
    assert (4, "CHEQUE_BOUNCE_PENALTY", Decimal("500.00")) in acc_types

    # Verify CutNPayCommPayable row is placed on hold
    await db_session.commit()
    cnp_res = await db_session.execute(
        text("SELECT Flag FROM tbl_cutnpaycommpayable WHERE TransactionId = :tid"),
        {"tid": tx_id},
    )
    assert cnp_res.scalar() == "HOLD_CHEQUE_BOUNCE"

    # Double bounce or clearing a bounced cheque must be rejected with 409 Conflict
    dup_bnc = await async_client.post(
        f"/api/v1/payments/{chq_id}/bounce",
        headers=admin_headers,
        json={"bounce_reason": "Funds Insufficient"},
    )
    assert dup_bnc.status_code == 409

    clr_after_bnc = await async_client.post(
        f"/api/v1/payments/{chq_id}/clear",
        headers=admin_headers,
        json={},
    )
    assert clr_after_bnc.status_code == 409

    # 3. Record replacement NEFT payment covering 16750.00 + 500.00 penalty = 17250.00
    rep_resp = await async_client.post(
        f"/api/v1/policies/{tx_id}/payments",
        headers=admin_headers,
        json={
            "payment_type": "NEFT",
            "paid_amount": "17250.00",
            "docno": "NEFT-REPLACEMENT-01",
            "bankname": "SBI",
        },
    )
    assert rep_resp.status_code == 201
    rep_body = rep_resp.json()
    assert rep_body["t_status"] == "Booked"
    assert rep_body["pending_status"] == 0
    assert Decimal(rep_body["payment_summary"]["paid_amount"]) == Decimal("17250.00")
    assert Decimal(rep_body["payment_summary"]["outstanding_amount"]) == Decimal("0.00")


# ===========================================================================
# 4. Payment Reversal & E-Wallet Automatic Refund
# ===========================================================================


@pytest.mark.asyncio
async def test_payment_reversal_and_ewallet_refund(
    async_client: AsyncClient,
    db_session: AsyncSession,
):
    _, admin_headers = await create_user_with_role(db_session, role_name="ADMIN", branch_id=101)
    cust, veh = await create_synthetic_customer_and_vehicle(
        db_session, branch_id=101, reg_no="MH12REV001"
    )

    # 1. Top up Agent #601 E-Wallet with 15,000.00
    topup = await async_client.post(
        "/api/v1/wallets/topup",
        headers=admin_headers,
        json={
            "owner_type": "AGENT",
            "owner_id": 601,
            "amount": "15000.00",
            "payment_mode": "NEFT",
            "doc_no": "UTR-TOPUP-601",
        },
    )
    assert topup.status_code == 201
    assert Decimal(topup.json()["wallet"]["available_balance"]) == Decimal("15000.00")

    # 2. Book policy with partial Cash (5000.00), then pay remaining (6800.00) via EWALLET
    book_resp = await async_client.post(
        "/api/v1/policies/book",
        headers=admin_headers,
        json={
            "customer_id": cust.CustomerId,
            "cust_veh_id": veh.CustVehId,
            "policy_no": "TEST_POL_REV_01",
            "vehicle_category": "PVT",
            "od_premium": "6000.00",
            "tp_premium": "4000.00",
            "commission": {"agent_id": 601, "agent_comm_od_percent": "10.00"},
            "payments": [{"payment_type": "CASH", "paid_amount": "5000.00"}],
        },
    )
    assert book_resp.status_code == 201
    tx_id = book_resp.json()["transaction_id"]

    ew_pay = await async_client.post(
        f"/api/v1/policies/{tx_id}/payments",
        headers=admin_headers,
        json={
            "payment_type": "EWALLET",
            "paid_amount": "6800.00",
            "wallet_owner_type": "AGENT",
            "wallet_owner_id": 601,
        },
    )
    assert ew_pay.status_code == 201
    ew_payment_id = ew_pay.json()["payment_summary"]["payments"][-1]["payment_id"]

    # Wallet balance should now be 15000 - 6800 = 8200.00
    bal_after_debit = await async_client.get(
        "/api/v1/wallets/AGENT/601", headers=admin_headers
    )
    assert Decimal(bal_after_debit.json()["available_balance"]) == Decimal("8200.00")

    # 3. Reverse the E-Wallet payment -> reopens policy balance (6800.00) and refunds wallet (+6800.00)
    rev_resp = await async_client.post(
        f"/api/v1/payments/{ew_payment_id}/reverse",
        headers=admin_headers,
        json={
            "reason": "Incorrect wallet selected by operator",
            "refund_to_wallet": True,
            "wallet_owner_type": "AGENT",
            "wallet_owner_id": 601,
        },
    )
    assert rev_resp.status_code == 200
    rev_body = rev_resp.json()
    assert rev_body["status"] == "REVERSED"
    assert Decimal(rev_body["policy_paid_amount"]) == Decimal("5000.00")
    assert Decimal(rev_body["policy_outstanding_amount"]) == Decimal("6800.00")
    assert rev_body["policy_t_status"] == "Pending"

    # Wallet balance restored to 15000.00
    bal_after_rev = await async_client.get(
        "/api/v1/wallets/AGENT/601", headers=admin_headers
    )
    assert Decimal(bal_after_rev.json()["available_balance"]) == Decimal("15000.00")


# ===========================================================================
# 5. Idempotency, Duplicate Cheque Guard & Atomic Rollback Verification
# ===========================================================================


@pytest.mark.asyncio
async def test_payment_idempotency_duplicate_cheque_guard_and_atomic_rollback(
    async_client: AsyncClient,
    db_session: AsyncSession,
):
    _, admin_headers = await create_user_with_role(db_session, role_name="ADMIN", branch_id=101)
    cust, veh = await create_synthetic_customer_and_vehicle(
        db_session, branch_id=101, reg_no="MH12IDM001"
    )

    book_resp = await async_client.post(
        "/api/v1/policies/book",
        headers=admin_headers,
        json={
            "customer_id": cust.CustomerId,
            "cust_veh_id": veh.CustVehId,
            "policy_no": "TEST_POL_IDM_01",
            "vehicle_category": "PVT",
            "od_premium": "6000.00",
            "tp_premium": "4000.00",
            "payments": [
                {
                    "payment_type": "CHEQUE",
                    "paid_amount": "5000.00",
                    "docno": "CHQ555001",
                    "bankname": "AXIS BANK",
                    "idempotency_key": "PAY-IDEMP-001",
                }
            ],
        },
    )
    assert book_resp.status_code == 201
    tx_id = book_resp.json()["transaction_id"]
    chq_id = book_resp.json()["payment_summary"]["payments"][0]["payment_id"]

    # 1. Duplicate idempotency_key on subsequent payment -> 409 Conflict
    dup_idem = await async_client.post(
        f"/api/v1/policies/{tx_id}/payments",
        headers=admin_headers,
        json={
            "payment_type": "CASH",
            "paid_amount": "2000.00",
            "idempotency_key": "PAY-IDEMP-001",
        },
    )
    assert dup_idem.status_code == 409

    # 2. Duplicate active cheque (same docno + bankname) -> 409 Conflict
    dup_chq = await async_client.post(
        f"/api/v1/policies/{tx_id}/payments",
        headers=admin_headers,
        json={
            "payment_type": "CHEQUE",
            "paid_amount": "2000.00",
            "docno": "CHQ555001",
            "bankname": "AXIS BANK",
        },
    )
    assert dup_chq.status_code == 409

    # 3. Simulated failure during subsequent payment rolls back PaidAmount and tbl_transactionpayment
    fail_pay = await async_client.post(
        f"/api/v1/policies/{tx_id}/payments",
        headers=admin_headers,
        json={
            "payment_type": "CASH",
            "paid_amount": "3000.00",
            "simulate_failure_at": "BEFORE_LEDGER_COMMIT",
        },
    )
    assert fail_pay.status_code == 500

    # Verify policy PaidAmount is still 5000.00 and OutstandingAmount is still 6800.00
    pol_check = await async_client.get(f"/api/v1/policies/{tx_id}", headers=admin_headers)
    assert Decimal(pol_check.json()["payment_summary"]["paid_amount"]) == Decimal("5000.00")
    assert Decimal(pol_check.json()["payment_summary"]["outstanding_amount"]) == Decimal("6800.00")

    # 4. Simulated failure during cheque bounce rolls back payment state and policy balance
    fail_bnc = await async_client.post(
        f"/api/v1/payments/{chq_id}/bounce",
        headers=admin_headers,
        json={
            "bounce_reason": "Simulated Fault Test",
            "penalty_amount": "500.00",
            "simulate_failure_at": "DURING_ACCOUNTING",
        },
    )
    assert fail_bnc.status_code == 500

    pay_check = await async_client.get(f"/api/v1/payments/{chq_id}", headers=admin_headers)
    assert pay_check.json()["status"] == "PENDING_CLEARANCE"
    assert pay_check.json()["isdeleted"] == "0"
