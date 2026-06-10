from types import SimpleNamespace

import pytest

from app.core.database import run_after_commit_callbacks
from app.models.export_job import ExportJob
from app.models.user import User
from app.schemas.export_job import ExportJobCreate
from app.services.export_job_service import ExportJobService


class _CreateOnlySession:
    def __init__(self) -> None:
        self.added = []
        self.info = {}
        self._next_id = 100
        self.flushed = 0

    def add(self, instance) -> None:
        self.added.append(instance)

    async def flush(self) -> None:
        self.flushed += 1
        for instance in self.added:
            if getattr(instance, "id", None) is None:
                instance.id = self._next_id
                self._next_id += 1


class _ScalarListResult:
    def __init__(self, rows) -> None:
        self.rows = rows

    def scalars(self):
        rows = self.rows

        class _Scalars:
            @staticmethod
            def all():
                return rows

        return _Scalars()


class _ScalarCountResult:
    def __init__(self, value: int) -> None:
        self.value = value

    def scalar(self):
        return self.value


class _QueuedJobSession:
    def __init__(self, jobs: list[ExportJob]) -> None:
        self.jobs = jobs
        self.executed = []
        self.flushed = 0

    async def execute(self, stmt):
        self.executed.append(stmt)
        return _ScalarListResult(self.jobs)

    async def flush(self) -> None:
        self.flushed += 1


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


@pytest.mark.asyncio
async def test_export_job_dispatch_after_commit_records_celery_id(monkeypatch: pytest.MonkeyPatch) -> None:
    session = _CreateOnlySession()
    user = make_user()
    delay_calls: list[int] = []
    monkeypatch.setattr(
        "app.tasks.export_jobs.run_export_job",
        SimpleNamespace(
            delay=lambda job_id: delay_calls.append(job_id)
            or SimpleNamespace(id=f"export-{job_id}"),
        ),
    )

    job = await ExportJobService.create_job(
        session,  # type: ignore[arg-type]
        data=ExportJobCreate(
            export_type="summary.detail",
            title="汇总明细导出",
            filename="汇总明细.xlsx",
            params={},
        ),
        user=user,
    )
    ExportJobService.dispatch_job_after_commit(session, job)  # type: ignore[arg-type]

    assert job.status == "queued"
    assert job.celery_task_id is None
    assert delay_calls == []

    await run_after_commit_callbacks(session)  # type: ignore[arg-type]

    assert job.celery_task_id == f"export-{job.id}"
    assert delay_calls == [job.id]


@pytest.mark.asyncio
async def test_export_job_dispatch_after_commit_marks_failed_on_broker_error(monkeypatch: pytest.MonkeyPatch) -> None:
    session = _CreateOnlySession()
    user = make_user()
    monkeypatch.setattr(
        "app.tasks.export_jobs.run_export_job",
        SimpleNamespace(delay=lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("worker unavailable"))),
    )

    job = await ExportJobService.create_job(
        session,  # type: ignore[arg-type]
        data=ExportJobCreate(
            export_type="summary.detail",
            title="汇总明细导出",
            filename="汇总明细.xlsx",
            params={},
        ),
        user=user,
    )
    ExportJobService.dispatch_job_after_commit(session, job)  # type: ignore[arg-type]

    await run_after_commit_callbacks(session)  # type: ignore[arg-type]

    assert job.status == "failed"
    assert job.progress == 100
    assert "导出任务投递失败" in (job.error_message or "")


@pytest.mark.asyncio
async def test_export_job_dispatch_unsubmitted_jobs_redelivers_visible_queued_jobs(monkeypatch: pytest.MonkeyPatch) -> None:
    job = ExportJob(
        id=12,
        org_id=9,
        user_id=7,
        module="summary",
        export_type="summary.detail",
        title="汇总明细导出",
        filename="汇总明细.xlsx",
        params={},
        status="queued",
        progress=0,
    )
    session = _QueuedJobSession([job])
    user = make_user()
    delay_calls: list[int] = []
    monkeypatch.setattr(
        "app.tasks.export_jobs.run_export_job",
        SimpleNamespace(
            delay=lambda job_id: delay_calls.append(job_id)
            or SimpleNamespace(id=f"export-{job_id}"),
        ),
    )

    dispatched = await ExportJobService.dispatch_unsubmitted_jobs(
        session,  # type: ignore[arg-type]
        user=user,
    )

    assert dispatched == 1
    assert job.celery_task_id == "export-12"
    assert delay_calls == [12]
    assert session.flushed == 1


@pytest.mark.asyncio
async def test_export_job_dispatch_unsubmitted_jobs_can_scope_superadmin_to_own_jobs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    job = ExportJob(
        id=18,
        org_id=9,
        user_id=7,
        module="summary",
        export_type="summary.detail",
        title="汇总明细导出",
        filename="汇总明细.xlsx",
        params={},
        status="queued",
        progress=0,
    )
    session = _QueuedJobSession([job])
    user = make_user(role="superadmin", org_id=0)
    delay_calls: list[int] = []
    monkeypatch.setattr(
        "app.tasks.export_jobs.run_export_job",
        SimpleNamespace(
            delay=lambda job_id: delay_calls.append(job_id)
            or SimpleNamespace(id=f"export-{job_id}"),
        ),
    )

    dispatched = await ExportJobService.dispatch_unsubmitted_jobs(
        session,  # type: ignore[arg-type]
        user=user,
        mine_only=True,
    )

    assert dispatched == 1
    assert job.celery_task_id == "export-18"
    assert delay_calls == [18]
    statement = str(session.executed[0])
    assert "fin_export_jobs.user_id" in statement
    assert "= :user_id_1" in statement


@pytest.mark.asyncio
async def test_export_job_list_jobs_can_scope_superadmin_to_own_jobs() -> None:
    jobs = [
        ExportJob(
            id=21,
            org_id=9,
            user_id=7,
            module="summary",
            export_type="summary.detail",
            title="我的汇总明细导出",
            filename="mine.xlsx",
            params={},
            status="success",
            progress=100,
        )
    ]

    class _ListJobSession:
        def __init__(self) -> None:
            self.executed = []

        async def execute(self, stmt):
            self.executed.append(stmt)
            if len(self.executed) == 1:
                return _ScalarCountResult(len(jobs))
            return _ScalarListResult(jobs)

    session = _ListJobSession()
    user = make_user(role="superadmin", org_id=0)

    result_jobs, total = await ExportJobService.list_jobs(
        session,  # type: ignore[arg-type]
        user=user,
        mine_only=True,
        page=1,
        page_size=6,
    )

    assert total == 1
    assert result_jobs == jobs
    assert len(session.executed) == 2
    count_statement = str(session.executed[0])
    list_statement = str(session.executed[1])
    assert "fin_export_jobs.user_id" in count_statement
    assert "= :user_id_1" in count_statement
    assert "fin_export_jobs.user_id" in list_statement
    assert "= :user_id_1" in list_statement


@pytest.mark.asyncio
async def test_export_job_mark_running_persists_worker_state() -> None:
    job = ExportJob(
        id=23,
        org_id=9,
        user_id=7,
        module="summary",
        export_type="summary.detail",
        title="汇总明细导出",
        filename="汇总明细.xlsx",
        params={},
        status="queued",
        progress=0,
    )

    class _RunningSession:
        flushed = 0

        async def get(self, model, item_id):
            assert model is ExportJob
            assert item_id == job.id
            return job

        async def flush(self) -> None:
            self.flushed += 1

    session = _RunningSession()

    marked = await ExportJobService.mark_job_running(
        session,  # type: ignore[arg-type]
        job_id=job.id,
        celery_task_id="worker-task-23",
    )

    assert marked is job
    assert job.status == "running"
    assert job.progress == 10
    assert job.celery_task_id == "worker-task-23"
    assert job.started_at is not None
    assert job.error_message is None
    assert session.flushed == 1
