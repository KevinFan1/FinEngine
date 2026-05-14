from datetime import datetime

from pydantic import BaseModel, Field


class ShopCreate(BaseModel):
    platform_name: str = Field(..., min_length=1, max_length=50, description="平台")
    shop_name: str = Field(..., min_length=2, max_length=200, description="店铺名称")
    shop_color: str | None = Field(None, max_length=20, description="店铺颜色")
    entity_name: str | None = Field(None, max_length=200, description="主体名称")
    remark: str | None = Field(None, max_length=2000, description="备注")


class ShopUpdate(BaseModel):
    platform_name: str | None = Field(None, min_length=1, max_length=50, description="平台")
    shop_name: str | None = Field(None, min_length=2, max_length=200, description="店铺名称")
    shop_color: str | None = Field(None, max_length=20, description="店铺颜色")
    entity_name: str | None = Field(None, max_length=200, description="主体名称")
    remark: str | None = Field(None, max_length=2000, description="备注")
    status: int | None = Field(None, ge=0, le=1, description="状态")


class ShopOut(BaseModel):
    id: int
    platform_name: str
    shop_name: str
    shop_color: str | None
    entity_name: str | None
    remark: str | None
    status: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
