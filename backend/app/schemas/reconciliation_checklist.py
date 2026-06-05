from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class ReconciliationChecklistTaskOut(BaseModel):
    id: int
    file_id: int
    org_id: int
    org_name: str | None = None
    user_id: int
    source_upload_file_id: int | None = None
    original_name: str
    celery_task_id: str | None = None
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


class ReconciliationChecklistSummaryOut(BaseModel):
    key: str
    org_id: int
    org_name: str | None = None
    accounting_year: int
    accounting_month: int
    accounting_period: int
    merchant_id: int | None = None
    live_promoter_id: int | None = None
    receipt_merchant_id: int | None = None
    merchant_name: str
    live_promoter: str
    receipt_merchant: str
    product_quantity: int
    total_order_amount: Decimal
    total_live_commission: Decimal
    total_merchant_net_amount: Decimal


class ReconciliationChecklistSummaryDetailOut(BaseModel):
    product_name: str
    product_quantity: int
    total_order_amount: Decimal
    total_live_commission: Decimal
    total_merchant_net_amount: Decimal


class ReconciliationChecklistEntityOptionOut(BaseModel):
    id: int
    org_id: int
    parent_id: int | None = None
    platform_code: str
    entity_type: str
    name: str
