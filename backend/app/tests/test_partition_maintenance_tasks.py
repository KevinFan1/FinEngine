from datetime import date

import pytest

import app.services.partition_maintenance_service as partition_service_module
from app.services.partition_maintenance_service import (
    PARTITION_PRECREATE_FUTURE_MONTHS,
    PARTITION_PRECREATE_PAST_MONTHS,
    ensure_reconciliation_checklist_partitions_for_anchor,
)
from app.services.partition_service import month_floor, shift_months
from app.tasks import partition_maintenance as partition_tasks


class _FakeSession:
    def __init__(self) -> None:
        self.commit_count = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def commit(self) -> None:
        self.commit_count += 1


class _FakeSessionFactory:
    def __init__(self, session: _FakeSession) -> None:
        self.session = session

    def __call__(self) -> _FakeSession:
        return self.session


@pytest.mark.asyncio
async def test_ensure_reconciliation_checklist_partitions_for_anchor_uses_precreate_window(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _FakeSession()
    anchor = date(2026, 2, 9)
    captured: dict[str, int] = {}

    async def fake_ensure_window(_db, *, start_period: int, end_period: int) -> dict[str, int]:
        assert _db is session
        captured["start_period"] = start_period
        captured["end_period"] = end_period
        return {"start_period": start_period, "end_period": end_period}

    monkeypatch.setattr(
        partition_service_module,
        "ensure_reconciliation_checklist_partitions_for_window",
        fake_ensure_window,
    )

    result = await ensure_reconciliation_checklist_partitions_for_anchor(
        session,  # type: ignore[arg-type]
        anchor=anchor,
    )

    assert captured == {
        "start_period": shift_months(anchor, -PARTITION_PRECREATE_PAST_MONTHS),
        "end_period": shift_months(anchor, PARTITION_PRECREATE_FUTURE_MONTHS),
    }
    assert result == {
        "start_period": captured["start_period"],
        "end_period": captured["end_period"],
        "base_period": month_floor(anchor),
    }


@pytest.mark.asyncio
async def test_reconciliation_checklist_partition_precreate_task_commits(monkeypatch: pytest.MonkeyPatch) -> None:
    session = _FakeSession()

    async def fake_ensure_partitions(_db, *, anchor=None) -> dict[str, int]:
        assert _db is session
        assert anchor is None
        return {"start_period": 202402, "end_period": 202702, "base_period": 202602}

    monkeypatch.setattr(partition_tasks, "async_session_factory", _FakeSessionFactory(session))
    monkeypatch.setattr(
        partition_tasks,
        "ensure_reconciliation_checklist_partitions_for_anchor",
        fake_ensure_partitions,
    )

    result = await partition_tasks._ensure_reconciliation_checklist_partitions_precreate_task()

    assert result == {"start_period": 202402, "end_period": 202702, "base_period": 202602}
    assert session.commit_count == 1


def test_celery_beat_schedule_registers_checklist_partition_precreate_task() -> None:
    schedule = partition_tasks.celery_app.conf.beat_schedule

    assert "ensure-reconciliation-checklist-partitions-daily" in schedule
    assert schedule["ensure-reconciliation-checklist-partitions-daily"]["task"] == (
        "app.tasks.partition_maintenance.ensure_reconciliation_checklist_partitions_precreate_task"
    )
