"""add user must change password flag

Revision ID: 014
Revises: 013
Create Date: 2026-05-21 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op


revision: str = "014"
down_revision: Union[str, None] = "013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE fin_users
        ADD COLUMN IF NOT EXISTS must_change_password BOOLEAN NOT NULL DEFAULT false
        """
    )


def downgrade() -> None:
    op.execute("ALTER TABLE fin_users DROP COLUMN IF EXISTS must_change_password")
