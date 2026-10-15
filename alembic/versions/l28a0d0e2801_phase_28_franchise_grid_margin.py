"""phase_28_franchise_grid_margin

Revision ID: l28a0d0e2801
Revises: k27a0c9d2701
Create Date: 2026-10-15 15:30:00.000000+00:00

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "l28a0d0e2801"
down_revision: Union[str, None] = "k27a0c9d2701"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. tbl_franchisegridmargin (Franchise Agent Custom Commission Margin Overrides)
    op.create_table(
        "tbl_franchisegridmargin",
        sa.Column("Id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("FranchiseId", sa.Integer(), nullable=False),
        sa.Column("FranchiseAgentId", sa.Integer(), nullable=False),
        sa.Column("InsuranceCompanyId", sa.Integer(), nullable=False),
        sa.Column("PolicyTypeId", sa.Integer(), nullable=False),
        sa.Column("margin", sa.Double(asdecimal=True), nullable=False, server_default=sa.text("0.0")),
        sa.Column("isdeleted", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("CreatedUser", sa.String(length=100), nullable=True),
        sa.Column("CreatedDate", sa.DateTime(), nullable=True, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("UpdatedUser", sa.String(length=100), nullable=True),
        sa.Column("UpdatedDate", sa.DateTime(), nullable=True, server_default=sa.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("Id"),
        mysql_charset="utf8",
        mysql_collate="utf8_general_ci",
        mysql_row_format="DYNAMIC",
    )
    op.create_index("ix_tbl_franchisegridmargin_franchise_id", "tbl_franchisegridmargin", ["FranchiseId"])
    op.create_index("ix_tbl_franchisegridmargin_agent_id", "tbl_franchisegridmargin", ["FranchiseAgentId"])
    op.create_index("ix_tbl_franchisegridmargin_company_id", "tbl_franchisegridmargin", ["InsuranceCompanyId"])
    op.create_index("ix_tbl_franchisegridmargin_policy_type_id", "tbl_franchisegridmargin", ["PolicyTypeId"])
    op.create_index("ix_tbl_franchisegridmargin_isdeleted", "tbl_franchisegridmargin", ["isdeleted"])
    op.create_index(
        "ix_tbl_franchisegridmargin_lookup",
        "tbl_franchisegridmargin",
        ["FranchiseId", "FranchiseAgentId", "InsuranceCompanyId", "PolicyTypeId", "isdeleted"],
    )


def downgrade() -> None:
    op.drop_table("tbl_franchisegridmargin")
