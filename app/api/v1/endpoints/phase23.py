"""
FastAPI Route Handlers for Phase 23 — Complete HR & Workforce Management System.
Organizations, Departments, Designations, Facilities, Holiday Calendar,
Leave Types, Employee Leave Application & Approvals Workflow, and Contact Persons.
"""
from typing import List, Optional
from datetime import date
from fastapi import APIRouter, Depends, Query, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.dependencies import get_current_user, require_roles
from app.models.user import User
from app.services.phase23_service import Phase23Service
from app.schemas.phase23 import (
    HROrganizationCreate,
    HROrganizationUpdate,
    HROrganizationResponse,
    HRDepartmentCreate,
    HRDepartmentUpdate,
    HRDepartmentResponse,
    HRDesignationCreate,
    HRDesignationUpdate,
    HRDesignationResponse,
    HRFacilityCreate,
    HRFacilityUpdate,
    HRFacilityResponse,
    HRHolidayCreate,
    HRHolidayUpdate,
    HRHolidayResponse,
    HRLeaveTypeCreate,
    HRLeaveTypeUpdate,
    HRLeaveTypeResponse,
    HRLeaveCreate,
    HRLeaveUpdate,
    HRLeaveStatusUpdateRequest,
    HRLeaveResponse,
    HRLeaveSummaryResponse,
    HRContactPersonCreate,
    HRContactPersonUpdate,
    HRContactPersonResponse,
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

hr_organizations_router = APIRouter(prefix="/hr/organizations", tags=["hr"])
hr_departments_router = APIRouter(prefix="/hr/departments", tags=["hr"])
hr_designations_router = APIRouter(prefix="/hr/designations", tags=["hr"])
hr_facilities_router = APIRouter(prefix="/hr/facilities", tags=["hr"])
hr_holidays_router = APIRouter(prefix="/hr/holidays", tags=["hr"])
hr_leave_types_router = APIRouter(prefix="/hr/leave-types", tags=["hr"])
hr_leaves_router = APIRouter(prefix="/hr/leaves", tags=["hr"])
hr_contacts_router = APIRouter(prefix="/hr/contacts", tags=["hr"])


# ============================================================================
# 1. HR ORGANIZATION ENDPOINTS
# ============================================================================

@hr_organizations_router.post(
    "",
    response_model=HROrganizationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new HR Organization entity",
)
async def create_organization(
    data: HROrganizationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*HR_ADMIN_ROLES)),
):
    service = Phase23Service(db)
    return await service.create_organization(data, current_username=current_user.UserName)


@hr_organizations_router.get(
    "",
    response_model=List[HROrganizationResponse],
    summary="List all HR Organizations",
)
async def list_organizations(
    query: Optional[str] = Query(None, description="Search by organization name"),
    is_active: Optional[int] = Query(1, description="1=Active, 0=Inactive"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*HR_ALL_ROLES)),
):
    service = Phase23Service(db)
    return await service.list_organizations(query=query, is_active=is_active, skip=skip, limit=limit)


@hr_organizations_router.get(
    "/{org_id}",
    response_model=HROrganizationResponse,
    summary="Get HR Organization by ID",
)
async def get_organization(
    org_id: int = Path(..., ge=1),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*HR_ALL_ROLES)),
):
    service = Phase23Service(db)
    return await service.get_organization(org_id)


@hr_organizations_router.put(
    "/{org_id}",
    response_model=HROrganizationResponse,
    summary="Update HR Organization",
)
async def update_organization(
    org_id: int = Path(..., ge=1),
    data: HROrganizationUpdate = ...,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*HR_ADMIN_ROLES)),
):
    service = Phase23Service(db)
    return await service.update_organization(org_id, data, current_username=current_user.UserName)


@hr_organizations_router.delete(
    "/{org_id}",
    summary="Deactivate or delete HR Organization",
)
async def delete_organization(
    org_id: int = Path(..., ge=1),
    soft: bool = Query(True, description="True for soft-delete (deactivate), False for hard delete"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*HR_ADMIN_ROLES)),
):
    service = Phase23Service(db)
    return await service.delete_organization(org_id, soft=soft)


# ============================================================================
# 2. HR DEPARTMENT ENDPOINTS
# ============================================================================

@hr_departments_router.post(
    "",
    response_model=HRDepartmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new HR Department",
)
async def create_department(
    data: HRDepartmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*HR_ADMIN_ROLES)),
):
    service = Phase23Service(db)
    return await service.create_department(data, current_username=current_user.UserName)


@hr_departments_router.get(
    "",
    response_model=List[HRDepartmentResponse],
    summary="List all HR Departments",
)
async def list_departments(
    org_id: Optional[int] = Query(None, description="Filter by Organization ID"),
    query: Optional[str] = Query(None, description="Search by department name"),
    is_active: Optional[int] = Query(1, description="1=Active, 0=Inactive"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*HR_ALL_ROLES)),
):
    service = Phase23Service(db)
    return await service.list_departments(
        org_id=org_id, query=query, is_active=is_active, skip=skip, limit=limit
    )


@hr_departments_router.get(
    "/organization/{org_id}",
    response_model=List[HRDepartmentResponse],
    summary="List HR Departments by Organization ID (Legacy OrgWise)",
)
async def list_departments_org_wise(
    org_id: int = Path(..., ge=1),
    is_active: Optional[int] = Query(1, description="1=Active, 0=Inactive"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*HR_ALL_ROLES)),
):
    service = Phase23Service(db)
    return await service.list_departments(org_id=org_id, is_active=is_active)


@hr_departments_router.get(
    "/{dept_id}",
    response_model=HRDepartmentResponse,
    summary="Get HR Department by ID",
)
async def get_department(
    dept_id: int = Path(..., ge=1),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*HR_ALL_ROLES)),
):
    service = Phase23Service(db)
    return await service.get_department(dept_id)


@hr_departments_router.put(
    "/{dept_id}",
    response_model=HRDepartmentResponse,
    summary="Update HR Department",
)
async def update_department(
    dept_id: int = Path(..., ge=1),
    data: HRDepartmentUpdate = ...,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*HR_ADMIN_ROLES)),
):
    service = Phase23Service(db)
    return await service.update_department(dept_id, data, current_username=current_user.UserName)


@hr_departments_router.delete(
    "/{dept_id}",
    summary="Deactivate or delete HR Department",
)
async def delete_department(
    dept_id: int = Path(..., ge=1),
    soft: bool = Query(True, description="True for soft-delete, False for hard delete"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*HR_ADMIN_ROLES)),
):
    service = Phase23Service(db)
    return await service.delete_department(dept_id, soft=soft)


# ============================================================================
# 3. HR DESIGNATION ENDPOINTS
# ============================================================================

@hr_designations_router.post(
    "",
    response_model=HRDesignationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new HR Designation",
)
async def create_designation(
    data: HRDesignationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*HR_ADMIN_ROLES)),
):
    service = Phase23Service(db)
    return await service.create_designation(data, current_username=current_user.UserName)


@hr_designations_router.get(
    "",
    response_model=List[HRDesignationResponse],
    summary="List all HR Designations",
)
async def list_designations(
    is_active: Optional[int] = Query(1, description="1=Active, 0=Inactive"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*HR_ALL_ROLES)),
):
    service = Phase23Service(db)
    return await service.list_designations(is_active=is_active, skip=skip, limit=limit)


@hr_designations_router.get(
    "/{desg_id}",
    response_model=HRDesignationResponse,
    summary="Get HR Designation by ID",
)
async def get_designation(
    desg_id: int = Path(..., ge=1),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*HR_ALL_ROLES)),
):
    service = Phase23Service(db)
    return await service.get_designation(desg_id)


@hr_designations_router.put(
    "/{desg_id}",
    response_model=HRDesignationResponse,
    summary="Update HR Designation",
)
async def update_designation(
    desg_id: int = Path(..., ge=1),
    data: HRDesignationUpdate = ...,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*HR_ADMIN_ROLES)),
):
    service = Phase23Service(db)
    return await service.update_designation(desg_id, data, current_username=current_user.UserName)


@hr_designations_router.delete(
    "/{desg_id}",
    summary="Deactivate HR Designation",
)
async def delete_designation(
    desg_id: int = Path(..., ge=1),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*HR_ADMIN_ROLES)),
):
    service = Phase23Service(db)
    return await service.delete_designation(desg_id)


# ============================================================================
# 4. HR FACILITY ENDPOINTS
# ============================================================================

@hr_facilities_router.post(
    "",
    response_model=HRFacilityResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new HR Facility / Perk",
)
async def create_facility(
    data: HRFacilityCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*HR_ADMIN_ROLES)),
):
    service = Phase23Service(db)
    return await service.create_facility(data, current_username=current_user.UserName)


@hr_facilities_router.get(
    "",
    response_model=List[HRFacilityResponse],
    summary="List all HR Facilities",
)
async def list_facilities(
    is_active: Optional[int] = Query(1, description="1=Active, 0=Inactive"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*HR_ALL_ROLES)),
):
    service = Phase23Service(db)
    return await service.list_facilities(is_active=is_active, skip=skip, limit=limit)


@hr_facilities_router.get(
    "/{faci_id}",
    response_model=HRFacilityResponse,
    summary="Get HR Facility by ID",
)
async def get_facility(
    faci_id: int = Path(..., ge=1),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*HR_ALL_ROLES)),
):
    service = Phase23Service(db)
    return await service.get_facility(faci_id)


@hr_facilities_router.put(
    "/{faci_id}",
    response_model=HRFacilityResponse,
    summary="Update HR Facility",
)
async def update_facility(
    faci_id: int = Path(..., ge=1),
    data: HRFacilityUpdate = ...,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*HR_ADMIN_ROLES)),
):
    service = Phase23Service(db)
    return await service.update_facility(faci_id, data, current_username=current_user.UserName)


@hr_facilities_router.delete(
    "/{faci_id}",
    summary="Deactivate HR Facility",
)
async def delete_facility(
    faci_id: int = Path(..., ge=1),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*HR_ADMIN_ROLES)),
):
    service = Phase23Service(db)
    return await service.delete_facility(faci_id)


# ============================================================================
# 5. HR HOLIDAY CALENDAR ENDPOINTS
# ============================================================================

@hr_holidays_router.post(
    "",
    response_model=HRHolidayResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new Holiday calendar entry",
)
async def create_holiday(
    data: HRHolidayCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*HR_ADMIN_ROLES)),
):
    service = Phase23Service(db)
    return await service.create_holiday(data, current_username=current_user.UserName)


@hr_holidays_router.get(
    "",
    response_model=List[HRHolidayResponse],
    summary="List Holidays with optional year, month, or employee filter",
)
async def list_holidays(
    year: Optional[int] = Query(None, description="Filter by year (e.g. 2026)"),
    month: Optional[int] = Query(None, ge=1, le=12, description="Filter by month (1-12)"),
    employee_id: Optional[int] = Query(None, description="Filter by employee ID (0 for general)"),
    is_active: Optional[int] = Query(1, description="1=Active, 0=Inactive"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*HR_ALL_ROLES)),
):
    service = Phase23Service(db)
    return await service.list_holidays(
        year=year,
        month=month,
        employee_id=employee_id,
        is_active=is_active,
        skip=skip,
        limit=limit,
    )


@hr_holidays_router.get(
    "/{holiday_id}",
    response_model=HRHolidayResponse,
    summary="Get Holiday by ID",
)
async def get_holiday(
    holiday_id: int = Path(..., ge=1),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*HR_ALL_ROLES)),
):
    service = Phase23Service(db)
    return await service.get_holiday(holiday_id)


@hr_holidays_router.put(
    "/{holiday_id}",
    response_model=HRHolidayResponse,
    summary="Update Holiday entry",
)
async def update_holiday(
    holiday_id: int = Path(..., ge=1),
    data: HRHolidayUpdate = ...,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*HR_ADMIN_ROLES)),
):
    service = Phase23Service(db)
    return await service.update_holiday(holiday_id, data, current_username=current_user.UserName)


@hr_holidays_router.delete(
    "/{holiday_id}",
    summary="Deactivate Holiday entry",
)
async def delete_holiday(
    holiday_id: int = Path(..., ge=1),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*HR_ADMIN_ROLES)),
):
    service = Phase23Service(db)
    return await service.delete_holiday(holiday_id)


# ============================================================================
# 6. HR LEAVE TYPE ENDPOINTS
# ============================================================================

@hr_leave_types_router.post(
    "",
    response_model=HRLeaveTypeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new HR Leave Type",
)
async def create_leave_type(
    data: HRLeaveTypeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*HR_ADMIN_ROLES)),
):
    service = Phase23Service(db)
    return await service.create_leave_type(data, current_username=current_user.UserName)


@hr_leave_types_router.get(
    "",
    response_model=List[HRLeaveTypeResponse],
    summary="List all HR Leave Types",
)
async def list_leave_types(
    is_active: Optional[int] = Query(1, description="1=Active, 0=Inactive"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*HR_ALL_ROLES)),
):
    service = Phase23Service(db)
    return await service.list_leave_types(is_active=is_active, skip=skip, limit=limit)


@hr_leave_types_router.get(
    "/{leave_type_id}",
    response_model=HRLeaveTypeResponse,
    summary="Get HR Leave Type by ID",
)
async def get_leave_type(
    leave_type_id: int = Path(..., ge=1),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*HR_ALL_ROLES)),
):
    service = Phase23Service(db)
    return await service.get_leave_type(leave_type_id)


@hr_leave_types_router.put(
    "/{leave_type_id}",
    response_model=HRLeaveTypeResponse,
    summary="Update HR Leave Type",
)
async def update_leave_type(
    leave_type_id: int = Path(..., ge=1),
    data: HRLeaveTypeUpdate = ...,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*HR_ADMIN_ROLES)),
):
    service = Phase23Service(db)
    return await service.update_leave_type(leave_type_id, data, current_username=current_user.UserName)


@hr_leave_types_router.delete(
    "/{leave_type_id}",
    summary="Deactivate HR Leave Type",
)
async def delete_leave_type(
    leave_type_id: int = Path(..., ge=1),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*HR_ADMIN_ROLES)),
):
    service = Phase23Service(db)
    return await service.delete_leave_type(leave_type_id)


# ============================================================================
# 7. HR LEAVE APPLICATIONS & APPROVALS ENDPOINTS
# ============================================================================

@hr_leaves_router.post(
    "",
    response_model=HRLeaveResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a new Employee Leave Application",
)
async def apply_leave(
    data: HRLeaveCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*HR_ALL_ROLES)),
):
    service = Phase23Service(db)
    return await service.apply_leave(data, current_username=current_user.UserName)


@hr_leaves_router.get(
    "/summary",
    response_model=HRLeaveSummaryResponse,
    summary="Get aggregate leave application summary metrics",
)
async def get_leave_summary(
    emp_id: Optional[int] = Query(None, description="Filter by Employee User ID"),
    org_id: Optional[int] = Query(None, description="Filter by Organization ID"),
    year: Optional[int] = Query(None, description="Filter by year"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*HR_ALL_ROLES)),
):
    service = Phase23Service(db)
    return await service.get_leave_summary(emp_id=emp_id, org_id=org_id, year=year)


@hr_leaves_router.get(
    "/manager-pending-count",
    response_model=int,
    summary="Get count of pending leave requests for a reporting manager (Legacy BLL_RptApplyLeaveReportingCount)",
)
async def get_manager_pending_count(
    reporting_id: int = Query(..., description="Manager User ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*HR_ADMIN_ROLES)),
):
    service = Phase23Service(db)
    return await service.get_manager_pending_count(reporting_id=reporting_id)


@hr_leaves_router.get(
    "",
    response_model=List[HRLeaveResponse],
    summary="List leave applications with extensive filters",
)
async def list_leaves(
    emp_id: Optional[int] = Query(None, description="Filter by Employee User ID"),
    reporting_id: Optional[int] = Query(None, description="Filter by Reporting Manager ID"),
    org_id: Optional[int] = Query(None, description="Filter by Organization ID"),
    dept_id: Optional[int] = Query(None, description="Filter by Department ID"),
    status_code: Optional[int] = Query(None, description="0=Pending, 1=Approved, 2=Rejected, 3=Cancelled"),
    from_date: Optional[date] = Query(None, description="Filter leave start on/after date"),
    to_date: Optional[date] = Query(None, description="Filter leave end on/before date"),
    month: Optional[int] = Query(None, ge=1, le=12, description="Filter leave month"),
    year: Optional[int] = Query(None, description="Filter leave year"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*HR_ALL_ROLES)),
):
    service = Phase23Service(db)
    return await service.list_leaves(
        emp_id=emp_id,
        reporting_id=reporting_id,
        org_id=org_id,
        dept_id=dept_id,
        status_code=status_code,
        from_date=from_date,
        to_date=to_date,
        month=month,
        year=year,
        skip=skip,
        limit=limit,
    )


@hr_leaves_router.get(
    "/{leave_id}",
    response_model=HRLeaveResponse,
    summary="Get Leave application by ID",
)
async def get_leave(
    leave_id: int = Path(..., ge=1),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*HR_ALL_ROLES)),
):
    service = Phase23Service(db)
    return await service.get_leave(leave_id)


@hr_leaves_router.put(
    "/{leave_id}",
    response_model=HRLeaveResponse,
    summary="Update details of a pending leave application",
)
async def update_leave(
    leave_id: int = Path(..., ge=1),
    data: HRLeaveUpdate = ...,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*HR_ALL_ROLES)),
):
    service = Phase23Service(db)
    return await service.update_leave(leave_id, data, current_username=current_user.UserName)


@hr_leaves_router.patch(
    "/{leave_id}/status",
    response_model=HRLeaveResponse,
    summary="Manager/HR Approval or Rejection of Leave application (1=Approved, 2=Rejected, 3=Cancelled)",
)
async def update_leave_status(
    leave_id: int = Path(..., ge=1),
    req: HRLeaveStatusUpdateRequest = ...,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*HR_ADMIN_ROLES)),
):
    service = Phase23Service(db)
    return await service.update_leave_status(leave_id, req, current_username=current_user.UserName)


# ============================================================================
# 8. HR CONTACT PERSON ENDPOINTS
# ============================================================================

@hr_contacts_router.post(
    "",
    response_model=HRContactPersonResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new HR Emergency/Reference Contact Person",
)
async def create_contact_person(
    data: HRContactPersonCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*HR_ADMIN_ROLES)),
):
    service = Phase23Service(db)
    return await service.create_contact_person(data, current_username=current_user.UserName)


@hr_contacts_router.get(
    "",
    response_model=List[HRContactPersonResponse],
    summary="List all HR Emergency/Reference Contact Persons",
)
async def list_contact_persons(
    query: Optional[str] = Query(None, description="Search by name or mobile number"),
    is_active: Optional[int] = Query(1, description="1=Active, 0=Inactive"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*HR_ALL_ROLES)),
):
    service = Phase23Service(db)
    return await service.list_contact_persons(
        query=query, is_active=is_active, skip=skip, limit=limit
    )


@hr_contacts_router.get(
    "/{contact_id}",
    response_model=HRContactPersonResponse,
    summary="Get Contact Person by ID",
)
async def get_contact_person(
    contact_id: int = Path(..., ge=1),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*HR_ALL_ROLES)),
):
    service = Phase23Service(db)
    return await service.get_contact_person(contact_id)


@hr_contacts_router.put(
    "/{contact_id}",
    response_model=HRContactPersonResponse,
    summary="Update Contact Person",
)
async def update_contact_person(
    contact_id: int = Path(..., ge=1),
    data: HRContactPersonUpdate = ...,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*HR_ADMIN_ROLES)),
):
    service = Phase23Service(db)
    return await service.update_contact_person(contact_id, data, current_username=current_user.UserName)


@hr_contacts_router.delete(
    "/{contact_id}",
    summary="Deactivate Contact Person",
)
async def delete_contact_person(
    contact_id: int = Path(..., ge=1),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(*HR_ADMIN_ROLES)),
):
    service = Phase23Service(db)
    return await service.delete_contact_person(contact_id)
