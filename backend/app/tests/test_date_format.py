#!/usr/bin/env python3
"""测试日期格式解析"""
from datetime import datetime
from pydantic import BaseModel, Field


class UpdateQuotaRequest(BaseModel):
    """更新配额请求。"""
    max_users: int | None = Field(None, ge=1, le=10000, description="最大用户数")
    max_storage_gb: int | None = Field(None, ge=1, le=100000, description="最大存储容量（GB）")
    plan_type: str | None = Field(None, description="套餐类型")
    plan_expires_at: datetime | None = Field(None, description="套餐到期时间")


# 测试不同的日期格式
test_cases = [
    "2025-12-31T23:59:59.000Z",  # ISO 8601 with milliseconds and Z
    "2025-12-31T23:59:59Z",      # ISO 8601 with Z
    "2025-12-31T23:59:59",       # ISO 8601 without timezone
    "2025-12-31 23:59:59",       # Space separator
    None,                         # Null value
]

for i, date_str in enumerate(test_cases, 1):
    print(f"\n测试 {i}: {date_str}")
    try:
        data = {
            "plan_type": "enterprise",
            "max_users": 100,
            "max_storage_gb": 1000,
            "plan_expires_at": date_str,
        }
        request = UpdateQuotaRequest(**data)
        print(f"  ✓ 解析成功: {request.plan_expires_at}")
    except Exception as e:
        print(f"  ✗ 解析失败: {e}")
