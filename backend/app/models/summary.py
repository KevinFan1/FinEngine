from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, SmallInteger, String, func, text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, NUMERIC
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, SoftDeleteMixin


class FinancialSummary(SoftDeleteMixin, Base):
    __tablename__ = "fin_financial_summaries"
    __table_args__ = (
        Index(
            "uq_fin_summary_lookup",
            "org_id",
            "summary_year",
            "summary_month",
            "shop_id",
            "source_year",
            "source_month",
            unique=True,
            postgresql_where=text("is_deleted = false"),
        ),
        Index("idx_fin_summaries_source_lookup", "org_id", "source_year", "source_month"),
        {"comment": "财务汇总表"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    org_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("fin_organizations.id"), nullable=False, comment="所属组织ID")
    shop_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("fin_shops.id"), nullable=False, comment="店铺ID")

    # Unique key dimensions
    summary_year: Mapped[int] = mapped_column(SmallInteger, nullable=False, comment="汇总年份")
    summary_month: Mapped[int] = mapped_column(SmallInteger, nullable=False, comment="汇总月份")
    source_year: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0, server_default=text("0"), comment="数据表上传年份，来自文件名解析")
    source_month: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0, server_default=text("0"), comment="数据表上传月份，来自文件名解析")
    platform_name: Mapped[str] = mapped_column(String(50), nullable=False, comment="平台编码冗余")
    shop_name: Mapped[str] = mapped_column(String(200), nullable=False, comment="店铺名称冗余")

    # 财务指标列 — 由「动账」文件填充
    gmv: Mapped[float] = mapped_column(NUMERIC(14, 2), default=0, comment="实收GMV")
    platform_income: Mapped[float] = mapped_column(NUMERIC(14, 2), default=0, comment="平台其他收入")
    platform_fee: Mapped[float] = mapped_column(NUMERIC(14, 2), default=0, comment="平台服务费")
    return_cost: Mapped[float] = mapped_column(NUMERIC(14, 2), default=0, comment="退货费用及其他费用")
    commission: Mapped[float] = mapped_column(NUMERIC(14, 2), default=0, comment="达人佣金")
    merchant_fee: Mapped[float] = mapped_column(NUMERIC(14, 2), default=0, comment="招商服务费")
    promotion_fee: Mapped[float] = mapped_column(NUMERIC(14, 2), default=0, comment="站外推广费")
    provider_commission: Mapped[float] = mapped_column(NUMERIC(14, 2), default=0, comment="服务商佣金")
    donation_fee: Mapped[float] = mapped_column(NUMERIC(14, 2), default=0, comment="支付捐赠费用")

    # 由「运费险」文件填充
    insurance_fee: Mapped[float] = mapped_column(NUMERIC(14, 2), default=0, comment="运费险")

    # 由「bic」文件填充
    bic: Mapped[float] = mapped_column(NUMERIC(14, 2), default=0, comment="BIC")

    # 扩展字段
    extra_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True, comment="扩展数据")

    # 来源追踪
    source_file_ids: Mapped[list[int]] = mapped_column(ARRAY(BigInteger), default=list, comment="来源文件ID列表")
    last_file_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("fin_upload_files.id"), nullable=True, comment="最近来源文件ID")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="更新时间")
