"""
Phase 26 Service Layer:
Emergency Roadside Claim Assistance & Accident Intake Lifecycle.
Physical Tables: tbl_claimassistance, tbl_claimassistanceimg.
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
import logging
from fastapi import HTTPException, status
from sqlalchemy import select, update, func, and_, or_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.phase26_features import ClaimAssistance, ClaimAssistanceImg
from app.models.master import InsuranceCompany
from app.models.user import User
from app.repositories.notification import NotificationRepository
from app.core.rbac import PrincipalContext, is_global_admin_role, is_global_read_role
from app.schemas.phase26 import (
    ClaimAssistanceCreate,
    ClaimAssistanceUpdate,
    ClaimAssistanceAssignClaimNo,
    ClaimAssistanceReadStatusUpdate,
    ClaimAssistanceResponse,
    ClaimAssistanceImgResponse,
    ClaimAssistanceSummaryResponse,
)

logger = logging.getLogger(__name__)


class Phase26Service:
    """Service orchestrating Emergency Roadside Claim Assistance & Accident Intake."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.notif_repo = NotificationRepository(db)

    # =========================================================================
    # 1. EMERGENCY INTAKE & CREATION
    # =========================================================================

    async def create_claim_assistance(
        self,
        payload: ClaimAssistanceCreate,
        principal: Optional[PrincipalContext] = None,
    ) -> ClaimAssistanceResponse:
        """
        Records a new emergency roadside claim assistance / accident intimation.
        Legacy Parity: Service.asmx.cs -> InsertClaimAssistance (Sp_InsertAppClaim + sp_InsertClaimImg).
        """
        # Validate Underwriting Insurance Company
        comp_stmt = select(InsuranceCompany).where(
            InsuranceCompany.InsuranceCompanyId == payload.insurance_company_id
        )
        comp = (await self.db.execute(comp_stmt)).scalars().first()
        if not comp:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Insurance Company ID {payload.insurance_company_id} not found.",
            )

        # Enforce server-side principal context for non-admins (GAP-5F-03)
        effective_branch = payload.branch_id or 101
        effective_agent = payload.agent_id or 0
        user_name = "MOBILE_APP"

        if principal:
            user_name = principal.username or "APP_USER"
            if not is_global_admin_role(principal.role_name):
                if principal.agent_id:
                    effective_agent = principal.agent_id
                    effective_branch = principal.branch_id or 101
                elif principal.branch_id:
                    effective_branch = principal.branch_id

        assistance = ClaimAssistance(
            CustomerId=payload.customer_id or (principal.user_id if principal and not principal.agent_id else None),
            InsuranceCompanyId=payload.insurance_company_id,
            IntimationDate=datetime.utcnow(),
            VehNo=payload.veh_no.strip().upper(),
            DateofAccident=payload.date_of_accident,
            Accidenttime=payload.accident_time,
            spot=payload.spot,
            Reason=payload.reason,
            DriverName=payload.driver_name,
            DriverLicenseNo=payload.driver_license_no,
            GarageName=payload.garage_name,
            GarageAddr=payload.garage_addr,
            Garagecontact=payload.garage_contact,
            ClaimNo=None,
            Status="INTIMATED",
            ReadStatus=0,
            isdeleted=0,
            BranchId=effective_branch,
            AgentId=effective_agent,
            SalesExId=payload.sales_ex_id or 0,
            CreatedDate=datetime.utcnow(),
            CreatedUser=user_name,
        )
        self.db.add(assistance)
        await self.db.flush()

        # Handle damage photographic evidence
        if payload.images:
            for img_path in payload.images:
                if img_path and img_path.strip():
                    img = ClaimAssistanceImg(
                        ClaimAssistanceId=assistance.ClaimAssistanceId,
                        ImgPath=img_path.strip(),
                        CreatedDate=datetime.utcnow(),
                    )
                    self.db.add(img)
            await self.db.flush()

        await self.db.commit()
        return await self.get_claim_assistance(assistance.ClaimAssistanceId, principal=principal)

    # =========================================================================
    # 2. DETAIL RETRIEVAL & QUERYING
    # =========================================================================

    async def get_claim_assistance(
        self,
        assistance_id: int,
        principal: Optional[PrincipalContext] = None,
    ) -> ClaimAssistanceResponse:
        """
        Retrieves claim assistance record by ID with eager-loaded photo evidence.
        Enforces tenant/branch isolation for non-global-read roles.
        Legacy Parity: DAL_selectclaimassistancedetailsByID / sp_selectclaimassistancedetailsByID.
        """
        stmt = (
            select(ClaimAssistance)
            .options(selectinload(ClaimAssistance.images))
            .where(
                ClaimAssistance.ClaimAssistanceId == assistance_id,
                ClaimAssistance.isdeleted == 0,
            )
        )
        record = (await self.db.execute(stmt)).scalars().first()
        if not record:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Claim Assistance ID {assistance_id} not found or has been deleted.",
            )

        # Tenant & agency access validation
        if principal and not (is_global_admin_role(principal.role_name) or is_global_read_role(principal.role_name)):
            if principal.agent_id:
                if record.AgentId != principal.agent_id and record.CustomerId != principal.user_id:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Access denied to claim assistance record outside authorized agency.",
                    )
            elif principal.branch_id:
                if record.BranchId != principal.branch_id:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Access denied to claim assistance record outside authorized branch.",
                    )

        # Resolve Insurance Company Name
        comp_stmt = select(InsuranceCompany.InsuranceCompany).where(
            InsuranceCompany.InsuranceCompanyId == record.InsuranceCompanyId
        )
        comp_name = (await self.db.execute(comp_stmt)).scalar_one_or_none()

        response = ClaimAssistanceResponse.model_validate(record)
        response.insurance_company_name = comp_name
        return response

    async def list_claim_assistance(
        self,
        skip: int = 0,
        limit: int = 50,
        veh_no: Optional[str] = None,
        insurance_company_id: Optional[int] = None,
        read_status: Optional[int] = None,
        status_filter: Optional[str] = None,
        branch_id: Optional[int] = None,
        principal: Optional[PrincipalContext] = None,
    ) -> List[ClaimAssistanceResponse]:
        """
        Lists claim assistance intimations with multi-criteria filtering and RBAC scoping.
        Legacy Parity: DAL_selectclaimassistancedetails / adm_claimAssistancereport.aspx.cs.
        """
        query = (
            select(ClaimAssistance)
            .options(selectinload(ClaimAssistance.images))
            .where(ClaimAssistance.isdeleted == 0)
        )

        if veh_no:
            query = query.where(ClaimAssistance.VehNo.ilike(f"%{veh_no.strip()}%"))
        if insurance_company_id:
            query = query.where(ClaimAssistance.InsuranceCompanyId == insurance_company_id)
        if read_status is not None:
            query = query.where(ClaimAssistance.ReadStatus == read_status)
        if status_filter:
            query = query.where(ClaimAssistance.Status == status_filter.strip().upper())

        # Role-based scoping: non-global readers are confined to their branch/agent
        if principal and not (is_global_admin_role(principal.role_name) or is_global_read_role(principal.role_name)):
            if principal.agent_id:
                query = query.where(
                    or_(
                        ClaimAssistance.AgentId == principal.agent_id,
                        ClaimAssistance.CustomerId == principal.user_id,
                    )
                )
            elif principal.branch_id:
                query = query.where(ClaimAssistance.BranchId == principal.branch_id)
        elif branch_id:
            query = query.where(ClaimAssistance.BranchId == branch_id)

        query = query.order_by(ClaimAssistance.ClaimAssistanceId.desc()).offset(skip).limit(limit)
        records = (await self.db.execute(query)).scalars().all()

        results: List[ClaimAssistanceResponse] = []
        for r in records:
            comp_stmt = select(InsuranceCompany.InsuranceCompany).where(
                InsuranceCompany.InsuranceCompanyId == r.InsuranceCompanyId
            )
            comp_name = (await self.db.execute(comp_stmt)).scalar_one_or_none()
            resp = ClaimAssistanceResponse.model_validate(r)
            resp.insurance_company_name = comp_name
            results.append(resp)

        return results

    # =========================================================================
    # 3. TRIAGE & DETAIL UPDATES
    # =========================================================================

    async def update_claim_assistance(
        self,
        assistance_id: int,
        payload: ClaimAssistanceUpdate,
        principal: PrincipalContext,
    ) -> ClaimAssistanceResponse:
        """
        Updates roadside accident triage details (driver, garage, spot, reason, status).
        Enforces branch isolation on modification.
        Legacy Parity: UpdateClaimAssistance.aspx.cs -> DAL_UpdateAppClaimAssistancenew.
        """
        record = await self.db.get(ClaimAssistance, assistance_id)
        if not record or record.isdeleted == 1:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Claim Assistance ID {assistance_id} not found.",
            )

        if not is_global_admin_role(principal.role_name):
            if principal.branch_id and record.BranchId != principal.branch_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to modify claim assistance record outside authorized branch.",
                )

        if payload.driver_name is not None:
            record.DriverName = payload.driver_name
        if payload.driver_license_no is not None:
            record.DriverLicenseNo = payload.driver_license_no
        if payload.garage_name is not None:
            record.GarageName = payload.garage_name
        if payload.garage_addr is not None:
            record.GarageAddr = payload.garage_addr
        if payload.garage_contact is not None:
            record.Garagecontact = payload.garage_contact
        if payload.spot is not None:
            record.spot = payload.spot
        if payload.reason is not None:
            record.Reason = payload.reason
        if payload.status is not None:
            record.Status = payload.status.upper()

        record.UpdatedDate = datetime.utcnow()
        record.UpdatedUser = principal.username or "STAFF"

        await self.db.commit()
        return await self.get_claim_assistance(assistance_id, principal=principal)

    # =========================================================================
    # 4. FORMAL CLAIM NUMBER LINKAGE & NOTIFICATIONS
    # =========================================================================

    async def assign_claim_number(
        self,
        assistance_id: int,
        payload: ClaimAssistanceAssignClaimNo,
        principal: PrincipalContext,
    ) -> ClaimAssistanceResponse:
        """
        Assigns official insurer Claim Number to roadside intimation and dispatches SMS/inbox notifications.
        Includes duplicate assignment protection and transaction safety.
        Legacy Parity: adm_claimAssistancereport.aspx.cs -> BLL_UpdateClaimNo (sp_UpdateClaimNo).
        """
        record = await self.db.get(ClaimAssistance, assistance_id)
        if not record or record.isdeleted == 1:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Claim Assistance ID {assistance_id} not found.",
            )

        if not is_global_admin_role(principal.role_name):
            if principal.branch_id and record.BranchId != principal.branch_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to assign claim number outside authorized branch.",
                )

        clean_claim_no = payload.claim_no.strip()

        # Duplicate / Repeated Request Handling
        if record.ClaimNo:
            if record.ClaimNo == clean_claim_no:
                # Idempotent re-submission: return current state without double notification
                return await self.get_claim_assistance(assistance_id, principal=principal)
            else:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Claim Assistance ID {assistance_id} is already linked to Claim Number '{record.ClaimNo}'.",
                )

        record.ClaimNo = clean_claim_no
        record.ClaimNoUpdateDate = datetime.utcnow()
        record.ClaimNoUpdateUser = principal.username or "STAFF"
        record.Status = "CLAIM_NO_ASSIGNED"
        record.ReadStatus = 1  # Processed by operator
        record.UpdatedDate = datetime.utcnow()
        record.UpdatedUser = principal.username or "STAFF"

        # Notification parity: SMS Dispatch
        msg_text = f"For {record.VehNo} Claim no. is Generated. Claim No: {clean_claim_no}. Please Check."
        if payload.dispatch_sms and record.Garagecontact:
            try:
                await self.notif_repo.log_sms(
                    mobile_number=record.Garagecontact,
                    message_text=msg_text,
                    template_id="CLAIM_NO_GEN",
                    provider="INTERNAL_MOCK",
                    status="SENT",
                    provider_message_id=f"MOCK-SMS-{assistance_id}",
                )
            except Exception as notif_err:
                logger.warning("Failed to log SMS notification: %s", notif_err)

        # Notification parity: Internal Inbox Dispatch (Flag="CL")
        if payload.dispatch_inbox and record.CustomerId:
            try:
                msg_master = await self.notif_repo.create_message_master(msg_text)
                await self.notif_repo.create_message_detail(
                    message_id=msg_master.MessageID,
                    user_id=record.CustomerId,
                    flag="CL",
                    opr="Insert",
                )
            except Exception as inbox_err:
                logger.warning("Failed to dispatch internal inbox notification: %s", inbox_err)

        await self.db.commit()
        return await self.get_claim_assistance(assistance_id, principal=principal)

    # =========================================================================
    # 5. READ STATUS & LIFECYCLE MANAGEMENT
    # =========================================================================

    async def update_read_status(
        self,
        assistance_id: int,
        payload: ClaimAssistanceReadStatusUpdate,
        principal: PrincipalContext,
    ) -> ClaimAssistanceResponse:
        """
        Updates read status (0=Unread, 1=Read).
        Legacy Parity: DAL_UpdateClaimAssistanceReadStatus / sp_UpdateClaimAssistanceReadStatus.
        """
        record = await self.db.get(ClaimAssistance, assistance_id)
        if not record or record.isdeleted == 1:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Claim Assistance ID {assistance_id} not found.",
            )

        if not is_global_admin_role(principal.role_name):
            if principal.branch_id and record.BranchId != principal.branch_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to update read status outside authorized branch.",
                )

        record.ReadStatus = payload.read_status
        record.UpdatedDate = datetime.utcnow()
        record.UpdatedUser = principal.username or "STAFF"

        await self.db.commit()
        return await self.get_claim_assistance(assistance_id, principal=principal)

    async def delete_claim_assistance(
        self,
        assistance_id: int,
        principal: PrincipalContext,
    ) -> Dict[str, Any]:
        """
        Performs soft deletion of claim assistance record.
        Legacy Parity: DAL_deleteClaimAssistanceReadStatus / sp_deleteClaimAssistanceReadStatus.
        """
        record = await self.db.get(ClaimAssistance, assistance_id)
        if not record or record.isdeleted == 1:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Claim Assistance ID {assistance_id} not found.",
            )

        if not is_global_admin_role(principal.role_name):
            if principal.branch_id and record.BranchId != principal.branch_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied to delete claim assistance record outside authorized branch.",
                )

        record.isdeleted = 1
        record.UpdatedDate = datetime.utcnow()
        record.UpdatedUser = principal.username or "STAFF"

        await self.db.commit()
        return {"success": True, "message": f"Claim Assistance ID {assistance_id} successfully deleted."}

    # =========================================================================
    # 6. DASHBOARD & OPERATIONAL SUMMARY METRICS
    # =========================================================================

    async def get_summary_metrics(
        self,
        branch_id: Optional[int] = None,
        principal: Optional[PrincipalContext] = None,
    ) -> ClaimAssistanceSummaryResponse:
        """
        Aggregates dashboard counts for roadside claim assistance intimations.
        Enforces branch scoping for branch operators.
        Legacy Parity: Dashboard_claimAssistance.aspx.cs -> DAL_DashboardClaimAssistanc / DAL_selectcountclaimassistance.
        """
        effective_branch = branch_id
        if principal and not (is_global_admin_role(principal.role_name) or is_global_read_role(principal.role_name)):
            effective_branch = principal.branch_id

        base_cond = [ClaimAssistance.isdeleted == 0]
        if effective_branch:
            base_cond.append(ClaimAssistance.BranchId == effective_branch)

        # Total intimations
        stmt_total = select(func.count(ClaimAssistance.ClaimAssistanceId)).where(and_(*base_cond))
        total = (await self.db.execute(stmt_total)).scalar_one() or 0

        # Unread intimations
        stmt_unread = select(func.count(ClaimAssistance.ClaimAssistanceId)).where(
            and_(*base_cond, ClaimAssistance.ReadStatus == 0)
        )
        unread = (await self.db.execute(stmt_unread)).scalar_one() or 0

        # Read intimations
        stmt_read = select(func.count(ClaimAssistance.ClaimAssistanceId)).where(
            and_(*base_cond, ClaimAssistance.ReadStatus == 1)
        )
        read = (await self.db.execute(stmt_read)).scalar_one() or 0

        # Pending claim assignment
        stmt_pending = select(func.count(ClaimAssistance.ClaimAssistanceId)).where(
            and_(*base_cond, or_(ClaimAssistance.ClaimNo == None, ClaimAssistance.ClaimNo == ""))
        )
        pending = (await self.db.execute(stmt_pending)).scalar_one() or 0

        # Claim assigned
        stmt_assigned = select(func.count(ClaimAssistance.ClaimAssistanceId)).where(
            and_(*base_cond, ClaimAssistance.ClaimNo != None, ClaimAssistance.ClaimNo != "")
        )
        assigned = (await self.db.execute(stmt_assigned)).scalar_one() or 0

        return ClaimAssistanceSummaryResponse(
            total_intimations=total,
            unread_intimations=unread,
            read_intimations=read,
            pending_claim_assignment=pending,
            claim_assigned=assigned,
        )
