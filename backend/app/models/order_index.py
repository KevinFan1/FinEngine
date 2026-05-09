from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, SmallInteger, String, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, SoftDeleteMixin


class OrderIndex(SoftDeleteMixin, Base):
    __tablename__ = "fin_order_indexes"
    __table_args__ = (
        Index(
            "uq_fin_order_index_platform_order",
            "platform_code",
            "order_no",
            unique=True,
            postgresql_where=text("is_deleted = false"),
        ),
        {"comment": "订单时间索引表"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    org_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("fin_organizations.id"), nullable=False, comment="所属组织ID")
    shop_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("fin_shops.id"), nullable=True, comment="店铺ID")
    platform_code: Mapped[str] = mapped_column(String(30), nullable=False, comment="平台编码")
    order_no: Mapped[str] = mapped_column(String(100), nullable=False, comment="订单号")
    order_created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, comment="订单创建时间")
    order_year: Mapped[int] = mapped_column(SmallInteger, nullable=False, comment="订单创建年份")
    order_month: Mapped[int] = mapped_column(SmallInteger, nullable=False, comment="订单创建月份")
    first_file_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("fin_upload_files.id"), nullable=True, comment="首次来源文件ID")
    last_file_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("fin_upload_files.id"), nullable=True, comment="最近来源文件ID")
    extra_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True, comment="扩展数据")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="更新时间")
