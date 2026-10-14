"""phase_25_commercial_sales_and_advances

Revision ID: i25a0c7d2501
Revises: h24a0c6d2401
Create Date: 2026-10-13 15:00:00.000000+00:00

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "i25a0c7d2501"
down_revision: Union[str, None] = "h24a0c6d2401"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. tbl_salestype (Commercial Sales Classification Master)
    op.create_table(
        "tbl_salestype",
        sa.Column("SalesTypeId", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("Description", sa.String(length=255), nullable=False),
        sa.Column("IsActive", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("CreatedDate", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("SalesTypeId"),
        mysql_charset="utf8",
        mysql_collate="utf8_general_ci",
        mysql_row_format="DYNAMIC",
    )
    op.create_index("ix_tbl_salestype_Description", "tbl_salestype", ["Description"])

    # 2. tbl_reliablecompanymst (Reliable Sister Group Companies & Invoicing Prefixes)
    op.create_table(
        "tbl_reliablecompanymst",
        sa.Column("RCompanyId", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("RCompany", sa.String(length=255), nullable=False),
        sa.Column("Prefix", sa.String(length=50), nullable=False),
        sa.Column("LedgerMId", sa.Integer(), nullable=True),
        sa.Column("IsActive", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("CreatedDate", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("RCompanyId"),
        mysql_charset="utf8",
        mysql_collate="utf8_general_ci",
        mysql_row_format="DYNAMIC",
    )
    op.create_index("ix_tbl_reliablecompanymst_Prefix", "tbl_reliablecompanymst", ["Prefix"])

    # 3. tbl_clientmaster (Corporate Group Client Registry)
    op.create_table(
        "tbl_clientmaster",
        sa.Column("ClientMasterId", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("Description", sa.String(length=255), nullable=False),
        sa.Column("InsuranceCompanyId", sa.Integer(), nullable=True),
        sa.Column("Address", sa.String(length=500), nullable=True),
        sa.Column("PanNo", sa.String(length=20), nullable=True),
        sa.Column("GST", sa.String(length=50), nullable=True),
        sa.Column("CGST", sa.Numeric(precision=6, scale=2), nullable=False, server_default=sa.text("0.00")),
        sa.Column("SGST", sa.Numeric(precision=6, scale=2), nullable=False, server_default=sa.text("0.00")),
        sa.Column("IGST", sa.Numeric(precision=6, scale=2), nullable=False, server_default=sa.text("0.00")),
        sa.Column("IsActive", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("CreatedUser", sa.String(length=100), nullable=True),
        sa.Column("Createdate", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("ClientMasterId"),
        mysql_charset="utf8",
        mysql_collate="utf8_general_ci",
        mysql_row_format="DYNAMIC",
    )
    op.create_index("ix_tbl_clientmaster_Description", "tbl_clientmaster", ["Description"])
    op.create_index("ix_tbl_clientmaster_GST", "tbl_clientmaster", ["GST"])
    op.create_index("ix_tbl_clientmaster_PanNo", "tbl_clientmaster", ["PanNo"])

    # 4. tbl_salesregdetails (Multi-Line Commercial Invoicing Details)
    op.create_table(
        "tbl_salesregdetails",
        sa.Column("SalesRegDetailId", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("InvoiceId", sa.Integer(), nullable=False),
        sa.Column("InvoiceNo", sa.String(length=100), nullable=False),
        sa.Column("SalesType", sa.String(length=100), nullable=True),
        sa.Column("SalesTypeId", sa.Integer(), nullable=True),
        sa.Column("TaxableAmt", sa.Numeric(precision=15, scale=2), nullable=False, server_default=sa.text("0.00")),
        sa.Column("CGSTPre", sa.Numeric(precision=6, scale=2), nullable=False, server_default=sa.text("0.00")),
        sa.Column("CGSTAmt", sa.Numeric(precision=15, scale=2), nullable=False, server_default=sa.text("0.00")),
        sa.Column("SGSTPre", sa.Numeric(precision=6, scale=2), nullable=False, server_default=sa.text("0.00")),
        sa.Column("SGSTAmt", sa.Numeric(precision=15, scale=2), nullable=False, server_default=sa.text("0.00")),
        sa.Column("IGSTPre", sa.Numeric(precision=6, scale=2), nullable=False, server_default=sa.text("0.00")),
        sa.Column("IGSTAmt", sa.Numeric(precision=15, scale=2), nullable=False, server_default=sa.text("0.00")),
        sa.Column("Total", sa.Numeric(precision=15, scale=2), nullable=False, server_default=sa.text("0.00")),
        sa.PrimaryKeyConstraint("SalesRegDetailId"),
        mysql_charset="utf8",
        mysql_collate="utf8_general_ci",
        mysql_row_format="DYNAMIC",
    )
    op.create_index("ix_tbl_salesregdetails_InvoiceId", "tbl_salesregdetails", ["InvoiceId"])
    op.create_index("ix_tbl_salesregdetails_InvoiceNo", "tbl_salesregdetails", ["InvoiceNo"])

    # 5. tbl_companyadvancemaster (Sister Concern Advance Master)
    op.create_table(
        "tbl_companyadvancemaster",
        sa.Column("CompanyAdvId", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("LedgerMID", sa.Integer(), nullable=False),
        sa.Column("compAdvDate", sa.Date(), nullable=False),
        sa.Column("Amount", sa.Numeric(precision=15, scale=2), nullable=False, server_default=sa.text("0.00")),
        sa.Column("RecivingAmount", sa.Numeric(precision=15, scale=2), nullable=False, server_default=sa.text("0.00")),
        sa.Column("BalanceAmt", sa.Numeric(precision=15, scale=2), nullable=False, server_default=sa.text("0.00")),
        sa.Column("Description", sa.String(length=500), nullable=True),
        sa.Column("CreatedUser", sa.String(length=100), nullable=True),
        sa.Column("CreatedDate", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("CompanyAdvId"),
        mysql_charset="utf8",
        mysql_collate="utf8_general_ci",
        mysql_row_format="DYNAMIC",
    )
    op.create_index("ix_tbl_companyadvancemaster_LedgerMID", "tbl_companyadvancemaster", ["LedgerMID"])

    # 6. tbl_companyadvdetails (Sister Concern Advance Recovery Log)
    op.create_table(
        "tbl_companyadvdetails",
        sa.Column("DetailId", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("CompanyAdvId", sa.Integer(), nullable=False),
        sa.Column("LedgerMID", sa.Integer(), nullable=False),
        sa.Column("HistoryDate", sa.Date(), nullable=False),
        sa.Column("SalesInvoiceId", sa.String(length=100), nullable=True),
        sa.Column("AccDocNo", sa.String(length=100), nullable=True),
        sa.Column("Amount", sa.Numeric(precision=15, scale=2), nullable=False, server_default=sa.text("0.00")),
        sa.Column("CreatedDate", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("DetailId"),
        mysql_charset="utf8",
        mysql_collate="utf8_general_ci",
        mysql_row_format="DYNAMIC",
    )
    op.create_index("ix_tbl_companyadvdetails_CompanyAdvId", "tbl_companyadvdetails", ["CompanyAdvId"])
    op.create_index("ix_tbl_companyadvdetails_LedgerMID", "tbl_companyadvdetails", ["LedgerMID"])
    op.create_index("ix_tbl_companyadvdetails_AccDocNo", "tbl_companyadvdetails", ["AccDocNo"])

    # 7. tbl_invoicesequence (Monotonic Commercial Invoicing Counter Generator)
    op.create_table(
        "tbl_invoicesequence",
        sa.Column("SequenceName", sa.String(length=50), nullable=False),
        sa.Column("CurrentValue", sa.Integer(), nullable=False, server_default=sa.text("1000")),
        sa.Column("UpdatedDate", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("SequenceName"),
        mysql_charset="utf8",
        mysql_collate="utf8_general_ci",
        mysql_row_format="DYNAMIC",
    )


def downgrade() -> None:
    op.drop_table("tbl_invoicesequence")
    op.drop_table("tbl_companyadvdetails")
    op.drop_table("tbl_companyadvancemaster")
    op.drop_table("tbl_salesregdetails")
    op.drop_table("tbl_clientmaster")
    op.drop_table("tbl_reliablecompanymst")
    op.drop_table("tbl_salestype")
