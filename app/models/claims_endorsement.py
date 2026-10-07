from datetime import datetime
from decimal import Decimal
from typing import Optional
from sqlalchemy import Integer, String, Text, DateTime, Double, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class Claim(Base):
    """
    Motor Insurance Claim Lifecycle & Settlement Model
    Physical Table: tbl_claims
    Physical PK: ClaimId
    """
    __tablename__ = "tbl_claims"
    __table_args__ = (
        Index("ix_tbl_claims_TransanctionId", "TransanctionId"),
        Index("ix_tbl_claims_ClaimNo", "ClaimNo", unique=True),
        Index("ix_tbl_claims_IdempotencyKey", "IdempotencyKey"),
        {
            "mysql_charset": "utf8",
            "mysql_collate": "utf8_general_ci",
            "mysql_row_format": "DYNAMIC",
        },
    )

    ClaimId: Mapped[int] = mapped_column("ClaimId", Integer, primary_key=True, autoincrement=True)
    ClaimNo: Mapped[str] = mapped_column("ClaimNo", String(50), nullable=False)
    TransanctionId: Mapped[int] = mapped_column("TransanctionId", Integer, nullable=False)
    PolicyNo: Mapped[Optional[str]] = mapped_column("PolicyNo", String(100), nullable=True)
    CustomerId: Mapped[Optional[int]] = mapped_column("CustomerId", Integer, nullable=True)
    CustVehId: Mapped[Optional[int]] = mapped_column("CustVehId", Integer, nullable=True)
    InsuranceCompanyId: Mapped[Optional[int]] = mapped_column("InsuranceCompanyId", Integer, nullable=True)
    BranchId: Mapped[Optional[int]] = mapped_column("BranchId", Integer, nullable=True)
    AgentId: Mapped[Optional[int]] = mapped_column("AgentId", Integer, nullable=True)
    FranchiseId: Mapped[Optional[int]] = mapped_column("FranchiseId", Integer, nullable=True)
    SalesExId: Mapped[Optional[int]] = mapped_column("SalesExId", Integer, nullable=True)

    ClaimType: Mapped[str] = mapped_column("ClaimType", String(30), nullable=False, default="OD")
    ClaimStatus: Mapped[str] = mapped_column("ClaimStatus", String(30), nullable=False, default="INTIMATED")

    IntimationDate: Mapped[datetime] = mapped_column("IntimationDate", DateTime, nullable=False)
    LossDate: Mapped[datetime] = mapped_column("LossDate", DateTime, nullable=False)
    LossLocation: Mapped[Optional[str]] = mapped_column("LossLocation", String(255), nullable=True)
    LossDescription: Mapped[Optional[str]] = mapped_column("LossDescription", Text, nullable=True)
    EstimatedAmount: Mapped[Decimal] = mapped_column(
        "EstimatedAmount", Double(asdecimal=True), nullable=False, default=Decimal("0.00")
    )

    SurveyorName: Mapped[Optional[str]] = mapped_column("SurveyorName", String(150), nullable=True)
    SurveyorMobile: Mapped[Optional[str]] = mapped_column("SurveyorMobile", String(20), nullable=True)
    SurveyorLicenseNo: Mapped[Optional[str]] = mapped_column("SurveyorLicenseNo", String(50), nullable=True)
    SurveyDate: Mapped[Optional[datetime]] = mapped_column("SurveyDate", DateTime, nullable=True)

    AssessedLossAmount: Mapped[Decimal] = mapped_column(
        "AssessedLossAmount", Double(asdecimal=True), nullable=False, default=Decimal("0.00")
    )
    DepreciationAmount: Mapped[Decimal] = mapped_column(
        "DepreciationAmount", Double(asdecimal=True), nullable=False, default=Decimal("0.00")
    )
    DeductibleAmount: Mapped[Decimal] = mapped_column(
        "DeductibleAmount", Double(asdecimal=True), nullable=False, default=Decimal("0.00")
    )
    ExcessAmount: Mapped[Decimal] = mapped_column(
        "ExcessAmount", Double(asdecimal=True), nullable=False, default=Decimal("0.00")
    )
    SalvageAmount: Mapped[Decimal] = mapped_column(
        "SalvageAmount", Double(asdecimal=True), nullable=False, default=Decimal("0.00")
    )
    ApprovedAmount: Mapped[Decimal] = mapped_column(
        "ApprovedAmount", Double(asdecimal=True), nullable=False, default=Decimal("0.00")
    )
    SettledAmount: Mapped[Decimal] = mapped_column(
        "SettledAmount", Double(asdecimal=True), nullable=False, default=Decimal("0.00")
    )
    InsurerPayableAmount: Mapped[Decimal] = mapped_column(
        "InsurerPayableAmount", Double(asdecimal=True), nullable=False, default=Decimal("0.00")
    )
    CustomerPayableAmount: Mapped[Decimal] = mapped_column(
        "CustomerPayableAmount", Double(asdecimal=True), nullable=False, default=Decimal("0.00")
    )
    GaragePayableAmount: Mapped[Decimal] = mapped_column(
        "GaragePayableAmount", Double(asdecimal=True), nullable=False, default=Decimal("0.00")
    )

    PayeeType: Mapped[Optional[str]] = mapped_column("PayeeType", String(30), nullable=True)
    PaymentMode: Mapped[Optional[str]] = mapped_column("PaymentMode", String(30), nullable=True)
    PaymentDocNo: Mapped[Optional[str]] = mapped_column("PaymentDocNo", String(100), nullable=True)
    SettlementDate: Mapped[Optional[datetime]] = mapped_column("SettlementDate", DateTime, nullable=True)
    InsurerClaimRef: Mapped[Optional[str]] = mapped_column("InsurerClaimRef", String(100), nullable=True)

    RejectionReason: Mapped[Optional[str]] = mapped_column("RejectionReason", String(500), nullable=True)
    Remarks: Mapped[Optional[str]] = mapped_column("Remarks", Text, nullable=True)
    IdempotencyKey: Mapped[Optional[str]] = mapped_column("IdempotencyKey", String(100), nullable=True)
    isdeleted: Mapped[str] = mapped_column("isdeleted", String(10), nullable=False, default="0")

    CreateDate: Mapped[datetime] = mapped_column("CreateDate", DateTime, nullable=False)
    CreateUser: Mapped[Optional[int]] = mapped_column("CreateUser", Integer, nullable=True)
    UpdateDate: Mapped[Optional[datetime]] = mapped_column("UpdateDate", DateTime, nullable=True)
    UpdateUser: Mapped[Optional[int]] = mapped_column("UpdateUser", Integer, nullable=True)


class ClaimDocument(Base):
    """
    Claim Supporting Document Reference Model
    Physical Table: tbl_claimdocument
    Physical PK: ClaimDocId
    """
    __tablename__ = "tbl_claimdocument"
    __table_args__ = (
        Index("ix_tbl_claimdocument_ClaimId", "ClaimId"),
        {
            "mysql_charset": "utf8",
            "mysql_collate": "utf8_general_ci",
            "mysql_row_format": "DYNAMIC",
        },
    )

    ClaimDocId: Mapped[int] = mapped_column("ClaimDocId", Integer, primary_key=True, autoincrement=True)
    ClaimId: Mapped[int] = mapped_column("ClaimId", Integer, nullable=False)
    TransanctionId: Mapped[int] = mapped_column("TransanctionId", Integer, nullable=False)
    DocumentType: Mapped[str] = mapped_column("DocumentType", String(50), nullable=False)
    DocumentName: Mapped[str] = mapped_column("DocumentName", String(255), nullable=False)
    StorageKey: Mapped[str] = mapped_column("StorageKey", String(500), nullable=False)
    VerifiedStatus: Mapped[str] = mapped_column("VerifiedStatus", String(30), nullable=False, default="PENDING")
    Remarks: Mapped[Optional[str]] = mapped_column("Remarks", String(500), nullable=True)
    isdeleted: Mapped[str] = mapped_column("isdeleted", String(10), nullable=False, default="0")
    CreateDate: Mapped[datetime] = mapped_column("CreateDate", DateTime, nullable=False)
    CreateUser: Mapped[Optional[int]] = mapped_column("CreateUser", Integer, nullable=True)


class PolicyEndorsement(Base):
    """
    Policy Endorsement, Modification, Premium Delta, Commission Delta & Refund Model
    Physical Table: tbl_appendorsement
    Physical PK: EndorsementId
    """
    __tablename__ = "tbl_appendorsement"
    __table_args__ = (
        Index("ix_tbl_appendorsement_TransanctionId", "TransanctionId"),
        Index("ix_tbl_appendorsement_EndorsementNo", "EndorsementNo", unique=True),
        Index("ix_tbl_appendorsement_IdempotencyKey", "IdempotencyKey"),
        {
            "mysql_charset": "utf8",
            "mysql_collate": "utf8_general_ci",
            "mysql_row_format": "DYNAMIC",
        },
    )

    EndorsementId: Mapped[int] = mapped_column("EndorsementId", Integer, primary_key=True, autoincrement=True)
    EndorsementNo: Mapped[str] = mapped_column("EndorsementNo", String(50), nullable=False)
    TransanctionId: Mapped[int] = mapped_column("TransanctionId", Integer, nullable=False)
    PolicyNo: Mapped[Optional[str]] = mapped_column("PolicyNo", String(100), nullable=True)
    CustomerId: Mapped[Optional[int]] = mapped_column("CustomerId", Integer, nullable=True)
    CustVehId: Mapped[Optional[int]] = mapped_column("CustVehId", Integer, nullable=True)
    BranchId: Mapped[Optional[int]] = mapped_column("BranchId", Integer, nullable=True)
    AgentId: Mapped[Optional[int]] = mapped_column("AgentId", Integer, nullable=True)
    FranchiseId: Mapped[Optional[int]] = mapped_column("FranchiseId", Integer, nullable=True)
    SalesExId: Mapped[Optional[int]] = mapped_column("SalesExId", Integer, nullable=True)

    EndorsementType: Mapped[str] = mapped_column("EndorsementType", String(50), nullable=False)
    EndorsementCategory: Mapped[str] = mapped_column("EndorsementCategory", String(30), nullable=False, default="NON_FINANCIAL")
    EndorsementStatus: Mapped[str] = mapped_column("EndorsementStatus", String(30), nullable=False, default="SUBMITTED")

    EffectiveDate: Mapped[datetime] = mapped_column("EffectiveDate", DateTime, nullable=False)
    RequestDate: Mapped[datetime] = mapped_column("RequestDate", DateTime, nullable=False)
    FieldChangesJson: Mapped[str] = mapped_column("FieldChangesJson", Text, nullable=False)

    OldODPremium: Mapped[Decimal] = mapped_column("OldODPremium", Double(asdecimal=True), nullable=False, default=Decimal("0.00"))
    NewODPremium: Mapped[Decimal] = mapped_column("NewODPremium", Double(asdecimal=True), nullable=False, default=Decimal("0.00"))
    OldTPPremium: Mapped[Decimal] = mapped_column("OldTPPremium", Double(asdecimal=True), nullable=False, default=Decimal("0.00"))
    NewTPPremium: Mapped[Decimal] = mapped_column("NewTPPremium", Double(asdecimal=True), nullable=False, default=Decimal("0.00"))
    OldNetPremium: Mapped[Decimal] = mapped_column("OldNetPremium", Double(asdecimal=True), nullable=False, default=Decimal("0.00"))
    NewNetPremium: Mapped[Decimal] = mapped_column("NewNetPremium", Double(asdecimal=True), nullable=False, default=Decimal("0.00"))
    OldGSTAmount: Mapped[Decimal] = mapped_column("OldGSTAmount", Double(asdecimal=True), nullable=False, default=Decimal("0.00"))
    NewGSTAmount: Mapped[Decimal] = mapped_column("NewGSTAmount", Double(asdecimal=True), nullable=False, default=Decimal("0.00"))
    OldFinalPremium: Mapped[Decimal] = mapped_column("OldFinalPremium", Double(asdecimal=True), nullable=False, default=Decimal("0.00"))
    NewFinalPremium: Mapped[Decimal] = mapped_column("NewFinalPremium", Double(asdecimal=True), nullable=False, default=Decimal("0.00"))
    PremiumDelta: Mapped[Decimal] = mapped_column("PremiumDelta", Double(asdecimal=True), nullable=False, default=Decimal("0.00"))

    OldNCBPercent: Mapped[Decimal] = mapped_column("OldNCBPercent", Double(asdecimal=True), nullable=False, default=Decimal("0.00"))
    NewNCBPercent: Mapped[Decimal] = mapped_column("NewNCBPercent", Double(asdecimal=True), nullable=False, default=Decimal("0.00"))
    OldIDV: Mapped[Decimal] = mapped_column("OldIDV", Double(asdecimal=True), nullable=False, default=Decimal("0.00"))
    NewIDV: Mapped[Decimal] = mapped_column("NewIDV", Double(asdecimal=True), nullable=False, default=Decimal("0.00"))

    OldAgentNetComm: Mapped[Decimal] = mapped_column("OldAgentNetComm", Double(asdecimal=True), nullable=False, default=Decimal("0.00"))
    NewAgentNetComm: Mapped[Decimal] = mapped_column("NewAgentNetComm", Double(asdecimal=True), nullable=False, default=Decimal("0.00"))
    AgentCommDelta: Mapped[Decimal] = mapped_column("AgentCommDelta", Double(asdecimal=True), nullable=False, default=Decimal("0.00"))
    OldAgentTdsAmt: Mapped[Decimal] = mapped_column("OldAgentTdsAmt", Double(asdecimal=True), nullable=False, default=Decimal("0.00"))
    NewAgentTdsAmt: Mapped[Decimal] = mapped_column("NewAgentTdsAmt", Double(asdecimal=True), nullable=False, default=Decimal("0.00"))

    OldFranchiseNetComm: Mapped[Decimal] = mapped_column("OldFranchiseNetComm", Double(asdecimal=True), nullable=False, default=Decimal("0.00"))
    NewFranchiseNetComm: Mapped[Decimal] = mapped_column("NewFranchiseNetComm", Double(asdecimal=True), nullable=False, default=Decimal("0.00"))
    FranchiseCommDelta: Mapped[Decimal] = mapped_column("FranchiseCommDelta", Double(asdecimal=True), nullable=False, default=Decimal("0.00"))
    CommissionRecoveryAmount: Mapped[Decimal] = mapped_column("CommissionRecoveryAmount", Double(asdecimal=True), nullable=False, default=Decimal("0.00"))

    RefundStatus: Mapped[str] = mapped_column("RefundStatus", String(30), nullable=False, default="NONE")
    RefundAmount: Mapped[Decimal] = mapped_column("RefundAmount", Double(asdecimal=True), nullable=False, default=Decimal("0.00"))
    RefundMode: Mapped[Optional[str]] = mapped_column("RefundMode", String(30), nullable=True)
    RefundDocNo: Mapped[Optional[str]] = mapped_column("RefundDocNo", String(100), nullable=True)

    SupportingDocKey: Mapped[Optional[str]] = mapped_column("SupportingDocKey", String(500), nullable=True)
    Remarks: Mapped[Optional[str]] = mapped_column("Remarks", Text, nullable=True)
    RejectionReason: Mapped[Optional[str]] = mapped_column("RejectionReason", String(500), nullable=True)
    IdempotencyKey: Mapped[Optional[str]] = mapped_column("IdempotencyKey", String(100), nullable=True)
    isdeleted: Mapped[str] = mapped_column("isdeleted", String(10), nullable=False, default="0")

    CreateDate: Mapped[datetime] = mapped_column("CreateDate", DateTime, nullable=False)
    CreateUser: Mapped[Optional[int]] = mapped_column("CreateUser", Integer, nullable=True)
    UpdateDate: Mapped[Optional[datetime]] = mapped_column("UpdateDate", DateTime, nullable=True)
    UpdateUser: Mapped[Optional[int]] = mapped_column("UpdateUser", Integer, nullable=True)
