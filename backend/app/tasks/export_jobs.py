"""Celery tasks for async export jobs."""

from app.core.database import async_session_factory
from app.services.export_job_service import ExportJobService
from app.tasks.celery_app import _run_async_in_worker, celery_app


@celery_app.task(bind=True, name="app.tasks.export_jobs.run_export_job")
def run_export_job(self, job_id: int) -> dict:
    return _run_async_in_worker(_run_export_job(job_id, celery_task_id=self.request.id))


def recover_queued_export_jobs(limit: int = 100) -> int:
    return _run_async_in_worker(_recover_queued_export_jobs(limit=limit))


async def _run_export_job(job_id: int, *, celery_task_id: str | None = None) -> dict:
    async with async_session_factory() as db:
        await ExportJobService.mark_job_running(db, job_id=job_id, celery_task_id=celery_task_id)
        await db.commit()

        job = await ExportJobService.run_job(db, job_id=job_id, mark_running=False)
        await db.commit()
        return {
            "job_id": job.id,
            "status": job.status,
            "oss_key": job.oss_key,
            "file_size": job.file_size,
        }


async def _recover_queued_export_jobs(limit: int = 100) -> int:
    async with async_session_factory() as db:
        dispatched = await ExportJobService.recover_queued_jobs(db, limit=limit)
        await db.commit()
        return dispatched
