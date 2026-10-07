import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.customer import Customer
from app.models.vehicle import VehicleDetails
from app.repositories.customer import CustomerRepository
from app.repositories.vehicle import VehicleRepository


@pytest.mark.asyncio
async def test_customer_vehicle_db_isolation_safety(db_session: AsyncSession):
    """
    CRITICAL ARCHITECTURAL CONTRACT:
    The tests must STRICTLY execute against the independent local
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
async def test_customer_repository_name_search_and_branch_scoping(db_session: AsyncSession):
    """
    Verify CustomerRepository search_by_name:
    - Substring matching across CustFName, CustMName, CustLName
    - Branch scoping (branch_id=0 for all, branch_id>0 for branch filter)
    - Excludes soft-deleted records (isdeleted='1')
    """
    repo = CustomerRepository(db_session)

    c1 = await repo.create(
        Customer(
            CustomerCode="CUST-SEARCH-001",
            CustFName="Anil",
            CustMName="Kumar",
            CustLName="Verma",
            BranchId=1,
            isdeleted="0",
        )
    )
    c2 = await repo.create(
        Customer(
            CustomerCode="CUST-SEARCH-002",
            CustFName="Sunil",
            CustMName="Kumar",
            CustLName="Sharma",
            BranchId=2,
            isdeleted="0",
        )
    )
    c_deleted = await repo.create(
        Customer(
            CustomerCode="CUST-SEARCH-003",
            CustFName="Pankaj",
            CustMName="Kumar",
            CustLName="Verma",
            BranchId=1,
            isdeleted="1",
        )
    )

    # Search Kumar across all branches (branch_id=0)
    all_results = await repo.search_by_name("Kumar", branch_id=0)
    all_ids = [c.CustomerId for c in all_results]
    assert c1.CustomerId in all_ids
    assert c2.CustomerId in all_ids
    assert c_deleted.CustomerId not in all_ids  # soft-deleted excluded

    # Search Kumar scoped to Branch 1
    branch1_results = await repo.search_by_name("Kumar", branch_id=1)
    b1_ids = [c.CustomerId for c in branch1_results]
    assert c1.CustomerId in b1_ids
    assert c2.CustomerId not in b1_ids


@pytest.mark.asyncio
async def test_customer_repository_duplicate_mobile_allowed(db_session: AsyncSession):
    """
    CRITICAL EMPIRICAL PARITY TEST:
    In the legacy production database, MoblieNo1 is NOT unique (47,704 unique values across 221,118 rows).
    Multiple customers with the identical phone number MUST persist without error,
    and get_by_mobile MUST return a collection of all matching customers.
    """
    repo = CustomerRepository(db_session)
    shared_mobile = "9988776655"

    cust1 = await repo.create(
        Customer(
            CustomerCode="CUST-MOB-001",
            CustFName="First",
            CustLName="User",
            MoblieNo1=shared_mobile,
            BranchId=1,
            isdeleted="0",
        )
    )
    cust2 = await repo.create(
        Customer(
            CustomerCode="CUST-MOB-002",
            CustFName="Second",
            CustLName="User",
            MoblieNo1=shared_mobile,
            BranchId=1,
            isdeleted="0",
        )
    )

    # Both customers should exist and be retrieved by mobile
    results = await repo.get_by_mobile(shared_mobile)
    result_ids = [c.CustomerId for c in results]
    assert cust1.CustomerId in result_ids
    assert cust2.CustomerId in result_ids
    assert len(result_ids) >= 2


@pytest.mark.asyncio
async def test_customer_repository_code_uniqueness_enforced(db_session: AsyncSession):
    """
    Verify CustomerCode_UNIQUE index enforces uniqueness at database layer.
    Attempting to insert two customers with duplicate CustomerCode raises IntegrityError.
    """
    repo = CustomerRepository(db_session)
    unique_code = "CUST-UNIQUE-TEST-001"

    cust1 = await repo.create(
        Customer(
            CustomerCode=unique_code,
            CustFName="Original",
            BranchId=1,
            isdeleted="0",
        )
    )
    assert cust1.CustomerId is not None

    # Fetch by code
    fetched = await repo.get_by_code(unique_code)
    assert fetched is not None
    assert fetched.CustomerId == cust1.CustomerId

    # Attempt duplicate insert must fail due to unique index
    dup_customer = Customer(
        CustomerCode=unique_code,
        CustFName="Duplicate",
        BranchId=1,
        isdeleted="0",
    )
    with pytest.raises(IntegrityError):
        await repo.create(dup_customer)

    # Roll back session after expected error
    await db_session.rollback()


@pytest.mark.asyncio
async def test_customer_repository_list_by_branch(db_session: AsyncSession):
    """Verify list_by_branch filters customers strictly by BranchId."""
    repo = CustomerRepository(db_session)

    b10_cust = await repo.create(
        Customer(
            CustomerCode="CUST-BR-10",
            CustFName="Branch10User",
            BranchId=10,
            isdeleted="0",
        )
    )
    b20_cust = await repo.create(
        Customer(
            CustomerCode="CUST-BR-20",
            CustFName="Branch20User",
            BranchId=20,
            isdeleted="0",
        )
    )

    b10_list = await repo.list_by_branch(branch_id=10)
    b10_ids = [c.CustomerId for c in b10_list]
    assert b10_cust.CustomerId in b10_ids
    assert b20_cust.CustomerId not in b10_ids


@pytest.mark.asyncio
async def test_vehicle_repository_non_unique_registration_allowed(db_session: AsyncSession):
    """
    CRITICAL EMPIRICAL PARITY TEST:
    RegistrationNo is NOT globally unique across the database.
    Only 169,418 unique registration numbers exist across 213,562 rows (renewals across FinancialYear).
    Multiple vehicles with identical RegistrationNo MUST persist cleanly,
    and search_by_registration MUST return all matching records.
    """
    cust_repo = CustomerRepository(db_session)
    veh_repo = VehicleRepository(db_session)

    cust = await cust_repo.create(
        Customer(
            CustomerCode="CUST-VEH-OWNER",
            CustFName="Vehicle",
            CustLName="Owner",
            BranchId=1,
            isdeleted="0",
        )
    )

    shared_reg = "MH14GH9999"

    # Year 1 policy vehicle
    veh_y1 = await veh_repo.create(
        VehicleDetails(
            CustomerId=cust.CustomerId,
            RegistrationNo=shared_reg,
            ChaiseNo="CHASSIS-Y1",
            EngineNo="ENG-Y1",
            FinancialYear="2023-2024",
            BranchId=1,
            isdeleted="0",
        )
    )

    # Year 2 renewal vehicle
    veh_y2 = await veh_repo.create(
        VehicleDetails(
            CustomerId=cust.CustomerId,
            RegistrationNo=shared_reg,
            ChaiseNo="CHASSIS-Y2",
            EngineNo="ENG-Y2",
            FinancialYear="2024-2025",
            BranchId=1,
            isdeleted="0",
        )
    )

    # Search should return both vehicles
    reg_results = await veh_repo.search_by_registration(shared_reg)
    reg_ids = [v.CustVehId for v in reg_results]
    assert veh_y1.CustVehId in reg_ids
    assert veh_y2.CustVehId in reg_ids
    assert len(reg_ids) >= 2

    # Scoped by financial year check
    fy24_results = await veh_repo.check_registration_in_fy(shared_reg, "2024-2025")
    fy24_ids = [v.CustVehId for v in fy24_results]
    assert veh_y2.CustVehId in fy24_ids
    assert veh_y1.CustVehId not in fy24_ids


@pytest.mark.asyncio
async def test_vehicle_repository_chassis_search_and_duplicate_allowance(db_session: AsyncSession):
    """
    Verify search_by_chassis returns collections and allows duplicate chassis numbers
    (e.g., default fallback values like '0' or 'NA' found extensively in legacy data).
    """
    veh_repo = VehicleRepository(db_session)
    shared_chassis = "CHASSIS-DUP-12345"

    v1 = await veh_repo.create(
        VehicleDetails(
            CustomerId=1,
            RegistrationNo="MH01AA1111",
            ChaiseNo=shared_chassis,
            FinancialYear="2024-2025",
            isdeleted="0",
        )
    )
    v2 = await veh_repo.create(
        VehicleDetails(
            CustomerId=2,
            RegistrationNo="MH01AA2222",
            ChaiseNo=shared_chassis,
            FinancialYear="2024-2025",
            isdeleted="0",
        )
    )

    results = await veh_repo.search_by_chassis(shared_chassis)
    chassis_ids = [v.CustVehId for v in results]
    assert v1.CustVehId in chassis_ids
    assert v2.CustVehId in chassis_ids
    assert len(chassis_ids) >= 2


@pytest.mark.asyncio
async def test_vehicle_repository_list_by_customer_id(db_session: AsyncSession):
    """Verify list_by_customer_id returns only active vehicles belonging to target customer."""
    veh_repo = VehicleRepository(db_session)
    target_cust_id = 99991

    v_active1 = await veh_repo.create(
        VehicleDetails(
            CustomerId=target_cust_id,
            RegistrationNo="MH04AA0001",
            ChaiseNo="CH-001",
            FinancialYear="2024-2025",
            isdeleted="0",
        )
    )
    v_active2 = await veh_repo.create(
        VehicleDetails(
            CustomerId=target_cust_id,
            RegistrationNo="MH04AA0002",
            ChaiseNo="CH-002",
            FinancialYear="2024-2025",
            isdeleted="0",
        )
    )
    v_other = await veh_repo.create(
        VehicleDetails(
            CustomerId=99992,
            RegistrationNo="MH04AA0003",
            ChaiseNo="CH-003",
            FinancialYear="2024-2025",
            isdeleted="0",
        )
    )
    v_deleted = await veh_repo.create(
        VehicleDetails(
            CustomerId=target_cust_id,
            RegistrationNo="MH04AA0004",
            ChaiseNo="CH-004",
            FinancialYear="2024-2025",
            isdeleted="1",
        )
    )

    cust_vehicles = await veh_repo.list_by_customer_id(target_cust_id)
    cust_veh_ids = [v.CustVehId for v in cust_vehicles]

    assert v_active1.CustVehId in cust_veh_ids
    assert v_active2.CustVehId in cust_veh_ids
    assert v_other.CustVehId not in cust_veh_ids
    assert v_deleted.CustVehId not in cust_veh_ids
