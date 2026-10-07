"""
Phase 10 Golden Parity Tests (`CL10-01` .. `CL10-10` and `EN10-01` .. `EN10-11`).
Verifies 100% legacy business parity across Claims, Endorsements, Policy Modification,
Premium Recalculation, Commission Adjustment, Paid-Commission Recovery, Refunds,
and Trial Balance (`variance == 0.00`).
"""
from datetime import datetime, timedelta
from decimal import Decimal
import pytest
from httpx import AsyncClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import Customer
from app.models.transaction import Transaction
from app.models.vehicle import VehicleDetails
from tests.integration.test_phase7_policy_booking_api import create_user_with_role
from tests.integration.test_phase10_claims_endorsements_api import seed_synthetic_booked_policy


@pytest.fixture(autouse=True)
async def cleanup_phase10_parity_tables(db_session: AsyncSession):
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
async def test_phase10_claims_golden_parity_scenarios_cl10_01_to_cl10_10(
    async_client: AsyncClient,
    db_session: AsyncSession,
):
    _, admin_headers = await create_user_with_role(db_session, role_name="ADMIN", branch_id=101)
    policy = await seed_synthetic_booked_policy(
        db_session,
        policy_no="POL-CLM-PARITY-01",
        od_premium=Decimal("10000.00"),
        tp_premium=Decimal("5000.00"),
        sum_insured=Decimal("500000.00"),
    )
    now_dt = datetime.utcnow()
    valid_loss_dt = (now_dt - timedelta(days=5)).isoformat()

    # CL10-01: Valid OD Claim Intimation on Active Policy + Document Attachment
    r_cl01 = await async_client.post(
        "/api/v1/claims",
        headers=admin_headers,
        json={
            "transaction_id": policy.TransanctionId,
            "claim_type": "OD",
            "loss_date": valid_loss_dt,
            "loss_location": "Ahmedabad SG Highway",
            "loss_description": "Front collision damage",
            "estimated_amount": "45000.00",
        },
    )
    assert r_cl01.status_code == 201
    clm1 = r_cl01.json()["data"]
    cid1 = clm1["claim_id"]
    assert clm1["claim_status"] == "INTIMATED"
    assert clm1["claim_no"].startswith("CLM-101-")

    r_doc = await async_client.post(
        f"/api/v1/claims/{cid1}/documents",
        headers=admin_headers,
        json={
            "document_type": "SURVEY_REPORT",
            "document_name": "survey_01.pdf",
            "storage_key": f"claims/{cid1}/survey_01.pdf",
            "verified_status": "VERIFIED",
        },
    )
    assert r_doc.status_code == 201

    # CL10-02: Surveyor Assignment & Survey Update
    r_cl02 = await async_client.post(
        f"/api/v1/claims/{cid1}/survey",
        headers=admin_headers,
        json={
            "surveyor_name": "Rajesh Sharma",
            "surveyor_mobile": "9822001122",
            "surveyor_license_no": "SLA-77889",
            "remarks": "Survey completed at workshop",
        },
    )
    assert r_cl02.status_code == 200
    assert r_cl02.json()["data"]["claim_status"] == "UNDER_SURVEY"

    # CL10-03: Claim Assessment with Depreciation, Deductible, Excess & Salvage
    # 45000 - 5000 - 1000 - 500 - 1500 = 37000.00
    r_cl03 = await async_client.post(
        f"/api/v1/claims/{cid1}/assess",
        headers=admin_headers,
        json={
            "assessed_loss_amount": "45000.00",
            "depreciation_amount": "5000.00",
            "deductible_amount": "1000.00",
            "excess_amount": "500.00",
            "salvage_amount": "1500.00",
        },
    )
    assert r_cl03.status_code == 200
    assert Decimal(r_cl03.json()["data"]["approved_amount"]) == Decimal("37000.00")
    assert r_cl03.json()["data"]["claim_status"] == "ASSESSED"

    # CL10-04: Claim Approval & Customer Reimbursement Settlement
    r_app = await async_client.post(
        f"/api/v1/claims/{cid1}/approve",
        headers=admin_headers,
        json={"remarks": "Approved 37000"},
    )
    assert r_app.status_code == 200
    assert r_app.json()["data"]["claim_status"] == "APPROVED"

    r_cl04 = await async_client.post(
        f"/api/v1/claims/{cid1}/settle",
        headers=admin_headers,
        json={
            "settled_amount": "37000.00",
            "payee_type": "CUSTOMER",
            "payment_mode": "NEFT",
            "payment_doc_no": "UTR-CL10-04",
        },
    )
    assert r_cl04.status_code == 200
    d_cl04 = r_cl04.json()["data"]
    assert d_cl04["claim_status"] == "SETTLED"
    assert Decimal(d_cl04["customer_payable_amount"]) == Decimal("37000.00")
    assert Decimal(d_cl04["insurer_payable_amount"]) == Decimal("37000.00")
    assert Decimal(d_cl04["garage_payable_amount"]) == Decimal("0.00")

    # CL10-10: Claim Settlement Reversal -> Re-Settle as Garage Cashless -> Close (CL10-05)
    r_cl10 = await async_client.post(
        f"/api/v1/claims/{cid1}/reverse-settlement",
        headers=admin_headers,
        json={"remarks": "Wrong payee type; switching to cashless garage"},
    )
    assert r_cl10.status_code == 200
    assert r_cl10.json()["data"]["claim_status"] == "APPROVED"
    assert Decimal(r_cl10.json()["data"]["settled_amount"]) == Decimal("0.00")

    # CL10-05: Cashless Garage Settlement & Closure
    r_cl05_set = await async_client.post(
        f"/api/v1/claims/{cid1}/settle",
        headers=admin_headers,
        json={
            "settled_amount": "37000.00",
            "payee_type": "GARAGE",
            "payment_mode": "NEFT",
            "payment_doc_no": "UTR-CL10-05-GAR",
        },
    )
    assert r_cl05_set.status_code == 200
    assert Decimal(r_cl05_set.json()["data"]["garage_payable_amount"]) == Decimal("37000.00")
    assert Decimal(r_cl05_set.json()["data"]["customer_payable_amount"]) == Decimal("0.00")

    r_cl05_close = await async_client.post(
        f"/api/v1/claims/{cid1}/close",
        headers=admin_headers,
        json={"remarks": "Discharge voucher received; claim closed"},
    )
    assert r_cl05_close.status_code == 200
    assert r_cl05_close.json()["data"]["claim_status"] == "CLOSED"

    # CL10-06: Claim Rejection & Authorized Reopen
    r_cl06_new = await async_client.post(
        "/api/v1/claims",
        headers=admin_headers,
        json={
            "transaction_id": policy.TransanctionId,
            "claim_type": "TP",
            "loss_date": (now_dt - timedelta(days=4)).isoformat(),
            "loss_location": "Surat",
            "loss_description": "Third party property damage",
            "estimated_amount": "15000.00",
        },
    )
    cid2 = r_cl06_new.json()["data"]["claim_id"]
    r_rej = await async_client.post(
        f"/api/v1/claims/{cid2}/reject",
        headers=admin_headers,
        json={"rejection_reason": "Missing third-party FIR documentation"},
    )
    assert r_rej.status_code == 200
    assert r_rej.json()["data"]["claim_status"] == "REJECTED"

    r_reopen = await async_client.post(
        f"/api/v1/claims/{cid2}/reopen",
        headers=admin_headers,
        json={"remarks": "FIR copy submitted on appeal"},
    )
    assert r_reopen.status_code == 200
    assert r_reopen.json()["data"]["claim_status"] == "REOPENED"

    # CL10-07: Loss Date Outside Policy Coverage Window Rejected (422)
    r_cl07 = await async_client.post(
        "/api/v1/claims",
        headers=admin_headers,
        json={
            "transaction_id": policy.TransanctionId,
            "claim_type": "OD",
            "loss_date": (now_dt - timedelta(days=90)).isoformat(),
            "loss_location": "Vadodara",
            "loss_description": "Prior to policy inception",
            "estimated_amount": "10000.00",
        },
    )
    assert r_cl07.status_code == 422

    # CL10-08: Claim on Cancelled Policy Rejected (409)
    canc_policy = await seed_synthetic_booked_policy(
        db_session, policy_no="POL-CANC-08", cancelled=True
    )
    r_cl08 = await async_client.post(
        "/api/v1/claims",
        headers=admin_headers,
        json={
            "transaction_id": canc_policy.TransanctionId,
            "claim_type": "OD",
            "loss_date": valid_loss_dt,
            "loss_location": "Pune",
            "loss_description": "Cancelled policy test",
            "estimated_amount": "10000.00",
        },
    )
    assert r_cl08.status_code == 409

    # CL10-09: OD Claim on TP-Only Policy Rejected (422)
    tp_only_policy = await seed_synthetic_booked_policy(
        db_session,
        policy_no="POL-TPONLY-09",
        od_premium=Decimal("0.00"),
        tp_premium=Decimal("5000.00"),
    )
    r_cl09 = await async_client.post(
        "/api/v1/claims",
        headers=admin_headers,
        json={
            "transaction_id": tp_only_policy.TransanctionId,
            "claim_type": "OD",
            "loss_date": valid_loss_dt,
            "loss_location": "Pune",
            "loss_description": "OD claim on TP policy",
            "estimated_amount": "10000.00",
        },
    )
    assert r_cl09.status_code == 422

    # Verify Trial Balance is 100% balanced (variance == 0.00)
    tb_resp = await async_client.get("/api/v1/accounting/trial-balance", headers=admin_headers)
    assert tb_resp.status_code == 200
    tb = tb_resp.json()
    assert tb["is_balanced"] is True
    assert Decimal(tb["variance"]) == Decimal("0.00")


@pytest.mark.asyncio
async def test_phase10_endorsements_golden_parity_scenarios_en10_01_to_en10_11(
    async_client: AsyncClient,
    db_session: AsyncSession,
):
    _, admin_headers = await create_user_with_role(db_session, role_name="ADMIN", branch_id=101)
    policy = await seed_synthetic_booked_policy(
        db_session,
        policy_no="POL-END-PARITY-01",
        od_premium=Decimal("10000.00"),
        tp_premium=Decimal("5000.00"),
        sum_insured=Decimal("500000.00"),
        ncb_pct=Decimal("20.00"),
    )

    async def create_approve_apply(end_type: str, changes: dict) -> dict:
        rc = await async_client.post(
            "/api/v1/endorsements",
            headers=admin_headers,
            json={
                "transaction_id": policy.TransanctionId,
                "endorsement_type": end_type,
                "field_changes": changes,
            },
        )
        assert rc.status_code == 201, rc.text
        eid = rc.json()["data"]["endorsement_id"]
        ra = await async_client.post(
            f"/api/v1/endorsements/{eid}/approve",
            headers=admin_headers,
            json={"remarks": f"Approve {end_type}"},
        )
        assert ra.status_code == 200, ra.text
        rap = await async_client.post(
            f"/api/v1/endorsements/{eid}/apply",
            headers=admin_headers,
            json={"remarks": f"Apply {end_type}"},
        )
        assert rap.status_code == 200, rap.text
        await db_session.commit()
        return rap.json()["data"]

    # EN10-01: Non-Financial Customer Name Correction
    en01 = await create_approve_apply("NAME_CORRECTION", {"CustFName": "Rameshwar"})
    assert en01["endorsement_category"] == "NON_FINANCIAL"
    assert Decimal(en01["premium_delta"]) == Decimal("0.00")
    cust_row = (
        await db_session.execute(select(Customer).where(Customer.CustomerId == policy.CustomerId))
    ).scalar_one()
    await db_session.refresh(cust_row)
    assert cust_row.CustFName == "Rameshwar"

    # EN10-02: Non-Financial Address & Contact Correction
    en02 = await create_approve_apply("ADDRESS_CORRECTION", {"Address": "99 Baner Road, Pune"})
    assert Decimal(en02["premium_delta"]) == Decimal("0.00")
    await db_session.refresh(cust_row)
    assert cust_row.PerAddrLine1 == "99 Baner Road, Pune"

    # EN10-03: Non-Financial Vehicle Registration & Engine/Chassis Correction
    en03 = await create_approve_apply(
        "VEHICLE_REGISTRATION_CORRECTION", {"RegistrationNo": "MH12ZZ9999"}
    )
    assert Decimal(en03["premium_delta"]) == Decimal("0.00")
    veh_row = (
        await db_session.execute(
            select(VehicleDetails).where(VehicleDetails.CustVehId == policy.CustVehId)
        )
    ).scalar_one()
    await db_session.refresh(veh_row)
    assert veh_row.RegistrationNo == "MH12ZZ9999"

    # EN10-04: Non-Financial Hypothecation & Nominee Change
    en04 = await create_approve_apply("HYPOTHECATION_CHANGE", {"Financer": "HDFC Bank Auto"})
    assert Decimal(en04["premium_delta"]) == Decimal("0.00")
    await db_session.refresh(veh_row)
    assert veh_row.Extra1 == "HDFC Bank Auto"

    # EN10-05: Upward IDV Change (500,000 -> 600,000 => OD 10,000 -> 12,000, +2360 Final, +285 Net Comm)
    en05 = await create_approve_apply("IDV_CHANGE", {"SumInsured": "600000.00"})
    assert en05["endorsement_category"] == "ADDITIONAL_PREMIUM"
    assert Decimal(en05["premium_delta"]) == Decimal("2360.00")
    assert Decimal(en05["agent_comm_delta"]) == Decimal("285.00")
    await db_session.refresh(policy)
    assert Decimal(str(policy.Amount)) == Decimal("20060.00")
    assert Decimal(str(policy.OutstandingAmount)) == Decimal("2360.00")

    # EN10-11: Reverse Upward Endorsement EN10-05 -> Restores Policy to 500,000 IDV and 17,700 Final Premium
    r_rev05 = await async_client.post(
        f"/api/v1/endorsements/{en05['endorsement_id']}/reverse",
        headers=admin_headers,
        json={"remarks": "Reverse EN10-05"},
    )
    assert r_rev05.status_code == 200
    assert r_rev05.json()["data"]["endorsement_status"] == "REVERSED"
    await db_session.commit()
    await db_session.refresh(policy)
    assert Decimal(str(policy.SumInsured)) == Decimal("500000.00")
    assert Decimal(str(policy.Amount)) == Decimal("17700.00")
    assert Decimal(str(policy.OutstandingAmount)) == Decimal("0.00")

    # EN10-07: NCB Correction (20% -> 0% on OD=8000 policy)
    ncb_policy = await seed_synthetic_booked_policy(
        db_session,
        policy_no="POL-END-NCB-07",
        od_premium=Decimal("8000.00"),
        tp_premium=Decimal("5000.00"),
        ncb_pct=Decimal("20.00"),
    )
    rc_ncb = await async_client.post(
        "/api/v1/endorsements",
        headers=admin_headers,
        json={
            "transaction_id": ncb_policy.TransanctionId,
            "endorsement_type": "NCB_CORRECTION",
            "field_changes": {"NCB": "0.00"},
        },
    )
    eid_ncb = rc_ncb.json()["data"]["endorsement_id"]
    await async_client.post(f"/api/v1/endorsements/{eid_ncb}/approve", headers=admin_headers, json={})
    rap_ncb = await async_client.post(f"/api/v1/endorsements/{eid_ncb}/apply", headers=admin_headers, json={})
    assert rap_ncb.status_code == 200
    assert Decimal(rap_ncb.json()["data"]["new_od_premium"]) == Decimal("10000.00")
    assert Decimal(rap_ncb.json()["data"]["premium_delta"]) == Decimal("2360.00")

    # EN10-08: Coverage / Add-On Addition (AddOn = 1500.00 => +1770.00 Final)
    en08 = await create_approve_apply("COVERAGE_ADDON_CHANGE", {"AddOn": "1500.00"})
    assert Decimal(en08["premium_delta"]) == Decimal("1770.00")
    await async_client.post(
        f"/api/v1/endorsements/{en08['endorsement_id']}/reverse",
        headers=admin_headers,
        json={"remarks": "Restore before downward test"},
    )

    # EN10-06, EN10-09 & EN10-10: Downward IDV Change on Policy with Already-Paid Commission -> Refund & Recovery
    paid_comm_policy = await seed_synthetic_booked_policy(
        db_session,
        policy_no="POL-END-PAIDCOMM-09",
        od_premium=Decimal("10000.00"),
        tp_premium=Decimal("5000.00"),
        sum_insured=Decimal("500000.00"),
        commission_paid="1",
    )
    rc_down = await async_client.post(
        "/api/v1/endorsements",
        headers=admin_headers,
        json={
            "transaction_id": paid_comm_policy.TransanctionId,
            "endorsement_type": "IDV_CHANGE",
            "field_changes": {"SumInsured": "400000.00"},
        },
    )
    eid_down = rc_down.json()["data"]["endorsement_id"]
    await async_client.post(f"/api/v1/endorsements/{eid_down}/approve", headers=admin_headers, json={})
    rap_down = await async_client.post(f"/api/v1/endorsements/{eid_down}/apply", headers=admin_headers, json={})
    assert rap_down.status_code == 200
    d_down = rap_down.json()["data"]
    assert d_down["endorsement_category"] == "REFUND_PREMIUM"
    assert Decimal(d_down["premium_delta"]) == Decimal("-2360.00")
    assert Decimal(d_down["refund_amount"]) == Decimal("2360.00")
    assert d_down["refund_status"] == "PENDING_APPROVAL"
    assert Decimal(d_down["commission_recovery_amount"]) == Decimal("285.00")

    # EN10-10: Refund Approval -> Disbursement -> Reversal
    r_ref_app = await async_client.post(
        f"/api/v1/refunds/{eid_down}/approve",
        headers=admin_headers,
        json={"remarks": "Approve refund 2360.00"},
    )
    assert r_ref_app.status_code == 200
    assert r_ref_app.json()["data"]["refund_status"] == "APPROVED"

    r_ref_disb = await async_client.post(
        f"/api/v1/refunds/{eid_down}/disburse",
        headers=admin_headers,
        json={
            "refund_mode": "NEFT",
            "refund_doc_no": "UTR-REF-EN10-10",
            "remarks": "Disbursed to customer",
        },
    )
    assert r_ref_disb.status_code == 200
    assert r_ref_disb.json()["data"]["refund_status"] == "REFUNDED"
    await db_session.commit()
    await db_session.refresh(paid_comm_policy)
    assert Decimal(str(paid_comm_policy.PaidAmount)) == Decimal("15340.00")

    r_ref_rev = await async_client.post(
        f"/api/v1/refunds/{eid_down}/reverse",
        headers=admin_headers,
        json={"remarks": "Reverse refund for audit test"},
    )
    assert r_ref_rev.status_code == 200
    assert r_ref_rev.json()["data"]["refund_status"] == "REVERSED"
    await db_session.commit()
    await db_session.refresh(paid_comm_policy)
    assert Decimal(str(paid_comm_policy.PaidAmount)) == Decimal("17700.00")

    # Verify Trial Balance is 100% balanced (variance == 0.00)
    tb_resp = await async_client.get("/api/v1/accounting/trial-balance", headers=admin_headers)
    assert tb_resp.status_code == 200
    tb = tb_resp.json()
    assert tb["is_balanced"] is True
    assert Decimal(tb["variance"]) == Decimal("0.00")


@pytest.mark.asyncio
async def test_phase10_gap_remediation_golden_parity_p0_p1_p2(
    async_client: AsyncClient,
    db_session: AsyncSession,
):
    """
    Verifies Phase 0-10 Remediation Golden Parity:
    1. GAP-P10-001 (P0, LBR-123) & GAP-P10-004 (P2):
       - Claim settlement and reversal write 0 rows to tbl_account.
       - FinalBill BillAmt, ICLAmt, and ILAmt are persisted and returned on ClaimResponse.
    2. GAP-P10-003 (P1, LBR-126 / LBR-127):
       - OWNERSHIP_TRANSFER (legacy_endorsement_type_id=12) creates a new Customer row in tbl_customer
         and rebinds policy.CustomerId and vehicle.CustomerId; reversal restores original CustomerId.
    3. GAP-P10-002 (P1, LBR-129 / LBR-065..070):
       - Financial endorsement posts AccTransId=3 on LedgerMId=1161 (Commission Control Ledger).
       - Paid endorsement fee posts the 3-leg AppEndorsementforApproval.aspx.cs split involving LedgerMId=1878.
    """
    from app.models.account import Account

    _, admin_headers = await create_user_with_role(db_session, role_name="ADMIN", branch_id=101)
    policy = await seed_synthetic_booked_policy(
        db_session,
        policy_no="POL-REM-PARITY-01",
        od_premium=Decimal("10000.00"),
        tp_premium=Decimal("5000.00"),
        sum_insured=Decimal("500000.00"),
        ncb_pct=Decimal("20.00"),
    )
    orig_customer_id = int(policy.CustomerId)
    now_dt = datetime.utcnow()

    # ------------------------------------------------------------------
    # 1. GAP-P10-001 & GAP-P10-004: Zero-ledger-impact claim + FinalBill
    # ------------------------------------------------------------------
    acct_before_claim = (
        await db_session.execute(
            select(Account).where(Account.TransId == policy.TransanctionId)
        )
    ).scalars().all()
    count_before_claim = len(acct_before_claim)

    r_cl = await async_client.post(
        "/api/v1/claims",
        headers=admin_headers,
        json={
            "transaction_id": policy.TransanctionId,
            "claim_type": "OD",
            "loss_date": (now_dt - timedelta(days=3)).isoformat(),
            "loss_location": "Ahmedabad",
            "loss_description": "Bumper damage",
            "estimated_amount": "30000.00",
        },
    )
    assert r_cl.status_code == 201
    cid = r_cl.json()["data"]["claim_id"]

    await async_client.post(
        f"/api/v1/claims/{cid}/assess",
        headers=admin_headers,
        json={"assessed_loss_amount": "28000.00", "deductible_amount": "1000.00"},
    )
    await async_client.post(f"/api/v1/claims/{cid}/approve", headers=admin_headers, json={})

    r_settle = await async_client.post(
        f"/api/v1/claims/{cid}/settle",
        headers=admin_headers,
        json={
            "settled_amount": "27000.00",
            "bill_amount": "30000.00",
            "icl_amount": "27000.00",
            "il_amount": "26500.00",
            "payee_type": "CUSTOMER",
            "payment_mode": "NEFT",
            "payment_doc_no": "UTR-GAP-P10-001",
            "remarks": "Settled with FinalBill breakdown",
        },
    )
    assert r_settle.status_code == 200
    d_settle = r_settle.json()["data"]
    assert Decimal(d_settle["bill_amount"]) == Decimal("30000.00")
    assert Decimal(d_settle["icl_amount"]) == Decimal("27000.00")
    assert Decimal(d_settle["il_amount"]) == Decimal("26500.00")

    # Verify 0 rows added to tbl_account on claim settlement (LBR-123)
    await db_session.commit()
    acct_after_settle = (
        await db_session.execute(
            select(Account).where(Account.TransId == policy.TransanctionId)
        )
    ).scalars().all()
    assert len(acct_after_settle) == count_before_claim
    assert all(int(a.AccTransId or 0) not in (15, 16) for a in acct_after_settle)

    # Reverse claim settlement -> still 0 rows added to tbl_account
    r_rev_cl = await async_client.post(
        f"/api/v1/claims/{cid}/reverse-settlement",
        headers=admin_headers,
        json={"remarks": "Verify zero ledger impact on reversal"},
    )
    assert r_rev_cl.status_code == 200
    await db_session.commit()
    acct_after_rev_cl = (
        await db_session.execute(
            select(Account).where(Account.TransId == policy.TransanctionId)
        )
    ).scalars().all()
    assert len(acct_after_rev_cl) == count_before_claim

    # ------------------------------------------------------------------
    # 2. GAP-P10-003: OWNERSHIP_TRANSFER (legacy_endorsement_type_id=12)
    # ------------------------------------------------------------------
    r_own_create = await async_client.post(
        "/api/v1/endorsements",
        headers=admin_headers,
        json={
            "transaction_id": policy.TransanctionId,
            "legacy_endorsement_type_id": 12,
            "field_changes": {
                "CustFName": "Vikram",
                "CustLName": "Desai",
                "MobileNo": "9898112233",
                "Address": "12 Satellite Road, Ahmedabad",
            },
        },
    )
    assert r_own_create.status_code == 201
    own_eid = r_own_create.json()["data"]["endorsement_id"]
    assert r_own_create.json()["data"]["endorsement_type"] == "OWNERSHIP_TRANSFER"
    assert r_own_create.json()["data"]["legacy_endorsement_type_id"] == 12

    await async_client.post(
        f"/api/v1/endorsements/{own_eid}/approve", headers=admin_headers, json={}
    )
    r_own_apply = await async_client.post(
        f"/api/v1/endorsements/{own_eid}/apply", headers=admin_headers, json={}
    )
    assert r_own_apply.status_code == 200
    await db_session.commit()
    await db_session.refresh(policy)
    new_customer_id = int(policy.CustomerId)
    assert new_customer_id != orig_customer_id

    new_cust_row = (
        await db_session.execute(select(Customer).where(Customer.CustomerId == new_customer_id))
    ).scalar_one()
    assert new_cust_row.CustFName == "Vikram"
    assert new_cust_row.CustLName == "Desai"

    # Reverse OWNERSHIP_TRANSFER -> restores orig_customer_id
    r_own_rev = await async_client.post(
        f"/api/v1/endorsements/{own_eid}/reverse",
        headers=admin_headers,
        json={"remarks": "Reverse ownership transfer"},
    )
    assert r_own_rev.status_code == 200
    await db_session.commit()
    await db_session.refresh(policy)
    assert int(policy.CustomerId) == orig_customer_id

    # ------------------------------------------------------------------
    # 3. GAP-P10-002: LedgerMId=1161 (AccTransId=3) & LedgerMId=1878 Fee Split
    # ------------------------------------------------------------------
    r_fin_create = await async_client.post(
        "/api/v1/endorsements",
        headers=admin_headers,
        json={
            "transaction_id": policy.TransanctionId,
            "legacy_endorsement_type_id": 7,  # IDV_CHANGE
            "field_changes": {"SumInsured": "600000.00"},
        },
    )
    assert r_fin_create.status_code == 201
    fin_eid = r_fin_create.json()["data"]["endorsement_id"]
    await async_client.post(
        f"/api/v1/endorsements/{fin_eid}/approve", headers=admin_headers, json={}
    )
    r_fin_apply = await async_client.post(
        f"/api/v1/endorsements/{fin_eid}/apply",
        headers=admin_headers,
        json={
            "remarks": "Apply IDV upward with endorsement fee split",
            "paid_endorsement_fee": "500.00",
            "service_charge": "100.00",
            "from_ledger_id": 102,
            "pay_to_ledger_id": 203,
        },
    )
    assert r_fin_apply.status_code == 200
    await db_session.commit()

    acct_rows = (
        await db_session.execute(
            select(Account).where(Account.TransId == policy.TransanctionId)
        )
    ).scalars().all()

    # Check AccTransId=3 on LedgerMId=1161 with amount = -285.00
    comm_1161 = [
        a for a in acct_rows
        if int(a.AccTransId or 0) == 3 and int(a.LedgerMId or 0) == 1161
    ]
    assert any(Decimal(str(a.amount)) == Decimal("-285.00") for a in comm_1161)

    # Check 3-leg Endorsement Fee split involving LedgerMId=1878 (cmp_amt = 500 - 100 = 400.00)
    fee_1878 = [
        a for a in acct_rows
        if int(a.AccTransId or 0) == 2 and int(a.LedgerMId or 0) == 1878
    ]
    assert any(Decimal(str(a.amount)) == Decimal("-400.00") for a in fee_1878)

    tb_resp = await async_client.get("/api/v1/accounting/trial-balance", headers=admin_headers)
    assert tb_resp.status_code == 200
    assert tb_resp.json()["is_balanced"] is True
    assert Decimal(tb_resp.json()["variance"]) == Decimal("0.00")

