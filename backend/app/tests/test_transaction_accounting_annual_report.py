from datetime import datetime
from decimal import Decimal

from openpyxl import load_workbook

from app.models.cash_flow import CashFlowItem
from app.services.transaction_accounting_service import (
    AnnualSummaryAmount,
    TransactionAccountingService,
)


def _cash_item(
    *,
    item_id: int,
    code: str,
    name: str,
    parent_id: int | None,
    level: int,
    item_type: str,
    flow_direction: str | None,
    summary_method: str,
    sort_order: int,
) -> CashFlowItem:
    return CashFlowItem(
        id=item_id,
        code=code,
        name=name,
        parent_id=parent_id,
        level=level,
        item_type=item_type,
        flow_section="operating",
        flow_direction=flow_direction,
        summary_method=summary_method,
        sort_order=sort_order,
        status=1,
        created_at=datetime(2026, 1, 1),
        updated_at=datetime(2026, 1, 1),
    )


def test_annual_report_uses_all_cash_rows_and_sums_parent_from_child_subjects() -> None:
    cash_items = [
        _cash_item(
            item_id=1,
            code="A",
            name="经营性现金流入",
            parent_id=None,
            level=1,
            item_type="group",
            flow_direction="inflow",
            summary_method="sum_children",
            sort_order=10,
        ),
        _cash_item(
            item_id=2,
            code="A4",
            name="收到其他与经营相关的收入",
            parent_id=1,
            level=2,
            item_type="detail",
            flow_direction="inflow",
            summary_method="manual",
            sort_order=14,
        ),
        _cash_item(
            item_id=3,
            code="A7",
            name="收到其他与经营相关的收入",
            parent_id=1,
            level=2,
            item_type="detail",
            flow_direction="inflow",
            summary_method="manual",
            sort_order=17,
        ),
        _cash_item(
            item_id=4,
            code="B",
            name="经营性现金流出",
            parent_id=None,
            level=1,
            item_type="group",
            flow_direction="outflow",
            summary_method="sum_children",
            sort_order=20,
        ),
        _cash_item(
            item_id=5,
            code="B16",
            name="支付抖音提现",
            parent_id=4,
            level=2,
            item_type="detail",
            flow_direction="outflow",
            summary_method="manual",
            sort_order=36,
        ),
    ]
    amounts = [
        AnnualSummaryAmount("收到其他与经营相关的收入", 1, Decimal("889500.88")),
        AnnualSummaryAmount("收到其他与经营相关的收入", 2, Decimal("849530.54")),
        AnnualSummaryAmount("支付抖音提现", 1, Decimal("40056360.62")),
    ]

    rows = TransactionAccountingService._build_annual_report_rows(
        year=2026,
        cash_items=cash_items,
        amounts=amounts,
    )

    by_code = {row.code: row for row in rows}
    assert len(rows) == 5
    assert by_code["A4"].months["202601"] == Decimal("0")
    assert by_code["A7"].months["202601"] == Decimal("889500.88")
    assert by_code["A7"].months["202602"] == Decimal("849530.54")
    assert by_code["A"].months["202601"] == Decimal("889500.88")
    assert by_code["A"].total_amount == Decimal("1739031.42")
    assert by_code["B"].months["202601"] == Decimal("40056360.62")
    assert by_code["B"].total_amount == Decimal("40056360.62")


def test_annual_report_formula_net_rows_use_inflow_minus_outflow() -> None:
    cash_items = [
        _cash_item(
            item_id=1,
            code="A",
            name="经营性现金流入",
            parent_id=None,
            level=1,
            item_type="group",
            flow_direction="inflow",
            summary_method="sum_children",
            sort_order=10,
        ),
        _cash_item(
            item_id=2,
            code="A5",
            name="收到抖音分账款",
            parent_id=1,
            level=2,
            item_type="detail",
            flow_direction="inflow",
            summary_method="manual",
            sort_order=15,
        ),
        _cash_item(
            item_id=3,
            code="B",
            name="经营性现金流出",
            parent_id=None,
            level=1,
            item_type="group",
            flow_direction="outflow",
            summary_method="sum_children",
            sort_order=20,
        ),
        _cash_item(
            item_id=4,
            code="B16",
            name="支付抖音提现",
            parent_id=3,
            level=2,
            item_type="detail",
            flow_direction="outflow",
            summary_method="manual",
            sort_order=36,
        ),
        _cash_item(
            item_id=5,
            code="C",
            name="经营性现金净额",
            parent_id=None,
            level=1,
            item_type="net",
            flow_direction="net",
            summary_method="formula",
            sort_order=50,
        ),
        _cash_item(
            item_id=6,
            code="C1",
            name="经营性现金净额",
            parent_id=5,
            level=2,
            item_type="net",
            flow_direction="net",
            summary_method="formula",
            sort_order=51,
        ),
        _cash_item(
            item_id=7,
            code="C2",
            name="经营性现金净额",
            parent_id=5,
            level=2,
            item_type="net",
            flow_direction="net",
            summary_method="formula",
            sort_order=52,
        ),
    ]
    amounts = [
        AnnualSummaryAmount("收到抖音分账款", 1, Decimal("100.00")),
        AnnualSummaryAmount("支付抖音提现", 1, Decimal("40.00")),
    ]

    rows = TransactionAccountingService._build_annual_report_rows(year=2026, cash_items=cash_items, amounts=amounts)

    by_code = {row.code: row for row in rows}
    assert by_code["C"].months["202601"] == Decimal("60.00")
    assert by_code["C"].total_amount == Decimal("60.00")
    assert by_code["C1"].months["202601"] == Decimal("0")
    assert by_code["C2"].months["202601"] == Decimal("60.00")


def test_annual_report_workbook_uses_month_columns_and_row_total() -> None:
    row = TransactionAccountingService._build_annual_report_rows(
        year=2026,
        cash_items=[
            _cash_item(
                item_id=1,
                code="A",
                name="经营性现金流入",
                parent_id=None,
                level=1,
                item_type="group",
                flow_direction="inflow",
                summary_method="sum_children",
                sort_order=10,
            )
        ],
        amounts=[AnnualSummaryAmount("经营性现金流入", 1, Decimal("12.30"))],
    )[0]

    workbook_buffer = TransactionAccountingService._build_annual_summary_workbook(year=2026, rows=[row])
    workbook = load_workbook(workbook_buffer)
    worksheet = workbook.active

    assert [cell.value for cell in worksheet[1]] == [
        "序号",
        "2026年",
        "202601",
        "202602",
        "202603",
        "202604",
        "202605",
        "202606",
        "202607",
        "202608",
        "202609",
        "202610",
        "202611",
        "202612",
        "合计",
    ]
    assert [cell.value for cell in worksheet[2]] == [
        "A",
        "经营性现金流入",
        12.3,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        12.3,
    ]
