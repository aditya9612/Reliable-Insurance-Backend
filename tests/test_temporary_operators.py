"""
Phase 29 Comprehensive Test Suite:
Temporary Operator Role & Workload Delegation Master.
Physical Tables:
1. tbl_tempararyoperator (TemporaryOperator)
"""
import asyncio
from datetime import datetime, timedelta
import pytest
from httpx import AsyncClient
from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import AsyncSession

from tests.integration.test_phase7_policy_booking_api import create_user_with_role
from app.models.temporary_operator import TemporaryOperator


@pytest.fixture(autouse=True)
async def cleanup_phase29_tables(db_session: AsyncSession):
    """Purge synthetic Phase 29 test rows before and after each test."""
    try:
        await db_session.execute(text("DELETE FROM tbl_tempararyoperator;"))
        await db_session.commit()
    except Exception:
        await db_session.rollback()
    yield
    try:
        await db_session.execute(text("DELETE FROM tbl_tempararyoperator;"))
        await db_session.commit()
    except Exception:
        await db_session.rollback()


# ==============================================================================
# 1. DELEGATION CREATION & VALIDATION TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_create_delegation_success(
    async_client: AsyncClient, db_session: AsyncSession
):
    admin_user, admin_headers = await create_user_with_role(db_session, "ADMIN")

    now = datetime.utcnow()
    valid_from = now - timedelta(hours=1)
    valid_up_to = now + timedelta(days=5)

    payload = {
        "per_operator_id": 10,
        "temp_operator_id": 20,
        "valid_from": valid_from.isoformat(),
        "valid_up_to": valid_up_to.isoformat(),
    }

    response = await async_client.post(
        "/api/v1/temporary-operators",
        json=payload,
        headers=admin_headers,
    )
    assert response.status_code == 201, response.text
    data = response.json()
    assert data["per_operator_id"] == 10
    assert data["temp_operator_id"] == 20
    assert data["isdeleted"] == 0
    assert data["is_active"] is True
    assert data["create_user"] == admin_user.UserName

    # Verify directly in database
    await db_session.commit()
    stmt = select(TemporaryOperator).where(TemporaryOperator.ID == data["id"])
    record = (await db_session.execute(stmt)).scalars().first()
    assert record is not None
    assert record.Per_OperatorId == 10
    assert record.Temp_OperatorId == 20
    assert record.isdeleted == 0


@pytest.mark.asyncio
async def test_create_delegation_same_user_rejected(
    async_client: AsyncClient, db_session: AsyncSession
):
    admin_user, admin_headers = await create_user_with_role(db_session, "ADMIN")

    payload = {
        "per_operator_id": 15,
        "temp_operator_id": 15,
    }

    response = await async_client.post(
        "/api/v1/temporary-operators",
        json=payload,
        headers=admin_headers,
    )
    assert response.status_code == 422, response.text
    assert "cannot be the same user" in response.text


@pytest.mark.asyncio
async def test_create_delegation_inverted_dates_rejected(
    async_client: AsyncClient, db_session: AsyncSession
):
    admin_user, admin_headers = await create_user_with_role(db_session, "ADMIN")

    now = datetime.utcnow()
    payload = {
        "per_operator_id": 10,
        "temp_operator_id": 20,
        "valid_from": (now + timedelta(days=5)).isoformat(),
        "valid_up_to": now.isoformat(),
    }

    response = await async_client.post(
        "/api/v1/temporary-operators",
        json=payload,
        headers=admin_headers,
    )
    assert response.status_code == 422, response.text
    assert "earlier than valid_from" in response.text


@pytest.mark.asyncio
async def test_create_delegation_overlapping_conflict(
    async_client: AsyncClient, db_session: AsyncSession
):
    admin_user, admin_headers = await create_user_with_role(db_session, "ADMIN")

    now = datetime.utcnow()
    payload1 = {
        "per_operator_id": 12,
        "temp_operator_id": 22,
        "valid_from": (now - timedelta(days=1)).isoformat(),
        "valid_up_to": (now + timedelta(days=5)).isoformat(),
    }

    res1 = await async_client.post(
        "/api/v1/temporary-operators",
        json=payload1,
        headers=admin_headers,
    )
    assert res1.status_code == 201

    # Attempt to assign another temporary operator for the same permanent operator during the overlapping period
    payload2 = {
        "per_operator_id": 12,
        "temp_operator_id": 33,
        "valid_from": (now + timedelta(days=2)).isoformat(),
        "valid_up_to": (now + timedelta(days=7)).isoformat(),
    }
    res2 = await async_client.post(
        "/api/v1/temporary-operators",
        json=payload2,
        headers=admin_headers,
    )
    assert res2.status_code == 409, res2.text
    assert "An active delegation already exists" in res2.text


# ==============================================================================
# 2. LISTING, FILTERING & DETAIL TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_list_delegations_and_filtering(
    async_client: AsyncClient, db_session: AsyncSession
):
    admin_user, admin_headers = await create_user_with_role(db_session, "ADMIN")

    now = datetime.utcnow()

    # Create two delegations
    await async_client.post(
        "/api/v1/temporary-operators",
        json={
            "per_operator_id": 101,
            "temp_operator_id": 201,
            "valid_from": (now - timedelta(days=1)).isoformat(),
            "valid_up_to": (now + timedelta(days=2)).isoformat(),
        },
        headers=admin_headers,
    )
    await async_client.post(
        "/api/v1/temporary-operators",
        json={
            "per_operator_id": 102,
            "temp_operator_id": 202,
            "valid_from": (now - timedelta(days=10)).isoformat(),
            "valid_up_to": (now - timedelta(days=5)).isoformat(),
        },
        headers=admin_headers,
    )

    # 1. List all
    res_all = await async_client.get(
        "/api/v1/temporary-operators",
        headers=admin_headers,
    )
    assert res_all.status_code == 200
    data_all = res_all.json()
    assert data_all["total"] == 2
    assert len(data_all["items"]) == 2

    # 2. Filter by per_operator_id
    res_filtered = await async_client.get(
        "/api/v1/temporary-operators?per_operator_id=101",
        headers=admin_headers,
    )
    assert res_filtered.status_code == 200
    data_filtered = res_filtered.json()
    assert data_filtered["total"] == 1
    assert data_filtered["items"][0]["per_operator_id"] == 101

    # 3. Filter by active_only
    res_active = await async_client.get(
        "/api/v1/temporary-operators?active_only=true",
        headers=admin_headers,
    )
    assert res_active.status_code == 200
    data_active = res_active.json()
    assert data_active["total"] == 1
    assert data_active["items"][0]["per_operator_id"] == 101


@pytest.mark.asyncio
async def test_get_delegation_by_id(
    async_client: AsyncClient, db_session: AsyncSession
):
    admin_user, admin_headers = await create_user_with_role(db_session, "ADMIN")

    res = await async_client.post(
        "/api/v1/temporary-operators",
        json={"per_operator_id": 50, "temp_operator_id": 60},
        headers=admin_headers,
    )
    delegation_id = res.json()["id"]

    res_get = await async_client.get(
        f"/api/v1/temporary-operators/{delegation_id}",
        headers=admin_headers,
    )
    assert res_get.status_code == 200
    assert res_get.json()["id"] == delegation_id
    assert res_get.json()["per_operator_id"] == 50

    # Test 404
    res_404 = await async_client.get(
        "/api/v1/temporary-operators/999999",
        headers=admin_headers,
    )
    assert res_404.status_code == 404


# ==============================================================================
# 3. UPDATE & REVOCATION (SOFT DELETE) TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_update_delegation(
    async_client: AsyncClient, db_session: AsyncSession
):
    admin_user, admin_headers = await create_user_with_role(db_session, "ADMIN")

    res = await async_client.post(
        "/api/v1/temporary-operators",
        json={"per_operator_id": 70, "temp_operator_id": 80},
        headers=admin_headers,
    )
    delegation_id = res.json()["id"]

    new_valid_to = datetime.utcnow() + timedelta(days=30)
    update_res = await async_client.put(
        f"/api/v1/temporary-operators/{delegation_id}",
        json={"valid_up_to": new_valid_to.isoformat()},
        headers=admin_headers,
    )
    assert update_res.status_code == 200
    data = update_res.json()
    assert data["updated_user"] == admin_user.UserName


@pytest.mark.asyncio
async def test_revoke_delegation_lifecycle(
    async_client: AsyncClient, db_session: AsyncSession
):
    admin_user, admin_headers = await create_user_with_role(db_session, "ADMIN")

    res = await async_client.post(
        "/api/v1/temporary-operators",
        json={"per_operator_id": 90, "temp_operator_id": 95},
        headers=admin_headers,
    )
    delegation_id = res.json()["id"]

    # Revoke delegation
    del_res = await async_client.delete(
        f"/api/v1/temporary-operators/{delegation_id}",
        headers=admin_headers,
    )
    assert del_res.status_code == 200
    assert del_res.json()["success"] is True

    # Subsequent GET returns 404
    get_res = await async_client.get(
        f"/api/v1/temporary-operators/{delegation_id}",
        headers=admin_headers,
    )
    assert get_res.status_code == 404

    # Subsequent DELETE returns 404
    del_res2 = await async_client.delete(
        f"/api/v1/temporary-operators/{delegation_id}",
        headers=admin_headers,
    )
    assert del_res2.status_code == 404


# ==============================================================================
# 4. EFFECTIVE OPERATOR RESOLUTION TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_resolve_effective_operator_active_and_fallback(
    async_client: AsyncClient, db_session: AsyncSession
):
    admin_user, admin_headers = await create_user_with_role(db_session, "ADMIN")

    now = datetime.utcnow()

    # Operator 300 delegates to Operator 400 for next 7 days
    res = await async_client.post(
        "/api/v1/temporary-operators",
        json={
            "per_operator_id": 300,
            "temp_operator_id": 400,
            "valid_from": (now - timedelta(hours=2)).isoformat(),
            "valid_up_to": (now + timedelta(days=7)).isoformat(),
        },
        headers=admin_headers,
    )
    assert res.status_code == 201

    # 1. Resolve effective operator right now -> should return 400 (temporary operator)
    res_eff = await async_client.get(
        "/api/v1/temporary-operators/effective/300",
        headers=admin_headers,
    )
    assert res_eff.status_code == 200
    data_eff = res_eff.json()
    assert data_eff["requested_operator_id"] == 300
    assert data_eff["effective_operator_id"] == 400
    assert data_eff["delegation_active"] is True
    assert data_eff["delegation_role"] == "TEMPORARY"

    # 2. Resolve for a date in the past (before delegation started) -> should return 300
    past_date = (now - timedelta(days=10)).isoformat()
    res_past = await async_client.get(
        f"/api/v1/temporary-operators/effective/300?as_of={past_date}",
        headers=admin_headers,
    )
    assert res_past.status_code == 200
    assert res_past.json()["effective_operator_id"] == 300
    assert res_past.json()["delegation_active"] is False

    # 3. Resolve for an operator who has no delegation -> should return requested operator
    res_none = await async_client.get(
        "/api/v1/temporary-operators/effective/999",
        headers=admin_headers,
    )
    assert res_none.status_code == 200
    assert res_none.json()["effective_operator_id"] == 999
    assert res_none.json()["delegation_active"] is False


# ==============================================================================
# 5. ELIGIBLE OPERATORS & CONCURRENCY TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_list_eligible_operators(
    async_client: AsyncClient, db_session: AsyncSession
):
    admin_user, admin_headers = await create_user_with_role(db_session, "ADMIN")

    res = await async_client.get(
        "/api/v1/temporary-operators/eligible",
        headers=admin_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_concurrency_safe_delegation_creation(
    async_client: AsyncClient, db_session: AsyncSession
):
    """Verify that multiple concurrent creation requests for the same permanent operator do not produce duplicate active overlaps."""
    admin_user, admin_headers = await create_user_with_role(db_session, "ADMIN")

    now = datetime.utcnow()
    payload = {
        "per_operator_id": 555,
        "temp_operator_id": 666,
        "valid_from": (now - timedelta(hours=1)).isoformat(),
        "valid_up_to": (now + timedelta(days=3)).isoformat(),
    }

    async def send_req():
        return await async_client.post(
            "/api/v1/temporary-operators",
            json=payload,
            headers=admin_headers,
        )

    # Fire 5 concurrent requests
    responses = await asyncio.gather(*[send_req() for _ in range(5)])
    status_codes = [r.status_code for r in responses]

    # Exactly 1 request must succeed (201), all other 4 must conflict (409)
    assert status_codes.count(201) == 1
    assert status_codes.count(409) == 4

    # Direct database verification
    await db_session.commit()
    stmt = select(TemporaryOperator).where(
        TemporaryOperator.Per_OperatorId == 555,
        TemporaryOperator.isdeleted == 0,
    )
    active_records = (await db_session.execute(stmt)).scalars().all()
    assert len(active_records) == 1


@pytest.mark.asyncio
async def test_unauthenticated_request_rejected(
    async_client: AsyncClient
):
    res = await async_client.get("/api/v1/temporary-operators")
    assert res.status_code == 401


# ==============================================================================
# 6. PHASE 30 DELEGATION AUTHORIZATION ENFORCEMENT & RBAC TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_delegation_creation_unauthorized_role_rejected(
    async_client: AsyncClient, db_session: AsyncSession
):
    """An agent or non-clerk role cannot create temporary operator delegations (403 Forbidden)."""
    agent_user, agent_headers = await create_user_with_role(db_session, "AGENT")

    payload = {
        "per_operator_id": 1001,
        "temp_operator_id": 1002,
    }

    res = await async_client.post(
        "/api/v1/temporary-operators",
        json=payload,
        headers=agent_headers,
    )
    assert res.status_code == 403, res.text
    assert "not authorized to manage operator delegations" in res.text


@pytest.mark.asyncio
async def test_delegation_creation_cross_branch_supervisor_rejected(
    async_client: AsyncClient, db_session: AsyncSession
):
    """A supervisory user in Branch 10 cannot delegate operators belonging to Branch 20 (403 Forbidden)."""
    # Create supervisor in Branch 10
    sup_user, sup_headers = await create_user_with_role(db_session, "SUPERVISOR")
    sup_user.BranchId = 10
    await db_session.commit()

    # Create operator in Branch 20
    op20_user, _ = await create_user_with_role(db_session, "OPERATOR")
    op20_user.BranchId = 20
    await db_session.commit()

    payload = {
        "per_operator_id": op20_user.UserId,
        "temp_operator_id": 1005,
    }

    res = await async_client.post(
        "/api/v1/temporary-operators",
        json=payload,
        headers=sup_headers,
    )
    assert res.status_code == 403, res.text
    assert "Supervisory users can only manage operator delegations for their own branch" in res.text


@pytest.mark.asyncio
async def test_operator_delegating_other_workload_rejected(
    async_client: AsyncClient, db_session: AsyncSession
):
    """An operator cannot delegate another operator's workload (403 Forbidden)."""
    op1, op1_headers = await create_user_with_role(db_session, "OPERATOR")
    op2, _ = await create_user_with_role(db_session, "OPERATOR")

    payload = {
        "per_operator_id": op2.UserId,  # op1 tries to delegate op2's workload
        "temp_operator_id": 1099,
    }

    res = await async_client.post(
        "/api/v1/temporary-operators",
        json=payload,
        headers=op1_headers,
    )
    assert res.status_code == 403, res.text
    assert "Operators are only permitted to delegate their own workload" in res.text


@pytest.mark.asyncio
async def test_operator_delegating_own_workload_success(
    async_client: AsyncClient, db_session: AsyncSession
):
    """An operator delegating their own workload to another operator in the same branch succeeds (201 Created)."""
    op1, op1_headers = await create_user_with_role(db_session, "OPERATOR")
    op2, _ = await create_user_with_role(db_session, "OPERATOR")
    op1.BranchId = 5
    op2.BranchId = 5
    await db_session.commit()

    now = datetime.utcnow()
    payload = {
        "per_operator_id": op1.UserId,
        "temp_operator_id": op2.UserId,
        "valid_from": now.isoformat(),
        "valid_up_to": (now + timedelta(days=2)).isoformat(),
    }

    res = await async_client.post(
        "/api/v1/temporary-operators",
        json=payload,
        headers=op1_headers,
    )
    assert res.status_code == 201, res.text
    assert res.json()["per_operator_id"] == op1.UserId
    assert res.json()["temp_operator_id"] == op2.UserId


@pytest.mark.asyncio
async def test_delegation_non_operator_role_rejected(
    async_client: AsyncClient, db_session: AsyncSession
):
    """Assigning a user who has a non-operator role (e.g. AGENT) as an operator delegate is rejected (400 Bad Request)."""
    admin_user, admin_headers = await create_user_with_role(db_session, "ADMIN")
    agent_user, _ = await create_user_with_role(db_session, "AGENT")
    op_user, _ = await create_user_with_role(db_session, "OPERATOR")

    payload = {
        "per_operator_id": op_user.UserId,
        "temp_operator_id": agent_user.UserId,  # Not an operator
    }

    res = await async_client.post(
        "/api/v1/temporary-operators",
        json=payload,
        headers=admin_headers,
    )
    assert res.status_code == 400, res.text
    assert "does not have an OPERATOR role" in res.text


@pytest.mark.asyncio
async def test_anti_circular_and_anti_chaining_delegation_rejected(
    async_client: AsyncClient, db_session: AsyncSession
):
    """Circular delegation (A->B then B->A) and chained delegation (A->B then B->C) are prohibited (400 Bad Request)."""
    admin_user, admin_headers = await create_user_with_role(db_session, "ADMIN")
    op_a, _ = await create_user_with_role(db_session, "OPERATOR")
    op_b, _ = await create_user_with_role(db_session, "OPERATOR")
    op_c, _ = await create_user_with_role(db_session, "OPERATOR")

    now = datetime.utcnow()
    # 1. A delegates to B
    res1 = await async_client.post(
        "/api/v1/temporary-operators",
        json={
            "per_operator_id": op_a.UserId,
            "temp_operator_id": op_b.UserId,
            "valid_from": now.isoformat(),
            "valid_up_to": (now + timedelta(days=5)).isoformat(),
        },
        headers=admin_headers,
    )
    assert res1.status_code == 201

    # 2. B attempts to delegate back to A (Circular) -> 400 Bad Request
    res_circ = await async_client.post(
        "/api/v1/temporary-operators",
        json={
            "per_operator_id": op_b.UserId,
            "temp_operator_id": op_a.UserId,
            "valid_from": now.isoformat(),
            "valid_up_to": (now + timedelta(days=5)).isoformat(),
        },
        headers=admin_headers,
    )
    assert res_circ.status_code == 400, res_circ.text
    assert "Circular delegation prohibited" in res_circ.text

    # 3. B attempts to delegate away their own duties to C (Chaining) -> 400 Bad Request
    res_chain = await async_client.post(
        "/api/v1/temporary-operators",
        json={
            "per_operator_id": op_b.UserId,
            "temp_operator_id": op_c.UserId,
            "valid_from": now.isoformat(),
            "valid_up_to": (now + timedelta(days=5)).isoformat(),
        },
        headers=admin_headers,
    )
    assert res_chain.status_code == 409 or res_chain.status_code == 400


@pytest.mark.asyncio
async def test_cross_branch_update_and_revoke_rejected(
    async_client: AsyncClient, db_session: AsyncSession
):
    """A supervisor from Branch 10 cannot update or revoke a delegation created in Branch 20 (403 Forbidden)."""
    admin_user, admin_headers = await create_user_with_role(db_session, "ADMIN")
    sup10_user, sup10_headers = await create_user_with_role(db_session, "SUPERVISOR")
    sup10_user.BranchId = 10

    op20_a, _ = await create_user_with_role(db_session, "OPERATOR")
    op20_a.BranchId = 20
    op20_b, _ = await create_user_with_role(db_session, "OPERATOR")
    op20_b.BranchId = 20
    await db_session.commit()

    # Create delegation in Branch 20
    res_create = await async_client.post(
        "/api/v1/temporary-operators",
        json={
            "per_operator_id": op20_a.UserId,
            "temp_operator_id": op20_b.UserId,
        },
        headers=admin_headers,
    )
    assert res_create.status_code == 201
    delegation_id = res_create.json()["id"]

    # Supervisor from Branch 10 attempts to update -> 403 Forbidden
    res_update = await async_client.put(
        f"/api/v1/temporary-operators/{delegation_id}",
        json={"valid_up_to": (datetime.utcnow() + timedelta(days=10)).isoformat()},
        headers=sup10_headers,
    )
    assert res_update.status_code == 403, res_update.text

    # Supervisor from Branch 10 attempts to revoke -> 403 Forbidden
    res_revoke = await async_client.delete(
        f"/api/v1/temporary-operators/{delegation_id}",
        headers=sup10_headers,
    )
    assert res_revoke.status_code == 403, res_revoke.text


@pytest.mark.asyncio
async def test_principal_context_delegation_resolution(
    async_client: AsyncClient, db_session: AsyncSession
):
    """When an operator with an active delegation authenticates, resolve_principal_context sets acting temporary operator attributes."""
    from app.core.rbac import resolve_principal_context
    from app.models.user import UserRole
    admin_user, admin_headers = await create_user_with_role(db_session, "ADMIN")
    op_per, _ = await create_user_with_role(db_session, "OPERATOR")
    op_temp, _ = await create_user_with_role(db_session, "OPERATOR")

    now = datetime.utcnow()
    res = await async_client.post(
        "/api/v1/temporary-operators",
        json={
            "per_operator_id": op_per.UserId,
            "temp_operator_id": op_temp.UserId,
            "valid_from": (now - timedelta(hours=1)).isoformat(),
            "valid_up_to": (now + timedelta(days=2)).isoformat(),
        },
        headers=admin_headers,
    )
    assert res.status_code == 201
    delegation_id = res.json()["id"]

    # Refresh session snapshot to see committed rows from async_client
    await db_session.commit()

    # Resolve principal context for op_temp
    role_obj = (await db_session.execute(select(UserRole).where(UserRole.UserRoleId == op_temp.UserRoleId))).scalar_one_or_none()
    ctx = await resolve_principal_context(db_session, op_temp, role_obj)
    assert ctx.is_acting_as_temporary_operator is True
    assert ctx.delegated_from_operator_id == op_per.UserId
    assert ctx.effective_operator_id == op_per.UserId

    # When delegation is revoked
    del_res = await async_client.delete(f"/api/v1/temporary-operators/{delegation_id}", headers=admin_headers)
    assert del_res.status_code == 200

    # Refresh session snapshot after revocation
    await db_session.commit()

    # Re-resolve principal context
    ctx2 = await resolve_principal_context(db_session, op_temp, role_obj)
    assert ctx2.is_acting_as_temporary_operator is False
    assert ctx2.delegated_from_operator_id is None
    assert ctx2.effective_operator_id == op_temp.UserId
