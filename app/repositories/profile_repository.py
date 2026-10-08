"""
Repository layer for Phase 15B — Employee, Agent & Franchise Profiles.
"""
from typing import Optional, Sequence, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, update
from app.repositories.base import BaseRepository
from app.models.profile import Employee, Agent, Franchise


class ProfileRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ========================================================================
    # EMPLOYEE METHODS
    # ========================================================================

    async def get_employee_by_id(self, emp_id: int) -> Optional[Employee]:
        stmt = select(Employee).where(
            Employee.EmpId == emp_id,
            Employee.isdeleted != "1"
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_employee_by_code(self, emp_code: str) -> Optional[Employee]:
        stmt = select(Employee).where(
            Employee.EmpCode == emp_code,
            Employee.isdeleted != "1"
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def list_employees(
        self,
        branch_id: Optional[int] = None,
        role_id: Optional[int] = None,
        search: Optional[str] = None,
        offset: int = 0,
        limit: int = 100
    ) -> Sequence[Employee]:
        stmt = select(Employee).where(Employee.isdeleted != "1")
        if branch_id is not None:
            stmt = stmt.where(Employee.BranchId == branch_id)
        if role_id is not None:
            stmt = stmt.where(Employee.UserRoleId == role_id)
        if search:
            search_pat = f"%{search.strip()}%"
            stmt = stmt.where(
                or_(
                    Employee.EmpFName.ilike(search_pat),
                    Employee.EmpLName.ilike(search_pat),
                    Employee.EmpCode.ilike(search_pat),
                    Employee.UserName.ilike(search_pat),
                )
            )
        stmt = stmt.order_by(Employee.EmpId.desc()).offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def create_employee(self, emp: Employee) -> Employee:
        self.session.add(emp)
        await self.session.flush()
        return emp

    async def soft_delete_employee(self, emp_id: int, user: str = "SYSTEM") -> bool:
        emp = await self.get_employee_by_id(emp_id)
        if not emp:
            return False
        emp.isdeleted = "1"
        emp.UpdateUser = user
        await self.session.flush()
        return True

    # ========================================================================
    # AGENT METHODS
    # ========================================================================

    async def get_agent_by_id(self, agent_id: int) -> Optional[Agent]:
        stmt = select(Agent).where(
            Agent.AgentId == agent_id,
            Agent.isdeleted != "1"
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_agent_by_code(self, agent_code: str) -> Optional[Agent]:
        stmt = select(Agent).where(
            Agent.AgentCode == agent_code,
            Agent.isdeleted != "1"
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def list_agents(
        self,
        branch_id: Optional[int] = None,
        sales_exec_id: Optional[int] = None,
        franchise_id: Optional[int] = None,
        search: Optional[str] = None,
        offset: int = 0,
        limit: int = 100
    ) -> Sequence[Agent]:
        stmt = select(Agent).where(Agent.isdeleted != "1")
        if branch_id is not None:
            stmt = stmt.where(Agent.BranchId == branch_id)
        if sales_exec_id is not None:
            stmt = stmt.where(Agent.SalesExecutiveId == sales_exec_id)
        if franchise_id is not None:
            stmt = stmt.where(Agent.FranchiseId == franchise_id)
        if search:
            search_pat = f"%{search.strip()}%"
            stmt = stmt.where(
                or_(
                    Agent.AgentFName.ilike(search_pat),
                    Agent.AgentLName.ilike(search_pat),
                    Agent.AgentCode.ilike(search_pat),
                    Agent.NickName.ilike(search_pat),
                )
            )
        stmt = stmt.order_by(Agent.AgentId.desc()).offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def create_agent(self, agent: Agent) -> Agent:
        self.session.add(agent)
        await self.session.flush()
        return agent

    async def soft_delete_agent(self, agent_id: int, user: str = "SYSTEM") -> bool:
        agent = await self.get_agent_by_id(agent_id)
        if not agent:
            return False
        agent.isdeleted = "1"
        agent.IsActive = 0
        agent.UpdateUser = user
        await self.session.flush()
        return True

    # ========================================================================
    # FRANCHISE METHODS
    # ========================================================================

    async def get_franchise_by_id(self, franchise_id: int) -> Optional[Franchise]:
        stmt = select(Franchise).where(
            Franchise.FranchiseId == franchise_id,
            Franchise.isdeleted != "1"
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_franchise_by_code(self, fran_code: str) -> Optional[Franchise]:
        stmt = select(Franchise).where(
            Franchise.FranCode == fran_code,
            Franchise.isdeleted != "1"
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def list_franchises(
        self,
        branch_id: Optional[int] = None,
        parent_id: Optional[int] = None,
        search: Optional[str] = None,
        offset: int = 0,
        limit: int = 100
    ) -> Sequence[Franchise]:
        stmt = select(Franchise).where(Franchise.isdeleted != "1")
        if branch_id is not None:
            stmt = stmt.where(Franchise.BranchId == branch_id)
        if parent_id is not None:
            stmt = stmt.where(Franchise.ParentFranchiseId == parent_id)
        if search:
            search_pat = f"%{search.strip()}%"
            stmt = stmt.where(
                or_(
                    Franchise.FranFName.ilike(search_pat),
                    Franchise.FranLName.ilike(search_pat),
                    Franchise.FranCode.ilike(search_pat),
                    Franchise.UserName.ilike(search_pat),
                )
            )
        stmt = stmt.order_by(Franchise.FranchiseId.desc()).offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def create_franchise(self, franchise: Franchise) -> Franchise:
        self.session.add(franchise)
        await self.session.flush()
        return franchise

    async def soft_delete_franchise(self, franchise_id: int, user: str = "SYSTEM") -> bool:
        fran = await self.get_franchise_by_id(franchise_id)
        if not fran:
            return False
        fran.isdeleted = "1"
        fran.UpdateUser = user
        await self.session.flush()
        return True
