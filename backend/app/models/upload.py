from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, SmallInteger, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, SoftDeleteMixin


class UploadBatch(SoftDeleteMixin, Base):
    __tablename__ = "fin_upload_batches"
    __table_args__ = {"comment": "上传批次表"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    org_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("fin_organizations.id"), nullable=False, comment="所属组织ID")
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("fin_users.id"), nullable=False, comment="上传用户ID")
    file_count: Mapped[int] = mapped_column(Integer, default=0, comment="文件数量")
    status: Mapped[str] = mapped_column(String(20), default="pending", comment="批次状态")
    remark: Mapped[str | None] = mapped_column(Text, nullable=True, comment="备注")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="更新时间")


class UploadFile(SoftDeleteMixin, Base):
    __tablename__ = "fin_upload_files"
    __table_args__ = {"comment": "上传文件表"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    batch_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("fin_upload_batches.id"), nullable=False, comment="上传批次ID")
    org_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("fin_organizations.id"), nullable=False, comment="所属组织ID")
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("fin_users.id"), nullable=False, comment="上传用户ID")
    shop_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("fin_shops.id"), nullable=True, comment="店铺ID")

    # File info
    original_name: Mapped[str] = mapped_column(String(500), nullable=False, comment="原始文件名")
    oss_key: Mapped[str] = mapped_column(String(1000), nullable=False, comment="OSS存储路径")
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="文件大小字节数")
    file_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="文件SHA256哈希")

    # Parsed metadata from filename
    parsed_year: Mapped[int | None] = mapped_column(SmallInteger, nullable=True, comment="文件名解析年份")
    parsed_month: Mapped[int | None] = mapped_column(SmallInteger, nullable=True, comment="文件名解析月份")
    parsed_type: Mapped[str | None] = mapped_column(String(20), nullable=True, comment="文件名解析业务类型")
    parsed_shop: Mapped[str | None] = mapped_column(String(200), nullable=True, comment="文件名解析店铺名称")

    # Detected platform from headers
    detected_platform: Mapped[str | None] = mapped_column(String(30), nullable=True, comment="表头识别平台编码")

    # Status
    status: Mapped[str] = mapped_column(String(20), default="uploaded", comment="文件处理状态")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True, comment="错误信息")
    row_count: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="处理行数")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="更新时间")
