"""
Business Services for Phase 20 Features — Batch 1.
Covers:
1. Bulletins & Circulars (F-20-001)
2. Mobile Customer Helpdesk & Support Chat (F-20-002)
3. Web Notification Alerts (F-20-003)
4. Partner Loyalty & Reward Points (F-20-004)
"""
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Dict, Any
from sqlalchemy import select, update, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.models.operational_extensions import (
    Circular,
    CustomerHelp,
    AppChatBoard,
    WebNotification,
    RewardPoint,
    ClusterMaster,
    ClusterDetail,
    ClusterWiseBrokerGrid,
    ClusterWiseAgentGrid,
    GridDeclineMaster,
    DeclineModel,
)
from app.models.user import User
from app.schemas.operational_extensions import (
    CircularCreate,
    CircularUpdate,
    CustomerHelpCreate,
    CustomerHelpResolve,
    ChatBoardMessageCreate,
    ChatBoardReplyCreate,
    WebNotificationCreate,
    RewardPointCreate,
    ClusterMasterCreate,
    ClusterDetailCreate,
    ClusterWiseBrokerGridCreate,
    ClusterWiseAgentGridCreate,
    GridDeclineCreate,
    DeclineModelDetailCreate,
    UnderwritingDeclineCheckRequest,
)


class OperationalExtensionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ========================================================================
    # 1. CIRCULARS & BULLETINS (F-20-001)
    # ========================================================================

    async def create_circular(self, payload: CircularCreate, user: User) -> Circular:
        circular = Circular(
            circulardate=payload.circulardate or date.today(),
            subject=payload.subject,
            pdfpath=payload.pdfpath,
            is_active=payload.is_active if payload.is_active is not None else 1,
            created_by=user.UserId,
            created_at=datetime.utcnow(),
        )
        self.db.add(circular)
        await self.db.commit()
        await self.db.refresh(circular)
        return circular

    async def list_circulars(
        self, active_only: bool = True, skip: int = 0, limit: int = 50
    ) -> List[Circular]:
        query = select(Circular)
        if active_only:
            query = query.where(Circular.is_active == 1)
        query = query.order_by(desc(Circular.circulardate), desc(Circular.circularid)).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_circular(self, circular_id: int) -> Circular:
        circular = await self.db.get(Circular, circular_id)
        if not circular:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Circular with ID {circular_id} not found",
            )
        return circular

    async def update_circular(self, circular_id: int, payload: CircularUpdate) -> Circular:
        circular = await self.get_circular(circular_id)
        if payload.subject is not None:
            circular.subject = payload.subject
        if payload.circulardate is not None:
            circular.circulardate = payload.circulardate
        if payload.pdfpath is not None:
            circular.pdfpath = payload.pdfpath
        if payload.is_active is not None:
            circular.is_active = payload.is_active
        circular.updated_at = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(circular)
        return circular

    async def delete_circular(self, circular_id: int) -> bool:
        circular = await self.get_circular(circular_id)
        circular.is_active = 0
        circular.updated_at = datetime.utcnow()
        await self.db.commit()
        return True

    # ========================================================================
    # 2. CUSTOMER HELPDESK & SUPPORT CHAT (F-20-002)
    # ========================================================================

    async def create_help_ticket(self, payload: CustomerHelpCreate, user: User) -> CustomerHelp:
        ticket = CustomerHelp(
            CustomerId=payload.CustomerId,
            HelpId=payload.HelpId,
            Subject=payload.Subject,
            Message=payload.Message,
            RegistrationNo=payload.RegistrationNo,
            PolicyNo=payload.PolicyNo,
            Status="OPEN",
            CustDate=datetime.utcnow(),
            is_deleted=0,
        )
        self.db.add(ticket)
        await self.db.commit()
        await self.db.refresh(ticket)
        return ticket

    async def list_help_tickets(
        self,
        status_filter: Optional[str] = None,
        customer_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[CustomerHelp]:
        query = select(CustomerHelp).where(CustomerHelp.is_deleted == 0)
        if status_filter:
            query = query.where(CustomerHelp.Status == status_filter)
        if customer_id:
            query = query.where(CustomerHelp.CustomerId == customer_id)
        query = query.order_by(desc(CustomerHelp.CustDate)).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_help_ticket(self, ticket_id: int) -> CustomerHelp:
        ticket = await self.db.get(CustomerHelp, ticket_id)
        if not ticket or ticket.is_deleted == 1:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Customer help ticket {ticket_id} not found",
            )
        return ticket

    async def resolve_help_ticket(
        self, ticket_id: int, payload: CustomerHelpResolve, user: User
    ) -> CustomerHelp:
        ticket = await self.get_help_ticket(ticket_id)
        ticket.Status = payload.Status
        ticket.ResolutionRemark = payload.ResolutionRemark
        ticket.ResolvedBy = user.UserId
        ticket.ResolvedDate = datetime.utcnow()
        await self.db.commit()
        await self.db.refresh(ticket)
        return ticket

    async def post_chat_message(self, payload: ChatBoardMessageCreate, user: User) -> AppChatBoard:
        role_label = getattr(user, "UserRole", None) or "USER"
        msg = AppChatBoard(
            CustHelpId=payload.CustHelpId,
            UserRoleId=getattr(user, "UserRoleId", None),
            ReferenceAgentId=payload.ReferenceAgentId,
            CoordinatorId=payload.CoordinatorId,
            RegistrationNo=payload.RegistrationNo,
            ChatText=payload.ChatText,
            ChatByUser=str(role_label),
            SenderUserId=user.UserId,
            Remark=payload.Remark,
            AttachmentPath=payload.AttachmentPath,
            IsRead=0,
            CreatedDate=datetime.utcnow(),
        )
        self.db.add(msg)
        await self.db.commit()
        await self.db.refresh(msg)
        return msg

    async def list_chat_messages(
        self,
        cust_help_id: Optional[int] = None,
        agent_id: Optional[int] = None,
        registration_no: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[AppChatBoard]:
        query = select(AppChatBoard)
        if cust_help_id:
            query = query.where(AppChatBoard.CustHelpId == cust_help_id)
        if agent_id:
            query = query.where(AppChatBoard.ReferenceAgentId == agent_id)
        if registration_no:
            query = query.where(AppChatBoard.RegistrationNo == registration_no)
        query = query.order_by(desc(AppChatBoard.CreatedDate)).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def reply_chat_message(
        self, chat_id: int, payload: ChatBoardReplyCreate, user: User
    ) -> AppChatBoard:
        msg = await self.db.get(AppChatBoard, chat_id)
        if not msg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Chat message {chat_id} not found",
            )
        msg.Reply = payload.Reply
        if payload.Remark:
            msg.Remark = payload.Remark
        msg.CoordinatorId = user.UserId
        msg.IsRead = 1
        await self.db.commit()
        await self.db.refresh(msg)
        return msg

    # ========================================================================
    # 3. WEB NOTIFICATION ALERTS (F-20-003)
    # ========================================================================

    async def create_web_notification(
        self, payload: WebNotificationCreate, user: User
    ) -> WebNotification:
        notification = WebNotification(
            NotMessage=payload.NotMessage,
            TargetRole=payload.TargetRole or "ALL",
            BranchId=payload.BranchId,
            Severity=payload.Severity or "INFO",
            IsActive=1,
            CreatedBy=user.UserId,
            CreatedDate=datetime.utcnow(),
            ExpiryDate=payload.ExpiryDate,
        )
        self.db.add(notification)
        await self.db.commit()
        await self.db.refresh(notification)
        return notification

    async def list_active_notifications(
        self, target_role: Optional[str] = None, branch_id: Optional[int] = None
    ) -> List[WebNotification]:
        now = datetime.utcnow()
        query = select(WebNotification).where(WebNotification.IsActive == 1)
        if target_role and target_role != "ALL":
            query = query.where(
                (WebNotification.TargetRole == "ALL") | (WebNotification.TargetRole == target_role)
            )
        if branch_id:
            query = query.where(
                (WebNotification.BranchId.is_(None)) | (WebNotification.BranchId == branch_id)
            )
        query = query.where(
            (WebNotification.ExpiryDate.is_(None)) | (WebNotification.ExpiryDate > now)
        )
        query = query.order_by(desc(WebNotification.CreatedDate))
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def dismiss_notification(self, notification_id: int) -> bool:
        notification = await self.db.get(WebNotification, notification_id)
        if not notification:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Notification {notification_id} not found",
            )
        notification.IsActive = 0
        await self.db.commit()
        return True

    # ========================================================================
    # 4. PARTNER LOYALTY & REWARD POINTS (F-20-004)
    # ========================================================================

    async def record_reward_points(
        self, payload: RewardPointCreate, user: User
    ) -> RewardPoint:
        # Determine latest balance
        last_entry_query = (
            select(RewardPoint)
            .where(
                RewardPoint.PartnerType == payload.PartnerType,
                RewardPoint.PartnerId == payload.PartnerId,
            )
            .order_by(desc(RewardPoint.RewardPointId))
            .limit(1)
        )
        last_entry_res = await self.db.execute(last_entry_query)
        last_entry = last_entry_res.scalar_one_or_none()

        prev_balance = last_entry.PointBalance if last_entry else Decimal("0.00")
        new_balance = prev_balance + payload.RewardPointGet - payload.RewardPointUtilizes
        if new_balance < Decimal("0.00"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient reward point balance. Available: {prev_balance}, requested redemption: {payload.RewardPointUtilizes}",
            )

        reward = RewardPoint(
            PartnerType=payload.PartnerType,
            PartnerId=payload.PartnerId,
            RefCustId=payload.RefCustId,
            PolicyId=payload.PolicyId,
            RewardDate=date.today(),
            RewardPointGet=payload.RewardPointGet,
            RewardPointUtilizes=payload.RewardPointUtilizes,
            PointBalance=new_balance,
            Remarks=payload.Remarks,
            CreatedDate=datetime.utcnow(),
        )
        self.db.add(reward)
        await self.db.commit()
        await self.db.refresh(reward)
        return reward

    async def get_partner_reward_points(
        self, partner_type: str, partner_id: int, skip: int = 0, limit: int = 50
    ) -> List[RewardPoint]:
        query = (
            select(RewardPoint)
            .where(
                RewardPoint.PartnerType == partner_type,
                RewardPoint.PartnerId == partner_id,
            )
            .order_by(desc(RewardPoint.RewardPointId))
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_reward_points_summary(
        self, partner_type: str, partner_id: int
    ) -> Dict[str, Any]:
        query = (
            select(
                func.coalesce(func.sum(RewardPoint.RewardPointGet), Decimal("0.00")),
                func.coalesce(func.sum(RewardPoint.RewardPointUtilizes), Decimal("0.00")),
                func.count(RewardPoint.RewardPointId),
            )
            .where(
                RewardPoint.PartnerType == partner_type,
                RewardPoint.PartnerId == partner_id,
            )
        )
        result = await self.db.execute(query)
        row = result.first()
        total_get = row[0] if row else Decimal("0.00")
        total_util = row[1] if row else Decimal("0.00")
        count = row[2] if row else 0

        # Latest balance
        last_entry_query = (
            select(RewardPoint.PointBalance)
            .where(
                RewardPoint.PartnerType == partner_type,
                RewardPoint.PartnerId == partner_id,
            )
            .order_by(desc(RewardPoint.RewardPointId))
            .limit(1)
        )
        last_res = await self.db.execute(last_entry_query)
        latest_bal = last_res.scalar_one_or_none() or Decimal("0.00")

        return {
            "PartnerType": partner_type,
            "PartnerId": partner_id,
            "TotalEarned": total_get,
            "TotalUtilized": total_util,
            "CurrentBalance": latest_bal,
            "TransactionsCount": count,
        }

    # ========================================================================
    # 5. GEOGRAPHIC CLUSTERS & COMMISSION GRIDS (F-20-005)
    # ========================================================================

    async def create_cluster(
        self, payload: ClusterMasterCreate, user: User
    ) -> ClusterMaster:
        cluster = ClusterMaster(
            InsuranceCompanyId=payload.InsuranceCompanyId,
            ClusterName=payload.ClusterName,
            StateId=payload.StateId,
            CreateUser=user.UserId,
            CreateDate=datetime.utcnow(),
            isdeleted=0,
        )
        self.db.add(cluster)
        await self.db.commit()
        await self.db.refresh(cluster)

        # Batch create RTO associations if provided
        if payload.RtoIds:
            for rto_id in payload.RtoIds:
                detail = ClusterDetail(
                    ClusterMId=cluster.ClusterMId,
                    InsuranceCompanyId=payload.InsuranceCompanyId,
                    RtoId=rto_id,
                    CreateUser=user.UserId,
                    CreateDate=datetime.utcnow(),
                )
                self.db.add(detail)
            await self.db.commit()

        return await self.get_cluster(cluster.ClusterMId)

    async def get_cluster(self, cluster_id: int) -> ClusterMaster:
        cluster = await self.db.get(ClusterMaster, cluster_id)
        if not cluster:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Cluster {cluster_id} not found",
            )
        # Load details
        q_det = select(ClusterDetail).where(ClusterDetail.ClusterMId == cluster_id)
        res = await self.db.execute(q_det)
        cluster.details = list(res.scalars().all())
        return cluster

    async def list_clusters(
        self,
        insurance_company_id: Optional[int] = None,
        state_id: Optional[int] = None,
        active_only: bool = True,
        skip: int = 0,
        limit: int = 50,
    ) -> List[ClusterMaster]:
        query = select(ClusterMaster).offset(skip).limit(limit).order_by(ClusterMaster.ClusterMId)
        if active_only:
            query = query.where(ClusterMaster.isdeleted == 0)
        if insurance_company_id:
            query = query.where(ClusterMaster.InsuranceCompanyId == insurance_company_id)
        if state_id:
            query = query.where(ClusterMaster.StateId == state_id)

        res = await self.db.execute(query)
        clusters = list(res.scalars().all())
        for c in clusters:
            q_det = select(ClusterDetail).where(ClusterDetail.ClusterMId == c.ClusterMId)
            det_res = await self.db.execute(q_det)
            c.details = list(det_res.scalars().all())
        return clusters

    async def add_cluster_rto(
        self, payload: ClusterDetailCreate, user: User
    ) -> ClusterDetail:
        # Check cluster existence
        cluster = await self.db.get(ClusterMaster, payload.ClusterMId)
        if not cluster:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Cluster {payload.ClusterMId} not found",
            )
        detail = ClusterDetail(
            ClusterMId=payload.ClusterMId,
            InsuranceCompanyId=payload.InsuranceCompanyId,
            RtoId=payload.RtoId,
            CreateUser=user.UserId,
            CreateDate=datetime.utcnow(),
        )
        self.db.add(detail)
        await self.db.commit()
        await self.db.refresh(detail)
        return detail

    async def create_cluster_broker_grid(
        self, payload: ClusterWiseBrokerGridCreate, user: User
    ) -> ClusterWiseBrokerGrid:
        grid = ClusterWiseBrokerGrid(
            ClusterMId=payload.ClusterMId,
            BrokerId=payload.BrokerId,
            InsuranceCompanyId=payload.InsuranceCompanyId,
            Veh_Type_ID=payload.Veh_Type_ID,
            StateId=payload.StateId,
            GridValue=payload.GridValue,
            ODDiscount=payload.ODDiscount,
            ValidFrom=payload.ValidFrom or date.today(),
            CalOn=payload.CalOn or "OD",
            ReferenceType=payload.ReferenceType,
            FuelTypeId=payload.FuelTypeId,
            ProductTypeId=payload.ProductTypeId,
            PolicyTypeId=payload.PolicyTypeId,
            CreatedUser=user.UserId,
            CreatedDate=datetime.utcnow(),
        )
        self.db.add(grid)
        await self.db.commit()
        await self.db.refresh(grid)
        return grid

    async def list_cluster_broker_grids(
        self,
        broker_id: Optional[int] = None,
        insurance_company_id: Optional[int] = None,
        veh_type_id: Optional[int] = None,
        cluster_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[ClusterWiseBrokerGrid]:
        query = select(ClusterWiseBrokerGrid).offset(skip).limit(limit).order_by(desc(ClusterWiseBrokerGrid.GridId))
        if broker_id:
            query = query.where(ClusterWiseBrokerGrid.BrokerId == broker_id)
        if insurance_company_id:
            query = query.where(ClusterWiseBrokerGrid.InsuranceCompanyId == insurance_company_id)
        if veh_type_id:
            query = query.where(ClusterWiseBrokerGrid.Veh_Type_ID == veh_type_id)
        if cluster_id:
            query = query.where(ClusterWiseBrokerGrid.ClusterMId == cluster_id)

        res = await self.db.execute(query)
        return list(res.scalars().all())

    async def create_cluster_agent_grid(
        self, payload: ClusterWiseAgentGridCreate, user: User
    ) -> ClusterWiseAgentGrid:
        grid = ClusterWiseAgentGrid(
            ClusterMId=payload.ClusterMId,
            AgentId=payload.AgentId,
            BrokerId=payload.BrokerId,
            InsuranceCompanyId=payload.InsuranceCompanyId,
            Veh_Type_ID=payload.Veh_Type_ID,
            StateId=payload.StateId,
            GridValue=payload.GridValue,
            ODDiscount=payload.ODDiscount,
            ValidFrom=payload.ValidFrom or date.today(),
            CalOn=payload.CalOn or "OD",
            ReferenceType=payload.ReferenceType,
            FuelTypeId=payload.FuelTypeId,
            ProductTypeId=payload.ProductTypeId,
            PolicyTypeId=payload.PolicyTypeId,
            CreatedUser=user.UserId,
            CreatedDate=datetime.utcnow(),
        )
        self.db.add(grid)
        await self.db.commit()
        await self.db.refresh(grid)
        return grid

    async def list_cluster_agent_grids(
        self,
        agent_id: Optional[int] = None,
        insurance_company_id: Optional[int] = None,
        veh_type_id: Optional[int] = None,
        cluster_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[ClusterWiseAgentGrid]:
        query = select(ClusterWiseAgentGrid).offset(skip).limit(limit).order_by(desc(ClusterWiseAgentGrid.GridId))
        if agent_id:
            query = query.where(ClusterWiseAgentGrid.AgentId == agent_id)
        if insurance_company_id:
            query = query.where(ClusterWiseAgentGrid.InsuranceCompanyId == insurance_company_id)
        if veh_type_id:
            query = query.where(ClusterWiseAgentGrid.Veh_Type_ID == veh_type_id)
        if cluster_id:
            query = query.where(ClusterWiseAgentGrid.ClusterMId == cluster_id)

        res = await self.db.execute(query)
        return list(res.scalars().all())

    # ========================================================================
    # 6. DECLINE MODELS & RESTRICTIONS GRID (F-20-006)
    # ========================================================================

    async def create_grid_decline(
        self, payload: GridDeclineCreate, user: User
    ) -> GridDeclineMaster:
        decline = GridDeclineMaster(
            DeclineDate=datetime.utcnow(),
            InsuranceCompanyId=payload.InsuranceCompanyId,
            MakeId=payload.MakeId,
            PolicyTypeId=payload.PolicyTypeId,
            ProductTypeId=payload.ProductTypeId,
            ModelId=payload.ModelId,
            RtoId=payload.RtoId,
            FuelTypeId=payload.FuelTypeId,
            Guide_line=payload.Guide_line,
            active=payload.active if payload.active is not None else 1,
            CreatedUser=user.UserId,
        )
        self.db.add(decline)
        await self.db.commit()
        await self.db.refresh(decline)
        return decline

    async def list_grid_declines(
        self,
        insurance_company_id: Optional[int] = None,
        make_id: Optional[int] = None,
        policy_type_id: Optional[int] = None,
        active_only: bool = True,
        skip: int = 0,
        limit: int = 50,
    ) -> List[GridDeclineMaster]:
        query = select(GridDeclineMaster).offset(skip).limit(limit).order_by(desc(GridDeclineMaster.DeclineId))
        if active_only:
            query = query.where(GridDeclineMaster.active == 1)
        if insurance_company_id:
            query = query.where(GridDeclineMaster.InsuranceCompanyId == insurance_company_id)
        if make_id:
            query = query.where(GridDeclineMaster.MakeId == make_id)
        if policy_type_id:
            query = query.where(GridDeclineMaster.PolicyTypeId == policy_type_id)

        res = await self.db.execute(query)
        return list(res.scalars().all())

    async def create_decline_model_detail(
        self, payload: DeclineModelDetailCreate, user: User
    ) -> DeclineModel:
        model_rule = DeclineModel(
            DeclineId=payload.DeclineId,
            MakeId=payload.MakeId,
            ModelId=payload.ModelId,
            InsuranceCompanyId=payload.InsuranceCompanyId,
            PolicyTypeId=payload.PolicyTypeId,
            ProductTypeId=payload.ProductTypeId,
            RtoId=payload.RtoId,
            FuelTypeId=payload.FuelTypeId,
            Remark=payload.Remark,
            CreatedDate=datetime.utcnow(),
            CreatedBy=user.UserId,
        )
        self.db.add(model_rule)
        await self.db.commit()
        await self.db.refresh(model_rule)
        return model_rule

    async def list_decline_model_details(
        self,
        insurance_company_id: Optional[int] = None,
        make_id: Optional[int] = None,
        model_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[DeclineModel]:
        query = select(DeclineModel).offset(skip).limit(limit).order_by(desc(DeclineModel.Id))
        if insurance_company_id:
            query = query.where(DeclineModel.InsuranceCompanyId == insurance_company_id)
        if make_id:
            query = query.where(DeclineModel.MakeId == make_id)
        if model_id:
            query = query.where(DeclineModel.ModelId == model_id)

        res = await self.db.execute(query)
        return list(res.scalars().all())

    async def check_underwriting_decline(
        self, payload: UnderwritingDeclineCheckRequest
    ) -> Dict[str, Any]:
        """
        Evaluates whether a quote/proposal falls under declined models or underwriting restrictions.
        Checks both tbl_griddecline and tbl_declinemodel rules.
        """
        # Check tbl_griddecline
        q_grid = select(GridDeclineMaster).where(
            GridDeclineMaster.active == 1,
            GridDeclineMaster.InsuranceCompanyId == payload.InsuranceCompanyId,
            GridDeclineMaster.MakeId == payload.MakeId,
            GridDeclineMaster.PolicyTypeId == payload.PolicyTypeId,
            GridDeclineMaster.ProductTypeId == payload.ProductTypeId,
        )
        if payload.ModelId:
            q_grid = q_grid.where(
                (GridDeclineMaster.ModelId.is_(None)) | (GridDeclineMaster.ModelId == payload.ModelId)
            )
        if payload.RtoId:
            q_grid = q_grid.where(
                (GridDeclineMaster.RtoId.is_(None)) | (GridDeclineMaster.RtoId == payload.RtoId)
            )
        if payload.FuelTypeId:
            q_grid = q_grid.where(
                (GridDeclineMaster.FuelTypeId.is_(None)) | (GridDeclineMaster.FuelTypeId == payload.FuelTypeId)
            )

        res_grid = await self.db.execute(q_grid)
        grid_matches = list(res_grid.scalars().all())

        # Check tbl_declinemodel
        q_model = select(DeclineModel).where(
            DeclineModel.InsuranceCompanyId == payload.InsuranceCompanyId,
            DeclineModel.MakeId == payload.MakeId,
            DeclineModel.ModelId == payload.ModelId,
            DeclineModel.PolicyTypeId == payload.PolicyTypeId,
            DeclineModel.ProductTypeId == payload.ProductTypeId,
        )
        if payload.RtoId:
            q_model = q_model.where(
                (DeclineModel.RtoId.is_(None)) | (DeclineModel.RtoId == payload.RtoId)
            )
        if payload.FuelTypeId:
            q_model = q_model.where(
                (DeclineModel.FuelTypeId.is_(None)) | (DeclineModel.FuelTypeId == payload.FuelTypeId)
            )

        res_model = await self.db.execute(q_model)
        model_matches = list(res_model.scalars().all())

        total_matches = len(grid_matches) + len(model_matches)
        if total_matches > 0:
            reasons = []
            for g in grid_matches:
                if g.Guide_line:
                    reasons.append(g.Guide_line)
            for m in model_matches:
                if m.Remark:
                    reasons.append(m.Remark)
            reason_str = "; ".join(reasons) if reasons else "Vehicle model or region is declined under underwriting guidelines."
            return {
                "is_declined": True,
                "reason": reason_str,
                "matching_rule_count": total_matches,
            }

        return {
            "is_declined": False,
            "reason": None,
            "matching_rule_count": 0,
        }


# Backward-compatibility alias
Phase20Service = OperationalExtensionService
