from decimal import Decimal
from pathlib import Path

from openpyxl import Workbook

from app.services.bic_accounting_service import BicAccountingService
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
            _row(DOUYIN_BIC_HEADERS, 费用项="质检费(通过)", QIC仓="华东仓", 结算金额="12.30"),
            _row(DOUYIN_BIC_HEADERS, 费用项="质检费(拒绝)", QIC仓="华东仓", 结算金额="99.00"),
            _row(DOUYIN_BIC_HEADERS, 费用项="质检费(通过)", QIC仓="华南仓", 结算金额="7.70"),
        ],
    )

    result = BicAccountingService.parse_file(str(file_path))

    assert result["total_rows"] == 3
    assert result["success_rows"] == 2
    assert result["failed_rows"] == 0
    assert [(row["qic_warehouse"], row["amount"]) for row in result["bic_rows"]] == [
        ("华东仓", Decimal("12.30")),
        ("华南仓", Decimal("7.70")),
    ]
