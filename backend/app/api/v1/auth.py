from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.deps import get_current_user
from app.core.rate_limit import limiter
from app.core.security import create_access_token
from app.models.user import User
from app.schemas.auth import (
    CaptchaResponse,
    ChangeMyPasswordRequest,
    LoginRequest,
    TokenResponse,
    UpdateMeRequest,
    UserInfo,
)
from app.schemas.common import ApiResponse
from app.schemas.user_preference import UserPreferenceOut, UserPreferenceUpdate
from app.services.audit_service import AuditService
from app.services.auth_service import AuthService
from app.services.user_preference_service import UserPreferenceService
from app.services.user_service import UserService
from app.services.captcha_service import captcha_service

router = APIRouter()


@router.get("/captcha", response_model=ApiResponse[CaptchaResponse])
@limiter.limit("10/minute")  # Limit captcha generation to prevent abuse
async def get_captcha(request: Request):
    """获取登录验证码。"""
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
    """使用用户名或手机号登录。"""
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
    """退出当前登录会话并记录审计日志。"""
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
    """获取当前登录用户信息。"""
    from sqlalchemy import select

    from app.models.organization import Organization

    org_name = None
    org_type = None
    if current_user.org_id:
        result = await db.execute(
            select(Organization.name, Organization.org_type).where(
                Organization.id == current_user.org_id,
                Organization.is_deleted.is_(False),
            )
        )
        org_row = result.one_or_none()
        if org_row is not None:
            org_name, org_type = org_row

    return ApiResponse(
        data=UserInfo(
            id=current_user.id,
            org_id=current_user.org_id,
            org_type=org_type,
            username=current_user.username,
            phone=current_user.phone,
            display_name=current_user.display_name,
            email=current_user.email,
            must_change_password=current_user.must_change_password,
            role=current_user.role,
            status=current_user.status,
            org_name=org_name,
            last_login_at=str(current_user.last_login_at) if current_user.last_login_at else None,
        )
    )


@router.put("/me", response_model=ApiResponse[UserInfo])
async def update_me(
    body: UpdateMeRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """更新当前登录用户资料。"""
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")

    try:
        user = await UserService.update_current_user(
            db,
            current_user=current_user,
            display_name=body.display_name,
            phone=body.phone,
            ip=ip,
            user_agent=ua,
        )
    except ValueError as e:
        return ApiResponse(code=400, message=str(e))

    return await get_me(current_user=user, db=db)


@router.put("/me/password", response_model=ApiResponse)
async def change_my_password(
    body: ChangeMyPasswordRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """修改当前登录用户密码。"""
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")

    try:
        await UserService.change_current_user_password(
            db,
            current_user=current_user,
            old_password=body.old_password,
            new_password=body.new_password,
            ip=ip,
            user_agent=ua,
        )
    except ValueError as e:
        return ApiResponse(code=400, message=str(e))

    return ApiResponse(message="密码修改成功，请重新登录")


@router.get("/me/preferences/{preference_key}", response_model=ApiResponse[UserPreferenceOut | None])
async def get_my_preference(
    preference_key: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """获取当前登录用户的指定偏好设置。"""
    preference = await UserPreferenceService.get_preference(
        db,
        user_id=current_user.id,
        preference_key=preference_key,
    )
    if preference is None:
        return ApiResponse(data=None)
    return ApiResponse(
        data=UserPreferenceOut(
            preference_key=preference.preference_key,
            preference_value=preference.preference_value,
        )
    )


@router.put("/me/preferences/{preference_key}", response_model=ApiResponse[UserPreferenceOut])
async def update_my_preference(
    preference_key: str,
    body: UserPreferenceUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """更新当前登录用户的指定偏好设置。"""
    preference = await UserPreferenceService.set_preference(
        db,
        user_id=current_user.id,
        preference_key=preference_key,
        preference_value=body.preference_value,
    )
    return ApiResponse(
        data=UserPreferenceOut(
            preference_key=preference.preference_key,
            preference_value=preference.preference_value,
        )
    )
