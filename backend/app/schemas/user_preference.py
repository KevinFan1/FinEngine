from typing import Any

from pydantic import BaseModel, Field


class UserPreferenceOut(BaseModel):
    preference_key: str = Field(..., min_length=1, max_length=100, description="配置键")
    preference_value: Any = Field(..., description="配置值")


class UserPreferenceUpdate(BaseModel):
    preference_value: Any = Field(..., description="配置值")
