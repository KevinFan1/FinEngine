from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, SmallInteger, String, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, SoftDeleteMixin


class User(SoftDeleteMixin, Base):
    __tablename__ = "fin_users"
    __table_args__ = (
        Index("uq_fin_user_username", "username", unique=True, postgresql_where=text("is_deleted = false")),
        Index("uq_fin_user_phone", "phone", unique=True, postgresql_where=text("is_deleted = false")),
        {"comment": "用户表"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    org_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("fin_organizations.id"), nullable=True, comment="所属组织ID")
    username: Mapped[str] = mapped_column(String(50), nullable=False, comment="用户名")
    phone: Mapped[str] = mapped_column(String(20), nullable=False, comment="手机号")
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False, comment="密码哈希")
    display_name: Mapped[str] = mapped_column(String(100), nullable=False, comment="显示名称")
    email: Mapped[str | None] = mapped_column(String(200), nullable=True, comment="邮箱")
    role: Mapped[str] = mapped_column(String(20), default="member", comment="角色: superadmin/org_admin/member")
    status: Mapped[int] = mapped_column(SmallInteger, default=1, comment="状态: 1=启用 0=禁用")
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="最后登录时间")
    active_session_id: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="当前有效登录会话ID")
    active_session_ip: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="当前登录IP")
    active_session_user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="当前登录客户端")
    active_session_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="当前会话登录时间")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="更新时间")
