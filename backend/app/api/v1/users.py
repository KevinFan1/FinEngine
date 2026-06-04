from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.deps import get_current_user, require_org_admin_or_above
from app.models.organization import Organization
from app.models.user import User
from app.schemas.common import ApiResponse, PageResponse
from app.schemas.user import UserCreate, UserOut, UserResetPassword, UserUpdate
from app.services.user_service import UserService

router = APIRouter()


def _user_out(user: User, org_name: str | None = None) -> UserOut:
    return UserOut.model_validate(user).model_copy(update={"org_name": org_name})


async def _load_org_name_map(db: AsyncSession, org_ids: set[int]) -> dict[int, str]:
    if not org_ids:
        return {}
    result = await db.execute(
        select(Organization.id, Organization.name).where(
            Organization.id.in_(org_ids),
            Organization.is_deleted.is_(False),
        )
    )
    return {org_id: org_name for org_id, org_name in result.all()}


async def _load_org_name(db: AsyncSession, org_id: int | None) -> str | None:
    if org_id is None:
        return None
    result = await db.execute(
        select(Organization.name).where(
            Organization.id == org_id,
            Organization.is_deleted.is_(False),
        )
    )
    return result.scalar_one_or_none()


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
    """分页查询用户列表。"""
    users, total = await UserService.list_users(
        db,
        page=page,
        page_size=page_size,
        keyword=keyword,
        org_id=org_id,
        operator=current_user,
    )
    org_name_map = await _load_org_name_map(
        db,
        {user.org_id for user in users if user.org_id is not None},
    )
    return ApiResponse(
        data=PageResponse(
            items=[_user_out(user, org_name_map.get(user.org_id)) for user in users],
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
    """创建新用户。"""
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

    return ApiResponse(data=_user_out(user, await _load_org_name(db, user.org_id)))


@router.get("/{user_id}", response_model=ApiResponse[UserOut])
async def get_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    _admin: User = Depends(require_org_admin_or_above),
    db: AsyncSession = Depends(get_async_session),
):
    """获取用户详情。"""
    try:
        user = await UserService.get_user_for_operator(db, user_id, current_user)
    except ValueError as e:
        return ApiResponse(code=404, message=str(e))
    if user is None:
        return ApiResponse(code=404, message="用户不存在")
    return ApiResponse(data=_user_out(user, await _load_org_name(db, user.org_id)))


@router.put("/{user_id}", response_model=ApiResponse[UserOut])
async def update_user(
    user_id: int,
    body: UserUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    _admin: User = Depends(require_org_admin_or_above),
    db: AsyncSession = Depends(get_async_session),
):
    """更新用户信息。"""
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
    return ApiResponse(data=_user_out(user, await _load_org_name(db, user.org_id)))


@router.put("/{user_id}/status", response_model=ApiResponse[UserOut])
async def update_user_status(
    user_id: int,
    status_val: int = Query(..., alias="status"),
    request: Request = None,
    current_user: User = Depends(get_current_user),
    _admin: User = Depends(require_org_admin_or_above),
    db: AsyncSession = Depends(get_async_session),
):
    """启用或禁用指定用户。"""
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
    return ApiResponse(data=_user_out(user, await _load_org_name(db, user.org_id)))


@router.post("/{user_id}/reset-password", response_model=ApiResponse)
async def reset_user_password(
    user_id: int,
    body: UserResetPassword,
    request: Request,
    current_user: User = Depends(get_current_user),
    _admin: User = Depends(require_org_admin_or_above),
    db: AsyncSession = Depends(get_async_session),
):
    """重置指定用户密码。"""
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
