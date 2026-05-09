from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.common import ApiResponse, PageResponse
from app.schemas.shop import ShopCreate, ShopOut, ShopUpdate
from app.services.shop_service import ShopService

router = APIRouter()


@router.get("", response_model=ApiResponse[PageResponse[ShopOut]])
async def list_shops(
    page: int = 1,
    page_size: int = 20,
    keyword: str | None = None,
    platform_name: str | None = None,
    org_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    scoped_org_id = current_user.org_id if current_user.role != "superadmin" else org_id
    items, total = await ShopService.list_shops(
        db,
        org_id=scoped_org_id,
        keyword=keyword,
        platform_name=platform_name,
        page=page,
        page_size=page_size,
    )
    return ApiResponse(
        data=PageResponse(
            items=[ShopOut.model_validate(i) for i in items],
            total=total,
            page=page,
            page_size=page_size,
        )
    )


@router.post("", response_model=ApiResponse[ShopOut])
async def create_shop(
    data: ShopCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    try:
        shop = await ShopService.create_shop(
            db,
            data=data,
            org_id=current_user.org_id,
            operator=current_user,
            ip=request.client.host,
            user_agent=request.headers.get("user-agent"),
        )
        return ApiResponse(data=ShopOut.model_validate(shop))
    except ValueError as e:
        return ApiResponse(code=400, message=str(e))


@router.put("/{shop_id}", response_model=ApiResponse[ShopOut])
async def update_shop(
    shop_id: int,
    data: ShopUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    shop = await ShopService.update_shop(
        db,
        shop_id=shop_id,
        data=data,
        operator=current_user,
        ip=request.client.host,
        user_agent=request.headers.get("user-agent"),
    )
    if not shop:
        return ApiResponse(code=404, message="店铺不存在")
    return ApiResponse(data=ShopOut.model_validate(shop))


@router.delete("/{shop_id}", response_model=ApiResponse)
async def delete_shop(
    shop_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    ok = await ShopService.delete_shop(
        db,
        shop_id=shop_id,
        operator=current_user,
        ip=request.client.host,
        user_agent=request.headers.get("user-agent"),
    )
    if not ok:
        return ApiResponse(code=404, message="店铺不存在")
    return ApiResponse(message="删除成功")
