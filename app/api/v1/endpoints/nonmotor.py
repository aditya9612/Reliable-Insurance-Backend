"""
FastAPI Route Handlers for Phase 21 — Non-Motor Commercial Insurance Lines of Business & Operations.
Covers:
1. Commercial Product Classes & Products Catalog (/non-motor/products)
2. Business Types & Required Document Types (/non-motor/products/business-types, /non-motor/products/document-types)
3. Endorsement Hierarchies (/non-motor/endorsements)
4. Insurer Types & Commission Grids (/non-motor/commissions)
5. Policy Booking & Proposal Transactions (/non-motor/policies)
"""
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, Query, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.dependencies import get_current_user, require_roles
from app.models.user import User
from app.services.nonmotor_service import NonMotorService
from app.schemas.nonmotor import (
    NonMotorClassCreate,
    NonMotorClassUpdate,
    NonMotorClassResponse,
    NonMotorProductCreate,
    NonMotorProductUpdate,
    NonMotorProductResponse,
    NonMotorBusinessTypeCreate,
    NonMotorBusinessTypeResponse,
    NonMotorDocumentTypeCreate,
    NonMotorDocumentTypeResponse,
    NonMotorEndorsementTypeCreate,
    NonMotorEndorsementTypeResponse,
    NonMotorEndorsementSubTypeCreate,
    NonMotorEndorsementSubTypeResponse,
    NonMotorInsuranceTypeCreate,
    NonMotorInsuranceTypeResponse,
    NonMotorInsuranceSubTypeCreate,
    NonMotorInsuranceSubTypeResponse,
    NonMotorTypeOfInsuranceSubTypeCreate,
    NonMotorTypeOfInsuranceSubTypeResponse,
    NonMotorCommissionCreate,
    NonMotorCommissionResponse,
    NonMotorCommissionCalculationRequest,
    NonMotorCommissionCalculationResponse,
    NonMotorTransactionCreate,
    NonMotorTransactionUpdate,
    NonMotorTransactionResponse,
    NonMotorDashboardSummaryResponse,
)

ADMIN_ROLES = ("OWNER", "ADMIN", "IT SUPPORT", "MANAGER", "SUPERVISOR", "LOCATION HEAD")
COORDINATOR_ROLES = (
    "OWNER",
    "ADMIN",
    "IT SUPPORT",
    "OPERATOR",
    "OPERATOR HEAD",
    "QUOT CO-ORDINATOR",
    "INSP CO-ORDINATION",
    "MANAGER",
    "SUPERVISOR",
)
FINANCE_ROLES = ("OWNER", "ADMIN", "IT SUPPORT", "ACCOUNT", "ACCOUNT HEAD", "CASHIER", "MANAGER")

# Router definitions
nonmotor_products_router = APIRouter(prefix="/non-motor/products", tags=["Non-Motor - Products & Classes"])
nonmotor_endorsements_router = APIRouter(prefix="/non-motor/endorsements", tags=["Non-Motor - Endorsements"])
nonmotor_commissions_router = APIRouter(prefix="/non-motor/commissions", tags=["Non-Motor - Commissions & Hierarchies"])
nonmotor_transactions_router = APIRouter(prefix="/non-motor/policies", tags=["Non-Motor - Policy Booking & Transactions"])


# ============================================================================
# 1. NON-MOTOR PRODUCTS, CLASSES, BUSINESS TYPES & DOCUMENT TYPES
# ============================================================================

@nonmotor_products_router.get(
    "/classes",
    response_model=List[NonMotorClassResponse],
    summary="List Non-Motor Product Classes",
)
async def list_nonmotor_classes(
    is_active: Optional[int] = Query(None, ge=0, le=1),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = NonMotorService(session)
    return await service.list_classes(is_active=is_active)


@nonmotor_products_router.get(
    "/classes/{class_id}",
    response_model=NonMotorClassResponse,
    summary="Get Non-Motor Product Class by ID",
)
async def get_nonmotor_class(
    class_id: int = Path(..., ge=1),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = NonMotorService(session)
    return await service.get_class(class_id)


@nonmotor_products_router.post(
    "/classes",
    response_model=NonMotorClassResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Non-Motor Product Class",
)
async def create_nonmotor_class(
    payload: NonMotorClassCreate,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*ADMIN_ROLES)),
):
    service = NonMotorService(session)
    return await service.create_class(payload, username=current_user.UserName)


@nonmotor_products_router.put(
    "/classes/{class_id}",
    response_model=NonMotorClassResponse,
    summary="Update Non-Motor Product Class",
)
async def update_nonmotor_class(
    class_id: int = Path(..., ge=1),
    payload: NonMotorClassUpdate = ...,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*ADMIN_ROLES)),
):
    service = NonMotorService(session)
    return await service.update_class(class_id, payload, username=current_user.UserName)


@nonmotor_products_router.get(
    "/business-types",
    response_model=List[NonMotorBusinessTypeResponse],
    summary="List Non-Motor Business Types",
)
async def list_business_types(
    is_active: Optional[int] = Query(None, ge=0, le=1),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = NonMotorService(session)
    return await service.list_business_types(is_active=is_active)


@nonmotor_products_router.post(
    "/business-types",
    response_model=NonMotorBusinessTypeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Non-Motor Business Type",
)
async def create_business_type(
    payload: NonMotorBusinessTypeCreate,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*ADMIN_ROLES)),
):
    service = NonMotorService(session)
    return await service.create_business_type(payload, username=current_user.UserName)


@nonmotor_products_router.get(
    "/document-types",
    response_model=List[NonMotorDocumentTypeResponse],
    summary="List Non-Motor Required Document Types",
)
async def list_document_types(
    is_active: Optional[int] = Query(None, ge=0, le=1),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = NonMotorService(session)
    return await service.list_document_types(is_active=is_active)


@nonmotor_products_router.post(
    "/document-types",
    response_model=NonMotorDocumentTypeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Non-Motor Document Type",
)
async def create_document_type(
    payload: NonMotorDocumentTypeCreate,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*ADMIN_ROLES)),
):
    service = NonMotorService(session)
    return await service.create_document_type(payload, username=current_user.UserName)


@nonmotor_products_router.get(
    "",
    response_model=List[NonMotorProductResponse],
    summary="List Non-Motor Commercial Products",
)
async def list_nonmotor_products(
    class_id: Optional[int] = Query(None, ge=1),
    is_active: Optional[int] = Query(None, ge=0, le=1),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = NonMotorService(session)
    return await service.list_products(class_id=class_id, is_active=is_active)


@nonmotor_products_router.get(
    "/{product_id}",
    response_model=NonMotorProductResponse,
    summary="Get Non-Motor Product by ID",
)
async def get_nonmotor_product(
    product_id: int = Path(..., ge=1),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = NonMotorService(session)
    return await service.get_product(product_id)


@nonmotor_products_router.post(
    "",
    response_model=NonMotorProductResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Non-Motor Commercial Product",
)
async def create_nonmotor_product(
    payload: NonMotorProductCreate,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*ADMIN_ROLES)),
):
    service = NonMotorService(session)
    return await service.create_product(payload, username=current_user.UserName)


@nonmotor_products_router.put(
    "/{product_id}",
    response_model=NonMotorProductResponse,
    summary="Update Non-Motor Commercial Product",
)
async def update_nonmotor_product(
    product_id: int = Path(..., ge=1),
    payload: NonMotorProductUpdate = ...,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*ADMIN_ROLES)),
):
    service = NonMotorService(session)
    return await service.update_product(product_id, payload, username=current_user.UserName)


# ============================================================================
# 2. NON-MOTOR ENDORSEMENTS
# ============================================================================

@nonmotor_endorsements_router.get(
    "/types",
    response_model=List[NonMotorEndorsementTypeResponse],
    summary="List Non-Motor Endorsement Types",
)
async def list_endorsement_types(
    is_active: Optional[int] = Query(None, ge=0, le=1),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = NonMotorService(session)
    return await service.list_endorsement_types(is_active=is_active)


@nonmotor_endorsements_router.post(
    "/types",
    response_model=NonMotorEndorsementTypeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Non-Motor Endorsement Type",
)
async def create_endorsement_type(
    payload: NonMotorEndorsementTypeCreate,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*ADMIN_ROLES)),
):
    service = NonMotorService(session)
    return await service.create_endorsement_type(payload, username=current_user.UserName)


@nonmotor_endorsements_router.get(
    "/sub-types",
    response_model=List[NonMotorEndorsementSubTypeResponse],
    summary="List Non-Motor Endorsement Sub-Types",
)
async def list_endorsement_sub_types(
    endorsement_id: Optional[int] = Query(None, ge=1),
    is_active: Optional[int] = Query(None, ge=0, le=1),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = NonMotorService(session)
    return await service.list_endorsement_sub_types(endorsement_id=endorsement_id, is_active=is_active)


@nonmotor_endorsements_router.post(
    "/sub-types",
    response_model=NonMotorEndorsementSubTypeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Non-Motor Endorsement Sub-Type",
)
async def create_endorsement_sub_type(
    payload: NonMotorEndorsementSubTypeCreate,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*ADMIN_ROLES)),
):
    service = NonMotorService(session)
    return await service.create_endorsement_sub_type(payload, username=current_user.UserName)


# ============================================================================
# 3. NON-MOTOR COMMISSIONS & HIERARCHIES
# ============================================================================

@nonmotor_commissions_router.get(
    "/insurance-types",
    response_model=List[NonMotorInsuranceTypeResponse],
    summary="List Non-Motor Insurer Types",
)
async def list_insurance_types(
    company_id: Optional[int] = Query(None, ge=1),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = NonMotorService(session)
    return await service.list_insurance_types(company_id=company_id)


@nonmotor_commissions_router.post(
    "/insurance-types",
    response_model=NonMotorInsuranceTypeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Non-Motor Insurer Type",
)
async def create_insurance_type(
    payload: NonMotorInsuranceTypeCreate,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*ADMIN_ROLES)),
):
    service = NonMotorService(session)
    return await service.create_insurance_type(payload, username=current_user.UserName)


@nonmotor_commissions_router.get(
    "/insurance-sub-types",
    response_model=List[NonMotorInsuranceSubTypeResponse],
    summary="List Non-Motor Insurer Sub-Types",
)
async def list_insurance_sub_types(
    type_id: Optional[int] = Query(None, ge=1),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = NonMotorService(session)
    return await service.list_insurance_sub_types(type_id=type_id)


@nonmotor_commissions_router.post(
    "/insurance-sub-types",
    response_model=NonMotorInsuranceSubTypeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Non-Motor Insurer Sub-Type",
)
async def create_insurance_sub_type(
    payload: NonMotorInsuranceSubTypeCreate,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*ADMIN_ROLES)),
):
    service = NonMotorService(session)
    return await service.create_insurance_sub_type(payload, username=current_user.UserName)


@nonmotor_commissions_router.get(
    "/types-of-sub-type",
    response_model=List[NonMotorTypeOfInsuranceSubTypeResponse],
    summary="List Detailed Non-Motor Types of Sub-Type",
)
async def list_types_of_sub_type(
    sub_type_id: Optional[int] = Query(None, ge=1),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = NonMotorService(session)
    return await service.list_types_of_sub_type(sub_type_id=sub_type_id)


@nonmotor_commissions_router.post(
    "/types-of-sub-type",
    response_model=NonMotorTypeOfInsuranceSubTypeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Detailed Non-Motor Type of Sub-Type",
)
async def create_type_of_sub_type(
    payload: NonMotorTypeOfInsuranceSubTypeCreate,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*ADMIN_ROLES)),
):
    service = NonMotorService(session)
    return await service.create_type_of_sub_type(payload, username=current_user.UserName)


@nonmotor_commissions_router.get(
    "/grids",
    response_model=List[NonMotorCommissionResponse],
    summary="List Non-Motor Commission Grids",
)
async def list_commissions(
    company_id: Optional[int] = Query(None, ge=1),
    reference_id: Optional[int] = Query(None, ge=1),
    reference_type: Optional[str] = Query(None, description="Agent, Broker, Franchise, Self, IE"),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = NonMotorService(session)
    return await service.list_commissions(
        company_id=company_id, reference_id=reference_id, reference_type=reference_type
    )


@nonmotor_commissions_router.post(
    "/grids",
    response_model=NonMotorCommissionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Non-Motor Commission Grid Entry",
)
async def create_commission(
    payload: NonMotorCommissionCreate,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*FINANCE_ROLES)),
):
    service = NonMotorService(session)
    return await service.create_commission(payload, user_id=current_user.UserId)


@nonmotor_commissions_router.post(
    "/calculate",
    response_model=NonMotorCommissionCalculationResponse,
    summary="Calculate Non-Motor Commission & TDS",
)
async def calculate_commission(
    payload: NonMotorCommissionCalculationRequest,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = NonMotorService(session)
    return await service.calculate_commission(payload)


# ============================================================================
# 4. NON-MOTOR POLICY TRANSACTIONS
# ============================================================================

@nonmotor_transactions_router.get(
    "/summary",
    response_model=NonMotorDashboardSummaryResponse,
    summary="Non-Motor Policy Booking Dashboard Summary",
)
async def get_dashboard_summary(
    from_date: Optional[datetime] = Query(None),
    to_date: Optional[datetime] = Query(None),
    branch_id: Optional[int] = Query(None, ge=1),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = NonMotorService(session)
    eff_branch = branch_id if getattr(current_user, "role_name", "") in ADMIN_ROLES else current_user.BranchId
    return await service.get_dashboard_summary(from_date=from_date, to_date=to_date, branch_id=eff_branch)


@nonmotor_transactions_router.get(
    "",
    response_model=List[NonMotorTransactionResponse],
    summary="List Non-Motor Policy Transactions",
)
async def list_transactions(
    from_date: Optional[datetime] = Query(None),
    to_date: Optional[datetime] = Query(None),
    branch_id: Optional[int] = Query(None, ge=1),
    customer_id: Optional[int] = Query(None, ge=1),
    agent_id: Optional[int] = Query(None, ge=1),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = NonMotorService(session)
    eff_branch = branch_id if getattr(current_user, "role_name", "") in ADMIN_ROLES else current_user.BranchId
    return await service.list_transactions(
        from_date=from_date,
        to_date=to_date,
        branch_id=eff_branch,
        customer_id=customer_id,
        agent_id=agent_id,
        limit=limit,
        offset=offset,
    )


@nonmotor_transactions_router.get(
    "/{trans_id}",
    response_model=NonMotorTransactionResponse,
    summary="Get Non-Motor Transaction by ID",
)
async def get_transaction(
    trans_id: int = Path(..., ge=1),
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = NonMotorService(session)
    return await service.get_transaction(trans_id)


@nonmotor_transactions_router.post(
    "",
    response_model=NonMotorTransactionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Book Non-Motor Policy / Proposal Transaction",
)
async def create_transaction(
    payload: NonMotorTransactionCreate,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*COORDINATOR_ROLES)),
):
    service = NonMotorService(session)
    return await service.create_transaction(payload, username=current_user.UserName)


@nonmotor_transactions_router.put(
    "/{trans_id}",
    response_model=NonMotorTransactionResponse,
    summary="Update Non-Motor Transaction Status / Details",
)
async def update_transaction(
    trans_id: int = Path(..., ge=1),
    payload: NonMotorTransactionUpdate = ...,
    session: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*ADMIN_ROLES)),
):
    service = NonMotorService(session)
    return await service.update_transaction(trans_id, payload, username=current_user.UserName)
