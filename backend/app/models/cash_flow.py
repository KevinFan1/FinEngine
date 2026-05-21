from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, SmallInteger, String, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, SoftDeleteMixin


class CashFlowItem(SoftDeleteMixin, Base):
    __tablename__ = "fin_cash_flow_items"
    __table_args__ = (
        Index(
            "uq_fin_cash_flow_item_code",
            "code",
            unique=True,
            postgresql_where=text("is_deleted = false"),
        ),
        Index("idx_fin_cash_flow_items_parent", "parent_id", "sort_order"),
        {"comment": "现金流项目字典表"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    code: Mapped[str] = mapped_column(String(20), nullable=False, comment="项目编号")
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="项目名称")
    parent_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("fin_cash_flow_items.id"), nullable=True, comment="父级项目ID")
    level: Mapped[int] = mapped_column(SmallInteger, nullable=False, comment="层级：1=大类 2=明细 3=校验")
    item_type: Mapped[str] = mapped_column(String(20), nullable=False, comment="分组/明细/净额/校验")
    flow_section: Mapped[str] = mapped_column(String(20), nullable=False, comment="经营/投资/筹资")
    flow_direction: Mapped[str | None] = mapped_column(String(20), nullable=True, comment="流入/流出/净额/校验")
    summary_method: Mapped[str] = mapped_column(String(20), nullable=False, comment="汇总子项/公式/手动/不汇总")
    sort_order: Mapped[int] = mapped_column(Integer, default=100, comment="排序")
    status: Mapped[int] = mapped_column(SmallInteger, default=1, comment="1=启用 0=停用")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="更新时间")
