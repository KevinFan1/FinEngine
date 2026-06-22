"""normalize bic service provider names

Revision ID: 055_bic_provider_norm
Revises: 054_fast_source_row_id_order
Create Date: 2026-06-22

"""
from typing import Sequence, Union

from alembic import op


revision: str = "055_bic_provider_norm"
down_revision: Union[str, None] = "054_fast_source_row_id_order"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _normalized_provider_sql(column_name: str) -> str:
    return (
        "COALESCE(NULLIF(btrim("
        "regexp_replace("
        f"replace(replace(replace(replace({column_name}, '(仓)', ''), '(配)', ''), '（仓）', ''), '（配）', ''),"
        " '-(仓|配)$', ''"
        ")"
        "), ''), '-')"
    )


def upgrade() -> None:
    normalized_detail_provider = _normalized_provider_sql("service_provider")
    normalized_source_provider = _normalized_provider_sql("service_provider")

    op.execute(
        f"""
        UPDATE fin_bic_details
        SET service_provider = {normalized_detail_provider}
        WHERE service_provider LIKE '%(仓)%'
           OR service_provider LIKE '%(配)%'
           OR service_provider LIKE '%（仓）%'
           OR service_provider LIKE '%（配）%'
           OR service_provider LIKE '%-仓'
           OR service_provider LIKE '%-配'
        """
    )
    op.execute(
        f"""
        UPDATE fin_bic_source_rows
        SET service_provider = {normalized_source_provider}
        WHERE service_provider LIKE '%(仓)%'
           OR service_provider LIKE '%(配)%'
           OR service_provider LIKE '%（仓）%'
           OR service_provider LIKE '%（配）%'
           OR service_provider LIKE '%-仓'
           OR service_provider LIKE '%-配'
        """
    )

    op.execute(
        """
        WITH detail_groups AS (
            SELECT
                task_id,
                file_id,
                org_id,
                COALESCE(shop_id, 0) AS shop_id_key,
                platform_code,
                shop_name,
                accounting_year,
                accounting_month,
                service_provider,
                qic_warehouse,
                MIN(id) AS keep_id,
                SUM(row_count) AS merged_row_count,
                SUM(total_amount) AS merged_total_amount,
                ARRAY_AGG(id) AS detail_ids
            FROM fin_bic_details
            WHERE is_deleted = false
            GROUP BY
                task_id,
                file_id,
                org_id,
                COALESCE(shop_id, 0),
                platform_code,
                shop_name,
                accounting_year,
                accounting_month,
                service_provider,
                qic_warehouse
            HAVING COUNT(*) > 1
        ),
        updated_sources AS (
            UPDATE fin_bic_source_rows AS source_row
            SET detail_id = detail_groups.keep_id
            FROM detail_groups
            WHERE source_row.detail_id = ANY(detail_groups.detail_ids)
              AND source_row.detail_id <> detail_groups.keep_id
            RETURNING source_row.id
        ),
        updated_details AS (
            UPDATE fin_bic_details AS detail
            SET
                row_count = detail_groups.merged_row_count,
                total_amount = detail_groups.merged_total_amount
            FROM detail_groups
            WHERE detail.id = detail_groups.keep_id
            RETURNING detail.id
        )
        DELETE FROM fin_bic_details AS detail
        USING detail_groups
        WHERE detail.id = ANY(detail_groups.detail_ids)
          AND detail.id <> detail_groups.keep_id
        """
    )


def downgrade() -> None:
    # Lossy normalization: original service-provider suffixes cannot be restored.
    pass
