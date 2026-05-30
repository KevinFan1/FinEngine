from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

import app.api.v1.tasks as tasks_api
from app.api.v1.tasks import _load_task_with_file, get_task_source_download, is_task_expired
from app.models.task import ProcessingTask


def test_task_action_expires_after_30_days() -> None:
    task = ProcessingTask(
        id=1,
        file_id=1,
        org_id=1,
        user_id=1,
        created_at=datetime.now(timezone.utc) - timedelta(days=31),
    )

    assert is_task_expired(task) is True


def test_task_action_not_expired_within_30_days() -> None:
    task = ProcessingTask(
        id=1,
        file_id=1,
        org_id=1,
        user_id=1,
        created_at=datetime.now(timezone.utc) - timedelta(days=29),
    )

    assert is_task_expired(task) is False


class _TaskQueryResult:
    def one_or_none(self):
        return None


class _TaskQuerySession:
    def __init__(self) -> None:
        self.statements: list[str] = []

    async def execute(self, statement):
        self.statements.append(str(statement.compile(compile_kwargs={"literal_binds": True})))
        return _TaskQueryResult()


@pytest.mark.asyncio
async def test_task_loader_hides_deleted_shop_uploads() -> None:
    session = _TaskQuerySession()

    await _load_task_with_file(
        session,  # type: ignore[arg-type]
        task_id=1,
        current_user=SimpleNamespace(role="member", org_id=1),  # type: ignore[arg-type]
    )

    statement_text = "\n".join(session.statements)
    assert "fin_upload_files.shop_id IS NULL" in statement_text
    assert "EXISTS" in statement_text
    assert "fin_shops" in statement_text


@pytest.mark.asyncio
async def test_task_source_download_requires_superadmin() -> None:
    response = await get_task_source_download(
        1,
        current_user=SimpleNamespace(role="admin"),
        db=SimpleNamespace(),  # type: ignore[arg-type]
    )

    assert response.code == 403
    assert response.message == "仅超级管理员可下载原表"


@pytest.mark.asyncio
async def test_task_source_download_returns_signed_url_for_superadmin(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_load_task_with_file(*_args, **_kwargs):
        return (
            SimpleNamespace(id=1),
            SimpleNamespace(original_name="原表.xlsx", oss_key="source-key.xlsx"),
        )

    monkeypatch.setattr(tasks_api, "_load_task_with_file", fake_load_task_with_file)

    signed_calls: list[dict[str, object]] = []

    def fake_sign_download_url(key, *, expires_seconds, filename=None):
        signed_calls.append({"key": key, "expires_seconds": expires_seconds, "filename": filename})
        return f"https://oss.test/{key}?e={expires_seconds}"

    monkeypatch.setattr(tasks_api.oss_service, "sign_download_url", fake_sign_download_url)

    response = await get_task_source_download(
        1,
        current_user=SimpleNamespace(role="superadmin"),
        db=SimpleNamespace(),  # type: ignore[arg-type]
    )

    assert response.code == 200
    assert response.data is not None
    assert response.data.download_url == "https://oss.test/source-key.xlsx?e=300"
    assert response.data.filename == "原表.xlsx"
    assert response.data.expires_seconds == 300
    assert signed_calls == [
        {"key": "source-key.xlsx", "expires_seconds": 300, "filename": "原表.xlsx"},
    ]
