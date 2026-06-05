"""add reconciliation checklist

Revision ID: 044_reconciliation_checklist
Revises: 043_douyin_source_partition
Create Date: 2026-06-04

"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "044_reconciliation_checklist"
down_revision: Union[str, None] = "043_douyin_source_partition"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "fin_reconciliation_checklist_upload_files",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False, comment="主键ID"),
        sa.Column("org_id", sa.BigInteger(), nullable=False, comment="所属组织ID"),
        sa.Column("user_id", sa.BigInteger(), nullable=False, comment="上传用户ID"),
        sa.Column("source_upload_file_id", sa.BigInteger(), nullable=True, comment="统一上传来源文件ID"),
        sa.Column("original_name", sa.String(length=500), nullable=False, comment="原始文件名"),
        sa.Column("oss_key", sa.String(length=1000), nullable=False, server_default="", comment="OSS存储路径"),
        sa.Column("file_size", sa.BigInteger(), nullable=False, server_default="0", comment="文件大小字节数"),
        sa.Column("file_hash", sa.String(length=64), nullable=True, comment="文件 SHA-256 哈希值"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="uploaded", comment="文件状态"),
        sa.Column("error_message", sa.Text(), nullable=True, comment="错误信息"),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false"), comment="是否已软删除"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True, comment="软删除时间"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, comment="更新时间"),
        sa.ForeignKeyConstraint(["org_id"], ["fin_organizations.id"]),
        sa.ForeignKeyConstraint(["source_upload_file_id"], ["fin_upload_files.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["fin_users.id"]),
        sa.PrimaryKeyConstraint("id"),
        comment="对账清单上传文件表",
    )
    op.create_index(
        "uq_fin_reconciliation_checklist_upload_source_file",
        "fin_reconciliation_checklist_upload_files",
        ["source_upload_file_id"],
        unique=True,
        postgresql_where=sa.text("is_deleted = false AND source_upload_file_id IS NOT NULL"),
    )
    op.create_index(
        "idx_fin_reconciliation_checklist_upload_org_status",
        "fin_reconciliation_checklist_upload_files",
        ["org_id", "status", "created_at"],
        postgresql_where=sa.text("is_deleted = false"),
    )

    op.create_table(
        "fin_reconciliation_checklist_tasks",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False, comment="主键ID"),
        sa.Column("file_id", sa.BigInteger(), nullable=False, comment="对账清单上传文件ID"),
        sa.Column("org_id", sa.BigInteger(), nullable=False, comment="所属组织ID"),
        sa.Column("user_id", sa.BigInteger(), nullable=False, comment="触发用户ID"),
        sa.Column("celery_task_id", sa.String(length=200), nullable=True, comment="异步任务 ID（Celery）"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="queued", comment="任务状态"),
        sa.Column("progress", sa.SmallInteger(), nullable=False, server_default="0", comment="进度百分比"),
        sa.Column("total_rows", sa.Integer(), nullable=False, server_default="0", comment="总行数"),
        sa.Column("success_rows", sa.Integer(), nullable=False, server_default="0", comment="成功行数"),
        sa.Column("failed_rows", sa.Integer(), nullable=False, server_default="0", comment="失败行数"),
        sa.Column("inserted_rows", sa.Integer(), nullable=False, server_default="0", comment="新增行数"),
        sa.Column("updated_rows", sa.Integer(), nullable=False, server_default="0", comment="更新行数"),
        sa.Column("error_message", sa.Text(), nullable=True, comment="错误信息"),
        sa.Column("result_summary", postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment="结果摘要"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True, comment="开始时间"),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True, comment="结束时间"),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false"), comment="是否已软删除"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True, comment="软删除时间"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, comment="更新时间"),
        sa.ForeignKeyConstraint(["file_id"], ["fin_reconciliation_checklist_upload_files.id"]),
        sa.ForeignKeyConstraint(["org_id"], ["fin_organizations.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["fin_users.id"]),
        sa.PrimaryKeyConstraint("id"),
        comment="对账清单处理任务表",
    )
    op.create_index("idx_fin_reconciliation_checklist_tasks_file", "fin_reconciliation_checklist_tasks", ["file_id"])
    op.create_index(
        "idx_fin_reconciliation_checklist_tasks_org_status",
        "fin_reconciliation_checklist_tasks",
        ["org_id", "status", "created_at"],
        postgresql_where=sa.text("is_deleted = false"),
    )

    op.execute("CREATE SEQUENCE IF NOT EXISTS fin_reconciliation_checklist_details_id_seq")
    op.create_table(
        "fin_reconciliation_checklist_details",
        sa.Column("id", sa.BigInteger(), server_default=sa.text("nextval('fin_reconciliation_checklist_details_id_seq'::regclass)"), nullable=False, comment="主键ID"),
        sa.Column("task_id", sa.BigInteger(), nullable=False, comment="处理任务ID"),
        sa.Column("file_id", sa.BigInteger(), nullable=False, comment="上传文件ID"),
        sa.Column("org_id", sa.BigInteger(), nullable=False, comment="所属组织ID"),
        sa.Column("shop_id", sa.BigInteger(), nullable=False, comment="店铺ID"),
        sa.Column("platform_code", sa.String(length=50), nullable=False, comment="平台"),
        sa.Column("shop_name", sa.String(length=200), nullable=False, comment="店铺"),
        sa.Column("accounting_year", sa.SmallInteger(), nullable=False, comment="动账时间年份"),
        sa.Column("accounting_month", sa.SmallInteger(), nullable=False, comment="动账时间月份"),
        sa.Column("accounting_period", sa.Integer(), nullable=False, comment="动账时间年月 YYYYMM"),
        sa.Column("source_row_number", sa.Integer(), nullable=False, server_default="0", comment="源文件行号"),
        sa.Column("transaction_time", sa.DateTime(timezone=False), nullable=False, comment="动账时间"),
        sa.Column("transaction_flow_no", sa.String(length=500), nullable=False, server_default="", comment="动账流水号"),
        sa.Column("product_name", sa.String(length=500), nullable=False, server_default="", comment="商品名称"),
        sa.Column("live_promoter", sa.String(length=500), nullable=False, server_default="", comment="直播推广方"),
        sa.Column("receipt_merchant", sa.String(length=500), nullable=False, server_default="", comment="收款商家"),
        sa.Column("order_amount", sa.Numeric(14, 2), nullable=False, server_default="0", comment="订单金额"),
        sa.Column("live_commission", sa.Numeric(14, 2), nullable=False, server_default="0", comment="直播推广佣金"),
        sa.Column("merchant_net_amount", sa.Numeric(14, 2), nullable=False, server_default="0", comment="应付商家净额"),
        sa.Column("raw_row", postgresql.JSONB(astext_type=sa.Text()), nullable=False, comment="原始行JSON"),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false"), comment="是否已软删除"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True, comment="软删除时间"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False, comment="更新时间"),
        sa.ForeignKeyConstraint(["file_id"], ["fin_reconciliation_checklist_upload_files.id"]),
        sa.ForeignKeyConstraint(["org_id"], ["fin_organizations.id"]),
        sa.ForeignKeyConstraint(["shop_id"], ["fin_shops.id"]),
        sa.ForeignKeyConstraint(["task_id"], ["fin_reconciliation_checklist_tasks.id"]),
        sa.PrimaryKeyConstraint("id", "accounting_period"),
        comment="对账清单明细表",
        postgresql_partition_by="RANGE (accounting_period)",
    )
    op.execute("ALTER SEQUENCE fin_reconciliation_checklist_details_id_seq OWNED BY fin_reconciliation_checklist_details.id")
    op.create_index("idx_fin_reconciliation_checklist_id", "fin_reconciliation_checklist_details", ["id"])
    op.create_index("idx_fin_reconciliation_checklist_task", "fin_reconciliation_checklist_details", ["task_id"])
    op.create_index("idx_fin_reconciliation_checklist_file", "fin_reconciliation_checklist_details", ["file_id"])
    op.create_index(
        "uq_fin_reconciliation_checklist_business_flow",
        "fin_reconciliation_checklist_details",
        ["org_id", "accounting_period", "platform_code", "shop_id", "transaction_flow_no"],
        unique=True,
        postgresql_where=sa.text("is_deleted = false AND transaction_flow_no <> ''"),
    )
    op.create_index(
        "idx_fin_reconciliation_checklist_shop_period",
        "fin_reconciliation_checklist_details",
        ["org_id", "shop_id", "accounting_period"],
        postgresql_where=sa.text("is_deleted = false"),
    )
    op.create_index(
        "idx_fin_reconciliation_checklist_summary",
        "fin_reconciliation_checklist_details",
        ["org_id", "accounting_period", "live_promoter", "receipt_merchant"],
        postgresql_where=sa.text("is_deleted = false"),
    )
    op.create_index(
        "idx_fin_reconciliation_checklist_export",
        "fin_reconciliation_checklist_details",
        ["org_id", "accounting_period", "receipt_merchant", "live_promoter", "product_name"],
        postgresql_where=sa.text("is_deleted = false"),
    )


def downgrade() -> None:
    op.drop_table("fin_reconciliation_checklist_details")
    op.execute("DROP SEQUENCE IF EXISTS fin_reconciliation_checklist_details_id_seq")
    op.drop_table("fin_reconciliation_checklist_tasks")
    op.drop_table("fin_reconciliation_checklist_upload_files")
