"""Add default shop color field

Revision ID: 003
Revises: 002
Create Date: 2026-05-12 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE fin_shops ADD COLUMN IF NOT EXISTS shop_color VARCHAR(20)")
    op.execute("COMMENT ON COLUMN fin_shops.shop_color IS '店铺展示色'")
    op.execute(
        """
        WITH numbered AS (
            SELECT
                id,
                ROW_NUMBER() OVER (ORDER BY id) AS rn
            FROM fin_shops
            WHERE is_deleted = false
        )
        UPDATE fin_shops AS s
        SET shop_color = CASE ((numbered.rn - 1) % 10)
            WHEN 0 THEN '#F59E0B'
            WHEN 1 THEN '#38BDF8'
            WHEN 2 THEN '#F97316'
            WHEN 3 THEN '#14B8A6'
            WHEN 4 THEN '#FB7185'
            WHEN 5 THEN '#C084FC'
            WHEN 6 THEN '#84CC16'
            WHEN 7 THEN '#06B6D4'
            WHEN 8 THEN '#F43F5E'
            ELSE '#A78BFA'
        END
        FROM numbered
        WHERE s.id = numbered.id
          AND (s.shop_color IS NULL OR s.shop_color = '')
        """
    )


def downgrade() -> None:
    op.drop_column("fin_shops", "shop_color")
