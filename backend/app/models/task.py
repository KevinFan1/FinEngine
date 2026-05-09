from datetime import datetime
from json import dumps

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, SmallInteger, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, SoftDeleteMixin


class ProcessingTask(SoftDeleteMixin, Base):
    __tablename__ = "fin_processing_tasks"
    __table_args__ = {"comment": "文件处理任务表"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    file_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("fin_upload_files.id"), nullable=False, comment="上传文件ID")
    org_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("fin_organizations.id"), nullable=False, comment="所属组织ID")
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("fin_users.id"), nullable=False, comment="触发用户ID")

    # Celery task tracking
    celery_task_id: Mapped[str | None] = mapped_column(String(200), nullable=True, comment="Celery任务ID")
    status: Mapped[str] = mapped_column(String(20), default="queued", comment="任务状态")
    progress: Mapped[int] = mapped_column(SmallInteger, default=0, comment="进度百分比 0~100")

    # Execution results
    processed_rows: Mapped[int] = mapped_column(Integer, default=0, comment="已处理行数")
    success_rows: Mapped[int] = mapped_column(Integer, default=0, comment="成功行数")
    failed_rows: Mapped[int] = mapped_column(Integer, default=0, comment="失败行数")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True, comment="错误信息")
    result_summary: Mapped[dict | None] = mapped_column(JSONB, nullable=True, comment="处理结果摘要")

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="开始时间")
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="结束时间")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="更新时间")

    @property
    def error_reason(self) -> str | None:
        if self.error_message:
            return self.error_message

        if not self.result_summary:
            return None

        errors = self.result_summary.get("errors")
        if not errors:
            return None
        if isinstance(errors, list):
            return "；".join(str(error) for error in errors if error)
        if isinstance(errors, str):
            return errors
        return dumps(errors, ensure_ascii=False)
