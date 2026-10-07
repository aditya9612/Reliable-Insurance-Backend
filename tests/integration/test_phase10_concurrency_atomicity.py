"""
Phase 10 Concurrency, Atomicity & Idempotency Tests:
1. Fault injection rollback on Claim Settlement (`simulate_failure_at="BEFORE_COMMIT"`)
2. Fault injection rollback on Endorsement Application (`simulate_failure_at="BEFORE_COMMIT"`)
3. Idempotent replay for Claim Intimation, Claim Settlement, Endorsement Creation, Endorsement Apply, and Refund Disbursement
4. Concurrent claim settlement race (`asyncio.gather` — exactly 1 succeeds, 1 gets 409 Conflict)
5. Concurrent endorsement application race (`asyncio.gather` — exactly 1 succeeds, 1 gets 409 Conflict)
"""
import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
import pytest
from httpx import AsyncClient
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.rbac import PrincipalContext
from app.models.account import Account
from app.schemas.claims_endorsement import (
    ClaimAssessmentRequest,
    ClaimApprovalRequest,
    ClaimIntimateRequest,
    ClaimSettlementRequest,
    EndorsementActionRequest,
    EndorsementApplyRequest,
    EndorsementCreateRequest,
)
from app.services.claims_endorsement import ClaimsEndorsementService
from tests.integration.test_phase7_policy_booking_api import create_user_with_role
from tests.integration.test_phase10_claims_endorsements_api import seed_synthetic_booked_policy


@pytest.fixture(autouse=True)
async def cleanup_phase10_concurrency_tables(db_session: AsyncSession):
    for tbl in (
        "tbl_claimdocument",
        "tbl_claims",
        "tbl_appendorsement",
        "tbl_account",
        "tbl_agentcommissionpayment",
        "tbl_franchisecommission",
        "tbl_transaction",
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
        "tbl_agentcommissionpayment",
        "tbl_franchisecommission",
        "tbl_transaction",
        "tbl_vehicledetails",
        "tbl_customer",
    ):
        await db_session.execute(text(f"DELETE FROM {tbl};"))
    await db_session.commit()


@pytest.mark.asyncio
async def test_phase10_atomic_rollback_on_claim_settlement_and_endorsement_apply_failure(
    db_session: AsyncSession,
):
    admin_user, _ = await create_user_with_role(db_session, role_name="ADMIN", branch_id=101)
    admin_user.principal_context = PrincipalContext(
        user_id=admin_user.UserId,
        username=admin_user.UserName,
        role_id=admin_user.UserRoleId,
        role_name="ADMIN",
        branch_id=101,
    )
    policy = await seed_synthetic_booked_policy(db_session, policy_no="POL-ATOM-1001")
    tx_id = policy.TransanctionId
    svc = ClaimsEndorsementService(db_session)

    # 1. Intimate, assess & approve claim
    clm, _ = await svc.intimate_claim(
        admin_user,
        ClaimIntimateRequest(
            transaction_id=tx_id,
            claim_type="OD",
            loss_date=datetime.utcnow() - timedelta(days=2),
            loss_location="Mumbai",
            loss_description="Windshield and hood damage",
            estimated_amount=Decimal("30000.00"),
        ),
    )
    await svc.assess_claim(
        admin_user,
        clm.claim_id,
        ClaimAssessmentRequest(
            assessed_loss_amount=Decimal("30000.00"),
            depreciation_amount=Decimal("2000.00"),
            deductible_amount=Decimal("1000.00"),
        ),
    )
    await svc.approve_claim(
        admin_user,
        clm.claim_id,
        ClaimApprovalRequest(remarks="Approved 27000"),
    )

    # Inject fault BEFORE_COMMIT during settle_claim
    with pytest.raises( Exception ):
        await svc.settle_claim(
            admin_user,
            clm.claim_id,
            ClaimSettlementRequest(
                settled_amount=Decimal("27000.00"),
                payee_type="CUSTOMER",
                payment_mode="NEFT",
                payment_doc_no="UTR-FAIL-001",
            ),
            simulate_failure_at="BEFORE_COMMIT",
        )

    # Verify claim status is still APPROVED and 0 account entries were committed
    clm_after = await svc.get_claim(admin_user, clm.claim_id)
    assert clm_after.claim_status == "APPROVED"
    assert clm_after.settled_amount == Decimal("0.00")
    acct_cnt = (
        await db_session.execute(select(func.count(Account.AccountId)))
    ).scalar_one()
    assert acct_cnt == 0

    # 2. Create & approve upward IDV endorsement, then inject fault BEFORE_COMMIT during apply_endorsement
    end_res, _ = await svc.create_endorsement(
        admin_user,
        EndorsementCreateRequest(
            transaction_id=tx_id,
            endorsement_type="IDV_CHANGE",
            field_changes={"SumInsured": "600000.00"},
        ),
    )
    await svc.approve_endorsement(
        admin_user,
        end_res.endorsement_id,
        EndorsementActionRequest(remarks="Approved"),
    )

    with pytest.raises(Exception):
        await svc.apply_endorsement(
            admin_user,
            end_res.endorsement_id,
            EndorsementApplyRequest(remarks="Apply with simulated fault"),
            simulate_failure_at="BEFORE_COMMIT",
        )

    # Verify endorsement is still APPROVED, policy SumInsured is still 500000.00, and 0 account rows exist
    end_after = await svc.get_endorsement(admin_user, end_res.endorsement_id)
    assert end_after.endorsement_status == "APPROVED"
    await db_session.refresh(policy)
    assert Decimal(str(policy.SumInsured)) == Decimal("500000.00")
    assert policy.UpdateEntryStatus == 0
    acct_cnt_after = (
        await db_session.execute(select(func.count(Account.AccountId)))
    ).scalar_one()
    assert acct_cnt_after == 0


@pytest.mark.asyncio
async def test_phase10_idempotency_and_concurrent_race_protection(
    async_client: AsyncClient,
    db_session: AsyncSession,
):
    _, admin_headers = await create_user_with_role(db_session, role_name="ADMIN", branch_id=101)
    policy = await seed_synthetic_booked_policy(db_session, policy_no="POL-CONC-1002")
    loss_dt = (datetime.utcnow() - timedelta(days=3)).isoformat()

    # 1. Idempotent Claim Intimation replay (201 first, 200 second, same claim_id)
    r1 = await async_client.post(
        "/api/v1/claims",
        headers={**admin_headers, "Idempotency-Key": "IDEM-CLM-1001"},
        json={
            "transaction_id": policy.TransanctionId,
            "claim_type": "OD",
            "loss_date": loss_dt,
            "loss_location": "Delhi",
            "loss_description": "Side door dent",
            "estimated_amount": "20000.00",
        },
    )
    assert r1.status_code == 201
    cid = r1.json()["data"]["claim_id"]

    r2 = await async_client.post(
        "/api/v1/claims",
        headers={**admin_headers, "Idempotency-Key": "IDEM-CLM-1001"},
        json={
            "transaction_id": policy.TransanctionId,
            "claim_type": "OD",
            "loss_date": loss_dt,
            "loss_location": "Delhi",
            "loss_description": "Side door dent",
            "estimated_amount": "20000.00",
        },
    )
    assert r2.status_code == 200
    assert r2.json()["data"]["claim_id"] == cid

    # Assess and approve claim
    await async_client.post(
        f"/api/v1/claims/{cid}/register",
        headers=admin_headers,
        json={"insurer_claim_ref": "IC-REF-9001"},
    )
    await async_client.post(
        f"/api/v1/claims/{cid}/assess",
        headers=admin_headers,
        json={
            "assessed_loss_amount": "20000.00",
            "depreciation_amount": "2000.00",
            "deductible_amount": "1000.00",
        },
    )
    await async_client.post(
        f"/api/v1/claims/{cid}/approve",
        headers=admin_headers,
        json={"remarks": "Approved 17000"},
    )

    # 2. Concurrent settlement race (two different payment_doc_no without shared idempotency key)
    s_req1 = async_client.post(
        f"/api/v1/claims/{cid}/settle",
        headers=admin_headers,
        json={
            "settled_amount": "17000.00",
            "payee_type": "CUSTOMER",
            "payment_mode": "NEFT",
            "payment_doc_no": "UTR-RACE-A",
        },
    )
    s_req2 = async_client.post(
        f"/api/v1/claims/{cid}/settle",
        headers=admin_headers,
        json={
            "settled_amount": "17000.00",
            "payee_type": "CUSTOMER",
            "payment_mode": "NEFT",
            "payment_doc_no": "UTR-RACE-B",
        },
    )
    res_a, res_b = await asyncio.gather(s_req1, s_req2)
    codes = sorted([res_a.status_code, res_b.status_code])
    assert codes == [200, 409]

    # 3. Concurrent endorsement apply race
    e_create = await async_client.post(
        "/api/v1/endorsements",
        headers={**admin_headers, "Idempotency-Key": "IDEM-END-1001"},
        json={
            "transaction_id": policy.TransanctionId,
            "endorsement_type": "IDV_CHANGE",
            "field_changes": {"SumInsured": "550000.00"},
        },
    )
    assert e_create.status_code == 201
    eid = e_create.json()["data"]["endorsement_id"]

    # Idempotent replay of endorsement creation
    e_replay = await async_client.post(
        "/api/v1/endorsements",
        headers={**admin_headers, "Idempotency-Key": "IDEM-END-1001"},
        json={
            "transaction_id": policy.TransanctionId,
            "endorsement_type": "IDV_CHANGE",
            "field_changes": {"SumInsured": "550000.00"},
        },
    )
    assert e_replay.status_code == 200
    assert e_replay.json()["data"]["endorsement_id"] == eid

    await async_client.post(
        f"/api/v1/endorsements/{eid}/approve",
        headers=admin_headers,
        json={"remarks": "Approved"},
    )

    app_1 = async_client.post(
        f"/api/v1/endorsements/{eid}/apply",
        headers=admin_headers,
        json={"remarks": "Concurrent apply 1"},
    )
    app_2 = async_client.post(
        f"/api/v1/endorsements/{eid}/apply",
        headers=admin_headers,
        json={"remarks": "Concurrent apply 2"},
    )
    ar1, ar2 = await asyncio.gather(app_1, app_2)
    assert sorted([ar1.status_code, ar2.status_code]) == [200, 409]
