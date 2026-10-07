"""Phase 11 Additive Document Metadata and Policy Parser Webhook Tables

Revision ID: b11d0c5f1101
Revises: a10c1a1m5001
Create Date: 2026-10-07 11:25:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b11d0c5f1101"
down_revision: Union[str, None] = "a10c1a1m5001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tbl_documents",
        sa.Column("DocumentId", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("DocumentUUID", sa.String(length=64), nullable=False),
        sa.Column("DocumentType", sa.String(length=50), nullable=False),
        sa.Column("DocSubType", sa.String(length=100), nullable=True),
        sa.Column("EntityType", sa.String(length=50), nullable=False),
        sa.Column("EntityId", sa.Integer(), nullable=True),
        sa.Column("TransanctionId", sa.Integer(), nullable=True),
        sa.Column("PolicyNo", sa.String(length=100), nullable=True),
        sa.Column("QuotationId", sa.Integer(), nullable=True),
        sa.Column("ClaimId", sa.Integer(), nullable=True),
        sa.Column("EndorsementId", sa.Integer(), nullable=True),
        sa.Column("CustomerId", sa.Integer(), nullable=True),
        sa.Column("CustVehId", sa.Integer(), nullable=True),
        sa.Column("PaymentId", sa.Integer(), nullable=True),
        sa.Column("BranchId", sa.Integer(), nullable=True),
        sa.Column("AgentId", sa.Integer(), nullable=True),
        sa.Column("FranchiseId", sa.Integer(), nullable=True),
        sa.Column("SalesExId", sa.Integer(), nullable=True),
        sa.Column("LegacyVirtualFolder", sa.String(length=100), nullable=False),
        sa.Column("OriginalFileName", sa.String(length=255), nullable=False),
        sa.Column("StoredFileName", sa.String(length=255), nullable=False),
        sa.Column("StorageKey", sa.String(length=500), nullable=False),
        sa.Column("MimeType", sa.String(length=120), nullable=False),
        sa.Column("FileExtension", sa.String(length=30), nullable=False),
        sa.Column("FileSizeBytes", sa.Integer(), nullable=False),
        sa.Column("ChecksumSha256", sa.String(length=64), nullable=False),
        sa.Column("VersionNo", sa.Integer(), nullable=False),
        sa.Column("ReplacesDocumentId", sa.Integer(), nullable=True),
        sa.Column("ReplacedByDocumentId", sa.Integer(), nullable=True),
        sa.Column("LegacyRefTable", sa.String(length=100), nullable=True),
        sa.Column("LegacyRefId", sa.Integer(), nullable=True),
        sa.Column("VerifiedStatus", sa.String(length=30), nullable=False),
        sa.Column("Remarks", sa.String(length=500), nullable=True),
        sa.Column("IdempotencyKey", sa.String(length=100), nullable=True),
        sa.Column("isdeleted", sa.String(length=10), nullable=False),
        sa.Column("CreateDate", sa.DateTime(), nullable=False),
        sa.Column("CreateUser", sa.Integer(), nullable=True),
        sa.Column("UpdateDate", sa.DateTime(), nullable=True),
        sa.Column("UpdateUser", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("DocumentId"),
        mysql_charset="utf8",
        mysql_collate="utf8_general_ci",
        mysql_row_format="DYNAMIC",
    )
    op.create_index("ix_tbl_documents_DocumentUUID", "tbl_documents", ["DocumentUUID"], unique=True)
    op.create_index("ix_tbl_documents_StorageKey", "tbl_documents", ["StorageKey"], unique=True)
    op.create_index("ix_tbl_documents_EntityType_EntityId", "tbl_documents", ["EntityType", "EntityId"], unique=False)
    op.create_index("ix_tbl_documents_TransanctionId", "tbl_documents", ["TransanctionId"], unique=False)
    op.create_index("ix_tbl_documents_PolicyNo", "tbl_documents", ["PolicyNo"], unique=False)
    op.create_index("ix_tbl_documents_QuotationId", "tbl_documents", ["QuotationId"], unique=False)
    op.create_index("ix_tbl_documents_ClaimId", "tbl_documents", ["ClaimId"], unique=False)
    op.create_index("ix_tbl_documents_EndorsementId", "tbl_documents", ["EndorsementId"], unique=False)
    op.create_index("ix_tbl_documents_CustomerId", "tbl_documents", ["CustomerId"], unique=False)
    op.create_index("ix_tbl_documents_CustVehId", "tbl_documents", ["CustVehId"], unique=False)
    op.create_index("ix_tbl_documents_IdempotencyKey", "tbl_documents", ["IdempotencyKey"], unique=False)

    op.create_table(
        "tbl_calliber_policy_webhook",
        sa.Column("CalliberPolicyId", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("WebhookEventId", sa.String(length=100), nullable=True),
        sa.Column("IdempotencyKey", sa.String(length=100), nullable=True),
        sa.Column("PayloadSha256", sa.String(length=64), nullable=False),
        sa.Column("PolicyNo", sa.String(length=100), nullable=True),
        sa.Column("CustomerName", sa.String(length=255), nullable=True),
        sa.Column("VehicleRegNo", sa.String(length=100), nullable=True),
        sa.Column("EngineNo", sa.String(length=100), nullable=True),
        sa.Column("ChassisNo", sa.String(length=100), nullable=True),
        sa.Column("InsCompany", sa.String(length=255), nullable=True),
        sa.Column("ProductType", sa.String(length=100), nullable=True),
        sa.Column("PolicyType", sa.String(length=100), nullable=True),
        sa.Column("StartDate", sa.String(length=50), nullable=True),
        sa.Column("EndDate", sa.String(length=50), nullable=True),
        sa.Column("IDV", sa.Double(asdecimal=True), nullable=False),
        sa.Column("ODPremium", sa.Double(asdecimal=True), nullable=False),
        sa.Column("TPPremium", sa.Double(asdecimal=True), nullable=False),
        sa.Column("NetPremium", sa.Double(asdecimal=True), nullable=False),
        sa.Column("GSTAmount", sa.Double(asdecimal=True), nullable=False),
        sa.Column("GrossPremium", sa.Double(asdecimal=True), nullable=False),
        sa.Column("NCBPercent", sa.Double(asdecimal=True), nullable=False),
        sa.Column("DocumentId", sa.Integer(), nullable=True),
        sa.Column("LinkedTransanctionId", sa.Integer(), nullable=True),
        sa.Column("RawPayloadJson", sa.Text(), nullable=False),
        sa.Column("ProcessingStatus", sa.String(length=30), nullable=False),
        sa.Column("UpdatedBy", sa.String(length=200), nullable=True),
        sa.Column("isdeleted", sa.String(length=10), nullable=False),
        sa.Column("CreateDate", sa.DateTime(), nullable=False),
        sa.Column("UpdateDate", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("CalliberPolicyId"),
        mysql_charset="utf8",
        mysql_collate="utf8_general_ci",
        mysql_row_format="DYNAMIC",
    )
    op.create_index("ix_tbl_calliber_webhook_PolicyNo", "tbl_calliber_policy_webhook", ["PolicyNo"], unique=False)
    op.create_index("ix_tbl_calliber_webhook_IdempotencyKey", "tbl_calliber_policy_webhook", ["IdempotencyKey"], unique=False)
    op.create_index("ix_tbl_calliber_webhook_PayloadSha256", "tbl_calliber_policy_webhook", ["PayloadSha256"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_tbl_calliber_webhook_PayloadSha256", table_name="tbl_calliber_policy_webhook")
    op.drop_index("ix_tbl_calliber_webhook_IdempotencyKey", table_name="tbl_calliber_policy_webhook")
    op.drop_index("ix_tbl_calliber_webhook_PolicyNo", table_name="tbl_calliber_policy_webhook")
    op.drop_table("tbl_calliber_policy_webhook")

    op.drop_index("ix_tbl_documents_IdempotencyKey", table_name="tbl_documents")
    op.drop_index("ix_tbl_documents_CustVehId", table_name="tbl_documents")
    op.drop_index("ix_tbl_documents_CustomerId", table_name="tbl_documents")
    op.drop_index("ix_tbl_documents_EndorsementId", table_name="tbl_documents")
    op.drop_index("ix_tbl_documents_ClaimId", table_name="tbl_documents")
    op.drop_index("ix_tbl_documents_QuotationId", table_name="tbl_documents")
    op.drop_index("ix_tbl_documents_PolicyNo", table_name="tbl_documents")
    op.drop_index("ix_tbl_documents_TransanctionId", table_name="tbl_documents")
    op.drop_index("ix_tbl_documents_EntityType_EntityId", table_name="tbl_documents")
    op.drop_index("ix_tbl_documents_StorageKey", table_name="tbl_documents")
    op.drop_index("ix_tbl_documents_DocumentUUID", table_name="tbl_documents")
    op.drop_table("tbl_documents")
