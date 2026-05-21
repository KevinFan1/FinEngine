from datetime import datetime, timezone
from decimal import Decimal

from openpyxl import load_workbook

from app.models.transaction_accounting import TransactionDetail
from app.services.transaction_accounting_service import TransactionAccountingService


def test_detail_export_headers_skip_upload_month_and_include_total_category() -> None:
    update_time = datetime(2026, 5, 20, 9, 30, 15, tzinfo=timezone.utc)
    detail = TransactionDetail(
        id=1,
        task_id=10,
        file_id=20,
        org_id=30,
        subject_id=40,
        category_id=50,
        rule_id=60,
        row_number=1,
        platform_code="douyin",
        shop_name="云上织高端定制店",
        accounting_year=2026,
        accounting_month=4,
        transaction_direction="入账",
        remark="订单结算",
        amount_field="动账金额",
        original_amount=Decimal("120.25"),
        calculated_amount=Decimal("120.25"),
        status="matched",
        error_message=None,
        raw_row={},
    )
    detail.cash_flow_group_name = "经营活动现金流入"
    detail.subject_name = "收到其他与经营相关的收入"
    detail.category_name = "平台补贴"
    detail.update_time = update_time

    workbook_buffer = TransactionAccountingService._build_detail_workbook([detail])
    workbook = load_workbook(workbook_buffer)
    worksheet = workbook.active

    assert [cell.value for cell in worksheet[1]] == [
        "序号",
        "业务年月",
        "平台",
        "店铺",
        "总分类",
        "科目",
        "重分类",
        "汇总数值",
        "最新统计时间",
    ]
    assert [cell.value for cell in worksheet[2]] == [
        1,
        "2026-04",
        "抖音",
        "云上织高端定制店",
        "经营活动现金流入",
        "收到其他与经营相关的收入",
        "平台补贴",
        120.25,
        "2026-05-20 17:30:15",
    ]
