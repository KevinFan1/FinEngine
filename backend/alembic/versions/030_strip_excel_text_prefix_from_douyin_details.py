"""strip excel text prefix from douyin details

Revision ID: 030
Revises: 029
Create Date: 2026-05-27 14:00:00.000000

"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op


revision: str = "030"
down_revision: Union[str, None] = "029"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


TEXT_COLUMNS: tuple[str, ...] = (
    "transaction_direction",
    "transaction_account",
    "transaction_scene",
    "billing_type",
    "sub_order_no",
    "order_no",
    "after_sale_no",
    "product_id",
    "product_name",
    "author_id",
    "author_name",
    "order_type",
    "is_commission_free",
    "merchant_name",
    "remark",
    "matched_compensation",
)


def upgrade() -> None:
    for column in TEXT_COLUMNS:
        op.execute(
            f"""
            UPDATE fin_douyin_dongzhang_details
            SET {column} = btrim(substr({column}, 2))
            WHERE {column} LIKE '''%%'
            """
        )

    op.execute(
        """
        UPDATE fin_douyin_dongzhang_details detail
        SET transaction_flow_no = btrim(substr(detail.transaction_flow_no, 2))
        WHERE detail.transaction_flow_no LIKE '''%'
          AND NOT EXISTS (
              SELECT 1
              FROM fin_douyin_dongzhang_details existing
              WHERE existing.id <> detail.id
                AND existing.is_deleted = false
                AND existing.org_id = detail.org_id
                AND existing.source_platform_code = detail.source_platform_code
                AND existing.shop_id = detail.shop_id
                AND existing.source_year = detail.source_year
                AND existing.source_month = detail.source_month
                AND existing.transaction_flow_no = btrim(substr(detail.transaction_flow_no, 2))
          )
        """
    )


def downgrade() -> None:
    # Data cleanup is intentionally irreversible.
    pass
