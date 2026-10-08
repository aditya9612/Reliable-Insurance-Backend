"""
SQLAlchemy 2.0 Declarative Models for Phase 18A — Complete Remaining Legacy Feature Implementation.
Physical Tables Added:
1. tbl_idealpaymentreceipt (Ideal / Broker Payment Receipt & Multi-Agent Settlement — F-17B-085)
2. tbl_commission_rate_grid (Partner Commission Rate Grid & Reliance OD Capping — F-17B-086)
3. tbl_remainingpendingcash (Remaining / Shortfall Cash Premium Ledger — F-17B-087)
4. tbl_salesregistration (Insurer B2B Sales Invoice Registration & Advance Adjustment — F-17B-088)
5. tbl_inspectionrequest (Vehicle Break-In Inspection Coordinator Request Queue — F-17B-091)
6. tbl_supportapp (Internal IT / Operator / Admin Support Ticketing Portal — F-17B-092)
7. tbl_callingimportdata (Telecalling Lead Import, Call Disposition & Field GPS Check-In — F-17B-093 / F-17B-098)
8. tbl_cashback (Cashback & Promotional Scheme Entry — F-17B-095)
"""
from datetime import datetime, date
from decimal import Decimal
from typing import Optional
from sqlalchemy import Integer, String, DateTime, Date, Numeric, Text, Index, text
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class IdealPaymentReceipt(Base):
    """
    Ideal / Broker Bulk Payment Receipt & Policy Commission Settlement Model.
    Physical Table: tbl_idealpaymentreceipt
    Physical PK: Id
    Legacy Reference: POSP_MultiEntryIdealPayment.aspx.cs, API_IdealPaymentReceipt, DAL_IdealPaymentReceipt
    """
    __tablename__ = "tbl_idealpaymentreceipt"
    __table_args__ = (
        Index("ix_tbl_idealpaymentreceipt_Ideal_Doc_No", "Ideal_Doc_No"),
        Index("ix_tbl_idealpaymentreceipt_POSP_Id", "POSP_Id"),
        Index("ix_tbl_idealpaymentreceipt_TransactionId", "TransactionId"),
        {
            "mysql_charset": "utf8",
            "mysql_collate": "utf8_general_ci",
            "mysql_row_format": "DYNAMIC",
        },
    )

    Id: Mapped[int] = mapped_column("Id", Integer, primary_key=True, autoincrement=True)
    Ideal_Doc_No: Mapped[str] = mapped_column("Ideal_Doc_No", String(100), nullable=False)
    PaymentDate: Mapped[Optional[date]] = mapped_column("PaymentDate", Date, nullable=True)
    POSPType_Id: Mapped[Optional[int]] = mapped_column("POSPType_Id", Integer, nullable=True)
    POSP_Id: Mapped[Optional[int]] = mapped_column("POSP_Id", Integer, nullable=True)
    Ideal_Amount: Mapped[Decimal] = mapped_column(
        "Ideal_Amount", Numeric(15, 2), nullable=False, server_default=text("0.00")
    )
    Ideal_NEFTNo: Mapped[Optional[str]] = mapped_column("Ideal_NEFTNo", String(100), nullable=True)
    PolicyNo: Mapped[Optional[str]] = mapped_column("PolicyNo", String(255), nullable=True)
    TransactionId: Mapped[Optional[int]] = mapped_column("TransactionId", Integer, nullable=True)
    ReceiptType: Mapped[str] = mapped_column(
        "ReceiptType", String(50), nullable=False, server_default=text("'Regular'")
    )
    IsDelete: Mapped[int] = mapped_column("IsDelete", Integer, nullable=False, server_default=text("0"))
    CreatedBy: Mapped[Optional[int]] = mapped_column("CreatedBy", Integer, nullable=True)
    CreateDate: Mapped[Optional[datetime]] = mapped_column(
        "CreateDate", DateTime, nullable=True, default=datetime.utcnow
    )


class CommissionRateGrid(Base):
    """
    Partner Commission Rate Grid (Broker / Agent / Franchise / Cluster) Model.
    Physical Table: tbl_commission_rate_grid
    Physical PK: GridId
    Legacy Reference: API_BrokerCommission, API_clusterwisebrokergrid, API_clusterwiseAgentgrid, DAL_Capping
    """
    __tablename__ = "tbl_commission_rate_grid"
    __table_args__ = (
        Index("ix_tbl_commission_rate_grid_InsComp", "InsuranceCompanyId"),
        Index("ix_tbl_commission_rate_grid_VehiType", "VehiTypeId"),
        Index("ix_tbl_commission_rate_grid_BrokerId", "BrokerId"),
        Index("ix_tbl_commission_rate_grid_FranchiseId", "FranchiseId"),
        Index("ix_tbl_commission_rate_grid_AgentId", "AgentId"),
        {
            "mysql_charset": "utf8",
            "mysql_collate": "utf8_general_ci",
            "mysql_row_format": "DYNAMIC",
        },
    )

    GridId: Mapped[int] = mapped_column("GridId", Integer, primary_key=True, autoincrement=True)
    GridScope: Mapped[str] = mapped_column(
        "GridScope", String(50), nullable=False, server_default=text("'BROKER'")
    )
    InsuranceCompanyId: Mapped[int] = mapped_column("InsuranceCompanyId", Integer, nullable=False)
    PolicyTypeId: Mapped[Optional[int]] = mapped_column("PolicyTypeId", Integer, nullable=True)
    ProductTypeId: Mapped[Optional[int]] = mapped_column("ProductTypeId", Integer, nullable=True)
    VehiTypeId: Mapped[Optional[int]] = mapped_column("VehiTypeId", Integer, nullable=True)
    VehiSubTypeId: Mapped[Optional[int]] = mapped_column("VehiSubTypeId", Integer, nullable=True)
    FuelTypeId: Mapped[Optional[int]] = mapped_column("FuelTypeId", Integer, nullable=True)
    MakeId: Mapped[Optional[int]] = mapped_column("MakeId", Integer, nullable=True)
    ModelId: Mapped[Optional[int]] = mapped_column("ModelId", Integer, nullable=True)
    RTO_Id: Mapped[Optional[int]] = mapped_column("RTO_Id", Integer, nullable=True)
    StateId: Mapped[Optional[int]] = mapped_column("StateId", Integer, nullable=True)
    ClusterMId: Mapped[Optional[int]] = mapped_column("ClusterMId", Integer, nullable=True)
    BrokerId: Mapped[Optional[int]] = mapped_column("BrokerId", Integer, nullable=True)
    FranchiseId: Mapped[Optional[int]] = mapped_column("FranchiseId", Integer, nullable=True)
    AgentId: Mapped[Optional[int]] = mapped_column("AgentId", Integer, nullable=True)
    Commission_OD: Mapped[Decimal] = mapped_column(
        "Commission_OD", Numeric(10, 2), nullable=False, server_default=text("0.00")
    )
    Commission_Net: Mapped[Decimal] = mapped_column(
        "Commission_Net", Numeric(10, 2), nullable=False, server_default=text("0.00")
    )
    Commission_TP: Mapped[Decimal] = mapped_column(
        "Commission_TP", Numeric(10, 2), nullable=False, server_default=text("0.00")
    )
    OD_Discount: Mapped[Decimal] = mapped_column(
        "OD_Discount", Numeric(10, 2), nullable=False, server_default=text("0.00")
    )
    CalOn: Mapped[str] = mapped_column("CalOn", String(50), nullable=False, server_default=text("'OD'"))
    ValidFromDate: Mapped[Optional[date]] = mapped_column("ValidFromDate", Date, nullable=True)
    ValidToDate: Mapped[Optional[date]] = mapped_column("ValidToDate", Date, nullable=True)
    isdeleted: Mapped[str] = mapped_column("isdeleted", String(10), nullable=False, server_default=text("'0'"))
    CreateUser: Mapped[Optional[int]] = mapped_column("CreateUser", Integer, nullable=True)
    Createdate: Mapped[Optional[datetime]] = mapped_column(
        "Createdate", DateTime, nullable=True, default=datetime.utcnow
    )


class RemainingPendingCash(Base):
    """
    Remaining / Shortfall Cash Premium Ledger & Cashier Approval Model.
    Physical Table: tbl_remainingpendingcash
    Physical PK: PendingCashId
    Legacy Reference: API_RemainingPendingCash, BLL_RemainingPendingCash, adm_LockCashEntry1.aspx.cs
    """
    __tablename__ = "tbl_remainingpendingcash"
    __table_args__ = (
        Index("ix_tbl_remainingpendingcash_AgentId", "AgentId"),
        Index("ix_tbl_remainingpendingcash_ExecutiveId", "ExecutiveId"),
        Index("ix_tbl_remainingpendingcash_BranchId", "BranchId"),
        Index("ix_tbl_remainingpendingcash_CashierApproval", "CashierApproval"),
        {
            "mysql_charset": "utf8",
            "mysql_collate": "utf8_general_ci",
            "mysql_row_format": "DYNAMIC",
        },
    )

    PendingCashId: Mapped[int] = mapped_column(
        "PendingCashId", Integer, primary_key=True, autoincrement=True
    )
    TransactionIdsCsv: Mapped[Optional[str]] = mapped_column(
        "TransactionIdsCsv", String(500), nullable=True
    )
    TotalPremium: Mapped[Decimal] = mapped_column(
        "TotalPremium", Numeric(15, 2), nullable=False, server_default=text("0.00")
    )
    PaidPremium: Mapped[Decimal] = mapped_column(
        "PaidPremium", Numeric(15, 2), nullable=False, server_default=text("0.00")
    )
    RemainingPremium: Mapped[Decimal] = mapped_column(
        "RemainingPremium", Numeric(15, 2), nullable=False, server_default=text("0.00")
    )
    ShortfallAmt: Mapped[Decimal] = mapped_column(
        "ShortfallAmt", Numeric(15, 2), nullable=False, server_default=text("0.00")
    )
    RemainingStatus: Mapped[str] = mapped_column(
        "RemainingStatus", String(50), nullable=False, server_default=text("'Short Fall'")
    )
    UserRoleId: Mapped[Optional[int]] = mapped_column("UserRoleId", Integer, nullable=True)
    AgentId: Mapped[Optional[int]] = mapped_column("AgentId", Integer, nullable=True)
    ExecutiveId: Mapped[Optional[int]] = mapped_column("ExecutiveId", Integer, nullable=True)
    BranchId: Mapped[Optional[int]] = mapped_column("BranchId", Integer, nullable=True)
    SupportingFileKey: Mapped[Optional[str]] = mapped_column(
        "SupportingFileKey", String(255), nullable=True
    )
    CashierApproval: Mapped[int] = mapped_column(
        "CashierApproval", Integer, nullable=False, server_default=text("0")
    )
    ApprovedBy: Mapped[Optional[int]] = mapped_column("ApprovedBy", Integer, nullable=True)
    ApprovedDate: Mapped[Optional[datetime]] = mapped_column("ApprovedDate", DateTime, nullable=True)
    Remark: Mapped[Optional[str]] = mapped_column("Remark", String(500), nullable=True)
    CreateUser: Mapped[Optional[int]] = mapped_column("CreateUser", Integer, nullable=True)
    CreateDate: Mapped[Optional[datetime]] = mapped_column(
        "CreateDate", DateTime, nullable=True, default=datetime.utcnow
    )


class SalesRegistration(Base):
    """
    Insurer B2B Sales Invoice Registration & Company Advance Master Adjustment Model.
    Physical Table: tbl_salesregistration
    Physical PK: salesRegId
    Legacy Reference: API_salesregistration, BLL_Loan.BLL_InsertSalesRegistration, BLL_UpdateCompanyAdvMaster
    """
    __tablename__ = "tbl_salesregistration"
    __table_args__ = (
        Index("ix_tbl_salesregistration_InvoiceNo", "InvoiceNo"),
        Index("ix_tbl_salesregistration_ClientMasterId", "ClientMasterId"),
        Index("ix_tbl_salesregistration_LedgerMId", "LedgerMId"),
        {
            "mysql_charset": "utf8",
            "mysql_collate": "utf8_general_ci",
            "mysql_row_format": "DYNAMIC",
        },
    )

    salesRegId: Mapped[int] = mapped_column(
        "salesRegId", Integer, primary_key=True, autoincrement=True
    )
    InvoiceNo: Mapped[str] = mapped_column("InvoiceNo", String(100), nullable=False)
    RegistrationType: Mapped[Optional[str]] = mapped_column(
        "RegistrationType", String(100), nullable=True
    )
    SalesDate: Mapped[date] = mapped_column("SalesDate", Date, nullable=False)
    RCompanyId: Mapped[Optional[int]] = mapped_column("RCompanyId", Integer, nullable=True)
    SalesTypeId: Mapped[Optional[int]] = mapped_column("SalesTypeId", Integer, nullable=True)
    SalesType: Mapped[Optional[str]] = mapped_column("SalesType", String(100), nullable=True)
    ClientMasterId: Mapped[int] = mapped_column("ClientMasterId", Integer, nullable=False)
    LedgerMId: Mapped[Optional[int]] = mapped_column("LedgerMId", Integer, nullable=True)
    Description: Mapped[Optional[str]] = mapped_column("Description", String(500), nullable=True)
    amount: Mapped[Decimal] = mapped_column(
        "amount", Numeric(15, 2), nullable=False, server_default=text("0.00")
    )
    CGSTPer: Mapped[Decimal] = mapped_column(
        "CGSTPer", Numeric(6, 2), nullable=False, server_default=text("0.00")
    )
    CGSTAmt: Mapped[Decimal] = mapped_column(
        "CGSTAmt", Numeric(15, 2), nullable=False, server_default=text("0.00")
    )
    SGSTPer: Mapped[Decimal] = mapped_column(
        "SGSTPer", Numeric(6, 2), nullable=False, server_default=text("0.00")
    )
    SGSTAmt: Mapped[Decimal] = mapped_column(
        "SGSTAmt", Numeric(15, 2), nullable=False, server_default=text("0.00")
    )
    IGSTPer: Mapped[Decimal] = mapped_column(
        "IGSTPer", Numeric(6, 2), nullable=False, server_default=text("0.00")
    )
    IGSTAmt: Mapped[Decimal] = mapped_column(
        "IGSTAmt", Numeric(15, 2), nullable=False, server_default=text("0.00")
    )
    Total: Mapped[Decimal] = mapped_column(
        "Total", Numeric(15, 2), nullable=False, server_default=text("0.00")
    )
    ReceivedAmt: Mapped[Decimal] = mapped_column(
        "ReceivedAmt", Numeric(15, 2), nullable=False, server_default=text("0.00")
    )
    BalanceAmt: Mapped[Decimal] = mapped_column(
        "BalanceAmt", Numeric(15, 2), nullable=False, server_default=text("0.00")
    )
    AccDocNo: Mapped[Optional[str]] = mapped_column("AccDocNo", String(100), nullable=True)
    CreatedUser: Mapped[Optional[int]] = mapped_column("CreatedUser", Integer, nullable=True)
    Createdate: Mapped[Optional[datetime]] = mapped_column(
        "Createdate", DateTime, nullable=True, default=datetime.utcnow
    )


class InspectionCoordinatorRequest(Base):
    """
    Vehicle Break-In Inspection Coordinator Request Queue Model.
    Physical Table: tbl_inspectionrequest
    Physical PK: InspectionId
    Legacy Reference: View_InspectionCordinatorRequest.aspx.cs, BLL_InspectionRequest
    """
    __tablename__ = "tbl_inspectionrequest"
    __table_args__ = (
        Index("ix_tbl_inspectionrequest_TransId", "TransId"),
        Index("ix_tbl_inspectionrequest_RegistrationNo", "RegistrationNo"),
        Index("ix_tbl_inspectionrequest_BranchId", "BranchId"),
        Index("ix_tbl_inspectionrequest_FranchiseId", "FranchiseId"),
        Index("ix_tbl_inspectionrequest_AgentId", "AgentId"),
        Index("ix_tbl_inspectionrequest_InspectionStatus", "InspectionStatus"),
        {
            "mysql_charset": "utf8",
            "mysql_collate": "utf8_general_ci",
            "mysql_row_format": "DYNAMIC",
        },
    )

    InspectionId: Mapped[int] = mapped_column(
        "InspectionId", Integer, primary_key=True, autoincrement=True
    )
    TransId: Mapped[Optional[int]] = mapped_column("TransId", Integer, nullable=True)
    RegistrationNo: Mapped[str] = mapped_column("RegistrationNo", String(50), nullable=False)
    CustomerName: Mapped[Optional[str]] = mapped_column("CustomerName", String(255), nullable=True)
    MobileNo: Mapped[Optional[str]] = mapped_column("MobileNo", String(50), nullable=True)
    InsuranceCompanyId: Mapped[Optional[int]] = mapped_column(
        "InsuranceCompanyId", Integer, nullable=True
    )
    VehicleTypeId: Mapped[Optional[int]] = mapped_column("VehicleTypeId", Integer, nullable=True)
    BranchId: Mapped[Optional[int]] = mapped_column("BranchId", Integer, nullable=True)
    FranchiseId: Mapped[Optional[int]] = mapped_column("FranchiseId", Integer, nullable=True)
    AgentId: Mapped[Optional[int]] = mapped_column("AgentId", Integer, nullable=True)
    ExecutiveId: Mapped[Optional[int]] = mapped_column("ExecutiveId", Integer, nullable=True)
    LeadNo: Mapped[Optional[str]] = mapped_column("LeadNo", String(100), nullable=True)
    InspectionStatus: Mapped[str] = mapped_column(
        "InspectionStatus", String(50), nullable=False, server_default=text("'PENDING'")
    )
    IsOwner: Mapped[int] = mapped_column("IsOwner", Integer, nullable=False, server_default=text("0"))
    InspectionPdfPath: Mapped[Optional[str]] = mapped_column(
        "InspectionPdfPath", String(255), nullable=True
    )
    ImagePathsJson: Mapped[Optional[str]] = mapped_column("ImagePathsJson", Text, nullable=True)
    Remark: Mapped[Optional[str]] = mapped_column("Remark", String(500), nullable=True)
    CreateUser: Mapped[Optional[int]] = mapped_column("CreateUser", Integer, nullable=True)
    CreatedDate: Mapped[Optional[datetime]] = mapped_column(
        "CreatedDate", DateTime, nullable=True, default=datetime.utcnow
    )
    UpdatedBy: Mapped[Optional[int]] = mapped_column("UpdatedBy", Integer, nullable=True)
    UpdatedDate: Mapped[Optional[datetime]] = mapped_column("UpdatedDate", DateTime, nullable=True)


class SupportTicket(Base):
    """
    Internal IT / Operator / Admin Support Ticketing Portal Model.
    Physical Table: tbl_supportapp
    Physical PK: SupportId
    Legacy Reference: API_SupportApp, API_SupportAPPFile, DAL_SupportPortal
    """
    __tablename__ = "tbl_supportapp"
    __table_args__ = (
        Index("ix_tbl_supportapp_UserId", "UserId"),
        Index("ix_tbl_supportapp_BranchId", "BranchId"),
        Index("ix_tbl_supportapp_Status", "Status"),
        {
            "mysql_charset": "utf8",
            "mysql_collate": "utf8_general_ci",
            "mysql_row_format": "DYNAMIC",
        },
    )

    SupportId: Mapped[int] = mapped_column("SupportId", Integer, primary_key=True, autoincrement=True)
    SupportTypeId: Mapped[int] = mapped_column(
        "SupportTypeId", Integer, nullable=False, server_default=text("1")
    )
    SupportType: Mapped[str] = mapped_column(
        "SupportType", String(100), nullable=False, server_default=text("'GENERAL'")
    )
    SupportDate: Mapped[Optional[datetime]] = mapped_column(
        "SupportDate", DateTime, nullable=True, default=datetime.utcnow
    )
    UserId: Mapped[int] = mapped_column("UserId", Integer, nullable=False)
    UserRoleId: Mapped[Optional[int]] = mapped_column("UserRoleId", Integer, nullable=True)
    BranchId: Mapped[Optional[int]] = mapped_column("BranchId", Integer, nullable=True)
    Remark: Mapped[str] = mapped_column("Remark", Text, nullable=False)
    RemarkFrom: Mapped[Optional[str]] = mapped_column("RemarkFrom", String(50), nullable=True)
    RemarksThreadJson: Mapped[Optional[str]] = mapped_column("RemarksThreadJson", Text, nullable=True)
    AttachmentFileName: Mapped[Optional[str]] = mapped_column(
        "AttachmentFileName", String(255), nullable=True
    )
    AttendBy: Mapped[Optional[int]] = mapped_column("AttendBy", Integer, nullable=True)
    Status: Mapped[str] = mapped_column(
        "Status", String(50), nullable=False, server_default=text("'OPEN'")
    )
    isApproved: Mapped[int] = mapped_column(
        "isApproved", Integer, nullable=False, server_default=text("0")
    )
    ApprovedBy: Mapped[Optional[int]] = mapped_column("ApprovedBy", Integer, nullable=True)
    ApprovedDate: Mapped[Optional[datetime]] = mapped_column("ApprovedDate", DateTime, nullable=True)
    UpdateBy: Mapped[Optional[int]] = mapped_column("UpdateBy", Integer, nullable=True)
    UpdateDate: Mapped[Optional[datetime]] = mapped_column("UpdateDate", DateTime, nullable=True)


class CallingImportLead(Base):
    """
    Telecalling Lead Import, Call Disposition & Field Visit GPS Check-In Model.
    Physical Table: tbl_callingimportdata
    Physical PK: CallingImportId
    Legacy Reference: API_CallingImportDatat, API_CallRecord, BLL_CallingImportToExcel, Clerk/Location.aspx.cs
    """
    __tablename__ = "tbl_callingimportdata"
    __table_args__ = (
        Index("ix_tbl_callingimportdata_RegistrationNo", "RegistrationNo"),
        Index("ix_tbl_callingimportdata_MobileNo", "MobileNo"),
        Index("ix_tbl_callingimportdata_UserId", "UserId"),
        Index("ix_tbl_callingimportdata_BranchId", "BranchId"),
        Index("ix_tbl_callingimportdata_FollowUpDate", "FollowUpDate"),
        {
            "mysql_charset": "utf8",
            "mysql_collate": "utf8_general_ci",
            "mysql_row_format": "DYNAMIC",
        },
    )

    CallingImportId: Mapped[int] = mapped_column(
        "CallingImportId", Integer, primary_key=True, autoincrement=True
    )
    RegistrationNo: Mapped[str] = mapped_column("RegistrationNo", String(50), nullable=False)
    RegistrationType: Mapped[Optional[str]] = mapped_column(
        "RegistrationType", String(100), nullable=True
    )
    RegnDate: Mapped[Optional[date]] = mapped_column("RegnDate", Date, nullable=True)
    OwnerName: Mapped[Optional[str]] = mapped_column("OwnerName", String(255), nullable=True)
    FatherName: Mapped[Optional[str]] = mapped_column("FatherName", String(255), nullable=True)
    PermanentAddress: Mapped[Optional[str]] = mapped_column(
        "PermanentAddress", String(500), nullable=True
    )
    ChassisNo: Mapped[Optional[str]] = mapped_column("ChassisNo", String(100), nullable=True)
    EngNo: Mapped[Optional[str]] = mapped_column("EngNo", String(100), nullable=True)
    VehicleClass: Mapped[Optional[str]] = mapped_column("VehicleClass", String(100), nullable=True)
    MakerModel: Mapped[Optional[str]] = mapped_column("MakerModel", String(255), nullable=True)
    DealerName: Mapped[Optional[str]] = mapped_column("DealerName", String(255), nullable=True)
    MobileNo: Mapped[Optional[str]] = mapped_column("MobileNo", String(50), nullable=True)
    UserId: Mapped[Optional[int]] = mapped_column("UserId", Integer, nullable=True)
    BranchId: Mapped[Optional[int]] = mapped_column("BranchId", Integer, nullable=True)
    CallingStatusId: Mapped[Optional[int]] = mapped_column(
        "CallingStatusId", Integer, nullable=True, server_default=text("0")
    )
    CallingStatusName: Mapped[Optional[str]] = mapped_column(
        "CallingStatusName", String(100), nullable=True, server_default=text("'NEW'")
    )
    CallingDate: Mapped[Optional[datetime]] = mapped_column("CallingDate", DateTime, nullable=True)
    FollowUpDate: Mapped[Optional[date]] = mapped_column("FollowUpDate", Date, nullable=True)
    Note: Mapped[Optional[str]] = mapped_column("Note", String(500), nullable=True)
    HistoryJson: Mapped[Optional[str]] = mapped_column("HistoryJson", Text, nullable=True)
    Latitude: Mapped[Optional[str]] = mapped_column("Latitude", String(50), nullable=True)
    Longitude: Mapped[Optional[str]] = mapped_column("Longitude", String(50), nullable=True)
    GPSLocation: Mapped[Optional[str]] = mapped_column("GPSLocation", String(500), nullable=True)
    CreateUser: Mapped[Optional[int]] = mapped_column("CreateUser", Integer, nullable=True)
    Createdate: Mapped[Optional[datetime]] = mapped_column(
        "Createdate", DateTime, nullable=True, default=datetime.utcnow
    )


class CashbackEntry(Base):
    """
    Cashback & Promotional Scheme Entry Model.
    Physical Table: tbl_cashback
    Physical PK: cashbackId
    Legacy Reference: API_cashback, DAL_CashBackAmount, BLL_OutStandingAmount.BLL_SelectCashBackAmtReport
    """
    __tablename__ = "tbl_cashback"
    __table_args__ = (
        Index("ix_tbl_cashback_TransactionId", "TransactionId"),
        Index("ix_tbl_cashback_CustomerId", "CustomerId"),
        Index("ix_tbl_cashback_AgentId", "AgentId"),
        Index("ix_tbl_cashback_BranchId", "BranchId"),
        {
            "mysql_charset": "utf8",
            "mysql_collate": "utf8_general_ci",
            "mysql_row_format": "DYNAMIC",
        },
    )

    cashbackId: Mapped[int] = mapped_column("cashbackId", Integer, primary_key=True, autoincrement=True)
    TransactionId: Mapped[int] = mapped_column("TransactionId", Integer, nullable=False)
    CustomerId: Mapped[Optional[int]] = mapped_column("CustomerId", Integer, nullable=True)
    CustVehId: Mapped[Optional[int]] = mapped_column("CustVehId", Integer, nullable=True)
    AgentId: Mapped[Optional[int]] = mapped_column("AgentId", Integer, nullable=True)
    BranchId: Mapped[Optional[int]] = mapped_column("BranchId", Integer, nullable=True)
    cashbackamount: Mapped[Decimal] = mapped_column(
        "cashbackamount", Numeric(15, 2), nullable=False, server_default=text("0.00")
    )
    TransDate: Mapped[date] = mapped_column("TransDate", Date, nullable=False)
    narration: Mapped[Optional[str]] = mapped_column("narration", String(500), nullable=True)
    Status: Mapped[str] = mapped_column(
        "Status", String(50), nullable=False, server_default=text("'APPROVED'")
    )
    CreatedUser: Mapped[Optional[int]] = mapped_column("CreatedUser", Integer, nullable=True)
    CreatedDate: Mapped[Optional[datetime]] = mapped_column(
        "CreatedDate", DateTime, nullable=True, default=datetime.utcnow
    )
