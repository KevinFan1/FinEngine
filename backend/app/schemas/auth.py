from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(..., description="用户名或手机号")
    password: str = Field(..., min_length=6, description="密码")
    captcha_id: str = Field(..., description="验证码 ID")
    captcha_code: str = Field(..., min_length=4, max_length=8, description="验证码")


class CaptchaResponse(BaseModel):
    captcha_id: str
    image: str
    expires_in: int


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
