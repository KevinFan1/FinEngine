"""对账清单接口。"""

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.deps import get_current_user
from app.models.reconciliation_checklist import ReconciliationChecklistTask, ReconciliationChecklistUploadFile
from app.models.user import User
from app.schemas.common import ApiResponse, PageResponse
from app.schemas.reconciliation_checklist import (
    ReconciliationChecklistEntityOptionOut,
    ReconciliationChecklistSummaryDetailOut,
    ReconciliationChecklistSummaryOut,
    ReconciliationChecklistTaskOut,
)
from app.services.oss_service import is_oss_object_unavailable_error, oss_service
from app.services.reconciliation_checklist_service import ReconciliationChecklistService

router = APIRouter()


class ReconciliationChecklistTaskRunOut(BaseModel):
    task_id: int
    status: str


class ReconciliationChecklistTaskBatchActionIn(BaseModel):
    task_ids: list[int]


class ReconciliationChecklistTaskBatchActionOut(BaseModel):
    total: int
    success_count: int
    failed_count: int
    success_ids: list[int]
    failed_items: list[dict[str, object]]


class ReconciliationChecklistTaskSourceDownloadOut(BaseModel):
    download_url: str
    filename: str
    expires_seconds: int


def _task_out(task, upload_file, org_name: str | None = None) -> ReconciliationChecklistTaskOut:
    return ReconciliationChecklistTaskOut(
        id=task.id,
        file_id=task.file_id,
        org_id=task.org_id,
        org_name=org_name,
        user_id=task.user_id,
        source_upload_file_id=upload_file.source_upload_file_id,
        original_name=upload_file.original_name,
        celery_task_id=task.celery_task_id,
        status=task.status,
        progress=task.progress,
        total_rows=task.total_rows,
        success_rows=task.success_rows,
        failed_rows=task.failed_rows,
        inserted_rows=task.inserted_rows,
        updated_rows=task.updated_rows,
        error_message=task.error_message,
        result_summary=task.result_summary,
        started_at=task.started_at,
        finished_at=task.finished_at,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


def _load_task_error(task: ReconciliationChecklistTask | None, upload_file: ReconciliationChecklistUploadFile | None) -> ApiResponse | None:
    if task is None or task.is_deleted:
        return ApiResponse(code=404, message="任务不存在")
    if upload_file is None or upload_file.is_deleted:
        return ApiResponse(code=404, message="上传文件不存在")
    return None


@router.get("/tasks", response_model=ApiResponse[PageResponse[ReconciliationChecklistTaskOut]])
async def list_tasks(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = Query(None),
    keyword: str | None = Query(None),
    org_id: str | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    rows, total = await ReconciliationChecklistService.list_tasks(
        db,
        user=current_user,
        org_id=org_id,
        status=status,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )
    items = [_task_out(task, upload_file, org_name) for task, upload_file, org_name in rows]
    return ApiResponse(data=PageResponse(items=items, total=total, page=page, page_size=page_size))


@router.post("/tasks/{task_id}/run", response_model=ApiResponse[ReconciliationChecklistTaskRunOut])
async def rerun_task(
    task_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")
    try:
        task = await ReconciliationChecklistService.rerun_task(
            db,
            task_id=task_id,
            user=current_user,
            ip=ip,
            user_agent=ua,
        )
    except ValueError as exc:
        return ApiResponse(code=400, message=str(exc))
    if task is None:
        return ApiResponse(code=404, message="任务不存在")
    return ApiResponse(data=ReconciliationChecklistTaskRunOut(task_id=task.id, status=task.status))


@router.post("/tasks/batch/recalculate", response_model=ApiResponse[ReconciliationChecklistTaskBatchActionOut])
async def batch_recalculate_tasks(
    body: ReconciliationChecklistTaskBatchActionIn,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """批量重新统计对账清单任务。"""
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
        task = await db.get(ReconciliationChecklistTask, task_id)
        if task is None or task.is_deleted:
            failed_items.append({"task_id": task_id, "message": "任务不存在"})
            continue
        if current_user.role != "superadmin" and task.org_id != current_user.org_id:
            failed_items.append({"task_id": task_id, "message": "数据不存在或无权访问"})
            continue
        if task.status in {"queued", "running"}:
            failed_items.append({"task_id": task_id, "message": "排队中或运行中的任务不能重新统计"})
            continue
        try:
            rerun = await ReconciliationChecklistService.rerun_task(
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

    data = ReconciliationChecklistTaskBatchActionOut(
        total=len(task_ids),
        success_count=len(success_ids),
        failed_count=len(failed_items),
        success_ids=success_ids,
        failed_items=failed_items,
    )
    message = "操作完成" if not failed_items else f"成功 {data.success_count} 个，失败 {data.failed_count} 个"
    return ApiResponse(data=data, message=message)


@router.post("/tasks/{task_id}/source-download", response_model=ApiResponse[ReconciliationChecklistTaskSourceDownloadOut])
async def get_task_source_download(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """获取对账清单任务原始文件的临时下载链接。"""
    if current_user.role != "superadmin":
        return ApiResponse(code=403, message="仅超级管理员可下载原表")

    task = await db.get(ReconciliationChecklistTask, task_id)
    if task is None or task.is_deleted:
        return ApiResponse(code=404, message="任务不存在")
    upload_file = await db.get(ReconciliationChecklistUploadFile, task.file_id)
    if upload_file is None or upload_file.is_deleted:
        return ApiResponse(code=404, message="上传文件不存在")
    if not upload_file.oss_key:
        return ApiResponse(code=404, message="原表不存在")

    expires_seconds = 300
    try:
        download_url = oss_service.sign_download_url(
            upload_file.oss_key,
            expires_seconds=expires_seconds,
            filename=upload_file.original_name,
        )
    except Exception as exc:
        if is_oss_object_unavailable_error(exc):
            return ApiResponse(code=404, message="源文件已过期或不存在，无法下载")
        return ApiResponse(code=502, message=f"生成下载链接失败: {exc}")

    return ApiResponse(
        data=ReconciliationChecklistTaskSourceDownloadOut(
            download_url=download_url,
            filename=upload_file.original_name,
            expires_seconds=expires_seconds,
        )
    )


@router.get("/summary", response_model=ApiResponse[PageResponse[ReconciliationChecklistSummaryOut]])
async def list_summary(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    org_id: str | None = Query(None),
    accounting_year: int | None = Query(None),
    accounting_month: int | None = Query(None, ge=1, le=12),
    accounting_start_year: int | None = Query(None),
    accounting_start_month: int | None = Query(None, ge=1, le=12),
    accounting_end_year: int | None = Query(None),
    accounting_end_month: int | None = Query(None, ge=1, le=12),
    shop_ids: str | None = Query(None),
    merchant_name: str | None = Query(None),
    live_promoter: str | None = Query(None),
    receipt_merchant: str | None = Query(None),
    merchant_ids: str | None = Query(None),
    live_promoter_ids: str | None = Query(None),
    receipt_merchant_ids: str | None = Query(None),
    keyword: str | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    rows, total = await ReconciliationChecklistService.list_summary(
        db,
        user=current_user,
        org_id=org_id,
        accounting_year=accounting_year,
        accounting_month=accounting_month,
        accounting_start_year=accounting_start_year,
        accounting_start_month=accounting_start_month,
        accounting_end_year=accounting_end_year,
        accounting_end_month=accounting_end_month,
        shop_ids=shop_ids,
        merchant_name=merchant_name,
        live_promoter=live_promoter,
        receipt_merchant=receipt_merchant,
        merchant_ids=merchant_ids,
        live_promoter_ids=live_promoter_ids,
        receipt_merchant_ids=receipt_merchant_ids,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )
    return ApiResponse(data=PageResponse(items=[ReconciliationChecklistSummaryOut.model_validate(row) for row in rows], total=total, page=page, page_size=page_size))


@router.get("/summary/details", response_model=ApiResponse[PageResponse[ReconciliationChecklistSummaryDetailOut]])
async def list_summary_details(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    org_id: str | None = Query(None),
    accounting_year: int = Query(...),
    accounting_month: int = Query(..., ge=1, le=12),
    merchant_name: str = Query(...),
    live_promoter: str = Query(...),
    receipt_merchant: str = Query(...),
    merchant_id: int | None = Query(None),
    live_promoter_id: int | None = Query(None),
    receipt_merchant_id: int | None = Query(None),
    shop_ids: str | None = Query(None),
    keyword: str | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    rows, total = await ReconciliationChecklistService.list_summary_details(
        db,
        user=current_user,
        org_id=org_id,
        accounting_year=accounting_year,
        accounting_month=accounting_month,
        merchant_name=merchant_name,
        live_promoter=live_promoter,
        receipt_merchant=receipt_merchant,
        merchant_id=merchant_id,
        live_promoter_id=live_promoter_id,
        receipt_merchant_id=receipt_merchant_id,
        shop_ids=shop_ids,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )
    return ApiResponse(data=PageResponse(items=[ReconciliationChecklistSummaryDetailOut.model_validate(row) for row in rows], total=total, page=page, page_size=page_size))


@router.get("/entities/options", response_model=ApiResponse[list[ReconciliationChecklistEntityOptionOut]])
async def list_entity_options(
    entity_type: str = Query(..., pattern="^(live_promoter|merchant|receipt_merchant)$"),
    accounting_year: int = Query(...),
    accounting_month: int = Query(..., ge=1, le=12),
    org_id: str | None = Query(None),
    parent_ids: str | None = Query(None),
    keyword: str | None = Query(None),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    try:
        rows = await ReconciliationChecklistService.list_entity_options(
            db,
            user=current_user,
            entity_type=entity_type,
            accounting_year=accounting_year,
            accounting_month=accounting_month,
            org_id=org_id,
            parent_ids=parent_ids,
            keyword=keyword,
            limit=limit,
        )
    except ValueError as exc:
        return ApiResponse(code=400, message=str(exc))
    return ApiResponse(data=[ReconciliationChecklistEntityOptionOut.model_validate(row) for row in rows])
