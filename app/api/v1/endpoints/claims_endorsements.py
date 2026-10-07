"""
FastAPI v1 Endpoints for Phase 10 — Claims & Endorsements Engine.

Exposes 3 routers:
1. `claims_router` (`/api/v1/claims`)
2. `endorsements_router` (`/api/v1/endorsements`)
3. `refunds_router` (`/api/v1/refunds`)
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, Header, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db, require_roles
from app.core.rbac import (
    CLAIM_APPROVE_SETTLE_ROLES,
    CLAIM_CREATE_ROLES,
    CLAIM_READ_ROLES,
    CLAIM_UPDATE_ROLES,
    ENDORSEMENT_APPROVE_APPLY_ROLES,
    ENDORSEMENT_CREATE_ROLES,
    ENDORSEMENT_READ_ROLES,
    REFUND_APPROVE_WRITE_ROLES,
)
from app.models.user import User
from app.schemas.claims_endorsement import (
    ClaimActionRemarksRequest,
    ClaimApprovalRequest,
    ClaimAssessmentRequest,
    ClaimDocumentCreateRequest,
    ClaimDocumentResponse,
    ClaimIntimateRequest,
    ClaimListResponse,
    ClaimRegisterRequest,
    ClaimRejectionRequest,
    ClaimResponse,
    ClaimSettlementRequest,
    ClaimSurveyUpdateRequest,
    EndorsementActionRequest,
    EndorsementApplyRequest,
    EndorsementCreateRequest,
    EndorsementListResponse,
    EndorsementPreviewResponse,
    EndorsementRejectRequest,
    EndorsementResponse,
    RefundActionRequest,
    RefundDisburseRequest,
    APIResponse,
)
from app.services.claims_endorsement import ClaimsEndorsementService

claims_router = APIRouter()
endorsements_router = APIRouter()
refunds_router = APIRouter()


# ===========================================================================
# 1. Claims Endpoints (`/api/v1/claims`)
# ===========================================================================

@claims_router.post(
    "",
    response_model=APIResponse[ClaimResponse],
    status_code=status.HTTP_201_CREATED,
)
async def intimate_claim_endpoint(
    payload: ClaimIntimateRequest,
    response: Response,
    idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*CLAIM_CREATE_ROLES)),
) -> APIResponse[ClaimResponse]:
    if idempotency_key and not payload.idempotency_key:
        payload.idempotency_key = idempotency_key
    svc = ClaimsEndorsementService(db)
    data, is_new = await svc.intimate_claim(current_user, payload)
    if not is_new:
        response.status_code = status.HTTP_200_OK
    return APIResponse(
        success=True,
        message="Claim intimated successfully" if is_new else "Idempotent claim replay returned",
        data=data,
    )


@claims_router.get(
    "",
    response_model=APIResponse[ClaimListResponse],
)
async def list_claims_endpoint(
    transaction_id: Optional[int] = Query(default=None),
    policy_no: Optional[str] = Query(default=None),
    claim_status: Optional[str] = Query(default=None),
    claim_type: Optional[str] = Query(default=None),
    branch_id: Optional[int] = Query(default=None),
    agent_id: Optional[int] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*CLAIM_READ_ROLES)),
) -> APIResponse[ClaimListResponse]:
    svc = ClaimsEndorsementService(db)
    data = await svc.list_claims(
        current_user,
        transaction_id=transaction_id,
        policy_no=policy_no,
        claim_status=claim_status,
        claim_type=claim_type,
        branch_id=branch_id,
        agent_id=agent_id,
        limit=limit,
        offset=offset,
    )
    return APIResponse(success=True, message="Claims retrieved", data=data)


@claims_router.get(
    "/{claim_id}",
    response_model=APIResponse[ClaimResponse],
)
async def get_claim_endpoint(
    claim_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*CLAIM_READ_ROLES)),
) -> APIResponse[ClaimResponse]:
    svc = ClaimsEndorsementService(db)
    data = await svc.get_claim(current_user, claim_id)
    return APIResponse(success=True, message="Claim retrieved", data=data)


@claims_router.post(
    "/{claim_id}/register",
    response_model=APIResponse[ClaimResponse],
)
async def register_claim_endpoint(
    claim_id: int,
    payload: ClaimRegisterRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*CLAIM_UPDATE_ROLES)),
) -> APIResponse[ClaimResponse]:
    svc = ClaimsEndorsementService(db)
    data = await svc.register_claim(current_user, claim_id, payload)
    return APIResponse(success=True, message="Claim registered", data=data)


@claims_router.post(
    "/{claim_id}/survey",
    response_model=APIResponse[ClaimResponse],
)
async def update_survey_endpoint(
    claim_id: int,
    payload: ClaimSurveyUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*CLAIM_UPDATE_ROLES)),
) -> APIResponse[ClaimResponse]:
    svc = ClaimsEndorsementService(db)
    data = await svc.update_survey(current_user, claim_id, payload)
    return APIResponse(success=True, message="Surveyor assigned and survey updated", data=data)


@claims_router.post(
    "/{claim_id}/assess",
    response_model=APIResponse[ClaimResponse],
)
async def assess_claim_endpoint(
    claim_id: int,
    payload: ClaimAssessmentRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*CLAIM_UPDATE_ROLES)),
) -> APIResponse[ClaimResponse]:
    svc = ClaimsEndorsementService(db)
    data = await svc.assess_claim(current_user, claim_id, payload)
    return APIResponse(success=True, message="Claim assessed", data=data)


@claims_router.post(
    "/{claim_id}/approve",
    response_model=APIResponse[ClaimResponse],
)
async def approve_claim_endpoint(
    claim_id: int,
    payload: ClaimApprovalRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*CLAIM_APPROVE_SETTLE_ROLES)),
) -> APIResponse[ClaimResponse]:
    svc = ClaimsEndorsementService(db)
    data = await svc.approve_claim(current_user, claim_id, payload)
    return APIResponse(success=True, message="Claim approved", data=data)


@claims_router.post(
    "/{claim_id}/settle",
    response_model=APIResponse[ClaimResponse],
)
async def settle_claim_endpoint(
    claim_id: int,
    payload: ClaimSettlementRequest,
    idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*CLAIM_APPROVE_SETTLE_ROLES)),
) -> APIResponse[ClaimResponse]:
    if idempotency_key and not payload.idempotency_key:
        payload.idempotency_key = idempotency_key
    svc = ClaimsEndorsementService(db)
    data = await svc.settle_claim(current_user, claim_id, payload)
    return APIResponse(success=True, message="Claim settled", data=data)


@claims_router.post(
    "/{claim_id}/reverse-settlement",
    response_model=APIResponse[ClaimResponse],
)
async def reverse_claim_settlement_endpoint(
    claim_id: int,
    payload: ClaimActionRemarksRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*CLAIM_APPROVE_SETTLE_ROLES)),
) -> APIResponse[ClaimResponse]:
    svc = ClaimsEndorsementService(db)
    data = await svc.reverse_claim_settlement(current_user, claim_id, payload)
    return APIResponse(success=True, message="Claim settlement reversed", data=data)


@claims_router.post(
    "/{claim_id}/close",
    response_model=APIResponse[ClaimResponse],
)
async def close_claim_endpoint(
    claim_id: int,
    payload: ClaimActionRemarksRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*CLAIM_APPROVE_SETTLE_ROLES)),
) -> APIResponse[ClaimResponse]:
    svc = ClaimsEndorsementService(db)
    data = await svc.close_claim(current_user, claim_id, payload)
    return APIResponse(success=True, message="Claim closed", data=data)


@claims_router.post(
    "/{claim_id}/reject",
    response_model=APIResponse[ClaimResponse],
)
async def reject_claim_endpoint(
    claim_id: int,
    payload: ClaimRejectionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*CLAIM_APPROVE_SETTLE_ROLES)),
) -> APIResponse[ClaimResponse]:
    svc = ClaimsEndorsementService(db)
    data = await svc.reject_claim(current_user, claim_id, payload)
    return APIResponse(success=True, message="Claim rejected", data=data)


@claims_router.post(
    "/{claim_id}/cancel",
    response_model=APIResponse[ClaimResponse],
)
async def cancel_claim_endpoint(
    claim_id: int,
    payload: ClaimActionRemarksRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*CLAIM_UPDATE_ROLES)),
) -> APIResponse[ClaimResponse]:
    svc = ClaimsEndorsementService(db)
    data = await svc.cancel_claim(current_user, claim_id, payload)
    return APIResponse(success=True, message="Claim cancelled", data=data)


@claims_router.post(
    "/{claim_id}/reopen",
    response_model=APIResponse[ClaimResponse],
)
async def reopen_claim_endpoint(
    claim_id: int,
    payload: ClaimActionRemarksRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*CLAIM_APPROVE_SETTLE_ROLES)),
) -> APIResponse[ClaimResponse]:
    svc = ClaimsEndorsementService(db)
    data = await svc.reopen_claim(current_user, claim_id, payload)
    return APIResponse(success=True, message="Claim reopened", data=data)


@claims_router.post(
    "/{claim_id}/documents",
    response_model=APIResponse[ClaimDocumentResponse],
    status_code=status.HTTP_201_CREATED,
)
async def attach_claim_document_endpoint(
    claim_id: int,
    payload: ClaimDocumentCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*CLAIM_CREATE_ROLES)),
) -> APIResponse[ClaimDocumentResponse]:
    svc = ClaimsEndorsementService(db)
    data = await svc.attach_claim_document(current_user, claim_id, payload)
    return APIResponse(success=True, message="Claim document attached", data=data)


@claims_router.get(
    "/{claim_id}/documents",
    response_model=APIResponse[List[ClaimDocumentResponse]],
)
async def list_claim_documents_endpoint(
    claim_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*CLAIM_READ_ROLES)),
) -> APIResponse[List[ClaimDocumentResponse]]:
    svc = ClaimsEndorsementService(db)
    data = await svc.list_claim_documents(current_user, claim_id)
    return APIResponse(success=True, message="Claim documents retrieved", data=data)


# ===========================================================================
# 2. Endorsements Endpoints (`/api/v1/endorsements`)
# ===========================================================================

@endorsements_router.post(
    "/preview",
    response_model=APIResponse[EndorsementPreviewResponse],
)
async def preview_endorsement_endpoint(
    payload: EndorsementCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*ENDORSEMENT_CREATE_ROLES)),
) -> APIResponse[EndorsementPreviewResponse]:
    svc = ClaimsEndorsementService(db)
    data = await svc.preview_endorsement(current_user, payload)
    return APIResponse(success=True, message="Endorsement financial impact previewed", data=data)


@endorsements_router.post(
    "",
    response_model=APIResponse[EndorsementResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_endorsement_endpoint(
    payload: EndorsementCreateRequest,
    response: Response,
    idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*ENDORSEMENT_CREATE_ROLES)),
) -> APIResponse[EndorsementResponse]:
    if idempotency_key and not payload.idempotency_key:
        payload.idempotency_key = idempotency_key
    svc = ClaimsEndorsementService(db)
    data, is_new = await svc.create_endorsement(current_user, payload)
    if not is_new:
        response.status_code = status.HTTP_200_OK
    return APIResponse(
        success=True,
        message="Endorsement created" if is_new else "Idempotent endorsement replay returned",
        data=data,
    )


@endorsements_router.get(
    "",
    response_model=APIResponse[EndorsementListResponse],
)
async def list_endorsements_endpoint(
    transaction_id: Optional[int] = Query(default=None),
    endorsement_status: Optional[str] = Query(default=None),
    endorsement_type: Optional[str] = Query(default=None),
    branch_id: Optional[int] = Query(default=None),
    agent_id: Optional[int] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*ENDORSEMENT_READ_ROLES)),
) -> APIResponse[EndorsementListResponse]:
    svc = ClaimsEndorsementService(db)
    data = await svc.list_endorsements(
        current_user,
        transaction_id=transaction_id,
        endorsement_status=endorsement_status,
        endorsement_type=endorsement_type,
        branch_id=branch_id,
        agent_id=agent_id,
        limit=limit,
        offset=offset,
    )
    return APIResponse(success=True, message="Endorsements retrieved", data=data)


@endorsements_router.get(
    "/{endorsement_id}",
    response_model=APIResponse[EndorsementResponse],
)
async def get_endorsement_endpoint(
    endorsement_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*ENDORSEMENT_READ_ROLES)),
) -> APIResponse[EndorsementResponse]:
    svc = ClaimsEndorsementService(db)
    data = await svc.get_endorsement(current_user, endorsement_id)
    return APIResponse(success=True, message="Endorsement retrieved", data=data)


@endorsements_router.post(
    "/{endorsement_id}/submit",
    response_model=APIResponse[EndorsementResponse],
)
async def submit_endorsement_endpoint(
    endorsement_id: int,
    payload: EndorsementActionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*ENDORSEMENT_CREATE_ROLES)),
) -> APIResponse[EndorsementResponse]:
    svc = ClaimsEndorsementService(db)
    data = await svc.submit_endorsement(current_user, endorsement_id, payload)
    return APIResponse(success=True, message="Endorsement submitted", data=data)


@endorsements_router.post(
    "/{endorsement_id}/approve",
    response_model=APIResponse[EndorsementResponse],
)
async def approve_endorsement_endpoint(
    endorsement_id: int,
    payload: EndorsementActionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*ENDORSEMENT_APPROVE_APPLY_ROLES)),
) -> APIResponse[EndorsementResponse]:
    svc = ClaimsEndorsementService(db)
    data = await svc.approve_endorsement(current_user, endorsement_id, payload)
    return APIResponse(success=True, message="Endorsement approved", data=data)


@endorsements_router.post(
    "/{endorsement_id}/apply",
    response_model=APIResponse[EndorsementResponse],
)
async def apply_endorsement_endpoint(
    endorsement_id: int,
    payload: EndorsementApplyRequest,
    idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*ENDORSEMENT_APPROVE_APPLY_ROLES)),
) -> APIResponse[EndorsementResponse]:
    if idempotency_key and not payload.idempotency_key:
        payload.idempotency_key = idempotency_key
    svc = ClaimsEndorsementService(db)
    data = await svc.apply_endorsement(current_user, endorsement_id, payload)
    return APIResponse(success=True, message="Endorsement applied to policy", data=data)


@endorsements_router.post(
    "/{endorsement_id}/reject",
    response_model=APIResponse[EndorsementResponse],
)
async def reject_endorsement_endpoint(
    endorsement_id: int,
    payload: EndorsementRejectRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*ENDORSEMENT_APPROVE_APPLY_ROLES)),
) -> APIResponse[EndorsementResponse]:
    svc = ClaimsEndorsementService(db)
    data = await svc.reject_endorsement(current_user, endorsement_id, payload)
    return APIResponse(success=True, message="Endorsement rejected", data=data)


@endorsements_router.post(
    "/{endorsement_id}/cancel",
    response_model=APIResponse[EndorsementResponse],
)
async def cancel_endorsement_endpoint(
    endorsement_id: int,
    payload: EndorsementActionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*ENDORSEMENT_CREATE_ROLES)),
) -> APIResponse[EndorsementResponse]:
    svc = ClaimsEndorsementService(db)
    data = await svc.cancel_endorsement(current_user, endorsement_id, payload)
    return APIResponse(success=True, message="Endorsement cancelled", data=data)


@endorsements_router.post(
    "/{endorsement_id}/reverse",
    response_model=APIResponse[EndorsementResponse],
)
async def reverse_endorsement_endpoint(
    endorsement_id: int,
    payload: EndorsementActionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*ENDORSEMENT_APPROVE_APPLY_ROLES)),
) -> APIResponse[EndorsementResponse]:
    svc = ClaimsEndorsementService(db)
    data = await svc.reverse_endorsement(current_user, endorsement_id, payload)
    return APIResponse(success=True, message="Endorsement reversed", data=data)


# ===========================================================================
# 3. Refunds Endpoints (`/api/v1/refunds`)
# ===========================================================================

@refunds_router.get(
    "",
    response_model=APIResponse[EndorsementListResponse],
)
async def list_refunds_endpoint(
    transaction_id: Optional[int] = Query(default=None),
    refund_status: Optional[str] = Query(default=None),
    branch_id: Optional[int] = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*REFUND_APPROVE_WRITE_ROLES)),
) -> APIResponse[EndorsementListResponse]:
    svc = ClaimsEndorsementService(db)
    data = await svc.list_refunds(
        current_user,
        transaction_id=transaction_id,
        refund_status=refund_status,
        branch_id=branch_id,
    )
    return APIResponse(success=True, message="Refunds retrieved", data=data)


@refunds_router.post(
    "/{endorsement_id}/approve",
    response_model=APIResponse[EndorsementResponse],
)
async def approve_refund_endpoint(
    endorsement_id: int,
    payload: RefundActionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*REFUND_APPROVE_WRITE_ROLES)),
) -> APIResponse[EndorsementResponse]:
    svc = ClaimsEndorsementService(db)
    data = await svc.approve_refund(current_user, endorsement_id, payload)
    return APIResponse(success=True, message="Endorsement refund approved", data=data)


@refunds_router.post(
    "/{endorsement_id}/disburse",
    response_model=APIResponse[EndorsementResponse],
)
async def disburse_refund_endpoint(
    endorsement_id: int,
    payload: RefundDisburseRequest,
    idempotency_key: Optional[str] = Header(default=None, alias="Idempotency-Key"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*REFUND_APPROVE_WRITE_ROLES)),
) -> APIResponse[EndorsementResponse]:
    if idempotency_key and not payload.idempotency_key:
        payload.idempotency_key = idempotency_key
    svc = ClaimsEndorsementService(db)
    data = await svc.disburse_refund(current_user, endorsement_id, payload)
    return APIResponse(success=True, message="Endorsement refund disbursed", data=data)


@refunds_router.post(
    "/{endorsement_id}/reverse",
    response_model=APIResponse[EndorsementResponse],
)
async def reverse_refund_endpoint(
    endorsement_id: int,
    payload: RefundActionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*REFUND_APPROVE_WRITE_ROLES)),
) -> APIResponse[EndorsementResponse]:
    svc = ClaimsEndorsementService(db)
    data = await svc.reverse_refund(current_user, endorsement_id, payload)
    return APIResponse(success=True, message="Endorsement refund reversed", data=data)
