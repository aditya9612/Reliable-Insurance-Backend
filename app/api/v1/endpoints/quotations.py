"""
FastAPI v1 Endpoints for Phase 6 Quotation & Rating Engine.
Mounted at /api/v1/quotations.
"""
from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db, require_roles
from app.core.rbac import (
    QUOTATION_CALCULATE_ROLES,
    QUOTATION_COORDINATOR_ROLES,
    QUOTATION_READ_ROLES,
    QUOTATION_WRITE_ROLES,
)
from app.models.user import User
from app.schemas.quotation import (
    AssistedQuotationListResponse,
    AssistedQuotationRequestCreate,
    AssistedQuotationRequestResponse,
    AssistedQuotationRequestUpdate,
    GenerateInsurerQuotesRequest,
    MultiInsurerCompareRequest,
    MultiInsurerCompareResponse,
    PolicyPrefillResponse,
    PremiumBreakdownResponse,
    PremiumCalculationRequest,
    QuotationAttendRequest,
    QuotationStatusTransitionRequest,
    SelfQuotationCreateRequest,
    SelfQuotationListResponse,
    SelfQuotationResponse,
)
from app.services.quotation import QuotationService

router = APIRouter()


# ---------------------------------------------------------------------------
# 1. Stateless Deterministic Rating & Multi-Insurer Comparison
# ---------------------------------------------------------------------------


@router.post(
    "/calculate",
    response_model=PremiumBreakdownResponse,
    status_code=status.HTTP_200_OK,
    summary="Calculate motor insurance premium breakdown",
    description=(
        "Executes the 9-step deterministic motor rating sequence across all 9 vehicle categories "
        "(PVT, TwoWheeler, Public_GCV, Private_GCV, PublicGCV3W, PublicPCV3W, Misc-D, PassengerTaxi(PCV), School_Bus) "
        "using Decimal arithmetic exclusively."
    ),
)
async def calculate_premium(
    payload: PremiumCalculationRequest,
    current_user: User = Depends(require_roles(*QUOTATION_CALCULATE_ROLES)),
    session: AsyncSession = Depends(get_db),
) -> PremiumBreakdownResponse:
    service = QuotationService(session)
    return await service.calculate_premium(payload)


@router.post(
    "/compare",
    response_model=MultiInsurerCompareResponse,
    status_code=status.HTTP_200_OK,
    summary="Compare motor insurance premiums across eligible insurers",
    description=(
        "Computes side-by-side premium breakdowns across multiple eligible underwriting companies "
        "(sp_SelectInsuranceCompanyByVehicleType parity)."
    ),
)
async def compare_insurers(
    payload: MultiInsurerCompareRequest,
    current_user: User = Depends(require_roles(*QUOTATION_CALCULATE_ROLES)),
    session: AsyncSession = Depends(get_db),
) -> MultiInsurerCompareResponse:
    service = QuotationService(session)
    return await service.compare_insurers(payload)


# ---------------------------------------------------------------------------
# 2. Self-Quotation Persistence & Retrieval (tbl_app_quatationentry)
# ---------------------------------------------------------------------------


@router.post(
    "/self",
    response_model=SelfQuotationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create and persist a Self-Quotation",
    description=(
        "Calculates motor rating breakdown, generates an SRQ quotation code "
        "(Sp_GetQuotationCodeForSelfRequestedQuotation parity), and persists the quotation "
        "in tbl_app_quatationentry."
    ),
)
async def create_self_quotation(
    payload: SelfQuotationCreateRequest,
    current_user: User = Depends(require_roles(*QUOTATION_WRITE_ROLES)),
    session: AsyncSession = Depends(get_db),
) -> SelfQuotationResponse:
    service = QuotationService(session)
    return await service.create_self_quotation(payload, current_user)


@router.get(
    "/self",
    response_model=SelfQuotationListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Self-Quotations",
    description="Lists persisted Self-Quotations within caller's authorized Agent / Sales Executive / Global scope.",
)
async def list_self_quotations(
    from_date: Optional[date] = Query(None, description="Start date filter"),
    to_date: Optional[date] = Query(None, description="End date filter"),
    registration_no: Optional[str] = Query(None, description="Registration number filter"),
    limit: int = Query(50, ge=1, le=100, description="Page size (max 100)"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    current_user: User = Depends(require_roles(*QUOTATION_READ_ROLES)),
    session: AsyncSession = Depends(get_db),
) -> SelfQuotationListResponse:
    service = QuotationService(session)
    return await service.list_self_quotations(
        current_user=current_user,
        from_date=from_date,
        to_date=to_date,
        registration_no=registration_no,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/self/{quotation_id}",
    response_model=SelfQuotationResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Self-Quotation by ID",
    description="Retrieves a single Self-Quotation by QuatationId with ownership scope enforcement.",
)
async def get_self_quotation(
    quotation_id: int,
    current_user: User = Depends(require_roles(*QUOTATION_READ_ROLES)),
    session: AsyncSession = Depends(get_db),
) -> SelfQuotationResponse:
    service = QuotationService(session)
    return await service.get_self_quotation(quotation_id, current_user)


@router.get(
    "/self/{quotation_id}/policy-prefill",
    response_model=PolicyPrefillResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Policy Proposal prefill data from Self-Quotation",
    description="Returns Phase 7 policy proposal prefill fields (sp_getDataForPolicyEntry SELFQUO parity).",
)
async def get_self_quotation_policy_prefill(
    quotation_id: int,
    current_user: User = Depends(require_roles(*QUOTATION_READ_ROLES)),
    session: AsyncSession = Depends(get_db),
) -> PolicyPrefillResponse:
    service = QuotationService(session)
    return await service.get_policy_prefill(
        quotation_id=quotation_id,
        source_type="SELF_QUOTATION",
        current_user=current_user,
    )


# ---------------------------------------------------------------------------
# 3. Assisted Quotation Request Lifecycle (tbl_app_quotationrequest)
# ---------------------------------------------------------------------------


@router.post(
    "/requests",
    response_model=AssistedQuotationRequestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit an Assisted Quotation Request",
    description=(
        "Creates an Assisted Quotation Request in tbl_app_quotationrequest "
        "(InsertAppQuotationRequest parity) with server-resolved Agent/RM/Franchise ownership."
    ),
)
async def create_quotation_request(
    payload: AssistedQuotationRequestCreate,
    current_user: User = Depends(require_roles(*QUOTATION_WRITE_ROLES)),
    session: AsyncSession = Depends(get_db),
) -> AssistedQuotationRequestResponse:
    service = QuotationService(session)
    return await service.create_quotation_request(payload, current_user)


@router.get(
    "/requests",
    response_model=AssistedQuotationListResponse,
    status_code=status.HTTP_200_OK,
    summary="List Assisted Quotation Requests",
    description="Lists Assisted Quotation Requests within caller's authorized scope or Coordinator queue.",
)
async def list_quotation_requests(
    is_generated: Optional[int] = Query(None, ge=0, le=1, description="0=Pending, 1=Generated"),
    is_pending_revert: Optional[int] = Query(
        None, ge=0, le=2, description="0=Normal, 1=Reverted by Coordinator, 2=Resubmitted"
    ),
    vehicle_no: Optional[str] = Query(None, description="Partial vehicle registration number"),
    limit: int = Query(50, ge=1, le=100, description="Page size (max 100)"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    current_user: User = Depends(require_roles(*QUOTATION_READ_ROLES)),
    session: AsyncSession = Depends(get_db),
) -> AssistedQuotationListResponse:
    service = QuotationService(session)
    return await service.list_quotation_requests(
        current_user=current_user,
        is_generated=is_generated,
        is_pending_revert=is_pending_revert,
        vehicle_no=vehicle_no,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/requests/{quotation_id}",
    response_model=AssistedQuotationRequestResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Assisted Quotation Request by ID",
    description="Retrieves an Assisted Quotation Request along with attached insurer quote options and remark history.",
)
async def get_quotation_request(
    quotation_id: int,
    current_user: User = Depends(require_roles(*QUOTATION_READ_ROLES)),
    session: AsyncSession = Depends(get_db),
) -> AssistedQuotationRequestResponse:
    service = QuotationService(session)
    return await service.get_quotation_request(quotation_id, current_user)


@router.put(
    "/requests/{quotation_id}",
    response_model=AssistedQuotationRequestResponse,
    status_code=status.HTTP_200_OK,
    summary="Update or resubmit an Assisted Quotation Request",
    description=(
        "Updates an Assisted Quotation Request and transitions isPendingRevert = 2 "
        "(Sp_UpdateAppQuotReqNew parity)."
    ),
)
async def update_quotation_request(
    quotation_id: int,
    payload: AssistedQuotationRequestUpdate,
    current_user: User = Depends(require_roles(*QUOTATION_WRITE_ROLES)),
    session: AsyncSession = Depends(get_db),
) -> AssistedQuotationRequestResponse:
    service = QuotationService(session)
    return await service.update_quotation_request(quotation_id, payload, current_user)


@router.post(
    "/requests/{quotation_id}/attend",
    response_model=AssistedQuotationRequestResponse,
    status_code=status.HTTP_200_OK,
    summary="Claim or release an Assisted Quotation Request",
    description="Coordinator claims or releases an Assisted Quotation Request (sp_UpdateAppAttendQuotation1 parity).",
)
async def attend_quotation_request(
    quotation_id: int,
    payload: QuotationAttendRequest,
    current_user: User = Depends(require_roles(*QUOTATION_COORDINATOR_ROLES)),
    session: AsyncSession = Depends(get_db),
) -> AssistedQuotationRequestResponse:
    service = QuotationService(session)
    return await service.attend_quotation_request(quotation_id, payload, current_user)


@router.post(
    "/requests/{quotation_id}/status",
    response_model=AssistedQuotationRequestResponse,
    status_code=status.HTTP_200_OK,
    summary="Transition Assisted Quotation Request status",
    description=(
        "Executes Coordinator status transitions ('revert', 'resubmit', 'mark_read', 'cancel') "
        "and logs an audit remark in tbl_app_quotationremark."
    ),
)
async def transition_quotation_request_status(
    quotation_id: int,
    payload: QuotationStatusTransitionRequest,
    current_user: User = Depends(require_roles(*QUOTATION_COORDINATOR_ROLES)),
    session: AsyncSession = Depends(get_db),
) -> AssistedQuotationRequestResponse:
    service = QuotationService(session)
    return await service.transition_quotation_request_status(quotation_id, payload, current_user)


@router.post(
    "/requests/{quotation_id}/quotes",
    response_model=AssistedQuotationRequestResponse,
    status_code=status.HTTP_200_OK,
    summary="Attach insurer quote options and mark request Generated",
    description=(
        "Saves one or more insurer quotation options in tbl_insurancecompanyquotation "
        "(sp_insertInsuranceComponyQuotation) and marks tbl_app_quotationrequest as Generated "
        "(sp_UpdateAppQuotationRequest)."
    ),
)
async def generate_insurer_quotes(
    quotation_id: int,
    payload: GenerateInsurerQuotesRequest,
    current_user: User = Depends(require_roles(*QUOTATION_COORDINATOR_ROLES)),
    session: AsyncSession = Depends(get_db),
) -> AssistedQuotationRequestResponse:
    service = QuotationService(session)
    return await service.generate_insurer_quotes(quotation_id, payload, current_user)


@router.get(
    "/requests/{quotation_id}/policy-prefill",
    response_model=PolicyPrefillResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Policy Proposal prefill data from Assisted Quotation Request",
    description="Returns Phase 7 policy proposal prefill fields (Sp_GetQuotationDetailByQuotationCode parity).",
)
async def get_quotation_request_policy_prefill(
    quotation_id: int,
    insurance_company_id: Optional[int] = Query(None, ge=1, description="Selected insurer option"),
    current_user: User = Depends(require_roles(*QUOTATION_READ_ROLES)),
    session: AsyncSession = Depends(get_db),
) -> PolicyPrefillResponse:
    service = QuotationService(session)
    return await service.get_policy_prefill(
        quotation_id=quotation_id,
        source_type="ASSISTED_REQUEST",
        current_user=current_user,
        insurance_company_id=insurance_company_id,
    )


@router.delete(
    "/requests/{quotation_id}",
    status_code=status.HTTP_200_OK,
    summary="Soft-delete an Assisted Quotation Request",
    description="Soft-deletes a pending Assisted Quotation Request (sp_UpdateClearSelfQutation('GETData') parity).",
)
async def delete_quotation_request(
    quotation_id: int,
    current_user: User = Depends(require_roles(*QUOTATION_WRITE_ROLES)),
    session: AsyncSession = Depends(get_db),
) -> dict:
    service = QuotationService(session)
    return await service.delete_quotation_request(quotation_id, current_user)
