from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ExportJobCreate(BaseModel):
    export_type: str = Field(..., min_length=1, max_length=80, description="导出类型")
    title: str = Field(..., min_length=1, max_length=200, description="任务标题")
    filename: str = Field(..., min_length=1, max_length=500, description="导出文件名")
    params: dict[str, Any] = Field(default_factory=dict, description="导出参数")


class ExportJobOut(BaseModel):
    id: int
    org_id: int | None
    user_id: int
    operator_name: str | None = None
    module: str
    export_type: str
    title: str
    filename: str
    status: str
    progress: int
    row_count: int | None
    file_size: int | None
    error_message: str | None
    result_summary: dict[str, Any] | None
    started_at: datetime | None
    finished_at: datetime | None
    expires_at: datetime | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ExportJobDownloadCredentialOut(BaseModel):
    access_key_id: str
    access_key_secret: str
    security_token: str
    expiration: str
    region: str
    bucket: str
    endpoint: str
    oss_key: str
    filename: str
    file_size: int | None = None
