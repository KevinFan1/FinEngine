from types import SimpleNamespace

import pytest

from app.models.organization import Organization
from app.models.task import ProcessingTask
from app.models.upload import UploadBatch, UploadFile
from app.models.user import User
from app.services import upload_service as upload_service_module
from app.services.bic_accounting_service import BicAccountingService
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
    assert derived_upload.oss_key == shared_upload.oss_key
    assert derived_upload.original_name == shared_upload.original_name
    assert task.file_id == derived_upload.id
    assert task.org_id == shared_upload.org_id
    assert task.celery_task_id == f"txn-{task.id}"
    assert delay_calls == [task.id]


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
    assert derived_upload.oss_key == shared_upload.oss_key
    assert derived_upload.original_name == shared_upload.original_name
    assert task.file_id == derived_upload.id
    assert task.org_id == shared_upload.org_id
    assert task.celery_task_id == f"bic-{task.id}"
    assert delay_calls == [task.id]


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

    assert task.status == "failed"
    assert task.progress == 100
    assert "BIC任务投递失败" in (task.error_message or "")


class _UploadDispatchSession:
    def __init__(self) -> None:
        self.added = []
        self._next_id = 1

    def add(self, instance) -> None:
        self.added.append(instance)

    async def flush(self) -> None:
        for instance in self.added:
            if getattr(instance, "id", None) is None:
                instance.id = self._next_id
                self._next_id += 1

    async def refresh(self, _instance) -> None:
        return None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("parsed_type", "expected_transaction_calls", "expected_bic_calls"),
    [
        ("动账", 1, 0),
        ("bic", 0, 1),
        ("订单", 0, 0),
    ],
)
async def test_upload_service_dispatches_shared_upload_to_independent_flows(
    monkeypatch: pytest.MonkeyPatch,
    parsed_type: str,
    expected_transaction_calls: int,
    expected_bic_calls: int,
) -> None:
    session = _UploadDispatchSession()
    user = make_user(user_id=7, org_id=9)
    batch = UploadBatch(id=1, org_id=9, user_id=7, file_count=1)
    transaction_calls: list[int] = []
    bic_calls: list[int] = []

    async def fake_get_batch_for_user(*args, **kwargs):
        return batch

    async def fake_check_storage_quota(*args, **kwargs):
        return True, ""

    async def fake_update_storage_usage(*args, **kwargs):
        return None

    async def fake_get_or_create_shop(*args, **kwargs):
        return SimpleNamespace(id=12)

    async def fake_log(*args, **kwargs):
        return None

    async def fake_transaction_create(*args, **kwargs):
        upload_file = kwargs["upload_file"]
        transaction_calls.append(upload_file.id)
        return SimpleNamespace(id=501)

    async def fake_bic_create(*args, **kwargs):
        upload_file = kwargs["upload_file"]
        bic_calls.append(upload_file.id)
        return SimpleNamespace(id=601)

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

    monkeypatch.setattr(
        "app.services.upload_service.resolve_platform_profile",
        fake_resolve_platform_profile,
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

    callback_data = upload_service_module.UploadFileCallback(
        batch_id=1,
        original_name=f"26年02月_{parsed_type}_抖音旗舰店.xlsx",
        oss_key="user-upload/test/current.xlsx",
        file_size=4096,
        file_hash="hash",
        parsed_year=2026,
        parsed_month=2,
        parsed_type=parsed_type,
        parsed_shop="抖音旗舰店",
        detected_platform="douyin",
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
    assert generic_task.file_id == upload_file.id
    assert transaction_calls == [upload_file.id] * expected_transaction_calls
    assert bic_calls == [upload_file.id] * expected_bic_calls
