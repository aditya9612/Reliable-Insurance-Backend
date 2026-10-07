"""
Phase 14 Integration Tests — Dashboards, MIS, POSP Invoices, Statutory TDS & Accounting Reports.
Tests RBAC, Multi-Tenant Row Scoping, Masking, Gated Exports, and Golden Parity.
"""
from datetime import datetime, date, timedelta
from decimal import Decimal
import io
import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import Customer
from app.models.vehicle import VehicleDetails
from app.models.transaction import Transaction
from app.models.report import PospInvoice, Target
from app.models.account import Account
from tests.integration.test_phase7_policy_booking_api import create_user_with_role
from tests.integration.test_phase12_search import make_synthetic_tx


@pytest.fixture(autouse=True)
async def cleanup_phase14_tables(db_session: AsyncSession):
    """Purge synthetic Phase 14 tables before and after test."""
    await db_session.execute(text("DELETE FROM tbl_target;"))
    await db_session.execute(text("DELETE FROM tbl_posp_invoice;"))
    await db_session.execute(text("DELETE FROM tbl_account;"))
    await db_session.execute(text("DELETE FROM tbl_transaction;"))
    await db_session.execute(text("DELETE FROM tbl_vehicledetails;"))
    await db_session.execute(text("DELETE FROM tbl_customer;"))
    await db_session.commit()
    yield
    await db_session.execute(text("DELETE FROM tbl_target;"))
    await db_session.execute(text("DELETE FROM tbl_posp_invoice;"))
    await db_session.execute(text("DELETE FROM tbl_account;"))
    await db_session.execute(text("DELETE FROM tbl_transaction;"))
    await db_session.execute(text("DELETE FROM tbl_vehicledetails;"))
    await db_session.execute(text("DELETE FROM tbl_customer;"))
    await db_session.commit()


# ============================================================================
# 1. Dashboards & KPIs
# ============================================================================

@pytest.mark.asyncio
async def test_admin_dashboard_api(async_client: AsyncClient, db_session: AsyncSession):
    _, admin_headers = await create_user_with_role(db_session, "ADMIN")

    resp = await async_client.get(
        "/api/v1/dashboards/admin?financial_year=2025-2026&date_mode=T_Date",
        headers=admin_headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["financial_year"] == "2025-2026"
    assert data["date_mode"] == "T_Date"
    assert len(data["monthly_matrix"]) == 12
    # Verify month ordering starts at April (legacy Indian FY)
    assert data["monthly_matrix"][0]["month"] == "April"
    assert data["monthly_matrix"][11]["month"] == "March"
    assert "totals" in data


@pytest.mark.asyncio
async def test_accounts_summary_api(async_client: AsyncClient, db_session: AsyncSession):
    _, admin_headers = await create_user_with_role(db_session, "ADMIN")

    resp = await async_client.get(
        "/api/v1/dashboards/accounts-summary?from_date=2025-04-01&to_date=2026-03-31",
        headers=admin_headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "cash_total" in data
    assert "cheque_total" in data
    assert "online_total" in data
    assert "total_collections" in data
    assert "net_cash_flow" in data


@pytest.mark.asyncio
async def test_owner_dashboard_api_and_rbac(async_client: AsyncClient, db_session: AsyncSession):
    _, owner_headers = await create_user_with_role(db_session, "OWNER")
    _, agent_headers = await create_user_with_role(db_session, "AGENT")

    # Owner access allowed
    resp_owner = await async_client.get(
        "/api/v1/dashboards/owner?from_date=2025-04-01&to_date=2026-03-31",
        headers=owner_headers,
    )
    assert resp_owner.status_code == 200, resp_owner.text
    data = resp_owner.json()
    assert "broker_splits" in data
    assert "source_splits" in data

    # Agent access forbidden
    resp_agent = await async_client.get(
        "/api/v1/dashboards/owner?from_date=2025-04-01&to_date=2026-03-31",
        headers=agent_headers,
    )
    assert resp_agent.status_code == 403


@pytest.mark.asyncio
async def test_cut_and_pay_and_outstanding_dashboards(async_client: AsyncClient, db_session: AsyncSession):
    _, admin_headers = await create_user_with_role(db_session, "ADMIN")

    resp_cp = await async_client.get(
        "/api/v1/dashboards/agent-cut-pay?financial_year=2025-2026",
        headers=admin_headers,
    )
    assert resp_cp.status_code == 200, resp_cp.text
    assert "total_remittance_due" in resp_cp.json()

    resp_out = await async_client.get(
        "/api/v1/dashboards/agent-outstanding",
        headers=admin_headers,
    )
    assert resp_out.status_code == 200, resp_out.text
    assert "total_outstanding" in resp_out.json()


# ============================================================================
# 2. MIS Transactions & Sensitive Data Masking & Gated Export
# ============================================================================

@pytest.mark.asyncio
async def test_mis_transactions_masking_parity(async_client: AsyncClient, db_session: AsyncSession):
    admin_user, admin_headers = await create_user_with_role(db_session, "ADMIN")
    agent_user, agent_headers = await create_user_with_role(db_session, "AGENT", partner_user_id=101)

    # Seed Customer, Vehicle and Transaction
    cust = Customer(CustFName="SURESH", CustLName="SHARMA", MoblieNo1="9822011111")
    db_session.add(cust)
    await db_session.flush()

    veh = VehicleDetails(RegistrationNo="MH12MIS001", Make_ID=1, Model_ID=1, FinancialYear="2025-2026")
    db_session.add(veh)
    await db_session.flush()

    tx = make_synthetic_tx(
        policy_no="POL-MIS-001",
        cust_veh_id=veh.CustVehId,
        customer_id=cust.CustomerId,
        gross_premium=Decimal("11800.00"),
        net_premium=Decimal("10000.00"),
        od_premium=Decimal("7000.00"),
        financial_year="2025-2026",
        agent_id=101,
    )
    tx.TransDate = datetime(2025, 4, 15, 10, 0, 0)
    tx.RiskStartdate = datetime(2025, 4, 15, 10, 0, 0)
    tx.Remark = "Confidential margin details"
    db_session.add(tx)
    await db_session.commit()

    # 1. Admin Query: Internal columns must NOT be masked
    resp_admin = await async_client.get(
        "/api/v1/reports/mis/transactions?policy_no=POL-MIS-001",
        headers=admin_headers,
    )
    assert resp_admin.status_code == 200, resp_admin.text
    items_admin = resp_admin.json()["items"]
    assert len(items_admin) == 1
    # Internal remarks visible to admin
    assert items_admin[0]["internal_remarks"] == "Confidential margin details"

    # 2. Agent Query: Internal columns MUST BE masked to None
    resp_agent = await async_client.get(
        "/api/v1/reports/mis/transactions?policy_no=POL-MIS-001",
        headers=agent_headers,
    )
    assert resp_agent.status_code == 200, resp_agent.text
    items_agent = resp_agent.json()["items"]
    assert len(items_agent) == 1
    # Internal fields masked
    assert items_agent[0]["internal_remarks"] is None
    assert items_agent[0]["company_profit"] is None
    assert items_agent[0]["company_commission_rate"] is None


@pytest.mark.asyncio
async def test_mis_export_gating_and_formats(async_client: AsyncClient, db_session: AsyncSession):
    _, admin_headers = await create_user_with_role(db_session, "ADMIN")
    _, agent_headers = await create_user_with_role(db_session, "AGENT")

    # 1. Export as XLSX by ADMIN
    resp_xlsx = await async_client.get(
        "/api/v1/reports/mis/transactions/export?format=xlsx",
        headers=admin_headers,
    )
    assert resp_xlsx.status_code == 200, resp_xlsx.text
    assert "spreadsheetml.sheet" in resp_xlsx.headers["content-type"]
    assert resp_xlsx.content.startswith(b"PK\x03\x04")

    # 2. Export as CSV by ADMIN
    resp_csv = await async_client.get(
        "/api/v1/reports/mis/transactions/export?format=csv",
        headers=admin_headers,
    )
    assert resp_csv.status_code == 200, resp_csv.text
    assert "text/csv" in resp_csv.headers["content-type"]
    assert "Trans ID,Policy No" in resp_csv.text

    # 3. Export by unauthorized AGENT role -> 403 Forbidden
    resp_agent_export = await async_client.get(
        "/api/v1/reports/mis/transactions/export?format=xlsx",
        headers=agent_headers,
    )
    assert resp_agent_export.status_code == 403


# ============================================================================
# 3. POSP Invoices & Tax Calculations
# ============================================================================

@pytest.mark.asyncio
async def test_posp_invoice_generation_lifecycle(async_client: AsyncClient, db_session: AsyncSession):
    admin_user, admin_headers = await create_user_with_role(db_session, "ADMIN")
    agent_user, agent_headers = await create_user_with_role(db_session, "AGENT", partner_user_id=201)

    # Generate invoice for agent (Unregistered: 0% GST, 5% TDS)
    payload = {
        "agent_id": 201,
        "posp_type": "POSP",
        "financial_year": "2025-2026",
        "month": "APRIL",
        "amount": "10000.00",
        "custom_invoice_no": "INV/TEST/001",
    }
    resp = await async_client.post(
        "/api/v1/reports/posp-invoices/generate",
        json=payload,
        headers=admin_headers,
    )
    assert resp.status_code == 201, resp.text
    inv_data = resp.json()
    assert inv_data["invoice_no"] == "INV/TEST/001"
    assert inv_data["amount"] == "10000.00"
    assert inv_data["gst_amt"] == "0.00"
    assert inv_data["tds_amount"] == "500.00"
    assert inv_data["net_payable"] == "9500.00"
    assert "Rupees Nine Thousand Five Hundred Only" in inv_data["amount_in_words"]
    inv_id = inv_data["invoice_id"]

    # Duplicate invoice number conflict check -> 409
    resp_dup = await async_client.post(
        "/api/v1/reports/posp-invoices/generate",
        json=payload,
        headers=admin_headers,
    )
    assert resp_dup.status_code == 409

    # Download PDF
    resp_pdf = await async_client.get(
        f"/api/v1/reports/posp-invoices/{inv_id}/pdf",
        headers=admin_headers,
    )
    assert resp_pdf.status_code == 200, resp_pdf.text
    assert resp_pdf.headers["content-type"] == "application/pdf"
    assert resp_pdf.content.startswith(b"%PDF")

    # List invoices as Agent: Agent can see their own invoice
    resp_list = await async_client.get(
        "/api/v1/reports/posp-invoices",
        headers=agent_headers,
    )
    assert resp_list.status_code == 200, resp_list.text
    assert resp_list.json()["total"] == 1


# ============================================================================
# 4. Accounting & Statutory TDS Reports
# ============================================================================

@pytest.mark.asyncio
async def test_statutory_tds_register_and_export(async_client: AsyncClient, db_session: AsyncSession):
    _, admin_headers = await create_user_with_role(db_session, "ADMIN")

    resp = await async_client.get(
        "/api/v1/reports/statutory/tds?from_date=2025-04-01&to_date=2026-03-31",
        headers=admin_headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "total_gross_commission" in data
    assert "total_tds_deducted" in data
    assert "total_net_commission" in data

    # Export TDS Register
    resp_exp = await async_client.get(
        "/api/v1/reports/statutory/tds/export?from_date=2025-04-01&to_date=2026-03-31",
        headers=admin_headers,
    )
    assert resp_exp.status_code == 200, resp_exp.text
    assert resp_exp.content.startswith(b"PK\x03\x04")


@pytest.mark.asyncio
async def test_accounting_ledger_summary_and_statement(async_client: AsyncClient, db_session: AsyncSession):
    _, admin_headers = await create_user_with_role(db_session, "ADMIN")

    # Ledger Summary
    resp_summary = await async_client.get(
        "/api/v1/reports/accounting/ledger-summary?from_date=2025-04-01&to_date=2026-03-31",
        headers=admin_headers,
    )
    assert resp_summary.status_code == 200, resp_summary.text
    assert isinstance(resp_summary.json(), list)

    # Ledger Statement
    resp_stmt = await async_client.get(
        "/api/v1/reports/accounting/ledger-statement?ledger_m_id=1&from_date=2025-04-01&to_date=2026-03-31",
        headers=admin_headers,
    )
    assert resp_stmt.status_code == 200, resp_stmt.text
    stmt_data = resp_stmt.json()
    assert "opening_balance" in stmt_data
    assert "closing_balance" in stmt_data
    assert "transactions" in stmt_data


# ============================================================================
# 5. Operations, Targets & Renewal Reports
# ============================================================================

@pytest.mark.asyncio
async def test_operations_and_targets_reports(async_client: AsyncClient, db_session: AsyncSession):
    _, admin_headers = await create_user_with_role(db_session, "ADMIN")

    # 1. Commission Discrepancy Reconciliation
    resp_comm = await async_client.get(
        "/api/v1/reports/operations/commission-reconciliation?from_date=2025-04-01&to_date=2026-03-31",
        headers=admin_headers,
    )
    assert resp_comm.status_code == 200, resp_comm.text
    assert "total_difference" in resp_comm.json()

    # 2. Bank Clearance Reconciliation
    resp_bank = await async_client.get(
        "/api/v1/reports/operations/bank-reconciliation?from_date=2025-04-01&to_date=2026-03-31",
        headers=admin_headers,
    )
    assert resp_bank.status_code == 200, resp_bank.text
    assert "total_uncleared_amount" in resp_bank.json()

    # 3. Telecaller Targets
    resp_tc = await async_client.get(
        "/api/v1/reports/targets/telecaller?financial_year=2025-2026&month=APRIL",
        headers=admin_headers,
    )
    assert resp_tc.status_code == 200, resp_tc.text
    assert "items" in resp_tc.json()

    # 4. Expiring Policies
    resp_exp = await async_client.get(
        "/api/v1/reports/renewals/expiring-policies?as_of_date=2025-04-01&window_days=30",
        headers=admin_headers,
    )
    assert resp_exp.status_code == 200, resp_exp.text
    assert "total_count" in resp_exp.json()
