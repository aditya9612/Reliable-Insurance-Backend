"""
Phase 8 Integration & Concurrency Tests — Partner E-Wallet (Top-Up, Lock, Release, Debit,
Principal Isolation), Insurer Payment & Brokerage Reconciliation, and 100-Operation
Concurrent Wallet Stress Test.
"""
import asyncio
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
async def cleanup_phase8_wallet_tables(db_session: AsyncSession):
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
# 1. Partner E-Wallet Lock -> Release -> Lock -> Consume Lifecycle & Isolation
# ===========================================================================


@pytest.mark.asyncio
async def test_wallet_lock_release_consume_and_principal_isolation(
    async_client: AsyncClient,
    db_session: AsyncSession,
):
    _, admin_headers = await create_user_with_role(db_session, role_name="ADMIN", branch_id=101)
    _, agent701_headers = await create_user_with_role(
        db_session, role_name="AGENT", branch_id=101, partner_user_id=701
    )
    _, agent702_headers = await create_user_with_role(
        db_session, role_name="AGENT", branch_id=101, partner_user_id=702
    )

    # 1. Admin tops up Agent #701 wallet with 20,000.00
    topup = await async_client.post(
        "/api/v1/wallets/topup",
        headers=admin_headers,
        json={
            "owner_type": "AGENT",
            "owner_id": 701,
            "amount": "20000.00",
            "payment_mode": "RTGS",
            "doc_no": "RTGS-701-01",
            "idempotency_key": "WAL-TOPUP-701-01",
        },
    )
    assert topup.status_code == 201
    assert Decimal(topup.json()["wallet"]["settled_balance"]) == Decimal("20000.00")
    assert Decimal(topup.json()["wallet"]["available_balance"]) == Decimal("20000.00")

    # Duplicate topup idempotency key -> 409 Conflict
    dup_top = await async_client.post(
        "/api/v1/wallets/topup",
        headers=admin_headers,
        json={
            "owner_type": "AGENT",
            "owner_id": 701,
            "amount": "20000.00",
            "idempotency_key": "WAL-TOPUP-701-01",
        },
    )
    assert dup_top.status_code == 409

    # 2. Agent #702 cannot read or lock Agent #701's wallet -> 403 Forbidden
    forbidden_read = await async_client.get(
        "/api/v1/wallets/AGENT/701", headers=agent702_headers
    )
    assert forbidden_read.status_code == 403

    forbidden_lock = await async_client.post(
        "/api/v1/wallets/lock",
        headers=agent702_headers,
        json={"owner_type": "AGENT", "owner_id": 701, "amount": "5000.00"},
    )
    assert forbidden_lock.status_code == 403

    # 3. Agent #701 locks 8,000.00 for a staged proposal
    lock1 = await async_client.post(
        "/api/v1/wallets/lock",
        headers=agent701_headers,
        json={
            "owner_type": "AGENT",
            "owner_id": 701,
            "amount": "8000.00",
            "narration": "Hold for Proposal #1",
        },
    )
    assert lock1.status_code == 201
    lock1_id = lock1.json()["ledger_entry"]["account_id"]
    assert Decimal(lock1.json()["wallet"]["settled_balance"]) == Decimal("20000.00")
    assert Decimal(lock1.json()["wallet"]["locked_balance"]) == Decimal("8000.00")
    assert Decimal(lock1.json()["wallet"]["available_balance"]) == Decimal("12000.00")

    # Attempting to lock 15,000.00 when only 12,000.00 is available -> 422
    over_lock = await async_client.post(
        "/api/v1/wallets/lock",
        headers=agent701_headers,
        json={"owner_type": "AGENT", "owner_id": 701, "amount": "15000.00"},
    )
    assert over_lock.status_code == 422

    # 4. Release lock1 -> available balance returns to 20,000.00
    rel1 = await async_client.post(
        "/api/v1/wallets/release",
        headers=agent701_headers,
        json={"lock_account_id": lock1_id, "reason": "Customer changed quote"},
    )
    assert rel1.status_code == 200
    assert Decimal(rel1.json()["wallet"]["locked_balance"]) == Decimal("0.00")
    assert Decimal(rel1.json()["wallet"]["available_balance"]) == Decimal("20000.00")

    # Double release rejected with 409 Conflict
    dup_rel = await async_client.post(
        "/api/v1/wallets/release",
        headers=agent701_headers,
        json={"lock_account_id": lock1_id, "reason": "Duplicate release"},
    )
    assert dup_rel.status_code == 409

    # 5. Lock 11,800.00 and consume it during Policy Booking
    lock2 = await async_client.post(
        "/api/v1/wallets/lock",
        headers=agent701_headers,
        json={"owner_type": "AGENT", "owner_id": 701, "amount": "11800.00"},
    )
    assert lock2.status_code == 201
    lock2_id = lock2.json()["ledger_entry"]["account_id"]
    assert Decimal(lock2.json()["wallet"]["available_balance"]) == Decimal("8200.00")

    cust, veh = await create_synthetic_customer_and_vehicle(
        db_session, branch_id=101, reg_no="MH12WAL701"
    )
    book_resp = await async_client.post(
        "/api/v1/policies/book",
        headers=admin_headers,
        json={
            "customer_id": cust.CustomerId,
            "cust_veh_id": veh.CustVehId,
            "policy_no": "TEST_POL_WAL_701",
            "vehicle_category": "PVT",
            "od_premium": "6000.00",
            "tp_premium": "4000.00",
            "ewallet_amount_used": "11800.00",
            "wallet_owner_type": "AGENT",
            "wallet_owner_id": 701,
            "wallet_lock_id": lock2_id,
            "commission": {"agent_id": 701, "agent_comm_od_percent": "10.00"},
        },
    )
    assert book_resp.status_code == 201
    assert book_resp.json()["t_status"] == "Booked"

    # Verify lock2 is now consumed: settled_balance = 8200.00, locked_balance = 0.00, available = 8200.00
    stmt_resp = await async_client.get(
        "/api/v1/wallets/AGENT/701/transactions", headers=agent701_headers
    )
    assert stmt_resp.status_code == 200
    w_state = stmt_resp.json()["wallet"]
    assert Decimal(w_state["settled_balance"]) == Decimal("8200.00")
    assert Decimal(w_state["locked_balance"]) == Decimal("0.00")
    assert Decimal(w_state["available_balance"]) == Decimal("8200.00")


# ===========================================================================
# 2. Insurer Payment & Brokerage Reconciliation Workflow
# ===========================================================================


@pytest.mark.asyncio
async def test_insurer_reconciliation_full_match_and_variance_workflow(
    async_client: AsyncClient,
    db_session: AsyncSession,
):
    _, admin_headers = await create_user_with_role(db_session, role_name="ADMIN", branch_id=101)
    _, acc_headers = await create_user_with_role(db_session, role_name="ACCOUNT", branch_id=101)
    cust, veh = await create_synthetic_customer_and_vehicle(
        db_session, branch_id=101, reg_no="MH12RCN001"
    )

    # Book policy: OD = 10000, TP = 5000 -> Net = 15000, Final = 17700; Gross Comm (10% OD) = 1000.00
    b_resp = await async_client.post(
        "/api/v1/policies/book",
        headers=admin_headers,
        json={
            "customer_id": cust.CustomerId,
            "cust_veh_id": veh.CustVehId,
            "policy_no": "TEST_POL_RCON_01",
            "vehicle_category": "PVT",
            "od_premium": "10000.00",
            "tp_premium": "5000.00",
            "commission": {
                "agent_id": 801,
                "agent_comm_od_percent": "10.00",
                "tds_percent": "5.00",
            },
            "payments": [{"payment_type": "ONLINE", "paid_amount": "17700.00"}],
        },
    )
    assert b_resp.status_code == 201
    tx_id = b_resp.json()["transaction_id"]

    # 1. Partial/variance match first (Insurer statement reports 850.00 instead of 1000.00)
    var_resp = await async_client.post(
        f"/api/v1/reconciliation/policies/{tx_id}/match",
        headers=acc_headers,
        json={
            "reconciled_comm_amount": "850.00",
            "company_submission_doc_no": "SUB-DOC-2026-01",
            "ib_doc_no": 5001,
            "allow_partial_match": True,
        },
    )
    assert var_resp.status_code == 200
    v_body = var_resp.json()
    assert v_body["is_rcon_data_match"] == 2
    assert v_body["match_status"] == "PARTIAL_VARIANCE"
    assert Decimal(v_body["commission_variance"]) == Decimal("-150.00")
    assert v_body["accounting_entry"]["acc_trans_id"] == 5

    # 2. Full exact match after insurer credit note (1000.00)
    full_resp = await async_client.post(
        f"/api/v1/reconciliation/policies/{tx_id}/match",
        headers=acc_headers,
        json={
            "reconciled_comm_amount": "1000.00",
            "company_submission_doc_no": "SUB-DOC-2026-02",
            "company_cheque_no": "CMP-CHQ-9001",
            "is_company_cheque": True,
            "ib_doc_no": 5002,
            "ib_receipt_status": 1,
        },
    )
    assert full_resp.status_code == 200
    f_body = full_resp.json()
    assert f_body["is_rcon_data_match"] == 1
    assert f_body["match_status"] == "MATCHED"
    assert Decimal(f_body["commission_variance"]) == Decimal("0.00")
    assert f_body["is_company_cheque"] == 1
    assert f_body["ib_doc_no"] == 5002

    # Duplicate full match with same ib_doc_no -> 409 Conflict
    dup_rcon = await async_client.post(
        f"/api/v1/reconciliation/policies/{tx_id}/match",
        headers=acc_headers,
        json={
            "reconciled_comm_amount": "1000.00",
            "ib_doc_no": 5002,
        },
    )
    assert dup_rcon.status_code == 409


# ===========================================================================
# 3. 100 Concurrent Wallet Operations Stress Test (Zero Negative Balance)
# ===========================================================================


@pytest.mark.asyncio
async def test_100_concurrent_wallet_operations_never_go_negative(
    async_client: AsyncClient,
    db_session: AsyncSession,
):
    """
    Phase 8 Concurrency Requirement:
    - Top up Agent #999 E-Wallet with 25,000.00 (50 units of 500.00).
    - Launch 100 concurrent debit/lock operations of 500.00 each.
    - Verify:
      1. Exactly 50 operations succeed (201 Created).
      2. Exactly 50 operations are rejected (422 Unprocessable Entity) for insufficient funds.
      3. Final available_balance == 0.00 (never negative).
    """
    _, admin_headers = await create_user_with_role(db_session, role_name="ADMIN", branch_id=101)

    topup = await async_client.post(
        "/api/v1/wallets/topup",
        headers=admin_headers,
        json={
            "owner_type": "AGENT",
            "owner_id": 999,
            "amount": "25000.00",
            "payment_mode": "NEFT",
            "doc_no": "CONC-SEED-25K",
        },
    )
    assert topup.status_code == 201
    assert Decimal(topup.json()["wallet"]["available_balance"]) == Decimal("25000.00")

    async def _attempt_wallet_op(idx: int):
        # Mix 50 locks and 50 direct debits across 100 concurrent tasks
        if idx % 2 == 0:
            return await async_client.post(
                "/api/v1/wallets/debit",
                headers=admin_headers,
                json={
                    "owner_type": "AGENT",
                    "owner_id": 999,
                    "amount": "500.00",
                    "narration": f"Concurrent Debit #{idx}",
                },
            )
        else:
            return await async_client.post(
                "/api/v1/wallets/lock",
                headers=admin_headers,
                json={
                    "owner_type": "AGENT",
                    "owner_id": 999,
                    "amount": "500.00",
                    "narration": f"Concurrent Lock #{idx}",
                },
            )

    responses = await asyncio.gather(*(_attempt_wallet_op(i) for i in range(100)))
    status_codes = [r.status_code for r in responses]

    succeeded = [r for r in responses if r.status_code == 201]
    rejected = [r for r in responses if r.status_code == 422]

    assert len(succeeded) == 50, f"Expected 50 successes, got {len(succeeded)} (codes: {status_codes})"
    assert len(rejected) == 50, f"Expected 50 rejections (422), got {len(rejected)}"

    # Verify final wallet balance is exactly 0.00 available
    final_bal = await async_client.get("/api/v1/wallets/AGENT/999", headers=admin_headers)
    assert final_bal.status_code == 200
    bal_data = final_bal.json()
    assert Decimal(bal_data["available_balance"]) == Decimal("0.00")
    assert (
        Decimal(bal_data["settled_balance"]) - Decimal(bal_data["locked_balance"])
        == Decimal("0.00")
    )
