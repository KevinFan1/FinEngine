from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.deps import get_current_user, require_superadmin
from app.models.platform import Platform
from app.models.user import User
from app.schemas.common import ApiResponse
from app.schemas.platform import PlatformOut, PlatformUpdate
from app.services.audit_service import AuditService

router = APIRouter()


@router.get("", response_model=ApiResponse[list[PlatformOut]])
async def list_platforms(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """查询全部启用的平台配置。"""
    result = await db.execute(select(Platform).where(Platform.is_deleted.is_(False)).order_by(Platform.sort_order, Platform.id))
    platforms = list(result.scalars().all())
    return ApiResponse(data=[PlatformOut.model_validate(p) for p in platforms])


@router.put("/{platform_id}", response_model=ApiResponse[PlatformOut])
async def update_platform(
    platform_id: int,
    body: PlatformUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    _superadmin: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_async_session),
):
    """更新平台配置。"""
    result = await db.execute(select(Platform).where(Platform.id == platform_id, Platform.is_deleted.is_(False)))
    platform = result.scalar_one_or_none()
    if platform is None:
        return ApiResponse(code=404, message="平台不存在")

    update_data = body.model_dump(exclude_unset=True)
    for field in ("parent_code", "processor_code", "order_scope_code"):
        if update_data.get(field) == "":
            update_data[field] = None
    for field, value in update_data.items():
        setattr(platform, field, value)
    await db.flush()

    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")

    await AuditService.log(
        db,
        user_id=current_user.id,
        username=current_user.username,
        display_name=current_user.display_name,
        org_id=current_user.org_id,
        module="system",
        action="config_change",
        description=f"超管修改平台配置 [{platform.name}]",
        target_type="platform",
        target_id=platform.id,
        target_name=platform.name,
        ip=ip,
        user_agent=ua,
    )

    return ApiResponse(data=PlatformOut.model_validate(platform))
