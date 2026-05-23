"""add shop profile fields

Revision ID: 017
Revises: 016
Create Date: 2026-05-22 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "017"
down_revision: Union[str, None] = "016"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


SHOP_PROFILE_COLUMNS = (
    ("tax_no", sa.String(length=100), "税号"),
    ("merchant", sa.String(length=200), "商户"),
    ("registered_address", sa.String(length=500), "注册地址"),
    ("legal_person", sa.String(length=100), "法人"),
    ("previous_name", sa.String(length=200), "曾用名"),
    ("store_long_id", sa.String(length=100), "store_long_id"),
    ("store_short_id", sa.String(length=100), "store_short_id"),
    ("settlement_period", sa.String(length=100), "settlement_period"),
    ("primary_account", sa.String(length=200), "primary_account"),
    ("anchor", sa.String(length=100), "主播"),
    ("shop_type", sa.String(length=100), "类型"),
    ("purpose", sa.String(length=200), "purpose"),
    ("former_name", sa.String(length=200), "former_name"),
)


def upgrade() -> None:
    for name, column_type, comment in SHOP_PROFILE_COLUMNS:
        op.add_column(
            "fin_shops",
            sa.Column(name, column_type, nullable=True, comment=comment),
        )


def downgrade() -> None:
    for name, _column_type, _comment in reversed(SHOP_PROFILE_COLUMNS):
        op.drop_column("fin_shops", name)
