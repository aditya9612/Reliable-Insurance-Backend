"""
SQLAlchemy 2.0 Declarative Models for Phase 11 — Document, File Handling & Policy Parser Webhook Engine.

Additive unified document metadata model (`tbl_documents`) + HiCaliber Policy Parser
webhook staging model (`tbl_calliber_policy_webhook`).
Preserves full dual-write compatibility with legacy document columns/tables:
- `tbl_claimdocument` (`ClaimDocument`)
- `tbl_appendorsement.SupportingDocKey` (`PolicyEndorsement`)
- `tbl_app_requestedquotationfile` (`AppRequestedQuotationFile`)
- `tbl_insurancecompanyquotation` (`InsuranceCompanyQuotation`)
- `tbl_app_quotationrequest` (`AppQuotationRequest`)
- `tbl_transaction` (`CustDocStatus`, `calliber_policyId`, `calliber_UpdateBy`)
- `tbl_transactionappnew` (`Document_List`, `FileUpload`, `FileNameForPdf`)
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional
from sqlalchemy import Integer, String, Text, DateTime, Double, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class DocumentRecord(Base):
    """
    Unified Additive Document Metadata & Versioning Model
    Physical Table: tbl_documents
    Physical PK: DocumentId
    """
    __tablename__ = "tbl_documents"
    __table_args__ = (
        Index("ix_tbl_documents_DocumentUUID", "DocumentUUID", unique=True),
        Index("ix_tbl_documents_StorageKey", "StorageKey", unique=True),
        Index("ix_tbl_documents_EntityType_EntityId", "EntityType", "EntityId"),
        Index("ix_tbl_documents_TransanctionId", "TransanctionId"),
        Index("ix_tbl_documents_PolicyNo", "PolicyNo"),
        Index("ix_tbl_documents_QuotationId", "QuotationId"),
        Index("ix_tbl_documents_ClaimId", "ClaimId"),
        Index("ix_tbl_documents_EndorsementId", "EndorsementId"),
        Index("ix_tbl_documents_CustomerId", "CustomerId"),
        Index("ix_tbl_documents_CustVehId", "CustVehId"),
        Index("ix_tbl_documents_IdempotencyKey", "IdempotencyKey"),
        {
            "mysql_charset": "utf8",
            "mysql_collate": "utf8_general_ci",
            "mysql_row_format": "DYNAMIC",
        },
    )

    DocumentId: Mapped[int] = mapped_column("DocumentId", Integer, primary_key=True, autoincrement=True)
    DocumentUUID: Mapped[str] = mapped_column("DocumentUUID", String(64), nullable=False)
    DocumentType: Mapped[str] = mapped_column("DocumentType", String(50), nullable=False)
    DocSubType: Mapped[Optional[str]] = mapped_column("DocSubType", String(100), nullable=True)

    EntityType: Mapped[str] = mapped_column("EntityType", String(50), nullable=False)
    EntityId: Mapped[Optional[int]] = mapped_column("EntityId", Integer, nullable=True)

    TransanctionId: Mapped[Optional[int]] = mapped_column("TransanctionId", Integer, nullable=True)
    PolicyNo: Mapped[Optional[str]] = mapped_column("PolicyNo", String(100), nullable=True)
    QuotationId: Mapped[Optional[int]] = mapped_column("QuotationId", Integer, nullable=True)
    ClaimId: Mapped[Optional[int]] = mapped_column("ClaimId", Integer, nullable=True)
    EndorsementId: Mapped[Optional[int]] = mapped_column("EndorsementId", Integer, nullable=True)
    CustomerId: Mapped[Optional[int]] = mapped_column("CustomerId", Integer, nullable=True)
    CustVehId: Mapped[Optional[int]] = mapped_column("CustVehId", Integer, nullable=True)
    PaymentId: Mapped[Optional[int]] = mapped_column("PaymentId", Integer, nullable=True)

    BranchId: Mapped[Optional[int]] = mapped_column("BranchId", Integer, nullable=True)
    AgentId: Mapped[Optional[int]] = mapped_column("AgentId", Integer, nullable=True)
    FranchiseId: Mapped[Optional[int]] = mapped_column("FranchiseId", Integer, nullable=True)
    SalesExId: Mapped[Optional[int]] = mapped_column("SalesExId", Integer, nullable=True)

    LegacyVirtualFolder: Mapped[str] = mapped_column("LegacyVirtualFolder", String(100), nullable=False)
    OriginalFileName: Mapped[str] = mapped_column("OriginalFileName", String(255), nullable=False)
    StoredFileName: Mapped[str] = mapped_column("StoredFileName", String(255), nullable=False)
    StorageKey: Mapped[str] = mapped_column("StorageKey", String(500), nullable=False)

    MimeType: Mapped[str] = mapped_column("MimeType", String(120), nullable=False)
    FileExtension: Mapped[str] = mapped_column("FileExtension", String(30), nullable=False)
    FileSizeBytes: Mapped[int] = mapped_column("FileSizeBytes", Integer, nullable=False, default=0)
    ChecksumSha256: Mapped[str] = mapped_column("ChecksumSha256", String(64), nullable=False)

    VersionNo: Mapped[int] = mapped_column("VersionNo", Integer, nullable=False, default=1)
    ReplacesDocumentId: Mapped[Optional[int]] = mapped_column("ReplacesDocumentId", Integer, nullable=True)
    ReplacedByDocumentId: Mapped[Optional[int]] = mapped_column("ReplacedByDocumentId", Integer, nullable=True)

    LegacyRefTable: Mapped[Optional[str]] = mapped_column("LegacyRefTable", String(100), nullable=True)
    LegacyRefId: Mapped[Optional[int]] = mapped_column("LegacyRefId", Integer, nullable=True)

    VerifiedStatus: Mapped[str] = mapped_column("VerifiedStatus", String(30), nullable=False, default="PENDING")
    Remarks: Mapped[Optional[str]] = mapped_column("Remarks", String(500), nullable=True)
    IdempotencyKey: Mapped[Optional[str]] = mapped_column("IdempotencyKey", String(100), nullable=True)
    isdeleted: Mapped[str] = mapped_column("isdeleted", String(10), nullable=False, default="0")

    CreateDate: Mapped[datetime] = mapped_column("CreateDate", DateTime, nullable=False)
    CreateUser: Mapped[Optional[int]] = mapped_column("CreateUser", Integer, nullable=True)
    UpdateDate: Mapped[Optional[datetime]] = mapped_column("UpdateDate", DateTime, nullable=True)
    UpdateUser: Mapped[Optional[int]] = mapped_column("UpdateUser", Integer, nullable=True)


class PolicyParserWebhookRecord(Base):
    """
    HiCaliber Policy PDF OCR / Parser Webhook Ingestion Model (`PolicyParserWebhook.aspx.cs`)
    Physical Table: tbl_calliber_policy_webhook
    Physical PK: CalliberPolicyId
    """
    __tablename__ = "tbl_calliber_policy_webhook"
    __table_args__ = (
        Index("ix_tbl_calliber_webhook_PolicyNo", "PolicyNo"),
        Index("ix_tbl_calliber_webhook_IdempotencyKey", "IdempotencyKey"),
        Index("ix_tbl_calliber_webhook_PayloadSha256", "PayloadSha256"),
        {
            "mysql_charset": "utf8",
            "mysql_collate": "utf8_general_ci",
            "mysql_row_format": "DYNAMIC",
        },
    )

    CalliberPolicyId: Mapped[int] = mapped_column("CalliberPolicyId", Integer, primary_key=True, autoincrement=True)
    WebhookEventId: Mapped[Optional[str]] = mapped_column("WebhookEventId", String(100), nullable=True)
    IdempotencyKey: Mapped[Optional[str]] = mapped_column("IdempotencyKey", String(100), nullable=True)
    PayloadSha256: Mapped[str] = mapped_column("PayloadSha256", String(64), nullable=False)

    PolicyNo: Mapped[Optional[str]] = mapped_column("PolicyNo", String(100), nullable=True)
    CustomerName: Mapped[Optional[str]] = mapped_column("CustomerName", String(255), nullable=True)
    VehicleRegNo: Mapped[Optional[str]] = mapped_column("VehicleRegNo", String(100), nullable=True)
    EngineNo: Mapped[Optional[str]] = mapped_column("EngineNo", String(100), nullable=True)
    ChassisNo: Mapped[Optional[str]] = mapped_column("ChassisNo", String(100), nullable=True)
    InsCompany: Mapped[Optional[str]] = mapped_column("InsCompany", String(255), nullable=True)
    ProductType: Mapped[Optional[str]] = mapped_column("ProductType", String(100), nullable=True)
    PolicyType: Mapped[Optional[str]] = mapped_column("PolicyType", String(100), nullable=True)
    StartDate: Mapped[Optional[str]] = mapped_column("StartDate", String(50), nullable=True)
    EndDate: Mapped[Optional[str]] = mapped_column("EndDate", String(50), nullable=True)

    IDV: Mapped[Decimal] = mapped_column("IDV", Double(asdecimal=True), nullable=False, default=Decimal("0.00"))
    ODPremium: Mapped[Decimal] = mapped_column("ODPremium", Double(asdecimal=True), nullable=False, default=Decimal("0.00"))
    TPPremium: Mapped[Decimal] = mapped_column("TPPremium", Double(asdecimal=True), nullable=False, default=Decimal("0.00"))
    NetPremium: Mapped[Decimal] = mapped_column("NetPremium", Double(asdecimal=True), nullable=False, default=Decimal("0.00"))
    GSTAmount: Mapped[Decimal] = mapped_column("GSTAmount", Double(asdecimal=True), nullable=False, default=Decimal("0.00"))
    GrossPremium: Mapped[Decimal] = mapped_column("GrossPremium", Double(asdecimal=True), nullable=False, default=Decimal("0.00"))
    NCBPercent: Mapped[Decimal] = mapped_column("NCBPercent", Double(asdecimal=True), nullable=False, default=Decimal("0.00"))

    DocumentId: Mapped[Optional[int]] = mapped_column("DocumentId", Integer, nullable=True)
    LinkedTransanctionId: Mapped[Optional[int]] = mapped_column("LinkedTransanctionId", Integer, nullable=True)
    RawPayloadJson: Mapped[str] = mapped_column("RawPayloadJson", Text, nullable=False)
    ProcessingStatus: Mapped[str] = mapped_column("ProcessingStatus", String(30), nullable=False, default="PROCESSED")
    UpdatedBy: Mapped[Optional[str]] = mapped_column("UpdatedBy", String(200), nullable=True)
    isdeleted: Mapped[str] = mapped_column("isdeleted", String(10), nullable=False, default="0")

    CreateDate: Mapped[datetime] = mapped_column("CreateDate", DateTime, nullable=False)
    UpdateDate: Mapped[Optional[datetime]] = mapped_column("UpdateDate", DateTime, nullable=True)
