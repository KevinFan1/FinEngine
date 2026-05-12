"""Shop model — platform + shop_name unique per org."""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, SmallInteger, String, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, SoftDeleteMixin


class Shop(SoftDeleteMixin, Base):
    __tablename__ = "fin_shops"
    __table_args__ = (
        Index(
            "uq_fin_shop_org_platform_name",
            "org_id",
            "platform_name",
            "shop_name",
            unique=True,
            postgresql_where=text("is_deleted = false"),
        ),
        {"comment": "店铺表"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    org_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("fin_organizations.id"), nullable=False, comment="所属组织ID")
    platform_name: Mapped[str] = mapped_column(String(50), nullable=False, comment="平台编码或平台名称")
    shop_name: Mapped[str] = mapped_column(String(200), nullable=False, comment="店铺名称")
    shop_color: Mapped[str | None] = mapped_column(String(20), nullable=True, comment="店铺展示色")
    entity_name: Mapped[str | None] = mapped_column(String(200), nullable=True, comment="主体名称")
    remark: Mapped[str | None] = mapped_column(Text, nullable=True, comment="备注")
    status: Mapped[int] = mapped_column(SmallInteger, default=1, comment="状态: 1=启用 0=禁用")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="更新时间")
