"""phase_29_temporary_operator

Revision ID: m29a0e1f2901
Revises: l28a0d0e2801
Create Date: 2026-10-15 16:00:00.000000+00:00

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "m29a0e1f2901"
down_revision: Union[str, None] = "l28a0d0e2801"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. tbl_tempararyoperator (Temporary Operator Assignment & Delegation)
    op.create_table(
        "tbl_tempararyoperator",
        sa.Column("ID", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("Per_OperatorId", sa.Integer(), nullable=False),
        sa.Column("Temp_OperatorId", sa.Integer(), nullable=False),
        sa.Column("ValidFrom", sa.DateTime(), nullable=True),
        sa.Column("ValidUpTo", sa.DateTime(), nullable=True),
        sa.Column("CreateUser", sa.String(length=100), nullable=True),
        sa.Column("CreateDate", sa.DateTime(), nullable=True, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("isdeleted", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("UpdatedUser", sa.String(length=100), nullable=True),
        sa.Column("UpdatedDate", sa.DateTime(), nullable=True, server_default=sa.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("ID"),
        mysql_charset="utf8",
        mysql_collate="utf8_general_ci",
        mysql_row_format="DYNAMIC",
    )
    op.create_index("ix_tbl_tempararyoperator_per_operator_id", "tbl_tempararyoperator", ["Per_OperatorId"])
    op.create_index("ix_tbl_tempararyoperator_temp_operator_id", "tbl_tempararyoperator", ["Temp_OperatorId"])
    op.create_index("ix_tbl_tempararyoperator_isdeleted", "tbl_tempararyoperator", ["isdeleted"])
    op.create_index(
        "ix_tbl_tempararyoperator_active_lookup",
        "tbl_tempararyoperator",
        ["Per_OperatorId", "Temp_OperatorId", "isdeleted", "ValidFrom", "ValidUpTo"],
    )


def downgrade() -> None:
    op.drop_table("tbl_tempararyoperator")
