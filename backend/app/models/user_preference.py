from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class UserPreference(Base):
    __tablename__ = "fin_user_preferences"
    __table_args__ = (
        Index("uq_fin_user_preference_user_key", "user_id", "preference_key", unique=True),
        {"comment": "用户偏好配置表"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("fin_users.id"), nullable=False, comment="用户ID")
    preference_key: Mapped[str] = mapped_column(String(100), nullable=False, comment="配置键")
    preference_value: Mapped[Any] = mapped_column(JSONB, nullable=False, comment="配置值(JSON)")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="更新时间")
