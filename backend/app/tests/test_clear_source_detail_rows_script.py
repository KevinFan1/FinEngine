from __future__ import annotations

import pytest

from scripts import clear_source_detail_rows as script_module


class _FakeResult:
    def __init__(self, *, scalar_value: int | None = None, rowcount: int = 0) -> None:
        self._scalar_value = scalar_value
        self.rowcount = rowcount

    def scalar(self) -> int | None:
        return self._scalar_value


class _FakeSession:
    def __init__(self, *, dongzhang_count: int, bic_count: int) -> None:
        self.commit_count = 0
        self.rollback_count = 0
        self.executed: list[tuple[str, dict[str, object]]] = []
        self._dongzhang_count = dongzhang_count
        self._bic_count = bic_count

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def execute(self, statement: object, params: dict[str, object] | None = None) -> _FakeResult:
        sql = str(statement)
        bind_params = dict(params or {})
        self.executed.append((sql, bind_params))

        if "SELECT COUNT(*)" in sql:
            if "fin_douyin_dongzhang_details" in sql:
                return _FakeResult(scalar_value=self._dongzhang_count)
            if "fin_bic_source_rows" in sql:
                return _FakeResult(scalar_value=self._bic_count)
            raise AssertionError(f"unexpected count SQL: {sql}")

        if "DELETE FROM fin_douyin_dongzhang_details" in sql:
            return _FakeResult(rowcount=self._dongzhang_count)
        if "DELETE FROM fin_bic_source_rows" in sql:
            return _FakeResult(rowcount=self._bic_count)
        if "TRUNCATE TABLE fin_douyin_dongzhang_details" in sql:
            return _FakeResult()
        if "TRUNCATE TABLE fin_bic_source_rows" in sql:
            return _FakeResult()
        raise AssertionError(f"unexpected SQL: {sql}")

    async def commit(self) -> None:
        self.commit_count += 1

    async def rollback(self) -> None:
        self.rollback_count += 1


class _FakeSessionFactory:
    def __init__(self, session: _FakeSession) -> None:
        self.session = session

    def __call__(self) -> _FakeSession:
        return self.session


@pytest.mark.asyncio
async def test_script_requires_all_or_before_days(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        script_module.argparse.ArgumentParser,
        "parse_args",
        lambda self: self.parse_known_args([])[0],
    )

    with pytest.raises(SystemExit):
        await script_module.main()


@pytest.mark.asyncio
async def test_script_dry_run_reports_counts_without_deleting(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    session = _FakeSession(dongzhang_count=12, bic_count=34)
    monkeypatch.setattr(script_module, "async_session_factory", _FakeSessionFactory(session))
    monkeypatch.setattr(
        script_module.argparse.ArgumentParser,
        "parse_args",
        lambda self: self.parse_known_args(["--all", "--dry-run"])[0],
    )

    await script_module.main()

    output = capsys.readouterr().out
    assert "目标表=动账明细 待清理行数=12" in output
    assert "目标表=BIC源数据 待清理行数=34" in output
    assert "演练模式，未执行实际删除" in output
    assert session.commit_count == 0
    assert session.rollback_count == 1
    assert all("TRUNCATE TABLE" not in sql and "DELETE FROM" not in sql for sql, _ in session.executed)


@pytest.mark.asyncio
async def test_script_truncates_all_selected_targets(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    session = _FakeSession(dongzhang_count=120, bic_count=45)
    monkeypatch.setattr(script_module, "async_session_factory", _FakeSessionFactory(session))
    monkeypatch.setattr(
        script_module.argparse.ArgumentParser,
        "parse_args",
        lambda self: self.parse_known_args(["--all"])[0],
    )

    await script_module.main()

    output = capsys.readouterr().out
    assert "源数据清理完成" in output
    assert "清理总行数=165" in output
    assert session.commit_count == 1
    assert session.rollback_count == 0
    executed_sql = "\n".join(sql for sql, _ in session.executed)
    assert "TRUNCATE TABLE fin_douyin_dongzhang_details" in executed_sql
    assert "TRUNCATE TABLE fin_bic_source_rows" in executed_sql


@pytest.mark.asyncio
async def test_script_can_delete_bic_rows_by_age_only(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    session = _FakeSession(dongzhang_count=9, bic_count=17)
    monkeypatch.setattr(script_module, "async_session_factory", _FakeSessionFactory(session))
    monkeypatch.setattr(
        script_module.argparse.ArgumentParser,
        "parse_args",
        lambda self: self.parse_known_args(["--target", "bic", "--before-days", "30"])[0],
    )

    await script_module.main()

    output = capsys.readouterr().out
    assert "目标表=BIC源数据" in output
    assert "按创建时间清理 30 天前数据" in output
    assert "已清理 BIC源数据 17 行" in output
    assert session.commit_count == 1
    assert session.rollback_count == 0
    executed_sql = "\n".join(sql for sql, _ in session.executed)
    assert "DELETE FROM fin_bic_source_rows" in executed_sql
    assert "fin_douyin_dongzhang_details" not in executed_sql
    delete_params = [params for sql, params in session.executed if "DELETE FROM fin_bic_source_rows" in sql]
    assert delete_params == [{"before_days": 30}]


@pytest.mark.asyncio
async def test_script_can_delete_dongzhang_rows_by_single_period(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    session = _FakeSession(dongzhang_count=23, bic_count=0)
    monkeypatch.setattr(script_module, "async_session_factory", _FakeSessionFactory(session))
    monkeypatch.setattr(
        script_module.argparse.ArgumentParser,
        "parse_args",
        lambda self: self.parse_known_args(["--target", "dongzhang", "--period", "202604"])[0],
    )

    await script_module.main()

    output = capsys.readouterr().out
    assert "按年月清理 202604" in output
    assert "已清理 动账明细 23 行" in output
    executed_sql = "\n".join(sql for sql, _ in session.executed)
    assert "DELETE FROM fin_douyin_dongzhang_details" in executed_sql
    assert "source_period = :period_start" in executed_sql
    delete_params = [params for sql, params in session.executed if "DELETE FROM fin_douyin_dongzhang_details" in sql]
    assert delete_params == [{"period_start": 202604}]


@pytest.mark.asyncio
async def test_script_dry_run_supports_period_range(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    session = _FakeSession(dongzhang_count=8, bic_count=11)
    monkeypatch.setattr(script_module, "async_session_factory", _FakeSessionFactory(session))
    monkeypatch.setattr(
        script_module.argparse.ArgumentParser,
        "parse_args",
        lambda self: self.parse_known_args(["--period-start", "202604", "--period-end", "202606", "--dry-run"])[0],
    )

    await script_module.main()

    output = capsys.readouterr().out
    assert "按年月范围清理 202604 ~ 202606" in output
    assert "演练模式，未执行实际删除" in output
    count_calls = [(sql, params) for sql, params in session.executed if "SELECT COUNT(*)" in sql]
    assert len(count_calls) == 2
    assert all(params == {"period_start": 202604, "period_end": 202606} for _, params in count_calls)
    assert any("source_period BETWEEN :period_start AND :period_end" in sql for sql, _ in count_calls)
    assert any("accounting_period BETWEEN :period_start AND :period_end" in sql for sql, _ in count_calls)
