"""
Phase 8 End-to-End (E2E) Cross-Phase Lifecycle Verification Suite:
TEST_CUSTOMER_001 -> TEST_VEHICLE_001 -> TEST_QUOTATION_001 -> TEST_POLICY_001
-> INITIAL PAYMENT -> SECOND PAYMENT -> CHEQUE -> DEPOSIT -> BOUNCE (+ PENALTY)
-> REPLACEMENT CHEQUE -> CLEARANCE -> WALLET LOCK/DEBIT -> COMMISSION
-> INSURER RECONCILIATION -> FINAL ACCOUNTING STATE.
"""
from decimal import Decimal
import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from tests.integration.test_phase7_policy_booking_api import create_user_with_role


@pytest.fixture(autouse=True)
async def cleanup_phase8_e2e_tables(db_session: AsyncSession):
    for tbl in (
        "tbl_account",
        "tbl_transactionpayment",
        "tbl_franchisecommission",
        "tbl_agentcommissionpayment",
        "tbl_cutnpaycommpayable",
        "tbl_transaction",
        "tbl_transactionappnew",
        "tbl_ledgermaster",
        "tbl_insurancecompanyquotation",
        "tbl_app_quotationremark",
        "tbl_app_quotationrequest",
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
        "tbl_ledgermaster",
        "tbl_insurancecompanyquotation",
        "tbl_app_quotationremark",
        "tbl_app_quotationrequest",
        "tbl_app_quatationentry",
    ):
        await db_session.execute(text(f"DELETE FROM {tbl};"))
    await db_session.commit()


@pytest.mark.asyncio
async def test_phase8_complete_cross_phase_e2e_journey(
    async_client: AsyncClient,
    db_session: AsyncSession,
):
    """
    Executes the full cross-phase lifecycle through FastAPI endpoints:
    1. Create TEST_CUSTOMER_001 (Phase 5)
    2. Create TEST_VEHICLE_001 (Phase 5)
    3. Create Self-Quotation TEST_QUOTATION_001 (Phase 6)
    4. Top-up Partner Agent E-Wallet & Reserve Wallet Lock (Phase 8)
    5. Create & Approve Staged Policy Proposal (Phase 7)
    6. Book TEST_POLICY_001 with E-Wallet Lock Consumption + Partial Cash + Cheque (Phase 7/8)
    7. Record Second UPI Payment to settle initial balance (Phase 8)
    8. Deposit Cheque -> Bounce Cheque with 500.00 Dishonor Penalty -> Reopen Policy & Hold Commission (Phase 8)
    9. Record Replacement Cheque (Cheque + Penalty) -> Clear Replacement Cheque -> Finalize Policy (Phase 8)
    10. Execute Insurer Payment & Brokerage Reconciliation -> Verify Final Accounting State (Phase 8)
    """
    _, admin_headers = await create_user_with_role(db_session, role_name="ADMIN", branch_id=101)
    _, cashier_headers = await create_user_with_role(db_session, role_name="CASHIER", branch_id=101)
    _, account_headers = await create_user_with_role(db_session, role_name="ACCOUNT", branch_id=101)
    _, agent_headers = await create_user_with_role(
        db_session, role_name="AGENT", branch_id=101, partner_user_id=888
    )

    # ------------------------------------------------------------------------
    # Step 1: Create TEST_CUSTOMER_001 via POST /api/v1/customers
    # ------------------------------------------------------------------------
    cust_resp = await async_client.post(
        "/api/v1/customers",
        headers=admin_headers,
        json={
            "initial": "MR.",
            "CustFName": "TEST_CUSTOMER_001",
            "CustMName": "SYNTHETIC",
            "CustLName": "PHASE8_E2E",
            "CustomerType": "INDIVIDUAL",
            "MoblieNo1": "9876588801",
            "EMailId": "test_customer_001_p8@example.local",
            "BranchId": 101,
        },
    )
    assert cust_resp.status_code == 201, cust_resp.text
    customer_id = cust_resp.json()["customer_id"]

    # ------------------------------------------------------------------------
    # Step 2: Create TEST_VEHICLE_001 via POST /api/v1/customers/{customer_id}/vehicles
    # ------------------------------------------------------------------------
    veh_resp = await async_client.post(
        f"/api/v1/customers/{customer_id}/vehicles",
        headers=admin_headers,
        json={
            "financial_year": "2026-2027",
            "registration_no": "MH12P8E2E01",
            "chaise_no": "SYNTHCHASSISP80001",
            "engine_no": "SYNTHENGINEP80001",
            "mfg_year": "2024",
            "seats_capacity": "5",
            "engine_power": "1197",
            "vehicle_weight": "1050",
            "vehicle_variant": "ZXI+",
        },
    )
    assert veh_resp.status_code == 201, veh_resp.text
    cust_veh_id = veh_resp.json()["cust_veh_id"]

    # ------------------------------------------------------------------------
    # Step 3: Create Self-Quotation TEST_QUOTATION_001 via POST /api/v1/quotations/self
    # ------------------------------------------------------------------------
    quot_resp = await async_client.post(
        "/api/v1/quotations/self",
        headers=agent_headers,
        json={
            "title": "TEST_QUOTATION_001",
            "registration_no": "MH12P8E2E01",
            "agent_id": 888,
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
    q_data = quot_resp.json()
    quotation_id = q_data["quatation_id"]
    quotation_code = q_data["quatation_code"]

    prefill_resp = await async_client.get(
        f"/api/v1/quotations/self/{quotation_id}/policy-prefill",
        headers=agent_headers,
    )
    assert prefill_resp.status_code == 200, prefill_resp.text
    prefill = prefill_resp.json()
    final_premium = Decimal(prefill["final_premium"])
    od_premium = Decimal(prefill["od_premium"])
    tp_premium = Decimal(prefill["tp_premium"])
    net_premium = Decimal(prefill["net_premium"])

    # ------------------------------------------------------------------------
    # Step 4: Top-Up Partner Agent #888 E-Wallet (15,000.00) & Lock 3,000.00
    # ------------------------------------------------------------------------
    topup_resp = await async_client.post(
        "/api/v1/wallets/topup",
        headers=cashier_headers,
        json={
            "owner_type": "AGENT",
            "owner_id": 888,
            "amount": "15000.00",
            "payment_mode": "NEFT",
            "doc_no": "NEFT-E2E-888",
        },
    )
    assert topup_resp.status_code == 201
    assert Decimal(topup_resp.json()["wallet"]["available_balance"]) == Decimal("15000.00")

    # ------------------------------------------------------------------------
    # Step 5: Create Staged Proposal & Lock 3,000.00 Wallet Funds
    # ------------------------------------------------------------------------
    prop_resp = await async_client.post(
        "/api/v1/policies/proposals",
        headers=agent_headers,
        json={
            "quotation_id": quotation_id,
            "quotation_source_type": "SELF_QUOTATION",
            "customer_name": "TEST_CUSTOMER_001 PHASE8_E2E",
            "contact_no": "9876588801",
            "registration_no": "MH12P8E2E01",
            "insurance_company_id": 1,
            "od_premium": str(od_premium),
            "tp_premium": str(tp_premium),
            "net_premium": str(net_premium),
            "final_premium": str(final_premium),
            "cash_paid_amount": "4000.00",
            "ewallet_used_amount": "3000.00",
        },
    )
    assert prop_resp.status_code == 201
    proposal_trans_id = prop_resp.json()["trans_id"]

    lock_resp = await async_client.post(
        "/api/v1/wallets/lock",
        headers=agent_headers,
        json={
            "owner_type": "AGENT",
            "owner_id": 888,
            "amount": "3000.00",
            "proposal_trans_id": proposal_trans_id,
            "quotation_code": quotation_code,
        },
    )
    assert lock_resp.status_code == 201
    lock_id = lock_resp.json()["ledger_entry"]["account_id"]
    assert Decimal(lock_resp.json()["wallet"]["locked_balance"]) == Decimal("3000.00")
    assert Decimal(lock_resp.json()["wallet"]["available_balance"]) == Decimal("12000.00")

    # Cashier & Accountant approve proposal
    await async_client.post(
        f"/api/v1/policies/proposals/{proposal_trans_id}/approve",
        headers=cashier_headers,
        json={"stage": "CASHIER", "approved": True},
    )
    await async_client.post(
        f"/api/v1/policies/proposals/{proposal_trans_id}/approve",
        headers=account_headers,
        json={"stage": "ACCOUNTANT", "approved": True},
    )

    # ------------------------------------------------------------------------
    # Step 6: Book TEST_POLICY_001 with E-Wallet Lock (3,000) + Cash (4,000) + Cheque (5,000)
    # ------------------------------------------------------------------------
    initial_collected = Decimal("3000.00") + Decimal("4000.00") + Decimal("5000.00")
    remaining_after_book = final_premium - initial_collected

    book_resp = await async_client.post(
        "/api/v1/policies/book",
        headers=admin_headers,
        json={
            "customer_id": customer_id,
            "cust_veh_id": cust_veh_id,
            "quotation_id": quotation_id,
            "quotation_source_type": "SELF_QUOTATION",
            "proposal_trans_id": proposal_trans_id,
            "policy_no": "TEST_POLICY_001_P8_E2E",
            "vehicle_category": "PVT",
            "ewallet_amount_used": "3000.00",
            "wallet_owner_type": "AGENT",
            "wallet_owner_id": 888,
            "wallet_lock_id": lock_id,
            "commission": {
                "agent_id": 888,
                "franchise_id": 401,
                "agent_comm_od_percent": "15.00",
                "agent_comm_net_percent": "5.00",
                "franchise_comm_od_percent": "18.00",
                "tds_percent": "5.00",
            },
            "payments": [
                {"payment_type": "CASH", "paid_amount": "4000.00", "docno": "CASH-E2E-01"},
                {
                    "payment_type": "CHEQUE",
                    "paid_amount": "5000.00",
                    "docno": "CHQ-E2E-001",
                    "bankname": "HDFC BANK",
                },
            ],
        },
    )
    assert book_resp.status_code == 201
    b_body = book_resp.json()
    tx_id = b_body["transaction_id"]
    chq_payment_id = b_body["payment_summary"]["payments"][1]["payment_id"]
    assert Decimal(b_body["payment_summary"]["paid_amount"]) == initial_collected
    assert Decimal(b_body["payment_summary"]["outstanding_amount"]) == remaining_after_book
    assert b_body["t_status"] == "Pending"

    # Verify E-Wallet lock was consumed: settled = 12,000.00, locked = 0.00, available = 12,000.00
    w_after_book = await async_client.get("/api/v1/wallets/AGENT/888", headers=agent_headers)
    assert Decimal(w_after_book.json()["settled_balance"]) == Decimal("12000.00")
    assert Decimal(w_after_book.json()["locked_balance"]) == Decimal("0.00")
    assert Decimal(w_after_book.json()["available_balance"]) == Decimal("12000.00")

    # ------------------------------------------------------------------------
    # Step 7: Record Second UPI Payment for remaining_after_book
    # ------------------------------------------------------------------------
    upi_resp = await async_client.post(
        f"/api/v1/policies/{tx_id}/payments",
        headers=cashier_headers,
        json={
            "payment_type": "UPI",
            "paid_amount": str(remaining_after_book),
            "docno": "UPI-E2E-002",
        },
    )
    assert upi_resp.status_code == 201
    assert Decimal(upi_resp.json()["payment_summary"]["outstanding_amount"]) == Decimal("0.00")

    # ------------------------------------------------------------------------
    # Step 8: Deposit Cheque -> Bounce Cheque with 500.00 Penalty -> Reopen Policy
    # ------------------------------------------------------------------------
    dep_resp = await async_client.post(
        f"/api/v1/payments/{chq_payment_id}/deposit",
        headers=cashier_headers,
        json={"bank_reference": "DEP-E2E-001"},
    )
    assert dep_resp.status_code == 200
    assert dep_resp.json()["status"] == "DEPOSITED"

    bnc_resp = await async_client.post(
        f"/api/v1/payments/{chq_payment_id}/bounce",
        headers=account_headers,
        json={
            "bounce_reason": "Drawer Signature Differs",
            "penalty_amount": "500.00",
            "bank_reference": "RET-E2E-001",
        },
    )
    assert bnc_resp.status_code == 200
    bnc_data = bnc_resp.json()
    assert bnc_data["status"] == "BOUNCED"
    assert Decimal(bnc_data["policy_outstanding_amount"]) == Decimal("5500.00")  # 5000 + 500 penalty
    assert bnc_data["policy_t_status"] == "Pending"
    assert bnc_data["cheque_bank_status"] == 2
    assert bnc_data["commission_paid"] == 0

    # ------------------------------------------------------------------------
    # Step 9: Record Replacement Cheque (5,500.00) & Clear Replacement Cheque
    # ------------------------------------------------------------------------
    rep_chq_resp = await async_client.post(
        f"/api/v1/policies/{tx_id}/payments",
        headers=cashier_headers,
        json={
            "payment_type": "CHEQUE",
            "paid_amount": "5500.00",
            "docno": "CHQ-E2E-REPLACEMENT-002",
            "bankname": "SBI",
        },
    )
    assert rep_chq_resp.status_code == 201
    rep_chq_id = rep_chq_resp.json()["payment_summary"]["payments"][-1]["payment_id"]

    clr_resp = await async_client.post(
        f"/api/v1/payments/{rep_chq_id}/clear",
        headers=account_headers,
        json={"bank_reference": "CLR-E2E-002", "remark": "Replacement cheque cleared"},
    )
    assert clr_resp.status_code == 200
    clr_data = clr_resp.json()
    assert clr_data["status"] == "CLEARED"
    assert clr_data["is_cheque_clearing"] == 0
    assert clr_data["is_cheque_cleared"] == 1
    assert clr_data["cheque_bank_status"] == 1
    assert clr_data["policy_t_status"] == "Booked"
    assert Decimal(clr_data["policy_outstanding_amount"]) == Decimal("0.00")

    # ------------------------------------------------------------------------
    # Step 10: Reconcile Insurer Brokerage Statement & Verify Final Accounting State
    # ------------------------------------------------------------------------
    booked_gross_comm = Decimal(b_body["commission_summary"]["total_gross_commission"])
    rcon_resp = await async_client.post(
        f"/api/v1/reconciliation/policies/{tx_id}/match",
        headers=account_headers,
        json={
            "reconciled_comm_amount": str(booked_gross_comm),
            "company_submission_doc_no": "INS-SUB-E2E-001",
            "company_cheque_no": "INS-CHQ-888",
            "is_company_cheque": True,
            "ib_doc_no": 9001,
            "ib_receipt_status": 1,
        },
    )
    assert rcon_resp.status_code == 200
    rcon_data = rcon_resp.json()
    assert rcon_data["is_rcon_data_match"] == 1
    assert rcon_data["match_status"] == "MATCHED"
    assert Decimal(rcon_data["commission_variance"]) == Decimal("0.00")
    assert rcon_data["accounting_entry"]["acc_trans_id"] == 5

    # Verify full payment history on the policy includes 4 instruments (3 active + 1 bounced)
    pay_hist = await async_client.get(
        f"/api/v1/policies/{tx_id}/payments?include_deleted=true",
        headers=admin_headers,
    )
    assert pay_hist.status_code == 200
    assert pay_hist.json()["total"] == 4
    statuses = [item["status"] for item in pay_hist.json()["items"]]
    assert "BOUNCED" in statuses
    assert "CLEARED" in statuses
    assert statuses.count("RECEIVED") == 2
