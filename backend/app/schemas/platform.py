from datetime import datetime

from pydantic import BaseModel, Field


class PlatformUpdate(BaseModel):
    name: str | None = Field(None, max_length=50, description="平台名称")
    parent_code: str | None = Field(None, max_length=30, description="父平台编码")
    processor_code: str | None = Field(None, max_length=30, description="处理器平台编码")
    order_scope_code: str | None = Field(None, max_length=30, description="订单索引归属编码")
    sort_order: int | None = Field(None, description="排序")
    status: int | None = Field(None, description="状态: 1=启用 0=禁用")


class PlatformOut(BaseModel):
    id: int
    code: str
    name: str
    parent_code: str | None = None
    processor_code: str | None = None
    order_scope_code: str | None = None
    sort_order: int
    status: int
    created_at: datetime

    class Config:
        from_attributes = True
