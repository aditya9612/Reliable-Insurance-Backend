"""
Phase 12 End-to-End (E2E) Integration Tests.
Validates complete cross-domain workflow:
Vehicle Hierarchy (Type -> SubType -> Make -> Model -> Variant + Regional Price) -> RTO & Insurer ->
Underwriting Lookups (Addons / PA Owner / Towing / NCB) -> Organizational Masters (Branch / State / District / Bank) ->
Search & Autocomplete -> Quick Duplicate Checks -> Operational Counters & Dashboard Summary.
"""
from decimal import Decimal
import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.master import (
    VehicleType,
    VehicleSubType,
    VehicleMake,
    VehicleModel,
    VehicleVariant,
    RTOMaster,
    InsuranceCompany,
    Branch,
    StateMaster,
    DistrictMaster,
    BankMaster,
)
from app.models.quotation import (
    AddonExtraAmt,
    PAToOwnerDriver,
    InsuranceCompanyWiseTowingChanges,
)
from app.models.customer import Customer
from app.models.vehicle import VehicleDetails
from tests.integration.test_phase7_policy_booking_api import create_user_with_role


@pytest.fixture(autouse=True)
async def cleanup_phase12_e2e_tables(db_session: AsyncSession):
    """Clean test tables before and after E2E execution."""
    await db_session.rollback()
    for tbl in (
        "tbl_transactionpayment",
        "tbl_transaction",
        "tbl_vehicledetails",
        "tbl_customer",
        "tbl_branch",
        "tbl_bank",
        "tbl_district",
        "tbl_state",
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
            "tbl_district",
            "tbl_state",
        ):
            await db_session.execute(text(f"DELETE FROM {tbl};"))
        await db_session.commit()
    except Exception:
        await db_session.rollback()


@pytest.mark.asyncio
async def test_phase12_full_masters_and_search_e2e_flow(
    async_client: AsyncClient,
    db_session: AsyncSession,
):
    """
    Comprehensive E2E workflow exercising Blocks 1-4:
    1. Vehicle Master Chain (Type -> SubType -> Make -> Model -> Variant + Regional Price)
    2. RTO & Insurers Lookups
    3. Underwriting Lookups (Addons, PA Owner Driver, Towing, NCB)
    4. Organizational References (Branch, State, District, Bank)
    5. Search / Autocomplete Typeahead
    6. Duplicate Vehicle Check
    7. Operational Inbox Counters & Dashboard Chart Data
    """
    user, auth_headers = await create_user_with_role(db_session, "ADMIN", branch_id=101)

    # -------------------------------------------------------------------------
    # Setup Domain Entities
    # -------------------------------------------------------------------------
    # 1. State & District
    st = StateMaster(StateName="MAHARASHTRA", isdeleted=0)
    db_session.add(st)
    await db_session.commit()
    await db_session.refresh(st)

    dist = DistrictMaster(DistrictName="MUMBAI", StateID=st.StateID, isdeleted=0)
    db_session.add(dist)

    # 2. Branch & Bank
    br = Branch(BranchName="MUMBAI CENTRAL", BranchCode="MUM01", Address="Nariman Point", isdeleted=0)
    bank = BankMaster(BankName="HDFC BANK LTD", isdeleted=0)
    db_session.add_all([br, bank])

    # 3. Vehicle Hierarchy
    v_type = VehicleType(Veh_Type_Name="TWO WHEELER")
    db_session.add(v_type)
    await db_session.commit()
    await db_session.refresh(v_type)

    v_subtype = VehicleSubType(Veh_Sub_Type_Name="SCOOTER", Veh_Type_ID=v_type.Veh_Type_ID)
    make = VehicleMake(Make_Name="HONDA MOTORS", PvtCar="1", isdeleted=0)
    db_session.add_all([v_subtype, make])
    await db_session.commit()
    await db_session.refresh(make)

    model = VehicleModel(Model_Name="ACTIVA 6G", Make_ID=make.Make_ID, SegmentId=1, isdeleted=0)
    db_session.add(model)
    await db_session.commit()
    await db_session.refresh(model)

    variant = VehicleVariant(
        Model_ID=model.Model_ID,
        Make_Id=make.Make_ID,
        Variance="DLX 110CC",
        CC="110",
        Seating_Capacity="2",
        Wheels="2",
        ExMumbai_Model_Price="85000",
        ExMumbai_Body_Price="82000",
        ExMumbai_Chasis_Price="80000",
    )
    rto = RTOMaster(
        RTOLocation="MUMBAI SOUTH",
        District="MUMBAI",
        REG_code="MH01",
        ClusterId=1,
        zone="A",
        isdeleted=0,
    )
    insurer = InsuranceCompany(
        InsuranceCompany="ICICI LOMBARD",
        NCB="1",
        Cluster="1",
        ZeroDeep="1",
        isdeleted="0",
        IsAppQuotation="1",
        CompImgPath="/logo.png",
        LedgerMId=501,
        ShortName="ICICI",
        PolicyNo="OG",
        len=16,
    )
    db_session.add_all([variant, rto, insurer])
    await db_session.commit()
    await db_session.refresh(variant)
    await db_session.refresh(rto)
    await db_session.refresh(insurer)

    # 4. Underwriting Lookups
    addon = AddonExtraAmt(
        InsuranceCompanyId=insurer.InsuranceCompanyId,
        VehiceTypeId=1,
        makeId=0,
        ModelId=0,
        Age=0,
        NillDep=1500.0,
        SecurePlus=500.0,
        IsDeleted=0,
    )
    pa = PAToOwnerDriver(
        InsuranceCompanyId=insurer.InsuranceCompanyId,
        Rate=350.0,
        TowingCharges=150.0,
        IsDeleted=0,
    )
    towing = InsuranceCompanyWiseTowingChanges(
        InsuranceCompanyId=insurer.InsuranceCompanyId,
        Selection=1.0,
        Rate=250.0,
        GST18=45.0,
        Total=295.0,
        IsDelete=0,
    )
    db_session.add_all([addon, pa, towing])

    # 5. Customer & Vehicle
    cust = Customer(
        CustFName="RAHUL",
        CustLName="VERMA",
        MoblieNo1="9820011223",
        CustomerCode="CUST_MH_001",
        PAN_No="ABCDE9999Z",
        BranchId=101,
        isdeleted="0",
    )
    veh = VehicleDetails(
        RegistrationNo="MH01AA1122",
        ChaiseNo="CHAS_MH01_1122",
        EngineNo="ENG_MH01_1122",
        FinancialYear="2026-2027",
        BranchId=101,
        isdeleted="0",
    )
    db_session.add_all([cust, veh])
    await db_session.commit()
    await db_session.refresh(cust)
    await db_session.refresh(veh)

    # -------------------------------------------------------------------------
    # STEP 1: Verify Vehicle Hierarchy APIs (Block 1)
    # -------------------------------------------------------------------------
    # Types
    r_vt = await async_client.get("/api/v1/masters/vehicle-types", headers=auth_headers)
    assert r_vt.status_code == 200
    assert any(x["Veh_Type_ID"] == v_type.Veh_Type_ID for x in r_vt.json())

    # Sub Types filtered by type
    r_vst = await async_client.get(f"/api/v1/masters/vehicle-sub-types?veh_type_id={v_type.Veh_Type_ID}", headers=auth_headers)
    assert r_vst.status_code == 200
    assert any(x["Veh_Sub_Type_ID"] == v_subtype.Veh_Sub_Type_ID for x in r_vst.json())

    # Makes
    r_mk = await async_client.get("/api/v1/masters/makes?search=HONDA", headers=auth_headers)
    assert r_mk.status_code == 200
    assert any(x["Make_ID"] == make.Make_ID for x in r_mk.json())

    # Models filtered by Make
    r_mod = await async_client.get(f"/api/v1/masters/models?make_id={make.Make_ID}", headers=auth_headers)
    assert r_mod.status_code == 200
    assert any(x["Model_ID"] == model.Model_ID for x in r_mod.json())

    # Variants filtered by Model
    r_var = await async_client.get(f"/api/v1/masters/variants?model_id={model.Model_ID}", headers=auth_headers)
    assert r_var.status_code == 200
    assert any(x["Variant_ID"] == variant.Variant_ID for x in r_var.json())

    # Regional Pricing resolution (Mumbai price)
    r_price = await async_client.get(f"/api/v1/masters/variants/{variant.Variant_ID}/price?city=Mumbai", headers=auth_headers)
    assert r_price.status_code == 200
    p_data = r_price.json()
    assert Decimal(str(p_data["effective_ex_showroom_price"])) == Decimal("85000.00")

    # RTO & Insurer
    r_rto = await async_client.get("/api/v1/masters/rtos?search=MH01", headers=auth_headers)
    assert r_rto.status_code == 200
    assert any(x["REG_code"] == "MH01" for x in r_rto.json())

    r_ins = await async_client.get("/api/v1/masters/insurance-companies?search=ICICI", headers=auth_headers)
    assert r_ins.status_code == 200
    assert any(x["InsuranceCompany"] == "ICICI LOMBARD" for x in r_ins.json())

    # -------------------------------------------------------------------------
    # STEP 2: Verify Underwriting Lookups (Block 2)
    # -------------------------------------------------------------------------
    r_ad = await async_client.get(f"/api/v1/masters/addons?insurance_company_id={insurer.InsuranceCompanyId}", headers=auth_headers)
    assert r_ad.status_code == 200
    assert len(r_ad.json()) >= 1

    r_pa = await async_client.get(f"/api/v1/masters/pa-owner-driver?insurance_company_id={insurer.InsuranceCompanyId}", headers=auth_headers)
    assert r_pa.status_code == 200
    assert any(x["InsuranceCompanyId"] == insurer.InsuranceCompanyId for x in r_pa.json())

    r_tow = await async_client.get(f"/api/v1/masters/towing-rates?insurance_company_id={insurer.InsuranceCompanyId}", headers=auth_headers)
    assert r_tow.status_code == 200
    assert any(x["InsuranceCompanyId"] == insurer.InsuranceCompanyId for x in r_tow.json())

    r_ncb = await async_client.get("/api/v1/masters/ncb-slabs", headers=auth_headers)
    assert r_ncb.status_code == 200
    assert len(r_ncb.json()) == 6

    # -------------------------------------------------------------------------
    # STEP 3: Verify Organizational References (Block 3)
    # -------------------------------------------------------------------------
    r_br = await async_client.get("/api/v1/masters/branches?search=MUMBAI", headers=auth_headers)
    assert r_br.status_code == 200
    assert any(x["BranchCode"] == "MUM01" for x in r_br.json())

    r_st = await async_client.get("/api/v1/masters/states?search=MAHA", headers=auth_headers)
    assert r_st.status_code == 200
    assert any(x["StateName"] == "MAHARASHTRA" for x in r_st.json())

    r_dst = await async_client.get(f"/api/v1/masters/districts?state_id={st.StateID}", headers=auth_headers)
    assert r_dst.status_code == 200
    assert any(x["DistrictName"] == "MUMBAI" for x in r_dst.json())

    r_bk = await async_client.get("/api/v1/masters/banks?search=HDFC", headers=auth_headers)
    assert r_bk.status_code == 200
    assert any(x["BankName"] == "HDFC BANK LTD" for x in r_bk.json())

    # -------------------------------------------------------------------------
    # STEP 4: Verify Search, Autocomplete & Typeahead (Block 4)
    # -------------------------------------------------------------------------
    # Customer typeahead
    s_c = await async_client.get("/api/v1/search/customers?q=RAHUL", headers=auth_headers)
    assert s_c.status_code == 200
    assert any(x["id"] == cust.CustomerId for x in s_c.json()["items"])

    # Vehicle typeahead
    s_v = await async_client.get("/api/v1/search/vehicles?q=MH01AA", headers=auth_headers)
    assert s_v.status_code == 200
    assert any(x["id"] == veh.CustVehId for x in s_v.json()["items"])

    # Unified autocomplete across make, bank, branch
    s_mk = await async_client.get("/api/v1/search/autocomplete?category=make&q=HONDA", headers=auth_headers)
    assert s_mk.status_code == 200
    assert any(x["id"] == make.Make_ID for x in s_mk.json()["items"])

    s_bank = await async_client.get("/api/v1/search/autocomplete?category=bank&q=HDFC", headers=auth_headers)
    assert s_bank.status_code == 200
    assert any(x["id"] == bank.BankId for x in s_bank.json()["items"])

    s_branch = await async_client.get("/api/v1/search/autocomplete?category=branch&q=MUMBAI", headers=auth_headers)
    assert s_branch.status_code == 200
    assert any(x["id"] == br.BranchId for x in s_branch.json()["items"])

    # -------------------------------------------------------------------------
    # STEP 5: Quick Duplicate Check & Operational Health
    # -------------------------------------------------------------------------
    # Duplicate check on registered vehicle (no policy yet -> is_allowed=True)
    c_veh = await async_client.get("/api/v1/search/quick-check/vehicle-no?registration_no=MH01AA1122", headers=auth_headers)
    assert c_veh.status_code == 200
    assert c_veh.json()["is_allowed"] is True

    # Pending operational counters
    r_cnt = await async_client.get("/api/v1/search/counters/pending", headers=auth_headers)
    assert r_cnt.status_code == 200
    assert "operator_pending_entries" in r_cnt.json()

    # Dashboard summary
    r_dash = await async_client.get("/api/v1/search/dashboard/summary?chart_type=premium_summary", headers=auth_headers)
    assert r_dash.status_code == 200
    assert "summary_string" in r_dash.json()

    # Server heartbeat
    r_hb = await async_client.get("/api/v1/search/server-status", headers=auth_headers)
    assert r_hb.status_code == 200
    assert r_hb.json()["status"] == "ACTIVE"
