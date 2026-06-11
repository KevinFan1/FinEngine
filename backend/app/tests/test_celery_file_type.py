import asyncio
from types import SimpleNamespace
from datetime import datetime
from decimal import Decimal
import logging

import pytest

from app.models.platform import Platform
from app.models.upload import UploadFile
import app.core.database as database_module
import app.services.oss_service as oss_service_module
import app.tasks.processors as processors_module
from app.tasks.celery_app import (
    _apply_processing_stage_metrics,
    _build_order_dependency_summary,
    _build_order_or_fallback_time_summary,
    _build_task_result_payload,
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

    assert summary["总行数"] == 3
    assert summary["成功行数"] == 1
    assert summary["失败行数"] == 2
    assert summary["缺少订单创建时间行数"] == 2
    assert summary["缺少订单创建时间订单样例"] == ["same-order"]


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

    assert summary["成功行数"] == 3
    assert summary["失败行数"] == 0
    assert summary["兜底时间字段"] == "生效时间"
    assert summary["兜底归属年月行数"] == 1
    assert summary["兜底归属年月订单样例"] == ["fallback-order"]
    assert summary["错误明细"] == ["订单索引未命中 1 条，已使用生效时间归属年月；订单号: fallback-order"]


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

    assert summary["兜底时间字段"] == "入账时间"
    assert summary["兜底归属年月行数"] == 1
    assert summary["兜底归属年月订单样例"] == ["fallback-order"]
    assert summary["错误明细"] == ["订单索引未命中 1 条，已使用入账时间归属年月；订单号: fallback-order"]


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

    assert summary["兜底归属年月行数"] == 2
    assert summary["兜底归属年月订单样例"] == ["same-order"]
    assert summary["错误明细"] == ["订单索引未命中 2 条，已使用入账时间归属年月；订单号: same-order"]


def test_result_task_status_uses_partial_success_when_failed_rows_exist() -> None:
    assert _result_task_status_from_processor_result({"failed_rows": 0}) == "success"
    assert _result_task_status_from_processor_result({"failed_rows": 2}) == "partial_success"
    assert _result_task_status_from_summary({"failed_rows": 1, "success_rows": 3}) == "partial_success"
    assert _result_task_status_from_summary({"失败行数": 1, "成功行数": 3}) == "partial_success"


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
        "文件类型": "动账",
        "总行数": 0,
        "成功行数": 0,
        "失败行数": 0,
        "汇总分组数": 0,
        "错误明细": ["空表，没有数据"],
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


def test_build_task_result_payload_includes_result_summary_for_flower() -> None:
    task = SimpleNamespace(
        id=12,
        status="success",
        processed_rows=100,
        success_rows=95,
        failed_rows=5,
        result_summary={"任务总耗时秒": 12.345, "处理器执行耗时秒": 4.321},
    )
    upload_file = SimpleNamespace(row_count=100)

    payload = _build_task_result_payload(task, upload_file=upload_file, extra={"文件ID": 34})

    assert payload == {
        "任务ID": 12,
        "任务状态": "success",
        "处理行数": 100,
        "成功行数": 95,
        "失败行数": 5,
        "结果摘要": {"任务总耗时秒": 12.345, "处理器执行耗时秒": 4.321},
        "上传行数": 100,
        "文件ID": 34,
    }


def test_process_file_platform_returns_result_summary_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    task = _RollbackSensitiveTask()
    task.status = "success"
    task.processed_rows = 1
    task.success_rows = 1
    task.failed_rows = 0
    task.result_summary = {"任务总耗时秒": 1.234, "汇总分组数": 0}

    async def fake_process_file_platform_async(*args, **kwargs):
        _ = args, kwargs
        return {
            "任务ID": task.id,
            "任务状态": task.status,
            "处理行数": task.processed_rows,
            "成功行数": task.success_rows,
            "失败行数": task.failed_rows,
            "结果摘要": task.result_summary,
            "上传行数": 1,
            "文件ID": 456,
            "文件类型": "动账",
        }

    monkeypatch.setattr(celery_module, "_process_file_platform_async", fake_process_file_platform_async)
    monkeypatch.setattr(celery_module, "_run_async_in_worker", lambda coro: asyncio.run(coro))

    task_instance = SimpleNamespace(request=SimpleNamespace(id="celery-task-id"))
    payload = celery_module.process_file_platform.run(
        task_instance,
        456,
        "oss-key",
        1,
        "douyin",
        "抖音旗舰店",
    )

    assert payload["结果摘要"] == {"任务总耗时秒": 1.234, "汇总分组数": 0}
    assert payload["文件类型"] == "动账"


def test_apply_processing_stage_metrics_uses_unified_chinese_keys() -> None:
    task = SimpleNamespace(
        result_summary={
            "文件类型": "动账",
            "总行数": 10,
            "成功行数": 9,
            "失败行数": 1,
        }
    )

    _apply_processing_stage_metrics(
        task,
        file_type="动账",
        download_seconds=1.111,
        period_seconds=2.222,
        category_seconds=3.333,
        processor_seconds=4.444,
        postprocess_seconds=5.555,
        total_seconds=6.666,
    )

    assert task.result_summary == {
        "文件类型": "动账",
        "总行数": 10,
        "成功行数": 9,
        "失败行数": 1,
        "文件下载耗时秒": 1.111,
        "所属年月解析耗时秒": 2.222,
        "类目加载耗时秒": 3.333,
        "处理器执行耗时秒": 4.444,
        "后处理入库耗时秒": 5.555,
        "任务总耗时秒": 6.666,
    }


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


class _FakeProcessor:
    def process(self, **_kwargs):
        return {
            "total_rows": 1,
            "success_rows": 1,
            "failed_rows": 0,
            "errors": [],
            "groups": {},
        }


class _MerchantSession(_ProcessFileSession):
    async def get(self, _model, _pk):
        return SimpleNamespace(id=2)


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
async def test_process_file_platform_logs_chinese_stage_summary(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
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
    monkeypatch.setattr(oss_service_module.oss_service, "download_to_temp", lambda *_args, **_kwargs: None)

    async def fake_resolve_upload_period_header(*_args, **_kwargs) -> str:
        return "动账时间"

    monkeypatch.setattr(celery_module, "resolve_upload_period_header", fake_resolve_upload_period_header)
    monkeypatch.setattr(
        celery_module,
        "extract_upload_period",
        lambda *_args, **_kwargs: SimpleNamespace(year=2026, month=2, header="动账时间"),
    )

    async def fake_resolve_platform_profile(_db, _platform_code):
        return SimpleNamespace(
            processor_code="douyin",
            source_platform_code="douyin",
            report_platform_code="douyin",
            order_scope_code="douyin",
        )

    async def fake_get_categories(*_args, **_kwargs):
        return []

    monkeypatch.setattr("app.services.platform_profile_service.resolve_platform_profile", fake_resolve_platform_profile)
    monkeypatch.setattr("app.services.category_dict_service.CategoryDictService.get_categories", fake_get_categories)
    monkeypatch.setitem(processors_module.PLATFORM_PROCESSORS, "douyin", _FakeProcessor())

    task_instance = SimpleNamespace(request=SimpleNamespace(id="celery-task-id"))

    with caplog.at_level(logging.INFO, logger="finengine.worker"):
        payload = await celery_module._process_file_platform_async(
            task_instance,
            file_id=456,
            oss_key="oss-key",
            org_id=1,
            platform_code="douyin",
            shop_name="抖音旗舰店",
            shop_id=None,
        )

    assert payload is not None
    assert payload["结果摘要"]["文件下载耗时秒"] >= 0
    assert payload["结果摘要"]["所属年月解析耗时秒"] >= 0
    assert payload["结果摘要"]["类目加载耗时秒"] >= 0
    assert payload["结果摘要"]["处理器执行耗时秒"] >= 0
    assert payload["结果摘要"]["后处理入库耗时秒"] >= 0
    assert payload["结果摘要"]["任务总耗时秒"] >= 0
    assert "核算任务阶段总览" in caplog.text
    assert "任务状态=success" in caplog.text
    assert "文件下载耗时秒=" in caplog.text
    assert "处理器执行耗时秒=" in caplog.text
    assert "后处理入库耗时秒=" in caplog.text


@pytest.mark.asyncio
async def test_process_merchant_red_sheet_returns_unified_stage_metrics(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task = _RollbackSensitiveTask()
    upload_file = UploadFile(
        id=456,
        batch_id=1,
        org_id=1,
        user_id=2,
        original_name="2026年02月_红单_测试店.xlsx",
        oss_key="oss-key",
        file_size=100,
        parsed_year=2026,
        parsed_month=2,
        parsed_type="红单",
        parsed_shop="测试店",
        detected_platform="douyin",
        status="uploaded",
    )
    session = _MerchantSession(task, upload_file, Platform(id=1, code="douyin", name="抖音", status=1))

    monkeypatch.setattr(database_module, "async_session_factory", _ProcessFileSessionFactory(session))
    monkeypatch.setattr(oss_service_module.oss_service, "download_to_temp", lambda *_args, **_kwargs: None)

    async def fake_import_red_sheet(*_args, **_kwargs):
        return SimpleNamespace(
            red_sheet_id=88,
            purchase_rows=3,
            payment_rows=2,
            warnings=["提示1"],
            errors=[],
        )

    monkeypatch.setattr(
        "app.services.merchant_reconciliation_service.MerchantReconciliationService.import_red_sheet",
        fake_import_red_sheet,
    )

    task_instance = SimpleNamespace(request=SimpleNamespace(id="celery-task-id"))
    payload = await celery_module._process_merchant_red_sheet_async(
        task_instance,
        task_id=task.id,
        file_id=upload_file.id,
        oss_key="oss-key",
    )

    assert payload is not None
    assert payload["文件类型"] == "红单"
    assert payload["结果摘要"]["文件下载耗时秒"] >= 0
    assert payload["结果摘要"]["文件读取耗时秒"] >= 0
    assert payload["结果摘要"]["导入处理耗时秒"] >= 0
    assert payload["结果摘要"]["结果入库耗时秒"] >= 0
    assert payload["结果摘要"]["任务总耗时秒"] >= 0


@pytest.mark.asyncio
async def test_process_merchant_bank_flow_returns_unified_stage_metrics(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task = _RollbackSensitiveTask()
    upload_file = UploadFile(
        id=456,
        batch_id=1,
        org_id=1,
        user_id=2,
        original_name="2026年02月_银行流水_测试店.xlsx",
        oss_key="oss-key",
        file_size=100,
        parsed_year=2026,
        parsed_month=2,
        parsed_type="银行流水",
        parsed_shop="测试店",
        detected_platform="douyin",
        status="uploaded",
    )
    session = _MerchantSession(task, upload_file, Platform(id=1, code="douyin", name="抖音", status=1))

    monkeypatch.setattr(database_module, "async_session_factory", _ProcessFileSessionFactory(session))
    monkeypatch.setattr(oss_service_module.oss_service, "download_to_temp", lambda *_args, **_kwargs: None)

    async def fake_import_bank_flow(*_args, **_kwargs):
        return SimpleNamespace(
            bank_flow_file_id=66,
            row_count=7,
            matched_row_count=5,
            warnings=["提示1"],
            errors=[],
        )

    monkeypatch.setattr(
        "app.services.merchant_reconciliation_service.MerchantReconciliationService.import_bank_flow",
        fake_import_bank_flow,
    )

    task_instance = SimpleNamespace(request=SimpleNamespace(id="celery-task-id"))
    payload = await celery_module._process_merchant_bank_flow_async(
        task_instance,
        task_id=task.id,
        file_id=upload_file.id,
        oss_key="oss-key",
    )

    assert payload is not None
    assert payload["文件类型"] == "银行流水"
    assert payload["结果摘要"]["文件下载耗时秒"] >= 0
    assert payload["结果摘要"]["导入处理耗时秒"] >= 0
    assert payload["结果摘要"]["结果入库耗时秒"] >= 0
    assert payload["结果摘要"]["任务总耗时秒"] >= 0


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
