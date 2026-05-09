from datetime import datetime

from pydantic import BaseModel, Field


class SummaryQuery(BaseModel):
    summary_year: int | None = Field(None, description="年份")
    summary_month: int | None = Field(None, description="月份")
    source_year: int | None = Field(None, description="数据表上传年份")
    source_month: int | None = Field(None, description="数据表上传月份")
    platform_name: str | None = Field(None, description="平台名称")
    shop_id: int | None = Field(None, description="店铺ID")
    shop_name: str | None = Field(None, description="店铺名（模糊搜索）")


class SummaryOut(BaseModel):
    id: int
    org_id: int
    shop_id: int
    summary_year: int
    summary_month: int
    summary_date: str
    source_year: int
    source_month: int
    source_date: str
    platform_name: str
    shop_name: str

    # Frontend-friendly aliases
    year: int
    month: int
    platform: str

    # 动账指标
    gmv: float = 0
    real_gmv: float = 0
    platform_income: float = 0
    platform_other_income: float = 0
    platform_fee: float = 0
    platform_service_fee: float = 0
    return_cost: float = 0
    return_and_other_fee: float = 0
    commission: float = 0
    daren_commission: float = 0
    merchant_fee: float = 0
    zhaoshang_service_fee: float = 0
    promotion_fee: float = 0
    outside_promotion_fee: float = 0
    provider_commission: float = 0
    service_provider_commission: float = 0
    donation_fee: float = 0
    payment_donation_fee: float = 0

    # 运费险
    insurance_fee: float = 0
    shipping_insurance: float = 0

    # BIC
    bic: float = 0

    extra_data: dict | None = None
    source_file_ids: list[int] = []
    last_file_id: int | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SummaryReportOut(BaseModel):
    id: str
    org_id: int
    shop_id: int
    source_year: int
    source_month: int
    source_date: str
    platform_name: str
    shop_name: str

    # Frontend-friendly aliases
    year: int
    month: int
    platform: str

    summary_count: int = 0
    original_gmv: float = 0
    gmv_adjustment: float = 0
    gmv: float = 0
    real_gmv: float = 0
    platform_income: float = 0
    platform_other_income: float = 0
    platform_fee: float = 0
    platform_service_fee: float = 0
    original_return_cost: float = 0
    return_cost_adjustment: float = 0
    return_cost: float = 0
    return_and_other_fee: float = 0
    commission: float = 0
    daren_commission: float = 0
    merchant_fee: float = 0
    zhaoshang_service_fee: float = 0
    promotion_fee: float = 0
    outside_promotion_fee: float = 0
    provider_commission: float = 0
    service_provider_commission: float = 0
    donation_fee: float = 0
    payment_donation_fee: float = 0
    insurance_fee: float = 0
    shipping_insurance: float = 0
    bic: float = 0
