"""文件规格维护接口。"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.deps import get_current_user, require_superadmin
from app.models.file_spec import FileSpec
from app.models.platform import Platform
from app.models.user import User
from app.schemas.common import ApiResponse, PageResponse
from app.schemas.file_spec import FileSpecCreate, FileSpecOut, FileSpecUpdate
from app.services.audit_service import AuditService

router = APIRouter()


def _file_spec_out(spec: FileSpec, platform_code: str | None = None, platform_name: str | None = None) -> FileSpecOut:
    out = FileSpecOut.model_validate(spec)
    out.platform_code = platform_code
    out.platform_name = platform_name
    return out


@router.get("", response_model=ApiResponse[list[FileSpecOut]])
async def list_file_specs(
    platform_code: str | None = Query(None, description="按平台编码过滤"),
    type_code: str | None = Query(None, description="按类型过滤: 动账/gmv/bic/运费险/订单"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """查询前端可用的启用文件规格。"""
    # Join FileSpec with Platform to get platform code/name
    stmt = (
        select(FileSpec, Platform.code, Platform.name)
        .join(Platform, FileSpec.platform_id == Platform.id)
        .where(FileSpec.status == 1, FileSpec.is_deleted.is_(False), Platform.is_deleted.is_(False))
        .order_by(Platform.sort_order, FileSpec.type_code)
    )

    if platform_code:
        stmt = stmt.where(Platform.code == platform_code)
    if type_code:
        stmt = stmt.where(FileSpec.type_code == type_code)

    result = await db.execute(stmt)
    rows = result.all()

    items = []
    for spec, plat_code, plat_name in rows:
        items.append(_file_spec_out(spec, plat_code, plat_name))

    return ApiResponse(data=items)


@router.get("/admin", response_model=ApiResponse[PageResponse[FileSpecOut]])
async def list_file_specs_admin(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    platform_id: int | None = Query(None, description="按平台ID过滤"),
    type_code: str | None = Query(None, description="按类型过滤"),
    status: int | None = Query(None, description="按状态过滤"),
    keyword: str | None = Query(None, description="按规格名、类型、表头搜索"),
    _admin: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_async_session),
):
    """分页查询文件规格管理列表。"""
    filters = [FileSpec.is_deleted.is_(False), Platform.is_deleted.is_(False)]
    if platform_id is not None:
        filters.append(FileSpec.platform_id == platform_id)
    if type_code:
        filters.append(FileSpec.type_code == type_code)
    if status is not None:
        filters.append(FileSpec.status == status)
    if keyword:
        pattern = f"%{keyword.strip()}%"
        filters.append(
            FileSpec.name.ilike(pattern)
            | FileSpec.type_code.ilike(pattern)
            | FileSpec.upload_period_header.ilike(pattern)
        )

    count_stmt = select(func.count()).select_from(FileSpec).join(Platform, FileSpec.platform_id == Platform.id).where(*filters)
    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0

    stmt = (
        select(FileSpec, Platform.code, Platform.name)
        .join(Platform, FileSpec.platform_id == Platform.id)
        .where(*filters)
        .order_by(Platform.sort_order, FileSpec.type_code, FileSpec.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(stmt)
    items = [_file_spec_out(spec, plat_code, plat_name) for spec, plat_code, plat_name in result.all()]
    return ApiResponse(data=PageResponse(items=items, total=total, page=page, page_size=page_size))


@router.post("", response_model=ApiResponse[FileSpecOut])
async def create_file_spec(
    body: FileSpecCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    _admin: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_async_session),
):
    """创建文件规格。"""
    platform = await _get_active_platform(db, body.platform_id)
    if platform is None:
        return ApiResponse(code=404, message="平台不存在")
    if await _file_spec_exists(db, platform_id=body.platform_id, type_code=body.type_code):
        return ApiResponse(code=400, message="同平台同业务类型的文件规格已存在")

    spec = FileSpec(
        platform_id=body.platform_id,
        type_code=body.type_code,
        name=body.name,
        headers=body.headers,
        match_threshold=body.match_threshold,
        upload_period_header=body.upload_period_header,
        status=body.status,
    )
    db.add(spec)
    await db.flush()
    await db.refresh(spec)
    await _log_file_spec_change(db, request, current_user, spec, f"超管创建文件规格 [{spec.name}]")
    return ApiResponse(data=_file_spec_out(spec, platform.code, platform.name))


@router.put("/{spec_id}", response_model=ApiResponse[FileSpecOut])
async def update_file_spec(
    spec_id: int,
    body: FileSpecUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    _admin: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_async_session),
):
    """更新文件规格。"""
    result = await db.execute(select(FileSpec).where(FileSpec.id == spec_id, FileSpec.is_deleted.is_(False)))
    spec = result.scalar_one_or_none()
    if spec is None:
        return ApiResponse(code=404, message="文件规格不存在")

    update_data = body.model_dump(exclude_unset=True)
    platform_id = update_data.get("platform_id", spec.platform_id)
    type_code = update_data.get("type_code", spec.type_code)
    platform = await _get_active_platform(db, platform_id)
    if platform is None:
        return ApiResponse(code=404, message="平台不存在")
    if (platform_id, type_code) != (spec.platform_id, spec.type_code) and await _file_spec_exists(
        db,
        platform_id=platform_id,
        type_code=type_code,
        exclude_id=spec.id,
    ):
        return ApiResponse(code=400, message="同平台同业务类型的文件规格已存在")

    for field, value in update_data.items():
        setattr(spec, field, value)
    await db.flush()
    await db.refresh(spec)
    await _log_file_spec_change(db, request, current_user, spec, f"超管修改文件规格 [{spec.name}]")
    return ApiResponse(data=_file_spec_out(spec, platform.code, platform.name))


@router.delete("/{spec_id}", response_model=ApiResponse[None])
async def delete_file_spec(
    spec_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    _admin: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_async_session),
):
    """删除文件规格。"""
    result = await db.execute(select(FileSpec).where(FileSpec.id == spec_id, FileSpec.is_deleted.is_(False)))
    spec = result.scalar_one_or_none()
    if spec is None:
        return ApiResponse(code=404, message="文件规格不存在")

    spec.is_deleted = True
    spec.deleted_at = datetime.now(timezone.utc)
    spec.status = 0
    await db.flush()
    await _log_file_spec_change(db, request, current_user, spec, f"超管删除文件规格 [{spec.name}]")
    return ApiResponse(message="已删除")


async def _get_active_platform(db: AsyncSession, platform_id: int) -> Platform | None:
    result = await db.execute(select(Platform).where(Platform.id == platform_id, Platform.is_deleted.is_(False)))
    return result.scalar_one_or_none()


async def _file_spec_exists(
    db: AsyncSession,
    *,
    platform_id: int,
    type_code: str,
    exclude_id: int | None = None,
) -> bool:
    stmt = select(FileSpec.id).where(
        FileSpec.platform_id == platform_id,
        FileSpec.type_code == type_code,
        FileSpec.is_deleted.is_(False),
    )
    if exclude_id is not None:
        stmt = stmt.where(FileSpec.id != exclude_id)
    result = await db.execute(stmt.limit(1))
    return result.scalar_one_or_none() is not None


async def _log_file_spec_change(
    db: AsyncSession,
    request: Request,
    user: User,
    spec: FileSpec,
    description: str,
) -> None:
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")
    await AuditService.log(
        db,
        user_id=user.id,
        username=user.username,
        display_name=user.display_name,
        org_id=user.org_id,
        module="system",
        action="config_change",
        description=description,
        target_type="file_spec",
        target_id=spec.id,
        target_name=spec.name,
        ip=ip,
        user_agent=ua,
    )
