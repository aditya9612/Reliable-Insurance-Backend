"""
Service layer for Phase 15B — Employee, Agent & Franchise Profiles.
Enforces RBAC, branch isolation, unique code generation, and principal scoping.
"""
from datetime import datetime
from typing import Optional, Sequence, List
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.rbac import is_global_admin_role, is_global_read_role
from app.models.profile import Employee, Agent, Franchise
from app.models.user import User
from app.repositories.profile_repository import ProfileRepository
from app.schemas.profile import (
    EmployeeCreate,
    EmployeeUpdate,
    EmployeeHierarchyUpdateRequest,
    AgentCreate,
    AgentUpdate,
    AgentKYCUpdateRequest,
    FranchiseCreate,
    FranchiseUpdate,
    FranchiseHierarchyNode,
)


class ProfileService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = ProfileRepository(session)

    def _is_admin(self, current_user: User) -> bool:
        role = getattr(current_user, "role_name", None)
        return is_global_admin_role(role) or role in ("HR", "OWNER", "ADMIN", "IT SUPPORT")

    def _can_read_all(self, current_user: User) -> bool:
        role = getattr(current_user, "role_name", None)
        return is_global_read_role(role) or role in ("HR", "OWNER", "ADMIN", "IT SUPPORT", "ACCOUNT")

    # ========================================================================
    # EMPLOYEE SERVICES
    # ========================================================================

    async def create_employee(self, payload: EmployeeCreate, current_user: User) -> Employee:
        if not self._is_admin(current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only HR or Administrative roles can create employees."
            )

        branch_id = payload.BranchId if (self._is_admin(current_user) and payload.BranchId is not None) else current_user.BranchId

        # Check duplicate EmpCode if supplied
        if payload.EmpCode:
            existing = await self.repo.get_employee_by_code(payload.EmpCode.strip())
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Employee code '{payload.EmpCode}' already exists."
                )

        emp_data = payload.model_dump(exclude_unset=True)
        emp_data["BranchId"] = branch_id
        emp_data["CreateUser"] = current_user.UserName or "ADMIN"
        emp_data["CreateDate"] = datetime.utcnow()
        emp_data["isdeleted"] = "0"

        emp = Employee(**emp_data)
        emp = await self.repo.create_employee(emp)

        # Auto-generate EmpCode if missing
        if not emp.EmpCode:
            emp.EmpCode = f"EMP{emp.EmpId:05d}"

        await self.session.commit()
        await self.session.refresh(emp)
        return emp

    async def get_employee(self, emp_id: int, current_user: User) -> Employee:
        emp = await self.repo.get_employee_by_id(emp_id)
        if not emp:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Employee with ID {emp_id} not found."
            )
        if not self._can_read_all(current_user) and emp.BranchId != current_user.BranchId:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Employee belongs to a different branch."
            )
        return emp

    async def list_employees(
        self,
        current_user: User,
        branch_id: Optional[int] = None,
        role_id: Optional[int] = None,
        search: Optional[str] = None,
        offset: int = 0,
        limit: int = 100
    ) -> Sequence[Employee]:
        target_branch = branch_id if self._can_read_all(current_user) else current_user.BranchId
        return await self.repo.list_employees(
            branch_id=target_branch,
            role_id=role_id,
            search=search,
            offset=offset,
            limit=limit
        )

    async def update_employee(self, emp_id: int, payload: EmployeeUpdate, current_user: User) -> Employee:
        emp = await self.get_employee(emp_id, current_user)
        if not self._is_admin(current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only HR or Administrative roles can update employee records."
            )

        update_data = payload.model_dump(exclude_unset=True)
        for key, val in update_data.items():
            if hasattr(emp, key):
                setattr(emp, key, val)

        emp.UpdateUser = current_user.UserName or "ADMIN"
        emp.UpdateDate = datetime.utcnow()
        await self.session.commit()
        await self.session.refresh(emp)
        return emp

    async def delete_employee(self, emp_id: int, current_user: User) -> bool:
        if not self._is_admin(current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only HR or Administrative roles can delete employees."
            )
        success = await self.repo.soft_delete_employee(emp_id, user=current_user.UserName or "ADMIN")
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Employee with ID {emp_id} not found."
            )
        await self.session.commit()
        return True

    # ========================================================================
    # AGENT SERVICES
    # ========================================================================

    async def create_agent(self, payload: AgentCreate, current_user: User) -> Agent:
        branch_id = payload.BranchId if (self._is_admin(current_user) and payload.BranchId is not None) else current_user.BranchId

        if payload.AgentCode:
            existing = await self.repo.get_agent_by_code(payload.AgentCode.strip())
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Agent code '{payload.AgentCode}' already exists."
                )

        agent_data = payload.model_dump(exclude_unset=True)
        agent_data["BranchId"] = branch_id
        agent_data["CreateUser"] = current_user.UserName or "ADMIN"
        agent_data["CreateDate"] = datetime.utcnow()
        agent_data["isdeleted"] = "0"
        agent_data["IsActive"] = 1

        agent = Agent(**agent_data)
        agent = await self.repo.create_agent(agent)

        if not agent.AgentCode:
            agent.AgentCode = f"AGT{agent.AgentId:05d}"

        await self.session.commit()
        await self.session.refresh(agent)
        return agent

    async def get_agent(self, agent_id: int, current_user: User) -> Agent:
        agent = await self.repo.get_agent_by_id(agent_id)
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent with ID {agent_id} not found."
            )
        if not self._can_read_all(current_user) and agent.BranchId != current_user.BranchId:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Agent belongs to a different branch."
            )
        return agent

    async def list_agents(
        self,
        current_user: User,
        branch_id: Optional[int] = None,
        sales_exec_id: Optional[int] = None,
        franchise_id: Optional[int] = None,
        search: Optional[str] = None,
        offset: int = 0,
        limit: int = 100
    ) -> Sequence[Agent]:
        target_branch = branch_id if self._can_read_all(current_user) else current_user.BranchId
        return await self.repo.list_agents(
            branch_id=target_branch,
            sales_exec_id=sales_exec_id,
            franchise_id=franchise_id,
            search=search,
            offset=offset,
            limit=limit
        )

    async def update_agent(self, agent_id: int, payload: AgentUpdate, current_user: User) -> Agent:
        agent = await self.get_agent(agent_id, current_user)

        update_data = payload.model_dump(exclude_unset=True)
        for key, val in update_data.items():
            if hasattr(agent, key):
                setattr(agent, key, val)

        agent.UpdateUser = current_user.UserName or "ADMIN"
        agent.UpdateDate = datetime.utcnow()
        await self.session.commit()
        await self.session.refresh(agent)
        return agent

    async def delete_agent(self, agent_id: int, current_user: User) -> bool:
        if not self._is_admin(current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only HR or Administrative roles can deactivate agents."
            )
        success = await self.repo.soft_delete_agent(agent_id, user=current_user.UserName or "ADMIN")
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Agent with ID {agent_id} not found."
            )
        await self.session.commit()
        return True

    # ========================================================================
    # FRANCHISE SERVICES
    # ========================================================================

    async def create_franchise(self, payload: FranchiseCreate, current_user: User) -> Franchise:
        if not self._is_admin(current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Administrative roles can register franchises."
            )

        branch_id = payload.BranchId if payload.BranchId is not None else current_user.BranchId

        if payload.FranCode:
            existing = await self.repo.get_franchise_by_code(payload.FranCode.strip())
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Franchise code '{payload.FranCode}' already exists."
                )

        fran_data = payload.model_dump(exclude_unset=True)
        fran_data["BranchId"] = branch_id
        fran_data["CreateUser"] = current_user.UserName or "ADMIN"
        fran_data["CreateDate"] = datetime.utcnow()
        fran_data["isdeleted"] = "0"

        fran = Franchise(**fran_data)
        fran = await self.repo.create_franchise(fran)

        if not fran.FranCode:
            fran.FranCode = f"FRN{fran.FranchiseId:05d}"

        await self.session.commit()
        await self.session.refresh(fran)
        return fran

    async def get_franchise(self, franchise_id: int, current_user: User) -> Franchise:
        fran = await self.repo.get_franchise_by_id(franchise_id)
        if not fran:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Franchise with ID {franchise_id} not found."
            )
        if not self._can_read_all(current_user) and fran.BranchId != current_user.BranchId:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Franchise belongs to a different branch."
            )
        return fran

    async def list_franchises(
        self,
        current_user: User,
        branch_id: Optional[int] = None,
        parent_id: Optional[int] = None,
        search: Optional[str] = None,
        offset: int = 0,
        limit: int = 100
    ) -> Sequence[Franchise]:
        target_branch = branch_id if self._can_read_all(current_user) else current_user.BranchId
        return await self.repo.list_franchises(
            branch_id=target_branch,
            parent_id=parent_id,
            search=search,
            offset=offset,
            limit=limit
        )

    async def update_franchise(self, franchise_id: int, payload: FranchiseUpdate, current_user: User) -> Franchise:
        fran = await self.get_franchise(franchise_id, current_user)
        if not self._is_admin(current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Administrative roles can update franchise details."
            )

        update_data = payload.model_dump(exclude_unset=True)
        for key, val in update_data.items():
            if hasattr(fran, key):
                setattr(fran, key, val)

        fran.UpdateUser = current_user.UserName or "ADMIN"
        fran.UpdateDate = datetime.utcnow()
        await self.session.commit()
        await self.session.refresh(fran)
        return fran

    async def delete_franchise(self, franchise_id: int, current_user: User) -> bool:
        if not self._is_admin(current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only Administrative roles can deactivate franchises."
            )
        success = await self.repo.soft_delete_franchise(franchise_id, user=current_user.UserName or "ADMIN")
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Franchise with ID {franchise_id} not found."
            )
        await self.session.commit()
        return True

    async def update_employee_hierarchy(
        self, emp_id: int, payload: EmployeeHierarchyUpdateRequest, current_user: User
    ) -> Employee:
        """Update staff organizational hierarchy strings."""
        if not self._is_admin(current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only HR or Administrative roles can update employee hierarchy.",
            )

        emp = await self.get_employee(emp_id, current_user)
        if payload.Hei_Data is not None:
            emp.Hei_Data = payload.Hei_Data
        if payload.Hie_DataSales is not None:
            emp.Hie_DataSales = payload.Hie_DataSales
        if payload.Hie_DataOprn is not None:
            emp.Hie_DataOprn = payload.Hie_DataOprn

        emp.UpdateDate = datetime.utcnow()
        emp.UpdateUser = current_user.UserName or "ADMIN"
        await self.session.commit()
        await self.session.refresh(emp)
        return emp

    async def update_agent_kyc(
        self, agent_id: int, payload: AgentKYCUpdateRequest, current_user: User
    ) -> Agent:
        """
        Enforce Agent KYC 3-state state machine:
        PENDING -> VERIFIED / REJECTED.
        Terminal states cannot transition again. Invalid transitions rejected with 400.
        """
        if not self._is_admin(current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only HR or Administrative roles can update agent KYC status.",
            )

        agent = await self.get_agent(agent_id, current_user)
        target_status = payload.kyc_status.strip().upper()
        if target_status not in ("VERIFIED", "REJECTED"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Target KYC status must be VERIFIED or REJECTED",
            )

        current_status = (agent.kyc_status or "PENDING").strip().upper()
        if current_status != "PENDING":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid KYC status transition from {current_status} to {target_status}. KYC status cannot be transitioned once verified or rejected.",
            )

        agent.kyc_status = target_status
        agent.kyc_remarks = payload.kyc_remarks
        agent.UpdateDate = datetime.utcnow()
        agent.UpdateUser = current_user.UserName or "ADMIN"
        await self.session.commit()
        await self.session.refresh(agent)
        return agent

    async def get_franchise_hierarchy(
        self, franchise_id: int, current_user: User
    ) -> FranchiseHierarchyNode:
        """
        Builds recursive franchise partner hierarchy tree with cycle detection and depth limit (max 10).
        """
        root = await self.get_franchise(franchise_id, current_user)

        async def build_tree(
            fran: Franchise, current_depth: int, visited: set
        ) -> FranchiseHierarchyNode:
            if current_depth >= 10:
                return FranchiseHierarchyNode(
                    FranchiseId=fran.FranchiseId,
                    FranCode=fran.FranCode,
                    FranFName=fran.FranFName,
                    FranMName=fran.FranMName,
                    FranLName=fran.FranLName,
                    ParentFranchiseId=fran.ParentFranchiseId,
                    BranchId=fran.BranchId,
                    depth=current_depth,
                    children=[],
                )

            visited.add(fran.FranchiseId)
            children_frans = await self.repo.list_franchises(parent_id=fran.FranchiseId, limit=100)
            child_nodes = []
            for child in children_frans:
                if child.FranchiseId not in visited:
                    child_node = await build_tree(child, current_depth + 1, visited.copy())
                    child_nodes.append(child_node)

            return FranchiseHierarchyNode(
                FranchiseId=fran.FranchiseId,
                FranCode=fran.FranCode,
                FranFName=fran.FranFName,
                FranMName=fran.FranMName,
                FranLName=fran.FranLName,
                ParentFranchiseId=fran.ParentFranchiseId,
                BranchId=fran.BranchId,
                depth=current_depth,
                children=child_nodes,
            )

        return await build_tree(root, 0, set())
