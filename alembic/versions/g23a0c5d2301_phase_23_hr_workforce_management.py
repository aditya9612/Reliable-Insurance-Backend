"""phase_23_hr_workforce_management

Revision ID: g23a0c5d2301
Revises: f22a0c4d2201
Create Date: 2026-10-12 14:30:00.000000+00:00

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "g23a0c5d2301"
down_revision: Union[str, None] = "f22a0c4d2201"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. tbl_hrorganization
    op.create_table(
        "tbl_hrorganization",
        sa.Column("OrganizationId", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("OrganizationName", sa.String(length=255), nullable=False),
        sa.Column("Address", sa.String(length=500), nullable=True),
        sa.Column("MobileNo", sa.String(length=50), nullable=True),
        sa.Column("CreatedDate", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("CreateUser", sa.String(length=100), nullable=True),
        sa.Column("UpdateDate", sa.DateTime(), nullable=True),
        sa.Column("UpdatedUser", sa.String(length=100), nullable=True),
        sa.Column("IsActive", sa.Integer(), nullable=False, server_default="1"),
        sa.PrimaryKeyConstraint("OrganizationId"),
        mysql_charset="utf8",
        mysql_collate="utf8_general_ci",
        mysql_row_format="DYNAMIC",
    )
    op.create_index("ix_tbl_hrorganization_Name", "tbl_hrorganization", ["OrganizationName"])

    # 2. tbl_hrdepartment
    op.create_table(
        "tbl_hrdepartment",
        sa.Column("DeparmentId", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("OrganizationId", sa.Integer(), nullable=False),
        sa.Column("Dname", sa.String(length=255), nullable=False),
        sa.Column("Dlocation", sa.String(length=255), nullable=True),
        sa.Column("CreatedDate", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("CreateUser", sa.String(length=100), nullable=True),
        sa.Column("UpdateDate", sa.DateTime(), nullable=True),
        sa.Column("UpdatedUser", sa.String(length=100), nullable=True),
        sa.Column("IsActive", sa.Integer(), nullable=False, server_default="1"),
        sa.ForeignKeyConstraint(
            ["OrganizationId"],
            ["tbl_hrorganization.OrganizationId"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("DeparmentId"),
        mysql_charset="utf8",
        mysql_collate="utf8_general_ci",
        mysql_row_format="DYNAMIC",
    )
    op.create_index("ix_tbl_hrdepartment_OrgId", "tbl_hrdepartment", ["OrganizationId"])
    op.create_index("ix_tbl_hrdepartment_DName", "tbl_hrdepartment", ["Dname"])

    # 3. tbl_hrdesignationmaster
    op.create_table(
        "tbl_hrdesignationmaster",
        sa.Column("DesignationId", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("Designation", sa.String(length=255), nullable=False),
        sa.Column("CreatedDate", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("CreateUser", sa.String(length=100), nullable=True),
        sa.Column("UpdateDate", sa.DateTime(), nullable=True),
        sa.Column("UpdatedUser", sa.String(length=100), nullable=True),
        sa.Column("IsActive", sa.Integer(), nullable=False, server_default="1"),
        sa.PrimaryKeyConstraint("DesignationId"),
        mysql_charset="utf8",
        mysql_collate="utf8_general_ci",
        mysql_row_format="DYNAMIC",
    )
    op.create_index("ix_tbl_hrdesignation_Name", "tbl_hrdesignationmaster", ["Designation"])

    # 4. tbl_hrfacility
    op.create_table(
        "tbl_hrfacility",
        sa.Column("FaciltiyId", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("Name", sa.String(length=255), nullable=False),
        sa.Column("percentage", sa.String(length=50), nullable=True),
        sa.Column("CreatedDate", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("CreateUser", sa.String(length=100), nullable=True),
        sa.Column("UpdateDate", sa.DateTime(), nullable=True),
        sa.Column("UpdatedUser", sa.String(length=100), nullable=True),
        sa.Column("IsActive", sa.Integer(), nullable=False, server_default="1"),
        sa.PrimaryKeyConstraint("FaciltiyId"),
        mysql_charset="utf8",
        mysql_collate="utf8_general_ci",
        mysql_row_format="DYNAMIC",
    )
    op.create_index("ix_tbl_hrfacility_Name", "tbl_hrfacility", ["Name"])

    # 5. tbl_hrholiday
    op.create_table(
        "tbl_hrholiday",
        sa.Column("HolidayId", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("EmployeeID", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("HolidayDesc", sa.String(length=255), nullable=False),
        sa.Column("HolidayDate", sa.Date(), nullable=False),
        sa.Column("CreatedDate", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("CreateUser", sa.String(length=100), nullable=True),
        sa.Column("UpdateDate", sa.DateTime(), nullable=True),
        sa.Column("UpdatedUser", sa.String(length=100), nullable=True),
        sa.Column("IsActive", sa.Integer(), nullable=False, server_default="1"),
        sa.PrimaryKeyConstraint("HolidayId"),
        mysql_charset="utf8",
        mysql_collate="utf8_general_ci",
        mysql_row_format="DYNAMIC",
    )
    op.create_index("ix_tbl_hrholiday_Date", "tbl_hrholiday", ["HolidayDate"])
    op.create_index("ix_tbl_hrholiday_EmpId", "tbl_hrholiday", ["EmployeeID"])

    # 6. tbl_hrleavetype
    op.create_table(
        "tbl_hrleavetype",
        sa.Column("LeaveTypeId", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("LeaveType", sa.String(length=100), nullable=False),
        sa.Column("CreatedDate", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("CreateUser", sa.String(length=100), nullable=True),
        sa.Column("UpdateDate", sa.DateTime(), nullable=True),
        sa.Column("UpdatedUser", sa.String(length=100), nullable=True),
        sa.Column("IsActive", sa.Integer(), nullable=False, server_default="1"),
        sa.PrimaryKeyConstraint("LeaveTypeId"),
        mysql_charset="utf8",
        mysql_collate="utf8_general_ci",
        mysql_row_format="DYNAMIC",
    )
    op.create_index("ix_tbl_hrleavetype_Name", "tbl_hrleavetype", ["LeaveType"])

    # 7. tbl_hrleave
    op.create_table(
        "tbl_hrleave",
        sa.Column("LeaveId", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("OrganizationId", sa.Integer(), nullable=False),
        sa.Column("DeparmentId", sa.Integer(), nullable=False),
        sa.Column("EmpId", sa.Integer(), nullable=False),
        sa.Column("LeaveTypeId", sa.Integer(), nullable=False),
        sa.Column("ApplicationDate", sa.Date(), nullable=False),
        sa.Column("FromDate", sa.Date(), nullable=False),
        sa.Column("ToDate", sa.Date(), nullable=False),
        sa.Column("NoOfDays", sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column("Reason", sa.String(length=500), nullable=True),
        sa.Column("Remark", sa.String(length=500), nullable=True),
        sa.Column("Handover", sa.String(length=255), nullable=True),
        sa.Column("ReportingId", sa.Integer(), nullable=True),
        sa.Column("ApprovalStatus", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ApprovalDate", sa.DateTime(), nullable=True),
        sa.Column("CreatedDate", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("CreateUser", sa.String(length=100), nullable=True),
        sa.Column("UpdateDate", sa.DateTime(), nullable=True),
        sa.Column("UpdatedUser", sa.String(length=100), nullable=True),
        sa.PrimaryKeyConstraint("LeaveId"),
        mysql_charset="utf8",
        mysql_collate="utf8_general_ci",
        mysql_row_format="DYNAMIC",
    )
    op.create_index("ix_tbl_hrleave_EmpId", "tbl_hrleave", ["EmpId"])
    op.create_index("ix_tbl_hrleave_Org_Dept", "tbl_hrleave", ["OrganizationId", "DeparmentId"])
    op.create_index("ix_tbl_hrleave_ReportingId", "tbl_hrleave", ["ReportingId"])
    op.create_index("ix_tbl_hrleave_Status", "tbl_hrleave", ["ApprovalStatus"])
    op.create_index("ix_tbl_hrleave_DateRange", "tbl_hrleave", ["FromDate", "ToDate"])

    # 8. tbl_hrcontactperson
    op.create_table(
        "tbl_hrcontactperson",
        sa.Column("ContactpersonId", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("ContactFName", sa.String(length=100), nullable=False),
        sa.Column("ContactMName", sa.String(length=100), nullable=True),
        sa.Column("ContactLName", sa.String(length=100), nullable=True),
        sa.Column("MobileNo", sa.String(length=50), nullable=True),
        sa.Column("Address", sa.String(length=500), nullable=True),
        sa.Column("CreatedDate", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("CreateUser", sa.String(length=100), nullable=True),
        sa.Column("UpdateDate", sa.DateTime(), nullable=True),
        sa.Column("UpdatedUser", sa.String(length=100), nullable=True),
        sa.Column("IsActive", sa.Integer(), nullable=False, server_default="1"),
        sa.PrimaryKeyConstraint("ContactpersonId"),
        mysql_charset="utf8",
        mysql_collate="utf8_general_ci",
        mysql_row_format="DYNAMIC",
    )
    op.create_index("ix_tbl_hrcontact_Name", "tbl_hrcontactperson", ["ContactFName", "ContactLName"])
    op.create_index("ix_tbl_hrcontact_MobileNo", "tbl_hrcontactperson", ["MobileNo"])


def downgrade() -> None:
    op.drop_table("tbl_hrcontactperson")
    op.drop_table("tbl_hrleave")
    op.drop_table("tbl_hrleavetype")
    op.drop_table("tbl_hrholiday")
    op.drop_table("tbl_hrfacility")
    op.drop_table("tbl_hrdesignationmaster")
    op.drop_table("tbl_hrdepartment")
    op.drop_table("tbl_hrorganization")
