"""add summary order paid and refund amounts

Revision ID: 011
Revises: 010
Create Date: 2026-05-20 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op


revision: str = "011"
down_revision: Union[str, None] = "010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE fin_financial_summaries ADD COLUMN IF NOT EXISTS order_paid_amount NUMERIC(14, 2) DEFAULT 0")
    op.execute("COMMENT ON COLUMN fin_financial_summaries.order_paid_amount IS '订单实付金额'")
    op.execute("ALTER TABLE fin_financial_summaries ADD COLUMN IF NOT EXISTS refund_amount NUMERIC(14, 2) DEFAULT 0")
    op.execute("COMMENT ON COLUMN fin_financial_summaries.refund_amount IS '退款金额'")


def downgrade() -> None:
    op.drop_column("fin_financial_summaries", "refund_amount")
    op.drop_column("fin_financial_summaries", "order_paid_amount")
