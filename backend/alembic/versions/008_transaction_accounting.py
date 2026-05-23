"""add independent transaction accounting tables

Revision ID: 008
Revises: 007
Create Date: 2026-05-19 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "fin_transaction_subjects",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False, comment="主键ID"),
        sa.Column("org_id", sa.BigInteger(), nullable=False, comment="所属组织ID"),
        sa.Column("name", sa.String(length=100), nullable=False, comment="科目名称"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="100", comment="排序"),
        sa.Column("status", sa.SmallInteger(), nullable=False, server_default="1", comment="状态：1=启用 0=停用"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, comment="更新时间"),
        sa.Column("is_deleted", sa.Boolean(), server_default="false", nullable=False, comment="是否已软删除"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True, comment="软删除时间"),
        sa.ForeignKeyConstraint(["org_id"], ["fin_organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
        comment="动账核算科目表",
    )
    op.create_index(
        "uq_fin_transaction_subject_org_name",
        "fin_transaction_subjects",
        ["org_id", "name"],
        unique=True,
        postgresql_where=sa.text("is_deleted = false"),
    )

    op.create_table(
        "fin_transaction_categories",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False, comment="主键ID"),
        sa.Column("org_id", sa.BigInteger(), nullable=False, comment="所属组织ID"),
        sa.Column("subject_id", sa.BigInteger(), nullable=False, comment="科目ID"),
        sa.Column("name", sa.String(length=100), nullable=False, comment="分类名称"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="100", comment="排序"),
        sa.Column("status", sa.SmallInteger(), nullable=False, server_default="1", comment="状态：1=启用 0=停用"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, comment="更新时间"),
        sa.Column("is_deleted", sa.Boolean(), server_default="false", nullable=False, comment="是否已软删除"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True, comment="软删除时间"),
        sa.ForeignKeyConstraint(["org_id"], ["fin_organizations.id"]),
        sa.ForeignKeyConstraint(["subject_id"], ["fin_transaction_subjects.id"]),
        sa.PrimaryKeyConstraint("id"),
        comment="动账核算分类表",
    )
    op.create_index(
        "uq_fin_transaction_category_subject_name",
        "fin_transaction_categories",
        ["subject_id", "name"],
        unique=True,
        postgresql_where=sa.text("is_deleted = false"),
    )

    op.create_table(
        "fin_transaction_rules",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False, comment="主键ID"),
        sa.Column("org_id", sa.BigInteger(), nullable=False, comment="所属组织ID"),
        sa.Column("subject_id", sa.BigInteger(), nullable=False, comment="科目ID"),
        sa.Column("category_id", sa.BigInteger(), nullable=False, comment="分类ID"),
        sa.Column("platform_code", sa.String(length=50), nullable=True, comment="平台编码，空表示通用"),
        sa.Column("transaction_direction", sa.String(length=20), nullable=False, comment="动账方向"),
        sa.Column("remark_field", sa.String(length=100), nullable=False, server_default="备注", comment="备注字段名"),
        sa.Column("direction_field", sa.String(length=100), nullable=False, server_default="动账方向", comment="方向字段名"),
        sa.Column("match_type", sa.String(length=20), nullable=False, server_default="contains", comment="匹配方式：精确/包含/不包含"),
        sa.Column("remark_pattern", sa.String(length=1000), nullable=False, comment="备注匹配内容"),
        sa.Column("amount_field", sa.String(length=100), nullable=False, comment="取数字段名"),
        sa.Column("result_direction", sa.String(length=30), nullable=False, server_default="original", comment="结果方向：原始/正值/负值/按方向"),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="100", comment="优先级，数字越小越先匹配"),
        sa.Column("status", sa.SmallInteger(), nullable=False, server_default="1", comment="1=启用 0=停用"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, comment="更新时间"),
        sa.Column("is_deleted", sa.Boolean(), server_default="false", nullable=False, comment="是否已软删除"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True, comment="软删除时间"),
        sa.ForeignKeyConstraint(["category_id"], ["fin_transaction_categories.id"]),
        sa.ForeignKeyConstraint(["org_id"], ["fin_organizations.id"]),
        sa.ForeignKeyConstraint(["subject_id"], ["fin_transaction_subjects.id"]),
        sa.PrimaryKeyConstraint("id"),
        comment="动账核算匹配规则表",
    )
    op.create_index("idx_fin_transaction_rules_lookup", "fin_transaction_rules", ["org_id", "platform_code", "transaction_direction", "status"])

    op.create_table(
        "fin_transaction_upload_files",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False, comment="主键ID"),
        sa.Column("org_id", sa.BigInteger(), nullable=False, comment="所属组织ID"),
        sa.Column("user_id", sa.BigInteger(), nullable=False, comment="上传用户ID"),
        sa.Column("source_upload_file_id", sa.BigInteger(), nullable=True, comment="统一上传来源文件ID"),
        sa.Column("original_name", sa.String(length=500), nullable=False, comment="原始文件名"),
        sa.Column("oss_key", sa.String(length=1000), nullable=False, server_default="", comment="OSS存储路径"),
        sa.Column("file_size", sa.BigInteger(), nullable=False, server_default="0", comment="文件大小字节数"),
        sa.Column("file_hash", sa.String(length=64), nullable=True, comment="文件 SHA-256 哈希值"),
        sa.Column("platform_code", sa.String(length=50), nullable=True, comment="平台编码"),
        sa.Column("shop_name", sa.String(length=200), nullable=True, comment="店铺名称"),
        sa.Column("accounting_year", sa.SmallInteger(), nullable=True, comment="核算年份"),
        sa.Column("accounting_month", sa.SmallInteger(), nullable=True, comment="核算月份"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="initialized", comment="文件状态"),
        sa.Column("error_message", sa.Text(), nullable=True, comment="错误信息"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, comment="更新时间"),
        sa.Column("is_deleted", sa.Boolean(), server_default="false", nullable=False, comment="是否已软删除"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True, comment="软删除时间"),
        sa.ForeignKeyConstraint(["org_id"], ["fin_organizations.id"]),
        sa.ForeignKeyConstraint(["source_upload_file_id"], ["fin_upload_files.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["fin_users.id"]),
        sa.PrimaryKeyConstraint("id"),
        comment="动账核算独立上传文件表",
    )
    op.create_index(
        "uq_fin_transaction_upload_source_file",
        "fin_transaction_upload_files",
        ["source_upload_file_id"],
        unique=True,
        postgresql_where=sa.text(
            "is_deleted = false AND source_upload_file_id IS NOT NULL"
        ),
    )

    op.create_table(
        "fin_transaction_tasks",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False, comment="主键ID"),
        sa.Column("file_id", sa.BigInteger(), nullable=False, comment="动账上传文件ID"),
        sa.Column("org_id", sa.BigInteger(), nullable=False, comment="所属组织ID"),
        sa.Column("user_id", sa.BigInteger(), nullable=False, comment="触发用户ID"),
        sa.Column("celery_task_id", sa.String(length=200), nullable=True, comment="异步任务 ID（Celery）"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="queued", comment="任务状态"),
        sa.Column("progress", sa.SmallInteger(), nullable=False, server_default="0", comment="进度百分比"),
        sa.Column("total_rows", sa.Integer(), nullable=False, server_default="0", comment="总行数"),
        sa.Column("matched_rows", sa.Integer(), nullable=False, server_default="0", comment="匹配行数"),
        sa.Column("unmatched_rows", sa.Integer(), nullable=False, server_default="0", comment="未匹配行数"),
        sa.Column("failed_rows", sa.Integer(), nullable=False, server_default="0", comment="失败行数"),
        sa.Column("error_message", sa.Text(), nullable=True, comment="错误信息"),
        sa.Column("result_summary", postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment="结果摘要"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True, comment="开始时间"),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True, comment="结束时间"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, comment="更新时间"),
        sa.Column("is_deleted", sa.Boolean(), server_default="false", nullable=False, comment="是否已软删除"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True, comment="软删除时间"),
        sa.ForeignKeyConstraint(["file_id"], ["fin_transaction_upload_files.id"]),
        sa.ForeignKeyConstraint(["org_id"], ["fin_organizations.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["fin_users.id"]),
        sa.PrimaryKeyConstraint("id"),
        comment="动账核算独立任务表",
    )

    op.create_table(
        "fin_transaction_details",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False, comment="主键ID"),
        sa.Column("task_id", sa.BigInteger(), nullable=False, comment="任务ID"),
        sa.Column("file_id", sa.BigInteger(), nullable=False, comment="文件ID"),
        sa.Column("org_id", sa.BigInteger(), nullable=False, comment="所属组织ID"),
        sa.Column("subject_id", sa.BigInteger(), nullable=True, comment="科目ID"),
        sa.Column("category_id", sa.BigInteger(), nullable=True, comment="分类ID"),
        sa.Column("rule_id", sa.BigInteger(), nullable=True, comment="规则ID"),
        sa.Column("row_number", sa.Integer(), nullable=False, comment="原始行号"),
        sa.Column("platform_code", sa.String(length=50), nullable=True, comment="平台编码"),
        sa.Column("shop_name", sa.String(length=200), nullable=True, comment="店铺名称"),
        sa.Column("accounting_year", sa.SmallInteger(), nullable=True, comment="核算年份"),
        sa.Column("accounting_month", sa.SmallInteger(), nullable=True, comment="核算月份"),
        sa.Column("transaction_direction", sa.String(length=20), nullable=True, comment="动账方向"),
        sa.Column("remark", sa.Text(), nullable=True, comment="备注"),
        sa.Column("amount_field", sa.String(length=100), nullable=True, comment="取数字段"),
        sa.Column("original_amount", sa.Numeric(14, 2), nullable=False, server_default="0", comment="原始金额"),
        sa.Column("calculated_amount", sa.Numeric(14, 2), nullable=False, server_default="0", comment="核算金额"),
        sa.Column("status", sa.String(length=20), nullable=False, comment="状态：已匹配/未匹配/失败"),
        sa.Column("error_message", sa.Text(), nullable=True, comment="错误原因"),
        sa.Column("raw_row", postgresql.JSONB(astext_type=sa.Text()), nullable=False, comment="原始行JSON"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, comment="创建时间"),
        sa.Column("is_deleted", sa.Boolean(), server_default="false", nullable=False, comment="是否已软删除"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True, comment="软删除时间"),
        sa.ForeignKeyConstraint(["category_id"], ["fin_transaction_categories.id"]),
        sa.ForeignKeyConstraint(["file_id"], ["fin_transaction_upload_files.id"]),
        sa.ForeignKeyConstraint(["org_id"], ["fin_organizations.id"]),
        sa.ForeignKeyConstraint(["rule_id"], ["fin_transaction_rules.id"]),
        sa.ForeignKeyConstraint(["subject_id"], ["fin_transaction_subjects.id"]),
        sa.ForeignKeyConstraint(["task_id"], ["fin_transaction_tasks.id"]),
        sa.PrimaryKeyConstraint("id"),
        comment="动账核算明细表",
    )
    op.create_index("idx_fin_transaction_details_org_period", "fin_transaction_details", ["org_id", "accounting_year", "accounting_month"])
    op.create_index("idx_fin_transaction_details_task_status", "fin_transaction_details", ["task_id", "status"])

    op.create_table(
        "fin_transaction_summary_rows",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False, comment="主键ID"),
        sa.Column("task_id", sa.BigInteger(), nullable=False, comment="任务ID"),
        sa.Column("file_id", sa.BigInteger(), nullable=False, comment="文件ID"),
        sa.Column("org_id", sa.BigInteger(), nullable=False, comment="所属组织ID"),
        sa.Column("subject_id", sa.BigInteger(), nullable=False, comment="科目ID"),
        sa.Column("category_id", sa.BigInteger(), nullable=False, comment="分类ID"),
        sa.Column("subject_name", sa.String(length=100), nullable=False, comment="科目名称快照"),
        sa.Column("category_name", sa.String(length=100), nullable=False, comment="分类名称快照"),
        sa.Column("transaction_direction", sa.String(length=20), nullable=True, comment="动账方向"),
        sa.Column("platform_code", sa.String(length=50), nullable=True, comment="平台编码"),
        sa.Column("shop_name", sa.String(length=200), nullable=True, comment="店铺名称"),
        sa.Column("accounting_year", sa.SmallInteger(), nullable=True, comment="核算年份"),
        sa.Column("accounting_month", sa.SmallInteger(), nullable=True, comment="核算月份"),
        sa.Column("row_count", sa.Integer(), nullable=False, server_default="0", comment="明细行数"),
        sa.Column("total_amount", sa.Numeric(14, 2), nullable=False, server_default="0", comment="汇总金额"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, comment="创建时间"),
        sa.Column("is_deleted", sa.Boolean(), server_default="false", nullable=False, comment="是否已软删除"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True, comment="软删除时间"),
        sa.ForeignKeyConstraint(["category_id"], ["fin_transaction_categories.id"]),
        sa.ForeignKeyConstraint(["file_id"], ["fin_transaction_upload_files.id"]),
        sa.ForeignKeyConstraint(["org_id"], ["fin_organizations.id"]),
        sa.ForeignKeyConstraint(["subject_id"], ["fin_transaction_subjects.id"]),
        sa.ForeignKeyConstraint(["task_id"], ["fin_transaction_tasks.id"]),
        sa.PrimaryKeyConstraint("id"),
        comment="动账核算汇总结果表",
    )
    op.create_index("idx_fin_transaction_summary_org_period", "fin_transaction_summary_rows", ["org_id", "accounting_year", "accounting_month"])
    op.create_index("idx_fin_transaction_summary_task", "fin_transaction_summary_rows", ["task_id"])


def downgrade() -> None:
    op.drop_index(
        "uq_fin_transaction_upload_source_file",
        table_name="fin_transaction_upload_files",
    )
    op.drop_index("idx_fin_transaction_summary_task", table_name="fin_transaction_summary_rows")
    op.drop_index("idx_fin_transaction_summary_org_period", table_name="fin_transaction_summary_rows")
    op.drop_table("fin_transaction_summary_rows")
    op.drop_index("idx_fin_transaction_details_task_status", table_name="fin_transaction_details")
    op.drop_index("idx_fin_transaction_details_org_period", table_name="fin_transaction_details")
    op.drop_table("fin_transaction_details")
    op.drop_table("fin_transaction_tasks")
    op.drop_table("fin_transaction_upload_files")
    op.drop_index("idx_fin_transaction_rules_lookup", table_name="fin_transaction_rules")
    op.drop_table("fin_transaction_rules")
    op.drop_index("uq_fin_transaction_category_subject_name", table_name="fin_transaction_categories")
    op.drop_table("fin_transaction_categories")
    op.drop_index("uq_fin_transaction_subject_org_name", table_name="fin_transaction_subjects")
    op.drop_table("fin_transaction_subjects")
