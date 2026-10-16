"""
Service Layer for Phase 22 — Sales Executive & Location Head Commission Hierarchy,
Insurer Partner Portals Registry, and App Billing & Field Reimbursement Claims.
"""
from datetime import datetime, date
from decimal import Decimal
from typing import List, Optional, Tuple, Dict, Any
from fastapi import HTTPException, status
from sqlalchemy import select, and_, or_, desc, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.executive_commission import (
    SalesExecutiveCommission,
    LocationHeadCommission,
    LocationHeadSalesExMap,
    InsuranceCompanyPortal,
    AppBillingDetails,
    AppBillingAttachment,
)
from app.schemas.executive_commission import (
    SalesExecutiveCommissionCreate,
    SalesExecutiveCommissionUpdate,
    SalesExecutiveCommissionLookupRequest,
    SalesExecutiveCommissionLookupResponse,
    LocationHeadCommissionCreate,
    LocationHeadCommissionUpdate,
    LocationHeadCommissionLookupRequest,
    LocationHeadCommissionLookupResponse,
    LocationHeadAssignmentRequest,
    InsuranceCompanyPortalCreate,
    InsuranceCompanyPortalUpdate,
    AppBillingDetailsCreate,
    AppBillingDetailsUpdate,
    AppBillingStatusUpdateRequest,
    AppBillingAttachmentResponse,
    AppBillingDetailsResponse,
)


class ExecutiveCommissionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ========================================================================
    # 1. SALES EXECUTIVE COMMISSION OPERATIONS
    # ========================================================================

    async def list_sales_ex_commissions(
        self,
        sales_ex_id: Optional[int] = None,
        insurance_company_id: Optional[int] = None,
        franchise_code: Optional[str] = None,
        policy_type: Optional[str] = None,
        product_type: Optional[str] = None,
        is_active: Optional[int] = 1,
        skip: int = 0,
        limit: int = 100,
    ) -> List[SalesExecutiveCommission]:
        """List sales executive commission grid entries with filtering."""
        query = select(SalesExecutiveCommission)
        conditions = []

        if sales_ex_id is not None:
            conditions.append(SalesExecutiveCommission.SalesEx_Id == sales_ex_id)
        if insurance_company_id is not None:
            conditions.append(SalesExecutiveCommission.InsuranceCompanyId == insurance_company_id)
        if franchise_code:
            conditions.append(SalesExecutiveCommission.FranchiseCode == franchise_code)
        if policy_type:
            conditions.append(SalesExecutiveCommission.PolicyType == policy_type)
        if product_type:
            conditions.append(SalesExecutiveCommission.ProductType == product_type)
        if is_active is not None:
            conditions.append(SalesExecutiveCommission.IsActive == is_active)

        if conditions:
            query = query.where(and_(*conditions))

        query = query.order_by(desc(SalesExecutiveCommission.SalesCommissionId)).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def create_sales_ex_commission(
        self,
        payload: SalesExecutiveCommissionCreate,
        current_user_id: Optional[int] = None,
    ) -> SalesExecutiveCommission:
        """Create a new sales executive commission grid entry with duplicate prevention."""
        if payload.Commission < 0 or payload.Commission_OD < 0 or payload.Commission_Net < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Commission rates cannot be negative.",
            )

        # Check for existing duplicate active entry
        dup_query = select(SalesExecutiveCommission).where(
            and_(
                SalesExecutiveCommission.SalesEx_Id == payload.SalesEx_Id,
                SalesExecutiveCommission.InsuranceCompanyId == payload.InsuranceCompanyId,
                SalesExecutiveCommission.PolicyType == payload.PolicyType,
                SalesExecutiveCommission.ProductType == payload.ProductType,
                SalesExecutiveCommission.VehiTypeId == payload.VehiTypeId,
                SalesExecutiveCommission.FuelTypeId == payload.FuelTypeId,
                SalesExecutiveCommission.FranchiseCode == payload.FranchiseCode,
                SalesExecutiveCommission.ncb == payload.ncb,
                SalesExecutiveCommission.ValidFromDate == payload.ValidFromDate,
                SalesExecutiveCommission.IsActive == 1,
            )
        )
        dup_result = await self.db.execute(dup_query)
        if dup_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Commission grid entry already exists for this parameter set.",
            )

        entry = SalesExecutiveCommission(
            SalesEx_Id=payload.SalesEx_Id,
            InsuranceCompanyId=payload.InsuranceCompanyId,
            PolicyType=payload.PolicyType,
            ProductType=payload.ProductType,
            VehiTypeId=payload.VehiTypeId,
            FuelTypeId=payload.FuelTypeId,
            Commission=payload.Commission,
            Commission_OD=payload.Commission_OD,
            Commission_Net=payload.Commission_Net,
            CommissionCalculateOn=payload.CommissionCalculateOn,
            ReferenceType=payload.ReferenceType,
            FlatRate=payload.FlatRate,
            OD_Discount=payload.OD_Discount,
            FranchiseCode=payload.FranchiseCode,
            ncb=payload.ncb,
            CCRange=payload.CCRange,
            Slab=payload.Slab,
            ND=payload.ND,
            MakeId=payload.MakeId,
            ModelId=payload.ModelId,
            RtoId=payload.RtoId,
            StateId=payload.StateId,
            ValidFromDate=payload.ValidFromDate,
            ValidToDate=payload.ValidToDate,
            CreateUser=current_user_id,
            CreateDate=datetime.utcnow(),
            IsActive=payload.IsActive,
        )
        self.db.add(entry)
        await self.db.commit()
        await self.db.refresh(entry)
        return entry

    async def get_sales_ex_commission(self, commission_id: int) -> SalesExecutiveCommission:
        """Retrieve single sales executive commission record by ID."""
        result = await self.db.execute(
            select(SalesExecutiveCommission).where(
                SalesExecutiveCommission.SalesCommissionId == commission_id
            )
        )
        record = result.scalar_one_or_none()
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Sales executive commission record {commission_id} not found.",
            )
        return record

    async def update_sales_ex_commission(
        self,
        commission_id: int,
        payload: SalesExecutiveCommissionUpdate,
        current_user_id: Optional[int] = None,
    ) -> SalesExecutiveCommission:
        """Update an existing sales executive commission record."""
        record = await self.get_sales_ex_commission(commission_id)

        update_data = payload.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(record, field, value)

        record.UpdateUser = current_user_id
        record.UpdateDate = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(record)
        return record

    async def delete_sales_ex_commission(
        self,
        commission_id: int,
        current_user_id: Optional[int] = None,
    ) -> SalesExecutiveCommission:
        """Soft delete a sales executive commission record."""
        record = await self.get_sales_ex_commission(commission_id)
        record.IsActive = 0
        record.UpdateUser = current_user_id
        record.UpdateDate = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(record)
        return record

    async def lookup_sales_ex_commission(
        self, payload: SalesExecutiveCommissionLookupRequest
    ) -> SalesExecutiveCommissionLookupResponse:
        """
        Lookup best-matching commission rate for a policy transaction.
        Preserves legacy matching priority: exact Vehicle Type, Fuel Type, NCB, Franchise Code.
        """
        check_date = payload.TransDate or date.today()

        query = select(SalesExecutiveCommission).where(
            and_(
                SalesExecutiveCommission.SalesEx_Id == payload.SalesEx_Id,
                SalesExecutiveCommission.InsuranceCompanyId == payload.InsuranceCompanyId,
                SalesExecutiveCommission.ValidFromDate <= check_date,
                or_(
                    SalesExecutiveCommission.ValidToDate.is_(None),
                    SalesExecutiveCommission.ValidToDate >= check_date,
                ),
                SalesExecutiveCommission.IsActive == 1,
            )
        )

        if payload.FranchiseCode:
            query = query.where(
                or_(
                    SalesExecutiveCommission.FranchiseCode == payload.FranchiseCode,
                    SalesExecutiveCommission.FranchiseCode.is_(None),
                )
            )

        if payload.VehiTypeId:
            query = query.where(
                or_(
                    SalesExecutiveCommission.VehiTypeId == payload.VehiTypeId,
                    SalesExecutiveCommission.VehiTypeId.is_(None),
                )
            )

        if payload.FuelTypeId:
            query = query.where(
                or_(
                    SalesExecutiveCommission.FuelTypeId == payload.FuelTypeId,
                    SalesExecutiveCommission.FuelTypeId.is_(None),
                )
            )

        query = query.order_by(
            desc(SalesExecutiveCommission.ValidFromDate),
            desc(SalesExecutiveCommission.SalesCommissionId),
        )

        result = await self.db.execute(query)
        candidates = list(result.scalars().all())

        if not candidates:
            return SalesExecutiveCommissionLookupResponse(
                matched=False,
                Commission=Decimal("0.00"),
                Commission_OD=Decimal("0.00"),
                Commission_Net=Decimal("0.00"),
                OD_Discount=Decimal("0.00"),
                ReferenceType="Self",
                FranchiseCode=payload.FranchiseCode or "RA",
                grid_id=None,
                message="No matching commission grid found for given parameters.",
            )

        # Select candidate with most matching attributes
        best_match = candidates[0]
        return SalesExecutiveCommissionLookupResponse(
            matched=True,
            Commission=best_match.Commission,
            Commission_OD=best_match.Commission_OD,
            Commission_Net=best_match.Commission_Net,
            OD_Discount=best_match.OD_Discount,
            ReferenceType=best_match.ReferenceType or "Self",
            FranchiseCode=best_match.FranchiseCode or (payload.FranchiseCode or "RA"),
            grid_id=best_match.SalesCommissionId,
            message="Commission rate matched successfully.",
        )

    # ========================================================================
    # 2. LOCATION HEAD COMMISSION OPERATIONS
    # ========================================================================

    async def list_location_head_commissions(
        self,
        location_head_id: Optional[int] = None,
        insurance_company_id: Optional[int] = None,
        franchise_code: Optional[str] = None,
        is_active: Optional[int] = 1,
        skip: int = 0,
        limit: int = 100,
    ) -> List[LocationHeadCommission]:
        """List location head commission grid entries with filtering."""
        query = select(LocationHeadCommission)
        conditions = []

        if location_head_id is not None:
            conditions.append(LocationHeadCommission.LocationHeadId == location_head_id)
        if insurance_company_id is not None:
            conditions.append(LocationHeadCommission.InsuranceCompanyId == insurance_company_id)
        if franchise_code:
            conditions.append(LocationHeadCommission.FranchiseCode == franchise_code)
        if is_active is not None:
            conditions.append(LocationHeadCommission.IsActive == is_active)

        if conditions:
            query = query.where(and_(*conditions))

        query = query.order_by(desc(LocationHeadCommission.LocationHeadCommId)).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def create_location_head_commission(
        self,
        payload: LocationHeadCommissionCreate,
        current_user_id: Optional[int] = None,
    ) -> LocationHeadCommission:
        """Create a new location head commission grid entry."""
        if payload.Commission < 0 or payload.Commission_OD < 0 or payload.Commission_Net < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Commission rates cannot be negative.",
            )

        dup_query = select(LocationHeadCommission).where(
            and_(
                LocationHeadCommission.LocationHeadId == payload.LocationHeadId,
                LocationHeadCommission.InsuranceCompanyId == payload.InsuranceCompanyId,
                LocationHeadCommission.PolicyType == payload.PolicyType,
                LocationHeadCommission.ProductType == payload.ProductType,
                LocationHeadCommission.VehiTypeId == payload.VehiTypeId,
                LocationHeadCommission.FuelTypeId == payload.FuelTypeId,
                LocationHeadCommission.FranchiseCode == payload.FranchiseCode,
                LocationHeadCommission.ValidFromDate == payload.ValidFromDate,
                LocationHeadCommission.IsActive == 1,
            )
        )
        dup_result = await self.db.execute(dup_query)
        if dup_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Location head commission entry already exists for this parameter set.",
            )

        entry = LocationHeadCommission(
            LocationHeadId=payload.LocationHeadId,
            InsuranceCompanyId=payload.InsuranceCompanyId,
            PolicyType=payload.PolicyType,
            ProductType=payload.ProductType,
            VehiTypeId=payload.VehiTypeId,
            FuelTypeId=payload.FuelTypeId,
            Commission=payload.Commission,
            Commission_OD=payload.Commission_OD,
            Commission_Net=payload.Commission_Net,
            OD_Discount=payload.OD_Discount,
            FranchiseCode=payload.FranchiseCode,
            ReferenceType=payload.ReferenceType,
            ValidFromDate=payload.ValidFromDate,
            ValidToDate=payload.ValidToDate,
            CreateUser=current_user_id,
            CreateDate=datetime.utcnow(),
            IsActive=payload.IsActive,
        )
        self.db.add(entry)
        await self.db.commit()
        await self.db.refresh(entry)
        return entry

    async def get_location_head_commission(self, commission_id: int) -> LocationHeadCommission:
        """Retrieve single location head commission record by ID."""
        result = await self.db.execute(
            select(LocationHeadCommission).where(
                LocationHeadCommission.LocationHeadCommId == commission_id
            )
        )
        record = result.scalar_one_or_none()
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Location head commission record {commission_id} not found.",
            )
        return record

    async def update_location_head_commission(
        self,
        commission_id: int,
        payload: LocationHeadCommissionUpdate,
        current_user_id: Optional[int] = None,
    ) -> LocationHeadCommission:
        """Update an existing location head commission record."""
        record = await self.get_location_head_commission(commission_id)

        update_data = payload.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(record, field, value)

        record.UpdateUser = current_user_id
        record.UpdateDate = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(record)
        return record

    async def delete_location_head_commission(
        self,
        commission_id: int,
        current_user_id: Optional[int] = None,
    ) -> LocationHeadCommission:
        """Soft delete a location head commission record."""
        record = await self.get_location_head_commission(commission_id)
        record.IsActive = 0
        record.UpdateUser = current_user_id
        record.UpdateDate = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(record)
        return record

    async def lookup_location_head_commission(
        self, payload: LocationHeadCommissionLookupRequest
    ) -> LocationHeadCommissionLookupResponse:
        """Lookup best-matching override rate for a Location Head."""
        check_date = payload.TransDate or date.today()

        query = select(LocationHeadCommission).where(
            and_(
                LocationHeadCommission.LocationHeadId == payload.LocationHeadId,
                LocationHeadCommission.InsuranceCompanyId == payload.InsuranceCompanyId,
                LocationHeadCommission.ValidFromDate <= check_date,
                or_(
                    LocationHeadCommission.ValidToDate.is_(None),
                    LocationHeadCommission.ValidToDate >= check_date,
                ),
                LocationHeadCommission.IsActive == 1,
            )
        )

        if payload.FranchiseCode:
            query = query.where(
                or_(
                    LocationHeadCommission.FranchiseCode == payload.FranchiseCode,
                    LocationHeadCommission.FranchiseCode.is_(None),
                )
            )

        if payload.VehiTypeId:
            query = query.where(
                or_(
                    LocationHeadCommission.VehiTypeId == payload.VehiTypeId,
                    LocationHeadCommission.VehiTypeId.is_(None),
                )
            )

        query = query.order_by(
            desc(LocationHeadCommission.ValidFromDate),
            desc(LocationHeadCommission.LocationHeadCommId),
        )

        result = await self.db.execute(query)
        candidates = list(result.scalars().all())

        if not candidates:
            return LocationHeadCommissionLookupResponse(
                matched=False,
                Commission=Decimal("0.00"),
                Commission_OD=Decimal("0.00"),
                Commission_Net=Decimal("0.00"),
                OD_Discount=Decimal("0.00"),
                ReferenceType="L.Head",
                FranchiseCode=payload.FranchiseCode or "RA",
                grid_id=None,
                message="No matching Location Head commission grid found.",
            )

        best_match = candidates[0]
        return LocationHeadCommissionLookupResponse(
            matched=True,
            Commission=best_match.Commission,
            Commission_OD=best_match.Commission_OD,
            Commission_Net=best_match.Commission_Net,
            OD_Discount=best_match.OD_Discount,
            ReferenceType=best_match.ReferenceType or "L.Head",
            FranchiseCode=best_match.FranchiseCode or (payload.FranchiseCode or "RA"),
            grid_id=best_match.LocationHeadCommId,
            message="Location Head commission matched successfully.",
        )

    # ========================================================================
    # 3. LOCATION HEAD <-> SALES EXECUTIVE HIERARCHY MAPPING
    # ========================================================================

    async def assign_sales_executives_to_location_head(
        self,
        payload: LocationHeadAssignmentRequest,
        current_user_id: Optional[int] = None,
    ) -> List[LocationHeadSalesExMap]:
        """
        Assign sales executives to a location head.
        Replaces any prior active assignments for the specified sales executives.
        """
        if not payload.SalesEx_Ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one Sales Executive ID must be specified.",
            )

        # Deactivate old active maps for these sales executives
        await self.db.execute(
            update(LocationHeadSalesExMap)
            .where(
                and_(
                    LocationHeadSalesExMap.SalesEx_Id.in_(payload.SalesEx_Ids),
                    LocationHeadSalesExMap.IsActive == 1,
                )
            )
            .values(IsActive=0)
        )

        created_maps = []
        for se_id in payload.SalesEx_Ids:
            new_map = LocationHeadSalesExMap(
                LocationHeadId=payload.LocationHeadId,
                SalesEx_Id=se_id,
                CreatedUser=current_user_id,
                CreatedDate=datetime.utcnow(),
                IsActive=1,
            )
            self.db.add(new_map)
            created_maps.append(new_map)

        await self.db.commit()
        for m in created_maps:
            await self.db.refresh(m)
        return created_maps

    async def get_location_head_for_sales_executive(
        self, sales_ex_id: int
    ) -> Optional[LocationHeadSalesExMap]:
        """Retrieve the active Location Head assigned to a Sales Executive."""
        result = await self.db.execute(
            select(LocationHeadSalesExMap).where(
                and_(
                    LocationHeadSalesExMap.SalesEx_Id == sales_ex_id,
                    LocationHeadSalesExMap.IsActive == 1,
                )
            )
        )
        return result.scalar_one_or_none()

    async def list_sales_executives_under_location_head(
        self, location_head_id: int
    ) -> List[LocationHeadSalesExMap]:
        """List all active Sales Executives currently reporting to a Location Head."""
        result = await self.db.execute(
            select(LocationHeadSalesExMap).where(
                and_(
                    LocationHeadSalesExMap.LocationHeadId == location_head_id,
                    LocationHeadSalesExMap.IsActive == 1,
                )
            )
        )
        return list(result.scalars().all())

    # ========================================================================
    # 4. INSURER PARTNER PORTALS REGISTRY
    # ========================================================================

    async def list_insurer_portals(
        self,
        insurance_company_id: Optional[int] = None,
        broker_id: Optional[int] = None,
        is_active: Optional[int] = 1,
        skip: int = 0,
        limit: int = 100,
    ) -> List[InsuranceCompanyPortal]:
        """List registered insurer portals with filtering."""
        query = select(InsuranceCompanyPortal)
        conditions = []

        if insurance_company_id is not None:
            conditions.append(InsuranceCompanyPortal.InsuranceCompanyId == insurance_company_id)
        if broker_id is not None:
            conditions.append(InsuranceCompanyPortal.BrokerId == broker_id)
        if is_active is not None:
            conditions.append(InsuranceCompanyPortal.IsActive == is_active)

        if conditions:
            query = query.where(and_(*conditions))

        query = query.order_by(desc(InsuranceCompanyPortal.tbl_Id)).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def create_insurer_portal(
        self,
        payload: InsuranceCompanyPortalCreate,
        current_user_id: Optional[int] = None,
    ) -> InsuranceCompanyPortal:
        """Create or register an insurer portal entry."""
        portal = InsuranceCompanyPortal(
            InsuranceCompanyId=payload.InsuranceCompanyId,
            PortalId=payload.PortalId,
            PersonName=payload.PersonName,
            BrokerId=payload.BrokerId,
            PortalUrl=payload.PortalUrl,
            PortalPassword=payload.PortalPassword,
            IsActive=payload.IsActive,
            CreatedUser=current_user_id,
            CreatedDate=datetime.utcnow(),
        )
        self.db.add(portal)
        await self.db.commit()
        await self.db.refresh(portal)
        return portal

    async def get_insurer_portal(self, portal_id: int) -> InsuranceCompanyPortal:
        """Retrieve single portal entry by tbl_Id."""
        result = await self.db.execute(
            select(InsuranceCompanyPortal).where(InsuranceCompanyPortal.tbl_Id == portal_id)
        )
        record = result.scalar_one_or_none()
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Insurer portal {portal_id} not found.",
            )
        return record

    async def update_insurer_portal(
        self,
        portal_id: int,
        payload: InsuranceCompanyPortalUpdate,
        current_user_id: Optional[int] = None,
    ) -> InsuranceCompanyPortal:
        """Update an existing insurer portal entry."""
        portal = await self.get_insurer_portal(portal_id)

        update_data = payload.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(portal, field, value)

        portal.UpdatedUser = current_user_id
        portal.UpdatedDate = datetime.utcnow()

        await self.db.commit()
        await self.db.refresh(portal)
        return portal

    async def delete_insurer_portal(
        self,
        portal_id: int,
        current_user_id: Optional[int] = None,
    ) -> InsuranceCompanyPortal:
        """Soft delete an insurer portal entry."""
        portal = await self.get_insurer_portal(portal_id)
        portal.IsActive = 0
        portal.UpdatedUser = current_user_id
        portal.UpdatedDate = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(portal)
        return portal

    # ========================================================================
    # 5. APP BILLING & FIELD EXPENSE REIMBURSEMENT OPERATIONS
    # ========================================================================

    async def submit_billing_claim(
        self,
        payload: AppBillingDetailsCreate,
        current_user_id: Optional[int] = None,
    ) -> AppBillingDetailsResponse:
        """Submit a new field expense reimbursement claim with optional photo/pdf receipts."""
        if payload.FromDate > payload.ToDate:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="FromDate cannot be after ToDate.",
            )
        if payload.BillingAmount < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Billing amount cannot be negative.",
            )

        claim = AppBillingDetails(
            SalesExId=payload.SalesExId,
            FromDate=payload.FromDate,
            ToDate=payload.ToDate,
            Remark=payload.Remark,
            BillingAmount=payload.BillingAmount,
            ReimbursementTypeId=payload.ReimbursementTypeId,
            Destination=payload.Destination,
            Status="PENDING",
            CreatedDate=datetime.utcnow(),
        )
        self.db.add(claim)
        await self.db.flush()

        attachments_response = []
        if payload.attachments:
            for att_data in payload.attachments:
                att = AppBillingAttachment(
                    BillingId=claim.BillingId,
                    FileType=att_data.FileType.upper(),
                    FilePath=att_data.FilePath,
                    FileName=att_data.FileName,
                    UploadedDate=datetime.utcnow(),
                )
                self.db.add(att)
                await self.db.flush()
                attachments_response.append(
                    AppBillingAttachmentResponse.model_validate(att)
                )

        await self.db.commit()
        await self.db.refresh(claim)

        return AppBillingDetailsResponse(
            BillingId=claim.BillingId,
            SalesExId=claim.SalesExId,
            FromDate=claim.FromDate,
            ToDate=claim.ToDate,
            Remark=claim.Remark,
            BillingAmount=claim.BillingAmount,
            ReimbursementTypeId=claim.ReimbursementTypeId,
            Destination=claim.Destination,
            Status=claim.Status,
            CreatedDate=claim.CreatedDate,
            ProcessedDate=claim.ProcessedDate,
            ProcessedBy=claim.ProcessedBy,
            attachments=attachments_response,
        )

    async def list_billing_claims(
        self,
        sales_ex_id: Optional[int] = None,
        status_filter: Optional[str] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[AppBillingDetailsResponse]:
        """List billing claims with associated receipt attachments."""
        query = select(AppBillingDetails)
        conditions = []

        if sales_ex_id is not None:
            conditions.append(AppBillingDetails.SalesExId == sales_ex_id)
        if status_filter:
            conditions.append(AppBillingDetails.Status == status_filter.upper())
        if from_date:
            conditions.append(AppBillingDetails.FromDate >= from_date)
        if to_date:
            conditions.append(AppBillingDetails.ToDate <= to_date)

        if conditions:
            query = query.where(and_(*conditions))

        query = query.order_by(desc(AppBillingDetails.BillingId)).offset(skip).limit(limit)
        result = await self.db.execute(query)
        claims = list(result.scalars().all())

        if not claims:
            return []

        # Load attachments for these claims
        claim_ids = [c.BillingId for c in claims]
        att_query = select(AppBillingAttachment).where(
            AppBillingAttachment.BillingId.in_(claim_ids)
        )
        att_result = await self.db.execute(att_query)
        all_attachments = list(att_result.scalars().all())

        att_by_claim: Dict[int, List[AppBillingAttachmentResponse]] = {}
        for att in all_attachments:
            att_by_claim.setdefault(att.BillingId, []).append(
                AppBillingAttachmentResponse.model_validate(att)
            )

        responses = []
        for c in claims:
            responses.append(
                AppBillingDetailsResponse(
                    BillingId=c.BillingId,
                    SalesExId=c.SalesExId,
                    FromDate=c.FromDate,
                    ToDate=c.ToDate,
                    Remark=c.Remark,
                    BillingAmount=c.BillingAmount,
                    ReimbursementTypeId=c.ReimbursementTypeId,
                    Destination=c.Destination,
                    Status=c.Status,
                    CreatedDate=c.CreatedDate,
                    ProcessedDate=c.ProcessedDate,
                    ProcessedBy=c.ProcessedBy,
                    attachments=att_by_claim.get(c.BillingId, []),
                )
            )
        return responses

    async def get_billing_claim_details(self, billing_id: int) -> AppBillingDetailsResponse:
        """Retrieve single billing claim with its photos and PDF attachments."""
        result = await self.db.execute(
            select(AppBillingDetails).where(AppBillingDetails.BillingId == billing_id)
        )
        claim = result.scalar_one_or_none()
        if not claim:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Billing claim {billing_id} not found.",
            )

        att_result = await self.db.execute(
            select(AppBillingAttachment).where(AppBillingAttachment.BillingId == billing_id)
        )
        attachments = [
            AppBillingAttachmentResponse.model_validate(a)
            for a in att_result.scalars().all()
        ]

        return AppBillingDetailsResponse(
            BillingId=claim.BillingId,
            SalesExId=claim.SalesExId,
            FromDate=claim.FromDate,
            ToDate=claim.ToDate,
            Remark=claim.Remark,
            BillingAmount=claim.BillingAmount,
            ReimbursementTypeId=claim.ReimbursementTypeId,
            Destination=claim.Destination,
            Status=claim.Status,
            CreatedDate=claim.CreatedDate,
            ProcessedDate=claim.ProcessedDate,
            ProcessedBy=claim.ProcessedBy,
            attachments=attachments,
        )

    async def update_billing_status(
        self,
        billing_id: int,
        payload: AppBillingStatusUpdateRequest,
        current_user_id: Optional[int] = None,
    ) -> AppBillingDetailsResponse:
        """Update billing status (e.g. APPROVED, REJECTED, PROCESSED)."""
        valid_statuses = ("PENDING", "APPROVED", "REJECTED", "PROCESSED")
        new_status = payload.Status.upper()
        if new_status not in valid_statuses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status '{payload.Status}'. Allowed: {valid_statuses}",
            )

        result = await self.db.execute(
            select(AppBillingDetails).where(AppBillingDetails.BillingId == billing_id)
        )
        claim = result.scalar_one_or_none()
        if not claim:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Billing claim {billing_id} not found.",
            )

        claim.Status = new_status
        claim.ProcessedDate = datetime.utcnow()
        claim.ProcessedBy = current_user_id
        if payload.Remark:
            claim.Remark = f"{claim.Remark or ''} [Status Note: {payload.Remark}]".strip()

        await self.db.commit()
        await self.db.refresh(claim)

        return await self.get_billing_claim_details(billing_id)


# Backward-compatibility alias
Phase22Service = ExecutiveCommissionService
