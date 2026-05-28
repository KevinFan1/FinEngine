from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, SoftDeleteMixin


class ExportJob(SoftDeleteMixin, Base):
    __tablename__ = "fin_export_jobs"
    __table_args__ = (
        Index("idx_fin_export_jobs_user_status", "user_id", "status", "created_at"),
        Index("idx_fin_export_jobs_org_created", "org_id", "created_at"),
        {"comment": "异步导出任务表"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    org_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("fin_organizations.id"), nullable=True, comment="所属组织ID")
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("fin_users.id"), nullable=False, comment="创建用户ID")
    celery_task_id: Mapped[str | None] = mapped_column(String(200), nullable=True, comment="异步任务ID")

    module: Mapped[str] = mapped_column(String(50), nullable=False, comment="导出模块")
    export_type: Mapped[str] = mapped_column(String(80), nullable=False, comment="导出类型")
    title: Mapped[str] = mapped_column(String(200), nullable=False, comment="任务标题")
    filename: Mapped[str] = mapped_column(String(500), nullable=False, comment="文件名")
    params: Mapped[dict] = mapped_column(JSONB, nullable=False, comment="导出参数")

    status: Mapped[str] = mapped_column(String(20), default="queued", nullable=False, comment="状态")
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="进度百分比")
    row_count: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="导出行数")
    file_size: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="导出文件大小")
    oss_key: Mapped[str | None] = mapped_column(String(1000), nullable=True, comment="OSS文件路径")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True, comment="错误信息")
    result_summary: Mapped[dict | None] = mapped_column(JSONB, nullable=True, comment="导出结果摘要")

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="开始时间")
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="结束时间")
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="过期时间")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="更新时间")
