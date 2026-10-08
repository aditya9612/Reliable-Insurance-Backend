"""phase_15b_operational_utilities_and_profiles

Revision ID: f15b0c3d1501
Revises: e14a0b2c1401
Create Date: 2026-10-08 01:45:00.000000+00:00

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f15b0c3d1501'
down_revision: Union[str, None] = 'e14a0b2c1401'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. tbl_employee (Staff Directory & Hierarchy Master)
    op.create_table(
        'tbl_employee',
        sa.Column('EmpId', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('UserName', sa.String(length=255), nullable=True),
        sa.Column('UserPassword', sa.String(length=255), nullable=True),
        sa.Column('EmpCode', sa.String(length=50), nullable=True),
        sa.Column('EmpFName', sa.String(length=100), nullable=True),
        sa.Column('EmpMName', sa.String(length=100), nullable=True),
        sa.Column('EmpLName', sa.String(length=100), nullable=True),
        sa.Column('AddrLine1', sa.String(length=255), nullable=True),
        sa.Column('AddrLine2', sa.String(length=255), nullable=True),
        sa.Column('TalukaId', sa.Integer(), nullable=True),
        sa.Column('StateId', sa.Integer(), nullable=True),
        sa.Column('DistrictId', sa.Integer(), nullable=True),
        sa.Column('Gender', sa.String(length=20), nullable=True),
        sa.Column('MaritalStatus', sa.String(length=20), nullable=True),
        sa.Column('MoblieNo', sa.String(length=50), nullable=True),
        sa.Column('MoblieNo1', sa.String(length=50), nullable=True),
        sa.Column('EmailId', sa.String(length=100), nullable=True),
        sa.Column('PAN_No', sa.String(length=20), nullable=True),
        sa.Column('AadharNo', sa.String(length=20), nullable=True),
        sa.Column('BankId', sa.Integer(), nullable=True),
        sa.Column('BankBranch', sa.String(length=100), nullable=True),
        sa.Column('Ifsc_code', sa.String(length=50), nullable=True),
        sa.Column('accountNo', sa.String(length=50), nullable=True),
        sa.Column('BranchId', sa.Integer(), nullable=True),
        sa.Column('UserRoleId', sa.Integer(), nullable=True),
        sa.Column('UserId', sa.Integer(), nullable=True),
        sa.Column('CreateDate', sa.DateTime(), nullable=True, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('CreateUser', sa.String(length=100), nullable=True),
        sa.Column('UpdateDate', sa.DateTime(), nullable=True),
        sa.Column('UpdateUser', sa.String(length=100), nullable=True),
        sa.Column('isdeleted', sa.String(length=10), nullable=False, server_default='0'),
        sa.PrimaryKeyConstraint('EmpId'),
        mysql_charset='utf8',
        mysql_collate='utf8_general_ci',
        mysql_row_format='DYNAMIC'
    )
    op.create_index('ix_tbl_employee_EmpCode', 'tbl_employee', ['EmpCode'])
    op.create_index('ix_tbl_employee_BranchId', 'tbl_employee', ['BranchId'])
    op.create_index('ix_tbl_employee_UserId', 'tbl_employee', ['UserId'])
    op.create_index('ix_tbl_employee_UserRoleId', 'tbl_employee', ['UserRoleId'])
    op.create_index('ix_tbl_employee_isdeleted', 'tbl_employee', ['isdeleted'])

    # 2. tbl_agent (POSP Agent Profiles & Master)
    op.create_table(
        'tbl_agent',
        sa.Column('AgentId', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('AgentCode', sa.String(length=50), nullable=True),
        sa.Column('AgentFName', sa.String(length=100), nullable=True),
        sa.Column('AgentMName', sa.String(length=100), nullable=True),
        sa.Column('AgentLName', sa.String(length=100), nullable=True),
        sa.Column('NickName', sa.String(length=100), nullable=True),
        sa.Column('Champanion', sa.String(length=100), nullable=True),
        sa.Column('MobileNo', sa.String(length=50), nullable=True),
        sa.Column('EmailId', sa.String(length=100), nullable=True),
        sa.Column('PANNo', sa.String(length=20), nullable=True),
        sa.Column('AadharNo', sa.String(length=20), nullable=True),
        sa.Column('SalesExecutiveId', sa.Integer(), nullable=True),
        sa.Column('CoordinatorId', sa.Integer(), nullable=True),
        sa.Column('FranchiseId', sa.Integer(), nullable=True),
        sa.Column('BranchId', sa.Integer(), nullable=True),
        sa.Column('UserId', sa.Integer(), nullable=True),
        sa.Column('BankId', sa.Integer(), nullable=True),
        sa.Column('BankBranch', sa.String(length=100), nullable=True),
        sa.Column('Ifsc_code', sa.String(length=50), nullable=True),
        sa.Column('accountNo', sa.String(length=50), nullable=True),
        sa.Column('IsActive', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('CreateDate', sa.DateTime(), nullable=True, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('CreateUser', sa.String(length=100), nullable=True),
        sa.Column('UpdateDate', sa.DateTime(), nullable=True),
        sa.Column('UpdateUser', sa.String(length=100), nullable=True),
        sa.Column('isdeleted', sa.String(length=10), nullable=False, server_default='0'),
        sa.PrimaryKeyConstraint('AgentId'),
        mysql_charset='utf8',
        mysql_collate='utf8_general_ci',
        mysql_row_format='DYNAMIC'
    )
    op.create_index('ix_tbl_agent_AgentCode', 'tbl_agent', ['AgentCode'])
    op.create_index('ix_tbl_agent_SalesExecutiveId', 'tbl_agent', ['SalesExecutiveId'])
    op.create_index('ix_tbl_agent_CoordinatorId', 'tbl_agent', ['CoordinatorId'])
    op.create_index('ix_tbl_agent_FranchiseId', 'tbl_agent', ['FranchiseId'])
    op.create_index('ix_tbl_agent_BranchId', 'tbl_agent', ['BranchId'])
    op.create_index('ix_tbl_agent_UserId', 'tbl_agent', ['UserId'])
    op.create_index('ix_tbl_agent_isdeleted', 'tbl_agent', ['isdeleted'])

    # 3. tbl_franchise (Franchise Hierarchy & Profiles)
    op.create_table(
        'tbl_franchise',
        sa.Column('FranchiseId', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('UserName', sa.String(length=255), nullable=True),
        sa.Column('UserPassword', sa.String(length=255), nullable=True),
        sa.Column('initial', sa.String(length=20), nullable=True),
        sa.Column('FranFName', sa.String(length=100), nullable=True),
        sa.Column('FranMName', sa.String(length=100), nullable=True),
        sa.Column('FranLName', sa.String(length=100), nullable=True),
        sa.Column('FranCode', sa.String(length=50), nullable=True),
        sa.Column('PerAddrLine1', sa.String(length=255), nullable=True),
        sa.Column('PerAddrLine2', sa.String(length=255), nullable=True),
        sa.Column('PerTalukaId', sa.Integer(), nullable=True),
        sa.Column('PerDistrictId', sa.Integer(), nullable=True),
        sa.Column('PerStateId', sa.Integer(), nullable=True),
        sa.Column('PerPinCode', sa.String(length=20), nullable=True),
        sa.Column('MoblieNo1', sa.String(length=50), nullable=True),
        sa.Column('MoblieNo2', sa.String(length=50), nullable=True),
        sa.Column('Gender', sa.String(length=20), nullable=True),
        sa.Column('MaritalStatus', sa.String(length=20), nullable=True),
        sa.Column('PAN_No', sa.String(length=20), nullable=True),
        sa.Column('AadharNo', sa.String(length=20), nullable=True),
        sa.Column('BankId', sa.Integer(), nullable=True),
        sa.Column('NominieeName', sa.String(length=100), nullable=True),
        sa.Column('Bank_branch', sa.String(length=100), nullable=True),
        sa.Column('Ifsc_code', sa.String(length=50), nullable=True),
        sa.Column('accountNo', sa.String(length=50), nullable=True),
        sa.Column('DateOfBirth', sa.Date(), nullable=True),
        sa.Column('EmailId', sa.String(length=100), nullable=True),
        sa.Column('BranchId', sa.Integer(), nullable=True),
        sa.Column('ParentFranchiseId', sa.Integer(), nullable=True),
        sa.Column('CoordinatorId', sa.Integer(), nullable=True),
        sa.Column('QuotationCo_Id', sa.Integer(), nullable=True),
        sa.Column('InspectionCo_Id', sa.Integer(), nullable=True),
        sa.Column('EndrosmentCo_Id', sa.Integer(), nullable=True),
        sa.Column('UserRoleId', sa.Integer(), nullable=True),
        sa.Column('CreateDate', sa.DateTime(), nullable=True, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('CreateUser', sa.String(length=100), nullable=True),
        sa.Column('UpdateDate', sa.DateTime(), nullable=True),
        sa.Column('UpdateUser', sa.String(length=100), nullable=True),
        sa.Column('isdeleted', sa.String(length=10), nullable=False, server_default='0'),
        sa.PrimaryKeyConstraint('FranchiseId'),
        mysql_charset='utf8',
        mysql_collate='utf8_general_ci',
        mysql_row_format='DYNAMIC'
    )
    op.create_index('ix_tbl_franchise_FranCode', 'tbl_franchise', ['FranCode'])
    op.create_index('ix_tbl_franchise_BranchId', 'tbl_franchise', ['BranchId'])
    op.create_index('ix_tbl_franchise_ParentFranchiseId', 'tbl_franchise', ['ParentFranchiseId'])
    op.create_index('ix_tbl_franchise_isdeleted', 'tbl_franchise', ['isdeleted'])

    # 4. tbl_idvrequest (Special Underwriter IDV Override Approval Queue)
    op.create_table(
        'tbl_idvrequest',
        sa.Column('IDVRequestId', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('RequestDate', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('InsuranceCompanyId', sa.Integer(), nullable=True),
        sa.Column('VehicleTypeId', sa.Integer(), nullable=True),
        sa.Column('PolicyTypeId', sa.String(length=50), nullable=True),
        sa.Column('VehicleMake', sa.String(length=100), nullable=True),
        sa.Column('VehicleModel', sa.String(length=100), nullable=True),
        sa.Column('RegistrationNo', sa.String(length=50), nullable=True),
        sa.Column('Passyear', sa.String(length=20), nullable=True),
        sa.Column('RequestedIDV', sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column('ApprovedIDV', sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column('SalesExId', sa.Integer(), nullable=True),
        sa.Column('RequestedBy', sa.String(length=100), nullable=True),
        sa.Column('ApprovedBy', sa.String(length=100), nullable=True),
        sa.Column('Status', sa.String(length=50), nullable=False, server_default='PENDING'),
        sa.Column('Note', sa.Text(), nullable=True),
        sa.Column('ApprovedRemark', sa.Text(), nullable=True),
        sa.Column('CreateDate', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('UpdateDate', sa.DateTime(), nullable=True),
        sa.Column('isdeleted', sa.String(length=10), nullable=False, server_default='0'),
        sa.PrimaryKeyConstraint('IDVRequestId'),
        mysql_charset='utf8',
        mysql_collate='utf8_general_ci',
        mysql_row_format='DYNAMIC'
    )
    op.create_index('ix_tbl_idvrequest_SalesExId', 'tbl_idvrequest', ['SalesExId'])
    op.create_index('ix_tbl_idvrequest_Status', 'tbl_idvrequest', ['Status'])
    op.create_index('ix_tbl_idvrequest_RegistrationNo', 'tbl_idvrequest', ['RegistrationNo'])
    op.create_index('ix_tbl_idvrequest_RequestDate', 'tbl_idvrequest', ['RequestDate'])
    op.create_index('ix_tbl_idvrequest_isdeleted', 'tbl_idvrequest', ['isdeleted'])

    # 5. tbl_healthmember (Non-Motor Health Family Member Grid)
    op.create_table(
        'tbl_healthmember',
        sa.Column('MemberId', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('TransanctionId', sa.Integer(), nullable=True),
        sa.Column('CustomerId', sa.Integer(), nullable=True),
        sa.Column('MemberName', sa.String(length=255), nullable=False),
        sa.Column('Relationship', sa.String(length=50), nullable=False),
        sa.Column('Gender', sa.String(length=20), nullable=False),
        sa.Column('DOB', sa.Date(), nullable=True),
        sa.Column('Age', sa.Integer(), nullable=False),
        sa.Column('SumInsured', sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column('PreExistingDisease', sa.String(length=500), nullable=True),
        sa.Column('NomineeName', sa.String(length=255), nullable=True),
        sa.Column('Status', sa.String(length=50), nullable=False, server_default='ACTIVE'),
        sa.Column('CreateDate', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('CreateUser', sa.String(length=100), nullable=True),
        sa.Column('UpdateDate', sa.DateTime(), nullable=True),
        sa.Column('UpdateUser', sa.String(length=100), nullable=True),
        sa.Column('isdeleted', sa.String(length=10), nullable=False, server_default='0'),
        sa.PrimaryKeyConstraint('MemberId'),
        mysql_charset='utf8',
        mysql_collate='utf8_general_ci',
        mysql_row_format='DYNAMIC'
    )
    op.create_index('ix_tbl_healthmember_TransanctionId', 'tbl_healthmember', ['TransanctionId'])
    op.create_index('ix_tbl_healthmember_CustomerId', 'tbl_healthmember', ['CustomerId'])
    op.create_index('ix_tbl_healthmember_Status', 'tbl_healthmember', ['Status'])
    op.create_index('ix_tbl_healthmember_isdeleted', 'tbl_healthmember', ['isdeleted'])

    # 6. tbl_importagentpolicy (Bulk Excel Policy MIS Staging Table)
    op.create_table(
        'tbl_importagentpolicy',
        sa.Column('Id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('DateOfInsurance', sa.String(length=50), nullable=True),
        sa.Column('BrokerName', sa.String(length=255), nullable=True),
        sa.Column('ClientName', sa.String(length=255), nullable=True),
        sa.Column('VehicleType', sa.String(length=100), nullable=True),
        sa.Column('VehicleNumber', sa.String(length=100), nullable=True),
        sa.Column('PolicyNumber', sa.String(length=100), nullable=True),
        sa.Column('Segments', sa.String(length=100), nullable=True),
        sa.Column('InsuranceCompany', sa.String(length=255), nullable=True),
        sa.Column('IssuingID', sa.String(length=100), nullable=True),
        sa.Column('InceptionDate', sa.String(length=50), nullable=True),
        sa.Column('ExpiryDate', sa.String(length=50), nullable=True),
        sa.Column('GrossAmount', sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column('NetAmount', sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column('ODPremium', sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column('TPPremium', sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column('BrokerReceivedPct', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('BrokerPayout', sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column('PolicyType', sa.String(length=100), nullable=True),
        sa.Column('FuelType', sa.String(length=100), nullable=True),
        sa.Column('MfgDate', sa.String(length=50), nullable=True),
        sa.Column('GVW', sa.String(length=50), nullable=True),
        sa.Column('ProductType', sa.String(length=100), nullable=True),
        sa.Column('CreatedBy', sa.String(length=100), nullable=True),
        sa.Column('CreatedDate', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('IsProcess', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('Remark', sa.String(length=1000), nullable=True),
        sa.Column('FinancialYear', sa.String(length=50), nullable=True),
        sa.Column('BatchId', sa.String(length=100), nullable=True),
        sa.Column('isdeleted', sa.String(length=10), nullable=False, server_default='0'),
        sa.PrimaryKeyConstraint('Id'),
        mysql_charset='utf8',
        mysql_collate='utf8_general_ci',
        mysql_row_format='DYNAMIC'
    )
    op.create_index('ix_tbl_importagentpolicy_BatchId', 'tbl_importagentpolicy', ['BatchId'])
    op.create_index('ix_tbl_importagentpolicy_PolicyNumber', 'tbl_importagentpolicy', ['PolicyNumber'])
    op.create_index('ix_tbl_importagentpolicy_IsProcess', 'tbl_importagentpolicy', ['IsProcess'])
    op.create_index('ix_tbl_importagentpolicy_isdeleted', 'tbl_importagentpolicy', ['isdeleted'])


def downgrade() -> None:
    op.drop_table('tbl_importagentpolicy')
    op.drop_table('tbl_healthmember')
    op.drop_table('tbl_idvrequest')
    op.drop_table('tbl_franchise')
    op.drop_table('tbl_agent')
    op.drop_table('tbl_employee')
