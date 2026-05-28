"""add async export jobs

Revision ID: 033
Revises: 032
Create Date: 2026-05-28 12:00:00.000000

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "033"
down_revision: Union[str, None] = "032"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "fin_export_jobs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False, comment="主键ID"),
        sa.Column("org_id", sa.BigInteger(), nullable=True, comment="所属组织ID"),
        sa.Column("user_id", sa.BigInteger(), nullable=False, comment="创建用户ID"),
        sa.Column("celery_task_id", sa.String(length=200), nullable=True, comment="异步任务ID"),
        sa.Column("module", sa.String(length=50), nullable=False, comment="导出模块"),
        sa.Column("export_type", sa.String(length=80), nullable=False, comment="导出类型"),
        sa.Column("title", sa.String(length=200), nullable=False, comment="任务标题"),
        sa.Column("filename", sa.String(length=500), nullable=False, comment="文件名"),
        sa.Column("params", postgresql.JSONB(astext_type=sa.Text()), nullable=False, comment="导出参数"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="queued", comment="状态"),
        sa.Column("progress", sa.Integer(), nullable=False, server_default="0", comment="进度百分比"),
        sa.Column("row_count", sa.Integer(), nullable=True, comment="导出行数"),
        sa.Column("file_size", sa.BigInteger(), nullable=True, comment="导出文件大小"),
        sa.Column("oss_key", sa.String(length=1000), nullable=True, comment="OSS文件路径"),
        sa.Column("error_message", sa.Text(), nullable=True, comment="错误信息"),
        sa.Column("result_summary", postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment="导出结果摘要"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True, comment="开始时间"),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True, comment="结束时间"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True, comment="过期时间"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, comment="更新时间"),
        sa.Column("is_deleted", sa.Boolean(), server_default="false", nullable=False, comment="是否已软删除"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True, comment="软删除时间"),
        sa.ForeignKeyConstraint(["org_id"], ["fin_organizations.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["fin_users.id"]),
        sa.PrimaryKeyConstraint("id"),
        comment="异步导出任务表",
    )
    op.create_index("idx_fin_export_jobs_user_status", "fin_export_jobs", ["user_id", "status", "created_at"])
    op.create_index("idx_fin_export_jobs_org_created", "fin_export_jobs", ["org_id", "created_at"])


def downgrade() -> None:
    op.drop_index("idx_fin_export_jobs_org_created", table_name="fin_export_jobs")
    op.drop_index("idx_fin_export_jobs_user_status", table_name="fin_export_jobs")
    op.drop_table("fin_export_jobs")
