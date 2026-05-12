from datetime import datetime

from pydantic import BaseModel, Field


class UploadBatchCreate(BaseModel):
    file_count: int = Field(..., ge=1, description="文件数量")
    org_id: int | None = Field(None, description="目标组织 ID，仅超级管理员上传时需要")
    remark: str | None = Field(None, description="备注")


class UploadFileCallback(BaseModel):
    batch_id: int = Field(..., description="上传批次 ID")
    original_name: str = Field(..., description="原始文件名")
    oss_key: str = Field(..., description="OSS 存储路径")
    file_size: int = Field(..., ge=0, description="文件大小(字节)")
    file_hash: str | None = Field(None, description="SHA256 校验")
    parsed_year: int | None = Field(None, description="解析出的年份")
    parsed_month: int | None = Field(None, description="解析出的月份")
    parsed_type: str | None = Field(None, description="类型: 动账/gmv/bic/运费险/订单/其他服务款")
    parsed_shop: str | None = Field(None, description="店铺名")
    detected_platform: str | None = Field(None, description="检测到的平台编码")


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
