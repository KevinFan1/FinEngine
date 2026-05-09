from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, SmallInteger, String, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, SoftDeleteMixin


class CategoryDict(SoftDeleteMixin, Base):
    """动账分类字典 — 由超管维护，用于备注文本的自动分类。

    categories 结构示例:
    {
        "小额打款": ["小额打款", "售后单仲裁申诉通过打款", ...],
        "商家责任赔付": [...],
    }
    """

    __tablename__ = "fin_category_dicts"
    __table_args__ = (
        Index(
            "uq_fin_category_dict_platform_type",
            "platform_id",
            "type_code",
            unique=True,
            postgresql_where=text("is_deleted = false"),
        ),
        {"comment": "分类字典表"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    platform_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("fin_platforms.id"), nullable=False, comment="平台ID")
    type_code: Mapped[str] = mapped_column(String(30), nullable=False, comment="业务类型: 动账/gmv/bic/运费险/订单")
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="字典名称，如「抖音动账分类」")
    categories: Mapped[dict] = mapped_column(JSONB, nullable=False, comment="分类字典 JSON")
    status: Mapped[int] = mapped_column(SmallInteger, default=1, comment="1=启用 0=禁用")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="更新时间")
