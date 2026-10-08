"""
Repository for tbl_role_privilege and tbl_menu (UI Presentation & Dynamic Navigation).
"""
from typing import Optional, Sequence, List
from datetime import datetime
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import RolePrivilege, MenuMaster
from app.repositories.base import BaseRepository


class PrivilegeRepository(BaseRepository[RolePrivilege]):
    """
    Data-access repository for Dynamic Privilege and Menu Presentation structures.
    """

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(RolePrivilege, session)

    async def get_all_menus(self) -> Sequence[MenuMaster]:
        """Fetch all active menu items sorted by OrderNo."""
        query = select(MenuMaster).where(
            (MenuMaster.isdeleted == None) | (MenuMaster.isdeleted != "1")  # noqa: E711
        ).order_by(MenuMaster.ParentMenuId.asc(), MenuMaster.OrderNo.asc(), MenuMaster.MenuId.asc())
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_privileges_by_role(
        self, role_id: int, branch_id: Optional[int] = None
    ) -> Sequence[RolePrivilege]:
        """Fetch all active screen privileges assigned to a role."""
        query = select(RolePrivilege).where(
            RolePrivilege.RoleId == role_id,
            (RolePrivilege.isdeleted == None) | (RolePrivilege.isdeleted != "1"),  # noqa: E711
        )
        if branch_id is not None:
            query = query.where(RolePrivilege.BranchId == branch_id)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def assign_privileges(
        self, role_id: int, screen_ids: List[int], branch_id: Optional[int] = None
    ) -> List[RolePrivilege]:
        """
        Soft-delete existing privileges for this role/branch and insert new mappings.
        """
        # Soft delete existing
        soft_del_stmt = (
            update(RolePrivilege)
            .where(
                RolePrivilege.RoleId == role_id,
                RolePrivilege.BranchId == branch_id if branch_id is not None else True,
            )
            .values(isdeleted="1")
        )
        await self.session.execute(soft_del_stmt)

        # Create new mappings
        created: List[RolePrivilege] = []
        for sid in screen_ids:
            mapping = RolePrivilege(
                RoleId=role_id,
                BranchId=branch_id,
                ScreenId=sid,
                CreateDate=datetime.utcnow(),
                isdeleted="0",
            )
            self.session.add(mapping)
            created.append(mapping)

        await self.session.flush()
        return created
