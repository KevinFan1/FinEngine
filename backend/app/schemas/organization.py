from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

OrganizationType = Literal["internal", "external"]


class OrganizationCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100, description="组织名称")
    code: str = Field(..., min_length=1, max_length=50, description="组织编码")
    org_type: OrganizationType = Field("external", description="组织类型：external=外部组织 internal=内部组织")
    remark: str | None = Field(None, max_length=2000, description="备注")


class OrganizationUpdate(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=100, description="组织名称")
    code: str | None = Field(None, min_length=1, max_length=50, description="组织编码")
    org_type: OrganizationType | None = Field(None, description="组织类型：internal=内部组织 external=外部组织")
    status: int | None = Field(None, ge=0, le=1, description="状态: 1=启用 0=禁用")
    remark: str | None = Field(None, max_length=2000, description="备注")


class OrganizationOut(BaseModel):
    id: int
    name: str
    code: str
    org_type: OrganizationType
    status: int
    remark: str | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
