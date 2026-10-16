"""
FastAPI Route Handlers for Phase 26:
Emergency Roadside Claim Assistance & Accident Intake Lifecycle.
Physical Tables: tbl_claimassistance, tbl_claimassistanceimg.
"""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, Query, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.dependencies import get_current_principal, require_roles
from app.core.rbac import PrincipalContext
from app.services.claim_assistance_service import ClaimAssistanceService, Phase26Service
from app.schemas.claim_assistance import (
    ClaimAssistanceCreate,
    ClaimAssistanceUpdate,
    ClaimAssistanceAssignClaimNo,
    ClaimAssistanceReadStatusUpdate,
    ClaimAssistanceResponse,
    ClaimAssistanceSummaryResponse,
)

claim_assistance_router = APIRouter(prefix="/claim-assistance", tags=["Emergency Claim Assistance"])


@claim_assistance_router.post(
    "",
    response_model=ClaimAssistanceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record Emergency Roadside Claim Assistance Intimation",
    description="Registers immediate roadside accident intimation with vehicle, driver, towing garage details and damage photos.",
)
async def create_claim_assistance(
    payload: ClaimAssistanceCreate,
    db: AsyncSession = Depends(get_db),
    principal: PrincipalContext = Depends(get_current_principal),
) -> ClaimAssistanceResponse:
    service = ClaimAssistanceService(db)
    return await service.create_claim_assistance(payload, principal=principal)


@claim_assistance_router.get(
    "/summary",
    response_model=ClaimAssistanceSummaryResponse,
    summary="Get Claim Assistance Dashboard Summary Metrics",
    description="Retrieves operational dashboard metrics including unread, pending claim assignment, and resolved counts.",
)
async def get_claim_assistance_summary(
    branch_id: Optional[int] = Query(None, description="Optional branch ID filter"),
    db: AsyncSession = Depends(get_db),
    principal: PrincipalContext = Depends(get_current_principal),
) -> ClaimAssistanceSummaryResponse:
    service = ClaimAssistanceService(db)
    return await service.get_summary_metrics(branch_id=branch_id, principal=principal)


@claim_assistance_router.get(
    "",
    response_model=List[ClaimAssistanceResponse],
    summary="List Claim Assistance Intimations",
    description="Lists accident intimations with multi-criteria filtering by vehicle, insurer, status, and read status.",
)
async def list_claim_assistance(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    veh_no: Optional[str] = Query(None, description="Filter by vehicle registration number"),
    insurance_company_id: Optional[int] = Query(None, description="Filter by insurance company ID"),
    read_status: Optional[int] = Query(None, ge=0, le=1, description="Filter by read status (0=Unread, 1=Read)"),
    status_filter: Optional[str] = Query(None, description="Filter by status (e.g. INTIMATED, CLAIM_NO_ASSIGNED)"),
    branch_id: Optional[int] = Query(None, description="Filter by operating branch ID"),
    db: AsyncSession = Depends(get_db),
    principal: PrincipalContext = Depends(get_current_principal),
) -> List[ClaimAssistanceResponse]:
    service = ClaimAssistanceService(db)
    return await service.list_claim_assistance(
        skip=skip,
        limit=limit,
        veh_no=veh_no,
        insurance_company_id=insurance_company_id,
        read_status=read_status,
        status_filter=status_filter,
        branch_id=branch_id,
        principal=principal,
    )


@claim_assistance_router.get(
    "/{assistance_id}",
    response_model=ClaimAssistanceResponse,
    summary="Get Claim Assistance Details by ID",
    description="Retrieves a single roadside accident intimation with all attached damage photos with branch/agency isolation.",
)
async def get_claim_assistance(
    assistance_id: int = Path(..., ge=1, description="Claim Assistance ID"),
    db: AsyncSession = Depends(get_db),
    principal: PrincipalContext = Depends(get_current_principal),
) -> ClaimAssistanceResponse:
    service = ClaimAssistanceService(db)
    return await service.get_claim_assistance(assistance_id, principal=principal)


@claim_assistance_router.put(
    "/{assistance_id}",
    response_model=ClaimAssistanceResponse,
    summary="Update Roadside Claim Assistance Triage Details",
    description="Updates driver, garage, location, reason or lifecycle status during operator triaging.",
    dependencies=[Depends(require_roles("ADMIN", "OWNER", "CLERK", "EMPLOYEE", "CLAIM", "OPERATOR"))],
)
async def update_claim_assistance(
    payload: ClaimAssistanceUpdate,
    assistance_id: int = Path(..., ge=1, description="Claim Assistance ID"),
    db: AsyncSession = Depends(get_db),
    principal: PrincipalContext = Depends(get_current_principal),
) -> ClaimAssistanceResponse:
    service = ClaimAssistanceService(db)
    return await service.update_claim_assistance(assistance_id, payload, principal=principal)


@claim_assistance_router.post(
    "/{assistance_id}/assign-claim-no",
    response_model=ClaimAssistanceResponse,
    summary="Assign Formal Claim Number & Dispatch Notifications",
    description="Assigns official insurer Claim Number, transitions status to CLAIM_NO_ASSIGNED, marks as read, and sends SMS/internal inbox alerts.",
    dependencies=[Depends(require_roles("ADMIN", "OWNER", "CLERK", "EMPLOYEE", "CLAIM"))],
)
async def assign_claim_number(
    payload: ClaimAssistanceAssignClaimNo,
    assistance_id: int = Path(..., ge=1, description="Claim Assistance ID"),
    db: AsyncSession = Depends(get_db),
    principal: PrincipalContext = Depends(get_current_principal),
) -> ClaimAssistanceResponse:
    service = ClaimAssistanceService(db)
    return await service.assign_claim_number(assistance_id, payload, principal=principal)


@claim_assistance_router.patch(
    "/{assistance_id}/read-status",
    response_model=ClaimAssistanceResponse,
    summary="Update Claim Assistance Read Status",
    description="Toggles or sets read status flag (0=Unread, 1=Read).",
    dependencies=[Depends(require_roles("ADMIN", "OWNER", "CLERK", "EMPLOYEE", "CLAIM", "OPERATOR"))],
)
async def update_read_status(
    payload: ClaimAssistanceReadStatusUpdate,
    assistance_id: int = Path(..., ge=1, description="Claim Assistance ID"),
    db: AsyncSession = Depends(get_db),
    principal: PrincipalContext = Depends(get_current_principal),
) -> ClaimAssistanceResponse:
    service = ClaimAssistanceService(db)
    return await service.update_read_status(assistance_id, payload, principal=principal)


@claim_assistance_router.delete(
    "/{assistance_id}",
    response_model=Dict[str, Any],
    summary="Soft Delete Claim Assistance Record",
    description="Marks roadside claim assistance intimation as deleted (isdeleted=1).",
    dependencies=[Depends(require_roles("ADMIN", "OWNER", "CLERK"))],
)
async def delete_claim_assistance(
    assistance_id: int = Path(..., ge=1, description="Claim Assistance ID"),
    db: AsyncSession = Depends(get_db),
    principal: PrincipalContext = Depends(get_current_principal),
) -> Dict[str, Any]:
    service = ClaimAssistanceService(db)
    return await service.delete_claim_assistance(assistance_id, principal=principal)
