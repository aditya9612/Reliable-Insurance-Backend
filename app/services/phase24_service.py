"""
Service Layer for Phase 24 — HR Workforce Lifecycle, Compensation Structure,
Employee Advances & Monthly Attendance Management.
"""
from datetime import datetime, date
from decimal import Decimal
from typing import List, Optional, Dict, Any
from fastapi import HTTPException, status
from sqlalchemy import select, and_, or_, desc, func, extract
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.phase24_features import (
    HRWorkingHistory,
    HRFamilyDetails,
    HRReferenceDetails,
    HRWorkingTime,
    HRSalaryStructureDef,
    HRAdvance,
    HRMonthlyWorkingDetails,
)
from app.models.phase23_features import HROrganization, HRDepartment
from app.schemas.phase24 import (
    HRWorkingHistoryCreate,
    HRWorkingHistoryUpdate,
    HRFamilyDetailsCreate,
    HRFamilyDetailsUpdate,
    HRReferenceDetailsCreate,
    HRReferenceDetailsUpdate,
    HRWorkingTimeCreate,
    HRWorkingTimeUpdate,
    HRSalaryStructureDefCreate,
    HRSalaryStructureDefUpdate,
    HRAdvanceCreate,
    HRAdvanceUpdate,
    HRAdvanceRecoveryRequest,
    HRMonthlyWorkingDetailsCreate,
    HRMonthlyWorkingDetailsUpdate,
    HRMonthlyWorkingSummaryReport,
)


class Phase24Service:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ========================================================================
    # 1. HR WORKING HISTORY OPERATIONS
    # ========================================================================

    async def create_working_history(
        self, data: HRWorkingHistoryCreate, current_username: Optional[str] = None
    ) -> HRWorkingHistory:
        """Record previous employer experience for an employee."""
        history = HRWorkingHistory(
            EmployeeID=data.EmployeeID,
            DepartMentID=data.DepartMentID,
            CompanyName=data.CompanyName.strip(),
            CompanyAddres=data.CompanyAddres,
            CompanyMobileNo=data.CompanyMobileNo,
            PreQualification=data.PreQualification,
            PreExprience=data.PreExprience,
            PreStartDate=data.PreStartDate,
            PreEndDate=data.PreEndDate,
            HRName=data.HRName,
            HRMobNo=data.HRMobNo,
            HRMailId=data.HRMailId,
            CreatedDate=datetime.utcnow(),
            CreateUser=current_username,
            IsActive=data.IsActive,
        )
        self.db.add(history)
        await self.db.commit()
        await self.db.refresh(history)
        return history

    async def get_working_history(self, history_id: int) -> HRWorkingHistory:
        """Retrieve working history record by ID."""
        history = await self.db.get(HRWorkingHistory, history_id)
        if not history:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Working history record {history_id} not found",
            )
        return history

    async def list_working_history(
        self,
        employee_id: Optional[int] = None,
        is_active: Optional[int] = 1,
        skip: int = 0,
        limit: int = 100,
    ) -> List[HRWorkingHistory]:
        """List employment history entries optionally filtered by employee ID."""
        stmt = select(HRWorkingHistory)
        filters = []
        if employee_id is not None:
            filters.append(HRWorkingHistory.EmployeeID == employee_id)
        if is_active is not None:
            filters.append(HRWorkingHistory.IsActive == is_active)
        if filters:
            stmt = stmt.where(and_(*filters))
        stmt = stmt.order_by(HRWorkingHistory.WorkingHistoryId.desc()).offset(skip).limit(limit)
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def update_working_history(
        self, history_id: int, data: HRWorkingHistoryUpdate, current_username: Optional[str] = None
    ) -> HRWorkingHistory:
        """Update working history record."""
        history = await self.get_working_history(history_id)
        update_data = data.model_dump(exclude_unset=True)

        for k, v in update_data.items():
            setattr(history, k, v)

        history.UpdateDate = datetime.utcnow()
        history.UpdateUser = current_username
        await self.db.commit()
        await self.db.refresh(history)
        return history

    async def delete_working_history(self, history_id: int) -> Dict[str, Any]:
        """Deactivate working history record."""
        history = await self.get_working_history(history_id)
        history.IsActive = 0
        history.UpdateDate = datetime.utcnow()
        await self.db.commit()
        return {"message": f"Working history {history_id} deactivated successfully"}

    # ========================================================================
    # 2. HR FAMILY DETAILS OPERATIONS
    # ========================================================================

    async def create_family_detail(
        self, data: HRFamilyDetailsCreate, current_username: Optional[str] = None
    ) -> HRFamilyDetails:
        """Add employee family dependent / relationship."""
        family = HRFamilyDetails(
            EmployeeID=data.EmployeeID,
            FName=data.FName.strip(),
            Relation=data.Relation.strip(),
            Occuption=data.Occuption,
            ContactNo=data.ContactNo,
            Designation=data.Designation,
            CreatedDate=datetime.utcnow(),
            CreateUser=current_username,
            IsActive=data.IsActive,
        )
        self.db.add(family)
        await self.db.commit()
        await self.db.refresh(family)
        return family

    async def get_family_detail(self, family_id: int) -> HRFamilyDetails:
        """Retrieve family dependent by ID."""
        family = await self.db.get(HRFamilyDetails, family_id)
        if not family:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Family detail {family_id} not found",
            )
        return family

    async def list_family_details(
        self,
        employee_id: Optional[int] = None,
        is_active: Optional[int] = 1,
        skip: int = 0,
        limit: int = 100,
    ) -> List[HRFamilyDetails]:
        """List family members optionally filtered by employee ID."""
        stmt = select(HRFamilyDetails)
        filters = []
        if employee_id is not None:
            filters.append(HRFamilyDetails.EmployeeID == employee_id)
        if is_active is not None:
            filters.append(HRFamilyDetails.IsActive == is_active)
        if filters:
            stmt = stmt.where(and_(*filters))
        stmt = stmt.order_by(HRFamilyDetails.FamilyId.asc()).offset(skip).limit(limit)
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def update_family_detail(
        self, family_id: int, data: HRFamilyDetailsUpdate, current_username: Optional[str] = None
    ) -> HRFamilyDetails:
        """Update family dependent."""
        family = await self.get_family_detail(family_id)
        update_data = data.model_dump(exclude_unset=True)

        for k, v in update_data.items():
            setattr(family, k, v)

        family.UpdateDate = datetime.utcnow()
        family.UpdateUser = current_username
        await self.db.commit()
        await self.db.refresh(family)
        return family

    async def delete_family_detail(self, family_id: int) -> Dict[str, Any]:
        """Deactivate family dependent."""
        family = await self.get_family_detail(family_id)
        family.IsActive = 0
        family.UpdateDate = datetime.utcnow()
        await self.db.commit()
        return {"message": f"Family detail {family_id} deactivated successfully"}

    # ========================================================================
    # 3. HR REFERENCE DETAILS OPERATIONS
    # ========================================================================

    async def create_reference_detail(
        self, data: HRReferenceDetailsCreate, current_username: Optional[str] = None
    ) -> HRReferenceDetails:
        """Add employee professional reference contact."""
        ref = HRReferenceDetails(
            EmployeeID=data.EmployeeID,
            ReferenceName=data.ReferenceName.strip(),
            Address=data.Address,
            ContactNo=data.ContactNo,
            Designation=data.Designation,
            MailId=data.MailId,
            CreatedDate=datetime.utcnow(),
            CreateUser=current_username,
            IsActive=data.IsActive,
        )
        self.db.add(ref)
        await self.db.commit()
        await self.db.refresh(ref)
        return ref

    async def get_reference_detail(self, ref_id: int) -> HRReferenceDetails:
        """Retrieve reference contact by ID."""
        ref = await self.db.get(HRReferenceDetails, ref_id)
        if not ref:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Reference detail {ref_id} not found",
            )
        return ref

    async def list_reference_details(
        self,
        employee_id: Optional[int] = None,
        is_active: Optional[int] = 1,
        skip: int = 0,
        limit: int = 100,
    ) -> List[HRReferenceDetails]:
        """List professional references optionally filtered by employee ID."""
        stmt = select(HRReferenceDetails)
        filters = []
        if employee_id is not None:
            filters.append(HRReferenceDetails.EmployeeID == employee_id)
        if is_active is not None:
            filters.append(HRReferenceDetails.IsActive == is_active)
        if filters:
            stmt = stmt.where(and_(*filters))
        stmt = stmt.order_by(HRReferenceDetails.ReferenceId.asc()).offset(skip).limit(limit)
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def update_reference_detail(
        self, ref_id: int, data: HRReferenceDetailsUpdate, current_username: Optional[str] = None
    ) -> HRReferenceDetails:
        """Update professional reference contact."""
        ref = await self.get_reference_detail(ref_id)
        update_data = data.model_dump(exclude_unset=True)

        for k, v in update_data.items():
            setattr(ref, k, v)

        ref.UpdateDate = datetime.utcnow()
        ref.UpdateUser = current_username
        await self.db.commit()
        await self.db.refresh(ref)
        return ref

    async def delete_reference_detail(self, ref_id: int) -> Dict[str, Any]:
        """Deactivate reference contact."""
        ref = await self.get_reference_detail(ref_id)
        ref.IsActive = 0
        ref.UpdateDate = datetime.utcnow()
        await self.db.commit()
        return {"message": f"Reference detail {ref_id} deactivated successfully"}

    # ========================================================================
    # 4. HR WORKING TIME SCHEDULE OPERATIONS
    # ========================================================================

    async def create_or_update_working_time(
        self, data: HRWorkingTimeCreate, current_username: Optional[str] = None
    ) -> HRWorkingTime:
        """Assign or update employee shift schedule and hours."""
        stmt = select(HRWorkingTime).where(
            and_(HRWorkingTime.EmployeeID == data.EmployeeID, HRWorkingTime.IsActive == 1)
        )
        res = await self.db.execute(stmt)
        existing = res.scalars().first()

        if existing:
            existing.DepartMentID = data.DepartMentID
            existing.workingHours = data.workingHours
            existing.offday = data.offday
            existing.overtime = data.overtime
            existing.ExtraDay = data.ExtraDay
            existing.UpdateDate = datetime.utcnow()
            existing.UpdateUser = current_username
            await self.db.commit()
            await self.db.refresh(existing)
            return existing

        wt = HRWorkingTime(
            EmployeeID=data.EmployeeID,
            DepartMentID=data.DepartMentID,
            workingHours=data.workingHours,
            offday=data.offday,
            overtime=data.overtime,
            ExtraDay=data.ExtraDay,
            CreatedDate=datetime.utcnow(),
            CreateUser=current_username,
            IsActive=data.IsActive,
        )
        self.db.add(wt)
        await self.db.commit()
        await self.db.refresh(wt)
        return wt

    async def get_working_time(self, timeinfo_id: int) -> HRWorkingTime:
        """Retrieve working time schedule by ID."""
        wt = await self.db.get(HRWorkingTime, timeinfo_id)
        if not wt:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Working time schedule {timeinfo_id} not found",
            )
        return wt

    async def get_working_time_by_employee(self, employee_id: int) -> HRWorkingTime:
        """Retrieve active working time schedule for an employee."""
        stmt = select(HRWorkingTime).where(
            and_(HRWorkingTime.EmployeeID == employee_id, HRWorkingTime.IsActive == 1)
        )
        res = await self.db.execute(stmt)
        wt = res.scalars().first()
        if not wt:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No active working time schedule found for employee {employee_id}",
            )
        return wt

    async def list_working_times(
        self,
        department_id: Optional[int] = None,
        is_active: Optional[int] = 1,
        skip: int = 0,
        limit: int = 100,
    ) -> List[HRWorkingTime]:
        """List working time schedules."""
        stmt = select(HRWorkingTime)
        filters = []
        if department_id is not None:
            filters.append(HRWorkingTime.DepartMentID == department_id)
        if is_active is not None:
            filters.append(HRWorkingTime.IsActive == is_active)
        if filters:
            stmt = stmt.where(and_(*filters))
        stmt = stmt.order_by(HRWorkingTime.timeinfoId.asc()).offset(skip).limit(limit)
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    # ========================================================================
    # 5. HR SALARY STRUCTURE DEFINITION OPERATIONS
    # ========================================================================

    async def create_salary_structure(
        self, data: HRSalaryStructureDefCreate, current_username: Optional[str] = None
    ) -> HRSalaryStructureDef:
        """Create a company salary structure template."""
        # Validate parent organization
        org = await self.db.get(HROrganization, data.OrganizationId)
        if not org:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Organization {data.OrganizationId} not found",
            )

        # Prevent duplicate structure name in the same organization
        stmt = select(HRSalaryStructureDef).where(
            and_(
                HRSalaryStructureDef.OrganizationId == data.OrganizationId,
                func.lower(HRSalaryStructureDef.salaryStructure) == data.salaryStructure.lower().strip(),
            )
        )
        res = await self.db.execute(stmt)
        if res.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Salary structure '{data.salaryStructure}' already exists in organization {data.OrganizationId}",
            )

        struct = HRSalaryStructureDef(
            OrganizationId=data.OrganizationId,
            salaryStructure=data.salaryStructure.strip(),
            InActive=data.InActive or "0",
            RateOnGross=data.RateOnGross,
            Remark=data.Remark,
            CreatedDate=datetime.utcnow(),
            CreateUser=current_username,
            IsActive=data.IsActive,
        )
        self.db.add(struct)
        await self.db.commit()
        await self.db.refresh(struct)
        return struct

    async def get_salary_structure(self, struct_id: int) -> HRSalaryStructureDef:
        """Retrieve salary structure by ID."""
        struct = await self.db.get(HRSalaryStructureDef, struct_id)
        if not struct:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Salary structure {struct_id} not found",
            )
        return struct

    async def list_salary_structures(
        self,
        org_id: Optional[int] = None,
        is_active: Optional[int] = 1,
        skip: int = 0,
        limit: int = 100,
    ) -> List[HRSalaryStructureDef]:
        """List salary structure definitions."""
        stmt = select(HRSalaryStructureDef)
        filters = []
        if org_id is not None:
            filters.append(HRSalaryStructureDef.OrganizationId == org_id)
        if is_active is not None:
            filters.append(HRSalaryStructureDef.IsActive == is_active)
        if filters:
            stmt = stmt.where(and_(*filters))
        stmt = stmt.order_by(HRSalaryStructureDef.SalaryStructureDefId.asc()).offset(skip).limit(limit)
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def update_salary_structure(
        self, struct_id: int, data: HRSalaryStructureDefUpdate, current_username: Optional[str] = None
    ) -> HRSalaryStructureDef:
        """Update salary structure definition."""
        struct = await self.get_salary_structure(struct_id)
        update_data = data.model_dump(exclude_unset=True)

        for k, v in update_data.items():
            setattr(struct, k, v)

        struct.UpdateDate = datetime.utcnow()
        struct.UpdatedUser = current_username
        await self.db.commit()
        await self.db.refresh(struct)
        return struct

    async def delete_salary_structure(self, struct_id: int) -> Dict[str, Any]:
        """Deactivate salary structure template."""
        struct = await self.get_salary_structure(struct_id)
        struct.IsActive = 0
        struct.InActive = "1"
        struct.UpdateDate = datetime.utcnow()
        await self.db.commit()
        return {"message": f"Salary structure {struct_id} deactivated successfully"}

    # ========================================================================
    # 6. HR ADVANCE & RECOVERY TRACKING OPERATIONS
    # ========================================================================

    async def create_advance(
        self, data: HRAdvanceCreate, current_username: Optional[str] = None
    ) -> HRAdvance:
        """
        Record employee salary advance disbursement and compute installment schedule.
        """
        org = await self.db.get(HROrganization, data.OrganizationId)
        if not org:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Organization {data.OrganizationId} not found",
            )

        total_advance = data.Amount
        total_interest = data.InterestAmount or Decimal("0.00")
        total_deu = total_advance + total_interest
        no_of_inst = max(1, int(data.NoOfInstallment or "1"))
        inst_amt = (total_deu / Decimal(str(no_of_inst))).quantize(Decimal("0.01"))

        adv = HRAdvance(
            EmpId=data.EmpId,
            OrganizationId=data.OrganizationId,
            AdvanceName=data.AdvanceName.strip(),
            AdvanceDate=data.AdvanceDate or date.today(),
            Amount=data.Amount,
            InterestAmount=total_interest,
            TotalAdvance=total_advance,
            TotalInterest=total_interest,
            TotalReceipts=total_advance,
            TotalRecovered=Decimal("0.00"),
            TotalDeu=total_deu,
            Lumpsum=data.Lumpsum or "No",
            NoOfInstallment=str(no_of_inst),
            Instlamt=inst_amt,
            RecoverFrom=data.RecoverFrom or "Salary",
            NoRecovery=data.NoRecovery or "0",
            Remark=data.Remark,
            CreatedDate=datetime.utcnow(),
            CreateUser=current_username,
            IsActive=data.IsActive,
        )
        self.db.add(adv)
        await self.db.commit()
        await self.db.refresh(adv)
        return adv

    async def get_advance(self, adv_id: int) -> HRAdvance:
        """Retrieve advance by ID."""
        adv = await self.db.get(HRAdvance, adv_id)
        if not adv:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Advance record {adv_id} not found",
            )
        return adv

    async def list_advances(
        self,
        emp_id: Optional[int] = None,
        org_id: Optional[int] = None,
        is_active: Optional[int] = 1,
        skip: int = 0,
        limit: int = 100,
    ) -> List[HRAdvance]:
        """List employee advance records."""
        stmt = select(HRAdvance)
        filters = []
        if emp_id is not None:
            filters.append(HRAdvance.EmpId == emp_id)
        if org_id is not None:
            filters.append(HRAdvance.OrganizationId == org_id)
        if is_active is not None:
            filters.append(HRAdvance.IsActive == is_active)
        if filters:
            stmt = stmt.where(and_(*filters))
        stmt = stmt.order_by(HRAdvance.HrAdvanceId.desc()).offset(skip).limit(limit)
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def record_advance_recovery(
        self, adv_id: int, req: HRAdvanceRecoveryRequest, current_username: Optional[str] = None
    ) -> HRAdvance:
        """Record an installment or partial recovery against an active advance."""
        adv = await self.get_advance(adv_id)
        if adv.TotalDeu <= Decimal("0.00"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Advance {adv_id} has already been completely recovered (Due balance is 0.00)",
            )

        recovery_amt = min(req.RecoveryAmount, adv.TotalDeu)
        adv.TotalRecovered = (adv.TotalRecovered + recovery_amt).quantize(Decimal("0.01"))
        adv.TotalDeu = max(Decimal("0.00"), adv.TotalDeu - recovery_amt).quantize(Decimal("0.01"))
        adv.UpdateDate = datetime.utcnow()
        adv.UpdatedUser = current_username
        if req.Remark:
            adv.Remark = f"{adv.Remark or ''} | Recovery: {req.Remark}".strip()

        await self.db.commit()
        await self.db.refresh(adv)
        return adv

    async def update_advance(
        self, adv_id: int, data: HRAdvanceUpdate, current_username: Optional[str] = None
    ) -> HRAdvance:
        """Update advance metadata."""
        adv = await self.get_advance(adv_id)
        update_data = data.model_dump(exclude_unset=True)

        for k, v in update_data.items():
            setattr(adv, k, v)

        adv.UpdateDate = datetime.utcnow()
        adv.UpdatedUser = current_username
        await self.db.commit()
        await self.db.refresh(adv)
        return adv

    async def delete_advance(self, adv_id: int) -> Dict[str, Any]:
        """Deactivate advance record."""
        adv = await self.get_advance(adv_id)
        adv.IsActive = 0
        adv.UpdateDate = datetime.utcnow()
        await self.db.commit()
        return {"message": f"Advance record {adv_id} deactivated successfully"}

    # ========================================================================
    # 7. HR MONTHLY WORKING DETAILS & ATTENDANCE OPERATIONS
    # ========================================================================

    async def create_or_update_monthly_working(
        self, data: HRMonthlyWorkingDetailsCreate, current_username: Optional[str] = None
    ) -> HRMonthlyWorkingDetails:
        """
        Record or reconcile monthly employee attendance and compute working days.
        Formula: workingDays = totalNoOfDays - Sunday - Hoildays - leaves + ExtraDays
        """
        await self.db.get(HROrganization, data.OrganizationId)
        await self.db.get(HRDepartment, data.DeparmentId)

        stmt = select(HRMonthlyWorkingDetails).where(
            and_(
                HRMonthlyWorkingDetails.EmpId == data.EmpId,
                HRMonthlyWorkingDetails.Year == data.Year,
                HRMonthlyWorkingDetails.Month == data.Month,
                HRMonthlyWorkingDetails.IsActive == 1,
            )
        )
        res = await self.db.execute(stmt)
        existing = res.scalars().first()

        calculated_working_days = max(
            Decimal("0.00"),
            data.totalNoOfDays - data.Sunday - data.Hoildays - data.leaves + data.ExtraDays,
        )

        if existing:
            existing.OrganizationId = data.OrganizationId
            existing.DeparmentId = data.DeparmentId
            existing.totalNoOfDays = data.totalNoOfDays
            existing.Sunday = data.Sunday
            existing.Hoildays = data.Hoildays
            existing.leaves = data.leaves
            existing.workingDays = calculated_working_days
            existing.ExtraDays = data.ExtraDays
            existing.overTimeHour = data.overTimeHour
            existing.PetrolAll = data.PetrolAll
            existing.Incentive = data.Incentive
            existing.Arrears = data.Arrears
            existing.UpdateDate = datetime.utcnow()
            existing.UpdatedUser = current_username
            await self.db.commit()
            await self.db.refresh(existing)
            return existing

        mwd = HRMonthlyWorkingDetails(
            OrganizationId=data.OrganizationId,
            DeparmentId=data.DeparmentId,
            EmpId=data.EmpId,
            Month=data.Month,
            Year=data.Year,
            totalNoOfDays=data.totalNoOfDays,
            Sunday=data.Sunday,
            Hoildays=data.Hoildays,
            leaves=data.leaves,
            workingDays=calculated_working_days,
            ExtraDays=data.ExtraDays,
            overTimeHour=data.overTimeHour,
            PetrolAll=data.PetrolAll,
            Incentive=data.Incentive,
            Arrears=data.Arrears,
            CreatedDate=datetime.utcnow(),
            CreateUser=current_username,
            IsActive=data.IsActive,
        )
        self.db.add(mwd)
        await self.db.commit()
        await self.db.refresh(mwd)
        return mwd

    async def get_monthly_working(self, working_id: int) -> HRMonthlyWorkingDetails:
        """Retrieve monthly working details by ID."""
        mwd = await self.db.get(HRMonthlyWorkingDetails, working_id)
        if not mwd:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Monthly working record {working_id} not found",
            )
        return mwd

    async def list_monthly_working(
        self,
        emp_id: Optional[int] = None,
        org_id: Optional[int] = None,
        dept_id: Optional[int] = None,
        month: Optional[int] = None,
        year: Optional[int] = None,
        is_active: Optional[int] = 1,
        skip: int = 0,
        limit: int = 100,
    ) -> List[HRMonthlyWorkingDetails]:
        """List monthly attendance and working day registers."""
        stmt = select(HRMonthlyWorkingDetails)
        filters = []
        if emp_id is not None:
            filters.append(HRMonthlyWorkingDetails.EmpId == emp_id)
        if org_id is not None:
            filters.append(HRMonthlyWorkingDetails.OrganizationId == org_id)
        if dept_id is not None:
            filters.append(HRMonthlyWorkingDetails.DeparmentId == dept_id)
        if month is not None:
            filters.append(HRMonthlyWorkingDetails.Month == month)
        if year is not None:
            filters.append(HRMonthlyWorkingDetails.Year == year)
        if is_active is not None:
            filters.append(HRMonthlyWorkingDetails.IsActive == is_active)
        if filters:
            stmt = stmt.where(and_(*filters))
        stmt = stmt.order_by(HRMonthlyWorkingDetails.MonthlyWorkingId.desc()).offset(skip).limit(limit)
        res = await self.db.execute(stmt)
        return list(res.scalars().all())

    async def get_monthly_summary_report(
        self,
        org_id: Optional[int] = None,
        year: Optional[int] = None,
        month: Optional[int] = None,
    ) -> HRMonthlyWorkingSummaryReport:
        """Aggregate monthly attendance and payroll register totals across staff."""
        stmt = select(HRMonthlyWorkingDetails).where(HRMonthlyWorkingDetails.IsActive == 1)
        filters = []
        if org_id is not None:
            filters.append(HRMonthlyWorkingDetails.OrganizationId == org_id)
        if year is not None:
            filters.append(HRMonthlyWorkingDetails.Year == year)
        if month is not None:
            filters.append(HRMonthlyWorkingDetails.Month == month)
        if filters:
            stmt = stmt.where(and_(*filters))

        res = await self.db.execute(stmt)
        records = res.scalars().all()

        total_employees = len(records)
        total_working = sum(r.workingDays for r in records) if records else Decimal("0.00")
        total_leaves = sum(r.leaves for r in records) if records else Decimal("0.00")
        total_ot = sum(r.overTimeHour for r in records) if records else Decimal("0.00")
        total_petrol = sum(r.PetrolAll for r in records) if records else Decimal("0.00")
        total_inc = sum(r.Incentive for r in records) if records else Decimal("0.00")
        total_arr = sum(r.Arrears for r in records) if records else Decimal("0.00")

        return HRMonthlyWorkingSummaryReport(
            total_employees_logged=total_employees,
            total_working_days=Decimal(str(total_working)),
            total_leaves_taken=Decimal(str(total_leaves)),
            total_overtime_hours=Decimal(str(total_ot)),
            total_petrol_allowances=Decimal(str(total_petrol)),
            total_incentives=Decimal(str(total_inc)),
            total_arrears=Decimal(str(total_arr)),
        )

    async def delete_monthly_working(self, working_id: int) -> Dict[str, Any]:
        """Deactivate monthly working record."""
        mwd = await self.get_monthly_working(working_id)
        mwd.IsActive = 0
        mwd.UpdateDate = datetime.utcnow()
        await self.db.commit()
        return {"message": f"Monthly working record {working_id} deactivated successfully"}
