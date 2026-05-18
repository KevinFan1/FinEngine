"""update storage quota to 1GB

Revision ID: 007
Revises: 006
Create Date: 2026-05-18 10:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '007'
down_revision = '006'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """将所有组织的存储配额更新为 1GB（如果当前大于 1GB）"""
    # 1GB in bytes
    one_gb = 1 * 1024 * 1024 * 1024

    # 只更新那些配额大于 1GB 的组织
    op.execute(
        sa.text(
            """
            UPDATE fin_organizations
            SET max_storage_bytes = :one_gb
            WHERE max_storage_bytes > :one_gb
            AND is_deleted = false
            """
        ).bindparams(one_gb=one_gb)
    )


def downgrade() -> None:
    """回滚：将存储配额恢复为 100GB"""
    # 100GB in bytes
    hundred_gb = 100 * 1024 * 1024 * 1024

    op.execute(
        sa.text(
            """
            UPDATE fin_organizations
            SET max_storage_bytes = :hundred_gb
            WHERE max_storage_bytes = :one_gb
            AND is_deleted = false
            """
        ).bindparams(hundred_gb=hundred_gb, one_gb=1 * 1024 * 1024 * 1024)
    )
