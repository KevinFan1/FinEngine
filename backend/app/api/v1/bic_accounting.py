"""BIC accounting API."""

from urllib.parse import quote

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.deps import get_current_user, require_org_admin_or_above
from app.models.bic_accounting import BicTask, BicUploadFile
from app.models.user import User
from app.schemas.bic_accounting import BicDetailOut, BicReportOut, BicTaskOut
from app.schemas.common import ApiResponse, PageResponse
from app.services.bic_accounting_service import BicAccountingService

router = APIRouter()


class BicTaskBatchActionIn(BaseModel):
    task_ids: list[int]


class BicTaskBatchActionOut(BaseModel):
    total: int
    success_count: int
    failed_count: int
    success_ids: list[int]
    failed_items: list[dict[str, object]]


def _task_out(task, upload_file) -> BicTaskOut:
    return BicTaskOut(
        id=task.id,
        file_id=task.file_id,
        org_id=task.org_id,
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
        result_summary=task.result_summary,
        started_at=task.started_at,
        finished_at=task.finished_at,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


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
    shop_id: int | None = Query(None),
    accounting_start_year: int | None = Query(None),
    accounting_start_month: int | None = Query(None),
    accounting_end_year: int | None = Query(None),
    accounting_end_month: int | None = Query(None),
    keyword: str | None = Query(None),
    org_id: int | None = Query(None),
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
        shop_id=shop_id,
        accounting_start_year=accounting_start_year,
        accounting_start_month=accounting_start_month,
        accounting_end_year=accounting_end_year,
        accounting_end_month=accounting_end_month,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )
    items = [_task_out(task, upload_file) for task, upload_file, _shop_color in rows]
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
    shop_id: int | None = Query(None),
    service_provider: str | None = Query(None),
    qic_warehouse: str | None = Query(None),
    accounting_year: int | None = Query(None),
    accounting_month: int | None = Query(None),
    accounting_start_year: int | None = Query(None),
    accounting_start_month: int | None = Query(None),
    accounting_end_year: int | None = Query(None),
    accounting_end_month: int | None = Query(None),
    org_id: int | None = Query(None),
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
        shop_id=shop_id,
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
    ids: str | None = Query(None),
    task_id: int | None = Query(None),
    platform_code: str | None = Query(None),
    shop_name: str | None = Query(None),
    shop_id: int | None = Query(None),
    service_provider: str | None = Query(None),
    qic_warehouse: str | None = Query(None),
    accounting_year: int | None = Query(None),
    accounting_month: int | None = Query(None),
    accounting_start_year: int | None = Query(None),
    accounting_start_month: int | None = Query(None),
    accounting_end_year: int | None = Query(None),
    accounting_end_month: int | None = Query(None),
    org_id: int | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    buffer = await BicAccountingService.export_details(
        db,
        user=current_user,
        org_id=org_id,
        ids=_parse_ids(ids) if ids else None,
        task_id=task_id,
        platform_code=platform_code,
        shop_name=shop_name,
        shop_id=shop_id,
        service_provider=service_provider,
        qic_warehouse=qic_warehouse,
        accounting_year=accounting_year,
        accounting_month=accounting_month,
        accounting_start_year=accounting_start_year,
        accounting_start_month=accounting_start_month,
        accounting_end_year=accounting_end_year,
        accounting_end_month=accounting_end_month,
    )
    return _export_response(buffer, "BIC明细.xlsx")


@router.get("/summary", response_model=ApiResponse[PageResponse[BicReportOut]])
async def list_reports(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    task_id: int | None = Query(None),
    platform_code: str | None = Query(None),
    shop_name: str | None = Query(None),
    shop_id: int | None = Query(None),
    service_provider: str | None = Query(None),
    accounting_year: int | None = Query(None),
    accounting_month: int | None = Query(None),
    accounting_start_year: int | None = Query(None),
    accounting_start_month: int | None = Query(None),
    accounting_end_year: int | None = Query(None),
    accounting_end_month: int | None = Query(None),
    org_id: int | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    rows, total = await BicAccountingService.list_reports(
        db,
        user=current_user,
        org_id=org_id,
        task_id=task_id,
        platform_code=platform_code,
        shop_name=shop_name,
        shop_id=shop_id,
        service_provider=service_provider,
        accounting_year=accounting_year,
        accounting_month=accounting_month,
        accounting_start_year=accounting_start_year,
        accounting_start_month=accounting_start_month,
        accounting_end_year=accounting_end_year,
        accounting_end_month=accounting_end_month,
        page=page,
        page_size=page_size,
    )
    return ApiResponse(data=PageResponse(items=[BicReportOut.model_validate(row) for row in rows], total=total, page=page, page_size=page_size))


@router.get("/summary/export")
async def export_reports(
    ids: str | None = Query(None),
    task_id: int | None = Query(None),
    platform_code: str | None = Query(None),
    shop_name: str | None = Query(None),
    shop_id: int | None = Query(None),
    service_provider: str | None = Query(None),
    accounting_year: int | None = Query(None),
    accounting_month: int | None = Query(None),
    accounting_start_year: int | None = Query(None),
    accounting_start_month: int | None = Query(None),
    accounting_end_year: int | None = Query(None),
    accounting_end_month: int | None = Query(None),
    org_id: int | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    buffer = await BicAccountingService.export_reports(
        db,
        user=current_user,
        org_id=org_id,
        ids=_parse_ids(ids) if ids else None,
        task_id=task_id,
        platform_code=platform_code,
        shop_name=shop_name,
        shop_id=shop_id,
        service_provider=service_provider,
        accounting_year=accounting_year,
        accounting_month=accounting_month,
        accounting_start_year=accounting_start_year,
        accounting_start_month=accounting_start_month,
        accounting_end_year=accounting_end_year,
        accounting_end_month=accounting_end_month,
    )
    return _export_response(buffer, "BIC报表.xlsx")
