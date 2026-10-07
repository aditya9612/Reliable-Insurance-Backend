"""
Phase 13 Integration Tests — Policy Renewal Engine & Telecaller CRM API.
Tests expiring policies due list, telecaller follow-up creation & listing,
status transitions, and executive dashboard metrics.
"""
from datetime import datetime, timedelta
import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transaction import Transaction
from app.models.vehicle import VehicleDetails
from app.models.renewal import PolicyRenewalStatus
from tests.integration.test_phase7_policy_booking_api import create_user_with_role
from tests.integration.test_phase12_search import make_synthetic_tx


@pytest.fixture(autouse=True)
async def cleanup_phase13_renewal_tables(db_session: AsyncSession):
    """Purge synthetic renewal and transaction records before and after test."""
    await db_session.execute(text("DELETE FROM tbl_renewal_followup_history;"))
    await db_session.execute(text("DELETE FROM tbl_preyearrenewalstatus;"))
    await db_session.execute(text("DELETE FROM tbl_transaction;"))
    await db_session.execute(text("DELETE FROM tbl_vehicledetails;"))
    await db_session.commit()
    yield
    await db_session.execute(text("DELETE FROM tbl_renewal_followup_history;"))
    await db_session.execute(text("DELETE FROM tbl_preyearrenewalstatus;"))
    await db_session.execute(text("DELETE FROM tbl_transaction;"))
    await db_session.execute(text("DELETE FROM tbl_vehicledetails;"))
    await db_session.commit()


@pytest.mark.asyncio
async def test_get_due_renewals_and_scoping(async_client: AsyncClient, db_session: AsyncSession):
    admin_user, admin_headers = await create_user_with_role(db_session, "ADMIN")
    agent_user, agent_headers = await create_user_with_role(db_session, "AGENT", branch_id=1, partner_user_id=50)

    now = datetime.utcnow()

    # Create vehicles
    v1 = VehicleDetails(RegistrationNo="MH12DUE001", FinancialYear="2024-2025")
    v2 = VehicleDetails(RegistrationNo="MH12DUE002", FinancialYear="2024-2025")
    db_session.add_all([v1, v2])
    await db_session.flush()

    # Policy 1: Belongs to Agent 50
    tx1 = make_synthetic_tx(
        policy_no="P-DUE-01",
        cust_veh_id=v1.CustVehId,
        agent_id=50,
        branch_id=1,
    )
    tx1.ExpiryDate = now + timedelta(days=10)
    tx1.SalesEx_id = 5

    # Policy 2: Belongs to Agent 99
    tx2 = make_synthetic_tx(
        policy_no="P-DUE-02",
        cust_veh_id=v2.CustVehId,
        agent_id=99,
        branch_id=1,
    )
    tx2.ExpiryDate = now + timedelta(days=15)
    tx2.SalesEx_id = 5

    db_session.add_all([tx1, tx2])
    await db_session.commit()

    # Admin sees both policies
    resp_admin = await async_client.get("/api/v1/renewals/due?days_ahead=30", headers=admin_headers)
    assert resp_admin.status_code == 200
    assert len(resp_admin.json()) == 2

    # Agent 50 sees only Policy 1
    resp_agent = await async_client.get("/api/v1/renewals/due?days_ahead=30", headers=agent_headers)
    assert resp_agent.status_code == 200
    agent_items = resp_agent.json()
    assert len(agent_items) == 1
    assert agent_items[0]["registration_no"] == "MH12DUE001"


@pytest.mark.asyncio
async def test_telecaller_followups_flow_and_transitions(async_client: AsyncClient, db_session: AsyncSession):
    _, tele_headers = await create_user_with_role(db_session, "OPERATOR")

    now = datetime.utcnow()

    # 1. Create Follow-Up
    post_payload = {
        "transaction_id": 501,
        "registration_number": "MH14FOL001",
        "financial_year": "2024-2025",
        "remark": "Customer requested callback tomorrow morning.",
        "followup_date": (now + timedelta(days=1)).isoformat(),
        "insurance_company": "TATA AIG",
        "total_premium": 18500.0,
        "mobile_number": "9850255555",
        "expiry_date": (now + timedelta(days=7)).isoformat(),
    }
    create_resp = await async_client.post(
        "/api/v1/renewals/followups",
        json=post_payload,
        headers=tele_headers,
    )
    assert create_resp.status_code == 201
    created_data = create_resp.json()
    status_id = created_data["id"]
    assert created_data["status"] == "Follow"
    assert created_data["registration_number"] == "MH14FOL001"

    # 2. List Follow-ups
    list_resp = await async_client.get(
        "/api/v1/renewals/followups?financial_year=2024-2025&status=Follow",
        headers=tele_headers,
    )
    assert list_resp.status_code == 200
    items = list_resp.json()
    assert len(items) >= 1
    assert any(i["id"] == status_id for i in items)

    # 3. Transition Status to Done
    put_resp = await async_client.put(
        f"/api/v1/renewals/{status_id}/status",
        json={"status": "Done", "remark": "New policy booked successfully."},
        headers=tele_headers,
    )
    assert put_resp.status_code == 200
    updated_data = put_resp.json()
    assert updated_data["status"] == "Done"

    # 4. Confirm it is now in Done list, no longer in Follow list
    follow_resp = await async_client.get(
        "/api/v1/renewals/followups?financial_year=2024-2025&status=Follow",
        headers=tele_headers,
    )
    assert not any(i["id"] == status_id for i in follow_resp.json())


@pytest.mark.asyncio
async def test_renewals_dashboard_metrics(async_client: AsyncClient, db_session: AsyncSession):
    _, admin_headers = await create_user_with_role(db_session, "ADMIN")

    now = datetime.utcnow()
    fy = "2024-2025"

    # Seed 3 renewal records: 1 Follow, 1 Done, 1 Lost
    r1 = PolicyRenewalStatus(
        TransanctionId=1,
        RegistrationNo="MH12DASH1",
        FinancialYear=fy,
        RenewalStatus="Follow",
        InsuranceCompany="BAJAJ ALLIANZ",
        TotalPremium=10000.0,
        ExpiryDate=now,
        ExecutiveId=10,
        isdeleted=0,
    )
    r2 = PolicyRenewalStatus(
        TransanctionId=2,
        RegistrationNo="MH12DASH2",
        FinancialYear=fy,
        RenewalStatus="Done",
        InsuranceCompany="BAJAJ ALLIANZ",
        TotalPremium=15000.0,
        ExpiryDate=now,
        ExecutiveId=10,
        isdeleted=0,
    )
    r3 = PolicyRenewalStatus(
        TransanctionId=3,
        RegistrationNo="MH12DASH3",
        FinancialYear=fy,
        RenewalStatus="Lost",
        InsuranceCompany="ICICI LOMBARD",
        TotalPremium=20000.0,
        ExpiryDate=now,
        ExecutiveId=20,
        isdeleted=0,
    )
    db_session.add_all([r1, r2, r3])
    await db_session.commit()

    resp = await async_client.get(
        f"/api/v1/renewals/dashboard?financial_year={fy}",
        headers=admin_headers,
    )
    assert resp.status_code == 200
    dash = resp.json()
    assert dash["financial_year"] == fy
    summary = dash["summary"]
    assert summary["follow_up_count"] == 1
    assert summary["renewed_done_count"] == 1
    assert summary["lost_count"] == 1
    assert summary["total_target_count"] == 3

    # Executive breakdown check
    execs = dash["executive_breakdown"]
    assert len(execs) == 2
    ex10 = next(e for e in execs if e["executive_id"] == 10)
    assert ex10["follow_up_count"] == 1
    assert ex10["done_count"] == 1

    # Company breakdown check
    comps = dash["company_breakdown"]
    assert len(comps) == 2
    bajaj = next(c for c in comps if c["insurance_company"] == "BAJAJ ALLIANZ")
    assert bajaj["due_count"] == 2
    assert bajaj["renewed_count"] == 1
    assert bajaj["retention_rate_pct"] == 50.0
