"""use shop_id business keys for accounting detail uploads

Revision ID: 015
Revises: 014
Create Date: 2026-05-21 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op


revision: str = "015"
down_revision: Union[str, None] = "014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    _add_shop_id_columns()
    _backfill_shop_ids()
    _soft_delete_duplicate_uploads()
    _create_business_key_indexes()


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_fin_bic_upload_business_key")
    op.execute("DROP INDEX IF EXISTS uq_fin_transaction_upload_business_key")

    for table_name in (
        "fin_bic_report_rows",
        "fin_bic_details",
        "fin_bic_upload_files",
        "fin_transaction_summary_rows",
        "fin_transaction_details",
        "fin_transaction_upload_files",
    ):
        op.execute(f"ALTER TABLE {table_name} DROP COLUMN IF EXISTS shop_id")


def _add_shop_id_columns() -> None:
    for table_name in (
        "fin_transaction_upload_files",
        "fin_transaction_details",
        "fin_transaction_summary_rows",
        "fin_bic_upload_files",
        "fin_bic_details",
        "fin_bic_report_rows",
    ):
        op.execute(
            f"""
            ALTER TABLE {table_name}
            ADD COLUMN IF NOT EXISTS shop_id BIGINT REFERENCES fin_shops(id)
            """
        )


def _backfill_shop_ids() -> None:
    op.execute(
        """
        UPDATE fin_transaction_upload_files AS f
        SET shop_id = s.id
        FROM fin_shops AS s
        WHERE f.shop_id IS NULL
          AND f.shop_name IS NOT NULL
          AND f.platform_code IS NOT NULL
          AND f.org_id = s.org_id
          AND s.is_deleted = false
          AND s.platform_name = f.platform_code
          AND s.shop_name = f.shop_name
        """
    )
    op.execute(
        """
        UPDATE fin_bic_upload_files AS f
        SET shop_id = s.id
        FROM fin_shops AS s
        WHERE f.shop_id IS NULL
          AND f.shop_name IS NOT NULL
          AND f.platform_code IS NOT NULL
          AND f.org_id = s.org_id
          AND s.is_deleted = false
          AND s.platform_name = f.platform_code
          AND s.shop_name = f.shop_name
        """
    )

    op.execute(
        """
        UPDATE fin_transaction_details AS d
        SET shop_id = f.shop_id
        FROM fin_transaction_upload_files AS f
        WHERE d.shop_id IS NULL
          AND d.file_id = f.id
          AND f.shop_id IS NOT NULL
        """
    )
    op.execute(
        """
        UPDATE fin_transaction_summary_rows AS r
        SET shop_id = f.shop_id
        FROM fin_transaction_upload_files AS f
        WHERE r.shop_id IS NULL
          AND r.file_id = f.id
          AND f.shop_id IS NOT NULL
        """
    )
    op.execute(
        """
        UPDATE fin_bic_details AS d
        SET shop_id = f.shop_id
        FROM fin_bic_upload_files AS f
        WHERE d.shop_id IS NULL
          AND d.file_id = f.id
          AND f.shop_id IS NOT NULL
        """
    )
    op.execute(
        """
        UPDATE fin_bic_report_rows AS r
        SET shop_id = f.shop_id
        FROM fin_bic_upload_files AS f
        WHERE r.shop_id IS NULL
          AND r.file_id = f.id
          AND f.shop_id IS NOT NULL
        """
    )


def _soft_delete_duplicate_uploads() -> None:
    op.execute("DROP TABLE IF EXISTS tmp_fin_transaction_duplicate_uploads")
    op.execute(
        """
        CREATE TEMP TABLE tmp_fin_transaction_duplicate_uploads (
            id BIGINT PRIMARY KEY
        ) ON COMMIT DROP
        """
    )
    op.execute(
        """
        INSERT INTO tmp_fin_transaction_duplicate_uploads (id)
        SELECT id
        FROM (
            SELECT
                id,
                ROW_NUMBER() OVER (
                    PARTITION BY org_id, platform_code, shop_id, accounting_year, accounting_month
                    ORDER BY max_task_id DESC, id DESC
                ) AS row_rank
            FROM (
                SELECT
                    f.id,
                    f.org_id,
                    f.platform_code,
                    f.shop_id,
                    f.accounting_year,
                    f.accounting_month,
                    COALESCE(MAX(t.id), 0) AS max_task_id
                FROM fin_transaction_upload_files AS f
                LEFT JOIN fin_transaction_tasks AS t
                  ON t.file_id = f.id
                 AND t.is_deleted = false
                WHERE f.is_deleted = false
                  AND f.platform_code IS NOT NULL
                  AND f.shop_id IS NOT NULL
                  AND f.accounting_year IS NOT NULL
                  AND f.accounting_month IS NOT NULL
                GROUP BY f.id, f.org_id, f.platform_code, f.shop_id, f.accounting_year, f.accounting_month
            ) AS scored
        ) AS ranked
        WHERE row_rank > 1
        """
    )
    op.execute(
        """
        UPDATE fin_transaction_upload_files AS f
        SET is_deleted = true,
            deleted_at = now()
        WHERE f.is_deleted = false
          AND f.id IN (SELECT id FROM tmp_fin_transaction_duplicate_uploads)
        """
    )
    op.execute(
        """
        UPDATE fin_transaction_tasks AS t
        SET is_deleted = true,
            deleted_at = now()
        WHERE t.is_deleted = false
          AND t.file_id IN (SELECT id FROM tmp_fin_transaction_duplicate_uploads)
        """
    )
    op.execute(
        """
        UPDATE fin_transaction_details AS d
        SET is_deleted = true,
            deleted_at = now()
        WHERE d.is_deleted = false
          AND d.file_id IN (SELECT id FROM tmp_fin_transaction_duplicate_uploads)
        """
    )
    op.execute(
        """
        UPDATE fin_transaction_summary_rows AS r
        SET is_deleted = true,
            deleted_at = now()
        WHERE r.is_deleted = false
          AND r.file_id IN (SELECT id FROM tmp_fin_transaction_duplicate_uploads)
        """
    )

    op.execute("DROP TABLE IF EXISTS tmp_fin_bic_duplicate_uploads")
    op.execute(
        """
        CREATE TEMP TABLE tmp_fin_bic_duplicate_uploads (
            id BIGINT PRIMARY KEY
        ) ON COMMIT DROP
        """
    )
    op.execute(
        """
        INSERT INTO tmp_fin_bic_duplicate_uploads (id)
        SELECT id
        FROM (
            SELECT
                id,
                ROW_NUMBER() OVER (
                    PARTITION BY org_id, platform_code, shop_id, accounting_year, accounting_month
                    ORDER BY max_task_id DESC, id DESC
                ) AS row_rank
            FROM (
                SELECT
                    f.id,
                    f.org_id,
                    f.platform_code,
                    f.shop_id,
                    f.accounting_year,
                    f.accounting_month,
                    COALESCE(MAX(t.id), 0) AS max_task_id
                FROM fin_bic_upload_files AS f
                LEFT JOIN fin_bic_tasks AS t
                  ON t.file_id = f.id
                 AND t.is_deleted = false
                WHERE f.is_deleted = false
                  AND f.platform_code IS NOT NULL
                  AND f.shop_id IS NOT NULL
                  AND f.accounting_year IS NOT NULL
                  AND f.accounting_month IS NOT NULL
                GROUP BY f.id, f.org_id, f.platform_code, f.shop_id, f.accounting_year, f.accounting_month
            ) AS scored
        ) AS ranked
        WHERE row_rank > 1
        """
    )
    op.execute(
        """
        UPDATE fin_bic_upload_files AS f
        SET is_deleted = true,
            deleted_at = now()
        WHERE f.is_deleted = false
          AND f.id IN (SELECT id FROM tmp_fin_bic_duplicate_uploads)
        """
    )
    op.execute(
        """
        UPDATE fin_bic_tasks AS t
        SET is_deleted = true,
            deleted_at = now()
        WHERE t.is_deleted = false
          AND t.file_id IN (SELECT id FROM tmp_fin_bic_duplicate_uploads)
        """
    )
    op.execute(
        """
        UPDATE fin_bic_details AS d
        SET is_deleted = true,
            deleted_at = now()
        WHERE d.is_deleted = false
          AND d.file_id IN (SELECT id FROM tmp_fin_bic_duplicate_uploads)
        """
    )
    op.execute(
        """
        UPDATE fin_bic_report_rows AS r
        SET is_deleted = true,
            deleted_at = now()
        WHERE r.is_deleted = false
          AND r.file_id IN (SELECT id FROM tmp_fin_bic_duplicate_uploads)
        """
    )


def _create_business_key_indexes() -> None:
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_fin_transaction_upload_business_key
        ON fin_transaction_upload_files (
            org_id,
            platform_code,
            shop_id,
            accounting_year,
            accounting_month
        )
        WHERE is_deleted = false
          AND platform_code IS NOT NULL
          AND shop_id IS NOT NULL
          AND accounting_year IS NOT NULL
          AND accounting_month IS NOT NULL
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_fin_bic_upload_business_key
        ON fin_bic_upload_files (
            org_id,
            platform_code,
            shop_id,
            accounting_year,
            accounting_month
        )
        WHERE is_deleted = false
          AND platform_code IS NOT NULL
          AND shop_id IS NOT NULL
          AND accounting_year IS NOT NULL
          AND accounting_month IS NOT NULL
        """
    )
