"""Pydantic schemas for FileSpec API."""

from datetime import datetime

from pydantic import BaseModel


class FileSpecOut(BaseModel):
    id: int
    platform_id: int
    type_code: str
    name: str
    headers: list[str]
    match_threshold: int
    status: int
    created_at: datetime
    updated_at: datetime

    # Joined fields
    platform_code: str | None = None
    platform_name: str | None = None

    class Config:
        from_attributes = True
