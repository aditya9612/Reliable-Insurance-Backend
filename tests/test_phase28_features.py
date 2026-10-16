"""
Phase 28 Comprehensive Test Suite:
Franchise Agent Grid Margin Override Engine.
Physical Tables:
1. tbl_franchisegridmargin (FranchiseGridMargin)
"""
from decimal import Decimal
import pytest
from httpx import AsyncClient
from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import AsyncSession

from tests.integration.test_phase7_policy_booking_api import create_user_with_role
from app.models.phase28_features import FranchiseGridMargin


@pytest.fixture(autouse=True)
async def cleanup_phase28_tables(db_session: AsyncSession):
    """Purge synthetic Phase 28 test rows before and after each test."""
    try:
        await db_session.execute(text("DELETE FROM tbl_franchisegridmargin;"))
        await db_session.commit()
    except Exception:
        await db_session.rollback()
    yield
    try:
        await db_session.execute(text("DELETE FROM tbl_franchisegridmargin;"))
        await db_session.commit()
    except Exception:
        await db_session.rollback()


# ==============================================================================
# 1. MARGIN CREATION & UPSERT LIFECYCLE TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_create_single_margin_override_success(
    async_client: AsyncClient, db_session: AsyncSession
):
    admin_user, admin_headers = await create_user_with_role(db_session, "ADMIN")

    payload = {
        "franchise_id": 101,
        "franchise_agent_id": 201,
        "insurance_company_id": 18,
        "policy_type_id": 2,
        "margin": "4.50",
    }

    response = await async_client.post(
        "/api/v1/franchise-margins",
        json=payload,
        headers=admin_headers,
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["franchise_id"] == 101
    assert data["franchise_agent_id"] == 201
    assert data["insurance_company_id"] == 18
    assert data["policy_type_id"] == 2
    assert Decimal(str(data["margin"])) == Decimal("4.50")
    assert data["isdeleted"] == 0

    # Verify directly in database
    await db_session.commit()
    stmt = select(FranchiseGridMargin).where(FranchiseGridMargin.Id == data["id"])
    record = (await db_session.execute(stmt)).scalars().first()
    assert record is not None
    assert record.FranchiseId == 101
    assert Decimal(str(record.margin)) == Decimal("4.50")
    assert record.CreatedUser == admin_user.UserName


@pytest.mark.asyncio
async def test_upsert_existing_margin_override(
    async_client: AsyncClient, db_session: AsyncSession
):
    admin_user, admin_headers = await create_user_with_role(db_session, "ADMIN")

    payload_initial = {
        "franchise_id": 102,
        "franchise_agent_id": 202,
        "insurance_company_id": 4,
        "policy_type_id": 1,
        "margin": "3.00",
    }
    resp1 = await async_client.post(
        "/api/v1/franchise-margins",
        json=payload_initial,
        headers=admin_headers,
    )
    assert resp1.status_code == 200
    initial_id = resp1.json()["id"]

    # Upsert with updated margin percentage
    payload_update = {
        "franchise_id": 102,
        "franchise_agent_id": 202,
        "insurance_company_id": 4,
        "policy_type_id": 1,
        "margin": "5.25",
    }
    resp2 = await async_client.post(
        "/api/v1/franchise-margins",
        json=payload_update,
        headers=admin_headers,
    )
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["id"] == initial_id
    assert Decimal(str(data2["margin"])) == Decimal("5.25")
    assert data2["updated_user"] == admin_user.UserName

    # Ensure no duplicate row created
    await db_session.commit()
    count_stmt = select(FranchiseGridMargin).where(
        FranchiseGridMargin.FranchiseId == 102,
        FranchiseGridMargin.FranchiseAgentId == 202,
    )
    rows = (await db_session.execute(count_stmt)).scalars().all()
    assert len(rows) == 1


@pytest.mark.asyncio
async def test_batch_upsert_margins(
    async_client: AsyncClient, db_session: AsyncSession
):
    admin_user, admin_headers = await create_user_with_role(db_session, "ADMIN")

    payload = {
        "franchise_id": 103,
        "franchise_agent_id": 203,
        "insurance_company_id": 3,
        "policy_type_ids": [1, 2, 3, 4],
        "margin": "2.75",
    }
    response = await async_client.post(
        "/api/v1/franchise-margins/batch",
        json=payload,
        headers=admin_headers,
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["success"] is True
    assert data["count"] == 4
    assert len(data["items"]) == 4

    for item in data["items"]:
        assert item["franchise_id"] == 103
        assert item["franchise_agent_id"] == 203
        assert Decimal(str(item["margin"])) == Decimal("2.75")


# ==============================================================================
# 2. LOOKUP, GET, UPDATE & SOFT DELETE TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_lookup_margin_endpoint(
    async_client: AsyncClient, db_session: AsyncSession
):
    admin_user, admin_headers = await create_user_with_role(db_session, "ADMIN")

    # Create record
    await async_client.post(
        "/api/v1/franchise-margins",
        json={
            "franchise_id": 104,
            "franchise_agent_id": 204,
            "insurance_company_id": 14,
            "policy_type_id": 5,
            "margin": "3.50",
        },
        headers=admin_headers,
    )

    # Lookup existing
    lookup_resp = await async_client.get(
        "/api/v1/franchise-margins/lookup",
        params={
            "franchise_id": 104,
            "franchise_agent_id": 204,
            "insurance_company_id": 14,
            "policy_type_id": 5,
        },
        headers=admin_headers,
    )
    assert lookup_resp.status_code == 200
    data = lookup_resp.json()
    assert data is not None
    assert Decimal(str(data["margin"])) == Decimal("3.50")

    # Lookup non-existing
    miss_resp = await async_client.get(
        "/api/v1/franchise-margins/lookup",
        params={
            "franchise_id": 104,
            "franchise_agent_id": 999,
            "insurance_company_id": 14,
            "policy_type_id": 5,
        },
        headers=admin_headers,
    )
    assert miss_resp.status_code == 200
    assert miss_resp.json() is None


@pytest.mark.asyncio
async def test_get_and_update_margin_by_id(
    async_client: AsyncClient, db_session: AsyncSession
):
    admin_user, admin_headers = await create_user_with_role(db_session, "ADMIN")

    create_resp = await async_client.post(
        "/api/v1/franchise-margins",
        json={
            "franchise_id": 105,
            "franchise_agent_id": 205,
            "insurance_company_id": 1,
            "policy_type_id": 1,
            "margin": "1.50",
        },
        headers=admin_headers,
    )
    margin_id = create_resp.json()["id"]

    # Get by ID
    get_resp = await async_client.get(
        f"/api/v1/franchise-margins/{margin_id}",
        headers=admin_headers,
    )
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == margin_id

    # Update by ID
    put_resp = await async_client.put(
        f"/api/v1/franchise-margins/{margin_id}",
        json={"margin": "2.25"},
        headers=admin_headers,
    )
    assert put_resp.status_code == 200
    assert Decimal(str(put_resp.json()["margin"])) == Decimal("2.25")


@pytest.mark.asyncio
async def test_soft_delete_margin(
    async_client: AsyncClient, db_session: AsyncSession
):
    admin_user, admin_headers = await create_user_with_role(db_session, "ADMIN")

    create_resp = await async_client.post(
        "/api/v1/franchise-margins",
        json={
            "franchise_id": 106,
            "franchise_agent_id": 206,
            "insurance_company_id": 2,
            "policy_type_id": 3,
            "margin": "4.00",
        },
        headers=admin_headers,
    )
    margin_id = create_resp.json()["id"]

    # Delete
    del_resp = await async_client.delete(
        f"/api/v1/franchise-margins/{margin_id}",
        headers=admin_headers,
    )
    assert del_resp.status_code == 200
    assert del_resp.json()["success"] is True

    # Lookup should now return null
    lookup_resp = await async_client.get(
        "/api/v1/franchise-margins/lookup",
        params={
            "franchise_id": 106,
            "franchise_agent_id": 206,
            "insurance_company_id": 2,
            "policy_type_id": 3,
        },
        headers=admin_headers,
    )
    assert lookup_resp.json() is None

    # Get by ID should return 404
    get_resp = await async_client.get(
        f"/api/v1/franchise-margins/{margin_id}",
        headers=admin_headers,
    )
    assert get_resp.status_code == 404


# ==============================================================================
# 3. COMMISSION CALCULATION SPLIT TESTS (LEGACY MATH PARITY)
# ==============================================================================

@pytest.mark.asyncio
async def test_calculate_commission_split_with_margin(
    async_client: AsyncClient, db_session: AsyncSession
):
    admin_user, admin_headers = await create_user_with_role(db_session, "ADMIN")

    # Configure 3.50% margin
    await async_client.post(
        "/api/v1/franchise-margins",
        json={
            "franchise_id": 107,
            "franchise_agent_id": 207,
            "insurance_company_id": 18,
            "policy_type_id": 1,
            "margin": "3.50",
        },
        headers=admin_headers,
    )

    # Calculate split: Gross Grid 15.00%, Premium 20,000.00
    # Retained Margin: 3.50% -> 700.00
    # Net Agent Grid: 11.50% -> 2,300.00
    calc_payload = {
        "franchise_id": 107,
        "franchise_agent_id": 207,
        "insurance_company_id": 18,
        "policy_type_id": 1,
        "gross_grid_percentage": "15.00",
        "premium_amount": "20000.00",
        "is_franchise_as_agent": False,
    }
    resp = await async_client.post(
        "/api/v1/franchise-margins/calculate-split",
        json=calc_payload,
        headers=admin_headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["has_margin_override"] is True
    assert Decimal(str(data["retained_margin_percentage"])) == Decimal("3.50")
    assert Decimal(str(data["effective_agent_grid_percentage"])) == Decimal("11.50")
    assert Decimal(str(data["franchise_retained_amount"])) == Decimal("700.00")
    assert Decimal(str(data["agent_payout_amount"])) == Decimal("2300.00")


@pytest.mark.asyncio
async def test_calculate_commission_split_without_margin(
    async_client: AsyncClient, db_session: AsyncSession
):
    admin_user, admin_headers = await create_user_with_role(db_session, "ADMIN")

    # No margin configured: agent gets full gross grid (12.00%)
    calc_payload = {
        "franchise_id": 108,
        "franchise_agent_id": 208,
        "insurance_company_id": 5,
        "policy_type_id": 2,
        "gross_grid_percentage": "12.00",
        "premium_amount": "10000.00",
        "is_franchise_as_agent": False,
    }
    resp = await async_client.post(
        "/api/v1/franchise-margins/calculate-split",
        json=calc_payload,
        headers=admin_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["has_margin_override"] is False
    assert Decimal(str(data["retained_margin_percentage"])) == Decimal("0.00")
    assert Decimal(str(data["effective_agent_grid_percentage"])) == Decimal("12.00")
    assert Decimal(str(data["franchise_retained_amount"])) == Decimal("0.00")
    assert Decimal(str(data["agent_payout_amount"])) == Decimal("1200.00")


@pytest.mark.asyncio
async def test_calculate_commission_split_franchise_as_agent(
    async_client: AsyncClient, db_session: AsyncSession
):
    admin_user, admin_headers = await create_user_with_role(db_session, "ADMIN")

    # Configure 4.00% margin
    await async_client.post(
        "/api/v1/franchise-margins",
        json={
            "franchise_id": 109,
            "franchise_agent_id": 209,
            "insurance_company_id": 1,
            "policy_type_id": 1,
            "margin": "4.00",
        },
        headers=admin_headers,
    )

    # Franchise acting as agent: IS_FR_As_AgentId == "1" -> no margin deduction
    calc_payload = {
        "franchise_id": 109,
        "franchise_agent_id": 209,
        "insurance_company_id": 1,
        "policy_type_id": 1,
        "gross_grid_percentage": "10.00",
        "premium_amount": "15000.00",
        "is_franchise_as_agent": True,
    }
    resp = await async_client.post(
        "/api/v1/franchise-margins/calculate-split",
        json=calc_payload,
        headers=admin_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["is_franchise_as_agent"] is True
    assert Decimal(str(data["effective_agent_grid_percentage"])) == Decimal("10.00")
    assert Decimal(str(data["agent_payout_amount"])) == Decimal("1500.00")
    assert Decimal(str(data["franchise_retained_amount"])) == Decimal("0.00")


@pytest.mark.asyncio
async def test_calculate_commission_split_margin_exceeds_gross(
    async_client: AsyncClient, db_session: AsyncSession
):
    admin_user, admin_headers = await create_user_with_role(db_session, "ADMIN")

    # Margin 8.00%, Gross Grid 5.00% -> agent grid clamps to 0.00% (non-negative)
    await async_client.post(
        "/api/v1/franchise-margins",
        json={
            "franchise_id": 110,
            "franchise_agent_id": 210,
            "insurance_company_id": 2,
            "policy_type_id": 1,
            "margin": "8.00",
        },
        headers=admin_headers,
    )

    calc_payload = {
        "franchise_id": 110,
        "franchise_agent_id": 210,
        "insurance_company_id": 2,
        "policy_type_id": 1,
        "gross_grid_percentage": "5.00",
        "premium_amount": "10000.00",
        "is_franchise_as_agent": False,
    }
    resp = await async_client.post(
        "/api/v1/franchise-margins/calculate-split",
        json=calc_payload,
        headers=admin_headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert Decimal(str(data["effective_agent_grid_percentage"])) == Decimal("0.00")
    assert Decimal(str(data["agent_payout_amount"])) == Decimal("0.00")


# ==============================================================================
# 4. MULTI-TENANT FRANCHISE ISOLATION & VALIDATION TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_franchise_tenant_isolation(
    async_client: AsyncClient, db_session: AsyncSession
):
    # Provision Franchise User for Franchise 555
    fr_user, fr_headers = await create_user_with_role(
        db_session, "FRANCHISE", partner_user_id=555
    )

    # 1. Franchise 555 can create margin for Franchise 555
    valid_payload = {
        "franchise_id": 555,
        "franchise_agent_id": 601,
        "insurance_company_id": 1,
        "policy_type_id": 1,
        "margin": "3.00",
    }
    resp1 = await async_client.post(
        "/api/v1/franchise-margins",
        json=valid_payload,
        headers=fr_headers,
    )
    assert resp1.status_code == 200

    # 2. Franchise 555 attempting to configure Franchise 999 must be rejected with 403 Forbidden
    forbidden_payload = {
        "franchise_id": 999,
        "franchise_agent_id": 701,
        "insurance_company_id": 1,
        "policy_type_id": 1,
        "margin": "3.00",
    }
    resp2 = await async_client.post(
        "/api/v1/franchise-margins",
        json=forbidden_payload,
        headers=fr_headers,
    )
    assert resp2.status_code == 403
    assert "Access denied" in resp2.text


@pytest.mark.asyncio
async def test_margin_validation_constraints(
    async_client: AsyncClient, db_session: AsyncSession
):
    admin_user, admin_headers = await create_user_with_role(db_session, "ADMIN")

    # Margin > 100% must be rejected
    invalid_payload = {
        "franchise_id": 111,
        "franchise_agent_id": 211,
        "insurance_company_id": 1,
        "policy_type_id": 1,
        "margin": "105.00",
    }
    resp = await async_client.post(
        "/api/v1/franchise-margins",
        json=invalid_payload,
        headers=admin_headers,
    )
    assert resp.status_code == 422


# ==============================================================================
# 5. END-TO-END COMMISSION & POLICY BOOKING INTEGRATION TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_end_to_end_policy_booking_with_franchise_margin(
    async_client: AsyncClient, db_session: AsyncSession
):
    """
    Verifies that policy booking (/api/v1/policies/book) dynamically consumes
    tbl_franchisegridmargin to deduce agent commission and credit franchise spread.
    """
    import uuid
    from tests.integration.test_phase7_policy_booking_api import create_synthetic_customer_and_vehicle
    from app.models.commission import FranchiseCommission

    admin_user, admin_headers = await create_user_with_role(db_session, "ADMIN")
    cust, veh = await create_synthetic_customer_and_vehicle(
        db_session, branch_id=101, reg_no=f"MH14M{uuid.uuid4().hex[:6].upper()}"
    )

    franchise_id = 888
    agent_id = 999
    company_id = 1
    policy_type_id = 1

    # 1. Configure custom Franchise Margin of 3.50% in tbl_franchisegridmargin
    margin_payload = {
        "franchise_id": franchise_id,
        "franchise_agent_id": agent_id,
        "insurance_company_id": company_id,
        "policy_type_id": policy_type_id,
        "margin": "3.50",
    }
    m_resp = await async_client.post(
        "/api/v1/franchise-margins",
        json=margin_payload,
        headers=admin_headers,
    )
    assert m_resp.status_code == 200

    # 2. Book policy with Gross Grid = 15.00% OD
    booking_payload = {
        "customer_id": cust.CustomerId,
        "cust_veh_id": veh.CustVehId,
        "insurance_company_id": company_id,
        "policy_type_id": policy_type_id,
        "vehicle_category": "PVT",
        "od_premium": "10000.00",
        "tp_premium": "0.00",
        "commission": {
            "agent_id": agent_id,
            "franchise_id": franchise_id,
            "agent_comm_od_percent": "15.00",
            "tds_percent": "5.00",
        },
        "payments": [{"payment_type": "CASH", "paid_amount": "11800.00"}],
    }

    book_resp = await async_client.post(
        "/api/v1/policies/book",
        json=booking_payload,
        headers=admin_headers,
    )
    assert book_resp.status_code == 201, book_resp.text
    book_data = book_resp.json()
    tx_id = book_data["transaction_id"]

    # 3. Verify Agent Commission in API response was deducted:
    # Gross Grid (15.00%) - Margin (3.50%) = Net Agent Grid (11.50%)
    comm_resp = book_data["commission_summary"]
    assert Decimal(str(comm_resp["agent_comm_od_percent"])) == Decimal("11.50")
    # Agent Gross = 10,000 * 11.5% = 1,150.00
    assert Decimal(str(comm_resp["total_gross_commission"])) == Decimal("1150.00")
    # Franchise Gross = 10,000 * 15.0% = 1,500.00
    assert Decimal(str(comm_resp["franchise_gross_commission"])) == Decimal("1500.00")

    # 4. Verify in database tbl_franchisecommission
    await db_session.commit()
    fc_stmt = select(FranchiseCommission).where(FranchiseCommission.TransanctionId == tx_id)
    fc_record = (await db_session.execute(fc_stmt)).scalars().first()
    assert fc_record is not None
    assert fc_record.FranchiseId == franchise_id
    assert fc_record.AgentId == agent_id
    assert Decimal(str(fc_record.Franchisecomm)) == Decimal("15.00")
    assert Decimal(str(fc_record.Franchisecomm_OD)) == Decimal("15.00")
    assert Decimal(str(fc_record.FranchiseCommAmt_OD)) == Decimal("1500.00")
    assert Decimal(str(fc_record.FranchiseNetComm)) == Decimal("1425.00")
    # Profit of Net Commission reflects exact franchise spread: 1425.00 (franchise net) - 1092.50 (agent net) = 332.50
    assert Decimal(str(fc_record.ProfitofNetCommision)) == Decimal("332.50")


@pytest.mark.asyncio
async def test_batch_upsert_concurrency_safety(
    async_client: AsyncClient, db_session: AsyncSession
):
    """
    Verifies that concurrent batch upserts do not create duplicate active rows
    due to race conditions.
    """
    import asyncio
    admin_user, admin_headers = await create_user_with_role(db_session, "ADMIN")

    franchise_id = 777
    agent_id = 778
    company_id = 10
    policy_type_ids = [101, 102, 103]

    payloads = [
        {
            "franchise_id": franchise_id,
            "franchise_agent_id": agent_id,
            "insurance_company_id": company_id,
            "policy_type_ids": policy_type_ids,
            "margin": f"{3.0 + i * 0.5:.2f}",
        }
        for i in range(3)
    ]

    # Execute 3 concurrent requests simultaneously
    responses = await asyncio.gather(
        *(
            async_client.post(
                "/api/v1/franchise-margins/batch",
                json=p,
                headers=admin_headers,
            )
            for p in payloads
        )
    )
    for r in responses:
        assert r.status_code == 200

    # Ensure exactly 3 rows exist in DB (1 per policy_type_id, no duplicates)
    await db_session.commit()
    count_stmt = select(FranchiseGridMargin).where(
        FranchiseGridMargin.FranchiseId == franchise_id,
        FranchiseGridMargin.FranchiseAgentId == agent_id,
        FranchiseGridMargin.isdeleted == 0,
    )
    rows = (await db_session.execute(count_stmt)).scalars().all()
    assert len(rows) == 3
