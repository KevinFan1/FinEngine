"""平台文件表头规格，用于自动识别上传文件。"""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, SmallInteger, String, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, SoftDeleteMixin


class FileSpec(SoftDeleteMixin, Base):
    __tablename__ = "fin_file_specs"
    __table_args__ = (
        Index(
            "uq_fin_file_spec_platform_type",
            "platform_id",
            "type_code",
            unique=True,
            postgresql_where=text("is_deleted = false"),
        ),
        {"comment": "平台文件表头规格表"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    platform_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("fin_platforms.id"), nullable=False, comment="平台ID")
    type_code: Mapped[str] = mapped_column(String(30), nullable=False, comment="业务类型：动账/gmv/bic/运费险/订单")
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="规格名称，如「抖音动账」")

    # 期望表头：按顺序保存的列名列表
    headers: Mapped[list] = mapped_column(JSONB, nullable=False, comment="期望表头列表")
    match_threshold: Mapped[int] = mapped_column(SmallInteger, default=5, comment="最少匹配表头数量")
    upload_period_header: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="上传所属年月取数表头")

    status: Mapped[int] = mapped_column(SmallInteger, default=1, comment="1=启用 0=禁用")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="更新时间")
