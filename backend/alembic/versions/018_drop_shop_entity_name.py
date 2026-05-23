"""replace shop entity name with merchant

Revision ID: 018
Revises: 017
Create Date: 2026-05-22 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "018"
down_revision: Union[str, None] = "017"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE fin_shops
        SET merchant = entity_name
        WHERE entity_name IS NOT NULL
          AND entity_name <> ''
          AND (merchant IS NULL OR merchant = '')
        """
    )
    op.drop_column("fin_shops", "entity_name")


def downgrade() -> None:
    op.add_column(
        "fin_shops",
        sa.Column("entity_name", sa.String(length=200), nullable=True, comment="主体名称"),
    )
    op.execute(
        """
        UPDATE fin_shops
        SET entity_name = merchant
        WHERE merchant IS NOT NULL
          AND merchant <> ''
          AND (entity_name IS NULL OR entity_name = '')
        """
    )
