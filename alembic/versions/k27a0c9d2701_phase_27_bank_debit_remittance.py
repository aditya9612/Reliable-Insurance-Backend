"""phase_27_bank_debit_remittance

Revision ID: k27a0c9d2701
Revises: j26a0c8d2601
Create Date: 2026-10-15 14:30:00.000000+00:00

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "k27a0c9d2701"
down_revision: Union[str, None] = "j26a0c8d2601"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. tbl_debitfrombankaccount (Remittance & Cash-to-Bank Settlement Journal)
    op.create_table(
        "tbl_debitfrombankaccount",
        sa.Column("Account_Id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("TransactionId", sa.Integer(), nullable=True),
        sa.Column("LedgerMId", sa.Integer(), nullable=True),
        sa.Column("BranchId", sa.Integer(), nullable=False, server_default=sa.text("101")),
        sa.Column("Doc_No", sa.String(length=50), nullable=True),
        sa.Column("Amount", sa.Double(asdecimal=True), nullable=False),
        sa.Column("AccountDate", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("Narration", sa.String(length=500), nullable=True),
        sa.Column("Flag", sa.String(length=50), nullable=False, server_default=sa.text("'Company'")),
        sa.Column("CompanyChequeNo", sa.String(length=50), nullable=True),
        sa.Column("Extra1", sa.String(length=255), nullable=True),
        sa.Column("Extra2", sa.String(length=255), nullable=True),
        sa.Column("isdeleted", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("CreatedUser", sa.String(length=100), nullable=True),
        sa.Column("CreatedDate", sa.DateTime(), nullable=True, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("UpdatedUser", sa.String(length=100), nullable=True),
        sa.Column("UpdatedDate", sa.DateTime(), nullable=True, server_default=sa.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP")),
        sa.PrimaryKeyConstraint("Account_Id"),
        mysql_charset="utf8",
        mysql_collate="utf8_general_ci",
        mysql_row_format="DYNAMIC",
    )
    op.create_index("ix_tbl_debitfrombankaccount_trans_id", "tbl_debitfrombankaccount", ["TransactionId"])
    op.create_index("ix_tbl_debitfrombankaccount_ledger_m_id", "tbl_debitfrombankaccount", ["LedgerMId"])
    op.create_index("ix_tbl_debitfrombankaccount_branch_id", "tbl_debitfrombankaccount", ["BranchId"])
    op.create_index("ix_tbl_debitfrombankaccount_doc_no", "tbl_debitfrombankaccount", ["Doc_No"])
    op.create_index("ix_tbl_debitfrombankaccount_flag", "tbl_debitfrombankaccount", ["Flag"])
    op.create_index("ix_tbl_debitfrombankaccount_account_date", "tbl_debitfrombankaccount", ["AccountDate"])
    op.create_index("ix_tbl_debitfrombankaccount_isdeleted", "tbl_debitfrombankaccount", ["isdeleted"])


def downgrade() -> None:
    op.drop_table("tbl_debitfrombankaccount")
