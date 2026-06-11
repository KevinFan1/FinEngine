from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.core.database import run_after_commit_callbacks
from app.models.bic_accounting import BicTask, BicUploadFile
from app.models.reconciliation_checklist import ReconciliationChecklistTask, ReconciliationChecklistUploadFile
from app.models.task import ProcessingTask
from app.models.transaction_accounting import TransactionTask, TransactionUploadFile
from app.models.upload import UploadBatch, UploadFile
from app.models.user import User
from app.services import upload_service as upload_service_module
from app.services.bic_accounting_service import BicAccountingService
from app.services.reconciliation_checklist_service import ReconciliationChecklistService
from app.services.transaction_accounting_service import (
    TransactionAccountingService,
)
from app.services.upload_service import UploadService


def make_user(*, user_id: int, org_id: int | None, role: str = "org_admin") -> User:
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


class _CreateOnlySession:
    def __init__(self) -> None:
        self.added = []
        self._next_id = 100
        self.executed = []
        self.info = {}

    def add(self, instance) -> None:
        self.added.append(instance)

    async def execute(self, stmt):
        self.executed.append(stmt)

        class _Result:
            @staticmethod
            def scalar_one_or_none():
                return None

            @staticmethod
            def scalars():
                class _Scalars:
                    @staticmethod
                    def first():
                        return None

                return _Scalars()

        return _Result()

    async def flush(self) -> None:
        for instance in self.added:
            if getattr(instance, "id", None) is None:
                instance.id = self._next_id
                self._next_id += 1

    async def refresh(self, _instance) -> None:
        return None


class _ScalarResult:
    def __init__(self, value=None) -> None:
        self.value = value

    def scalar_one_or_none(self):
        return self.value

    def scalars(self):
        value = self.value

        class _Scalars:
            @staticmethod
            def first():
                return value

        return _Scalars()


@pytest.mark.asyncio
async def test_transaction_accounting_init_upload_uses_current_period_oss_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _CreateOnlySession()
    user = make_user(user_id=7, org_id=9)

    async def fake_get_or_create_shop(*_args, **_kwargs):
        return SimpleNamespace(id=12, shop_name="云上叙珍珠臻品店")

    class _FixedDatetime:
        @staticmethod
        def now():
            return datetime(2026, 6, 11, 14, 30)

    monkeypatch.setattr(
        "app.services.transaction_accounting_service.ShopService.get_or_create_shop",
        fake_get_or_create_shop,
    )
    monkeypatch.setattr("app.services.transaction_accounting_service.datetime", _FixedDatetime)

    upload_file = await TransactionAccountingService.init_upload(
        session,  # type: ignore[arg-type]
        data=SimpleNamespace(
            original_name="26年04月_动账_云上叙珍珠臻品店.xlsx",
            file_size=12345,
            platform_code="douyin",
            shop_name="云上叙珍珠臻品店",
            accounting_year=None,
            accounting_month=None,
        ),
        user=user,
        org_id=9,
    )

    assert upload_file.oss_key == "upload/dongzhang/202606/100_26年04月_动账_云上叙珍珠臻品店.xlsx"


class _ExistingBusinessSession(_CreateOnlySession):
    def __init__(self, *, existing_upload: TransactionUploadFile) -> None:
        super().__init__()
        self.existing_upload = existing_upload

    async def execute(self, stmt):
        self.executed.append(stmt)
        statement = str(stmt)
        if "WHERE fin_transaction_upload_files.org_id" in statement:
            return _ScalarResult(self.existing_upload)
        return _ScalarResult(None)


class _ExistingBicBusinessSession(_CreateOnlySession):
    def __init__(self, *, existing_upload: BicUploadFile) -> None:
        super().__init__()
        self.existing_upload = existing_upload

    async def execute(self, stmt):
        self.executed.append(stmt)
        statement = str(stmt)
        if "WHERE fin_bic_upload_files.org_id" in statement:
            return _ScalarResult(self.existing_upload)
        return _ScalarResult(None)


class _ExistingChecklistSourceSession(_CreateOnlySession):
    def __init__(self, *, existing_upload: ReconciliationChecklistUploadFile, existing_task: ReconciliationChecklistTask | None = None) -> None:
        super().__init__()
        self.existing_upload = existing_upload
        self.existing_task = existing_task

    async def execute(self, stmt):
        self.executed.append(stmt)
        statement = str(stmt)
        if "WHERE fin_reconciliation_checklist_upload_files.source_upload_file_id" in statement:
            return _ScalarResult(self.existing_upload)
        if "WHERE fin_reconciliation_checklist_tasks.file_id" in statement:
            return _ScalarResult(self.existing_task)
        return _ScalarResult(None)


class _RerunSession:
    def __init__(self, *, task: TransactionTask, upload_file: TransactionUploadFile) -> None:
        self.task = task
        self.upload_file = upload_file
        self.added = []
        self.executed = []
        self._next_id = 700
        self.info = {}

    def add(self, instance) -> None:
        self.added.append(instance)

    async def get(self, model, item_id):
        if item_id == getattr(self.task, "id", None) and model is self.task.__class__:
            return self.task
        if item_id == getattr(self.upload_file, "id", None) and model is self.upload_file.__class__:
            return self.upload_file
        return None

    async def execute(self, stmt):
        self.executed.append(stmt)
        return _ScalarResult(None)

    async def flush(self) -> None:
        for instance in self.added:
            if getattr(instance, "id", None) is None:
                instance.id = self._next_id
                self._next_id += 1

    async def refresh(self, _instance) -> None:
        return None


def make_shared_upload(
    *,
    upload_id: int,
    parsed_type: str,
    source_platform_code: str = "douyin",
) -> UploadFile:
    return UploadFile(
        id=upload_id,
        batch_id=1,
        org_id=9,
        user_id=7,
        shop_id=12,
        original_name=f"26年02月_{parsed_type}_抖音旗舰店.xlsx",
        oss_key=f"user-upload/test/{upload_id}.xlsx",
        file_size=12345,
        file_hash="abc123",
        parsed_year=2026,
        parsed_month=2,
        parsed_type=parsed_type,
        parsed_shop="抖音旗舰店",
        detected_platform="douyin",
        source_platform_code=source_platform_code,
        report_platform_code="douyin",
        processor_code="douyin",
        order_scope_code="douyin",
        status="uploaded",
    )


def test_upload_file_size_label_uses_real_binary_units() -> None:
    assert upload_service_module._format_file_size(40 * 1024 * 1024) == "40.00 MB"
    assert upload_service_module._format_file_size(4096) == "4.00 KB"


def test_internal_only_shared_upload_detector_matches_douyin_dongzhang_and_bic() -> None:
    assert upload_service_module._is_internal_only_shared_upload(
        platform_code="douyin",
        parsed_type="动账",
    )
    assert upload_service_module._is_internal_only_shared_upload(
        platform_code="douyin",
        parsed_type="bic",
    )
    assert not upload_service_module._is_internal_only_shared_upload(
        platform_code="douyin",
        parsed_type="对账清单",
    )
    assert not upload_service_module._is_internal_only_shared_upload(
        platform_code="kuaishou",
        parsed_type="动账",
    )


@pytest.mark.asyncio
async def test_transaction_accounting_creates_independent_records_from_shared_upload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _CreateOnlySession()
    user = make_user(user_id=7, org_id=9)
    shared_upload = make_shared_upload(upload_id=21, parsed_type="动账")
    delay_calls: list[int] = []

    async def fake_log(*args, **kwargs):
        return None

    monkeypatch.setattr(
        "app.services.audit_service.AuditService.log",
        fake_log,
    )
    monkeypatch.setattr(
        "app.tasks.transaction_accounting.run_transaction_accounting_task",
        SimpleNamespace(
            delay=lambda task_id: delay_calls.append(task_id)
            or SimpleNamespace(id=f"txn-{task_id}"),
        ),
    )

    task = await TransactionAccountingService.create_from_shared_upload(
        session,  # type: ignore[arg-type]
        upload_file=shared_upload,
        user=user,
    )

    derived_upload = next(
        item
        for item in session.added
        if item.__class__.__name__ == "TransactionUploadFile"
    )
    assert derived_upload.source_upload_file_id == shared_upload.id
    assert derived_upload.shop_id == shared_upload.shop_id
    assert derived_upload.oss_key == shared_upload.oss_key
    assert derived_upload.original_name == shared_upload.original_name
    assert task.file_id == derived_upload.id
    assert task.org_id == shared_upload.org_id
    assert task.celery_task_id is None
    assert delay_calls == []

    await run_after_commit_callbacks(session)  # type: ignore[arg-type]

    assert task.celery_task_id == f"txn-{task.id}"
    assert delay_calls == [task.id]


@pytest.mark.asyncio
async def test_transaction_accounting_reupload_creates_new_records_for_same_business_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    existing_upload = TransactionUploadFile(
        id=77,
        org_id=9,
        user_id=7,
        shop_id=12,
        source_upload_file_id=21,
        original_name="26年02月_动账_抖音旗舰店.xlsx",
        oss_key="old-key.xlsx",
        platform_code="douyin",
        shop_name="抖音旗舰店",
        accounting_year=2026,
        accounting_month=2,
        status="processed",
    )
    session = _ExistingBusinessSession(existing_upload=existing_upload)
    user = make_user(user_id=7, org_id=9)
    shared_upload = make_shared_upload(upload_id=22, parsed_type="动账")

    async def fake_log(*args, **kwargs):
        return None

    monkeypatch.setattr(
        "app.services.audit_service.AuditService.log",
        fake_log,
    )

    task = await TransactionAccountingService.create_from_shared_upload(
        session,  # type: ignore[arg-type]
        upload_file=shared_upload,
        user=user,
    )

    derived_upload = next(
        item
        for item in session.added
        if item.__class__.__name__ == "TransactionUploadFile"
    )
    assert derived_upload.id != existing_upload.id
    assert derived_upload.source_upload_file_id == shared_upload.id
    assert derived_upload.oss_key == shared_upload.oss_key
    assert task.file_id == derived_upload.id
    assert all(
        "WHERE fin_transaction_upload_files.org_id" not in str(stmt)
        for stmt in session.executed
    )


@pytest.mark.asyncio
async def test_transaction_accounting_rerun_reuses_task_and_preserves_result_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    previous_started_at = datetime(2026, 2, 1, 8, 0, tzinfo=timezone.utc)
    previous_finished_at = datetime(2026, 2, 1, 9, 0, tzinfo=timezone.utc)
    previous_updated_at = datetime(2026, 2, 1, 9, 5, tzinfo=timezone.utc)
    old_task = TransactionTask(
        id=7,
        file_id=77,
        org_id=9,
        user_id=7,
        status="success",
        progress=100,
        total_rows=10,
        matched_rows=10,
        unmatched_rows=0,
        failed_rows=0,
        result_summary={"ok": True},
        started_at=previous_started_at,
        finished_at=previous_finished_at,
        updated_at=previous_updated_at,
    )
    upload_file = TransactionUploadFile(
        id=77,
        org_id=9,
        user_id=7,
        shop_id=12,
        source_upload_file_id=21,
        original_name="26年02月_动账_抖音旗舰店.xlsx",
        oss_key="oss-key.xlsx",
        platform_code="douyin",
        shop_name="抖音旗舰店",
        accounting_year=2026,
        accounting_month=2,
        status="processed",
        error_message="old error",
    )
    session = _RerunSession(task=old_task, upload_file=upload_file)
    user = make_user(user_id=7, org_id=9)
    delay_calls: list[int] = []

    async def fake_log(*args, **kwargs):
        return None

    monkeypatch.setattr(
        "app.services.audit_service.AuditService.log",
        fake_log,
    )
    monkeypatch.setattr(
        "app.tasks.transaction_accounting.run_transaction_accounting_task",
        SimpleNamespace(
            delay=lambda task_id: delay_calls.append(task_id)
            or SimpleNamespace(id=f"txn-{task_id}"),
        ),
    )

    rerun_task = await TransactionAccountingService.rerun_task(
        session,  # type: ignore[arg-type]
        task_id=old_task.id,
        user=user,
    )

    assert rerun_task is old_task
    assert session.added == []
    assert old_task.file_id == upload_file.id
    assert old_task.status == "queued"
    assert old_task.progress == 0
    assert old_task.total_rows == 10
    assert old_task.matched_rows == 10
    assert old_task.unmatched_rows == 0
    assert old_task.failed_rows == 0
    assert old_task.error_message is None
    assert old_task.result_summary == {"ok": True}
    assert old_task.started_at is None
    assert old_task.finished_at is None
    assert old_task.updated_at is not None
    assert old_task.updated_at > previous_updated_at
    assert upload_file.status == "uploaded"
    assert upload_file.error_message is None
    executed_sql = "\n".join(str(stmt) for stmt in session.executed)
    assert "DELETE FROM fin_transaction_details" not in executed_sql
    assert "DELETE FROM fin_transaction_summary_rows" not in executed_sql

    await run_after_commit_callbacks(session)  # type: ignore[arg-type]

    assert old_task.celery_task_id == f"txn-{old_task.id}"
    assert delay_calls == [old_task.id]


@pytest.mark.asyncio
async def test_bic_accounting_creates_independent_records_from_shared_upload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _CreateOnlySession()
    user = make_user(user_id=7, org_id=9)
    shared_upload = make_shared_upload(upload_id=31, parsed_type="bic")
    delay_calls: list[int] = []

    async def fake_log(*args, **kwargs):
        return None

    monkeypatch.setattr(
        "app.services.audit_service.AuditService.log",
        fake_log,
    )
    monkeypatch.setattr(
        "app.tasks.bic_accounting.run_bic_accounting_task",
        SimpleNamespace(
            delay=lambda task_id: delay_calls.append(task_id)
            or SimpleNamespace(id=f"bic-{task_id}"),
        ),
    )

    task = await BicAccountingService.create_from_shared_upload(
        session,  # type: ignore[arg-type]
        upload_file=shared_upload,
        user=user,
    )

    derived_upload = next(
        item for item in session.added if item.__class__.__name__ == "BicUploadFile"
    )
    assert derived_upload.source_upload_file_id == shared_upload.id
    assert derived_upload.shop_id == shared_upload.shop_id
    assert derived_upload.oss_key == shared_upload.oss_key
    assert derived_upload.original_name == shared_upload.original_name
    assert task.file_id == derived_upload.id
    assert task.org_id == shared_upload.org_id
    assert task.celery_task_id is None
    assert delay_calls == []

    await run_after_commit_callbacks(session)  # type: ignore[arg-type]

    assert task.celery_task_id == f"bic-{task.id}"
    assert delay_calls == [task.id]


@pytest.mark.asyncio
async def test_bic_accounting_rerun_resets_task_timestamps(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    previous_started_at = datetime(2026, 2, 1, 8, 0, tzinfo=timezone.utc)
    previous_finished_at = datetime(2026, 2, 1, 9, 0, tzinfo=timezone.utc)
    previous_updated_at = datetime(2026, 2, 1, 9, 5, tzinfo=timezone.utc)
    task = BicTask(
        id=17,
        file_id=88,
        org_id=9,
        user_id=7,
        status="success",
        progress=100,
        processed_rows=10,
        success_rows=10,
        failed_rows=0,
        result_summary={"ok": True},
        started_at=previous_started_at,
        finished_at=previous_finished_at,
        updated_at=previous_updated_at,
    )
    upload_file = BicUploadFile(
        id=88,
        org_id=9,
        user_id=7,
        shop_id=12,
        source_upload_file_id=21,
        original_name="26年02月_bic_抖音旗舰店.xlsx",
        oss_key="bic-oss-key.xlsx",
        platform_code="douyin",
        shop_name="抖音旗舰店",
        accounting_year=2026,
        accounting_month=2,
        status="processed",
        error_message="old error",
    )
    session = _RerunSession(task=task, upload_file=upload_file)
    user = make_user(user_id=7, org_id=9)
    delay_calls: list[int] = []

    async def fake_log(*args, **kwargs):
        return None

    monkeypatch.setattr(
        "app.services.audit_service.AuditService.log",
        fake_log,
    )
    monkeypatch.setattr(
        "app.tasks.bic_accounting.run_bic_accounting_task",
        SimpleNamespace(
            delay=lambda task_id: delay_calls.append(task_id)
            or SimpleNamespace(id=f"bic-{task_id}"),
        ),
    )

    rerun_task = await BicAccountingService.rerun_task(
        session,  # type: ignore[arg-type]
        task_id=task.id,
        user=user,
    )

    assert rerun_task is task
    assert task.status == "queued"
    assert task.progress == 0
    assert task.error_message is None
    assert task.started_at is None
    assert task.finished_at is None
    assert task.updated_at is not None
    assert task.updated_at > previous_updated_at
    assert upload_file.status == "uploaded"
    assert upload_file.error_message is None

    await run_after_commit_callbacks(session)  # type: ignore[arg-type]

    assert task.celery_task_id == f"bic-{task.id}"
    assert delay_calls == [task.id]


@pytest.mark.asyncio
async def test_bic_accounting_reupload_creates_new_records_for_same_business_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    existing_upload = BicUploadFile(
        id=88,
        org_id=9,
        user_id=7,
        shop_id=12,
        source_upload_file_id=31,
        original_name="26年02月_bic_抖音旗舰店.xlsx",
        oss_key="old-bic-key.xlsx",
        platform_code="douyin",
        shop_name="抖音旗舰店",
        accounting_year=2026,
        accounting_month=2,
        status="processed",
    )
    session = _ExistingBicBusinessSession(existing_upload=existing_upload)
    user = make_user(user_id=7, org_id=9)
    shared_upload = make_shared_upload(upload_id=33, parsed_type="bic")

    async def fake_log(*args, **kwargs):
        return None

    monkeypatch.setattr(
        "app.services.audit_service.AuditService.log",
        fake_log,
    )

    task = await BicAccountingService.create_from_shared_upload(
        session,  # type: ignore[arg-type]
        upload_file=shared_upload,
        user=user,
    )

    derived_upload = next(
        item for item in session.added if item.__class__.__name__ == "BicUploadFile"
    )
    assert derived_upload.id != existing_upload.id
    assert derived_upload.source_upload_file_id == shared_upload.id
    assert derived_upload.oss_key == shared_upload.oss_key
    assert task.file_id == derived_upload.id
    assert all(
        "WHERE fin_bic_upload_files.org_id" not in str(stmt)
        for stmt in session.executed
    )


@pytest.mark.asyncio
async def test_bic_accounting_marks_task_failed_when_dispatch_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _CreateOnlySession()
    user = make_user(user_id=7, org_id=9)
    shared_upload = make_shared_upload(upload_id=32, parsed_type="bic")

    async def fake_log(*args, **kwargs):
        return None

    monkeypatch.setattr(
        "app.services.audit_service.AuditService.log",
        fake_log,
    )
    monkeypatch.setattr(
        "app.tasks.bic_accounting.run_bic_accounting_task",
        SimpleNamespace(delay=lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("worker unavailable"))),
    )

    task = await BicAccountingService.create_from_shared_upload(
        session,  # type: ignore[arg-type]
        upload_file=shared_upload,
        user=user,
    )

    assert task.status == "queued"

    await run_after_commit_callbacks(session)  # type: ignore[arg-type]

    assert task.status == "failed"
    assert task.progress == 100
    assert "BIC任务投递失败" in (task.error_message or "")


@pytest.mark.asyncio
async def test_reconciliation_checklist_creates_independent_records_from_shared_upload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _CreateOnlySession()
    user = make_user(user_id=7, org_id=9)
    shared_upload = make_shared_upload(upload_id=41, parsed_type="对账清单")
    shared_upload.parsed_year = None
    shared_upload.parsed_month = None
    shared_upload.parsed_shop = ""
    shared_upload.detected_platform = ""
    shared_upload.source_platform_code = ""
    delay_calls: list[int] = []

    async def fake_log(*args, **kwargs):
        return None

    monkeypatch.setattr(
        "app.services.audit_service.AuditService.log",
        fake_log,
    )
    monkeypatch.setattr(
        "app.tasks.reconciliation_checklist.run_reconciliation_checklist_task",
        SimpleNamespace(
            delay=lambda task_id: delay_calls.append(task_id)
            or SimpleNamespace(id=f"checklist-{task_id}"),
        ),
    )

    task = await ReconciliationChecklistService.create_from_shared_upload(
        session,  # type: ignore[arg-type]
        upload_file=shared_upload,
        user=user,
    )

    derived_upload = next(
        item
        for item in session.added
        if item.__class__.__name__ == "ReconciliationChecklistUploadFile"
    )
    assert derived_upload.source_upload_file_id == shared_upload.id
    assert derived_upload.oss_key == shared_upload.oss_key
    assert derived_upload.original_name == shared_upload.original_name
    assert task.file_id == derived_upload.id
    assert task.org_id == shared_upload.org_id
    assert task.celery_task_id is None
    assert delay_calls == []

    await run_after_commit_callbacks(session)  # type: ignore[arg-type]

    assert task.celery_task_id == f"checklist-{task.id}"
    assert delay_calls == [task.id]


@pytest.mark.asyncio
async def test_reconciliation_checklist_rerun_resets_task_timestamps(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    previous_started_at = datetime(2026, 2, 1, 8, 0, tzinfo=timezone.utc)
    previous_finished_at = datetime(2026, 2, 1, 9, 0, tzinfo=timezone.utc)
    previous_updated_at = datetime(2026, 2, 1, 9, 5, tzinfo=timezone.utc)
    task = ReconciliationChecklistTask(
        id=27,
        file_id=98,
        org_id=9,
        user_id=7,
        status="success",
        progress=100,
        total_rows=10,
        success_rows=10,
        failed_rows=0,
        inserted_rows=6,
        updated_rows=4,
        result_summary={"ok": True},
        started_at=previous_started_at,
        finished_at=previous_finished_at,
        updated_at=previous_updated_at,
    )
    upload_file = ReconciliationChecklistUploadFile(
        id=98,
        org_id=9,
        user_id=7,
        source_upload_file_id=21,
        original_name="26年02月_对账清单_抖音旗舰店.xlsx",
        oss_key="checklist-oss-key.xlsx",
        status="processed",
        error_message="old error",
    )
    session = _RerunSession(task=task, upload_file=upload_file)
    user = make_user(user_id=7, org_id=9)
    delay_calls: list[int] = []

    async def fake_log(*args, **kwargs):
        return None

    monkeypatch.setattr(
        "app.services.audit_service.AuditService.log",
        fake_log,
    )
    monkeypatch.setattr(
        "app.tasks.reconciliation_checklist.run_reconciliation_checklist_task",
        SimpleNamespace(
            delay=lambda task_id: delay_calls.append(task_id)
            or SimpleNamespace(id=f"checklist-{task_id}"),
        ),
    )

    rerun_task = await ReconciliationChecklistService.rerun_task(
        session,  # type: ignore[arg-type]
        task_id=task.id,
        user=user,
    )

    assert rerun_task is task
    assert task.status == "queued"
    assert task.progress == 0
    assert task.error_message is None
    assert task.started_at is None
    assert task.finished_at is None
    assert task.updated_at is not None
    assert task.updated_at > previous_updated_at
    assert upload_file.status == "uploaded"
    assert upload_file.error_message is None

    await run_after_commit_callbacks(session)  # type: ignore[arg-type]

    assert task.celery_task_id == f"checklist-{task.id}"
    assert delay_calls == [task.id]


@pytest.mark.asyncio
async def test_reconciliation_checklist_reuses_existing_source_task(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    existing_upload = ReconciliationChecklistUploadFile(
        id=91,
        org_id=9,
        user_id=7,
        source_upload_file_id=41,
        original_name="对账清单.xlsx",
        oss_key="old-key.xlsx",
        status="processed",
    )
    existing_task = ReconciliationChecklistTask(
        id=92,
        file_id=91,
        org_id=9,
        user_id=7,
        status="success",
    )
    session = _ExistingChecklistSourceSession(existing_upload=existing_upload, existing_task=existing_task)
    user = make_user(user_id=7, org_id=9)
    shared_upload = make_shared_upload(upload_id=41, parsed_type="对账清单")

    async def fake_log(*args, **kwargs):
        return None

    monkeypatch.setattr(
        "app.services.audit_service.AuditService.log",
        fake_log,
    )

    task = await ReconciliationChecklistService.create_from_shared_upload(
        session,  # type: ignore[arg-type]
        upload_file=shared_upload,
        user=user,
    )

    assert task is existing_task
    assert not any(item.__class__.__name__ == "ReconciliationChecklistUploadFile" for item in session.added)


class _UploadDispatchSession:
    def __init__(self) -> None:
        self.added = []
        self._next_id = 1
        self.info = {}
        self.org_type = "internal"

    def add(self, instance) -> None:
        self.added.append(instance)

    async def execute(self, stmt):
        class _Result:
            def __init__(self, value):
                self._value = value

            def scalar_one_or_none(self):
                return self._value

        statement = str(stmt)
        if "SELECT fin_organizations.org_type" in statement:
            return _Result(self.org_type)
        return _Result(None)

    async def flush(self) -> None:
        for instance in self.added:
            if getattr(instance, "id", None) is None:
                instance.id = self._next_id
                self._next_id += 1

    async def refresh(self, _instance) -> None:
        return None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    (
        "parsed_type",
        "parsed_year",
        "parsed_month",
        "expected_transaction_calls",
        "expected_bic_calls",
        "expected_checklist_calls",
    ),
    [
        ("动账", 2026, 2, 1, 0, 0),
        ("bic", 2026, 2, 0, 1, 0),
        ("对账清单", None, None, 0, 0, 1),
        ("对账清单-原始数据", None, None, 0, 0, 1),
        ("对账清单-发票更新", None, None, 0, 0, 1),
        ("对账清单-商家更新", None, None, 0, 0, 1),
        ("订单", 2026, 2, 0, 0, 0),
        ("订单", None, None, 0, 0, 0),
    ],
)
async def test_upload_service_dispatches_shared_upload_to_independent_flows(
    monkeypatch: pytest.MonkeyPatch,
    parsed_type: str,
    parsed_year: int | None,
    parsed_month: int | None,
    expected_transaction_calls: int,
    expected_bic_calls: int,
    expected_checklist_calls: int,
) -> None:
    session = _UploadDispatchSession()
    user = make_user(user_id=7, org_id=9)
    batch = UploadBatch(id=1, org_id=9, user_id=7, file_count=1)
    transaction_calls: list[int] = []
    bic_calls: list[int] = []
    checklist_calls: list[int] = []
    audit_descriptions: list[str] = []

    async def fake_get_batch_for_user(*args, **kwargs):
        return batch

    async def fake_check_storage_quota(*args, **kwargs):
        return True, ""

    async def fake_update_storage_usage(*args, **kwargs):
        return None

    async def fake_get_or_create_shop(*args, **kwargs):
        return SimpleNamespace(id=12)

    async def fake_log(*args, **kwargs):
        audit_descriptions.append(kwargs["description"])
        return None

    async def fake_transaction_create(*args, **kwargs):
        upload_file = kwargs["upload_file"]
        transaction_calls.append(upload_file.id)
        return SimpleNamespace(id=501)

    async def fake_bic_create(*args, **kwargs):
        upload_file = kwargs["upload_file"]
        bic_calls.append(upload_file.id)
        return SimpleNamespace(id=601)

    async def fake_checklist_create(*args, **kwargs):
        upload_file = kwargs["upload_file"]
        checklist_calls.append(upload_file.id)
        return SimpleNamespace(id=701)

    monkeypatch.setattr(UploadService, "get_batch_for_user", fake_get_batch_for_user)
    monkeypatch.setattr(
        "app.services.upload_service.QuotaService.check_storage_quota",
        fake_check_storage_quota,
    )
    monkeypatch.setattr(
        "app.services.upload_service.QuotaService.update_storage_usage",
        fake_update_storage_usage,
    )
    async def fake_resolve_platform_profile(*args, **kwargs):
        return SimpleNamespace(
            source_platform_code="douyin",
            report_platform_code="douyin",
            processor_code="douyin",
            order_scope_code="douyin",
        )

    async def fake_resolve_upload_period_header(*args, **kwargs):
        return "动账时间"

    monkeypatch.setattr(
        "app.services.upload_service.resolve_platform_profile",
        fake_resolve_platform_profile,
    )
    monkeypatch.setattr(
        "app.services.upload_service.resolve_upload_period_header",
        fake_resolve_upload_period_header,
    )
    monkeypatch.setattr(
        "app.services.upload_service.ShopService.get_or_create_shop",
        fake_get_or_create_shop,
    )
    monkeypatch.setattr(
        "app.services.upload_service.AuditService.log",
        fake_log,
    )
    monkeypatch.setattr(
        "app.tasks.celery_app.process_file_platform",
        SimpleNamespace(delay=lambda **kwargs: SimpleNamespace(id="generic-1")),
    )
    monkeypatch.setattr(
        TransactionAccountingService,
        "create_from_shared_upload",
        fake_transaction_create,
        raising=False,
    )
    monkeypatch.setattr(
        BicAccountingService,
        "create_from_shared_upload",
        fake_bic_create,
        raising=False,
    )
    monkeypatch.setattr(
        ReconciliationChecklistService,
        "create_from_shared_upload",
        fake_checklist_create,
        raising=False,
    )

    callback_data = upload_service_module.UploadFileCallback(
        batch_id=1,
        original_name=(
            f"26年02月_{parsed_type}_抖音旗舰店.xlsx"
            if parsed_year and parsed_month
            else f"{parsed_type}_抖音旗舰店明细.xlsx"
        ),
        oss_key="user-upload/test/current.xlsx",
        file_size=4096,
        file_hash="hash",
        parsed_year=parsed_year,
        parsed_month=parsed_month,
        parsed_type=parsed_type,
        parsed_shop="" if parsed_type.startswith("对账清单") else "抖音旗舰店",
        detected_platform="" if parsed_type.startswith("对账清单") else "douyin",
    )

    upload_file = await UploadService.handle_file_callback(
        session,  # type: ignore[arg-type]
        batch_id=1,
        data=callback_data,
        user=user,
    )

    generic_task = next(
        item for item in session.added if isinstance(item, ProcessingTask)
    )
    assert upload_file.id is not None
    assert upload_file.parsed_year == parsed_year
    assert upload_file.parsed_month == parsed_month
    assert generic_task.file_id == upload_file.id
    assert transaction_calls == [upload_file.id] * expected_transaction_calls
    assert bic_calls == [upload_file.id] * expected_bic_calls
    assert checklist_calls == [upload_file.id] * expected_checklist_calls
    assert any("大小 4.00 KB" in description for description in audit_descriptions)


@pytest.mark.asyncio
async def test_upload_service_rejects_internal_only_shared_upload_for_external_org(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = _UploadDispatchSession()
    session.org_type = "external"
    user = make_user(user_id=7, org_id=9)
    batch = UploadBatch(id=1, org_id=9, user_id=7, file_count=1)

    async def fake_get_batch_for_user(*args, **kwargs):
        return batch

    async def fake_check_storage_quota(*args, **kwargs):
        return True, ""

    async def fake_get_or_create_shop(*args, **kwargs):
        return SimpleNamespace(id=12)

    async def fake_resolve_platform_profile(*args, **kwargs):
        return SimpleNamespace(
            source_platform_code="douyin",
            report_platform_code="douyin",
            processor_code="douyin",
            order_scope_code="douyin",
        )

    monkeypatch.setattr(UploadService, "get_batch_for_user", fake_get_batch_for_user)
    monkeypatch.setattr(
        "app.services.upload_service.QuotaService.check_storage_quota",
        fake_check_storage_quota,
    )
    monkeypatch.setattr(
        "app.services.upload_service.resolve_platform_profile",
        fake_resolve_platform_profile,
    )
    monkeypatch.setattr(
        "app.services.upload_service.ShopService.get_or_create_shop",
        fake_get_or_create_shop,
    )

    callback_data = upload_service_module.UploadFileCallback(
        batch_id=1,
        original_name="26年02月_动账_抖音旗舰店.xlsx",
        oss_key="user-upload/test/current.xlsx",
        file_size=4096,
        file_hash="hash",
        parsed_year=2026,
        parsed_month=2,
        parsed_type="动账",
        parsed_shop="抖音旗舰店",
        detected_platform="douyin",
    )

    with pytest.raises(ValueError, match="外部组织不能使用该核算功能"):
        await UploadService.handle_file_callback(
            session,  # type: ignore[arg-type]
            batch_id=1,
            data=callback_data,
            user=user,
        )
