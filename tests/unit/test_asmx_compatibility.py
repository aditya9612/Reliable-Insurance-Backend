"""
Comprehensive Unit & Contract Test Suite for Legacy ASMX Compatibility Router (GAP-P1-001 & GAP-P1-002).
Tests request parsing (JSON, Form-URL-Encoded), case-insensitivity, conflict handling,
authentication, active account/role gating, transparent Bcrypt upgrade, audit logging,
legacy customer lookup, wallet balance calculations, BOLA/IDOR authorization gating,
and preservation of modern /api/v1/auth/login.
"""
import uuid
from decimal import Decimal
import pytest
from httpx import AsyncClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash, create_access_token
from app.models.user import User, UserRole, LoginHistory
from app.models.profile import Agent, Employee
from app.models.customer import Customer
from app.models.ledger import LedgerMaster
from app.models.account import Account
from app.models.master import (
    VehicleType,
    VehicleMake,
    VehicleModel,
    VehicleVariant,
    RTOMaster,
    InsuranceCompany,
)
from app.schemas.asmx_compat import (
    API_AgentResponse,
    API_AgentNewResponse,
    API_CustomerAppResponse,
    API_EwalletBalanceResponse,
    API_VehicleTypeResponse,
    API_VehicleMakeResponse,
    API_VehicleModelResponse,
    API_VehicleVariantResponse,
    API_RTOResponse,
    API_InsuranceCompanyResponse,
)


# ==============================================================================
# 1. Pydantic Contract Schema Tests
# ==============================================================================

def test_api_agent_schema_contract():
    """Verify API_AgentResponse exact field names, casing, count, and defaults."""
    schema = API_AgentResponse()
    dumped = schema.model_dump()
    expected_keys = {
        "UserId",
        "SalesExecutiveId",
        "CoordinatorId",
        "AgentId",
        "UserName",
        "Password",
        "Coordinator",
        "UserRoleId",
        "OldVersion",
        "NewVersion",
    }
    assert set(dumped.keys()) == expected_keys
    assert len(dumped) == 10
    assert dumped["UserId"] == 0
    assert dumped["Password"] == ""
    assert dumped["Coordinator"] == ""
    assert dumped["OldVersion"] is None
    assert dumped["NewVersion"] is None


def test_api_agent_new_schema_contract():
    """Verify API_AgentNewResponse exact field names, casing, count, and FranchaiseId spelling."""
    schema = API_AgentNewResponse()
    dumped = schema.model_dump()
    expected_keys = {
        "UserId",
        "SalesExecutiveId",
        "CoordinatorId",
        "AgentId",
        "UserName",
        "Password",
        "Coordinator",
        "UserRoleId",
        "OldVersion",
        "NewVersion",
        "FranchaiseId",
        "BranchId",
        "FullName",
        "MobileNo",
        "MailId",
    }
    assert set(dumped.keys()) == expected_keys
    assert len(dumped) == 15
    assert "FranchaiseId" in dumped
    assert dumped["FranchaiseId"] == 0
    assert dumped["FullName"] == ""
    assert dumped["MobileNo"] == ""
    assert dumped["MailId"] == ""


def test_api_customer_app_schema_contract():
    """Verify API_CustomerAppResponse exact field names, casing, and legacy spellings."""
    schema = API_CustomerAppResponse()
    dumped = schema.model_dump()
    expected_keys = {
        "CustomerId",
        "Name",
        "MoblieNo1",
        "MoblieNo2",
        "EMailId",
        "Address",
    }
    assert set(dumped.keys()) == expected_keys
    assert len(dumped) == 6
    assert "MoblieNo1" in dumped
    assert "MoblieNo2" in dumped
    assert "EMailId" in dumped
    assert dumped["CustomerId"] == 0
    assert dumped["Name"] == ""


def test_api_ewallet_balance_schema_contract():
    """Verify API_EwalletBalanceResponse exact field names, casing, count, and defaults (GAP-P1-002)."""
    schema = API_EwalletBalanceResponse()
    dumped = schema.model_dump()
    expected_keys = {
        "Balance",
        "EwalletBalance",
        "AgentId",
    }
    assert set(dumped.keys()) == expected_keys
    assert len(dumped) == 3
    assert dumped["Balance"] == 0.0
    assert dumped["EwalletBalance"] == 0.0
    assert dumped["AgentId"] == 0


def test_api_vehicle_type_schema_contract():
    """Verify API_VehicleTypeResponse exact field names, casing, count, and defaults (GAP-P1-003)."""
    schema = API_VehicleTypeResponse()
    dumped = schema.model_dump()
    expected_keys = {
        "Veh_Type_ID",
        "Veh_Type_Name",
        "VehicleTypeId",
        "VehicleType",
        "IsAppQuotation",
    }
    assert set(dumped.keys()) == expected_keys
    assert len(dumped) == 5
    assert dumped["Veh_Type_ID"] == 0
    assert dumped["VehicleTypeId"] == 0
    assert dumped["Veh_Type_Name"] == ""
    assert dumped["VehicleType"] == ""


def test_api_vehicle_make_schema_contract():
    """Verify API_VehicleMakeResponse exact field names, casing, count, and defaults (GAP-P1-003)."""
    schema = API_VehicleMakeResponse()
    dumped = schema.model_dump()
    expected_keys = {
        "Make_ID",
        "Make_Name",
        "VehicleMakeId",
        "CompanyName",
        "R_Make_ID",
        "GCV",
        "Misc_D",
        "PCV",
        "PvtCar",
        "Two_Wheeler",
        "Bus",
    }
    assert set(dumped.keys()) == expected_keys
    assert len(dumped) == 11
    assert dumped["Make_ID"] == 0
    assert dumped["VehicleMakeId"] == 0
    assert dumped["Make_Name"] == ""
    assert dumped["CompanyName"] == ""


def test_api_vehicle_model_schema_contract():
    """Verify API_VehicleModelResponse exact field names, casing, count, and defaults (GAP-P1-003)."""
    schema = API_VehicleModelResponse()
    dumped = schema.model_dump()
    expected_keys = {
        "Model_ID",
        "Model_Name",
        "Make_ID",
        "ModelId",
        "ModelName",
        "MakeId",
        "VehicleModelId",
        "VehicleModelName",
        "Type",
        "SegmentId",
    }
    assert set(dumped.keys()) == expected_keys
    assert len(dumped) == 10
    assert dumped["Model_ID"] == 0
    assert dumped["Make_ID"] == 0
    assert dumped["Model_Name"] == ""


def test_api_vehicle_variant_schema_contract():
    """Verify API_VehicleVariantResponse exact field names, casing, count, and defaults (GAP-P1-003)."""
    schema = API_VehicleVariantResponse()
    dumped = schema.model_dump()
    expected_keys = {
        "Variant_ID",
        "Variance",
        "Model_ID",
        "Veh_Type_ID",
        "Veh_Sub_Type_ID",
        "VariantId",
        "VarianceName",
        "CC",
        "Seating_Capacity",
        "Carrying_Capacity",
        "Body_Type",
        "FuelType",
    }
    assert set(dumped.keys()) == expected_keys
    assert len(dumped) == 12
    assert dumped["Variant_ID"] == 0
    assert dumped["Variance"] == ""


def test_api_rto_schema_contract():
    """Verify API_RTOResponse exact field names, casing, count, and defaults (GAP-P1-003)."""
    schema = API_RTOResponse()
    dumped = schema.model_dump()
    expected_keys = {
        "RTOId",
        "RTOLocation",
        "REG_code",
        "District",
        "StateId",
        "zone",
        "ClusterId",
        "RTOWithLocation",
        "RTO_ID",
        "RTO_Location",
    }
    assert set(dumped.keys()) == expected_keys
    assert len(dumped) == 10
    assert dumped["RTOId"] == 0
    assert dumped["RTOLocation"] == ""
    assert dumped["REG_code"] == ""


def test_api_insurance_company_schema_contract():
    """Verify API_InsuranceCompanyResponse exact field names, casing, count, and defaults (GAP-P1-003)."""
    schema = API_InsuranceCompanyResponse()
    dumped = schema.model_dump()
    expected_keys = {
        "InsuranceCompanyId",
        "InsuranceCompany",
        "BranchName",
        "BranchCode",
        "MailId",
        "CompImgPath",
        "ShortName",
        "IsAppQuotation",
    }
    assert set(dumped.keys()) == expected_keys
    assert len(dumped) == 8
    assert dumped["InsuranceCompanyId"] == 0
    assert dumped["InsuranceCompany"] == ""




# ==============================================================================
# 2. Endpoint Authentication & Contract Tests
# ==============================================================================

@pytest.fixture
async def asmx_test_fixtures(db_session: AsyncSession):
    """
    Creates isolated test Role, User, Employee (Coordinator), Agent, and Customer.
    Cleans up automatically via db_session rollback.
    """
    suffix = uuid.uuid4().hex[:6]
    test_username = f"asmx_agent_{suffix}"
    test_plaintext_pass = f"Pass_{suffix}!"

    # 1. Active Role
    role = UserRole(UserRole=f"POSP_{suffix}", code="POSP", isdeleted="0")
    db_session.add(role)
    await db_session.flush()

    # 2. Active User with legacy plaintext password
    user = User(
        UserName=test_username,
        UserPassword=test_plaintext_pass,  # legacy plaintext for upgrade testing
        UserRoleId=role.UserRoleId,
        BranchId=1,
        isdeleted="0",
        mobile_no="9876543210",
    )
    db_session.add(user)
    await db_session.flush()

    # 3. Employee (Coordinator)
    coordinator = Employee(
        UserName=f"coord_{suffix}",
        EmpFName="Vikas",
        EmpLName="Sharma",
        isdeleted="0",
    )
    db_session.add(coordinator)
    await db_session.flush()

    # 4. Agent linked to User and Coordinator
    agent = Agent(
        AgentCode=f"AG_{suffix}",
        AgentFName="Rahul",
        AgentLName="Verma",
        MobileNo="9876543210",
        EmailId="rahul@example.com",
        SalesExecutiveId=108,
        CoordinatorId=coordinator.EmpId,
        FranchiseId=1015,
        BranchId=1,
        UserId=user.UserId,
        isdeleted="0",
    )
    db_session.add(agent)
    await db_session.flush()

    # 5. Customer with primary and secondary numbers
    customer = Customer(
        CustomerCode=f"CUST_{suffix}",
        CustFName="Amit",
        CustLName="Patil",
        MoblieNo1=f"9100{suffix[:6]}",
        MoblieNo2=f"9200{suffix[:6]}",
        EMailId="amit.patil@example.com",
        ComAddrLine1="42 Reliable Park, Pune",
        isdeleted="0",
    )
    db_session.add(customer)
    await db_session.commit()

    return {
        "username": test_username,
        "password": test_plaintext_pass,
        "user": user,
        "role": role,
        "coordinator": coordinator,
        "agent": agent,
        "customer": customer,
    }


@pytest.mark.asyncio
async def test_app_login_json_success(async_client: AsyncClient, asmx_test_fixtures: dict):
    """Verify AppLogin with JSON payload returns 200, 1-element list, empty password, and correct fields."""
    fix = asmx_test_fixtures
    payload = {"UserName": fix["username"], "Password": fix["password"]}

    resp = await async_client.post("/Service.asmx/AppLogin", json=payload)
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/json")

    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 1

    entry = data[0]
    assert entry["UserId"] == fix["user"].UserId
    assert entry["AgentId"] == fix["agent"].AgentId
    assert entry["SalesExecutiveId"] == 108
    assert entry["CoordinatorId"] == fix["coordinator"].EmpId
    assert entry["Coordinator"] == "Vikas Sharma"
    assert entry["UserName"] == fix["username"]
    assert entry["UserRoleId"] == str(fix["role"].UserRoleId)
    assert entry["Password"] == ""  # STRICT SECURITY: NEVER EXPOSE PASSWORD


@pytest.mark.asyncio
async def test_app_login_form_encoded_success(async_client: AsyncClient, asmx_test_fixtures: dict):
    """Verify AppLogin with form-urlencoded payload works identically to JSON."""
    fix = asmx_test_fixtures
    form_data = {"UserName": fix["username"], "Password": fix["password"]}

    resp = await async_client.post(
        "/Service.asmx/AppLogin",
        data=form_data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["UserId"] == fix["user"].UserId
    assert data[0]["AgentId"] == fix["agent"].AgentId


@pytest.mark.asyncio
async def test_app_login_lowercase_param_matching(async_client: AsyncClient, asmx_test_fixtures: dict):
    """Verify AppLogin supports lowercase username and password keys."""
    fix = asmx_test_fixtures
    payload = {"username": fix["username"], "password": fix["password"]}

    resp = await async_client.post("/Service.asmx/AppLogin", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["UserId"] == fix["user"].UserId


@pytest.mark.asyncio
async def test_app_login_invalid_password_returns_zero_ids(async_client: AsyncClient, asmx_test_fixtures: dict):
    """Verify failed login returns HTTP 200 with 1-element list containing zero IDs (not empty list)."""
    fix = asmx_test_fixtures
    payload = {"UserName": fix["username"], "Password": "wrong_password_123"}

    resp = await async_client.post("/Service.asmx/AppLogin", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 1

    entry = data[0]
    assert entry["UserId"] == 0
    assert entry["AgentId"] == 0
    assert entry["SalesExecutiveId"] == 0
    assert entry["CoordinatorId"] == 0
    assert entry["UserName"] == fix["username"]
    assert entry["Password"] == ""


@pytest.mark.asyncio
async def test_app_login_nonexistent_user_returns_zero_ids(async_client: AsyncClient):
    """Verify non-existent user returns HTTP 200 with 1-element list containing zero IDs."""
    payload = {"UserName": "completely_unknown_user_9999", "Password": "some_password"}

    resp = await async_client.post("/Service.asmx/AppLogin", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["UserId"] == 0
    assert data[0]["AgentId"] == 0


@pytest.mark.asyncio
async def test_app_login_inactive_user_rejected(async_client: AsyncClient, db_session: AsyncSession):
    """Verify user with isdeleted='1' fails authentication and returns zero IDs."""
    suffix = uuid.uuid4().hex[:6]
    deleted_user = User(
        UserName=f"deleted_user_{suffix}",
        UserPassword=get_password_hash("Secret123!"),
        isdeleted="1",
    )
    db_session.add(deleted_user)
    await db_session.commit()

    resp = await async_client.post(
        "/Service.asmx/AppLogin",
        json={"UserName": deleted_user.UserName, "Password": "Secret123!"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["UserId"] == 0


@pytest.mark.asyncio
async def test_app_login_conflicting_parameters_rejected(async_client: AsyncClient, asmx_test_fixtures: dict):
    """Verify request with conflicting parameter values safely rejects login."""
    fix = asmx_test_fixtures
    # Conflicting UserName vs username
    payload = {"UserName": fix["username"], "username": "conflicting_username", "Password": fix["password"]}

    resp = await async_client.post("/Service.asmx/AppLogin", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["UserId"] == 0


@pytest.mark.asyncio
async def test_app_login_transparent_bcrypt_upgrade(
    async_client: AsyncClient, db_session: AsyncSession, asmx_test_fixtures: dict
):
    """Verify that a legacy user with plaintext password is automatically upgraded to Bcrypt on login."""
    fix = asmx_test_fixtures
    user_id = fix["user"].UserId

    # Authenticate via ASMX AppLogin
    resp = await async_client.post(
        "/Service.asmx/AppLogin",
        json={"UserName": fix["username"], "Password": fix["password"]},
    )
    assert resp.status_code == 200

    # Query DB to verify password column was updated to a Bcrypt hash ($2b$)
    await db_session.commit()
    await db_session.refresh(fix["user"])

    assert fix["user"].UserPassword.startswith(("$2a$", "$2b$", "$2y$"))


@pytest.mark.asyncio
async def test_app_login_audit_logging(
    async_client: AsyncClient, db_session: AsyncSession, asmx_test_fixtures: dict
):
    """Verify that tbl_loginhistory captures audit entries for ASMX login attempts."""
    fix = asmx_test_fixtures

    # 1. Trigger successful login
    await async_client.post(
        "/Service.asmx/AppLogin",
        json={"UserName": fix["username"], "Password": fix["password"]},
    )

    # 2. Trigger failed login
    await async_client.post(
        "/Service.asmx/AppLogin",
        json={"UserName": fix["username"], "Password": "invalid_password"},
    )

    # Query audit logs
    stmt = (
        select(LoginHistory)
        .where(LoginHistory.UserName == fix["username"])
        .order_by(LoginHistory.LoginHistoryId.desc())
    )
    res = await db_session.execute(stmt)
    logs = res.scalars().all()

    actions = [log.LogInOrLogOut for log in logs]
    assert "LOGIN" in actions
    assert "FAILED_LOGIN" in actions


# ==============================================================================
# 3. AgentAppLoginNew Endpoint Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_agent_app_login_new_success(async_client: AsyncClient, asmx_test_fixtures: dict):
    """Verify AgentAppLoginNew returns all 15 fields including FranchaiseId and contact details."""
    fix = asmx_test_fixtures
    payload = {"UserName": fix["username"], "Password": fix["password"]}

    resp = await async_client.post("/Service.asmx/AgentAppLoginNew", json=payload)
    assert resp.status_code == 200

    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 1

    entry = data[0]
    assert entry["UserId"] == fix["user"].UserId
    assert entry["AgentId"] == fix["agent"].AgentId
    assert entry["FranchaiseId"] == 1015
    assert entry["BranchId"] == 1
    assert entry["FullName"] == "Rahul Verma"
    assert entry["MobileNo"] == "9876543210"
    assert entry["MailId"] == "rahul@example.com"
    assert entry["OldVersion"] == "1.0"
    assert entry["NewVersion"] == "1.0"
    assert entry["Password"] == ""


@pytest.mark.asyncio
async def test_agent_app_login_new_failure_contract(async_client: AsyncClient):
    """Verify AgentAppLoginNew failure returns 1-element list with zero IDs and blank strings."""
    payload = {"UserName": "unknown_user_555", "Password": "wrong_password"}

    resp = await async_client.post("/Service.asmx/AgentAppLoginNew", json=payload)
    assert resp.status_code == 200

    data = resp.json()
    assert len(data) == 1
    entry = data[0]
    assert entry["UserId"] == 0
    assert entry["AgentId"] == 0
    assert entry["FranchaiseId"] == 0
    assert entry["FullName"] == ""
    assert entry["MobileNo"] == ""
    assert entry["MailId"] == ""


# ==============================================================================
# 4. CheckLoginCustomer Endpoint Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_check_login_customer_match_primary_mobile(async_client: AsyncClient, asmx_test_fixtures: dict):
    """Verify CheckLoginCustomer matches customer on MoblieNo1."""
    cust = asmx_test_fixtures["customer"]
    payload = {"MoblieNo1": cust.MoblieNo1, "MoblieNo2": ""}

    resp = await async_client.post("/Service.asmx/CheckLoginCustomer", json=payload)
    assert resp.status_code == 200

    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 1

    entry = data[0]
    assert entry["CustomerId"] == cust.CustomerId
    assert entry["Name"] == "Amit Patil"
    assert entry["MoblieNo1"] == cust.MoblieNo1
    assert entry["EMailId"] == "amit.patil@example.com"
    assert entry["Address"] == "42 Reliable Park, Pune"


@pytest.mark.asyncio
async def test_check_login_customer_match_secondary_mobile(async_client: AsyncClient, asmx_test_fixtures: dict):
    """Verify CheckLoginCustomer matches customer on MoblieNo2."""
    cust = asmx_test_fixtures["customer"]
    payload = {"MoblieNo1": cust.MoblieNo2, "MoblieNo2": ""}

    resp = await async_client.post("/Service.asmx/CheckLoginCustomer", json=payload)
    assert resp.status_code == 200

    data = resp.json()
    assert len(data) == 1
    assert data[0]["CustomerId"] == cust.CustomerId


@pytest.mark.asyncio
async def test_check_login_customer_not_found(async_client: AsyncClient):
    """Verify CheckLoginCustomer when not found returns CustomerId=0 and empty fields."""
    payload = {"MoblieNo1": "0000000000", "MoblieNo2": ""}

    resp = await async_client.post("/Service.asmx/CheckLoginCustomer", json=payload)
    assert resp.status_code == 200

    data = resp.json()
    assert len(data) == 1
    entry = data[0]
    assert entry["CustomerId"] == 0
    assert entry["Name"] == ""
    assert entry["MoblieNo1"] == "0000000000"
    assert entry["EMailId"] == ""
    assert entry["Address"] == ""


# ==============================================================================
# 5. Regression Safety Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_modern_auth_login_unaffected(async_client: AsyncClient, asmx_test_fixtures: dict):
    """Verify that modern /api/v1/auth/login endpoint continues to work and return JWT access token."""
    fix = asmx_test_fixtures
    payload = {"username": fix["username"], "password": fix["password"]}

    resp = await async_client.post("/api/v1/auth/login", json=payload)
    assert resp.status_code == 200

    data = resp.json()
    assert "access_token" in data
    assert data["token_type"].lower() == "bearer"
    assert "user" in data
    assert data["user"]["username"] == fix["username"]


# ==============================================================================
# 6. GAP-P1-002: SelectEwalletBalanceByAgent & IDOR/BOLA Protection Tests
# ==============================================================================

@pytest.fixture
async def asmx_wallet_fixtures(db_session: AsyncSession):
    """
    Creates an Agent with an active User, a LedgerMaster entry, and Account entries (available balance 12,000.00).
    """
    suffix = uuid.uuid4().hex[:6]
    role = UserRole(UserRole="AGENT", code="AGT", isdeleted="0")
    db_session.add(role)
    await db_session.flush()

    user = User(
        UserName=f"agt_{suffix}",
        UserPassword=get_password_hash("Pass123!"),
        UserRoleId=role.UserRoleId,
        BranchId=1,
        partner_user_id=None,
        isdeleted="0",
        mobile_no="9876543210",
    )
    db_session.add(user)
    await db_session.flush()

    agent = Agent(
        AgentCode=f"AG_{suffix}",
        AgentFName="Sanjay",
        AgentLName="Mehta",
        MobileNo="9876543210",
        EmailId="sanjay@example.com",
        BranchId=1,
        UserId=user.UserId,
        IsActive=1,
        isdeleted="0",
    )
    db_session.add(agent)
    await db_session.flush()

    user.partner_user_id = agent.AgentId
    await db_session.flush()

    ledger = LedgerMaster(
        LedgerTypeId=5,
        ReferenceId=agent.AgentId,
        LedgerName=f"EWALLET - AGENT #{agent.AgentId}",
        LedgerGroupId=2,
        BranchId=1,
        isdeleted="0",
    )
    db_session.add(ledger)
    await db_session.flush()

    acc_credit = Account(
        AccTransId=10,
        LedgerMId=ledger.LedgerMId,
        amount=Decimal("15000.00"),
        isdeleted=0,
        IsNill=0,
        TransactionId=0,
        CustVehId=0,
        MonthId=0,
        EndorsementId=0,
        TransId=0,
    )
    acc_lock = Account(
        AccTransId=11,
        LedgerMId=ledger.LedgerMId,
        amount=Decimal("-3000.00"),
        Extra1="WALLET_LOCK",
        isdeleted=0,
        IsNill=0,
        TransactionId=0,
        CustVehId=0,
        MonthId=0,
        EndorsementId=0,
        TransId=0,
    )
    db_session.add(acc_credit)
    db_session.add(acc_lock)
    await db_session.commit()
    await db_session.refresh(agent)
    await db_session.refresh(user)

    token = create_access_token(
        {
            "sub": str(user.UserId),
            "username": user.UserName,
            "role": "AGENT",
            "branch_id": 1,
        }
    )

    return {
        "user": user,
        "role": role,
        "agent": agent,
        "ledger": ledger,
        "token": token,
        "headers": {"Authorization": f"Bearer {token}"},
    }


@pytest.fixture
async def asmx_second_agent_fixtures(db_session: AsyncSession):
    """Creates a second active POSP Agent for IDOR / BOLA authorization testing."""
    suffix = uuid.uuid4().hex[:6]
    role = UserRole(UserRole="AGENT", code="AGT", isdeleted="0")
    db_session.add(role)
    await db_session.flush()

    user = User(
        UserName=f"agt2_{suffix}",
        UserPassword=get_password_hash("Pass123!"),
        UserRoleId=role.UserRoleId,
        BranchId=1,
        isdeleted="0",
        mobile_no="9876543211",
    )
    db_session.add(user)
    await db_session.flush()

    agent = Agent(
        AgentCode=f"AG2_{suffix}",
        AgentFName="Sunil",
        AgentLName="Verma",
        MobileNo="9876543211",
        EmailId="sunil@example.com",
        BranchId=1,
        UserId=user.UserId,
        IsActive=1,
        isdeleted="0",
    )
    db_session.add(agent)
    await db_session.flush()

    user.partner_user_id = agent.AgentId
    await db_session.commit()
    await db_session.refresh(agent)
    await db_session.refresh(user)

    token = create_access_token(
        {
            "sub": str(user.UserId),
            "username": user.UserName,
            "role": "AGENT",
            "branch_id": 1,
        }
    )
    return {
        "user": user,
        "agent": agent,
        "token": token,
        "headers": {"Authorization": f"Bearer {token}"},
    }


@pytest.fixture
async def asmx_admin_fixtures(db_session: AsyncSession):
    """Creates an active Admin user with Bearer token."""
    suffix = uuid.uuid4().hex[:6]
    role = UserRole(UserRole="ADMIN", code="ADM", isdeleted="0")
    db_session.add(role)
    await db_session.flush()

    user = User(
        UserName=f"adm_{suffix}",
        UserPassword=get_password_hash("AdminPass123!"),
        UserRoleId=role.UserRoleId,
        BranchId=1,
        isdeleted="0",
        mobile_no="9876543212",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    token = create_access_token(
        {
            "sub": str(user.UserId),
            "username": user.UserName,
            "role": "ADMIN",
            "branch_id": 1,
        }
    )
    return {
        "user": user,
        "headers": {"Authorization": f"Bearer {token}"},
    }


@pytest.fixture
async def asmx_customer_fixtures(db_session: AsyncSession):
    """Creates an active Customer user with Bearer token."""
    suffix = uuid.uuid4().hex[:6]
    role = UserRole(UserRole="CUSTOMER", code="CUS", isdeleted="0")
    db_session.add(role)
    await db_session.flush()

    user = User(
        UserName=f"cus_{suffix}",
        UserPassword=get_password_hash("CustPass123!"),
        UserRoleId=role.UserRoleId,
        BranchId=1,
        isdeleted="0",
        mobile_no="9876543213",
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    token = create_access_token(
        {
            "sub": str(user.UserId),
            "username": user.UserName,
            "role": "CUSTOMER",
            "branch_id": 1,
        }
    )
    return {
        "user": user,
        "headers": {"Authorization": f"Bearer {token}"},
    }


@pytest.mark.asyncio
async def test_select_ewallet_balance_unauthenticated_rejected_401(
    async_client: AsyncClient, asmx_wallet_fixtures: dict
):
    """
    CRITICAL SECURITY TEST:
    Verify unauthenticated requests to SelectEwalletBalanceByAgent are strictly rejected with HTTP 401.
    Prevents unauthenticated BOLA / IDOR financial balance enumeration.
    """
    agent = asmx_wallet_fixtures["agent"]
    resp = await async_client.post(
        "/Service.asmx/SelectEwalletBalanceByAgent",
        json={"AgentId": agent.AgentId},
    )
    assert resp.status_code == 401
    error_code = resp.json().get("error", {}).get("code", "")
    assert error_code == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_select_ewallet_balance_unauthenticated_causes_zero_database_queries(
    async_client: AsyncClient, asmx_wallet_fixtures: dict
):
    """
    CRITICAL SECURITY & PERFORMANCE GATE:
    Verify that an unauthenticated request to /Service.asmx/SelectEwalletBalanceByAgent
    returns HTTP 401 and causes ZERO SQLAlchemy database queries to be executed.
    Guarantees fail-closed gate blocks before any table or stored procedure access.
    """
    from app.db.session import engine
    from sqlalchemy import event

    executed_queries = []

    def before_cursor_execute_listener(conn, cursor, statement, parameters, context, executemany):
        executed_queries.append(statement)

    event.listen(engine.sync_engine, "before_cursor_execute", before_cursor_execute_listener)
    try:
        agent = asmx_wallet_fixtures["agent"]
        resp = await async_client.post(
            "/Service.asmx/SelectEwalletBalanceByAgent",
            json={"AgentId": agent.AgentId},
        )
        assert resp.status_code == 401
        assert resp.json().get("error", {}).get("code") == "UNAUTHORIZED"
        assert len(executed_queries) == 0, f"Expected 0 queries, executed {len(executed_queries)}: {executed_queries}"
    finally:
        event.remove(engine.sync_engine, "before_cursor_execute", before_cursor_execute_listener)



@pytest.mark.asyncio
async def test_select_ewallet_balance_unauthenticated_form_encoded_rejected_401(
    async_client: AsyncClient, asmx_wallet_fixtures: dict
):
    """Verify unauthenticated form URL-encoded request is strictly rejected with HTTP 401."""
    agent = asmx_wallet_fixtures["agent"]
    resp = await async_client.post(
        "/Service.asmx/SelectEwalletBalanceByAgent",
        data={"AgentId": str(agent.AgentId)},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_select_ewallet_balance_json_success(
    async_client: AsyncClient, asmx_wallet_fixtures: dict
):
    """Verify authenticated owner agent with JSON payload computes correct available balance."""
    agent = asmx_wallet_fixtures["agent"]
    resp = await async_client.post(
        "/Service.asmx/SelectEwalletBalanceByAgent",
        headers=asmx_wallet_fixtures["headers"],
        json={"AgentId": agent.AgentId},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["AgentId"] == agent.AgentId
    assert data[0]["Balance"] == 12000.0
    assert data[0]["EwalletBalance"] == 12000.0


@pytest.mark.asyncio
async def test_select_ewallet_balance_form_encoded_success(
    async_client: AsyncClient, asmx_wallet_fixtures: dict
):
    """Verify authenticated owner agent with form URL-encoded payload."""
    agent = asmx_wallet_fixtures["agent"]
    resp = await async_client.post(
        "/Service.asmx/SelectEwalletBalanceByAgent",
        headers=asmx_wallet_fixtures["headers"],
        data={"AgentId": str(agent.AgentId)},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["AgentId"] == agent.AgentId
    assert data[0]["Balance"] == 12000.0
    assert data[0]["EwalletBalance"] == 12000.0


@pytest.mark.asyncio
async def test_select_ewallet_balance_lowercase_key(
    async_client: AsyncClient, asmx_wallet_fixtures: dict
):
    """Verify case-insensitivity of AgentId parameter for authenticated owner."""
    agent = asmx_wallet_fixtures["agent"]
    resp = await async_client.post(
        "/Service.asmx/SelectEwalletBalanceByAgent",
        headers=asmx_wallet_fixtures["headers"],
        json={"agentid": agent.AgentId},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["AgentId"] == agent.AgentId
    assert data[0]["Balance"] == 12000.0


@pytest.mark.asyncio
async def test_select_ewallet_balance_no_ledger_returns_zero(
    async_client: AsyncClient, db_session: AsyncSession
):
    """Verify authenticated agent with no existing wallet ledger returns 0.0 balance."""
    suffix = uuid.uuid4().hex[:6]
    role = UserRole(UserRole="AGENT", code="AGT", isdeleted="0")
    db_session.add(role)
    await db_session.flush()

    user = User(
        UserName=f"agt_nl_{suffix}",
        UserPassword=get_password_hash("Pass123!"),
        UserRoleId=role.UserRoleId,
        BranchId=1,
        isdeleted="0",
        mobile_no="9876543299",
    )
    db_session.add(user)
    await db_session.flush()

    agent = Agent(
        AgentCode=f"AG_NOLED_{suffix}",
        AgentFName="Pooja",
        AgentLName="Shah",
        UserId=user.UserId,
        IsActive=1,
        isdeleted="0",
    )
    db_session.add(agent)
    await db_session.flush()

    user.partner_user_id = agent.AgentId
    await db_session.commit()

    token = create_access_token(
        {
            "sub": str(user.UserId),
            "username": user.UserName,
            "role": "AGENT",
            "branch_id": 1,
        }
    )

    resp = await async_client.post(
        "/Service.asmx/SelectEwalletBalanceByAgent",
        headers={"Authorization": f"Bearer {token}"},
        json={"AgentId": agent.AgentId},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["AgentId"] == agent.AgentId
    assert data[0]["Balance"] == 0.0
    assert data[0]["EwalletBalance"] == 0.0


@pytest.mark.asyncio
async def test_select_ewallet_balance_nonexistent_agent(
    async_client: AsyncClient, asmx_admin_fixtures: dict
):
    """Verify authenticated admin querying nonexistent agent returns AgentId=0 and Balance=0.0."""
    resp = await async_client.post(
        "/Service.asmx/SelectEwalletBalanceByAgent",
        headers=asmx_admin_fixtures["headers"],
        json={"AgentId": 9999999},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["AgentId"] == 0
    assert data[0]["Balance"] == 0.0
    assert data[0]["EwalletBalance"] == 0.0


@pytest.mark.asyncio
async def test_select_ewallet_balance_inactive_agent_rejected(
    async_client: AsyncClient, db_session: AsyncSession, asmx_admin_fixtures: dict
):
    """Verify authenticated admin querying inactive or deleted agent returns zero IDs."""
    suffix = uuid.uuid4().hex[:6]
    agent = Agent(
        AgentCode=f"AG_INACT_{suffix}",
        AgentFName="Inactive",
        AgentLName="Agent",
        IsActive=0,  # Inactive
        isdeleted="0",
    )
    db_session.add(agent)
    await db_session.commit()
    await db_session.refresh(agent)

    resp = await async_client.post(
        "/Service.asmx/SelectEwalletBalanceByAgent",
        headers=asmx_admin_fixtures["headers"],
        json={"AgentId": agent.AgentId},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["AgentId"] == 0
    assert data[0]["Balance"] == 0.0


@pytest.mark.asyncio
async def test_select_ewallet_balance_invalid_id_inputs(
    async_client: AsyncClient, asmx_admin_fixtures: dict
):
    """Verify authenticated admin passing malformed, negative, string, and conflicting AgentId inputs fail closed."""
    for bad_id in ["not_a_number", -10, 0, "", None]:
        resp = await async_client.post(
            "/Service.asmx/SelectEwalletBalanceByAgent",
            headers=asmx_admin_fixtures["headers"],
            json={"AgentId": bad_id},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["AgentId"] == 0
        assert data[0]["Balance"] == 0.0

    # Conflicting duplicate keys
    resp_conflict = await async_client.post(
        "/Service.asmx/SelectEwalletBalanceByAgent",
        headers=asmx_admin_fixtures["headers"],
        json={"AgentId": 100, "agentid": 200},
    )
    assert resp_conflict.status_code == 200
    assert resp_conflict.json()[0]["AgentId"] == 0



@pytest.mark.asyncio
async def test_select_ewallet_balance_authenticated_owner_success(
    async_client: AsyncClient, asmx_wallet_fixtures: dict
):
    """Verify authenticated Agent principal can access its own E-Wallet balance."""
    fix = asmx_wallet_fixtures
    resp = await async_client.post(
        "/Service.asmx/SelectEwalletBalanceByAgent",
        headers=fix["headers"],
        json={"AgentId": fix["agent"].AgentId},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["AgentId"] == fix["agent"].AgentId
    assert data[0]["Balance"] == 12000.0


@pytest.mark.asyncio
async def test_select_ewallet_balance_authenticated_agent_idor_bola_rejected_403(
    async_client: AsyncClient,
    asmx_wallet_fixtures: dict,
    asmx_second_agent_fixtures: dict,
):
    """
    CRITICAL SECURITY TEST (BOLA / IDOR):
    Verify Agent 2 CANNOT access Agent 1's E-Wallet balance using client-supplied AgentId.
    Must be rejected with HTTP 403 Forbidden.
    """
    agent1 = asmx_wallet_fixtures["agent"]
    agent2_headers = asmx_second_agent_fixtures["headers"]

    resp = await async_client.post(
        "/Service.asmx/SelectEwalletBalanceByAgent",
        headers=agent2_headers,
        json={"AgentId": agent1.AgentId},
    )
    assert resp.status_code == 403
    error_msg = resp.json().get("error", {}).get("message", "") or resp.json().get("detail", "")
    assert "access denied" in error_msg.lower()


@pytest.mark.asyncio
async def test_select_ewallet_balance_authenticated_admin_can_query_any_agent(
    async_client: AsyncClient,
    asmx_wallet_fixtures: dict,
    asmx_admin_fixtures: dict,
):
    """Verify ADMIN role is authorized to inspect any agent's wallet balance."""
    agent1 = asmx_wallet_fixtures["agent"]
    admin_headers = asmx_admin_fixtures["headers"]

    resp = await async_client.post(
        "/Service.asmx/SelectEwalletBalanceByAgent",
        headers=admin_headers,
        json={"AgentId": agent1.AgentId},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["AgentId"] == agent1.AgentId
    assert data[0]["Balance"] == 12000.0


@pytest.mark.asyncio
async def test_select_ewallet_balance_authenticated_customer_rejected_403(
    async_client: AsyncClient,
    asmx_wallet_fixtures: dict,
    asmx_customer_fixtures: dict,
):
    """Verify CUSTOMER role cannot access partner agent E-Wallet balance."""
    agent1 = asmx_wallet_fixtures["agent"]
    cust_headers = asmx_customer_fixtures["headers"]

    resp = await async_client.post(
        "/Service.asmx/SelectEwalletBalanceByAgent",
        headers=cust_headers,
        json={"AgentId": agent1.AgentId},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_select_ewallet_balance_invalid_bearer_token_rejected_401(
    async_client: AsyncClient, asmx_wallet_fixtures: dict
):
    """Verify malformed or forged Bearer token is rejected with HTTP 401."""
    agent1 = asmx_wallet_fixtures["agent"]
    resp = await async_client.post(
        "/Service.asmx/SelectEwalletBalanceByAgent",
        headers={"Authorization": "Bearer invalid_forged_token"},
        json={"AgentId": agent1.AgentId},
    )
    assert resp.status_code == 401


# ==============================================================================
# 6. ASMX Vehicle & Entity Catalog Master Endpoints Tests (GAP-P1-003)
# ==============================================================================

@pytest.fixture
async def asmx_catalog_fixtures(db_session: AsyncSession):
    """
    Catalog Master Fixture:
    Sets up isolated VehicleType, VehicleMake (PvtCar & Two_Wheeler), VehicleModel,
    VehicleVariant, RTOMaster, and InsuranceCompany for ASMX catalog tests.
    """
    vtype = VehicleType(
        Veh_Type_Name="TEST_PVT_CAR_TYPE",
        VehicleType="Four Wheeler",
        IsAppQuotation=1,
    )
    db_session.add(vtype)

    make_car = VehicleMake(
        Make_Name="TEST_MARUTI",
        PvtCar="1",
        Two_Wheeler="0",
        GCV="0",
        PCV="0",
        isdeleted=0,
    )
    make_bike = VehicleMake(
        Make_Name="TEST_HONDA_BIKE",
        PvtCar="0",
        Two_Wheeler="1",
        GCV="0",
        PCV="0",
        isdeleted=0,
    )
    db_session.add(make_car)
    db_session.add(make_bike)
    await db_session.commit()
    await db_session.refresh(vtype)
    await db_session.refresh(make_car)
    await db_session.refresh(make_bike)

    model1 = VehicleModel(
        Make_ID=make_car.Make_ID,
        Model_Name="TEST_SWIFT",
        SegmentId=1,
        isdeleted=0,
    )
    db_session.add(model1)
    await db_session.commit()
    await db_session.refresh(model1)

    variant1 = VehicleVariant(
        Model_ID=model1.Model_ID,
        Veh_Type_ID=vtype.Veh_Type_ID,
        Variance="TEST_SWIFT_VXI",
        CC="1197",
        Seating_Capacity="5",
        Carrying_Capacity="0",
        Body_Type="Hatchback",
    )
    db_session.add(variant1)

    rto1 = RTOMaster(
        RTOLocation="TEST_BANDRA_RTO",
        District="MUMBAI",
        REG_code="MH02_TEST",
        StateId=14,
        ClusterId=1,
        zone="West",
        RTOWithLocation="MH-02 (TEST BANDRA)",
        isdeleted=0,
    )
    db_session.add(rto1)

    insurer1 = InsuranceCompany(
        InsuranceCompany="TEST_RELIANCE_GI",
        BranchName="MUMBAI_MAIN",
        BranchCode="BR001",
        NCB="1",
        Cluster="1",
        ZeroDeep="1",
        isdeleted="0",
        IsAppQuotation="1",
        MailId="test@reliance.com",
        CompImgPath="/logos/reliance.png",
        LedgerMId=700,
        ShortName="TEST_REL",
        PolicyNo="POL_TEST",
        len=16,
    )
    db_session.add(insurer1)
    await db_session.commit()
    await db_session.refresh(variant1)
    await db_session.refresh(rto1)
    await db_session.refresh(insurer1)

    yield {
        "vtype": vtype,
        "make_car": make_car,
        "make_bike": make_bike,
        "model1": model1,
        "variant1": variant1,
        "rto1": rto1,
        "insurer1": insurer1,
    }

    # Teardown
    await db_session.delete(variant1)
    await db_session.delete(model1)
    await db_session.delete(make_bike)
    await db_session.delete(make_car)
    await db_session.delete(vtype)
    await db_session.delete(rto1)
    await db_session.delete(insurer1)
    await db_session.commit()


@pytest.mark.asyncio
async def test_select_vehicle_type_json_success(
    async_client: AsyncClient, asmx_catalog_fixtures: dict
):
    """Verify POST /Service.asmx/SelectVehicleType returns expected JSON array with 5 fields."""
    vtype = asmx_catalog_fixtures["vtype"]
    resp = await async_client.post("/Service.asmx/SelectVehicleType", json={})
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    matching = [x for x in data if x.get("Veh_Type_ID") == vtype.Veh_Type_ID]
    assert len(matching) == 1
    item = matching[0]
    assert item["Veh_Type_ID"] == vtype.Veh_Type_ID
    assert item["VehicleTypeId"] == vtype.Veh_Type_ID
    assert item["Veh_Type_Name"] == "TEST_PVT_CAR_TYPE"
    assert item["VehicleType"] == "Four Wheeler"
    assert item["IsAppQuotation"] == 1


@pytest.mark.asyncio
async def test_select_vehicle_type_form_encoded_success(
    async_client: AsyncClient, asmx_catalog_fixtures: dict
):
    """Verify POST /Service.asmx/SelectVehicleType handles application/x-www-form-urlencoded."""
    vtype = asmx_catalog_fixtures["vtype"]
    resp = await async_client.post(
        "/Service.asmx/SelectVehicleType",
        data={"IsAppQuotation": "1"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert any(x.get("Veh_Type_ID") == vtype.Veh_Type_ID for x in data)


@pytest.mark.asyncio
async def test_select_vehicle_type_alias_route(
    async_client: AsyncClient, asmx_catalog_fixtures: dict
):
    """Verify alias route /Service.asmx/SelectVehicleTypeForQuaotation functions identically."""
    vtype = asmx_catalog_fixtures["vtype"]
    resp = await async_client.post(
        "/Service.asmx/SelectVehicleTypeForQuaotation",
        json={"IsAppQuotation": 1},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert any(x.get("Veh_Type_ID") == vtype.Veh_Type_ID for x in data)


@pytest.mark.asyncio
async def test_select_vehicle_make_json_success(
    async_client: AsyncClient, asmx_catalog_fixtures: dict
):
    """Verify POST /Service.asmx/SelectVehicleMake returns expected JSON array with 11 fields."""
    make_car = asmx_catalog_fixtures["make_car"]
    resp = await async_client.post("/Service.asmx/SelectVehicleMake", json={})
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    matching = [x for x in data if x.get("Make_ID") == make_car.Make_ID]
    assert len(matching) == 1
    item = matching[0]
    assert item["Make_ID"] == make_car.Make_ID
    assert item["VehicleMakeId"] == make_car.Make_ID
    assert item["Make_Name"] == "TEST_MARUTI"
    assert item["CompanyName"] == "TEST_MARUTI"
    assert item["PvtCar"] == "1"


@pytest.mark.asyncio
async def test_select_vehicle_make_category_filter(
    async_client: AsyncClient, asmx_catalog_fixtures: dict
):
    """Verify filtering by category (e.g. Two_Wheeler vs PvtCar) filters results correctly."""
    make_car = asmx_catalog_fixtures["make_car"]
    make_bike = asmx_catalog_fixtures["make_bike"]

    # Filter for Two_Wheeler
    resp_bike = await async_client.post(
        "/Service.asmx/SelectVehicleMake",
        json={"Category": "Two_Wheeler"},
    )
    assert resp_bike.status_code == 200
    bike_data = resp_bike.json()
    assert any(x["Make_ID"] == make_bike.Make_ID for x in bike_data)
    assert not any(x["Make_ID"] == make_car.Make_ID for x in bike_data)

    # Filter for PvtCar
    resp_car = await async_client.post(
        "/Service.asmx/SelectVehicleMake",
        json={"Category": "PvtCar"},
    )
    assert resp_car.status_code == 200
    car_data = resp_car.json()
    assert any(x["Make_ID"] == make_car.Make_ID for x in car_data)
    assert not any(x["Make_ID"] == make_bike.Make_ID for x in car_data)


@pytest.mark.asyncio
async def test_select_vehicle_make_conflicting_params(
    async_client: AsyncClient, asmx_catalog_fixtures: dict
):
    """Verify conflicting parameter values in payload fail gracefully to empty list."""
    resp = await async_client.post(
        "/Service.asmx/SelectVehicleMake",
        json={"Category": "PvtCar", "category": "Two_Wheeler"},
    )
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_select_vehicle_make_alias_routes(
    async_client: AsyncClient, asmx_catalog_fixtures: dict
):
    """Verify all alias routes for SelectVehicleMake work identically."""
    make_car = asmx_catalog_fixtures["make_car"]
    aliases = [
        "/Service.asmx/selectVehicleMakeByType",
        "/Service.asmx/selectVehicleMakeByTypeNew",
        "/Service.asmx/SelectVehicleMakeForQuaotation",
    ]
    for url in aliases:
        resp = await async_client.post(url, json={"Category": "PvtCar"})
        assert resp.status_code == 200, f"Failed on alias {url}"
        assert any(x["Make_ID"] == make_car.Make_ID for x in resp.json())


@pytest.mark.asyncio
async def test_select_vehicle_model_by_make_id(
    async_client: AsyncClient, asmx_catalog_fixtures: dict
):
    """Verify POST /Service.asmx/SelectVehicleModel by Make_ID returns models."""
    make_car = asmx_catalog_fixtures["make_car"]
    model1 = asmx_catalog_fixtures["model1"]

    # Test with Make_ID
    resp = await async_client.post(
        "/Service.asmx/SelectVehicleModel",
        json={"Make_ID": make_car.Make_ID},
    )
    assert resp.status_code == 200
    data = resp.json()
    matching = [x for x in data if x.get("Model_ID") == model1.Model_ID]
    assert len(matching) == 1
    item = matching[0]
    assert item["Model_ID"] == model1.Model_ID
    assert item["ModelId"] == model1.Model_ID
    assert item["Model_Name"] == "TEST_SWIFT"
    assert item["ModelName"] == "TEST_SWIFT"
    assert item["Make_ID"] == make_car.Make_ID

    # Test with VehicleMakeId alias
    resp_alias_key = await async_client.post(
        "/Service.asmx/SelectVehicleModel",
        json={"VehicleMakeId": make_car.Make_ID},
    )
    assert resp_alias_key.status_code == 200
    assert any(x.get("Model_ID") == model1.Model_ID for x in resp_alias_key.json())


@pytest.mark.asyncio
async def test_select_vehicle_model_form_encoded(
    async_client: AsyncClient, asmx_catalog_fixtures: dict
):
    """Verify POST /Service.asmx/SelectVehicleModel via application/x-www-form-urlencoded."""
    make_car = asmx_catalog_fixtures["make_car"]
    model1 = asmx_catalog_fixtures["model1"]

    resp = await async_client.post(
        "/Service.asmx/SelectVehicleModel",
        data={"Make_ID": str(make_car.Make_ID)},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert resp.status_code == 200
    assert any(x.get("Model_ID") == model1.Model_ID for x in resp.json())


@pytest.mark.asyncio
async def test_select_vehicle_model_not_found_and_invalid(
    async_client: AsyncClient, asmx_catalog_fixtures: dict
):
    """Verify non-existent make ID, negative ID, and non-integer inputs return empty list []."""
    for bad_input in [999999, -1, 0, "invalid_abc"]:
        resp = await async_client.post(
            "/Service.asmx/SelectVehicleModel",
            json={"Make_ID": bad_input},
        )
        assert resp.status_code == 200
        assert resp.json() == []


@pytest.mark.asyncio
async def test_select_vehicle_model_alias_routes(
    async_client: AsyncClient, asmx_catalog_fixtures: dict
):
    """Verify alias routes for SelectVehicleModel work as expected."""
    make_car = asmx_catalog_fixtures["make_car"]
    model1 = asmx_catalog_fixtures["model1"]
    aliases = [
        "/Service.asmx/selectVehicleModel",
        "/Service.asmx/AppVehicleModelNew",
        "/Service.asmx/SelectVehicleModelForQuaotation",
    ]
    for url in aliases:
        resp = await async_client.post(url, json={"Make_ID": make_car.Make_ID})
        assert resp.status_code == 200, f"Failed on alias {url}"
        assert any(x["Model_ID"] == model1.Model_ID for x in resp.json())


@pytest.mark.asyncio
async def test_select_vehicle_variance_by_model_id(
    async_client: AsyncClient, asmx_catalog_fixtures: dict
):
    """Verify POST /Service.asmx/SelectVehicleVariance by ModelId returns variants."""
    model1 = asmx_catalog_fixtures["model1"]
    variant1 = asmx_catalog_fixtures["variant1"]

    # Test with ModelId
    resp = await async_client.post(
        "/Service.asmx/SelectVehicleVariance",
        json={"ModelId": model1.Model_ID},
    )
    assert resp.status_code == 200
    data = resp.json()
    matching = [x for x in data if x.get("Variant_ID") == variant1.Variant_ID]
    assert len(matching) == 1
    item = matching[0]
    assert item["Variant_ID"] == variant1.Variant_ID
    assert item["VariantId"] == variant1.Variant_ID
    assert item["Variance"] == "TEST_SWIFT_VXI"
    assert item["VarianceName"] == "TEST_SWIFT_VXI"
    assert item["Model_ID"] == model1.Model_ID
    assert item["CC"] == "1197"
    assert item["Seating_Capacity"] == "5"

    # Test with Model_ID alias key
    resp2 = await async_client.post(
        "/Service.asmx/SelectVehicleVariance",
        json={"Model_ID": model1.Model_ID},
    )
    assert resp2.status_code == 200
    assert any(x.get("Variant_ID") == variant1.Variant_ID for x in resp2.json())


@pytest.mark.asyncio
async def test_select_vehicle_variance_by_model_and_veh_type(
    async_client: AsyncClient, asmx_catalog_fixtures: dict
):
    """Verify POST /Service.asmx/SelectVehicleVariance filtering by ModelId and VehTypeId."""
    model1 = asmx_catalog_fixtures["model1"]
    vtype = asmx_catalog_fixtures["vtype"]
    variant1 = asmx_catalog_fixtures["variant1"]

    resp = await async_client.post(
        "/Service.asmx/SelectVehicleVariance",
        json={"ModelId": model1.Model_ID, "VehTypeId": vtype.Veh_Type_ID},
    )
    assert resp.status_code == 200
    assert any(x.get("Variant_ID") == variant1.Variant_ID for x in resp.json())

    # Mismatched veh_type_id returns empty list
    resp_mismatch = await async_client.post(
        "/Service.asmx/SelectVehicleVariance",
        json={"ModelId": model1.Model_ID, "VehTypeId": 99999},
    )
    assert resp_mismatch.status_code == 200
    assert resp_mismatch.json() == []


@pytest.mark.asyncio
async def test_select_vehicle_variance_alias_routes(
    async_client: AsyncClient, asmx_catalog_fixtures: dict
):
    """Verify alias routes for SelectVehicleVariance work identically."""
    model1 = asmx_catalog_fixtures["model1"]
    variant1 = asmx_catalog_fixtures["variant1"]
    aliases = [
        "/Service.asmx/selectVehicleVariantType",
        "/Service.asmx/SelectVehicleVarianceForQuaotation",
        "/Service.asmx/selectVehicleVariantSubType",
    ]
    for url in aliases:
        resp = await async_client.post(url, json={"ModelId": model1.Model_ID})
        assert resp.status_code == 200, f"Failed on alias {url}"
        assert any(x["Variant_ID"] == variant1.Variant_ID for x in resp.json())


@pytest.mark.asyncio
async def test_select_rto_list_all_and_by_id(
    async_client: AsyncClient, asmx_catalog_fixtures: dict
):
    """Verify POST /Service.asmx/SelectRTO returns all RTOs and supports filtering by RTOId / StateId."""
    rto1 = asmx_catalog_fixtures["rto1"]

    # All RTOs
    resp_all = await async_client.post("/Service.asmx/SelectRTO", json={})
    assert resp_all.status_code == 200
    assert any(x.get("RTOId") == rto1.RTOId for x in resp_all.json())

    # By RTOId
    resp_one = await async_client.post(
        "/Service.asmx/SelectRTO",
        json={"RTOId": rto1.RTOId},
    )
    assert resp_one.status_code == 200
    data = resp_one.json()
    assert len(data) == 1
    assert data[0]["RTOId"] == rto1.RTOId
    assert data[0]["RTO_ID"] == rto1.RTOId
    assert data[0]["RTOLocation"] == "TEST_BANDRA_RTO"
    assert data[0]["REG_code"] == "MH02_TEST"
    assert data[0]["StateId"] == 14

    # By StateId
    resp_state = await async_client.post(
        "/Service.asmx/SelectRTO",
        json={"StateId": 14},
    )
    assert resp_state.status_code == 200
    assert any(x.get("RTOId") == rto1.RTOId for x in resp_state.json())


@pytest.mark.asyncio
async def test_select_rto_alias_routes(
    async_client: AsyncClient, asmx_catalog_fixtures: dict
):
    """Verify alias routes /selectAppRto and /SelectRTOByID work as expected."""
    rto1 = asmx_catalog_fixtures["rto1"]

    resp1 = await async_client.post("/Service.asmx/selectAppRto", json={})
    assert resp1.status_code == 200
    assert any(x.get("RTOId") == rto1.RTOId for x in resp1.json())

    resp2 = await async_client.post(
        "/Service.asmx/SelectRTOByID",
        json={"RTOId": rto1.RTOId},
    )
    assert resp2.status_code == 200
    assert len(resp2.json()) == 1
    assert resp2.json()[0]["RTOId"] == rto1.RTOId


@pytest.mark.asyncio
async def test_select_insurance_company_list_all_and_by_id(
    async_client: AsyncClient, asmx_catalog_fixtures: dict
):
    """Verify POST /Service.asmx/SelectInsuranceCompany returns insurance companies."""
    insurer1 = asmx_catalog_fixtures["insurer1"]

    # All insurers
    resp_all = await async_client.post("/Service.asmx/SelectInsuranceCompany", json={})
    assert resp_all.status_code == 200
    matching = [x for x in resp_all.json() if x.get("InsuranceCompanyId") == insurer1.InsuranceCompanyId]
    assert len(matching) == 1
    item = matching[0]
    assert item["InsuranceCompanyId"] == insurer1.InsuranceCompanyId
    assert item["InsuranceCompany"] == "TEST_RELIANCE_GI"
    assert item["BranchName"] == "MUMBAI_MAIN"
    assert item["BranchCode"] == "BR001"
    assert item["MailId"] == "test@reliance.com"
    assert item["CompImgPath"] == "/logos/reliance.png"
    assert item["ShortName"] == "TEST_REL"

    # By ID
    resp_one = await async_client.post(
        "/Service.asmx/SelectInsuranceCompany",
        json={"InsuranceCompanyId": insurer1.InsuranceCompanyId},
    )
    assert resp_one.status_code == 200
    data = resp_one.json()
    assert len(data) == 1
    assert data[0]["InsuranceCompanyId"] == insurer1.InsuranceCompanyId


@pytest.mark.asyncio
async def test_select_insurance_company_alias_route(
    async_client: AsyncClient, asmx_catalog_fixtures: dict
):
    """Verify alias route /Service.asmx/SelectInsuranceCompanyNew works identically."""
    insurer1 = asmx_catalog_fixtures["insurer1"]
    resp = await async_client.post("/Service.asmx/SelectInsuranceCompanyNew", json={})
    assert resp.status_code == 200
    assert any(x.get("InsuranceCompanyId") == insurer1.InsuranceCompanyId for x in resp.json())
