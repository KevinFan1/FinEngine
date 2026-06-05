from types import SimpleNamespace
from datetime import datetime
from decimal import Decimal

import pytest

from app.models.platform import Platform
from app.models.upload import UploadFile
import app.core.database as database_module
import app.services.oss_service as oss_service_module
from app.tasks.celery_app import (
    _build_order_dependency_summary,
    _build_order_or_fallback_time_summary,
    _group_money_by_order_created_time,
    _group_return_cost_by_order_created_time,
    _group_money_by_order_or_fallback_time,
    _infer_file_type,
    _mark_task_empty_success,
    _result_task_status_from_processor_result,
    _result_task_status_from_summary,
)
from app.tasks import celery_app as celery_module
from app.services.oss_service import OSSObjectUnavailableError, SOURCE_FILE_UNAVAILABLE_MESSAGE


def test_infer_file_type_prefers_filename_over_stored_default() -> None:
    upload_file = SimpleNamespace(
        id=1,
        original_name="26年02月_运费险_快手店铺.csv",
        parsed_type="gmv",
    )

    assert _infer_file_type(upload_file) == "运费险"


def test_infer_file_type_normalizes_gmv_from_filename() -> None:
    upload_file = SimpleNamespace(
        id=2,
        original_name="26年02月_GMV_快手店铺.xlsx",
        parsed_type=None,
    )

    assert _infer_file_type(upload_file) == "gmv"


def test_infer_file_type_supports_order_from_filename() -> None:
    upload_file = SimpleNamespace(
        id=3,
        original_name="26年02月_订单_快手店铺.xlsx",
        parsed_type=None,
    )

    assert _infer_file_type(upload_file) == "订单"


def test_infer_file_type_supports_other_service_from_filename() -> None:
    upload_file = SimpleNamespace(
        id=4,
        original_name="26年02月_其他服务款_小红书店铺.xlsx",
        parsed_type=None,
    )

    assert _infer_file_type(upload_file) == "其他服务款"


def test_infer_file_type_supports_new_filename_without_period() -> None:
    upload_file = SimpleNamespace(
        id=8,
        original_name="BIC_抖音旗舰店明细.xlsx",
        parsed_type=None,
    )

    assert _infer_file_type(upload_file) == "bic"


def test_infer_file_type_supports_new_gmv_alias() -> None:
    upload_file = SimpleNamespace(
        id=9,
        original_name="GMV其他服务款_小红书店铺明细.xlsx",
        parsed_type=None,
    )

    assert _infer_file_type(upload_file) == "其他服务款"


def test_infer_file_type_supports_xlsm_from_filename() -> None:
    upload_file = SimpleNamespace(
        id=5,
        original_name="26年02月_动账_抖音旗舰店.xlsm",
        parsed_type=None,
    )

    assert _infer_file_type(upload_file) == "动账"


def test_infer_file_type_supports_xls_from_filename() -> None:
    upload_file = SimpleNamespace(
        id=6,
        original_name="26年02月_动账_抖音旗舰店.xls",
        parsed_type=None,
    )

    assert _infer_file_type(upload_file) == "动账"


def test_group_return_cost_by_order_created_time_counts_missing_orders() -> None:
    grouped, missing_order_nos = _group_return_cost_by_order_created_time(
        [
            {"order_no": "order-1", "return_cost": Decimal("-10.50")},
            {"order_no": "order-2", "return_cost": Decimal("3.25")},
            {"order_no": "missing", "return_cost": Decimal("-5")},
        ],
        {
            "order-1": datetime(2026, 4, 1, 12, 0, 0),
            "order-2": datetime(2026, 5, 2, 12, 0, 0),
        },
    )

    assert grouped == {
        (2026, 4): Decimal("-10.50"),
        (2026, 5): Decimal("3.25"),
    }
    assert missing_order_nos == ["missing"]


def test_group_money_by_order_or_fallback_time_falls_back_to_entry_time() -> None:
    grouped, missing_order_nos, fallback_order_nos = _group_money_by_order_or_fallback_time(
        [
            {
                "order_no": "indexed-order",
                "entry_time": datetime(2026, 6, 1, 12, 0, 0),
                "return_cost": Decimal("-10.50"),
            },
            {
                "order_no": "fallback-order",
                "entry_time": datetime(2026, 5, 2, 12, 0, 0),
                "return_cost": Decimal("3.25"),
            },
            {"order_no": "missing", "entry_time": None, "return_cost": Decimal("-5")},
        ],
        order_created_times={
            "indexed-order": datetime(2026, 4, 1, 12, 0, 0),
        },
        amount_key="return_cost",
        fallback_time_key="entry_time",
    )

    assert grouped == {
        (2026, 4): Decimal("-10.50"),
        (2026, 5): Decimal("3.25"),
    }
    assert missing_order_nos == ["missing"]
    assert fallback_order_nos == ["fallback-order"]


def test_group_money_by_order_or_fallback_time_falls_back_to_effective_time() -> None:
    grouped, missing_order_nos, fallback_order_nos = _group_money_by_order_or_fallback_time(
        [
            {
                "order_no": "indexed-order",
                "effective_time": datetime(2026, 6, 1, 12, 0, 0),
                "insurance_fee": Decimal("1.25"),
            },
            {
                "order_no": "fallback-order",
                "effective_time": datetime(2026, 5, 2, 12, 0, 0),
                "insurance_fee": Decimal("2.50"),
            },
            {"order_no": "missing", "effective_time": None, "insurance_fee": Decimal("3.00")},
        ],
        order_created_times={
            "indexed-order": datetime(2026, 4, 1, 12, 0, 0),
        },
        amount_key="insurance_fee",
        fallback_time_key="effective_time",
    )

    assert grouped == {
        (2026, 4): Decimal("1.25"),
        (2026, 5): Decimal("2.50"),
    }
    assert missing_order_nos == ["missing"]
    assert fallback_order_nos == ["fallback-order"]


def test_group_money_by_order_created_time_preserves_missing_row_count() -> None:
    grouped, missing_order_nos = _group_money_by_order_created_time(
        [
            {"order_no": "missing-order", "return_cost": Decimal("1")},
            {"order_no": "missing-order", "return_cost": Decimal("2")},
        ],
        order_created_times={},
        amount_key="return_cost",
    )

    assert grouped == {}
    assert missing_order_nos == ["missing-order", "missing-order"]


def test_order_dependency_summary_counts_missing_rows_not_unique_orders() -> None:
    summary = _build_order_dependency_summary(
        type_code="动账",
        proc_result={"total_rows": 3, "success_rows": 3, "failed_rows": 0, "errors": []},
        summary_ids=[],
        groups=0,
        missing_order_nos=["same-order", "same-order"],
    )

    assert summary["total_rows"] == 3
    assert summary["success_rows"] == 1
    assert summary["failed_rows"] == 2
    assert summary["missing_order_count"] == 2
    assert summary["missing_order_samples"] == ["same-order"]


def test_order_or_fallback_time_summary_reports_fallback_time() -> None:
    summary = _build_order_or_fallback_time_summary(
        type_code="运费险",
        proc_result={"success_rows": 3, "failed_rows": 0, "errors": []},
        summary_ids=[1, 2],
        groups=2,
        missing_order_nos=[],
        fallback_order_nos=["fallback-order"],
        fallback_label="生效时间",
    )

    assert summary["success_rows"] == 3
    assert summary["failed_rows"] == 0
    assert summary["fallback_time_label"] == "生效时间"
    assert summary["fallback_time_count"] == 1
    assert summary["fallback_time_samples"] == ["fallback-order"]
    assert summary["errors"] == ["订单索引未命中 1 条，已使用生效时间归属年月；订单号: fallback-order"]


def test_order_or_fallback_time_summary_reports_entry_time_compatibility() -> None:
    summary = _build_order_or_fallback_time_summary(
        type_code="动账",
        proc_result={"success_rows": 3, "failed_rows": 0, "errors": []},
        summary_ids=[1, 2],
        groups=2,
        missing_order_nos=[],
        fallback_order_nos=["fallback-order"],
        fallback_label="入账时间",
    )

    assert summary["fallback_time_label"] == "入账时间"
    assert summary["fallback_time_count"] == 1
    assert summary["fallback_time_samples"] == ["fallback-order"]
    assert summary["errors"] == ["订单索引未命中 1 条，已使用入账时间归属年月；订单号: fallback-order"]


def test_order_or_fallback_time_summary_counts_fallback_rows_with_unique_samples() -> None:
    summary = _build_order_or_fallback_time_summary(
        type_code="动账",
        proc_result={"success_rows": 3, "failed_rows": 0, "errors": []},
        summary_ids=[1],
        groups=1,
        missing_order_nos=[],
        fallback_order_nos=["same-order", "same-order"],
        fallback_label="入账时间",
    )

    assert summary["fallback_time_count"] == 2
    assert summary["fallback_time_samples"] == ["same-order"]
    assert summary["errors"] == ["订单索引未命中 2 条，已使用入账时间归属年月；订单号: same-order"]


def test_result_task_status_uses_partial_success_when_failed_rows_exist() -> None:
    assert _result_task_status_from_processor_result({"failed_rows": 0}) == "success"
    assert _result_task_status_from_processor_result({"failed_rows": 2}) == "partial_success"
    assert _result_task_status_from_summary({"failed_rows": 1, "success_rows": 3}) == "partial_success"


def test_mark_task_failed_sets_task_and_upload_file_state() -> None:
    task = SimpleNamespace(status="running", progress=60, error_message=None, finished_at=None)
    upload_file = SimpleNamespace(status="processing", error_message=None)

    celery_module._mark_task_failed(task, upload_file, "OSS文件不存在")

    assert task.status == "failed"
    assert task.progress == 100
    assert task.error_message == "OSS文件不存在"
    assert task.finished_at is not None
    assert upload_file.status == "failed"
    assert upload_file.error_message == "OSS文件不存在"


def test_mark_task_failed_sets_expired_for_unavailable_source_file() -> None:
    previous_state = {
        "processed_rows": 8,
        "success_rows": 7,
        "failed_rows": 1,
        "result_summary": {"old": True},
        "upload_row_count": 8,
    }
    task = SimpleNamespace(
        status="running",
        processed_rows=2,
        success_rows=2,
        failed_rows=0,
        result_summary=None,
        progress=60,
        error_message=None,
        finished_at=None,
    )
    upload_file = SimpleNamespace(status="processing", error_message=None, row_count=2)

    celery_module._mark_task_failed(
        task,
        upload_file,
        OSSObjectUnavailableError("missing"),
        previous_state=previous_state,
    )

    assert task.status == "expired"
    assert task.progress == 100
    assert task.error_message == SOURCE_FILE_UNAVAILABLE_MESSAGE
    assert task.processed_rows == 8
    assert task.success_rows == 7
    assert task.failed_rows == 1
    assert task.result_summary == {"old": True}
    assert upload_file.status == "expired"
    assert upload_file.error_message == SOURCE_FILE_UNAVAILABLE_MESSAGE
    assert upload_file.row_count == 8


def test_mark_task_empty_success_keeps_success_status_with_empty_reason() -> None:
    task = SimpleNamespace(
        status="processing",
        progress=20,
        processed_rows=4,
        success_rows=3,
        failed_rows=1,
        error_message=None,
        result_summary=None,
        finished_at=None,
    )
    upload_file = SimpleNamespace(status="processing", error_message=None, row_count=4)

    _mark_task_empty_success(task, upload_file, file_type="动账")

    assert task.status == "success"
    assert task.progress == 100
    assert task.processed_rows == 0
    assert task.success_rows == 0
    assert task.failed_rows == 0
    assert task.error_message == "空表，没有数据"
    assert task.result_summary == {
        "type": "动账",
        "total_rows": 0,
        "success_rows": 0,
        "failed_rows": 0,
        "groups": 0,
        "errors": ["空表，没有数据"],
    }
    assert task.finished_at is not None
    assert upload_file.status == "success"
    assert upload_file.error_message == "空表，没有数据"
    assert upload_file.row_count == 0


def test_celery_imports_include_bic_task_module() -> None:
    assert "app.tasks.transaction_accounting" in celery_module.celery_app.conf.imports
    assert "app.tasks.bic_accounting" in celery_module.celery_app.conf.imports


def test_celery_enables_worker_events_for_flower_monitoring() -> None:
    assert celery_module.celery_app.conf.task_track_started is True
    assert celery_module.celery_app.conf.worker_send_task_events is True
    assert celery_module.celery_app.conf.task_send_sent_event is True


def test_celery_initializes_backend_logging_for_worker(monkeypatch: pytest.MonkeyPatch) -> None:
    called = {"count": 0}

    def fake_setup_logging() -> None:
        called["count"] += 1

    monkeypatch.setattr(celery_module, "setup_logging", fake_setup_logging)

    celery_module._configure_worker_logging()

    assert called["count"] == 1


class _ExpiredTaskIdAccessError(RuntimeError):
    pass


class _RollbackSensitiveTask:
    def __init__(self) -> None:
        self._id = 123
        self.file_id = 456
        self.org_id = 1
        self.user_id = 2
        self.status = "queued"
        self.progress = 0
        self.celery_task_id = None
        self.started_at = None
        self.finished_at = None
        self.error_message = None
        self.processed_rows = 9
        self.success_rows = 8
        self.failed_rows = 1
        self.result_summary = {"old": True}
        self.expired = False

    @property
    def id(self) -> int:
        if self.expired:
            raise _ExpiredTaskIdAccessError("task.id was accessed after rollback")
        return self._id


class _ScalarResult:
    def __init__(self, value) -> None:
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class _ProcessFileSession:
    def __init__(self, task: _RollbackSensitiveTask, upload_file: UploadFile, platform: Platform) -> None:
        self.task = task
        self.upload_file = upload_file
        self.platform = platform
        self.commit_count = 0
        self.rollback_count = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def execute(self, stmt):
        statement = str(stmt)
        if "FROM fin_processing_tasks" in statement:
            return _ScalarResult(self.task)
        if "FROM fin_upload_files" in statement:
            return _ScalarResult(self.upload_file)
        if "FROM fin_platforms" in statement:
            return _ScalarResult(self.platform)
        return _ScalarResult(None)

    async def commit(self) -> None:
        self.commit_count += 1

    async def rollback(self) -> None:
        self.rollback_count += 1
        self.task.expired = True


class _ProcessFileSessionFactory:
    def __init__(self, session: _ProcessFileSession) -> None:
        self.session = session

    def __call__(self):
        return self.session


class _ReconcileSession(_ProcessFileSession):
    async def execute(self, stmt):
        statement = str(stmt)
        if "FROM fin_processing_tasks" in statement:
            return _RowsResult([(self.task, self.upload_file)])
        return _RowsResult([])


class _RowsResult:
    def __init__(self, rows) -> None:
        self._rows = rows

    def all(self):
        return self._rows


class _FakeAsyncResult:
    def __init__(self, state: str, result) -> None:
        self.state = state
        self.result = result


@pytest.mark.asyncio
async def test_process_file_exception_reloads_task_without_accessing_expired_task_id(monkeypatch) -> None:
    task = _RollbackSensitiveTask()
    upload_file = UploadFile(
        id=456,
        batch_id=1,
        org_id=1,
        user_id=2,
        original_name="26年02月_动账_抖音旗舰店.xlsx",
        oss_key="oss-key",
        file_size=100,
        parsed_year=2026,
        parsed_month=2,
        parsed_type="动账",
        parsed_shop="抖音旗舰店",
        detected_platform="douyin",
        status="uploaded",
    )
    platform = Platform(id=1, code="douyin", name="抖音", status=1)
    session = _ProcessFileSession(task, upload_file, platform)

    monkeypatch.setattr(database_module, "async_session_factory", _ProcessFileSessionFactory(session))

    def fail_download(_oss_key: str, _target_path: str) -> None:
        raise OSSObjectUnavailableError("missing")

    monkeypatch.setattr(oss_service_module.oss_service, "download_to_temp", fail_download)

    task_instance = SimpleNamespace(request=SimpleNamespace(id="celery-task-id"))

    with pytest.raises(OSSObjectUnavailableError):
        await celery_module._process_file_platform_async(
            task_instance,
            file_id=456,
            oss_key="oss-key",
            org_id=1,
            platform_code="douyin",
            shop_name="抖音旗舰店",
            shop_id=None,
        )

    assert session.rollback_count == 1
    assert task.status == "expired"
    assert task.error_message == SOURCE_FILE_UNAVAILABLE_MESSAGE
    assert task.processed_rows == 9
    assert upload_file.status == "expired"


@pytest.mark.asyncio
async def test_reconcile_terminal_running_processing_tasks_marks_failed(monkeypatch) -> None:
    task = _RollbackSensitiveTask()
    task.status = "running"
    task.progress = 60
    task.celery_task_id = "failed-celery-task"
    upload_file = UploadFile(
        id=456,
        batch_id=1,
        org_id=1,
        user_id=2,
        original_name="26年02月_动账_抖音旗舰店.xlsx",
        oss_key="oss-key",
        file_size=100,
        status="processing",
    )
    session = _ReconcileSession(task, upload_file, Platform(id=1, code="douyin", name="抖音", status=1))

    monkeypatch.setattr(database_module, "async_session_factory", _ProcessFileSessionFactory(session))
    monkeypatch.setattr(
        celery_module.celery_app,
        "AsyncResult",
        lambda _task_id: _FakeAsyncResult("FAILURE", RuntimeError("boom")),
    )

    reconciled = await celery_module._reconcile_terminal_running_processing_tasks_async(limit=10)

    assert reconciled == 1
    assert session.commit_count == 1
    assert task.status == "failed"
    assert task.progress == 100
    assert task.error_message == "boom"
    assert upload_file.status == "failed"


@pytest.mark.asyncio
async def test_reconcile_terminal_running_processing_tasks_keeps_active_task(monkeypatch) -> None:
    task = _RollbackSensitiveTask()
    task.status = "running"
    task.progress = 60
    task.celery_task_id = "active-celery-task"
    upload_file = UploadFile(
        id=456,
        batch_id=1,
        org_id=1,
        user_id=2,
        original_name="26年02月_动账_抖音旗舰店.xlsx",
        oss_key="oss-key",
        file_size=100,
        status="processing",
    )
    session = _ReconcileSession(task, upload_file, Platform(id=1, code="douyin", name="抖音", status=1))

    monkeypatch.setattr(database_module, "async_session_factory", _ProcessFileSessionFactory(session))
    monkeypatch.setattr(
        celery_module.celery_app,
        "AsyncResult",
        lambda _task_id: _FakeAsyncResult("STARTED", None),
    )

    reconciled = await celery_module._reconcile_terminal_running_processing_tasks_async(limit=10)

    assert reconciled == 0
    assert session.commit_count == 0
    assert task.status == "running"
    assert task.progress == 60
    assert upload_file.status == "processing"
