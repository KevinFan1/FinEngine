"""add organization type

Revision ID: 050_add_org_type
Revises: 049_checklist_order_base
Create Date: 2026-06-09

"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "050_add_org_type"
down_revision: Union[str, None] = "049_checklist_order_base"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "fin_organizations",
        sa.Column(
            "org_type",
            sa.String(length=20),
            nullable=False,
            server_default="external",
            comment="组织类型：external=外部组织 internal=内部组织",
        ),
    )
    op.execute(
        """
        UPDATE fin_organizations
        SET org_type = 'internal'
        WHERE code = 'default'
        """
    )
    op.alter_column("fin_organizations", "org_type", server_default=None)


def downgrade() -> None:
    op.drop_column("fin_organizations", "org_type")
