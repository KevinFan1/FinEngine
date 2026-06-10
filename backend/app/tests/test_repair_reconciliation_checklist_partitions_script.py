from __future__ import annotations

import pytest

from scripts import repair_reconciliation_checklist_partitions as script_module


class _FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def fetchall(self):
        return self._rows


class _FakeSession:
    def __init__(self) -> None:
        self.commit_count = 0
        self.statements: list[str] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def commit(self) -> None:
        self.commit_count += 1

    async def execute(self, statement, params=None):
        self.statements.append(str(statement))
        _ = params
        if "FROM pg_inherits i" in str(statement):
            return _FakeResult([("fin_reconciliation_checklist_payable_balance_summary_rows_20260",)])
        return _FakeResult([])


class _FakeSessionFactory:
    def __init__(self, session: _FakeSession) -> None:
        self.session = session

    def __call__(self) -> _FakeSession:
        return self.session


@pytest.mark.asyncio
async def test_repair_script_drops_mismatched_partitions_and_rebuilds_window(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    session = _FakeSession()

    async def fake_ensure_window(_db, *, start_period: int, end_period: int):
        assert _db is session
        assert start_period == 202601
        assert end_period == 202602
        return {"start_period": start_period, "end_period": end_period}

    monkeypatch.setattr(script_module, "async_session_factory", _FakeSessionFactory(session))
    monkeypatch.setattr(script_module, "ensure_reconciliation_checklist_partitions_for_window", fake_ensure_window)
    monkeypatch.setattr(
        script_module.argparse.ArgumentParser,
        "parse_args",
        lambda self: self.parse_known_args(["--start", "202601", "--end", "202602"])[0],
    )

    await script_module.main()

    output = capsys.readouterr().out
    assert 'DROP TABLE IF EXISTS "fin_reconciliation_checklist_payable_balance_summary_rows_20260" CASCADE' in "\n".join(session.statements)
    assert "已清理旧分区:" in output
    assert "已修复并重建对账清单分区窗口: 202601 ~ 202602" in output
    assert session.commit_count == 1
