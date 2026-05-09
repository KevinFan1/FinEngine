from decimal import Decimal
from pathlib import Path

import pytest
from openpyxl import Workbook

from app.models.shop import Shop
from app.models.summary import FinancialSummary
from app.tasks.aggregation import AggregationService
from app.tasks.processors.xiaohongshu import (
    XIAOHONGSHU_DONGZHANG_HEADERS,
    XIAOHONGSHU_GMV_HEADERS,
    XIAOHONGSHU_OTHER_SERVICE_HEADERS,
    xiaohongshu_processor,
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


def test_xiaohongshu_gmv_aggregates_and_extracts_order_times(tmp_path: Path) -> None:
    file_path = tmp_path / "xiaohongshu_gmv.xlsx"
    _write_workbook(
        file_path,
        XIAOHONGSHU_GMV_HEADERS,
        [
            _row(
                XIAOHONGSHU_GMV_HEADERS,
                订单号="xhs-1",
                下单时间="2026-04-01 12:00:00",
                **{"商品实付/实退": "100", "平台优惠补贴": "5", "佣金": "3", "分销佣金": "8"},
            ),
            _row(
                XIAOHONGSHU_GMV_HEADERS,
                订单号="xhs-2",
                下单时间="2026/04/02",
                **{"商品实付/实退": "-20", "平台优惠补贴": "1.50", "佣金": "0.50", "分销佣金": "2"},
            ),
        ],
    )

    result = xiaohongshu_processor.process(str(file_path), shop_name="小红书店铺", type_code="gmv")

    assert result["total_rows"] == 2
    assert result["success_rows"] == 2
    assert result["failed_rows"] == 0
    assert [row["order_no"] for row in result["orders"]] == ["xhs-1", "xhs-2"]
    agg = result["groups"]["小红书店铺|2026|4"]
    assert agg["gmv"] == Decimal("80")
    assert agg["platform_income"] == Decimal("6.50")
    assert agg["platform_fee"] == Decimal("3.50")
    assert agg["commission"] == Decimal("10")


def test_xiaohongshu_other_service_extracts_small_payment_rows(tmp_path: Path) -> None:
    file_path = tmp_path / "xiaohongshu_other_service.xlsx"
    _write_workbook(
        file_path,
        XIAOHONGSHU_OTHER_SERVICE_HEADERS,
        [
            _row(XIAOHONGSHU_OTHER_SERVICE_HEADERS, 业务款项="小额打款", 订单号="xhs-1", 动账金额="12.30"),
            _row(XIAOHONGSHU_OTHER_SERVICE_HEADERS, 业务款项="其他", 订单号="xhs-2", 动账金额="9"),
        ],
    )

    result = xiaohongshu_processor.process(str(file_path), shop_name="小红书店铺", type_code="其他服务款")

    assert result["total_rows"] == 2
    assert result["success_rows"] == 2
    assert result["failed_rows"] == 0
    assert result["groups"] == {}
    assert result["return_cost_contribution_rows"] == [{"order_no": "xhs-1", "return_cost": Decimal("12.30")}]


def test_xiaohongshu_dongzhang_extracts_small_receipt_negative_contribution(tmp_path: Path) -> None:
    file_path = tmp_path / "xiaohongshu_dongzhang.xlsx"
    _write_workbook(
        file_path,
        XIAOHONGSHU_DONGZHANG_HEADERS,
        [
            _row(XIAOHONGSHU_DONGZHANG_HEADERS, 交易类型描述="小额收款", **{"收入（元）": "4.50", "支出（元）": "", "业务单号": "xhs-1"}),
            _row(XIAOHONGSHU_DONGZHANG_HEADERS, 交易类型描述="其他", **{"收入（元）": "9", "业务单号": "xhs-2"}),
        ],
    )

    result = xiaohongshu_processor.process(str(file_path), shop_name="小红书店铺", type_code="动账")

    assert result["total_rows"] == 2
    assert result["success_rows"] == 2
    assert result["failed_rows"] == 0
    assert result["groups"] == {}
    assert result["return_cost_contribution_rows"] == [{"order_no": "xhs-1", "return_cost": Decimal("-4.50")}]


async def _run_return_cost_contribution_case(first_value: Decimal, second_value: Decimal) -> FinancialSummary:
    summary = FinancialSummary(
        org_id=1,
        shop_id=1,
        summary_year=2026,
        summary_month=4,
        source_year=2026,
        source_month=4,
        platform_name="xiaohongshu",
        shop_name="小红书店铺",
        return_cost=Decimal("0"),
        source_file_ids=[],
    )
    shop = Shop(id=1, org_id=1, platform_name="xiaohongshu", shop_name="小红书店铺")

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
            return FakeResult(shop if self.calls % 2 == 1 else summary)

        async def flush(self):
            return None

    db = FakeSession()
    await AggregationService.upsert_return_cost_contribution(
        db,
        org_id=1,
        shop_id=1,
        year=2026,
        month=4,
        platform_name="xiaohongshu",
        shop_name="小红书店铺",
        contribution_key="其他服务款",
        return_cost=first_value,
        source_file_id=10,
        source_year=2026,
        source_month=4,
    )
    await AggregationService.upsert_return_cost_contribution(
        db,
        org_id=1,
        shop_id=1,
        year=2026,
        month=4,
        platform_name="xiaohongshu",
        shop_name="小红书店铺",
        contribution_key="动账",
        return_cost=second_value,
        source_file_id=11,
        source_year=2026,
        source_month=4,
    )
    return summary


@pytest.mark.asyncio
async def test_return_cost_contributions_are_summed_by_source_file() -> None:
    summary = await _run_return_cost_contribution_case(Decimal("12.30"), Decimal("-4.50"))

    assert summary.return_cost == Decimal("7.80")
    assert summary.extra_data == {
        "return_cost_contributions": {
            "其他服务款:10": "12.30",
            "动账:11": "-4.50",
        }
    }
    assert summary.source_file_ids == [10, 11]
