"""partition reconciliation checklist summary tables

Revision ID: 048_checklist_summary_partition
Revises: 047_checklist_preaggregation
Create Date: 2026-06-05

"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "048_checklist_summary_partition"
down_revision: Union[str, None] = "047_checklist_preaggregation"
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

SUMMARY_COLUMNS = [
    "id",
    "org_id",
    "shop_id",
    "platform_code",
    "shop_name",
    "accounting_year",
    "accounting_month",
    "accounting_period",
    "live_promoter_id",
    "merchant_id",
    "receipt_merchant_id",
    "live_promoter",
    "merchant_name",
    "receipt_merchant",
    "product_quantity",
    "total_order_amount",
    "total_live_commission",
    "total_merchant_net_amount",
    "created_at",
    "updated_at",
]
PRODUCT_COLUMNS = [
    *SUMMARY_COLUMNS[:14],
    "product_name",
    *SUMMARY_COLUMNS[14:],
]


def _table_exists(table_name: str) -> bool:
    return bool(op.get_bind().scalar(sa.text("SELECT to_regclass(:table_name) IS NOT NULL"), {"table_name": table_name}))


def _is_partitioned(table_name: str) -> bool:
    return bool(
        op.get_bind().scalar(
            sa.text(
                """
                SELECT EXISTS (
                    SELECT 1
                    FROM pg_partitioned_table
                    WHERE partrelid = to_regclass(:table_name)
                )
                """
            ),
            {"table_name": table_name},
        )
    )


def _next_yyyymm(period: int) -> int:
    year = period // 100
    month = period % 100
    if month == 12:
        return (year + 1) * 100 + 1
    return year * 100 + month + 1


def _summary_columns(*, include_product: bool, sequence_name: str) -> list[sa.Column | sa.ForeignKeyConstraint | sa.PrimaryKeyConstraint]:
    columns: list[sa.Column | sa.ForeignKeyConstraint | sa.PrimaryKeyConstraint] = [
        sa.Column("id", sa.BigInteger(), server_default=sa.text(f"nextval('{sequence_name}'::regclass)"), nullable=False, comment="主键ID"),
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


def _drop_old_indexes_and_primary_key(*, legacy_table: str, product: bool) -> None:
    table_name = "fin_reconciliation_checklist_summary_product_rows" if product else "fin_reconciliation_checklist_summary_rows"
    op.execute(f"ALTER TABLE IF EXISTS {legacy_table} DROP CONSTRAINT IF EXISTS {table_name}_pkey CASCADE")
    op.execute(f"DROP INDEX IF EXISTS uq_fin_reconciliation_checklist_summary_{'product_' if product else ''}row")
    op.execute(f"DROP INDEX IF EXISTS idx_fin_reconciliation_checklist_summary_{'product_' if product else 'row_'}query")


def _create_period_partitions(*, table_name: str, source_table: str) -> None:
    periods = [
        int(row[0])
        for row in op.get_bind().execute(
            sa.text(
                f"""
                SELECT DISTINCT accounting_period
                FROM {source_table}
                WHERE accounting_period IS NOT NULL
                  AND accounting_period > 0
                ORDER BY accounting_period
                """
            )
        )
    ]
    for period in periods:
        op.execute(
            sa.text(
                f"""
                CREATE TABLE IF NOT EXISTS {table_name}_{period}
                PARTITION OF {table_name}
                FOR VALUES FROM ({period}) TO ({_next_yyyymm(period)})
                """
            )
        )


def _copy_rows(*, source_table: str, target_table: str, columns: list[str]) -> None:
    column_sql = ", ".join(columns)
    op.execute(f"INSERT INTO {target_table} ({column_sql}) SELECT {column_sql} FROM {source_table}")


def _set_sequence_value(*, table_name: str, sequence_name: str) -> None:
    op.execute(
        sa.text(
            f"""
            SELECT setval(
                '{sequence_name}',
                COALESCE((SELECT MAX(id) FROM {table_name}), 1),
                EXISTS (SELECT 1 FROM {table_name})
            )
            """
        )
    )
    op.execute(f"ALTER SEQUENCE {sequence_name} OWNED BY {table_name}.id")


def _create_indexes(*, table_name: str, product: bool) -> None:
    if product:
        op.create_index(
            "uq_fin_reconciliation_checklist_summary_product_row",
            table_name,
            [*SUMMARY_DIMENSIONS, "product_name"],
            unique=True,
        )
        op.create_index(
            "idx_fin_reconciliation_checklist_summary_product_query",
            table_name,
            ["org_id", "accounting_period", "merchant_id", "receipt_merchant_id", "live_promoter_id", "product_name"],
        )
        return
    op.create_index(
        "uq_fin_reconciliation_checklist_summary_row",
        table_name,
        SUMMARY_DIMENSIONS,
        unique=True,
    )
    op.create_index(
        "idx_fin_reconciliation_checklist_summary_row_query",
        table_name,
        ["org_id", "accounting_period", "merchant_id", "receipt_merchant_id", "live_promoter_id"],
    )


def _partition_summary_table(*, table_name: str, product: bool) -> None:
    if not _table_exists(table_name) or _is_partitioned(table_name):
        return

    legacy_table = f"{table_name}_legacy_048"
    if _table_exists(legacy_table):
        raise RuntimeError(f"legacy table {legacy_table} already exists")

    sequence_name = f"{table_name}_id_seq"
    op.execute(f"ALTER TABLE {table_name} RENAME TO {legacy_table}")
    _drop_old_indexes_and_primary_key(legacy_table=legacy_table, product=product)

    op.execute(f"CREATE SEQUENCE IF NOT EXISTS {sequence_name}")
    op.create_table(
        table_name,
        *_summary_columns(include_product=product, sequence_name=sequence_name),
        comment="对账清单商品预聚合汇总表" if product else "对账清单预聚合汇总表",
        postgresql_partition_by="RANGE (accounting_period)",
    )
    _create_period_partitions(table_name=table_name, source_table=legacy_table)
    _copy_rows(
        source_table=legacy_table,
        target_table=table_name,
        columns=PRODUCT_COLUMNS if product else SUMMARY_COLUMNS,
    )
    _set_sequence_value(table_name=table_name, sequence_name=sequence_name)
    _create_indexes(table_name=table_name, product=product)
    op.execute(f"DROP TABLE IF EXISTS {legacy_table} CASCADE")


def upgrade() -> None:
    _partition_summary_table(table_name="fin_reconciliation_checklist_summary_rows", product=False)
    _partition_summary_table(table_name="fin_reconciliation_checklist_summary_product_rows", product=True)


def downgrade() -> None:
    # Current 047 creates these tables as partitioned tables, so downgrading from
    # this compatibility revision does not need to rewrite table storage.
    pass
