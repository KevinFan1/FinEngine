from decimal import Decimal
from pathlib import Path

from openpyxl import Workbook

from app.tasks.processors.qianniu import (
    QIANNIU_DONGZHANG_HEADERS,
    QIANNIU_ORDER_HEADERS,
    QIANNIU_ORDER_SUMMARY_FIELDS,
    qianniu_processor,
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


def test_qianniu_order_extracts_order_created_times(tmp_path: Path) -> None:
    file_path = tmp_path / "qianniu_order.xlsx"
    _write_workbook(
        file_path,
        QIANNIU_ORDER_HEADERS,
        [
            _row(QIANNIU_ORDER_HEADERS, 订单编号="qn-1", 订单创建时间="2026-04-01 12:00:00"),
            _row(QIANNIU_ORDER_HEADERS, 订单编号="qn-2", 订单创建时间="2026/04/02"),
            _row(QIANNIU_ORDER_HEADERS, 订单编号="", 订单创建时间="2026/04/03"),
        ],
    )

    result = qianniu_processor.process(str(file_path), shop_name="千牛店铺", type_code="订单")

    assert result["total_rows"] == 3
    assert result["success_rows"] == 2
    assert result["failed_rows"] == 1
    assert result["groups"] == {}
    assert [row["order_no"] for row in result["orders"]] == ["qn-1", "qn-2"]
    assert result["orders"][0]["order_created_at"].year == 2026
    assert result["orders"][0]["order_created_at"].month == 4


def test_qianniu_order_reads_html_table_xls_export(tmp_path: Path) -> None:
    file_path = tmp_path / "qianniu_order.xls"
    headers = "".join(f"<th>{header}</th>" for header in QIANNIU_ORDER_HEADERS)
    row = _row(QIANNIU_ORDER_HEADERS, 订单编号="qn-html-1", 订单创建时间="2026-04-01 12:00:00")
    cells = "".join(f"<td>{cell or ''}</td>" for cell in row)
    file_path.write_text(f"<html><body><table><tr>{headers}</tr><tr>{cells}</tr></table></body></html>", encoding="gb18030")

    result = qianniu_processor.process(str(file_path), shop_name="千牛店铺", type_code="订单")

    assert result["total_rows"] == 1
    assert result["success_rows"] == 1
    assert result["failed_rows"] == 0
    assert result["orders"][0]["order_no"] == "qn-html-1"
    assert result["orders"][0]["order_created_at"].year == 2026


def test_qianniu_dongzhang_returns_order_summary_rows(tmp_path: Path) -> None:
    file_path = tmp_path / "qianniu_dongzhang.xlsx"
    _write_workbook(
        file_path,
        QIANNIU_DONGZHANG_HEADERS,
        [
            _row(QIANNIU_DONGZHANG_HEADERS, 支付流水号="f1", 主订单id="qn-1", 入帐类型="交易收款", **{"收入金额(元)": "100.50"}),
            _row(QIANNIU_DONGZHANG_HEADERS, 支付流水号="f2", 主订单id="qn-1", 入帐类型="交易收款", **{"支出金额(元)": "20"}),
            _row(QIANNIU_DONGZHANG_HEADERS, 支付流水号="f6", 主订单id="qn-1", 入帐类型="交易退款(售后)", **{"支出金额(元)": "15.25"}),
            _row(QIANNIU_DONGZHANG_HEADERS, 支付流水号="f3", 主订单id="qn-1", 入帐类型="服务费", **{"收入金额(元)": "1.00", "支出金额(元)": "4.50"}),
            _row(QIANNIU_DONGZHANG_HEADERS, 支付流水号="f4", 主订单id="qn-2", 入帐类型="其他", **{"收入金额(元)": "8"}),
            _row(QIANNIU_DONGZHANG_HEADERS, 支付流水号="f5", 主订单id="", 入帐类型="交易收款", **{"收入金额(元)": "9"}),
        ],
    )

    result = qianniu_processor.process(str(file_path), shop_name="千牛店铺", type_code="动账")

    assert result["total_rows"] == 6
    assert result["success_rows"] == 5
    assert result["failed_rows"] == 1
    assert result["groups"] == {}
    assert result["order_summary_fields"] == list(QIANNIU_ORDER_SUMMARY_FIELDS)
    assert result["order_summary_fields"][:2] == ["order_paid_amount", "refund_amount"]
    assert result["order_summary_rows"] == [
        {"order_no": "qn-1", "order_paid_amount": Decimal("100.50"), "gmv": Decimal("100.50")},
        {"order_no": "qn-1", "order_paid_amount": Decimal("0"), "gmv": Decimal("-20")},
        {"order_no": "qn-1", "refund_amount": Decimal("15.25")},
        {"order_no": "qn-1", "platform_fee": Decimal("-3.50")},
    ]
