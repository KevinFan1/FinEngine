from types import SimpleNamespace
from datetime import datetime
from decimal import Decimal

from app.tasks.celery_app import (
    _build_order_or_fallback_time_summary,
    _group_return_cost_by_order_created_time,
    _group_money_by_order_or_fallback_time,
    _infer_file_type,
)
from app.tasks import celery_app as celery_module


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


def test_mark_task_failed_sets_task_and_upload_file_state() -> None:
    task = SimpleNamespace(status="running", error_message=None, finished_at=None)
    upload_file = SimpleNamespace(status="processing", error_message=None)

    celery_module._mark_task_failed(task, upload_file, "OSS文件不存在")

    assert task.status == "failed"
    assert task.error_message == "OSS文件不存在"
    assert task.finished_at is not None
    assert upload_file.status == "failed"
    assert upload_file.error_message == "OSS文件不存在"


def test_celery_imports_include_bic_task_module() -> None:
    assert "app.tasks.transaction_accounting" in celery_module.celery_app.conf.imports
    assert "app.tasks.bic_accounting" in celery_module.celery_app.conf.imports
