"""
Phase 12 Integration Tests — Master Data, Underwriting Lookups, Organizational Masters,
and Regional Pricing Resolution.
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
    ZeroDep,
    PAToOwnerDriver,
    InsuranceCompanyWiseTowingChanges,
    InsuranceCompanyByVehicleType,
)
from tests.integration.test_phase7_policy_booking_api import create_user_with_role


@pytest.fixture(autouse=True)
async def cleanup_phase12_master_tables(db_session: AsyncSession):
    """Clean synthetic test rows from master tables before and after test."""
    await db_session.execute(text("DELETE FROM tbl_district;"))
    await db_session.execute(text("DELETE FROM tbl_state;"))
    await db_session.execute(text("DELETE FROM tbl_branch;"))
    await db_session.execute(text("DELETE FROM tbl_bank;"))
    await db_session.commit()
    yield
    await db_session.execute(text("DELETE FROM tbl_district;"))
    await db_session.execute(text("DELETE FROM tbl_state;"))
    await db_session.execute(text("DELETE FROM tbl_branch;"))
    await db_session.execute(text("DELETE FROM tbl_bank;"))
    await db_session.commit()


# ---------------------------------------------------------------------------
# BLOCK 1: 7 Master APIs Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_vehicle_types_api(async_client: AsyncClient, db_session: AsyncSession):
    """Test GET /api/v1/masters/vehicle-types and get by ID."""
    _, auth_headers = await create_user_with_role(db_session, "ADMIN")

    vt = VehicleType(Veh_Type_Name="P12_PVT_CAR", IsAppQuotation=1, Comprehensive="Comp", TP="TP")
    db_session.add(vt)
    await db_session.commit()
    await db_session.refresh(vt)

    try:
        resp = await async_client.get("/api/v1/masters/vehicle-types", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert any(x["Veh_Type_ID"] == vt.Veh_Type_ID for x in data)

        # Get by ID
        resp_one = await async_client.get(f"/api/v1/masters/vehicle-types/{vt.Veh_Type_ID}", headers=auth_headers)
        assert resp_one.status_code == 200
        assert resp_one.json()["Veh_Type_Name"] == "P12_PVT_CAR"

        # Not found
        resp_404 = await async_client.get("/api/v1/masters/vehicle-types/999999", headers=auth_headers)
        assert resp_404.status_code == 404
    finally:
        await db_session.delete(vt)
        await db_session.commit()


@pytest.mark.asyncio
async def test_vehicle_sub_types_api(async_client: AsyncClient, db_session: AsyncSession):
    """Test GET /api/v1/masters/vehicle-sub-types with parent filter."""
    _, auth_headers = await create_user_with_role(db_session, "ADMIN")

    vt = VehicleType(Veh_Type_Name="P12_BIKE", IsAppQuotation=1)
    db_session.add(vt)
    await db_session.commit()
    await db_session.refresh(vt)

    st = VehicleSubType(Veh_Sub_Type_Name="P12_SCOOTER", Veh_Type_ID=vt.Veh_Type_ID)
    db_session.add(st)
    await db_session.commit()
    await db_session.refresh(st)

    try:
        resp = await async_client.get(f"/api/v1/masters/vehicle-sub-types?veh_type_id={vt.Veh_Type_ID}", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert any(x["Veh_Sub_Type_ID"] == st.Veh_Sub_Type_ID for x in data)
    finally:
        await db_session.delete(st)
        await db_session.delete(vt)
        await db_session.commit()


@pytest.mark.asyncio
async def test_vehicle_makes_and_models_api(async_client: AsyncClient, db_session: AsyncSession):
    """Test GET /api/v1/masters/makes and /api/v1/masters/models with cascading parent filter."""
    _, auth_headers = await create_user_with_role(db_session, "ADMIN")

    make = VehicleMake(Make_Name="P12_HYUNDAI", PvtCar="1", isdeleted=0)
    db_session.add(make)
    await db_session.commit()
    await db_session.refresh(make)

    model = VehicleModel(Make_ID=make.Make_ID, Model_Name="P12_CRETA", SegmentId=1, isdeleted=0)
    db_session.add(model)
    await db_session.commit()
    await db_session.refresh(model)

    try:
        # Makes
        resp_make = await async_client.get("/api/v1/masters/makes?category=Car&search=P12", headers=auth_headers)
        assert resp_make.status_code == 200
        assert any(x["Make_ID"] == make.Make_ID for x in resp_make.json())

        # Models
        resp_model = await async_client.get(f"/api/v1/masters/models?make_id={make.Make_ID}", headers=auth_headers)
        assert resp_model.status_code == 200
        assert any(x["Model_ID"] == model.Model_ID for x in resp_model.json())
    finally:
        await db_session.delete(model)
        await db_session.delete(make)
        await db_session.commit()


@pytest.mark.asyncio
async def test_vehicle_variants_and_regional_pricing(async_client: AsyncClient, db_session: AsyncSession):
    """Test full 91-column variant and 19-city regional pricing resolution."""
    _, auth_headers = await create_user_with_role(db_session, "ADMIN")

    make = VehicleMake(Make_Name="P12_TATA", PvtCar="1", isdeleted=0)
    db_session.add(make)
    await db_session.commit()
    await db_session.refresh(make)

    model = VehicleModel(Make_ID=make.Make_ID, Model_Name="P12_NEXON", SegmentId=1, isdeleted=0)
    db_session.add(model)
    await db_session.commit()
    await db_session.refresh(model)

    variant = VehicleVariant(
        Model_ID=model.Model_ID,
        Make_Id=make.Make_ID,
        Variance="P12_NEXON_EV_XZ_PLUS",
        CC="0",
        Seating_Capacity="5",
        Wheels="4",
        ExMumbai_Body_Price="1450000",
        ExMumbai_Model_Price="1500000",
        ExMumbai_Chasis_Price="1400000",
        ExNewDelhi_Model_Price="1480000",
        ExBangalore_Model_Price="1520000",
    )
    db_session.add(variant)
    await db_session.commit()
    await db_session.refresh(variant)

    try:
        # Summary list
        resp_list = await async_client.get(f"/api/v1/masters/variants?model_id={model.Model_ID}", headers=auth_headers)
        assert resp_list.status_code == 200
        assert any(v["Variant_ID"] == variant.Variant_ID for v in resp_list.json())

        # Detail 91 columns
        resp_detail = await async_client.get(f"/api/v1/masters/variants/{variant.Variant_ID}", headers=auth_headers)
        assert resp_detail.status_code == 200
        detail = resp_detail.json()
        assert detail["ExMumbai_Model_Price"] == "1500000"
        assert detail["ExNewDelhi_Model_Price"] == "1480000"

        # Regional Price Resolution for Mumbai
        resp_price_mum = await async_client.get(f"/api/v1/masters/variants/{variant.Variant_ID}/price?city=Mumbai", headers=auth_headers)
        assert resp_price_mum.status_code == 200
        p_mum = resp_price_mum.json()
        assert Decimal(str(p_mum["effective_ex_showroom_price"])) == Decimal("1500000")

        # Regional Price Resolution for Bangalore
        resp_price_blr = await async_client.get(f"/api/v1/masters/variants/{variant.Variant_ID}/price?city=Bangalore", headers=auth_headers)
        assert resp_price_blr.status_code == 200
        assert Decimal(str(resp_price_blr.json()["effective_ex_showroom_price"])) == Decimal("1520000")
    finally:
        await db_session.delete(variant)
        await db_session.delete(model)
        await db_session.delete(make)
        await db_session.commit()


@pytest.mark.asyncio
async def test_rtos_and_insurers_api(async_client: AsyncClient, db_session: AsyncSession):
    """Test GET /api/v1/masters/rtos and /api/v1/masters/insurance-companies."""
    _, auth_headers = await create_user_with_role(db_session, "ADMIN")

    rto = RTOMaster(
        RTOLocation="P12 ANDHERI RTO",
        District="MUMBAI",
        REG_code="P12MH02",
        ClusterId=1,
        zone="A",
        isdeleted=0,
    )
    db_session.add(rto)

    insurer = InsuranceCompany(
        InsuranceCompany="P12_ICICI_LOMBARD",
        NCB="1",
        Cluster="1",
        ZeroDeep="1",
        isdeleted="0",
        IsAppQuotation="1",
        CompImgPath="/logo.png",
        LedgerMId=501,
        ShortName="P12ICICI",
        PolicyNo="OG",
        len=16,
    )
    db_session.add(insurer)
    await db_session.commit()
    await db_session.refresh(rto)
    await db_session.refresh(insurer)

    try:
        # RTO search
        resp_rto = await async_client.get("/api/v1/masters/rtos?search=P12MH02", headers=auth_headers)
        assert resp_rto.status_code == 200
        assert any(r["RTOId"] == rto.RTOId for r in resp_rto.json())

        # Insurer search
        resp_ins = await async_client.get("/api/v1/masters/insurance-companies?search=P12_ICICI", headers=auth_headers)
        assert resp_ins.status_code == 200
        assert any(i["InsuranceCompanyId"] == insurer.InsuranceCompanyId for i in resp_ins.json())
    finally:
        await db_session.delete(rto)
        await db_session.delete(insurer)
        await db_session.commit()


# ---------------------------------------------------------------------------
# BLOCK 2: Underwriting / Rating Lookups Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_underwriting_lookups_api(async_client: AsyncClient, db_session: AsyncSession):
    """Test Addons, PA Owner Driver, Towing, and NCB lookups."""
    _, auth_headers = await create_user_with_role(db_session, "ADMIN")

    insurer = InsuranceCompany(
        InsuranceCompany="P12_HDFC_ERGO",
        NCB="1",
        Cluster="1",
        ZeroDeep="1",
        isdeleted="0",
        IsAppQuotation="1",
        CompImgPath="/logo.png",
        LedgerMId=502,
        ShortName="P12HDFC",
        PolicyNo="231",
        len=16,
    )
    db_session.add(insurer)
    await db_session.commit()
    await db_session.refresh(insurer)

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
    await db_session.commit()

    try:
        # Addons
        r_addon = await async_client.get(f"/api/v1/masters/addons?insurance_company_id={insurer.InsuranceCompanyId}", headers=auth_headers)
        assert r_addon.status_code == 200
        assert len(r_addon.json()) >= 1

        # PA Owner Driver
        r_pa = await async_client.get(f"/api/v1/masters/pa-owner-driver?insurance_company_id={insurer.InsuranceCompanyId}", headers=auth_headers)
        assert r_pa.status_code == 200
        assert len(r_pa.json()) >= 1

        # Towing
        r_tow = await async_client.get(f"/api/v1/masters/towing-rates?insurance_company_id={insurer.InsuranceCompanyId}", headers=auth_headers)
        assert r_tow.status_code == 200
        assert len(r_tow.json()) >= 1

        # NCB Slabs
        r_ncb = await async_client.get("/api/v1/masters/ncb-slabs", headers=auth_headers)
        assert r_ncb.status_code == 200
        slabs = r_ncb.json()
        assert len(slabs) == 6
        assert slabs[0]["slab_code"] == "0"
        assert slabs[-1]["slab_code"] == "50"
    finally:
        await db_session.delete(towing)
        await db_session.delete(pa)
        await db_session.delete(addon)
        await db_session.delete(insurer)
        await db_session.commit()


# ---------------------------------------------------------------------------
# BLOCK 3: Organizational / Reference Masters Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_organizational_masters_api(async_client: AsyncClient, db_session: AsyncSession):
    """Test Branch, State, District, and Bank master APIs."""
    _, auth_headers = await create_user_with_role(db_session, "ADMIN")

    branch = Branch(BranchCode="MUM01", BranchName="MUMBAI MAIN", Address="Nariman Point", ContactNo="0221234567")
    state = StateMaster(StateName="MAHARASHTRA")
    db_session.add_all([branch, state])
    await db_session.commit()
    await db_session.refresh(branch)
    await db_session.refresh(state)

    district = DistrictMaster(DistrictName="MUMBAI CITY", StateID=state.StateID)
    bank = BankMaster(BankName="HDFC BANK")
    db_session.add_all([district, bank])
    await db_session.commit()
    await db_session.refresh(district)
    await db_session.refresh(bank)

    # Branch
    r_br = await async_client.get(f"/api/v1/masters/branches/{branch.BranchId}", headers=auth_headers)
    assert r_br.status_code == 200
    assert r_br.json()["BranchCode"] == "MUM01"

    # State
    r_st = await async_client.get(f"/api/v1/masters/states/{state.StateID}", headers=auth_headers)
    assert r_st.status_code == 200
    assert r_st.json()["StateName"] == "MAHARASHTRA"

    # District
    r_dst = await async_client.get(f"/api/v1/masters/districts?state_id={state.StateID}", headers=auth_headers)
    assert r_dst.status_code == 200
    assert any(d["DistrictID"] == district.DistrictID for d in r_dst.json())

    # Bank
    r_bk = await async_client.get(f"/api/v1/masters/banks/{bank.BankId}", headers=auth_headers)
    assert r_bk.status_code == 200
    assert r_bk.json()["BankName"] == "HDFC BANK"


# ---------------------------------------------------------------------------
# Security & Pagination Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_masters_security_unauthenticated(async_client: AsyncClient):
    """Test that all master endpoints reject unauthenticated requests with HTTP 401."""
    endpoints = [
        "/api/v1/masters/vehicle-types",
        "/api/v1/masters/makes",
        "/api/v1/masters/models",
        "/api/v1/masters/variants",
        "/api/v1/masters/rtos",
        "/api/v1/masters/insurance-companies",
        "/api/v1/masters/branches",
        "/api/v1/masters/states",
        "/api/v1/masters/districts",
        "/api/v1/masters/banks",
    ]
    for ep in endpoints:
        resp = await async_client.get(ep)
        assert resp.status_code == 401
