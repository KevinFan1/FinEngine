from datetime import datetime

from pydantic import BaseModel


class TaskOut(BaseModel):
    id: int
    file_id: int
    org_id: int
    user_id: int
    batch_id: int | None = None
    filename: str | None = None
    platform: str | None = None
    source_platform_code: str | None = None
    report_platform_code: str | None = None
    shop_id: int | None = None
    shop_name: str | None = None
    shop_color: str | None = None
    parsed_type: str | None = None
    parsed_year: int | None = None
    parsed_month: int | None = None
    celery_task_id: str | None
    status: str
    progress: int
    processed_rows: int
    success_rows: int
    failed_rows: int
    error_message: str | None
    error_reason: str | None = None
    action_expired: bool = False
    action_expire_reason: str | None = None
    result_summary: dict | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TaskListOut(BaseModel):
    id: int
    file_id: int
    batch_id: int | None = None
    filename: str | None = None
    platform: str | None = None
    source_platform_code: str | None = None
    report_platform_code: str | None = None
    shop_id: int | None = None
    shop_name: str | None = None
    shop_color: str | None = None
    parsed_type: str | None = None
    parsed_year: int | None = None
    parsed_month: int | None = None
    status: str
    progress: int
    processed_rows: int
    success_rows: int
    failed_rows: int
    result_success: int | None = None
    result_failed: int | None = None
    error_message: str | None = None
    error_reason: str | None = None
    action_expired: bool = False
    action_expire_reason: str | None = None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime
