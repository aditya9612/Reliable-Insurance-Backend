"""
Service Layer for Phase 23 — Complete HR & Workforce Management System.
Handles Organizations, Departments, Designations, Facilities, Holiday Calendar,
Leave Types, Employee Leave Application & Approvals Workflow, and Contact Persons.
"""
from datetime import datetime, date
from decimal import Decimal
from typing import List, Optional, Dict, Any
from fastapi import HTTPException, status
from sqlalchemy import select, and_, or_, desc, func, extract
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.phase23_features import (
    HROrganization,
    HRDepartment,
    HRDesignation,
    HRFacility,
    HRHoliday,
    HRLeaveType,
    HRLeave,
    HRContactPerson,
)
from app.schemas.phase23 import (
    HROrganizationCreate,
    HROrganizationUpdate,
    HRDepartmentCreate,
    HRDepartmentUpdate,
    HRDesignationCreate,
    HRDesignationUpdate,
    HRFacilityCreate,
    HRFacilityUpdate,
    HRHolidayCreate,
    HRHolidayUpdate,
    HRLeaveTypeCreate,
    HRLeaveTypeUpdate,
    HRLeaveCreate,
    HRLeaveUpdate,
    HRLeaveStatusUpdateRequest,
    HRLeaveSummaryResponse,
    HRContactPersonCreate,
    HRContactPersonUpdate,
)


class Phase23Service:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ========================================================================
    # 1. HR ORGANIZATION OPERATIONS
    # ========================================================================

    async def create_organization(
        self, data: HROrganizationCreate, current_username: Optional[str] = None
    ) -> HROrganization:
        """Create a new HR Organization entity."""
        # Check duplicate by name
        stmt = select(HROrganization).where(
            func.lower(HROrganization.OrganizationName) == data.OrganizationName.lower().strip()
        )
        res = await self.db.execute(stmt)
        if res.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Organization with name '{data.OrganizationName}' already exists",
            )

        org = HROrganization(
            OrganizationName=data.OrganizationName.strip(),
            Address=data.Address,
            MobileNo=data.MobileNo,
            CreatedDate=datetime.utcnow(),
            CreateUser=current_username,
            IsActive=data.IsActive,
        )
        self.db.add(org)
        await self.db.commit()
        await self.db.refresh(org)
        return org

    async def get_organization(self, org_id: int) -> HROrganization:
        """Retrieve an organization by ID."""
        org = await self.db.get(HROrganization, org_id)
        if not org:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Organization with ID {org_id} not found",
            )
        return org

    async def list_organizations(
        self,
        query: Optional[str] = None,
        is_active: Optional[int] = 1,
        skip: int = 0,
        limit: int = 100,
    ) -> List[HROrganization]:
        """List organizations with optional name search and active status filter."""
        stmt = select(HROrganization)
        filters = []
        if is_active is not None:
            filters.append(HROrganization.IsActive == is_active)
        if query:
            filters.append(HROrganization.OrganizationName.ilike(f"%{query}%"))
        if filters:
            stmt = stmt.where(and_(*filters))
        stmt = stmt.order_by(HROrganization.OrganizationId.asc()).offset(skip).limit(limit)
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def update_organization(
        self, org_id: int, data: HROrganizationUpdate, current_username: Optional[str] = None
    ) -> HROrganization:
        """Update an organization."""
        org = await self.get_organization(org_id)
        update_data = data.model_dump(exclude_unset=True)

        if "OrganizationName" in update_data and update_data["OrganizationName"]:
            new_name = update_data["OrganizationName"].strip()
            dup_stmt = select(HROrganization).where(
                and_(
                    func.lower(HROrganization.OrganizationName) == new_name.lower(),
                    HROrganization.OrganizationId != org_id,
                )
            )
            res = await self.db.execute(dup_stmt)
            if res.scalars().first():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Organization with name '{new_name}' already exists",
                )
            org.OrganizationName = new_name

        for k, v in update_data.items():
            if k != "OrganizationName":
                setattr(org, k, v)

        org.UpdateDate = datetime.utcnow()
        org.UpdatedUser = current_username
        await self.db.commit()
        await self.db.refresh(org)
        return org

    async def delete_organization(self, org_id: int, soft: bool = True) -> Dict[str, Any]:
        """Delete or deactivate an organization."""
        org = await self.get_organization(org_id)
        if soft:
            org.IsActive = 0
            org.UpdateDate = datetime.utcnow()
            await self.db.commit()
            return {"message": f"Organization {org_id} deactivated successfully", "soft_deleted": True}
        else:
            await self.db.delete(org)
            await self.db.commit()
            return {"message": f"Organization {org_id} permanently deleted", "soft_deleted": False}

    # ========================================================================
    # 2. HR DEPARTMENT OPERATIONS
    # ========================================================================

    async def create_department(
        self, data: HRDepartmentCreate, current_username: Optional[str] = None
    ) -> HRDepartment:
        """Create a new HR Department within an organization."""
        # Ensure parent organization exists
        await self.get_organization(data.OrganizationId)

        # Ensure unique department name within organization
        stmt = select(HRDepartment).where(
            and_(
                HRDepartment.OrganizationId == data.OrganizationId,
                func.lower(HRDepartment.Dname) == data.Dname.lower().strip(),
            )
        )
        res = await self.db.execute(stmt)
        if res.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Department '{data.Dname}' already exists in organization {data.OrganizationId}",
            )

        dept = HRDepartment(
            OrganizationId=data.OrganizationId,
            Dname=data.Dname.strip(),
            Dlocation=data.Dlocation,
            CreatedDate=datetime.utcnow(),
            CreateUser=current_username,
            IsActive=data.IsActive,
        )
        self.db.add(dept)
        await self.db.commit()
        await self.db.refresh(dept)
        return dept

    async def get_department(self, dept_id: int) -> HRDepartment:
        """Retrieve a department by ID."""
        dept = await self.db.get(HRDepartment, dept_id)
        if not dept:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Department with ID {dept_id} not found",
            )
        return dept

    async def list_departments(
        self,
        org_id: Optional[int] = None,
        query: Optional[str] = None,
        is_active: Optional[int] = 1,
        skip: int = 0,
        limit: int = 100,
    ) -> List[HRDepartment]:
        """List departments optionally filtered by organization (legacy OrgWise)."""
        stmt = select(HRDepartment)
        filters = []
        if org_id is not None:
            filters.append(HRDepartment.OrganizationId == org_id)
        if is_active is not None:
            filters.append(HRDepartment.IsActive == is_active)
        if query:
            filters.append(HRDepartment.Dname.ilike(f"%{query}%"))
        if filters:
            stmt = stmt.where(and_(*filters))
        stmt = stmt.order_by(HRDepartment.DeparmentId.asc()).offset(skip).limit(limit)
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def update_department(
        self, dept_id: int, data: HRDepartmentUpdate, current_username: Optional[str] = None
    ) -> HRDepartment:
        """Update a department."""
        dept = await self.get_department(dept_id)
        update_data = data.model_dump(exclude_unset=True)

        if "OrganizationId" in update_data and update_data["OrganizationId"]:
            await self.get_organization(update_data["OrganizationId"])
            dept.OrganizationId = update_data["OrganizationId"]

        if "Dname" in update_data and update_data["Dname"]:
            new_name = update_data["Dname"].strip()
            org_id = dept.OrganizationId
            dup_stmt = select(HRDepartment).where(
                and_(
                    HRDepartment.OrganizationId == org_id,
                    func.lower(HRDepartment.Dname) == new_name.lower(),
                    HRDepartment.DeparmentId != dept_id,
                )
            )
            res = await self.db.execute(dup_stmt)
            if res.scalars().first():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Department '{new_name}' already exists in organization {org_id}",
                )
            dept.Dname = new_name

        for k, v in update_data.items():
            if k not in ("OrganizationId", "Dname"):
                setattr(dept, k, v)

        dept.UpdateDate = datetime.utcnow()
        dept.UpdatedUser = current_username
        await self.db.commit()
        await self.db.refresh(dept)
        return dept

    async def delete_department(self, dept_id: int, soft: bool = True) -> Dict[str, Any]:
        """Delete or deactivate a department."""
        dept = await self.get_department(dept_id)
        if soft:
            dept.IsActive = 0
            dept.UpdateDate = datetime.utcnow()
            await self.db.commit()
            return {"message": f"Department {dept_id} deactivated successfully", "soft_deleted": True}
        else:
            await self.db.delete(dept)
            await self.db.commit()
            return {"message": f"Department {dept_id} permanently deleted", "soft_deleted": False}

    # ========================================================================
    # 3. HR DESIGNATION OPERATIONS
    # ========================================================================

    async def create_designation(
        self, data: HRDesignationCreate, current_username: Optional[str] = None
    ) -> HRDesignation:
        """Create a new job designation."""
        stmt = select(HRDesignation).where(
            func.lower(HRDesignation.Designation) == data.Designation.lower().strip()
        )
        res = await self.db.execute(stmt)
        if res.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Designation '{data.Designation}' already exists",
            )

        desg = HRDesignation(
            Designation=data.Designation.strip(),
            CreatedDate=datetime.utcnow(),
            CreateUser=current_username,
            IsActive=data.IsActive,
        )
        self.db.add(desg)
        await self.db.commit()
        await self.db.refresh(desg)
        return desg

    async def get_designation(self, desg_id: int) -> HRDesignation:
        """Retrieve designation by ID."""
        desg = await self.db.get(HRDesignation, desg_id)
        if not desg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Designation with ID {desg_id} not found",
            )
        return desg

    async def list_designations(
        self, is_active: Optional[int] = 1, skip: int = 0, limit: int = 100
    ) -> List[HRDesignation]:
        """List designations."""
        stmt = select(HRDesignation)
        if is_active is not None:
            stmt = stmt.where(HRDesignation.IsActive == is_active)
        stmt = stmt.order_by(HRDesignation.DesignationId.asc()).offset(skip).limit(limit)
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def update_designation(
        self, desg_id: int, data: HRDesignationUpdate, current_username: Optional[str] = None
    ) -> HRDesignation:
        """Update designation."""
        desg = await self.get_designation(desg_id)
        update_data = data.model_dump(exclude_unset=True)

        if "Designation" in update_data and update_data["Designation"]:
            new_title = update_data["Designation"].strip()
            dup_stmt = select(HRDesignation).where(
                and_(
                    func.lower(HRDesignation.Designation) == new_title.lower(),
                    HRDesignation.DesignationId != desg_id,
                )
            )
            res = await self.db.execute(dup_stmt)
            if res.scalars().first():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Designation '{new_title}' already exists",
                )
            desg.Designation = new_title

        if "IsActive" in update_data and update_data["IsActive"] is not None:
            desg.IsActive = update_data["IsActive"]

        desg.UpdateDate = datetime.utcnow()
        desg.UpdatedUser = current_username
        await self.db.commit()
        await self.db.refresh(desg)
        return desg

    async def delete_designation(self, desg_id: int) -> Dict[str, Any]:
        """Deactivate designation."""
        desg = await self.get_designation(desg_id)
        desg.IsActive = 0
        desg.UpdateDate = datetime.utcnow()
        await self.db.commit()
        return {"message": f"Designation {desg_id} deactivated successfully"}

    # ========================================================================
    # 4. HR FACILITY OPERATIONS
    # ========================================================================

    async def create_facility(
        self, data: HRFacilityCreate, current_username: Optional[str] = None
    ) -> HRFacility:
        """Create a new HR Facility / Perk."""
        stmt = select(HRFacility).where(
            func.lower(HRFacility.Name) == data.Name.lower().strip()
        )
        res = await self.db.execute(stmt)
        if res.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Facility '{data.Name}' already exists",
            )

        faci = HRFacility(
            Name=data.Name.strip(),
            percentage=data.percentage,
            CreatedDate=datetime.utcnow(),
            CreateUser=current_username,
            IsActive=data.IsActive,
        )
        self.db.add(faci)
        await self.db.commit()
        await self.db.refresh(faci)
        return faci

    async def get_facility(self, faci_id: int) -> HRFacility:
        """Retrieve facility by ID."""
        faci = await self.db.get(HRFacility, faci_id)
        if not faci:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Facility with ID {faci_id} not found",
            )
        return faci

    async def list_facilities(
        self, is_active: Optional[int] = 1, skip: int = 0, limit: int = 100
    ) -> List[HRFacility]:
        """List facilities."""
        stmt = select(HRFacility)
        if is_active is not None:
            stmt = stmt.where(HRFacility.IsActive == is_active)
        stmt = stmt.order_by(HRFacility.FaciltiyId.asc()).offset(skip).limit(limit)
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def update_facility(
        self, faci_id: int, data: HRFacilityUpdate, current_username: Optional[str] = None
    ) -> HRFacility:
        """Update facility."""
        faci = await self.get_facility(faci_id)
        update_data = data.model_dump(exclude_unset=True)

        for k, v in update_data.items():
            setattr(faci, k, v)

        faci.UpdateDate = datetime.utcnow()
        faci.UpdatedUser = current_username
        await self.db.commit()
        await self.db.refresh(faci)
        return faci

    async def delete_facility(self, faci_id: int) -> Dict[str, Any]:
        """Deactivate facility."""
        faci = await self.get_facility(faci_id)
        faci.IsActive = 0
        faci.UpdateDate = datetime.utcnow()
        await self.db.commit()
        return {"message": f"Facility {faci_id} deactivated successfully"}

    # ========================================================================
    # 5. HR HOLIDAY CALENDAR OPERATIONS
    # ========================================================================

    async def create_holiday(
        self, data: HRHolidayCreate, current_username: Optional[str] = None
    ) -> HRHoliday:
        """Create a new holiday calendar entry."""
        # Check duplicate holiday on the same date for the target employee/all
        emp_id = data.EmployeeID or 0
        stmt = select(HRHoliday).where(
            and_(
                HRHoliday.HolidayDate == data.HolidayDate,
                HRHoliday.EmployeeID == emp_id,
                HRHoliday.IsActive == 1,
            )
        )
        res = await self.db.execute(stmt)
        if res.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Holiday already configured for date {data.HolidayDate}",
            )

        holiday = HRHoliday(
            EmployeeID=emp_id,
            HolidayDesc=data.HolidayDesc.strip(),
            HolidayDate=data.HolidayDate,
            CreatedDate=datetime.utcnow(),
            CreateUser=current_username,
            IsActive=data.IsActive,
        )
        self.db.add(holiday)
        await self.db.commit()
        await self.db.refresh(holiday)
        return holiday

    async def get_holiday(self, holiday_id: int) -> HRHoliday:
        """Retrieve holiday by ID."""
        holiday = await self.db.get(HRHoliday, holiday_id)
        if not holiday:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Holiday with ID {holiday_id} not found",
            )
        return holiday

    async def list_holidays(
        self,
        year: Optional[int] = None,
        month: Optional[int] = None,
        employee_id: Optional[int] = None,
        is_active: Optional[int] = 1,
        skip: int = 0,
        limit: int = 100,
    ) -> List[HRHoliday]:
        """List holidays with optional year, month, or employee filter."""
        stmt = select(HRHoliday)
        filters = []
        if is_active is not None:
            filters.append(HRHoliday.IsActive == is_active)
        if year is not None:
            filters.append(extract("year", HRHoliday.HolidayDate) == year)
        if month is not None:
            filters.append(extract("month", HRHoliday.HolidayDate) == month)
        if employee_id is not None:
            filters.append(or_(HRHoliday.EmployeeID == employee_id, HRHoliday.EmployeeID == 0))
        if filters:
            stmt = stmt.where(and_(*filters))
        stmt = stmt.order_by(HRHoliday.HolidayDate.asc()).offset(skip).limit(limit)
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def update_holiday(
        self, holiday_id: int, data: HRHolidayUpdate, current_username: Optional[str] = None
    ) -> HRHoliday:
        """Update holiday calendar entry."""
        holiday = await self.get_holiday(holiday_id)
        update_data = data.model_dump(exclude_unset=True)

        for k, v in update_data.items():
            setattr(holiday, k, v)

        holiday.UpdateDate = datetime.utcnow()
        holiday.UpdatedUser = current_username
        await self.db.commit()
        await self.db.refresh(holiday)
        return holiday

    async def delete_holiday(self, holiday_id: int) -> Dict[str, Any]:
        """Deactivate holiday entry."""
        holiday = await self.get_holiday(holiday_id)
        holiday.IsActive = 0
        holiday.UpdateDate = datetime.utcnow()
        await self.db.commit()
        return {"message": f"Holiday {holiday_id} deactivated successfully"}

    # ========================================================================
    # 6. HR LEAVE TYPE OPERATIONS
    # ========================================================================

    async def create_leave_type(
        self, data: HRLeaveTypeCreate, current_username: Optional[str] = None
    ) -> HRLeaveType:
        """Create a new leave type."""
        stmt = select(HRLeaveType).where(
            func.lower(HRLeaveType.LeaveType) == data.LeaveType.lower().strip()
        )
        res = await self.db.execute(stmt)
        if res.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Leave type '{data.LeaveType}' already exists",
            )

        lt = HRLeaveType(
            LeaveType=data.LeaveType.strip(),
            CreatedDate=datetime.utcnow(),
            CreateUser=current_username,
            IsActive=data.IsActive,
        )
        self.db.add(lt)
        await self.db.commit()
        await self.db.refresh(lt)
        return lt

    async def get_leave_type(self, leave_type_id: int) -> HRLeaveType:
        """Retrieve leave type by ID."""
        lt = await self.db.get(HRLeaveType, leave_type_id)
        if not lt:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Leave type with ID {leave_type_id} not found",
            )
        return lt

    async def list_leave_types(
        self, is_active: Optional[int] = 1, skip: int = 0, limit: int = 100
    ) -> List[HRLeaveType]:
        """List leave types."""
        stmt = select(HRLeaveType)
        if is_active is not None:
            stmt = stmt.where(HRLeaveType.IsActive == is_active)
        stmt = stmt.order_by(HRLeaveType.LeaveTypeId.asc()).offset(skip).limit(limit)
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def update_leave_type(
        self, leave_type_id: int, data: HRLeaveTypeUpdate, current_username: Optional[str] = None
    ) -> HRLeaveType:
        """Update leave type."""
        lt = await self.get_leave_type(leave_type_id)
        update_data = data.model_dump(exclude_unset=True)

        if "LeaveType" in update_data and update_data["LeaveType"]:
            new_title = update_data["LeaveType"].strip()
            dup_stmt = select(HRLeaveType).where(
                and_(
                    func.lower(HRLeaveType.LeaveType) == new_title.lower(),
                    HRLeaveType.LeaveTypeId != leave_type_id,
                )
            )
            res = await self.db.execute(dup_stmt)
            if res.scalars().first():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Leave type '{new_title}' already exists",
                )
            lt.LeaveType = new_title

        if "IsActive" in update_data and update_data["IsActive"] is not None:
            lt.IsActive = update_data["IsActive"]

        lt.UpdateDate = datetime.utcnow()
        lt.UpdatedUser = current_username
        await self.db.commit()
        await self.db.refresh(lt)
        return lt

    async def delete_leave_type(self, leave_type_id: int) -> Dict[str, Any]:
        """Deactivate leave type."""
        lt = await self.get_leave_type(leave_type_id)
        lt.IsActive = 0
        lt.UpdateDate = datetime.utcnow()
        await self.db.commit()
        return {"message": f"Leave type {leave_type_id} deactivated successfully"}

    # ========================================================================
    # 7. HR LEAVE APPLICATION & APPROVAL OPERATIONS
    # ========================================================================

    async def apply_leave(
        self, data: HRLeaveCreate, current_username: Optional[str] = None
    ) -> HRLeave:
        """
        Submit a new leave application.
        Validates date ranges, foreign entities, and prevents overlapping active leaves.
        """
        if data.FromDate > data.ToDate:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"FromDate ({data.FromDate}) cannot be after ToDate ({data.ToDate})",
            )
        if data.NoOfDays <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="NoOfDays must be greater than zero",
            )

        # Validate Organization, Department, and LeaveType
        await self.get_organization(data.OrganizationId)
        await self.get_department(data.DeparmentId)
        await self.get_leave_type(data.LeaveTypeId)

        # Check overlapping active leaves (Pending=0 or Approved=1)
        overlap_stmt = select(HRLeave).where(
            and_(
                HRLeave.EmpId == data.EmpId,
                HRLeave.ApprovalStatus.in_([0, 1]),
                or_(
                    and_(HRLeave.FromDate <= data.FromDate, data.FromDate <= HRLeave.ToDate),
                    and_(HRLeave.FromDate <= data.ToDate, data.ToDate <= HRLeave.ToDate),
                    and_(data.FromDate <= HRLeave.FromDate, HRLeave.ToDate <= data.ToDate),
                ),
            )
        )
        res = await self.db.execute(overlap_stmt)
        if res.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Employee {data.EmpId} already has an active or pending leave overlapping {data.FromDate} to {data.ToDate}",
            )

        leave = HRLeave(
            OrganizationId=data.OrganizationId,
            DeparmentId=data.DeparmentId,
            EmpId=data.EmpId,
            LeaveTypeId=data.LeaveTypeId,
            ApplicationDate=data.ApplicationDate or date.today(),
            FromDate=data.FromDate,
            ToDate=data.ToDate,
            NoOfDays=data.NoOfDays,
            Reason=data.Reason,
            Remark=data.Remark,
            Handover=data.Handover,
            ReportingId=data.ReportingId,
            ApprovalStatus=0,  # 0=Pending
            ApprovalDate=None,
            CreatedDate=datetime.utcnow(),
            CreateUser=current_username,
        )
        self.db.add(leave)
        await self.db.commit()
        await self.db.refresh(leave)
        return leave

    async def get_leave(self, leave_id: int) -> HRLeave:
        """Retrieve leave by ID."""
        leave = await self.db.get(HRLeave, leave_id)
        if not leave:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Leave application with ID {leave_id} not found",
            )
        return leave

    async def update_leave(
        self, leave_id: int, data: HRLeaveUpdate, current_username: Optional[str] = None
    ) -> HRLeave:
        """
        Update leave application details.
        Permitted only when leave is still in Pending status (ApprovalStatus == 0).
        """
        leave = await self.get_leave(leave_id)
        if leave.ApprovalStatus != 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot edit leave {leave_id} with status {leave.ApprovalStatus} (only Pending leaves can be edited)",
            )

        update_data = data.model_dump(exclude_unset=True)
        from_date = update_data.get("FromDate", leave.FromDate)
        to_date = update_data.get("ToDate", leave.ToDate)

        if from_date > to_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"FromDate ({from_date}) cannot be after ToDate ({to_date})",
            )

        for k, v in update_data.items():
            setattr(leave, k, v)

        leave.UpdateDate = datetime.utcnow()
        leave.UpdatedUser = current_username
        await self.db.commit()
        await self.db.refresh(leave)
        return leave

    async def update_leave_status(
        self,
        leave_id: int,
        req: HRLeaveStatusUpdateRequest,
        current_username: Optional[str] = None,
    ) -> HRLeave:
        """
        Manager / HR approval or rejection workflow.
        Status: 1=Approved, 2=Rejected, 3=Cancelled
        """
        leave = await self.get_leave(leave_id)
        if leave.ApprovalStatus in (1, 2) and req.ApprovalStatus == leave.ApprovalStatus:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Leave {leave_id} is already in status {req.ApprovalStatus}",
            )

        leave.ApprovalStatus = req.ApprovalStatus
        leave.ApprovalDate = datetime.utcnow()
        if req.Remark:
            leave.Remark = req.Remark
        leave.UpdateDate = datetime.utcnow()
        leave.UpdatedUser = current_username

        await self.db.commit()
        await self.db.refresh(leave)
        return leave

    async def list_leaves(
        self,
        emp_id: Optional[int] = None,
        reporting_id: Optional[int] = None,
        org_id: Optional[int] = None,
        dept_id: Optional[int] = None,
        status_code: Optional[int] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        month: Optional[int] = None,
        year: Optional[int] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[HRLeave]:
        """List leave applications with extensive filters."""
        stmt = select(HRLeave)
        filters = []
        if emp_id is not None:
            filters.append(HRLeave.EmpId == emp_id)
        if reporting_id is not None:
            filters.append(HRLeave.ReportingId == reporting_id)
        if org_id is not None:
            filters.append(HRLeave.OrganizationId == org_id)
        if dept_id is not None:
            filters.append(HRLeave.DeparmentId == dept_id)
        if status_code is not None:
            filters.append(HRLeave.ApprovalStatus == status_code)
        if from_date:
            filters.append(HRLeave.FromDate >= from_date)
        if to_date:
            filters.append(HRLeave.ToDate <= to_date)
        if month:
            filters.append(extract("month", HRLeave.FromDate) == month)
        if year:
            filters.append(extract("year", HRLeave.FromDate) == year)

        if filters:
            stmt = stmt.where(and_(*filters))
        stmt = stmt.order_by(desc(HRLeave.LeaveId)).offset(skip).limit(limit)
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def get_manager_pending_count(self, reporting_id: int) -> int:
        """Count pending leave requests awaiting approval from this manager (BLL_RptApplyLeaveReportingCount)."""
        stmt = select(func.count(HRLeave.LeaveId)).where(
            and_(HRLeave.ReportingId == reporting_id, HRLeave.ApprovalStatus == 0)
        )
        res = await self.db.execute(stmt)
        return res.scalar_one() or 0

    async def get_leave_summary(
        self,
        emp_id: Optional[int] = None,
        org_id: Optional[int] = None,
        year: Optional[int] = None,
    ) -> HRLeaveSummaryResponse:
        """Calculate aggregate leave statistics (Total, Pending, Approved, Rejected, Cancelled)."""
        base_stmt = select(HRLeave)
        filters = []
        if emp_id is not None:
            filters.append(HRLeave.EmpId == emp_id)
        if org_id is not None:
            filters.append(HRLeave.OrganizationId == org_id)
        if year is not None:
            filters.append(extract("year", HRLeave.FromDate) == year)

        if filters:
            base_stmt = base_stmt.where(and_(*filters))

        res = await self.db.execute(base_stmt)
        all_leaves = res.scalars().all()

        total_applications = len(all_leaves)
        pending_count = sum(1 for l in all_leaves if l.ApprovalStatus == 0)
        approved_count = sum(1 for l in all_leaves if l.ApprovalStatus == 1)
        rejected_count = sum(1 for l in all_leaves if l.ApprovalStatus == 2)
        cancelled_count = sum(1 for l in all_leaves if l.ApprovalStatus == 3)
        total_approved_days = sum(
            Decimal(str(l.NoOfDays)) for l in all_leaves if l.ApprovalStatus == 1
        )

        return HRLeaveSummaryResponse(
            total_applications=total_applications,
            pending_count=pending_count,
            approved_count=approved_count,
            rejected_count=rejected_count,
            cancelled_count=cancelled_count,
            total_approved_days=total_approved_days,
        )

    # ========================================================================
    # 8. HR CONTACT PERSON OPERATIONS
    # ========================================================================

    async def create_contact_person(
        self, data: HRContactPersonCreate, current_username: Optional[str] = None
    ) -> HRContactPerson:
        """Create a new Emergency/Reference contact person."""
        contact = HRContactPerson(
            ContactFName=data.ContactFName.strip(),
            ContactMName=data.ContactMName.strip() if data.ContactMName else None,
            ContactLName=data.ContactLName.strip() if data.ContactLName else None,
            MobileNo=data.MobileNo,
            Address=data.Address,
            CreatedDate=datetime.utcnow(),
            CreateUser=current_username,
            IsActive=data.IsActive,
        )
        self.db.add(contact)
        await self.db.commit()
        await self.db.refresh(contact)
        return contact

    async def get_contact_person(self, contact_id: int) -> HRContactPerson:
        """Retrieve contact person by ID."""
        contact = await self.db.get(HRContactPerson, contact_id)
        if not contact:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Contact person with ID {contact_id} not found",
            )
        return contact

    async def list_contact_persons(
        self,
        query: Optional[str] = None,
        is_active: Optional[int] = 1,
        skip: int = 0,
        limit: int = 100,
    ) -> List[HRContactPerson]:
        """List contact persons with optional name search."""
        stmt = select(HRContactPerson)
        filters = []
        if is_active is not None:
            filters.append(HRContactPerson.IsActive == is_active)
        if query:
            filters.append(
                or_(
                    HRContactPerson.ContactFName.ilike(f"%{query}%"),
                    HRContactPerson.ContactLName.ilike(f"%{query}%"),
                    HRContactPerson.MobileNo.ilike(f"%{query}%"),
                )
            )
        if filters:
            stmt = stmt.where(and_(*filters))
        stmt = stmt.order_by(HRContactPerson.ContactpersonId.asc()).offset(skip).limit(limit)
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def update_contact_person(
        self, contact_id: int, data: HRContactPersonUpdate, current_username: Optional[str] = None
    ) -> HRContactPerson:
        """Update contact person."""
        contact = await self.get_contact_person(contact_id)
        update_data = data.model_dump(exclude_unset=True)

        for k, v in update_data.items():
            setattr(contact, k, v)

        contact.UpdateDate = datetime.utcnow()
        contact.UpdatedUser = current_username
        await self.db.commit()
        await self.db.refresh(contact)
        return contact

    async def delete_contact_person(self, contact_id: int) -> Dict[str, Any]:
        """Deactivate contact person."""
        contact = await self.get_contact_person(contact_id)
        contact.IsActive = 0
        contact.UpdateDate = datetime.utcnow()
        await self.db.commit()
        return {"message": f"Contact person {contact_id} deactivated successfully"}
