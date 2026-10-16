"""
Phase 20 Batch 2 Automated Test Suite — Commercial Clusters & Underwriting Restrictions.
Covers:
1. Geographic Cluster Master & Commission Grids (F-20-005)
2. Decline Models & Restrictions Grid (F-20-006)
"""
from datetime import date, datetime, timedelta
from decimal import Decimal
import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from tests.integration.test_phase7_policy_booking_api import create_user_with_role


@pytest.fixture(autouse=True)
async def cleanup_phase20_batch2_tables(db_session: AsyncSession):
    """Purge synthetic Phase 20 Batch 2 tables before and after each test."""
    tables = [
        "tbl_declinemodel",
        "tbl_griddecline",
        "tbl_clusterwiseagentgrid",
        "tbl_clusterwisebrokergrid",
        "tbl_clusterdetails",
        "tbl_clustermaster",
    ]
    for tbl in tables:
        await db_session.execute(text(f"DELETE FROM {tbl};"))
    await db_session.commit()
    yield
    for tbl in tables:
        await db_session.execute(text(f"DELETE FROM {tbl};"))
    await db_session.commit()


# ==============================================================================
# 1. F-20-005: Commercial Clusters & Commission Grids
# ==============================================================================

@pytest.mark.asyncio
async def test_cluster_master_and_commission_grids(async_client: AsyncClient, db_session: AsyncSession):
    _, admin_headers = await create_user_with_role(db_session, "ADMIN")
    _, account_headers = await create_user_with_role(db_session, "ACCOUNT")
    _, agent_headers = await create_user_with_role(db_session, "AGENT")

    # 1. Non-admin forbidden to create cluster
    unauth_resp = await async_client.post(
        "/api/v1/commercial/clusters",
        headers=agent_headers,
        json={
            "ClusterName": "Unauthorized Cluster",
            "InsuranceCompanyId": 1,
            "StateId": 12,
        },
    )
    assert unauth_resp.status_code == 403

    # 2. Admin creates cluster with initial RTO mappings
    create_resp = await async_client.post(
        "/api/v1/commercial/clusters",
        headers=admin_headers,
        json={
            "ClusterName": "Maharashtra Cluster North",
            "InsuranceCompanyId": 1,
            "StateId": 12,
            "RtoIds": [101, 102],
        },
    )
    assert create_resp.status_code == 201
    cluster = create_resp.json()
    cluster_id = cluster["ClusterMId"]
    assert cluster["ClusterName"] == "Maharashtra Cluster North"
    assert len(cluster["details"]) == 2

    # 3. List clusters
    list_resp = await async_client.get(
        "/api/v1/commercial/clusters?state_id=12",
        headers=agent_headers,
    )
    assert list_resp.status_code == 200
    clusters = list_resp.json()
    assert any(c["ClusterMId"] == cluster_id for c in clusters)

    # 4. Add another RTO to cluster
    add_rto_resp = await async_client.post(
        f"/api/v1/commercial/clusters/{cluster_id}/rtos",
        headers=admin_headers,
        json={
            "ClusterMId": cluster_id,
            "InsuranceCompanyId": 1,
            "RtoId": 103,
        },
    )
    assert add_rto_resp.status_code == 201
    assert add_rto_resp.json()["RtoId"] == 103

    # 5. Check cluster details reloaded
    get_cluster_resp = await async_client.get(
        f"/api/v1/commercial/clusters/{cluster_id}",
        headers=agent_headers,
    )
    assert get_cluster_resp.status_code == 200
    updated_cluster = get_cluster_resp.json()
    assert len(updated_cluster["details"]) == 3

    # 6. Finance creates Cluster-Wise Broker Grid
    broker_grid_resp = await async_client.post(
        "/api/v1/commercial/clusters/broker-grids",
        headers=account_headers,
        json={
            "ClusterMId": cluster_id,
            "BrokerId": 5,
            "InsuranceCompanyId": 1,
            "Veh_Type_ID": 2,
            "StateId": 12,
            "GridValue": "18.50",
            "ODDiscount": "65.00",
            "CalOn": "OD",
            "ReferenceType": "COMPREHENSIVE",
        },
    )
    assert broker_grid_resp.status_code == 201
    bg = broker_grid_resp.json()
    assert Decimal(str(bg["GridValue"])) == Decimal("18.50")
    assert Decimal(str(bg["ODDiscount"])) == Decimal("65.00")

    # 7. List Broker Grids
    list_bg_resp = await async_client.get(
        f"/api/v1/commercial/clusters/broker-grids?cluster_id={cluster_id}",
        headers=agent_headers,
    )
    assert list_bg_resp.status_code == 200
    assert len(list_bg_resp.json()) >= 1

    # 8. Finance creates Cluster-Wise Agent Grid
    agent_grid_resp = await async_client.post(
        "/api/v1/commercial/clusters/agent-grids",
        headers=account_headers,
        json={
            "ClusterMId": cluster_id,
            "AgentId": 10,
            "BrokerId": 5,
            "InsuranceCompanyId": 1,
            "Veh_Type_ID": 2,
            "StateId": 12,
            "GridValue": "12.00",
            "ODDiscount": "65.00",
            "CalOn": "OD",
            "ReferenceType": "COMPREHENSIVE",
        },
    )
    assert agent_grid_resp.status_code == 201
    ag = agent_grid_resp.json()
    assert Decimal(str(ag["GridValue"])) == Decimal("12.00")

    # 9. List Agent Grids
    list_ag_resp = await async_client.get(
        f"/api/v1/commercial/clusters/agent-grids?agent_id=10",
        headers=agent_headers,
    )
    assert list_ag_resp.status_code == 200
    assert len(list_ag_resp.json()) >= 1


# ==============================================================================
# 2. F-20-006: Underwriting Rules & Decline Restrictions
# ==============================================================================

@pytest.mark.asyncio
async def test_decline_rules_master_and_evaluation(async_client: AsyncClient, db_session: AsyncSession):
    _, admin_headers = await create_user_with_role(db_session, "ADMIN")
    _, agent_headers = await create_user_with_role(db_session, "AGENT")

    # 1. Non-admin forbidden to create decline rule
    unauth_resp = await async_client.post(
        "/api/v1/underwriting/decline-rules",
        headers=agent_headers,
        json={
            "InsuranceCompanyId": 1,
            "MakeId": 10,
            "PolicyTypeId": 1,
            "ProductTypeId": 2,
        },
    )
    assert unauth_resp.status_code == 403

    # 2. Admin creates Grid Decline Master rule (e.g. Make-level commercial decline)
    decline_rule_resp = await async_client.post(
        "/api/v1/underwriting/decline-rules",
        headers=admin_headers,
        json={
            "InsuranceCompanyId": 1,
            "MakeId": 10,
            "PolicyTypeId": 1,
            "ProductTypeId": 2,
            "Guide_line": "Commercial heavy vehicle make excluded per underwriter guidelines.",
            "active": 1,
        },
    )
    assert decline_rule_resp.status_code == 201
    decline_data = decline_rule_resp.json()
    decline_id = decline_data["DeclineId"]
    assert decline_data["MakeId"] == 10

    # 3. List Decline Rules
    list_rules_resp = await async_client.get(
        "/api/v1/underwriting/decline-rules?insurance_company_id=1",
        headers=agent_headers,
    )
    assert list_rules_resp.status_code == 200
    assert any(r["DeclineId"] == decline_id for r in list_rules_resp.json())

    # 4. Admin creates specific Model Level Decline rule
    model_decline_resp = await async_client.post(
        "/api/v1/underwriting/decline-rules/models",
        headers=admin_headers,
        json={
            "DeclineId": decline_id,
            "MakeId": 10,
            "ModelId": 50,
            "InsuranceCompanyId": 1,
            "PolicyTypeId": 1,
            "ProductTypeId": 2,
            "FuelTypeId": 3,
            "Remark": "CNG variant strictly restricted for commercial transit.",
        },
    )
    assert model_decline_resp.status_code == 201
    assert model_decline_resp.json()["ModelId"] == 50

    # 5. List Model Level Declines
    list_models_resp = await async_client.get(
        "/api/v1/underwriting/decline-rules/models?make_id=10",
        headers=agent_headers,
    )
    assert list_models_resp.status_code == 200
    assert len(list_models_resp.json()) >= 1

    # 6. Evaluation Check: Proposal matching declined rule
    check_declined_resp = await async_client.post(
        "/api/v1/underwriting/decline-rules/check",
        headers=agent_headers,
        json={
            "InsuranceCompanyId": 1,
            "MakeId": 10,
            "ModelId": 50,
            "PolicyTypeId": 1,
            "ProductTypeId": 2,
            "FuelTypeId": 3,
        },
    )
    assert check_declined_resp.status_code == 200
    declined_eval = check_declined_resp.json()
    assert declined_eval["is_declined"] is True
    assert "CNG variant strictly restricted" in declined_eval["reason"] or "Commercial heavy vehicle make excluded" in declined_eval["reason"]
    assert declined_eval["matching_rule_count"] >= 1

    # 7. Evaluation Check: Non-matching proposal (Allowed)
    check_allowed_resp = await async_client.post(
        "/api/v1/underwriting/decline-rules/check",
        headers=agent_headers,
        json={
            "InsuranceCompanyId": 1,
            "MakeId": 99,
            "ModelId": 999,
            "PolicyTypeId": 1,
            "ProductTypeId": 2,
        },
    )
    assert check_allowed_resp.status_code == 200
    allowed_eval = check_allowed_resp.json()
    assert allowed_eval["is_declined"] is False
    assert allowed_eval["matching_rule_count"] == 0
    assert allowed_eval["reason"] is None
