"""Add platform hierarchy fields

Revision ID: 002
Revises: 001
Create Date: 2026-05-09 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def add_column_if_not_exists(table_name: str, column_name: str, column_sql: str, comment: str) -> None:
    op.execute(f"ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS {column_name} {column_sql}")
    op.execute(f"COMMENT ON COLUMN {table_name}.{column_name} IS '{comment}'")


def upgrade() -> None:
    add_column_if_not_exists("fin_platforms", "parent_code", "VARCHAR(30)", "父平台编码，用于汇总报表归集")
    add_column_if_not_exists("fin_platforms", "processor_code", "VARCHAR(30)", "处理器平台编码，默认等于平台编码")
    add_column_if_not_exists("fin_platforms", "order_scope_code", "VARCHAR(30)", "订单索引归属编码，默认等于父平台编码")

    op.execute(
        """
        UPDATE fin_platforms
        SET
            parent_code = COALESCE(parent_code, CASE WHEN code IN ('tmall', 'alipay', 'qianniu') THEN 'taobao' ELSE code END),
            processor_code = COALESCE(processor_code, code),
            order_scope_code = COALESCE(order_scope_code, CASE WHEN code IN ('tmall', 'alipay', 'qianniu') THEN 'taobao' ELSE code END)
        WHERE is_deleted = false
            AND (parent_code IS NULL OR processor_code IS NULL OR order_scope_code IS NULL)
        """
    )
    op.execute(
        """
        INSERT INTO fin_platforms
            (code, name, parent_code, processor_code, order_scope_code, sort_order, status, is_deleted, created_at)
        VALUES
            ('alipay', '支付宝', 'taobao', 'alipay', 'taobao', 6, 1, false, now()),
            ('qianniu', '千牛', 'taobao', 'qianniu', 'taobao', 7, 1, false, now())
        ON CONFLICT DO NOTHING
        """
    )

    add_column_if_not_exists("fin_upload_files", "source_platform_code", "VARCHAR(30)", "来源子平台编码")
    add_column_if_not_exists("fin_upload_files", "report_platform_code", "VARCHAR(30)", "归集父平台编码")
    add_column_if_not_exists("fin_upload_files", "processor_code", "VARCHAR(30)", "处理器平台编码")
    add_column_if_not_exists("fin_upload_files", "order_scope_code", "VARCHAR(30)", "订单索引归属编码")
    op.execute(
        """
        UPDATE fin_upload_files
        SET
            source_platform_code = COALESCE(source_platform_code, detected_platform),
            report_platform_code = COALESCE(report_platform_code, CASE WHEN detected_platform IN ('tmall', 'alipay', 'qianniu') THEN 'taobao' ELSE detected_platform END),
            processor_code = COALESCE(processor_code, detected_platform),
            order_scope_code = COALESCE(order_scope_code, CASE WHEN detected_platform IN ('tmall', 'alipay', 'qianniu') THEN 'taobao' ELSE detected_platform END)
        WHERE detected_platform IS NOT NULL
            AND (
                source_platform_code IS NULL
                OR report_platform_code IS NULL
                OR processor_code IS NULL
                OR order_scope_code IS NULL
            )
        """
    )

    add_column_if_not_exists("fin_financial_summaries", "source_platform_code", "VARCHAR(50)", "来源子平台编码，用于汇总明细")
    add_column_if_not_exists("fin_financial_summaries", "report_platform_code", "VARCHAR(50)", "归集父平台编码，用于汇总报表")
    op.execute(
        """
        UPDATE fin_financial_summaries
        SET
            source_platform_code = COALESCE(source_platform_code, platform_name),
            report_platform_code = COALESCE(report_platform_code, CASE WHEN platform_name IN ('tmall', 'alipay', 'qianniu') THEN 'taobao' ELSE platform_name END)
        WHERE source_platform_code IS NULL OR report_platform_code IS NULL
        """
    )
    op.alter_column("fin_financial_summaries", "source_platform_code", nullable=False)
    op.alter_column("fin_financial_summaries", "report_platform_code", nullable=False)

    op.drop_index("uq_fin_summary_lookup", table_name="fin_financial_summaries", if_exists=True)
    op.create_index(
        "uq_fin_summary_lookup",
        "fin_financial_summaries",
        ["org_id", "summary_year", "summary_month", "shop_id", "source_platform_code", "source_year", "source_month"],
        unique=True,
        postgresql_where=sa.text("is_deleted = false"),
        if_not_exists=True,
    )
    op.create_index("idx_fin_summaries_source_platform", "fin_financial_summaries", ["org_id", "source_platform_code"], if_not_exists=True)
    op.create_index("idx_fin_summaries_report_platform", "fin_financial_summaries", ["org_id", "report_platform_code"], if_not_exists=True)


def downgrade() -> None:
    op.drop_index("idx_fin_summaries_report_platform", table_name="fin_financial_summaries")
    op.drop_index("idx_fin_summaries_source_platform", table_name="fin_financial_summaries")
    op.drop_index("uq_fin_summary_lookup", table_name="fin_financial_summaries")
    op.create_index(
        "uq_fin_summary_lookup",
        "fin_financial_summaries",
        ["org_id", "summary_year", "summary_month", "shop_id", "source_year", "source_month"],
        unique=True,
        postgresql_where=sa.text("is_deleted = false"),
    )
    op.drop_column("fin_financial_summaries", "report_platform_code")
    op.drop_column("fin_financial_summaries", "source_platform_code")

    op.drop_column("fin_upload_files", "order_scope_code")
    op.drop_column("fin_upload_files", "processor_code")
    op.drop_column("fin_upload_files", "report_platform_code")
    op.drop_column("fin_upload_files", "source_platform_code")

    op.drop_column("fin_platforms", "order_scope_code")
    op.drop_column("fin_platforms", "processor_code")
    op.drop_column("fin_platforms", "parent_code")
