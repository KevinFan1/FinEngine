from datetime import datetime
from decimal import Decimal
from pathlib import Path

from pydantic import BaseModel, Field, field_validator

from app.schemas.upload import ALLOWED_EXTENSIONS


class TransactionSubjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    sort_order: int = Field(100, ge=0)
    status: int = Field(1, ge=0, le=1)


class TransactionSubjectUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    sort_order: int | None = Field(None, ge=0)
    status: int | None = Field(None, ge=0, le=1)


class TransactionSubjectOut(BaseModel):
    id: int
    name: str
    sort_order: int
    status: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TransactionCategoryCreate(BaseModel):
    subject_id: int
    name: str = Field(..., min_length=1, max_length=100)
    sort_order: int = Field(100, ge=0)
    status: int = Field(1, ge=0, le=1)


class TransactionCategoryUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    sort_order: int | None = Field(None, ge=0)
    status: int | None = Field(None, ge=0, le=1)


class TransactionCategoryOut(BaseModel):
    id: int
    subject_id: int
    name: str
    sort_order: int
    status: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TransactionRuleCreate(BaseModel):
    subject_id: int
    category_id: int
    platform_code: str | None = Field(None, max_length=50)
    transaction_direction: str = Field(..., min_length=1, max_length=20)
    remark_field: str = Field("备注", min_length=1, max_length=100)
    direction_field: str = Field("动账方向", min_length=1, max_length=100)
    match_type: str = Field("contains", pattern="^(exact|contains|regex)$")
    remark_pattern: str = Field(..., min_length=1, max_length=1000)
    amount_field: str = Field(..., min_length=1, max_length=100)
    result_direction: str = Field("original", pattern="^(original|positive|negative|directional)$")
    priority: int = Field(100, ge=0)
    status: int = Field(1, ge=0, le=1)


class TransactionRuleUpdate(BaseModel):
    subject_id: int | None = None
    category_id: int | None = None
    platform_code: str | None = Field(None, max_length=50)
    transaction_direction: str | None = Field(None, min_length=1, max_length=20)
    remark_field: str | None = Field(None, min_length=1, max_length=100)
    direction_field: str | None = Field(None, min_length=1, max_length=100)
    match_type: str | None = Field(None, pattern="^(exact|contains|regex)$")
    remark_pattern: str | None = Field(None, min_length=1, max_length=1000)
    amount_field: str | None = Field(None, min_length=1, max_length=100)
    result_direction: str | None = Field(None, pattern="^(original|positive|negative|directional)$")
    priority: int | None = Field(None, ge=0)
    status: int | None = Field(None, ge=0, le=1)


class TransactionRuleOut(BaseModel):
    id: int
    subject_id: int
    category_id: int
    platform_code: str | None
    transaction_direction: str
    remark_field: str
    direction_field: str
    match_type: str
    remark_pattern: str
    amount_field: str
    result_direction: str
    priority: int
    status: int
    subject_name: str | None = None
    category_name: str | None = None
    reclassification_name: str | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TransactionUploadInit(BaseModel):
    original_name: str = Field(..., min_length=1, max_length=500)
    file_size: int = Field(0, ge=0, le=1024 * 1024 * 1024)
    platform_code: str | None = Field(None, max_length=50)
    shop_name: str | None = Field(None, max_length=200)
    accounting_year: int | None = Field(None, ge=2000, le=2100)
    accounting_month: int | None = Field(None, ge=1, le=12)

    @field_validator("original_name")
    @classmethod
    def validate_filename(cls, value: str) -> str:
        ext = Path(value).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise ValueError(f"不支持的文件类型: {ext}，仅支持 {', '.join(sorted(ALLOWED_EXTENSIONS))}")
        return value


class TransactionUploadInitOut(BaseModel):
    file_id: int
    access_key_id: str
    access_key_secret: str
    security_token: str
    expiration: str
    region: str
    bucket: str
    endpoint: str
    oss_key_prefix: str


class TransactionUploadCallback(BaseModel):
    file_id: int
    oss_key: str = Field(..., min_length=1, max_length=1000)
    file_size: int = Field(..., ge=0, le=1024 * 1024 * 1024)
    file_hash: str | None = Field(None, max_length=64)


class TransactionUploadFileOut(BaseModel):
    id: int
    org_id: int
    user_id: int
    shop_id: int | None = None
    original_name: str
    oss_key: str
    file_size: int
    file_hash: str | None
    platform_code: str | None
    shop_name: str | None
    accounting_year: int | None
    accounting_month: int | None
    status: str
    error_message: str | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TransactionTaskOut(BaseModel):
    id: int
    file_id: int
    org_id: int
    user_id: int
    shop_id: int | None = None
    celery_task_id: str | None
    status: str
    progress: int
    total_rows: int
    matched_rows: int
    unmatched_rows: int
    failed_rows: int
    error_message: str | None
    result_summary: dict | None
    original_name: str | None = None
    platform_code: str | None = None
    shop_name: str | None = None
    accounting_year: int | None = None
    accounting_month: int | None = None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TransactionDetailOut(BaseModel):
    id: int
    task_id: int
    file_id: int
    org_id: int
    shop_id: int | None = None
    subject_id: int | None
    category_id: int | None
    rule_id: int | None
    row_number: int
    platform_code: str | None
    shop_name: str | None
    upload_accounting_year: int | None = None
    upload_accounting_month: int | None = None
    accounting_year: int | None
    accounting_month: int | None
    transaction_direction: str | None
    remark: str | None
    amount_field: str | None
    original_amount: Decimal
    calculated_amount: Decimal
    status: str
    error_message: str | None
    raw_row: dict
    subject_name: str | None = None
    category_name: str | None = None
    reclassification_name: str | None = None
    cash_flow_group_name: str | None = None
    total_amount: Decimal | None = None
    update_time: datetime | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class TransactionSummaryOut(BaseModel):
    id: int
    task_id: int
    file_id: int
    org_id: int
    shop_id: int | None = None
    subject_id: int
    category_id: int
    subject_name: str
    category_name: str
    reclassification_name: str | None = None
    transaction_direction: str | None
    platform_code: str | None
    shop_name: str | None
    upload_accounting_year: int | None = None
    upload_accounting_month: int | None = None
    accounting_year: int | None
    accounting_month: int | None
    cash_flow_group_name: str | None = None
    row_count: int
    total_amount: Decimal
    created_at: datetime

    class Config:
        from_attributes = True


class TransactionAnnualSummaryRowOut(BaseModel):
    code: str
    name: str
    parent_code: str | None
    level: int
    item_type: str
    flow_section: str
    flow_direction: str | None
    summary_method: str
    months: dict[str, Decimal]
    total_amount: Decimal

    class Config:
        from_attributes = True


class TransactionAnnualSummaryOut(BaseModel):
    year: int
    months: list[str]
    rows: list[TransactionAnnualSummaryRowOut]

    class Config:
        from_attributes = True
