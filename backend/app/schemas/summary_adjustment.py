from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, field_validator


SummaryAdjustmentMetric = Literal["gmv", "return_cost"]
SummaryAdjustmentDirection = Literal["increase", "decrease"]

SUMMARY_ADJUSTMENT_METRIC_LABELS = {
    "gmv": "实收GMV",
    "return_cost": "退货费用及其他费用",
}


class SummaryAdjustmentCreate(BaseModel):
    source_year: int = Field(..., ge=2000, le=2100, description="数据表上传年份")
    source_month: int = Field(..., ge=1, le=12, description="数据表上传月份")
    platform_name: str = Field(..., min_length=1, max_length=50, description="平台编码")
    shop_id: int = Field(..., description="店铺ID")
    shop_name: str = Field(..., min_length=1, max_length=200, description="店铺名称")
    metric_key: SummaryAdjustmentMetric = Field(..., description="调整指标")
    direction: SummaryAdjustmentDirection = Field(..., description="调整方向")
    amount: Decimal = Field(..., gt=0, decimal_places=2, description="调整金额绝对值")
    remark: str | None = Field(None, max_length=2000, description="备注")

    @field_validator("platform_name", "shop_name")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("不能为空")
        return stripped

    @field_validator("remark")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        return value.strip() if value else None


class SummaryAdjustmentUpdate(BaseModel):
    metric_key: SummaryAdjustmentMetric | None = Field(None, description="调整指标")
    direction: SummaryAdjustmentDirection | None = Field(None, description="调整方向")
    amount: Decimal | None = Field(None, gt=0, decimal_places=2, description="调整金额绝对值")
    remark: str | None = Field(None, max_length=2000, description="备注")

    @field_validator("remark")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        return value.strip() if value else None


class SummaryAdjustmentOut(BaseModel):
    id: int
    org_id: int
    source_year: int
    source_month: int
    platform_name: str
    shop_id: int
    shop_name: str
    metric_key: str
    metric_label: str
    direction: str
    amount: float
    adjustment_amount: float
    remark: str | None = None
    created_by: int
    updated_by: int | None = None
    created_at: datetime
    updated_at: datetime


def signed_adjustment_amount(direction: str, amount: Decimal) -> Decimal:
    return amount if direction == "increase" else -amount
