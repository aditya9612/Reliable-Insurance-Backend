"""phase_20_batch_1_operational_extensions

Revision ID: c20a0b1c2001
Revises: b18a0c5d1801
Create Date: 2026-10-12 10:55:00.000000+00:00

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c20a0b1c2001"
down_revision: Union[str, None] = "b18a0c5d1801"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. tbl_circular (F-20-001)
    op.create_table(
        "tbl_circular",
        sa.Column("circularid", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("circulardate", sa.Date(), nullable=False),
        sa.Column("subject", sa.String(length=500), nullable=False),
        sa.Column("pdfpath", sa.String(length=1000), nullable=True),
        sa.Column("is_active", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("circularid"),
        mysql_charset="utf8",
        mysql_collate="utf8_general_ci",
        mysql_row_format="DYNAMIC",
    )
    op.create_index("ix_tbl_circular_circulardate", "tbl_circular", ["circulardate"])
    op.create_index("ix_tbl_circular_is_active", "tbl_circular", ["is_active"])

    # 2. tbl_customerhelp (F-20-002)
    op.create_table(
        "tbl_customerhelp",
        sa.Column("CustHelpId", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("CustomerId", sa.Integer(), nullable=False),
        sa.Column("HelpId", sa.Integer(), nullable=True),
        sa.Column("Subject", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("Message", sa.Text(), nullable=True),
        sa.Column("RegistrationNo", sa.String(length=100), nullable=True),
        sa.Column("PolicyNo", sa.String(length=100), nullable=True),
        sa.Column("Status", sa.String(length=50), nullable=False, server_default="OPEN"),
        sa.Column("CustDate", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("ResolvedBy", sa.Integer(), nullable=True),
        sa.Column("ResolvedDate", sa.DateTime(), nullable=True),
        sa.Column("ResolutionRemark", sa.String(length=1000), nullable=True),
        sa.Column("is_deleted", sa.Integer(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("CustHelpId"),
        mysql_charset="utf8",
        mysql_collate="utf8_general_ci",
        mysql_row_format="DYNAMIC",
    )
    op.create_index("ix_tbl_customerhelp_CustomerId", "tbl_customerhelp", ["CustomerId"])
    op.create_index("ix_tbl_customerhelp_Status", "tbl_customerhelp", ["Status"])
    op.create_index("ix_tbl_customerhelp_CustDate", "tbl_customerhelp", ["CustDate"])

    # 3. tbl_chatboard (F-20-002)
    op.create_table(
        "tbl_chatboard",
        sa.Column("ChatId", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("CustHelpId", sa.Integer(), nullable=True),
        sa.Column("UserRoleId", sa.Integer(), nullable=True),
        sa.Column("ReferenceAgentId", sa.Integer(), nullable=True),
        sa.Column("CoordinatorId", sa.Integer(), nullable=True),
        sa.Column("RegistrationNo", sa.String(length=100), nullable=True),
        sa.Column("ChatText", sa.Text(), nullable=False),
        sa.Column("ChatByUser", sa.String(length=100), nullable=False),
        sa.Column("SenderUserId", sa.Integer(), nullable=True),
        sa.Column("Reply", sa.Text(), nullable=True),
        sa.Column("Remark", sa.String(length=500), nullable=True),
        sa.Column("AttachmentPath", sa.String(length=1000), nullable=True),
        sa.Column("IsRead", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("CreatedDate", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("ChatId"),
        mysql_charset="utf8",
        mysql_collate="utf8_general_ci",
        mysql_row_format="DYNAMIC",
    )
    op.create_index("ix_tbl_chatboard_CustHelpId", "tbl_chatboard", ["CustHelpId"])
    op.create_index("ix_tbl_chatboard_ReferenceAgentId", "tbl_chatboard", ["ReferenceAgentId"])
    op.create_index("ix_tbl_chatboard_CreatedDate", "tbl_chatboard", ["CreatedDate"])

    # 4. tbl_webnotification (F-20-003)
    op.create_table(
        "tbl_webnotification",
        sa.Column("NotId", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("NotMessage", sa.String(length=1000), nullable=False),
        sa.Column("TargetRole", sa.String(length=50), nullable=True, server_default="ALL"),
        sa.Column("BranchId", sa.Integer(), nullable=True),
        sa.Column("Severity", sa.String(length=20), nullable=False, server_default="INFO"),
        sa.Column("IsActive", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("CreatedBy", sa.Integer(), nullable=True),
        sa.Column("CreatedDate", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("ExpiryDate", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("NotId"),
        mysql_charset="utf8",
        mysql_collate="utf8_general_ci",
        mysql_row_format="DYNAMIC",
    )
    op.create_index("ix_tbl_webnotification_TargetRole", "tbl_webnotification", ["TargetRole"])
    op.create_index("ix_tbl_webnotification_IsActive", "tbl_webnotification", ["IsActive"])
    op.create_index("ix_tbl_webnotification_CreatedDate", "tbl_webnotification", ["CreatedDate"])

    # 5. tbl_rewardpoint (F-20-004)
    op.create_table(
        "tbl_rewardpoint",
        sa.Column("RewardPointId", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("PartnerType", sa.String(length=50), nullable=False, server_default="AGENT"),
        sa.Column("PartnerId", sa.Integer(), nullable=False),
        sa.Column("RefCustId", sa.Integer(), nullable=True),
        sa.Column("PolicyId", sa.Integer(), nullable=True),
        sa.Column("RewardDate", sa.Date(), nullable=False),
        sa.Column("RewardPointGet", sa.Numeric(precision=12, scale=2), nullable=False, server_default="0.00"),
        sa.Column("RewardPointUtilizes", sa.Numeric(precision=12, scale=2), nullable=False, server_default="0.00"),
        sa.Column("PointBalance", sa.Numeric(precision=12, scale=2), nullable=False, server_default="0.00"),
        sa.Column("Remarks", sa.String(length=500), nullable=True),
        sa.Column("CreatedDate", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("RewardPointId"),
        mysql_charset="utf8",
        mysql_collate="utf8_general_ci",
        mysql_row_format="DYNAMIC",
    )
    op.create_index("ix_tbl_rewardpoint_Partner", "tbl_rewardpoint", ["PartnerType", "PartnerId"])
    op.create_index("ix_tbl_rewardpoint_RewardDate", "tbl_rewardpoint", ["RewardDate"])


def downgrade() -> None:
    op.drop_table("tbl_rewardpoint")
    op.drop_table("tbl_webnotification")
    op.drop_table("tbl_chatboard")
    op.drop_table("tbl_customerhelp")
    op.drop_table("tbl_circular")
