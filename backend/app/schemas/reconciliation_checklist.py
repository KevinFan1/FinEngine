from datetime import datetime
from decimal import Decimal

from pathlib import Path

from pydantic import BaseModel, Field, field_validator

from app.schemas.upload import ALLOWED_EXTENSIONS


class ReconciliationChecklistTaskOut(BaseModel):
    id: int
    file_id: int
    org_id: int
    org_name: str | None = None
    user_id: int
    source_upload_file_id: int | None = None
    original_name: str
    celery_task_id: str | None = None
    task_type: str = "source_import"
    status: str
    progress: int
    total_rows: int
    success_rows: int
    failed_rows: int
    inserted_rows: int
    updated_rows: int
    error_message: str | None = None
    result_summary: dict | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ReconciliationChecklistProductSummaryOut(BaseModel):
    key: str
    org_id: int
    org_name: str | None = None
    accounting_year: int
    accounting_month: int
    accounting_period: int
    receipt_merchant: str
    merchant_subject_name: str
    product_name: str
    product_quantity: int
    total_user_paid_amount: Decimal
    total_live_commission: Decimal
    total_merchant_net_amount: Decimal


class ReconciliationChecklistReceiptSummaryOut(BaseModel):
    key: str
    org_id: int
    org_name: str | None = None
    accounting_year: int
    accounting_month: int
    accounting_period: int
    merchant_subject_name: str
    live_platform: str
    receipt_merchant: str
    order_count: int
    total_user_paid_amount: Decimal
    total_live_commission: Decimal
    total_merchant_net_amount: Decimal


class ReconciliationChecklistPayableBalanceSummaryOut(BaseModel):
    key: str
    org_id: int
    org_name: str | None = None
    accounting_year: int
    accounting_month: int
    accounting_period: int
    merchant_subject_name: str
    receipt_merchant: str
    total_user_paid_amount: Decimal
    total_merchant_net_amount: Decimal
    total_payment_amount: Decimal
    total_merchant_net_balance: Decimal


class ReconciliationChecklistSummaryOut(ReconciliationChecklistProductSummaryOut):
    pass


class ReconciliationChecklistSummaryDetailOut(ReconciliationChecklistProductSummaryOut):
    pass


class ReconciliationChecklistEntityOptionOut(BaseModel):
    id: int
    org_id: int
    parent_id: int | None = None
    platform_code: str
    entity_type: str
    name: str


class ReconciliationChecklistOptionOut(BaseModel):
    label: str
    value: str


class ReconciliationChecklistManualEditQueryIn(BaseModel):
    org_id: int
    sub_order_nos: list[str]


class ReconciliationChecklistInvoiceEditItemIn(BaseModel):
    unique_id: str = ""
    sub_order_no: str
    receipt_merchant: str = ""
    invoice_time: datetime | None = None
    invoice_number: str = ""


class ReconciliationChecklistMerchantEditItemIn(BaseModel):
    unique_id: str = ""
    sub_order_no: str
    receipt_merchant: str = ""
    merchant_net_amount: Decimal | None = None
    payment_amount: Decimal | None = None
    merchant_payment_time: datetime | None = None


class ReconciliationChecklistInvoiceEditSaveIn(BaseModel):
    org_id: int
    items: list[ReconciliationChecklistInvoiceEditItemIn]


class ReconciliationChecklistMerchantEditSaveIn(BaseModel):
    org_id: int
    items: list[ReconciliationChecklistMerchantEditItemIn]


class ReconciliationChecklistManualEditSaveOut(BaseModel):
    success_count: int
    failed_count: int
    unchanged_count: int = 0
    missing_sub_order_nos: list[str]
    affected_periods: list[int]
    error_messages: list[str] = []


class ReconciliationChecklistManualEditUploadInitIn(BaseModel):
    org_id: int
    original_name: str = Field(..., min_length=1, max_length=500)
    file_size: int = Field(0, ge=0, le=1024 * 1024 * 1024)

    @field_validator("original_name")
    @classmethod
    def validate_filename(cls, value: str) -> str:
        ext = Path(value).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise ValueError(f"不支持的文件类型: {ext}，仅支持 {', '.join(sorted(ALLOWED_EXTENSIONS))}")
        return value


class ReconciliationChecklistManualEditUploadFileOut(BaseModel):
    id: int
    org_id: int
    user_id: int
    original_name: str
    oss_key: str
    file_size: int
    file_hash: str | None = None
    status: str

    class Config:
        from_attributes = True


class ReconciliationChecklistManualEditUploadInitOut(BaseModel):
    file_id: int
    access_key_id: str
    access_key_secret: str
    security_token: str
    expiration: str
    region: str
    bucket: str
    endpoint: str
    oss_key_prefix: str


class ReconciliationChecklistManualEditUploadInitResponse(BaseModel):
    file: ReconciliationChecklistManualEditUploadFileOut
    upload: ReconciliationChecklistManualEditUploadInitOut


class ReconciliationChecklistManualEditUploadCallbackIn(BaseModel):
    file_id: int
    oss_key: str = Field(..., min_length=1, max_length=1000)
    file_size: int = Field(..., ge=0, le=1024 * 1024 * 1024)
    file_hash: str | None = Field(None, max_length=64)


class ReconciliationChecklistInvoiceEditItemOut(BaseModel):
    unique_id: str = ""
    sub_order_no: str
    settlement_time: datetime | None = None
    platform_subsidy: Decimal | None = None
    talent_subsidy: Decimal | None = None
    douyin_pay_subsidy: Decimal | None = None
    douyin_monthly_pay_subsidy: Decimal | None = None
    bank_subsidy: Decimal | None = None
    user_paid_amount: Decimal | None = None
    platform_service_fee: Decimal | None = None
    talent_commission: Decimal | None = None
    investment_service_fee: Decimal | None = None
    receipt_merchant: str
    invoice_time: datetime | None = None
    invoice_number: str


class ReconciliationChecklistMerchantEditItemOut(BaseModel):
    unique_id: str = ""
    sub_order_no: str
    settlement_time: datetime | None = None
    platform_subsidy: Decimal | None = None
    talent_subsidy: Decimal | None = None
    douyin_pay_subsidy: Decimal | None = None
    douyin_monthly_pay_subsidy: Decimal | None = None
    bank_subsidy: Decimal | None = None
    user_paid_amount: Decimal | None = None
    platform_service_fee: Decimal | None = None
    talent_commission: Decimal | None = None
    investment_service_fee: Decimal | None = None
    receipt_merchant: str
    merchant_net_amount: Decimal | None = None
    payment_amount: Decimal | None = None
    merchant_payment_time: datetime | None = None


class ReconciliationChecklistInvoiceEditQueryOut(BaseModel):
    matched_items: list[ReconciliationChecklistInvoiceEditItemOut]
    missing_sub_order_nos: list[str]


class ReconciliationChecklistMerchantEditQueryOut(BaseModel):
    matched_items: list[ReconciliationChecklistMerchantEditItemOut]
    missing_sub_order_nos: list[str]
