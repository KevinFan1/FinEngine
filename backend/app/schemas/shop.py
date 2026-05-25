from datetime import datetime

from pydantic import BaseModel, Field


class ShopInfoFields(BaseModel):
    tax_no: str | None = Field(None, max_length=100, description="税号")
    merchant: str | None = Field(None, max_length=200, description="商户")
    registered_address: str | None = Field(None, max_length=500, description="注册地址")
    legal_person: str | None = Field(None, max_length=100, description="法人")
    previous_name: str | None = Field(None, max_length=200, description="曾用名")
    store_long_id: str | None = Field(None, max_length=100, description="store_long_id")
    store_short_id: str | None = Field(None, max_length=100, description="store_short_id")
    settlement_period: str | None = Field(None, max_length=100, description="settlement_period")
    primary_account: str | None = Field(None, max_length=200, description="primary_account")
    anchor: str | None = Field(None, max_length=100, description="主播")
    shop_type: str | None = Field(None, max_length=100, description="类型")
    purpose: str | None = Field(None, max_length=200, description="purpose")
    former_name: str | None = Field(None, max_length=200, description="former_name")


class ShopCreate(ShopInfoFields):
    platform_name: str = Field(..., min_length=1, max_length=50, description="平台")
    shop_name: str = Field(..., min_length=2, max_length=200, description="店铺名称")
    shop_color: str | None = Field(None, max_length=20, description="店铺颜色")
    remark: str | None = Field(None, max_length=2000, description="备注")


class ShopUpdate(ShopInfoFields):
    platform_name: str | None = Field(None, min_length=1, max_length=50, description="平台")
    shop_name: str | None = Field(None, min_length=2, max_length=200, description="店铺名称")
    shop_color: str | None = Field(None, max_length=20, description="店铺颜色")
    remark: str | None = Field(None, max_length=2000, description="备注")
    status: int | None = Field(None, ge=0, le=1, description="状态")


class ShopOut(ShopInfoFields):
    id: int
    org_id: int
    org_name: str | None = None
    platform_name: str
    shop_name: str
    shop_color: str | None
    remark: str | None
    status: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ShopImportError(BaseModel):
    row: int
    message: str


class ShopImportResult(BaseModel):
    total: int
    created: int
    updated: int
    skipped: int
    errors: list[ShopImportError] = Field(default_factory=list)
