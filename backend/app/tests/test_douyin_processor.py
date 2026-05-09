from decimal import Decimal
from pathlib import Path

from openpyxl import Workbook

from app.tasks.processors.douyin import (
    DOUYIN_BIC_HEADERS,
    DOUYIN_DONGZHANG_HEADERS,
    DOUYIN_SHIPPING_INSURANCE_HEADERS,
    douyin_processor,
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


def test_douyin_dongzhang_preserves_platform_formulas(tmp_path: Path) -> None:
    file_path = tmp_path / "douyin.xlsx"
    _write_workbook(
        file_path,
        DOUYIN_DONGZHANG_HEADERS,
        [
            _row(
                DOUYIN_DONGZHANG_HEADERS,
                动账时间="2026-05-01 00:00:00",
                备注="售后单仲裁申诉通过打款",
                动账金额="3",
                订单实付应结="100",
                订单退款="-20",
                实际平台补贴="1",
                实际抖音支付补贴="2",
                实际抖音月付营销补贴="3",
                平台服务费="-5",
                佣金="6",
                招商服务费="7",
                站外推广费="8",
                服务商佣金="9",
            )
        ],
    )

    result = douyin_processor.process(
        str(file_path),
        shop_name="抖音店铺",
        type_code="动账",
        category_dict={"赔付": ["仲裁申诉通过打款"]},
    )

    assert result["success_rows"] == 1
    agg = result["groups"]["抖音店铺|2026|4"]
    assert agg["gmv"] == Decimal("80")
    assert agg["platform_income"] == Decimal("6")
    assert agg["platform_fee"] == Decimal("5")
    assert agg["return_cost"] == Decimal("3")
    assert agg["commission"] == Decimal("6")
    assert agg["merchant_fee"] == Decimal("7")
    assert agg["promotion_fee"] == Decimal("8")
    assert agg["provider_commission"] == Decimal("9")
    assert "donation_fee" not in agg


def test_douyin_simple_monthly_sum_types(tmp_path: Path) -> None:
    bic_path = tmp_path / "douyin_bic.xlsx"
    _write_workbook(
        bic_path,
        DOUYIN_BIC_HEADERS,
        [_row(DOUYIN_BIC_HEADERS, 业务发生时间="2026-04-02 12:00:00", 结算金额="12.30")],
    )

    insurance_path = tmp_path / "douyin_insurance.xlsx"
    _write_workbook(
        insurance_path,
        DOUYIN_SHIPPING_INSURANCE_HEADERS,
        [_row(DOUYIN_SHIPPING_INSURANCE_HEADERS, 下单时间="2026-04-03", 支付保费="4.50")],
    )

    bic_result = douyin_processor.process(str(bic_path), shop_name="抖音店铺", type_code="bic")
    insurance_result = douyin_processor.process(str(insurance_path), shop_name="抖音店铺", type_code="运费险")

    assert bic_result["groups"]["抖音店铺|2026|4"]["bic"] == Decimal("12.30")
    assert insurance_result["groups"]["抖音店铺|2026|4"]["insurance_fee"] == Decimal("4.50")
