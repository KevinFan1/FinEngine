from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, SmallInteger, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB, NUMERIC
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, SoftDeleteMixin


class TransactionSubject(SoftDeleteMixin, Base):
    __tablename__ = "fin_transaction_subjects"
    __table_args__ = (
        Index(
            "uq_fin_transaction_subject_name",
            "name",
            unique=True,
            postgresql_where=text("is_deleted = false"),
        ),
        {"comment": "动账核算科目表"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="科目名称")
    sort_order: Mapped[int] = mapped_column(Integer, default=100, comment="排序")
    status: Mapped[int] = mapped_column(SmallInteger, default=1, comment="状态：1=启用 0=停用")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="更新时间")


class TransactionCategory(SoftDeleteMixin, Base):
    __tablename__ = "fin_transaction_categories"
    __table_args__ = (
        Index(
            "uq_fin_transaction_category_subject_name",
            "subject_id",
            "name",
            unique=True,
            postgresql_where=text("is_deleted = false"),
        ),
        {"comment": "动账核算分类表"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    subject_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("fin_transaction_subjects.id"), nullable=False, comment="科目ID")
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="分类名称")
    sort_order: Mapped[int] = mapped_column(Integer, default=100, comment="排序")
    status: Mapped[int] = mapped_column(SmallInteger, default=1, comment="状态：1=启用 0=停用")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="更新时间")


class TransactionRule(SoftDeleteMixin, Base):
    __tablename__ = "fin_transaction_rules"
    __table_args__ = (
        Index("idx_fin_transaction_rules_lookup", "platform_code", "transaction_direction", "status"),
        Index(
            "uq_fin_transaction_rule_business_key",
            "subject_id",
            "category_id",
            "platform_code",
            "transaction_direction",
            "remark_pattern",
            "amount_field",
            "result_direction",
            unique=True,
            postgresql_where=text("is_deleted = false"),
        ),
        {"comment": "动账核算匹配规则表"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    subject_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("fin_transaction_subjects.id"), nullable=False, comment="科目ID")
    category_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("fin_transaction_categories.id"), nullable=False, comment="分类ID")
    platform_code: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="平台编码，空表示通用")
    transaction_direction: Mapped[str] = mapped_column(String(20), nullable=False, comment="动账方向")
    remark_field: Mapped[str] = mapped_column(String(100), default="备注", comment="备注字段名")
    direction_field: Mapped[str] = mapped_column(String(100), default="动账方向", comment="方向字段名")
    match_type: Mapped[str] = mapped_column(String(20), default="contains", comment="匹配方式：精确/包含/正则")
    remark_pattern: Mapped[str] = mapped_column(String(1000), nullable=False, comment="备注匹配内容")
    amount_field: Mapped[str] = mapped_column(String(100), nullable=False, comment="取数字段名")
    result_direction: Mapped[str] = mapped_column(String(30), default="original", comment="结果方向：原始/正值/负值/按方向")
    priority: Mapped[int] = mapped_column(Integer, default=100, comment="优先级，数字越小越先匹配")
    status: Mapped[int] = mapped_column(SmallInteger, default=1, comment="1=启用 0=停用")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="更新时间")


class TransactionUploadFile(SoftDeleteMixin, Base):
    __tablename__ = "fin_transaction_upload_files"
    __table_args__ = (
        Index(
            "uq_fin_transaction_upload_source_file",
            "source_upload_file_id",
            unique=True,
            postgresql_where=text(
                "is_deleted = false AND source_upload_file_id IS NOT NULL"
            ),
        ),
        Index(
            "uq_fin_transaction_upload_business_key",
            "org_id",
            "platform_code",
            "shop_id",
            "accounting_year",
            "accounting_month",
            unique=True,
            postgresql_where=text(
                "is_deleted = false "
                "AND platform_code IS NOT NULL "
                "AND shop_id IS NOT NULL "
                "AND accounting_year IS NOT NULL "
                "AND accounting_month IS NOT NULL"
            ),
        ),
        {"comment": "动账核算独立上传文件表"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    org_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("fin_organizations.id"), nullable=False, comment="所属组织ID")
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("fin_users.id"), nullable=False, comment="上传用户ID")
    shop_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("fin_shops.id"), nullable=True, comment="店铺ID")
    source_upload_file_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("fin_upload_files.id"),
        nullable=True,
        comment="统一上传来源文件ID",
    )
    original_name: Mapped[str] = mapped_column(String(500), nullable=False, comment="原始文件名")
    oss_key: Mapped[str] = mapped_column(String(1000), nullable=False, default="", comment="OSS存储路径")
    file_size: Mapped[int] = mapped_column(BigInteger, default=0, comment="文件大小字节数")
    file_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="文件 SHA-256 哈希值")
    platform_code: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="平台编码")
    shop_name: Mapped[str | None] = mapped_column(String(200), nullable=True, comment="店铺名称")
    accounting_year: Mapped[int | None] = mapped_column(SmallInteger, nullable=True, comment="核算年份")
    accounting_month: Mapped[int | None] = mapped_column(SmallInteger, nullable=True, comment="核算月份")
    status: Mapped[str] = mapped_column(String(20), default="initialized", comment="文件状态")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True, comment="错误信息")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="更新时间")


class TransactionTask(SoftDeleteMixin, Base):
    __tablename__ = "fin_transaction_tasks"
    __table_args__ = {"comment": "动账核算独立任务表"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    file_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("fin_transaction_upload_files.id"), nullable=False, comment="动账上传文件ID")
    org_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("fin_organizations.id"), nullable=False, comment="所属组织ID")
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("fin_users.id"), nullable=False, comment="触发用户ID")
    celery_task_id: Mapped[str | None] = mapped_column(String(200), nullable=True, comment="异步任务 ID（Celery）")
    status: Mapped[str] = mapped_column(String(20), default="queued", comment="任务状态")
    progress: Mapped[int] = mapped_column(SmallInteger, default=0, comment="进度百分比")
    total_rows: Mapped[int] = mapped_column(Integer, default=0, comment="总行数")
    matched_rows: Mapped[int] = mapped_column(Integer, default=0, comment="匹配行数")
    unmatched_rows: Mapped[int] = mapped_column(Integer, default=0, comment="未匹配行数")
    failed_rows: Mapped[int] = mapped_column(Integer, default=0, comment="失败行数")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True, comment="错误信息")
    result_summary: Mapped[dict | None] = mapped_column(JSONB, nullable=True, comment="结果摘要")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="开始时间")
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="结束时间")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="更新时间")


class TransactionDetail(SoftDeleteMixin, Base):
    __tablename__ = "fin_transaction_details"
    __table_args__ = (
        Index("idx_fin_transaction_details_task_status", "task_id", "status"),
        Index("idx_fin_transaction_details_org_period", "org_id", "accounting_year", "accounting_month"),
        {"comment": "动账核算明细表"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    task_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("fin_transaction_tasks.id"), nullable=False, comment="任务ID")
    file_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("fin_transaction_upload_files.id"), nullable=False, comment="文件ID")
    org_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("fin_organizations.id"), nullable=False, comment="所属组织ID")
    shop_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("fin_shops.id"), nullable=True, comment="店铺ID")
    subject_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("fin_transaction_subjects.id"), nullable=True, comment="科目ID")
    category_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("fin_transaction_categories.id"), nullable=True, comment="分类ID")
    rule_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("fin_transaction_rules.id"), nullable=True, comment="规则ID")
    row_number: Mapped[int] = mapped_column(Integer, nullable=False, comment="原始行号")
    platform_code: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="平台编码")
    shop_name: Mapped[str | None] = mapped_column(String(200), nullable=True, comment="店铺名称")
    accounting_year: Mapped[int | None] = mapped_column(SmallInteger, nullable=True, comment="核算年份")
    accounting_month: Mapped[int | None] = mapped_column(SmallInteger, nullable=True, comment="核算月份")
    transaction_direction: Mapped[str | None] = mapped_column(String(20), nullable=True, comment="动账方向")
    remark: Mapped[str | None] = mapped_column(Text, nullable=True, comment="备注")
    amount_field: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="取数字段")
    original_amount: Mapped[float] = mapped_column(NUMERIC(14, 2), default=0, comment="原始金额")
    calculated_amount: Mapped[float] = mapped_column(NUMERIC(14, 2), default=0, comment="核算金额")
    status: Mapped[str] = mapped_column(String(20), nullable=False, comment="状态：已匹配/未匹配/失败")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True, comment="错误原因")
    raw_row: Mapped[dict] = mapped_column(JSONB, nullable=False, comment="原始行JSON")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")


class TransactionSummaryRow(SoftDeleteMixin, Base):
    __tablename__ = "fin_transaction_summary_rows"
    __table_args__ = (
        Index("idx_fin_transaction_summary_task", "task_id"),
        Index("idx_fin_transaction_summary_org_period", "org_id", "accounting_year", "accounting_month"),
        {"comment": "动账核算汇总结果表"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    task_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("fin_transaction_tasks.id"), nullable=False, comment="任务ID")
    file_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("fin_transaction_upload_files.id"), nullable=False, comment="文件ID")
    org_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("fin_organizations.id"), nullable=False, comment="所属组织ID")
    shop_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("fin_shops.id"), nullable=True, comment="店铺ID")
    subject_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("fin_transaction_subjects.id"), nullable=False, comment="科目ID")
    category_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("fin_transaction_categories.id"), nullable=False, comment="分类ID")
    subject_name: Mapped[str] = mapped_column(String(100), nullable=False, comment="科目名称快照")
    category_name: Mapped[str] = mapped_column(String(100), nullable=False, comment="分类名称快照")
    transaction_direction: Mapped[str | None] = mapped_column(String(20), nullable=True, comment="动账方向")
    platform_code: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="平台编码")
    shop_name: Mapped[str | None] = mapped_column(String(200), nullable=True, comment="店铺名称")
    accounting_year: Mapped[int | None] = mapped_column(SmallInteger, nullable=True, comment="核算年份")
    accounting_month: Mapped[int | None] = mapped_column(SmallInteger, nullable=True, comment="核算月份")
    row_count: Mapped[int] = mapped_column(Integer, default=0, comment="明细行数")
    total_amount: Mapped[float] = mapped_column(NUMERIC(14, 2), default=0, comment="汇总金额")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
