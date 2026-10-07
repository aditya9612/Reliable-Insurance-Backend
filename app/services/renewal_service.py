"""
Service for Phase 13 Block E — Policy Renewal Engine & CRM.
Implements Indian financial year arithmetic, telecaller workflow, 4-state lifecycle,
and executive/company dashboard reporting.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.renewal import RenewalRepository
from app.models.renewal import PolicyRenewalStatus
from app.schemas.renewal import (
    ExpiringPolicyResponse,
    CreateRenewalFollowupRequest,
    UpdateRenewalStatusRequest,
    RenewalFollowupResponse,
    RenewalDashboardResponse,
)


def get_indian_financial_year(dt: Optional[datetime] = None) -> str:
    """
    Computes Indian Financial Year (April 1 to March 31).
    Matches legacy Dashboard_PrevYearRenewalStatus.aspx.cs (L27–L32).
    """
    if dt is None:
        dt = datetime.utcnow()
    if dt.month <= 3:
        start_year = dt.year - 1
    else:
        start_year = dt.year
    return f"{start_year}-{start_year + 1}"


class RenewalService:
    """Service orchestrating renewal tracking, telecaller updates, and analytics."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = RenewalRepository(session)

    async def get_due_renewals(
        self,
        days_ahead: int = 30,
        branch_id: Optional[int] = None,
        agent_id: Optional[int] = None,
        executive_id: Optional[int] = None,
        offset: int = 0,
        limit: int = 50,
    ) -> Tuple[List[ExpiringPolicyResponse], int]:
        """Queries policies nearing expiration scoped by tenancy."""
        return await self.repo.get_expiring_policies(
            days_ahead=days_ahead,
            branch_id=branch_id,
            agent_id=agent_id,
            executive_id=executive_id,
            offset=offset,
            limit=limit,
        )

    async def get_followups(
        self,
        financial_year: Optional[str] = None,
        status_filter: Optional[str] = None,
        branch_id: Optional[int] = None,
        agent_id: Optional[int] = None,
        executive_id: Optional[int] = None,
        offset: int = 0,
        limit: int = 50,
    ) -> Tuple[List[RenewalFollowupResponse], int]:
        """Lists active follow-up entries for telecallers."""
        fy = financial_year or get_indian_financial_year()
        entities, total = await self.repo.get_followups(
            financial_year=fy,
            status=status_filter,
            branch_id=branch_id,
            agent_id=agent_id,
            executive_id=executive_id,
            offset=offset,
            limit=limit,
        )

        dtos = [
            RenewalFollowupResponse(
                id=e.Id,
                transaction_id=e.TransanctionId,
                registration_number=e.RegistrationNo,
                financial_year=e.FinancialYear,
                status=e.RenewalStatus,
                remark=e.Remark,
                followup_date=e.FollowupDate,
                insurance_company=e.InsuranceCompany,
                total_premium=float(e.TotalPremium),
                mobile_no=e.MobileNo,
                expiry_date=e.ExpiryDate,
                created_date=e.CreatedDate,
                agent_id=e.AgentId,
                executive_id=e.ExecutiveId,
                branch_id=e.BranchId,
            )
            for e in entities
        ]
        return dtos, total

    async def record_followup(
        self,
        payload: CreateRenewalFollowupRequest,
        recorded_by: str,
        user_role_id: int = 0,
        agent_id: int = 0,
        executive_id: int = 0,
        branch_id: Optional[int] = None,
    ) -> RenewalFollowupResponse:
        """Records a telecaller interaction remark and reschedules followup date."""
        entity = await self.repo.upsert_followup(
            transaction_id=payload.transaction_id,
            registration_no=payload.registration_number,
            financial_year=payload.financial_year,
            remark=payload.remark,
            followup_date=payload.followup_date,
            insurance_company=payload.insurance_company,
            total_premium=payload.total_premium,
            mobile_no=payload.mobile_number,
            expiry_date=payload.expiry_date,
            user_role_id=user_role_id,
            agent_id=agent_id,
            executive_id=executive_id,
            branch_id=branch_id,
            recorded_by=recorded_by,
        )
        await self.session.commit()

        return RenewalFollowupResponse(
            id=entity.Id,
            transaction_id=entity.TransanctionId,
            registration_number=entity.RegistrationNo,
            financial_year=entity.FinancialYear,
            status=entity.RenewalStatus,
            remark=entity.Remark,
            followup_date=entity.FollowupDate,
            insurance_company=entity.InsuranceCompany,
            total_premium=float(entity.TotalPremium),
            mobile_no=entity.MobileNo,
            expiry_date=entity.ExpiryDate,
            created_date=entity.CreatedDate,
            agent_id=entity.AgentId,
            executive_id=entity.ExecutiveId,
            branch_id=entity.BranchId,
        )

    async def update_renewal_status(
        self,
        status_id: int,
        payload: UpdateRenewalStatusRequest,
        updated_by: str,
    ) -> RenewalFollowupResponse:
        """Transitions renewal status (Follow, Done, Lost, Vehicle)."""
        entity = await self.repo.update_status(
            status_id=status_id,
            new_status=payload.status,
            remark=payload.remark,
            updated_by=updated_by,
        )
        if not entity:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Renewal record with ID {status_id} not found.",
            )

        await self.session.commit()
        return RenewalFollowupResponse(
            id=entity.Id,
            transaction_id=entity.TransanctionId,
            registration_number=entity.RegistrationNo,
            financial_year=entity.FinancialYear,
            status=entity.RenewalStatus,
            remark=entity.Remark,
            followup_date=entity.FollowupDate,
            insurance_company=entity.InsuranceCompany,
            total_premium=float(entity.TotalPremium),
            mobile_no=entity.MobileNo,
            expiry_date=entity.ExpiryDate,
            created_date=entity.CreatedDate,
            agent_id=entity.AgentId,
            executive_id=entity.ExecutiveId,
            branch_id=entity.BranchId,
        )

    async def get_dashboard(
        self,
        financial_year: Optional[str] = None,
        month: Optional[int] = None,
        branch_id: Optional[int] = None,
    ) -> RenewalDashboardResponse:
        """Aggregates executive management dashboard metrics."""
        fy = financial_year or get_indian_financial_year()

        summary_counts = await self.repo.get_dashboard_counts(
            financial_year=fy,
            month=month,
            branch_id=branch_id,
        )
        exec_breakdown = await self.repo.get_executive_counts(
            financial_year=fy,
            month=month,
            branch_id=branch_id,
        )
        comp_breakdown = await self.repo.get_company_counts(
            financial_year=fy,
            month=month,
            branch_id=branch_id,
        )

        return RenewalDashboardResponse(
            financial_year=fy,
            month=month,
            summary=summary_counts,
            executive_breakdown=exec_breakdown,
            company_breakdown=comp_breakdown,
        )
