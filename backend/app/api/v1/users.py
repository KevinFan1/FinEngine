from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.deps import get_current_user, require_org_admin_or_above
from app.models.user import User
from app.schemas.common import ApiResponse, PageResponse
from app.schemas.user import UserCreate, UserOut, UserResetPassword, UserUpdate
from app.services.user_service import UserService

router = APIRouter()


@router.get("", response_model=ApiResponse[PageResponse[UserOut]])
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str | None = Query(None),
    org_id: str | None = Query(None),
    current_user: User = Depends(get_current_user),
    _admin: User = Depends(require_org_admin_or_above),
    db: AsyncSession = Depends(get_async_session),
):
    """List users. Superadmin sees all; org_admin sees own org."""
    users, total = await UserService.list_users(
        db,
        page=page,
        page_size=page_size,
        keyword=keyword,
        org_id=org_id,
        operator=current_user,
    )
    return ApiResponse(
        data=PageResponse(
            items=[UserOut.model_validate(u) for u in users],
            total=total,
            page=page,
            page_size=page_size,
        )
    )


@router.post("", response_model=ApiResponse[UserOut])
async def create_user(
    body: UserCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    _admin: User = Depends(require_org_admin_or_above),
    db: AsyncSession = Depends(get_async_session),
):
    """Create a new user. Phone must be unique."""
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")

    try:
        user = await UserService.create_user(
            db,
            data=body,
            operator=current_user,
            ip=ip,
            user_agent=ua,
        )
    except ValueError as e:
        return ApiResponse(code=400, message=str(e))

    return ApiResponse(data=UserOut.model_validate(user))


@router.get("/{user_id}", response_model=ApiResponse[UserOut])
async def get_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    _admin: User = Depends(require_org_admin_or_above),
    db: AsyncSession = Depends(get_async_session),
):
    """Get user detail."""
    try:
        user = await UserService.get_user_for_operator(db, user_id, current_user)
    except ValueError as e:
        return ApiResponse(code=404, message=str(e))
    if user is None:
        return ApiResponse(code=404, message="用户不存在")
    return ApiResponse(data=UserOut.model_validate(user))


@router.put("/{user_id}", response_model=ApiResponse[UserOut])
async def update_user(
    user_id: int,
    body: UserUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    _admin: User = Depends(require_org_admin_or_above),
    db: AsyncSession = Depends(get_async_session),
):
    """Update user info."""
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")

    try:
        user = await UserService.update_user(
            db,
            user_id=user_id,
            data=body,
            operator=current_user,
            ip=ip,
            user_agent=ua,
        )
    except ValueError as e:
        return ApiResponse(code=400, message=str(e))

    if user is None:
        return ApiResponse(code=404, message="用户不存在")
    return ApiResponse(data=UserOut.model_validate(user))


@router.put("/{user_id}/status", response_model=ApiResponse[UserOut])
async def update_user_status(
    user_id: int,
    status_val: int = Query(..., alias="status"),
    request: Request = None,
    current_user: User = Depends(get_current_user),
    _admin: User = Depends(require_org_admin_or_above),
    db: AsyncSession = Depends(get_async_session),
):
    """Enable/disable user."""
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent") if request else None

    try:
        user = await UserService.update_user_status(
            db,
            user_id=user_id,
            status_val=status_val,
            operator=current_user,
            ip=ip,
            user_agent=ua,
        )
    except ValueError as e:
        return ApiResponse(code=400, message=str(e))
    if user is None:
        return ApiResponse(code=404, message="用户不存在")
    return ApiResponse(data=UserOut.model_validate(user))


@router.post("/{user_id}/reset-password", response_model=ApiResponse)
async def reset_user_password(
    user_id: int,
    body: UserResetPassword,
    request: Request,
    current_user: User = Depends(get_current_user),
    _admin: User = Depends(require_org_admin_or_above),
    db: AsyncSession = Depends(get_async_session),
):
    """Reset user password."""
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")

    try:
        user = await UserService.reset_password(
            db,
            user_id=user_id,
            new_password=body.new_password,
            operator=current_user,
            ip=ip,
            user_agent=ua,
        )
    except ValueError as e:
        return ApiResponse(code=400, message=str(e))
    if user is None:
        return ApiResponse(code=404, message="用户不存在")
    return ApiResponse(message="密码已重置")
