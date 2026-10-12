"""
FastAPI Route Handlers for Phase 20 Features — Batch 1.
Covers:
1. Bulletins & Circulars (F-20-001)
2. Mobile Customer Helpdesk & Support Chat (F-20-002)
3. Web Notification Alerts (F-20-003)
4. Partner Loyalty & Reward Points (F-20-004)
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.core.dependencies import get_current_user, require_roles
from app.models.user import User
from app.services.phase20_service import Phase20Service
from app.schemas.phase20 import (
    CircularCreate,
    CircularUpdate,
    CircularResponse,
    CustomerHelpCreate,
    CustomerHelpResolve,
    CustomerHelpResponse,
    ChatBoardMessageCreate,
    ChatBoardReplyCreate,
    ChatBoardMessageResponse,
    WebNotificationCreate,
    WebNotificationResponse,
    RewardPointCreate,
    RewardPointResponse,
    RewardPointSummaryResponse,
    ClusterMasterCreate,
    ClusterDetailCreate,
    ClusterDetailResponse,
    ClusterMasterResponse,
    ClusterWiseBrokerGridCreate,
    ClusterWiseBrokerGridResponse,
    ClusterWiseAgentGridCreate,
    ClusterWiseAgentGridResponse,
    GridDeclineCreate,
    GridDeclineResponse,
    DeclineModelDetailCreate,
    DeclineModelResponse,
    UnderwritingDeclineCheckRequest,
    UnderwritingDeclineCheckResponse,
)

ADMIN_ROLES = ("OWNER", "ADMIN", "IT SUPPORT", "MANAGER", "SUPERVISOR", "LOCATION HEAD")
COORDINATOR_ROLES = ("OWNER", "ADMIN", "IT SUPPORT", "OPERATOR", "OPERATOR HEAD", "QUOT CO-ORDINATOR", "INSP CO-ORDINATION", "MANAGER", "SUPERVISOR")
FINANCE_ROLES = ("OWNER", "ADMIN", "IT SUPPORT", "ACCOUNT", "ACCOUNT HEAD", "CASHIER", "MANAGER")

# Individual domain routers
circulars_router = APIRouter(prefix="/admin/circulars", tags=["Admin - Circulars & Bulletins"])
customer_help_router = APIRouter(prefix="/renewals/customer-help", tags=["Renewals & CRM - Customer Helpdesk"])
web_notifications_router = APIRouter(prefix="/admin/web-notifications", tags=["Admin - Web Notifications"])
reward_points_router = APIRouter(prefix="/agents/reward-points", tags=["Agents - Loyalty & Reward Points"])
clusters_router = APIRouter(prefix="/commercial/clusters", tags=["Commercial Masters - Geographic Clusters & Grids"])
decline_rules_router = APIRouter(prefix="/underwriting/decline-rules", tags=["Underwriting - Decline Models & Restrictions"])


# ============================================================================
# 1. CIRCULARS & BULLETINS ENDPOINTS (F-20-001)
# ============================================================================

@circulars_router.post(
    "",
    response_model=CircularResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Company Circular / Bulletin",
)
async def create_circular_endpoint(
    payload: CircularCreate,
    current_user: User = Depends(require_roles(*ADMIN_ROLES)),
    db: AsyncSession = Depends(get_db),
) -> CircularResponse:
    service = Phase20Service(db)
    circular = await service.create_circular(payload, current_user)
    return CircularResponse.model_validate(circular)


@circulars_router.get(
    "",
    response_model=List[CircularResponse],
    summary="List Company Circulars / Bulletins",
)
async def list_circulars_endpoint(
    active_only: bool = Query(True, description="Filter active circulars"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[CircularResponse]:
    service = Phase20Service(db)
    circulars = await service.list_circulars(active_only=active_only, skip=skip, limit=limit)
    return [CircularResponse.model_validate(c) for c in circulars]


@circulars_router.get(
    "/{circular_id}",
    response_model=CircularResponse,
    summary="Get Circular by ID",
)
async def get_circular_endpoint(
    circular_id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CircularResponse:
    service = Phase20Service(db)
    circular = await service.get_circular(circular_id)
    return CircularResponse.model_validate(circular)


@circulars_router.put(
    "/{circular_id}",
    response_model=CircularResponse,
    summary="Update Company Circular",
)
async def update_circular_endpoint(
    circular_id: int = Path(..., ge=1),
    payload: CircularUpdate = ...,
    current_user: User = Depends(require_roles(*ADMIN_ROLES)),
    db: AsyncSession = Depends(get_db),
) -> CircularResponse:
    service = Phase20Service(db)
    circular = await service.update_circular(circular_id, payload)
    return CircularResponse.model_validate(circular)


@circulars_router.delete(
    "/{circular_id}",
    status_code=status.HTTP_200_OK,
    summary="Deactivate Company Circular",
)
async def delete_circular_endpoint(
    circular_id: int = Path(..., ge=1),
    current_user: User = Depends(require_roles(*ADMIN_ROLES)),
    db: AsyncSession = Depends(get_db),
) -> dict:
    service = Phase20Service(db)
    await service.delete_circular(circular_id)
    return {"status": "SUCCESS", "message": f"Circular {circular_id} deactivated."}


# ============================================================================
# 2. CUSTOMER HELPDESK & SUPPORT CHAT ENDPOINTS (F-20-002)
# ============================================================================

@customer_help_router.post(
    "",
    response_model=CustomerHelpResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit Customer Help Inquiry",
)
async def create_help_ticket_endpoint(
    payload: CustomerHelpCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CustomerHelpResponse:
    service = Phase20Service(db)
    ticket = await service.create_help_ticket(payload, current_user)
    return CustomerHelpResponse.model_validate(ticket)


@customer_help_router.get(
    "",
    response_model=List[CustomerHelpResponse],
    summary="List Customer Help Inquiries",
)
async def list_help_tickets_endpoint(
    status_filter: Optional[str] = Query(None, alias="status", description="Status filter"),
    customer_id: Optional[int] = Query(None, description="Customer filter"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[CustomerHelpResponse]:
    service = Phase20Service(db)
    tickets = await service.list_help_tickets(
        status_filter=status_filter, customer_id=customer_id, skip=skip, limit=limit
    )
    return [CustomerHelpResponse.model_validate(t) for t in tickets]


@customer_help_router.get(
    "/{ticket_id}",
    response_model=CustomerHelpResponse,
    summary="Get Customer Help Ticket Details",
)
async def get_help_ticket_endpoint(
    ticket_id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CustomerHelpResponse:
    service = Phase20Service(db)
    ticket = await service.get_help_ticket(ticket_id)
    return CustomerHelpResponse.model_validate(ticket)


@customer_help_router.post(
    "/{ticket_id}/resolve",
    response_model=CustomerHelpResponse,
    summary="Resolve Customer Help Ticket",
)
async def resolve_help_ticket_endpoint(
    ticket_id: int = Path(..., ge=1),
    payload: CustomerHelpResolve = ...,
    current_user: User = Depends(require_roles(*COORDINATOR_ROLES)),
    db: AsyncSession = Depends(get_db),
) -> CustomerHelpResponse:
    service = Phase20Service(db)
    ticket = await service.resolve_help_ticket(ticket_id, payload, current_user)
    return CustomerHelpResponse.model_validate(ticket)


@customer_help_router.post(
    "/chat",
    response_model=ChatBoardMessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Post Support Chat Message",
)
async def post_chat_message_endpoint(
    payload: ChatBoardMessageCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ChatBoardMessageResponse:
    service = Phase20Service(db)
    msg = await service.post_chat_message(payload, current_user)
    return ChatBoardMessageResponse.model_validate(msg)


@customer_help_router.get(
    "/chat/messages",
    response_model=List[ChatBoardMessageResponse],
    summary="List Support Chat Messages",
)
async def list_chat_messages_endpoint(
    cust_help_id: Optional[int] = Query(None, description="Help ticket ID filter"),
    agent_id: Optional[int] = Query(None, description="Agent filter"),
    registration_no: Optional[str] = Query(None, description="Registration No filter"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[ChatBoardMessageResponse]:
    service = Phase20Service(db)
    messages = await service.list_chat_messages(
        cust_help_id=cust_help_id,
        agent_id=agent_id,
        registration_no=registration_no,
        skip=skip,
        limit=limit,
    )
    return [ChatBoardMessageResponse.model_validate(m) for m in messages]


@customer_help_router.post(
    "/chat/{chat_id}/reply",
    response_model=ChatBoardMessageResponse,
    summary="Reply to Support Chat Message",
)
async def reply_chat_message_endpoint(
    chat_id: int = Path(..., ge=1),
    payload: ChatBoardReplyCreate = ...,
    current_user: User = Depends(require_roles(*COORDINATOR_ROLES)),
    db: AsyncSession = Depends(get_db),
) -> ChatBoardMessageResponse:
    service = Phase20Service(db)
    msg = await service.reply_chat_message(chat_id, payload, current_user)
    return ChatBoardMessageResponse.model_validate(msg)


# ============================================================================
# 3. WEB NOTIFICATIONS ENDPOINTS (F-20-003)
# ============================================================================

@web_notifications_router.post(
    "",
    response_model=WebNotificationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Web Notification Alert",
)
async def create_web_notification_endpoint(
    payload: WebNotificationCreate,
    current_user: User = Depends(require_roles(*ADMIN_ROLES)),
    db: AsyncSession = Depends(get_db),
) -> WebNotificationResponse:
    service = Phase20Service(db)
    notif = await service.create_web_notification(payload, current_user)
    return WebNotificationResponse.model_validate(notif)


@web_notifications_router.get(
    "",
    response_model=List[WebNotificationResponse],
    summary="List Active Web Notification Alerts",
)
async def list_web_notifications_endpoint(
    target_role: Optional[str] = Query(None, description="Role target filter"),
    branch_id: Optional[int] = Query(None, description="Branch filter"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[WebNotificationResponse]:
    service = Phase20Service(db)
    notifications = await service.list_active_notifications(target_role=target_role, branch_id=branch_id)
    return [WebNotificationResponse.model_validate(n) for n in notifications]


@web_notifications_router.delete(
    "/{notification_id}",
    status_code=status.HTTP_200_OK,
    summary="Dismiss / Deactivate Web Notification Alert",
)
async def dismiss_web_notification_endpoint(
    notification_id: int = Path(..., ge=1),
    current_user: User = Depends(require_roles(*ADMIN_ROLES)),
    db: AsyncSession = Depends(get_db),
) -> dict:
    service = Phase20Service(db)
    await service.dismiss_notification(notification_id)
    return {"status": "SUCCESS", "message": f"Notification {notification_id} dismissed."}


# ============================================================================
# 4. PARTNER LOYALTY & REWARD POINTS ENDPOINTS (F-20-004)
# ============================================================================

@reward_points_router.post(
    "",
    response_model=RewardPointResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record Reward Points Transaction",
)
async def record_reward_points_endpoint(
    payload: RewardPointCreate,
    current_user: User = Depends(require_roles(*FINANCE_ROLES)),
    db: AsyncSession = Depends(get_db),
) -> RewardPointResponse:
    service = Phase20Service(db)
    reward = await service.record_reward_points(payload, current_user)
    return RewardPointResponse.model_validate(reward)


@reward_points_router.get(
    "",
    response_model=List[RewardPointResponse],
    summary="List Partner Reward Points Ledger",
)
async def get_partner_reward_points_endpoint(
    partner_type: str = Query("AGENT", description="Partner type: AGENT, FRANCHISE, EXECUTIVE, CUSTOMER"),
    partner_id: int = Query(..., ge=1, description="Partner identity ID"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[RewardPointResponse]:
    service = Phase20Service(db)
    points = await service.get_partner_reward_points(
        partner_type=partner_type, partner_id=partner_id, skip=skip, limit=limit
    )
    return [RewardPointResponse.model_validate(p) for p in points]


@reward_points_router.get(
    "/summary",
    response_model=RewardPointSummaryResponse,
    summary="Get Partner Reward Points Summary",
)
async def get_reward_points_summary_endpoint(
    partner_type: str = Query("AGENT", description="Partner type: AGENT, FRANCHISE, EXECUTIVE, CUSTOMER"),
    partner_id: int = Query(..., ge=1, description="Partner identity ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RewardPointSummaryResponse:
    service = Phase20Service(db)
    summary = await service.get_reward_points_summary(partner_type=partner_type, partner_id=partner_id)
    return RewardPointSummaryResponse.model_validate(summary)


# ============================================================================
# 5. GEOGRAPHIC CLUSTERS & COMMISSION GRIDS ENDPOINTS (F-20-005)
# ============================================================================

@clusters_router.post(
    "",
    response_model=ClusterMasterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Geographic Cluster",
)
async def create_cluster_endpoint(
    payload: ClusterMasterCreate,
    current_user: User = Depends(require_roles(*ADMIN_ROLES)),
    db: AsyncSession = Depends(get_db),
) -> ClusterMasterResponse:
    service = Phase20Service(db)
    cluster = await service.create_cluster(payload, current_user)
    return ClusterMasterResponse.model_validate(cluster)


@clusters_router.get(
    "",
    response_model=List[ClusterMasterResponse],
    summary="List Geographic Clusters",
)
async def list_clusters_endpoint(
    insurance_company_id: Optional[int] = Query(None, description="Company filter"),
    state_id: Optional[int] = Query(None, description="State filter"),
    active_only: bool = Query(True, description="Active clusters only"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[ClusterMasterResponse]:
    service = Phase20Service(db)
    clusters = await service.list_clusters(
        insurance_company_id=insurance_company_id,
        state_id=state_id,
        active_only=active_only,
        skip=skip,
        limit=limit,
    )
    return [ClusterMasterResponse.model_validate(c) for c in clusters]


@clusters_router.post(
    "/broker-grids",
    response_model=ClusterWiseBrokerGridResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Cluster-Wise Broker Grid Rate",
)
async def create_cluster_broker_grid_endpoint(
    payload: ClusterWiseBrokerGridCreate,
    current_user: User = Depends(require_roles(*FINANCE_ROLES)),
    db: AsyncSession = Depends(get_db),
) -> ClusterWiseBrokerGridResponse:
    service = Phase20Service(db)
    grid = await service.create_cluster_broker_grid(payload, current_user)
    return ClusterWiseBrokerGridResponse.model_validate(grid)


@clusters_router.get(
    "/broker-grids",
    response_model=List[ClusterWiseBrokerGridResponse],
    summary="List Cluster-Wise Broker Grid Rates",
)
async def list_cluster_broker_grids_endpoint(
    broker_id: Optional[int] = Query(None),
    insurance_company_id: Optional[int] = Query(None),
    veh_type_id: Optional[int] = Query(None),
    cluster_id: Optional[int] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[ClusterWiseBrokerGridResponse]:
    service = Phase20Service(db)
    grids = await service.list_cluster_broker_grids(
        broker_id=broker_id,
        insurance_company_id=insurance_company_id,
        veh_type_id=veh_type_id,
        cluster_id=cluster_id,
        skip=skip,
        limit=limit,
    )
    return [ClusterWiseBrokerGridResponse.model_validate(g) for g in grids]


@clusters_router.post(
    "/agent-grids",
    response_model=ClusterWiseAgentGridResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Cluster-Wise Agent Grid Rate",
)
async def create_cluster_agent_grid_endpoint(
    payload: ClusterWiseAgentGridCreate,
    current_user: User = Depends(require_roles(*FINANCE_ROLES)),
    db: AsyncSession = Depends(get_db),
) -> ClusterWiseAgentGridResponse:
    service = Phase20Service(db)
    grid = await service.create_cluster_agent_grid(payload, current_user)
    return ClusterWiseAgentGridResponse.model_validate(grid)


@clusters_router.get(
    "/agent-grids",
    response_model=List[ClusterWiseAgentGridResponse],
    summary="List Cluster-Wise Agent Grid Rates",
)
async def list_cluster_agent_grids_endpoint(
    agent_id: Optional[int] = Query(None),
    insurance_company_id: Optional[int] = Query(None),
    veh_type_id: Optional[int] = Query(None),
    cluster_id: Optional[int] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[ClusterWiseAgentGridResponse]:
    service = Phase20Service(db)
    grids = await service.list_cluster_agent_grids(
        agent_id=agent_id,
        insurance_company_id=insurance_company_id,
        veh_type_id=veh_type_id,
        cluster_id=cluster_id,
        skip=skip,
        limit=limit,
    )
    return [ClusterWiseAgentGridResponse.model_validate(g) for g in grids]


@clusters_router.get(
    "/{cluster_id}",
    response_model=ClusterMasterResponse,
    summary="Get Geographic Cluster with RTO Mappings",
)
async def get_cluster_endpoint(
    cluster_id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ClusterMasterResponse:
    service = Phase20Service(db)
    cluster = await service.get_cluster(cluster_id)
    return ClusterMasterResponse.model_validate(cluster)


@clusters_router.post(
    "/{cluster_id}/rtos",
    response_model=ClusterDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add RTO to Geographic Cluster",
)
async def add_cluster_rto_endpoint(
    cluster_id: int = Path(..., ge=1),
    payload: ClusterDetailCreate = ...,
    current_user: User = Depends(require_roles(*ADMIN_ROLES)),
    db: AsyncSession = Depends(get_db),
) -> ClusterDetailResponse:
    service = Phase20Service(db)
    payload.ClusterMId = cluster_id
    detail = await service.add_cluster_rto(payload, current_user)
    return ClusterDetailResponse.model_validate(detail)


# ============================================================================
# 6. DECLINE MODELS & RESTRICTIONS GRID ENDPOINTS (F-20-006)
# ============================================================================

@decline_rules_router.post(
    "",
    response_model=GridDeclineResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Underwriting Decline Master Rule",
)
async def create_grid_decline_endpoint(
    payload: GridDeclineCreate,
    current_user: User = Depends(require_roles(*ADMIN_ROLES)),
    db: AsyncSession = Depends(get_db),
) -> GridDeclineResponse:
    service = Phase20Service(db)
    rule = await service.create_grid_decline(payload, current_user)
    return GridDeclineResponse.model_validate(rule)


@decline_rules_router.get(
    "",
    response_model=List[GridDeclineResponse],
    summary="List Underwriting Decline Rules",
)
async def list_grid_declines_endpoint(
    insurance_company_id: Optional[int] = Query(None),
    make_id: Optional[int] = Query(None),
    policy_type_id: Optional[int] = Query(None),
    active_only: bool = Query(True),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[GridDeclineResponse]:
    service = Phase20Service(db)
    rules = await service.list_grid_declines(
        insurance_company_id=insurance_company_id,
        make_id=make_id,
        policy_type_id=policy_type_id,
        active_only=active_only,
        skip=skip,
        limit=limit,
    )
    return [GridDeclineResponse.model_validate(r) for r in rules]


@decline_rules_router.post(
    "/models",
    response_model=DeclineModelResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Vehicle Model Level Decline Detail Rule",
)
async def create_decline_model_detail_endpoint(
    payload: DeclineModelDetailCreate,
    current_user: User = Depends(require_roles(*ADMIN_ROLES)),
    db: AsyncSession = Depends(get_db),
) -> DeclineModelResponse:
    service = Phase20Service(db)
    rule = await service.create_decline_model_detail(payload, current_user)
    return DeclineModelResponse.model_validate(rule)


@decline_rules_router.get(
    "/models",
    response_model=List[DeclineModelResponse],
    summary="List Vehicle Model Decline Detail Rules",
)
async def list_decline_model_details_endpoint(
    insurance_company_id: Optional[int] = Query(None),
    make_id: Optional[int] = Query(None),
    model_id: Optional[int] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[DeclineModelResponse]:
    service = Phase20Service(db)
    rules = await service.list_decline_model_details(
        insurance_company_id=insurance_company_id,
        make_id=make_id,
        model_id=model_id,
        skip=skip,
        limit=limit,
    )
    return [DeclineModelResponse.model_validate(r) for r in rules]


@decline_rules_router.post(
    "/check",
    response_model=UnderwritingDeclineCheckResponse,
    summary="Check Proposal Against Underwriting Decline Rules",
)
async def check_underwriting_decline_endpoint(
    payload: UnderwritingDeclineCheckRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UnderwritingDeclineCheckResponse:
    service = Phase20Service(db)
    result = await service.check_underwriting_decline(payload)
    return UnderwritingDeclineCheckResponse.model_validate(result)
