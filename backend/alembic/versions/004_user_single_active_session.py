"""为用户添加单一有效会话标记

Revision ID: 004
Revises: 003
Create Date: 2026-05-14 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE fin_users ADD COLUMN IF NOT EXISTS active_session_id VARCHAR(64)")
    op.execute("COMMENT ON COLUMN fin_users.active_session_id IS '当前有效登录会话 ID'")


def downgrade() -> None:
    op.drop_column("fin_users", "active_session_id")
