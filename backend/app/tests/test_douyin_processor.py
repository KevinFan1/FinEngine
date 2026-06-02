from decimal import Decimal
from datetime import datetime
from pathlib import Path

import pytest
from openpyxl import Workbook

from app.models.shop import Shop
from app.models.summary import FinancialSummary
from app.tasks.aggregation import AggregationService
from app.tasks.processors.douyin import (
    DOUYIN_BIC_HEADERS,
    DOUYIN_DONGZHANG_HEADERS,
    DOUYIN_ORDER_HEADERS,
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
                备注="仲裁申诉通过打款",
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
    assert result["detail_rows"][0]["summary_year"] == 2026
    assert result["detail_rows"][0]["summary_month"] == 4
    assert result["detail_rows"][0]["period_source"] == "transaction_time_previous_month"
    assert len(result["detail_rows"][0]["period_source"]) > 30
    agg = result["groups"]["抖音店铺|2026|4"]
    assert agg["gmv"] == Decimal("80")
    assert agg["order_paid_amount"] == Decimal("100")
    assert agg["refund_amount"] == Decimal("20")
    assert agg["platform_income"] == Decimal("6")
    assert agg["platform_fee"] == Decimal("5")
    assert agg["return_cost"] == Decimal("3")
    assert agg["commission"] == Decimal("6")
    assert agg["merchant_fee"] == Decimal("7")
    assert agg["promotion_fee"] == Decimal("8")
    assert agg["provider_commission"] == Decimal("9")
    assert "donation_fee" not in agg


def test_douyin_dongzhang_computes_paid_refund_and_positive_fee_totals(tmp_path: Path) -> None:
    file_path = tmp_path / "douyin_positive_fees.xlsx"
    _write_workbook(
        file_path,
        DOUYIN_DONGZHANG_HEADERS,
        [
            _row(
                DOUYIN_DONGZHANG_HEADERS,
                下单时间="2026-05-01 10:00:00",
                动账时间="2026-05-02 10:00:00",
                动账方向="入账",
                备注="订单结算",
                动账金额="0",
                订单实付应结="100",
                订单退款="-20",
                平台服务费="0",
                佣金="-10",
                招商服务费="-8",
                站外推广费="-6",
                服务商佣金="-4",
            ),
            _row(
                DOUYIN_DONGZHANG_HEADERS,
                下单时间="2026-05-01 10:00:00",
                动账时间="2026-05-02 10:00:00",
                动账方向="入账",
                备注="下单返现金活动追缴用户后商家退回平台返现金额",
                动账金额="5",
                订单实付应结="0",
                订单退款="0",
                平台服务费="0",
                佣金="3",
                招商服务费="2",
                站外推广费="1",
                服务商佣金="0.5",
            ),
            _row(
                DOUYIN_DONGZHANG_HEADERS,
                下单时间="2026-05-01 10:00:00",
                动账时间="2026-05-02 10:00:00",
                动账方向="出账",
                备注="下单返现金活动追缴用户后商家退回平台返现金额",
                动账金额="11",
                订单实付应结="0",
                订单退款="0",
                平台服务费="0",
            ),
            _row(
                DOUYIN_DONGZHANG_HEADERS,
                下单时间="2026-05-01 10:00:00",
                动账时间="2026-05-02 10:00:00",
                动账方向="出账",
                备注="退款转赔付",
                动账金额="3",
                订单实付应结="0",
                订单退款="0",
                平台服务费="0",
            ),
        ],
    )

    result = douyin_processor.process(str(file_path), shop_name="抖音店铺", type_code="动账")

    assert result["success_rows"] == 4
    agg = result["groups"]["抖音店铺|2026|5"]
    assert agg["order_paid_amount"] == Decimal("95")
    assert agg["refund_amount"] == Decimal("23")
    assert agg["gmv"] == Decimal("72")
    assert agg["commission"] == Decimal("7")
    assert agg["merchant_fee"] == Decimal("6")
    assert agg["promotion_fee"] == Decimal("5")
    assert agg["provider_commission"] == Decimal("3.5")


def test_douyin_dongzhang_strips_excel_text_prefix_from_detail_fields(tmp_path: Path) -> None:
    file_path = tmp_path / "douyin_text_prefix.xlsx"
    _write_workbook(
        file_path,
        DOUYIN_DONGZHANG_HEADERS,
        [
            _row(
                DOUYIN_DONGZHANG_HEADERS,
                下单时间="2026-04-01 01:17:24",
                动账时间="2026-04-02 10:00:00",
                动帐流水号="'2026040101172401977718277000",
                动账方向="入账",
                动账金额="83.16",
                动账账户="聚合账户",
                动账场景="货款结算入账",
                计费类型="精选联盟",
                子订单号="'6925040387642719692",
                订单号="'6925040387642719692",
                订单实付应结="83.16",
                订单退款="0",
                平台服务费="0",
                佣金="0",
                招商服务费="0",
                站外推广费="0",
                服务商佣金="0",
            )
        ],
    )

    result = douyin_processor.process(str(file_path), shop_name="抖音店铺", type_code="动账")

    assert result["success_rows"] == 1
    detail_row = result["detail_rows"][0]
    assert detail_row["transaction_flow_no"] == "2026040101172401977718277000"
    assert detail_row["sub_order_no"] == "6925040387642719692"
    assert detail_row["order_no"] == "6925040387642719692"


def test_douyin_dongzhang_extracts_product_code(tmp_path: Path) -> None:
    file_path = tmp_path / "douyin_product_code.xlsx"
    _write_workbook(
        file_path,
        DOUYIN_DONGZHANG_HEADERS,
        [
            _row(
                DOUYIN_DONGZHANG_HEADERS,
                下单时间="2026-04-01 01:17:24",
                动账时间="2026-04-02 10:00:00",
                动账方向="入账",
                动账金额="83.16",
                动账场景="货款结算入账",
                商品名称="足金项链 can123+can456 T20260001",
                订单实付应结="83.16",
                订单退款="0",
                平台服务费="0",
                佣金="0",
                招商服务费="0",
                站外推广费="0",
                服务商佣金="0",
            ),
            _row(
                DOUYIN_DONGZHANG_HEADERS,
                下单时间="2026-04-01 01:17:24",
                动账时间="2026-04-02 10:00:00",
                动账方向="入账",
                动账金额="83.16",
                动账场景="货款结算入账",
                商品名称="淡水珍珠项链-多样性发一件-约4.5mm-V45054-25（东哥）",
                订单实付应结="83.16",
                订单退款="0",
                平台服务费="0",
                佣金="0",
                招商服务费="0",
                站外推广费="0",
                服务商佣金="0",
            )
        ],
    )

    result = douyin_processor.process(str(file_path), shop_name="抖音店铺", type_code="动账")

    assert result["success_rows"] == 2
    assert result["detail_rows"][0]["product_code"] == "CAN123+CAN456,T20260001"
    assert result["detail_rows"][1]["product_code"] == "V45054"


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


def test_douyin_shipping_insurance_supports_discount_header_variant(tmp_path: Path) -> None:
    headers = [
        "投保单号",
        "订单编号",
        "下单时间",
        "承保时间",
        "保险名称",
        "承保保司",
        "保费来源",
        "支付保费",
        "保费状态",
        "动账时间",
        "动账流水号",
        "保险交易单号",
        "平台优惠【营销补贴】",
        "保障额度",
        "保障状态",
        "备注",
        "平台优惠【特殊活动】",
        "平台优惠",
    ]
    file_path = tmp_path / "douyin_insurance_variant.xlsx"
    _write_workbook(
        file_path,
        headers,
        [
            _row(headers, 下单时间="2026-04-03", 支付保费="4.50"),
            _row(headers, 下单时间="2026-04-04", 支付保费="1.20"),
        ],
    )

    result = douyin_processor.process(str(file_path), shop_name="抖音店铺", type_code="运费险")

    assert result["success_rows"] == 2
    assert result["groups"]["抖音店铺|2026|4"]["insurance_fee"] == Decimal("5.70")


def test_douyin_order_extracts_sub_order_time_and_parent_order(tmp_path: Path) -> None:
    file_path = tmp_path / "douyin_order.xlsx"
    _write_workbook(
        file_path,
        DOUYIN_ORDER_HEADERS,
        [
            _row(
                DOUYIN_ORDER_HEADERS,
                主订单编号="P20260515001",
                子订单编号="S20260515001-1",
                订单提交时间="2026-05-14 10:20:30",
            )
        ],
    )

    result = douyin_processor.process(str(file_path), shop_name="抖音店铺", type_code="订单")

    assert result["success_rows"] == 1
    assert result["orders"] == [
        {
            "order_no": "S20260515001-1",
            "order_created_at": datetime(2026, 5, 14, 10, 20, 30),
            "extra_data": {"主订单编号": "P20260515001"},
        }
    ]


@pytest.mark.asyncio
async def test_douyin_order_paid_and_refund_amounts_are_persisted() -> None:
    summary = FinancialSummary(
        org_id=1,
        shop_id=1,
        summary_year=2026,
        summary_month=5,
        source_platform_code="douyin",
        report_platform_code="douyin",
        platform_name="douyin",
        shop_name="抖音店铺",
        order_paid_amount=Decimal("0"),
        refund_amount=Decimal("0"),
        commission=Decimal("0"),
        merchant_fee=Decimal("0"),
        promotion_fee=Decimal("0"),
        provider_commission=Decimal("0"),
        source_file_ids=[1],
    )
    shop = Shop(id=1, org_id=1, platform_name="douyin", shop_name="抖音店铺")

    class FakeResult:
        def __init__(self, value):
            self.value = value

        def scalar_one_or_none(self):
            return self.value

    class FakeSession:
        def __init__(self):
            self.calls = 0

        async def execute(self, _stmt):
            self.calls += 1
            return FakeResult(shop if self.calls == 1 else summary)

        async def flush(self):
            return None

    await AggregationService.upsert_summary_dict(
        FakeSession(),
        org_id=1,
        shop_id=1,
        year=2026,
        month=5,
        platform_name="douyin",
        shop_name="抖音店铺",
        values={
            "order_paid_amount": Decimal("95"),
            "refund_amount": Decimal("-23"),
            "commission": Decimal("-7"),
            "merchant_fee": Decimal("-6"),
            "promotion_fee": Decimal("-5"),
            "provider_commission": Decimal("-3.5"),
        },
        source_file_id=2,
    )

    assert summary.order_paid_amount == Decimal("95")
    assert summary.refund_amount == Decimal("23")
    assert summary.commission == Decimal("7")
    assert summary.merchant_fee == Decimal("6")
    assert summary.promotion_fee == Decimal("5")
    assert summary.provider_commission == Decimal("3.5")
