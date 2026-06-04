"""add product code to merchant red sheet purchases

Revision ID: 042_purchase_product_code
Revises: 041_merchant_net_rate_settings
Create Date: 2026-06-03

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "042_purchase_product_code"
down_revision: Union[str, None] = "041_merchant_net_rate_settings"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE fin_merchant_red_sheet_purchases
        ADD COLUMN IF NOT EXISTS product_code varchar(1000) NOT NULL DEFAULT ''
        """
    )
    op.execute(
        "COMMENT ON COLUMN fin_merchant_red_sheet_purchases.product_code IS '从货品名称提取的商品编码'"
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_fin_merchant_purchase_product_code
        ON fin_merchant_red_sheet_purchases (org_id, accounting_period, product_code)
        WHERE is_deleted = false
        """
    )


def downgrade() -> None:
    op.drop_index("idx_fin_merchant_purchase_product_code", table_name="fin_merchant_red_sheet_purchases")
    op.drop_column("fin_merchant_red_sheet_purchases", "product_code")
