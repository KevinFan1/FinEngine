"""add douyin dongzhang detail table

Revision ID: 027
Revises: 026
Create Date: 2026-05-27 00:00:00.000000

"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op


revision: str = "027"
down_revision: Union[str, None] = "026"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS fin_douyin_dongzhang_details (
            id BIGSERIAL PRIMARY KEY,
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
    op.execute("COMMENT ON TABLE fin_douyin_dongzhang_details IS 'Douyin 动账核算源明细表'")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS fin_douyin_dongzhang_details")
