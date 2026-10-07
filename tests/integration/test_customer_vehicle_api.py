import asyncio
import uuid
from datetime import datetime, date
import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import get_password_hash, create_access_token
from app.models.user import User, UserRole
from app.models.customer import Customer
from app.models.vehicle import VehicleDetails
from app.models.master import VehicleMake, VehicleType, RTOMaster
from app.repositories.user import UserRepository
from app.repositories.role import RoleRepository
from app.repositories.master import VehicleMakeRepository, VehicleTypeRepository, RTORepository


@pytest.fixture(autouse=True)
async def cleanup_customer_vehicle_tables(db_session: AsyncSession):
    """Ensures clean state for each test run."""
    await db_session.execute(text("DELETE FROM tbl_vehicledetails;"))
    await db_session.execute(text("DELETE FROM tbl_customer;"))
    await db_session.commit()
    yield
    await db_session.execute(text("DELETE FROM tbl_vehicledetails;"))
    await db_session.execute(text("DELETE FROM tbl_customer;"))
    await db_session.commit()


async def create_test_user_and_token(
    db_session: AsyncSession,
    username: str,
    role_name: str = "ADMIN",
    branch_id: int = 0,
) -> tuple[User, dict[str, str]]:
    """Helper to provision a test user and return signed JWT authorization headers."""
    user_repo = UserRepository(db_session)
    role_repo = RoleRepository(db_session)

    role = UserRole(UserRole=role_name, code=role_name[:3].upper(), isdeleted="0")
    await role_repo.create(role)

    user = User(
        UserName=username,
        UserPassword=get_password_hash("Password123!"),
        UserRoleId=role.UserRoleId,
        BranchId=branch_id,
        isdeleted="0",
        mobile_no="9876543210",
    )
    await user_repo.create(user)
    await db_session.commit()
    await db_session.refresh(user)

    token = create_access_token({
        "sub": str(user.UserId),
        "username": user.UserName,
        "role": role_name,
        "branch_id": branch_id,
    })
    headers = {"Authorization": f"Bearer {token}"}
    return user, headers


@pytest.mark.asyncio
async def test_database_isolation_safety(db_session: AsyncSession):
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
async def test_unauthenticated_requests_rejected(async_client: AsyncClient):
    """Verify all 4 endpoints require valid Bearer token (401 Unauthorized)."""
    # 1. Customer Create
    r1 = await async_client.post("/api/v1/customers", json={"CustFName": "ANONYMOUS"})
    assert r1.status_code == 401

    # 2. Customer Update
    r2 = await async_client.put("/api/v1/customers/1", json={"CustFName": "ANONYMOUS"})
    assert r2.status_code == 401

    # 3. Vehicle Create
    r3 = await async_client.post(
        "/api/v1/customers/1/vehicles",
        json={"financial_year": "2024-2025", "registration_no": "MH12AB1234"},
    )
    assert r3.status_code == 401

    # 4. Vehicle Update
    r4 = await async_client.put(
        "/api/v1/customers/1/vehicles/1",
        json={"registration_no": "MH12AB1234"},
    )
    assert r4.status_code == 401


@pytest.mark.asyncio
async def test_customer_create_success_auto_code(
    async_client: AsyncClient, db_session: AsyncSession
):
    """
    Verify customer creation with automatic CustomerCode generation:
    - CustomerCode = str(CustomerId)
    - Uppercase transforms applied to names, addresses, Aadhaar, email
    - PAN_No casing preserved
    - Communication address mirrored from permanent address if omitted
    - isdeleted set to '0'
    """
    _, headers = await create_test_user_and_token(
        db_session, f"admin_{uuid.uuid4().hex[:6]}", role_name="ADMIN", branch_id=0
    )

    payload = {
        "cust_f_name": "  suresh  ",
        "cust_m_name": "  k  ",
        "cust_l_name": "  patil  ",
        "customer_type": "Individual",
        "per_addr_line1": "  flat 202, galaxy apts  ",
        "per_addr_line2": "  kothrud  ",
        "per_pin_code": "411038",
        "moblie_no1": "  9822012345  ",
        "pan_no": "  abcde1234f  ",
        "aadhar_no": "  123456789012  ",
        "email_id": "  suresh.patil@example.com  ",
        "marital_status": "Married",
        "extra1": "15-05-2018",
    }

    response = await async_client.post("/api/v1/customers", headers=headers, json=payload)
    assert response.status_code == 201
    data = response.json()

    assert data["customer_id"] is not None
    # Concurrency-safe automatic CustomerCode matches stringified CustomerId
    assert data["customer_code"] == str(data["customer_id"])
    assert data["cust_f_name"] == "SURESH"
    assert data["cust_m_name"] == "K"
    assert data["cust_l_name"] == "PATIL"
    assert data["per_addr_line1"] == "FLAT 202, GALAXY APTS"
    # Communication address mirrored from permanent
    assert data["com_addr_line1"] == "FLAT 202, GALAXY APTS"
    assert data["com_pin_code"] == "411038"
    assert data["moblie_no1"] == "9822012345"
    assert data["pan_no"] == "abcde1234f"  # Preserved as audited in Phase 5C
    assert data["aadhar_no"] == "123456789012"
    assert data["email_id"] == "SURESH.PATIL@EXAMPLE.COM"
    assert data["marital_status"] == "Married"
    assert data["extra1"] == "15-05-2018"
    assert data["isdeleted"] == "0"


@pytest.mark.asyncio
async def test_customer_create_explicit_code_and_conflict(
    async_client: AsyncClient, db_session: AsyncSession
):
    """Verify explicit CustomerCode assignment and 409 Conflict when duplicate CustomerCode is sent."""
    _, headers = await create_test_user_and_token(
        db_session, f"admin_{uuid.uuid4().hex[:6]}", role_name="ADMIN", branch_id=0
    )

    explicit_code = f"CUST-EXPLICIT-{uuid.uuid4().hex[:4].upper()}"

    # First insert with explicit code -> 201 Created
    r1 = await async_client.post(
        "/api/v1/customers",
        headers=headers,
        json={"CustomerCode": explicit_code, "CustFName": "EXPLICIT_ONE"},
    )
    assert r1.status_code == 201
    assert r1.json()["customer_code"] == explicit_code

    # Second insert with identical code -> 409 Conflict
    r2 = await async_client.post(
        "/api/v1/customers",
        headers=headers,
        json={"CustomerCode": explicit_code, "CustFName": "EXPLICIT_TWO"},
    )
    assert r2.status_code == 409
    assert "already exists" in r2.json()["error"]["message"]


@pytest.mark.asyncio
async def test_customer_create_duplicate_mobile_and_pan_allowed(
    async_client: AsyncClient, db_session: AsyncSession
):
    """
    Verify legacy contract: MoblieNo1 and PAN_No are NOT globally unique in database.
    Multiple customers with identical mobile numbers and PANs must be accepted.
    """
    _, headers = await create_test_user_and_token(
        db_session, f"admin_{uuid.uuid4().hex[:6]}", role_name="ADMIN", branch_id=0
    )
    shared_mobile = "9988776655"
    shared_pan = "ABCDE1234F"

    r1 = await async_client.post(
        "/api/v1/customers",
        headers=headers,
        json={
            "CustFName": "FIRST",
            "CustLName": "USER",
            "MoblieNo1": shared_mobile,
            "PAN_No": shared_pan,
        },
    )
    assert r1.status_code == 201

    r2 = await async_client.post(
        "/api/v1/customers",
        headers=headers,
        json={
            "CustFName": "SECOND",
            "CustLName": "USER",
            "MoblieNo1": shared_mobile,
            "PAN_No": shared_pan,
        },
    )
    assert r2.status_code == 201
    assert r1.json()["customer_id"] != r2.json()["customer_id"]


@pytest.mark.asyncio
async def test_customer_update_success_and_immutability(
    async_client: AsyncClient, db_session: AsyncSession
):
    """
    Verify Customer update endpoint:
    - Mutable fields are updated
    - Immutable fields (CustomerId, CustomerCode, CreateDate, CreateUser, CompanyName, isdeleted) remain unchanged
    """
    user, headers = await create_test_user_and_token(
        db_session, f"admin_{uuid.uuid4().hex[:6]}", role_name="ADMIN", branch_id=0
    )

    # 1. Create initial customer
    create_resp = await async_client.post(
        "/api/v1/customers",
        headers=headers,
        json={"CustFName": "INITIAL", "CustLName": "NAME", "CompanyName": "ORIGINAL_CORP"},
    )
    assert create_resp.status_code == 201
    initial_data = create_resp.json()
    cid = initial_data["customer_id"]
    code_before = initial_data["customer_code"]
    created_date = initial_data["create_date"]
    created_user = initial_data["create_user"]

    # 2. Update customer mutable fields and attempt to modify immutable fields
    update_resp = await async_client.put(
        f"/api/v1/customers/{cid}",
        headers=headers,
        json={
            "CustFName": "updated name",
            "per_addr_line1": "new address",
            "CompanyName": "HACKED_CORP",  # Should be ignored / immutable
            "CustomerCode": "HACKED_CODE",  # Should be ignored / immutable
            "isdeleted": "1",  # Should be ignored / immutable
        },
    )
    assert update_resp.status_code == 200
    updated_data = update_resp.json()

    # Mutable fields updated
    assert updated_data["cust_f_name"] == "UPDATED NAME"
    assert updated_data["per_addr_line1"] == "NEW ADDRESS"

    # Immutable fields preserved
    assert updated_data["customer_code"] == code_before
    assert updated_data["company_name"] == "ORIGINAL_CORP"
    assert updated_data["create_date"] == created_date
    assert updated_data["create_user"] == created_user
    assert updated_data["isdeleted"] == "0"


@pytest.mark.asyncio
async def test_customer_update_not_found(async_client: AsyncClient, db_session: AsyncSession):
    """Verify updating non-existent customer returns 404 Not Found."""
    _, headers = await create_test_user_and_token(
        db_session, f"admin_{uuid.uuid4().hex[:6]}", role_name="ADMIN", branch_id=0
    )
    resp = await async_client.put(
        "/api/v1/customers/999999",
        headers=headers,
        json={"CustFName": "GHOST"},
    )
    assert resp.status_code == 404
    assert "not found" in resp.json()["error"]["message"]


@pytest.mark.asyncio
async def test_branch_jurisdiction_enforcement(
    async_client: AsyncClient, db_session: AsyncSession
):
    """
    Verify branch security contract:
    - User with BranchId=101 creates customer scoped to BranchId=101.
    - User with BranchId=102 CANNOT update or register vehicle for Branch 101's customer (403 Forbidden).
    - Admin (BranchId=0 or role=ADMIN) can update across any branch.
    """
    _, headers_b1 = await create_test_user_and_token(
        db_session, f"clerk1_{uuid.uuid4().hex[:6]}", role_name="OPERATOR", branch_id=101
    )
    _, headers_b2 = await create_test_user_and_token(
        db_session, f"clerk2_{uuid.uuid4().hex[:6]}", role_name="OPERATOR", branch_id=102
    )
    _, headers_admin = await create_test_user_and_token(
        db_session, f"admin_{uuid.uuid4().hex[:6]}", role_name="ADMIN", branch_id=0
    )

    # 1. Clerk 1 creates customer -> strictly bound to Branch 101
    c1_resp = await async_client.post(
        "/api/v1/customers",
        headers=headers_b1,
        json={"CustFName": "BRANCH1_CLIENT", "BranchId": 999},  # Attempted override ignored
    )
    assert c1_resp.status_code == 201
    c1 = c1_resp.json()
    assert c1["branch_id"] == 101

    # 2. Clerk 2 attempts to update Clerk 1's customer -> 403 Forbidden
    put_by_c2 = await async_client.put(
        f"/api/v1/customers/{c1['customer_id']}",
        headers=headers_b2,
        json={"CustFName": "INTRUDER_UPDATE"},
    )
    assert put_by_c2.status_code == 403
    assert "Forbidden" in put_by_c2.json()["error"]["message"]

    # 3. Clerk 2 attempts to create vehicle for Clerk 1's customer -> 403 Forbidden
    veh_by_c2 = await async_client.post(
        f"/api/v1/customers/{c1['customer_id']}/vehicles",
        headers=headers_b2,
        json={"registration_no": "MH12XY0001", "financial_year": "2024-2025"},
    )
    assert veh_by_c2.status_code == 403

    # 4. Admin updates Clerk 1's customer -> 200 OK
    put_by_admin = await async_client.put(
        f"/api/v1/customers/{c1['customer_id']}",
        headers=headers_admin,
        json={"CustFName": "ADMIN_UPDATE"},
    )
    assert put_by_admin.status_code == 200
    assert put_by_admin.json()["cust_f_name"] == "ADMIN_UPDATE"


@pytest.mark.asyncio
async def test_vehicle_create_success_and_chaise_no_preserved(
    async_client: AsyncClient, db_session: AsyncSession
):
    """
    Verify vehicle creation under a customer:
    - Preserves physical ChaiseNo column
    - Uppercases registration, engine, chassis numbers
    - CustomerId correctly linked
    """
    _, headers = await create_test_user_and_token(
        db_session, f"admin_{uuid.uuid4().hex[:6]}", role_name="ADMIN", branch_id=0
    )
    cust_resp = await async_client.post(
        "/api/v1/customers",
        headers=headers,
        json={"CustFName": "DEEPAK", "CustLName": "JOSHI"},
    )
    cid = cust_resp.json()["customer_id"]

    veh_payload = {
        "financial_year": "2024-2025",
        "registration_no": "  mh12cd9876  ",
        "chaise_no": "  chas987654  ",
        "engine_no": "  eng123456  ",
        "mfg_year": "2023",
        "seats_capacity": "5",
        "engine_power": "1197",
        "vehicle_weight": "1050",
        "vehicle_variant": "ZXI+",
    }

    veh_resp = await async_client.post(
        f"/api/v1/customers/{cid}/vehicles",
        headers=headers,
        json=veh_payload,
    )
    assert veh_resp.status_code == 201
    veh_data = veh_resp.json()

    assert veh_data["cust_veh_id"] is not None
    assert veh_data["customer_id"] == cid
    assert veh_data["registration_no"] == "MH12CD9876"
    assert veh_data["chaise_no"] == "CHAS987654"
    assert veh_data["engine_no"] == "ENG123456"
    assert veh_data["financial_year"] == "2024-2025"
    assert veh_data["vehicle_variant"] == "ZXI+"
    assert veh_data["isdeleted"] == "0"


@pytest.mark.asyncio
async def test_vehicle_create_nonexistent_customer_returns_404(
    async_client: AsyncClient, db_session: AsyncSession
):
    """Verify creating a vehicle for a non-existent customer returns 404."""
    _, headers = await create_test_user_and_token(
        db_session, f"admin_{uuid.uuid4().hex[:6]}", role_name="ADMIN", branch_id=0
    )
    resp = await async_client.post(
        "/api/v1/customers/999999/vehicles",
        headers=headers,
        json={"financial_year": "2024-2025", "registration_no": "MH12AB1234"},
    )
    assert resp.status_code == 404
    assert "does not exist" in resp.json()["error"]["message"]


@pytest.mark.asyncio
async def test_vehicle_master_id_validation(
    async_client: AsyncClient, db_session: AsyncSession
):
    """
    Verify application-layer master foreign key validation:
    - Non-existent Make_ID -> 400 Bad Request
    - Valid Make_ID -> 201 Created
    """
    _, headers = await create_test_user_and_token(
        db_session, f"admin_{uuid.uuid4().hex[:6]}", role_name="ADMIN", branch_id=0
    )
    cust_resp = await async_client.post(
        "/api/v1/customers",
        headers=headers,
        json={"CustFName": "VIJAY", "CustLName": "PATIL"},
    )
    cid = cust_resp.json()["customer_id"]

    # 1. Invalid make_id -> 400 Bad Request
    invalid_resp = await async_client.post(
        f"/api/v1/customers/{cid}/vehicles",
        headers=headers,
        json={
            "financial_year": "2024-2025",
            "registration_no": "MH12TT1234",
            "make_id": 999999,
        },
    )
    assert invalid_resp.status_code == 400
    assert "Vehicle make ID 999999 does not exist" in invalid_resp.json()["error"]["message"]

    # 2. Insert valid Make in DB
    make_repo = VehicleMakeRepository(db_session)
    make = VehicleMake(Make_Name="HYUNDAI", isdeleted=0)
    await make_repo.create(make)
    await db_session.commit()

    # Valid make_id -> 201 Created
    valid_resp = await async_client.post(
        f"/api/v1/customers/{cid}/vehicles",
        headers=headers,
        json={
            "financial_year": "2024-2025",
            "registration_no": "MH12TT1234",
            "make_id": make.Make_ID,
        },
    )
    assert valid_resp.status_code == 201
    assert valid_resp.json()["make_id"] == make.Make_ID


@pytest.mark.asyncio
async def test_vehicle_duplicate_registration_in_same_fy_rejected(
    async_client: AsyncClient, db_session: AsyncSession
):
    """
    Verify sp_CheckRegistrationNo rule:
    Duplicate RegistrationNo in the SAME FinancialYear is rejected with 409 Conflict.
    """
    _, headers = await create_test_user_and_token(
        db_session, f"admin_{uuid.uuid4().hex[:6]}", role_name="ADMIN", branch_id=0
    )
    cust_resp = await async_client.post(
        "/api/v1/customers",
        headers=headers,
        json={"CustFName": "AMIT", "CustLName": "VERMA"},
    )
    cid = cust_resp.json()["customer_id"]
    reg = "MH14CD5678"

    # First vehicle in FY 2024-2025 -> 201 Created
    v1 = await async_client.post(
        f"/api/v1/customers/{cid}/vehicles",
        headers=headers,
        json={"financial_year": "2024-2025", "registration_no": reg, "chaise_no": "CHAS1"},
    )
    assert v1.status_code == 201

    # Second vehicle with same reg in SAME FY 2024-2025 -> 409 Conflict
    v2 = await async_client.post(
        f"/api/v1/customers/{cid}/vehicles",
        headers=headers,
        json={"financial_year": "2024-2025", "registration_no": reg, "chaise_no": "CHAS2"},
    )
    assert v2.status_code == 409
    assert "already exists in financial year" in v2.json()["error"]["message"]


@pytest.mark.asyncio
async def test_vehicle_duplicate_registration_in_different_fy_allowed(
    async_client: AsyncClient, db_session: AsyncSession
):
    """
    Verify Annual Policy Renewal Workflow:
    Same RegistrationNo across DIFFERENT FinancialYears is ALLOWED.
    """
    _, headers = await create_test_user_and_token(
        db_session, f"admin_{uuid.uuid4().hex[:6]}", role_name="ADMIN", branch_id=0
    )
    cust_resp = await async_client.post(
        "/api/v1/customers",
        headers=headers,
        json={"CustFName": "RENEWAL", "CustLName": "USER"},
    )
    cid = cust_resp.json()["customer_id"]
    reg = "MH14XY9999"

    # Year 1 (FY 2024-2025)
    v1 = await async_client.post(
        f"/api/v1/customers/{cid}/vehicles",
        headers=headers,
        json={"financial_year": "2024-2025", "registration_no": reg, "chaise_no": "CHAS1001"},
    )
    assert v1.status_code == 201

    # Year 2 (FY 2025-2026) -> ALLOWED (Annual Renewal)
    v2 = await async_client.post(
        f"/api/v1/customers/{cid}/vehicles",
        headers=headers,
        json={"financial_year": "2025-2026", "registration_no": reg, "chaise_no": "CHAS1001"},
    )
    assert v2.status_code == 201
    assert v1.json()["cust_veh_id"] != v2.json()["cust_veh_id"]


@pytest.mark.asyncio
async def test_vehicle_update_success_and_immutability(
    async_client: AsyncClient, db_session: AsyncSession
):
    """
    Verify Vehicle update endpoint:
    - Mutable specs are updated
    - Immutable columns (CustomerId, FinancialYear, BranchId, CorporateClientId, VehicleVariant, CreateDate, CreatedUser, isdeleted) remain unchanged
    """
    _, headers = await create_test_user_and_token(
        db_session, f"admin_{uuid.uuid4().hex[:6]}", role_name="ADMIN", branch_id=0
    )
    cust_resp = await async_client.post(
        "/api/v1/customers",
        headers=headers,
        json={"CustFName": "PRAKASH", "CustLName": "KUMAR"},
    )
    cid = cust_resp.json()["customer_id"]

    v_create = await async_client.post(
        f"/api/v1/customers/{cid}/vehicles",
        headers=headers,
        json={
            "financial_year": "2024-2025",
            "registration_no": "MH12AA0001",
            "chaise_no": "CHAS_INIT",
            "engine_no": "ENG_INIT",
            "vehicle_variant": "ORIGINAL_VARIANT",
        },
    )
    assert v_create.status_code == 201
    init_data = v_create.json()
    vid = init_data["cust_veh_id"]

    # Update mutable fields while attempting to overwrite immutable fields
    v_update = await async_client.put(
        f"/api/v1/customers/{cid}/vehicles/{vid}",
        headers=headers,
        json={
            "engine_no": "eng_updated",
            "seats_capacity": "7",
            "financial_year": "HACKED_FY",  # Immutable
            "vehicle_variant": "HACKED_VARIANT",  # Immutable
            "corporate_client_id": 999,  # Immutable
        },
    )
    assert v_update.status_code == 200
    updated_data = v_update.json()

    # Mutable fields updated
    assert updated_data["engine_no"] == "ENG_UPDATED"
    assert updated_data["seats_capacity"] == "7"

    # Immutable fields preserved
    assert updated_data["customer_id"] == cid
    assert updated_data["financial_year"] == "2024-2025"
    assert updated_data["vehicle_variant"] == "ORIGINAL_VARIANT"
    assert updated_data["corporate_client_id"] == 1
    assert updated_data["create_date"] == init_data["create_date"]
    assert updated_data["created_user"] == init_data["created_user"]
    assert updated_data["isdeleted"] == "0"


@pytest.mark.asyncio
async def test_vehicle_update_customer_mismatch_returns_400(
    async_client: AsyncClient, db_session: AsyncSession
):
    """Verify attempting to update a vehicle under a different customer ID returns 400 Bad Request."""
    _, headers = await create_test_user_and_token(
        db_session, f"admin_{uuid.uuid4().hex[:6]}", role_name="ADMIN", branch_id=0
    )
    c1 = (await async_client.post("/api/v1/customers", headers=headers, json={"CustFName": "OWNER1"})).json()["customer_id"]
    c2 = (await async_client.post("/api/v1/customers", headers=headers, json={"CustFName": "OWNER2"})).json()["customer_id"]

    v = (await async_client.post(
        f"/api/v1/customers/{c1}/vehicles",
        headers=headers,
        json={"financial_year": "2024-2025", "registration_no": "MH12MM1111"},
    )).json()["cust_veh_id"]

    # Attempt to update vehicle of Customer 1 using Customer 2's URL -> 400 Bad Request
    resp = await async_client.put(
        f"/api/v1/customers/{c2}/vehicles/{v}",
        headers=headers,
        json={"seats_capacity": "6"},
    )
    assert resp.status_code == 400
    assert "does not belong to customer" in resp.json()["error"]["message"]


@pytest.mark.asyncio
async def test_concurrent_customer_creation_collision_free(
    async_client: AsyncClient, db_session: AsyncSession
):
    """
    CRITICAL CONCURRENCY TEST:
    Simultaneously launches 10 concurrent requests creating customers without CustomerCode.
    Verifies that:
    1. All 10 requests succeed (HTTP 201).
    2. Every customer receives a unique, collision-free CustomerCode.
    3. Zero database deadlocks or unique key violations occur.
    """
    _, headers = await create_test_user_and_token(
        db_session, f"admin_{uuid.uuid4().hex[:6]}", role_name="ADMIN", branch_id=0
    )

    async def create_single_customer(idx: int):
        return await async_client.post(
            "/api/v1/customers",
            headers=headers,
            json={
                "CustFName": f"CONCURRENT_{idx}",
                "CustLName": "TESTER",
                "MoblieNo1": "9876543210",
            },
        )

    # Execute 10 simultaneous requests
    tasks = [create_single_customer(i) for i in range(10)]
    responses = await asyncio.gather(*tasks)

    assert len(responses) == 10
    customer_codes = set()
    customer_ids = set()

    for resp in responses:
        assert resp.status_code == 201, f"Expected 201, got {resp.status_code}: {resp.text}"
        data = resp.json()
        assert data["customer_id"] is not None
        assert data["customer_code"] is not None
        assert data["customer_code"] == str(data["customer_id"])
        customer_codes.add(data["customer_code"])
        customer_ids.add(data["customer_id"])

    assert len(customer_codes) == 10, "Collision detected in generated customer codes!"
    assert len(customer_ids) == 10, "Collision detected in customer IDs!"
