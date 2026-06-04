"""通用处理任务查询与操作接口。"""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.deps import get_current_user
from app.models.organization import Organization
from app.models.shop import Shop
from app.models.task import ProcessingTask
from app.models.upload import UploadFile
from app.models.user import User
from app.schemas.common import ApiResponse, PageResponse
from app.schemas.task import TaskListOut, TaskOut
from app.services.oss_service import is_oss_object_unavailable_error, oss_service
from app.services.platform_profile_service import resolve_platform_profile
from app.services.shop_visibility import active_shop_filter
from app.utils.query_filters import datetime_range_filters, parse_query_datetime, split_int_filter_values

router = APIRouter()
TASK_ACTION_EXPIRE_DAYS = 30


def split_filter_values(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


class TaskProgressOut(BaseModel):
    """Lightweight progress info for frontend polling."""

    id: int
    status: str
    progress: int
    processed_rows: int
    success_rows: int
    failed_rows: int
    error_message: str | None = None
    error_reason: str | None = None

    class Config:
        from_attributes = True


class TaskBatchActionIn(BaseModel):
    task_ids: list[int]


class TaskBatchActionOut(BaseModel):
    total: int
    success_count: int
    failed_count: int
    success_ids: list[int]
    failed_items: list[dict[str, object]]


class TaskSourceDownloadOut(BaseModel):
    download_url: str
    filename: str
    expires_seconds: int


@router.get("", response_model=ApiResponse[PageResponse[TaskListOut]])
async def list_tasks(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: str | None = Query(None, alias="status"),
    platform: str | None = Query(None),
    shop_id: str | None = Query(None),
    shop_name: str | None = Query(None),
    parsed_type: str | None = Query(None),
    parsed_year: int | None = Query(None),
    parsed_month: int | None = Query(None),
    keyword: str | None = Query(None),
    batch_id: int | None = Query(None),
    org_id: str | None = Query(None),
    created_start_time: str | None = Query(None),
    created_end_time: str | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """分页查询处理任务列表。"""
    stmt = (
        select(ProcessingTask, UploadFile, Shop.shop_color, Organization.name.label("org_name"))
        .join(UploadFile, ProcessingTask.file_id == UploadFile.id)
        .outerjoin(Shop, UploadFile.shop_id == Shop.id)
        .outerjoin(
            Organization,
            and_(Organization.id == ProcessingTask.org_id, Organization.is_deleted.is_(False)),
        )
        .where(
            ProcessingTask.is_deleted.is_(False),
            UploadFile.is_deleted.is_(False),
            active_shop_filter(UploadFile.shop_id),
        )
        .order_by(ProcessingTask.updated_at.desc(), ProcessingTask.id.desc())
    )
    count_stmt = (
        select(func.count())
        .select_from(ProcessingTask)
        .join(UploadFile, ProcessingTask.file_id == UploadFile.id)
        .where(
            ProcessingTask.is_deleted.is_(False),
            UploadFile.is_deleted.is_(False),
            active_shop_filter(UploadFile.shop_id),
        )
    )

    # Scope: non-superadmin only sees own org
    if current_user.role != "superadmin":
        stmt = stmt.where(ProcessingTask.org_id == current_user.org_id)
        count_stmt = count_stmt.where(ProcessingTask.org_id == current_user.org_id)
    else:
        org_ids = split_int_filter_values(org_id)
        if org_ids:
            stmt = stmt.where(ProcessingTask.org_id.in_(org_ids))
            count_stmt = count_stmt.where(ProcessingTask.org_id.in_(org_ids))

    status_values = split_filter_values(status_filter)
    if status_values:
        stmt = stmt.where(ProcessingTask.status.in_(status_values))
        count_stmt = count_stmt.where(ProcessingTask.status.in_(status_values))

    platform_values = split_filter_values(platform)
    if platform_values:
        stmt = stmt.where(UploadFile.detected_platform.in_(platform_values))
        count_stmt = count_stmt.where(UploadFile.detected_platform.in_(platform_values))

    shop_ids = split_int_filter_values(shop_id)
    if shop_ids:
        stmt = stmt.where(UploadFile.shop_id.in_(shop_ids))
        count_stmt = count_stmt.where(UploadFile.shop_id.in_(shop_ids))

    shop_names = split_filter_values(shop_name)
    if shop_names:
        stmt = stmt.where(UploadFile.parsed_shop.in_(shop_names))
        count_stmt = count_stmt.where(UploadFile.parsed_shop.in_(shop_names))

    parsed_type_values = split_filter_values(parsed_type)
    if parsed_type_values:
        stmt = stmt.where(UploadFile.parsed_type.in_(parsed_type_values))
        count_stmt = count_stmt.where(UploadFile.parsed_type.in_(parsed_type_values))

    if parsed_year is not None:
        stmt = stmt.where(UploadFile.parsed_year == parsed_year)
        count_stmt = count_stmt.where(UploadFile.parsed_year == parsed_year)

    if parsed_month is not None:
        stmt = stmt.where(UploadFile.parsed_month == parsed_month)
        count_stmt = count_stmt.where(UploadFile.parsed_month == parsed_month)

    if keyword:
        keyword_pattern = f"%{keyword.strip()}%"
        stmt = stmt.where(or_(UploadFile.original_name.ilike(keyword_pattern), UploadFile.parsed_shop.ilike(keyword_pattern)))
        count_stmt = count_stmt.where(or_(UploadFile.original_name.ilike(keyword_pattern), UploadFile.parsed_shop.ilike(keyword_pattern)))

    if batch_id is not None:
        stmt = stmt.where(UploadFile.batch_id == batch_id)
        count_stmt = count_stmt.where(UploadFile.batch_id == batch_id)

    created_time_filters = datetime_range_filters(
        ProcessingTask.created_at,
        start_time=parse_query_datetime(created_start_time),
        end_time=parse_query_datetime(created_end_time),
    )
    if created_time_filters:
        stmt = stmt.where(*created_time_filters)
        count_stmt = count_stmt.where(*created_time_filters)

    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0

    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(stmt)
    rows = result.all()

    return ApiResponse(
        data=PageResponse(
            items=[
                build_task_list_out(task, upload_file, shop_color, org_name)
                for task, upload_file, shop_color, org_name in rows
            ],
            total=total,
            page=page,
            page_size=page_size,
        )
    )


def build_task_list_out(
    task: ProcessingTask,
    upload_file: UploadFile,
    shop_color: str | None = None,
    org_name: str | None = None,
) -> TaskListOut:
    error_reason = task.error_reason or upload_file.error_message
    action_expired = is_task_expired(task)
    return TaskListOut(
        id=task.id,
        file_id=task.file_id,
        org_id=task.org_id,
        org_name=org_name,
        batch_id=upload_file.batch_id,
        filename=upload_file.original_name,
        platform=upload_file.source_platform_code or upload_file.detected_platform,
        source_platform_code=upload_file.source_platform_code or upload_file.detected_platform,
        report_platform_code=upload_file.report_platform_code,
        shop_id=upload_file.shop_id,
        shop_name=upload_file.parsed_shop,
        shop_color=shop_color,
        parsed_type=upload_file.parsed_type,
        parsed_year=upload_file.parsed_year,
        parsed_month=upload_file.parsed_month,
        status=task.status,
        progress=task.progress,
        processed_rows=task.processed_rows,
        success_rows=task.success_rows,
        failed_rows=task.failed_rows,
        result_success=task.success_rows,
        result_failed=task.failed_rows,
        error_message=error_reason,
        error_reason=error_reason,
        action_expired=action_expired,
        action_expire_reason=_task_expired_message() if action_expired else None,
        result_summary=task.result_summary,
        started_at=task.started_at,
        finished_at=task.finished_at,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


def is_task_expired(task: ProcessingTask) -> bool:
    created_at = task.created_at
    if created_at is None:
        return False
    now = datetime.now(timezone.utc)
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    return created_at < now - timedelta(days=TASK_ACTION_EXPIRE_DAYS)


def _task_expired_message() -> str:
    return f"任务创建时间超过 {TASK_ACTION_EXPIRE_DAYS} 天，已过期，不能重新提交或重新统计"


async def _load_task_with_file(
    db: AsyncSession,
    *,
    task_id: int,
    current_user: User,
) -> tuple[ProcessingTask, UploadFile] | ApiResponse:
    result = await db.execute(
        select(ProcessingTask, UploadFile)
        .join(UploadFile, ProcessingTask.file_id == UploadFile.id)
        .where(
            ProcessingTask.id == task_id,
            ProcessingTask.is_deleted.is_(False),
            UploadFile.is_deleted.is_(False),
            active_shop_filter(UploadFile.shop_id),
        )
    )
    row = result.one_or_none()
    if row is None:
        return ApiResponse(code=404, message="任务不存在")

    task, upload_file = row
    if current_user.role != "superadmin" and task.org_id != current_user.org_id:
        return ApiResponse(code=403, message="无权访问该任务")
    return task, upload_file


@router.post("/{task_id}/source-download", response_model=ApiResponse[TaskSourceDownloadOut])
async def get_task_source_download(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """获取任务原始上传文件的临时下载链接。"""
    if current_user.role != "superadmin":
        return ApiResponse(code=403, message="仅超级管理员可下载原表")

    loaded = await _load_task_with_file(db, task_id=task_id, current_user=current_user)
    if isinstance(loaded, ApiResponse):
        return loaded

    _task, upload_file = loaded
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
        data=TaskSourceDownloadOut(
            download_url=download_url,
            filename=upload_file.original_name,
            expires_seconds=expires_seconds,
        )
    )


async def _validate_task_action(
    db: AsyncSession,
    *,
    task: ProcessingTask,
    upload_file: UploadFile,
    action: str,
) -> str | None:
    parsed_type = (upload_file.parsed_type or "").strip()
    if task.status == "expired":
        return "源文件已过期或不存在，不能重新提交，请重新上传文件"
    if is_task_expired(task):
        return _task_expired_message()
    if action == "retry":
        if parsed_type == "银行流水":
            if task.status in {"queued", "running"}:
                return "排队中或运行中的银行流水任务不能重新处理"
        elif task.status != "failed":
            return "只有失败任务可以重试"
    if action == "recalculate":
        if task.status in {"queued", "running"}:
            return "排队中或运行中的任务不能重新统计"
    if parsed_type in {"红单", "银行流水"}:
        return None
    if not upload_file.detected_platform:
        return "文件缺少平台信息，无法重新提交" if action == "retry" else "文件缺少平台信息，无法重新统计"

    from app.tasks.processors import PLATFORM_PROCESSORS

    profile = await resolve_platform_profile(db, upload_file.detected_platform)
    if profile.processor_code not in PLATFORM_PROCESSORS:
        return f"未找到平台 [{profile.processor_code}] 的处理器"
    return None


async def _enqueue_task_again(task: ProcessingTask, upload_file: UploadFile, db: AsyncSession) -> None:
    task.status = "queued"
    task.progress = 0
    task.celery_task_id = None
    task.error_message = None
    task.processed_rows = 0
    task.success_rows = 0
    task.failed_rows = 0
    task.result_summary = None
    task.started_at = None
    task.finished_at = None
    upload_file.status = "uploaded"
    upload_file.error_message = None
    upload_file.row_count = 0
    await db.commit()
    await db.refresh(task)

    parsed_type = (upload_file.parsed_type or "").strip()
    if parsed_type == "红单":
        from app.tasks.celery_app import process_merchant_red_sheet

        async_result = process_merchant_red_sheet.delay(
            task_id=task.id,
            file_id=upload_file.id,
            oss_key=upload_file.oss_key,
        )
    elif parsed_type == "银行流水":
        from app.tasks.celery_app import process_merchant_bank_flow

        async_result = process_merchant_bank_flow.delay(
            task_id=task.id,
            file_id=upload_file.id,
            oss_key=upload_file.oss_key,
        )
    else:
        from app.tasks.celery_app import process_file_platform

        async_result = process_file_platform.delay(
            file_id=upload_file.id,
            oss_key=upload_file.oss_key,
            org_id=task.org_id,
            platform_code=upload_file.detected_platform,
            shop_name=upload_file.parsed_shop or "",
            shop_id=upload_file.shop_id,
        )
    task.celery_task_id = async_result.id
    await db.commit()
    await db.refresh(task)


async def _batch_task_action(
    *,
    body: TaskBatchActionIn,
    action: str,
    current_user: User,
    db: AsyncSession,
) -> ApiResponse[TaskBatchActionOut]:
    task_ids = list(dict.fromkeys(body.task_ids))
    if not task_ids:
        return ApiResponse(code=400, message="请选择任务")
    if len(task_ids) > 100:
        return ApiResponse(code=400, message="单次最多操作 100 个任务")

    success_ids: list[int] = []
    failed_items: list[dict[str, object]] = []
    for task_id in task_ids:
        loaded = await _load_task_with_file(db, task_id=task_id, current_user=current_user)
        if isinstance(loaded, ApiResponse):
            failed_items.append({"task_id": task_id, "message": loaded.message})
            continue

        task, upload_file = loaded
        error_message = await _validate_task_action(db, task=task, upload_file=upload_file, action=action)
        if error_message:
            failed_items.append({"task_id": task_id, "message": error_message})
            continue

        await _enqueue_task_again(task, upload_file, db)
        success_ids.append(task.id)

    data = TaskBatchActionOut(
        total=len(task_ids),
        success_count=len(success_ids),
        failed_count=len(failed_items),
        success_ids=success_ids,
        failed_items=failed_items,
    )
    message = "操作完成" if not failed_items else f"成功 {data.success_count} 个，失败 {data.failed_count} 个"
    return ApiResponse(data=data, message=message)


@router.get("/{task_id}", response_model=ApiResponse[TaskOut])
async def get_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """获取任务详情。"""
    result = await db.execute(
        select(ProcessingTask, UploadFile, Shop.shop_color, Organization.name.label("org_name"))
        .join(UploadFile, ProcessingTask.file_id == UploadFile.id)
        .outerjoin(Shop, UploadFile.shop_id == Shop.id)
        .outerjoin(
            Organization,
            and_(Organization.id == ProcessingTask.org_id, Organization.is_deleted.is_(False)),
        )
        .where(
            ProcessingTask.id == task_id,
            ProcessingTask.is_deleted.is_(False),
            UploadFile.is_deleted.is_(False),
            active_shop_filter(UploadFile.shop_id),
        )
    )
    row = result.one_or_none()
    if row is None:
        return ApiResponse(code=404, message="任务不存在")

    task, upload_file, shop_color, org_name = row
    # Scope check
    if current_user.role != "superadmin" and task.org_id != current_user.org_id:
        return ApiResponse(code=403, message="无权访问该任务")

    return ApiResponse(data=build_task_out(task, upload_file, shop_color, org_name))


def build_task_out(
    task: ProcessingTask,
    upload_file: UploadFile,
    shop_color: str | None = None,
    org_name: str | None = None,
) -> TaskOut:
    data = TaskOut.model_validate(task)
    data.org_name = org_name
    data.batch_id = upload_file.batch_id
    data.filename = upload_file.original_name
    data.platform = upload_file.source_platform_code or upload_file.detected_platform
    data.source_platform_code = upload_file.source_platform_code or upload_file.detected_platform
    data.report_platform_code = upload_file.report_platform_code
    data.shop_id = upload_file.shop_id
    data.shop_name = upload_file.parsed_shop
    data.shop_color = shop_color
    data.parsed_type = upload_file.parsed_type
    data.parsed_year = upload_file.parsed_year
    data.parsed_month = upload_file.parsed_month
    data.action_expired = is_task_expired(task)
    data.action_expire_reason = _task_expired_message() if data.action_expired else None
    return data


@router.post("/batch/retry", response_model=ApiResponse[TaskBatchActionOut])
async def batch_retry_tasks(
    body: TaskBatchActionIn,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """批量重试失败任务或重跑银行流水任务。"""
    return await _batch_task_action(body=body, action="retry", current_user=current_user, db=db)


@router.post("/batch/recalculate", response_model=ApiResponse[TaskBatchActionOut])
async def batch_recalculate_tasks(
    body: TaskBatchActionIn,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """批量重新统计任务结果。"""
    return await _batch_task_action(body=body, action="recalculate", current_user=current_user, db=db)


@router.post("/{task_id}/retry", response_model=ApiResponse[TaskOut])
async def retry_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """手动重试单个失败任务或重跑银行流水任务。"""
    loaded = await _load_task_with_file(db, task_id=task_id, current_user=current_user)
    if isinstance(loaded, ApiResponse):
        return loaded

    task, upload_file = loaded
    error_message = await _validate_task_action(db, task=task, upload_file=upload_file, action="retry")
    if error_message:
        return ApiResponse(code=400, message=error_message)

    await _enqueue_task_again(task, upload_file, db)
    return ApiResponse(data=build_task_out(task, upload_file))


@router.post("/{task_id}/recalculate", response_model=ApiResponse[TaskOut])
async def recalculate_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """手动重新统计单个任务。"""
    loaded = await _load_task_with_file(db, task_id=task_id, current_user=current_user)
    if isinstance(loaded, ApiResponse):
        return loaded

    task, upload_file = loaded
    error_message = await _validate_task_action(db, task=task, upload_file=upload_file, action="recalculate")
    if error_message:
        return ApiResponse(code=400, message=error_message)

    await _enqueue_task_again(task, upload_file, db)
    return ApiResponse(data=build_task_out(task, upload_file))


@router.get("/{task_id}/progress", response_model=ApiResponse[TaskProgressOut])
async def get_task_progress(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """获取任务进度信息，供前端轮询刷新。"""
    result = await db.execute(
        select(ProcessingTask)
        .join(UploadFile, ProcessingTask.file_id == UploadFile.id)
        .where(
            ProcessingTask.id == task_id,
            ProcessingTask.is_deleted.is_(False),
            UploadFile.is_deleted.is_(False),
            active_shop_filter(UploadFile.shop_id),
        )
    )
    task = result.scalar_one_or_none()
    if task is None:
        return ApiResponse(code=404, message="任务不存在")

    # Scope check
    if current_user.role != "superadmin" and task.org_id != current_user.org_id:
        return ApiResponse(code=403, message="无权访问该任务")

    return ApiResponse(
        data=TaskProgressOut(
            id=task.id,
            status=task.status,
            progress=task.progress,
            processed_rows=task.processed_rows,
            success_rows=task.success_rows,
            failed_rows=task.failed_rows,
            error_message=task.error_message,
            error_reason=task.error_reason,
        )
    )
