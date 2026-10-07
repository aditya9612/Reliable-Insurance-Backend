import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.master import (
    VehicleType,
    VehicleSubType,
    VehicleMake,
    VehicleModel,
    VehicleVariant,
    RTOMaster,
    InsuranceCompany,
)
from app.repositories.master import (
    VehicleTypeRepository,
    VehicleSubTypeRepository,
    VehicleMakeRepository,
    VehicleModelRepository,
    VehicleVariantRepository,
    RTORepository,
    InsuranceCompanyRepository,
)


@pytest.mark.asyncio
async def test_master_database_isolation_safety(db_session: AsyncSession):
    """
    CRITICAL ARCHITECTURAL CONTRACT:
    The master repository tests must STRICTLY execute against the independent local
    'reliable_insurance_dev' database. It MUST NEVER communicate with legacy production
    database 'brahmainsurance' or remote hosts.
    """
    result = await db_session.execute(text("SELECT DATABASE()"))
    current_db = result.scalar()
    assert current_db == "reliable_insurance_dev", f"Safety violation: unexpected DB {current_db}"
    assert "localhost" in settings.DATABASE_URL or "127.0.0.1" in settings.DATABASE_URL
    assert "brahmainsurance" not in settings.DATABASE_URL
    assert "103.149.199.250" not in settings.DATABASE_URL


@pytest.mark.asyncio
async def test_vehicle_type_repository_crud(db_session: AsyncSession):
    """Verify VehicleTypeRepository create, get_by_id, and get_by_name."""
    repo = VehicleTypeRepository(db_session)

    vt = VehicleType(
        Veh_Type_Name="TEST_PVT_CAR",
        IsAppQuotation=1,
        Comprehensive="Comprehensive",
        TP="ThirdParty",
    )
    created = await repo.create(vt)
    assert created.Veh_Type_ID is not None

    fetched = await repo.get_by_id(created.Veh_Type_ID)
    assert fetched is not None
    assert fetched.Veh_Type_Name == "TEST_PVT_CAR"

    by_name = await repo.get_by_name("TEST_PVT_CAR")
    assert by_name is not None
    assert by_name.Veh_Type_ID == created.Veh_Type_ID


@pytest.mark.asyncio
async def test_vehicle_sub_type_repository_hierarchy(db_session: AsyncSession):
    """Verify VehicleSubTypeRepository list_by_type_id linkage."""
    vt_repo = VehicleTypeRepository(db_session)
    sub_repo = VehicleSubTypeRepository(db_session)

    vt = await vt_repo.create(VehicleType(Veh_Type_Name="TEST_COMMERCIAL_CATEGORY"))

    sub1 = await sub_repo.create(
        VehicleSubType(Veh_Sub_Type_Name="TEST_SUB_HATCHBACK", Veh_Type_ID=vt.Veh_Type_ID)
    )
    sub2 = await sub_repo.create(
        VehicleSubType(Veh_Sub_Type_Name="TEST_SUB_SEDAN", Veh_Type_ID=vt.Veh_Type_ID)
    )

    sub_types = await sub_repo.list_by_type_id(vt.Veh_Type_ID)
    sub_ids = [s.Veh_Sub_Type_ID for s in sub_types]
    assert sub1.Veh_Sub_Type_ID in sub_ids
    assert sub2.Veh_Sub_Type_ID in sub_ids


@pytest.mark.asyncio
async def test_vehicle_make_repository_active_filter(db_session: AsyncSession):
    """Verify VehicleMakeRepository list_active filters out isdeleted=1."""
    repo = VehicleMakeRepository(db_session)

    make_active = await repo.create(
        VehicleMake(Make_Name="TEST_ACTIVE_MAKE", isdeleted=0, PvtCar="1")
    )
    make_deleted = await repo.create(
        VehicleMake(Make_Name="TEST_DELETED_MAKE", isdeleted=1, PvtCar="0")
    )

    active_makes = await repo.list_active()
    active_ids = [m.Make_ID for m in active_makes]

    assert make_active.Make_ID in active_ids
    assert make_deleted.Make_ID not in active_ids


@pytest.mark.asyncio
async def test_vehicle_model_repository_filtering(db_session: AsyncSession):
    """Verify VehicleModelRepository list_by_make_id filters by make and isdeleted."""
    make_repo = VehicleMakeRepository(db_session)
    model_repo = VehicleModelRepository(db_session)

    make = await make_repo.create(VehicleMake(Make_Name="TEST_MAKE_FOR_MODEL", isdeleted=0))

    model_active = await model_repo.create(
        VehicleModel(
            Make_ID=make.Make_ID,
            Model_Name="TEST_MODEL_ACTIVE",
            SegmentId=1,
            isdeleted=0,
        )
    )
    model_deleted = await model_repo.create(
        VehicleModel(
            Make_ID=make.Make_ID,
            Model_Name="TEST_MODEL_DELETED",
            SegmentId=1,
            isdeleted=1,
        )
    )

    models = await model_repo.list_by_make_id(make.Make_ID)
    model_ids = [m.Model_ID for m in models]

    assert model_active.Model_ID in model_ids
    assert model_deleted.Model_ID not in model_ids


@pytest.mark.asyncio
async def test_vehicle_variant_repository_pricing_matrix(db_session: AsyncSession):
    """Verify VehicleVariantRepository list_by_model_id and pricing column storage."""
    make_repo = VehicleMakeRepository(db_session)
    model_repo = VehicleModelRepository(db_session)
    variant_repo = VehicleVariantRepository(db_session)

    make = await make_repo.create(VehicleMake(Make_Name="TEST_MAKE_VARIANT", isdeleted=0))
    model = await model_repo.create(
        VehicleModel(Make_ID=make.Make_ID, Model_Name="TEST_MODEL_VARIANT", SegmentId=2, isdeleted=0)
    )

    variant = await variant_repo.create(
        VehicleVariant(
            Model_ID=model.Model_ID,
            Make_Id=make.Make_ID,
            Variance="TEST_VARIANT_ZXI",
            CC="1197",
            Seating_Capacity="5",
            Wheels="4",
            ExMumbai_Body_Price="750000",
            ExMumbai_Model_Price="800000",
            ExNewDelhi_Body_Price="740000",
            ExBangalore_Body_Price="760000",
        )
    )
    assert variant.Variant_ID is not None

    variants = await variant_repo.list_by_model_id(model.Model_ID)
    assert len(variants) >= 1
    found = [v for v in variants if v.Variant_ID == variant.Variant_ID][0]
    assert found.Variance == "TEST_VARIANT_ZXI"
    assert found.ExMumbai_Body_Price == "750000"
    assert found.ExNewDelhi_Body_Price == "740000"
    assert found.ExBangalore_Body_Price == "760000"


@pytest.mark.asyncio
async def test_rto_repository_lookup(db_session: AsyncSession):
    """Verify RTORepository lookup by registration code and active list."""
    repo = RTORepository(db_session)

    rto = await repo.create(
        RTOMaster(
            RTOLocation="TEST MUMBAI CENTRAL",
            District="MUMBAI",
            REG_code="MH99TEST",
            ClusterId=1,
            isdeleted=0,
        )
    )
    assert rto.RTOId is not None

    fetched = await repo.get_by_reg_code("MH99TEST")
    assert fetched is not None
    assert fetched.RTOId == rto.RTOId
    assert fetched.District == "MUMBAI"

    active_rtos = await repo.list_active()
    assert any(r.RTOId == rto.RTOId for r in active_rtos)


@pytest.mark.asyncio
async def test_insurance_company_repository_active_filter(db_session: AsyncSession):
    """Verify InsuranceCompanyRepository list_active filters on isdeleted='0' and LedgerMId != 0."""
    repo = InsuranceCompanyRepository(db_session)

    ic_active = await repo.create(
        InsuranceCompany(
            InsuranceCompany="TEST_ICICI_LOMBARD",
            NCB="Yes",
            Cluster="1",
            ZeroDeep="Yes",
            isdeleted="0",
            IsAppQuotation="1",
            CompImgPath="/logos/icici.png",
            LedgerMId=105,
            ShortName="ICICI",
            PolicyNo="POL-TEST-100",
            len=10,
        )
    )

    ic_deleted = await repo.create(
        InsuranceCompany(
            InsuranceCompany="TEST_DELETED_INSURER",
            NCB="No",
            Cluster="1",
            ZeroDeep="No",
            isdeleted="1",
            IsAppQuotation="0",
            CompImgPath="/logos/deleted.png",
            LedgerMId=106,
            ShortName="DEL",
            PolicyNo="POL-TEST-DEL",
            len=10,
        )
    )

    ic_zero_ledger = await repo.create(
        InsuranceCompany(
            InsuranceCompany="TEST_ZERO_LEDGER_INSURER",
            NCB="No",
            Cluster="1",
            ZeroDeep="No",
            isdeleted="0",
            IsAppQuotation="1",
            CompImgPath="/logos/zero.png",
            LedgerMId=0,
            ShortName="ZERO",
            PolicyNo="POL-TEST-ZERO",
            len=10,
        )
    )

    active_companies = await repo.list_active()
    active_ids = [c.InsuranceCompanyId for c in active_companies]

    assert ic_active.InsuranceCompanyId in active_ids
    assert ic_deleted.InsuranceCompanyId not in active_ids
    assert ic_zero_ledger.InsuranceCompanyId not in active_ids
