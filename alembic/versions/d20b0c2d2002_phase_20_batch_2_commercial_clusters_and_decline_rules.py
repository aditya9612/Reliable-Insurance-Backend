"""phase_20_batch_2_commercial_clusters_and_decline_rules

Revision ID: d20b0c2d2002
Revises: c20a0b1c2001
Create Date: 2026-10-12 12:15:00.000000+00:00

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d20b0c2d2002"
down_revision: Union[str, None] = "c20a0b1c2001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. tbl_clustermaster (F-20-005)
    op.create_table(
        "tbl_clustermaster",
        sa.Column("ClusterMId", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("InsuranceCompanyId", sa.Integer(), nullable=False),
        sa.Column("ClusterName", sa.String(length=255), nullable=False),
        sa.Column("StateId", sa.Integer(), nullable=False),
        sa.Column("CreateUser", sa.Integer(), nullable=True),
        sa.Column("CreateDate", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("isdeleted", sa.Integer(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("ClusterMId"),
        mysql_charset="utf8",
        mysql_collate="utf8_general_ci",
        mysql_row_format="DYNAMIC",
    )
    op.create_index(
        "ix_tbl_clustermaster_Company_State",
        "tbl_clustermaster",
        ["InsuranceCompanyId", "StateId"],
    )

    # 2. tbl_clusterdetails (F-20-005)
    op.create_table(
        "tbl_clusterdetails",
        sa.Column("ClusterDId", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("ClusterMId", sa.Integer(), nullable=False),
        sa.Column("InsuranceCompanyId", sa.Integer(), nullable=False),
        sa.Column("RtoId", sa.Integer(), nullable=False),
        sa.Column("CreateUser", sa.Integer(), nullable=True),
        sa.Column("CreateDate", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("ClusterDId"),
        mysql_charset="utf8",
        mysql_collate="utf8_general_ci",
        mysql_row_format="DYNAMIC",
    )
    op.create_index("ix_tbl_clusterdetails_ClusterMId", "tbl_clusterdetails", ["ClusterMId"])
    op.create_index("ix_tbl_clusterdetails_RtoId", "tbl_clusterdetails", ["RtoId"])

    # 3. tbl_clusterwisebrokergrid (F-20-005)
    op.create_table(
        "tbl_clusterwisebrokergrid",
        sa.Column("GridId", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("GridValue", sa.Numeric(precision=12, scale=2), nullable=False, server_default="0.00"),
        sa.Column("CalOn", sa.String(length=50), nullable=True),
        sa.Column("ODDiscount", sa.Numeric(precision=12, scale=2), nullable=False, server_default="0.00"),
        sa.Column("ValidFrom", sa.Date(), nullable=False),
        sa.Column("ReferenceType", sa.String(length=50), nullable=True),
        sa.Column("BrokerId", sa.Integer(), nullable=False),
        sa.Column("InsuranceCompanyId", sa.Integer(), nullable=False),
        sa.Column("Veh_Type_ID", sa.Integer(), nullable=False),
        sa.Column("StateId", sa.Integer(), nullable=False),
        sa.Column("FuelTypeId", sa.Integer(), nullable=True),
        sa.Column("ProductTypeId", sa.Integer(), nullable=True),
        sa.Column("PolicyTypeId", sa.Integer(), nullable=True),
        sa.Column("ClusterMId", sa.Integer(), nullable=False),
        sa.Column("CreatedUser", sa.Integer(), nullable=True),
        sa.Column("CreatedDate", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("UpdatedUser", sa.Integer(), nullable=True),
        sa.Column("UpdatedDate", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("GridId"),
        mysql_charset="utf8",
        mysql_collate="utf8_general_ci",
        mysql_row_format="DYNAMIC",
    )
    op.create_index(
        "ix_tbl_cwbg_Broker_Company",
        "tbl_clusterwisebrokergrid",
        ["BrokerId", "InsuranceCompanyId"],
    )
    op.create_index(
        "ix_tbl_cwbg_ClusterMId",
        "tbl_clusterwisebrokergrid",
        ["ClusterMId"],
    )

    # 4. tbl_clusterwiseagentgrid (F-20-005)
    op.create_table(
        "tbl_clusterwiseagentgrid",
        sa.Column("GridId", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("GridValue", sa.Numeric(precision=12, scale=2), nullable=False, server_default="0.00"),
        sa.Column("CalOn", sa.String(length=50), nullable=True),
        sa.Column("ODDiscount", sa.Numeric(precision=12, scale=2), nullable=False, server_default="0.00"),
        sa.Column("ValidFrom", sa.Date(), nullable=False),
        sa.Column("ReferenceType", sa.String(length=50), nullable=True),
        sa.Column("AgentId", sa.Integer(), nullable=False),
        sa.Column("BrokerId", sa.Integer(), nullable=True),
        sa.Column("InsuranceCompanyId", sa.Integer(), nullable=False),
        sa.Column("Veh_Type_ID", sa.Integer(), nullable=False),
        sa.Column("StateId", sa.Integer(), nullable=False),
        sa.Column("FuelTypeId", sa.Integer(), nullable=True),
        sa.Column("ProductTypeId", sa.Integer(), nullable=True),
        sa.Column("PolicyTypeId", sa.Integer(), nullable=True),
        sa.Column("ClusterMId", sa.Integer(), nullable=False),
        sa.Column("CreatedUser", sa.Integer(), nullable=True),
        sa.Column("CreatedDate", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("UpdatedUser", sa.Integer(), nullable=True),
        sa.Column("UpdatedDate", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("GridId"),
        mysql_charset="utf8",
        mysql_collate="utf8_general_ci",
        mysql_row_format="DYNAMIC",
    )
    op.create_index(
        "ix_tbl_cwag_Agent_Company",
        "tbl_clusterwiseagentgrid",
        ["AgentId", "InsuranceCompanyId"],
    )
    op.create_index(
        "ix_tbl_cwag_ClusterMId",
        "tbl_clusterwiseagentgrid",
        ["ClusterMId"],
    )

    # 5. tbl_griddecline (F-20-006)
    op.create_table(
        "tbl_griddecline",
        sa.Column("DeclineId", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("DeclineDate", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("InsuranceCompanyId", sa.Integer(), nullable=False),
        sa.Column("MakeId", sa.Integer(), nullable=False),
        sa.Column("PolicyTypeId", sa.Integer(), nullable=False),
        sa.Column("ModelId", sa.Integer(), nullable=True),
        sa.Column("RtoId", sa.Integer(), nullable=True),
        sa.Column("ProductTypeId", sa.Integer(), nullable=False),
        sa.Column("FuelTypeId", sa.Integer(), nullable=True),
        sa.Column("Guide_line", sa.String(length=1000), nullable=True),
        sa.Column("active", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("CreatedUser", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("DeclineId"),
        mysql_charset="utf8",
        mysql_collate="utf8_general_ci",
        mysql_row_format="DYNAMIC",
    )
    op.create_index(
        "ix_tbl_griddecline_Company_Policy",
        "tbl_griddecline",
        ["InsuranceCompanyId", "PolicyTypeId"],
    )
    op.create_index(
        "ix_tbl_griddecline_Make_Model",
        "tbl_griddecline",
        ["MakeId", "ModelId"],
    )

    # 6. tbl_declinemodel (F-20-006)
    op.create_table(
        "tbl_declinemodel",
        sa.Column("Id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("DeclineId", sa.Integer(), nullable=True),
        sa.Column("MakeId", sa.Integer(), nullable=False),
        sa.Column("ModelId", sa.Integer(), nullable=False),
        sa.Column("InsuranceCompanyId", sa.Integer(), nullable=False),
        sa.Column("PolicyTypeId", sa.Integer(), nullable=False),
        sa.Column("ProductTypeId", sa.Integer(), nullable=False),
        sa.Column("RtoId", sa.Integer(), nullable=True),
        sa.Column("FuelTypeId", sa.Integer(), nullable=True),
        sa.Column("Remark", sa.String(length=500), nullable=True),
        sa.Column("CreatedDate", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("CreatedBy", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("Id"),
        mysql_charset="utf8",
        mysql_collate="utf8_general_ci",
        mysql_row_format="DYNAMIC",
    )
    op.create_index("ix_tbl_declinemodel_DeclineId", "tbl_declinemodel", ["DeclineId"])
    op.create_index(
        "ix_tbl_declinemodel_Lookup",
        "tbl_declinemodel",
        ["InsuranceCompanyId", "MakeId", "ModelId"],
    )


def downgrade() -> None:
    op.drop_index("ix_tbl_declinemodel_Lookup", table_name="tbl_declinemodel")
    op.drop_index("ix_tbl_declinemodel_DeclineId", table_name="tbl_declinemodel")
    op.drop_table("tbl_declinemodel")

    op.drop_index("ix_tbl_griddecline_Make_Model", table_name="tbl_griddecline")
    op.drop_index("ix_tbl_griddecline_Company_Policy", table_name="tbl_griddecline")
    op.drop_table("tbl_griddecline")

    op.drop_index("ix_tbl_cwag_ClusterMId", table_name="tbl_clusterwiseagentgrid")
    op.drop_index("ix_tbl_cwag_Agent_Company", table_name="tbl_clusterwiseagentgrid")
    op.drop_table("tbl_clusterwiseagentgrid")

    op.drop_index("ix_tbl_cwbg_ClusterMId", table_name="tbl_clusterwisebrokergrid")
    op.drop_index("ix_tbl_cwbg_Broker_Company", table_name="tbl_clusterwisebrokergrid")
    op.drop_table("tbl_clusterwisebrokergrid")

    op.drop_index("ix_tbl_clusterdetails_RtoId", table_name="tbl_clusterdetails")
    op.drop_index("ix_tbl_clusterdetails_ClusterMId", table_name="tbl_clusterdetails")
    op.drop_table("tbl_clusterdetails")

    op.drop_index("ix_tbl_clustermaster_Company_State", table_name="tbl_clustermaster")
    op.drop_table("tbl_clustermaster")
