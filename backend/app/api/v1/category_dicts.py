"""分类字典管理 API — 超管 CRUD + 文本分类接口"""

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.deps import get_current_user, require_superadmin
from app.models.user import User
from app.schemas.category_dict import (
    CategoryDictCreate,
    CategoryDictOut,
    CategoryDictUpdate,
    ClassifyBatchRequest,
    ClassifyRequest,
    ClassifyResult,
)
from app.schemas.common import ApiResponse, PageResponse
from app.services.audit_service import AuditService
from app.services.category_dict_service import CategoryDictService
from app.utils.text_classifier import classify_batch, classify_text

router = APIRouter()


# ============================================================
# 超管：字典 CRUD
# ============================================================


@router.get("", response_model=ApiResponse[PageResponse[CategoryDictOut]])
async def list_category_dicts(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    platform_id: int | None = Query(None),
    type_code: str | None = Query(None),
    _admin: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_async_session),
):
    """列出分类字典（支持按平台/类型筛选）。"""
    items, total = await CategoryDictService.list_dicts(
        db,
        platform_id=platform_id,
        type_code=type_code,
        page=page,
        page_size=page_size,
    )
    return ApiResponse(
        data=PageResponse(
            items=[CategoryDictOut.model_validate(i) for i in items],
            total=total,
            page=page,
            page_size=page_size,
        )
    )


@router.post("", response_model=ApiResponse[CategoryDictOut])
async def create_category_dict(
    body: CategoryDictCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    _admin: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_async_session),
):
    """创建分类字典（超管）。"""
    cd = await CategoryDictService.create_dict(db, data=body)

    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")

    cat_count = len(body.categories)
    kw_count = sum(len(v) for v in body.categories.values())
    await AuditService.log(
        db,
        user_id=current_user.id,
        username=current_user.username,
        display_name=current_user.display_name,
        org_id=current_user.org_id,
        module="system",
        action="config_change",
        description=f"超管创建分类字典 [{cd.name}]，{cat_count} 个分类，{kw_count} 个关键词",
        target_type="category_dict",
        target_id=cd.id,
        target_name=cd.name,
        ip=ip,
        user_agent=ua,
    )

    return ApiResponse(data=CategoryDictOut.model_validate(cd))


@router.put("/{dict_id}", response_model=ApiResponse[CategoryDictOut])
async def update_category_dict(
    dict_id: int,
    body: CategoryDictUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    _admin: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_async_session),
):
    """更新分类字典（超管）。"""
    cd = await CategoryDictService.update_dict(db, dict_id=dict_id, data=body)
    if cd is None:
        return ApiResponse(code=404, message="字典不存在")

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
        description=f"超管修改分类字典 [{cd.name}]",
        target_type="category_dict",
        target_id=cd.id,
        target_name=cd.name,
        ip=ip,
        user_agent=ua,
    )

    return ApiResponse(data=CategoryDictOut.model_validate(cd))


@router.delete("/{dict_id}")
async def delete_category_dict(
    dict_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    _admin: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_async_session),
):
    """删除分类字典（超管）。"""
    ok = await CategoryDictService.delete_dict(db, dict_id=dict_id)
    if not ok:
        return ApiResponse(code=404, message="字典不存在")

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
        description=f"超管删除分类字典 id={dict_id}",
        target_type="category_dict",
        target_id=dict_id,
        ip=ip,
        user_agent=ua,
    )

    return ApiResponse(message="已删除")


# ============================================================
# 分类接口（供内部/前端调用）
# ============================================================


@router.post("/classify", response_model=ApiResponse[ClassifyResult])
async def classify_single(
    body: ClassifyRequest,
    _admin: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_async_session),
):
    """对单条文本进行分类。"""
    categories = await CategoryDictService.get_categories(
        db,
        platform_id=body.platform_id,
        type_code=body.type_code,
    )
    if categories is None:
        return ApiResponse(code=404, message="未找到对应平台和类型的分类字典")

    result = classify_text(body.text, categories)
    return ApiResponse(
        data=ClassifyResult(
            text=result.text,
            chinese_text=result.chinese_text,
            category=result.category,
            matched_keyword=result.matched_keyword,
            match_type=result.match_type,
            match_score=result.match_score,
        )
    )


@router.post("/classify-batch", response_model=ApiResponse[list[ClassifyResult]])
async def classify_batch_endpoint(
    body: ClassifyBatchRequest,
    _admin: User = Depends(require_superadmin),
    db: AsyncSession = Depends(get_async_session),
):
    """批量文本分类。"""
    categories = await CategoryDictService.get_categories(
        db,
        platform_id=body.platform_id,
        type_code=body.type_code,
    )
    if categories is None:
        return ApiResponse(code=404, message="未找到对应平台和类型的分类字典")

    results = classify_batch(body.texts, categories)
    return ApiResponse(
        data=[
            ClassifyResult(
                text=r.text,
                chinese_text=r.chinese_text,
                category=r.category,
                matched_keyword=r.matched_keyword,
                match_type=r.match_type,
                match_score=r.match_score,
            )
            for r in results
        ]
    )
