"""FileSpec API — list file header specifications for frontend auto-detection."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.deps import get_current_user
from app.models.file_spec import FileSpec
from app.models.platform import Platform
from app.models.user import User
from app.schemas.common import ApiResponse
from app.schemas.file_spec import FileSpecOut

router = APIRouter()


@router.get("", response_model=ApiResponse[list[FileSpecOut]])
async def list_file_specs(
    platform_code: str | None = Query(None, description="按平台编码过滤"),
    type_code: str | None = Query(None, description="按类型过滤: 动账/gmv/bic/运费险/订单"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """List all enabled file specs (with platform info) for frontend header matching."""
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
        out = FileSpecOut.model_validate(spec)
        out.platform_code = plat_code
        out.platform_name = plat_name
        items.append(out)

    return ApiResponse(data=items)
