from types import SimpleNamespace
import pytest

from app.core.rbac import (
    VERIFIED_ROLE_CATALOG,
    VERIFIED_ROLE_NAMES,
    GLOBAL_ADMIN_ROLES,
    GLOBAL_READ_ROLES,
    CUSTOMER_VEHICLE_WRITE_ROLES,
    CUSTOMER_VEHICLE_READ_ROLES,
    AGENT_PRINCIPAL_ROLES,
    EMPLOYEE_PRINCIPAL_ROLES,
    FRANCHISE_PRINCIPAL_ROLES,
    is_global_admin_role,
    is_global_read_role,
    is_verified_role,
    PrincipalContext,
    resolve_principal_context,
)
from app.services.customer import CustomerService
from app.services.vehicle import VehicleService


def test_verified_role_catalog_completeness_and_superadmin_exclusion():
    """
    GAP-5F-02: Verify the 56-role catalog matches Phase 5F audit and excludes phantom 'SUPERADMIN'.
    (56 RoleId rows with 55 distinct role names because RoleId 29 and 43 are both 'ZONAL HEAD').
    """
    assert len(VERIFIED_ROLE_CATALOG) == 56
    assert len(VERIFIED_ROLE_NAMES) == 55
    assert "SUPERADMIN" not in VERIFIED_ROLE_NAMES
    assert not is_verified_role("SUPERADMIN")
    assert not is_global_admin_role("SUPERADMIN")
    assert not is_global_read_role("SUPERADMIN")




def test_global_admin_and_read_roles():
    """
    GAP-5F-02: Verify only OWNER, ADMIN, IT SUPPORT are global admin roles,
    and ACCOUNT / ACCOUNT HEAD are included in global read roles.
    """
    assert GLOBAL_ADMIN_ROLES == frozenset({"OWNER", "ADMIN", "IT SUPPORT"})
    for role in ("OWNER", "ADMIN", "IT SUPPORT"):
        assert is_global_admin_role(role)
        assert is_global_read_role(role)

    for role in ("ACCOUNT", "ACCOUNT HEAD"):
        assert not is_global_admin_role(role)
        assert is_global_read_role(role)

    for non_global in ("OPERATOR", "AGENT", "CASHIER", "CLAIM", "RELATIONSHIP MANAGER", "SUPERADMIN", None, ""):
        assert not is_global_admin_role(non_global)
        assert not is_global_read_role(non_global)


def test_branch_zero_or_none_never_grants_admin_in_services():
    """
    GAP-5F-02: Verify CustomerService._is_admin and VehicleService._is_admin never treat
    BranchId == 0, BranchId is None, or role_name == 'SUPERADMIN' as admin.
    """
    customer_service = CustomerService(session=None)  # type: ignore[arg-type]
    vehicle_service = VehicleService(session=None)  # type: ignore[arg-type]

    # 1. SUPERADMIN with BranchId=0 -> NOT admin
    superadmin_user = SimpleNamespace(UserId=1, role_name="SUPERADMIN", BranchId=0)
    assert customer_service._is_admin(superadmin_user) is False
    assert vehicle_service._is_admin(superadmin_user) is False

    # 2. OPERATOR with BranchId=0 -> NOT admin
    operator_b0 = SimpleNamespace(UserId=2, role_name="OPERATOR", BranchId=0)
    assert customer_service._is_admin(operator_b0) is False
    assert vehicle_service._is_admin(operator_b0) is False

    # 3. OPERATOR with BranchId=None -> NOT admin
    operator_bnone = SimpleNamespace(UserId=3, role_name="OPERATOR", BranchId=None)
    assert customer_service._is_admin(operator_bnone) is False
    assert vehicle_service._is_admin(operator_bnone) is False

    # 4. AGENT with BranchId=0 -> NOT admin
    agent_b0 = SimpleNamespace(UserId=4, role_name="AGENT", BranchId=0)
    assert customer_service._is_admin(agent_b0) is False
    assert vehicle_service._is_admin(agent_b0) is False

    # 5. Verified global admins (OWNER, ADMIN, IT SUPPORT) -> ARE admin even with non-zero BranchId
    for admin_role in ("OWNER", "ADMIN", "IT SUPPORT"):
        admin_user = SimpleNamespace(UserId=5, role_name=admin_role, BranchId=101)
        assert customer_service._is_admin(admin_user) is True
        assert vehicle_service._is_admin(admin_user) is True


def test_customer_vehicle_write_and_read_role_sets():
    """
    GAP-5F-01: Verify CUSTOMER_VEHICLE_WRITE_ROLES and CUSTOMER_VEHICLE_READ_ROLES.
    """
    expected_write = {
        "OWNER",
        "ADMIN",
        "IT SUPPORT",
        "OPERATOR",
        "OPERATOR HEAD",
        "ALL USER",
        "Freelancer",
        "FRANCHISE",
        "FRANCHISE TYPE 2",
        "FRANCHISE TYPE 3",
        "FRANCHISE OPERATOR",
        "OTHER",
        "ENDORSEMENT",
    }
    assert CUSTOMER_VEHICLE_WRITE_ROLES == frozenset(expected_write)

    for forbidden_write_role in (
        "AGENT",
        "CASHIER",
        "CLAIM",
        "RELATIONSHIP MANAGER",
        "ACCOUNT",
        "ACCOUNT HEAD",
        "POLICY BAZAR",
        "POLICY BAZAR AGENT",
        "SUPERADMIN",
    ):
        assert forbidden_write_role not in CUSTOMER_VEHICLE_WRITE_ROLES

    # Inactive roles POLICY BAZAR and POLICY BAZAR AGENT must not be in active read roles
    assert "POLICY BAZAR" not in CUSTOMER_VEHICLE_READ_ROLES
    assert "POLICY BAZAR AGENT" not in CUSTOMER_VEHICLE_READ_ROLES
    assert "AGENT" in CUSTOMER_VEHICLE_READ_ROLES
    assert "OPERATOR" in CUSTOMER_VEHICLE_READ_ROLES


@pytest.mark.asyncio
async def test_principal_context_resolution_from_partner_user_id():
    """
    GAP-5F-03: Verify server-side principal context resolution populates agent_id, emp_id/employee_id,
    or franchise_id strictly from server-side user/role mappings and leaves unrelated IDs None.
    """
    # 1. Agent role with partner_user_id=501
    agent_user = SimpleNamespace(UserId=10, UserRoleId=15, BranchId=3, partner_user_id=501)
    agent_role = SimpleNamespace(UserRoleId=15, UserRole="AGENT", is_active=True)
    ctx_agent = await resolve_principal_context(None, agent_user, agent_role)  # type: ignore[arg-type]
    assert ctx_agent.role_name == "AGENT"
    assert ctx_agent.branch_id == 3
    assert ctx_agent.agent_id == 501
    assert ctx_agent.emp_id is None
    assert ctx_agent.employee_id is None
    assert ctx_agent.franchise_id is None
    assert agent_user.agent_id == 501
    assert agent_user.emp_id is None
    assert agent_user.franchise_id is None

    # 2. Employee role (RELATIONSHIP MANAGER) with partner_user_id=777
    rm_user = SimpleNamespace(UserId=11, UserRoleId=29, BranchId=4, partner_user_id=777)
    rm_role = SimpleNamespace(UserRoleId=29, UserRole="RELATIONSHIP MANAGER", is_active=True)
    ctx_rm = await resolve_principal_context(None, rm_user, rm_role)  # type: ignore[arg-type]
    assert ctx_rm.role_name == "RELATIONSHIP MANAGER"
    assert ctx_rm.emp_id == 777
    assert ctx_rm.employee_id == 777
    assert ctx_rm.agent_id is None
    assert ctx_rm.franchise_id is None

    # 3. Franchise role (FRANCHISE) with partner_user_id=888
    fr_user = SimpleNamespace(UserId=12, UserRoleId=21, BranchId=5, partner_user_id=888)
    fr_role = SimpleNamespace(UserRoleId=21, UserRole="FRANCHISE", is_active=True)
    ctx_fr = await resolve_principal_context(None, fr_user, fr_role)  # type: ignore[arg-type]
    assert ctx_fr.role_name == "FRANCHISE"
    assert ctx_fr.franchise_id == 888
    assert ctx_fr.agent_id is None
    assert ctx_fr.emp_id is None

    # 4. Back-office OPERATOR with partner_user_id=999 -> does NOT populate agent/emp/franchise
    op_user = SimpleNamespace(UserId=13, UserRoleId=2, BranchId=2, partner_user_id=999)
    op_role = SimpleNamespace(UserRoleId=2, UserRole="OPERATOR", is_active=True)
    ctx_op = await resolve_principal_context(None, op_user, op_role)  # type: ignore[arg-type]
    assert ctx_op.role_name == "OPERATOR"
    assert ctx_op.agent_id is None
    assert ctx_op.emp_id is None
    assert ctx_op.employee_id is None
    assert ctx_op.franchise_id is None
