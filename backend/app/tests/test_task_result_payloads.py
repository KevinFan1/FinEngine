from types import SimpleNamespace

import pytest

import app.tasks.bic_accounting as bic_task_module
import app.tasks.reconciliation_checklist as checklist_task_module
import app.tasks.transaction_accounting as transaction_task_module


class _FakeAsyncSession:
    def __init__(self, task) -> None:
        self.task = task
        self.commit_count = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def commit(self) -> None:
        self.commit_count += 1


class _FakeSessionFactory:
    def __init__(self, session) -> None:
        self.session = session

    def __call__(self):
        return self.session


@pytest.mark.asyncio
async def test_run_transaction_accounting_task_returns_result_summary(monkeypatch: pytest.MonkeyPatch) -> None:
    task = SimpleNamespace(
        id=11,
        status="partial_success",
        processed_rows=120,
        success_rows=100,
        failed_rows=20,
        total_rows=120,
        matched_rows=90,
        unmatched_rows=10,
        result_summary={"任务总耗时秒": 22.345, "行处理耗时秒": 10.111},
    )
    session = _FakeAsyncSession(task)

    async def fake_execute_task(db, *, task_id: int):
        assert db is session
        assert task_id == 11
        return task

    monkeypatch.setattr(transaction_task_module, "async_session_factory", _FakeSessionFactory(session))
    monkeypatch.setattr(transaction_task_module.TransactionAccountingService, "execute_task", fake_execute_task)

    payload = await transaction_task_module._run_transaction_accounting_task(11)

    assert payload["任务ID"] == 11
    assert payload["结果摘要"] == {"任务总耗时秒": 22.345, "行处理耗时秒": 10.111}
    assert payload["匹配行数"] == 90
    assert session.commit_count == 1


@pytest.mark.asyncio
async def test_run_bic_accounting_task_returns_result_summary(monkeypatch: pytest.MonkeyPatch) -> None:
    task = SimpleNamespace(
        id=21,
        status="success",
        processed_rows=66,
        success_rows=60,
        failed_rows=6,
        result_summary={"任务总耗时秒": 9.876, "结果入库耗时秒": 1.234},
    )
    session = _FakeAsyncSession(task)

    async def fake_execute_task(db, *, task_id: int):
        assert db is session
        assert task_id == 21
        return task

    monkeypatch.setattr(bic_task_module, "async_session_factory", _FakeSessionFactory(session))
    monkeypatch.setattr(bic_task_module.BicAccountingService, "execute_task", fake_execute_task)

    payload = await bic_task_module._run_bic_accounting_task(21)

    assert payload["任务ID"] == 21
    assert payload["结果摘要"] == {"任务总耗时秒": 9.876, "结果入库耗时秒": 1.234}
    assert payload["处理行数"] == 66
    assert session.commit_count == 1


@pytest.mark.asyncio
async def test_run_reconciliation_checklist_task_returns_result_summary(monkeypatch: pytest.MonkeyPatch) -> None:
    task = SimpleNamespace(
        id=31,
        status="success",
        processed_rows=80,
        success_rows=80,
        failed_rows=0,
        total_rows=80,
        inserted_rows=50,
        updated_rows=20,
        result_summary={"任务总耗时秒": 5.678, "汇总重建耗时秒": 0.456},
    )
    session = _FakeAsyncSession(task)

    async def fake_execute_task(db, *, task_id: int):
        assert db is session
        assert task_id == 31
        return task

    monkeypatch.setattr(checklist_task_module, "async_session_factory", _FakeSessionFactory(session))
    monkeypatch.setattr(checklist_task_module.ReconciliationChecklistService, "execute_task", fake_execute_task)

    payload = await checklist_task_module._run_reconciliation_checklist_task(31)

    assert payload["任务ID"] == 31
    assert payload["结果摘要"] == {"任务总耗时秒": 5.678, "汇总重建耗时秒": 0.456}
    assert payload["新增行数"] == 50
    assert payload["更新行数"] == 20
    assert session.commit_count == 1
