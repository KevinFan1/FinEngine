"""对账清单接口。"""

from datetime import datetime

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_async_session
from app.core.deps import get_current_user
from app.models.reconciliation_checklist import ReconciliationChecklistTask, ReconciliationChecklistUploadFile
from app.models.user import User
from app.schemas.common import ApiResponse, PageResponse
from app.schemas.reconciliation_checklist import (
    ReconciliationChecklistEntityOptionOut,
    ReconciliationChecklistInvoiceEditQueryOut,
    ReconciliationChecklistInvoiceEditSaveIn,
    ReconciliationChecklistManualEditUploadCallbackIn,
    ReconciliationChecklistManualEditUploadFileOut,
    ReconciliationChecklistManualEditUploadInitIn,
    ReconciliationChecklistManualEditUploadInitOut,
    ReconciliationChecklistManualEditUploadInitResponse,
    ReconciliationChecklistManualEditQueryIn,
    ReconciliationChecklistManualEditSaveOut,
    ReconciliationChecklistMerchantEditQueryOut,
    ReconciliationChecklistMerchantEditSaveIn,
    ReconciliationChecklistOptionOut,
    ReconciliationChecklistPayableBalanceSummaryOut,
    ReconciliationChecklistProductSummaryOut,
    ReconciliationChecklistReceiptSummaryOut,
    ReconciliationChecklistSummaryDetailOut,
    ReconciliationChecklistSummaryOut,
    ReconciliationChecklistTaskOut,
)
from app.services.oss_service import assume_sts_role, is_oss_object_unavailable_error, oss_service
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


class ReconciliationChecklistDashboardMonthlyOut(BaseModel):
    month: int
    task_count: int


class ReconciliationChecklistDashboardMonthlyAmountOut(BaseModel):
    month: int
    total_user_paid_amount: str


class ReconciliationChecklistDashboardMerchantOut(BaseModel):
    merchant_name: str
    total_user_paid_amount: str


class ReconciliationChecklistDashboardRecentTaskOut(BaseModel):
    id: int
    original_name: str
    task_type: str
    status: str
    total_rows: int
    success_rows: int
    failed_rows: int
    inserted_rows: int
    finished_at: datetime | None


class ReconciliationChecklistDashboardOut(BaseModel):
    processed_task_count: int
    total_task_count: int
    failed_task_count: int
    total_rows: int
    total_user_paid_amount: str
    merchant_count: int
    covered_month_count: int
    completion_rate: str
    year: int
    monthly_task_counts: list[ReconciliationChecklistDashboardMonthlyOut]
    monthly_user_paid_amounts: list[ReconciliationChecklistDashboardMonthlyAmountOut]
    top_merchants: list[ReconciliationChecklistDashboardMerchantOut]
    recent_tasks: list[ReconciliationChecklistDashboardRecentTaskOut]


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
        task_type=getattr(task, "task_type", "source_import"),
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


async def _manual_edit_upload_init(
    *,
    body: ReconciliationChecklistManualEditUploadInitIn,
    task_type: str,
    current_user: User,
    db: AsyncSession,
) -> ApiResponse[ReconciliationChecklistManualEditUploadInitResponse]:
    if not settings.ALIYUN_STS_ROLE_ARN or not settings.ALIYUN_ACCESS_KEY_ID:
        return ApiResponse(code=501, message="阿里云 OSS STS 未配置")
    try:
        upload_file = await ReconciliationChecklistService.init_manual_edit_upload(
            db,
            org_id=body.org_id,
            user=current_user,
            original_name=body.original_name,
            file_size=body.file_size,
            task_type=task_type,
        )
    except ValueError as exc:
        return ApiResponse(code=400, message=str(exc))
    try:
        creds = assume_sts_role(
            role_arn=settings.ALIYUN_STS_ROLE_ARN,
            session_name=f"finengine-rcl-edit-{upload_file.org_id}-{upload_file.id}-{current_user.id}",
            duration_seconds=settings.ALIYUN_STS_EXPIRE_SECONDS,
        )
    except Exception:
        return ApiResponse(code=502, message="获取 OSS 上传凭证失败，请稍后重试")
    prefix = "upload/"
    return ApiResponse(
        data=ReconciliationChecklistManualEditUploadInitResponse(
            file=ReconciliationChecklistManualEditUploadFileOut.model_validate(upload_file),
            upload=ReconciliationChecklistManualEditUploadInitOut(
                file_id=upload_file.id,
                access_key_id=creds["access_key_id"],
                access_key_secret=creds["access_key_secret"],
                security_token=creds["security_token"],
                expiration=creds["expiration"],
                region=settings.ALIYUN_OSS_REGION,
                bucket=settings.ALIYUN_OSS_BUCKET,
                endpoint=oss_service.normalized_endpoint(),
                oss_key_prefix=prefix,
            ),
        )
    )


async def _manual_edit_upload_callback(
    *,
    body: ReconciliationChecklistManualEditUploadCallbackIn,
    task_type: str,
    request: Request,
    current_user: User,
    db: AsyncSession,
) -> ApiResponse[ReconciliationChecklistTaskRunOut]:
    upload_file = await db.get(ReconciliationChecklistUploadFile, body.file_id)
    if upload_file is None or upload_file.is_deleted:
        return ApiResponse(code=404, message="上传文件不存在")
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")
    try:
        task = await ReconciliationChecklistService.create_manual_edit_upload_task_from_oss(
            db,
            org_id=upload_file.org_id,
            user=current_user,
            file_id=upload_file.id,
            original_name=upload_file.original_name,
            oss_key=body.oss_key,
            file_size=body.file_size,
            file_hash=body.file_hash,
            task_type=task_type,
            ip=ip,
            user_agent=ua,
        )
    except ValueError as exc:
        return ApiResponse(code=400, message=str(exc))
    return ApiResponse(data=ReconciliationChecklistTaskRunOut(task_id=task.id, status=task.status), message="已提交任务中心处理")


@router.post("/invoice-edits/query", response_model=ApiResponse[ReconciliationChecklistInvoiceEditQueryOut])
async def query_invoice_edit_items(
    body: ReconciliationChecklistManualEditQueryIn,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    try:
        matched_items, missing_sub_order_nos = await ReconciliationChecklistService.query_invoice_edit_items(
            db,
            org_id=body.org_id,
            user=current_user,
            sub_order_nos=body.sub_order_nos,
        )
    except ValueError as exc:
        return ApiResponse(code=400, message=str(exc))
    return ApiResponse(data=ReconciliationChecklistInvoiceEditQueryOut(matched_items=matched_items, missing_sub_order_nos=missing_sub_order_nos))


@router.post("/invoice-edits/save", response_model=ApiResponse[ReconciliationChecklistManualEditSaveOut])
async def save_invoice_edit_items(
    body: ReconciliationChecklistInvoiceEditSaveIn,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")
    try:
        result = await ReconciliationChecklistService.save_invoice_edit_items(
            db,
            org_id=body.org_id,
            user=current_user,
            items=[item.model_dump() for item in body.items],
            ip=ip,
            user_agent=ua,
        )
    except ValueError as exc:
        return ApiResponse(code=400, message=str(exc))
    return ApiResponse(data=ReconciliationChecklistManualEditSaveOut.model_validate(result))


@router.post("/invoice-edits/upload-init", response_model=ApiResponse[ReconciliationChecklistManualEditUploadInitResponse])
async def init_invoice_edit_upload(
    body: ReconciliationChecklistManualEditUploadInitIn,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    return await _manual_edit_upload_init(body=body, task_type="invoice_edit", current_user=current_user, db=db)


@router.post("/invoice-edits/upload-callback", response_model=ApiResponse[ReconciliationChecklistTaskRunOut])
async def callback_invoice_edit_upload(
    body: ReconciliationChecklistManualEditUploadCallbackIn,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    return await _manual_edit_upload_callback(body=body, task_type="invoice_edit", request=request, current_user=current_user, db=db)


@router.post("/merchant-edits/query", response_model=ApiResponse[ReconciliationChecklistMerchantEditQueryOut])
async def query_merchant_edit_items(
    body: ReconciliationChecklistManualEditQueryIn,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    try:
        matched_items, missing_sub_order_nos = await ReconciliationChecklistService.query_merchant_edit_items(
            db,
            org_id=body.org_id,
            user=current_user,
            sub_order_nos=body.sub_order_nos,
        )
    except ValueError as exc:
        return ApiResponse(code=400, message=str(exc))
    return ApiResponse(data=ReconciliationChecklistMerchantEditQueryOut(matched_items=matched_items, missing_sub_order_nos=missing_sub_order_nos))


@router.post("/merchant-edits/save", response_model=ApiResponse[ReconciliationChecklistManualEditSaveOut])
async def save_merchant_edit_items(
    body: ReconciliationChecklistMerchantEditSaveIn,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")
    try:
        result = await ReconciliationChecklistService.save_merchant_edit_items(
            db,
            org_id=body.org_id,
            user=current_user,
            items=[item.model_dump() for item in body.items],
            ip=ip,
            user_agent=ua,
        )
    except ValueError as exc:
        return ApiResponse(code=400, message=str(exc))
    return ApiResponse(data=ReconciliationChecklistManualEditSaveOut.model_validate(result))


@router.post("/merchant-edits/upload-init", response_model=ApiResponse[ReconciliationChecklistManualEditUploadInitResponse])
async def init_merchant_edit_upload(
    body: ReconciliationChecklistManualEditUploadInitIn,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    return await _manual_edit_upload_init(body=body, task_type="merchant_edit", current_user=current_user, db=db)


@router.post("/merchant-edits/upload-callback", response_model=ApiResponse[ReconciliationChecklistTaskRunOut])
async def callback_merchant_edit_upload(
    body: ReconciliationChecklistManualEditUploadCallbackIn,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    return await _manual_edit_upload_callback(body=body, task_type="merchant_edit", request=request, current_user=current_user, db=db)


@router.get("/dashboard-metrics", response_model=ApiResponse[ReconciliationChecklistDashboardOut])
async def get_dashboard_metrics(
    year: int | None = Query(None, ge=2000, le=2100),
    org_id: str | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    metric_year = year or datetime.now().year
    metrics = await ReconciliationChecklistService.get_dashboard_metrics(
        db,
        user=current_user,
        year=metric_year,
        org_id=org_id,
    )
    return ApiResponse(
        data=ReconciliationChecklistDashboardOut(
            processed_task_count=int(metrics["processed_task_count"]),
            total_task_count=int(metrics["total_task_count"]),
            failed_task_count=int(metrics["failed_task_count"]),
            total_rows=int(metrics["total_rows"]),
            total_user_paid_amount=str(metrics["total_user_paid_amount"]),
            merchant_count=int(metrics["merchant_count"]),
            covered_month_count=int(metrics["covered_month_count"]),
            completion_rate=str(metrics["completion_rate"]),
            year=int(metrics["year"]),
            monthly_task_counts=[
                ReconciliationChecklistDashboardMonthlyOut(
                    month=int(item["month"]),
                    task_count=int(item["task_count"]),
                )
                for item in metrics["monthly_task_counts"]
            ],
            monthly_user_paid_amounts=[
                ReconciliationChecklistDashboardMonthlyAmountOut(
                    month=int(item["month"]),
                    total_user_paid_amount=str(item["total_user_paid_amount"]),
                )
                for item in metrics["monthly_user_paid_amounts"]
            ],
            top_merchants=[
                ReconciliationChecklistDashboardMerchantOut(
                    merchant_name=str(item["merchant_name"]),
                    total_user_paid_amount=str(item["total_user_paid_amount"]),
                )
                for item in metrics["top_merchants"]
            ],
            recent_tasks=[
                ReconciliationChecklistDashboardRecentTaskOut(
                    id=int(item["id"]),
                    original_name=str(item["original_name"]),
                    status=str(item["status"]),
                    task_type=str(item.get("task_type") or "source_import"),
                    total_rows=int(item["total_rows"]),
                    success_rows=int(item["success_rows"]),
                    failed_rows=int(item["failed_rows"]),
                    inserted_rows=int(item["inserted_rows"]),
                    finished_at=item["finished_at"],
                )
                for item in metrics["recent_tasks"]
            ],
        )
    )


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
    rows, total = await ReconciliationChecklistService.list_product_summary(
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
        merchant_subject_name=merchant_name,
        receipt_merchant=receipt_merchant,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )
    return ApiResponse(data=PageResponse(items=[ReconciliationChecklistSummaryOut.model_validate(row) for row in rows], total=total, page=page, page_size=page_size))


@router.get("/product-summary", response_model=ApiResponse[PageResponse[ReconciliationChecklistProductSummaryOut]])
async def list_product_summary(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    org_id: str | None = Query(None),
    accounting_year: int | None = Query(None),
    accounting_month: int | None = Query(None, ge=1, le=12),
    accounting_start_year: int | None = Query(None),
    accounting_start_month: int | None = Query(None, ge=1, le=12),
    accounting_end_year: int | None = Query(None),
    accounting_end_month: int | None = Query(None, ge=1, le=12),
    merchant_subject_name: str | None = Query(None),
    receipt_merchant: str | None = Query(None),
    product_name: str | None = Query(None),
    keyword: str | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    rows, total = await ReconciliationChecklistService.list_product_summary(
        db,
        user=current_user,
        org_id=org_id,
        accounting_year=accounting_year,
        accounting_month=accounting_month,
        accounting_start_year=accounting_start_year,
        accounting_start_month=accounting_start_month,
        accounting_end_year=accounting_end_year,
        accounting_end_month=accounting_end_month,
        merchant_subject_name=merchant_subject_name,
        receipt_merchant=receipt_merchant,
        product_name=product_name,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )
    return ApiResponse(data=PageResponse(items=[ReconciliationChecklistProductSummaryOut.model_validate(row) for row in rows], total=total, page=page, page_size=page_size))


@router.get("/receipt-summary", response_model=ApiResponse[PageResponse[ReconciliationChecklistReceiptSummaryOut]])
async def list_receipt_summary(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    org_id: str | None = Query(None),
    accounting_year: int | None = Query(None),
    accounting_month: int | None = Query(None, ge=1, le=12),
    accounting_start_year: int | None = Query(None),
    accounting_start_month: int | None = Query(None, ge=1, le=12),
    accounting_end_year: int | None = Query(None),
    accounting_end_month: int | None = Query(None, ge=1, le=12),
    merchant_subject_name: str | None = Query(None),
    receipt_merchant: str | None = Query(None),
    live_platform: str | None = Query(None),
    keyword: str | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    rows, total = await ReconciliationChecklistService.list_receipt_summary(
        db,
        user=current_user,
        org_id=org_id,
        accounting_year=accounting_year,
        accounting_month=accounting_month,
        accounting_start_year=accounting_start_year,
        accounting_start_month=accounting_start_month,
        accounting_end_year=accounting_end_year,
        accounting_end_month=accounting_end_month,
        merchant_subject_name=merchant_subject_name,
        receipt_merchant=receipt_merchant,
        live_platform=live_platform,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )
    return ApiResponse(data=PageResponse(items=[ReconciliationChecklistReceiptSummaryOut.model_validate(row) for row in rows], total=total, page=page, page_size=page_size))


@router.get("/payable-balance-summary", response_model=ApiResponse[PageResponse[ReconciliationChecklistPayableBalanceSummaryOut]])
async def list_payable_balance_summary(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    org_id: str | None = Query(None),
    accounting_year: int | None = Query(None),
    accounting_month: int | None = Query(None, ge=1, le=12),
    accounting_start_year: int | None = Query(None),
    accounting_start_month: int | None = Query(None, ge=1, le=12),
    accounting_end_year: int | None = Query(None),
    accounting_end_month: int | None = Query(None, ge=1, le=12),
    merchant_subject_name: str | None = Query(None),
    receipt_merchant: str | None = Query(None),
    keyword: str | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    rows, total = await ReconciliationChecklistService.list_payable_balance_summary(
        db,
        user=current_user,
        org_id=org_id,
        accounting_year=accounting_year,
        accounting_month=accounting_month,
        accounting_start_year=accounting_start_year,
        accounting_start_month=accounting_start_month,
        accounting_end_year=accounting_end_year,
        accounting_end_month=accounting_end_month,
        merchant_subject_name=merchant_subject_name,
        receipt_merchant=receipt_merchant,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )
    return ApiResponse(data=PageResponse(items=[ReconciliationChecklistPayableBalanceSummaryOut.model_validate(row) for row in rows], total=total, page=page, page_size=page_size))


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
    rows, total = await ReconciliationChecklistService.list_product_summary(
        db,
        user=current_user,
        org_id=org_id,
        accounting_year=accounting_year,
        accounting_month=accounting_month,
        merchant_subject_name=merchant_name,
        receipt_merchant=receipt_merchant,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )
    return ApiResponse(data=PageResponse(items=[ReconciliationChecklistSummaryDetailOut.model_validate(row) for row in rows], total=total, page=page, page_size=page_size))


@router.get("/options", response_model=ApiResponse[list[ReconciliationChecklistOptionOut]])
async def list_options(
    kind: str = Query(..., pattern="^(merchant_subject|receipt_merchant|live_platform|product_name)$"),
    accounting_year: int | None = Query(None),
    accounting_month: int | None = Query(None, ge=1, le=12),
    org_id: str | None = Query(None),
    keyword: str | None = Query(None),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    try:
        rows = await ReconciliationChecklistService.list_options(
            db,
            user=current_user,
            kind=kind,
            accounting_year=accounting_year,
            accounting_month=accounting_month,
            org_id=org_id,
            keyword=keyword,
            limit=limit,
        )
    except ValueError as exc:
        return ApiResponse(code=400, message=str(exc))
    return ApiResponse(data=[ReconciliationChecklistOptionOut.model_validate(row) for row in rows])


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
