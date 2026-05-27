"""BIC accounting API."""
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.deps import get_current_user, require_org_admin_or_above
from app.models.bic_accounting import BicTask, BicUploadFile
from app.models.user import User
from app.schemas.bic_accounting import BicDetailOut, BicSourceRowOut, BicTaskOut
from app.schemas.common import ApiResponse, PageResponse
from app.services.bic_accounting_service import BicAccountingService
from app.utils.query_filters import parse_query_datetime

router = APIRouter()


class BicTaskBatchActionIn(BaseModel):
    task_ids: list[int]


class BicTaskBatchActionOut(BaseModel):
    total: int
    success_count: int
    failed_count: int
    success_ids: list[int]
    failed_items: list[dict[str, object]]


def _task_out(task, upload_file, org_name: str | None = None) -> BicTaskOut:
    item = BicTaskOut(
        id=task.id,
        file_id=task.file_id,
        org_id=task.org_id,
        org_name=org_name,
        user_id=task.user_id,
        shop_id=upload_file.shop_id,
        source_upload_file_id=upload_file.source_upload_file_id,
        original_name=upload_file.original_name,
        platform_code=upload_file.platform_code,
        shop_name=upload_file.shop_name,
        accounting_year=upload_file.accounting_year,
        accounting_month=upload_file.accounting_month,
        celery_task_id=task.celery_task_id,
        status=task.status,
        progress=task.progress,
        processed_rows=task.processed_rows,
        success_rows=task.success_rows,
        failed_rows=task.failed_rows,
        result_success=task.success_rows,
        result_failed=task.failed_rows,
        error_message=task.error_message,
        error_reason=task.error_message,
        result_summary=_normalize_bic_summary(task.result_summary),
        started_at=task.started_at,
        finished_at=task.finished_at,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )
    return item


def _normalize_bic_summary(result_summary: dict | None) -> dict | None:
    if not result_summary:
        return result_summary
    hidden_keys = {
        "report_groups",
        "report_ids",
        "report_id",
        "报表分组数",
        "报表记录ID列表",
        "首个报表记录ID",
    }
    labels = {
        "type": "文件类型",
        "total_rows": "总行数",
        "success_rows": "符合条件行数",
        "failed_rows": "失败行数",
        "groups": "明细分组数",
        "source_rows": "源数据行数",
        "errors": "错误明细",
        "detail_ids": "明细记录ID列表",
    }
    normalized: dict = {}
    for key, value in result_summary.items():
        if key in hidden_keys:
            continue
        label = labels.get(key, key)
        if key == "type" and isinstance(value, str) and value.lower() == "bic":
            value = "BIC"
        normalized[label] = value
    return normalized


def _export_response(buffer, filename: str) -> StreamingResponse:
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
    )


def _parse_ids(raw_ids: str | None) -> list[int]:
    if not raw_ids:
        return []
    ids: list[int] = []
    for raw in raw_ids.split(","):
        raw = raw.strip()
        if raw:
            ids.append(int(raw))
    return ids


@router.get("/tasks", response_model=ApiResponse[PageResponse[BicTaskOut]])
async def list_tasks(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = Query(None),
    platform_code: str | None = Query(None),
    shop_name: str | None = Query(None),
    shop_ids: str | None = Query(None),
    accounting_start_year: int | None = Query(None),
    accounting_start_month: int | None = Query(None),
    accounting_end_year: int | None = Query(None),
    accounting_end_month: int | None = Query(None),
    keyword: str | None = Query(None),
    org_id: str | None = Query(None),
    created_start_time: str | None = Query(None),
    created_end_time: str | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    rows, total = await BicAccountingService.list_tasks(
        db,
        user=current_user,
        org_id=org_id,
        status=status,
        platform_code=platform_code,
        shop_name=shop_name,
        shop_ids=shop_ids,
        accounting_start_year=accounting_start_year,
        accounting_start_month=accounting_start_month,
        accounting_end_year=accounting_end_year,
        accounting_end_month=accounting_end_month,
        keyword=keyword,
        created_start_time=parse_query_datetime(created_start_time),
        created_end_time=parse_query_datetime(created_end_time),
        page=page,
        page_size=page_size,
    )
    items = [_task_out(task, upload_file, org_name) for task, upload_file, _shop_color, org_name in rows]
    return ApiResponse(data=PageResponse(items=items, total=total, page=page, page_size=page_size))


@router.post("/tasks/{task_id}/run", response_model=ApiResponse[BicTaskOut])
async def rerun_task(
    task_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    _admin: User = Depends(require_org_admin_or_above),
    db: AsyncSession = Depends(get_async_session),
):
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")
    try:
        task = await BicAccountingService.rerun_task(
            db,
            task_id=task_id,
            user=current_user,
            ip=ip,
            user_agent=ua,
        )
    except ValueError as exc:
        return ApiResponse(code=403, message=str(exc))
    if task is None:
        return ApiResponse(code=404, message="任务不存在")
    upload_file = await db.get(BicUploadFile, task.file_id)
    return ApiResponse(data=_task_out(task, upload_file))


@router.post("/tasks/batch/recalculate", response_model=ApiResponse[BicTaskBatchActionOut])
async def batch_recalculate_tasks(
    body: BicTaskBatchActionIn,
    request: Request,
    current_user: User = Depends(get_current_user),
    _admin: User = Depends(require_org_admin_or_above),
    db: AsyncSession = Depends(get_async_session),
):
    task_ids = list(dict.fromkeys(body.task_ids))
    if not task_ids:
        return ApiResponse(code=400, message="请选择任务")
    if len(task_ids) > 100:
        return ApiResponse(code=400, message="单次最多操作 100 个任务")

    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")
    success_ids: list[int] = []
    failed_items: list[dict[str, object]] = []
    for task_id in task_ids:
        task = await db.get(BicTask, task_id)
        if task is None or task.is_deleted:
            failed_items.append({"task_id": task_id, "message": "任务不存在"})
            continue
        if current_user.role != "superadmin" and task.org_id != current_user.org_id:
            failed_items.append({"task_id": task_id, "message": "数据不存在或无权访问"})
            continue
        if task.status in {"queued", "processing"}:
            failed_items.append({"task_id": task_id, "message": "排队中或运行中的任务不能重新统计"})
            continue

        try:
            rerun = await BicAccountingService.rerun_task(
                db,
                task_id=task_id,
                user=current_user,
                ip=ip,
                user_agent=ua,
            )
        except ValueError as exc:
            failed_items.append({"task_id": task_id, "message": str(exc)})
            continue
        if rerun is None:
            failed_items.append({"task_id": task_id, "message": "任务不存在"})
            continue
        success_ids.append(rerun.id)

    data = BicTaskBatchActionOut(
        total=len(task_ids),
        success_count=len(success_ids),
        failed_count=len(failed_items),
        success_ids=success_ids,
        failed_items=failed_items,
    )
    message = "操作完成" if not failed_items else f"成功 {data.success_count} 个，失败 {data.failed_count} 个"
    return ApiResponse(data=data, message=message)


@router.get("/details", response_model=ApiResponse[PageResponse[BicDetailOut]])
async def list_details(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    task_id: int | None = Query(None),
    platform_code: str | None = Query(None),
    shop_name: str | None = Query(None),
    shop_ids: str | None = Query(None),
    service_provider: str | None = Query(None),
    qic_warehouse: str | None = Query(None),
    accounting_year: int | None = Query(None),
    accounting_month: int | None = Query(None),
    accounting_start_year: int | None = Query(None),
    accounting_start_month: int | None = Query(None),
    accounting_end_year: int | None = Query(None),
    accounting_end_month: int | None = Query(None),
    org_id: str | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    rows, total = await BicAccountingService.list_details(
        db,
        user=current_user,
        org_id=org_id,
        task_id=task_id,
        platform_code=platform_code,
        shop_name=shop_name,
        shop_ids=shop_ids,
        service_provider=service_provider,
        qic_warehouse=qic_warehouse,
        accounting_year=accounting_year,
        accounting_month=accounting_month,
        accounting_start_year=accounting_start_year,
        accounting_start_month=accounting_start_month,
        accounting_end_year=accounting_end_year,
        accounting_end_month=accounting_end_month,
        page=page,
        page_size=page_size,
    )
    return ApiResponse(data=PageResponse(items=[BicDetailOut.model_validate(row) for row in rows], total=total, page=page, page_size=page_size))


@router.get("/details/export")
async def export_details(
    scope: str = Query("all", pattern="^(all|current_page|selected)$"),
    ids: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    task_id: int | None = Query(None),
    platform_code: str | None = Query(None),
    shop_name: str | None = Query(None),
    shop_ids: str | None = Query(None),
    service_provider: str | None = Query(None),
    qic_warehouse: str | None = Query(None),
    accounting_year: int | None = Query(None),
    accounting_month: int | None = Query(None),
    accounting_start_year: int | None = Query(None),
    accounting_start_month: int | None = Query(None),
    accounting_end_year: int | None = Query(None),
    accounting_end_month: int | None = Query(None),
    org_id: str | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    selected_ids = _parse_ids(ids) if ids else []
    if scope == "selected" and not selected_ids:
        raise HTTPException(status_code=400, detail="请选择要导出的汇总")
    try:
        buffer = await BicAccountingService.export_details(
            db,
            scope=scope,
            user=current_user,
            org_id=org_id,
            ids=selected_ids if scope == "selected" else None,
            page=page,
            page_size=page_size,
            task_id=task_id,
            platform_code=platform_code,
            shop_name=shop_name,
            shop_ids=shop_ids,
            service_provider=service_provider,
            qic_warehouse=qic_warehouse,
            accounting_year=accounting_year,
            accounting_month=accounting_month,
            accounting_start_year=accounting_start_year,
            accounting_start_month=accounting_start_month,
            accounting_end_year=accounting_end_year,
            accounting_end_month=accounting_end_month,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _export_response(buffer, "BIC汇总.xlsx")


@router.get("/source-rows", response_model=ApiResponse[PageResponse[BicSourceRowOut]])
async def list_source_rows(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    task_id: int | None = Query(None),
    platform_code: str | None = Query(None),
    shop_name: str | None = Query(None),
    shop_ids: str | None = Query(None),
    service_provider: str | None = Query(None),
    qic_warehouse: str | None = Query(None),
    accounting_year: int | None = Query(None),
    accounting_month: int | None = Query(None),
    accounting_start_year: int | None = Query(None),
    accounting_start_month: int | None = Query(None),
    accounting_end_year: int | None = Query(None),
    accounting_end_month: int | None = Query(None),
    org_id: str | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    rows, total = await BicAccountingService.list_source_rows(
        db,
        user=current_user,
        org_id=org_id,
        task_id=task_id,
        platform_code=platform_code,
        shop_name=shop_name,
        shop_ids=shop_ids,
        service_provider=service_provider,
        qic_warehouse=qic_warehouse,
        accounting_year=accounting_year,
        accounting_month=accounting_month,
        accounting_start_year=accounting_start_year,
        accounting_start_month=accounting_start_month,
        accounting_end_year=accounting_end_year,
        accounting_end_month=accounting_end_month,
        page=page,
        page_size=page_size,
    )
    return ApiResponse(data=PageResponse(items=[BicSourceRowOut.model_validate(row) for row in rows], total=total, page=page, page_size=page_size))


@router.get("/source-rows/export")
async def export_source_rows(
    scope: str = Query("current_page", pattern="^(current_page|selected)$"),
    ids: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    task_id: int | None = Query(None),
    platform_code: str | None = Query(None),
    shop_name: str | None = Query(None),
    shop_ids: str | None = Query(None),
    service_provider: str | None = Query(None),
    qic_warehouse: str | None = Query(None),
    accounting_year: int | None = Query(None),
    accounting_month: int | None = Query(None),
    accounting_start_year: int | None = Query(None),
    accounting_start_month: int | None = Query(None),
    accounting_end_year: int | None = Query(None),
    accounting_end_month: int | None = Query(None),
    org_id: str | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    selected_ids = _parse_ids(ids) if ids else []
    if scope == "selected" and not selected_ids:
        raise HTTPException(status_code=400, detail="请选择要导出的源数据")
    try:
        buffer = await BicAccountingService.export_source_rows(
            db,
            scope=scope,
            user=current_user,
            org_id=org_id,
            ids=selected_ids if scope == "selected" else None,
            task_id=task_id,
            platform_code=platform_code,
            shop_name=shop_name,
            shop_ids=shop_ids,
            service_provider=service_provider,
            qic_warehouse=qic_warehouse,
            accounting_year=accounting_year,
            accounting_month=accounting_month,
            accounting_start_year=accounting_start_year,
            accounting_start_month=accounting_start_month,
            accounting_end_year=accounting_end_year,
            accounting_end_month=accounting_end_month,
            page=page,
            page_size=page_size,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _export_response(buffer, "BIC明细.xlsx")


@router.get("/details/{detail_id}/source-rows", response_model=ApiResponse[PageResponse[BicSourceRowOut]])
async def list_detail_source_rows(
    detail_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    org_id: str | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    rows, total = await BicAccountingService.list_source_rows(
        db,
        user=current_user,
        org_id=org_id,
        detail_id=detail_id,
        page=page,
        page_size=page_size,
    )
    return ApiResponse(data=PageResponse(items=[BicSourceRowOut.model_validate(row) for row in rows], total=total, page=page, page_size=page_size))


@router.get("/reconciliation/export")
async def export_reconciliation(
    accounting_year: int = Query(...),
    accounting_month: int = Query(..., ge=1, le=12),
    service_provider: str = Query(..., min_length=1),
    platform_code: str | None = Query(None),
    shop_name: str | None = Query(None),
    shop_ids: str | None = Query(None),
    qic_warehouse: str | None = Query(None),
    org_id: str | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    try:
        buffer = await BicAccountingService.export_reconciliation(
            db,
            user=current_user,
            org_id=org_id,
            accounting_year=accounting_year,
            accounting_month=accounting_month,
            service_provider=service_provider,
            platform_code=platform_code,
            shop_name=shop_name,
            shop_ids=shop_ids,
            qic_warehouse=qic_warehouse,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    filename = f"{accounting_year}-{accounting_month:02d}_{service_provider}_BIC对账表.xlsx"
    return _export_response(buffer, filename)
