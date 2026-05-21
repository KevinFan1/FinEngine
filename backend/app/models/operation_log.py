from datetime import datetime

from sqlalchemy import BigInteger, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, SoftDeleteMixin


class OperationLog(SoftDeleteMixin, Base):
    __tablename__ = "fin_operation_logs"
    __table_args__ = {"comment": "操作日志表"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")

    # 操作人信息
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="操作用户ID")
    org_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="操作组织ID")
    username: Mapped[str] = mapped_column(String(50), nullable=False, comment="用户名快照")
    display_name: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="显示名称快照")

    # 操作分类
    module: Mapped[str] = mapped_column(String(30), nullable=False, comment="模块")
    action: Mapped[str] = mapped_column(String(30), nullable=False, comment="操作动作")

    # 操作详情
    description: Mapped[str] = mapped_column(Text, nullable=False, comment="操作描述")
    target_type: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="目标类型")
    target_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, comment="目标ID")
    target_name: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="目标名称")

    # 请求上下文
    ip: Mapped[str | None] = mapped_column(String(45), nullable=True, comment="客户端IP")
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="客户端标识")
    method: Mapped[str | None] = mapped_column(String(10), nullable=True, comment="HTTP 请求方法")
    path: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="请求路径")

    # 变更记录
    old_value: Mapped[dict | None] = mapped_column(JSONB, nullable=True, comment="变更前数据")
    new_value: Mapped[dict | None] = mapped_column(JSONB, nullable=True, comment="变更后数据")

    # 扩展上下文
    extra_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True, comment="扩展数据")

    # 操作结果
    status: Mapped[str] = mapped_column(String(10), default="success", comment="操作结果")
    error_msg: Mapped[str | None] = mapped_column(Text, nullable=True, comment="错误信息")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
