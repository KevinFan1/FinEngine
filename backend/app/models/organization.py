from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Index, Integer, SmallInteger, String, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, SoftDeleteMixin


class Organization(SoftDeleteMixin, Base):
    __tablename__ = "fin_organizations"
    __table_args__ = (
        Index("uq_fin_org_name", "name", unique=True, postgresql_where=text("is_deleted = false")),
        Index("uq_fin_org_code", "code", unique=True, postgresql_where=text("is_deleted = false")),
        Index("idx_org_plan_type", "plan_type"),
        {"comment": "组织表"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="组织名称")
    code: Mapped[str] = mapped_column(String(50), nullable=False, comment="组织编码")
    status: Mapped[int] = mapped_column(SmallInteger, default=1, comment="状态: 1=启用 0=禁用")
    remark: Mapped[str | None] = mapped_column(Text, nullable=True, comment="备注")

    # 配额管理
    max_users: Mapped[int] = mapped_column(Integer, default=5, comment="最大用户数量（免费版 5 个）")
    max_storage_bytes: Mapped[int] = mapped_column(
        BigInteger,
        default=1 * 1024 * 1024 * 1024,  # 1GB
        comment="最大存储容量（字节）"
    )
    used_storage_bytes: Mapped[int] = mapped_column(BigInteger, default=0, comment="已使用存储容量（字节）")

    # 套餐管理
    plan_type: Mapped[str] = mapped_column(
        String(20),
        default="free",
        comment="套餐类型: free=免费版, basic=基础版, pro=专业版, enterprise=企业版"
    )
    plan_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="套餐到期时间（免费版为 NULL）"
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="更新时间")

