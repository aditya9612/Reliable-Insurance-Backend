"""
SQLAlchemy 2.0 Declarative Models for Phase 20 — Complete Project Migration Execution.
Physical Tables Added:
1. tbl_circular (Company Bulletins & Circulars Master — F-20-001)
2. tbl_customerhelp (Mobile Customer Helpdesk Inquiries — F-20-002)
3. tbl_chatboard (Customer & Agent Support Chat Messages — F-20-002)
4. tbl_webnotification (Web Notification Alerts Master — F-20-003)
5. tbl_rewardpoint (Partner Loyalty & Reward Points Ledger — F-20-004)
"""
from datetime import datetime, date
from decimal import Decimal
from typing import Optional
from sqlalchemy import Integer, String, DateTime, Date, Numeric, Text, Index, text
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class Circular(Base):
    """
    Company Bulletins & Circulars Master Model.
    Physical Table: tbl_circular
    Physical PK: circularid
    Legacy Reference: adm_Circular.aspx.cs, BLL_Circular, DAL_Circular, api_circular, Sp_CircularOperation
    """
    __tablename__ = "tbl_circular"
    __table_args__ = (
        Index("ix_tbl_circular_circulardate", "circulardate"),
        Index("ix_tbl_circular_is_active", "is_active"),
        {
            "mysql_charset": "utf8",
            "mysql_collate": "utf8_general_ci",
            "mysql_row_format": "DYNAMIC",
        },
    )

    circularid: Mapped[int] = mapped_column("circularid", Integer, primary_key=True, autoincrement=True)
    circulardate: Mapped[date] = mapped_column("circulardate", Date, nullable=False, default=date.today)
    subject: Mapped[str] = mapped_column("subject", String(500), nullable=False)
    pdfpath: Mapped[Optional[str]] = mapped_column("pdfpath", String(1000), nullable=True)
    is_active: Mapped[int] = mapped_column("is_active", Integer, nullable=False, server_default=text("1"))
    created_by: Mapped[Optional[int]] = mapped_column("created_by", Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        "created_at", DateTime, nullable=False, default=datetime.utcnow
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        "updated_at", DateTime, nullable=True, onupdate=datetime.utcnow
    )


class CustomerHelp(Base):
    """
    Mobile Customer Helpdesk Inquiry Master Model.
    Physical Table: tbl_customerhelp
    Physical PK: CustHelpId
    Legacy Reference: BLL_CustomerHelp, DAL_CustomerHelp, API_CustomerHelp, adm_ChatSelect.aspx.cs
    """
    __tablename__ = "tbl_customerhelp"
    __table_args__ = (
        Index("ix_tbl_customerhelp_CustomerId", "CustomerId"),
        Index("ix_tbl_customerhelp_Status", "Status"),
        Index("ix_tbl_customerhelp_CustDate", "CustDate"),
        {
            "mysql_charset": "utf8",
            "mysql_collate": "utf8_general_ci",
            "mysql_row_format": "DYNAMIC",
        },
    )

    CustHelpId: Mapped[int] = mapped_column("CustHelpId", Integer, primary_key=True, autoincrement=True)
    CustomerId: Mapped[int] = mapped_column("CustomerId", Integer, nullable=False)
    HelpId: Mapped[Optional[int]] = mapped_column("HelpId", Integer, nullable=True)
    Subject: Mapped[str] = mapped_column("Subject", String(255), nullable=False, server_default=text("''"))
    Message: Mapped[Optional[str]] = mapped_column("Message", Text, nullable=True)
    RegistrationNo: Mapped[Optional[str]] = mapped_column("RegistrationNo", String(100), nullable=True)
    PolicyNo: Mapped[Optional[str]] = mapped_column("PolicyNo", String(100), nullable=True)
    Status: Mapped[str] = mapped_column(
        "Status", String(50), nullable=False, server_default=text("'OPEN'")
    )  # OPEN, IN_PROGRESS, RESOLVED, CLOSED
    CustDate: Mapped[datetime] = mapped_column("CustDate", DateTime, nullable=False, default=datetime.utcnow)
    ResolvedBy: Mapped[Optional[int]] = mapped_column("ResolvedBy", Integer, nullable=True)
    ResolvedDate: Mapped[Optional[datetime]] = mapped_column("ResolvedDate", DateTime, nullable=True)
    ResolutionRemark: Mapped[Optional[str]] = mapped_column("ResolutionRemark", String(1000), nullable=True)
    is_deleted: Mapped[int] = mapped_column("is_deleted", Integer, nullable=False, server_default=text("0"))


class AppChatBoard(Base):
    """
    Customer & Agent Support Chat Communication Model.
    Physical Table: tbl_chatboard
    Physical PK: ChatId
    Legacy Reference: API_AppchatBorad, Sp_InsertAppChatboard, Sp_ViewAppChat, Sp_AppChatReplyFile
    """
    __tablename__ = "tbl_chatboard"
    __table_args__ = (
        Index("ix_tbl_chatboard_CustHelpId", "CustHelpId"),
        Index("ix_tbl_chatboard_ReferenceAgentId", "ReferenceAgentId"),
        Index("ix_tbl_chatboard_CreatedDate", "CreatedDate"),
        {
            "mysql_charset": "utf8",
            "mysql_collate": "utf8_general_ci",
            "mysql_row_format": "DYNAMIC",
        },
    )

    ChatId: Mapped[int] = mapped_column("ChatId", Integer, primary_key=True, autoincrement=True)
    CustHelpId: Mapped[Optional[int]] = mapped_column("CustHelpId", Integer, nullable=True)
    UserRoleId: Mapped[Optional[int]] = mapped_column("UserRoleId", Integer, nullable=True)
    ReferenceAgentId: Mapped[Optional[int]] = mapped_column("ReferenceAgentId", Integer, nullable=True)
    CoordinatorId: Mapped[Optional[int]] = mapped_column("CoordinatorId", Integer, nullable=True)
    RegistrationNo: Mapped[Optional[str]] = mapped_column("RegistrationNo", String(100), nullable=True)
    ChatText: Mapped[str] = mapped_column("ChatText", Text, nullable=False)
    ChatByUser: Mapped[str] = mapped_column("ChatByUser", String(100), nullable=False)  # CUSTOMER, AGENT, OPERATOR
    SenderUserId: Mapped[Optional[int]] = mapped_column("SenderUserId", Integer, nullable=True)
    Reply: Mapped[Optional[str]] = mapped_column("Reply", Text, nullable=True)
    Remark: Mapped[Optional[str]] = mapped_column("Remark", String(500), nullable=True)
    AttachmentPath: Mapped[Optional[str]] = mapped_column("AttachmentPath", String(1000), nullable=True)
    IsRead: Mapped[int] = mapped_column("IsRead", Integer, nullable=False, server_default=text("0"))
    CreatedDate: Mapped[datetime] = mapped_column(
        "CreatedDate", DateTime, nullable=False, default=datetime.utcnow
    )


class WebNotification(Base):
    """
    Web Notification & Portal Broadcast Alert Model.
    Physical Table: tbl_webnotification
    Physical PK: NotId
    Legacy Reference: BLL_WebNotification, DAL_WebNotification, API_WebNotification, sp_insertWebNotification
    """
    __tablename__ = "tbl_webnotification"
    __table_args__ = (
        Index("ix_tbl_webnotification_TargetRole", "TargetRole"),
        Index("ix_tbl_webnotification_IsActive", "IsActive"),
        Index("ix_tbl_webnotification_CreatedDate", "CreatedDate"),
        {
            "mysql_charset": "utf8",
            "mysql_collate": "utf8_general_ci",
            "mysql_row_format": "DYNAMIC",
        },
    )

    NotId: Mapped[int] = mapped_column("NotId", Integer, primary_key=True, autoincrement=True)
    NotMessage: Mapped[str] = mapped_column("NotMessage", String(1000), nullable=False)
    TargetRole: Mapped[Optional[str]] = mapped_column("TargetRole", String(50), nullable=True, server_default=text("'ALL'"))
    BranchId: Mapped[Optional[int]] = mapped_column("BranchId", Integer, nullable=True)
    Severity: Mapped[str] = mapped_column(
        "Severity", String(20), nullable=False, server_default=text("'INFO'")
    )  # INFO, WARNING, URGENT
    IsActive: Mapped[int] = mapped_column("IsActive", Integer, nullable=False, server_default=text("1"))
    CreatedBy: Mapped[Optional[int]] = mapped_column("CreatedBy", Integer, nullable=True)
    CreatedDate: Mapped[datetime] = mapped_column(
        "CreatedDate", DateTime, nullable=False, default=datetime.utcnow
    )
    ExpiryDate: Mapped[Optional[datetime]] = mapped_column("ExpiryDate", DateTime, nullable=True)


class RewardPoint(Base):
    """
    Partner & Customer Loyalty / Referral Reward Points Ledger Model.
    Physical Table: tbl_rewardpoint
    Physical PK: RewardPointId
    Legacy Reference: BLL_RewardPoint, DAL_RewardPoint, API_RewardPoint, sp_AppSelectRewardPoint
    """
    __tablename__ = "tbl_rewardpoint"
    __table_args__ = (
        Index("ix_tbl_rewardpoint_Partner", "PartnerType", "PartnerId"),
        Index("ix_tbl_rewardpoint_RewardDate", "RewardDate"),
        {
            "mysql_charset": "utf8",
            "mysql_collate": "utf8_general_ci",
            "mysql_row_format": "DYNAMIC",
        },
    )

    RewardPointId: Mapped[int] = mapped_column("RewardPointId", Integer, primary_key=True, autoincrement=True)
    PartnerType: Mapped[str] = mapped_column(
        "PartnerType", String(50), nullable=False, server_default=text("'AGENT'")
    )  # AGENT, FRANCHISE, EXECUTIVE, CUSTOMER
    PartnerId: Mapped[int] = mapped_column("PartnerId", Integer, nullable=False)
    RefCustId: Mapped[Optional[int]] = mapped_column("RefCustId", Integer, nullable=True)
    PolicyId: Mapped[Optional[int]] = mapped_column("PolicyId", Integer, nullable=True)
    RewardDate: Mapped[date] = mapped_column("RewardDate", Date, nullable=False, default=date.today)
    RewardPointGet: Mapped[Decimal] = mapped_column(
        "RewardPointGet", Numeric(12, 2), nullable=False, server_default=text("0.00")
    )
    RewardPointUtilizes: Mapped[Decimal] = mapped_column(
        "RewardPointUtilizes", Numeric(12, 2), nullable=False, server_default=text("0.00")
    )
    PointBalance: Mapped[Decimal] = mapped_column(
        "PointBalance", Numeric(12, 2), nullable=False, server_default=text("0.00")
    )
    Remarks: Mapped[Optional[str]] = mapped_column("Remarks", String(500), nullable=True)
    CreatedDate: Mapped[datetime] = mapped_column(
        "CreatedDate", DateTime, nullable=False, default=datetime.utcnow
    )


# ============================================================================
# 5. GEOGRAPHIC CLUSTERS & COMMISSION GRIDS (F-20-005)
# ============================================================================

class ClusterMaster(Base):
    """
    Commercial Geographic Cluster Master Model.
    Physical Table: tbl_clustermaster
    Physical PK: ClusterMId
    Legacy Reference: BLL_ClusterMaster, DAL_ClusterMaster, API_ClusterMaster, sp_InsertClusterMaster
    """
    __tablename__ = "tbl_clustermaster"
    __table_args__ = (
        Index("ix_tbl_clustermaster_Company_State", "InsuranceCompanyId", "StateId"),
        {
            "mysql_charset": "utf8",
            "mysql_collate": "utf8_general_ci",
            "mysql_row_format": "DYNAMIC",
        },
    )

    ClusterMId: Mapped[int] = mapped_column("ClusterMId", Integer, primary_key=True, autoincrement=True)
    InsuranceCompanyId: Mapped[int] = mapped_column("InsuranceCompanyId", Integer, nullable=False)
    ClusterName: Mapped[str] = mapped_column("ClusterName", String(255), nullable=False)
    StateId: Mapped[int] = mapped_column("StateId", Integer, nullable=False)
    CreateUser: Mapped[Optional[int]] = mapped_column("CreateUser", Integer, nullable=True)
    CreateDate: Mapped[datetime] = mapped_column(
        "CreateDate", DateTime, nullable=False, default=datetime.utcnow
    )
    isdeleted: Mapped[int] = mapped_column("isdeleted", Integer, nullable=False, server_default=text("0"))


class ClusterDetail(Base):
    """
    Geographic Cluster RTO Mapping Detail Model.
    Physical Table: tbl_clusterdetails
    Physical PK: ClusterDId
    Legacy Reference: BLL_ClusterMaster, DAL_ClusterMaster, sp_InsertClusterDetails
    """
    __tablename__ = "tbl_clusterdetails"
    __table_args__ = (
        Index("ix_tbl_clusterdetails_ClusterMId", "ClusterMId"),
        Index("ix_tbl_clusterdetails_RtoId", "RtoId"),
        {
            "mysql_charset": "utf8",
            "mysql_collate": "utf8_general_ci",
            "mysql_row_format": "DYNAMIC",
        },
    )

    ClusterDId: Mapped[int] = mapped_column("ClusterDId", Integer, primary_key=True, autoincrement=True)
    ClusterMId: Mapped[int] = mapped_column("ClusterMId", Integer, nullable=False)
    InsuranceCompanyId: Mapped[int] = mapped_column("InsuranceCompanyId", Integer, nullable=False)
    RtoId: Mapped[int] = mapped_column("RtoId", Integer, nullable=False)
    CreateUser: Mapped[Optional[int]] = mapped_column("CreateUser", Integer, nullable=True)
    CreateDate: Mapped[datetime] = mapped_column(
        "CreateDate", DateTime, nullable=False, default=datetime.utcnow
    )


class ClusterWiseBrokerGrid(Base):
    """
    Cluster-Wise Broker Commission Grid Model.
    Physical Table: tbl_clusterwisebrokergrid
    Physical PK: GridId
    Legacy Reference: BLL_ClusterMaster, DAL_ClusterMaster, API_clusterwisebrokergrid, sp_insertclusterwisebrokergrid
    """
    __tablename__ = "tbl_clusterwisebrokergrid"
    __table_args__ = (
        Index("ix_tbl_cwbg_Broker_Company", "BrokerId", "InsuranceCompanyId"),
        Index("ix_tbl_cwbg_ClusterMId", "ClusterMId"),
        {
            "mysql_charset": "utf8",
            "mysql_collate": "utf8_general_ci",
            "mysql_row_format": "DYNAMIC",
        },
    )

    GridId: Mapped[int] = mapped_column("GridId", Integer, primary_key=True, autoincrement=True)
    GridValue: Mapped[Decimal] = mapped_column(
        "GridValue", Numeric(12, 2), nullable=False, server_default=text("0.00")
    )
    CalOn: Mapped[Optional[str]] = mapped_column("CalOn", String(50), nullable=True)
    ODDiscount: Mapped[Decimal] = mapped_column(
        "ODDiscount", Numeric(12, 2), nullable=False, server_default=text("0.00")
    )
    ValidFrom: Mapped[date] = mapped_column("ValidFrom", Date, nullable=False, default=date.today)
    ReferenceType: Mapped[Optional[str]] = mapped_column("ReferenceType", String(50), nullable=True)
    BrokerId: Mapped[int] = mapped_column("BrokerId", Integer, nullable=False)
    InsuranceCompanyId: Mapped[int] = mapped_column("InsuranceCompanyId", Integer, nullable=False)
    Veh_Type_ID: Mapped[int] = mapped_column("Veh_Type_ID", Integer, nullable=False)
    StateId: Mapped[int] = mapped_column("StateId", Integer, nullable=False)
    FuelTypeId: Mapped[Optional[int]] = mapped_column("FuelTypeId", Integer, nullable=True)
    ProductTypeId: Mapped[Optional[int]] = mapped_column("ProductTypeId", Integer, nullable=True)
    PolicyTypeId: Mapped[Optional[int]] = mapped_column("PolicyTypeId", Integer, nullable=True)
    ClusterMId: Mapped[int] = mapped_column("ClusterMId", Integer, nullable=False)
    CreatedUser: Mapped[Optional[int]] = mapped_column("CreatedUser", Integer, nullable=True)
    CreatedDate: Mapped[datetime] = mapped_column(
        "CreatedDate", DateTime, nullable=False, default=datetime.utcnow
    )
    UpdatedUser: Mapped[Optional[int]] = mapped_column("UpdatedUser", Integer, nullable=True)
    UpdatedDate: Mapped[Optional[datetime]] = mapped_column("UpdatedDate", DateTime, nullable=True)


class ClusterWiseAgentGrid(Base):
    """
    Cluster-Wise Agent Commission Grid Model.
    Physical Table: tbl_clusterwiseagentgrid
    Physical PK: GridId
    Legacy Reference: BLL_ClusterMaster, DAL_ClusterMaster, API_clusterwiseAgentgrid, sp_insertclusterwiseAgentgrid
    """
    __tablename__ = "tbl_clusterwiseagentgrid"
    __table_args__ = (
        Index("ix_tbl_cwag_Agent_Company", "AgentId", "InsuranceCompanyId"),
        Index("ix_tbl_cwag_ClusterMId", "ClusterMId"),
        {
            "mysql_charset": "utf8",
            "mysql_collate": "utf8_general_ci",
            "mysql_row_format": "DYNAMIC",
        },
    )

    GridId: Mapped[int] = mapped_column("GridId", Integer, primary_key=True, autoincrement=True)
    GridValue: Mapped[Decimal] = mapped_column(
        "GridValue", Numeric(12, 2), nullable=False, server_default=text("0.00")
    )
    CalOn: Mapped[Optional[str]] = mapped_column("CalOn", String(50), nullable=True)
    ODDiscount: Mapped[Decimal] = mapped_column(
        "ODDiscount", Numeric(12, 2), nullable=False, server_default=text("0.00")
    )
    ValidFrom: Mapped[date] = mapped_column("ValidFrom", Date, nullable=False, default=date.today)
    ReferenceType: Mapped[Optional[str]] = mapped_column("ReferenceType", String(50), nullable=True)
    AgentId: Mapped[int] = mapped_column("AgentId", Integer, nullable=False)
    BrokerId: Mapped[Optional[int]] = mapped_column("BrokerId", Integer, nullable=True)
    InsuranceCompanyId: Mapped[int] = mapped_column("InsuranceCompanyId", Integer, nullable=False)
    Veh_Type_ID: Mapped[int] = mapped_column("Veh_Type_ID", Integer, nullable=False)
    StateId: Mapped[int] = mapped_column("StateId", Integer, nullable=False)
    FuelTypeId: Mapped[Optional[int]] = mapped_column("FuelTypeId", Integer, nullable=True)
    ProductTypeId: Mapped[Optional[int]] = mapped_column("ProductTypeId", Integer, nullable=True)
    PolicyTypeId: Mapped[Optional[int]] = mapped_column("PolicyTypeId", Integer, nullable=True)
    ClusterMId: Mapped[int] = mapped_column("ClusterMId", Integer, nullable=False)
    CreatedUser: Mapped[Optional[int]] = mapped_column("CreatedUser", Integer, nullable=True)
    CreatedDate: Mapped[datetime] = mapped_column(
        "CreatedDate", DateTime, nullable=False, default=datetime.utcnow
    )
    UpdatedUser: Mapped[Optional[int]] = mapped_column("UpdatedUser", Integer, nullable=True)
    UpdatedDate: Mapped[Optional[datetime]] = mapped_column("UpdatedDate", DateTime, nullable=True)


# ============================================================================
# 6. DECLINE MODELS & RESTRICTIONS GRID (F-20-006)
# ============================================================================

class GridDeclineMaster(Base):
    """
    Vehicle Decline & Underwriting Restrictions Master Model.
    Physical Table: tbl_griddecline
    Physical PK: DeclineId
    Legacy Reference: BLL_Operations, DAL_Operations, API_GridDecline, sp_InsertGriddeclinemaster
    """
    __tablename__ = "tbl_griddecline"
    __table_args__ = (
        Index("ix_tbl_griddecline_Company_Policy", "InsuranceCompanyId", "PolicyTypeId"),
        Index("ix_tbl_griddecline_Make_Model", "MakeId", "ModelId"),
        {
            "mysql_charset": "utf8",
            "mysql_collate": "utf8_general_ci",
            "mysql_row_format": "DYNAMIC",
        },
    )

    DeclineId: Mapped[int] = mapped_column("DeclineId", Integer, primary_key=True, autoincrement=True)
    DeclineDate: Mapped[datetime] = mapped_column(
        "DeclineDate", DateTime, nullable=False, default=datetime.utcnow
    )
    InsuranceCompanyId: Mapped[int] = mapped_column("InsuranceCompanyId", Integer, nullable=False)
    MakeId: Mapped[int] = mapped_column("MakeId", Integer, nullable=False)
    PolicyTypeId: Mapped[int] = mapped_column("PolicyTypeId", Integer, nullable=False)
    ModelId: Mapped[Optional[int]] = mapped_column("ModelId", Integer, nullable=True)
    RtoId: Mapped[Optional[int]] = mapped_column("RtoId", Integer, nullable=True)
    ProductTypeId: Mapped[int] = mapped_column("ProductTypeId", Integer, nullable=False)
    FuelTypeId: Mapped[Optional[int]] = mapped_column("FuelTypeId", Integer, nullable=True)
    Guide_line: Mapped[Optional[str]] = mapped_column("Guide_line", String(1000), nullable=True)
    active: Mapped[int] = mapped_column("active", Integer, nullable=False, server_default=text("1"))
    CreatedUser: Mapped[Optional[int]] = mapped_column("CreatedUser", Integer, nullable=True)


class DeclineModel(Base):
    """
    Vehicle Model & Fuel-Type Level Decline Detail Rules.
    Physical Table: tbl_declinemodel
    Physical PK: Id
    Legacy Reference: sp_DeclineModel_2025, sp_SelectDeclineModel, sp_InsertGridDeclineDetails
    """
    __tablename__ = "tbl_declinemodel"
    __table_args__ = (
        Index("ix_tbl_declinemodel_DeclineId", "DeclineId"),
        Index("ix_tbl_declinemodel_Lookup", "InsuranceCompanyId", "MakeId", "ModelId"),
        {
            "mysql_charset": "utf8",
            "mysql_collate": "utf8_general_ci",
            "mysql_row_format": "DYNAMIC",
        },
    )

    Id: Mapped[int] = mapped_column("Id", Integer, primary_key=True, autoincrement=True)
    DeclineId: Mapped[Optional[int]] = mapped_column("DeclineId", Integer, nullable=True)
    MakeId: Mapped[int] = mapped_column("MakeId", Integer, nullable=False)
    ModelId: Mapped[int] = mapped_column("ModelId", Integer, nullable=False)
    InsuranceCompanyId: Mapped[int] = mapped_column("InsuranceCompanyId", Integer, nullable=False)
    PolicyTypeId: Mapped[int] = mapped_column("PolicyTypeId", Integer, nullable=False)
    ProductTypeId: Mapped[int] = mapped_column("ProductTypeId", Integer, nullable=False)
    RtoId: Mapped[Optional[int]] = mapped_column("RtoId", Integer, nullable=True)
    FuelTypeId: Mapped[Optional[int]] = mapped_column("FuelTypeId", Integer, nullable=True)
    Remark: Mapped[Optional[str]] = mapped_column("Remark", String(500), nullable=True)
    CreatedDate: Mapped[datetime] = mapped_column(
        "CreatedDate", DateTime, nullable=False, default=datetime.utcnow
    )
    CreatedBy: Mapped[Optional[int]] = mapped_column("CreatedBy", Integer, nullable=True)
