"""add reconciliation checklist preaggregation

Revision ID: 047_checklist_preaggregation
Revises: 046_checklist_entities
Create Date: 2026-06-05

"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "047_checklist_preaggregation"
down_revision: Union[str, None] = "046_checklist_entities"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


SUMMARY_DIMENSIONS = [
    "org_id",
    "shop_id",
    "accounting_period",
    "platform_code",
    "merchant_id",
    "receipt_merchant_id",
    "live_promoter_id",
    "merchant_name",
    "receipt_merchant",
    "live_promoter",
]


def _next_yyyymm(period: int) -> int:
    year = period // 100
    month = period % 100
    if month == 12:
        return (year + 1) * 100 + 1
    return year * 100 + month + 1


def _summary_columns(include_product: bool = False) -> list[sa.Column]:
    columns = [
        sa.Column("id", sa.BigInteger(), nullable=False, comment="主键ID"),
        sa.Column("org_id", sa.BigInteger(), nullable=False, comment="所属组织ID"),
        sa.Column("shop_id", sa.BigInteger(), nullable=False, comment="店铺ID"),
        sa.Column("platform_code", sa.String(length=50), nullable=False, comment="平台"),
        sa.Column("shop_name", sa.String(length=200), nullable=False, comment="店铺"),
        sa.Column("accounting_year", sa.SmallInteger(), nullable=False, comment="动账时间年份"),
        sa.Column("accounting_month", sa.SmallInteger(), nullable=False, comment="动账时间月份"),
        sa.Column("accounting_period", sa.Integer(), nullable=False, comment="动账时间年月 YYYYMM"),
        sa.Column("live_promoter_id", sa.BigInteger(), nullable=True, comment="直播推广方ID"),
        sa.Column("merchant_id", sa.BigInteger(), nullable=True, comment="商家ID"),
        sa.Column("receipt_merchant_id", sa.BigInteger(), nullable=True, comment="收款商家ID"),
        sa.Column("live_promoter", sa.String(length=500), nullable=False, server_default="", comment="直播推广方"),
        sa.Column("merchant_name", sa.String(length=500), nullable=False, server_default="", comment="商家"),
        sa.Column("receipt_merchant", sa.String(length=500), nullable=False, server_default="", comment="收款商家"),
    ]
    if include_product:
        columns.append(sa.Column("product_name", sa.String(length=500), nullable=False, server_default="", comment="商品名称"))
    columns.extend(
        [
            sa.Column("product_quantity", sa.Integer(), nullable=False, server_default="0", comment="货品数量"),
            sa.Column("total_order_amount", sa.Numeric(14, 2), nullable=False, server_default="0", comment="订单总金额"),
            sa.Column("total_live_commission", sa.Numeric(14, 2), nullable=False, server_default="0", comment="直播推广佣金总金额"),
            sa.Column("total_merchant_net_amount", sa.Numeric(14, 2), nullable=False, server_default="0", comment="应付商家净额总金额"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, comment="创建时间"),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, comment="更新时间"),
            sa.ForeignKeyConstraint(["org_id"], ["fin_organizations.id"]),
            sa.ForeignKeyConstraint(["shop_id"], ["fin_shops.id"]),
            sa.ForeignKeyConstraint(["live_promoter_id"], ["fin_reconciliation_checklist_entities.id"]),
            sa.ForeignKeyConstraint(["merchant_id"], ["fin_reconciliation_checklist_entities.id"]),
            sa.ForeignKeyConstraint(["receipt_merchant_id"], ["fin_reconciliation_checklist_entities.id"]),
            sa.PrimaryKeyConstraint("id", "accounting_period"),
        ]
    )
    return columns


def _create_existing_period_partitions() -> None:
    bind = op.get_bind()
    periods = [
        row[0]
        for row in bind.execute(
            sa.text(
                """
                SELECT DISTINCT accounting_period
                FROM fin_reconciliation_checklist_details
                WHERE accounting_period IS NOT NULL
                ORDER BY accounting_period
                """
            )
        )
    ]
    for period in periods:
        next_period = _next_yyyymm(int(period))
        for table_name in (
            "fin_reconciliation_checklist_summary_rows",
            "fin_reconciliation_checklist_summary_product_rows",
        ):
            op.execute(
                sa.text(
                    f"""
                    CREATE TABLE IF NOT EXISTS {table_name}_{int(period)}
                    PARTITION OF {table_name}
                    FOR VALUES FROM ({int(period)}) TO ({next_period})
                    """
                )
            )


def _backfill_summary_rows() -> None:
    op.execute(
        """
        INSERT INTO fin_reconciliation_checklist_summary_rows (
            org_id,
            shop_id,
            platform_code,
            shop_name,
            accounting_year,
            accounting_month,
            accounting_period,
            live_promoter_id,
            merchant_id,
            receipt_merchant_id,
            live_promoter,
            merchant_name,
            receipt_merchant,
            product_quantity,
            total_order_amount,
            total_live_commission,
            total_merchant_net_amount
        )
        SELECT
            org_id,
            shop_id,
            platform_code,
            shop_name,
            accounting_year,
            accounting_month,
            accounting_period,
            live_promoter_id,
            merchant_id,
            receipt_merchant_id,
            live_promoter,
            merchant_name,
            receipt_merchant,
            COUNT(id),
            SUM(order_amount),
            SUM(live_commission),
            SUM(merchant_net_amount)
        FROM fin_reconciliation_checklist_details
        WHERE is_deleted = false
        GROUP BY
            org_id,
            shop_id,
            platform_code,
            shop_name,
            accounting_year,
            accounting_month,
            accounting_period,
            live_promoter_id,
            merchant_id,
            receipt_merchant_id,
            live_promoter,
            merchant_name,
            receipt_merchant
        """
    )
    op.execute(
        """
        INSERT INTO fin_reconciliation_checklist_summary_product_rows (
            org_id,
            shop_id,
            platform_code,
            shop_name,
            accounting_year,
            accounting_month,
            accounting_period,
            live_promoter_id,
            merchant_id,
            receipt_merchant_id,
            live_promoter,
            merchant_name,
            receipt_merchant,
            product_name,
            product_quantity,
            total_order_amount,
            total_live_commission,
            total_merchant_net_amount
        )
        SELECT
            org_id,
            shop_id,
            platform_code,
            shop_name,
            accounting_year,
            accounting_month,
            accounting_period,
            live_promoter_id,
            merchant_id,
            receipt_merchant_id,
            live_promoter,
            merchant_name,
            receipt_merchant,
            product_name,
            COUNT(id),
            SUM(order_amount),
            SUM(live_commission),
            SUM(merchant_net_amount)
        FROM fin_reconciliation_checklist_details
        WHERE is_deleted = false
        GROUP BY
            org_id,
            shop_id,
            platform_code,
            shop_name,
            accounting_year,
            accounting_month,
            accounting_period,
            live_promoter_id,
            merchant_id,
            receipt_merchant_id,
            live_promoter,
            merchant_name,
            receipt_merchant,
            product_name
        """
    )


def upgrade() -> None:
    op.execute("CREATE SEQUENCE IF NOT EXISTS fin_reconciliation_checklist_summary_rows_id_seq")
    op.execute("CREATE SEQUENCE IF NOT EXISTS fin_reconciliation_checklist_summary_product_rows_id_seq")

    op.create_table(
        "fin_reconciliation_checklist_summary_rows",
        *_summary_columns(),
        comment="对账清单预聚合汇总表",
        postgresql_partition_by="RANGE (accounting_period)",
    )
    op.create_table(
        "fin_reconciliation_checklist_summary_product_rows",
        *_summary_columns(include_product=True),
        comment="对账清单商品预聚合汇总表",
        postgresql_partition_by="RANGE (accounting_period)",
    )
    op.execute(
        """
        ALTER TABLE fin_reconciliation_checklist_summary_rows
        ALTER COLUMN id SET DEFAULT nextval('fin_reconciliation_checklist_summary_rows_id_seq'::regclass)
        """
    )
    op.execute(
        """
        ALTER TABLE fin_reconciliation_checklist_summary_product_rows
        ALTER COLUMN id SET DEFAULT nextval('fin_reconciliation_checklist_summary_product_rows_id_seq'::regclass)
        """
    )
    op.execute("ALTER SEQUENCE fin_reconciliation_checklist_summary_rows_id_seq OWNED BY fin_reconciliation_checklist_summary_rows.id")
    op.execute("ALTER SEQUENCE fin_reconciliation_checklist_summary_product_rows_id_seq OWNED BY fin_reconciliation_checklist_summary_product_rows.id")

    _create_existing_period_partitions()
    _backfill_summary_rows()

    op.create_index(
        "uq_fin_reconciliation_checklist_summary_row",
        "fin_reconciliation_checklist_summary_rows",
        SUMMARY_DIMENSIONS,
        unique=True,
    )
    op.create_index(
        "idx_fin_reconciliation_checklist_summary_row_query",
        "fin_reconciliation_checklist_summary_rows",
        ["org_id", "accounting_period", "merchant_id", "receipt_merchant_id", "live_promoter_id"],
    )
    op.create_index(
        "uq_fin_reconciliation_checklist_summary_product_row",
        "fin_reconciliation_checklist_summary_product_rows",
        [*SUMMARY_DIMENSIONS, "product_name"],
        unique=True,
    )
    op.create_index(
        "idx_fin_reconciliation_checklist_summary_product_query",
        "fin_reconciliation_checklist_summary_product_rows",
        ["org_id", "accounting_period", "merchant_id", "receipt_merchant_id", "live_promoter_id", "product_name"],
    )

    op.execute("ALTER TABLE fin_reconciliation_checklist_details DROP COLUMN IF EXISTS raw_row")


def downgrade() -> None:
    op.add_column(
        "fin_reconciliation_checklist_details",
        sa.Column("raw_row", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default=sa.text("'{}'::jsonb"), comment="原始行JSON"),
    )
    op.alter_column("fin_reconciliation_checklist_details", "raw_row", server_default=None)
    op.drop_table("fin_reconciliation_checklist_summary_product_rows")
    op.drop_table("fin_reconciliation_checklist_summary_rows")
    op.execute("DROP SEQUENCE IF EXISTS fin_reconciliation_checklist_summary_product_rows_id_seq")
    op.execute("DROP SEQUENCE IF EXISTS fin_reconciliation_checklist_summary_rows_id_seq")
