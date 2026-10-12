"""phase_21_nonmotor_insurance_operations

Revision ID: e21a0c3d2101
Revises: d20b0c2d2002
Create Date: 2026-10-12 13:15:00.000000+00:00

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e21a0c3d2101"
down_revision: Union[str, None] = "d20b0c2d2002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. tbl_nonmotorclass
    op.create_table(
        "tbl_nonmotorclass",
        sa.Column("ClassId", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("Class", sa.String(length=255), nullable=False),
        sa.Column("IsActive", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("CreatedDate", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("CreatedBy", sa.String(length=100), nullable=True),
        sa.Column("UpdatedDate", sa.DateTime(), nullable=True),
        sa.Column("UpdatedBy", sa.String(length=100), nullable=True),
        sa.PrimaryKeyConstraint("ClassId"),
        mysql_charset="utf8",
        mysql_collate="utf8_general_ci",
        mysql_row_format="DYNAMIC",
    )
    op.create_index("ix_tbl_nonmotorclass_Class", "tbl_nonmotorclass", ["Class"])
    op.create_index("ix_tbl_nonmotorclass_IsActive", "tbl_nonmotorclass", ["IsActive"])

    # 2. tbl_nonmotorproduct
    op.create_table(
        "tbl_nonmotorproduct",
        sa.Column("NonMotorProductId", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("ClassId", sa.Integer(), nullable=False),
        sa.Column("ProductType", sa.String(length=255), nullable=False),
        sa.Column("ProductCode", sa.String(length=100), nullable=True),
        sa.Column("IsActive", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("CreatedDate", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("CreatedBy", sa.String(length=100), nullable=True),
        sa.Column("UpdatedDate", sa.DateTime(), nullable=True),
        sa.Column("UpdatedBy", sa.String(length=100), nullable=True),
        sa.ForeignKeyConstraint(["ClassId"], ["tbl_nonmotorclass.ClassId"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("NonMotorProductId"),
        mysql_charset="utf8",
        mysql_collate="utf8_general_ci",
        mysql_row_format="DYNAMIC",
    )
    op.create_index("ix_tbl_nonmotorproduct_ClassId", "tbl_nonmotorproduct", ["ClassId"])
    op.create_index("ix_tbl_nonmotorproduct_ProductType", "tbl_nonmotorproduct", ["ProductType"])
    op.create_index("ix_tbl_nonmotorproduct_IsActive", "tbl_nonmotorproduct", ["IsActive"])

    # 3. tbl_nonmotorbusinesstype
    op.create_table(
        "tbl_nonmotorbusinesstype",
        sa.Column("NonBusinessId", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("BusinessType", sa.String(length=255), nullable=False),
        sa.Column("IsActive", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("CreatedDate", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("CreatedBy", sa.String(length=100), nullable=True),
        sa.Column("UpdatedDate", sa.DateTime(), nullable=True),
        sa.Column("UpdatedBy", sa.String(length=100), nullable=True),
        sa.PrimaryKeyConstraint("NonBusinessId"),
        mysql_charset="utf8",
        mysql_collate="utf8_general_ci",
        mysql_row_format="DYNAMIC",
    )
    op.create_index("ix_tbl_nonmotorbusinesstype_BusinessType", "tbl_nonmotorbusinesstype", ["BusinessType"])
    op.create_index("ix_tbl_nonmotorbusinesstype_IsActive", "tbl_nonmotorbusinesstype", ["IsActive"])

    # 4. tbl_nonmotordocumenttype
    op.create_table(
        "tbl_nonmotordocumenttype",
        sa.Column("NonDocumentTypeId", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("DocumentType", sa.String(length=255), nullable=False),
        sa.Column("IsActive", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("CreatedDate", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("CreatedBy", sa.String(length=100), nullable=True),
        sa.Column("UpdatedDate", sa.DateTime(), nullable=True),
        sa.Column("UpdatedBy", sa.String(length=100), nullable=True),
        sa.PrimaryKeyConstraint("NonDocumentTypeId"),
        mysql_charset="utf8",
        mysql_collate="utf8_general_ci",
        mysql_row_format="DYNAMIC",
    )
    op.create_index("ix_tbl_nonmotordocumenttype_DocumentType", "tbl_nonmotordocumenttype", ["DocumentType"])
    op.create_index("ix_tbl_nonmotordocumenttype_IsActive", "tbl_nonmotordocumenttype", ["IsActive"])

    # 5. tbl_nonmotorendorsmenttype
    op.create_table(
        "tbl_nonmotorendorsmenttype",
        sa.Column("NonEndorsementId", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("EndorsementType", sa.String(length=255), nullable=False),
        sa.Column("IsActive", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("CreatedDate", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("CreatedBy", sa.String(length=100), nullable=True),
        sa.Column("UpdatedDate", sa.DateTime(), nullable=True),
        sa.Column("UpdatedBy", sa.String(length=100), nullable=True),
        sa.PrimaryKeyConstraint("NonEndorsementId"),
        mysql_charset="utf8",
        mysql_collate="utf8_general_ci",
        mysql_row_format="DYNAMIC",
    )
    op.create_index("ix_tbl_nonmotorendorsmenttype_EndorsementType", "tbl_nonmotorendorsmenttype", ["EndorsementType"])
    op.create_index("ix_tbl_nonmotorendorsmenttype_IsActive", "tbl_nonmotorendorsmenttype", ["IsActive"])

    # 6. tbl_nonmotorendorsmentsubtype
    op.create_table(
        "tbl_nonmotorendorsmentsubtype",
        sa.Column("NonEndorsesubId", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("NonEndorsementId", sa.Integer(), nullable=False),
        sa.Column("EndorsementSubType", sa.String(length=255), nullable=False),
        sa.Column("IsActive", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("CreatedDate", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("CreatedBy", sa.String(length=100), nullable=True),
        sa.Column("UpdatedDate", sa.DateTime(), nullable=True),
        sa.Column("UpdatedBy", sa.String(length=100), nullable=True),
        sa.ForeignKeyConstraint(["NonEndorsementId"], ["tbl_nonmotorendorsmenttype.NonEndorsementId"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("NonEndorsesubId"),
        mysql_charset="utf8",
        mysql_collate="utf8_general_ci",
        mysql_row_format="DYNAMIC",
    )
    op.create_index("ix_tbl_nonmotorendorsmentsubtype_NonEndorsementId", "tbl_nonmotorendorsmentsubtype", ["NonEndorsementId"])
    op.create_index("ix_tbl_nonmotorendorsmentsubtype_EndorsementSubType", "tbl_nonmotorendorsmentsubtype", ["EndorsementSubType"])
    op.create_index("ix_tbl_nonmotorendorsmentsubtype_IsActive", "tbl_nonmotorendorsmentsubtype", ["IsActive"])

    # 7. tbl_nonmotorinsurancetype
    op.create_table(
        "tbl_nonmotorinsurancetype",
        sa.Column("InsuranceTypeId", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("InsuranceType", sa.String(length=255), nullable=False),
        sa.Column("InsuranceCompanyId", sa.Integer(), nullable=False),
        sa.Column("IsDeleted", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("Flag", sa.String(length=50), nullable=True),
        sa.Column("CreatedDate", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("CreatedBy", sa.String(length=100), nullable=True),
        sa.PrimaryKeyConstraint("InsuranceTypeId"),
        mysql_charset="utf8",
        mysql_collate="utf8_general_ci",
        mysql_row_format="DYNAMIC",
    )
    op.create_index("ix_tbl_nonmotorinsurancetype_CompanyId", "tbl_nonmotorinsurancetype", ["InsuranceCompanyId"])
    op.create_index("ix_tbl_nonmotorinsurancetype_Type", "tbl_nonmotorinsurancetype", ["InsuranceType"])
    op.create_index("ix_tbl_nonmotorinsurancetype_IsDeleted", "tbl_nonmotorinsurancetype", ["IsDeleted"])

    # 8. tbl_nonmotorinsurancesubtype
    op.create_table(
        "tbl_nonmotorinsurancesubtype",
        sa.Column("InsuranceSubTypeId", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("InsuranceSubType", sa.String(length=255), nullable=False),
        sa.Column("InsuranceTypeId", sa.Integer(), nullable=False),
        sa.Column("IsDeleted", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("Flag", sa.String(length=50), nullable=True),
        sa.Column("CreatedDate", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("CreatedBy", sa.String(length=100), nullable=True),
        sa.ForeignKeyConstraint(["InsuranceTypeId"], ["tbl_nonmotorinsurancetype.InsuranceTypeId"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("InsuranceSubTypeId"),
        mysql_charset="utf8",
        mysql_collate="utf8_general_ci",
        mysql_row_format="DYNAMIC",
    )
    op.create_index("ix_tbl_nonmotorinsurancesubtype_TypeId", "tbl_nonmotorinsurancesubtype", ["InsuranceTypeId"])
    op.create_index("ix_tbl_nonmotorinsurancesubtype_SubType", "tbl_nonmotorinsurancesubtype", ["InsuranceSubType"])
    op.create_index("ix_tbl_nonmotorinsurancesubtype_IsDeleted", "tbl_nonmotorinsurancesubtype", ["IsDeleted"])

    # 9. tbl_nonmotortypeofinsurancesubtype
    op.create_table(
        "tbl_nonmotortypeofinsurancesubtype",
        sa.Column("TypeSubTypeId", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("TypeOfSubType", sa.String(length=255), nullable=False),
        sa.Column("InsuranceTypeId", sa.Integer(), nullable=False),
        sa.Column("InsuranceSubTypeId", sa.Integer(), nullable=False),
        sa.Column("IsDeleted", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("Flag", sa.String(length=50), nullable=True),
        sa.Column("CreatedDate", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("CreatedBy", sa.String(length=100), nullable=True),
        sa.PrimaryKeyConstraint("TypeSubTypeId"),
        mysql_charset="utf8",
        mysql_collate="utf8_general_ci",
        mysql_row_format="DYNAMIC",
    )
    op.create_index("ix_tbl_nonmotortypeofsub_TypeId", "tbl_nonmotortypeofinsurancesubtype", ["InsuranceTypeId"])
    op.create_index("ix_tbl_nonmotortypeofsub_SubTypeId", "tbl_nonmotortypeofinsurancesubtype", ["InsuranceSubTypeId"])
    op.create_index("ix_tbl_nonmotortypeofsub_IsDeleted", "tbl_nonmotortypeofinsurancesubtype", ["IsDeleted"])

    # 10. tbl_nonmotorcommission
    op.create_table(
        "tbl_nonmotorcommission",
        sa.Column("NonMotorCommId", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("InsuranceCompanyId", sa.Integer(), nullable=False),
        sa.Column("InsuranceTypeId", sa.Integer(), nullable=False),
        sa.Column("InsuranceSubTypeId", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("TypeSubTypeId", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ReferanceId", sa.Integer(), nullable=False),
        sa.Column("ReferenceType", sa.String(length=50), nullable=False),
        sa.Column("Commission", sa.Numeric(precision=10, scale=2), nullable=False, server_default="0.00"),
        sa.Column("CommissionCalculateOn", sa.String(length=100), nullable=False, server_default="NetPremium"),
        sa.Column("ValidFromDate", sa.Date(), nullable=False),
        sa.Column("Extra1", sa.String(length=255), nullable=True),
        sa.Column("Extra2", sa.String(length=255), nullable=True),
        sa.Column("IsActive", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("CreateDate", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("CreateUser", sa.Integer(), nullable=True),
        sa.Column("UpdateDate", sa.DateTime(), nullable=True),
        sa.Column("UpdateUser", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("NonMotorCommId"),
        mysql_charset="utf8",
        mysql_collate="utf8_general_ci",
        mysql_row_format="DYNAMIC",
    )
    op.create_index("ix_tbl_nmcomm_company", "tbl_nonmotorcommission", ["InsuranceCompanyId"])
    op.create_index("ix_tbl_nmcomm_ref", "tbl_nonmotorcommission", ["ReferanceId", "ReferenceType"])
    op.create_index("ix_tbl_nmcomm_type_sub", "tbl_nonmotorcommission", ["InsuranceTypeId", "InsuranceSubTypeId"])
    op.create_index("ix_tbl_nmcomm_valid", "tbl_nonmotorcommission", ["ValidFromDate"])

    # 11. tbl_nonmotortransaction
    op.create_table(
        "tbl_nonmotortransaction",
        sa.Column("NonMotorTransactionId", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("InwardNo", sa.String(length=100), nullable=False),
        sa.Column("TransDate", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("BranchId", sa.Integer(), nullable=False),
        sa.Column("CustomerId", sa.Integer(), nullable=False),
        sa.Column("InsuranceCompanyId", sa.Integer(), nullable=False),
        sa.Column("CoverNote", sa.String(length=100), nullable=True),
        sa.Column("PreviousPolicyNo", sa.String(length=100), nullable=True),
        sa.Column("PolicyNo", sa.String(length=100), nullable=True),
        sa.Column("CnIssueDate", sa.DateTime(), nullable=True),
        sa.Column("ClassId", sa.Integer(), nullable=False),
        sa.Column("ProductTypeId", sa.Integer(), nullable=False),
        sa.Column("BusinessTypeId", sa.Integer(), nullable=False),
        sa.Column("NonDocumentTypeId", sa.Integer(), nullable=True),
        sa.Column("NonEndorsementId", sa.Integer(), nullable=True),
        sa.Column("NonEndorsesubId", sa.Integer(), nullable=True),
        sa.Column("EndorsementReason", sa.String(length=500), nullable=True),
        sa.Column("AgentId", sa.Integer(), nullable=False),
        sa.Column("SalesEx_id", sa.Integer(), nullable=True),
        sa.Column("RiskStartdate", sa.DateTime(), nullable=True),
        sa.Column("ExpiryDate", sa.DateTime(), nullable=True),
        sa.Column("SumInsured", sa.Numeric(precision=18, scale=2), nullable=False, server_default="0.00"),
        sa.Column("NetPermium", sa.Numeric(precision=18, scale=2), nullable=False, server_default="0.00"),
        sa.Column("ProPosalAmt", sa.Numeric(precision=18, scale=2), nullable=False, server_default="0.00"),
        sa.Column("Remark", sa.Text(), nullable=True),
        sa.Column("ReferenceType", sa.String(length=50), nullable=True),
        sa.Column("ReferenceBy", sa.String(length=100), nullable=True),
        sa.Column("ReferenceRole", sa.String(length=100), nullable=True),
        sa.Column("PersonName", sa.String(length=200), nullable=True),
        sa.Column("tat", sa.String(length=50), nullable=True),
        sa.Column("AgentComm", sa.Numeric(precision=10, scale=2), nullable=False, server_default="0.00"),
        sa.Column("AgentCommAmt", sa.Numeric(precision=18, scale=2), nullable=False, server_default="0.00"),
        sa.Column("TdsAmt", sa.Numeric(precision=18, scale=2), nullable=False, server_default="0.00"),
        sa.Column("NetCommission", sa.Numeric(precision=18, scale=2), nullable=False, server_default="0.00"),
        sa.Column("Amount", sa.Numeric(precision=18, scale=2), nullable=False, server_default="0.00"),
        sa.Column("TStatus", sa.String(length=50), nullable=False, server_default="Active"),
        sa.Column("CreateDate", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("CreateUser", sa.String(length=100), nullable=True),
        sa.Column("UpdateDate", sa.DateTime(), nullable=True),
        sa.Column("UpdateUser", sa.String(length=100), nullable=True),
        sa.PrimaryKeyConstraint("NonMotorTransactionId"),
        mysql_charset="utf8",
        mysql_collate="utf8_general_ci",
        mysql_row_format="DYNAMIC",
    )
    op.create_index("ix_tbl_nmtrans_inward", "tbl_nonmotortransaction", ["InwardNo"], unique=True)
    op.create_index("ix_tbl_nmtrans_branch", "tbl_nonmotortransaction", ["BranchId"])
    op.create_index("ix_tbl_nmtrans_customer", "tbl_nonmotortransaction", ["CustomerId"])
    op.create_index("ix_tbl_nmtrans_agent", "tbl_nonmotortransaction", ["AgentId"])
    op.create_index("ix_tbl_nmtrans_date", "tbl_nonmotortransaction", ["TransDate"])
    op.create_index("ix_tbl_nmtrans_policy", "tbl_nonmotortransaction", ["PolicyNo"])


def downgrade() -> None:
    op.drop_table("tbl_nonmotortransaction")
    op.drop_table("tbl_nonmotorcommission")
    op.drop_table("tbl_nonmotortypeofinsurancesubtype")
    op.drop_table("tbl_nonmotorinsurancesubtype")
    op.drop_table("tbl_nonmotorinsurancetype")
    op.drop_table("tbl_nonmotorendorsmentsubtype")
    op.drop_table("tbl_nonmotorendorsmenttype")
    op.drop_table("tbl_nonmotordocumenttype")
    op.drop_table("tbl_nonmotorbusinesstype")
    op.drop_table("tbl_nonmotorproduct")
    op.drop_table("tbl_nonmotorclass")
