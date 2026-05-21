"""Celery tasks for the independent transaction-accounting flow."""

from app.core.database import async_session_factory
from app.services.transaction_accounting_service import TransactionAccountingService
from app.tasks.celery_app import _run_async_in_worker, celery_app


@celery_app.task(name="app.tasks.transaction_accounting.run_transaction_accounting_task")
def run_transaction_accounting_task(task_id: int) -> dict:
    return _run_async_in_worker(_run_transaction_accounting_task(task_id))


async def _run_transaction_accounting_task(task_id: int) -> dict:
    async with async_session_factory() as db:
        task = await TransactionAccountingService.execute_task(db, task_id=task_id)
        await db.commit()
        return {
            "task_id": task.id,
            "status": task.status,
            "total_rows": task.total_rows,
            "matched_rows": task.matched_rows,
            "unmatched_rows": task.unmatched_rows,
            "failed_rows": task.failed_rows,
        }
