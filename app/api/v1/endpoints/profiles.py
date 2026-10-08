"""
FastAPI Endpoints for Phase 15B — Employee, Agent & Franchise Profiles.
"""
from typing import Optional, List
from fastapi import APIRouter, Depends, Query, Path, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.dependencies import get_db, get_current_user
from app.models.user import User
from app.schemas.profile import (
    EmployeeCreate,
    EmployeeUpdate,
    EmployeeResponse,
    AgentCreate,
    AgentUpdate,
    AgentResponse,
    FranchiseCreate,
    FranchiseUpdate,
    FranchiseResponse,
    mask_employee_pii,
    mask_agent_pii,
    mask_franchise_pii,
)
from app.services.profile_service import ProfileService

employees_router = APIRouter()
agents_router = APIRouter()
franchises_router = APIRouter()

# Phase 15B Remediation: Privileged roles that have full access to raw unmasked PII
PRIVILEGED_PII_ROLES = frozenset({"OWNER", "ADMIN", "IT SUPPORT", "HR"})


def is_privileged_for_pii(user: User) -> bool:
    """Checks whether the user role is authorized to view unmasked PII."""
    role = (getattr(user, "role_name", None) or "").strip().upper()
    return role in PRIVILEGED_PII_ROLES



# ============================================================================
# EMPLOYEES ENDPOINTS
# ============================================================================

@employees_router.post(
    "",
    response_model=EmployeeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Internal Employee",
)
async def create_employee(
    payload: EmployeeCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> EmployeeResponse:
    service = ProfileService(session)
    emp = await service.create_employee(payload, current_user)
    resp = EmployeeResponse.model_validate(emp)
    return resp if is_privileged_for_pii(current_user) else mask_employee_pii(resp)


@employees_router.get(
    "",
    response_model=List[EmployeeResponse],
    status_code=status.HTTP_200_OK,
    summary="List Internal Employees",
)
async def list_employees(
    branch_id: Optional[int] = Query(None, description="Filter by Branch ID"),
    role_id: Optional[int] = Query(None, description="Filter by User Role ID"),
    search: Optional[str] = Query(None, description="Search by name or employee code"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> List[EmployeeResponse]:
    service = ProfileService(session)
    employees = await service.list_employees(
        current_user=current_user,
        branch_id=branch_id,
        role_id=role_id,
        search=search,
        offset=skip,
        limit=limit,
    )
    is_priv = is_privileged_for_pii(current_user)
    return [
        resp if is_priv else mask_employee_pii(resp)
        for resp in (EmployeeResponse.model_validate(e) for e in employees)
    ]


@employees_router.get(
    "/{id}",
    response_model=EmployeeResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Employee by ID",
)
async def get_employee(
    id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> EmployeeResponse:
    service = ProfileService(session)
    emp = await service.get_employee(id, current_user)
    resp = EmployeeResponse.model_validate(emp)
    return resp if is_privileged_for_pii(current_user) else mask_employee_pii(resp)


@employees_router.put(
    "/{id}",
    response_model=EmployeeResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Employee Profile",
)
async def update_employee(
    payload: EmployeeUpdate,
    id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> EmployeeResponse:
    service = ProfileService(session)
    emp = await service.update_employee(id, payload, current_user)
    resp = EmployeeResponse.model_validate(emp)
    return resp if is_privileged_for_pii(current_user) else mask_employee_pii(resp)


@employees_router.delete(
    "/{id}",
    status_code=status.HTTP_200_OK,
    summary="Deactivate Employee Profile",
)
async def delete_employee(
    id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    service = ProfileService(session)
    await service.delete_employee(id, current_user)
    return {"status": "SUCCESS", "message": f"Employee {id} deactivated."}


# ============================================================================
# AGENTS ENDPOINTS
# ============================================================================

@agents_router.post(
    "",
    response_model=AgentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register POSP Agent",
)
async def create_agent(
    payload: AgentCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> AgentResponse:
    service = ProfileService(session)
    agent = await service.create_agent(payload, current_user)
    resp = AgentResponse.model_validate(agent)
    return resp if is_privileged_for_pii(current_user) else mask_agent_pii(resp)


@agents_router.get(
    "",
    response_model=List[AgentResponse],
    status_code=status.HTTP_200_OK,
    summary="List POSP Agents",
)
async def list_agents(
    branch_id: Optional[int] = Query(None, description="Filter by Branch ID"),
    sales_exec_id: Optional[int] = Query(None, description="Filter by Sales Executive ID"),
    franchise_id: Optional[int] = Query(None, description="Filter by Franchise ID"),
    search: Optional[str] = Query(None, description="Search by name, nickname, or agent code"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> List[AgentResponse]:
    service = ProfileService(session)
    agents = await service.list_agents(
        current_user=current_user,
        branch_id=branch_id,
        sales_exec_id=sales_exec_id,
        franchise_id=franchise_id,
        search=search,
        offset=skip,
        limit=limit,
    )
    is_priv = is_privileged_for_pii(current_user)
    return [
        resp if is_priv else mask_agent_pii(resp)
        for resp in (AgentResponse.model_validate(a) for e, a in enumerate(agents))
    ]


@agents_router.get(
    "/{id}",
    response_model=AgentResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Agent by ID",
)
async def get_agent(
    id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> AgentResponse:
    service = ProfileService(session)
    agent = await service.get_agent(id, current_user)
    resp = AgentResponse.model_validate(agent)
    return resp if is_privileged_for_pii(current_user) else mask_agent_pii(resp)


@agents_router.put(
    "/{id}",
    response_model=AgentResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Agent Profile",
)
async def update_agent(
    payload: AgentUpdate,
    id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> AgentResponse:
    service = ProfileService(session)
    agent = await service.update_agent(id, payload, current_user)
    resp = AgentResponse.model_validate(agent)
    return resp if is_privileged_for_pii(current_user) else mask_agent_pii(resp)


@agents_router.delete(
    "/{id}",
    status_code=status.HTTP_200_OK,
    summary="Deactivate POSP Agent",
)
async def delete_agent(
    id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    service = ProfileService(session)
    await service.delete_agent(id, current_user)
    return {"status": "SUCCESS", "message": f"Agent {id} deactivated."}


# ============================================================================
# FRANCHISES ENDPOINTS
# ============================================================================

@franchises_router.post(
    "",
    response_model=FranchiseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register Franchise Partner",
)
async def create_franchise(
    payload: FranchiseCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> FranchiseResponse:
    service = ProfileService(session)
    fran = await service.create_franchise(payload, current_user)
    resp = FranchiseResponse.model_validate(fran)
    return resp if is_privileged_for_pii(current_user) else mask_franchise_pii(resp)


@franchises_router.get(
    "",
    response_model=List[FranchiseResponse],
    status_code=status.HTTP_200_OK,
    summary="List Franchise Partners",
)
async def list_franchises(
    branch_id: Optional[int] = Query(None, description="Filter by Branch ID"),
    parent_id: Optional[int] = Query(None, description="Filter by Parent Franchise ID"),
    search: Optional[str] = Query(None, description="Search by name or franchise code"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> List[FranchiseResponse]:
    service = ProfileService(session)
    franchises = await service.list_franchises(
        current_user=current_user,
        branch_id=branch_id,
        parent_id=parent_id,
        search=search,
        offset=skip,
        limit=limit,
    )
    is_priv = is_privileged_for_pii(current_user)
    return [
        resp if is_priv else mask_franchise_pii(resp)
        for resp in (FranchiseResponse.model_validate(f) for f in franchises)
    ]


@franchises_router.get(
    "/{id}",
    response_model=FranchiseResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Franchise by ID",
)
async def get_franchise(
    id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> FranchiseResponse:
    service = ProfileService(session)
    fran = await service.get_franchise(id, current_user)
    resp = FranchiseResponse.model_validate(fran)
    return resp if is_privileged_for_pii(current_user) else mask_franchise_pii(resp)


@franchises_router.put(
    "/{id}",
    response_model=FranchiseResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Franchise Profile",
)
async def update_franchise(
    payload: FranchiseUpdate,
    id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> FranchiseResponse:
    service = ProfileService(session)
    fran = await service.update_franchise(id, payload, current_user)
    resp = FranchiseResponse.model_validate(fran)
    return resp if is_privileged_for_pii(current_user) else mask_franchise_pii(resp)


@franchises_router.delete(
    "/{id}",
    status_code=status.HTTP_200_OK,
    summary="Deactivate Franchise Partner",
)
async def delete_franchise(
    id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> dict:
    service = ProfileService(session)
    await service.delete_franchise(id, current_user)
    return {"status": "SUCCESS", "message": f"Franchise {id} deactivated."}
