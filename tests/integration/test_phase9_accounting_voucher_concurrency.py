"""
Phase 9 Integration & Concurrency Tests — Master Ledgers, Running-Balance Ledger Statements,
Double-Entry Vouchers, Unbalanced Voucher Rejection, Voucher Reversal, Trial Balance Zero-Variance
Invariants, and 100-Concurrent-Commission-Payout Stress Test.
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
async def cleanup_phase9_accounting_tables(db_session: AsyncSession):
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
# 1. Master Ledgers, Double-Entry Vouchers, Running Statements & Trial Balance
# ===========================================================================


@pytest.mark.asyncio
async def test_master_ledgers_double_entry_vouchers_statements_and_trial_balance(
    async_client: AsyncClient,
    db_session: AsyncSession,
):
    _, acc_headers = await create_user_with_role(db_session, role_name="ACCOUNT HEAD", branch_id=101)

    # 1. Create two Master Ledgers in tbl_ledgermaster
    l1_resp = await async_client.post(
        "/api/v1/accounting/ledgers",
        headers=acc_headers,
        json={
            "ledger_name": "TEST_LEDGER_001_BANK_HDFC",
            "ledger_type_id": 1,
            "ledger_group_id": 10,
            "reference_id": 0,
            "branch_id": 101,
        },
    )
    assert l1_resp.status_code == 201
    ledger_bank_id = l1_resp.json()["ledger_m_id"]

    # Duplicate ledger name in same branch rejected with 409
    dup_l1 = await async_client.post(
        "/api/v1/accounting/ledgers",
        headers=acc_headers,
        json={
            "ledger_name": "TEST_LEDGER_001_BANK_HDFC",
            "ledger_type_id": 1,
            "ledger_group_id": 10,
            "branch_id": 101,
        },
    )
    assert dup_l1.status_code == 409

    l2_resp = await async_client.post(
        "/api/v1/accounting/ledgers",
        headers=acc_headers,
        json={
            "ledger_name": "TEST_LEDGER_002_OFFICE_EXPENSE",
            "ledger_type_id": 4,
            "ledger_group_id": 40,
            "reference_id": 0,
            "branch_id": 101,
        },
    )
    assert l2_resp.status_code == 201
    ledger_exp_id = l2_resp.json()["ledger_m_id"]

    # 2. Reject Unbalanced Voucher (DR 1500 != CR 1400) -> 422
    unbal_resp = await async_client.post(
        "/api/v1/accounting/vouchers",
        headers=acc_headers,
        json={
            "voucher_type": "JOURNAL",
            "narration": "Unbalanced test voucher",
            "lines": [
                {"ledger_m_id": ledger_exp_id, "dr_cr": "DR", "amount": "1500.00"},
                {"ledger_m_id": ledger_bank_id, "dr_cr": "CR", "amount": "1400.00"},
            ],
        },
    )
    assert unbal_resp.status_code == 422

    # 3. Reject Atomic Fault Injection ("AFTER_FIRST_LINE") -> 500 and zero persisted lines
    fault_vch = await async_client.post(
        "/api/v1/accounting/vouchers",
        headers=acc_headers,
        json={
            "voucher_type": "PAYMENT",
            "narration": "Simulated failure voucher",
            "simulate_failure_at": "AFTER_FIRST_LINE",
            "lines": [
                {"ledger_m_id": ledger_exp_id, "dr_cr": "DR", "amount": "2500.00"},
                {"ledger_m_id": ledger_bank_id, "dr_cr": "CR", "amount": "2500.00"},
            ],
        },
    )
    assert fault_vch.status_code == 500

    # Verify zero entries in ledger statement after rollback
    stmt_empty = (
        await async_client.get(
            f"/api/v1/accounting/ledgers/{ledger_exp_id}/entries", headers=acc_headers
        )
    ).json()
    assert stmt_empty["total_entries"] == 0

    # 4. Create Balanced Voucher #1 (2500.00) with idempotency_key
    v1_resp = await async_client.post(
        "/api/v1/accounting/vouchers",
        headers=acc_headers,
        json={
            "voucher_type": "PAYMENT",
            "payment_mode": "NEFT",
            "narration": "TEST_VOUCHER_001 Office Rent",
            "idempotency_key": "IDEMP-VCH-001",
            "lines": [
                {"ledger_m_id": ledger_exp_id, "dr_cr": "DR", "amount": "2500.00"},
                {"ledger_m_id": ledger_bank_id, "dr_cr": "CR", "amount": "2500.00"},
            ],
        },
    )
    assert v1_resp.status_code == 201
    v1 = v1_resp.json()
    assert v1["is_balanced"] is True
    assert Decimal(v1["total_debit"]) == Decimal("2500.00")
    assert Decimal(v1["total_credit"]) == Decimal("2500.00")
    doc_no_1 = v1["doc_no"]

    # Duplicate voucher idempotency_key -> 409
    dup_v1 = await async_client.post(
        "/api/v1/accounting/vouchers",
        headers=acc_headers,
        json={
            "voucher_type": "PAYMENT",
            "narration": "Duplicate voucher",
            "idempotency_key": "IDEMP-VCH-001",
            "lines": [
                {"ledger_m_id": ledger_exp_id, "dr_cr": "DR", "amount": "2500.00"},
                {"ledger_m_id": ledger_bank_id, "dr_cr": "CR", "amount": "2500.00"},
            ],
        },
    )
    assert dup_v1.status_code == 409

    # 5. Check Running-Balance Ledger Statement & Trial Balance
    stmt_exp = (
        await async_client.get(
            f"/api/v1/accounting/ledgers/{ledger_exp_id}/entries", headers=acc_headers
        )
    ).json()
    assert stmt_exp["total_entries"] == 1
    assert Decimal(stmt_exp["closing_balance"]) == Decimal("2500.00")
    assert stmt_exp["closing_polarity"] == "DR"

    tb1 = (await async_client.get("/api/v1/accounting/trial-balance", headers=acc_headers)).json()
    assert tb1["is_balanced"] is True
    assert Decimal(tb1["variance"]) == Decimal("0.00")
    assert Decimal(tb1["total_gross_debit"]) == Decimal("2500.00")
    assert Decimal(tb1["total_gross_credit"]) == Decimal("2500.00")

    # 6. Reverse Voucher #1 and verify closing balance returns to 0.00 and Trial Balance remains balanced
    rev_v1 = await async_client.post(
        f"/api/v1/accounting/vouchers/{doc_no_1}/reverse",
        headers=acc_headers,
        json={"reason": "Posted to wrong expense head"},
    )
    assert rev_v1.status_code == 200
    assert rev_v1.json()["status"] == "REVERSED"

    stmt_after = (
        await async_client.get(
            f"/api/v1/accounting/ledgers/{ledger_exp_id}/entries", headers=acc_headers
        )
    ).json()
    assert stmt_after["total_entries"] == 2
    assert Decimal(stmt_after["closing_balance"]) == Decimal("0.00")
    assert stmt_after["closing_polarity"] == "ZERO"

    tb2 = (await async_client.get("/api/v1/accounting/trial-balance", headers=acc_headers)).json()
    assert tb2["is_balanced"] is True
    assert Decimal(tb2["variance"]) == Decimal("0.00")
    assert Decimal(tb2["total_gross_debit"]) == Decimal("5000.00")
    assert Decimal(tb2["total_gross_credit"]) == Decimal("5000.00")
    assert Decimal(tb2["total_net_debit"]) == Decimal("0.00")
    assert Decimal(tb2["total_net_credit"]) == Decimal("0.00")


# ===========================================================================
# 2. 100 Concurrent Commission Payouts Against Single Payable Pool
# ===========================================================================


@pytest.mark.asyncio
async def test_100_concurrent_commission_payouts_never_overpay_or_duplicate_doc_no(
    async_client: AsyncClient,
    db_session: AsyncSession,
):
    """
    Seeds a settled policy with exactly ₹5,000.00 Agent Net Commission payable for Agent #999.
    Executes 100 concurrent POST /api/v1/commission-payouts requests of ₹500.00 each.
    Verifies:
    - Exactly 10 requests succeed (10 * 500.00 = 5,000.00)
    - Exactly 90 requests fail with 409 Conflict
    - Final Agent remaining payable is 0.00 (never negative!)
    - All 10 generated voucher Doc_No values are strictly unique
    - Trial Balance remains 100% balanced (variance == 0.00)
    """
    _, op_headers = await create_user_with_role(db_session, role_name="OPERATOR", branch_id=101)
    _, acc_headers = await create_user_with_role(db_session, role_name="ACCOUNT", branch_id=101)
    cust, veh = await create_synthetic_customer_and_vehicle(db_session, branch_id=101)

    # Book policy with OD = 50,000, Agent OD % = 10% (5,000 gross), TDS = 0% -> 5,000.00 NetCommission
    book_resp = await async_client.post(
        "/api/v1/policies/book",
        headers=op_headers,
        json={
            "customer_id": cust.CustomerId,
            "cust_veh_id": veh.CustVehId,
            "policy_no": "TEST_POLICY_CONC_100",
            "vehicle_category": "PVT",
            "od_premium": "50000.00",
            "tp_premium": "0.00",
            "commission": {
                "agent_id": 999,
                "agent_comm_od_percent": "10.00",
                "tds_percent": "0.00",
            },
            "payments": [
                {
                    "payment_type": "CASH",
                    "paid_amount": "59000.00",
                }
            ],
        },
    )
    assert book_resp.status_code == 201, book_resp.text
    tx_id = book_resp.json()["transaction_id"]

    async def _attempt_payout(idx: int):
        return await async_client.post(
            "/api/v1/commission-payouts",
            headers=acc_headers,
            json={
                "partner_type": "AGENT",
                "partner_id": 999,
                "payment_mode": "NEFT",
                "payout_amount": "500.00",
                "transaction_ids": [tx_id],
                "narration": f"Concurrent Payout Worker #{idx}",
            },
        )

    responses = await asyncio.gather(*(_attempt_payout(i) for i in range(100)))

    succeeded = [r for r in responses if r.status_code == 201]
    rejected = [r for r in responses if r.status_code == 409]

    assert len(succeeded) == 10, f"Expected 10 successes, got {len(succeeded)}"
    assert len(rejected) == 90, f"Expected 90 conflicts, got {len(rejected)}"

    # Verify all 10 voucher Doc_No values are unique
    doc_nos = {r.json()["payout_id"] for r in succeeded}
    assert len(doc_nos) == 10

    # Verify final policy commission payable is exactly 0.00 and CommissionPaid == 1
    comm_after = (await async_client.get(f"/api/v1/commissions/{tx_id}", headers=acc_headers)).json()
    assert Decimal(comm_after["agent_paid_amount"]) == Decimal("5000.00")
    assert Decimal(comm_after["agent_remaining_payable"]) == Decimal("0.00")
    assert comm_after["commission_paid_flag"] == 1
    assert Decimal(comm_after["agent_commission_row"]["payment_status"]) == Decimal("1.00")

    # Verify Trial Balance is balanced with 0.00 variance
    tb = (await async_client.get("/api/v1/accounting/trial-balance", headers=acc_headers)).json()
    assert tb["is_balanced"] is True
    assert Decimal(tb["variance"]) == Decimal("0.00")
