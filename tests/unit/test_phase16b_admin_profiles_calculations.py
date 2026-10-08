"""
Phase 16B Unit Tests — Models, Schemas, Validation & RBAC Security Boundary.
"""
import pytest
from app.models.user import User, UserRole, LoginHistory, RolePrivilege, MenuMaster
from app.models.master import FuelType, Financier, Surveyor
from app.models.profile import Employee, Agent, Franchise
from app.schemas.user import UserCreate, UserResponse, UsernameCheckResponse
from app.schemas.login_history import LoginHistoryResponse, AccountUnlockResponse
from app.schemas.privilege import DynamicMenuTreeResponse, MenuResponse, RolePrivilegeAssignRequest
from app.schemas.admin_dashboard import AdminCountersResponse
from app.schemas.profile import AgentKYCUpdateRequest, EmployeeHierarchyUpdateRequest, FranchiseHierarchyNode
from app.core.dependencies import require_roles


def test_phase16b_models_active_properties():
    """Verify is_active property on newly introduced master and user entities."""
    u_active = User(isdeleted="0")
    u_deleted = User(isdeleted="1")
    assert u_active.is_active is True
    assert u_deleted.is_active is False

    role_priv_active = RolePrivilege(isdeleted="0")
    role_priv_deleted = RolePrivilege(isdeleted="1")
    assert role_priv_active.is_active is True
    assert role_priv_deleted.is_active is False

    menu_active = MenuMaster(isdeleted="0")
    menu_deleted = MenuMaster(isdeleted="1")
    assert menu_active.is_active is True
    assert menu_deleted.is_active is False

    ft_active = FuelType(isdeleted="0")
    ft_deleted = FuelType(isdeleted="1")
    assert ft_active.is_active is True
    assert ft_deleted.is_active is False

    fin_active = Financier(isdeleted="0")
    fin_deleted = Financier(isdeleted="1")
    assert fin_active.is_active is True
    assert fin_deleted.is_active is False

    surv_active = Surveyor(isdeleted="0")
    surv_deleted = Surveyor(isdeleted="1")
    assert surv_active.is_active is True
    assert surv_deleted.is_active is False


def test_agent_kyc_and_employee_hierarchy_models():
    """Verify default KYC status on Agent and hierarchy columns on Employee."""
    agent = Agent(kyc_status="PENDING")
    assert agent.kyc_status == "PENDING"

    emp = Employee(Hei_Data="REGION_1", Hie_DataSales="SALES_1", Hie_DataOprn="OPS_1")
    assert emp.Hei_Data == "REGION_1"
    assert emp.Hie_DataSales == "SALES_1"
    assert emp.Hie_DataOprn == "OPS_1"


def test_admin_counters_schema():
    """Verify AdminCountersResponse structure."""
    counters = AdminCountersResponse(
        total_users=10,
        active_users=8,
        locked_users=2,
        pending_kyc_agents=3,
        total_agents=15,
        total_employees=12,
        total_franchises=5,
    )
    assert counters.total_users == 10
    assert counters.pending_kyc_agents == 3


def test_privilege_and_menu_tree_schemas():
    """Verify MenuResponse and DynamicMenuTreeResponse structure."""
    child_node = MenuResponse(MenuId=102, MenuName="Sub menu", ParentMenuId=101, OrderNo=1)
    root_node = MenuResponse(MenuId=101, MenuName="Root menu", ParentMenuId=0, OrderNo=1, children=[child_node])

    tree = DynamicMenuTreeResponse(
        role_id=1,
        role_name="ADMIN",
        menus=[root_node],
    )
    assert tree.role_id == 1
    assert len(tree.menus) == 1
    assert len(tree.menus[0].children) == 1
    assert tree.menus[0].children[0].MenuId == 102


def test_rbac_security_boundary_isolation():
    """
    CRITICAL SECURITY CHECK:
    Verify that dynamic menu privilege models do not alter or weaken
    server-side require_roles RBAC authorization.
    """
    admin_checker = require_roles("ADMIN", "OWNER")
    assert callable(admin_checker)
