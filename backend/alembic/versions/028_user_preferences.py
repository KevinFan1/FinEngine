"""add user preferences table

Revision ID: 028
Revises: 027
Create Date: 2026-05-27 12:00:00.000000

"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op


revision: str = "028"
down_revision: Union[str, None] = "027"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS fin_user_preferences (
            id BIGSERIAL PRIMARY KEY,
            user_id BIGINT NOT NULL REFERENCES fin_users(id),
            preference_key VARCHAR(100) NOT NULL,
            preference_value JSONB NOT NULL,
            created_at TIMESTAMPTZ DEFAULT now(),
            updated_at TIMESTAMPTZ DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_fin_user_preference_user_key
        ON fin_user_preferences (user_id, preference_key)
        """
    )
    op.execute("COMMENT ON TABLE fin_user_preferences IS '用户偏好配置表'")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS fin_user_preferences")
