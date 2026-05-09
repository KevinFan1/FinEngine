from types import SimpleNamespace
from datetime import datetime
from decimal import Decimal

from app.tasks.celery_app import _group_return_cost_by_order_created_time, _infer_file_type


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
