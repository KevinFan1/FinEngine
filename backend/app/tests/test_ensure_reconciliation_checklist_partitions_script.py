from __future__ import annotations

import pytest

from scripts import ensure_reconciliation_checklist_partitions as script_module


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
async def test_script_defaults_to_anchor_precreate_window(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    session = _FakeSession()

    async def fake_ensure_anchor(_db):
        assert _db is session
        return {"start_period": 202302, "end_period": 202702, "base_period": 202602}

    monkeypatch.setattr(script_module, "async_session_factory", _FakeSessionFactory(session))
    monkeypatch.setattr(
        script_module,
        "ensure_reconciliation_checklist_partitions_for_anchor",
        fake_ensure_anchor,
    )
    monkeypatch.setattr(script_module, "ensure_reconciliation_checklist_partitions_for_window", None)
    monkeypatch.setattr(
        script_module.argparse.ArgumentParser,
        "parse_args",
        lambda self: self.parse_known_args([])[0],
    )

    await script_module.main()

    output = capsys.readouterr().out
    assert "已创建对账清单分区窗口: 202302 ~ 202702 (base=202602)" in output
    assert session.commit_count == 1


@pytest.mark.asyncio
async def test_script_supports_manual_window(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    session = _FakeSession()

    async def fake_ensure_window(_db, *, start_period: int, end_period: int):
        assert _db is session
        assert start_period == 202601
        assert end_period == 202612
        return {"start_period": start_period, "end_period": end_period}

    monkeypatch.setattr(script_module, "async_session_factory", _FakeSessionFactory(session))
    monkeypatch.setattr(script_module, "ensure_reconciliation_checklist_partitions_for_anchor", None)
    monkeypatch.setattr(
        script_module,
        "ensure_reconciliation_checklist_partitions_for_window",
        fake_ensure_window,
    )
    monkeypatch.setattr(
        script_module.argparse.ArgumentParser,
        "parse_args",
        lambda self: self.parse_known_args(["--start", "202601", "--end", "202612"])[0],
    )

    await script_module.main()

    output = capsys.readouterr().out
    assert "已创建对账清单分区窗口: 202601 ~ 202612" in output
    assert session.commit_count == 1


@pytest.mark.asyncio
async def test_script_rejects_half_manual_window(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        script_module.argparse.ArgumentParser,
        "parse_args",
        lambda self: self.parse_known_args(["--start", "202601"])[0],
    )

    with pytest.raises(SystemExit, match="必须同时提供 --start 和 --end，或者都不提供"):
        await script_module.main()
