from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from app.api.v1.tasks import _load_task_with_file, is_task_expired
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
