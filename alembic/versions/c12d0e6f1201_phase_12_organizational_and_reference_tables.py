"""phase_12_organizational_and_reference_tables

Revision ID: c12d0e6f1201
Revises: b11d0c5f1101
Create Date: 2026-10-07 13:00:00.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c12d0e6f1201'
down_revision: Union[str, None] = 'b11d0c5f1101'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'tbl_branch',
        sa.Column('BranchId', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('BranchCode', sa.String(length=50), nullable=True),
        sa.Column('BranchName', sa.String(length=255), nullable=True),
        sa.Column('Address', sa.String(length=500), nullable=True),
        sa.Column('ContactNo', sa.String(length=50), nullable=True),
        sa.Column('BranchTypeId', sa.Integer(), server_default=sa.text('1'), nullable=True),
        sa.Column('isdeleted', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.PrimaryKeyConstraint('BranchId'),
        mysql_charset='utf8',
        mysql_collate='utf8_general_ci',
        mysql_row_format='DYNAMIC'
    )
    op.create_index('tbl_branch_code_idx', 'tbl_branch', ['BranchCode'], unique=False)

    op.create_table(
        'tbl_state',
        sa.Column('StateID', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('StateName', sa.String(length=255), nullable=False),
        sa.Column('isdeleted', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.PrimaryKeyConstraint('StateID'),
        mysql_charset='utf8',
        mysql_collate='utf8_general_ci',
        mysql_row_format='DYNAMIC'
    )

    op.create_table(
        'tbl_district',
        sa.Column('DistrictID', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('DistrictName', sa.String(length=255), nullable=False),
        sa.Column('StateID', sa.Integer(), nullable=False),
        sa.Column('isdeleted', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.PrimaryKeyConstraint('DistrictID'),
        mysql_charset='utf8',
        mysql_collate='utf8_general_ci',
        mysql_row_format='DYNAMIC'
    )
    op.create_index('tbl_district_state_id_idx', 'tbl_district', ['StateID'], unique=False)

    op.create_table(
        'tbl_bank',
        sa.Column('BankId', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('BankName', sa.String(length=255), nullable=False),
        sa.Column('isdeleted', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.PrimaryKeyConstraint('BankId'),
        mysql_charset='utf8',
        mysql_collate='utf8_general_ci',
        mysql_row_format='DYNAMIC'
    )


def downgrade() -> None:
    op.drop_table('tbl_bank')
    op.drop_index('tbl_district_state_id_idx', table_name='tbl_district')
    op.drop_table('tbl_district')
    op.drop_table('tbl_state')
    op.drop_index('tbl_branch_code_idx', table_name='tbl_branch')
    op.drop_table('tbl_branch')
