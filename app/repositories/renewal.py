"""
Repository for Phase 13 Block E — Policy Renewal Engine & Telecaller CRM.
"""
from datetime import datetime, timedelta
from typing import Optional, List, Sequence, Tuple, Dict, Any
from sqlalchemy import select, update, func, extract, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.renewal import PolicyRenewalStatus, RenewalFollowupHistory
from app.models.transaction import Transaction
from app.models.vehicle import VehicleDetails
from app.models.customer import Customer
from app.models.master import InsuranceCompany
from app.models.user import User
from app.repositories.base import BaseRepository
from app.schemas.renewal import (
    ExpiringPolicyResponse,
    ExecutiveRenewalCount,
    InsurerRenewalCount,
)


class RenewalRepository(BaseRepository[PolicyRenewalStatus]):
    """Data-access repository for policy renewals, expiring alerts and CRM follow-ups."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(PolicyRenewalStatus, session)

    async def get_expiring_policies(
        self,
        days_ahead: int = 30,
        branch_id: Optional[int] = None,
        agent_id: Optional[int] = None,
        executive_id: Optional[int] = None,
        offset: int = 0,
        limit: int = 50,
    ) -> Tuple[List[ExpiringPolicyResponse], int]:
        """
        Retrieves policies approaching expiration.
        Replaces sp_SelectpolicyExpiryDate.
        """
        now = datetime.utcnow()
        end_threshold = now + timedelta(days=days_ahead)

        conditions = [
            Transaction.ExpiryDate >= now,
            Transaction.ExpiryDate <= end_threshold,
            or_(Transaction.isdeleted == "0", Transaction.isdeleted.is_(None)),
        ]

        if branch_id and branch_id > 0:
            conditions.append(Transaction.BranchId == branch_id)
        if agent_id and agent_id > 0:
            conditions.append(Transaction.AgentId == agent_id)
        if executive_id and executive_id > 0:
            conditions.append(Transaction.SalesEx_id == executive_id)

        # Count total
        count_stmt = select(func.count(Transaction.TransanctionId)).where(and_(*conditions))
        total_count = (await self.session.execute(count_stmt)).scalar() or 0

        # Query items
        stmt = (
            select(Transaction, VehicleDetails, Customer, InsuranceCompany)
            .outerjoin(VehicleDetails, VehicleDetails.CustVehId == Transaction.CustVehId)
            .outerjoin(Customer, Customer.CustomerId == Transaction.CustomerId)
            .outerjoin(InsuranceCompany, InsuranceCompany.InsuranceCompanyId == Transaction.InsuranceCompanyId)
            .where(and_(*conditions))
            .order_by(Transaction.ExpiryDate.asc())
            .offset(offset)
            .limit(limit)
        )

        rows = (await self.session.execute(stmt)).all()
        items: List[ExpiringPolicyResponse] = []

        for row in rows:
            tx: Transaction = row[0]
            veh: Optional[VehicleDetails] = row[1]
            cust: Optional[Customer] = row[2]
            ins_comp: Optional[InsuranceCompany] = row[3] if len(row) > 3 else None
            comp_name = (ins_comp.InsuranceCompany if ins_comp and ins_comp.InsuranceCompany else None) or str(getattr(tx, "InsuranceCompanyId", "") or "")

            cust_name = ""
            if cust:
                parts = [cust.CustFName or "", cust.CustMName or "", cust.CustLName or ""]
                cust_name = " ".join(p for p in parts if p).strip()

            days_left = 0
            if tx.ExpiryDate:
                days_left = max(0, (tx.ExpiryDate - now).days)

            prem = float(getattr(tx, "Amount", 0.0) or getattr(tx, "NetPermium", 0.0) or 0.0)
            items.append(
                ExpiringPolicyResponse(
                    transaction_id=tx.TransanctionId,
                    policy_no=tx.PolicyNo,
                    registration_no=getattr(veh, "RegistrationNo", "") or "",
                    customer_name=cust_name or None,
                    mobile_no=getattr(cust, "MoblieNo1", None) or getattr(cust, "MoblieNo", None),
                    insurance_company=comp_name,
                    gross_premium=prem,
                    expiry_date=tx.ExpiryDate or now,
                    days_until_expiry=days_left,
                    agent_id=int(tx.AgentId or 0),
                    agent_name=None,
                    executive_id=int(getattr(tx, "SalesEx_id", 0) or 0),
                    branch_id=tx.BranchId,
                )
            )

        return items, total_count

    async def get_followups(
        self,
        financial_year: Optional[str] = None,
        status: Optional[str] = None,
        branch_id: Optional[int] = None,
        agent_id: Optional[int] = None,
        executive_id: Optional[int] = None,
        offset: int = 0,
        limit: int = 50,
    ) -> Tuple[Sequence[PolicyRenewalStatus], int]:
        """
        Retrieves telecaller follow-up entries.
        Replaces sp_SelectFollowupEntry.
        """
        conditions = [PolicyRenewalStatus.isdeleted == 0]

        if financial_year:
            conditions.append(PolicyRenewalStatus.FinancialYear == financial_year)
        if status:
            conditions.append(PolicyRenewalStatus.RenewalStatus == status)
        if branch_id and branch_id > 0:
            conditions.append(PolicyRenewalStatus.BranchId == branch_id)
        if agent_id and agent_id > 0:
            conditions.append(PolicyRenewalStatus.AgentId == agent_id)
        if executive_id and executive_id > 0:
            conditions.append(PolicyRenewalStatus.ExecutiveId == executive_id)

        count_stmt = select(func.count(PolicyRenewalStatus.Id)).where(and_(*conditions))
        total = (await self.session.execute(count_stmt)).scalar() or 0

        stmt = (
            select(PolicyRenewalStatus)
            .where(and_(*conditions))
            .order_by(PolicyRenewalStatus.FollowupDate.asc(), PolicyRenewalStatus.Id.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all(), total

    async def get_followup_by_id(self, status_id: int) -> Optional[PolicyRenewalStatus]:
        """Fetches renewal status record by PK."""
        return await self.get_by_id(status_id)

    async def upsert_followup(
        self,
        transaction_id: int,
        registration_no: str,
        financial_year: str,
        remark: str,
        followup_date: datetime,
        insurance_company: Optional[str],
        total_premium: float,
        mobile_no: Optional[str],
        expiry_date: Optional[datetime],
        user_role_id: int,
        agent_id: int,
        executive_id: int,
        branch_id: Optional[int],
        recorded_by: str,
    ) -> PolicyRenewalStatus:
        """
        Upserts a telecaller follow-up record and logs history.
        Replaces Sp_InsertFollowPreYearRenewalStatus.
        """
        clean_reg = registration_no.strip().upper().replace(" ", "").replace("-", "")

        # Check existing active status for (RegistrationNo, FinancialYear)
        stmt = select(PolicyRenewalStatus).where(
            PolicyRenewalStatus.RegistrationNo == clean_reg,
            PolicyRenewalStatus.FinancialYear == financial_year,
            PolicyRenewalStatus.isdeleted == 0,
        )
        existing = (await self.session.execute(stmt)).scalars().first()

        now = datetime.utcnow()
        if existing:
            existing.Remark = remark
            existing.FollowupDate = followup_date
            existing.UpdatedDate = now
            existing.UpdatedBy = recorded_by
            if insurance_company:
                existing.InsuranceCompany = insurance_company
            if total_premium > 0:
                existing.TotalPremium = total_premium
            if mobile_no:
                existing.MobileNo = mobile_no
            if expiry_date:
                existing.ExpiryDate = expiry_date
            status_obj = existing
        else:
            status_obj = PolicyRenewalStatus(
                TransanctionId=transaction_id,
                Remark=remark,
                FinancialYear=financial_year,
                isdeleted=0,
                CreatedDate=now,
                RegistrationNo=clean_reg,
                InsuranceCompany=insurance_company,
                TotalPremium=total_premium,
                MobileNo=mobile_no,
                ExpiryDate=expiry_date or now,
                FollowupDate=followup_date,
                UserRoleId=user_role_id,
                AgentId=agent_id,
                ExecutiveId=executive_id,
                RenewalStatus="Follow",
                BranchId=branch_id or 0,
                UpdatedDate=now,
                UpdatedBy=recorded_by,
            )
            self.session.add(status_obj)

        await self.session.flush()

        # Add audit trail entry
        history = RenewalFollowupHistory(
            renewal_status_id=status_obj.Id,
            remark=remark,
            followup_date=followup_date,
            status_at_time=status_obj.RenewalStatus,
            recorded_by=recorded_by,
            created_at=now,
        )
        self.session.add(history)
        await self.session.flush()

        return status_obj

    async def update_status(
        self,
        status_id: int,
        new_status: str,
        remark: Optional[str],
        updated_by: str,
    ) -> Optional[PolicyRenewalStatus]:
        """
        Transitions renewal status (Follow, Done, Lost, Vehicle).
        Replaces Sp_UpdatePreYearRenewalStatus.
        """
        status_obj = await self.get_by_id(status_id)
        if not status_obj:
            return None

        status_obj.RenewalStatus = new_status
        status_obj.UpdatedDate = datetime.utcnow()
        status_obj.UpdatedBy = updated_by
        if remark:
            status_obj.Remark = f"{status_obj.Remark or ''} | [{new_status}]: {remark}".strip(" |")

        # History log
        history = RenewalFollowupHistory(
            renewal_status_id=status_obj.Id,
            remark=remark or f"Status changed to {new_status}",
            followup_date=status_obj.FollowupDate,
            status_at_time=new_status,
            recorded_by=updated_by,
            created_at=datetime.utcnow(),
        )
        self.session.add(history)
        await self.session.flush()
        return status_obj

    async def get_dashboard_counts(
        self,
        financial_year: str,
        month: Optional[int] = None,
        branch_id: Optional[int] = None,
    ) -> Dict[str, int]:
        """
        Aggregates summary counts for Follow, Done, Lost, Vehicle.
        Replaces sp_SelectPrevYearRenewalPolicySatusDashboard.
        """
        conditions = [
            PolicyRenewalStatus.FinancialYear == financial_year,
            PolicyRenewalStatus.isdeleted == 0,
        ]
        if branch_id and branch_id > 0:
            conditions.append(PolicyRenewalStatus.BranchId == branch_id)
        if month and month > 0:
            conditions.append(extract('month', PolicyRenewalStatus.ExpiryDate) == month)

        stmt = (
            select(PolicyRenewalStatus.RenewalStatus, func.count(PolicyRenewalStatus.Id))
            .where(and_(*conditions))
            .group_by(PolicyRenewalStatus.RenewalStatus)
        )
        rows = (await self.session.execute(stmt)).all()

        counts = {
            "follow_up_count": 0,
            "renewed_done_count": 0,
            "lost_count": 0,
            "vehicle_sold_count": 0,
            "total_target_count": 0,
        }

        for status_val, count_val in rows:
            s_lower = str(status_val).lower()
            if s_lower == "follow":
                counts["follow_up_count"] = count_val
            elif s_lower == "done":
                counts["renewed_done_count"] = count_val
            elif s_lower == "lost":
                counts["lost_count"] = count_val
            elif s_lower == "vehicle":
                counts["vehicle_sold_count"] = count_val

        counts["total_target_count"] = (
            counts["follow_up_count"]
            + counts["renewed_done_count"]
            + counts["lost_count"]
            + counts["vehicle_sold_count"]
        )
        return counts

    async def get_executive_counts(
        self,
        financial_year: str,
        month: Optional[int] = None,
        branch_id: Optional[int] = None,
    ) -> List[ExecutiveRenewalCount]:
        """
        Aggregates renewal metrics broken down by Sales Executive.
        Replaces sp_PreYearRenawalentryExcutivewiseCount.
        """
        conditions = [
            PolicyRenewalStatus.FinancialYear == financial_year,
            PolicyRenewalStatus.isdeleted == 0,
        ]
        if branch_id and branch_id > 0:
            conditions.append(PolicyRenewalStatus.BranchId == branch_id)
        if month and month > 0:
            conditions.append(extract('month', PolicyRenewalStatus.ExpiryDate) == month)

        stmt = (
            select(
                PolicyRenewalStatus.ExecutiveId,
                PolicyRenewalStatus.RenewalStatus,
                func.count(PolicyRenewalStatus.Id),
            )
            .where(and_(*conditions))
            .group_by(PolicyRenewalStatus.ExecutiveId, PolicyRenewalStatus.RenewalStatus)
        )
        rows = (await self.session.execute(stmt)).all()

        exec_dict: Dict[int, Dict[str, int]] = {}
        for ex_id, st_val, cnt in rows:
            if ex_id not in exec_dict:
                exec_dict[ex_id] = {"follow": 0, "done": 0, "lost": 0, "vehicle": 0}
            s = str(st_val).lower()
            if s in exec_dict[ex_id]:
                exec_dict[ex_id][s] = cnt

        result: List[ExecutiveRenewalCount] = []
        for ex_id, data in exec_dict.items():
            tot = data["follow"] + data["done"] + data["lost"] + data["vehicle"]
            result.append(
                ExecutiveRenewalCount(
                    executive_id=ex_id,
                    executive_name=f"Executive-{ex_id}",
                    follow_up_count=data["follow"],
                    done_count=data["done"],
                    lost_count=data["lost"],
                    vehicle_count=data["vehicle"],
                    total_count=tot,
                )
            )
        return result

    async def get_company_counts(
        self,
        financial_year: str,
        month: Optional[int] = None,
        branch_id: Optional[int] = None,
    ) -> List[InsurerRenewalCount]:
        """
        Aggregates renewal metrics per Insurance Company.
        Replaces sp_PreYearRenawalentryCompanywiseCount.
        """
        conditions = [
            PolicyRenewalStatus.FinancialYear == financial_year,
            PolicyRenewalStatus.isdeleted == 0,
            PolicyRenewalStatus.InsuranceCompany.isnot(None),
        ]
        if branch_id and branch_id > 0:
            conditions.append(PolicyRenewalStatus.BranchId == branch_id)
        if month and month > 0:
            conditions.append(extract('month', PolicyRenewalStatus.ExpiryDate) == month)

        stmt = (
            select(
                PolicyRenewalStatus.InsuranceCompany,
                PolicyRenewalStatus.RenewalStatus,
                func.count(PolicyRenewalStatus.Id),
            )
            .where(and_(*conditions))
            .group_by(PolicyRenewalStatus.InsuranceCompany, PolicyRenewalStatus.RenewalStatus)
        )
        rows = (await self.session.execute(stmt)).all()

        comp_dict: Dict[str, Dict[str, int]] = {}
        for comp, st_val, cnt in rows:
            if not comp:
                continue
            if comp not in comp_dict:
                comp_dict[comp] = {"due": 0, "renewed": 0}
            comp_dict[comp]["due"] += cnt
            if str(st_val).lower() == "done":
                comp_dict[comp]["renewed"] += cnt

        result: List[InsurerRenewalCount] = []
        for comp, data in comp_dict.items():
            due = data["due"]
            ren = data["renewed"]
            pct = round((ren / due * 100.0), 2) if due > 0 else 0.0
            result.append(
                InsurerRenewalCount(
                    insurance_company=comp,
                    due_count=due,
                    renewed_count=ren,
                    retention_rate_pct=pct,
                )
            )
        return result
