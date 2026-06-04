from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Request, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.common import ApiResponse, PageResponse
from app.schemas.shop import ShopCreate, ShopImportResult, ShopOut, ShopUpdate
from app.services.shop_service import ShopService

router = APIRouter()


@router.get("", response_model=ApiResponse[PageResponse[ShopOut]])
async def list_shops(
    page: int = 1,
    page_size: int = 20,
    keyword: str | None = None,
    platform_name: str | None = None,
    org_id: str | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """分页查询店铺列表。"""
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
            items=[
                ShopOut.model_validate(shop).model_copy(update={"org_name": org_name})
                for shop, org_name in items
            ],
            total=total,
            page=page,
            page_size=page_size,
        )
    )


@router.get("/import-template")
async def download_shop_import_template(
    current_user: User = Depends(get_current_user),
):
    """下载店铺资料导入模板。"""
    buffer = ShopService.build_import_template()
    filename = "店铺资料导入模板.xlsx"
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
    )


@router.post("/import", response_model=ApiResponse[ShopImportResult])
async def import_shops(
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """批量导入店铺资料。"""
    content = await file.read()
    if not content:
        return ApiResponse(code=400, message="导入文件不能为空")
    try:
        result = await ShopService.import_shops(
            db,
            content=content,
            filename=file.filename or "",
            operator=current_user,
            ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
    except ValueError as e:
        return ApiResponse(code=400, message=str(e))
    return ApiResponse(data=result, message="导入完成")


@router.post("", response_model=ApiResponse[ShopOut])
async def create_shop(
    data: ShopCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """创建店铺。"""
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


@router.get("/{shop_id}", response_model=ApiResponse[ShopOut])
async def get_shop(
    shop_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """获取店铺详情。"""
    try:
        shop = await ShopService.get_shop(db, shop_id)
        if shop:
            ShopService.validate_shop_scope(shop=shop, operator=current_user)
    except ValueError as e:
        return ApiResponse(code=404, message=str(e))
    if not shop:
        return ApiResponse(code=404, message="店铺不存在")
    return ApiResponse(data=ShopOut.model_validate(shop))


@router.put("/{shop_id}", response_model=ApiResponse[ShopOut])
async def update_shop(
    shop_id: int,
    data: ShopUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """更新店铺信息。"""
    try:
        shop = await ShopService.update_shop(
            db,
            shop_id=shop_id,
            data=data,
            operator=current_user,
            ip=request.client.host,
            user_agent=request.headers.get("user-agent"),
        )
    except ValueError as e:
        return ApiResponse(code=400, message=str(e))
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
    """删除指定店铺。"""
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
