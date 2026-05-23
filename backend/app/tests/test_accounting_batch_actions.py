from types import SimpleNamespace

import pytest

from app.api.v1.bic_accounting import BicTaskBatchActionIn, batch_recalculate_tasks as batch_recalculate_bic_tasks
from app.api.v1.transaction_accounting import (
    TransactionTaskBatchActionIn,
    batch_recalculate_tasks as batch_recalculate_transaction_tasks,
)
from app.models.bic_accounting import BicTask
from app.models.transaction_accounting import TransactionTask
from app.models.user import User
from app.services.bic_accounting_service import BicAccountingService
from app.services.transaction_accounting_service import TransactionAccountingService


def make_user(*, user_id: int = 7, org_id: int = 9, role: str = "org_admin") -> User:
    return User(
        id=user_id,
        org_id=org_id,
        username=f"user{user_id}",
        phone=f"1390000{user_id:04d}",
        password_hash="hash",
        display_name=f"用户{user_id}",
        role=role,
        status=1,
    )


def make_request():
    return SimpleNamespace(
        client=SimpleNamespace(host="127.0.0.1"),
        headers={"user-agent": "pytest"},
    )


class _TaskLookupSession:
    def __init__(self, tasks: dict[int, object]) -> None:
        self.tasks = tasks

    async def get(self, _model, item_id: int):
        return self.tasks.get(item_id)


@pytest.mark.asyncio
async def test_transaction_batch_recalculate_skips_running_tasks(monkeypatch: pytest.MonkeyPatch) -> None:
    user = make_user()
    runnable = TransactionTask(id=1, file_id=11, org_id=user.org_id, user_id=user.id, status="success")
    running = TransactionTask(id=2, file_id=12, org_id=user.org_id, user_id=user.id, status="processing")
    session = _TaskLookupSession({1: runnable, 2: running})
    rerun_ids: list[int] = []

    async def fake_rerun_task(*_args, task_id: int, **_kwargs):
        rerun_ids.append(task_id)
        return session.tasks[task_id]

    monkeypatch.setattr(TransactionAccountingService, "rerun_task", staticmethod(fake_rerun_task))

    response = await batch_recalculate_transaction_tasks(
        TransactionTaskBatchActionIn(task_ids=[1, 2]),
        make_request(),
        current_user=user,
        _admin=user,
        db=session,  # type: ignore[arg-type]
    )

    assert response.data.success_ids == [1]
    assert response.data.failed_count == 1
    assert response.data.failed_items[0]["task_id"] == 2
    assert "不能重新统计" in str(response.data.failed_items[0]["message"])
    assert rerun_ids == [1]


@pytest.mark.asyncio
async def test_bic_batch_recalculate_skips_running_tasks(monkeypatch: pytest.MonkeyPatch) -> None:
    user = make_user()
    runnable = BicTask(id=1, file_id=11, org_id=user.org_id, user_id=user.id, status="failed")
    queued = BicTask(id=2, file_id=12, org_id=user.org_id, user_id=user.id, status="queued")
    session = _TaskLookupSession({1: runnable, 2: queued})
    rerun_ids: list[int] = []

    async def fake_rerun_task(*_args, task_id: int, **_kwargs):
        rerun_ids.append(task_id)
        return session.tasks[task_id]

    monkeypatch.setattr(BicAccountingService, "rerun_task", staticmethod(fake_rerun_task))

    response = await batch_recalculate_bic_tasks(
        BicTaskBatchActionIn(task_ids=[1, 2]),
        make_request(),
        current_user=user,
        _admin=user,
        db=session,  # type: ignore[arg-type]
    )

    assert response.data.success_ids == [1]
    assert response.data.failed_count == 1
    assert response.data.failed_items[0]["task_id"] == 2
    assert "不能重新统计" in str(response.data.failed_items[0]["message"])
    assert rerun_ids == [1]
