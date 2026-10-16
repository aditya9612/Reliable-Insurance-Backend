"""
Phase 28 Service Layer:
Franchise Agent Grid Margin Override Engine.
Physical Tables:
1. tbl_franchisegridmargin (FranchiseGridMargin)
"""
import asyncio
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional, Tuple
import logging
from fastapi import HTTPException, status
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.franchise_margin import FranchiseGridMargin
from app.core.rbac import PrincipalContext, is_global_admin_role
from app.schemas.franchise_margin import (
    FranchiseGridMarginCreate,
    FranchiseGridMarginBatchCreate,
    FranchiseGridMarginUpdate,
    FranchiseMarginCalculationRequest,
    FranchiseMarginCalculationResponse,
    FranchiseGridMarginResponse,
    FranchiseGridMarginBatchResponse,
    FranchiseGridMarginListResponse,
)

logger = logging.getLogger(__name__)

# Mutex to guarantee concurrency-safe margin upserts and prevent duplicate active rows
_MARGIN_WRITE_LOCK = asyncio.Lock()


class FranchiseGridMarginService:
    """Service orchestrating franchise agent commission margin overrides."""

    def __init__(self, db: AsyncSession):
        self.db = db

    def _validate_franchise_access(self, franchise_id: int, principal: PrincipalContext) -> None:
        """
        Enforce multi-tenant franchise isolation.
        Legacy Parity: adm_FranchiseGridMargin.aspx.cs L44-55 (RoleId 9 restricted to Session['FranchiseId']).
        """
        if is_global_admin_role(principal.role_name):
            return

        # If user is a franchise user (RoleId 9 or role_name 'FRANCHISE') or has an assigned franchise_id
        if (principal.role_id == 9 or (principal.role_name and "FRANCHISE" in principal.role_name.upper())) and principal.franchise_id is not None:
            if principal.franchise_id != franchise_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Access denied: Franchise users can only manage margins for their assigned Franchise ID ({principal.franchise_id}).",
                )
        elif principal.franchise_id is not None and principal.franchise_id != franchise_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: Principal is restricted to Franchise ID ({principal.franchise_id}).",
            )

    async def upsert_margin(
        self, payload: FranchiseGridMarginCreate, principal: PrincipalContext
    ) -> FranchiseGridMargin:
        """
        Create or update a franchise agent commission margin override.
        Legacy Parity: adm_FranchiseGridMargin.aspx.cs L258-294 (btn_Submit_Click / sp_franchsieGridMargin).
        """
        self._validate_franchise_access(payload.franchise_id, principal)

        async with _MARGIN_WRITE_LOCK:
            stmt = (
                select(FranchiseGridMargin)
                .where(
                    and_(
                        FranchiseGridMargin.FranchiseId == payload.franchise_id,
                        FranchiseGridMargin.FranchiseAgentId == payload.franchise_agent_id,
                        FranchiseGridMargin.InsuranceCompanyId == payload.insurance_company_id,
                        FranchiseGridMargin.PolicyTypeId == payload.policy_type_id,
                        FranchiseGridMargin.isdeleted == 0,
                    )
                )
                .with_for_update()
            )
        existing = (await self.db.execute(stmt)).scalars().first()

        now = datetime.utcnow()
        username = principal.username or f"user_{principal.user_id}"

        if existing:
            existing.margin = payload.margin
            existing.UpdatedUser = username
            existing.UpdatedDate = now
            margin_record = existing
        else:
            margin_record = FranchiseGridMargin(
                FranchiseId=payload.franchise_id,
                FranchiseAgentId=payload.franchise_agent_id,
                InsuranceCompanyId=payload.insurance_company_id,
                PolicyTypeId=payload.policy_type_id,
                margin=payload.margin,
                isdeleted=0,
                CreatedUser=username,
                CreatedDate=now,
            )
            self.db.add(margin_record)

        await self.db.commit()
        await self.db.refresh(margin_record)
        return margin_record

    async def batch_upsert_margins(
        self, payload: FranchiseGridMarginBatchCreate, principal: PrincipalContext
    ) -> List[FranchiseGridMargin]:
        """
        Batch configure a uniform margin percentage across multiple policy types.
        Legacy Parity: adm_FranchiseGridMargin.aspx.cs L296-385 (btnsave_Click).
        """
        self._validate_franchise_access(payload.franchise_id, principal)

        now = datetime.utcnow()
        username = principal.username or f"user_{principal.user_id}"
        results: List[FranchiseGridMargin] = []

        async with _MARGIN_WRITE_LOCK:
            for pt_id in payload.policy_type_ids:
                stmt = (
                    select(FranchiseGridMargin)
                    .where(
                        and_(
                            FranchiseGridMargin.FranchiseId == payload.franchise_id,
                            FranchiseGridMargin.FranchiseAgentId == payload.franchise_agent_id,
                            FranchiseGridMargin.InsuranceCompanyId == payload.insurance_company_id,
                            FranchiseGridMargin.PolicyTypeId == pt_id,
                            FranchiseGridMargin.isdeleted == 0,
                        )
                    )
                    .with_for_update()
                )
                existing = (await self.db.execute(stmt)).scalars().first()

                if existing:
                    existing.margin = payload.margin
                    existing.UpdatedUser = username
                    existing.UpdatedDate = now
                    results.append(existing)
                else:
                    new_margin = FranchiseGridMargin(
                        FranchiseId=payload.franchise_id,
                        FranchiseAgentId=payload.franchise_agent_id,
                        InsuranceCompanyId=payload.insurance_company_id,
                        PolicyTypeId=pt_id,
                        margin=payload.margin,
                        isdeleted=0,
                        CreatedUser=username,
                        CreatedDate=now,
                    )
                    self.db.add(new_margin)
                    results.append(new_margin)

            await self.db.commit()
            for r in results:
                await self.db.refresh(r)
            return results

    async def get_margin_by_id(
        self, margin_id: int, principal: PrincipalContext
    ) -> FranchiseGridMargin:
        """Fetch margin override by primary key."""
        stmt = select(FranchiseGridMargin).where(
            and_(FranchiseGridMargin.Id == margin_id, FranchiseGridMargin.isdeleted == 0)
        )
        record = (await self.db.execute(stmt)).scalars().first()
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Franchise grid margin record {margin_id} not found or deleted.",
            )
        self._validate_franchise_access(record.FranchiseId, principal)
        return record

    async def update_margin(
        self, margin_id: int, payload: FranchiseGridMarginUpdate, principal: PrincipalContext
    ) -> FranchiseGridMargin:
        """Update margin percentage on an existing margin record."""
        record = await self.get_margin_by_id(margin_id, principal)
        record.margin = payload.margin
        record.UpdatedUser = principal.username or f"user_{principal.user_id}"
        record.UpdatedDate = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(record)
        return record

    async def delete_margin(
        self, margin_id: int, principal: PrincipalContext
    ) -> bool:
        """Soft delete a margin override."""
        record = await self.get_margin_by_id(margin_id, principal)
        record.isdeleted = 1
        record.UpdatedUser = principal.username or f"user_{principal.user_id}"
        record.UpdatedDate = datetime.utcnow()
        await self.db.commit()
        return True

    async def lookup_margin(
        self,
        franchise_id: int,
        agent_id: int,
        company_id: int,
        policy_type_id: int,
        principal: Optional[PrincipalContext] = None,
    ) -> Optional[FranchiseGridMargin]:
        """
        Lookup configured margin for an agent, insurer, and policy type.
        Legacy Parity: sp_franchsieGridMargin with P_opr='SELECT1' or 'SELECT2'.
        """
        if principal:
            self._validate_franchise_access(franchise_id, principal)

        stmt = select(FranchiseGridMargin).where(
            and_(
                FranchiseGridMargin.FranchiseId == franchise_id,
                FranchiseGridMargin.FranchiseAgentId == agent_id,
                FranchiseGridMargin.InsuranceCompanyId == company_id,
                FranchiseGridMargin.PolicyTypeId == policy_type_id,
                FranchiseGridMargin.isdeleted == 0,
            )
        )
        return (await self.db.execute(stmt)).scalars().first()

    async def list_margins(
        self,
        franchise_id: Optional[int] = None,
        franchise_agent_id: Optional[int] = None,
        insurance_company_id: Optional[int] = None,
        policy_type_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 50,
        principal: Optional[PrincipalContext] = None,
    ) -> Tuple[List[FranchiseGridMargin], int]:
        """List active margin overrides with filtering, pagination, and tenant isolation."""
        if principal and principal.franchise_id is not None and not is_global_admin_role(principal.role_name):
            franchise_id = principal.franchise_id

        filters = [FranchiseGridMargin.isdeleted == 0]
        if franchise_id is not None:
            if principal:
                self._validate_franchise_access(franchise_id, principal)
            filters.append(FranchiseGridMargin.FranchiseId == franchise_id)
        if franchise_agent_id is not None:
            filters.append(FranchiseGridMargin.FranchiseAgentId == franchise_agent_id)
        if insurance_company_id is not None:
            filters.append(FranchiseGridMargin.InsuranceCompanyId == insurance_company_id)
        if policy_type_id is not None:
            filters.append(FranchiseGridMargin.PolicyTypeId == policy_type_id)

        count_stmt = select(func.count(FranchiseGridMargin.Id)).where(and_(*filters))
        total = (await self.db.execute(count_stmt)).scalar() or 0

        query_stmt = (
            select(FranchiseGridMargin)
            .where(and_(*filters))
            .order_by(FranchiseGridMargin.Id.desc())
            .offset(skip)
            .limit(limit)
        )
        items = (await self.db.execute(query_stmt)).scalars().all()
        return list(items), total

    async def calculate_commission_split(
        self, payload: FranchiseMarginCalculationRequest, principal: Optional[PrincipalContext] = None
    ) -> FranchiseMarginCalculationResponse:
        """
        Compute effective commission split between franchise and agent.
        Legacy Parity:
        AgentCommissionRecalculation.aspx.cs L1869-1895: FranchiseAgent_CalculateCommission:
        if (Margine > 0)
        {
            if (IS_FR_As_AgentId == "0")
            {
                double grid = gridValue - Margine;
            }
            else
            {
                double grid = gridValue;
            }
        }
        """
        if principal:
            self._validate_franchise_access(payload.franchise_id, principal)

        margin_record = await self.lookup_margin(
            franchise_id=payload.franchise_id,
            agent_id=payload.franchise_agent_id,
            company_id=payload.insurance_company_id,
            policy_type_id=payload.policy_type_id,
        )

        has_override = margin_record is not None
        retained_margin = margin_record.margin if margin_record else Decimal("0.00")

        # Franchise acting as agent receives full commission (no franchise deduction)
        if payload.is_franchise_as_agent:
            effective_agent_grid = payload.gross_grid_percentage
            retained_margin = Decimal("0.00")
        else:
            if retained_margin > Decimal("0.00"):
                effective_agent_grid = max(Decimal("0.00"), payload.gross_grid_percentage - retained_margin)
            else:
                effective_agent_grid = payload.gross_grid_percentage

        # Payout math
        hundred = Decimal("100.00")
        franchise_amount = (payload.premium_amount * (retained_margin / hundred)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        agent_amount = (payload.premium_amount * (effective_agent_grid / hundred)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

        return FranchiseMarginCalculationResponse(
            franchise_id=payload.franchise_id,
            franchise_agent_id=payload.franchise_agent_id,
            insurance_company_id=payload.insurance_company_id,
            policy_type_id=payload.policy_type_id,
            premium_amount=payload.premium_amount,
            gross_grid_percentage=payload.gross_grid_percentage,
            retained_margin_percentage=retained_margin,
            effective_agent_grid_percentage=effective_agent_grid,
            franchise_retained_amount=franchise_amount,
            agent_payout_amount=agent_amount,
            is_franchise_as_agent=bool(payload.is_franchise_as_agent),
            has_margin_override=has_override,
        )
