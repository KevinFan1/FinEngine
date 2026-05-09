from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(..., description="用户名或手机号")
    password: str = Field(..., min_length=6, description="密码")


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserInfo(BaseModel):
    id: int
    org_id: int | None
    username: str
    phone: str
    display_name: str
    email: str | None
    role: str
    status: int
    org_name: str | None = None
    last_login_at: str | None = None

    class Config:
        from_attributes = True
