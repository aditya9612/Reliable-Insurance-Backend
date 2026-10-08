"""
Service for Dynamic Privilege & Menu Presentation Tree.
CRITICAL SECURITY: Dynamic menu privileges are for UI PRESENTATION ONLY.
Backend authorization remains strictly enforced by require_roles / server-side RBAC dependencies.
"""
from typing import Optional, List, Dict, Set
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.models.user import MenuMaster, RolePrivilege
from app.repositories.privilege import PrivilegeRepository
from app.repositories.role import RoleRepository
from app.schemas.privilege import (
    MenuResponse,
    RolePrivilegeAssignResponse,
    DynamicMenuTreeResponse,
)


class PrivilegeService:
    """
    Domain service for dynamic UI menu presentation hierarchy and role privilege mappings.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.privilege_repo = PrivilegeRepository(session)
        self.role_repo = RoleRepository(session)

    async def get_menu_tree_for_role(
        self, role_id: int, branch_id: Optional[int] = None
    ) -> DynamicMenuTreeResponse:
        """
        Builds a nested UI navigation tree for a specific role and optional branch.
        """
        role = await self.role_repo.get_by_id(role_id)
        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Role with ID {role_id} not found",
            )

        all_menus = await self.privilege_repo.get_all_menus()
        privileges = await self.privilege_repo.get_privileges_by_role(role_id, branch_id)
        granted_screen_ids: Set[int] = {p.ScreenId for p in privileges if p.ScreenId is not None}

        # Build tree representation
        # Map MenuId -> MenuResponse
        menu_map: Dict[int, MenuResponse] = {}
        for m in all_menus:
            # If privileges are defined for this role, filter by granted screen IDs;
            # If no privileges are defined, show empty or default to ungranted
            menu_map[m.MenuId] = MenuResponse(
                MenuId=m.MenuId,
                MenuName=m.MenuName,
                MenuUrl=m.MenuUrl,
                ParentMenuId=m.ParentMenuId,
                OrderNo=m.OrderNo,
                IconClass=m.IconClass,
                isdeleted=m.isdeleted,
                is_active=m.is_active,
                children=[],
            )

        roots: List[MenuResponse] = []
        for m in all_menus:
            node = menu_map[m.MenuId]
            if granted_screen_ids and m.MenuId not in granted_screen_ids:
                # If privileges exist and this menu item is not granted, skip unless child is granted
                continue

            if m.ParentMenuId == 0 or m.ParentMenuId not in menu_map:
                roots.append(node)
            else:
                menu_map[m.ParentMenuId].children.append(node)

        return DynamicMenuTreeResponse(
            role_id=role.UserRoleId,
            role_name=role.UserRole,
            menus=roots,
        )

    async def assign_privileges(
        self, role_id: int, screen_ids: List[int], branch_id: Optional[int] = None
    ) -> RolePrivilegeAssignResponse:
        """Assigns screen/menu permissions for a role."""
        role = await self.role_repo.get_by_id(role_id)
        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Role with ID {role_id} not found",
            )

        created = await self.privilege_repo.assign_privileges(
            role_id=role_id,
            screen_ids=screen_ids,
            branch_id=branch_id,
        )
        await self.session.commit()

        return RolePrivilegeAssignResponse(
            role_id=role_id,
            branch_id=branch_id,
            assigned_screen_ids=[c.ScreenId for c in created if c.ScreenId is not None],
            message=f"Successfully assigned {len(created)} screen privileges to role {role.UserRole}",
        )
