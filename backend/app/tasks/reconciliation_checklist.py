"""Celery tasks for the independent reconciliation checklist flow."""

from sqlalchemy import select

from app.core.database import async_session_factory
from app.models.reconciliation_checklist import ReconciliationChecklistTask
from app.services.reconciliation_checklist_service import ReconciliationChecklistService
from app.tasks.celery_app import _build_task_result_payload, _run_async_in_worker, celery_app


@celery_app.task(
    bind=True,
    name="app.tasks.reconciliation_checklist.run_reconciliation_checklist_task",
    max_retries=5,
)
def run_reconciliation_checklist_task(self, task_id: int) -> dict:
    try:
        return _run_async_in_worker(_run_reconciliation_checklist_task(task_id))
    except ValueError as exc:
        if str(exc) == "对账清单任务不存在":
            countdown = min(2 ** self.request.retries, 30)
            raise self.retry(exc=exc, countdown=countdown)
        raise


async def _run_reconciliation_checklist_task(task_id: int) -> dict:
    async with async_session_factory() as db:
        task = await ReconciliationChecklistService.execute_task(db, task_id=task_id)
        await db.commit()
        return _build_task_result_payload(
            task,
            extra={
                "总行数": task.total_rows,
                "新增行数": task.inserted_rows,
                "更新行数": task.updated_rows,
            },
        )


def recover_queued_reconciliation_checklist_tasks(limit: int = 100) -> int:
    return _run_async_in_worker(_recover_queued_reconciliation_checklist_tasks_async(limit=limit))


async def _recover_queued_reconciliation_checklist_tasks_async(limit: int = 100) -> int:
    async with async_session_factory() as db:
        result = await db.execute(
            select(ReconciliationChecklistTask)
            .where(
                ReconciliationChecklistTask.status == "queued",
                ReconciliationChecklistTask.is_deleted.is_(False),
            )
            .order_by(ReconciliationChecklistTask.id.asc())
            .limit(limit)
        )
        tasks = result.scalars().all()
        dispatched = 0
        for task in tasks:
            async_result = run_reconciliation_checklist_task.delay(task.id)
            task.celery_task_id = async_result.id
            dispatched += 1
        await db.commit()
        return dispatched
