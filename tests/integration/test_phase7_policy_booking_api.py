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
from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, get_password_hash
from app.models.customer import Customer
from app.models.transaction import Transaction
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

    # 4b. Partial update rollback verification: expiry_date before persisted risk_start_date
    cur_pol = (await async_client.get(f"/api/v1/policies/{tx_id}", headers=op_headers)).json()
    orig_expiry = cur_pol["expiry_date"]
    orig_remark = cur_pol["remark"]

    inv_upd1 = await async_client.put(
        f"/api/v1/policies/{tx_id}",
        headers=op_headers,
        json={"expiry_date": "2020-01-01", "remark": "INVALID_EXPIRY_REMARK"},
    )
    assert inv_upd1.status_code == 400
    assert "Policy ExpiryDate cannot be earlier than RiskStartdate" in inv_upd1.json()["error"]["message"]

    # Verify database state was rolled back (persisted dates and remark unchanged)
    chk1 = (await async_client.get(f"/api/v1/policies/{tx_id}", headers=op_headers)).json()
    assert chk1["expiry_date"] == orig_expiry
    assert chk1["remark"] == orig_remark

    # 4c. Partial update rollback verification: risk_start_date after persisted expiry_date
    inv_upd2 = await async_client.put(
        f"/api/v1/policies/{tx_id}",
        headers=op_headers,
        json={"risk_start_date": "2035-01-01", "remark": "INVALID_START_REMARK"},
    )
    assert inv_upd2.status_code == 400
    assert "Policy ExpiryDate cannot be earlier than RiskStartdate" in inv_upd2.json()["error"]["message"]

    # Verify database state was rolled back
    chk2 = (await async_client.get(f"/api/v1/policies/{tx_id}", headers=op_headers)).json()
    assert chk2["risk_start_date"] == cur_pol["risk_start_date"]
    assert chk2["remark"] == orig_remark

    # 4d. Same-day expiry update (equality boundary allowed for commercial transit)
    sameday_upd = await async_client.put(
        f"/api/v1/policies/{tx_id}",
        headers=op_headers,
        json={"risk_start_date": "2026-06-01", "expiry_date": "2026-06-01", "remark": "Transit Policy"},
    )
    assert sameday_upd.status_code == 200
    assert sameday_upd.json()["risk_start_date"].startswith("2026-06-01")
    assert sameday_upd.json()["expiry_date"].startswith("2026-06-01")
    assert sameday_upd.json()["remark"] == "Transit Policy"

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


@pytest.mark.asyncio
async def test_p0_cheque_dd_underwriting_integrity_and_issuance_gates(
    async_client: AsyncClient,
    db_session: AsyncSession,
):
    """
    P0 Financial & Underwriting Integrity Gate Verification:
    1. Uncleared Cheque/DD policies cannot be marked 'Booked' or 'Issued' at booking or via update.
    2. PolicyNo assignment/update is blocked while Cheque/DD is pending clearance or balance is unpaid.
    3. Rejection rolls back transaction atomicity cleanly.
    4. Bank clearance unlocks 'Booked' status and enables PolicyNo issuance.
    5. Partial payments with unpaid balances cannot be issued until fully settled.
    """
    _, op_headers = await create_user_with_role(db_session, role_name="OPERATOR", branch_id=101)
    _, acc_headers = await create_user_with_role(db_session, role_name="ACCOUNT", branch_id=101)
    cust, veh = await create_synthetic_customer_and_vehicle(db_session, branch_id=101, reg_no="MH12P0GATE01")

    # 1. Booking with full premium paid by CHEQUE -> Must remain 'Pending', pendingStatus=1
    book_chq = await async_client.post(
        "/api/v1/policies/book",
        headers=op_headers,
        json={
            "customer_id": cust.CustomerId,
            "cust_veh_id": veh.CustVehId,
            "vehicle_category": "PVT",
            "od_premium": "6000.00",
            "tp_premium": "4000.00",
            "commission": {"agent_id": 401, "franchise_id": 601, "agent_comm_od_percent": "10.00"},
            "payments": [
                {
                    "payment_type": "CHEQUE",
                    "paid_amount": "11800.00",
                    "docno": "CHQ-P0-001",
                    "bankname": "AXIS BANK",
                }
            ],
        },
    )
    assert book_chq.status_code == 201
    chq_data = book_chq.json()
    tx_id = chq_data["transaction_id"]
    pay_id = chq_data["payment_summary"]["payments"][0]["payment_id"]
    assert chq_data["t_status"] == "Pending"
    assert chq_data["pending_status"] == 1
    assert chq_data["policy_no"] is None

    # 2. Attempting to transition status to 'Booked' or 'Issued' on uncleared cheque -> 400 Bad Request
    upd_status_booked = await async_client.put(
        f"/api/v1/policies/{tx_id}",
        headers=op_headers,
        json={"t_status": "Booked", "remark": "Premature Booked Transition"},
    )
    assert upd_status_booked.status_code == 400
    assert "Cheque/DD payment is pending bank clearance" in upd_status_booked.json()["error"]["message"]

    upd_status_issued = await async_client.put(
        f"/api/v1/policies/{tx_id}",
        headers=op_headers,
        json={"t_status": "Issued", "remark": "Premature Issued Transition"},
    )
    assert upd_status_issued.status_code == 400
    assert "Cheque/DD payment is pending bank clearance" in upd_status_issued.json()["error"]["message"]

    # 3. Attempting to assign PolicyNo on uncleared cheque -> 400 Bad Request
    upd_polno = await async_client.put(
        f"/api/v1/policies/{tx_id}",
        headers=op_headers,
        json={"policy_no": "PREMATURE-POL-001", "remark": "Premature PolicyNo"},
    )
    assert upd_polno.status_code == 400
    assert "Cheque/DD payment is pending bank clearance" in upd_polno.json()["error"]["message"]

    # 4. Verify transaction rollback (status and policy_no remain unchanged in DB)
    cur_tx = (await async_client.get(f"/api/v1/policies/{tx_id}", headers=op_headers)).json()
    assert cur_tx["t_status"] == "Pending"
    assert cur_tx["pending_status"] == 1
    assert cur_tx["policy_no"] is None
    assert cur_tx["remark"] is None

    # 5. Deposited but uncleared cheque is still blocked
    dep_resp = await async_client.post(
        f"/api/v1/payments/{pay_id}/deposit",
        headers=acc_headers,
        json={"bank_reference": "DEP-SLIP-P0-001"},
    )
    assert dep_resp.status_code == 200

    upd_after_dep = await async_client.put(
        f"/api/v1/policies/{tx_id}",
        headers=op_headers,
        json={"policy_no": "PREMATURE-POL-DEP-001"},
    )
    assert upd_after_dep.status_code == 400
    assert "Cheque/DD payment is pending bank clearance" in upd_after_dep.json()["error"]["message"]

    # 6. Clearance releases the gate: transitions policy to 'Booked' and allows PolicyNo assignment
    clr_resp = await async_client.post(
        f"/api/v1/payments/{pay_id}/clear",
        headers=acc_headers,
        json={"bank_reference": "CLR-UTR-P0-001"},
    )
    assert clr_resp.status_code == 200
    assert clr_resp.json()["policy_t_status"] == "Booked"
    assert clr_resp.json()["policy_pending_status"] == 0

    upd_after_clr = await async_client.put(
        f"/api/v1/policies/{tx_id}",
        headers=op_headers,
        json={"policy_no": "VALID-ISSUED-POL-001", "remark": "Policy Schedule Issued After Clearance"},
    )
    assert upd_after_clr.status_code == 200
    assert upd_after_clr.json()["policy_no"] == "VALID-ISSUED-POL-001"
    assert upd_after_clr.json()["t_status"] == "Booked"

    # 7. Demand Draft (DD) Gate Verification
    cust_dd, veh_dd = await create_synthetic_customer_and_vehicle(db_session, branch_id=101, reg_no="MH12P0DD01")
    book_dd = await async_client.post(
        "/api/v1/policies/book",
        headers=op_headers,
        json={
            "customer_id": cust_dd.CustomerId,
            "cust_veh_id": veh_dd.CustVehId,
            "vehicle_category": "PVT",
            "od_premium": "6000.00",
            "tp_premium": "4000.00",
            "commission": {"agent_id": 401, "franchise_id": 601, "agent_comm_od_percent": "10.00"},
            "payments": [
                {
                    "payment_type": "DD",
                    "paid_amount": "11800.00",
                    "docno": "DD-P0-001",
                    "bankname": "SBI",
                }
            ],
        },
    )
    assert book_dd.status_code == 201
    assert book_dd.json()["t_status"] == "Pending"
    tx_dd_id = book_dd.json()["transaction_id"]

    dd_blocked = await async_client.put(
        f"/api/v1/policies/{tx_dd_id}",
        headers=op_headers,
        json={"t_status": "Booked"},
    )
    assert dd_blocked.status_code == 400
    assert "Cheque/DD payment is pending bank clearance" in dd_blocked.json()["error"]["message"]

    # 8. Unpaid Balance Gate Verification (Partial Cash)
    cust_pt, veh_pt = await create_synthetic_customer_and_vehicle(db_session, branch_id=101, reg_no="MH12P0PART01")
    book_partial = await async_client.post(
        "/api/v1/policies/book",
        headers=op_headers,
        json={
            "customer_id": cust_pt.CustomerId,
            "cust_veh_id": veh_pt.CustVehId,
            "vehicle_category": "PVT",
            "od_premium": "6000.00",
            "tp_premium": "4000.00",
            "commission": {"agent_id": 401, "franchise_id": 601, "agent_comm_od_percent": "10.00"},
            "payments": [{"payment_type": "CASH", "paid_amount": "5000.00"}],
        },
    )
    assert book_partial.status_code == 201
    tx_pt_id = book_partial.json()["transaction_id"]
    assert book_partial.json()["t_status"] == "Pending"

    part_polno_blocked = await async_client.put(
        f"/api/v1/policies/{tx_pt_id}",
        headers=op_headers,
        json={"policy_no": "PARTIAL-UNPAID-POL-001"},
    )
    assert part_polno_blocked.status_code == 400
    assert "Policy has an outstanding balance of" in part_polno_blocked.json()["error"]["message"]

    part_status_blocked = await async_client.put(
        f"/api/v1/policies/{tx_pt_id}",
        headers=op_headers,
        json={"t_status": "Booked"},
    )
    assert part_status_blocked.status_code == 400
    assert "Policy has an outstanding balance of" in part_status_blocked.json()["error"]["message"]


@pytest.mark.asyncio
async def test_p0_risk_a_valid_cash_neft_settlement_allows_issuance(
    async_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """
    Forensic Edge-Case Risk A Audit:
    Ensure valid non-cheque transactions (CASH, NEFT) are never falsely blocked
    from policy number assignment or status transitions, even if the database
    clearing flag IsChequeCleared is 0 or absent.
    """
    _, op_headers = await create_user_with_role(
        db_session, role_name="OPERATOR", branch_id=101
    )

    # 1. 100% Cash Policy Booking
    cust_cash, veh_cash = await create_synthetic_customer_and_vehicle(
        db_session, branch_id=101, reg_no="MH12P0RISKA01"
    )
    book_cash = await async_client.post(
        "/api/v1/policies/book",
        headers=op_headers,
        json={
            "customer_id": cust_cash.CustomerId,
            "cust_veh_id": veh_cash.CustVehId,
            "vehicle_category": "PVT",
            "od_premium": "6000.00",
            "tp_premium": "4000.00",
            "commission": {"agent_id": 401, "franchise_id": 601, "agent_comm_od_percent": "10.00"},
            "payments": [{"payment_type": "CASH", "paid_amount": "11800.00"}],
        },
    )
    assert book_cash.status_code == 201
    tx_cash_id = book_cash.json()["transaction_id"]
    assert book_cash.json()["t_status"] == "Booked"
    assert book_cash.json()["pending_status"] == 0

    # Simulate legacy database default where IsChequeCleared is 0 for Cash
    await db_session.rollback()
    tx_model = (await db_session.execute(
        select(Transaction).where(Transaction.TransanctionId == tx_cash_id)
    )).scalar_one()
    tx_model.IsChequeCleared = 0
    await db_session.commit()

    # Risk A Verification: Cash transaction with zero balance and zero cheques MUST NOT BE BLOCKED
    upd_cash = await async_client.put(
        f"/api/v1/policies/{tx_cash_id}",
        headers=op_headers,
        json={"policy_no": "CASH-POL-RISKA-001", "t_status": "Issued"},
    )
    assert upd_cash.status_code == 200
    assert upd_cash.json()["policy_no"] == "CASH-POL-RISKA-001"
    assert upd_cash.json()["t_status"] == "Issued"

    # 2. 100% NEFT Policy Booking
    cust_neft, veh_neft = await create_synthetic_customer_and_vehicle(
        db_session, branch_id=101, reg_no="MH12P0RISKANEFT"
    )
    book_neft = await async_client.post(
        "/api/v1/policies/book",
        headers=op_headers,
        json={
            "customer_id": cust_neft.CustomerId,
            "cust_veh_id": veh_neft.CustVehId,
            "vehicle_category": "PVT",
            "od_premium": "6000.00",
            "tp_premium": "4000.00",
            "commission": {"agent_id": 401, "franchise_id": 601, "agent_comm_od_percent": "10.00"},
            "payments": [{"payment_type": "NEFT", "paid_amount": "11800.00", "docno": "NEFT-UTR-001"}],
        },
    )
    assert book_neft.status_code == 201
    tx_neft_id = book_neft.json()["transaction_id"]

    upd_neft = await async_client.put(
        f"/api/v1/policies/{tx_neft_id}",
        headers=op_headers,
        json={"policy_no": "NEFT-POL-RISKA-002", "t_status": "Approved"},
    )
    assert upd_neft.status_code == 200
    assert upd_neft.json()["policy_no"] == "NEFT-POL-RISKA-002"
    assert upd_neft.json()["t_status"] == "Approved"


@pytest.mark.asyncio
async def test_p0_risk_b_mixed_instruments_supplemental_cash_cannot_clear_pending_cheque(
    async_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """
    Forensic Edge-Case Risk B Audit:
    Ensure supplemental non-cheque payments (CASH) that settle an outstanding balance
    do NOT prematurely transition policy to 'Booked' or clear IsChequeCleared when
    an uncleared Cheque/DD remains on the policy.
    """
    _, op_headers = await create_user_with_role(
        db_session, role_name="OPERATOR", branch_id=101
    )
    _, acc_headers = await create_user_with_role(
        db_session, role_name="ACCOUNT", branch_id=101
    )

    # 1. Initial booking with mixed instruments: CHEQUE (₹5,000) + CASH (₹5,000)
    # Total premium = ₹11,800. Outstanding = ₹1,800.
    cust, veh = await create_synthetic_customer_and_vehicle(
        db_session, branch_id=101, reg_no="MH12P0RISKB01"
    )
    book_resp = await async_client.post(
        "/api/v1/policies/book",
        headers=op_headers,
        json={
            "customer_id": cust.CustomerId,
            "cust_veh_id": veh.CustVehId,
            "vehicle_category": "PVT",
            "od_premium": "6000.00",
            "tp_premium": "4000.00",
            "commission": {"agent_id": 401, "franchise_id": 601, "agent_comm_od_percent": "10.00"},
            "payments": [
                {
                    "payment_type": "CHEQUE",
                    "paid_amount": "5000.00",
                    "docno": "CHQ-RISKB-001",
                    "bankname": "HDFC",
                },
                {
                    "payment_type": "CASH",
                    "paid_amount": "5000.00",
                },
            ],
        },
    )
    assert book_resp.status_code == 201
    tx_id = book_resp.json()["transaction_id"]
    payments = book_resp.json()["payment_summary"]["payments"]
    assert len(payments) == 2
    cheque_pay = next(p for p in payments if p["payment_type"] == "CHEQUE")
    chq_id = cheque_pay["payment_id"]
    assert book_resp.json()["t_status"] == "Pending"
    assert book_resp.json()["pending_status"] == 1
    assert Decimal(str(book_resp.json()["payment_summary"]["outstanding_amount"])) == Decimal("1800.00")

    # 2. Add supplemental CASH payment of ₹1,800 settling the entire remaining balance
    supp_resp = await async_client.post(
        f"/api/v1/policies/{tx_id}/payments",
        headers=op_headers,
        json={
            "payment_type": "CASH",
            "paid_amount": "1800.00",
            "payment_details": "Settlement of remaining balance via Cash",
        },
    )
    assert supp_resp.status_code == 201
    assert Decimal(str(supp_resp.json()["payment_summary"]["outstanding_amount"])) == Decimal("0.00")

    # Risk B Verification: Even though outstanding is 0.00 and payment was Cash,
    # policy MUST REMAIN 'Pending' because CHQ-RISKB-001 is STILL UNCLEARED!
    assert supp_resp.json()["t_status"] == "Pending"
    assert supp_resp.json()["pending_status"] == 1

    # Database verification: IsChequeCleared must remain 0
    await db_session.rollback()
    tx_row = (await db_session.execute(
        select(Transaction).where(Transaction.TransanctionId == tx_id)
    )).scalar_one()
    assert tx_row.IsChequeCleared == 0
    assert tx_row.TStatus == "Pending"

    # 3. PolicyNo assignment must STILL be rejected because Cheque is uncleared
    upd_blocked = await async_client.put(
        f"/api/v1/policies/{tx_id}",
        headers=op_headers,
        json={"policy_no": "BLOCKED-POL-RISKB-001"},
    )
    assert upd_blocked.status_code == 400
    assert "Cheque/DD payment is pending bank clearance" in upd_blocked.json()["error"]["message"]

    # 4. Deposit and Clear the Cheque instrument
    dep_resp = await async_client.post(
        f"/api/v1/payments/{chq_id}/deposit",
        headers=acc_headers,
        json={"bank_reference": "DEP-SLIP-RISKB-001"},
    )
    assert dep_resp.status_code == 200

    clr_resp = await async_client.post(
        f"/api/v1/payments/{chq_id}/clear",
        headers=acc_headers,
        json={"bank_reference": "CLR-UTR-RISKB-001"},
    )
    assert clr_resp.status_code == 200
    assert clr_resp.json()["policy_t_status"] == "Booked"
    assert clr_resp.json()["policy_pending_status"] == 0

    # 5. Now that cheque has cleared, policy number assignment succeeds
    upd_success = await async_client.put(
        f"/api/v1/policies/{tx_id}",
        headers=op_headers,
        json={"policy_no": "CLEARED-POL-RISKB-001"},
    )
    assert upd_success.status_code == 200
    assert upd_success.json()["policy_no"] == "CLEARED-POL-RISKB-001"
    assert upd_success.json()["t_status"] == "Booked"

    # 6. Mixed DD + NEFT Transaction Verification
    cust_dd, veh_dd = await create_synthetic_customer_and_vehicle(
        db_session, branch_id=101, reg_no="MH12P0DDNEFT01"
    )
    book_dd_neft = await async_client.post(
        "/api/v1/policies/book",
        headers=op_headers,
        json={
            "customer_id": cust_dd.CustomerId,
            "cust_veh_id": veh_dd.CustVehId,
            "vehicle_category": "PVT",
            "od_premium": "6000.00",
            "tp_premium": "4000.00",
            "commission": {"agent_id": 401, "franchise_id": 601, "agent_comm_od_percent": "10.00"},
            "payments": [
                {
                    "payment_type": "DD",
                    "paid_amount": "6000.00",
                    "docno": "DD-RISKB-002",
                    "bankname": "SBI",
                },
                {
                    "payment_type": "NEFT",
                    "paid_amount": "4000.00",
                    "docno": "NEFT-RISKB-002",
                },
            ],
        },
    )
    assert book_dd_neft.status_code == 201
    tx_dd_id = book_dd_neft.json()["transaction_id"]
    dd_payments = book_dd_neft.json()["payment_summary"]["payments"]
    dd_pay = next(p for p in dd_payments if p["payment_type"] == "DD")
    dd_pay_id = dd_pay["payment_id"]
    assert book_dd_neft.json()["t_status"] == "Pending"

    # Add supplemental NEFT payment of 1800.00
    supp_neft = await async_client.post(
        f"/api/v1/policies/{tx_dd_id}/payments",
        headers=op_headers,
        json={
            "payment_type": "NEFT",
            "paid_amount": "1800.00",
            "docno": "NEFT-SETTLE-003",
        },
    )
    assert supp_neft.status_code == 201
    assert Decimal(str(supp_neft.json()["payment_summary"]["outstanding_amount"])) == Decimal("0.00")
    assert supp_neft.json()["t_status"] == "Pending"
    assert supp_neft.json()["pending_status"] == 1

    # PolicyNo blocked while DD is uncleared
    upd_dd_blocked = await async_client.put(
        f"/api/v1/policies/{tx_dd_id}",
        headers=op_headers,
        json={"policy_no": "BLOCKED-DD-NEFT-001"},
    )
    assert upd_dd_blocked.status_code == 400
    assert "Cheque/DD payment is pending bank clearance" in upd_dd_blocked.json()["error"]["message"]

    # Clear the DD instrument
    dep_dd = await async_client.post(
        f"/api/v1/payments/{dd_pay_id}/deposit",
        headers=acc_headers,
        json={"bank_reference": "DEP-SLIP-DD-002"},
    )
    assert dep_dd.status_code == 200

    clr_dd = await async_client.post(
        f"/api/v1/payments/{dd_pay_id}/clear",
        headers=acc_headers,
        json={"bank_reference": "CLR-UTR-DD-002"},
    )
    assert clr_dd.status_code == 200
    assert clr_dd.json()["policy_t_status"] == "Booked"

    upd_dd_ok = await async_client.put(
        f"/api/v1/policies/{tx_dd_id}",
        headers=op_headers,
        json={"policy_no": "CLEARED-DD-NEFT-POL-002"},
    )
    assert upd_dd_ok.status_code == 200
    assert upd_dd_ok.json()["policy_no"] == "CLEARED-DD-NEFT-POL-002"
    assert upd_dd_ok.json()["t_status"] == "Booked"
