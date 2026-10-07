"""phase_14_reporting_posp_invoice_target_tables

Revision ID: e14a0b2c1401
Revises: d13e0f7a1301
Create Date: 2026-10-07 21:30:00.000000+00:00

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e14a0b2c1401'
down_revision: Union[str, None] = 'd13e0f7a1301'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. tbl_posp_invoice (POSP Agent Payout Invoicing & PDF Tracking)
    op.create_table(
        'tbl_posp_invoice',
        sa.Column('InvoiceId', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('InvoiceNo', sa.String(length=100), nullable=False),
        sa.Column('InvoiceDate', sa.Date(), nullable=False),
        sa.Column('AgentId', sa.Integer(), nullable=False),
        sa.Column('AgentName', sa.String(length=255), nullable=False),
        sa.Column('POSPType', sa.String(length=50), nullable=False),
        sa.Column('FinancialYear', sa.String(length=20), nullable=False),
        sa.Column('Month', sa.String(length=20), nullable=False),
        sa.Column('Amount', sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column('GSTAmt', sa.Numeric(precision=18, scale=2), nullable=False, server_default='0.00'),
        sa.Column('GrandTotal', sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column('TDSAmount', sa.Numeric(precision=18, scale=2), nullable=False, server_default='0.00'),
        sa.Column('NetPayable', sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column('PdfPath', sa.String(length=500), nullable=True),
        sa.Column('Status', sa.String(length=50), nullable=False, server_default='GENERATED'),
        sa.Column('CreatedDate', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('CreatedBy', sa.String(length=100), nullable=False),
        sa.PrimaryKeyConstraint('InvoiceId'),
        sa.UniqueConstraint('InvoiceNo', name='uk_tbl_posp_invoice_InvoiceNo'),
        mysql_charset='utf8',
        mysql_collate='utf8_general_ci',
        mysql_row_format='DYNAMIC'
    )
    op.create_index('ix_tbl_posp_invoice_InvoiceNo', 'tbl_posp_invoice', ['InvoiceNo'])
    op.create_index('ix_tbl_posp_invoice_Agent_FY_Month', 'tbl_posp_invoice', ['AgentId', 'FinancialYear', 'Month'])
    op.create_index('ix_tbl_posp_invoice_InvoiceDate', 'tbl_posp_invoice', ['InvoiceDate'])
    op.create_index('ix_tbl_posp_invoice_Status', 'tbl_posp_invoice', ['Status'])

    # 2. tbl_target (Employee & Sales Executive Monthly Quotas & Achievement)
    op.create_table(
        'tbl_target',
        sa.Column('TargetId', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('EmpId', sa.Integer(), nullable=False),
        sa.Column('FinancialYear', sa.String(length=20), nullable=False),
        sa.Column('Month', sa.String(length=20), nullable=False),
        sa.Column('TargetMonth', sa.String(length=20), nullable=True),
        sa.Column('TargetAmount', sa.Numeric(precision=18, scale=2), nullable=False, server_default='0.00'),
        sa.Column('AchievedTargetAmount', sa.Numeric(precision=18, scale=2), nullable=False, server_default='0.00'),
        sa.Column('HealthInsuranceAmount', sa.Numeric(precision=18, scale=2), nullable=False, server_default='0.00'),
        sa.Column('AnnualAmount', sa.Numeric(precision=18, scale=2), nullable=True, server_default='0.00'),
        sa.Column('CreatedDate', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('CreatedBy', sa.String(length=100), nullable=True),
        sa.Column('UpdatedDate', sa.DateTime(), nullable=True),
        sa.Column('UpdatedBy', sa.String(length=100), nullable=True),
        sa.PrimaryKeyConstraint('TargetId'),
        mysql_charset='utf8',
        mysql_collate='utf8_general_ci',
        mysql_row_format='DYNAMIC'
    )
    op.create_index('ix_tbl_target_Emp_FY_Month', 'tbl_target', ['EmpId', 'FinancialYear', 'Month'])
    op.create_index('ix_tbl_target_FinancialYear', 'tbl_target', ['FinancialYear'])


def downgrade() -> None:
    op.drop_index('ix_tbl_target_FinancialYear', table_name='tbl_target')
    op.drop_index('ix_tbl_target_Emp_FY_Month', table_name='tbl_target')
    op.drop_table('tbl_target')

    op.drop_index('ix_tbl_posp_invoice_Status', table_name='tbl_posp_invoice')
    op.drop_index('ix_tbl_posp_invoice_InvoiceDate', table_name='tbl_posp_invoice')
    op.drop_index('ix_tbl_posp_invoice_Agent_FY_Month', table_name='tbl_posp_invoice')
    op.drop_index('ix_tbl_posp_invoice_InvoiceNo', table_name='tbl_posp_invoice')
    op.drop_table('tbl_posp_invoice')
