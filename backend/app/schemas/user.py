from datetime import datetime

from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    org_id: int | None = Field(None, description="组织ID，超管可不填")
    username: str = Field(..., min_length=2, max_length=50, description="用户名")
    phone: str = Field(..., min_length=11, max_length=20, description="手机号（唯一）")
    password: str = Field(..., min_length=6, max_length=128, description="密码")
    display_name: str = Field(..., min_length=1, max_length=100, description="显示名称")
    email: str | None = Field(None, max_length=200, description="邮箱")
    role: str = Field("member", description="角色: superadmin/org_admin/member")


class UserUpdate(BaseModel):
    org_id: int | None = Field(None, description="组织ID")
    phone: str | None = Field(None, min_length=11, max_length=20, description="手机号")
    display_name: str | None = Field(None, min_length=1, max_length=100, description="显示名称")
    email: str | None = Field(None, max_length=200, description="邮箱")
    role: str | None = Field(None, description="角色: superadmin/org_admin/member")
    status: int | None = Field(None, ge=0, le=1, description="状态: 1=启用 0=禁用")


class UserResetPassword(BaseModel):
    new_password: str = Field(..., min_length=6, max_length=128, description="新密码")


class UserOut(BaseModel):
    id: int
    org_id: int | None
    username: str
    phone: str
    display_name: str
    email: str | None
    role: str
    status: int
    last_login_at: datetime | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
