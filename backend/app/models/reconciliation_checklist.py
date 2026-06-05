from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, SmallInteger, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB, NUMERIC
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, SoftDeleteMixin


class ReconciliationChecklistUploadFile(SoftDeleteMixin, Base):
    __tablename__ = "fin_reconciliation_checklist_upload_files"
    __table_args__ = (
        Index(
            "uq_fin_reconciliation_checklist_upload_source_file",
            "source_upload_file_id",
            unique=True,
            postgresql_where=text("is_deleted = false AND source_upload_file_id IS NOT NULL"),
        ),
        Index(
            "idx_fin_reconciliation_checklist_upload_org_status",
            "org_id",
            "status",
            "created_at",
            postgresql_where=text("is_deleted = false"),
        ),
        {"comment": "对账清单上传文件表"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    org_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("fin_organizations.id"), nullable=False, comment="所属组织ID")
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("fin_users.id"), nullable=False, comment="上传用户ID")
    source_upload_file_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("fin_upload_files.id"), nullable=True, comment="统一上传来源文件ID")
    original_name: Mapped[str] = mapped_column(String(500), nullable=False, comment="原始文件名")
    oss_key: Mapped[str] = mapped_column(String(1000), nullable=False, default="", comment="OSS存储路径")
    file_size: Mapped[int] = mapped_column(BigInteger, default=0, comment="文件大小字节数")
    file_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="文件 SHA-256 哈希值")
    status: Mapped[str] = mapped_column(String(20), default="uploaded", comment="文件状态")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True, comment="错误信息")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="更新时间")


class ReconciliationChecklistTask(SoftDeleteMixin, Base):
    __tablename__ = "fin_reconciliation_checklist_tasks"
    __table_args__ = (
        Index("idx_fin_reconciliation_checklist_tasks_file", "file_id"),
        Index("idx_fin_reconciliation_checklist_tasks_org_status", "org_id", "status", "created_at", postgresql_where=text("is_deleted = false")),
        {"comment": "对账清单处理任务表"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    file_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("fin_reconciliation_checklist_upload_files.id"), nullable=False, comment="对账清单上传文件ID")
    org_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("fin_organizations.id"), nullable=False, comment="所属组织ID")
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("fin_users.id"), nullable=False, comment="触发用户ID")
    celery_task_id: Mapped[str | None] = mapped_column(String(200), nullable=True, comment="异步任务 ID（Celery）")
    status: Mapped[str] = mapped_column(String(20), default="queued", comment="任务状态")
    progress: Mapped[int] = mapped_column(SmallInteger, default=0, comment="进度百分比")
    total_rows: Mapped[int] = mapped_column(Integer, default=0, comment="总行数")
    success_rows: Mapped[int] = mapped_column(Integer, default=0, comment="成功行数")
    failed_rows: Mapped[int] = mapped_column(Integer, default=0, comment="失败行数")
    inserted_rows: Mapped[int] = mapped_column(Integer, default=0, comment="新增行数")
    updated_rows: Mapped[int] = mapped_column(Integer, default=0, comment="更新行数")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True, comment="错误信息")
    result_summary: Mapped[dict | None] = mapped_column(JSONB, nullable=True, comment="结果摘要")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="开始时间")
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="结束时间")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="更新时间")


class ReconciliationChecklistEntity(SoftDeleteMixin, Base):
    __tablename__ = "fin_reconciliation_checklist_entities"
    __table_args__ = (
        Index(
            "uq_fin_reconciliation_checklist_entity_name",
            "org_id",
            "platform_code",
            "entity_type",
            "name",
            unique=True,
            postgresql_where=text("is_deleted = false"),
        ),
        Index(
            "idx_fin_reconciliation_checklist_entity_search",
            "org_id",
            "platform_code",
            "entity_type",
            "status",
            "name",
            postgresql_where=text("is_deleted = false"),
        ),
        Index("idx_fin_reconciliation_checklist_entity_parent", "parent_id", postgresql_where=text("is_deleted = false")),
        {"comment": "对账清单商家与推广方维护表"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    org_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("fin_organizations.id"), nullable=False, comment="所属组织ID")
    parent_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("fin_reconciliation_checklist_entities.id"), nullable=True, comment="父级商家ID")
    platform_code: Mapped[str] = mapped_column(String(50), nullable=False, default="", comment="平台")
    entity_type: Mapped[str] = mapped_column(String(40), nullable=False, comment="类型：live_promoter/merchant/receipt_merchant")
    name: Mapped[str] = mapped_column(String(500), nullable=False, comment="名称")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active", comment="状态")
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="auto", comment="来源")
    last_seen_period: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="最近出现年月 YYYYMM")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="更新时间")


class ReconciliationChecklistDetail(SoftDeleteMixin, Base):
    __tablename__ = "fin_reconciliation_checklist_details"
    __table_args__ = (
        Index(
            "uq_fin_reconciliation_checklist_business_flow",
            "org_id",
            "accounting_period",
            "platform_code",
            "shop_id",
            "transaction_flow_no",
            unique=True,
            postgresql_where=text("is_deleted = false AND transaction_flow_no <> ''"),
        ),
        Index("idx_fin_reconciliation_checklist_id", "id"),
        Index("idx_fin_reconciliation_checklist_task", "task_id"),
        Index("idx_fin_reconciliation_checklist_file", "file_id"),
        Index("idx_fin_reconciliation_checklist_shop_period", "org_id", "shop_id", "accounting_period", postgresql_where=text("is_deleted = false")),
        Index(
            "idx_fin_reconciliation_checklist_summary",
            "org_id",
            "accounting_period",
            "merchant_id",
            "receipt_merchant_id",
            "live_promoter_id",
            "merchant_name",
            "receipt_merchant",
            "live_promoter",
            postgresql_where=text("is_deleted = false"),
        ),
        Index(
            "idx_fin_reconciliation_checklist_export",
            "org_id",
            "accounting_period",
            "merchant_id",
            "receipt_merchant_id",
            "live_promoter_id",
            "merchant_name",
            "receipt_merchant",
            "live_promoter",
            "product_name",
            postgresql_where=text("is_deleted = false"),
        ),
        Index("idx_fin_reconciliation_checklist_live_promoter_filter", "org_id", "accounting_period", "live_promoter_id", postgresql_where=text("is_deleted = false")),
        Index("idx_fin_reconciliation_checklist_merchant_filter", "org_id", "accounting_period", "merchant_id", postgresql_where=text("is_deleted = false")),
        Index("idx_fin_reconciliation_checklist_receipt_filter", "org_id", "accounting_period", "receipt_merchant_id", postgresql_where=text("is_deleted = false")),
        {"comment": "对账清单明细表", "postgresql_partition_by": "RANGE (accounting_period)"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    task_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("fin_reconciliation_checklist_tasks.id"), nullable=False, comment="处理任务ID")
    file_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("fin_reconciliation_checklist_upload_files.id"), nullable=False, comment="上传文件ID")
    org_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("fin_organizations.id"), nullable=False, comment="所属组织ID")
    shop_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("fin_shops.id"), nullable=False, comment="店铺ID")
    platform_code: Mapped[str] = mapped_column(String(50), nullable=False, comment="平台")
    shop_name: Mapped[str] = mapped_column(String(200), nullable=False, comment="店铺")
    accounting_year: Mapped[int] = mapped_column(SmallInteger, nullable=False, comment="动账时间年份")
    accounting_month: Mapped[int] = mapped_column(SmallInteger, nullable=False, comment="动账时间月份")
    accounting_period: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False, comment="动账时间年月 YYYYMM")
    source_row_number: Mapped[int] = mapped_column(Integer, default=0, comment="源文件行号")
    transaction_time: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, comment="动账时间")
    transaction_flow_no: Mapped[str] = mapped_column(String(500), nullable=False, default="", comment="动账流水号")
    product_name: Mapped[str] = mapped_column(String(500), nullable=False, default="", comment="商品名称")
    live_promoter_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("fin_reconciliation_checklist_entities.id"), nullable=True, comment="直播推广方ID")
    merchant_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("fin_reconciliation_checklist_entities.id"), nullable=True, comment="商家ID")
    receipt_merchant_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("fin_reconciliation_checklist_entities.id"), nullable=True, comment="收款商家ID")
    live_promoter: Mapped[str] = mapped_column(String(500), nullable=False, default="", comment="直播推广方")
    merchant_name: Mapped[str] = mapped_column(String(500), nullable=False, default="", comment="商家")
    receipt_merchant: Mapped[str] = mapped_column(String(500), nullable=False, default="", comment="收款商家")
    order_amount: Mapped[Decimal] = mapped_column(NUMERIC(14, 2), nullable=False, default=0, comment="订单金额")
    live_commission: Mapped[Decimal] = mapped_column(NUMERIC(14, 2), nullable=False, default=0, comment="直播推广佣金")
    merchant_net_amount: Mapped[Decimal] = mapped_column(NUMERIC(14, 2), nullable=False, default=0, comment="应付商家净额")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="更新时间")


class ReconciliationChecklistSummaryRow(Base):
    __tablename__ = "fin_reconciliation_checklist_summary_rows"
    __table_args__ = (
        Index(
            "uq_fin_reconciliation_checklist_summary_row",
            "org_id",
            "shop_id",
            "accounting_period",
            "platform_code",
            "merchant_id",
            "receipt_merchant_id",
            "live_promoter_id",
            "merchant_name",
            "receipt_merchant",
            "live_promoter",
            unique=True,
        ),
        Index(
            "idx_fin_reconciliation_checklist_summary_row_query",
            "org_id",
            "accounting_period",
            "merchant_id",
            "receipt_merchant_id",
            "live_promoter_id",
        ),
        {"comment": "对账清单预聚合汇总表", "postgresql_partition_by": "RANGE (accounting_period)"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    org_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("fin_organizations.id"), nullable=False, comment="所属组织ID")
    shop_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("fin_shops.id"), nullable=False, comment="店铺ID")
    platform_code: Mapped[str] = mapped_column(String(50), nullable=False, comment="平台")
    shop_name: Mapped[str] = mapped_column(String(200), nullable=False, comment="店铺")
    accounting_year: Mapped[int] = mapped_column(SmallInteger, nullable=False, comment="动账时间年份")
    accounting_month: Mapped[int] = mapped_column(SmallInteger, nullable=False, comment="动账时间月份")
    accounting_period: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False, comment="动账时间年月 YYYYMM")
    live_promoter_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("fin_reconciliation_checklist_entities.id"), nullable=True, comment="直播推广方ID")
    merchant_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("fin_reconciliation_checklist_entities.id"), nullable=True, comment="商家ID")
    receipt_merchant_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("fin_reconciliation_checklist_entities.id"), nullable=True, comment="收款商家ID")
    live_promoter: Mapped[str] = mapped_column(String(500), nullable=False, default="", comment="直播推广方")
    merchant_name: Mapped[str] = mapped_column(String(500), nullable=False, default="", comment="商家")
    receipt_merchant: Mapped[str] = mapped_column(String(500), nullable=False, default="", comment="收款商家")
    product_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="货品数量")
    total_order_amount: Mapped[Decimal] = mapped_column(NUMERIC(14, 2), nullable=False, default=0, comment="订单总金额")
    total_live_commission: Mapped[Decimal] = mapped_column(NUMERIC(14, 2), nullable=False, default=0, comment="直播推广佣金总金额")
    total_merchant_net_amount: Mapped[Decimal] = mapped_column(NUMERIC(14, 2), nullable=False, default=0, comment="应付商家净额总金额")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="更新时间")


class ReconciliationChecklistSummaryProductRow(Base):
    __tablename__ = "fin_reconciliation_checklist_summary_product_rows"
    __table_args__ = (
        Index(
            "uq_fin_reconciliation_checklist_summary_product_row",
            "org_id",
            "shop_id",
            "accounting_period",
            "platform_code",
            "merchant_id",
            "receipt_merchant_id",
            "live_promoter_id",
            "merchant_name",
            "receipt_merchant",
            "live_promoter",
            "product_name",
            unique=True,
        ),
        Index(
            "idx_fin_reconciliation_checklist_summary_product_query",
            "org_id",
            "accounting_period",
            "merchant_id",
            "receipt_merchant_id",
            "live_promoter_id",
            "product_name",
        ),
        {"comment": "对账清单商品预聚合汇总表", "postgresql_partition_by": "RANGE (accounting_period)"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    org_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("fin_organizations.id"), nullable=False, comment="所属组织ID")
    shop_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("fin_shops.id"), nullable=False, comment="店铺ID")
    platform_code: Mapped[str] = mapped_column(String(50), nullable=False, comment="平台")
    shop_name: Mapped[str] = mapped_column(String(200), nullable=False, comment="店铺")
    accounting_year: Mapped[int] = mapped_column(SmallInteger, nullable=False, comment="动账时间年份")
    accounting_month: Mapped[int] = mapped_column(SmallInteger, nullable=False, comment="动账时间月份")
    accounting_period: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False, comment="动账时间年月 YYYYMM")
    live_promoter_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("fin_reconciliation_checklist_entities.id"), nullable=True, comment="直播推广方ID")
    merchant_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("fin_reconciliation_checklist_entities.id"), nullable=True, comment="商家ID")
    receipt_merchant_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("fin_reconciliation_checklist_entities.id"), nullable=True, comment="收款商家ID")
    live_promoter: Mapped[str] = mapped_column(String(500), nullable=False, default="", comment="直播推广方")
    merchant_name: Mapped[str] = mapped_column(String(500), nullable=False, default="", comment="商家")
    receipt_merchant: Mapped[str] = mapped_column(String(500), nullable=False, default="", comment="收款商家")
    product_name: Mapped[str] = mapped_column(String(500), nullable=False, default="", comment="商品名称")
    product_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="货品数量")
    total_order_amount: Mapped[Decimal] = mapped_column(NUMERIC(14, 2), nullable=False, default=0, comment="订单总金额")
    total_live_commission: Mapped[Decimal] = mapped_column(NUMERIC(14, 2), nullable=False, default=0, comment="直播推广佣金总金额")
    total_merchant_net_amount: Mapped[Decimal] = mapped_column(NUMERIC(14, 2), nullable=False, default=0, comment="应付商家净额总金额")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="更新时间")
