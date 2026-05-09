import csv
from decimal import Decimal
from pathlib import Path
from zipfile import ZipFile

import pytest
from openpyxl import Workbook

from app.models.shop import Shop
from app.models.summary import FinancialSummary
from app.tasks.aggregation import AggregationService
from app.tasks.processors.kuaishou import (
    KUAISHOU_DONGZHANG_HEADERS,
    KUAISHOU_GMV_HEADERS,
    KUAISHOU_ORDER_HEADERS,
    KUAISHOU_SHIPPING_INSURANCE_HEADERS,
    kuaishou_processor,
)


def _write_workbook(path: Path, rows: list[list[object]]) -> None:
    wb = Workbook()
    ws = wb.active
    ws.append(KUAISHOU_GMV_HEADERS)
    for row in rows:
        ws.append(row)
    wb.save(path)
    wb.close()


def _write_workbook_with_headers(path: Path, headers: list[str], rows: list[list[object]]) -> None:
    wb = Workbook()
    ws = wb.active
    ws.append(headers)
    for row in rows:
        ws.append(row)
    wb.save(path)
    wb.close()


def _force_bad_xlsx_dimension(path: Path, dimension_ref: str = "A1") -> None:
    with ZipFile(path) as zin:
        entries = {name: zin.read(name) for name in zin.namelist()}

    sheet_name = "xl/worksheets/sheet1.xml"
    sheet_xml = entries[sheet_name].decode("utf-8")
    sheet_xml = sheet_xml.replace('<dimension ref="A1:F3"/>', f'<dimension ref="{dimension_ref}"/>')
    sheet_xml = sheet_xml.replace('<dimension ref="A1:AN2"/>', f'<dimension ref="{dimension_ref}"/>')
    entries[sheet_name] = sheet_xml.encode("utf-8")

    with ZipFile(path, "w") as zout:
        for name, data in entries.items():
            zout.writestr(name, data)


def _write_csv_with_headers(path: Path, headers: list[str], rows: list[list[object]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(headers)
        writer.writerows(rows)


def _write_csv_rows(path: Path, rows: list[list[object]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.writer(file)
        writer.writerows(rows)


def _row(**overrides: object) -> list[object]:
    values = {header: None for header in KUAISHOU_GMV_HEADERS}
    values.update(
        {
            "商家ID": "m-1",
            "订单号": "o-1",
            "商品ID": "sku-1",
            "商品名称": "测试商品",
            "商品数量": 1,
            "订单创建时间": "2026-04-15 10:20:30",
            "订单实付(元)": 100,
            "政府补贴": 1,
            "支付营销补贴": 2,
            "平台补贴": 3,
            "商家补贴(元)": 4,
            "达人补贴": 5,
            "订单退款(元)": 10,
            "支付营销回退（元）": 2,
            "技术服务费(元)": 6,
            "达人佣金(元)": 7,
            "团长佣金(元)": 8,
            "其他收费": 3,
            "实际结算时间": "2026-05-01 00:00:00",
        }
    )
    values.update(overrides)
    return [values[header] for header in KUAISHOU_GMV_HEADERS]


def test_kuaishou_gmv_aggregates_financial_fields(tmp_path: Path) -> None:
    file_path = tmp_path / "kuaishou.xlsx"
    _write_workbook(
        file_path,
        [
            _row(),
            _row(
                商家ID="m-2",
                订单号="o-2",
                订单创建时间="2026/04/20",
                **{
                    "订单实付(元)": "200",
                    "订单退款(元)": "20",
                    "政府补贴": "10",
                    "支付营销补贴": "20",
                    "平台补贴": "30",
                    "商家补贴(元)": "40",
                    "达人补贴": "50",
                    "支付营销回退（元）": "5",
                    "技术服务费(元)": "60",
                    "其他收费": "7",
                    "达人佣金(元)": "70",
                    "团长佣金(元)": "80",
                },
            ),
        ],
    )

    result = kuaishou_processor.process(str(file_path), shop_name="快手店铺", type_code="gmv")

    assert result["total_rows"] == 2
    assert result["success_rows"] == 2
    assert result["failed_rows"] == 0
    assert result["errors"] == []

    agg = result["groups"]["快手店铺|2026|4"]
    assert agg["gmv"] == Decimal("270")
    assert agg["platform_income"] == Decimal("165")
    assert agg["platform_fee"] == Decimal("69")
    assert agg["return_cost"] == Decimal("0")
    assert agg["commission"] == Decimal("165")
    assert agg["merchant_fee"] == Decimal("0")
    assert agg["promotion_fee"] == Decimal("0")
    assert agg["provider_commission"] == Decimal("0")
    assert agg["donation_fee"] == Decimal("0")
    assert "insurance_fee" not in agg
    assert "bic" not in agg


def test_kuaishou_gmv_requires_only_formula_headers(tmp_path: Path) -> None:
    file_path = tmp_path / "kuaishou_minimal_gmv.xlsx"
    headers = [
        "订单创建时间",
        "订单实付(元)",
        "政府补贴",
        "支付营销补贴",
        "平台补贴",
        "商家补贴(元)",
        "达人补贴",
        "订单退款(元)",
        "支付营销回退（元）",
        "技术服务费(元)",
        "达人佣金(元)",
        "团长佣金(元)",
        "其他收费",
    ]
    _write_workbook_with_headers(
        file_path,
        headers,
        [["2026-04-15 10:20:30", "100", "1", "2", "3", "4", "5", "10", "2", "6", "7", "8", "3"]],
    )

    result = kuaishou_processor.process(str(file_path), shop_name="快手店铺", type_code="gmv")

    assert result["errors"] == []
    assert result["groups"]["快手店铺|2026|4"]["gmv"] == Decimal("90")


def test_kuaishou_gmv_accepts_half_width_parentheses_headers(tmp_path: Path) -> None:
    file_path = tmp_path / "kuaishou_half_width_headers.csv"
    headers = [
        "订单创建时间",
        "订单实付(元)",
        "政府补贴",
        "支付营销补贴",
        "平台补贴",
        "商家补贴(元)",
        "达人补贴",
        "订单退款(元)",
        "支付营销回退(元)",
        "技术服务费(元)",
        "达人佣金(元)",
        "团长佣金(元)",
        "其他收费",
    ]
    _write_csv_with_headers(
        file_path,
        headers,
        [["2026-04-15 10:20:30", "100", "1", "2", "3", "4", "5", "10", "2", "6", "7", "8", "3"]],
    )

    result = kuaishou_processor.process(str(file_path), shop_name="快手店铺", type_code="gmv")

    assert result["errors"] == []
    assert result["groups"]["快手店铺|2026|4"]["platform_fee"] == Decimal("7")


def test_kuaishou_year_month_falls_back_to_settlement_time(tmp_path: Path) -> None:
    file_path = tmp_path / "kuaishou_settlement_time.xlsx"
    _write_workbook(
        file_path,
        [
            _row(
                订单创建时间="",
                实际结算时间="2026-03-02 12:00:00",
            )
        ],
    )

    result = kuaishou_processor.process(str(file_path), shop_name="快手店铺", type_code="gmv")

    assert result["success_rows"] == 1
    assert "快手店铺|2026|3" in result["groups"]


def test_kuaishou_dongzhang_aggregates_return_cost_only(tmp_path: Path) -> None:
    file_path = tmp_path / "kuaishou_dongzhang.xlsx"
    _write_workbook_with_headers(
        file_path,
        KUAISHOU_DONGZHANG_HEADERS,
        [
            ["flow-1", "order-1", "2026-04-01 12:00:00", "支", "10.50", "100", "赔付", "desc", "晚揽立赔平台追回"],
            ["flow-2", "order-2", "2026/04/02", "收", "3.25", "103.25", "赔付", "desc", "平台赔付商家"],
            ["flow-3", "order-3", "2026/04/03", "支", "5", "98.25", "其他", "desc", "普通调整"],
        ],
    )

    result = kuaishou_processor.process(
        str(file_path),
        shop_name="快手店铺",
        type_code="动账",
        category_dict={"其他费用": ["晚揽立赔平台追回", "平台赔付商家"]},
    )

    assert result["total_rows"] == 3
    assert result["success_rows"] == 3
    assert result["failed_rows"] == 0
    assert result["errors"] == []
    assert result["groups"] == {}
    assert result["return_cost_rows"] == [
        {"order_no": "order-1", "return_cost": Decimal("-10.50")},
        {"order_no": "order-2", "return_cost": Decimal("3.25")},
    ]


def test_kuaishou_dongzhang_csv_aggregates_return_cost_only(tmp_path: Path) -> None:
    file_path = tmp_path / "kuaishou_dongzhang.csv"
    _write_csv_with_headers(
        file_path,
        KUAISHOU_DONGZHANG_HEADERS,
        [
            ["flow-1", "order-1", "2026-04-01 12:00:00", "支", "10.50", "100", "退款", "desc", "晚揽立赔平台追回"],
            ["flow-2", "order-2", "2026/04/02", "收", "3.25", "103.25", "补偿", "desc", "平台赔付商家"],
        ],
    )

    result = kuaishou_processor.process(
        str(file_path),
        shop_name="快手店铺",
        type_code="动账",
        category_dict={"其他费用": ["晚揽立赔平台追回", "平台赔付商家"]},
    )

    assert result["success_rows"] == 2
    assert result["return_cost_rows"] == [
        {"order_no": "order-1", "return_cost": Decimal("-10.50")},
        {"order_no": "order-2", "return_cost": Decimal("3.25")},
    ]


def test_kuaishou_shipping_insurance_aggregates_insurance_fee(tmp_path: Path) -> None:
    file_path = tmp_path / "kuaishou_shipping_insurance.xlsx"
    _write_workbook_with_headers(
        file_path,
        KUAISHOU_SHIPPING_INSURANCE_HEADERS,
        [
            ["order-1", "2.00", "1.25", "0.75", "2026-04-01 12:00:00", "fee-1"],
            ["order-2", "3.00", "2.50", "0.50", "2026/04/02", "fee-2"],
        ],
    )

    result = kuaishou_processor.process(str(file_path), shop_name="快手店铺", type_code="运费险")

    assert result["total_rows"] == 2
    assert result["success_rows"] == 2
    assert result["failed_rows"] == 0
    assert result["errors"] == []
    assert result["groups"] == {}
    assert result["insurance_fee_rows"] == [
        {"order_no": "order-1", "insurance_fee": Decimal("1.25")},
        {"order_no": "order-2", "insurance_fee": Decimal("2.50")},
    ]


def test_kuaishou_shipping_insurance_reads_bad_xlsx_dimension(tmp_path: Path) -> None:
    file_path = tmp_path / "kuaishou_shipping_insurance_bad_dimension.xlsx"
    _write_workbook_with_headers(
        file_path,
        KUAISHOU_SHIPPING_INSURANCE_HEADERS,
        [
            ["order-1", "2.00", "1.25", "0.75", "2026-04-01 12:00:00", "fee-1"],
            ["order-2", "3.00", "2.50", "0.50", "2026/04/02", "fee-2"],
        ],
    )
    _force_bad_xlsx_dimension(file_path)

    result = kuaishou_processor.process(str(file_path), shop_name="快手店铺", type_code="运费险")

    assert result["errors"] == []
    assert result["insurance_fee_rows"] == [
        {"order_no": "order-1", "insurance_fee": Decimal("1.25")},
        {"order_no": "order-2", "insurance_fee": Decimal("2.50")},
    ]


def test_kuaishou_shipping_insurance_csv_aggregates_insurance_fee(tmp_path: Path) -> None:
    file_path = tmp_path / "kuaishou_shipping_insurance.csv"
    _write_csv_rows(
        file_path,
        [
            ["快手运费险账单", "", "", "", "", ""],
            KUAISHOU_SHIPPING_INSURANCE_HEADERS,
            ["order-1", "2.00", "1.25", "0.75", "2026-04-01 12:00:00", "fee-1"],
            ["order-2", "3.00", "2.50", "0.50", "2026/04/02", "fee-2"],
        ],
    )

    result = kuaishou_processor.process(str(file_path), shop_name="快手店铺", type_code="运费险")

    assert result["success_rows"] == 2
    assert result["insurance_fee_rows"] == [
        {"order_no": "order-1", "insurance_fee": Decimal("1.25")},
        {"order_no": "order-2", "insurance_fee": Decimal("2.50")},
    ]


def test_kuaishou_order_extracts_order_created_times(tmp_path: Path) -> None:
    file_path = tmp_path / "kuaishou_order.xlsx"
    _write_workbook_with_headers(
        file_path,
        KUAISHOU_ORDER_HEADERS,
        [
            ["order-1", "", "", "2026-04-01 12:00:00", *[""] * (len(KUAISHOU_ORDER_HEADERS) - 4)],
            ["order-2", "", "", "2026/04/02", *[""] * (len(KUAISHOU_ORDER_HEADERS) - 4)],
            ["", "", "", "2026/04/03", *[""] * (len(KUAISHOU_ORDER_HEADERS) - 4)],
        ],
    )

    result = kuaishou_processor.process(str(file_path), shop_name="快手店铺", type_code="订单")

    assert result["total_rows"] == 3
    assert result["success_rows"] == 2
    assert result["failed_rows"] == 1
    assert result["groups"] == {}
    assert [row["order_no"] for row in result["orders"]] == ["order-1", "order-2"]
    assert result["orders"][0]["order_created_at"].year == 2026
    assert result["orders"][0]["order_created_at"].month == 4


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("values", "expected_field", "expected_value"),
    [
        ({"return_cost": Decimal("-7.25")}, "return_cost", Decimal("-7.25")),
        ({"insurance_fee": Decimal("3.75")}, "insurance_fee", Decimal("3.75")),
    ],
)
async def test_kuaishou_partial_type_does_not_overwrite_gmv_fields(
    values: dict[str, Decimal],
    expected_field: str,
    expected_value: Decimal,
) -> None:
    summary = FinancialSummary(
        org_id=1,
        shop_id=1,
        summary_year=2026,
        summary_month=4,
        platform_name="kuaishou",
        shop_name="快手店铺",
        gmv=Decimal("270"),
        platform_income=Decimal("165"),
        platform_fee=Decimal("69"),
        commission=Decimal("165"),
        return_cost=Decimal("0"),
        insurance_fee=Decimal("0"),
        source_file_ids=[1],
    )
    shop = Shop(id=1, org_id=1, platform_name="kuaishou", shop_name="快手店铺")

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
        month=4,
        platform_name="kuaishou",
        shop_name="快手店铺",
        values=values,
        source_file_id=2,
    )

    assert summary.gmv == Decimal("270")
    assert summary.platform_income == Decimal("165")
    assert summary.platform_fee == Decimal("69")
    assert summary.commission == Decimal("165")
    assert getattr(summary, expected_field) == expected_value
