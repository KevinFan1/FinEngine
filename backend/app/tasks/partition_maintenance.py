"""Celery tasks for partition maintenance."""

from app.core.database import async_session_factory
from app.services.partition_maintenance_service import (
    ensure_reconciliation_checklist_partitions_for_anchor,
    ensure_reconciliation_checklist_partitions_for_window,
    ensure_source_partitions_for_window,
)
from app.tasks.celery_app import _run_async_in_worker, celery_app


@celery_app.task(
    bind=True,
    name="app.tasks.partition_maintenance.ensure_source_partitions_task",
    max_retries=3,
)
def ensure_source_partitions_task(self) -> dict:
    return _run_async_in_worker(_ensure_source_partitions_task())


async def _ensure_source_partitions_task() -> dict:
    async with async_session_factory() as db:
        result = await ensure_source_partitions_for_window(db)
        await db.commit()
        return result


@celery_app.task(
    bind=True,
    name="app.tasks.partition_maintenance.ensure_reconciliation_checklist_partitions_task",
    max_retries=3,
)
def ensure_reconciliation_checklist_partitions_task(self, start_period: int, end_period: int) -> dict:
    _ = self
    return _run_async_in_worker(
        _ensure_reconciliation_checklist_partitions_task(
            start_period=start_period,
            end_period=end_period,
        )
    )


async def _ensure_reconciliation_checklist_partitions_task(*, start_period: int, end_period: int) -> dict:
    async with async_session_factory() as db:
        result = await ensure_reconciliation_checklist_partitions_for_window(
            db,
            start_period=start_period,
            end_period=end_period,
        )
        await db.commit()
        return result


@celery_app.task(
    bind=True,
    name="app.tasks.partition_maintenance.ensure_reconciliation_checklist_partitions_precreate_task",
    max_retries=3,
)
def ensure_reconciliation_checklist_partitions_precreate_task(self) -> dict:
    _ = self
    return _run_async_in_worker(_ensure_reconciliation_checklist_partitions_precreate_task())


async def _ensure_reconciliation_checklist_partitions_precreate_task() -> dict:
    async with async_session_factory() as db:
        result = await ensure_reconciliation_checklist_partitions_for_anchor(db)
        await db.commit()
        return result
