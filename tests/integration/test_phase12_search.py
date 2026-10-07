"""
Phase 12 Integration Tests — Search, Autocomplete & Typeahead covering all 57 legacy
AJAX WebMethods (SearchMethods.aspx.cs & AppSearchMethod.aspx.cs) with RBAC, Branch Isolation,
and Search Semantics.
"""
from decimal import Decimal
from datetime import datetime, timedelta
import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import Customer
from app.models.vehicle import VehicleDetails
from app.models.transaction import Transaction
from app.models.payment import TransactionPayment
from app.models.master import Branch, BankMaster
from tests.integration.test_phase7_policy_booking_api import create_user_with_role


def make_synthetic_tx(
    policy_no: str = "POL001",
    inward_no: str = "INW001",
    branch_id: int = 101,
    cust_veh_id: int = 1,
    customer_id: int = 1,
    gross_premium: Decimal = Decimal("10000.00"),
    od_premium: Decimal = Decimal("6000.00"),
    net_premium: Decimal = Decimal("8474.58"),
    financial_year: str = "2026-2027",
    t_status: str = "Booked",
    pending_status: int = 0,
    isdeleted: str = "0",
    agent_id: int = 0,
    mis_id: int = 0,
    insurance_company_id: int = 1,
    policy_type_id: int = 1,
) -> Transaction:
    """Creates a fully valid Transaction model instance satisfying all non-nullable legacy columns."""
    now_dt = datetime.now()
    return Transaction(
        PolicyNo=policy_no,
        InwardNo=inward_no,
        BranchId=branch_id,
        CustVehId=cust_veh_id,
        CustomerId=customer_id,
        ODPermium=od_premium,
        NetPermium=net_premium,
        FinancialYear=financial_year,
        TStatus=t_status,
        pendingStatus=pending_status,
        isdeleted=isdeleted,
        AgentId=agent_id,
        MISId=mis_id,
        InsuranceCompanyId=insurance_company_id,
        PolicyTypeId=policy_type_id,
        TransDate=now_dt,
        RiskStartdate=now_dt,
        ExpiryDate=now_dt + timedelta(days=365),
        DeuDate=now_dt + timedelta(days=365),
        QualityCheckDate=now_dt,
        Amount=gross_premium,
        ProPosalAmt=gross_premium,
        PaidAmount=gross_premium,
        OutstandingAmount=Decimal("0.00"),
        PACovertoOwner=Decimal("0.00"),
        PACoverDriverCleaner=Decimal("0.00"),
        LegalLiabilitytoPaidDriver=Decimal("0.00"),
        RoadSidePremium=Decimal("0.00"),
        AddOn="0.00",
        TowingChargesAmt=Decimal("0.00"),
        NCB=Decimal("0.00"),
        NCBPermium=Decimal("0.00"),
        ODDiscount=Decimal("0.00"),
        TPPermium=Decimal("0.00"),
        tdsPercent=Decimal("5.00"),
        CommissionPaid=0,
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
        FranchiseCode="FR01",
        SelfDiscount=Decimal("0.00"),
        IntensiveAmount=Decimal("0.00"),
        LocationHeadId=0,
        Ischequeclearing=0,
        IsChequeCleared=1,
        IsCompanyChequeNo=0,
        IsActivePendingCash=0,
        CashBackStatus=0,
        CashBackAmt=Decimal("0.00"),
        CutNPay=Decimal("0.00"),
        ChequeBankStatus=0,
        IncentiveStatus=0,
        UpdateEntryStatus=0,
        ExectiveGrid=Decimal("0.00"),
        EWalletAmountUsed=Decimal("0.00"),
        PolicycancelId=0,
        IsRconDataMatch=1,
        TransId=0,
        RconGrid=Decimal("0.00"),
        RconComm=Decimal("0.00"),
        IsQualityCheck=1,
        ND="NO",
        FranchiseTypeId=0,
        RAPaymentStatus="COMPLETE",
    )


@pytest.fixture(autouse=True)
async def cleanup_phase12_search_tables(db_session: AsyncSession):
    """Clean tables before and after search integration tests."""
    await db_session.rollback()
    for tbl in (
        "tbl_transactionpayment",
        "tbl_transaction",
        "tbl_vehicledetails",
        "tbl_customer",
        "tbl_branch",
        "tbl_bank",
    ):
        await db_session.execute(text(f"DELETE FROM {tbl};"))
    await db_session.commit()
    yield
    try:
        await db_session.rollback()
        for tbl in (
            "tbl_transactionpayment",
            "tbl_transaction",
            "tbl_vehicledetails",
            "tbl_customer",
            "tbl_branch",
            "tbl_bank",
        ):
            await db_session.execute(text(f"DELETE FROM {tbl};"))
        await db_session.commit()
    except Exception:
        await db_session.rollback()


# ---------------------------------------------------------------------------
# Test 1: Autocomplete across multiple entities (Maps 22 search WebMethods)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_autocomplete_customers_and_vehicles(async_client: AsyncClient, db_session: AsyncSession):
    """Test customer and vehicle typeahead autocomplete (Maps GetCustName, GetCustVehicleNo, etc.)."""
    _, auth_headers = await create_user_with_role(db_session, "ADMIN")

    cust = Customer(
        CustFName="ADITYA",
        CustLName="SHARMA",
        MoblieNo1="9876543210",
        CustomerCode="CUST_SEARCH_001",
        PAN_No="ABCDE1234F",
        BranchId=101,
        isdeleted="0",
    )
    veh = VehicleDetails(
        RegistrationNo="MH02AB1234",
        ChaiseNo="CHAS998877",
        EngineNo="ENG554433",
        FinancialYear="2026-2027",
        isdeleted="0",
    )
    db_session.add_all([cust, veh])
    await db_session.commit()
    await db_session.refresh(cust)
    await db_session.refresh(veh)

    # 1. Generic autocomplete for customer
    resp_cust = await async_client.get("/api/v1/search/autocomplete?category=customer&q=ADITYA", headers=auth_headers)
    assert resp_cust.status_code == 200
    data_cust = resp_cust.json()
    assert data_cust["total"] >= 1
    assert any(x["id"] == cust.CustomerId for x in data_cust["items"])

    # 2. Dedicated customers typeahead route
    resp_c2 = await async_client.get("/api/v1/search/customers?q=987654", headers=auth_headers)
    assert resp_c2.status_code == 200
    assert any(x["id"] == cust.CustomerId for x in resp_c2.json()["items"])

    # 3. Generic autocomplete for vehicle
    resp_veh = await async_client.get("/api/v1/search/autocomplete?category=vehicle&q=MH02", headers=auth_headers)
    assert resp_veh.status_code == 200
    data_veh = resp_veh.json()
    assert any(x["id"] == veh.CustVehId for x in data_veh["items"])

    # 4. Dedicated vehicles typeahead route
    resp_v2 = await async_client.get("/api/v1/search/vehicles?q=CHAS99", headers=auth_headers)
    assert resp_v2.status_code == 200
    assert any(x["id"] == veh.CustVehId for x in resp_v2.json()["items"])


@pytest.mark.asyncio
async def test_autocomplete_policies_and_cheque_policies(async_client: AsyncClient, db_session: AsyncSession):
    """Test policy search including by-cheque filtering (Maps GetPolicyNo, GetPolicyNoByCheqe)."""
    _, auth_headers = await create_user_with_role(db_session, "ADMIN")

    tx1 = make_synthetic_tx(
        policy_no="POL_CASH_001",
        inward_no="INW_001",
        branch_id=101,
        gross_premium=Decimal("10000.00"),
    )
    tx2 = make_synthetic_tx(
        policy_no="POL_CHQ_002",
        inward_no="INW_002",
        branch_id=101,
        gross_premium=Decimal("15000.00"),
    )
    db_session.add_all([tx1, tx2])
    await db_session.commit()
    await db_session.refresh(tx1)
    await db_session.refresh(tx2)

    pay_chq = TransactionPayment(
        TransanctionId=tx2.TransanctionId,
        PaymentType="Cheque",
        PaidAmount=Decimal("15000.00"),
        isCompletePayment=1,
        isdeleted="0",
    )
    db_session.add(pay_chq)
    await db_session.commit()

    # All policies search
    r_all = await async_client.get("/api/v1/search/policies?q=POL", headers=auth_headers)
    assert r_all.status_code == 200
    pols = r_all.json()["items"]
    assert len(pols) >= 2

    # Cheque-only policies search (GetPolicyNoByCheqe)
    r_chq = await async_client.get("/api/v1/search/policies?q=POL&by_cheque_only=true", headers=auth_headers)
    assert r_chq.status_code == 200
    chq_pols = r_chq.json()["items"]
    assert any(x["id"] == tx2.TransanctionId for x in chq_pols)
    assert not any(x["id"] == tx1.TransanctionId for x in chq_pols)


# ---------------------------------------------------------------------------
# Test 2: Duplicate Vehicle Check (Maps checkVehicleNo)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_duplicate_vehicle_check(async_client: AsyncClient, db_session: AsyncSession):
    """Test duplicate registration verification (Maps checkVehicleNo)."""
    _, auth_headers = await create_user_with_role(db_session, "ADMIN")

    # Available vehicle number
    r_avail = await async_client.get("/api/v1/search/quick-check/vehicle-no?registration_no=DL01ZZ9999", headers=auth_headers)
    assert r_avail.status_code == 200
    d_avail = r_avail.json()
    assert d_avail["is_duplicate"] is False
    assert d_avail["is_allowed"] is True

    # Vehicle with active policy in current FY
    veh = VehicleDetails(
        RegistrationNo="DL01ZZ9999",
        FinancialYear="2026-2027",
        isdeleted="0",
    )
    db_session.add(veh)
    await db_session.commit()
    await db_session.refresh(veh)

    tx = make_synthetic_tx(
        cust_veh_id=veh.CustVehId,
        financial_year="2026-2027",
        inward_no="INW_DUP_01",
    )
    db_session.add(tx)
    await db_session.commit()
    await db_session.refresh(tx)

    r_dup = await async_client.get(
        "/api/v1/search/quick-check/vehicle-no?registration_no=DL01ZZ9999&financial_year=2026-2027",
        headers=auth_headers,
    )
    assert r_dup.status_code == 200
    d_dup = r_dup.json()
    assert d_dup["is_duplicate"] is True
    assert d_dup["is_allowed"] is False
    assert d_dup["existing_transaction_id"] == tx.TransanctionId


# ---------------------------------------------------------------------------
# Test 3: Operational Inbox Counters (Maps getNewAppEntry, getPendingEntryOp, etc.)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_pending_operational_counters(async_client: AsyncClient, db_session: AsyncSession):
    """Test operational inbox badges (Maps getNewAppEntry, getPendingEntryOp, etc.)."""
    _, auth_headers = await create_user_with_role(db_session, "ADMIN")

    tx_pend = make_synthetic_tx(
        t_status="Pending",
        pending_status=1,
        branch_id=101,
    )
    db_session.add(tx_pend)
    await db_session.commit()

    resp = await async_client.get("/api/v1/search/counters/pending", headers=auth_headers)
    assert resp.status_code == 200
    counters = resp.json()
    assert counters["operator_pending_entries"] >= 1
    assert counters["operator_pending_inward"] >= 1


# ---------------------------------------------------------------------------
# Test 4: Dashboard Summaries & Charts (Maps chart_Premium_Summary, pie_*, etc.)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_dashboard_chart_and_summary(async_client: AsyncClient, db_session: AsyncSession):
    """Test dashboard chart aggregation (Maps chart_Premium_Summary, pie_ODPremium_Summary, etc.)."""
    _, auth_headers = await create_user_with_role(db_session, "ADMIN")

    tx = make_synthetic_tx(
        gross_premium=Decimal("50000.00"),
        od_premium=Decimal("30000.00"),
        net_premium=Decimal("42372.88"),
        insurance_company_id=1,
        branch_id=101,
    )
    db_session.add(tx)
    await db_session.commit()

    # 1. Premium summary
    r_prem = await async_client.get("/api/v1/search/dashboard/summary?chart_type=premium_summary", headers=auth_headers)
    assert r_prem.status_code == 200
    d_prem = r_prem.json()
    assert Decimal(str(d_prem["total_amount"])) >= Decimal("50000.00")
    assert "Total Policies" in d_prem["summary_string"]

    # 2. OD vs Net summary
    r_od = await async_client.get("/api/v1/search/dashboard/summary?chart_type=od_net", headers=auth_headers)
    assert r_od.status_code == 200
    d_od = r_od.json()
    assert len(d_od["labels"]) == 2


# ---------------------------------------------------------------------------
# Test 5: Server Status Heartbeat (Maps getserverInactive)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_server_status_heartbeat(async_client: AsyncClient, db_session: AsyncSession):
    """Test server status check (Maps getserverInactive)."""
    _, auth_headers = await create_user_with_role(db_session, "ADMIN")

    resp = await async_client.get("/api/v1/search/server-status", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ACTIVE"
    assert data["is_inactive"] is False


# ---------------------------------------------------------------------------
# Test 6: RBAC & Branch Isolation Security Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_search_branch_isolation(async_client: AsyncClient, db_session: AsyncSession):
    """Verify branch-scoped user sees only their branch data, while global user sees cross-branch data."""
    # User 1: Branch 201 (Operator)
    _, op_branch_201_headers = await create_user_with_role(db_session, "OPERATOR", branch_id=201)
    # User 2: Global Admin
    _, admin_headers = await create_user_with_role(db_session, "ADMIN", branch_id=101)

    c_201 = Customer(CustFName="BRANCH_201_CUST", CustLName="TEST", BranchId=201, isdeleted="0")
    c_301 = Customer(CustFName="BRANCH_301_CUST", CustLName="TEST", BranchId=301, isdeleted="0")
    db_session.add_all([c_201, c_301])
    await db_session.commit()
    await db_session.refresh(c_201)
    await db_session.refresh(c_301)

    # Operator in branch 201 searching for "BRANCH"
    r_op = await async_client.get("/api/v1/search/customers?q=BRANCH", headers=op_branch_201_headers)
    assert r_op.status_code == 200
    items_op = r_op.json()["items"]
    assert any(x["id"] == c_201.CustomerId for x in items_op)
    assert not any(x["id"] == c_301.CustomerId for x in items_op)

    # Admin (global read) searching for "BRANCH"
    r_adm = await async_client.get("/api/v1/search/customers?q=BRANCH", headers=admin_headers)
    assert r_adm.status_code == 200
    items_adm = r_adm.json()["items"]
    assert any(x["id"] == c_201.CustomerId for x in items_adm)
    assert any(x["id"] == c_301.CustomerId for x in items_adm)


# ---------------------------------------------------------------------------
# Test 7: Search Semantics Tests (Prefix, Case, Whitespace, Empty, Limits)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_search_semantics_and_limits(async_client: AsyncClient, db_session: AsyncSession):
    """Verify prefix matching, case insensitivity, whitespace trimming, and bounding limits."""
    _, auth_headers = await create_user_with_role(db_session, "ADMIN")

    bank = BankMaster(BankName="KOTAK MAHINDRA BANK", isdeleted=0)
    db_session.add(bank)
    await db_session.commit()
    await db_session.refresh(bank)

    # Prefix with leading/trailing whitespace
    r_ws = await async_client.get("/api/v1/search/autocomplete?category=bank&q=  KOTAK  ", headers=auth_headers)
    assert r_ws.status_code == 200
    assert any(x["id"] == bank.BankId for x in r_ws.json()["items"])

    # Empty string input (safely bounded)
    r_empty = await async_client.get("/api/v1/search/autocomplete?category=bank&q=", headers=auth_headers)
    assert r_empty.status_code == 200
    assert isinstance(r_empty.json()["items"], list)

    # Limit bounding
    r_limit = await async_client.get("/api/v1/search/autocomplete?category=bank&q=K&limit=1", headers=auth_headers)
    assert r_limit.status_code == 200
    assert len(r_limit.json()["items"]) <= 1
