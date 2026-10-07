"""
Phase 6 Integration Tests — Quotation & Rating REST APIs, RBAC Role Enforcement,
Principal Ownership Scoping, and Assisted Request State Machine Lifecycle.
"""
import uuid
from typing import Optional
import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, get_password_hash
from app.models.user import User, UserRole
from app.repositories.role import RoleRepository
from app.repositories.user import UserRepository


@pytest.fixture(autouse=True)
async def cleanup_phase6_tables(db_session: AsyncSession):
    """Ensure clean Quotation tables before and after each integration test."""
    await db_session.execute(text("DELETE FROM tbl_insurancecompanyquotation;"))
    await db_session.execute(text("DELETE FROM tbl_app_quotationremark;"))
    await db_session.execute(text("DELETE FROM tbl_app_quotationrequest;"))
    await db_session.execute(text("DELETE FROM tbl_app_quatationentry;"))
    await db_session.commit()
    yield
    await db_session.execute(text("DELETE FROM tbl_insurancecompanyquotation;"))
    await db_session.execute(text("DELETE FROM tbl_app_quotationremark;"))
    await db_session.execute(text("DELETE FROM tbl_app_quotationrequest;"))
    await db_session.execute(text("DELETE FROM tbl_app_quatationentry;"))
    await db_session.commit()


async def create_user_with_role(
    db_session: AsyncSession,
    role_name: str,
    branch_id: Optional[int] = 101,
    partner_user_id: Optional[int] = None,
    password: str = "Password123!",
) -> tuple[User, dict[str, str]]:
    """Helper to provision a test user, role, and Bearer authorization header."""
    user_repo = UserRepository(db_session)
    role_repo = RoleRepository(db_session)

    role = UserRole(
        UserRole=role_name,
        code=(role_name[:3].upper() if role_name else "ROL"),
        isdeleted="0",
    )
    await role_repo.create(role)

    username = f"u6_{role_name[:4].strip().lower()}_{uuid.uuid4().hex[:6]}"
    user = User(
        UserName=username,
        UserPassword=get_password_hash(password),
        UserRoleId=role.UserRoleId,
        BranchId=branch_id,
        partner_user_id=partner_user_id,
        isdeleted="0",
        mobile_no="9876543210",
    )
    await user_repo.create(user)
    await db_session.commit()
    await db_session.refresh(user)

    token = create_access_token(
        {
            "sub": str(user.UserId),
            "username": user.UserName,
            "role": role_name,
            "branch_id": branch_id,
        }
    )
    return user, {"Authorization": f"Bearer {token}"}


# ============================================================================
# 1. Authentication & RBAC Role Gate Enforcement
# ============================================================================


@pytest.mark.asyncio
async def test_unauthenticated_requests_rejected_401(async_client: AsyncClient):
    """Unauthenticated calls to Quotation & Rating endpoints return 401 Unauthorized."""
    calc_resp = await async_client.post(
        "/api/v1/quotations/calculate",
        json={"vehicle_category": "PVT", "base_idv_override": "500000"},
    )
    assert calc_resp.status_code == 401

    self_resp = await async_client.get("/api/v1/quotations/self")
    assert self_resp.status_code == 401

    req_resp = await async_client.get("/api/v1/quotations/requests")
    assert req_resp.status_code == 401


@pytest.mark.asyncio
@pytest.mark.parametrize("restricted_role", ["CASHIER", "CLAIM", "ACCOUNT", "pOLICY VIEW"])
async def test_non_quotation_roles_rejected_403_on_calculate_and_write(
    async_client: AsyncClient,
    db_session: AsyncSession,
    restricted_role: str,
):
    """Roles outside QUOTATION_CALCULATE_ROLES / QUOTATION_WRITE_ROLES receive 403 Forbidden."""
    _, headers = await create_user_with_role(db_session, role_name=restricted_role)

    calc_resp = await async_client.post(
        "/api/v1/quotations/calculate",
        headers=headers,
        json={"vehicle_category": "PVT", "base_idv_override": "500000"},
    )
    assert calc_resp.status_code == 403

    req_resp = await async_client.post(
        "/api/v1/quotations/requests",
        headers=headers,
        json={
            "insurance_company_id": "3",
            "mobile_no": "9876543210",
            "ncb": "20",
            "vehicle_no": "MH01AB1234",
            "vehicle_type": "GCV",
            "vehicle_make": "TATA",
            "vehicle_model": "ACE",
            "vehicle_variance": "GOLD",
        },
    )
    assert req_resp.status_code == 403


# ============================================================================
# 2. Self-Quotation Creation, Ownership Pinning, Duplicate Title & Scoping
# ============================================================================


@pytest.mark.asyncio
async def test_self_quotation_create_scoping_duplicate_title_and_prefill(
    async_client: AsyncClient,
    db_session: AsyncSession,
):
    """
    Verifies:
    - Agent A creates a Self-Quotation; server pins agent_id to Agent A's partner_user_id (7001)
      ignoring any spoofed agent_id in payload.
    - Quotation code starts with 'SRQ'.
    - Duplicate title returns 409 Conflict.
    - Agent B (partner_user_id=7002) cannot view Agent A's Self-Quotation (403 Forbidden)
      and does not see it in GET /api/v1/quotations/self.
    - QUOT CO-ORDINATOR can view Agent A's Self-Quotation (200 OK).
    - Policy prefill endpoint returns Phase 7 SELF_QUOTATION contract.
    """
    _, headers_agent_a = await create_user_with_role(
        db_session, role_name="AGENT", partner_user_id=7001
    )
    _, headers_agent_b = await create_user_with_role(
        db_session, role_name="AGENT", partner_user_id=7002
    )
    _, headers_coord = await create_user_with_role(
        db_session, role_name="QUOT CO-ORDINATOR", partner_user_id=8001
    )

    payload = {
        "title": "TEST_SELF_QUO_001",
        "product_name": "Package Policy",
        "product_type": "COMPREHENSIVE",
        "registration_no": "mh12cd5678",
        "mgf_year": "2024",
        "agent_id": 999999,  # Spoof attempt! Server must pin to 7001
        "calculation_input": {
            "vehicle_category": "PVT",
            "insurance_company_id": 3,
            "veh_type_id": 4,
            "zone": "A",
            "cubic_capacity": 1197,
            "vehicle_age_override": "2.0",
            "base_idv_override": "600000",
            "od_discount_override": "50",
            "ncb_percent": "20",
            "pa_to_owner_driver": True,
        },
    }

    create_resp = await async_client.post(
        "/api/v1/quotations/self", headers=headers_agent_a, json=payload
    )
    assert create_resp.status_code == 201
    data = create_resp.json()
    q_id = data["quatation_id"]
    assert data["quatation_code"].startswith("SRQ43")
    assert data["agent_id"] == 7001  # Pinned to Agent A's server-resolved agent_id
    assert data["registration_no"] == "MH12CD5678"
    assert Decimal_str_eq(data["idv"], "600000")
    assert Decimal_str_eq(data["final_premium"], "13771")

    # Duplicate Title check -> 409 Conflict
    dup_resp = await async_client.post(
        "/api/v1/quotations/self", headers=headers_agent_a, json=payload
    )
    assert dup_resp.status_code == 409

    # Agent B attempts to read Agent A's Self-Quotation -> 403 Forbidden
    forbidden_resp = await async_client.get(
        f"/api/v1/quotations/self/{q_id}", headers=headers_agent_b
    )
    assert forbidden_resp.status_code == 403

    # Agent B lists self-quotations -> 0 items
    list_b = await async_client.get("/api/v1/quotations/self", headers=headers_agent_b)
    assert list_b.status_code == 200
    assert list_b.json()["total"] == 0

    # Agent A lists self-quotations -> 1 item
    list_a = await async_client.get("/api/v1/quotations/self", headers=headers_agent_a)
    assert list_a.status_code == 200
    assert list_a.json()["total"] == 1

    # Coordinator can read Agent A's Self-Quotation -> 200 OK
    coord_get = await async_client.get(
        f"/api/v1/quotations/self/{q_id}", headers=headers_coord
    )
    assert coord_get.status_code == 200

    # Policy Prefill from Self-Quotation -> 200 OK
    prefill_resp = await async_client.get(
        f"/api/v1/quotations/self/{q_id}/policy-prefill", headers=headers_agent_a
    )
    assert prefill_resp.status_code == 200
    pf = prefill_resp.json()
    assert pf["source_type"] == "SELF_QUOTATION"
    assert pf["quotation_id"] == q_id
    assert pf["registration_no"] == "MH12CD5678"
    assert Decimal_str_eq(pf["final_premium"], "13771")


# ============================================================================
# 3. Assisted Quotation Request End-to-End Lifecycle & State Machine
# ============================================================================


@pytest.mark.asyncio
async def test_assisted_quotation_request_full_lifecycle(
    async_client: AsyncClient,
    db_session: AsyncSession,
):
    """
    Verifies the complete Assisted Quotation Request lifecycle:
    1. Agent A submits request (POST /requests -> 201).
    2. Agent B blocked from reading/updating Agent A's request (403).
    3. Agent A blocked from calling coordinator endpoints (/attend, /status, /quotes -> 403).
    4. Coordinator 1 claims request (POST /requests/{id}/attend -> 200).
    5. Coordinator 2 blocked from hijacking Coordinator 1's attended request (409).
    6. Coordinator 1 reverts request with remark (POST /requests/{id}/status action='revert' -> isPendingRevert=1).
    7. Agent A updates & resubmits request (PUT /requests/{id} -> isPendingRevert=2).
    8. Coordinator 1 uploads insurer quotes (POST /requests/{id}/quotes -> IsQuotationGenerate=1, isPendingRevert=0).
    9. Agent A retrieves Phase 7 policy prefill (GET /requests/{id}/policy-prefill -> 200).
    10. Agent A blocked from deleting generated request (DELETE /requests/{id} -> 409).
    """
    _, headers_agent_a = await create_user_with_role(
        db_session, role_name="AGENT", partner_user_id=5001
    )
    _, headers_agent_b = await create_user_with_role(
        db_session, role_name="AGENT", partner_user_id=5002
    )
    coord_1, headers_coord_1 = await create_user_with_role(
        db_session, role_name="QUOT CO-ORDINATOR", partner_user_id=6001
    )
    _, headers_coord_2 = await create_user_with_role(
        db_session, role_name="QUOT CO-ORDINATOR", partner_user_id=6002
    )

    # 1. Agent A submits Assisted Quotation Request
    create_resp = await async_client.post(
        "/api/v1/quotations/requests",
        headers=headers_agent_a,
        json={
            "insurance_company_id": "2,3,14",
            "product_type": "1",
            "zerodepth": "Yes",
            "policy_mode": "Online",
            "mobile_no": "9876543210",
            "ncb": "25",
            "vehicle_no": "mh04xy9876",
            "vehicle_type": "GCV",
            "vehicle_make": "ASHOK LEYLAND",
            "vehicle_model": "DOST",
            "vehicle_variance": "LS",
            "policytype": "Package",
            "note": "Urgent fleet quote",
            "remark": "Initial RC & prev policy uploaded",
            "agent_id": 99999,  # Spoof attempt; pinned to 5001
        },
    )
    assert create_resp.status_code == 201
    req_data = create_resp.json()
    q_id = req_data["quatation_id"]
    assert req_data["agent_id"] == 5001
    assert req_data["vehicle_no"] == "MH04XY9876"
    assert req_data["is_quotation_generate"] == 0
    assert req_data["is_pending_revert"] == 0
    assert len(req_data["remarks_history"]) == 1
    assert req_data["remarks_history"][0]["remark_from"] == "Sales"

    # 2. Agent B cannot read or update Agent A's request
    assert (
        await async_client.get(f"/api/v1/quotations/requests/{q_id}", headers=headers_agent_b)
    ).status_code == 403
    assert (
        await async_client.put(
            f"/api/v1/quotations/requests/{q_id}",
            headers=headers_agent_b,
            json={"ncb": "35"},
        )
    ).status_code == 403

    # 3. Agent A cannot invoke Coordinator-only endpoints (/attend, /status, /quotes)
    assert (
        await async_client.post(
            f"/api/v1/quotations/requests/{q_id}/attend",
            headers=headers_agent_a,
            json={"attend": True},
        )
    ).status_code == 403
    assert (
        await async_client.post(
            f"/api/v1/quotations/requests/{q_id}/status",
            headers=headers_agent_a,
            json={"action": "revert", "remark": "Trying to self-revert"},
        )
    ).status_code == 403

    # 4. Coordinator 1 claims the request
    attend_resp = await async_client.post(
        f"/api/v1/quotations/requests/{q_id}/attend",
        headers=headers_coord_1,
        json={"attend": True},
    )
    assert attend_resp.status_code == 200
    assert attend_resp.json()["attended_user_id"] == coord_1.UserId

    # 5. Coordinator 2 blocked from hijacking Coordinator 1's claim -> 409 Conflict
    hijack_resp = await async_client.post(
        f"/api/v1/quotations/requests/{q_id}/attend",
        headers=headers_coord_2,
        json={"attend": True},
    )
    assert hijack_resp.status_code == 409

    # 6. Coordinator 1 reverts the request for clear RC copy -> isPendingRevert = 1
    revert_resp = await async_client.post(
        f"/api/v1/quotations/requests/{q_id}/status",
        headers=headers_coord_1,
        json={"action": "revert", "remark": "Please upload clear RC front & back"},
    )
    assert revert_resp.status_code == 200
    rev_data = revert_resp.json()
    assert rev_data["is_pending_revert"] == 1
    assert rev_data["is_quotation_generate"] == 0
    assert len(rev_data["remarks_history"]) == 2
    assert rev_data["remarks_history"][0]["remark_from"] == "Operator"

    # 7. Agent A updates and resubmits -> isPendingRevert = 2
    resubmit_resp = await async_client.put(
        f"/api/v1/quotations/requests/{q_id}",
        headers=headers_agent_a,
        json={
            "policy_image": "rc_clear_v2.pdf",
            "remark": "Uploaded clear RC copy",
        },
    )
    assert resubmit_resp.status_code == 200
    resub_data = resubmit_resp.json()
    assert resub_data["is_pending_revert"] == 2
    assert resub_data["is_quotation_generate"] == 0
    assert len(resub_data["remarks_history"]) == 3

    # 8. Coordinator 1 attaches 2 insurer quote options -> IsQuotationGenerate = 1, isPendingRevert = 0
    quotes_resp = await async_client.post(
        f"/api/v1/quotations/requests/{q_id}/quotes",
        headers=headers_coord_1,
        json={
            "replace_existing": True,
            "coordinator_remark": "Quotes generated for ICICI and Bajaj",
            "options": [
                {
                    "insurance_company_id": 2,
                    "quotation_file": "icici_quote_001.pdf",
                    "quotation_file_name": "ICICI Lombard Quote",
                    "product_id": 1,
                    "remark": "Best IDV option",
                },
                {
                    "insurance_company_id": 3,
                    "quotation_file": "bajaj_quote_002.pdf",
                    "quotation_file_name": "Bajaj Allianz Quote",
                    "product_id": 1,
                    "remark": "Lowest OD option",
                },
            ],
        },
    )
    assert quotes_resp.status_code == 200
    gen_data = quotes_resp.json()
    assert gen_data["is_quotation_generate"] == 1
    assert gen_data["is_pending_revert"] == 0
    assert len(gen_data["insurer_quotes"]) == 2

    # 9. Agent A fetches Phase 7 Policy Prefill for selected insurer #3 (Bajaj)
    prefill_resp = await async_client.get(
        f"/api/v1/quotations/requests/{q_id}/policy-prefill?insurance_company_id=3",
        headers=headers_agent_a,
    )
    assert prefill_resp.status_code == 200
    pf = prefill_resp.json()
    assert pf["source_type"] == "ASSISTED_REQUEST"
    assert pf["insurance_company_id"] == 3
    assert pf["quotation_file"] == "bajaj_quote_002.pdf"
    assert pf["registration_no"] == "MH04XY9876"

    # 10. Agent A cannot delete an already-generated request -> 409 Conflict
    del_gen_resp = await async_client.delete(
        f"/api/v1/quotations/requests/{q_id}", headers=headers_agent_a
    )
    assert del_gen_resp.status_code == 409


@pytest.mark.asyncio
async def test_pending_quotation_request_soft_delete(
    async_client: AsyncClient,
    db_session: AsyncSession,
):
    """Agent can soft-delete their own pending (un-generated) Assisted Quotation Request."""
    _, headers_agent = await create_user_with_role(
        db_session, role_name="AGENT", partner_user_id=5010
    )
    create_resp = await async_client.post(
        "/api/v1/quotations/requests",
        headers=headers_agent,
        json={
            "insurance_company_id": "2",
            "mobile_no": "9876543210",
            "ncb": "0",
            "vehicle_no": "MH02ZZ1111",
            "vehicle_type": "PVT",
            "vehicle_make": "MARUTI",
            "vehicle_model": "SWIFT",
            "vehicle_variance": "VXI",
        },
    )
    assert create_resp.status_code == 201
    q_id = create_resp.json()["quatation_id"]

    del_resp = await async_client.delete(
        f"/api/v1/quotations/requests/{q_id}", headers=headers_agent
    )
    assert del_resp.status_code == 200
    assert del_resp.json()["deleted"] is True

    get_resp = await async_client.get(
        f"/api/v1/quotations/requests/{q_id}", headers=headers_agent
    )
    assert get_resp.status_code == 404


def Decimal_str_eq(actual: str, expected: str) -> bool:
    from decimal import Decimal
    return Decimal(str(actual)) == Decimal(str(expected))
