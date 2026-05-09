from datetime import datetime

from sqlalchemy import Boolean, DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class SoftDeleteMixin:
    """Common soft-delete columns for all business tables."""

    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False, comment="是否已软删除")
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="软删除时间")
