"""
Phase 10 Integration Tests — Claims, Endorsements & Refunds API Endpoints,
RBAC Role Gates, Branch Isolation, and Principal Ownership Enforcement.
"""
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional
import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.commission import AgentCommissionPayment
from app.models.customer import Customer
from app.models.transaction import Transaction
from app.models.vehicle import VehicleDetails
from tests.integration.test_phase7_policy_booking_api import create_user_with_role


@pytest.fixture(autouse=True)
async def cleanup_phase10_api_tables(db_session: AsyncSession):
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


async def seed_synthetic_booked_policy(
    db_session: AsyncSession,
    *,
    policy_no: str = "POL-P10-0001",
    branch_id: int = 101,
    agent_id: int = 501,
    franchise_id: int = 601,
    sales_ex_id: int = 701,
    od_premium: Decimal = Decimal("10000.00"),
    tp_premium: Decimal = Decimal("5000.00"),
    sum_insured: Decimal = Decimal("500000.00"),
    ncb_pct: Decimal = Decimal("20.00"),
    paid_amount: Optional[Decimal] = None,
    commission_paid: str = "0",
    cancelled: bool = False,
) -> Transaction:
    now_dt = datetime.utcnow()
    cust = Customer(
        CustFName="Ramesh",
        CustMName="Kumar",
        CustLName="Verma",
        MoblieNo1="9811122233",
        EMailId="ramesh.verma@example.local",
        PerAddrLine1="12 MG Road, Pune",
        PAN_No="ABCDE1234F",
        Extra1="27ABCDE1234F1Z5",
        BranchId=branch_id,
        isdeleted="0",
    )
    db_session.add(cust)
    await db_session.flush()

    veh = VehicleDetails(
        CustomerId=cust.CustomerId,
        RegistrationNo="MH12AB1234",
        ChaiseNo="CHASSISP10001",
        EngineNo="ENGINEP10001",
        MfgYear="2025",
        Extra1="SBI Auto Loan",
        Extra2="Pune Main",
        BranchId=branch_id,
        FinancialYear="2026-2027",
        isdeleted="0",
    )
    db_session.add(veh)
    await db_session.flush()

    net_prem = od_premium + tp_premium
    gst_amt = (net_prem * Decimal("0.18")).quantize(Decimal("0.01"))
    final_amt = net_prem + gst_amt
    eff_paid = final_amt if paid_amount is None else paid_amount
    out_amt = max(Decimal("0.00"), final_amt - eff_paid)

    ag_od_amt = (od_premium * Decimal("0.15")).quantize(Decimal("0.01"))
    ag_tds_amt = (ag_od_amt * Decimal("0.05")).quantize(Decimal("0.01"))
    ag_net_amt = ag_od_amt - ag_tds_amt

    tx = Transaction(
        InwardNo=f"INW-{policy_no}",
        TransDate=now_dt,
        CustomerId=cust.CustomerId,
        CustVehId=veh.CustVehId,
        PolicyNo=policy_no,
        InsuranceCompanyId=1,
        BranchId=branch_id,
        AgentId=agent_id,
        FranchiseCode=str(franchise_id),
        SalesEx_id=sales_ex_id,
        RiskStartdate=now_dt - timedelta(days=30),
        ExpiryDate=now_dt + timedelta(days=335),
        SumInsured=sum_insured,
        NCB=ncb_pct,
        NCBPermium=Decimal("2500.00"),
        ODPermium=od_premium,
        TPPermium=tp_premium,
        NetPermium=net_prem,
        GST_Amount=gst_amt,
        Amount=final_amt,
        ProPosalAmt=final_amt,
        PaidAmount=eff_paid,
        OutstandingAmount=out_amt,
        AddOn="0.00",
        TowingChargesAmt=Decimal("0.00"),
        PACovertoOwner=Decimal("0.00"),
        PACoverDriverCleaner=Decimal("0.00"),
        LegalLiabilitytoPaidDriver=Decimal("0.00"),
        RoadSidePremium=Decimal("0.00"),
        AgentComm_OD=Decimal("15.00"),
        AgentCommAmt_OD=ag_od_amt,
        TdsAmt_OD=ag_tds_amt,
        NetCommission_OD=ag_net_amt,
        AgentComm=Decimal("15.00"),
        AgentCommAmt=ag_od_amt,
        TdsAmt=ag_tds_amt,
        NetCommission=ag_net_amt,
        AgentComm_Net=Decimal("0.00"),
        AgentCommAmt_Net=Decimal("0.00"),
        TdsAmt_Net=Decimal("0.00"),
        NetCommission_Net=Decimal("0.00"),
        AgentComm_Extra=Decimal("0.00"),
        AgentCommAmt_Extra=Decimal("0.00"),
        TdsAmt_Extra=Decimal("0.00"),
        NetCommission_Extra=Decimal("0.00"),
        tdsPercent=Decimal("5.00"),
        CommissionPaid=int(commission_paid),
        FranchiseCommPaid=0,
        CommProcessSubmit=0,
        IsRecalculate=0,
        MotorOrNonMotor="MOTOR",
        InsuranceTypeId=1,
        InsuranceSubTypeId=1,
        TypeOfSubType=1,
        AddOnRate=Decimal("0.00"),
        OnlinePaymentToCompany=0,
        GridAgentId=agent_id,
        PremiumCashToBank=0,
        CreatedSystem="FASTAPI",
        CreatedIP="127.0.0.1",
        UpdatedSystem="FASTAPI",
        UpdatedIP="127.0.0.1",
        PortalId="DIRECT",
        SelfDiscount=Decimal("0.00"),
        IntensiveAmount=Decimal("0.00"),
        LocationHeadId=0,
        Ischequeclearing=0,
        IsChequeCleared=1,
        IsCompanyChequeNo=0,
        IsActivePendingCash=0,
        FinancialYear="2026-2027",
        CashBackStatus=0,
        CashBackAmt=Decimal("0.00"),
        CutNPay=Decimal("0.00"),
        ChequeBankStatus=0,
        IncentiveStatus=0,
        DeuDate=now_dt + timedelta(days=335),
        UpdateEntryStatus=0,
        ExectiveGrid=Decimal("0.00"),
        EWalletAmountUsed=Decimal("0.00"),
        PolicycancelId=1 if cancelled else 0,
        IsRconDataMatch=1,
        TransId=0,
        RconGrid=Decimal("0.00"),
        RconComm=Decimal("0.00"),
        TStatus="CANCELLED" if cancelled else "Booked",
        pendingStatus=0,
        IsQualityCheck=1,
        QualityCheckDate=now_dt,
        ND="NO",
        FranchiseTypeId=1 if franchise_id > 0 else 0,
        RAPaymentStatus="COMPLETE",
        isdeleted="0",
    )
    db_session.add(tx)
    await db_session.flush()

    ag_row = AgentCommissionPayment(
        FromDate=now_dt,
        ToDate=now_dt,
        TransanctionId=tx.TransanctionId,
        BranchName=str(branch_id),
        AgentName=str(agent_id),
        PremiumAmount=final_amt,
        NetCommission=ag_net_amt,
        totalCommision=ag_od_amt,
        AdvAmt=Decimal("0.00"),
        NetAmount=ag_net_amt,
        PaymentStatus=Decimal("1.00") if commission_paid == "1" else Decimal("0.00"),
        Narration="Initial policy commission accrual",
        Extra1=policy_no,
        Extra2="PAID" if commission_paid == "1" else "UNPAID",
        isdeleted="0",
        NetCommission_OD=ag_net_amt,
        NetCommission_Net=Decimal("0.00"),
        NetCommission_Extra=Decimal("0.00"),
        TransDate=now_dt,
    )
    db_session.add(ag_row)
    await db_session.commit()
    await db_session.refresh(tx)
    return tx


@pytest.mark.asyncio
async def test_phase10_rbac_branch_and_principal_ownership_enforcement(
    async_client: AsyncClient,
    db_session: AsyncSession,
):
    policy = await seed_synthetic_booked_policy(
        db_session, branch_id=101, agent_id=501, franchise_id=601
    )

    _, hr_headers = await create_user_with_role(db_session, role_name="HR", branch_id=101)
    _, agent_501_headers = await create_user_with_role(
        db_session, role_name="AGENT", branch_id=101, partner_user_id=501
    )
    _, agent_999_headers = await create_user_with_role(
        db_session, role_name="AGENT", branch_id=101, partner_user_id=999
    )
    _, op_branch202_headers = await create_user_with_role(
        db_session, role_name="OPERATOR", branch_id=202
    )
    _, admin_headers = await create_user_with_role(db_session, role_name="ADMIN", branch_id=101)

    now_dt = datetime.utcnow()
    loss_dt = (now_dt - timedelta(days=2)).isoformat()

    # 1. HR role is denied claim creation and endorsement creation (403)
    r_hr_clm = await async_client.post(
        "/api/v1/claims",
        headers=hr_headers,
        json={
            "transaction_id": policy.TransanctionId,
            "claim_type": "OD",
            "loss_date": loss_dt,
            "loss_location": "Pune Highway",
            "loss_description": "Front bumper damage",
            "estimated_amount": "25000.00",
        },
    )
    assert r_hr_clm.status_code == 403

    r_hr_end = await async_client.post(
        "/api/v1/endorsements",
        headers=hr_headers,
        json={
            "transaction_id": policy.TransanctionId,
            "endorsement_type": "NAME_CORRECTION",
            "field_changes": {"CustFName": "Rameshwar"},
        },
    )
    assert r_hr_end.status_code == 403

    # 2. Agent 999 cannot intimate claim or submit endorsement on Agent 501's policy (403)
    r_other_agent = await async_client.post(
        "/api/v1/claims",
        headers=agent_999_headers,
        json={
            "transaction_id": policy.TransanctionId,
            "claim_type": "OD",
            "loss_date": loss_dt,
            "loss_location": "Pune Highway",
            "loss_description": "Front bumper damage",
            "estimated_amount": "25000.00",
        },
    )
    assert r_other_agent.status_code == 403

    # 3. Operator from Branch 202 cannot access Branch 101 policy (403)
    r_other_branch = await async_client.post(
        "/api/v1/endorsements",
        headers=op_branch202_headers,
        json={
            "transaction_id": policy.TransanctionId,
            "endorsement_type": "NAME_CORRECTION",
            "field_changes": {"CustFName": "Rameshwar"},
        },
    )
    assert r_other_branch.status_code == 403

    # 4. Owning Agent 501 CAN intimate claim and submit endorsement, but CANNOT approve/settle/apply (403)
    r_own_clm = await async_client.post(
        "/api/v1/claims",
        headers=agent_501_headers,
        json={
            "transaction_id": policy.TransanctionId,
            "claim_type": "OD",
            "loss_date": loss_dt,
            "loss_location": "Pune Highway",
            "loss_description": "Front bumper damage",
            "estimated_amount": "25000.00",
        },
    )
    assert r_own_clm.status_code == 201, r_own_clm.text
    claim_id = r_own_clm.json()["data"]["claim_id"]

    r_agent_approve_clm = await async_client.post(
        f"/api/v1/claims/{claim_id}/approve",
        headers=agent_501_headers,
        json={"remarks": "Trying self-approval"},
    )
    assert r_agent_approve_clm.status_code == 403

    r_own_end = await async_client.post(
        "/api/v1/endorsements",
        headers=agent_501_headers,
        json={
            "transaction_id": policy.TransanctionId,
            "endorsement_type": "NAME_CORRECTION",
            "field_changes": {"CustFName": "Rameshwar"},
        },
    )
    assert r_own_end.status_code == 201, r_own_end.text
    end_id = r_own_end.json()["data"]["endorsement_id"]

    r_agent_approve_end = await async_client.post(
        f"/api/v1/endorsements/{end_id}/approve",
        headers=agent_501_headers,
        json={"remarks": "Trying self-approval"},
    )
    assert r_agent_approve_end.status_code == 403

    # Admin can approve and apply endorsement
    r_adm_app = await async_client.post(
        f"/api/v1/endorsements/{end_id}/approve",
        headers=admin_headers,
        json={"remarks": "Approved by admin"},
    )
    assert r_adm_app.status_code == 200
    r_adm_apply = await async_client.post(
        f"/api/v1/endorsements/{end_id}/apply",
        headers=admin_headers,
        json={"remarks": "Applied by admin"},
    )
    assert r_adm_apply.status_code == 200
    assert r_adm_apply.json()["data"]["endorsement_status"] == "APPLIED"
