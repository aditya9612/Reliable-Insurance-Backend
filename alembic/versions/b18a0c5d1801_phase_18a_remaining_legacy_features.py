"""phase_18a_remaining_legacy_features

Revision ID: b18a0c5d1801
Revises: a16b0c4d1601
Create Date: 2026-10-08 19:58:00.000000+00:00

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b18a0c5d1801"
down_revision: Union[str, None] = "a16b0c4d1601"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. tbl_idealpaymentreceipt (F-17B-085)
    op.create_table(
        "tbl_idealpaymentreceipt",
        sa.Column("Id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("Ideal_Doc_No", sa.String(length=100), nullable=False),
        sa.Column("PaymentDate", sa.Date(), nullable=True),
        sa.Column("POSPType_Id", sa.Integer(), nullable=True),
        sa.Column("POSP_Id", sa.Integer(), nullable=True),
        sa.Column("Ideal_Amount", sa.Numeric(precision=15, scale=2), nullable=False, server_default="0.00"),
        sa.Column("Ideal_NEFTNo", sa.String(length=100), nullable=True),
        sa.Column("PolicyNo", sa.String(length=255), nullable=True),
        sa.Column("TransactionId", sa.Integer(), nullable=True),
        sa.Column("ReceiptType", sa.String(length=50), nullable=False, server_default="Regular"),
        sa.Column("IsDelete", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("CreatedBy", sa.Integer(), nullable=True),
        sa.Column("CreateDate", sa.DateTime(), nullable=True, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("Id"),
        mysql_charset="utf8",
        mysql_collate="utf8_general_ci",
        mysql_row_format="DYNAMIC",
    )
    op.create_index("ix_tbl_idealpaymentreceipt_Ideal_Doc_No", "tbl_idealpaymentreceipt", ["Ideal_Doc_No"])
    op.create_index("ix_tbl_idealpaymentreceipt_POSP_Id", "tbl_idealpaymentreceipt", ["POSP_Id"])
    op.create_index("ix_tbl_idealpaymentreceipt_TransactionId", "tbl_idealpaymentreceipt", ["TransactionId"])

    # 2. tbl_commission_rate_grid (F-17B-086)
    op.create_table(
        "tbl_commission_rate_grid",
        sa.Column("GridId", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("GridScope", sa.String(length=50), nullable=False, server_default="BROKER"),
        sa.Column("InsuranceCompanyId", sa.Integer(), nullable=False),
        sa.Column("PolicyTypeId", sa.Integer(), nullable=True),
        sa.Column("ProductTypeId", sa.Integer(), nullable=True),
        sa.Column("VehiTypeId", sa.Integer(), nullable=True),
        sa.Column("VehiSubTypeId", sa.Integer(), nullable=True),
        sa.Column("FuelTypeId", sa.Integer(), nullable=True),
        sa.Column("MakeId", sa.Integer(), nullable=True),
        sa.Column("ModelId", sa.Integer(), nullable=True),
        sa.Column("RTO_Id", sa.Integer(), nullable=True),
        sa.Column("StateId", sa.Integer(), nullable=True),
        sa.Column("ClusterMId", sa.Integer(), nullable=True),
        sa.Column("BrokerId", sa.Integer(), nullable=True),
        sa.Column("FranchiseId", sa.Integer(), nullable=True),
        sa.Column("AgentId", sa.Integer(), nullable=True),
        sa.Column("Commission_OD", sa.Numeric(precision=10, scale=2), nullable=False, server_default="0.00"),
        sa.Column("Commission_Net", sa.Numeric(precision=10, scale=2), nullable=False, server_default="0.00"),
        sa.Column("Commission_TP", sa.Numeric(precision=10, scale=2), nullable=False, server_default="0.00"),
        sa.Column("OD_Discount", sa.Numeric(precision=10, scale=2), nullable=False, server_default="0.00"),
        sa.Column("CalOn", sa.String(length=50), nullable=False, server_default="OD"),
        sa.Column("ValidFromDate", sa.Date(), nullable=True),
        sa.Column("ValidToDate", sa.Date(), nullable=True),
        sa.Column("isdeleted", sa.String(length=10), nullable=False, server_default="0"),
        sa.Column("CreateUser", sa.Integer(), nullable=True),
        sa.Column("Createdate", sa.DateTime(), nullable=True, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("GridId"),
        mysql_charset="utf8",
        mysql_collate="utf8_general_ci",
        mysql_row_format="DYNAMIC",
    )
    op.create_index("ix_tbl_commission_rate_grid_InsComp", "tbl_commission_rate_grid", ["InsuranceCompanyId"])
    op.create_index("ix_tbl_commission_rate_grid_VehiType", "tbl_commission_rate_grid", ["VehiTypeId"])
    op.create_index("ix_tbl_commission_rate_grid_BrokerId", "tbl_commission_rate_grid", ["BrokerId"])
    op.create_index("ix_tbl_commission_rate_grid_FranchiseId", "tbl_commission_rate_grid", ["FranchiseId"])
    op.create_index("ix_tbl_commission_rate_grid_AgentId", "tbl_commission_rate_grid", ["AgentId"])

    # 3. tbl_remainingpendingcash (F-17B-087)
    op.create_table(
        "tbl_remainingpendingcash",
        sa.Column("PendingCashId", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("TransactionIdsCsv", sa.String(length=500), nullable=True),
        sa.Column("TotalPremium", sa.Numeric(precision=15, scale=2), nullable=False, server_default="0.00"),
        sa.Column("PaidPremium", sa.Numeric(precision=15, scale=2), nullable=False, server_default="0.00"),
        sa.Column("RemainingPremium", sa.Numeric(precision=15, scale=2), nullable=False, server_default="0.00"),
        sa.Column("ShortfallAmt", sa.Numeric(precision=15, scale=2), nullable=False, server_default="0.00"),
        sa.Column("RemainingStatus", sa.String(length=50), nullable=False, server_default="Short Fall"),
        sa.Column("UserRoleId", sa.Integer(), nullable=True),
        sa.Column("AgentId", sa.Integer(), nullable=True),
        sa.Column("ExecutiveId", sa.Integer(), nullable=True),
        sa.Column("BranchId", sa.Integer(), nullable=True),
        sa.Column("SupportingFileKey", sa.String(length=255), nullable=True),
        sa.Column("CashierApproval", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ApprovedBy", sa.Integer(), nullable=True),
        sa.Column("ApprovedDate", sa.DateTime(), nullable=True),
        sa.Column("Remark", sa.String(length=500), nullable=True),
        sa.Column("CreateUser", sa.Integer(), nullable=True),
        sa.Column("CreateDate", sa.DateTime(), nullable=True, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("PendingCashId"),
        mysql_charset="utf8",
        mysql_collate="utf8_general_ci",
        mysql_row_format="DYNAMIC",
    )
    op.create_index("ix_tbl_remainingpendingcash_AgentId", "tbl_remainingpendingcash", ["AgentId"])
    op.create_index("ix_tbl_remainingpendingcash_ExecutiveId", "tbl_remainingpendingcash", ["ExecutiveId"])
    op.create_index("ix_tbl_remainingpendingcash_BranchId", "tbl_remainingpendingcash", ["BranchId"])
    op.create_index("ix_tbl_remainingpendingcash_CashierApproval", "tbl_remainingpendingcash", ["CashierApproval"])

    # 4. tbl_salesregistration (F-17B-088)
    op.create_table(
        "tbl_salesregistration",
        sa.Column("salesRegId", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("InvoiceNo", sa.String(length=100), nullable=False),
        sa.Column("RegistrationType", sa.String(length=100), nullable=True),
        sa.Column("SalesDate", sa.Date(), nullable=False),
        sa.Column("RCompanyId", sa.Integer(), nullable=True),
        sa.Column("SalesTypeId", sa.Integer(), nullable=True),
        sa.Column("SalesType", sa.String(length=100), nullable=True),
        sa.Column("ClientMasterId", sa.Integer(), nullable=False),
        sa.Column("LedgerMId", sa.Integer(), nullable=True),
        sa.Column("Description", sa.String(length=500), nullable=True),
        sa.Column("amount", sa.Numeric(precision=15, scale=2), nullable=False, server_default="0.00"),
        sa.Column("CGSTPer", sa.Numeric(precision=6, scale=2), nullable=False, server_default="0.00"),
        sa.Column("CGSTAmt", sa.Numeric(precision=15, scale=2), nullable=False, server_default="0.00"),
        sa.Column("SGSTPer", sa.Numeric(precision=6, scale=2), nullable=False, server_default="0.00"),
        sa.Column("SGSTAmt", sa.Numeric(precision=15, scale=2), nullable=False, server_default="0.00"),
        sa.Column("IGSTPer", sa.Numeric(precision=6, scale=2), nullable=False, server_default="0.00"),
        sa.Column("IGSTAmt", sa.Numeric(precision=15, scale=2), nullable=False, server_default="0.00"),
        sa.Column("Total", sa.Numeric(precision=15, scale=2), nullable=False, server_default="0.00"),
        sa.Column("ReceivedAmt", sa.Numeric(precision=15, scale=2), nullable=False, server_default="0.00"),
        sa.Column("BalanceAmt", sa.Numeric(precision=15, scale=2), nullable=False, server_default="0.00"),
        sa.Column("AccDocNo", sa.String(length=100), nullable=True),
        sa.Column("CreatedUser", sa.Integer(), nullable=True),
        sa.Column("Createdate", sa.DateTime(), nullable=True, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("salesRegId"),
        mysql_charset="utf8",
        mysql_collate="utf8_general_ci",
        mysql_row_format="DYNAMIC",
    )
    op.create_index("ix_tbl_salesregistration_InvoiceNo", "tbl_salesregistration", ["InvoiceNo"])
    op.create_index("ix_tbl_salesregistration_ClientMasterId", "tbl_salesregistration", ["ClientMasterId"])
    op.create_index("ix_tbl_salesregistration_LedgerMId", "tbl_salesregistration", ["LedgerMId"])

    # 5. tbl_inspectionrequest (F-17B-091)
    op.create_table(
        "tbl_inspectionrequest",
        sa.Column("InspectionId", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("TransId", sa.Integer(), nullable=True),
        sa.Column("RegistrationNo", sa.String(length=50), nullable=False),
        sa.Column("CustomerName", sa.String(length=255), nullable=True),
        sa.Column("MobileNo", sa.String(length=50), nullable=True),
        sa.Column("InsuranceCompanyId", sa.Integer(), nullable=True),
        sa.Column("VehicleTypeId", sa.Integer(), nullable=True),
        sa.Column("BranchId", sa.Integer(), nullable=True),
        sa.Column("FranchiseId", sa.Integer(), nullable=True),
        sa.Column("AgentId", sa.Integer(), nullable=True),
        sa.Column("ExecutiveId", sa.Integer(), nullable=True),
        sa.Column("LeadNo", sa.String(length=100), nullable=True),
        sa.Column("InspectionStatus", sa.String(length=50), nullable=False, server_default="PENDING"),
        sa.Column("IsOwner", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("InspectionPdfPath", sa.String(length=255), nullable=True),
        sa.Column("ImagePathsJson", sa.Text(), nullable=True),
        sa.Column("Remark", sa.String(length=500), nullable=True),
        sa.Column("CreateUser", sa.Integer(), nullable=True),
        sa.Column("CreatedDate", sa.DateTime(), nullable=True, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("UpdatedBy", sa.Integer(), nullable=True),
        sa.Column("UpdatedDate", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("InspectionId"),
        mysql_charset="utf8",
        mysql_collate="utf8_general_ci",
        mysql_row_format="DYNAMIC",
    )
    op.create_index("ix_tbl_inspectionrequest_TransId", "tbl_inspectionrequest", ["TransId"])
    op.create_index("ix_tbl_inspectionrequest_RegistrationNo", "tbl_inspectionrequest", ["RegistrationNo"])
    op.create_index("ix_tbl_inspectionrequest_BranchId", "tbl_inspectionrequest", ["BranchId"])
    op.create_index("ix_tbl_inspectionrequest_FranchiseId", "tbl_inspectionrequest", ["FranchiseId"])
    op.create_index("ix_tbl_inspectionrequest_AgentId", "tbl_inspectionrequest", ["AgentId"])
    op.create_index("ix_tbl_inspectionrequest_InspectionStatus", "tbl_inspectionrequest", ["InspectionStatus"])

    # 6. tbl_supportapp (F-17B-092)
    op.create_table(
        "tbl_supportapp",
        sa.Column("SupportId", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("SupportTypeId", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("SupportType", sa.String(length=100), nullable=False, server_default="GENERAL"),
        sa.Column("SupportDate", sa.DateTime(), nullable=True, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("UserId", sa.Integer(), nullable=False),
        sa.Column("UserRoleId", sa.Integer(), nullable=True),
        sa.Column("BranchId", sa.Integer(), nullable=True),
        sa.Column("Remark", sa.Text(), nullable=False),
        sa.Column("RemarkFrom", sa.String(length=50), nullable=True),
        sa.Column("RemarksThreadJson", sa.Text(), nullable=True),
        sa.Column("AttachmentFileName", sa.String(length=255), nullable=True),
        sa.Column("AttendBy", sa.Integer(), nullable=True),
        sa.Column("Status", sa.String(length=50), nullable=False, server_default="OPEN"),
        sa.Column("isApproved", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ApprovedBy", sa.Integer(), nullable=True),
        sa.Column("ApprovedDate", sa.DateTime(), nullable=True),
        sa.Column("UpdateBy", sa.Integer(), nullable=True),
        sa.Column("UpdateDate", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("SupportId"),
        mysql_charset="utf8",
        mysql_collate="utf8_general_ci",
        mysql_row_format="DYNAMIC",
    )
    op.create_index("ix_tbl_supportapp_UserId", "tbl_supportapp", ["UserId"])
    op.create_index("ix_tbl_supportapp_BranchId", "tbl_supportapp", ["BranchId"])
    op.create_index("ix_tbl_supportapp_Status", "tbl_supportapp", ["Status"])

    # 7. tbl_callingimportdata (F-17B-093 / F-17B-098)
    op.create_table(
        "tbl_callingimportdata",
        sa.Column("CallingImportId", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("RegistrationNo", sa.String(length=50), nullable=False),
        sa.Column("RegistrationType", sa.String(length=100), nullable=True),
        sa.Column("RegnDate", sa.Date(), nullable=True),
        sa.Column("OwnerName", sa.String(length=255), nullable=True),
        sa.Column("FatherName", sa.String(length=255), nullable=True),
        sa.Column("PermanentAddress", sa.String(length=500), nullable=True),
        sa.Column("ChassisNo", sa.String(length=100), nullable=True),
        sa.Column("EngNo", sa.String(length=100), nullable=True),
        sa.Column("VehicleClass", sa.String(length=100), nullable=True),
        sa.Column("MakerModel", sa.String(length=255), nullable=True),
        sa.Column("DealerName", sa.String(length=255), nullable=True),
        sa.Column("MobileNo", sa.String(length=50), nullable=True),
        sa.Column("UserId", sa.Integer(), nullable=True),
        sa.Column("BranchId", sa.Integer(), nullable=True),
        sa.Column("CallingStatusId", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("CallingStatusName", sa.String(length=100), nullable=True, server_default="NEW"),
        sa.Column("CallingDate", sa.DateTime(), nullable=True),
        sa.Column("FollowUpDate", sa.Date(), nullable=True),
        sa.Column("Note", sa.String(length=500), nullable=True),
        sa.Column("HistoryJson", sa.Text(), nullable=True),
        sa.Column("Latitude", sa.String(length=50), nullable=True),
        sa.Column("Longitude", sa.String(length=50), nullable=True),
        sa.Column("GPSLocation", sa.String(length=500), nullable=True),
        sa.Column("CreateUser", sa.Integer(), nullable=True),
        sa.Column("Createdate", sa.DateTime(), nullable=True, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("CallingImportId"),
        mysql_charset="utf8",
        mysql_collate="utf8_general_ci",
        mysql_row_format="DYNAMIC",
    )
    op.create_index("ix_tbl_callingimportdata_RegistrationNo", "tbl_callingimportdata", ["RegistrationNo"])
    op.create_index("ix_tbl_callingimportdata_MobileNo", "tbl_callingimportdata", ["MobileNo"])
    op.create_index("ix_tbl_callingimportdata_UserId", "tbl_callingimportdata", ["UserId"])
    op.create_index("ix_tbl_callingimportdata_BranchId", "tbl_callingimportdata", ["BranchId"])
    op.create_index("ix_tbl_callingimportdata_FollowUpDate", "tbl_callingimportdata", ["FollowUpDate"])

    # 8. tbl_cashback (F-17B-095)
    op.create_table(
        "tbl_cashback",
        sa.Column("cashbackId", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("TransactionId", sa.Integer(), nullable=False),
        sa.Column("CustomerId", sa.Integer(), nullable=True),
        sa.Column("CustVehId", sa.Integer(), nullable=True),
        sa.Column("AgentId", sa.Integer(), nullable=True),
        sa.Column("BranchId", sa.Integer(), nullable=True),
        sa.Column("cashbackamount", sa.Numeric(precision=15, scale=2), nullable=False, server_default="0.00"),
        sa.Column("TransDate", sa.Date(), nullable=False),
        sa.Column("narration", sa.String(length=500), nullable=True),
        sa.Column("Status", sa.String(length=50), nullable=False, server_default="APPROVED"),
        sa.Column("CreatedUser", sa.Integer(), nullable=True),
        sa.Column("CreatedDate", sa.DateTime(), nullable=True, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("cashbackId"),
        mysql_charset="utf8",
        mysql_collate="utf8_general_ci",
        mysql_row_format="DYNAMIC",
    )
    op.create_index("ix_tbl_cashback_TransactionId", "tbl_cashback", ["TransactionId"])
    op.create_index("ix_tbl_cashback_CustomerId", "tbl_cashback", ["CustomerId"])
    op.create_index("ix_tbl_cashback_AgentId", "tbl_cashback", ["AgentId"])
    op.create_index("ix_tbl_cashback_BranchId", "tbl_cashback", ["BranchId"])

    # 9. Add Sub-Agent columns to tbl_agent (F-17B-097)
    op.add_column("tbl_agent", sa.Column("ParentAgentId", sa.Integer(), nullable=True))
    op.add_column(
        "tbl_agent",
        sa.Column("SubAgentSplitPercent", sa.Numeric(precision=6, scale=2), nullable=True, server_default="0.00"),
    )


def downgrade() -> None:
    op.drop_column("tbl_agent", "SubAgentSplitPercent")
    op.drop_column("tbl_agent", "ParentAgentId")
    op.drop_table("tbl_cashback")
    op.drop_table("tbl_callingimportdata")
    op.drop_table("tbl_supportapp")
    op.drop_table("tbl_inspectionrequest")
    op.drop_table("tbl_salesregistration")
    op.drop_table("tbl_remainingpendingcash")
    op.drop_table("tbl_commission_rate_grid")
    op.drop_table("tbl_idealpaymentreceipt")
