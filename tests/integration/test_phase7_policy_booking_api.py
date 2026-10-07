"""
Phase 7 Integration Tests — Policy Booking & Transaction REST APIs, RBAC Role Gates,
Branch Isolation, Principal Ownership Scoping, Staged Proposal Approvals, Subsequent
Payments, and Policy Cancellation.
"""
import uuid
from datetime import date
from decimal import Decimal
from typing import Optional, Tuple
import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, get_password_hash
from app.models.customer import Customer
from app.models.user import User, UserRole
from app.models.vehicle import VehicleDetails
from app.repositories.role import RoleRepository
from app.repositories.user import UserRepository


@pytest.fixture(autouse=True)
async def cleanup_phase7_tables(db_session: AsyncSession):
    """Ensure clean Phase 7 policy/transaction tables before and after each test."""
    await db_session.execute(text("DELETE FROM tbl_account;"))
    await db_session.execute(text("DELETE FROM tbl_transactionpayment;"))
    await db_session.execute(text("DELETE FROM tbl_franchisecommission;"))
    await db_session.execute(text("DELETE FROM tbl_agentcommissionpayment;"))
    await db_session.execute(text("DELETE FROM tbl_cutnpaycommpayable;"))
    await db_session.execute(text("DELETE FROM tbl_transaction;"))
    await db_session.execute(text("DELETE FROM tbl_transactionappnew;"))
    await db_session.commit()
    yield
    await db_session.execute(text("DELETE FROM tbl_account;"))
    await db_session.execute(text("DELETE FROM tbl_transactionpayment;"))
    await db_session.execute(text("DELETE FROM tbl_franchisecommission;"))
    await db_session.execute(text("DELETE FROM tbl_agentcommissionpayment;"))
    await db_session.execute(text("DELETE FROM tbl_cutnpaycommpayable;"))
    await db_session.execute(text("DELETE FROM tbl_transaction;"))
    await db_session.execute(text("DELETE FROM tbl_transactionappnew;"))
    await db_session.commit()


async def create_user_with_role(
    db_session: AsyncSession,
    role_name: str,
    branch_id: Optional[int] = 101,
    partner_user_id: Optional[int] = None,
    password: str = "Password123!",
) -> Tuple[User, dict[str, str]]:
    """Helper to provision a synthetic test user, role, and Bearer authorization header."""
    user_repo = UserRepository(db_session)
    role_repo = RoleRepository(db_session)

    role = UserRole(
        UserRole=role_name,
        code=(role_name[:3].upper() if role_name else "ROL"),
        isdeleted="0",
    )
    await role_repo.create(role)

    username = f"u7_{role_name[:4].strip().lower()}_{uuid.uuid4().hex[:6]}"
    user = User(
        UserName=username,
        UserPassword=get_password_hash(password),
        UserRoleId=role.UserRoleId,
        BranchId=branch_id,
        partner_user_id=partner_user_id,
        isdeleted="0",
        mobile_no="9876543210",
    )
    await user_repo.create(user)
    await db_session.commit()
    await db_session.refresh(user)

    token = create_access_token(
        {
            "sub": str(user.UserId),
            "username": user.UserName,
            "role": role_name,
            "branch_id": branch_id,
        }
    )
    return user, {"Authorization": f"Bearer {token}"}


async def create_synthetic_customer_and_vehicle(
    db_session: AsyncSession,
    branch_id: int = 101,
    reg_no: str = "MH12TEST0001",
) -> Tuple[Customer, VehicleDetails]:
    """Creates synthetic TEST_CUSTOMER and TEST_VEHICLE rows in local test DB."""
    cust = Customer(
        CustFName="TEST_CUSTOMER_001",
        CustLName="SYNTHETIC",
        MoblieNo1="9876500001",
        BranchId=branch_id,
        isdeleted="0",
    )
    db_session.add(cust)
    await db_session.flush()
    cust.CustomerCode = str(cust.CustomerId)

    veh = VehicleDetails(
        CustomerId=cust.CustomerId,
        RegistrationNo=reg_no,
        ChaiseNo="SYNTHCHASSIS00001",
        EngineNo="SYNTHENGINE00001",
        MfgYear="2024",
        FuelTypeId=1,
        Veh_Type_ID=1,
        BranchId=branch_id,
        isdeleted="0",
        FinancialYear="2026-2027",
    )
    db_session.add(veh)
    await db_session.commit()
    await db_session.refresh(cust)
    await db_session.refresh(veh)
    return cust, veh


# ============================================================================
# 1. Authentication & Role Gate Enforcement
# ============================================================================


@pytest.mark.asyncio
async def test_unauthenticated_policy_endpoints_rejected_401(async_client: AsyncClient):
    r1 = await async_client.post(
        "/api/v1/policies/preview",
        json={"vehicle_category": "PVT", "od_premium": "5000", "tp_premium": "2000"},
    )
    assert r1.status_code == 401

    r2 = await async_client.post("/api/v1/policies/book", json={})
    assert r2.status_code == 401

    r3 = await async_client.get("/api/v1/policies")
    assert r3.status_code == 401


@pytest.mark.asyncio
@pytest.mark.parametrize("restricted_role", ["AGENT", "RELATIONSHIP MANAGER", "CASHIER", "CLAIM", "pOLICY VIEW"])
async def test_non_booking_roles_rejected_403_on_direct_book(
    async_client: AsyncClient,
    db_session: AsyncSession,
    restricted_role: str,
):
    """Roles outside POLICY_BOOKING_WRITE_ROLES cannot call POST /api/v1/policies/book directly."""
    _, headers = await create_user_with_role(db_session, role_name=restricted_role, branch_id=101)
    cust, veh = await create_synthetic_customer_and_vehicle(db_session, branch_id=101)

    resp = await async_client.post(
        "/api/v1/policies/book",
        headers=headers,
        json={
            "customer_id": cust.CustomerId,
            "cust_veh_id": veh.CustVehId,
            "vehicle_category": "PVT",
            "od_premium": "5000.00",
            "tp_premium": "2000.00",
        },
    )
    assert resp.status_code == 403


# ============================================================================
# 2. Branch Isolation & Principal Ownership Scoping
# ============================================================================


@pytest.mark.asyncio
async def test_branch_isolation_enforced_on_policy_booking_and_read(
    async_client: AsyncClient,
    db_session: AsyncSession,
):
    """Branch 101 OPERATOR cannot book or read a policy for Branch 202 Customer/Vehicle."""
    _, op_b101_headers = await create_user_with_role(db_session, role_name="OPERATOR", branch_id=101)
    _, op_b202_headers = await create_user_with_role(db_session, role_name="OPERATOR", branch_id=202)
    _, admin_headers = await create_user_with_role(db_session, role_name="ADMIN", branch_id=101)

    cust_b202, veh_b202 = await create_synthetic_customer_and_vehicle(
        db_session, branch_id=202, reg_no="MH14BR202"
    )

    # 1. Branch 101 operator tries to book policy for Branch 202 customer -> 403
    forbidden_book = await async_client.post(
        "/api/v1/policies/book",
        headers=op_b101_headers,
        json={
            "customer_id": cust_b202.CustomerId,
            "cust_veh_id": veh_b202.CustVehId,
            "vehicle_category": "PVT",
            "od_premium": "6000.00",
            "tp_premium": "2500.00",
            "payments": [{"payment_type": "CASH", "paid_amount": "10030.00"}],
        },
    )
    assert forbidden_book.status_code == 403

    # 2. Branch 202 operator books the policy -> 201 Created
    ok_book = await async_client.post(
        "/api/v1/policies/book",
        headers=op_b202_headers,
        json={
            "customer_id": cust_b202.CustomerId,
            "cust_veh_id": veh_b202.CustVehId,
            "vehicle_category": "PVT",
            "od_premium": "6000.00",
            "tp_premium": "2500.00",
            "payments": [{"payment_type": "CASH", "paid_amount": "10030.00"}],
        },
    )
    assert ok_book.status_code == 201
    tx_id = ok_book.json()["transaction_id"]

    # 3. Branch 101 operator tries to GET Branch 202 policy -> 403
    get_b101 = await async_client.get(f"/api/v1/policies/{tx_id}", headers=op_b101_headers)
    assert get_b101.status_code == 403

    # 4. Global ADMIN in Branch 101 can GET Branch 202 policy -> 200 OK
    get_admin = await async_client.get(f"/api/v1/policies/{tx_id}", headers=admin_headers)
    assert get_admin.status_code == 200
    assert get_admin.json()["branch_id"] == 202


@pytest.mark.asyncio
async def test_franchise_principal_cannot_spoof_another_franchise_id(
    async_client: AsyncClient,
    db_session: AsyncSession,
):
    """FRANCHISE user bound to franchise_id=501 cannot book a policy claiming franchise_id=999."""
    _, frn_headers = await create_user_with_role(
        db_session, role_name="FRANCHISE", branch_id=101, partner_user_id=501
    )
    cust, veh = await create_synthetic_customer_and_vehicle(db_session, branch_id=101)

    spoof_resp = await async_client.post(
        "/api/v1/policies/book",
        headers=frn_headers,
        json={
            "customer_id": cust.CustomerId,
            "cust_veh_id": veh.CustVehId,
            "vehicle_category": "PVT",
            "od_premium": "4000.00",
            "tp_premium": "2000.00",
            "commission": {
                "franchise_id": 999,
                "agent_comm_od_percent": "10.00",
            },
        },
    )
    assert spoof_resp.status_code == 403

    # Booking without spoofed franchise_id automatically binds to 501 and writes tbl_franchisecommission
    valid_resp = await async_client.post(
        "/api/v1/policies/book",
        headers=frn_headers,
        json={
            "customer_id": cust.CustomerId,
            "cust_veh_id": veh.CustVehId,
            "vehicle_category": "PVT",
            "od_premium": "4000.00",
            "tp_premium": "2000.00",
            "commission": {
                "agent_comm_od_percent": "10.00",
            },
        },
    )
    assert valid_resp.status_code == 201
    body = valid_resp.json()
    assert body["commission_summary"]["franchise_id"] == 501
    assert body["commission_summary"]["franchise_comm_id"] is not None


# ============================================================================
# 3. Staged Mobile Proposal Intake & Approval Gates (tbl_transactionappnew)
# ============================================================================


@pytest.mark.asyncio
async def test_staged_proposal_lifecycle_and_approval_gates(
    async_client: AsyncClient,
    db_session: AsyncSession,
):
    """
    Tests AGENT creating a staged proposal -> CASHIER approval -> ACCOUNTANT approval
    -> OWNER approval -> OPERATOR converting proposal into a booked policy.
    """
    _, agent_headers = await create_user_with_role(
        db_session, role_name="AGENT", branch_id=101, partner_user_id=777
    )
    _, cashier_headers = await create_user_with_role(
        db_session, role_name="CASHIER", branch_id=101
    )
    _, account_headers = await create_user_with_role(
        db_session, role_name="ACCOUNT", branch_id=101
    )
    _, owner_headers = await create_user_with_role(
        db_session, role_name="OWNER", branch_id=101
    )
    _, operator_headers = await create_user_with_role(
        db_session, role_name="OPERATOR", branch_id=101
    )

    # 1. Agent creates proposal (attempting to pass agent_id=888; server binds to 777)
    prop_resp = await async_client.post(
        "/api/v1/policies/proposals",
        headers=agent_headers,
        json={
            "customer_name": "TEST_CUSTOMER_PROPOSAL",
            "contact_no": "9876543210",
            "registration_no": "MH12PR0001",
            "insurance_company_id": 2,
            "od_premium": "8000.00",
            "tp_premium": "2000.00",
            "net_premium": "10000.00",
            "final_premium": "11800.00",
            "cash_paid_amount": "5000.00",
            "ewallet_used_amount": "1800.00",
            "agent_id": 888,
        },
    )
    assert prop_resp.status_code == 201
    prop_data = prop_resp.json()
    trans_id = prop_data["trans_id"]
    assert prop_data["user_id"] == 777
    assert Decimal(prop_data["cash_short_amount"]) == Decimal("5000.00")
    assert prop_data["is_owner_approve"] == 0
    assert prop_data["is_cashier_approve"] == 0
    assert prop_data["is_account_approval"] == 0

    # 2. Cashier cannot approve OWNER stage -> 403
    bad_stage = await async_client.post(
        f"/api/v1/policies/proposals/{trans_id}/approve",
        headers=cashier_headers,
        json={"stage": "OWNER", "approved": True},
    )
    assert bad_stage.status_code == 403

    # 3. Cashier approves CASHIER stage -> 200
    c_app = await async_client.post(
        f"/api/v1/policies/proposals/{trans_id}/approve",
        headers=cashier_headers,
        json={"stage": "CASHIER", "approved": True},
    )
    assert c_app.status_code == 200
    assert c_app.json()["is_cashier_approve"] == 1

    # 4. Accountant approves ACCOUNTANT stage -> 200
    a_app = await async_client.post(
        f"/api/v1/policies/proposals/{trans_id}/approve",
        headers=account_headers,
        json={"stage": "ACCOUNTANT", "approved": True, "remark": "Verified TDS & Net"},
    )
    assert a_app.status_code == 200
    assert a_app.json()["is_account_approval"] == 1
    assert a_app.json()["account_remark"] == "Verified TDS & Net"

    # 5. Owner approves OWNER stage -> 200
    o_app = await async_client.post(
        f"/api/v1/policies/proposals/{trans_id}/approve",
        headers=owner_headers,
        json={"stage": "OWNER", "approved": True},
    )
    assert o_app.status_code == 200
    assert o_app.json()["is_owner_approve"] == 1

    # 6. Operator converts staged proposal into booked policy
    cust, veh = await create_synthetic_customer_and_vehicle(
        db_session, branch_id=101, reg_no="MH12PR0001"
    )
    book_resp = await async_client.post(
        "/api/v1/policies/book",
        headers=operator_headers,
        json={
            "customer_id": cust.CustomerId,
            "cust_veh_id": veh.CustVehId,
            "proposal_trans_id": trans_id,
            "insurance_company_id": 2,
            "vehicle_category": "PVT",
            "od_premium": "8000.00",
            "tp_premium": "2000.00",
            "ewallet_amount_used": "1800.00",
            "payments": [{"payment_type": "CASH", "paid_amount": "5000.00"}],
        },
    )
    assert book_resp.status_code == 201
    booked = book_resp.json()
    assert booked["proposal_trans_id"] == trans_id
    assert Decimal(booked["payment_summary"]["outstanding_amount"]) == Decimal("5000.00")
    assert booked["t_status"] == "Pending"

    # Verify proposal is now marked IsSubmit = 1
    prop_after = await async_client.get(
        f"/api/v1/policies/proposals/{trans_id}",
        headers=operator_headers,
    )
    assert prop_after.status_code == 200
    assert prop_after.json()["is_submit"] == 1


# ============================================================================
# 4. Subsequent Payment Recording, Policy Update & Policy Cancellation
# ============================================================================


@pytest.mark.asyncio
async def test_subsequent_payment_update_and_cancellation_reverses_all_rows(
    async_client: AsyncClient,
    db_session: AsyncSession,
):
    """
    Books a policy with partial payment -> records remaining payment -> updates PolicyNo
    -> cancels policy and verifies all downstream rows are soft-deleted.
    """
    _, op_headers = await create_user_with_role(db_session, role_name="OPERATOR", branch_id=101)
    _, admin_headers = await create_user_with_role(db_session, role_name="ADMIN", branch_id=101)
    cust, veh = await create_synthetic_customer_and_vehicle(db_session, branch_id=101)

    # 1. Book policy with partial payment (Paid 5000 of 11800)
    book_resp = await async_client.post(
        "/api/v1/policies/book",
        headers=op_headers,
        json={
            "customer_id": cust.CustomerId,
            "cust_veh_id": veh.CustVehId,
            "vehicle_category": "PVT",
            "od_premium": "8000.00",
            "tp_premium": "2000.00",
            "commission": {
                "agent_id": 401,
                " franchise_id": 601,
                "agent_comm_od_percent": "10.00",
            }
            if False
            else {
                "agent_id": 401,
                "franchise_id": 601,
                "agent_comm_od_percent": "10.00",
            },
            "payments": [{"payment_type": "CASH", "paid_amount": "5000.00"}],
        },
    )
    assert book_resp.status_code == 201
    tx_id = book_resp.json()["transaction_id"]
    assert Decimal(book_resp.json()["payment_summary"]["outstanding_amount"]) == Decimal("6800.00")
    assert book_resp.json()["t_status"] == "Pending"

    # 2. Overpaying remaining balance (7000 > 6800) is rejected with 422
    over_resp = await async_client.post(
        f"/api/v1/policies/{tx_id}/payments",
        headers=op_headers,
        json={"payment_type": "ONLINE", "paid_amount": "7000.00", "docno": "UTR999"},
    )
    assert over_resp.status_code == 422

    # 3. Pay exact remaining balance (6800.00) -> completes payment & sets TStatus="Booked"
    pay_resp = await async_client.post(
        f"/api/v1/policies/{tx_id}/payments",
        headers=op_headers,
        json={"payment_type": "ONLINE", "paid_amount": "6800.00", "docno": "UTR888"},
    )
    assert pay_resp.status_code == 201
    pay_body = pay_resp.json()
    assert Decimal(pay_body["payment_summary"]["paid_amount"]) == Decimal("11800.00")
    assert Decimal(pay_body["payment_summary"]["outstanding_amount"]) == Decimal("0.00")
    assert pay_body["t_status"] == "Booked"
    assert len(pay_body["payment_summary"]["payments"]) == 2
    assert len(pay_body["accounting_entries"]) == 4  # Initial 1,2,3 + subsequent AccTransId=2

    # 4. Update PolicyNo via PUT /api/v1/policies/{tx_id}
    upd_resp = await async_client.put(
        f"/api/v1/policies/{tx_id}",
        headers=op_headers,
        json={"policy_no": "TEST_POLICY_UPD_001", "remark": "Policy Schedule Issued"},
    )
    assert upd_resp.status_code == 200
    assert upd_resp.json()["policy_no"] == "TEST_POLICY_UPD_001"

    # 5. Operator cannot cancel policy (only ADMIN/OWNER/ACCOUNT/IT SUPPORT) -> 403
    op_cancel = await async_client.post(
        f"/api/v1/policies/{tx_id}/cancel",
        headers=op_headers,
        json={"reason": "Customer requested cancellation"},
    )
    assert op_cancel.status_code == 403

    # 6. ADMIN cancels policy -> 200 OK & reverses all downstream rows
    adm_cancel = await async_client.post(
        f"/api/v1/policies/{tx_id}/cancel",
        headers=admin_headers,
        json={"reason": "Cheque dishonored / Cancelled by Admin"},
    )
    assert adm_cancel.status_code == 200
    c_body = adm_cancel.json()
    assert c_body["t_status"] == "Cancelled"
    assert c_body["isdeleted"] == "1"
    assert c_body["payments_reversed"] == 2
    assert c_body["accounting_entries_reversed"] == 4
    assert c_body["franchise_commissions_reversed"] == 1
    assert c_body["agent_comm_payments_reversed"] == 1

    # 7. Cancelled policy returns 404 on active GET
    get_after = await async_client.get(f"/api/v1/policies/{tx_id}", headers=admin_headers)
    assert get_after.status_code == 404
