"""phase_13_integrations_notifications_renewal_tables

Revision ID: d13e0f7a1301
Revises: c12d0e6f1201
Create Date: 2026-10-07 16:30:00.000000+00:00

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd13e0f7a1301'
down_revision: Union[str, None] = 'c12d0e6f1201'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. tbl_vehiclenorc_details (Vehicle RC & KYC Local Cache - 54 fields)
    op.create_table(
        'tbl_vehiclenorc_details',
        sa.Column('VehRcId', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('request_id', sa.String(length=100), nullable=True),
        sa.Column('license_plate_RegNo', sa.String(length=50), nullable=False),
        sa.Column('owner_name', sa.String(length=255), nullable=True),
        sa.Column('father_name', sa.String(length=255), nullable=True),
        sa.Column('is_financed', sa.String(length=50), nullable=True),
        sa.Column('financer', sa.String(length=255), nullable=True),
        sa.Column('present_address', sa.Text(), nullable=True),
        sa.Column('permanent_address', sa.Text(), nullable=True),
        sa.Column('insurance_company', sa.String(length=255), nullable=True),
        sa.Column('insurance_policy', sa.String(length=100), nullable=True),
        sa.Column('insurance_expiry', sa.DateTime(), nullable=True),
        sa.Column('rc_class', sa.String(length=100), nullable=True),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('registration_date', sa.DateTime(), nullable=True),
        sa.Column('vehicle_age', sa.String(length=100), nullable=True),
        sa.Column('pucc_upto', sa.DateTime(), nullable=True),
        sa.Column('pucc_number', sa.String(length=100), nullable=True),
        sa.Column('chassis_number', sa.String(length=100), nullable=True),
        sa.Column('engine_number', sa.String(length=100), nullable=True),
        sa.Column('fuel_type', sa.String(length=50), nullable=True),
        sa.Column('brand_name', sa.String(length=100), nullable=True),
        sa.Column('brand_model', sa.String(length=100), nullable=True),
        sa.Column('body_type', sa.String(length=100), nullable=True),
        sa.Column('cubic_capacity', sa.String(length=50), nullable=True),
        sa.Column('gross_weight', sa.String(length=50), nullable=True),
        sa.Column('cylinders', sa.String(length=50), nullable=True),
        sa.Column('color', sa.String(length=50), nullable=True),
        sa.Column('norms', sa.String(length=50), nullable=True),
        sa.Column('fit_up_to', sa.String(length=50), nullable=True),
        sa.Column('manufacturing_date', sa.String(length=50), nullable=True),
        sa.Column('manufacturing_date_formatted', sa.String(length=50), nullable=True),
        sa.Column('rto_name', sa.String(length=100), nullable=True),
        sa.Column('latest_by', sa.String(length=100), nullable=True),
        sa.Column('sleeper_capacity', sa.String(length=50), nullable=True),
        sa.Column('standing_capacity', sa.String(length=50), nullable=True),
        sa.Column('wheelbase', sa.String(length=50), nullable=True),
        sa.Column('unladen_weight', sa.String(length=50), nullable=True),
        sa.Column('noc_details', sa.String(length=100), nullable=True),
        sa.Column('seating_capacity', sa.String(length=50), nullable=True),
        sa.Column('owner_count', sa.String(length=50), nullable=True),
        sa.Column('tax_upto', sa.String(length=50), nullable=True),
        sa.Column('tax_paid_upto', sa.String(length=50), nullable=True),
        sa.Column('permit_number', sa.String(length=100), nullable=True),
        sa.Column('permit_issue_date', sa.String(length=50), nullable=True),
        sa.Column('permit_valid_from', sa.String(length=50), nullable=True),
        sa.Column('permit_valid_upto', sa.String(length=50), nullable=True),
        sa.Column('permit_type', sa.String(length=100), nullable=True),
        sa.Column('national_permit_number', sa.String(length=100), nullable=True),
        sa.Column('national_permit_upto', sa.String(length=50), nullable=True),
        sa.Column('national_permit_issued_by', sa.String(length=100), nullable=True),
        sa.Column('rc_status', sa.String(length=50), nullable=True),
        sa.Column('CreatedDate', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('CreatedBy', sa.String(length=100), nullable=True),
        sa.PrimaryKeyConstraint('VehRcId'),
        mysql_charset='utf8',
        mysql_collate='utf8_general_ci',
        mysql_row_format='DYNAMIC'
    )
    op.create_index('ix_tbl_vehiclenorc_details_RegNo', 'tbl_vehiclenorc_details', ['license_plate_RegNo'], unique=True)
    op.create_index('ix_tbl_vehiclenorc_details_request_id', 'tbl_vehiclenorc_details', ['request_id'], unique=False)
    op.create_index('ix_tbl_vehiclenorc_details_chassis', 'tbl_vehiclenorc_details', ['chassis_number'], unique=False)
    op.create_index('ix_tbl_vehiclenorc_details_engine', 'tbl_vehiclenorc_details', ['engine_number'], unique=False)
    op.create_index('ix_tbl_vehiclenorc_details_insurance_expiry', 'tbl_vehiclenorc_details', ['insurance_expiry'], unique=False)

    # 2. tbl_preyearrenewalstatus (Policy Renewal Status & CRM)
    op.create_table(
        'tbl_preyearrenewalstatus',
        sa.Column('Id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('TransanctionId', sa.Integer(), nullable=False),
        sa.Column('Remark', sa.Text(), nullable=True),
        sa.Column('FinancialYear', sa.String(length=20), nullable=False),
        sa.Column('isdeleted', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('CreatedDate', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('RegistrationNo', sa.String(length=50), nullable=False),
        sa.Column('InsuranceCompany', sa.String(length=255), nullable=True),
        sa.Column('TotalPremium', sa.Float(), server_default=sa.text('0.0'), nullable=False),
        sa.Column('MobileNo', sa.String(length=50), nullable=True),
        sa.Column('ExpiryDate', sa.DateTime(), nullable=False),
        sa.Column('FollowupDate', sa.DateTime(), nullable=True),
        sa.Column('UserRoleId', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('AgentId', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('ExecutiveId', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('RenewalStatus', sa.String(length=50), server_default=sa.text("'Follow'"), nullable=False),
        sa.Column('BranchId', sa.Integer(), server_default=sa.text('0'), nullable=True),
        sa.Column('UpdatedDate', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=True),
        sa.Column('UpdatedBy', sa.String(length=100), nullable=True),
        sa.PrimaryKeyConstraint('Id'),
        mysql_charset='utf8',
        mysql_collate='utf8_general_ci',
        mysql_row_format='DYNAMIC'
    )
    op.create_index('ix_tbl_preyearrenewalstatus_RegNo_FY', 'tbl_preyearrenewalstatus', ['RegistrationNo', 'FinancialYear'], unique=False)
    op.create_index('ix_tbl_preyearrenewalstatus_TransanctionId', 'tbl_preyearrenewalstatus', ['TransanctionId'], unique=False)
    op.create_index('ix_tbl_preyearrenewalstatus_ExpiryDate', 'tbl_preyearrenewalstatus', ['ExpiryDate'], unique=False)
    op.create_index('ix_tbl_preyearrenewalstatus_FollowupDate', 'tbl_preyearrenewalstatus', ['FollowupDate'], unique=False)
    op.create_index('ix_tbl_preyearrenewalstatus_AgentId', 'tbl_preyearrenewalstatus', ['AgentId'], unique=False)
    op.create_index('ix_tbl_preyearrenewalstatus_ExecutiveId', 'tbl_preyearrenewalstatus', ['ExecutiveId'], unique=False)
    op.create_index('ix_tbl_preyearrenewalstatus_BranchId', 'tbl_preyearrenewalstatus', ['BranchId'], unique=False)
    op.create_index('ix_tbl_preyearrenewalstatus_RenewalStatus', 'tbl_preyearrenewalstatus', ['RenewalStatus'], unique=False)

    # 3. tbl_renewal_followup_history (Additive telecaller interaction audit history)
    op.create_table(
        'tbl_renewal_followup_history',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('renewal_status_id', sa.Integer(), nullable=False),
        sa.Column('remark', sa.Text(), nullable=False),
        sa.Column('followup_date', sa.DateTime(), nullable=True),
        sa.Column('status_at_time', sa.String(length=50), server_default=sa.text("'Follow'"), nullable=False),
        sa.Column('recorded_by', sa.String(length=100), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        mysql_charset='utf8',
        mysql_collate='utf8_general_ci',
        mysql_row_format='DYNAMIC'
    )
    op.create_index('ix_tbl_renewal_history_renewal_status_id', 'tbl_renewal_followup_history', ['renewal_status_id'], unique=False)

    # 4. tbl_sms_log (Outbound SMS audit log)
    op.create_table(
        'tbl_sms_log',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('mobile_number', sa.String(length=20), nullable=False),
        sa.Column('message_text', sa.Text(), nullable=False),
        sa.Column('template_id', sa.String(length=50), nullable=True),
        sa.Column('provider', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('provider_message_id', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        mysql_charset='utf8',
        mysql_collate='utf8_general_ci',
        mysql_row_format='DYNAMIC'
    )
    op.create_index('ix_tbl_sms_log_mobile', 'tbl_sms_log', ['mobile_number'], unique=False)
    op.create_index('ix_tbl_sms_log_created_at', 'tbl_sms_log', ['created_at'], unique=False)

    # 5. tbl_pushnotification_log (OneSignal & Push Notification Log)
    op.create_table(
        'tbl_pushnotification_log',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('external_user_id', sa.String(length=100), nullable=False),
        sa.Column('notification_type', sa.String(length=50), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('provider', sa.String(length=50), nullable=False),
        sa.Column('provider_response_id', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        mysql_charset='utf8',
        mysql_collate='utf8_general_ci',
        mysql_row_format='DYNAMIC'
    )
    op.create_index('ix_tbl_push_log_external_user', 'tbl_pushnotification_log', ['external_user_id'], unique=False)
    op.create_index('ix_tbl_push_log_type', 'tbl_pushnotification_log', ['notification_type'], unique=False)
    op.create_index('ix_tbl_push_log_created_at', 'tbl_pushnotification_log', ['created_at'], unique=False)

    # 6. tbl_messagemaster (Internal Inbox Master)
    op.create_table(
        'tbl_messagemaster',
        sa.Column('MessageID', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('Message', sa.Text(), nullable=False),
        sa.Column('CreatedDate', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('MessageID'),
        mysql_charset='utf8',
        mysql_collate='utf8_general_ci',
        mysql_row_format='DYNAMIC'
    )

    # 7. tbl_messagedetails (Internal Inbox Recipient & Status)
    op.create_table(
        'tbl_messagedetails',
        sa.Column('MessagedetailId', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('MessageID', sa.Integer(), nullable=False),
        sa.Column('userId', sa.Integer(), nullable=False),
        sa.Column('Messagedate', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('readStatus', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('Flag', sa.String(length=10), nullable=True),
        sa.Column('Opr', sa.String(length=50), nullable=True),
        sa.PrimaryKeyConstraint('MessagedetailId'),
        mysql_charset='utf8',
        mysql_collate='utf8_general_ci',
        mysql_row_format='DYNAMIC'
    )
    op.create_index('ix_tbl_messagedetails_MessageID', 'tbl_messagedetails', ['MessageID'], unique=False)
    op.create_index('ix_tbl_messagedetails_userId', 'tbl_messagedetails', ['userId'], unique=False)
    op.create_index('ix_tbl_messagedetails_readStatus', 'tbl_messagedetails', ['readStatus'], unique=False)

    # 8. tbl_otp_log (OTP Lifecycle & Persistence)
    op.create_table(
        'tbl_otp_log',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('mobile_number', sa.String(length=20), nullable=False),
        sa.Column('otp_hash', sa.String(length=128), nullable=False),
        sa.Column('purpose', sa.String(length=50), server_default=sa.text("'LOGIN'"), nullable=False),
        sa.Column('attempts_count', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('max_attempts', sa.Integer(), server_default=sa.text('3'), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('is_verified', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        mysql_charset='utf8',
        mysql_collate='utf8_general_ci',
        mysql_row_format='DYNAMIC'
    )
    op.create_index('ix_tbl_otp_log_mobile', 'tbl_otp_log', ['mobile_number'], unique=False)
    op.create_index('ix_tbl_otp_log_expires_at', 'tbl_otp_log', ['expires_at'], unique=False)


def downgrade() -> None:
    op.drop_table('tbl_otp_log')
    op.drop_table('tbl_messagedetails')
    op.drop_table('tbl_messagemaster')
    op.drop_table('tbl_pushnotification_log')
    op.drop_table('tbl_sms_log')
    op.drop_table('tbl_renewal_followup_history')
    op.drop_table('tbl_preyearrenewalstatus')
    op.drop_table('tbl_vehiclenorc_details')
