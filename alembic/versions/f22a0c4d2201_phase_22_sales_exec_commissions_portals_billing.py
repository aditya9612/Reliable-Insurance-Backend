"""phase_22_sales_exec_commissions_portals_billing

Revision ID: f22a0c4d2201
Revises: e21a0c3d2101
Create Date: 2026-10-12 14:00:00.000000+00:00

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f22a0c4d2201"
down_revision: Union[str, None] = "e21a0c3d2101"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. tbl_salesexcommission
    op.create_table(
        "tbl_salesexcommission",
        sa.Column("SalesCommissionId", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("SalesEx_Id", sa.Integer(), nullable=False),
        sa.Column("InsuranceCompanyId", sa.Integer(), nullable=False),
        sa.Column("PolicyType", sa.String(length=100), nullable=True),
        sa.Column("ProductType", sa.String(length=100), nullable=True),
        sa.Column("VehiTypeId", sa.Integer(), nullable=True),
        sa.Column("FuelTypeId", sa.Integer(), nullable=True),
        sa.Column("Commission", sa.Numeric(precision=10, scale=2), nullable=False, server_default="0.00"),
        sa.Column("Commission_OD", sa.Numeric(precision=10, scale=2), nullable=False, server_default="0.00"),
        sa.Column("Commission_Net", sa.Numeric(precision=10, scale=2), nullable=False, server_default="0.00"),
        sa.Column("CommissionCalculateOn", sa.String(length=50), nullable=True, server_default="'-'"),
        sa.Column("ReferenceType", sa.String(length=50), nullable=True, server_default="'Self'"),
        sa.Column("FlatRate", sa.String(length=50), nullable=True),
        sa.Column("OD_Discount", sa.Numeric(precision=10, scale=2), nullable=False, server_default="0.00"),
        sa.Column("FranchiseCode", sa.String(length=50), nullable=True, server_default="'RA'"),
        sa.Column("ncb", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("CCRange", sa.String(length=50), nullable=True),
        sa.Column("Slab", sa.String(length=50), nullable=True),
        sa.Column("ND", sa.String(length=50), nullable=True),
        sa.Column("MakeId", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("ModelId", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("RtoId", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("StateId", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("ValidFromDate", sa.Date(), nullable=False),
        sa.Column("ValidToDate", sa.Date(), nullable=True),
        sa.Column("CreateUser", sa.Integer(), nullable=True),
        sa.Column("CreateDate", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("UpdateUser", sa.Integer(), nullable=True),
        sa.Column("UpdateDate", sa.DateTime(), nullable=True),
        sa.Column("IsActive", sa.Integer(), nullable=False, server_default="1"),
        sa.PrimaryKeyConstraint("SalesCommissionId"),
        mysql_charset="utf8",
        mysql_collate="utf8_general_ci",
        mysql_row_format="DYNAMIC",
    )
    op.create_index("ix_tbl_salesexcomm_SalesEx_Id", "tbl_salesexcommission", ["SalesEx_Id"])
    op.create_index(
        "ix_tbl_salesexcomm_Company_Policy_Product",
        "tbl_salesexcommission",
        ["InsuranceCompanyId", "PolicyType", "ProductType"],
    )
    op.create_index("ix_tbl_salesexcomm_FranchiseCode", "tbl_salesexcommission", ["FranchiseCode"])
    op.create_index("ix_tbl_salesexcomm_ValidFromDate", "tbl_salesexcommission", ["ValidFromDate"])

    # 2. tbl_locationheadcommission
    op.create_table(
        "tbl_locationheadcommission",
        sa.Column("LocationHeadCommId", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("LocationHeadId", sa.Integer(), nullable=False),
        sa.Column("InsuranceCompanyId", sa.Integer(), nullable=False),
        sa.Column("PolicyType", sa.String(length=100), nullable=True),
        sa.Column("ProductType", sa.String(length=100), nullable=True),
        sa.Column("VehiTypeId", sa.Integer(), nullable=True),
        sa.Column("FuelTypeId", sa.Integer(), nullable=True),
        sa.Column("Commission", sa.Numeric(precision=10, scale=2), nullable=False, server_default="0.00"),
        sa.Column("Commission_OD", sa.Numeric(precision=10, scale=2), nullable=False, server_default="0.00"),
        sa.Column("Commission_Net", sa.Numeric(precision=10, scale=2), nullable=False, server_default="0.00"),
        sa.Column("OD_Discount", sa.Numeric(precision=10, scale=2), nullable=False, server_default="0.00"),
        sa.Column("FranchiseCode", sa.String(length=50), nullable=True, server_default="'RA'"),
        sa.Column("ReferenceType", sa.String(length=50), nullable=True, server_default="'L.Head'"),
        sa.Column("ValidFromDate", sa.Date(), nullable=False),
        sa.Column("ValidToDate", sa.Date(), nullable=True),
        sa.Column("CreateUser", sa.Integer(), nullable=True),
        sa.Column("CreateDate", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("UpdateUser", sa.Integer(), nullable=True),
        sa.Column("UpdateDate", sa.DateTime(), nullable=True),
        sa.Column("IsActive", sa.Integer(), nullable=False, server_default="1"),
        sa.PrimaryKeyConstraint("LocationHeadCommId"),
        mysql_charset="utf8",
        mysql_collate="utf8_general_ci",
        mysql_row_format="DYNAMIC",
    )
    op.create_index("ix_tbl_lochcomm_LocationHeadId", "tbl_locationheadcommission", ["LocationHeadId"])
    op.create_index(
        "ix_tbl_lochcomm_Company_Policy_Product",
        "tbl_locationheadcommission",
        ["InsuranceCompanyId", "PolicyType", "ProductType"],
    )
    op.create_index("ix_tbl_lochcomm_FranchiseCode", "tbl_locationheadcommission", ["FranchiseCode"])
    op.create_index("ix_tbl_lochcomm_ValidFromDate", "tbl_locationheadcommission", ["ValidFromDate"])

    # 3. tbl_locationheadsalesexmap
    op.create_table(
        "tbl_locationheadsalesexmap",
        sa.Column("MapId", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("LocationHeadId", sa.Integer(), nullable=False),
        sa.Column("SalesEx_Id", sa.Integer(), nullable=False),
        sa.Column("CreatedUser", sa.Integer(), nullable=True),
        sa.Column("CreatedDate", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("IsActive", sa.Integer(), nullable=False, server_default="1"),
        sa.PrimaryKeyConstraint("MapId"),
        mysql_charset="utf8",
        mysql_collate="utf8_general_ci",
        mysql_row_format="DYNAMIC",
    )
    op.create_index("ix_tbl_lhsemap_LocationHeadId", "tbl_locationheadsalesexmap", ["LocationHeadId"])
    op.create_index("ix_tbl_lhsemap_SalesEx_Id", "tbl_locationheadsalesexmap", ["SalesEx_Id"])

    # 4. tbl_insurancecompanyportal
    op.create_table(
        "tbl_insurancecompanyportal",
        sa.Column("tbl_Id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("InsuranceCompanyId", sa.Integer(), nullable=False),
        sa.Column("PortalId", sa.String(length=200), nullable=True),
        sa.Column("PersonName", sa.String(length=200), nullable=True),
        sa.Column("BrokerId", sa.Integer(), nullable=True),
        sa.Column("PortalUrl", sa.String(length=500), nullable=True),
        sa.Column("PortalPassword", sa.String(length=255), nullable=True),
        sa.Column("IsActive", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("CreatedUser", sa.Integer(), nullable=True),
        sa.Column("CreatedDate", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("UpdatedUser", sa.Integer(), nullable=True),
        sa.Column("UpdatedDate", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("tbl_Id"),
        mysql_charset="utf8",
        mysql_collate="utf8_general_ci",
        mysql_row_format="DYNAMIC",
    )
    op.create_index("ix_tbl_icp_InsuranceCompanyId", "tbl_insurancecompanyportal", ["InsuranceCompanyId"])
    op.create_index("ix_tbl_icp_BrokerId", "tbl_insurancecompanyportal", ["BrokerId"])

    # 5. tbl_appbillingdetails
    op.create_table(
        "tbl_appbillingdetails",
        sa.Column("BillingId", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("SalesExId", sa.Integer(), nullable=False),
        sa.Column("FromDate", sa.Date(), nullable=False),
        sa.Column("ToDate", sa.Date(), nullable=False),
        sa.Column("Remark", sa.Text(), nullable=True),
        sa.Column("BillingAmount", sa.Numeric(precision=12, scale=2), nullable=False, server_default="0.00"),
        sa.Column("ReimbursementTypeId", sa.Integer(), nullable=True),
        sa.Column("Destination", sa.String(length=255), nullable=True),
        sa.Column("Status", sa.String(length=50), nullable=False, server_default="'PENDING'"),
        sa.Column("CreatedDate", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("ProcessedDate", sa.DateTime(), nullable=True),
        sa.Column("ProcessedBy", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("BillingId"),
        mysql_charset="utf8",
        mysql_collate="utf8_general_ci",
        mysql_row_format="DYNAMIC",
    )
    op.create_index("ix_tbl_appbill_SalesExId", "tbl_appbillingdetails", ["SalesExId"])
    op.create_index("ix_tbl_appbill_Status", "tbl_appbillingdetails", ["Status"])
    op.create_index("ix_tbl_appbill_FromDate_ToDate", "tbl_appbillingdetails", ["FromDate", "ToDate"])

    # 6. tbl_appbillingattachment
    op.create_table(
        "tbl_appbillingattachment",
        sa.Column("AttachmentId", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("BillingId", sa.Integer(), nullable=False),
        sa.Column("FileType", sa.String(length=20), nullable=False),
        sa.Column("FilePath", sa.String(length=500), nullable=False),
        sa.Column("FileName", sa.String(length=255), nullable=True),
        sa.Column("UploadedDate", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("AttachmentId"),
        mysql_charset="utf8",
        mysql_collate="utf8_general_ci",
        mysql_row_format="DYNAMIC",
    )
    op.create_index("ix_tbl_appbillatt_BillingId", "tbl_appbillingattachment", ["BillingId"])
    op.create_index("ix_tbl_appbillatt_FileType", "tbl_appbillingattachment", ["FileType"])


def downgrade() -> None:
    op.drop_index("ix_tbl_appbillatt_FileType", table_name="tbl_appbillingattachment")
    op.drop_index("ix_tbl_appbillatt_BillingId", table_name="tbl_appbillingattachment")
    op.drop_table("tbl_appbillingattachment")

    op.drop_index("ix_tbl_appbill_FromDate_ToDate", table_name="tbl_appbillingdetails")
    op.drop_index("ix_tbl_appbill_Status", table_name="tbl_appbillingdetails")
    op.drop_index("ix_tbl_appbill_SalesExId", table_name="tbl_appbillingdetails")
    op.drop_table("tbl_appbillingdetails")

    op.drop_index("ix_tbl_icp_BrokerId", table_name="tbl_insurancecompanyportal")
    op.drop_index("ix_tbl_icp_InsuranceCompanyId", table_name="tbl_insurancecompanyportal")
    op.drop_table("tbl_insurancecompanyportal")

    op.drop_index("ix_tbl_lhsemap_SalesEx_Id", table_name="tbl_locationheadsalesexmap")
    op.drop_index("ix_tbl_lhsemap_LocationHeadId", table_name="tbl_locationheadsalesexmap")
    op.drop_table("tbl_locationheadsalesexmap")

    op.drop_index("ix_tbl_lochcomm_ValidFromDate", table_name="tbl_locationheadcommission")
    op.drop_index("ix_tbl_lochcomm_FranchiseCode", table_name="tbl_locationheadcommission")
    op.drop_index("ix_tbl_lochcomm_Company_Policy_Product", table_name="tbl_locationheadcommission")
    op.drop_index("ix_tbl_lochcomm_LocationHeadId", table_name="tbl_locationheadcommission")
    op.drop_table("tbl_locationheadcommission")

    op.drop_index("ix_tbl_salesexcomm_ValidFromDate", table_name="tbl_salesexcommission")
    op.drop_index("ix_tbl_salesexcomm_FranchiseCode", table_name="tbl_salesexcommission")
    op.drop_index("ix_tbl_salesexcomm_Company_Policy_Product", table_name="tbl_salesexcommission")
    op.drop_index("ix_tbl_salesexcomm_SalesEx_Id", table_name="tbl_salesexcommission")
    op.drop_table("tbl_salesexcommission")
