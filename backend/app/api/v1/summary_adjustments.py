"""汇总报表手工调整接口。"""

from decimal import Decimal

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.deps import get_current_user
from app.models.summary_adjustment import SummaryAdjustment
from app.models.user import User
from app.schemas.common import ApiResponse
from app.schemas.summary_adjustment import (
    SUMMARY_ADJUSTMENT_METRIC_LABELS,
    SummaryAdjustmentCreate,
    SummaryAdjustmentOut,
    SummaryAdjustmentUpdate,
)
from app.services.summary_adjustment_service import SummaryAdjustmentService

router = APIRouter()


@router.get("", response_model=ApiResponse[list[SummaryAdjustmentOut]])
async def list_summary_adjustments(
    source_year: int = Query(..., ge=2000, le=2100),
    source_month: int = Query(..., ge=1, le=12),
    platform_name: str = Query(...),
    shop_id: int = Query(...),
    metric_key: str | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """查询指定汇总维度下的调整记录。"""
    org_id = current_user.org_id if current_user.role != "superadmin" else current_user.org_id or 0
    items = await SummaryAdjustmentService.list_adjustments(
        db,
        org_id=org_id,
        source_year=source_year,
        source_month=source_month,
        platform_name=platform_name,
        shop_id=shop_id,
        metric_key=metric_key,
    )
    return ApiResponse(data=[to_adjustment_out(item) for item in items])


@router.post("", response_model=ApiResponse[SummaryAdjustmentOut])
async def create_summary_adjustment(
    body: SummaryAdjustmentCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """创建汇总调整记录。"""
    adjustment = await SummaryAdjustmentService.create_adjustment(
        db,
        data=body,
        current_user=current_user,
        request=request,
    )
    return ApiResponse(data=to_adjustment_out(adjustment))


@router.put("/{adjustment_id}", response_model=ApiResponse[SummaryAdjustmentOut])
async def update_summary_adjustment(
    adjustment_id: int,
    body: SummaryAdjustmentUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """更新汇总调整记录。"""
    adjustment = await SummaryAdjustmentService.update_adjustment(
        db,
        adjustment_id=adjustment_id,
        data=body,
        current_user=current_user,
        request=request,
    )
    if adjustment is None:
        return ApiResponse(code=404, message="调整记录不存在")
    return ApiResponse(data=to_adjustment_out(adjustment))


@router.delete("/{adjustment_id}", response_model=ApiResponse[None])
async def delete_summary_adjustment(
    adjustment_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """删除汇总调整记录。"""
    adjustment = await SummaryAdjustmentService.delete_adjustment(
        db,
        adjustment_id=adjustment_id,
        current_user=current_user,
        request=request,
    )
    if adjustment is None:
        return ApiResponse(code=404, message="调整记录不存在")
    return ApiResponse(message="已删除")


def to_adjustment_out(adjustment: SummaryAdjustment) -> SummaryAdjustmentOut:
    signed_amount = Decimal(str(adjustment.adjustment_amount or 0))
    return SummaryAdjustmentOut(
        id=adjustment.id,
        org_id=adjustment.org_id,
        source_year=adjustment.source_year,
        source_month=adjustment.source_month,
        platform_name=adjustment.platform_name,
        shop_id=adjustment.shop_id,
        shop_name=adjustment.shop_name,
        metric_key=adjustment.metric_key,
        metric_label=SUMMARY_ADJUSTMENT_METRIC_LABELS.get(adjustment.metric_key, adjustment.metric_key),
        direction="increase" if signed_amount >= 0 else "decrease",
        amount=float(abs(signed_amount)),
        adjustment_amount=float(signed_amount),
        remark=adjustment.remark,
        created_by=adjustment.created_by,
        updated_by=adjustment.updated_by,
        created_at=adjustment.created_at,
        updated_at=adjustment.updated_at,
    )
