"""add cash flow item dictionary

Revision ID: 010
Revises: 009
Create Date: 2026-05-20 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "fin_cash_flow_items",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False, comment="主键ID"),
        sa.Column("code", sa.String(length=20), nullable=False, comment="项目编号"),
        sa.Column("name", sa.String(length=100), nullable=False, comment="项目名称"),
        sa.Column("parent_id", sa.BigInteger(), nullable=True, comment="父级项目ID"),
        sa.Column("level", sa.SmallInteger(), nullable=False, comment="层级：1=大类 2=明细 3=校验"),
        sa.Column("item_type", sa.String(length=20), nullable=False, comment="分组/明细/净额/校验"),
        sa.Column("flow_section", sa.String(length=20), nullable=False, comment="经营/投资/筹资"),
        sa.Column("flow_direction", sa.String(length=20), nullable=True, comment="流入/流出/净额/校验"),
        sa.Column("summary_method", sa.String(length=20), nullable=False, comment="汇总子项/公式/手动/不汇总"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="100", comment="排序"),
        sa.Column("status", sa.SmallInteger(), nullable=False, server_default="1", comment="状态：1=启用 0=停用"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, comment="更新时间"),
        sa.Column("is_deleted", sa.Boolean(), server_default="false", nullable=False, comment="是否已软删除"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True, comment="软删除时间"),
        sa.ForeignKeyConstraint(["parent_id"], ["fin_cash_flow_items.id"]),
        sa.PrimaryKeyConstraint("id"),
        comment="现金流项目字典表",
    )
    op.create_index(
        "uq_fin_cash_flow_item_code",
        "fin_cash_flow_items",
        ["code"],
        unique=True,
        postgresql_where=sa.text("is_deleted = false"),
    )
    op.create_index("idx_fin_cash_flow_items_parent", "fin_cash_flow_items", ["parent_id", "sort_order"])


def downgrade() -> None:
    op.drop_index("idx_fin_cash_flow_items_parent", table_name="fin_cash_flow_items")
    op.drop_index("uq_fin_cash_flow_item_code", table_name="fin_cash_flow_items")
    op.drop_table("fin_cash_flow_items")
