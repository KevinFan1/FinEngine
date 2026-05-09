from datetime import datetime

from pydantic import BaseModel, Field


class PlatformUpdate(BaseModel):
    name: str | None = Field(None, max_length=50, description="平台名称")
    sort_order: int | None = Field(None, description="排序")
    status: int | None = Field(None, description="状态: 1=启用 0=禁用")


class PlatformOut(BaseModel):
    id: int
    code: str
    name: str
    sort_order: int
    status: int
    created_at: datetime

    class Config:
        from_attributes = True
