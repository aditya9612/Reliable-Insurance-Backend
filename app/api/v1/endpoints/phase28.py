"""
FastAPI Route Handlers for Phase 28:
Franchise Agent Grid Margin Override Engine.
Physical Tables: tbl_franchisegridmargin.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.dependencies import get_current_principal
from app.core.rbac import PrincipalContext
from app.services.phase28_service import FranchiseGridMarginService
from app.schemas.phase28 import (
    FranchiseGridMarginCreate,
    FranchiseGridMarginBatchCreate,
    FranchiseGridMarginUpdate,
    FranchiseMarginCalculationRequest,
    FranchiseMarginCalculationResponse,
    FranchiseGridMarginResponse,
    FranchiseGridMarginBatchResponse,
    FranchiseGridMarginListResponse,
)

franchise_margins_router = APIRouter(prefix="/franchise-margins", tags=["Franchise Grid Margins"])


@franchise_margins_router.post(
    "",
    response_model=FranchiseGridMarginResponse,
    status_code=status.HTTP_200_OK,
    summary="Create or Update Franchise Agent Grid Margin Override",
    description="Inserts or updates the retained commission margin override for an agent under a franchise for a specific insurer and policy type.",
)
async def upsert_franchise_margin(
    payload: FranchiseGridMarginCreate,
    db: AsyncSession = Depends(get_db),
    principal: PrincipalContext = Depends(get_current_principal),
) -> FranchiseGridMarginResponse:
    service = FranchiseGridMarginService(db)
    record = await service.upsert_margin(payload, principal)
    return FranchiseGridMarginResponse.model_validate(record)


@franchise_margins_router.post(
    "/batch",
    response_model=FranchiseGridMarginBatchResponse,
    status_code=status.HTTP_200_OK,
    summary="Batch Apply Franchise Margin Across Multiple Policy Types",
    description="Batch creates or updates uniform margin percentages across a list of policy types for an agent under a franchise.",
)
async def batch_upsert_franchise_margins(
    payload: FranchiseGridMarginBatchCreate,
    db: AsyncSession = Depends(get_db),
    principal: PrincipalContext = Depends(get_current_principal),
) -> FranchiseGridMarginBatchResponse:
    service = FranchiseGridMarginService(db)
    records = await service.batch_upsert_margins(payload, principal)
    validated_items = [FranchiseGridMarginResponse.model_validate(r) for r in records]
    return FranchiseGridMarginBatchResponse(
        success=True,
        count=len(validated_items),
        message=f"Successfully configured margin override for {len(validated_items)} policy types.",
        items=validated_items,
    )


@franchise_margins_router.get(
    "",
    response_model=FranchiseGridMarginListResponse,
    summary="List Franchise Grid Margin Overrides",
    description="Lists active margin overrides filtered by franchise, agent, insurance company, or policy type with pagination.",
)
async def list_franchise_margins(
    franchise_id: Optional[int] = Query(None, ge=1, description="Franchise ID filter"),
    franchise_agent_id: Optional[int] = Query(None, ge=1, description="Agent ID filter"),
    insurance_company_id: Optional[int] = Query(None, ge=1, description="Insurance Company ID filter"),
    policy_type_id: Optional[int] = Query(None, ge=1, description="Policy Type ID filter"),
    skip: int = Query(0, ge=0, description="Pagination skip offset"),
    limit: int = Query(50, ge=1, le=500, description="Pagination page limit"),
    db: AsyncSession = Depends(get_db),
    principal: PrincipalContext = Depends(get_current_principal),
) -> FranchiseGridMarginListResponse:
    service = FranchiseGridMarginService(db)
    items, total = await service.list_margins(
        franchise_id=franchise_id,
        franchise_agent_id=franchise_agent_id,
        insurance_company_id=insurance_company_id,
        policy_type_id=policy_type_id,
        skip=skip,
        limit=limit,
        principal=principal,
    )
    validated = [FranchiseGridMarginResponse.model_validate(i) for i in items]
    return FranchiseGridMarginListResponse(
        total=total,
        skip=skip,
        limit=limit,
        items=validated,
    )


@franchise_margins_router.get(
    "/lookup",
    response_model=Optional[FranchiseGridMarginResponse],
    summary="Lookup Specific Margin Override",
    description="Direct lookup for the active margin override matching a franchise, agent, insurer, and policy type.",
)
async def lookup_franchise_margin(
    franchise_id: int = Query(..., ge=1, description="Franchise ID"),
    franchise_agent_id: int = Query(..., ge=1, description="Agent ID"),
    insurance_company_id: int = Query(..., ge=1, description="Insurance Company ID"),
    policy_type_id: int = Query(..., ge=1, description="Policy Type ID"),
    db: AsyncSession = Depends(get_db),
    principal: PrincipalContext = Depends(get_current_principal),
) -> Optional[FranchiseGridMarginResponse]:
    service = FranchiseGridMarginService(db)
    record = await service.lookup_margin(
        franchise_id=franchise_id,
        agent_id=franchise_agent_id,
        company_id=insurance_company_id,
        policy_type_id=policy_type_id,
        principal=principal,
    )
    if not record:
        return None
    return FranchiseGridMarginResponse.model_validate(record)


@franchise_margins_router.post(
    "/calculate-split",
    response_model=FranchiseMarginCalculationResponse,
    summary="Calculate Franchise & Agent Commission Split",
    description="Simulates the legacy commission engine calculation, applying retained margin deductions to determine net agent grid and payout.",
)
async def calculate_commission_split(
    payload: FranchiseMarginCalculationRequest,
    db: AsyncSession = Depends(get_db),
    principal: PrincipalContext = Depends(get_current_principal),
) -> FranchiseMarginCalculationResponse:
    service = FranchiseGridMarginService(db)
    return await service.calculate_commission_split(payload, principal)


@franchise_margins_router.get(
    "/{margin_id}",
    response_model=FranchiseGridMarginResponse,
    summary="Get Franchise Margin Override Detail",
    description="Fetches an existing margin override record by primary key ID.",
)
async def get_franchise_margin(
    margin_id: int = Path(..., ge=1, description="Margin record ID"),
    db: AsyncSession = Depends(get_db),
    principal: PrincipalContext = Depends(get_current_principal),
) -> FranchiseGridMarginResponse:
    service = FranchiseGridMarginService(db)
    record = await service.get_margin_by_id(margin_id, principal)
    return FranchiseGridMarginResponse.model_validate(record)


@franchise_margins_router.put(
    "/{margin_id}",
    response_model=FranchiseGridMarginResponse,
    summary="Update Franchise Margin Override Percentage",
    description="Updates the retained commission margin percentage for an existing margin record.",
)
async def update_franchise_margin(
    margin_id: int = Path(..., ge=1, description="Margin record ID"),
    payload: FranchiseGridMarginUpdate = ...,
    db: AsyncSession = Depends(get_db),
    principal: PrincipalContext = Depends(get_current_principal),
) -> FranchiseGridMarginResponse:
    service = FranchiseGridMarginService(db)
    record = await service.update_margin(margin_id, payload, principal)
    return FranchiseGridMarginResponse.model_validate(record)


@franchise_margins_router.delete(
    "/{margin_id}",
    summary="Soft Delete Franchise Margin Override",
    description="Soft-deletes the margin override record so that default grid rates apply without franchise deduction.",
)
async def delete_franchise_margin(
    margin_id: int = Path(..., ge=1, description="Margin record ID"),
    db: AsyncSession = Depends(get_db),
    principal: PrincipalContext = Depends(get_current_principal),
):
    service = FranchiseGridMarginService(db)
    await service.delete_margin(margin_id, principal)
    return {"success": True, "message": f"Margin override {margin_id} successfully deactivated."}
