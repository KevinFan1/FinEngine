"""Tasks API — list, detail, and progress query."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import or_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.core.deps import get_current_user
from app.models.task import ProcessingTask
from app.models.upload import UploadFile
from app.models.user import User
from app.schemas.common import ApiResponse, PageResponse
from app.schemas.task import TaskListOut, TaskOut

router = APIRouter()
RECALCULABLE_TYPES = {"动账", "运费险", "bic", "其他服务款"}


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


@router.get("", response_model=ApiResponse[PageResponse[TaskListOut]])
async def list_tasks(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: str | None = Query(None, alias="status"),
    platform: str | None = Query(None),
    shop_id: int | None = Query(None),
    shop_name: str | None = Query(None),
    parsed_type: str | None = Query(None),
    parsed_year: int | None = Query(None),
    parsed_month: int | None = Query(None),
    keyword: str | None = Query(None),
    batch_id: int | None = Query(None),
    org_id: int | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """List processing tasks with pagination and filters."""
    stmt = (
        select(ProcessingTask, UploadFile)
        .join(UploadFile, ProcessingTask.file_id == UploadFile.id)
        .where(ProcessingTask.is_deleted.is_(False), UploadFile.is_deleted.is_(False))
        .order_by(ProcessingTask.id.desc())
    )
    count_stmt = (
        select(func.count())
        .select_from(ProcessingTask)
        .join(UploadFile, ProcessingTask.file_id == UploadFile.id)
        .where(ProcessingTask.is_deleted.is_(False), UploadFile.is_deleted.is_(False))
    )

    # Scope: non-superadmin only sees own org
    if current_user.role != "superadmin":
        stmt = stmt.where(ProcessingTask.org_id == current_user.org_id)
        count_stmt = count_stmt.where(ProcessingTask.org_id == current_user.org_id)
    elif org_id is not None:
        stmt = stmt.where(ProcessingTask.org_id == org_id)
        count_stmt = count_stmt.where(ProcessingTask.org_id == org_id)

    if status_filter:
        stmt = stmt.where(ProcessingTask.status == status_filter)
        count_stmt = count_stmt.where(ProcessingTask.status == status_filter)

    if platform:
        stmt = stmt.where(UploadFile.detected_platform == platform)
        count_stmt = count_stmt.where(UploadFile.detected_platform == platform)

    if shop_id is not None:
        stmt = stmt.where(UploadFile.shop_id == shop_id)
        count_stmt = count_stmt.where(UploadFile.shop_id == shop_id)

    if shop_name:
        stmt = stmt.where(UploadFile.parsed_shop.ilike(f"%{shop_name}%"))
        count_stmt = count_stmt.where(UploadFile.parsed_shop.ilike(f"%{shop_name}%"))

    if parsed_type:
        stmt = stmt.where(UploadFile.parsed_type == parsed_type)
        count_stmt = count_stmt.where(UploadFile.parsed_type == parsed_type)

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

    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0

    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(stmt)
    rows = result.all()

    return ApiResponse(
        data=PageResponse(
            items=[
                build_task_list_out(task, upload_file)
                for task, upload_file in rows
            ],
            total=total,
            page=page,
            page_size=page_size,
        )
    )


def build_task_list_out(task: ProcessingTask, upload_file: UploadFile) -> TaskListOut:
    error_reason = task.error_reason or upload_file.error_message
    return TaskListOut(
        id=task.id,
        file_id=task.file_id,
        batch_id=upload_file.batch_id,
        filename=upload_file.original_name,
        platform=upload_file.detected_platform,
        shop_id=upload_file.shop_id,
        shop_name=upload_file.parsed_shop,
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
        started_at=task.started_at,
        finished_at=task.finished_at,
        created_at=task.created_at,
    )


@router.get("/{task_id}", response_model=ApiResponse[TaskOut])
async def get_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Get task detail."""
    result = await db.execute(select(ProcessingTask).where(ProcessingTask.id == task_id, ProcessingTask.is_deleted.is_(False)))
    task = result.scalar_one_or_none()
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")

    # Scope check
    if current_user.role != "superadmin" and task.org_id != current_user.org_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权访问该任务")

    return ApiResponse(data=TaskOut.model_validate(task))


@router.post("/{task_id}/retry", response_model=ApiResponse[TaskOut])
async def retry_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Manually retry a failed processing task."""
    result = await db.execute(
        select(ProcessingTask, UploadFile)
        .join(UploadFile, ProcessingTask.file_id == UploadFile.id)
        .where(ProcessingTask.id == task_id, ProcessingTask.is_deleted.is_(False), UploadFile.is_deleted.is_(False))
    )
    row = result.one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")

    task, upload_file = row
    if current_user.role != "superadmin" and task.org_id != current_user.org_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权访问该任务")
    if task.status != "failed":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="只有失败任务可以重试")
    if not upload_file.detected_platform:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="文件缺少平台信息，无法重试")

    from app.tasks.processors import PLATFORM_PROCESSORS

    if upload_file.detected_platform not in PLATFORM_PROCESSORS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"未找到平台 [{upload_file.detected_platform}] 的处理器")

    task.status = "queued"
    task.progress = 0
    task.celery_task_id = None
    task.processed_rows = 0
    task.success_rows = 0
    task.failed_rows = 0
    task.error_message = None
    task.result_summary = None
    task.started_at = None
    task.finished_at = None
    upload_file.status = "uploaded"
    upload_file.error_message = None
    await db.commit()
    await db.refresh(task)

    from app.tasks.celery_app import process_file_platform

    process_file_platform.delay(
        file_id=upload_file.id,
        oss_key=upload_file.oss_key,
        org_id=task.org_id,
        platform_code=upload_file.detected_platform,
        shop_name=upload_file.parsed_shop or "",
        shop_id=upload_file.shop_id,
    )

    return ApiResponse(data=TaskOut.model_validate(task))


@router.post("/{task_id}/recalculate", response_model=ApiResponse[TaskOut])
async def recalculate_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Manually recalculate an order-dependent processing task."""
    result = await db.execute(
        select(ProcessingTask, UploadFile)
        .join(UploadFile, ProcessingTask.file_id == UploadFile.id)
        .where(ProcessingTask.id == task_id, ProcessingTask.is_deleted.is_(False), UploadFile.is_deleted.is_(False))
    )
    row = result.one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")

    task, upload_file = row
    if current_user.role != "superadmin" and task.org_id != current_user.org_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权访问该任务")
    if task.status in {"queued", "running"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="排队中或运行中的任务不能重新统计")
    if upload_file.parsed_type not in RECALCULABLE_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="当前文件类型不支持重新统计")
    if not upload_file.detected_platform:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="文件缺少平台信息，无法重新统计")

    from app.tasks.processors import PLATFORM_PROCESSORS

    if upload_file.detected_platform not in PLATFORM_PROCESSORS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"未找到平台 [{upload_file.detected_platform}] 的处理器")

    task.status = "queued"
    task.progress = 0
    task.celery_task_id = None
    task.processed_rows = 0
    task.success_rows = 0
    task.failed_rows = 0
    task.error_message = None
    task.result_summary = None
    task.started_at = None
    task.finished_at = None
    upload_file.status = "uploaded"
    upload_file.error_message = None
    await db.commit()
    await db.refresh(task)

    from app.tasks.celery_app import process_file_platform

    process_file_platform.delay(
        file_id=upload_file.id,
        oss_key=upload_file.oss_key,
        org_id=task.org_id,
        platform_code=upload_file.detected_platform,
        shop_name=upload_file.parsed_shop or "",
        shop_id=upload_file.shop_id,
    )

    return ApiResponse(data=TaskOut.model_validate(task))


@router.get("/{task_id}/progress", response_model=ApiResponse[TaskProgressOut])
async def get_task_progress(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    """Get lightweight task progress — designed for frontend polling.

    Returns only status, progress percentage, and row counts.
    """
    result = await db.execute(select(ProcessingTask).where(ProcessingTask.id == task_id, ProcessingTask.is_deleted.is_(False)))
    task = result.scalar_one_or_none()
    if task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="任务不存在")

    # Scope check
    if current_user.role != "superadmin" and task.org_id != current_user.org_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权访问该任务")

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
