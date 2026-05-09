from datetime import datetime

from pydantic import BaseModel, Field


class AuditLogQuery(BaseModel):
    module: str | None = Field(None, description="模块: auth/org/user/upload/task/summary/export/system")
    action: str | None = Field(None, description="操作类型")
    user_id: int | None = Field(None, description="操作人ID")
    start_time: datetime | None = Field(None, description="开始时间")
    end_time: datetime | None = Field(None, description="结束时间")


class AuditLogOut(BaseModel):
    id: int
    user_id: int
    org_id: int | None
    username: str
    display_name: str | None
    module: str
    action: str
    description: str
    target_type: str | None
    target_id: int | None
    target_name: str | None
    ip: str | None
    user_agent: str | None
    method: str | None
    path: str | None
    old_value: dict | None
    new_value: dict | None
    extra_data: dict | None
    status: str
    error_msg: str | None
    created_at: datetime

    class Config:
        from_attributes = True
