from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Index, Integer, SmallInteger, String, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, SoftDeleteMixin


class Platform(SoftDeleteMixin, Base):
    __tablename__ = "fin_platforms"
    __table_args__ = (
        Index("uq_fin_platform_code", "code", unique=True, postgresql_where=text("is_deleted = false")),
        {"comment": "平台表"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    code: Mapped[str] = mapped_column(String(30), nullable=False, comment="平台编码")
    name: Mapped[str] = mapped_column(String(50), nullable=False, comment="平台名称")
    parent_code: Mapped[str | None] = mapped_column(String(30), nullable=True, comment="父平台编码，用于汇总报表归集")
    processor_code: Mapped[str | None] = mapped_column(String(30), nullable=True, comment="处理器平台编码，默认等于平台编码")
    order_scope_code: Mapped[str | None] = mapped_column(String(30), nullable=True, comment="订单索引归属编码，默认等于父平台编码")
    sort_order: Mapped[int] = mapped_column(Integer, default=0, comment="排序值")
    status: Mapped[int] = mapped_column(SmallInteger, default=1, comment="状态: 1=启用 0=禁用")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
