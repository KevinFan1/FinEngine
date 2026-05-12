from datetime import datetime, timedelta, timezone

from app.api.v1.tasks import is_task_expired
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
