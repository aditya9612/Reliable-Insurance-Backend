"""
Service for Admin Dashboard Overview Counters.
"""
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.models.profile import Agent, Employee, Franchise
from app.schemas.admin_dashboard import AdminCountersResponse


class AdminDashboardService:
    """
    Domain service aggregating executive/administrative system-wide counters.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_counters(self) -> AdminCountersResponse:
        """Calculates system-wide user, agent, employee, franchise, and KYC status counters."""
        # Total users
        tot_users_q = select(func.count(User.UserId))
        tot_users = (await self.session.execute(tot_users_q)).scalar() or 0

        # Active users
        active_users_q = select(func.count(User.UserId)).where(
            or_(User.isdeleted == None, User.isdeleted != "1")  # noqa: E711
        )
        active_users = (await self.session.execute(active_users_q)).scalar() or 0

        # Locked users
        locked_users_q = select(func.count(User.UserId)).where(User.isdeleted == "1")
        locked_users = (await self.session.execute(locked_users_q)).scalar() or 0

        # Pending KYC agents
        pending_kyc_q = select(func.count(Agent.AgentId)).where(
            func.upper(Agent.kyc_status) == "PENDING",
            or_(Agent.isdeleted == None, Agent.isdeleted != "1"),  # noqa: E711
        )
        pending_kyc = (await self.session.execute(pending_kyc_q)).scalar() or 0

        # Total agents
        tot_agents_q = select(func.count(Agent.AgentId)).where(
            or_(Agent.isdeleted == None, Agent.isdeleted != "1")  # noqa: E711
        )
        tot_agents = (await self.session.execute(tot_agents_q)).scalar() or 0

        # Total employees
        tot_emp_q = select(func.count(Employee.EmpId)).where(
            or_(Employee.isdeleted == None, Employee.isdeleted != "1")  # noqa: E711
        )
        tot_emp = (await self.session.execute(tot_emp_q)).scalar() or 0

        # Total franchises
        tot_fran_q = select(func.count(Franchise.FranchiseId)).where(
            or_(Franchise.isdeleted == None, Franchise.isdeleted != "1")  # noqa: E711
        )
        tot_fran = (await self.session.execute(tot_fran_q)).scalar() or 0

        return AdminCountersResponse(
            total_users=tot_users,
            active_users=active_users,
            locked_users=locked_users,
            pending_kyc_agents=pending_kyc,
            total_agents=tot_agents,
            total_employees=tot_emp,
            total_franchises=tot_fran,
        )
