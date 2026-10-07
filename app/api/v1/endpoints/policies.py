"""
FastAPI v1 Endpoints for Phase 7 Policy Booking & Transaction Engine.
Mounted at /api/v1/policies.
"""
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db, require_roles
from app.core.rbac import (
    POLICY_APPROVAL_ROLES,
    POLICY_BOOKING_READ_ROLES,
    POLICY_BOOKING_WRITE_ROLES,
    POLICY_DELETE_ROLES,
    POLICY_PAYMENT_WRITE_ROLES,
    POLICY_PROPOSAL_WRITE_ROLES,
)
from app.models.user import User
from app.schemas.policy import (
    PaymentInstrumentCreateRequest,
    PolicyBookingCreateRequest,
    PolicyBookingListResponse,
    PolicyBookingResponse,
    PolicyBookingUpdateRequest,
    PolicyCancelRequest,
    PolicyCancelResponse,
    PolicyPreviewRequest,
    PolicyPreviewResponse,
    PolicyProposalApprovalRequest,
    PolicyProposalCreateRequest,
    PolicyProposalListResponse,
    PolicyProposalResponse,
)
from app.services.policy_booking import PolicyBookingService

router = APIRouter()


# ---------------------------------------------------------------------------
# 1. Financial Preview & Revalidation (Stateless / Quotation-Backed)
# ---------------------------------------------------------------------------


@router.post(
    "/preview",
    response_model=PolicyPreviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Preview and revalidate policy booking financials",
    description=(
        "Revalidates policy premium, NCB, OD discount, GST (18% or GCV split 12%+18%), "
        "multi-bucket commission, TDS, Cut & Pay / E-Wallet payment balance, and double-entry "
        "accounting ledger entries (AccTransId = 1, 2, 3) without writing to the database."
    ),
)
async def preview_policy(
    payload: PolicyPreviewRequest,
    current_user: User = Depends(require_roles(*POLICY_PROPOSAL_WRITE_ROLES)),
    session: AsyncSession = Depends(get_db),
) -> PolicyPreviewResponse:
    service = PolicyBookingService(session)
    return await service.preview_policy(payload, current_user)


# ---------------------------------------------------------------------------
# 2. Staged Mobile / Partner Policy Proposal Intake (tbl_transactionappnew)
# ---------------------------------------------------------------------------


@router.post(
    "/proposals",
    response_model=PolicyProposalResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a staged policy proposal",
    description=(
        "Creates a staged policy proposal in tbl_transactionappnew "
        "(Sp_InsertAppTransctiondetailsNew8 parity) with server-resolved principal ownership."
    ),
)
async def create_proposal(
    payload: PolicyProposalCreateRequest,
    current_user: User = Depends(require_roles(*POLICY_PROPOSAL_WRITE_ROLES)),
    session: AsyncSession = Depends(get_db),
) -> PolicyProposalResponse:
    service = PolicyBookingService(session)
    return await service.create_proposal(payload, current_user)


@router.get(
    "/proposals",
    response_model=PolicyProposalListResponse,
    status_code=status.HTTP_200_OK,
    summary="List staged policy proposals",
    description="Lists staged policy proposals in tbl_transactionappnew within the caller's authorized scope.",
)
async def list_proposals(
    quotation_code: Optional[str] = Query(None, description="Filter by QuatationCode"),
    registration_no: Optional[str] = Query(None, description="Filter by RegistrationNo"),
    is_submit: Optional[int] = Query(None, description="Filter by IsSubmit (0 or 1)"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_roles(*POLICY_BOOKING_READ_ROLES)),
    session: AsyncSession = Depends(get_db),
) -> PolicyProposalListResponse:
    service = PolicyBookingService(session)
    return await service.list_proposals(
        current_user=current_user,
        quotation_code=quotation_code,
        registration_no=registration_no,
        is_submit=is_submit,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/proposals/{trans_id}",
    response_model=PolicyProposalResponse,
    status_code=status.HTTP_200_OK,
    summary="Get staged policy proposal by TransId",
)
async def get_proposal(
    trans_id: int,
    current_user: User = Depends(require_roles(*POLICY_BOOKING_READ_ROLES)),
    session: AsyncSession = Depends(get_db),
) -> PolicyProposalResponse:
    service = PolicyBookingService(session)
    return await service.get_proposal(trans_id, current_user)


@router.post(
    "/proposals/{trans_id}/approve",
    response_model=PolicyProposalResponse,
    status_code=status.HTTP_200_OK,
    summary="Approve or reject a staged policy proposal at Cashier / Accountant / Owner gate",
    description=(
        "Executes Cashier (IsChashierApprove), Accountant (IsAccountApproval), or Owner "
        "(IsOwnerApprove) approval transitions on tbl_transactionappnew."
    ),
)
async def approve_proposal(
    trans_id: int,
    payload: PolicyProposalApprovalRequest,
    current_user: User = Depends(require_roles(*POLICY_APPROVAL_ROLES)),
    session: AsyncSession = Depends(get_db),
) -> PolicyProposalResponse:
    service = PolicyBookingService(session)
    return await service.approve_proposal(trans_id, payload, current_user)


# ---------------------------------------------------------------------------
# 3. Atomic Policy Booking & Transaction Lifecycle (tbl_transaction)
# ---------------------------------------------------------------------------


@router.post(
    "/book",
    response_model=PolicyBookingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Book a policy transaction atomically",
    description=(
        "Executes atomic policy booking across tbl_transaction (sp_InsertTransactionNew_2026 parity), "
        "concurrency-safe InwardNo allocation (sp_generateInwardNo parity), tbl_transactionpayment, "
        "commission tables (tbl_franchisecommission, tbl_cutnpaycommpayable, tbl_agentcommissionpayment), "
        "and double-entry accounting ledger rows in tbl_account (AccTransId = 1, 2, 3)."
    ),
)
async def book_policy(
    payload: PolicyBookingCreateRequest,
    current_user: User = Depends(require_roles(*POLICY_BOOKING_WRITE_ROLES)),
    session: AsyncSession = Depends(get_db),
) -> PolicyBookingResponse:
    service = PolicyBookingService(session)
    return await service.book_policy(payload, current_user)


@router.get(
    "",
    response_model=PolicyBookingListResponse,
    status_code=status.HTTP_200_OK,
    summary="List and search booked policy transactions",
    description="Lists booked policies in tbl_transaction with branch and principal ownership isolation.",
)
async def list_policies(
    customer_id: Optional[int] = Query(None, description="Filter by CustomerId"),
    cust_veh_id: Optional[int] = Query(None, description="Filter by CustVehId"),
    policy_no: Optional[str] = Query(None, description="Filter by PolicyNo"),
    inward_no: Optional[str] = Query(None, description="Filter by InwardNo"),
    quotation_code: Optional[str] = Query(None, description="Filter by QuatationCode"),
    t_status: Optional[str] = Query(None, description="Filter by TStatus"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_roles(*POLICY_BOOKING_READ_ROLES)),
    session: AsyncSession = Depends(get_db),
) -> PolicyBookingListResponse:
    service = PolicyBookingService(session)
    return await service.list_policies(
        current_user=current_user,
        customer_id=customer_id,
        cust_veh_id=cust_veh_id,
        policy_no=policy_no,
        inward_no=inward_no,
        quotation_code=quotation_code,
        t_status=t_status,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{transaction_id}",
    response_model=PolicyBookingResponse,
    status_code=status.HTTP_200_OK,
    summary="Get booked policy transaction by TransanctionId",
)
async def get_policy(
    transaction_id: int,
    current_user: User = Depends(require_roles(*POLICY_BOOKING_READ_ROLES)),
    session: AsyncSession = Depends(get_db),
) -> PolicyBookingResponse:
    service = PolicyBookingService(session)
    return await service.get_policy(transaction_id, current_user)


@router.put(
    "/{transaction_id}",
    response_model=PolicyBookingResponse,
    status_code=status.HTTP_200_OK,
    summary="Update policy underwriting metadata",
    description="Updates PolicyNo, dates, status, or remarks on tbl_transaction (sp_UpdateTransactionNew_2026 parity).",
)
async def update_policy(
    transaction_id: int,
    payload: PolicyBookingUpdateRequest,
    current_user: User = Depends(require_roles(*POLICY_BOOKING_WRITE_ROLES)),
    session: AsyncSession = Depends(get_db),
) -> PolicyBookingResponse:
    service = PolicyBookingService(session)
    return await service.update_policy(transaction_id, payload, current_user)


from app.schemas.payment import PaymentListResponse
from app.services.payment_engine import PaymentEngineService


@router.get(
    "/{transaction_id}/payments",
    response_model=PaymentListResponse,
    status_code=status.HTTP_200_OK,
    summary="List all payment instruments recorded against a policy",
    description="Returns all payment instruments (including active, bounced, and reversed) for a policy transaction.",
)
async def list_policy_payments(
    transaction_id: int,
    include_deleted: bool = Query(True, description="Include bounced/reversed payment instruments"),
    current_user: User = Depends(require_roles(*POLICY_BOOKING_READ_ROLES)),
    session: AsyncSession = Depends(get_db),
) -> PaymentListResponse:
    service = PaymentEngineService(session)
    return await service.list_payments(
        current_user=current_user,
        transaction_id=transaction_id,
        include_deleted=include_deleted,
        limit=100,
        offset=0,
    )


@router.post(
    "/{transaction_id}/payments",
    response_model=PolicyBookingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record an additional payment instrument against a policy",
    description=(
        "Appends a payment instrument to tbl_transactionpayment, updates PaidAmount and "
        "OutstandingAmount on tbl_transaction, and posts an AccTransId=2 entry in tbl_account."
    ),
)
async def record_payment(
    transaction_id: int,
    payload: PaymentInstrumentCreateRequest,
    current_user: User = Depends(require_roles(*POLICY_PAYMENT_WRITE_ROLES)),
    session: AsyncSession = Depends(get_db),
) -> PolicyBookingResponse:
    service = PolicyBookingService(session)
    return await service.record_payment(transaction_id, payload, current_user)


@router.post(
    "/{transaction_id}/cancel",
    response_model=PolicyCancelResponse,
    status_code=status.HTTP_200_OK,
    summary="Cancel / soft-delete a booked policy and reverse ledger entries",
    description=(
        "Atomically soft-deletes a booked policy in tbl_transaction (isdeleted=1, TStatus='Cancelled') "
        "and reverses associated payment, commission, and accounting ledger rows (sp_DeleteTransactionByTransId parity)."
    ),
)
async def cancel_policy(
    transaction_id: int,
    payload: PolicyCancelRequest,
    current_user: User = Depends(require_roles(*POLICY_DELETE_ROLES)),
    session: AsyncSession = Depends(get_db),
) -> PolicyCancelResponse:
    service = PolicyBookingService(session)
    return await service.cancel_policy(transaction_id, payload, current_user)

