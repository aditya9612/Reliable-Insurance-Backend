"""phase_16b_admin_profiles_masters_and_audit

Revision ID: a16b0c4d1601
Revises: f15b0c3d1501
Create Date: 2026-10-08 14:50:00.000000+00:00

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a16b0c4d1601'
down_revision: Union[str, None] = 'f15b0c3d1501'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. tbl_loginhistory (Persistent Login & Session Audit Log)
    op.create_table(
        'tbl_loginhistory',
        sa.Column('LoginHistoryId', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('UserId', sa.Integer(), nullable=True),
        sa.Column('UserName', sa.String(length=255), nullable=True),
        sa.Column('LogInOrLogOut', sa.String(length=50), nullable=True),
        sa.Column('funPerform', sa.String(length=255), nullable=True),
        sa.Column('IPAddress', sa.String(length=100), nullable=True),
        sa.Column('CreateDate', sa.DateTime(), nullable=True, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('Remark', sa.String(length=255), nullable=True),
        sa.PrimaryKeyConstraint('LoginHistoryId'),
        mysql_charset='utf8',
        mysql_collate='utf8_general_ci',
        mysql_row_format='DYNAMIC'
    )
    op.create_index('ix_tbl_loginhistory_UserId', 'tbl_loginhistory', ['UserId'])
    op.create_index('ix_tbl_loginhistory_CreateDate', 'tbl_loginhistory', ['CreateDate'])

    # 2. tbl_role_privilege (Dynamic Menu & Screen Privilege Mapping)
    op.create_table(
        'tbl_role_privilege',
        sa.Column('Id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('BranchId', sa.Integer(), nullable=True),
        sa.Column('RoleId', sa.Integer(), nullable=True),
        sa.Column('ScreenId', sa.Integer(), nullable=True),
        sa.Column('CreateDate', sa.DateTime(), nullable=True, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('isdeleted', sa.String(length=10), nullable=False, server_default='0'),
        sa.PrimaryKeyConstraint('Id'),
        mysql_charset='utf8',
        mysql_collate='utf8_general_ci',
        mysql_row_format='DYNAMIC'
    )
    op.create_index('ix_tbl_role_privilege_BranchId', 'tbl_role_privilege', ['BranchId'])
    op.create_index('ix_tbl_role_privilege_RoleId', 'tbl_role_privilege', ['RoleId'])
    op.create_index('ix_tbl_role_privilege_ScreenId', 'tbl_role_privilege', ['ScreenId'])

    # 3. tbl_menu (System Navigation Tree & Screen Master)
    op.create_table(
        'tbl_menu',
        sa.Column('MenuId', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('MenuName', sa.String(length=100), nullable=True),
        sa.Column('MenuUrl', sa.String(length=255), nullable=True),
        sa.Column('ParentMenuId', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('OrderNo', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('IconClass', sa.String(length=50), nullable=True),
        sa.Column('isdeleted', sa.String(length=10), nullable=False, server_default='0'),
        sa.PrimaryKeyConstraint('MenuId'),
        mysql_charset='utf8',
        mysql_collate='utf8_general_ci',
        mysql_row_format='DYNAMIC'
    )
    op.create_index('ix_tbl_menu_ParentMenuId', 'tbl_menu', ['ParentMenuId'])

    # 4. tbl_fueltype (Vehicle Fuel Type Reference Master)
    op.create_table(
        'tbl_fueltype',
        sa.Column('FuelTypeId', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('FuelType', sa.String(length=50), nullable=True),
        sa.Column('isdeleted', sa.String(length=10), nullable=False, server_default='0'),
        sa.Column('CreateDate', sa.DateTime(), nullable=True, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('FuelTypeId'),
        mysql_charset='utf8',
        mysql_collate='utf8_general_ci',
        mysql_row_format='DYNAMIC'
    )
    op.create_index('ix_tbl_fueltype_isdeleted', 'tbl_fueltype', ['isdeleted'])

    # 5. tbl_financier (Financier Directory Master)
    op.create_table(
        'tbl_financier',
        sa.Column('FinancierId', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('FinancierName', sa.String(length=255), nullable=True),
        sa.Column('BranchId', sa.Integer(), nullable=True),
        sa.Column('ContactNo', sa.String(length=50), nullable=True),
        sa.Column('EmailId', sa.String(length=100), nullable=True),
        sa.Column('Address', sa.String(length=255), nullable=True),
        sa.Column('isdeleted', sa.String(length=10), nullable=False, server_default='0'),
        sa.Column('CreateDate', sa.DateTime(), nullable=True, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('FinancierId'),
        mysql_charset='utf8',
        mysql_collate='utf8_general_ci',
        mysql_row_format='DYNAMIC'
    )
    op.create_index('ix_tbl_financier_BranchId', 'tbl_financier', ['BranchId'])
    op.create_index('ix_tbl_financier_isdeleted', 'tbl_financier', ['isdeleted'])

    # 6. tbl_surveyor (Surveyor Directory Master)
    op.create_table(
        'tbl_surveyor',
        sa.Column('SurveyorId', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('SurveyorName', sa.String(length=100), nullable=True),
        sa.Column('ContactNo', sa.String(length=50), nullable=True),
        sa.Column('EmailId', sa.String(length=100), nullable=True),
        sa.Column('LicenseNo', sa.String(length=50), nullable=True),
        sa.Column('LicenseExpiryDate', sa.Date(), nullable=True),
        sa.Column('Address', sa.String(length=255), nullable=True),
        sa.Column('City', sa.String(length=100), nullable=True),
        sa.Column('StateId', sa.Integer(), nullable=True),
        sa.Column('BranchId', sa.Integer(), nullable=True),
        sa.Column('BankId', sa.Integer(), nullable=True),
        sa.Column('AccountNo', sa.String(length=50), nullable=True),
        sa.Column('IFSC_Code', sa.String(length=50), nullable=True),
        sa.Column('isdeleted', sa.String(length=10), nullable=False, server_default='0'),
        sa.Column('CreateDate', sa.DateTime(), nullable=True, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('UpdateDate', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('SurveyorId'),
        mysql_charset='utf8',
        mysql_collate='utf8_general_ci',
        mysql_row_format='DYNAMIC'
    )
    op.create_index('ix_tbl_surveyor_BranchId', 'tbl_surveyor', ['BranchId'])
    op.create_index('ix_tbl_surveyor_LicenseNo', 'tbl_surveyor', ['LicenseNo'])
    op.create_index('ix_tbl_surveyor_isdeleted', 'tbl_surveyor', ['isdeleted'])

    # 7. Add hierarchy columns to tbl_employee
    op.add_column('tbl_employee', sa.Column('Hei_Data', sa.String(length=255), nullable=True))
    op.add_column('tbl_employee', sa.Column('Hie_DataSales', sa.String(length=255), nullable=True))
    op.add_column('tbl_employee', sa.Column('Hie_DataOprn', sa.String(length=255), nullable=True))

    # 8. Add KYC status and remarks to tbl_agent
    op.add_column('tbl_agent', sa.Column('kyc_status', sa.String(length=20), nullable=False, server_default='PENDING'))
    op.add_column('tbl_agent', sa.Column('kyc_remarks', sa.String(length=255), nullable=True))


def downgrade() -> None:
    # 8. Drop KYC columns from tbl_agent
    op.drop_column('tbl_agent', 'kyc_remarks')
    op.drop_column('tbl_agent', 'kyc_status')

    # 7. Drop hierarchy columns from tbl_employee
    op.drop_column('tbl_employee', 'Hie_DataOprn')
    op.drop_column('tbl_employee', 'Hie_DataSales')
    op.drop_column('tbl_employee', 'Hei_Data')

    # 6-1. Drop tables
    op.drop_table('tbl_surveyor')
    op.drop_table('tbl_financier')
    op.drop_table('tbl_fueltype')
    op.drop_table('tbl_menu')
    op.drop_table('tbl_role_privilege')
    op.drop_table('tbl_loginhistory')
