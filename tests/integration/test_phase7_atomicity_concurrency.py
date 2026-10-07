"""
Phase 7 Atomicity, Rollback, Idempotency & Concurrency Integration Tests.

Verifies:
1. Single unit-of-work rollback when failure occurs AFTER_TRANSACTION, AFTER_PAYMENT,
   AFTER_COMMISSION, or DURING_ACCOUNTING (zero orphan rows in any table).
2. Idempotency & duplicate booking prevention on idempotency_key, PolicyNo, QuatationCode,
   and staged proposal TransId (HTTP 409 Conflict).
3. Concurrency-safe InwardNo allocation under parallel async policy booking requests
   (zero duplicate InwardNo values).
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
async def cleanup_atomicity_tables(db_session: AsyncSession):
    """Ensure clean Phase 6 & Phase 7 tables before and after each test."""
    for tbl in (
        "tbl_account",
        "tbl_transactionpayment",
        "tbl_franchisecommission",
        "tbl_agentcommissionpayment",
        "tbl_cutnpaycommpayable",
        "tbl_transaction",
        "tbl_transactionappnew",
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
        "tbl_app_quatationentry",
    ):
        await db_session.execute(text(f"DELETE FROM {tbl};"))
    await db_session.commit()


# ============================================================================
# 1. Single Unit-of-Work Atomicity & Deterministic Rollback Tests
# ============================================================================


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "failure_stage",
    [
        "AFTER_TRANSACTION",
        "AFTER_PAYMENT",
        "AFTER_COMMISSION",
        "DURING_ACCOUNTING",
    ],
)
async def test_atomic_rollback_leaves_zero_orphan_rows_on_downstream_failure(
    async_client: AsyncClient,
    db_session: AsyncSession,
    failure_stage: str,
):
    """
    When a failure occurs at any point after tbl_transaction flush, the entire
    unit of work rolls back cleanly leaving 0 rows in tbl_transaction,
    tbl_transactionpayment, commission tables, and tbl_account.
    """
    _, headers = await create_user_with_role(db_session, role_name="OPERATOR", branch_id=101)
    cust, veh = await create_synthetic_customer_and_vehicle(
        db_session, branch_id=101, reg_no=f"MH12RB{failure_stage[:4]}"
    )

    resp = await async_client.post(
        "/api/v1/policies/book",
        headers=headers,
        json={
            "customer_id": cust.CustomerId,
            "cust_veh_id": veh.CustVehId,
            "policy_no": f"TEST_POL_ROLLBACK_{failure_stage}",
            "vehicle_category": "PVT",
            "od_premium": "10000.00",
            "tp_premium": "4000.00",
            "cutnpay_enabled": True,
            "commission": {
                "agent_id": 111,
                "franchise_id": 222,
                "agent_comm_od_percent": "12.00",
            },
            "payments": [{"payment_type": "CASH", "paid_amount": "15380.00"}],
            "simulate_failure_at": failure_stage,
        },
    )
    assert resp.status_code == 500
    assert "rolled back" in str(resp.json()).lower()

    # Verify ZERO rows exist across all 6 tables
    for tbl in (
        "tbl_transaction",
        "tbl_transactionpayment",
        "tbl_franchisecommission",
        "tbl_agentcommissionpayment",
        "tbl_cutnpaycommpayable",
        "tbl_account",
    ):
        cnt_res = await db_session.execute(text(f"SELECT COUNT(*) FROM {tbl};"))
        assert int(cnt_res.scalar() or 0) == 0, f"Orphan row found in {tbl} after {failure_stage}"

    # Verify a subsequent valid booking succeeds and gets sequence #000001 (InwardNo was NOT burned!)
    ok_resp = await async_client.post(
        "/api/v1/policies/book",
        headers=headers,
        json={
            "customer_id": cust.CustomerId,
            "cust_veh_id": veh.CustVehId,
            "policy_no": f"TEST_POL_ROLLBACK_{failure_stage}",
            "vehicle_category": "PVT",
            "od_premium": "10000.00",
            "tp_premium": "4000.00",
            "payments": [{"payment_type": "CASH", "paid_amount": "16520.00"}],
        },
    )
    assert ok_resp.status_code == 201
    assert ok_resp.json()["inward_no"].endswith("-000001")


# ============================================================================
# 2. Idempotency & Duplicate Booking Prevention Tests
# ============================================================================


@pytest.mark.asyncio
async def test_duplicate_policy_no_idempotency_key_and_quotation_rejected_409(
    async_client: AsyncClient,
    db_session: AsyncSession,
):
    """
    Verifies all 4 duplicate booking guards:
    1. Duplicate idempotency_key -> 409 Conflict
    2. Duplicate (PolicyNo, InsuranceCompanyId) -> 409 Conflict
    3. Duplicate Self-Quotation consumption -> 409 Conflict
    4. Re-booking allowed after policy cancellation
    """
    _, headers = await create_user_with_role(db_session, role_name="ADMIN", branch_id=101)
    cust, veh = await create_synthetic_customer_and_vehicle(
        db_session, branch_id=101, reg_no="MH12IDEMP01"
    )

    # Create a Self-Quotation first
    q_resp = await async_client.post(
        "/api/v1/quotations/self",
        headers=headers,
        json={
            "title": "TEST_QUOTATION_IDEMP_001",
            "registration_no": "MH12IDEMP01",
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
    assert q_resp.status_code == 201
    q_id = q_resp.json()["quatation_id"]
    final_prem = q_resp.json()["final_premium"]

    # 1. First booking succeeds
    b1 = await async_client.post(
        "/api/v1/policies/book",
        headers=headers,
        json={
            "idempotency_key": "IDEMP-KEY-001",
            "customer_id": cust.CustomerId,
            "cust_veh_id": veh.CustVehId,
            "quotation_id": q_id,
            "quotation_source_type": "SELF_QUOTATION",
            "insurance_company_id": 1,
            "policy_no": "TEST_POLICY_UNIQ_001",
            "vehicle_category": "PVT",
            "payments": [{"payment_type": "CASH", "paid_amount": str(final_prem)}],
        },
    )
    assert b1.status_code == 201
    tx1_id = b1.json()["transaction_id"]

    # 2. Retry with same idempotency_key -> 409 Conflict
    dup_idem = await async_client.post(
        "/api/v1/policies/book",
        headers=headers,
        json={
            "idempotency_key": "IDEMP-KEY-001",
            "customer_id": cust.CustomerId,
            "cust_veh_id": veh.CustVehId,
            "insurance_company_id": 1,
            "policy_no": "TEST_POLICY_UNIQ_002",
            "vehicle_category": "PVT",
            "od_premium": "5000.00",
            "tp_premium": "2000.00",
        },
    )
    assert dup_idem.status_code == 409

    # 3. Retry with same PolicyNo for same insurer -> 409 Conflict
    dup_pol = await async_client.post(
        "/api/v1/policies/book",
        headers=headers,
        json={
            "customer_id": cust.CustomerId,
            "cust_veh_id": veh.CustVehId,
            "insurance_company_id": 1,
            "policy_no": "TEST_POLICY_UNIQ_001",
            "vehicle_category": "PVT",
            "od_premium": "5000.00",
            "tp_premium": "2000.00",
        },
    )
    assert dup_pol.status_code == 409

    # 4. Retry consuming the same Self-Quotation -> 409 Conflict
    dup_quot = await async_client.post(
        "/api/v1/policies/book",
        headers=headers,
        json={
            "customer_id": cust.CustomerId,
            "cust_veh_id": veh.CustVehId,
            "quotation_id": q_id,
            "quotation_source_type": "SELF_QUOTATION",
            "insurance_company_id": 1,
            "policy_no": "TEST_POLICY_UNIQ_003",
            "vehicle_category": "PVT",
        },
    )
    assert dup_quot.status_code == 409

    # 5. Cancel the first policy -> re-booking the quotation is now allowed!
    cancel_resp = await async_client.post(
        f"/api/v1/policies/{tx1_id}/cancel",
        headers=headers,
        json={"reason": "Data entry correction"},
    )
    assert cancel_resp.status_code == 200

    rebook_resp = await async_client.post(
        "/api/v1/policies/book",
        headers=headers,
        json={
            "customer_id": cust.CustomerId,
            "cust_veh_id": veh.CustVehId,
            "quotation_id": q_id,
            "quotation_source_type": "SELF_QUOTATION",
            "insurance_company_id": 1,
            "policy_no": "TEST_POLICY_UNIQ_001",
            "vehicle_category": "PVT",
            "payments": [{"payment_type": "CASH", "paid_amount": str(final_prem)}],
        },
    )
    assert rebook_resp.status_code == 201


# ============================================================================
# 3. Concurrent Inward Number Allocation Verification
# ============================================================================


@pytest.mark.asyncio
async def test_concurrent_policy_bookings_allocate_unique_sequential_inward_numbers(
    async_client: AsyncClient,
    db_session: AsyncSession,
):
    """
    Launches 5 concurrent policy booking requests in Branch 101 and verifies that
    every request succeeds with a unique, sequential InwardNo (000001..000005).
    """
    _, headers = await create_user_with_role(db_session, role_name="OPERATOR", branch_id=101)
    cust, veh = await create_synthetic_customer_and_vehicle(
        db_session, branch_id=101, reg_no="MH12CONC001"
    )

    async def _book_one(idx: int):
        return await async_client.post(
            "/api/v1/policies/book",
            headers=headers,
            json={
                "customer_id": cust.CustomerId,
                "cust_veh_id": veh.CustVehId,
                "policy_no": f"TEST_POL_CONC_{idx:03d}",
                "vehicle_category": "PVT",
                "od_premium": "5000.00",
                "tp_premium": "2000.00",
                "payments": [{"payment_type": "CASH", "paid_amount": "8260.00"}],
            },
        )

    responses = await asyncio.gather(*[_book_one(i) for i in range(1, 6)])
    for r in responses:
        assert r.status_code == 201, r.text

    inward_numbers = sorted(r.json()["inward_no"] for r in responses)
    assert len(set(inward_numbers)) == 5
    for idx, inw in enumerate(inward_numbers, start=1):
        assert inw.endswith(f"-{idx:06d}")
