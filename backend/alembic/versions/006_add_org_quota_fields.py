"""添加组织配额管理字段

Revision ID: 006
Revises: 005
Create Date: 2026-05-16 23:40:00.000000

添加组织的用户数量限制和存储容量限制字段。
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """添加配额字段。"""

    # 添加用户配额字段
    op.add_column('fin_organizations', sa.Column(
        'max_users',
        sa.Integer(),
        nullable=False,
        server_default='5',
        comment='最大用户数量（免费版 5 个）'
    ))

    # 添加存储配额字段（单位：字节）
    op.add_column('fin_organizations', sa.Column(
        'max_storage_bytes',
        sa.BigInteger(),
        nullable=False,
        server_default=str(100 * 1024 * 1024 * 1024),  # 100GB
        comment='最大存储容量（字节），免费版 100GB'
    ))

    # 添加当前使用的存储量字段
    op.add_column('fin_organizations', sa.Column(
        'used_storage_bytes',
        sa.BigInteger(),
        nullable=False,
        server_default='0',
        comment='已使用存储容量（字节）'
    ))

    # 添加套餐类型字段
    op.add_column('fin_organizations', sa.Column(
        'plan_type',
        sa.String(20),
        nullable=False,
        server_default='free',
        comment='套餐类型: free=免费版, basic=基础版, pro=专业版, enterprise=企业版'
    ))

    # 添加套餐到期时间
    op.add_column('fin_organizations', sa.Column(
        'plan_expires_at',
        sa.DateTime(timezone=True),
        nullable=True,
        comment='套餐到期时间（免费版为 NULL）'
    ))

    # 创建索引
    op.create_index('idx_org_plan_type', 'fin_organizations', ['plan_type'])


def downgrade() -> None:
    """移除配额字段。"""

    op.drop_index('idx_org_plan_type', table_name='fin_organizations')
    op.drop_column('fin_organizations', 'plan_expires_at')
    op.drop_column('fin_organizations', 'plan_type')
    op.drop_column('fin_organizations', 'used_storage_bytes')
    op.drop_column('fin_organizations', 'max_storage_bytes')
    op.drop_column('fin_organizations', 'max_users')
