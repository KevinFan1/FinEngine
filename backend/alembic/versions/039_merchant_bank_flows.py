"""add merchant reconciliation bank flow tables

Revision ID: 039_merchant_bank_flows
Revises: 038_backfill_chinese_comments
Create Date: 2026-06-02

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "039_merchant_bank_flows"
down_revision: Union[str, None] = "038_backfill_chinese_comments"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "fin_merchant_bank_flow_files",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False, comment="主键ID"),
        sa.Column("org_id", sa.BigInteger(), nullable=False, comment="所属组织ID"),
        sa.Column("user_id", sa.BigInteger(), nullable=False, comment="上传用户ID"),
        sa.Column("accounting_year", sa.SmallInteger(), nullable=False, comment="核算年份"),
        sa.Column("accounting_month", sa.SmallInteger(), nullable=False, comment="核算月份"),
        sa.Column("accounting_period", sa.Integer(), nullable=False, comment="核算年月 YYYYMM"),
        sa.Column("original_name", sa.String(length=500), nullable=False, comment="原始文件名"),
        sa.Column("file_size", sa.BigInteger(), nullable=False, server_default="0", comment="文件大小字节数"),
        sa.Column("file_hash", sa.String(length=64), nullable=True, comment="文件 SHA-256 哈希值"),
        sa.Column("bank_name", sa.String(length=100), nullable=False, server_default="", comment="银行名称"),
        sa.Column("account_name", sa.String(length=500), nullable=False, server_default="", comment="账户名称"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="success", comment="状态"),
        sa.Column("row_count", sa.Integer(), nullable=False, server_default="0", comment="流水行数"),
        sa.Column("matched_row_count", sa.Integer(), nullable=False, server_default="0", comment="已解析直播日期行数"),
        sa.Column("error_message", sa.Text(), nullable=True, comment="错误信息"),
        sa.Column("result_summary", postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment="导入结果摘要"),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false"), comment="是否删除"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True, comment="删除时间"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, comment="更新时间"),
        sa.ForeignKeyConstraint(["org_id"], ["fin_organizations.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["fin_users.id"]),
        sa.PrimaryKeyConstraint("id"),
        comment="商家对账银行流水导入批次表",
    )
    op.create_index(
        "idx_fin_merchant_bank_flow_file_lookup",
        "fin_merchant_bank_flow_files",
        ["org_id", "accounting_period", "account_name"],
        postgresql_where=sa.text("is_deleted = false"),
    )
    op.create_index(
        "idx_fin_merchant_bank_flow_file_created",
        "fin_merchant_bank_flow_files",
        ["org_id", "created_at"],
        postgresql_where=sa.text("is_deleted = false"),
    )

    op.create_table(
        "fin_merchant_bank_flow_rows",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False, comment="主键ID"),
        sa.Column("bank_flow_file_id", sa.BigInteger(), nullable=False, comment="银行流水批次ID"),
        sa.Column("org_id", sa.BigInteger(), nullable=False, comment="所属组织ID"),
        sa.Column("accounting_period", sa.Integer(), nullable=False, comment="核算年月 YYYYMM"),
        sa.Column("source_row_number", sa.Integer(), nullable=False, server_default="0", comment="源文件行号"),
        sa.Column("bank_name", sa.String(length=100), nullable=False, server_default="", comment="银行名称"),
        sa.Column("account_no", sa.String(length=200), nullable=False, server_default="", comment="账号"),
        sa.Column("account_name", sa.String(length=500), nullable=False, server_default="", comment="账户名称"),
        sa.Column("transaction_date", sa.Date(), nullable=True, comment="交易日期"),
        sa.Column("transaction_time", sa.DateTime(timezone=False), nullable=True, comment="交易时间"),
        sa.Column("debit_amount", sa.Numeric(14, 2), nullable=False, server_default="0", comment="借方发生额/支出金额"),
        sa.Column("credit_amount", sa.Numeric(14, 2), nullable=False, server_default="0", comment="贷方发生额/收入金额"),
        sa.Column("flow_amount", sa.Numeric(14, 2), nullable=False, server_default="0", comment="流水净额：支出为正，收入为负"),
        sa.Column("balance", sa.Numeric(14, 2), nullable=False, server_default="0", comment="余额"),
        sa.Column("counterparty_account_no", sa.String(length=200), nullable=False, server_default="", comment="对方账号"),
        sa.Column("counterparty_name", sa.String(length=500), nullable=False, server_default="", comment="对方户名"),
        sa.Column("counterparty_bank", sa.String(length=500), nullable=False, server_default="", comment="对方开户机构/行名"),
        sa.Column("summary", sa.String(length=500), nullable=False, server_default="", comment="摘要"),
        sa.Column("purpose", sa.Text(), nullable=False, server_default="", comment="用途/备注/附言"),
        sa.Column("remark", sa.Text(), nullable=False, server_default="", comment="备注"),
        sa.Column("live_date", sa.String(length=100), nullable=False, server_default="", comment="解析直播日期"),
        sa.Column("transaction_flow_no", sa.String(length=500), nullable=False, server_default="", comment="交易流水号"),
        sa.Column("raw_row", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb"), comment="原始行JSON"),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false"), comment="是否删除"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True, comment="删除时间"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, comment="创建时间"),
        sa.ForeignKeyConstraint(["bank_flow_file_id"], ["fin_merchant_bank_flow_files.id"]),
        sa.ForeignKeyConstraint(["org_id"], ["fin_organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
        comment="商家对账银行流水明细表",
    )
    op.create_index(
        "idx_fin_merchant_bank_flow_match",
        "fin_merchant_bank_flow_rows",
        ["org_id", "accounting_period", "account_name", "counterparty_name", "live_date"],
        postgresql_where=sa.text("is_deleted = false"),
    )


def downgrade() -> None:
    op.drop_index("idx_fin_merchant_bank_flow_match", table_name="fin_merchant_bank_flow_rows")
    op.drop_table("fin_merchant_bank_flow_rows")
    op.drop_index("idx_fin_merchant_bank_flow_file_created", table_name="fin_merchant_bank_flow_files")
    op.drop_index("idx_fin_merchant_bank_flow_file_lookup", table_name="fin_merchant_bank_flow_files")
    op.drop_table("fin_merchant_bank_flow_files")
