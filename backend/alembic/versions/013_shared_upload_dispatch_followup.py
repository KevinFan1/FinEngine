"""follow up shared upload dispatch tables

Revision ID: 013
Revises: 012
Create Date: 2026-05-20 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op


revision: str = "013"
down_revision: Union[str, None] = "012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE fin_transaction_upload_files
        ADD COLUMN IF NOT EXISTS source_upload_file_id BIGINT REFERENCES fin_upload_files(id)
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_fin_transaction_upload_source_file
        ON fin_transaction_upload_files(source_upload_file_id)
        WHERE is_deleted = false AND source_upload_file_id IS NOT NULL
        """
    )

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

    op.execute("ALTER TABLE fin_bic_details DROP CONSTRAINT IF EXISTS fin_bic_details_task_id_fkey")
    op.execute("ALTER TABLE fin_bic_details DROP CONSTRAINT IF EXISTS fin_bic_details_file_id_fkey")
    op.execute(
        """
        ALTER TABLE fin_bic_details
        ADD CONSTRAINT fin_bic_details_task_id_fkey
        FOREIGN KEY (task_id) REFERENCES fin_bic_tasks(id)
        """
    )
    op.execute(
        """
        ALTER TABLE fin_bic_details
        ADD CONSTRAINT fin_bic_details_file_id_fkey
        FOREIGN KEY (file_id) REFERENCES fin_bic_upload_files(id)
        """
    )

    op.execute("ALTER TABLE fin_bic_report_rows DROP CONSTRAINT IF EXISTS fin_bic_report_rows_task_id_fkey")
    op.execute("ALTER TABLE fin_bic_report_rows DROP CONSTRAINT IF EXISTS fin_bic_report_rows_file_id_fkey")
    op.execute(
        """
        ALTER TABLE fin_bic_report_rows
        ADD CONSTRAINT fin_bic_report_rows_task_id_fkey
        FOREIGN KEY (task_id) REFERENCES fin_bic_tasks(id)
        """
    )
    op.execute(
        """
        ALTER TABLE fin_bic_report_rows
        ADD CONSTRAINT fin_bic_report_rows_file_id_fkey
        FOREIGN KEY (file_id) REFERENCES fin_bic_upload_files(id)
        """
    )


def downgrade() -> None:
    op.execute("ALTER TABLE fin_bic_report_rows DROP CONSTRAINT IF EXISTS fin_bic_report_rows_file_id_fkey")
    op.execute("ALTER TABLE fin_bic_report_rows DROP CONSTRAINT IF EXISTS fin_bic_report_rows_task_id_fkey")
    op.execute(
        """
        ALTER TABLE fin_bic_report_rows
        ADD CONSTRAINT fin_bic_report_rows_task_id_fkey
        FOREIGN KEY (task_id) REFERENCES fin_processing_tasks(id)
        """
    )
    op.execute(
        """
        ALTER TABLE fin_bic_report_rows
        ADD CONSTRAINT fin_bic_report_rows_file_id_fkey
        FOREIGN KEY (file_id) REFERENCES fin_upload_files(id)
        """
    )

    op.execute("ALTER TABLE fin_bic_details DROP CONSTRAINT IF EXISTS fin_bic_details_file_id_fkey")
    op.execute("ALTER TABLE fin_bic_details DROP CONSTRAINT IF EXISTS fin_bic_details_task_id_fkey")
    op.execute(
        """
        ALTER TABLE fin_bic_details
        ADD CONSTRAINT fin_bic_details_task_id_fkey
        FOREIGN KEY (task_id) REFERENCES fin_processing_tasks(id)
        """
    )
    op.execute(
        """
        ALTER TABLE fin_bic_details
        ADD CONSTRAINT fin_bic_details_file_id_fkey
        FOREIGN KEY (file_id) REFERENCES fin_upload_files(id)
        """
    )

    op.execute("DROP TABLE IF EXISTS fin_bic_tasks")
    op.execute("DROP TABLE IF EXISTS fin_bic_upload_files")
    op.execute("DROP INDEX IF EXISTS uq_fin_transaction_upload_source_file")
    op.execute("ALTER TABLE fin_transaction_upload_files DROP COLUMN IF EXISTS source_upload_file_id")
