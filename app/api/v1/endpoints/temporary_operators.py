"""
FastAPI Route Handlers for Phase 29:
Temporary Operator Role & Workload Delegation Master.
Physical Tables: tbl_tempararyoperator.
"""
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.dependencies import get_current_principal
from app.core.rbac import PrincipalContext
from app.services.temporary_operator_service import TemporaryOperatorService
from app.schemas.temporary_operator import (
    TemporaryOperatorCreate,
    TemporaryOperatorUpdate,
    TemporaryOperatorResponse,
    TemporaryOperatorListResponse,
    EffectiveOperatorResponse,
    EligibleOperatorResponse,
)

temporary_operators_router = APIRouter(prefix="/temporary-operators", tags=["Temporary Operators"])


@temporary_operators_router.post(
    "",
    response_model=TemporaryOperatorResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Assign Temporary Operator Delegation",
    description="Creates a workload delegation assignment from a permanent operator to a designated substitute operator for a validity window.",
)
async def create_delegation(
    payload: TemporaryOperatorCreate,
    db: AsyncSession = Depends(get_db),
    principal: PrincipalContext = Depends(get_current_principal),
) -> TemporaryOperatorResponse:
    service = TemporaryOperatorService(db)
    return await service.create_delegation(payload, principal)


@temporary_operators_router.get(
    "",
    response_model=TemporaryOperatorListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Temporary Operator Delegations",
    description="Retrieves a paginated list of operator delegations with optional filtering by permanent or temporary operator and active status.",
)
async def list_delegations(
    per_operator_id: Optional[int] = Query(None, description="Filter by Permanent Operator ID"),
    temp_operator_id: Optional[int] = Query(None, description="Filter by Temporary Operator ID"),
    active_only: bool = Query(False, description="Filter to currently active delegations only"),
    skip: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(50, ge=1, le=200, description="Pagination limit"),
    db: AsyncSession = Depends(get_db),
    principal: PrincipalContext = Depends(get_current_principal),
) -> TemporaryOperatorListResponse:
    service = TemporaryOperatorService(db)
    return await service.list_delegations(
        principal=principal,
        per_operator_id=per_operator_id,
        temp_operator_id=temp_operator_id,
        active_only=active_only,
        skip=skip,
        limit=limit,
    )


@temporary_operators_router.get(
    "/eligible",
    response_model=List[EligibleOperatorResponse],
    status_code=status.HTTP_200_OK,
    summary="List Eligible Operators",
    description="Lists staff members with operator roles eligible for assignment or delegation.",
)
async def list_eligible_operators(
    db: AsyncSession = Depends(get_db),
    principal: PrincipalContext = Depends(get_current_principal),
) -> List[EligibleOperatorResponse]:
    service = TemporaryOperatorService(db)
    return await service.list_eligible_operators(principal=principal)


@temporary_operators_router.get(
    "/effective/{operator_id}",
    response_model=EffectiveOperatorResponse,
    status_code=status.HTTP_200_OK,
    summary="Resolve Effective Operator",
    description="Determines whether an operator's workload is currently delegated and returns the acting effective operator ID.",
)
async def resolve_effective_operator(
    operator_id: int = Path(..., gt=0, description="Operator Employee/User ID to resolve"),
    as_of: Optional[datetime] = Query(None, description="Optional timestamp to check delegation status for (defaults to UTC now)"),
    db: AsyncSession = Depends(get_db),
    principal: PrincipalContext = Depends(get_current_principal),
) -> EffectiveOperatorResponse:
    service = TemporaryOperatorService(db)
    return await service.resolve_effective_operator(operator_id=operator_id, principal=principal, as_of=as_of)


@temporary_operators_router.get(
    "/{delegation_id}",
    response_model=TemporaryOperatorResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Delegation Details by ID",
    description="Retrieves a single operator delegation record.",
)
async def get_delegation(
    delegation_id: int = Path(..., gt=0, description="Delegation primary key ID"),
    db: AsyncSession = Depends(get_db),
    principal: PrincipalContext = Depends(get_current_principal),
) -> TemporaryOperatorResponse:
    service = TemporaryOperatorService(db)
    return await service.get_delegation_by_id(delegation_id=delegation_id, principal=principal)


@temporary_operators_router.put(
    "/{delegation_id}",
    response_model=TemporaryOperatorResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Delegation Validity Window",
    description="Updates the start and end validity timestamps of an existing delegation.",
)
async def update_delegation(
    payload: TemporaryOperatorUpdate,
    delegation_id: int = Path(..., gt=0, description="Delegation primary key ID"),
    db: AsyncSession = Depends(get_db),
    principal: PrincipalContext = Depends(get_current_principal),
) -> TemporaryOperatorResponse:
    service = TemporaryOperatorService(db)
    return await service.update_delegation(delegation_id, payload, principal)


@temporary_operators_router.delete(
    "/{delegation_id}",
    status_code=status.HTTP_200_OK,
    summary="Revoke Delegation",
    description="Soft-deletes (revokes) an active temporary operator assignment.",
)
async def revoke_delegation(
    delegation_id: int = Path(..., gt=0, description="Delegation primary key ID"),
    db: AsyncSession = Depends(get_db),
    principal: PrincipalContext = Depends(get_current_principal),
) -> dict:
    service = TemporaryOperatorService(db)
    return await service.revoke_delegation(delegation_id, principal)
