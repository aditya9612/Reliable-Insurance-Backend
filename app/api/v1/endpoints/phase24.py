"""
FastAPI Route Handlers for Phase 24 — HR Workforce Lifecycle, Compensation Structure,
Employee Advances & Monthly Attendance Management.
"""
from typing import List, Optional
from datetime import date
from fastapi import APIRouter, Depends, Query, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.dependencies import get_current_user, require_roles
from app.models.user import User
from app.services.phase24_service import Phase24Service
from app.schemas.phase24 import (
    HRWorkingHistoryCreate,
    HRWorkingHistoryUpdate,
    HRWorkingHistoryResponse,
    HRFamilyDetailsCreate,
    HRFamilyDetailsUpdate,
    HRFamilyDetailsResponse,
    HRReferenceDetailsCreate,
    HRReferenceDetailsUpdate,
    HRReferenceDetailsResponse,
    HRWorkingTimeCreate,
    HRWorkingTimeResponse,
    HRSalaryStructureDefCreate,
    HRSalaryStructureDefUpdate,
    HRSalaryStructureDefResponse,
    HRAdvanceCreate,
    HRAdvanceUpdate,
    HRAdvanceRecoveryRequest,
    HRAdvanceResponse,
    HRMonthlyWorkingDetailsCreate,
    HRMonthlyWorkingDetailsResponse,
    HRMonthlyWorkingSummaryReport,
)

HR_ADMIN_ROLES = ("OWNER", "ADMIN", "IT SUPPORT", "MANAGER", "SUPERVISOR", "HR")
HR_ALL_ROLES = (
    "OWNER",
    "ADMIN",
    "IT SUPPORT",
    "MANAGER",
    "SUPERVISOR",
    "HR",
    "LOCATION HEAD",
    "SALES EXECUTIVE",
    "CLERK",
    "ACCOUNTANT",
    "ACCOUNTS HEAD",
    "TELECALLER",
    "FIELD AGENT",
)

hr_working_history_router = APIRouter(prefix="/hr/working-history", tags=["hr"])
hr_family_details_router = APIRouter(prefix="/hr/family-details", tags=["hr"])
hr_references_router = APIRouter(prefix="/hr/references", tags=["hr"])
hr_working_time_router = APIRouter(prefix="/hr/working-time", tags=["hr"])
hr_salary_structures_router = APIRouter(prefix="/hr/salary-structures", tags=["hr"])
hr_advances_router = APIRouter(prefix="/hr/advances", tags=["hr"])
hr_monthly_working_router = APIRouter(prefix="/hr/monthly-working", tags=["hr"])


# ============================================================================
# 1. HR WORKING HISTORY ENDPOINTS
# ============================================================================

@hr_working_history_router.post(
    "",
    response_model=HRWorkingHistoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record previous employer experience for an employee",
)
async def create_working_history(
    data: HRWorkingHistoryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*HR_ADMIN_ROLES)),
):
    service = Phase24Service(db)
    return await service.create_working_history(data, current_username=current_user.UserName)


@hr_working_history_router.get(
    "",
    response_model=List[HRWorkingHistoryResponse],
    summary="List employment history records",
)
async def list_working_history(
    employee_id: Optional[int] = Query(None, description="Filter by Employee ID"),
    is_active: Optional[int] = Query(1, description="1=Active, 0=Inactive"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*HR_ALL_ROLES)),
):
    service = Phase24Service(db)
    return await service.list_working_history(
        employee_id=employee_id, is_active=is_active, skip=skip, limit=limit
    )


@hr_working_history_router.get(
    "/{history_id}",
    response_model=HRWorkingHistoryResponse,
    summary="Get employment history record by ID",
)
async def get_working_history(
    history_id: int = Path(..., ge=1),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*HR_ALL_ROLES)),
):
    service = Phase24Service(db)
    return await service.get_working_history(history_id)


@hr_working_history_router.put(
    "/{history_id}",
    response_model=HRWorkingHistoryResponse,
    summary="Update employment history record",
)
async def update_working_history(
    history_id: int = Path(..., ge=1),
    data: HRWorkingHistoryUpdate = ...,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*HR_ADMIN_ROLES)),
):
    service = Phase24Service(db)
    return await service.update_working_history(history_id, data, current_username=current_user.UserName)


@hr_working_history_router.delete(
    "/{history_id}",
    summary="Deactivate employment history record",
)
async def delete_working_history(
    history_id: int = Path(..., ge=1),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*HR_ADMIN_ROLES)),
):
    service = Phase24Service(db)
    return await service.delete_working_history(history_id)


# ============================================================================
# 2. HR FAMILY DETAILS ENDPOINTS
# ============================================================================

@hr_family_details_router.post(
    "",
    response_model=HRFamilyDetailsResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add an employee family dependent",
)
async def create_family_detail(
    data: HRFamilyDetailsCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*HR_ALL_ROLES)),
):
    service = Phase24Service(db)
    return await service.create_family_detail(data, current_username=current_user.UserName)


@hr_family_details_router.get(
    "",
    response_model=List[HRFamilyDetailsResponse],
    summary="List employee family dependents",
)
async def list_family_details(
    employee_id: Optional[int] = Query(None, description="Filter by Employee ID"),
    is_active: Optional[int] = Query(1, description="1=Active, 0=Inactive"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*HR_ALL_ROLES)),
):
    service = Phase24Service(db)
    return await service.list_family_details(
        employee_id=employee_id, is_active=is_active, skip=skip, limit=limit
    )


@hr_family_details_router.get(
    "/{family_id}",
    response_model=HRFamilyDetailsResponse,
    summary="Get family dependent by ID",
)
async def get_family_detail(
    family_id: int = Path(..., ge=1),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*HR_ALL_ROLES)),
):
    service = Phase24Service(db)
    return await service.get_family_detail(family_id)


@hr_family_details_router.put(
    "/{family_id}",
    response_model=HRFamilyDetailsResponse,
    summary="Update family dependent",
)
async def update_family_detail(
    family_id: int = Path(..., ge=1),
    data: HRFamilyDetailsUpdate = ...,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*HR_ALL_ROLES)),
):
    service = Phase24Service(db)
    return await service.update_family_detail(family_id, data, current_username=current_user.UserName)


@hr_family_details_router.delete(
    "/{family_id}",
    summary="Deactivate family dependent",
)
async def delete_family_detail(
    family_id: int = Path(..., ge=1),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*HR_ADMIN_ROLES)),
):
    service = Phase24Service(db)
    return await service.delete_family_detail(family_id)


# ============================================================================
# 3. HR REFERENCE DETAILS ENDPOINTS
# ============================================================================

@hr_references_router.post(
    "",
    response_model=HRReferenceDetailsResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add an employee professional reference contact",
)
async def create_reference_detail(
    data: HRReferenceDetailsCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*HR_ADMIN_ROLES)),
):
    service = Phase24Service(db)
    return await service.create_reference_detail(data, current_username=current_user.UserName)


@hr_references_router.get(
    "",
    response_model=List[HRReferenceDetailsResponse],
    summary="List employee professional reference contacts",
)
async def list_reference_details(
    employee_id: Optional[int] = Query(None, description="Filter by Employee ID"),
    is_active: Optional[int] = Query(1, description="1=Active, 0=Inactive"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*HR_ALL_ROLES)),
):
    service = Phase24Service(db)
    return await service.list_reference_details(
        employee_id=employee_id, is_active=is_active, skip=skip, limit=limit
    )


@hr_references_router.get(
    "/{ref_id}",
    response_model=HRReferenceDetailsResponse,
    summary="Get professional reference contact by ID",
)
async def get_reference_detail(
    ref_id: int = Path(..., ge=1),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*HR_ALL_ROLES)),
):
    service = Phase24Service(db)
    return await service.get_reference_detail(ref_id)


@hr_references_router.put(
    "/{ref_id}",
    response_model=HRReferenceDetailsResponse,
    summary="Update professional reference contact",
)
async def update_reference_detail(
    ref_id: int = Path(..., ge=1),
    data: HRReferenceDetailsUpdate = ...,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*HR_ADMIN_ROLES)),
):
    service = Phase24Service(db)
    return await service.update_reference_detail(ref_id, data, current_username=current_user.UserName)


@hr_references_router.delete(
    "/{ref_id}",
    summary="Deactivate professional reference contact",
)
async def delete_reference_detail(
    ref_id: int = Path(..., ge=1),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*HR_ADMIN_ROLES)),
):
    service = Phase24Service(db)
    return await service.delete_reference_detail(ref_id)


# ============================================================================
# 4. HR WORKING TIME SCHEDULE ENDPOINTS
# ============================================================================

@hr_working_time_router.post(
    "",
    response_model=HRWorkingTimeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Assign or update employee working hours and shift schedule",
)
async def create_or_update_working_time(
    data: HRWorkingTimeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*HR_ADMIN_ROLES)),
):
    service = Phase24Service(db)
    return await service.create_or_update_working_time(data, current_username=current_user.UserName)


@hr_working_time_router.get(
    "/employee/{employee_id}",
    response_model=HRWorkingTimeResponse,
    summary="Get active working time schedule for an employee",
)
async def get_working_time_by_employee(
    employee_id: int = Path(..., ge=1),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*HR_ALL_ROLES)),
):
    service = Phase24Service(db)
    return await service.get_working_time_by_employee(employee_id)


@hr_working_time_router.get(
    "",
    response_model=List[HRWorkingTimeResponse],
    summary="List working time schedules",
)
async def list_working_times(
    department_id: Optional[int] = Query(None, description="Filter by Department ID"),
    is_active: Optional[int] = Query(1, description="1=Active, 0=Inactive"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*HR_ALL_ROLES)),
):
    service = Phase24Service(db)
    return await service.list_working_times(
        department_id=department_id, is_active=is_active, skip=skip, limit=limit
    )


@hr_working_time_router.get(
    "/{timeinfo_id}",
    response_model=HRWorkingTimeResponse,
    summary="Get working time schedule by ID",
)
async def get_working_time(
    timeinfo_id: int = Path(..., ge=1),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*HR_ALL_ROLES)),
):
    service = Phase24Service(db)
    return await service.get_working_time(timeinfo_id)


# ============================================================================
# 5. HR SALARY STRUCTURE DEFINITION ENDPOINTS
# ============================================================================

@hr_salary_structures_router.post(
    "",
    response_model=HRSalaryStructureDefResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a company salary structure template",
)
async def create_salary_structure(
    data: HRSalaryStructureDefCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*HR_ADMIN_ROLES)),
):
    service = Phase24Service(db)
    return await service.create_salary_structure(data, current_username=current_user.UserName)


@hr_salary_structures_router.get(
    "",
    response_model=List[HRSalaryStructureDefResponse],
    summary="List salary structure templates",
)
async def list_salary_structures(
    org_id: Optional[int] = Query(None, description="Filter by Organization ID"),
    is_active: Optional[int] = Query(1, description="1=Active, 0=Inactive"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*HR_ALL_ROLES)),
):
    service = Phase24Service(db)
    return await service.list_salary_structures(org_id=org_id, is_active=is_active, skip=skip, limit=limit)


@hr_salary_structures_router.get(
    "/{struct_id}",
    response_model=HRSalaryStructureDefResponse,
    summary="Get salary structure template by ID",
)
async def get_salary_structure(
    struct_id: int = Path(..., ge=1),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*HR_ALL_ROLES)),
):
    service = Phase24Service(db)
    return await service.get_salary_structure(struct_id)


@hr_salary_structures_router.put(
    "/{struct_id}",
    response_model=HRSalaryStructureDefResponse,
    summary="Update salary structure template",
)
async def update_salary_structure(
    struct_id: int = Path(..., ge=1),
    data: HRSalaryStructureDefUpdate = ...,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*HR_ADMIN_ROLES)),
):
    service = Phase24Service(db)
    return await service.update_salary_structure(struct_id, data, current_username=current_user.UserName)


@hr_salary_structures_router.delete(
    "/{struct_id}",
    summary="Deactivate salary structure template",
)
async def delete_salary_structure(
    struct_id: int = Path(..., ge=1),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*HR_ADMIN_ROLES)),
):
    service = Phase24Service(db)
    return await service.delete_salary_structure(struct_id)


# ============================================================================
# 6. HR ADVANCE & RECOVERY TRACKING ENDPOINTS
# ============================================================================

@hr_advances_router.post(
    "",
    response_model=HRAdvanceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record employee salary advance disbursement and compute installment schedule",
)
async def create_advance(
    data: HRAdvanceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*HR_ADMIN_ROLES)),
):
    service = Phase24Service(db)
    return await service.create_advance(data, current_username=current_user.UserName)


@hr_advances_router.get(
    "",
    response_model=List[HRAdvanceResponse],
    summary="List employee advance records",
)
async def list_advances(
    emp_id: Optional[int] = Query(None, description="Filter by Employee ID"),
    org_id: Optional[int] = Query(None, description="Filter by Organization ID"),
    is_active: Optional[int] = Query(1, description="1=Active, 0=Inactive"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*HR_ALL_ROLES)),
):
    service = Phase24Service(db)
    return await service.list_advances(emp_id=emp_id, org_id=org_id, is_active=is_active, skip=skip, limit=limit)


@hr_advances_router.get(
    "/{adv_id}",
    response_model=HRAdvanceResponse,
    summary="Get advance record by ID",
)
async def get_advance(
    adv_id: int = Path(..., ge=1),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*HR_ALL_ROLES)),
):
    service = Phase24Service(db)
    return await service.get_advance(adv_id)


@hr_advances_router.post(
    "/{adv_id}/recovery",
    response_model=HRAdvanceResponse,
    summary="Record installment or partial recovery against an active advance",
)
async def record_advance_recovery(
    adv_id: int = Path(..., ge=1),
    req: HRAdvanceRecoveryRequest = ...,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*HR_ADMIN_ROLES)),
):
    service = Phase24Service(db)
    return await service.record_advance_recovery(adv_id, req, current_username=current_user.UserName)


@hr_advances_router.put(
    "/{adv_id}",
    response_model=HRAdvanceResponse,
    summary="Update advance metadata",
)
async def update_advance(
    adv_id: int = Path(..., ge=1),
    data: HRAdvanceUpdate = ...,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*HR_ADMIN_ROLES)),
):
    service = Phase24Service(db)
    return await service.update_advance(adv_id, data, current_username=current_user.UserName)


@hr_advances_router.delete(
    "/{adv_id}",
    summary="Deactivate advance record",
)
async def delete_advance(
    adv_id: int = Path(..., ge=1),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*HR_ADMIN_ROLES)),
):
    service = Phase24Service(db)
    return await service.delete_advance(adv_id)


# ============================================================================
# 7. HR MONTHLY WORKING DETAILS & ATTENDANCE ENDPOINTS
# ============================================================================

@hr_monthly_working_router.post(
    "",
    response_model=HRMonthlyWorkingDetailsResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record or reconcile monthly employee attendance and compute working days",
)
async def create_or_update_monthly_working(
    data: HRMonthlyWorkingDetailsCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*HR_ADMIN_ROLES)),
):
    service = Phase24Service(db)
    return await service.create_or_update_monthly_working(data, current_username=current_user.UserName)


@hr_monthly_working_router.get(
    "/summary",
    response_model=HRMonthlyWorkingSummaryReport,
    summary="Aggregate monthly attendance, working days, and overtime totals across staff",
)
async def get_monthly_summary_report(
    org_id: Optional[int] = Query(None, description="Filter by Organization ID"),
    year: Optional[int] = Query(None, description="Filter by Year"),
    month: Optional[int] = Query(None, ge=1, le=12, description="Filter by Month"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*HR_ALL_ROLES)),
):
    service = Phase24Service(db)
    return await service.get_monthly_summary_report(org_id=org_id, year=year, month=month)


@hr_monthly_working_router.get(
    "",
    response_model=List[HRMonthlyWorkingDetailsResponse],
    summary="List monthly attendance and working day registers",
)
async def list_monthly_working(
    emp_id: Optional[int] = Query(None, description="Filter by Employee ID"),
    org_id: Optional[int] = Query(None, description="Filter by Organization ID"),
    dept_id: Optional[int] = Query(None, description="Filter by Department ID"),
    month: Optional[int] = Query(None, ge=1, le=12, description="Filter by Month"),
    year: Optional[int] = Query(None, description="Filter by Year"),
    is_active: Optional[int] = Query(1, description="1=Active, 0=Inactive"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*HR_ALL_ROLES)),
):
    service = Phase24Service(db)
    return await service.list_monthly_working(
        emp_id=emp_id,
        org_id=org_id,
        dept_id=dept_id,
        month=month,
        year=year,
        is_active=is_active,
        skip=skip,
        limit=limit,
    )


@hr_monthly_working_router.get(
    "/{working_id}",
    response_model=HRMonthlyWorkingDetailsResponse,
    summary="Get monthly working record by ID",
)
async def get_monthly_working(
    working_id: int = Path(..., ge=1),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*HR_ALL_ROLES)),
):
    service = Phase24Service(db)
    return await service.get_monthly_working(working_id)


@hr_monthly_working_router.delete(
    "/{working_id}",
    summary="Deactivate monthly working record",
)
async def delete_monthly_working(
    working_id: int = Path(..., ge=1),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*HR_ADMIN_ROLES)),
):
    service = Phase24Service(db)
    return await service.delete_monthly_working(working_id)
