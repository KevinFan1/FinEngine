"""partition bic and douyin source detail tables

Revision ID: 032
Revises: 031
Create Date: 2026-05-28 00:00:00.000000

"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
from sqlalchemy import text


revision: str = "032"
down_revision: Union[str, None] = "031"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


BIC_LEGACY_TABLE = "fin_bic_source_rows_legacy_032"
DOUYIN_LEGACY_TABLE = "fin_douyin_dongzhang_details_legacy_032"


def _table_exists(table_name: str) -> bool:
    return bool(
        op.get_bind().execute(text("SELECT to_regclass(:table_name) IS NOT NULL"), {"table_name": table_name}).scalar()
    )


def _is_partitioned(table_name: str) -> bool:
    return bool(
        op.get_bind()
        .execute(
            text(
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
        .scalar()
    )


def upgrade() -> None:
    _partition_bic_source_rows()
    _partition_douyin_dongzhang_details()


def downgrade() -> None:
    _restore_douyin_dongzhang_details()
    _restore_bic_source_rows()


def _partition_bic_source_rows() -> None:
    if _is_partitioned("fin_bic_source_rows"):
        return
    if _table_exists("fin_bic_source_rows"):
        if _table_exists(BIC_LEGACY_TABLE):
            raise RuntimeError(f"legacy table {BIC_LEGACY_TABLE} already exists")
        op.execute(f"ALTER TABLE fin_bic_source_rows RENAME TO {BIC_LEGACY_TABLE}")
    elif not _table_exists(BIC_LEGACY_TABLE):
        return
    op.execute("DROP INDEX IF EXISTS uq_fin_bic_source_platform_flow")
    op.execute("DROP INDEX IF EXISTS idx_fin_bic_source_detail")
    op.execute("DROP INDEX IF EXISTS idx_fin_bic_source_task")
    op.execute("DROP INDEX IF EXISTS idx_fin_bic_source_org_period_provider")
    op.execute("DROP INDEX IF EXISTS idx_fin_bic_source_export")
    op.execute("DROP INDEX IF EXISTS idx_fin_bic_source_filters")

    op.execute("CREATE SEQUENCE IF NOT EXISTS fin_bic_source_rows_id_seq")
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS fin_bic_source_rows (
            id BIGINT NOT NULL DEFAULT nextval('fin_bic_source_rows_id_seq'::regclass),
            task_id BIGINT NOT NULL REFERENCES fin_bic_tasks(id),
            file_id BIGINT NOT NULL REFERENCES fin_bic_upload_files(id),
            detail_id BIGINT NOT NULL REFERENCES fin_bic_details(id),
            org_id BIGINT NOT NULL REFERENCES fin_organizations(id),
            shop_id BIGINT REFERENCES fin_shops(id),
            platform_code VARCHAR(50) NOT NULL,
            shop_name VARCHAR(500) NOT NULL,
            accounting_year SMALLINT NOT NULL,
            accounting_month SMALLINT NOT NULL,
            accounting_period INTEGER NOT NULL,
            service_provider VARCHAR(500) NOT NULL DEFAULT '-',
            qic_warehouse VARCHAR(500) NOT NULL DEFAULT '-',
            source_row_number INTEGER DEFAULT 0,
            settlement_no VARCHAR(500) NOT NULL DEFAULT '',
            order_code VARCHAR(500) NOT NULL DEFAULT '',
            related_order_no VARCHAR(500) NOT NULL DEFAULT '',
            related_waybill_no VARCHAR(500) NOT NULL DEFAULT '',
            fee_item VARCHAR(500) NOT NULL DEFAULT '',
            settlement_amount NUMERIC(14, 2) NOT NULL DEFAULT 0,
            billing_params TEXT NOT NULL DEFAULT '',
            billing_completed_time TIMESTAMP,
            business_node VARCHAR(500) NOT NULL DEFAULT '',
            business_occurred_time TIMESTAMP,
            settled_at TIMESTAMP,
            status VARCHAR(500) NOT NULL DEFAULT '',
            transaction_account VARCHAR(500) NOT NULL DEFAULT '',
            transaction_flow_no VARCHAR(500) NOT NULL DEFAULT '',
            remark TEXT NOT NULL DEFAULT '',
            is_mudaibao VARCHAR(50) NOT NULL DEFAULT '',
            is_child_order VARCHAR(50) NOT NULL DEFAULT '',
            created_at TIMESTAMPTZ DEFAULT now(),
            is_deleted BOOLEAN NOT NULL DEFAULT false,
            deleted_at TIMESTAMPTZ
        ) PARTITION BY RANGE (accounting_period)
        """
    )
    op.execute("ALTER SEQUENCE fin_bic_source_rows_id_seq OWNED BY fin_bic_source_rows.id")
    op.execute("COMMENT ON TABLE fin_bic_source_rows IS 'BIC 源数据明细表'")
    op.execute(
        """
        DO $$
        DECLARE
            period_value INTEGER;
            next_period INTEGER;
            partition_name TEXT;
        BEGIN
            FOR period_value IN
                SELECT DISTINCT accounting_year::INTEGER * 100 + accounting_month::INTEGER
                FROM fin_bic_source_rows_legacy_032
                WHERE accounting_year IS NOT NULL
                  AND accounting_month IS NOT NULL
                  AND accounting_month BETWEEN 1 AND 12
                UNION
                SELECT to_char(month_value, 'YYYYMM')::INTEGER
                FROM generate_series(
                    date_trunc('month', CURRENT_DATE),
                    date_trunc('month', CURRENT_DATE) + interval '12 months',
                    interval '1 month'
                ) AS month_value
            LOOP
                next_period := CASE
                    WHEN period_value % 100 = 12 THEN ((period_value / 100)::INTEGER + 1) * 100 + 1
                    ELSE period_value + 1
                END;
                partition_name := format('fin_bic_source_rows_%s', period_value);
                EXECUTE format(
                    'CREATE TABLE IF NOT EXISTS %I PARTITION OF fin_bic_source_rows FOR VALUES FROM (%s) TO (%s)',
                    partition_name,
                    period_value,
                    next_period
                );
            END LOOP;
            CREATE TABLE IF NOT EXISTS fin_bic_source_rows_default
            PARTITION OF fin_bic_source_rows DEFAULT;
        END $$;
        """
    )
    op.execute(
        """
        DO $$
        DECLARE
            part_name TEXT;
            part_start INTEGER;
            part_end INTEGER;
        BEGIN
            FOR part_start IN
                SELECT DISTINCT accounting_year::INTEGER * 100 + accounting_month::INTEGER
                FROM fin_bic_source_rows_legacy_032
                WHERE accounting_year IS NOT NULL
                  AND accounting_month IS NOT NULL
                  AND accounting_month BETWEEN 1 AND 12
            LOOP
                part_name := format('fin_bic_source_rows_%s', part_start);
                part_end := CASE
                    WHEN part_start % 100 = 12 THEN ((part_start / 100)::INTEGER + 1) * 100 + 1
                    ELSE part_start + 1
                END;
                EXECUTE format(
                    'CREATE TABLE IF NOT EXISTS %I PARTITION OF fin_bic_source_rows FOR VALUES FROM (%s) TO (%s)',
                    part_name,
                    part_start,
                    part_end
                );
            END LOOP;
        END $$;
        """
    )
    op.execute(
        """
        INSERT INTO fin_bic_source_rows (
            id,
            task_id,
            file_id,
            detail_id,
            org_id,
            shop_id,
            platform_code,
            shop_name,
            accounting_year,
            accounting_month,
            accounting_period,
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
            id,
            task_id,
            file_id,
            detail_id,
            org_id,
            shop_id,
            platform_code,
            shop_name,
            accounting_year,
            accounting_month,
            accounting_year::INTEGER * 100 + accounting_month::INTEGER,
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
        FROM fin_bic_source_rows_legacy_032
        """
    )
    op.execute(
        """
        SELECT setval(
            'fin_bic_source_rows_id_seq',
            GREATEST(
                COALESCE((SELECT max(id) FROM fin_bic_source_rows), 0),
                COALESCE((SELECT last_value FROM fin_bic_source_rows_id_seq), 0)
            ),
            true
        )
        """
    )
    _create_bic_source_indexes()


def _partition_douyin_dongzhang_details() -> None:
    if _is_partitioned("fin_douyin_dongzhang_details"):
        return
    if _table_exists("fin_douyin_dongzhang_details"):
        if _table_exists(DOUYIN_LEGACY_TABLE):
            raise RuntimeError(f"legacy table {DOUYIN_LEGACY_TABLE} already exists")
        op.execute(f"ALTER TABLE fin_douyin_dongzhang_details RENAME TO {DOUYIN_LEGACY_TABLE}")
    elif not _table_exists(DOUYIN_LEGACY_TABLE):
        return
    op.execute("DROP INDEX IF EXISTS uq_douyin_dongzhang_detail_flow")
    op.execute("DROP INDEX IF EXISTS idx_douyin_dongzhang_detail_summary")
    op.execute("DROP INDEX IF EXISTS idx_douyin_dongzhang_detail_task")
    op.execute("DROP INDEX IF EXISTS idx_douyin_dongzhang_detail_file")
    op.execute("DROP INDEX IF EXISTS idx_douyin_dongzhang_detail_source_period")
    op.execute("DROP INDEX IF EXISTS idx_douyin_dongzhang_detail_summary_period")

    op.execute("CREATE SEQUENCE IF NOT EXISTS fin_douyin_dongzhang_details_id_seq")
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS fin_douyin_dongzhang_details (
            id BIGINT NOT NULL DEFAULT nextval('fin_douyin_dongzhang_details_id_seq'::regclass),
            task_id BIGINT NOT NULL REFERENCES fin_processing_tasks(id),
            file_id BIGINT NOT NULL REFERENCES fin_upload_files(id),
            summary_id BIGINT REFERENCES fin_financial_summaries(id),
            org_id BIGINT NOT NULL REFERENCES fin_organizations(id),
            shop_id BIGINT NOT NULL REFERENCES fin_shops(id),
            source_platform_code VARCHAR(50) NOT NULL,
            report_platform_code VARCHAR(50) NOT NULL,
            shop_name VARCHAR(500) NOT NULL,
            source_year SMALLINT NOT NULL,
            source_month SMALLINT NOT NULL,
            source_period INTEGER NOT NULL,
            summary_year SMALLINT NOT NULL,
            summary_month SMALLINT NOT NULL,
            period_source VARCHAR(100) NOT NULL DEFAULT '',
            source_row_number INTEGER NOT NULL DEFAULT 0,
            transaction_time TIMESTAMP,
            transaction_flow_no VARCHAR(500) NOT NULL DEFAULT '',
            transaction_direction VARCHAR(50) NOT NULL DEFAULT '',
            transaction_amount NUMERIC(14, 2) NOT NULL DEFAULT 0,
            transaction_account VARCHAR(500) NOT NULL DEFAULT '',
            transaction_scene VARCHAR(500) NOT NULL DEFAULT '',
            billing_type VARCHAR(500) NOT NULL DEFAULT '',
            sub_order_no VARCHAR(500) NOT NULL DEFAULT '',
            order_no VARCHAR(500) NOT NULL DEFAULT '',
            after_sale_no VARCHAR(500) NOT NULL DEFAULT '',
            order_time TIMESTAMP,
            product_id VARCHAR(500) NOT NULL DEFAULT '',
            product_name TEXT NOT NULL DEFAULT '',
            author_id VARCHAR(500) NOT NULL DEFAULT '',
            author_name VARCHAR(500) NOT NULL DEFAULT '',
            order_type VARCHAR(200) NOT NULL DEFAULT '',
            order_paid_amount_raw NUMERIC(14, 2) NOT NULL DEFAULT 0,
            shipping_fee NUMERIC(14, 2) NOT NULL DEFAULT 0,
            platform_subsidy_shipping NUMERIC(14, 2) NOT NULL DEFAULT 0,
            platform_subsidy NUMERIC(14, 2) NOT NULL DEFAULT 0,
            other_platform_subsidy NUMERIC(14, 2) NOT NULL DEFAULT 0,
            trade_in_deduction NUMERIC(14, 2) NOT NULL DEFAULT 0,
            gov_subsidy_platform NUMERIC(14, 2) NOT NULL DEFAULT 0,
            author_subsidy NUMERIC(14, 2) NOT NULL DEFAULT 0,
            douyin_pay_subsidy NUMERIC(14, 2) NOT NULL DEFAULT 0,
            douyin_monthly_subsidy NUMERIC(14, 2) NOT NULL DEFAULT 0,
            bank_subsidy NUMERIC(14, 2) NOT NULL DEFAULT 0,
            order_refund_raw NUMERIC(14, 2) NOT NULL DEFAULT 0,
            platform_fee_raw NUMERIC(14, 2) NOT NULL DEFAULT 0,
            commission_raw NUMERIC(14, 2) NOT NULL DEFAULT 0,
            provider_commission_raw NUMERIC(14, 2) NOT NULL DEFAULT 0,
            channel_share NUMERIC(14, 2) NOT NULL DEFAULT 0,
            merchant_fee_raw NUMERIC(14, 2) NOT NULL DEFAULT 0,
            promotion_fee_raw NUMERIC(14, 2) NOT NULL DEFAULT 0,
            other_share NUMERIC(14, 2) NOT NULL DEFAULT 0,
            is_commission_free VARCHAR(50) NOT NULL DEFAULT '',
            commission_free_amount NUMERIC(14, 2) NOT NULL DEFAULT 0,
            merchant_name TEXT NOT NULL DEFAULT '',
            remark TEXT NOT NULL DEFAULT '',
            matched_compensation VARCHAR(500) NOT NULL DEFAULT '',
            refund_to_compensation NUMERIC(14, 2) NOT NULL DEFAULT 0,
            cashback NUMERIC(14, 2) NOT NULL DEFAULT 0,
            order_paid NUMERIC(14, 2) NOT NULL DEFAULT 0,
            refund_amount NUMERIC(14, 2) NOT NULL DEFAULT 0,
            gmv NUMERIC(14, 2) NOT NULL DEFAULT 0,
            platform_income NUMERIC(14, 2) NOT NULL DEFAULT 0,
            platform_fee_positive NUMERIC(14, 2) NOT NULL DEFAULT 0,
            return_cost NUMERIC(14, 2) NOT NULL DEFAULT 0,
            commission_derived NUMERIC(14, 2) NOT NULL DEFAULT 0,
            bic NUMERIC(14, 2) NOT NULL DEFAULT 0,
            insurance_fee NUMERIC(14, 2) NOT NULL DEFAULT 0,
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now(),
            is_deleted BOOLEAN NOT NULL DEFAULT false,
            deleted_at TIMESTAMPTZ
        ) PARTITION BY RANGE (source_period)
        """
    )
    op.execute("ALTER SEQUENCE fin_douyin_dongzhang_details_id_seq OWNED BY fin_douyin_dongzhang_details.id")
    op.execute("COMMENT ON TABLE fin_douyin_dongzhang_details IS 'Douyin 动账核算源明细表'")
    op.execute(
        """
        DO $$
        DECLARE
            period_value INTEGER;
            next_period INTEGER;
            partition_name TEXT;
        BEGIN
            FOR period_value IN
                SELECT DISTINCT source_year::INTEGER * 100 + source_month::INTEGER
                FROM fin_douyin_dongzhang_details_legacy_032
                WHERE source_year IS NOT NULL
                  AND source_month IS NOT NULL
                  AND source_month BETWEEN 1 AND 12
                UNION
                SELECT to_char(month_value, 'YYYYMM')::INTEGER
                FROM generate_series(
                    date_trunc('month', CURRENT_DATE),
                    date_trunc('month', CURRENT_DATE) + interval '12 months',
                    interval '1 month'
                ) AS month_value
            LOOP
                next_period := CASE
                    WHEN period_value % 100 = 12 THEN ((period_value / 100)::INTEGER + 1) * 100 + 1
                    ELSE period_value + 1
                END;
                partition_name := format('fin_douyin_dongzhang_details_%s', period_value);
                EXECUTE format(
                    'CREATE TABLE IF NOT EXISTS %I PARTITION OF fin_douyin_dongzhang_details FOR VALUES FROM (%s) TO (%s)',
                    partition_name,
                    period_value,
                    next_period
                );
            END LOOP;
            CREATE TABLE IF NOT EXISTS fin_douyin_dongzhang_details_default
            PARTITION OF fin_douyin_dongzhang_details DEFAULT;
        END $$;
        """
    )
    op.execute(
        """
        DO $$
        DECLARE
            part_name TEXT;
            part_start INTEGER;
            part_end INTEGER;
        BEGIN
            FOR part_start IN
                SELECT DISTINCT source_year::INTEGER * 100 + source_month::INTEGER
                FROM fin_douyin_dongzhang_details_legacy_032
                WHERE source_year IS NOT NULL
                  AND source_month IS NOT NULL
                  AND source_month BETWEEN 1 AND 12
            LOOP
                part_name := format('fin_douyin_dongzhang_details_%s', part_start);
                part_end := CASE
                    WHEN part_start % 100 = 12 THEN ((part_start / 100)::INTEGER + 1) * 100 + 1
                    ELSE part_start + 1
                END;
                EXECUTE format(
                    'CREATE TABLE IF NOT EXISTS %I PARTITION OF fin_douyin_dongzhang_details FOR VALUES FROM (%s) TO (%s)',
                    part_name,
                    part_start,
                    part_end
                );
            END LOOP;
        END $$;
        """
    )
    op.execute(
        """
        INSERT INTO fin_douyin_dongzhang_details (
            id,
            task_id,
            file_id,
            summary_id,
            org_id,
            shop_id,
            source_platform_code,
            report_platform_code,
            shop_name,
            source_year,
            source_month,
            source_period,
            summary_year,
            summary_month,
            period_source,
            source_row_number,
            transaction_time,
            transaction_flow_no,
            transaction_direction,
            transaction_amount,
            transaction_account,
            transaction_scene,
            billing_type,
            sub_order_no,
            order_no,
            after_sale_no,
            order_time,
            product_id,
            product_name,
            author_id,
            author_name,
            order_type,
            order_paid_amount_raw,
            shipping_fee,
            platform_subsidy_shipping,
            platform_subsidy,
            other_platform_subsidy,
            trade_in_deduction,
            gov_subsidy_platform,
            author_subsidy,
            douyin_pay_subsidy,
            douyin_monthly_subsidy,
            bank_subsidy,
            order_refund_raw,
            platform_fee_raw,
            commission_raw,
            provider_commission_raw,
            channel_share,
            merchant_fee_raw,
            promotion_fee_raw,
            other_share,
            is_commission_free,
            commission_free_amount,
            merchant_name,
            remark,
            matched_compensation,
            refund_to_compensation,
            cashback,
            order_paid,
            refund_amount,
            gmv,
            platform_income,
            platform_fee_positive,
            return_cost,
            commission_derived,
            bic,
            insurance_fee,
            created_at,
            updated_at,
            is_deleted,
            deleted_at
        )
        SELECT
            id,
            task_id,
            file_id,
            summary_id,
            org_id,
            shop_id,
            source_platform_code,
            report_platform_code,
            shop_name,
            source_year,
            source_month,
            source_year::INTEGER * 100 + source_month::INTEGER,
            summary_year,
            summary_month,
            period_source,
            source_row_number,
            transaction_time,
            transaction_flow_no,
            transaction_direction,
            transaction_amount,
            transaction_account,
            transaction_scene,
            billing_type,
            sub_order_no,
            order_no,
            after_sale_no,
            order_time,
            product_id,
            product_name,
            author_id,
            author_name,
            order_type,
            order_paid_amount_raw,
            shipping_fee,
            platform_subsidy_shipping,
            platform_subsidy,
            other_platform_subsidy,
            trade_in_deduction,
            gov_subsidy_platform,
            author_subsidy,
            douyin_pay_subsidy,
            douyin_monthly_subsidy,
            bank_subsidy,
            order_refund_raw,
            platform_fee_raw,
            commission_raw,
            provider_commission_raw,
            channel_share,
            merchant_fee_raw,
            promotion_fee_raw,
            other_share,
            is_commission_free,
            commission_free_amount,
            merchant_name,
            remark,
            matched_compensation,
            refund_to_compensation,
            cashback,
            order_paid,
            refund_amount,
            gmv,
            platform_income,
            platform_fee_positive,
            return_cost,
            commission_derived,
            bic,
            insurance_fee,
            created_at,
            updated_at,
            is_deleted,
            deleted_at
        FROM fin_douyin_dongzhang_details_legacy_032
        """
    )
    op.execute(
        """
        SELECT setval(
            'fin_douyin_dongzhang_details_id_seq',
            GREATEST(
                COALESCE((SELECT max(id) FROM fin_douyin_dongzhang_details), 0),
                COALESCE((SELECT last_value FROM fin_douyin_dongzhang_details_id_seq), 0)
            ),
            true
        )
        """
    )
    _create_douyin_detail_indexes()


def _restore_bic_source_rows() -> None:
    op.execute(
        """
        ALTER TABLE IF EXISTS fin_bic_source_rows RENAME TO fin_bic_source_rows_partitioned_032
        """
    )
    op.execute("CREATE SEQUENCE IF NOT EXISTS fin_bic_source_rows_id_seq")
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS fin_bic_source_rows (
            id BIGINT NOT NULL DEFAULT nextval('fin_bic_source_rows_id_seq'::regclass),
            task_id BIGINT NOT NULL REFERENCES fin_bic_tasks(id),
            file_id BIGINT NOT NULL REFERENCES fin_bic_upload_files(id),
            detail_id BIGINT NOT NULL REFERENCES fin_bic_details(id),
            org_id BIGINT NOT NULL REFERENCES fin_organizations(id),
            shop_id BIGINT REFERENCES fin_shops(id),
            platform_code VARCHAR(50) NOT NULL,
            shop_name VARCHAR(500) NOT NULL,
            accounting_year SMALLINT NOT NULL,
            accounting_month SMALLINT NOT NULL,
            service_provider VARCHAR(500) NOT NULL DEFAULT '-',
            qic_warehouse VARCHAR(500) NOT NULL DEFAULT '-',
            source_row_number INTEGER DEFAULT 0,
            settlement_no VARCHAR(500) NOT NULL DEFAULT '',
            order_code VARCHAR(500) NOT NULL DEFAULT '',
            related_order_no VARCHAR(500) NOT NULL DEFAULT '',
            related_waybill_no VARCHAR(500) NOT NULL DEFAULT '',
            fee_item VARCHAR(500) NOT NULL DEFAULT '',
            settlement_amount NUMERIC(14, 2) NOT NULL DEFAULT 0,
            billing_params TEXT NOT NULL DEFAULT '',
            billing_completed_time TIMESTAMP,
            business_node VARCHAR(500) NOT NULL DEFAULT '',
            business_occurred_time TIMESTAMP,
            settled_at TIMESTAMP,
            status VARCHAR(500) NOT NULL DEFAULT '',
            transaction_account VARCHAR(500) NOT NULL DEFAULT '',
            transaction_flow_no VARCHAR(500) NOT NULL DEFAULT '',
            remark TEXT NOT NULL DEFAULT '',
            is_mudaibao VARCHAR(50) NOT NULL DEFAULT '',
            is_child_order VARCHAR(50) NOT NULL DEFAULT '',
            created_at TIMESTAMPTZ DEFAULT now(),
            is_deleted BOOLEAN NOT NULL DEFAULT false,
            deleted_at TIMESTAMPTZ
        )
        """
    )
    op.execute(
        """
        INSERT INTO fin_bic_source_rows
        SELECT
            id,
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
        FROM fin_bic_source_rows_partitioned_032
        """
    )
    op.execute("DROP TABLE IF EXISTS fin_bic_source_rows_partitioned_032 CASCADE")
    op.execute("DROP TABLE IF EXISTS fin_bic_source_rows_legacy_032 CASCADE")
    op.execute("ALTER TABLE fin_bic_source_rows ADD PRIMARY KEY (id)")
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


def _restore_douyin_dongzhang_details() -> None:
    op.execute(
        """
        ALTER TABLE IF EXISTS fin_douyin_dongzhang_details RENAME TO fin_douyin_dongzhang_details_partitioned_032
        """
    )
    op.execute("CREATE SEQUENCE IF NOT EXISTS fin_douyin_dongzhang_details_id_seq")
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS fin_douyin_dongzhang_details (
            id BIGINT NOT NULL DEFAULT nextval('fin_douyin_dongzhang_details_id_seq'::regclass),
            task_id BIGINT NOT NULL REFERENCES fin_processing_tasks(id),
            file_id BIGINT NOT NULL REFERENCES fin_upload_files(id),
            summary_id BIGINT REFERENCES fin_financial_summaries(id),
            org_id BIGINT NOT NULL REFERENCES fin_organizations(id),
            shop_id BIGINT NOT NULL REFERENCES fin_shops(id),
            source_platform_code VARCHAR(50) NOT NULL,
            report_platform_code VARCHAR(50) NOT NULL,
            shop_name VARCHAR(500) NOT NULL,
            source_year SMALLINT NOT NULL,
            source_month SMALLINT NOT NULL,
            summary_year SMALLINT NOT NULL,
            summary_month SMALLINT NOT NULL,
            period_source VARCHAR(100) NOT NULL DEFAULT '',
            source_row_number INTEGER NOT NULL DEFAULT 0,
            transaction_time TIMESTAMP,
            transaction_flow_no VARCHAR(500) NOT NULL DEFAULT '',
            transaction_direction VARCHAR(50) NOT NULL DEFAULT '',
            transaction_amount NUMERIC(14, 2) NOT NULL DEFAULT 0,
            transaction_account VARCHAR(500) NOT NULL DEFAULT '',
            transaction_scene VARCHAR(500) NOT NULL DEFAULT '',
            billing_type VARCHAR(500) NOT NULL DEFAULT '',
            sub_order_no VARCHAR(500) NOT NULL DEFAULT '',
            order_no VARCHAR(500) NOT NULL DEFAULT '',
            after_sale_no VARCHAR(500) NOT NULL DEFAULT '',
            order_time TIMESTAMP,
            product_id VARCHAR(500) NOT NULL DEFAULT '',
            product_name TEXT NOT NULL DEFAULT '',
            author_id VARCHAR(500) NOT NULL DEFAULT '',
            author_name VARCHAR(500) NOT NULL DEFAULT '',
            order_type VARCHAR(200) NOT NULL DEFAULT '',
            order_paid_amount_raw NUMERIC(14, 2) NOT NULL DEFAULT 0,
            shipping_fee NUMERIC(14, 2) NOT NULL DEFAULT 0,
            platform_subsidy_shipping NUMERIC(14, 2) NOT NULL DEFAULT 0,
            platform_subsidy NUMERIC(14, 2) NOT NULL DEFAULT 0,
            other_platform_subsidy NUMERIC(14, 2) NOT NULL DEFAULT 0,
            trade_in_deduction NUMERIC(14, 2) NOT NULL DEFAULT 0,
            gov_subsidy_platform NUMERIC(14, 2) NOT NULL DEFAULT 0,
            author_subsidy NUMERIC(14, 2) NOT NULL DEFAULT 0,
            douyin_pay_subsidy NUMERIC(14, 2) NOT NULL DEFAULT 0,
            douyin_monthly_subsidy NUMERIC(14, 2) NOT NULL DEFAULT 0,
            bank_subsidy NUMERIC(14, 2) NOT NULL DEFAULT 0,
            order_refund_raw NUMERIC(14, 2) NOT NULL DEFAULT 0,
            platform_fee_raw NUMERIC(14, 2) NOT NULL DEFAULT 0,
            commission_raw NUMERIC(14, 2) NOT NULL DEFAULT 0,
            provider_commission_raw NUMERIC(14, 2) NOT NULL DEFAULT 0,
            channel_share NUMERIC(14, 2) NOT NULL DEFAULT 0,
            merchant_fee_raw NUMERIC(14, 2) NOT NULL DEFAULT 0,
            promotion_fee_raw NUMERIC(14, 2) NOT NULL DEFAULT 0,
            other_share NUMERIC(14, 2) NOT NULL DEFAULT 0,
            is_commission_free VARCHAR(50) NOT NULL DEFAULT '',
            commission_free_amount NUMERIC(14, 2) NOT NULL DEFAULT 0,
            merchant_name TEXT NOT NULL DEFAULT '',
            remark TEXT NOT NULL DEFAULT '',
            matched_compensation VARCHAR(500) NOT NULL DEFAULT '',
            refund_to_compensation NUMERIC(14, 2) NOT NULL DEFAULT 0,
            cashback NUMERIC(14, 2) NOT NULL DEFAULT 0,
            order_paid NUMERIC(14, 2) NOT NULL DEFAULT 0,
            refund_amount NUMERIC(14, 2) NOT NULL DEFAULT 0,
            gmv NUMERIC(14, 2) NOT NULL DEFAULT 0,
            platform_income NUMERIC(14, 2) NOT NULL DEFAULT 0,
            platform_fee_positive NUMERIC(14, 2) NOT NULL DEFAULT 0,
            return_cost NUMERIC(14, 2) NOT NULL DEFAULT 0,
            commission_derived NUMERIC(14, 2) NOT NULL DEFAULT 0,
            bic NUMERIC(14, 2) NOT NULL DEFAULT 0,
            insurance_fee NUMERIC(14, 2) NOT NULL DEFAULT 0,
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now(),
            is_deleted BOOLEAN NOT NULL DEFAULT false,
            deleted_at TIMESTAMPTZ
        )
        """
    )
    op.execute(
        """
        INSERT INTO fin_douyin_dongzhang_details
        SELECT
            id,
            task_id,
            file_id,
            summary_id,
            org_id,
            shop_id,
            source_platform_code,
            report_platform_code,
            shop_name,
            source_year,
            source_month,
            summary_year,
            summary_month,
            period_source,
            source_row_number,
            transaction_time,
            transaction_flow_no,
            transaction_direction,
            transaction_amount,
            transaction_account,
            transaction_scene,
            billing_type,
            sub_order_no,
            order_no,
            after_sale_no,
            order_time,
            product_id,
            product_name,
            author_id,
            author_name,
            order_type,
            order_paid_amount_raw,
            shipping_fee,
            platform_subsidy_shipping,
            platform_subsidy,
            other_platform_subsidy,
            trade_in_deduction,
            gov_subsidy_platform,
            author_subsidy,
            douyin_pay_subsidy,
            douyin_monthly_subsidy,
            bank_subsidy,
            order_refund_raw,
            platform_fee_raw,
            commission_raw,
            provider_commission_raw,
            channel_share,
            merchant_fee_raw,
            promotion_fee_raw,
            other_share,
            is_commission_free,
            commission_free_amount,
            merchant_name,
            remark,
            matched_compensation,
            refund_to_compensation,
            cashback,
            order_paid,
            refund_amount,
            gmv,
            platform_income,
            platform_fee_positive,
            return_cost,
            commission_derived,
            bic,
            insurance_fee,
            created_at,
            updated_at,
            is_deleted,
            deleted_at
        FROM fin_douyin_dongzhang_details_partitioned_032
        """
    )
    op.execute("DROP TABLE IF EXISTS fin_douyin_dongzhang_details_partitioned_032 CASCADE")
    op.execute("DROP TABLE IF EXISTS fin_douyin_dongzhang_details_legacy_032 CASCADE")
    op.execute("ALTER TABLE fin_douyin_dongzhang_details ADD PRIMARY KEY (id)")
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_douyin_dongzhang_detail_flow
        ON fin_douyin_dongzhang_details (
            org_id,
            source_platform_code,
            shop_id,
            source_year,
            source_month,
            transaction_flow_no
        )
        WHERE is_deleted = false AND transaction_flow_no <> ''
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_douyin_dongzhang_detail_summary
        ON fin_douyin_dongzhang_details (summary_id)
        WHERE is_deleted = false
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_douyin_dongzhang_detail_task ON fin_douyin_dongzhang_details(task_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_douyin_dongzhang_detail_file ON fin_douyin_dongzhang_details(file_id)")
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_douyin_dongzhang_detail_source_period
        ON fin_douyin_dongzhang_details (
            org_id,
            source_platform_code,
            shop_id,
            source_year,
            source_month
        )
        WHERE is_deleted = false
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_douyin_dongzhang_detail_summary_period
        ON fin_douyin_dongzhang_details (
            org_id,
            source_platform_code,
            shop_id,
            summary_year,
            summary_month
        )
        WHERE is_deleted = false
        """
    )


def _create_bic_source_indexes() -> None:
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_fin_bic_source_platform_flow
        ON fin_bic_source_rows(accounting_period, platform_code, transaction_flow_no)
        WHERE is_deleted = false AND transaction_flow_no <> ''
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_fin_bic_source_id ON fin_bic_source_rows(id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_fin_bic_source_detail ON fin_bic_source_rows(detail_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_fin_bic_source_task ON fin_bic_source_rows(task_id)")
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_fin_bic_source_org_period_provider
        ON fin_bic_source_rows(org_id, accounting_period, service_provider)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_fin_bic_source_export
        ON fin_bic_source_rows(org_id, accounting_period, service_provider, shop_id, qic_warehouse)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_fin_bic_source_filters
        ON fin_bic_source_rows(org_id, platform_code, accounting_period, shop_id, qic_warehouse, service_provider)
        WHERE is_deleted = false
        """
    )


def _create_douyin_detail_indexes() -> None:
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_douyin_dongzhang_detail_flow
        ON fin_douyin_dongzhang_details (
            org_id,
            source_platform_code,
            shop_id,
            source_period,
            transaction_flow_no
        )
        WHERE is_deleted = false AND transaction_flow_no <> ''
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_douyin_dongzhang_detail_id ON fin_douyin_dongzhang_details(id)")
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_douyin_dongzhang_detail_summary
        ON fin_douyin_dongzhang_details (summary_id)
        WHERE is_deleted = false
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_douyin_dongzhang_detail_task ON fin_douyin_dongzhang_details(task_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_douyin_dongzhang_detail_file ON fin_douyin_dongzhang_details(file_id)")
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_douyin_dongzhang_detail_source_period
        ON fin_douyin_dongzhang_details (
            org_id,
            source_platform_code,
            shop_id,
            source_period
        )
        WHERE is_deleted = false
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_douyin_dongzhang_detail_summary_period
        ON fin_douyin_dongzhang_details (
            org_id,
            source_platform_code,
            shop_id,
            summary_year,
            summary_month
        )
        WHERE is_deleted = false
        """
    )
