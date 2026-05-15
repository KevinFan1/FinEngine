"""Add active session device metadata

Revision ID: 005
Revises: 004
Create Date: 2026-05-14 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE fin_users ADD COLUMN IF NOT EXISTS active_session_ip VARCHAR(64)")
    op.execute("ALTER TABLE fin_users ADD COLUMN IF NOT EXISTS active_session_user_agent VARCHAR(500)")
    op.execute("ALTER TABLE fin_users ADD COLUMN IF NOT EXISTS active_session_at TIMESTAMP WITH TIME ZONE")
    op.execute("COMMENT ON COLUMN fin_users.active_session_ip IS '当前登录IP'")
    op.execute("COMMENT ON COLUMN fin_users.active_session_user_agent IS '当前登录客户端'")
    op.execute("COMMENT ON COLUMN fin_users.active_session_at IS '当前会话登录时间'")


def downgrade() -> None:
    op.drop_column("fin_users", "active_session_at")
    op.drop_column("fin_users", "active_session_user_agent")
    op.drop_column("fin_users", "active_session_ip")
