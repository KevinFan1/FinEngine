"""add merchant reconciliation net rate settings

Revision ID: 041_merchant_net_rate_settings
Revises: 040_merchant_opening_balances
Create Date: 2026-06-03

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "041_merchant_net_rate_settings"
down_revision: Union[str, None] = "040_merchant_opening_balances"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "fin_merchant_net_rate_settings",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False, comment="主键ID"),
        sa.Column("org_id", sa.BigInteger(), nullable=False, comment="所属组织ID"),
        sa.Column("platform_code", sa.String(length=50), nullable=False, server_default="douyin", comment="平台编码"),
        sa.Column("shop_id", sa.BigInteger(), nullable=True, comment="店铺ID，预留店铺级比例"),
        sa.Column("accounting_year", sa.SmallInteger(), nullable=False, comment="核算年份"),
        sa.Column("accounting_month", sa.SmallInteger(), nullable=False, comment="核算月份"),
        sa.Column("accounting_period", sa.Integer(), nullable=False, comment="核算年月 YYYYMM"),
        sa.Column("net_rate", sa.Numeric(8, 6), nullable=False, server_default="0.700000", comment="应付商家净额比例，小数形式"),
        sa.Column("remark", sa.Text(), nullable=False, server_default="", comment="备注"),
        sa.Column("created_by", sa.BigInteger(), nullable=False, comment="创建用户ID"),
        sa.Column("updated_by", sa.BigInteger(), nullable=True, comment="最近修改用户ID"),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false"), comment="是否删除"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True, comment="删除时间"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, comment="更新时间"),
        sa.ForeignKeyConstraint(["created_by"], ["fin_users.id"]),
        sa.ForeignKeyConstraint(["org_id"], ["fin_organizations.id"]),
        sa.ForeignKeyConstraint(["shop_id"], ["fin_shops.id"]),
        sa.ForeignKeyConstraint(["updated_by"], ["fin_users.id"]),
        sa.PrimaryKeyConstraint("id"),
        comment="商家对账净额比例维护表",
    )
    op.create_index(
        "uq_fin_merchant_net_rate_setting",
        "fin_merchant_net_rate_settings",
        [
            sa.text("org_id"),
            sa.text("platform_code"),
            sa.text("accounting_period"),
            sa.text("coalesce(shop_id, 0)"),
        ],
        unique=True,
        postgresql_where=sa.text("is_deleted = false"),
    )
    op.create_index(
        "idx_fin_merchant_net_rate_setting_lookup",
        "fin_merchant_net_rate_settings",
        ["org_id", "platform_code", "accounting_period"],
        postgresql_where=sa.text("is_deleted = false"),
    )


def downgrade() -> None:
    op.drop_index("idx_fin_merchant_net_rate_setting_lookup", table_name="fin_merchant_net_rate_settings")
    op.drop_index("uq_fin_merchant_net_rate_setting", table_name="fin_merchant_net_rate_settings")
    op.drop_table("fin_merchant_net_rate_settings")
