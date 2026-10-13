"""phase_24_hr_workforce_payroll_attendance

Revision ID: h24a0c6d2401
Revises: g23a0c5d2301
Create Date: 2026-10-12 15:38:00.000000+00:00

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "h24a0c6d2401"
down_revision: Union[str, None] = "g23a0c5d2301"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. tbl_hrworkinghistory
    op.create_table(
        "tbl_hrworkinghistory",
        sa.Column("WorkingHistoryId", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("EmployeeID", sa.Integer(), nullable=False),
        sa.Column("DepartMentID", sa.Integer(), nullable=True),
        sa.Column("CompanyName", sa.String(length=255), nullable=False),
        sa.Column("CompanyAddres", sa.String(length=500), nullable=True),
        sa.Column("CompanyMobileNo", sa.String(length=50), nullable=True),
        sa.Column("PreQualification", sa.String(length=255), nullable=True),
        sa.Column("PreExprience", sa.String(length=100), nullable=True),
        sa.Column("PreStartDate", sa.Date(), nullable=True),
        sa.Column("PreEndDate", sa.Date(), nullable=True),
        sa.Column("HRName", sa.String(length=100), nullable=True),
        sa.Column("HRMobNo", sa.String(length=50), nullable=True),
        sa.Column("HRMailId", sa.String(length=100), nullable=True),
        sa.Column("CreatedDate", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("CreateUser", sa.String(length=100), nullable=True),
        sa.Column("UpdateDate", sa.DateTime(), nullable=True),
        sa.Column("UpdateUser", sa.String(length=100), nullable=True),
        sa.Column("IsActive", sa.Integer(), nullable=False, server_default="1"),
        sa.PrimaryKeyConstraint("WorkingHistoryId"),
        mysql_charset="utf8",
        mysql_collate="utf8_general_ci",
        mysql_row_format="DYNAMIC",
    )
    op.create_index("ix_tbl_hrworkinghistory_EmployeeID", "tbl_hrworkinghistory", ["EmployeeID"])
    op.create_index("ix_tbl_hrworkinghistory_CompanyName", "tbl_hrworkinghistory", ["CompanyName"])

    # 2. tbl_hrfamilydetails
    op.create_table(
        "tbl_hrfamilydetails",
        sa.Column("FamilyId", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("EmployeeID", sa.Integer(), nullable=False),
        sa.Column("FName", sa.String(length=150), nullable=False),
        sa.Column("Relation", sa.String(length=50), nullable=False),
        sa.Column("Occuption", sa.String(length=100), nullable=True),
        sa.Column("ContactNo", sa.String(length=50), nullable=True),
        sa.Column("Designation", sa.String(length=100), nullable=True),
        sa.Column("CreatedDate", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("CreateUser", sa.String(length=100), nullable=True),
        sa.Column("UpdateDate", sa.DateTime(), nullable=True),
        sa.Column("UpdateUser", sa.String(length=100), nullable=True),
        sa.Column("IsActive", sa.Integer(), nullable=False, server_default="1"),
        sa.PrimaryKeyConstraint("FamilyId"),
        mysql_charset="utf8",
        mysql_collate="utf8_general_ci",
        mysql_row_format="DYNAMIC",
    )
    op.create_index("ix_tbl_hrfamilydetails_EmployeeID", "tbl_hrfamilydetails", ["EmployeeID"])
    op.create_index("ix_tbl_hrfamilydetails_Relation", "tbl_hrfamilydetails", ["Relation"])

    # 3. tbl_hrreferencedetails
    op.create_table(
        "tbl_hrreferencedetails",
        sa.Column("ReferenceId", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("EmployeeID", sa.Integer(), nullable=False),
        sa.Column("ReferenceName", sa.String(length=150), nullable=False),
        sa.Column("Address", sa.String(length=500), nullable=True),
        sa.Column("ContactNo", sa.String(length=50), nullable=True),
        sa.Column("Designation", sa.String(length=100), nullable=True),
        sa.Column("MailId", sa.String(length=100), nullable=True),
        sa.Column("CreatedDate", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("CreateUser", sa.String(length=100), nullable=True),
        sa.Column("UpdateDate", sa.DateTime(), nullable=True),
        sa.Column("UpdateUser", sa.String(length=100), nullable=True),
        sa.Column("IsActive", sa.Integer(), nullable=False, server_default="1"),
        sa.PrimaryKeyConstraint("ReferenceId"),
        mysql_charset="utf8",
        mysql_collate="utf8_general_ci",
        mysql_row_format="DYNAMIC",
    )
    op.create_index("ix_tbl_hrreferencedetails_EmployeeID", "tbl_hrreferencedetails", ["EmployeeID"])
    op.create_index("ix_tbl_hrreferencedetails_ReferenceName", "tbl_hrreferencedetails", ["ReferenceName"])

    # 4. tbl_hrworkingtime
    op.create_table(
        "tbl_hrworkingtime",
        sa.Column("timeinfoId", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("EmployeeID", sa.Integer(), nullable=False),
        sa.Column("DepartMentID", sa.Integer(), nullable=True),
        sa.Column("workingHours", sa.String(length=50), nullable=True),
        sa.Column("offday", sa.String(length=50), nullable=True, server_default="Sunday"),
        sa.Column("overtime", sa.String(length=50), nullable=True),
        sa.Column("ExtraDay", sa.String(length=50), nullable=True),
        sa.Column("CreatedDate", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("CreateUser", sa.String(length=100), nullable=True),
        sa.Column("UpdateDate", sa.DateTime(), nullable=True),
        sa.Column("UpdateUser", sa.String(length=100), nullable=True),
        sa.Column("IsActive", sa.Integer(), nullable=False, server_default="1"),
        sa.PrimaryKeyConstraint("timeinfoId"),
        mysql_charset="utf8",
        mysql_collate="utf8_general_ci",
        mysql_row_format="DYNAMIC",
    )
    op.create_index("ix_tbl_hrworkingtime_EmployeeID", "tbl_hrworkingtime", ["EmployeeID"])
    op.create_index("ix_tbl_hrworkingtime_DepartMentID", "tbl_hrworkingtime", ["DepartMentID"])

    # 5. tbl_hrsalarystructuredef
    op.create_table(
        "tbl_hrsalarystructuredef",
        sa.Column("SalaryStructureDefId", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("OrganizationId", sa.Integer(), nullable=False),
        sa.Column("salaryStructure", sa.String(length=255), nullable=False),
        sa.Column("InActive", sa.String(length=10), nullable=True, server_default="0"),
        sa.Column("RateOnGross", sa.String(length=50), nullable=True),
        sa.Column("Remark", sa.String(length=500), nullable=True),
        sa.Column("CreatedDate", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("CreateUser", sa.String(length=100), nullable=True),
        sa.Column("UpdateDate", sa.DateTime(), nullable=True),
        sa.Column("UpdatedUser", sa.String(length=100), nullable=True),
        sa.Column("IsActive", sa.Integer(), nullable=False, server_default="1"),
        sa.PrimaryKeyConstraint("SalaryStructureDefId"),
        mysql_charset="utf8",
        mysql_collate="utf8_general_ci",
        mysql_row_format="DYNAMIC",
    )
    op.create_index("ix_tbl_hrsalarystructure_OrgId", "tbl_hrsalarystructuredef", ["OrganizationId"])
    op.create_index("ix_tbl_hrsalarystructure_Name", "tbl_hrsalarystructuredef", ["salaryStructure"])

    # 6. tbl_hradvance
    op.create_table(
        "tbl_hradvance",
        sa.Column("HrAdvanceId", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("EmpId", sa.Integer(), nullable=False),
        sa.Column("OrganizationId", sa.Integer(), nullable=False),
        sa.Column("AdvanceName", sa.String(length=100), nullable=False),
        sa.Column("AdvanceDate", sa.Date(), nullable=False),
        sa.Column("Amount", sa.Numeric(precision=12, scale=2), nullable=False, server_default="0.00"),
        sa.Column("InterestAmount", sa.Numeric(precision=12, scale=2), nullable=False, server_default="0.00"),
        sa.Column("TotalAdvance", sa.Numeric(precision=12, scale=2), nullable=False, server_default="0.00"),
        sa.Column("TotalInterest", sa.Numeric(precision=12, scale=2), nullable=False, server_default="0.00"),
        sa.Column("TotalReceipts", sa.Numeric(precision=12, scale=2), nullable=False, server_default="0.00"),
        sa.Column("TotalRecovered", sa.Numeric(precision=12, scale=2), nullable=False, server_default="0.00"),
        sa.Column("TotalDeu", sa.Numeric(precision=12, scale=2), nullable=False, server_default="0.00"),
        sa.Column("Lumpsum", sa.String(length=10), nullable=True, server_default="No"),
        sa.Column("NoOfInstallment", sa.String(length=10), nullable=True, server_default="1"),
        sa.Column("Instlamt", sa.Numeric(precision=12, scale=2), nullable=False, server_default="0.00"),
        sa.Column("RecoverFrom", sa.String(length=50), nullable=True, server_default="Salary"),
        sa.Column("NoRecovery", sa.String(length=10), nullable=True, server_default="0"),
        sa.Column("Remark", sa.String(length=500), nullable=True),
        sa.Column("CreatedDate", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("CreateUser", sa.String(length=100), nullable=True),
        sa.Column("UpdateDate", sa.DateTime(), nullable=True),
        sa.Column("UpdatedUser", sa.String(length=100), nullable=True),
        sa.Column("IsActive", sa.Integer(), nullable=False, server_default="1"),
        sa.PrimaryKeyConstraint("HrAdvanceId"),
        mysql_charset="utf8",
        mysql_collate="utf8_general_ci",
        mysql_row_format="DYNAMIC",
    )
    op.create_index("ix_tbl_hradvance_EmpId", "tbl_hradvance", ["EmpId"])
    op.create_index("ix_tbl_hradvance_OrgId", "tbl_hradvance", ["OrganizationId"])
    op.create_index("ix_tbl_hradvance_AdvanceDate", "tbl_hradvance", ["AdvanceDate"])

    # 7. tbl_hrmonthlyworkingdetails
    op.create_table(
        "tbl_hrmonthlyworkingdetails",
        sa.Column("MonthlyWorkingId", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("OrganizationId", sa.Integer(), nullable=False),
        sa.Column("DeparmentId", sa.Integer(), nullable=False),
        sa.Column("EmpId", sa.Integer(), nullable=False),
        sa.Column("Month", sa.Integer(), nullable=False),
        sa.Column("Year", sa.Integer(), nullable=False),
        sa.Column("totalNoOfDays", sa.Numeric(precision=5, scale=2), nullable=False, server_default="30.00"),
        sa.Column("Sunday", sa.Numeric(precision=5, scale=2), nullable=False, server_default="4.00"),
        sa.Column("Hoildays", sa.Numeric(precision=5, scale=2), nullable=False, server_default="0.00"),
        sa.Column("leaves", sa.Numeric(precision=5, scale=2), nullable=False, server_default="0.00"),
        sa.Column("workingDays", sa.Numeric(precision=5, scale=2), nullable=False, server_default="26.00"),
        sa.Column("ExtraDays", sa.Numeric(precision=5, scale=2), nullable=False, server_default="0.00"),
        sa.Column("overTimeHour", sa.Numeric(precision=6, scale=2), nullable=False, server_default="0.00"),
        sa.Column("PetrolAll", sa.Numeric(precision=10, scale=2), nullable=False, server_default="0.00"),
        sa.Column("Incentive", sa.Numeric(precision=10, scale=2), nullable=False, server_default="0.00"),
        sa.Column("Arrears", sa.Numeric(precision=10, scale=2), nullable=False, server_default="0.00"),
        sa.Column("CreatedDate", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("CreateUser", sa.String(length=100), nullable=True),
        sa.Column("UpdateDate", sa.DateTime(), nullable=True),
        sa.Column("UpdatedUser", sa.String(length=100), nullable=True),
        sa.Column("IsActive", sa.Integer(), nullable=False, server_default="1"),
        sa.PrimaryKeyConstraint("MonthlyWorkingId"),
        mysql_charset="utf8",
        mysql_collate="utf8_general_ci",
        mysql_row_format="DYNAMIC",
    )
    op.create_index(
        "ix_tbl_hrmonthlyworking_Emp_Period", "tbl_hrmonthlyworkingdetails", ["EmpId", "Year", "Month"]
    )
    op.create_index(
        "ix_tbl_hrmonthlyworking_Org_Dept", "tbl_hrmonthlyworkingdetails", ["OrganizationId", "DeparmentId"]
    )


def downgrade() -> None:
    op.drop_table("tbl_hrmonthlyworkingdetails")
    op.drop_table("tbl_hradvance")
    op.drop_table("tbl_hrsalarystructuredef")
    op.drop_table("tbl_hrworkingtime")
    op.drop_table("tbl_hrreferencedetails")
    op.drop_table("tbl_hrfamilydetails")
    op.drop_table("tbl_hrworkinghistory")
