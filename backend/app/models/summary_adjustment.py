from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, SmallInteger, String, Text, func
from sqlalchemy.dialects.postgresql import NUMERIC
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, SoftDeleteMixin


class SummaryAdjustment(SoftDeleteMixin, Base):
    """汇总报表人工调整记录。

    调整只作用于汇总报表展示和导出，不回写动账明细或原始汇总数据。
    """

    __tablename__ = "fin_summary_adjustments"
    __table_args__ = (
        Index("idx_fin_summary_adjustments_lookup", "org_id", "source_year", "source_month", "platform_name", "shop_id"),
        Index("idx_fin_summary_adjustments_metric", "org_id", "metric_key"),
        {"comment": "汇总报表调整表"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    org_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("fin_organizations.id"), nullable=False, comment="所属组织ID")
    source_year: Mapped[int] = mapped_column(SmallInteger, nullable=False, comment="数据表上传年份")
    source_month: Mapped[int] = mapped_column(SmallInteger, nullable=False, comment="数据表上传月份")
    platform_name: Mapped[str] = mapped_column(String(50), nullable=False, comment="平台编码")
    shop_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("fin_shops.id"), nullable=False, comment="店铺ID")
    shop_name: Mapped[str] = mapped_column(String(200), nullable=False, comment="店铺名称快照")
    metric_key: Mapped[str] = mapped_column(String(50), nullable=False, comment="调整指标：实收GMV/退货费用及其他费用")
    adjustment_amount: Mapped[float] = mapped_column(NUMERIC(14, 2), nullable=False, default=0, comment="有符号调整金额，正数增加，负数减少")
    remark: Mapped[str | None] = mapped_column(Text, nullable=True, comment="调整备注")
    created_by: Mapped[int] = mapped_column(BigInteger, ForeignKey("fin_users.id"), nullable=False, comment="创建用户ID")
    updated_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("fin_users.id"), nullable=True, comment="最近修改用户ID")
    deleted_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("fin_users.id"), nullable=True, comment="删除用户ID")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="更新时间")
