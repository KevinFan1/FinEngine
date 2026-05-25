from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

class BicUploadFileOut(BaseModel):
    id: int
    org_id: int
    user_id: int
    shop_id: int | None = None
    source_upload_file_id: int | None = None
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


class BicTaskOut(BaseModel):
    id: int
    file_id: int
    org_id: int
    org_name: str | None = None
    user_id: int
    shop_id: int | None = None
    source_upload_file_id: int | None = None
    original_name: str | None = None
    platform_code: str | None = None
    shop_name: str | None = None
    accounting_year: int | None = None
    accounting_month: int | None = None
    celery_task_id: str | None = None
    status: str
    progress: int
    processed_rows: int
    success_rows: int
    failed_rows: int
    result_success: int | None = None
    result_failed: int | None = None
    error_message: str | None = None
    error_reason: str | None = None
    result_summary: dict | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class BicDetailOut(BaseModel):
    id: int
    task_id: int
    file_id: int
    org_id: int
    org_name: str | None = None
    shop_id: int | None = None
    platform_code: str
    store_short_id: str | None = None
    service_provider: str
    shop_name: str
    qic_warehouse: str
    merchant: str | None = None
    tax_no: str | None = None
    shop_type: str | None = None
    registered_address: str | None = None
    total_amount: Decimal
    created_at: datetime

    class Config:
        from_attributes = True


class BicReportOut(BaseModel):
    id: int
    task_id: int
    file_id: int
    org_id: int
    org_name: str | None = None
    shop_id: int | None = None
    platform_code: str
    store_short_id: str | None = None
    service_provider: str
    shop_name: str
    accounting_year: int
    accounting_month: int
    row_count: int
    merchant: str | None = None
    tax_no: str | None = None
    shop_type: str | None = None
    registered_address: str | None = None
    total_amount: Decimal
    created_at: datetime

    class Config:
        from_attributes = True
