from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, SmallInteger, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB, NUMERIC
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, SoftDeleteMixin


class BicUploadFile(SoftDeleteMixin, Base):
    __tablename__ = "fin_bic_upload_files"
    __table_args__ = (
        Index(
            "uq_fin_bic_upload_source_file",
            "source_upload_file_id",
            unique=True,
            postgresql_where=text(
                "is_deleted = false AND source_upload_file_id IS NOT NULL"
            ),
        ),
        Index(
            "idx_fin_bic_upload_business_key",
            "org_id",
            "platform_code",
            "shop_id",
            "accounting_year",
            "accounting_month",
            postgresql_where=text(
                "is_deleted = false "
                "AND platform_code IS NOT NULL "
                "AND shop_id IS NOT NULL "
                "AND accounting_year IS NOT NULL "
                "AND accounting_month IS NOT NULL"
            ),
        ),
        {"comment": "BIC 独立上传文件表"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    org_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("fin_organizations.id"), nullable=False, comment="所属组织ID")
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("fin_users.id"), nullable=False, comment="上传用户ID")
    shop_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("fin_shops.id"), nullable=True, comment="店铺ID")
    source_upload_file_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("fin_upload_files.id"),
        nullable=True,
        comment="统一上传来源文件 ID",
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


class BicTask(SoftDeleteMixin, Base):
    __tablename__ = "fin_bic_tasks"
    __table_args__ = {"comment": "BIC 独立任务表"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    file_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("fin_bic_upload_files.id"), nullable=False, comment="BIC上传文件ID")
    org_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("fin_organizations.id"), nullable=False, comment="所属组织ID")
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("fin_users.id"), nullable=False, comment="触发用户ID")
    celery_task_id: Mapped[str | None] = mapped_column(String(200), nullable=True, comment="异步任务 ID（Celery）")
    status: Mapped[str] = mapped_column(String(20), default="queued", comment="任务状态")
    progress: Mapped[int] = mapped_column(SmallInteger, default=0, comment="进度百分比")
    processed_rows: Mapped[int] = mapped_column(Integer, default=0, comment="已处理行数")
    success_rows: Mapped[int] = mapped_column(Integer, default=0, comment="成功行数")
    failed_rows: Mapped[int] = mapped_column(Integer, default=0, comment="失败行数")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True, comment="错误信息")
    result_summary: Mapped[dict | None] = mapped_column(JSONB, nullable=True, comment="处理结果摘要")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="开始时间")
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="结束时间")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="更新时间")


class BicDetail(SoftDeleteMixin, Base):
    __tablename__ = "fin_bic_details"
    __table_args__ = (
        Index("idx_fin_bic_details_task", "task_id"),
        Index("idx_fin_bic_details_org_period", "org_id", "accounting_year", "accounting_month"),
        Index("idx_fin_bic_details_provider", "service_provider"),
        Index("idx_fin_bic_details_qic", "qic_warehouse"),
        {"comment": "BIC 核算明细汇总表"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    task_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("fin_bic_tasks.id"), nullable=False, comment="处理任务ID")
    file_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("fin_bic_upload_files.id"), nullable=False, comment="上传文件ID")
    org_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("fin_organizations.id"), nullable=False, comment="所属组织ID")
    shop_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("fin_shops.id"), nullable=True, comment="店铺ID")
    platform_code: Mapped[str] = mapped_column(String(50), nullable=False, comment="平台编码")
    shop_name: Mapped[str] = mapped_column(String(200), nullable=False, comment="店铺名称")
    accounting_year: Mapped[int] = mapped_column(SmallInteger, nullable=False, comment="文件名核算年份")
    accounting_month: Mapped[int] = mapped_column(SmallInteger, nullable=False, comment="文件名核算月份")
    service_provider: Mapped[str] = mapped_column(String(200), nullable=False, default="-", comment="服务商")
    qic_warehouse: Mapped[str] = mapped_column(String(200), nullable=False, comment="QIC仓")
    row_count: Mapped[int] = mapped_column(Integer, default=0, comment="汇总行数")
    total_amount: Mapped[float] = mapped_column(NUMERIC(14, 2), default=0, comment="结算金额合计")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")


class BicSourceRow(SoftDeleteMixin, Base):
    __tablename__ = "fin_bic_source_rows"
    __table_args__ = (
        Index(
            "uq_fin_bic_source_platform_flow",
            "platform_code",
            "transaction_flow_no",
            unique=True,
            postgresql_where=text("is_deleted = false AND transaction_flow_no <> ''"),
        ),
        Index("idx_fin_bic_source_detail", "detail_id"),
        Index("idx_fin_bic_source_task", "task_id"),
        Index("idx_fin_bic_source_org_period_provider", "org_id", "accounting_year", "accounting_month", "service_provider"),
        Index("idx_fin_bic_source_export", "org_id", "accounting_year", "accounting_month", "service_provider", "shop_id", "qic_warehouse"),
        Index(
            "idx_fin_bic_source_filters",
            "org_id",
            "platform_code",
            "accounting_year",
            "accounting_month",
            "shop_id",
            "qic_warehouse",
            "service_provider",
            postgresql_where=text("is_deleted = false"),
        ),
        {"comment": "BIC 源数据明细表"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    task_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("fin_bic_tasks.id"), nullable=False, comment="处理任务ID")
    file_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("fin_bic_upload_files.id"), nullable=False, comment="上传文件ID")
    detail_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("fin_bic_details.id"), nullable=False, comment="BIC明细汇总ID")
    org_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("fin_organizations.id"), nullable=False, comment="所属组织ID")
    shop_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("fin_shops.id"), nullable=True, comment="店铺ID")
    platform_code: Mapped[str] = mapped_column(String(50), nullable=False, comment="平台编码")
    shop_name: Mapped[str] = mapped_column(String(200), nullable=False, comment="店铺名称")
    accounting_year: Mapped[int] = mapped_column(SmallInteger, nullable=False, comment="文件名核算年份")
    accounting_month: Mapped[int] = mapped_column(SmallInteger, nullable=False, comment="文件名核算月份")
    service_provider: Mapped[str] = mapped_column(String(200), nullable=False, default="-", comment="服务商")
    qic_warehouse: Mapped[str] = mapped_column(String(200), nullable=False, default="-", comment="QIC仓")
    source_row_number: Mapped[int] = mapped_column(Integer, default=0, comment="源文件行号")
    settlement_no: Mapped[str] = mapped_column(String(300), nullable=False, default="", comment="结算单号")
    order_code: Mapped[str] = mapped_column(String(100), nullable=False, default="", comment="订单码")
    related_order_no: Mapped[str] = mapped_column(String(100), nullable=False, default="", comment="关联订单号")
    related_waybill_no: Mapped[str] = mapped_column(String(100), nullable=False, default="", comment="关联运单号")
    fee_item: Mapped[str] = mapped_column(String(100), nullable=False, default="", comment="费用项")
    settlement_amount: Mapped[float] = mapped_column(NUMERIC(14, 2), nullable=False, default=0, comment="结算金额")
    billing_params: Mapped[str] = mapped_column(Text, nullable=False, default="", comment="计费参数")
    billing_completed_time: Mapped[str] = mapped_column(String(100), nullable=False, default="", comment="计费完成时间")
    business_node: Mapped[str] = mapped_column(String(100), nullable=False, default="", comment="业务节点")
    business_occurred_time: Mapped[str] = mapped_column(String(100), nullable=False, default="", comment="业务发生时间")
    settled_at: Mapped[str] = mapped_column(String(100), nullable=False, default="", comment="结算时间")
    status: Mapped[str] = mapped_column(String(100), nullable=False, default="", comment="状态")
    transaction_account: Mapped[str] = mapped_column(String(100), nullable=False, default="", comment="动账账户")
    transaction_flow_no: Mapped[str] = mapped_column(String(200), nullable=False, default="", comment="动账流水号")
    remark: Mapped[str] = mapped_column(Text, nullable=False, default="", comment="备注")
    is_mudaibao: Mapped[str] = mapped_column(String(20), nullable=False, default="", comment="是否木带宝")
    is_child_order: Mapped[str] = mapped_column(String(20), nullable=False, default="", comment="是否子单")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
