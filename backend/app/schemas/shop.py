from datetime import datetime

from pydantic import BaseModel


class ShopCreate(BaseModel):
    platform_name: str
    shop_name: str
    entity_name: str | None = None
    remark: str | None = None


class ShopUpdate(BaseModel):
    platform_name: str | None = None
    shop_name: str | None = None
    entity_name: str | None = None
    remark: str | None = None
    status: int | None = None


class ShopOut(BaseModel):
    id: int
    platform_name: str
    shop_name: str
    entity_name: str | None
    remark: str | None
    status: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
