"""add reconciliation checklist entity dictionary

Revision ID: 046_checklist_entities
Revises: 045_checklist_merchant
Create Date: 2026-06-04

"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "046_checklist_entities"
down_revision: Union[str, None] = "045_checklist_merchant"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "fin_reconciliation_checklist_entities",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False, comment="主键ID"),
        sa.Column("org_id", sa.BigInteger(), nullable=False, comment="所属组织ID"),
        sa.Column("parent_id", sa.BigInteger(), nullable=True, comment="父级商家ID"),
        sa.Column("platform_code", sa.String(length=50), nullable=False, server_default="", comment="平台"),
        sa.Column("entity_type", sa.String(length=40), nullable=False, comment="类型：live_promoter/merchant/receipt_merchant"),
        sa.Column("name", sa.String(length=500), nullable=False, comment="名称"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active", comment="状态"),
        sa.Column("source", sa.String(length=20), nullable=False, server_default="auto", comment="来源"),
        sa.Column("last_seen_period", sa.Integer(), nullable=True, comment="最近出现年月 YYYYMM"),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false"), comment="是否已软删除"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True, comment="软删除时间"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, comment="更新时间"),
        sa.ForeignKeyConstraint(["org_id"], ["fin_organizations.id"]),
        sa.ForeignKeyConstraint(["parent_id"], ["fin_reconciliation_checklist_entities.id"]),
        sa.PrimaryKeyConstraint("id"),
        comment="对账清单商家与推广方维护表",
    )
    op.create_index(
        "uq_fin_reconciliation_checklist_entity_name",
        "fin_reconciliation_checklist_entities",
        ["org_id", "platform_code", "entity_type", "name"],
        unique=True,
        postgresql_where=sa.text("is_deleted = false"),
    )
    op.create_index(
        "idx_fin_reconciliation_checklist_entity_search",
        "fin_reconciliation_checklist_entities",
        ["org_id", "platform_code", "entity_type", "status", "name"],
        postgresql_where=sa.text("is_deleted = false"),
    )
    op.create_index(
        "idx_fin_reconciliation_checklist_entity_parent",
        "fin_reconciliation_checklist_entities",
        ["parent_id"],
        postgresql_where=sa.text("is_deleted = false"),
    )

    for column_name, comment in (
        ("live_promoter_id", "直播推广方ID"),
        ("merchant_id", "商家ID"),
        ("receipt_merchant_id", "收款商家ID"),
    ):
        op.execute(
            f"ALTER TABLE fin_reconciliation_checklist_details "
            f"ADD COLUMN IF NOT EXISTS {column_name} BIGINT NULL"
        )
        op.execute(f"COMMENT ON COLUMN fin_reconciliation_checklist_details.{column_name} IS '{comment}'")

    op.create_foreign_key(
        "fk_reconciliation_checklist_detail_live_promoter_entity",
        "fin_reconciliation_checklist_details",
        "fin_reconciliation_checklist_entities",
        ["live_promoter_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_reconciliation_checklist_detail_merchant_entity",
        "fin_reconciliation_checklist_details",
        "fin_reconciliation_checklist_entities",
        ["merchant_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_reconciliation_checklist_detail_receipt_entity",
        "fin_reconciliation_checklist_details",
        "fin_reconciliation_checklist_entities",
        ["receipt_merchant_id"],
        ["id"],
    )

    op.execute("DROP INDEX IF EXISTS idx_fin_reconciliation_checklist_export")
    op.execute("DROP INDEX IF EXISTS idx_fin_reconciliation_checklist_summary")
    op.create_index(
        "idx_fin_reconciliation_checklist_summary",
        "fin_reconciliation_checklist_details",
        [
            "org_id",
            "accounting_period",
            "merchant_id",
            "receipt_merchant_id",
            "live_promoter_id",
            "merchant_name",
            "receipt_merchant",
            "live_promoter",
        ],
        postgresql_where=sa.text("is_deleted = false"),
    )
    op.create_index(
        "idx_fin_reconciliation_checklist_export",
        "fin_reconciliation_checklist_details",
        [
            "org_id",
            "accounting_period",
            "merchant_id",
            "receipt_merchant_id",
            "live_promoter_id",
            "merchant_name",
            "receipt_merchant",
            "live_promoter",
            "product_name",
        ],
        postgresql_where=sa.text("is_deleted = false"),
    )
    op.create_index(
        "idx_fin_reconciliation_checklist_live_promoter_filter",
        "fin_reconciliation_checklist_details",
        ["org_id", "accounting_period", "live_promoter_id"],
        postgresql_where=sa.text("is_deleted = false"),
    )
    op.create_index(
        "idx_fin_reconciliation_checklist_merchant_filter",
        "fin_reconciliation_checklist_details",
        ["org_id", "accounting_period", "merchant_id"],
        postgresql_where=sa.text("is_deleted = false"),
    )
    op.create_index(
        "idx_fin_reconciliation_checklist_receipt_filter",
        "fin_reconciliation_checklist_details",
        ["org_id", "accounting_period", "receipt_merchant_id"],
        postgresql_where=sa.text("is_deleted = false"),
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_fin_reconciliation_checklist_receipt_filter")
    op.execute("DROP INDEX IF EXISTS idx_fin_reconciliation_checklist_merchant_filter")
    op.execute("DROP INDEX IF EXISTS idx_fin_reconciliation_checklist_live_promoter_filter")
    op.execute("DROP INDEX IF EXISTS idx_fin_reconciliation_checklist_export")
    op.execute("DROP INDEX IF EXISTS idx_fin_reconciliation_checklist_summary")
    op.create_index(
        "idx_fin_reconciliation_checklist_summary",
        "fin_reconciliation_checklist_details",
        ["org_id", "accounting_period", "merchant_name", "receipt_merchant", "live_promoter"],
        postgresql_where=sa.text("is_deleted = false"),
    )
    op.create_index(
        "idx_fin_reconciliation_checklist_export",
        "fin_reconciliation_checklist_details",
        ["org_id", "accounting_period", "merchant_name", "receipt_merchant", "live_promoter", "product_name"],
        postgresql_where=sa.text("is_deleted = false"),
    )
    op.drop_constraint(
        "fk_reconciliation_checklist_detail_receipt_entity",
        "fin_reconciliation_checklist_details",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_reconciliation_checklist_detail_merchant_entity",
        "fin_reconciliation_checklist_details",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_reconciliation_checklist_detail_live_promoter_entity",
        "fin_reconciliation_checklist_details",
        type_="foreignkey",
    )
    op.drop_column("fin_reconciliation_checklist_details", "receipt_merchant_id")
    op.drop_column("fin_reconciliation_checklist_details", "merchant_id")
    op.drop_column("fin_reconciliation_checklist_details", "live_promoter_id")
    op.drop_table("fin_reconciliation_checklist_entities")
