"""Pydantic schemas for FileSpec API."""

from datetime import datetime

from pydantic import BaseModel, Field


class FileSpecCreate(BaseModel):
    platform_id: int = Field(..., description="平台ID")
    type_code: str = Field(..., max_length=30, description="业务类型：动账/gmv/bic/运费险/订单")
    name: str = Field(..., max_length=100, description="规格名称")
    headers: list[str] = Field(..., min_length=1, description="期望表头列表")
    match_threshold: int = Field(5, ge=1, le=200, description="最少匹配表头数量")
    upload_period_header: str | None = Field(None, max_length=100, description="上传所属年月取数表头")
    status: int = Field(1, description="1=启用 0=禁用")


class FileSpecUpdate(BaseModel):
    platform_id: int | None = Field(None, description="平台ID")
    type_code: str | None = Field(None, max_length=30, description="业务类型")
    name: str | None = Field(None, max_length=100, description="规格名称")
    headers: list[str] | None = Field(None, min_length=1, description="期望表头列表")
    match_threshold: int | None = Field(None, ge=1, le=200, description="最少匹配表头数量")
    upload_period_header: str | None = Field(None, max_length=100, description="上传所属年月取数表头")
    status: int | None = Field(None, description="1=启用 0=禁用")


class FileSpecOut(BaseModel):
    id: int
    platform_id: int
    type_code: str
    name: str
    headers: list[str]
    match_threshold: int
    upload_period_header: str | None = None
    status: int
    created_at: datetime
    updated_at: datetime

    # Joined fields
    platform_code: str | None = None
    platform_name: str | None = None

    class Config:
        from_attributes = True
