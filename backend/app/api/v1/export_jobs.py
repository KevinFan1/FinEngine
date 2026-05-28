"""Async export center API."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session, register_after_commit
from app.core.deps import get_current_user
from app.models.export_job import ExportJob
from app.models.user import User
from app.schemas.common import ApiResponse, PageResponse
from app.schemas.export_job import ExportJobCreate, ExportJobDownloadCredentialOut, ExportJobOut
from app.services.export_job_service import EXPORT_JOB_STATUSES, ExportJobService

router = APIRouter()


async def _load_operator_name_map(db: AsyncSession, user_ids: set[int]) -> dict[int, str]:
    if not user_ids:
        return {}
    result = await db.execute(
        select(User.id, User.display_name, User.username).where(User.id.in_(user_ids), User.is_deleted.is_(False))
    )
    return {
        user_id: display_name or username or f"用户#{user_id}"
        for user_id, display_name, username in result.all()
    }


@router.post("", response_model=ApiResponse[ExportJobOut])
async def create_export_job(
    body: ExportJobCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    try:
        job = await ExportJobService.create_job(db, data=body, user=current_user)
        register_after_commit(db, lambda: ExportJobService.dispatch_job_by_id(job.id))
    except ValueError as exc:
        return ApiResponse(code=400, message=str(exc))
    return ApiResponse(
        data=ExportJobOut.model_validate(job).model_copy(update={"operator_name": current_user.display_name}),
        message="已加入下载中心",
    )


@router.get("", response_model=ApiResponse[PageResponse[ExportJobOut]])
async def list_export_jobs(
    status: str | None = Query(None),
    module: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    if status and status not in EXPORT_JOB_STATUSES:
        return ApiResponse(code=400, message="导出状态不正确")
    jobs, total = await ExportJobService.list_jobs(
        db,
        user=current_user,
        status=status,
        module=module,
        page=page,
        page_size=page_size,
    )
    operator_name_map = await _load_operator_name_map(db, {job.user_id for job in jobs})
    return ApiResponse(
        data=PageResponse(
            items=[
                ExportJobOut.model_validate(job).model_copy(
                    update={"operator_name": operator_name_map.get(job.user_id, f"用户#{job.user_id}")}
                )
                for job in jobs
            ],
            total=total,
            page=page,
            page_size=page_size,
        )
    )


@router.get("/{job_id}", response_model=ApiResponse[ExportJobOut])
async def get_export_job(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    job = await ExportJobService.get_job_for_user(db, job_id=job_id, user=current_user)
    if job is None:
        return ApiResponse(code=404, message="导出任务不存在或无权访问")
    operator_name_map = await _load_operator_name_map(db, {job.user_id})
    return ApiResponse(
        data=ExportJobOut.model_validate(job).model_copy(
            update={"operator_name": operator_name_map.get(job.user_id, f"用户#{job.user_id}")}
        )
    )


@router.post("/{job_id}/download-credential", response_model=ApiResponse[ExportJobDownloadCredentialOut])
async def get_export_download_credential(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_session),
):
    job = await ExportJobService.get_job_for_user(db, job_id=job_id, user=current_user)
    if job is None:
        return ApiResponse(code=404, message="导出任务不存在或无权访问")
    try:
        data = ExportJobService.download_sts(job)
    except ValueError as exc:
        return ApiResponse(code=400, message=str(exc))
    return ApiResponse(data=ExportJobDownloadCredentialOut(**data))
