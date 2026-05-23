from decimal import Decimal
from pathlib import Path

from openpyxl import Workbook, load_workbook

from app.models.bic_accounting import BicTask, BicUploadFile
from app.services.bic_accounting_service import BicAccountingService
from app.services.transaction_accounting_service import TransactionAccountingService
from app.tasks.processors.douyin import DOUYIN_BIC_HEADERS


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


def test_bic_accounting_parse_file_keeps_only_quality_inspection_rows(tmp_path: Path) -> None:
    file_path = tmp_path / "douyin_bic_qic.xlsx"
    _write_workbook(
        file_path,
        DOUYIN_BIC_HEADERS,
        [
            _row(DOUYIN_BIC_HEADERS, 费用项="质检费(通过)", 服务商="服务商A", QIC仓="华东仓", 结算金额="12.30"),
            _row(DOUYIN_BIC_HEADERS, 费用项="质检费(拒绝)", 服务商="服务商A", QIC仓="华东仓", 结算金额="99.00"),
            _row(DOUYIN_BIC_HEADERS, 费用项="质检费(通过)", 服务商="服务商B", QIC仓="华南仓", 结算金额="7.70"),
        ],
    )

    result = BicAccountingService.parse_file(str(file_path))

    assert result["total_rows"] == 3
    assert result["success_rows"] == 2
    assert result["failed_rows"] == 0
    assert [(row["service_provider"], row["qic_warehouse"], row["amount"]) for row in result["bic_rows"]] == [
        ("服务商A", "华东仓", Decimal("12.30")),
        ("服务商B", "华南仓", Decimal("7.70")),
    ]


def test_bic_detail_workbook_includes_shop_profile_fields() -> None:
    buffer = BicAccountingService._build_detail_workbook(
        [
            {
                "platform_code": "douyin",
                "service_provider": "服务商A",
                "store_short_id": "S001",
                "shop_name": "示例店铺",
                "qic_warehouse": "华东仓",
                "merchant": "示例商户",
                "tax_no": "91310000000000000X",
                "shop_type": "旗舰店",
                "registered_address": "上海市浦东新区张江路 88 号",
                "total_amount": Decimal("123.45"),
            }
        ]
    )
    workbook = load_workbook(buffer)
    sheet = workbook.active

    headers = [sheet.cell(row=1, column=index).value for index in range(1, 12)]
    values = [sheet.cell(row=2, column=index).value for index in range(1, 12)]

    assert headers == ["序号", "平台", "服务商", "店铺id", "店铺名称", "QIC仓", "公司名称", "税号", "抬头类型", "注册地址", "结算金额"]
    assert values == [
        1,
        TransactionAccountingService._format_platform("douyin"),
        "服务商A",
        "S001",
        "示例店铺",
        "华东仓",
        "示例商户",
        "91310000000000000X",
        "旗舰店",
        "上海市浦东新区张江路 88 号",
        123.45,
    ]


def test_bic_report_workbook_matches_detail_without_qic_warehouse() -> None:
    buffer = BicAccountingService._build_report_workbook(
        [
            {
                "platform_code": "douyin",
                "service_provider": "服务商A",
                "store_short_id": "S001",
                "shop_name": "示例店铺",
                "merchant": "示例商户",
                "tax_no": "91310000000000000X",
                "shop_type": "旗舰店",
                "registered_address": "上海市浦东新区张江路 88 号",
                "total_amount": Decimal("123.45"),
            }
        ]
    )
    workbook = load_workbook(buffer)
    sheet = workbook.active

    headers = [sheet.cell(row=1, column=index).value for index in range(1, 11)]
    values = [sheet.cell(row=2, column=index).value for index in range(1, 11)]

    assert headers == ["序号", "平台", "服务商", "店铺id", "店铺名称", "公司名称", "税号", "抬头类型", "注册地址", "结算金额"]
    assert values == [
        1,
        TransactionAccountingService._format_platform("douyin"),
        "服务商A",
        "S001",
        "示例店铺",
        "示例商户",
        "91310000000000000X",
        "旗舰店",
        "上海市浦东新区张江路 88 号",
        123.45,
    ]


def test_bic_detail_rows_group_by_service_provider_and_qic() -> None:
    task = BicTask(id=1, file_id=2, org_id=3, user_id=4, status="success", progress=100)
    upload_file = BicUploadFile(
        id=2,
        org_id=3,
        user_id=4,
        original_name="bic.xlsx",
        oss_key="oss://bic.xlsx",
        file_size=123,
        platform_code="douyin",
        shop_name="示例店铺",
        accounting_year=2026,
        accounting_month=5,
    )

    rows = BicAccountingService._build_detail_rows(
        task=task,
        upload_file=upload_file,
        rows=[
            {"service_provider": "服务商A", "qic_warehouse": "华东仓", "amount": Decimal("1.20"), "raw_row": {}},
            {"service_provider": "服务商A", "qic_warehouse": "华东仓", "amount": Decimal("2.30"), "raw_row": {}},
            {"service_provider": "服务商B", "qic_warehouse": "华东仓", "amount": Decimal("4.50"), "raw_row": {}},
        ],
        platform_code="douyin",
        shop_id=None,
        shop_name="示例店铺",
    )

    assert sorted((row.service_provider, row.qic_warehouse, row.row_count, row.total_amount) for row in rows) == [
        ("服务商A", "华东仓", 2, Decimal("3.50")),
        ("服务商B", "华东仓", 1, Decimal("4.50")),
    ]


def test_bic_report_rows_group_by_service_provider() -> None:
    task = BicTask(id=1, file_id=2, org_id=3, user_id=4, status="success", progress=100)
    upload_file = BicUploadFile(
        id=2,
        org_id=3,
        user_id=4,
        original_name="bic.xlsx",
        oss_key="oss://bic.xlsx",
        file_size=123,
        platform_code="douyin",
        shop_name="示例店铺",
        accounting_year=2026,
        accounting_month=5,
    )
    detail_rows = [
        BicAccountingService._build_detail_rows(
            task=task,
            upload_file=upload_file,
            rows=[{"service_provider": "服务商A", "qic_warehouse": "华东仓", "amount": Decimal("1.20"), "raw_row": {}}],
            platform_code="douyin",
            shop_id=None,
            shop_name="示例店铺",
        )[0],
        BicAccountingService._build_detail_rows(
            task=task,
            upload_file=upload_file,
            rows=[{"service_provider": "服务商A", "qic_warehouse": "华南仓", "amount": Decimal("2.30"), "raw_row": {}}],
            platform_code="douyin",
            shop_id=None,
            shop_name="示例店铺",
        )[0],
        BicAccountingService._build_detail_rows(
            task=task,
            upload_file=upload_file,
            rows=[{"service_provider": "服务商B", "qic_warehouse": "华东仓", "amount": Decimal("4.50"), "raw_row": {}}],
            platform_code="douyin",
            shop_id=None,
            shop_name="示例店铺",
        )[0],
    ]

    rows = BicAccountingService._build_report_rows(
        task=task,
        upload_file=upload_file,
        detail_rows=detail_rows,
        platform_code="douyin",
        shop_id=None,
        shop_name="示例店铺",
    )

    assert sorted((row.service_provider, row.row_count, row.total_amount) for row in rows) == [
        ("服务商A", 2, Decimal("3.50")),
        ("服务商B", 1, Decimal("4.50")),
    ]
