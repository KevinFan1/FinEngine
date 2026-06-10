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
    task_type: Mapped[str] = mapped_column(String(30), nullable=False, default="source_import", server_default="source_import", comment="任务类型")
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


class ReconciliationChecklistOrderKey(Base):
    __tablename__ = "fin_reconciliation_checklist_order_keys"
    __table_args__ = (
        Index("uq_fin_reconciliation_checklist_order_key", "org_id", "sub_order_no", unique=True),
        Index("idx_fin_reconciliation_checklist_order_key_period", "org_id", "accounting_period"),
        {"comment": "对账清单子订单全局定位表"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    org_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("fin_organizations.id"), nullable=False, comment="所属组织ID")
    sub_order_no: Mapped[str] = mapped_column(String(200), nullable=False, comment="子订单号")
    accounting_period: Mapped[int] = mapped_column(Integer, nullable=False, comment="结算年月 YYYYMM")
    detail_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="明细ID")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="更新时间")


class ReconciliationChecklistDetail(SoftDeleteMixin, Base):
    __tablename__ = "fin_reconciliation_checklist_details"
    __table_args__ = (
        Index(
            "uq_fin_reconciliation_checklist_detail_row_fingerprint",
            "org_id",
            "accounting_period",
            "row_fingerprint",
            unique=True,
            postgresql_where=text("is_deleted = false AND row_fingerprint <> ''"),
        ),
        Index("idx_fin_reconciliation_checklist_id", "id"),
        Index("idx_fin_reconciliation_checklist_task", "task_id"),
        Index("idx_fin_reconciliation_checklist_file", "file_id"),
        Index("idx_fin_reconciliation_checklist_period_org", "accounting_period", "org_id", postgresql_where=text("is_deleted = false")),
        Index("idx_fin_reconciliation_checklist_sub_order", "org_id", "sub_order_no", postgresql_where=text("is_deleted = false")),
        Index("idx_fin_reconciliation_checklist_product_summary", "org_id", "accounting_period", "receipt_merchant", "merchant_subject_name", "product_name", postgresql_where=text("is_deleted = false")),
        Index("idx_fin_reconciliation_checklist_receipt_summary", "org_id", "accounting_period", "merchant_subject_name", "live_platform", "receipt_merchant", postgresql_where=text("is_deleted = false")),
        Index("idx_fin_reconciliation_checklist_balance_summary", "org_id", "accounting_period", "merchant_subject_name", "receipt_merchant", postgresql_where=text("is_deleted = false")),
        {"comment": "对账清单订单明细底表", "postgresql_partition_by": "RANGE (accounting_period)"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    task_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("fin_reconciliation_checklist_tasks.id"), nullable=False, comment="处理任务ID")
    file_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("fin_reconciliation_checklist_upload_files.id"), nullable=False, comment="上传文件ID")
    org_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("fin_organizations.id"), primary_key=True, nullable=False, comment="所属组织ID")
    accounting_year: Mapped[int] = mapped_column(SmallInteger, nullable=False, comment="结算年份")
    accounting_month: Mapped[int] = mapped_column(SmallInteger, nullable=False, comment="结算月份")
    accounting_period: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False, comment="结算年月 YYYYMM")
    source_row_number: Mapped[int] = mapped_column(Integer, default=0, comment="源文件行号")
    live_platform: Mapped[str] = mapped_column(String(100), nullable=False, default="", comment="进驻的直播平台")
    settlement_time: Mapped[datetime] = mapped_column(DateTime(timezone=False), nullable=False, comment="结算时间")
    sub_order_no: Mapped[str] = mapped_column(String(200), nullable=False, default="", comment="子订单号")
    row_fingerprint: Mapped[str] = mapped_column(String(32), nullable=False, default="", comment="系统行定位值")
    order_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True, comment="下单时间")
    product_id: Mapped[str] = mapped_column(String(200), nullable=False, default="", comment="商品ID")
    product_name: Mapped[str] = mapped_column(String(500), nullable=False, default="", comment="商品名称")
    product_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="商品数量")
    talent_name: Mapped[str] = mapped_column(String(500), nullable=False, default="", comment="达人名称")
    platform_subsidy: Mapped[Decimal] = mapped_column(NUMERIC(14, 2), nullable=False, default=0, comment="平台补贴")
    talent_subsidy: Mapped[Decimal] = mapped_column(NUMERIC(14, 2), nullable=False, default=0, comment="达人补贴")
    douyin_pay_subsidy: Mapped[Decimal] = mapped_column(NUMERIC(14, 2), nullable=False, default=0, comment="抖音支付补贴")
    douyin_monthly_pay_subsidy: Mapped[Decimal] = mapped_column(NUMERIC(14, 2), nullable=False, default=0, comment="抖音月付营销补贴")
    bank_subsidy: Mapped[Decimal] = mapped_column(NUMERIC(14, 2), nullable=False, default=0, comment="银行补贴")
    user_paid_amount: Mapped[Decimal] = mapped_column(NUMERIC(14, 2), nullable=False, default=0, comment="用户实付（订单金额）")
    platform_service_fee: Mapped[Decimal] = mapped_column(NUMERIC(14, 2), nullable=False, default=0, comment="平台服务费")
    talent_commission: Mapped[Decimal] = mapped_column(NUMERIC(14, 2), nullable=False, default=0, comment="达人佣金")
    investment_service_fee: Mapped[Decimal] = mapped_column(NUMERIC(14, 2), nullable=False, default=0, comment="招商服务费")
    merchant_subject_name: Mapped[str] = mapped_column(String(500), nullable=False, default="", comment="商户主体名称")
    customer_service_code: Mapped[str] = mapped_column(String(200), nullable=False, default="", comment="客服代码")
    receipt_merchant: Mapped[str] = mapped_column(String(500), nullable=False, default="", comment="收款商家")
    live_commission: Mapped[Decimal] = mapped_column(NUMERIC(14, 2), nullable=False, default=0, comment="直播推广佣金")
    commission_rate: Mapped[Decimal | None] = mapped_column(NUMERIC(10, 6), nullable=True, comment="佣金率")
    merchant_net_amount: Mapped[Decimal] = mapped_column(NUMERIC(14, 2), nullable=False, default=0, comment="应付商家净额")
    payment_amount: Mapped[Decimal | None] = mapped_column(NUMERIC(14, 2), nullable=True, comment="付款金额")
    merchant_net_balance: Mapped[Decimal] = mapped_column(NUMERIC(14, 2), nullable=False, default=0, comment="应付商家净额余额")
    merchant_payment_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True, comment="付款时间（商家）")
    invoice_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True, comment="开票时间")
    invoice_number: Mapped[str] = mapped_column(String(200), nullable=False, default="", comment="发票号码")
    raw_row: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict, comment="原始行JSON")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="更新时间")


class ReconciliationChecklistProductSummaryRow(Base):
    __tablename__ = "fin_reconciliation_checklist_product_summary_rows"
    __table_args__ = (
        Index(
            "uq_fin_reconciliation_checklist_product_summary",
            "org_id",
            "accounting_period",
            "receipt_merchant",
            "merchant_subject_name",
            "product_name",
            unique=True,
        ),
        Index("idx_fin_reconciliation_checklist_product_summary_query", "org_id", "accounting_period", "receipt_merchant", "merchant_subject_name", "product_name"),
        {"comment": "对账清单商品维度预聚合汇总表", "postgresql_partition_by": "RANGE (accounting_period)"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    org_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("fin_organizations.id"), primary_key=True, nullable=False, comment="所属组织ID")
    accounting_year: Mapped[int] = mapped_column(SmallInteger, nullable=False, comment="结算年份")
    accounting_month: Mapped[int] = mapped_column(SmallInteger, nullable=False, comment="结算月份")
    accounting_period: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False, comment="结算年月 YYYYMM")
    receipt_merchant: Mapped[str] = mapped_column(String(500), nullable=False, default="", comment="收款商家")
    merchant_subject_name: Mapped[str] = mapped_column(String(500), nullable=False, default="", comment="商户主体名称")
    product_name: Mapped[str] = mapped_column(String(500), nullable=False, default="", comment="商品名称")
    product_quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="商品数量合计")
    total_user_paid_amount: Mapped[Decimal] = mapped_column(NUMERIC(14, 2), nullable=False, default=0, comment="用户实付合计")
    total_live_commission: Mapped[Decimal] = mapped_column(NUMERIC(14, 2), nullable=False, default=0, comment="直播推广佣金合计")
    total_merchant_net_amount: Mapped[Decimal] = mapped_column(NUMERIC(14, 2), nullable=False, default=0, comment="应付商家净额合计")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="更新时间")


class ReconciliationChecklistReceiptSummaryRow(Base):
    __tablename__ = "fin_reconciliation_checklist_receipt_summary_rows"
    __table_args__ = (
        Index(
            "uq_fin_reconciliation_checklist_receipt_summary",
            "org_id",
            "accounting_period",
            "merchant_subject_name",
            "live_platform",
            "receipt_merchant",
            unique=True,
        ),
        Index("idx_fin_reconciliation_checklist_receipt_summary_query", "org_id", "accounting_period", "merchant_subject_name", "live_platform", "receipt_merchant"),
        {"comment": "对账清单收款商家维度预聚合汇总表", "postgresql_partition_by": "RANGE (accounting_period)"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    org_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("fin_organizations.id"), primary_key=True, nullable=False, comment="所属组织ID")
    accounting_year: Mapped[int] = mapped_column(SmallInteger, nullable=False, comment="结算年份")
    accounting_month: Mapped[int] = mapped_column(SmallInteger, nullable=False, comment="结算月份")
    accounting_period: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False, comment="结算年月 YYYYMM")
    merchant_subject_name: Mapped[str] = mapped_column(String(500), nullable=False, default="", comment="商户主体名称")
    live_platform: Mapped[str] = mapped_column(String(100), nullable=False, default="", comment="进驻的直播平台")
    receipt_merchant: Mapped[str] = mapped_column(String(500), nullable=False, default="", comment="收款商家")
    order_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="订单数量")
    total_user_paid_amount: Mapped[Decimal] = mapped_column(NUMERIC(14, 2), nullable=False, default=0, comment="用户实付合计")
    total_live_commission: Mapped[Decimal] = mapped_column(NUMERIC(14, 2), nullable=False, default=0, comment="直播推广佣金合计")
    total_merchant_net_amount: Mapped[Decimal] = mapped_column(NUMERIC(14, 2), nullable=False, default=0, comment="应付商家净额合计")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="更新时间")


class ReconciliationChecklistPayableBalanceSummaryRow(Base):
    __tablename__ = "fin_reconciliation_checklist_payable_balance_summary_rows"
    __table_args__ = (
        Index(
            "uq_fin_reconciliation_checklist_payable_balance_summary",
            "org_id",
            "accounting_period",
            "merchant_subject_name",
            "receipt_merchant",
            unique=True,
        ),
        Index("idx_fin_reconciliation_checklist_payable_balance_summary_query", "org_id", "accounting_period", "merchant_subject_name", "receipt_merchant"),
        {"comment": "对账清单商家应付余额预聚合汇总表", "postgresql_partition_by": "RANGE (accounting_period)"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    org_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("fin_organizations.id"), primary_key=True, nullable=False, comment="所属组织ID")
    accounting_year: Mapped[int] = mapped_column(SmallInteger, nullable=False, comment="结算年份")
    accounting_month: Mapped[int] = mapped_column(SmallInteger, nullable=False, comment="结算月份")
    accounting_period: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False, comment="结算年月 YYYYMM")
    merchant_subject_name: Mapped[str] = mapped_column(String(500), nullable=False, default="", comment="商户主体名称")
    receipt_merchant: Mapped[str] = mapped_column(String(500), nullable=False, default="", comment="收款商家")
    total_user_paid_amount: Mapped[Decimal] = mapped_column(NUMERIC(14, 2), nullable=False, default=0, comment="用户实付合计")
    total_merchant_net_amount: Mapped[Decimal] = mapped_column(NUMERIC(14, 2), nullable=False, default=0, comment="应付商家净额合计")
    total_payment_amount: Mapped[Decimal] = mapped_column(NUMERIC(14, 2), nullable=False, default=0, comment="付款金额合计")
    total_merchant_net_balance: Mapped[Decimal] = mapped_column(NUMERIC(14, 2), nullable=False, default=0, comment="应付商家净额余额合计")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="更新时间")


# Backwards-compatible aliases used by older imports while the UI/API migrates.
ReconciliationChecklistSummaryProductRow = ReconciliationChecklistProductSummaryRow
ReconciliationChecklistSummaryRow = ReconciliationChecklistReceiptSummaryRow
