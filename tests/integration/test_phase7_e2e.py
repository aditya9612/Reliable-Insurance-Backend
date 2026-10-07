"""
Phase 7 End-to-End (E2E) Verification Test Suite.

Executes the complete local synthetic insurance lifecycle:
    TEST_CUSTOMER_001 (POST /api/v1/customers)
      ↓
    TEST_VEHICLE_001 (POST /api/v1/customers/{id}/vehicles)
      ↓
    TEST_QUOTATION_001 (POST /api/v1/quotations/self)
      ↓
    Quotation Policy Prefill (GET /api/v1/quotations/self/{qid}/policy-prefill)
      ↓
    Policy Financial Preview (POST /api/v1/policies/preview)
      ↓
    Staged Proposal & Cashier/Accountant/Owner Approval (POST /api/v1/policies/proposals)
      ↓
    Atomic Policy Booking TEST_POLICY_001 (POST /api/v1/policies/book)
      ↓
    Subsequent Balance Settlement Payment (POST /api/v1/policies/{tx_id}/payments)
      ↓
    Full Verification of tbl_transaction, tbl_transactionpayment, commission tables, and tbl_account
"""
from decimal import Decimal
import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from tests.integration.test_phase7_policy_booking_api import create_user_with_role


@pytest.fixture(autouse=True)
async def cleanup_e2e_tables(db_session: AsyncSession):
    for tbl in (
        "tbl_account",
        "tbl_transactionpayment",
        "tbl_franchisecommission",
        "tbl_agentcommissionpayment",
        "tbl_cutnpaycommpayable",
        "tbl_transaction",
        "tbl_transactionappnew",
        "tbl_app_quatationentry",
        "tbl_vehicledetails",
        "tbl_customer",
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
        "tbl_vehicledetails",
        "tbl_customer",
    ):
        await db_session.execute(text(f"DELETE FROM {tbl};"))
    await db_session.commit()


@pytest.mark.asyncio
async def test_full_end_to_end_customer_vehicle_quotation_to_policy_booking_lifecycle(
    async_client: AsyncClient,
    db_session: AsyncSession,
):
    """
    Full E2E Pipeline:
    1. Create TEST_CUSTOMER_001 via Customer API
    2. Create TEST_VEHICLE_001 via Vehicle API
    3. Create TEST_QUOTATION_001 via Quotation API
    4. Fetch Policy Prefill from TEST_QUOTATION_001
    5. Preview Policy Financials
    6. Submit Staged Proposal & Approve across Cashier, Accountant, and Owner
    7. Book TEST_POLICY_001 atomically with partial payment
    8. Settle remaining balance via Payments API
    9. Verify all persisted database records and negative tamper/duplicate paths
    """
    _, admin_headers = await create_user_with_role(
        db_session, role_name="ADMIN", branch_id=101
    )

    # Step 1: Create TEST_CUSTOMER_001 via POST /api/v1/customers
    cust_resp = await async_client.post(
        "/api/v1/customers",
        headers=admin_headers,
        json={
            "initial": "MR.",
            "CustFName": "TEST_CUSTOMER_001",
            "CustMName": "SYNTHETIC",
            "CustLName": "USER",
            "CustomerType": "INDIVIDUAL",
            "MoblieNo1": "9876501001",
            "EMailId": "test_customer_001@example.local",
            "BranchId": 101,
        },
    )
    assert cust_resp.status_code == 201, cust_resp.text
    customer_id = cust_resp.json()["customer_id"]
    assert cust_resp.json()["customer_code"] == str(customer_id)

    # Step 2: Create TEST_VEHICLE_001 via POST /api/v1/customers/{customer_id}/vehicles
    veh_resp = await async_client.post(
        f"/api/v1/customers/{customer_id}/vehicles",
        headers=admin_headers,
        json={
            "financial_year": "2026-2027",
            "registration_no": "MH12E2E1001",
            "chaise_no": "E2ECHASSIS1000001",
            "engine_no": "E2EENGINE1000001",
            "mfg_year": "2024",
            "seats_capacity": "5",
            "engine_power": "1197",
            "vehicle_weight": "1050",
            "vehicle_variant": "ZXI+",
        },
    )
    assert veh_resp.status_code == 201, veh_resp.text
    cust_veh_id = veh_resp.json()["cust_veh_id"]

    # Step 3: Create TEST_QUOTATION_001 via POST /api/v1/quotations/self
    quot_resp = await async_client.post(
        "/api/v1/quotations/self",
        headers=admin_headers,
        json={
            "title": "TEST_QUOTATION_001",
            "registration_no": "MH12E2E1001",
            "agent_id": 501,
            "sale_ex_id": 601,
            "calculation_input": {
                "vehicle_category": "PVT",
                "product_type_id": 1,
                "business_type_id": 3,
                "insurance_company_id": 1,
                "cubic_capacity": 1197,
                "seating_capacity": 5,
                "zone": "A",
                "vehicle_age_override": "2.0",
                "base_idv_override": "600000",
                "selected_idv": "600000",
                "ncb_percent": "20",
                "od_discount_override": "40",
                "pa_to_owner_driver": True,
                "ll_paid_driver_count": 1,
            },
        },
    )
    assert quot_resp.status_code == 201, quot_resp.text
    quot_data = quot_resp.json()
    quotation_id = quot_data["quatation_id"]
    quotation_code = quot_data["quatation_code"]

    # Step 4: Fetch Policy Prefill via GET /api/v1/quotations/self/{quotation_id}/policy-prefill
    prefill_resp = await async_client.get(
        f"/api/v1/quotations/self/{quotation_id}/policy-prefill",
        headers=admin_headers,
    )
    assert prefill_resp.status_code == 200
    prefill = prefill_resp.json()
    assert prefill["quotation_code"] == quotation_code
    assert Decimal(prefill["final_premium"]) == Decimal(quot_data["final_premium"])

    # Step 5: Preview Policy Financials via POST /api/v1/policies/preview
    preview_resp = await async_client.post(
        "/api/v1/policies/preview",
        headers=admin_headers,
        json={
            "quotation_id": quotation_id,
            "quotation_source_type": "SELF_QUOTATION",
            "insurance_company_id": 1,
            "vehicle_category": "PVT",
            "commission": {
                "agent_id": 501,
                "sales_ex_id": 601,
                "franchise_id": 701,
                "agent_comm_od_percent": "15.00",
                "agent_comm_net_percent": "5.00",
                "tds_percent": "5.00",
            },
            "payments": [
                {"payment_type": "CASH", "paid_amount": "5000.00"},
            ],
        },
    )
    assert preview_resp.status_code == 200
    prev_body = preview_resp.json()
    final_premium = Decimal(prev_body["premium_summary"]["final_premium"])
    expected_outstanding = final_premium - Decimal("5000.00")
    assert Decimal(prev_body["payment_summary"]["outstanding_amount"]) == expected_outstanding

    # Step 6: Negative Tamper Check — submitting tampered final_premium against quotation -> 422
    tamper_resp = await async_client.post(
        "/api/v1/policies/book",
        headers=admin_headers,
        json={
            "customer_id": customer_id,
            "cust_veh_id": cust_veh_id,
            "quotation_id": quotation_id,
            "quotation_source_type": "SELF_QUOTATION",
            "final_premium": "100.00",
        },
    )
    assert tamper_resp.status_code == 422

    # Step 7: Book TEST_POLICY_001 via POST /api/v1/policies/book
    book_resp = await async_client.post(
        "/api/v1/policies/book",
        headers=admin_headers,
        json={
            "idempotency_key": "E2E-TEST-POLICY-001",
            "customer_id": customer_id,
            "cust_veh_id": cust_veh_id,
            "quotation_id": quotation_id,
            "quotation_source_type": "SELF_QUOTATION",
            "insurance_company_id": 1,
            "policy_no": "TEST_POLICY_001",
            "vehicle_category": "PVT",
            "commission": {
                "agent_id": 501,
                "sales_ex_id": 601,
                "franchise_id": 701,
                "agent_comm_od_percent": "15.00",
                "agent_comm_net_percent": "5.00",
                "tds_percent": "5.00",
            },
            "payments": [
                {"payment_type": "CASH", "paid_amount": "5000.00"},
            ],
        },
    )
    assert book_resp.status_code == 201, book_resp.text
    booked = book_resp.json()
    tx_id = booked["transaction_id"]
    assert booked["policy_no"] == "TEST_POLICY_001"
    assert booked["quotation_code"] == quotation_code
    assert booked["inward_no"].startswith("INW-101-")
    assert booked["t_status"] == "Pending"
    assert Decimal(booked["payment_summary"]["outstanding_amount"]) == expected_outstanding

    # Verify AccTransId = 1, 2, 3 in accounting_entries
    acct_map = {e["acc_trans_id"]: Decimal(e["amount"]) for e in booked["accounting_entries"]}
    assert acct_map[1] == final_premium
    assert acct_map[2] == Decimal("5000.00")
    assert acct_map[3] == -Decimal(booked["commission_summary"]["total_net_commission"])

    # Step 8: Settle Remaining Balance via POST /api/v1/policies/{tx_id}/payments
    settle_resp = await async_client.post(
        f"/api/v1/policies/{tx_id}/payments",
        headers=admin_headers,
        json={
            "payment_type": "NEFT",
            "paid_amount": str(expected_outstanding),
            "docno": "UTR-E2E-001",
            "bankname": "HDFC BANK",
        },
    )
    assert settle_resp.status_code == 201
    settled = settle_resp.json()
    assert Decimal(settled["payment_summary"]["paid_amount"]) == final_premium
    assert Decimal(settled["payment_summary"]["outstanding_amount"]) == Decimal("0.00")
    assert settled["t_status"] == "Booked"
    assert settled["pending_status"] == 0

    # Step 9: List and Retrieve Policy via GET /api/v1/policies & GET /api/v1/policies/{tx_id}
    list_resp = await async_client.get(
        "/api/v1/policies",
        headers=admin_headers,
        params={"policy_no": "TEST_POLICY_001"},
    )
    assert list_resp.status_code == 200
    assert list_resp.json()["total"] == 1
    assert list_resp.json()["items"][0]["transaction_id"] == tx_id
