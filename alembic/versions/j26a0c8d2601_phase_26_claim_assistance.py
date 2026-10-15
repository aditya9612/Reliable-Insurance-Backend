"""phase_26_claim_assistance

Revision ID: j26a0c8d2601
Revises: i25a0c7d2501
Create Date: 2026-10-15 13:45:00.000000+00:00

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "j26a0c8d2601"
down_revision: Union[str, None] = "i25a0c7d2501"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. tbl_claimassistance (Emergency Accident Intimation & Assistance Requests)
    op.create_table(
        "tbl_claimassistance",
        sa.Column("ClaimAssistanceId", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("CustomerId", sa.Integer(), nullable=True),
        sa.Column("InsuranceCompanyId", sa.Integer(), nullable=False),
        sa.Column("IntimationDate", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("VehNo", sa.String(length=50), nullable=False),
        sa.Column("DateofAccident", sa.DateTime(), nullable=False),
        sa.Column("Accidenttime", sa.String(length=50), nullable=True),
        sa.Column("spot", sa.String(length=255), nullable=True),
        sa.Column("Reason", sa.Text(), nullable=True),
        sa.Column("DriverName", sa.String(length=150), nullable=True),
        sa.Column("DriverLicenseNo", sa.String(length=100), nullable=True),
        sa.Column("GarageName", sa.String(length=200), nullable=True),
        sa.Column("GarageAddr", sa.String(length=500), nullable=True),
        sa.Column("Garagecontact", sa.String(length=50), nullable=True),
        sa.Column("ClaimNo", sa.String(length=100), nullable=True),
        sa.Column("ClaimNoUpdateDate", sa.DateTime(), nullable=True),
        sa.Column("ClaimNoUpdateUser", sa.String(length=100), nullable=True),
        sa.Column("Status", sa.String(length=50), nullable=False, server_default=sa.text("'INTIMATED'")),
        sa.Column("ReadStatus", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("isdeleted", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("BranchId", sa.Integer(), nullable=True, server_default=sa.text("101")),
        sa.Column("AgentId", sa.Integer(), nullable=True, server_default=sa.text("0")),
        sa.Column("SalesExId", sa.Integer(), nullable=True, server_default=sa.text("0")),
        sa.Column("CreatedDate", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("CreatedUser", sa.String(length=100), nullable=True),
        sa.Column("UpdatedDate", sa.DateTime(), nullable=True, server_default=sa.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP")),
        sa.Column("UpdatedUser", sa.String(length=100), nullable=True),
        sa.PrimaryKeyConstraint("ClaimAssistanceId"),
        mysql_charset="utf8",
        mysql_collate="utf8_general_ci",
        mysql_row_format="DYNAMIC",
    )
    op.create_index("ix_tbl_claimassistance_veh_no", "tbl_claimassistance", ["VehNo"])
    op.create_index("ix_tbl_claimassistance_claim_no", "tbl_claimassistance", ["ClaimNo"])
    op.create_index("ix_tbl_claimassistance_company_id", "tbl_claimassistance", ["InsuranceCompanyId"])
    op.create_index("ix_tbl_claimassistance_intimation_date", "tbl_claimassistance", ["IntimationDate"])
    op.create_index("ix_tbl_claimassistance_status", "tbl_claimassistance", ["Status"])
    op.create_index("ix_tbl_claimassistance_read_status", "tbl_claimassistance", ["ReadStatus"])
    op.create_index("ix_tbl_claimassistance_isdeleted", "tbl_claimassistance", ["isdeleted"])
    op.create_index("ix_tbl_claimassistance_CustomerId", "tbl_claimassistance", ["CustomerId"])
    op.create_index("ix_tbl_claimassistance_BranchId", "tbl_claimassistance", ["BranchId"])
    op.create_index("ix_tbl_claimassistance_AgentId", "tbl_claimassistance", ["AgentId"])

    # 2. tbl_claimassistanceimg (Accident Damage Photos)
    op.create_table(
        "tbl_claimassistanceimg",
        sa.Column("ClaimAssistanceImgId", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("ClaimAssistanceId", sa.Integer(), nullable=False),
        sa.Column("ImgPath", sa.String(length=500), nullable=False),
        sa.Column("CreatedDate", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(
            ["ClaimAssistanceId"],
            ["tbl_claimassistance.ClaimAssistanceId"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("ClaimAssistanceImgId"),
        mysql_charset="utf8",
        mysql_collate="utf8_general_ci",
        mysql_row_format="DYNAMIC",
    )
    op.create_index("ix_tbl_claimassistanceimg_assistance_id", "tbl_claimassistanceimg", ["ClaimAssistanceId"])


def downgrade() -> None:
    op.drop_table("tbl_claimassistanceimg")
    op.drop_table("tbl_claimassistance")
