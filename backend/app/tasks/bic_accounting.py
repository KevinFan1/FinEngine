"""Celery tasks for the independent BIC accounting flow."""

from sqlalchemy import select

from app.core.database import async_session_factory
from app.models.bic_accounting import BicTask
from app.services.bic_accounting_service import BicAccountingService
from app.tasks.celery_app import _run_async_in_worker, celery_app


@celery_app.task(
    bind=True,
    name="app.tasks.bic_accounting.run_bic_accounting_task",
    max_retries=5,
)
def run_bic_accounting_task(self, task_id: int) -> dict:
    try:
        return _run_async_in_worker(_run_bic_accounting_task(task_id))
    except ValueError as exc:
        if str(exc) == "BIC任务不存在":
            countdown = min(2 ** self.request.retries, 30)
            raise self.retry(exc=exc, countdown=countdown)
        raise


async def _run_bic_accounting_task(task_id: int) -> dict:
    async with async_session_factory() as db:
        task = await BicAccountingService.execute_task(db, task_id=task_id)
        await db.commit()
        return {
            "task_id": task.id,
            "status": task.status,
            "processed_rows": task.processed_rows,
            "success_rows": task.success_rows,
            "failed_rows": task.failed_rows,
        }


def recover_queued_bic_tasks(limit: int = 100) -> int:
    return _run_async_in_worker(_recover_queued_bic_tasks_async(limit=limit))


async def _recover_queued_bic_tasks_async(limit: int = 100) -> int:
    async with async_session_factory() as db:
        result = await db.execute(
            select(BicTask)
            .where(
                BicTask.status == "queued",
                BicTask.is_deleted.is_(False),
            )
            .order_by(BicTask.id.asc())
            .limit(limit)
        )
        tasks = result.scalars().all()
        dispatched = 0
        for task in tasks:
            async_result = run_bic_accounting_task.delay(task.id)
            task.celery_task_id = async_result.id
            dispatched += 1
        await db.commit()
        return dispatched
