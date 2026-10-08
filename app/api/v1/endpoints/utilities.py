"""
FastAPI Endpoints for Phase 15B — IDV Override Queue, Health Family Member Grid, Bulk Policy MIS & Operational Batch Jobs.
"""
from typing import Optional, List
from datetime import date
from fastapi import APIRouter, Depends, Query, Path, UploadFile, File, Form, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.dependencies import get_db, get_current_user, require_roles
from app.models.user import User
from app.schemas.utility import (
    IDVRequestCreate,
    IDVRequestApprove,
    IDVRequestReject,
    IDVRequestResponse,
    HealthMemberCreate,
    HealthMemberUpdate,
    HealthMemberResponse,
    ImportPolicyMISResponse,
    ImportBatchSummary,
    ProcessBatchRequest,
    OverdueChequeLockResult,
    BirthdayGreetingDispatchResult,
    OperationalCleanupResult,
)
from app.services.utility_service import UtilityService

idv_router = APIRouter()
health_members_router = APIRouter()
imports_router = APIRouter()
batch_tasks_router = APIRouter()


# ============================================================================
# IDV OVERRIDE REQUEST ENDPOINTS
# ============================================================================

@idv_router.post(
    "",
    response_model=IDVRequestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit Special IDV Override Request",
)
async def create_idv_request(
    payload: IDVRequestCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> IDVRequestResponse:
    service = UtilityService(session)
    req = await service.create_idv_request(payload, current_user)
    return IDVRequestResponse.model_validate(req)


@idv_router.get(
    "",
    response_model=List[IDVRequestResponse],
    status_code=status.HTTP_200_OK,
    summary="List IDV Override Requests",
)
async def list_idv_requests(
    status_filter: Optional[str] = Query(None, alias="status", description="PENDING, APPROVED, REJECTED"),
    sales_ex_id: Optional[int] = Query(None, description="Filter by Sales Executive ID"),
    reg_no: Optional[str] = Query(None, description="Filter by Registration Number"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> List[IDVRequestResponse]:
    service = UtilityService(session)
    requests = await service.list_idv_requests(
        current_user=current_user,
        status_filter=status_filter,
        sales_ex_id=sales_ex_id,
        reg_no=reg_no,
        offset=skip,
        limit=limit,
    )
    return [IDVRequestResponse.model_validate(r) for r in requests]


@idv_router.get(
    "/{id}",
    response_model=IDVRequestResponse,
    status_code=status.HTTP_200_OK,
    summary="Get IDV Override Request by ID",
)
async def get_idv_request(
    id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> IDVRequestResponse:
    service = UtilityService(session)
    req = await service.get_idv_request(id, current_user)
    return IDVRequestResponse.model_validate(req)


@idv_router.put(
    "/{id}/approve",
    response_model=IDVRequestResponse,
    status_code=status.HTTP_200_OK,
    summary="Underwriter Approve IDV Override",
)
async def approve_idv_request(
    payload: IDVRequestApprove,
    id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> IDVRequestResponse:
    service = UtilityService(session)
    req = await service.approve_idv_request(id, payload, current_user)
    return IDVRequestResponse.model_validate(req)


@idv_router.put(
    "/{id}/reject",
    response_model=IDVRequestResponse,
    status_code=status.HTTP_200_OK,
    summary="Underwriter Reject IDV Override",
)
async def reject_idv_request(
    payload: IDVRequestReject,
    id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> IDVRequestResponse:
    service = UtilityService(session)
    req = await service.reject_idv_request(id, payload, current_user)
    return IDVRequestResponse.model_validate(req)


# ============================================================================
# HEALTH FAMILY MEMBER GRID ENDPOINTS
# ============================================================================

@health_members_router.post(
    "",
    response_model=HealthMemberResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add Health Policy Family Member",
)
async def create_health_member(
    payload: HealthMemberCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> HealthMemberResponse:
    service = UtilityService(session)
    member = await service.create_health_member(payload, current_user)
    return HealthMemberResponse.model_validate(member)


@health_members_router.get(
    "",
    response_model=List[HealthMemberResponse],
    status_code=status.HTTP_200_OK,
    summary="List Health Policy Family Members",
)
async def list_health_members(
    transaction_id: Optional[int] = Query(None, description="Filter by Policy Transaction ID"),
    customer_id: Optional[int] = Query(None, description="Filter by Customer ID"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> List[HealthMemberResponse]:
    service = UtilityService(session)
    members = await service.list_health_members(
        current_user=current_user,
        transaction_id=transaction_id,
        customer_id=customer_id,
        offset=skip,
        limit=limit,
    )
    return [HealthMemberResponse.model_validate(m) for m in members]


@health_members_router.get(
    "/{id}",
    response_model=HealthMemberResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Health Member by ID",
)
async def get_health_member(
    id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> HealthMemberResponse:
    service = UtilityService(session)
    member = await service.get_health_member(id, current_user)
    return HealthMemberResponse.model_validate(member)


@health_members_router.put(
    "/{id}",
    response_model=HealthMemberResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Health Member Details",
)
async def update_health_member(
    payload: HealthMemberUpdate,
    id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> HealthMemberResponse:
    service = UtilityService(session)
    member = await service.update_health_member(id, payload, current_user)
    return HealthMemberResponse.model_validate(member)


@health_members_router.delete(
    "/{id}",
    status_code=status.HTTP_200_OK,
    summary="Remove Health Member",
)
async def delete_health_member(
    id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    service = UtilityService(session)
    await service.delete_health_member(id, current_user)
    return {"status": "SUCCESS", "message": f"Health member {id} removed."}


# ============================================================================
# BULK POLICY MIS IMPORT ENDPOINTS
# ============================================================================

@imports_router.post(
    "/policy-mis/upload",
    response_model=ImportBatchSummary,
    status_code=status.HTTP_201_CREATED,
    summary="Upload & Stage Bulk Excel/CSV Policy MIS",
)
async def upload_policy_mis(
    file: UploadFile = File(..., description="Excel (.xlsx) or CSV file"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ImportBatchSummary:
    file_bytes = await file.read()
    service = UtilityService(session)
    return await service.parse_and_stage_policy_mis(
        file_bytes=file_bytes,
        filename=file.filename or "import.csv",
        current_user=current_user,
    )


@imports_router.get(
    "/policy-mis/records",
    response_model=List[ImportPolicyMISResponse],
    status_code=status.HTTP_200_OK,
    summary="List Staged Policy MIS Records",
)
async def list_imported_policies(
    batch_id: Optional[str] = Query(None, description="Filter by Staging Batch ID"),
    is_process: Optional[int] = Query(None, description="Filter by Processed status (0=Pending, 1=Processed)"),
    policy_no: Optional[str] = Query(None, description="Filter by Policy Number"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> List[ImportPolicyMISResponse]:
    service = UtilityService(session)
    records = await service.list_imported_policies(
        current_user=current_user,
        batch_id=batch_id,
        is_process=is_process,
        policy_no=policy_no,
        offset=skip,
        limit=limit,
    )
    return [ImportPolicyMISResponse.model_validate(r) for r in records]


@imports_router.post(
    "/policy-mis/process",
    status_code=status.HTTP_200_OK,
    summary="Mark Staged Policy MIS Batch Processed",
)
async def process_policy_mis_batch(
    payload: ProcessBatchRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    service = UtilityService(session)
    return await service.process_batch(
        batch_id=payload.batch_id,
        remark=payload.remark,
        current_user=current_user,
    )


# ============================================================================
# OPERATIONAL BATCH TASKS ENDPOINTS
# ============================================================================

@batch_tasks_router.post(
    "/overdue-cheque-lock/run",
    response_model=OverdueChequeLockResult,
    status_code=status.HTTP_200_OK,
    summary="Trigger Overdue Cheque Lock Audit (LBR-069)",
)
async def trigger_overdue_cheque_lock(
    threshold_days: int = Query(15, ge=1, le=90, description="Overdue threshold days (default 15)"),
    current_user: User = Depends(require_roles("OWNER", "ADMIN", "IT SUPPORT")),
    session: AsyncSession = Depends(get_db),
) -> OverdueChequeLockResult:
    service = UtilityService(session)
    return await service.enforce_overdue_cheque_locks(
        threshold_days=threshold_days, current_user=current_user
    )


@batch_tasks_router.post(
    "/birthday-greetings/dispatch",
    response_model=BirthdayGreetingDispatchResult,
    status_code=status.HTTP_200_OK,
    summary="Dispatch Customer & Partner Birthday Greetings",
)
async def trigger_birthday_greetings_dispatch(
    target_date: Optional[date] = Query(None, description="Optional target date (default today)"),
    current_user: User = Depends(require_roles("OWNER", "ADMIN", "IT SUPPORT")),
    session: AsyncSession = Depends(get_db),
) -> BirthdayGreetingDispatchResult:
    service = UtilityService(session)
    return await service.dispatch_birthday_greetings(
        target_date=target_date, current_user=current_user
    )


@batch_tasks_router.post(
    "/wallet-locks/cleanup",
    response_model=OperationalCleanupResult,
    status_code=status.HTTP_200_OK,
    summary="Cleanup Stale E-Wallet Reservations",
)
async def trigger_wallet_lock_cleanup(
    current_user: User = Depends(require_roles("OWNER", "ADMIN", "IT SUPPORT")),
    session: AsyncSession = Depends(get_db),
) -> OperationalCleanupResult:
    service = UtilityService(session)
    return await service.cleanup_stale_wallet_locks()


@batch_tasks_router.post(
    "/storage/ephemeral-cleanup",
    response_model=OperationalCleanupResult,
    status_code=status.HTTP_200_OK,
    summary="Cleanup Ephemeral Staging Files",
)
async def trigger_storage_cleanup(
    current_user: User = Depends(require_roles("OWNER", "ADMIN", "IT SUPPORT")),
    session: AsyncSession = Depends(get_db),
) -> OperationalCleanupResult:
    service = UtilityService(session)
    return await service.cleanup_ephemeral_storage()
