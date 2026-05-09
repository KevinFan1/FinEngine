from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Index, SmallInteger, String, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, SoftDeleteMixin


class Organization(SoftDeleteMixin, Base):
    __tablename__ = "fin_organizations"
    __table_args__ = (
        Index("uq_fin_org_name", "name", unique=True, postgresql_where=text("is_deleted = false")),
        Index("uq_fin_org_code", "code", unique=True, postgresql_where=text("is_deleted = false")),
        {"comment": "组织表"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="组织名称")
    code: Mapped[str] = mapped_column(String(50), nullable=False, comment="组织编码")
    status: Mapped[int] = mapped_column(SmallInteger, default=1, comment="状态: 1=启用 0=禁用")
    remark: Mapped[str | None] = mapped_column(Text, nullable=True, comment="备注")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="更新时间")
