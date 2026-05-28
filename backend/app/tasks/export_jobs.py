"""Celery tasks for async export jobs."""

from app.core.database import async_session_factory
from app.services.export_job_service import ExportJobService
from app.tasks.celery_app import _run_async_in_worker, celery_app


@celery_app.task(bind=True, name="app.tasks.export_jobs.run_export_job")
def run_export_job(self, job_id: int) -> dict:
    return _run_async_in_worker(_run_export_job(job_id))


async def _run_export_job(job_id: int) -> dict:
    async with async_session_factory() as db:
        job = await ExportJobService.run_job(db, job_id=job_id)
        await db.commit()
        return {
            "job_id": job.id,
            "status": job.status,
            "oss_key": job.oss_key,
            "file_size": job.file_size,
        }
