"""allow repeated bic upload tasks

Revision ID: 024
Revises: 023
Create Date: 2026-05-25 00:00:00.000000

"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "024"
down_revision: Union[str, None] = "023"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


BUSINESS_KEY_WHERE = (
    "is_deleted = false "
    "AND platform_code IS NOT NULL "
    "AND shop_id IS NOT NULL "
    "AND accounting_year IS NOT NULL "
    "AND accounting_month IS NOT NULL"
)


def upgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_fin_bic_upload_business_key")
    op.execute("DROP INDEX IF EXISTS idx_fin_bic_upload_business_key")
    op.create_index(
        "idx_fin_bic_upload_business_key",
        "fin_bic_upload_files",
        ["org_id", "platform_code", "shop_id", "accounting_year", "accounting_month"],
        unique=False,
        postgresql_where=sa.text(BUSINESS_KEY_WHERE),
    )


def downgrade() -> None:
    op.drop_index(
        "idx_fin_bic_upload_business_key",
        table_name="fin_bic_upload_files",
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
