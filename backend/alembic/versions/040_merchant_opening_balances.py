"""add merchant reconciliation opening balances

Revision ID: 040_merchant_opening_balances
Revises: 039_merchant_bank_flows
Create Date: 2026-06-02

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "040_merchant_opening_balances"
down_revision: Union[str, None] = "039_merchant_bank_flows"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "fin_merchant_opening_balances",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False, comment="主键ID"),
        sa.Column("org_id", sa.BigInteger(), nullable=False, comment="所属组织ID"),
        sa.Column("platform_code", sa.String(length=50), nullable=False, server_default="douyin", comment="平台编码"),
        sa.Column("accounting_year", sa.SmallInteger(), nullable=False, comment="核算年份"),
        sa.Column("accounting_month", sa.SmallInteger(), nullable=False, comment="核算月份"),
        sa.Column("accounting_period", sa.Integer(), nullable=False, comment="核算年月 YYYYMM"),
        sa.Column("our_subject", sa.String(length=500), nullable=False, server_default="", comment="我方主体"),
        sa.Column("receipt_merchant", sa.String(length=500), nullable=False, server_default="", comment="收款商家"),
        sa.Column("opening_balance", sa.Numeric(14, 2), nullable=False, server_default="0", comment="期初余额"),
        sa.Column("remark", sa.Text(), nullable=False, server_default="", comment="备注"),
        sa.Column("created_by", sa.BigInteger(), nullable=False, comment="创建用户ID"),
        sa.Column("updated_by", sa.BigInteger(), nullable=True, comment="最近修改用户ID"),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false"), comment="是否删除"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True, comment="删除时间"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, comment="更新时间"),
        sa.ForeignKeyConstraint(["created_by"], ["fin_users.id"]),
        sa.ForeignKeyConstraint(["org_id"], ["fin_organizations.id"]),
        sa.ForeignKeyConstraint(["updated_by"], ["fin_users.id"]),
        sa.PrimaryKeyConstraint("id"),
        comment="商家对账期初余额表",
    )
    op.create_index(
        "uq_fin_merchant_opening_balance",
        "fin_merchant_opening_balances",
        ["org_id", "platform_code", "accounting_period", "our_subject", "receipt_merchant"],
        unique=True,
        postgresql_where=sa.text("is_deleted = false"),
    )
    op.create_index(
        "idx_fin_merchant_opening_balance_lookup",
        "fin_merchant_opening_balances",
        ["org_id", "platform_code", "accounting_period"],
        postgresql_where=sa.text("is_deleted = false"),
    )


def downgrade() -> None:
    op.drop_index("idx_fin_merchant_opening_balance_lookup", table_name="fin_merchant_opening_balances")
    op.drop_index("uq_fin_merchant_opening_balance", table_name="fin_merchant_opening_balances")
    op.drop_table("fin_merchant_opening_balances")
