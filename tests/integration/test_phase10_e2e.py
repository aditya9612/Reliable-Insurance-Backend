"""
Phase 10 Cross-Phase End-to-End (E2E) Integration Test (Phases 5 -> 6 -> 7 -> 8 -> 9 -> 10).

Executes TWO mandatory E2E journeys against local synthetic data:
1. Full Lifecycle Journey:
   TEST_CUSTOMER_001
   -> TEST_VEHICLE_001
   -> TEST_QUOTATION_001
   -> TEST_POLICY_001
   -> PAYMENT & CLEARANCE (Phase 8)
   -> COMMISSION EVALUATION, APPROVAL & PAYOUT (Phase 9)
   -> TEST_CLAIM_001 -> REGISTER -> SURVEY -> ASSESS -> APPROVE -> SETTLE -> CLOSE (Phase 10)
   -> TEST_ENDORSEMENT_001 -> PREMIUM RECALC -> REFUND APPROVAL & DISBURSEMENT -> COMMISSION RECOVERY -> ACCOUNTING -> TRIAL BALANCE
2. Endorsement-Only Journey:
   Upward Financial Endorsement -> Additional Premium Receivable -> Payment Collection -> Commission Delta -> Trial Balance
"""
from datetime import datetime, timedelta
from decimal import Decimal
import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from tests.integration.test_phase7_policy_booking_api import create_user_with_role


@pytest.fixture(autouse=True)
async def cleanup_phase10_e2e_tables(db_session: AsyncSession):
    for tbl in (
        "tbl_claimdocument",
        "tbl_claims",
        "tbl_appendorsement",
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
        "tbl_vehicledetails",
        "tbl_customer",
    ):
        await db_session.execute(text(f"DELETE FROM {tbl};"))
    await db_session.commit()
    yield
    for tbl in (
        "tbl_claimdocument",
        "tbl_claims",
        "tbl_appendorsement",
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
        "tbl_vehicledetails",
        "tbl_customer",
    ):
        await db_session.execute(text(f"DELETE FROM {tbl};"))
    await db_session.commit()


@pytest.mark.asyncio
async def test_phase10_full_cross_phase_e2e_and_endorsement_only_journeys(
    async_client: AsyncClient,
    db_session: AsyncSession,
):
    _, admin_headers = await create_user_with_role(db_session, role_name="ADMIN", branch_id=101)
    _, op_headers = await create_user_with_role(db_session, role_name="OPERATOR", branch_id=101)
    _, acc_headers = await create_user_with_role(db_session, role_name="ACCOUNT HEAD", branch_id=101)
    _, agent_headers = await create_user_with_role(
        db_session, role_name="AGENT", branch_id=101, partner_user_id=501
    )

    # -----------------------------------------------------------------------
    # Step 1 & 2: Create TEST_CUSTOMER_001 & TEST_VEHICLE_001 (Phase 5)
    # -----------------------------------------------------------------------
    cust_resp = await async_client.post(
        "/api/v1/customers",
        headers=admin_headers,
        json={
            "initial": "MR.",
            "CustFName": "TEST_CUSTOMER_001",
            "CustMName": "SYNTHETIC",
            "CustLName": "PHASE10_E2E",
            "CustomerType": "INDIVIDUAL",
            "MoblieNo1": "9898001001",
            "EMailId": "test_customer_001_p10@example.local",
            "BranchId": 101,
        },
    )
    assert cust_resp.status_code == 201, cust_resp.text
    customer_id = cust_resp.json()["customer_id"]

    veh_resp = await async_client.post(
        f"/api/v1/customers/{customer_id}/vehicles",
        headers=admin_headers,
        json={
            "financial_year": "2026-2027",
            "registration_no": "MH01P10001",
            "chaise_no": "SYNTHCHASSISP10001",
            "engine_no": "SYNTHENGINEP10001",
            "mfg_year": "2025",
            "seats_capacity": "5",
            "engine_power": "1197",
            "vehicle_weight": "1050",
            "vehicle_variant": "ZXI+",
        },
    )
    assert veh_resp.status_code == 201, veh_resp.text
    cust_veh_id = veh_resp.json()["cust_veh_id"]

    # -----------------------------------------------------------------------
    # Step 3: Create Self-Quotation TEST_QUOTATION_001 (Phase 6)
    # -----------------------------------------------------------------------
    quot_resp = await async_client.post(
        "/api/v1/quotations/self",
        headers=agent_headers,
        json={
            "title": "TEST_QUOTATION_001",
            "registration_no": "MH01P10001",
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
                "vehicle_age_override": "1.0",
                "base_idv_override": "500000",
                "selected_idv": "500000",
                "ncb_percent": "20",
                "od_discount_override": "0",
                "pa_to_owner_driver": True,
                "ll_paid_driver_count": 1,
            },
        },
    )
    assert quot_resp.status_code == 201, quot_resp.text

    # -----------------------------------------------------------------------
    # Step 4: Book Policy TEST_POLICY_001 with CHEQUE + Clear & Reconcile (Phases 7 & 8)
    # -----------------------------------------------------------------------
    now_dt = datetime.utcnow()
    book_resp = await async_client.post(
        "/api/v1/policies/book",
        headers=op_headers,
        json={
            "customer_id": customer_id,
            "cust_veh_id": cust_veh_id,
            "policy_no": "TEST_POLICY_001_E2E_P10",
            "vehicle_category": "PVT",
            "sum_insured_idv": "500000.00",
            "od_premium": "10000.00",
            "tp_premium": "5000.00",
            "ncb_percent": "20.00",
            "risk_start_date": (now_dt - timedelta(days=20)).strftime("%Y-%m-%d"),
            "expiry_date": (now_dt + timedelta(days=345)).strftime("%Y-%m-%d"),
            "commission": {
                "agent_id": 501,
                "agent_comm_od_percent": "15.00",
                "tds_percent": "5.00",
                "franchise_id": 601,
                "franchise_comm_od_percent": "15.00",
            },
            "payments": [
                {
                    "payment_type": "CHEQUE",
                    "paid_amount": "17700.00",
                    "docno": "CHQ100999",
                    "bankname": "HDFC BANK",
                }
            ],
        },
    )
    assert book_resp.status_code == 201, book_resp.text
    tx_id = book_resp.json()["transaction_id"]
    payment_id = book_resp.json()["payment_summary"]["payments"][0]["payment_id"]

    # Deposit & Clear Cheque + Reconcile Insurer Brokerage (Phase 8)
    dep_resp = await async_client.post(
        f"/api/v1/payments/{payment_id}/deposit",
        headers=acc_headers,
        json={"bank_reference": "DEP-100999"},
    )
    assert dep_resp.status_code == 200

    clr_resp = await async_client.post(
        f"/api/v1/payments/{payment_id}/clear",
        headers=acc_headers,
        json={"bank_reference": "CLR-100999"},
    )
    assert clr_resp.status_code == 200

    rcon_resp = await async_client.post(
        f"/api/v1/reconciliation/policies/{tx_id}/match",
        headers=acc_headers,
        json={
            "reconciled_comm_amount": "1500.00",
            "company_submission_doc_no": "ICICI-RCON-P10",
            "company_cheque_no": "ICICI-CHQ-P10",
            "is_company_cheque": True,
            "ib_doc_no": 9010,
            "ib_receipt_status": 1,
        },
    )
    assert rcon_resp.status_code == 200

    # -----------------------------------------------------------------------
    # Step 5: Approve & Disburse Agent Commission (Phase 9)
    # -----------------------------------------------------------------------
    app_comm_resp = await async_client.post(
        f"/api/v1/commissions/{tx_id}/approve",
        headers=acc_headers,
        json={"partner_type": "BOTH", "remark": "Approve commission for TEST_POLICY_001"},
    )
    assert app_comm_resp.status_code == 200, app_comm_resp.text

    payout_resp = await async_client.post(
        "/api/v1/commission-payouts",
        headers=acc_headers,
        json={
            "partner_type": "AGENT",
            "partner_id": 501,
            "payment_mode": "NEFT",
            "transaction_ids": [tx_id],
            "bank_reference": "UTR-P10-COMM-001",
            "narration": "Agent commission payout before endorsement",
        },
    )
    assert payout_resp.status_code == 201, payout_resp.text
    assert Decimal(payout_resp.json()["total_payout_amount"]) == Decimal("1425.00")

    # -----------------------------------------------------------------------
    # Step 6: TEST_CLAIM_001 Intimation -> Survey -> Assess -> Approve -> Settle -> Close (Phase 10)
    # -----------------------------------------------------------------------
    clm_resp = await async_client.post(
        "/api/v1/claims",
        headers=admin_headers,
        json={
            "transaction_id": tx_id,
            "claim_type": "OD",
            "loss_date": (now_dt - timedelta(days=5)).isoformat(),
            "loss_location": "Mumbai Western Express Highway",
            "loss_description": "TEST_CLAIM_001 bumper and headlamp damage",
            "estimated_amount": "45000.00",
            "insurer_claim_ref": "TEST_CLAIM_001",
        },
    )
    assert clm_resp.status_code == 201, clm_resp.text
    claim_id = clm_resp.json()["data"]["claim_id"]

    await async_client.post(
        f"/api/v1/claims/{claim_id}/register",
        headers=admin_headers,
        json={"insurer_claim_ref": "TEST_CLAIM_001"},
    )
    await async_client.post(
        f"/api/v1/claims/{claim_id}/survey",
        headers=admin_headers,
        json={
            "surveyor_name": "Vikram Mehta",
            "surveyor_license_no": "SLA-10001",
        },
    )
    assess_resp = await async_client.post(
        f"/api/v1/claims/{claim_id}/assess",
        headers=admin_headers,
        json={
            "assessed_loss_amount": "45000.00",
            "depreciation_amount": "5000.00",
            "deductible_amount": "1000.00",
            "excess_amount": "500.00",
            "salvage_amount": "1500.00",
        },
    )
    assert assess_resp.status_code == 200
    assert Decimal(assess_resp.json()["data"]["approved_amount"]) == Decimal("37000.00")

    await async_client.post(
        f"/api/v1/claims/{claim_id}/approve",
        headers=acc_headers,
        json={"remarks": "Approved TEST_CLAIM_001"},
    )
    settle_resp = await async_client.post(
        f"/api/v1/claims/{claim_id}/settle",
        headers=acc_headers,
        json={
            "settled_amount": "37000.00",
            "payee_type": "CUSTOMER",
            "payment_mode": "NEFT",
            "payment_doc_no": "UTR-TEST-CLAIM-001",
        },
    )
    assert settle_resp.status_code == 200
    assert settle_resp.json()["data"]["claim_status"] == "SETTLED"

    close_resp = await async_client.post(
        f"/api/v1/claims/{claim_id}/close",
        headers=acc_headers,
        json={"remarks": "TEST_CLAIM_001 settled and closed"},
    )
    assert close_resp.status_code == 200
    assert close_resp.json()["data"]["claim_status"] == "CLOSED"

    # -----------------------------------------------------------------------
    # Step 7: TEST_ENDORSEMENT_001 Downward IDV -> Refund -> Commission Recovery (Phase 10)
    # -----------------------------------------------------------------------
    end_resp = await async_client.post(
        "/api/v1/endorsements",
        headers=admin_headers,
        json={
            "transaction_id": tx_id,
            "endorsement_type": "IDV_CHANGE",
            "field_changes": {"SumInsured": "400000.00"},
            "remarks": "TEST_ENDORSEMENT_001 downward IDV adjustment",
        },
    )
    assert end_resp.status_code == 201, end_resp.text
    end_id = end_resp.json()["data"]["endorsement_id"]

    await async_client.post(
        f"/api/v1/endorsements/{end_id}/approve",
        headers=admin_headers,
        json={"remarks": "Approve TEST_ENDORSEMENT_001"},
    )
    apply_resp = await async_client.post(
        f"/api/v1/endorsements/{end_id}/apply",
        headers=admin_headers,
        json={"remarks": "Apply TEST_ENDORSEMENT_001"},
    )
    assert apply_resp.status_code == 200, apply_resp.text
    app_data = apply_resp.json()["data"]
    assert app_data["endorsement_status"] == "APPLIED"
    assert Decimal(app_data["premium_delta"]) == Decimal("-2360.00")
    assert Decimal(app_data["refund_amount"]) == Decimal("2360.00")
    assert app_data["refund_status"] == "PENDING_APPROVAL"
    assert Decimal(app_data["commission_recovery_amount"]) == Decimal("285.00")

    # Approve and disburse customer refund
    await async_client.post(
        f"/api/v1/refunds/{end_id}/approve",
        headers=acc_headers,
        json={"remarks": "Approve refund for TEST_ENDORSEMENT_001"},
    )
    disb_resp = await async_client.post(
        f"/api/v1/refunds/{end_id}/disburse",
        headers=acc_headers,
        json={
            "refund_mode": "NEFT",
            "refund_doc_no": "UTR-REF-TEST-END-001",
            "remarks": "Disburse refund for TEST_ENDORSEMENT_001",
        },
    )
    assert disb_resp.status_code == 200
    assert disb_resp.json()["data"]["refund_status"] == "REFUNDED"

    # -----------------------------------------------------------------------
    # Step 8: Journey 2 (Endorsement-Only Upward Modification & Additional Premium)
    # -----------------------------------------------------------------------
    end2_resp = await async_client.post(
        "/api/v1/endorsements",
        headers=admin_headers,
        json={
            "transaction_id": tx_id,
            "endorsement_type": "COVERAGE_ADDON_CHANGE",
            "field_changes": {"AddOn": "1000.00"},
            "remarks": "Add Zero Dep AddOn",
        },
    )
    assert end2_resp.status_code == 201
    end2_id = end2_resp.json()["data"]["endorsement_id"]
    await async_client.post(f"/api/v1/endorsements/{end2_id}/approve", headers=admin_headers, json={})
    apply2_resp = await async_client.post(f"/api/v1/endorsements/{end2_id}/apply", headers=admin_headers, json={})
    assert apply2_resp.status_code == 200
    assert Decimal(apply2_resp.json()["data"]["premium_delta"]) == Decimal("1180.00")

    # -----------------------------------------------------------------------
    # Step 9: Verify Trial Balance Zero Variance Across All Phases (Phases 7-10)
    # -----------------------------------------------------------------------
    tb_resp = await async_client.get("/api/v1/accounting/trial-balance", headers=acc_headers)
    assert tb_resp.status_code == 200, tb_resp.text
    tb_data = tb_resp.json()
    assert tb_data["is_balanced"] is True
    assert Decimal(tb_data["variance"]) == Decimal("0.00")
    assert Decimal(tb_data["total_gross_debit"]) == Decimal(tb_data["total_gross_credit"])
    assert Decimal(tb_data["total_net_debit"]) == Decimal(tb_data["total_net_credit"])
