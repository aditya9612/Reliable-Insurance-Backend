"""
Phase 9 Cross-Phase End-to-End (E2E) Integration Test (Phases 5 -> 6 -> 7 -> 8 -> 9).

Executes the complete synthetic business journey:
TEST_CUSTOMER_001
  -> TEST_VEHICLE_001
  -> TEST_QUOTATION_001
  -> TEST_POLICY_001 (with Agent #501, Franchise #601, TDS 5%, Partial Cut & Pay, and CHEQUE Payment)
  -> CHEQUE DEPOSIT & CLEARANCE (releasing commission payout eligibility)
  -> INSURER PAYMENT & BROKERAGE RECONCILIATION
  -> COMMISSION PAYABLE QUEUE & APPROVAL
  -> AGENT & FRANCHISE COMMISSION PAYOUT (`TEST_PAYOUT_001`)
  -> MASTER LEDGERS (`TEST_LEDGER_001`) & DOUBLE-ENTRY VOUCHER (`TEST_VOUCHER_001`)
  -> LEDGER STATEMENT RUNNING BALANCE
  -> TRIAL BALANCE ZERO-VARIANCE VERIFICATION
  -> PAYOUT REVERSAL & RE-PAYOUT -> FINAL BALANCES
"""
from decimal import Decimal
import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from tests.integration.test_phase7_policy_booking_api import create_user_with_role


@pytest.fixture(autouse=True)
async def cleanup_phase9_e2e_tables(db_session: AsyncSession):
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
async def test_phase9_full_cross_phase_e2e_journey(
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
            "CustLName": "PHASE9_E2E",
            "CustomerType": "INDIVIDUAL",
            "MoblieNo1": "9898000901",
            "EMailId": "test_customer_001_p9@example.local",
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
            "registration_no": "MH01P90001",
            "chaise_no": "SYNTHCHASSISP90001",
            "engine_no": "SYNTHENGINEP90001",
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
            "registration_no": "MH01P90001",
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
                "ncb_percent": "0",
                "od_discount_override": "0",
                "pa_to_owner_driver": True,
                "ll_paid_driver_count": 1,
            },
        },
    )
    assert quot_resp.status_code == 201, quot_resp.text
    quotation_id = quot_resp.json()["quatation_id"]

    prefill_resp = await async_client.get(
        f"/api/v1/quotations/self/{quotation_id}/policy-prefill",
        headers=agent_headers,
    )
    assert prefill_resp.status_code == 200, prefill_resp.text

    # -----------------------------------------------------------------------
    # Step 4: Preview Commission & TDS (`POST /api/v1/commissions/preview`)
    # -----------------------------------------------------------------------
    prev_resp = await async_client.post(
        "/api/v1/commissions/preview",
        headers=op_headers,
        json={
            "od_premium": "10000.00",
            "tp_premium": "5000.00",
            "agent_id": 501,
            "agent_comm_od_pct": "10.00",
            "agent_tds_pct": "5.00",
            "franchise_id": 601,
            "franchise_comm_od_pct": "15.00",
            "franchise_tds_pct": "5.00",
            "cutnpay_enabled": True,
            "cutnpay_amount": "350.00",
        },
    )
    assert prev_resp.status_code == 200
    prev = prev_resp.json()
    assert Decimal(prev["agent_net_commission"]) == Decimal("950.00")
    assert Decimal(prev["agent_remaining_payable_amount"]) == Decimal("600.00")
    assert Decimal(prev["franchise_net_commission"]) == Decimal("1425.00")
    assert Decimal(prev["profit_of_net_commission"]) == Decimal("475.00")
    req_payable = prev["customer_required_payable_amount"]

    # -----------------------------------------------------------------------
    # Step 5: Book TEST_POLICY_001 with CHEQUE + Partial Cut & Pay (Phase 7)
    # -----------------------------------------------------------------------
    book_resp = await async_client.post(
        "/api/v1/policies/book",
        headers=op_headers,
        json={
            "customer_id": customer_id,
            "cust_veh_id": cust_veh_id,
            "policy_no": "TEST_POLICY_001_E2E_P9",
            "vehicle_category": "PVT",
            "od_premium": "10000.00",
            "tp_premium": "5000.00",
            "commission": {
                "agent_id": 501,
                "agent_comm_od_percent": "10.00",
                "tds_percent": "5.00",
                "franchise_id": 601,
                "franchise_comm_od_percent": "15.00",
            },
            "cutnpay_enabled": True,
            "cutnpay_amount": "350.00",
            "payments": [
                {
                    "payment_type": "CHEQUE",
                    "paid_amount": req_payable,
                    "docno": "CHQ501999",
                    "bankname": "HDFC BANK",
                }
            ],
        },
    )
    assert book_resp.status_code == 201, book_resp.text
    tx_id = book_resp.json()["transaction_id"]
    payment_id = book_resp.json()["payment_summary"]["payments"][0]["payment_id"]

    # -----------------------------------------------------------------------
    # Step 6: Verify Commission Payable is blocked while Cheque is Pending Clearance
    # -----------------------------------------------------------------------
    comm_pre = (await async_client.get(f"/api/v1/commissions/{tx_id}", headers=agent_headers)).json()
    assert comm_pre["is_payout_eligible"] is False
    assert "Ischequeclearing=1" in comm_pre["eligibility_reason"]

    # -----------------------------------------------------------------------
    # Step 7: Deposit & Clear Cheque + Reconcile Insurer Brokerage (Phase 8)
    # -----------------------------------------------------------------------
    dep_resp = await async_client.post(
        f"/api/v1/payments/{payment_id}/deposit",
        headers=acc_headers,
        json={"bank_reference": "DEP-501999"},
    )
    assert dep_resp.status_code == 200

    clr_resp = await async_client.post(
        f"/api/v1/payments/{payment_id}/clear",
        headers=acc_headers,
        json={"bank_reference": "CLR-501999"},
    )
    assert clr_resp.status_code == 200

    rcon_resp = await async_client.post(
        f"/api/v1/reconciliation/policies/{tx_id}/match",
        headers=acc_headers,
        json={
            "reconciled_comm_amount": "1000.00",
            "company_submission_doc_no": "ICICI-RCON-001",
            "company_cheque_no": "ICICI-CHQ-001",
            "is_company_cheque": True,
            "ib_doc_no": 9001,
            "ib_receipt_status": 1,
        },
    )
    assert rcon_resp.status_code == 200

    # -----------------------------------------------------------------------
    # Step 8: Verify Commission Payable Queue & Approve Commission (Phase 9)
    # -----------------------------------------------------------------------
    payables_resp = await async_client.get(
        "/api/v1/commissions/payables?only_eligible=true",
        headers=acc_headers,
    )
    assert payables_resp.status_code == 200
    p_list = payables_resp.json()
    assert p_list["total"] == 2  # 1 Agent payable (600.00) + 1 Franchise payable (1425.00)
    assert Decimal(p_list["eligible_payable_amount"]) == Decimal("2025.00")

    app_resp = await async_client.post(
        f"/api/v1/commissions/{tx_id}/approve",
        headers=acc_headers,
        json={"partner_type": "BOTH", "remark": "TEST_COMMISSION_001 Approved"},
    )
    assert app_resp.status_code == 200
    assert Decimal(app_resp.json()["agent_commission_row"]["payment_status"]) == Decimal("3.00")

    # -----------------------------------------------------------------------
    # Step 9: Disburse Agent & Franchise Commission Payouts (`TEST_PAYOUT_001`)
    # -----------------------------------------------------------------------
    ag_payout_resp = await async_client.post(
        "/api/v1/commission-payouts",
        headers=acc_headers,
        json={
            "partner_type": "AGENT",
            "partner_id": 501,
            "payment_mode": "NEFT",
            "transaction_ids": [tx_id],
            "bank_reference": "UTR-TEST-PAYOUT-001",
            "narration": "TEST_PAYOUT_001 Agent Disbursement",
            "idempotency_key": "IDEMP-TEST-PAYOUT-001",
        },
    )
    assert ag_payout_resp.status_code == 201
    ag_payout = ag_payout_resp.json()
    ag_payout_id = ag_payout["payout_id"]
    assert Decimal(ag_payout["total_payout_amount"]) == Decimal("600.00")

    frn_payout_resp = await async_client.post(
        "/api/v1/commission-payouts",
        headers=acc_headers,
        json={
            "partner_type": "FRANCHISE",
            "partner_id": 601,
            "payment_mode": "RTGS",
            "transaction_ids": [tx_id],
            "bank_reference": "UTR-TEST-PAYOUT-002",
            "narration": "TEST_PAYOUT_001 Franchise Disbursement",
        },
    )
    assert frn_payout_resp.status_code == 201
    assert Decimal(frn_payout_resp.json()["total_payout_amount"]) == Decimal("1425.00")
    assert frn_payout_resp.json()["allocations"][0]["commission_paid_flag"] == 1

    # -----------------------------------------------------------------------
    # Step 10: Create Master Ledgers (`TEST_LEDGER_001`) & Voucher (`TEST_VOUCHER_001`)
    # -----------------------------------------------------------------------
    l1 = (
        await async_client.post(
            "/api/v1/accounting/ledgers",
            headers=acc_headers,
            json={"ledger_name": "TEST_LEDGER_001_EXPENSE", "ledger_type_id": 4, "ledger_group_id": 40},
        )
    ).json()
    l2 = (
        await async_client.post(
            "/api/v1/accounting/ledgers",
            headers=acc_headers,
            json={"ledger_name": "TEST_LEDGER_001_BANK", "ledger_type_id": 1, "ledger_group_id": 10},
        )
    ).json()

    vch_resp = await async_client.post(
        "/api/v1/accounting/vouchers",
        headers=acc_headers,
        json={
            "voucher_type": "JOURNAL",
            "narration": "TEST_VOUCHER_001 Marketing Expense",
            "lines": [
                {"ledger_m_id": l1["ledger_m_id"], "dr_cr": "DR", "amount": "1500.00"},
                {"ledger_m_id": l2["ledger_m_id"], "dr_cr": "CR", "amount": "1500.00"},
            ],
        },
    )
    assert vch_resp.status_code == 201

    # Verify Running-Balance Ledger Statement for Agent #501 Commission Payable Ledger
    ag_payable_ledger_id = ag_payout["debit_ledger_m_id"]
    stmt_resp = await async_client.get(
        f"/api/v1/accounting/ledgers/{ag_payable_ledger_id}/entries",
        headers=acc_headers,
    )
    assert stmt_resp.status_code == 200
    assert Decimal(stmt_resp.json()["closing_balance"]) == Decimal("600.00")

    # -----------------------------------------------------------------------
    # Step 11: Reverse Agent Payout, Re-Disburse, and Verify Final Trial Balance
    # -----------------------------------------------------------------------
    rev_resp = await async_client.post(
        f"/api/v1/commission-payouts/{ag_payout_id}/reverse",
        headers=acc_headers,
        json={"reason": "E2E Reversal and Re-Disbursement Check"},
    )
    assert rev_resp.status_code == 200
    assert rev_resp.json()["status"] == "REVERSED"

    # Re-disburse the restored 600.00 Agent commission payable
    re_pay_resp = await async_client.post(
        "/api/v1/commission-payouts",
        headers=acc_headers,
        json={
            "partner_type": "AGENT",
            "partner_id": 501,
            "payment_mode": "UPI",
            "transaction_ids": [tx_id],
            "narration": "TEST_PAYOUT_001 Re-Disbursed",
        },
    )
    assert re_pay_resp.status_code == 201
    assert Decimal(re_pay_resp.json()["total_payout_amount"]) == Decimal("600.00")

    # Final Policy Commission State Check
    final_comm = (await async_client.get(f"/api/v1/commissions/{tx_id}", headers=acc_headers)).json()
    assert Decimal(final_comm["agent_remaining_payable"]) == Decimal("0.00")
    assert Decimal(final_comm["franchise_remaining_payable"]) == Decimal("0.00")
    assert final_comm["commission_paid_flag"] == 1

    # Final Trial Balance Check (variance == 0.00)
    tb_resp = await async_client.get("/api/v1/accounting/trial-balance", headers=acc_headers)
    assert tb_resp.status_code == 200
    tb = tb_resp.json()
    assert tb["is_balanced"] is True
    assert Decimal(tb["variance"]) == Decimal("0.00")
    assert Decimal(tb["total_gross_debit"]) == Decimal(tb["total_gross_credit"])
    assert Decimal(tb["total_net_debit"]) == Decimal(tb["total_net_credit"])
