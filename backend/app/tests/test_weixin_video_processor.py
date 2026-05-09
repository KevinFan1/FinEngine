from datetime import datetime
from decimal import Decimal
from pathlib import Path

from openpyxl import Workbook

from app.tasks.celery_app import _group_summary_rows_by_order_created_time
from app.tasks.processors.weixin_video import (
    WEIXIN_VIDEO_BIC_HEADERS,
    WEIXIN_VIDEO_DONGZHANG_HEADERS,
    WEIXIN_VIDEO_ORDER_HEADERS,
    WEIXIN_VIDEO_ORDER_SUMMARY_FIELDS,
    weixin_video_processor,
)


def _write_workbook(path: Path, headers: list[str], rows: list[list[object]]) -> None:
    wb = Workbook()
    ws = wb.active
    ws.append(headers)
    for row in rows:
        ws.append(row)
    wb.save(path)
    wb.close()


def _row(headers: list[str], **overrides: object) -> list[object]:
    values = {header: None for header in headers}
    values.update(overrides)
    return [values[header] for header in headers]


def test_weixin_video_order_extracts_order_created_times(tmp_path: Path) -> None:
    file_path = tmp_path / "weixin_video_order.xlsx"
    _write_workbook(
        file_path,
        WEIXIN_VIDEO_ORDER_HEADERS,
        [
            _row(WEIXIN_VIDEO_ORDER_HEADERS, 订单号="wx-1", 订单下单时间="2026-04-01 12:00:00"),
            _row(WEIXIN_VIDEO_ORDER_HEADERS, 订单号="wx-2", 订单下单时间="2026/04/02"),
            _row(WEIXIN_VIDEO_ORDER_HEADERS, 订单号="", 订单下单时间="2026/04/03"),
        ],
    )

    result = weixin_video_processor.process(str(file_path), shop_name="微信小店", type_code="订单")

    assert result["total_rows"] == 3
    assert result["success_rows"] == 2
    assert result["failed_rows"] == 1
    assert result["groups"] == {}
    assert [row["order_no"] for row in result["orders"]] == ["wx-1", "wx-2"]
    assert result["orders"][0]["order_created_at"].year == 2026
    assert result["orders"][0]["order_created_at"].month == 4


def test_weixin_video_dongzhang_returns_order_summary_rows(tmp_path: Path) -> None:
    file_path = tmp_path / "weixin_video_dongzhang.xlsx"
    _write_workbook(
        file_path,
        WEIXIN_VIDEO_DONGZHANG_HEADERS,
        [
            _row(WEIXIN_VIDEO_DONGZHANG_HEADERS, 流水单号="f1", 动帐类型="订单支付", 收支金额="100.50", 关联订单号="wx-1"),
            _row(WEIXIN_VIDEO_DONGZHANG_HEADERS, 流水单号="f2", 动帐类型="订单退款", 收支金额="20", 关联订单号="wx-1"),
            _row(WEIXIN_VIDEO_DONGZHANG_HEADERS, 流水单号="f3", 动帐类型="技术服务费", 收支金额="-3.50", 关联订单号="wx-1"),
            _row(WEIXIN_VIDEO_DONGZHANG_HEADERS, 流水单号="f4", 动帐类型="达人佣金", 收支金额="-8", 关联订单号="wx-2"),
            _row(WEIXIN_VIDEO_DONGZHANG_HEADERS, 流水单号="f5", 动帐类型="提现", 收支金额="-1", 关联订单号="wx-2"),
        ],
    )

    result = weixin_video_processor.process(str(file_path), shop_name="微信小店", type_code="动账")

    assert result["total_rows"] == 5
    assert result["success_rows"] == 5
    assert result["failed_rows"] == 0
    assert result["groups"] == {}
    assert result["order_summary_fields"] == list(WEIXIN_VIDEO_ORDER_SUMMARY_FIELDS)
    assert result["order_summary_rows"] == [
        {"order_no": "wx-1", "gmv": Decimal("100.50")},
        {"order_no": "wx-1", "gmv": Decimal("-20")},
        {"order_no": "wx-1", "platform_fee": Decimal("3.50")},
        {"order_no": "wx-2", "commission": Decimal("8")},
    ]


def test_weixin_video_bic_returns_shipped_bic_rows(tmp_path: Path) -> None:
    file_path = tmp_path / "weixin_video_bic.xlsx"
    _write_workbook(
        file_path,
        WEIXIN_VIDEO_BIC_HEADERS,
        [
            _row(WEIXIN_VIDEO_BIC_HEADERS, 订单编号="wx-1", 质检状态="已发货", 实扣合计="12.30"),
            _row(WEIXIN_VIDEO_BIC_HEADERS, 订单编号="wx-2", 质检状态="待发货", 实扣合计="4.50"),
            _row(WEIXIN_VIDEO_BIC_HEADERS, 订单编号="wx-3", 质检状态="已发货", 实扣合计="7.70"),
        ],
    )

    result = weixin_video_processor.process(str(file_path), shop_name="微信小店", type_code="bic")

    assert result["total_rows"] == 3
    assert result["success_rows"] == 3
    assert result["failed_rows"] == 0
    assert result["groups"] == {}
    assert result["bic_rows"] == [
        {"order_no": "wx-1", "bic": Decimal("12.30")},
        {"order_no": "wx-3", "bic": Decimal("7.70")},
    ]


def test_weixin_video_shipping_insurance_returns_zero_placeholder(tmp_path: Path) -> None:
    file_path = tmp_path / "placeholder.xlsx"
    file_path.write_bytes(b"")

    result = weixin_video_processor.process(str(file_path), shop_name="微信小店", type_code="运费险")

    assert result["total_rows"] == 0
    assert result["success_rows"] == 0
    assert result["failed_rows"] == 0
    assert result["groups"] == {}
    assert result["insurance_fee_rows"] == []
    assert result["insurance_fee"] == Decimal("0")


def test_group_summary_rows_by_order_created_time_supports_multiple_fields() -> None:
    grouped, missing_order_nos = _group_summary_rows_by_order_created_time(
        [
            {"order_no": "wx-1", "gmv": Decimal("100.50")},
            {"order_no": "wx-1", "gmv": Decimal("-20"), "platform_fee": Decimal("3.50")},
            {"order_no": "wx-2", "commission": Decimal("8")},
            {"order_no": "missing", "gmv": Decimal("5")},
        ],
        order_created_times={
            "wx-1": datetime(2026, 4, 1, 12, 0, 0),
            "wx-2": datetime(2026, 5, 2, 12, 0, 0),
        },
        fields=WEIXIN_VIDEO_ORDER_SUMMARY_FIELDS,
    )

    assert grouped[(2026, 4)]["gmv"] == Decimal("80.50")
    assert grouped[(2026, 4)]["platform_fee"] == Decimal("3.50")
    assert grouped[(2026, 4)]["commission"] == Decimal("0")
    assert grouped[(2026, 5)]["gmv"] == Decimal("0")
    assert grouped[(2026, 5)]["commission"] == Decimal("8")
    assert missing_order_nos == ["missing"]
