"""Phase 10 Claims, Claim Documents, and Policy Endorsements tables

Revision ID: a10c1a1m5001
Revises: 7bfd3202dcf7
Create Date: 2026-10-06 22:12:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a10c1a1m5001"
down_revision: Union[str, None] = "7bfd3202dcf7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tbl_claims",
        sa.Column("ClaimId", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("ClaimNo", sa.String(length=50), nullable=False),
        sa.Column("TransanctionId", sa.Integer(), nullable=False),
        sa.Column("PolicyNo", sa.String(length=100), nullable=True),
        sa.Column("CustomerId", sa.Integer(), nullable=True),
        sa.Column("CustVehId", sa.Integer(), nullable=True),
        sa.Column("InsuranceCompanyId", sa.Integer(), nullable=True),
        sa.Column("BranchId", sa.Integer(), nullable=True),
        sa.Column("AgentId", sa.Integer(), nullable=True),
        sa.Column("FranchiseId", sa.Integer(), nullable=True),
        sa.Column("SalesExId", sa.Integer(), nullable=True),
        sa.Column("ClaimType", sa.String(length=30), nullable=False),
        sa.Column("ClaimStatus", sa.String(length=30), nullable=False),
        sa.Column("IntimationDate", sa.DateTime(), nullable=False),
        sa.Column("LossDate", sa.DateTime(), nullable=False),
        sa.Column("LossLocation", sa.String(length=255), nullable=True),
        sa.Column("LossDescription", sa.Text(), nullable=True),
        sa.Column("EstimatedAmount", sa.Double(asdecimal=True), nullable=False),
        sa.Column("SurveyorName", sa.String(length=150), nullable=True),
        sa.Column("SurveyorMobile", sa.String(length=20), nullable=True),
        sa.Column("SurveyorLicenseNo", sa.String(length=50), nullable=True),
        sa.Column("SurveyDate", sa.DateTime(), nullable=True),
        sa.Column("AssessedLossAmount", sa.Double(asdecimal=True), nullable=False),
        sa.Column("DepreciationAmount", sa.Double(asdecimal=True), nullable=False),
        sa.Column("DeductibleAmount", sa.Double(asdecimal=True), nullable=False),
        sa.Column("ExcessAmount", sa.Double(asdecimal=True), nullable=False),
        sa.Column("SalvageAmount", sa.Double(asdecimal=True), nullable=False),
        sa.Column("ApprovedAmount", sa.Double(asdecimal=True), nullable=False),
        sa.Column("SettledAmount", sa.Double(asdecimal=True), nullable=False),
        sa.Column("InsurerPayableAmount", sa.Double(asdecimal=True), nullable=False),
        sa.Column("CustomerPayableAmount", sa.Double(asdecimal=True), nullable=False),
        sa.Column("GaragePayableAmount", sa.Double(asdecimal=True), nullable=False),
        sa.Column("PayeeType", sa.String(length=30), nullable=True),
        sa.Column("PaymentMode", sa.String(length=30), nullable=True),
        sa.Column("PaymentDocNo", sa.String(length=100), nullable=True),
        sa.Column("SettlementDate", sa.DateTime(), nullable=True),
        sa.Column("InsurerClaimRef", sa.String(length=100), nullable=True),
        sa.Column("RejectionReason", sa.String(length=500), nullable=True),
        sa.Column("Remarks", sa.Text(), nullable=True),
        sa.Column("IdempotencyKey", sa.String(length=100), nullable=True),
        sa.Column("isdeleted", sa.String(length=10), nullable=False),
        sa.Column("CreateDate", sa.DateTime(), nullable=False),
        sa.Column("CreateUser", sa.Integer(), nullable=True),
        sa.Column("UpdateDate", sa.DateTime(), nullable=True),
        sa.Column("UpdateUser", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("ClaimId"),
        mysql_charset="utf8",
        mysql_collate="utf8_general_ci",
        mysql_row_format="DYNAMIC",
    )
    op.create_index("ix_tbl_claims_ClaimNo", "tbl_claims", ["ClaimNo"], unique=True)
    op.create_index("ix_tbl_claims_IdempotencyKey", "tbl_claims", ["IdempotencyKey"], unique=False)
    op.create_index("ix_tbl_claims_TransanctionId", "tbl_claims", ["TransanctionId"], unique=False)

    op.create_table(
        "tbl_claimdocument",
        sa.Column("ClaimDocId", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("ClaimId", sa.Integer(), nullable=False),
        sa.Column("TransanctionId", sa.Integer(), nullable=False),
        sa.Column("DocumentType", sa.String(length=50), nullable=False),
        sa.Column("DocumentName", sa.String(length=255), nullable=False),
        sa.Column("StorageKey", sa.String(length=500), nullable=False),
        sa.Column("VerifiedStatus", sa.String(length=30), nullable=False),
        sa.Column("Remarks", sa.String(length=500), nullable=True),
        sa.Column("isdeleted", sa.String(length=10), nullable=False),
        sa.Column("CreateDate", sa.DateTime(), nullable=False),
        sa.Column("CreateUser", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("ClaimDocId"),
        mysql_charset="utf8",
        mysql_collate="utf8_general_ci",
        mysql_row_format="DYNAMIC",
    )
    op.create_index("ix_tbl_claimdocument_ClaimId", "tbl_claimdocument", ["ClaimId"], unique=False)

    op.create_table(
        "tbl_appendorsement",
        sa.Column("EndorsementId", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("EndorsementNo", sa.String(length=50), nullable=False),
        sa.Column("TransanctionId", sa.Integer(), nullable=False),
        sa.Column("PolicyNo", sa.String(length=100), nullable=True),
        sa.Column("CustomerId", sa.Integer(), nullable=True),
        sa.Column("CustVehId", sa.Integer(), nullable=True),
        sa.Column("BranchId", sa.Integer(), nullable=True),
        sa.Column("AgentId", sa.Integer(), nullable=True),
        sa.Column("FranchiseId", sa.Integer(), nullable=True),
        sa.Column("SalesExId", sa.Integer(), nullable=True),
        sa.Column("EndorsementType", sa.String(length=50), nullable=False),
        sa.Column("EndorsementCategory", sa.String(length=30), nullable=False),
        sa.Column("EndorsementStatus", sa.String(length=30), nullable=False),
        sa.Column("EffectiveDate", sa.DateTime(), nullable=False),
        sa.Column("RequestDate", sa.DateTime(), nullable=False),
        sa.Column("FieldChangesJson", sa.Text(), nullable=False),
        sa.Column("OldODPremium", sa.Double(asdecimal=True), nullable=False),
        sa.Column("NewODPremium", sa.Double(asdecimal=True), nullable=False),
        sa.Column("OldTPPremium", sa.Double(asdecimal=True), nullable=False),
        sa.Column("NewTPPremium", sa.Double(asdecimal=True), nullable=False),
        sa.Column("OldNetPremium", sa.Double(asdecimal=True), nullable=False),
        sa.Column("NewNetPremium", sa.Double(asdecimal=True), nullable=False),
        sa.Column("OldGSTAmount", sa.Double(asdecimal=True), nullable=False),
        sa.Column("NewGSTAmount", sa.Double(asdecimal=True), nullable=False),
        sa.Column("OldFinalPremium", sa.Double(asdecimal=True), nullable=False),
        sa.Column("NewFinalPremium", sa.Double(asdecimal=True), nullable=False),
        sa.Column("PremiumDelta", sa.Double(asdecimal=True), nullable=False),
        sa.Column("OldNCBPercent", sa.Double(asdecimal=True), nullable=False),
        sa.Column("NewNCBPercent", sa.Double(asdecimal=True), nullable=False),
        sa.Column("OldIDV", sa.Double(asdecimal=True), nullable=False),
        sa.Column("NewIDV", sa.Double(asdecimal=True), nullable=False),
        sa.Column("OldAgentNetComm", sa.Double(asdecimal=True), nullable=False),
        sa.Column("NewAgentNetComm", sa.Double(asdecimal=True), nullable=False),
        sa.Column("AgentCommDelta", sa.Double(asdecimal=True), nullable=False),
        sa.Column("OldAgentTdsAmt", sa.Double(asdecimal=True), nullable=False),
        sa.Column("NewAgentTdsAmt", sa.Double(asdecimal=True), nullable=False),
        sa.Column("OldFranchiseNetComm", sa.Double(asdecimal=True), nullable=False),
        sa.Column("NewFranchiseNetComm", sa.Double(asdecimal=True), nullable=False),
        sa.Column("FranchiseCommDelta", sa.Double(asdecimal=True), nullable=False),
        sa.Column("CommissionRecoveryAmount", sa.Double(asdecimal=True), nullable=False),
        sa.Column("RefundStatus", sa.String(length=30), nullable=False),
        sa.Column("RefundAmount", sa.Double(asdecimal=True), nullable=False),
        sa.Column("RefundMode", sa.String(length=30), nullable=True),
        sa.Column("RefundDocNo", sa.String(length=100), nullable=True),
        sa.Column("SupportingDocKey", sa.String(length=500), nullable=True),
        sa.Column("Remarks", sa.Text(), nullable=True),
        sa.Column("RejectionReason", sa.String(length=500), nullable=True),
        sa.Column("IdempotencyKey", sa.String(length=100), nullable=True),
        sa.Column("isdeleted", sa.String(length=10), nullable=False),
        sa.Column("CreateDate", sa.DateTime(), nullable=False),
        sa.Column("CreateUser", sa.Integer(), nullable=True),
        sa.Column("UpdateDate", sa.DateTime(), nullable=True),
        sa.Column("UpdateUser", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("EndorsementId"),
        mysql_charset="utf8",
        mysql_collate="utf8_general_ci",
        mysql_row_format="DYNAMIC",
    )
    op.create_index("ix_tbl_appendorsement_EndorsementNo", "tbl_appendorsement", ["EndorsementNo"], unique=True)
    op.create_index("ix_tbl_appendorsement_IdempotencyKey", "tbl_appendorsement", ["IdempotencyKey"], unique=False)
    op.create_index("ix_tbl_appendorsement_TransanctionId", "tbl_appendorsement", ["TransanctionId"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_tbl_appendorsement_TransanctionId", table_name="tbl_appendorsement")
    op.drop_index("ix_tbl_appendorsement_IdempotencyKey", table_name="tbl_appendorsement")
    op.drop_index("ix_tbl_appendorsement_EndorsementNo", table_name="tbl_appendorsement")
    op.drop_table("tbl_appendorsement")

    op.drop_index("ix_tbl_claimdocument_ClaimId", table_name="tbl_claimdocument")
    op.drop_table("tbl_claimdocument")

    op.drop_index("ix_tbl_claims_TransanctionId", table_name="tbl_claims")
    op.drop_index("ix_tbl_claims_IdempotencyKey", table_name="tbl_claims")
    op.drop_index("ix_tbl_claims_ClaimNo", table_name="tbl_claims")
    op.drop_table("tbl_claims")
