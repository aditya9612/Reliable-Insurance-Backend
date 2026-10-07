from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db, require_roles
from app.core.rbac import CUSTOMER_VEHICLE_READ_ROLES, CUSTOMER_VEHICLE_WRITE_ROLES
from app.models.user import User
from app.schemas.customer import CustomerCreate, CustomerUpdate, CustomerResponse
from app.schemas.vehicle import VehicleCreate, VehicleUpdate, VehicleResponse
from app.services.customer import CustomerService
from app.services.vehicle import VehicleService

router = APIRouter()
vehicles_router = APIRouter()


@router.get(
    "",
    response_model=list[CustomerResponse],
    status_code=status.HTTP_200_OK,
    summary="Search and list customers",
    description="Searches active customers with bounded pagination and server-enforced branch scoping.",
)
async def search_customers(
    name: Optional[str] = Query(None, description="Partial customer name filter"),
    search: Optional[str] = Query(None, description="Alias for partial customer name filter"),
    mobile: Optional[str] = Query(None, description="Partial or exact mobile filter"),
    pan: Optional[str] = Query(None, description="Exact PAN number filter"),
    customer_code: Optional[str] = Query(None, description="Exact CustomerCode filter"),
    branch_id: Optional[int] = Query(None, description="BranchId filter (global roles only)"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(20, ge=1, le=100, description="Bounded page size (max 100)"),
    current_user: User = Depends(require_roles(*CUSTOMER_VEHICLE_READ_ROLES)),
    session: AsyncSession = Depends(get_db),
) -> list[CustomerResponse]:
    """Search active customers within caller's authorized branch scope."""
    effective_name = name if name is not None else search
    service = CustomerService(session)
    customers = await service.search_customers(
        current_user,
        name=effective_name,
        mobile=mobile,
        pan=pan,
        customer_code=customer_code,
        branch_id=branch_id,
        offset=offset,
        limit=limit,
    )
    return [CustomerResponse.model_validate(c) for c in customers]


@router.get(
    "/{customer_id}",
    response_model=CustomerResponse,
    status_code=status.HTTP_200_OK,
    summary="Get customer by ID",
    description="Retrieves a single active customer by CustomerId with branch jurisdiction enforcement.",
)
async def get_customer(
    customer_id: int,
    current_user: User = Depends(require_roles(*CUSTOMER_VEHICLE_READ_ROLES)),
    session: AsyncSession = Depends(get_db),
) -> CustomerResponse:
    """Get active customer details by CustomerId."""
    service = CustomerService(session)
    customer = await service.get_customer(customer_id, current_user)
    return CustomerResponse.model_validate(customer)


@router.post(
    "",
    response_model=CustomerResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new customer",
    description="Registers a new retail/corporate customer. Enforces legacy casing normalizations, branch scoping, and collision-free CustomerCode generation.",
)
async def create_customer(
    payload: CustomerCreate,
    current_user: User = Depends(require_roles(*CUSTOMER_VEHICLE_WRITE_ROLES)),
    session: AsyncSession = Depends(get_db),
) -> CustomerResponse:
    """Create a new policyholder customer."""
    service = CustomerService(session)
    customer = await service.create_customer(payload, current_user)
    return CustomerResponse.model_validate(customer)


@router.put(
    "/{customer_id}",
    response_model=CustomerResponse,
    status_code=status.HTTP_200_OK,
    summary="Update an existing customer",
    description="Updates customer details following the legacy sp_UpdateCustomer allowlist. Protects immutable columns and enforces branch access.",
)
async def update_customer(
    customer_id: int,
    payload: CustomerUpdate,
    current_user: User = Depends(require_roles(*CUSTOMER_VEHICLE_WRITE_ROLES)),
    session: AsyncSession = Depends(get_db),
) -> CustomerResponse:
    """Update customer details by CustomerId."""
    service = CustomerService(session)
    customer = await service.update_customer(customer_id, payload, current_user)
    return CustomerResponse.model_validate(customer)


@router.get(
    "/{customer_id}/vehicles",
    response_model=list[VehicleResponse],
    status_code=status.HTTP_200_OK,
    summary="List vehicles for a customer",
    description="Lists all active vehicle assets belonging to the specified customer within authorized branch scope.",
)
async def list_customer_vehicles(
    customer_id: int,
    offset: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(100, ge=1, le=100, description="Bounded page size (max 100)"),
    current_user: User = Depends(require_roles(*CUSTOMER_VEHICLE_READ_ROLES)),
    session: AsyncSession = Depends(get_db),
) -> list[VehicleResponse]:
    """List active vehicle assets for a customer."""
    service = VehicleService(session)
    vehicles = await service.list_customer_vehicles(
        customer_id, current_user, offset=offset, limit=limit
    )
    return [VehicleResponse.model_validate(v) for v in vehicles]


@router.post(
    "/{customer_id}/vehicles",
    response_model=VehicleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a vehicle asset for a customer",
    description="Registers a new vehicle under the specified customer. Enforces customer existence, master catalog integrity, and FY-scoped registration uniqueness.",
)
async def create_vehicle(
    customer_id: int,
    payload: VehicleCreate,
    current_user: User = Depends(require_roles(*CUSTOMER_VEHICLE_WRITE_ROLES)),
    session: AsyncSession = Depends(get_db),
) -> VehicleResponse:
    """Register a motor vehicle asset for a customer."""
    service = VehicleService(session)
    vehicle = await service.create_vehicle(customer_id, payload, current_user)
    return VehicleResponse.model_validate(vehicle)


@router.put(
    "/{customer_id}/vehicles/{vehicle_id}",
    response_model=VehicleResponse,
    status_code=status.HTTP_200_OK,
    summary="Update an existing vehicle asset",
    description="Updates vehicle technical specifications. Enforces customer ownership, master integrity, immutable field restrictions, and FY registration uniqueness.",
)
async def update_vehicle(
    customer_id: int,
    vehicle_id: int,
    payload: VehicleUpdate,
    current_user: User = Depends(require_roles(*CUSTOMER_VEHICLE_WRITE_ROLES)),
    session: AsyncSession = Depends(get_db),
) -> VehicleResponse:
    """Update vehicle specifications by CustomerId and CustVehId."""
    service = VehicleService(session)
    vehicle = await service.update_vehicle(customer_id, vehicle_id, payload, current_user)
    return VehicleResponse.model_validate(vehicle)


@vehicles_router.get(
    "",
    response_model=list[VehicleResponse],
    status_code=status.HTTP_200_OK,
    summary="Search and list vehicle assets",
    description=(
        "Searches active vehicles by registration number and/or financial year with branch isolation. "
        "Supports multi-row registration results across distinct FinancialYear records."
    ),
)
async def search_vehicles(
    registration_no: Optional[str] = Query(None, description="Vehicle registration number filter"),
    reg_no: Optional[str] = Query(None, description="Alias for registration_no filter"),
    financial_year: Optional[str] = Query(None, description="FinancialYear filter (e.g., 2025-2026)"),
    branch_id: Optional[int] = Query(None, description="BranchId filter (global roles only)"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(20, ge=1, le=100, description="Bounded page size (max 100)"),
    current_user: User = Depends(require_roles(*CUSTOMER_VEHICLE_READ_ROLES)),
    session: AsyncSession = Depends(get_db),
) -> list[VehicleResponse]:
    """Search active vehicle assets within caller's authorized branch scope."""
    effective_reg_no = registration_no if registration_no is not None else reg_no
    service = VehicleService(session)
    vehicles = await service.search_vehicles(
        current_user,
        reg_no=effective_reg_no,
        financial_year=financial_year,
        branch_id=branch_id,
        offset=offset,
        limit=limit,
    )
    return [VehicleResponse.model_validate(v) for v in vehicles]

