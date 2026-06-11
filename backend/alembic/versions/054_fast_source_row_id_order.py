"""fast source row id order

Revision ID: 054_fast_source_row_id_order
Revises: 053_drop_raw_row
Create Date: 2026-06-11

"""
from typing import Sequence, Union

from alembic import op


revision: str = "054_fast_source_row_id_order"
down_revision: Union[str, None] = "053_drop_raw_row"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_fin_bic_source_visible_id
        ON fin_bic_source_rows (id)
        WHERE is_deleted = false
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_fin_bic_source_org_visible_id
        ON fin_bic_source_rows (org_id, id)
        WHERE is_deleted = false
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_douyin_dongzhang_detail_summary_id
        ON fin_douyin_dongzhang_details (summary_id, id)
        WHERE is_deleted = false
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_douyin_dongzhang_detail_summary_id")
    op.execute("DROP INDEX IF EXISTS idx_fin_bic_source_org_visible_id")
    op.execute("DROP INDEX IF EXISTS idx_fin_bic_source_visible_id")
