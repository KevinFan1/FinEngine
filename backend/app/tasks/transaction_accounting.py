"""Celery tasks for the independent transaction-accounting flow."""

from app.core.database import async_session_factory
from app.services.transaction_accounting_service import TransactionAccountingService
from app.tasks.celery_app import _build_task_result_payload, _run_async_in_worker, celery_app


@celery_app.task(
    bind=True,
    name="app.tasks.transaction_accounting.run_transaction_accounting_task",
    max_retries=5,
)
def run_transaction_accounting_task(self, task_id: int) -> dict:
    try:
        return _run_async_in_worker(_run_transaction_accounting_task(task_id))
    except ValueError as exc:
        if str(exc) == "动账核算任务不存在":
            countdown = min(2 ** self.request.retries, 30)
            raise self.retry(exc=exc, countdown=countdown)
        raise


async def _run_transaction_accounting_task(task_id: int) -> dict:
    async with async_session_factory() as db:
        task = await TransactionAccountingService.execute_task(db, task_id=task_id)
        await db.commit()
        return _build_task_result_payload(
            task,
            extra={
                "总行数": task.total_rows,
                "匹配行数": task.matched_rows,
                "未匹配行数": task.unmatched_rows,
            },
        )


def recover_queued_transaction_tasks(limit: int = 100) -> int:
    return _run_async_in_worker(_recover_queued_transaction_tasks_async(limit=limit))


async def _recover_queued_transaction_tasks_async(limit: int = 100) -> int:
    from sqlalchemy import select

    from app.models.transaction_accounting import TransactionTask

    async with async_session_factory() as db:
        result = await db.execute(
            select(TransactionTask)
            .where(
                TransactionTask.status == "queued",
                TransactionTask.is_deleted.is_(False),
            )
            .order_by(TransactionTask.id.asc())
            .limit(limit)
        )
        tasks = result.scalars().all()
        dispatched = 0
        for task in tasks:
            async_result = run_transaction_accounting_task.delay(task.id)
            task.celery_task_id = async_result.id
            dispatched += 1
        await db.commit()
        return dispatched
