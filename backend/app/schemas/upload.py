from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field, field_validator


# Allowed file extensions and MIME types
ALLOWED_EXTENSIONS = {'.xlsx', '.xlsm', '.xls', '.csv'}
ALLOWED_MIME_TYPES = {
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/vnd.ms-excel',
    'application/vnd.ms-excel.sheet.macroEnabled.12',
    'text/csv',
    'application/csv',
}


class UploadBatchCreate(BaseModel):
    file_count: int = Field(..., ge=1, description="文件数量")
    total_bytes: int = Field(0, ge=0, description="本次计划上传总字节数，用于上传前检查每月额度")
    org_id: int | None = Field(None, description="目标组织 ID，仅超级管理员上传时需要")
    remark: str | None = Field(None, max_length=2000, description="备注")


class UploadFileCallback(BaseModel):
    batch_id: int = Field(..., description="上传批次 ID")
    original_name: str = Field(..., min_length=1, max_length=500, description="原始文件名")
    oss_key: str = Field(..., min_length=1, max_length=1000, description="OSS 存储路径")
    file_size: int = Field(..., ge=0, le=1024 * 1024 * 1024, description="文件大小(字节)，最大 1GB")
    file_hash: str | None = Field(None, max_length=64, description="SHA256 校验")
    content_type: str | None = Field(None, max_length=200, description="文件 MIME 类型")
    parsed_year: int | None = Field(None, description="解析出的年份")
    parsed_month: int | None = Field(None, description="解析出的月份")
    parsed_type: str | None = Field(None, max_length=20, description="类型: 动账/gmv/bic/运费险/订单/其他服务款")
    parsed_shop: str | None = Field(None, max_length=200, description="店铺名")
    detected_platform: str | None = Field(None, max_length=30, description="检测到的平台编码")

    @field_validator('original_name')
    @classmethod
    def validate_filename(cls, v: str) -> str:
        """Validate file extension."""
        ext = Path(v).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise ValueError(f"不支持的文件类型: {ext}，仅支持 {', '.join(ALLOWED_EXTENSIONS)}")
        return v

    @field_validator('content_type')
    @classmethod
    def validate_content_type(cls, v: str | None) -> str | None:
        """Validate MIME type."""
        if v and v not in ALLOWED_MIME_TYPES:
            raise ValueError(f"不支持的 MIME 类型: {v}")
        return v


class UploadBatchOut(BaseModel):
    id: int
    org_id: int
    user_id: int
    file_count: int
    status: str
    remark: str | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UploadFileOut(BaseModel):
    id: int
    batch_id: int
    org_id: int
    user_id: int
    shop_id: int | None
    original_name: str
    oss_key: str
    file_size: int
    file_hash: str | None
    parsed_year: int | None
    parsed_month: int | None
    parsed_type: str | None
    parsed_shop: str | None
    detected_platform: str | None
    source_platform_code: str | None
    report_platform_code: str | None
    processor_code: str | None
    order_scope_code: str | None
    status: str
    error_message: str | None
    row_count: int | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UploadBatchDetail(UploadBatchOut):
    files: list[UploadFileOut] = []
