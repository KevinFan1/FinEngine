"""add bic accounting tables

Revision ID: 012
Revises: 011
Create Date: 2026-05-20 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op


revision: str = "012"
down_revision: Union[str, None] = "011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS fin_bic_upload_files (
            id BIGSERIAL PRIMARY KEY,
            org_id BIGINT NOT NULL REFERENCES fin_organizations(id),
            user_id BIGINT NOT NULL REFERENCES fin_users(id),
            source_upload_file_id BIGINT REFERENCES fin_upload_files(id),
            original_name VARCHAR(500) NOT NULL,
            oss_key VARCHAR(1000) NOT NULL DEFAULT '',
            file_size BIGINT NOT NULL DEFAULT 0,
            file_hash VARCHAR(64),
            platform_code VARCHAR(50),
            shop_name VARCHAR(200),
            accounting_year SMALLINT,
            accounting_month SMALLINT,
            status VARCHAR(20) NOT NULL DEFAULT 'initialized',
            error_message TEXT,
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now(),
            is_deleted BOOLEAN NOT NULL DEFAULT false,
            deleted_at TIMESTAMPTZ
        )
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_fin_bic_upload_source_file
        ON fin_bic_upload_files(source_upload_file_id)
        WHERE is_deleted = false AND source_upload_file_id IS NOT NULL
        """
    )
    op.execute("COMMENT ON TABLE fin_bic_upload_files IS 'BIC 独立上传文件表'")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS fin_bic_tasks (
            id BIGSERIAL PRIMARY KEY,
            file_id BIGINT NOT NULL REFERENCES fin_bic_upload_files(id),
            org_id BIGINT NOT NULL REFERENCES fin_organizations(id),
            user_id BIGINT NOT NULL REFERENCES fin_users(id),
            celery_task_id VARCHAR(200),
            status VARCHAR(20) NOT NULL DEFAULT 'queued',
            progress SMALLINT NOT NULL DEFAULT 0,
            processed_rows INTEGER NOT NULL DEFAULT 0,
            success_rows INTEGER NOT NULL DEFAULT 0,
            failed_rows INTEGER NOT NULL DEFAULT 0,
            error_message TEXT,
            result_summary JSONB,
            started_at TIMESTAMPTZ,
            finished_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now(),
            is_deleted BOOLEAN NOT NULL DEFAULT false,
            deleted_at TIMESTAMPTZ
        )
        """
    )
    op.execute("COMMENT ON TABLE fin_bic_tasks IS 'BIC 独立任务表'")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS fin_bic_details (
            id BIGSERIAL PRIMARY KEY,
            task_id BIGINT NOT NULL REFERENCES fin_bic_tasks(id),
            file_id BIGINT NOT NULL REFERENCES fin_bic_upload_files(id),
            org_id BIGINT NOT NULL REFERENCES fin_organizations(id),
            platform_code VARCHAR(50) NOT NULL,
            shop_name VARCHAR(200) NOT NULL,
            accounting_year SMALLINT NOT NULL,
            accounting_month SMALLINT NOT NULL,
            qic_warehouse VARCHAR(200) NOT NULL,
            row_count INTEGER DEFAULT 0,
            total_amount NUMERIC(14, 2) DEFAULT 0,
            raw_rows JSONB,
            created_at TIMESTAMPTZ DEFAULT now(),
            is_deleted BOOLEAN NOT NULL DEFAULT false,
            deleted_at TIMESTAMPTZ
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_fin_bic_details_task ON fin_bic_details(task_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_fin_bic_details_org_period ON fin_bic_details(org_id, accounting_year, accounting_month)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_fin_bic_details_qic ON fin_bic_details(qic_warehouse)")
    op.execute("COMMENT ON TABLE fin_bic_details IS 'BIC 核算明细汇总表'")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS fin_bic_report_rows (
            id BIGSERIAL PRIMARY KEY,
            task_id BIGINT NOT NULL REFERENCES fin_bic_tasks(id),
            file_id BIGINT NOT NULL REFERENCES fin_bic_upload_files(id),
            org_id BIGINT NOT NULL REFERENCES fin_organizations(id),
            platform_code VARCHAR(50) NOT NULL,
            shop_name VARCHAR(200) NOT NULL,
            accounting_year SMALLINT NOT NULL,
            accounting_month SMALLINT NOT NULL,
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
    op.execute("COMMENT ON TABLE fin_bic_report_rows IS 'BIC 核算报表汇总表'")


def downgrade() -> None:
    op.drop_table("fin_bic_report_rows")
    op.drop_table("fin_bic_details")
    op.drop_table("fin_bic_tasks")
    op.drop_table("fin_bic_upload_files")
