from decimal import Decimal
from pathlib import Path

from openpyxl import Workbook

from app.tasks.processors.alipay import ALIPAY_DONGZHANG_HEADERS, alipay_processor


def _write_workbook_with_preface(path: Path, headers: list[str], rows: list[list[object]]) -> None:
    wb = Workbook()
    ws = wb.active
    ws.append(["支付宝账单"])
    ws.append(["说明：前两行为导出说明"])
    ws.append(headers)
    for row in rows:
        ws.append(row)
    wb.save(path)
    wb.close()


def _row(headers: list[str], **overrides: object) -> list[object]:
    values = {header: None for header in headers}
    values.update(overrides)
    return [values[header] for header in headers]


def test_alipay_dongzhang_uses_third_row_header_and_trade_month(tmp_path: Path) -> None:
    file_path = tmp_path / "alipay_dongzhang.xlsx"
    long_trade_no = "202604" + ("1" * 23)
    _write_workbook_with_preface(
        file_path,
        ALIPAY_DONGZHANG_HEADERS,
        [
            _row(
                ALIPAY_DONGZHANG_HEADERS,
                支付宝交易号="2026041234567890123456789012",
                账务类型="在线支付",
                **{"收入（+元）": "100.50"},
            ),
            _row(
                ALIPAY_DONGZHANG_HEADERS,
                支付宝交易号="2026042234567890123456789012",
                账务类型="退款（交易退款）",
                **{"支出（-元）": "20.00"},
            ),
            _row(
                ALIPAY_DONGZHANG_HEADERS,
                支付宝交易号="2026043234567890123456789012",
                业务描述="其他收入-百亿补贴激励前返",
                **{"收入（+元）": "8.00", "支出（-元）": "1.50"},
            ),
            _row(
                ALIPAY_DONGZHANG_HEADERS,
                支付宝交易号="2026044234567890123456789012",
                业务描述="其他支出-百亿补贴预收",
                **{"收入（+元）": "1.00", "支出（-元）": "9.00"},
            ),
            _row(
                ALIPAY_DONGZHANG_HEADERS,
                支付宝交易号=long_trade_no,
                备注="淘宝客佣金代扣款",
                **{"收入（+元）": "2.00", "支出（-元）": "7.00"},
            ),
            _row(
                ALIPAY_DONGZHANG_HEADERS,
                支付宝交易号=long_trade_no,
                业务描述="软件服务费",
                **{"收入（+元）": "1.00", "支出（-元）": "4.00"},
            ),
            _row(
                ALIPAY_DONGZHANG_HEADERS,
                支付宝交易号=long_trade_no,
                业务描述="",
                备注="百亿补贴软件服务费",
                **{"收入（+元）": "0.50", "支出（-元）": "3.00"},
            ),
        ],
    )

    result = alipay_processor.process(str(file_path), shop_name="支付宝店铺", type_code="动账")

    assert result["total_rows"] == 7
    assert result["success_rows"] == 7
    assert result["failed_rows"] == 0
    assert set(result["groups"]) == {"支付宝店铺|2026|4", "支付宝店铺|2026|3"}

    april = result["groups"]["支付宝店铺|2026|4"]
    assert april["gmv"] == Decimal("80.50")
    assert april["platform_income"] == Decimal("6.50")
    assert april["platform_fee"] == Decimal("0")
    assert april["return_cost"] == Decimal("8.00")

    march = result["groups"]["支付宝店铺|2026|3"]
    assert march["platform_fee"] == Decimal("-10.50")
    assert march["gmv"] == Decimal("0")
    assert march["platform_income"] == Decimal("0")


def test_alipay_dongzhang_fails_when_trade_no_cannot_parse_month(tmp_path: Path) -> None:
    file_path = tmp_path / "alipay_invalid_trade_no.xlsx"
    _write_workbook_with_preface(
        file_path,
        ALIPAY_DONGZHANG_HEADERS,
        [
            _row(
                ALIPAY_DONGZHANG_HEADERS,
                支付宝交易号="invalid",
                账务类型="在线支付",
                **{"收入（+元）": "100"},
            ),
        ],
    )

    result = alipay_processor.process(str(file_path), shop_name="支付宝店铺", type_code="动账")

    assert result["total_rows"] == 1
    assert result["success_rows"] == 0
    assert result["failed_rows"] == 1
    assert result["groups"] == {}
