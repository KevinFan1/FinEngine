"""add bic source rows and drop bic report rows

Revision ID: 026
Revises: 025
Create Date: 2026-05-26 00:00:00.000000

"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op


revision: str = "026"
down_revision: Union[str, None] = "025"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS fin_bic_source_rows (
            id BIGSERIAL PRIMARY KEY,
            task_id BIGINT NOT NULL REFERENCES fin_bic_tasks(id),
            file_id BIGINT NOT NULL REFERENCES fin_bic_upload_files(id),
            detail_id BIGINT NOT NULL REFERENCES fin_bic_details(id),
            org_id BIGINT NOT NULL REFERENCES fin_organizations(id),
            shop_id BIGINT REFERENCES fin_shops(id),
            platform_code VARCHAR(50) NOT NULL,
            shop_name VARCHAR(200) NOT NULL,
            accounting_year SMALLINT NOT NULL,
            accounting_month SMALLINT NOT NULL,
            service_provider VARCHAR(200) NOT NULL DEFAULT '-',
            qic_warehouse VARCHAR(200) NOT NULL DEFAULT '-',
            source_row_number INTEGER DEFAULT 0,
            settlement_no VARCHAR(300) NOT NULL DEFAULT '',
            order_code VARCHAR(100) NOT NULL DEFAULT '',
            related_order_no VARCHAR(100) NOT NULL DEFAULT '',
            related_waybill_no VARCHAR(100) NOT NULL DEFAULT '',
            fee_item VARCHAR(100) NOT NULL DEFAULT '',
            settlement_amount NUMERIC(14, 2) NOT NULL DEFAULT 0,
            billing_params TEXT NOT NULL DEFAULT '',
            billing_completed_time VARCHAR(100) NOT NULL DEFAULT '',
            business_node VARCHAR(100) NOT NULL DEFAULT '',
            business_occurred_time VARCHAR(100) NOT NULL DEFAULT '',
            settled_at VARCHAR(100) NOT NULL DEFAULT '',
            status VARCHAR(100) NOT NULL DEFAULT '',
            transaction_account VARCHAR(100) NOT NULL DEFAULT '',
            transaction_flow_no VARCHAR(200) NOT NULL DEFAULT '',
            remark TEXT NOT NULL DEFAULT '',
            is_mudaibao VARCHAR(20) NOT NULL DEFAULT '',
            is_child_order VARCHAR(20) NOT NULL DEFAULT '',
            created_at TIMESTAMPTZ DEFAULT now(),
            is_deleted BOOLEAN NOT NULL DEFAULT false,
            deleted_at TIMESTAMPTZ
        )
        """
    )

    op.execute(
        """
        INSERT INTO fin_bic_source_rows (
            task_id,
            file_id,
            detail_id,
            org_id,
            shop_id,
            platform_code,
            shop_name,
            accounting_year,
            accounting_month,
            service_provider,
            qic_warehouse,
            source_row_number,
            settlement_no,
            order_code,
            related_order_no,
            related_waybill_no,
            fee_item,
            settlement_amount,
            billing_params,
            billing_completed_time,
            business_node,
            business_occurred_time,
            settled_at,
            status,
            transaction_account,
            transaction_flow_no,
            remark,
            is_mudaibao,
            is_child_order,
            created_at,
            is_deleted,
            deleted_at
        )
        SELECT
            d.task_id,
            d.file_id,
            d.id,
            d.org_id,
            d.shop_id,
            d.platform_code,
            d.shop_name,
            d.accounting_year,
            d.accounting_month,
            COALESCE(NULLIF(raw_row->>'服务商', ''), d.service_provider, '-'),
            COALESCE(NULLIF(raw_row->>'QIC仓', ''), d.qic_warehouse, '-'),
            raw_item.ordinality::INTEGER,
            COALESCE(raw_row->>'结算单号', ''),
            COALESCE(raw_row->>'订单码', ''),
            COALESCE(raw_row->>'关联订单号', ''),
            COALESCE(raw_row->>'关联运单号', ''),
            COALESCE(raw_row->>'费用项', ''),
            CASE
                WHEN replace(COALESCE(raw_row->>'结算金额', '0'), ',', '') ~ '^-?[0-9]+(\\.[0-9]+)?$'
                THEN replace(COALESCE(raw_row->>'结算金额', '0'), ',', '')::NUMERIC(14, 2)
                ELSE 0
            END,
            COALESCE(raw_row->>'计费参数', ''),
            COALESCE(raw_row->>'计费完成时间', ''),
            COALESCE(raw_row->>'业务节点', ''),
            COALESCE(raw_row->>'业务发生时间', ''),
            COALESCE(raw_row->>'结算时间', ''),
            COALESCE(raw_row->>'状态', ''),
            COALESCE(raw_row->>'动账账户', ''),
            COALESCE(raw_row->>'动账流水号', ''),
            COALESCE(raw_row->>'备注', ''),
            COALESCE(raw_row->>'是否木带宝', ''),
            COALESCE(raw_row->>'是否子单', ''),
            d.created_at,
            d.is_deleted,
            d.deleted_at
        FROM fin_bic_details AS d
        CROSS JOIN LATERAL jsonb_array_elements(
            CASE
                WHEN d.raw_rows IS NOT NULL AND jsonb_typeof(d.raw_rows) = 'array'
                THEN d.raw_rows
                ELSE '[]'::jsonb
            END
        ) WITH ORDINALITY AS raw_item(raw_row, ordinality)
        """
    )

    op.execute(
        """
        WITH ranked AS (
            SELECT
                id,
                row_number() OVER (
                    PARTITION BY platform_code, transaction_flow_no
                    ORDER BY is_deleted ASC, task_id DESC, id DESC
                ) AS row_rank
            FROM fin_bic_source_rows
            WHERE transaction_flow_no <> ''
        )
        DELETE FROM fin_bic_source_rows AS source_row
        USING ranked
        WHERE ranked.id = source_row.id
          AND ranked.row_rank > 1
        """
    )

    op.execute("CREATE INDEX IF NOT EXISTS idx_fin_bic_source_detail ON fin_bic_source_rows(detail_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_fin_bic_source_task ON fin_bic_source_rows(task_id)")
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_fin_bic_source_org_period_provider
        ON fin_bic_source_rows(org_id, accounting_year, accounting_month, service_provider)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_fin_bic_source_export
        ON fin_bic_source_rows(org_id, accounting_year, accounting_month, service_provider, shop_id, qic_warehouse)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_fin_bic_source_filters
        ON fin_bic_source_rows(org_id, platform_code, accounting_year, accounting_month, shop_id, qic_warehouse, service_provider)
        WHERE is_deleted = false
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_fin_bic_source_platform_flow
        ON fin_bic_source_rows(platform_code, transaction_flow_no)
        WHERE is_deleted = false AND transaction_flow_no <> ''
        """
    )
    op.execute("COMMENT ON TABLE fin_bic_source_rows IS 'BIC 源数据明细表'")

    op.execute("DROP TABLE IF EXISTS fin_bic_report_rows")
    op.execute("ALTER TABLE fin_bic_details DROP COLUMN IF EXISTS raw_rows")
    op.execute(
        """
        UPDATE fin_bic_tasks
        SET result_summary =
            COALESCE(result_summary, '{}'::jsonb)
            - 'report_groups'
            - 'report_ids'
            - 'report_id'
            - '报表分组数'
            - '报表记录ID列表'
            - '首个报表记录ID'
        WHERE result_summary IS NOT NULL
          AND result_summary ?| ARRAY[
            'report_groups',
            'report_ids',
            'report_id',
            '报表分组数',
            '报表记录ID列表',
            '首个报表记录ID'
          ]
        """
    )


def downgrade() -> None:
    op.execute("ALTER TABLE fin_bic_details ADD COLUMN IF NOT EXISTS raw_rows JSONB")
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS fin_bic_report_rows (
            id BIGSERIAL PRIMARY KEY,
            task_id BIGINT NOT NULL REFERENCES fin_bic_tasks(id),
            file_id BIGINT NOT NULL REFERENCES fin_bic_upload_files(id),
            org_id BIGINT NOT NULL REFERENCES fin_organizations(id),
            shop_id BIGINT REFERENCES fin_shops(id),
            platform_code VARCHAR(50) NOT NULL,
            shop_name VARCHAR(200) NOT NULL,
            accounting_year SMALLINT NOT NULL,
            accounting_month SMALLINT NOT NULL,
            service_provider VARCHAR(200) NOT NULL DEFAULT '-',
            row_count INTEGER DEFAULT 0,
            total_amount NUMERIC(14, 2) DEFAULT 0,
            created_at TIMESTAMPTZ DEFAULT now(),
            is_deleted BOOLEAN NOT NULL DEFAULT false,
            deleted_at TIMESTAMPTZ
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_fin_bic_report_task ON fin_bic_report_rows(task_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_fin_bic_report_org_period ON fin_bic_report_rows(org_id, accounting_year, accounting_month)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_fin_bic_report_provider ON fin_bic_report_rows(service_provider)")
    op.execute("DROP TABLE IF EXISTS fin_bic_source_rows")
