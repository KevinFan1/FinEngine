from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.deps import get_current_user
from app.core.rate_limit import limiter
from app.core.security import create_access_token
from app.models.user import User
from app.schemas.auth import CaptchaResponse, LoginRequest, TokenResponse, UserInfo
from app.schemas.common import ApiResponse
from app.services.audit_service import AuditService
from app.services.auth_service import AuthService
from app.services.captcha_service import captcha_service

router = APIRouter()


@router.get("/captcha", response_model=ApiResponse[CaptchaResponse])
@limiter.limit("10/minute")  # Limit captcha generation to prevent abuse
async def get_captcha(request: Request):
    """Create a login captcha challenge."""
    challenge = await captcha_service.generate()
    return ApiResponse(
        data=CaptchaResponse(
            captcha_id=challenge.captcha_id,
            image=challenge.image,
            expires_in=challenge.expires_in,
        )
    )


@router.post("/login", response_model=ApiResponse[TokenResponse])
@limiter.limit("5/minute")  # Strict limit on login attempts to prevent brute force
async def login(
    body: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_async_session),
):
    """Login with username or phone + password."""
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")

    if not await captcha_service.verify(body.captcha_id, body.captcha_code):
        return ApiResponse(code=status.HTTP_400_BAD_REQUEST, message="验证码错误或已过期")

    user = await AuthService.login(
        db,
        username=body.username,
        password=body.password,
        ip=ip,
        user_agent=ua,
    )
    if user is None:
        return ApiResponse(code=status.HTTP_401_UNAUTHORIZED, message="用户名/手机号或密码错误")

    token = create_access_token(subject=user.id, session_id=user.active_session_id)
    return ApiResponse(data=TokenResponse(access_token=token))


@router.post("/logout", response_model=ApiResponse)
async def logout(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Logout — record audit log."""
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")

    await AuditService.log(
        db,
        user_id=current_user.id,
        username=current_user.username,
        display_name=current_user.display_name,
        org_id=current_user.org_id,
        module="auth",
        action="logout",
        description=f"用户 [{current_user.display_name}] 退出登录",
        ip=ip,
        user_agent=ua,
    )
    current_user.active_session_id = None
    current_user.active_session_ip = None
    current_user.active_session_user_agent = None
    current_user.active_session_at = None
    await db.flush()
    return ApiResponse(message="已退出登录")


@router.get("/me", response_model=ApiResponse[UserInfo])
async def get_me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Get current user info."""
    from sqlalchemy import select

    from app.models.organization import Organization

    org_name = None
    if current_user.org_id:
        result = await db.execute(select(Organization.name).where(Organization.id == current_user.org_id, Organization.is_deleted.is_(False)))
        org_name = result.scalar()

    return ApiResponse(
        data=UserInfo(
            id=current_user.id,
            org_id=current_user.org_id,
            username=current_user.username,
            phone=current_user.phone,
            display_name=current_user.display_name,
            email=current_user.email,
            role=current_user.role,
            status=current_user.status,
            org_name=org_name,
            last_login_at=str(current_user.last_login_at) if current_user.last_login_at else None,
        )
    )
