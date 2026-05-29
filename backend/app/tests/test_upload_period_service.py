from pathlib import Path

import pytest
from openpyxl import Workbook

from app.services.upload_period_service import (
    extract_upload_period,
    get_upload_period_header,
    normalize_period_type,
    parse_period_value,
)


def _write_workbook(path: Path, headers: list[str], rows: list[list[object]]) -> None:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.append(headers)
    for row in rows:
        worksheet.append(row)
    workbook.save(path)
    workbook.close()


def test_extract_upload_period_reads_single_configured_column(tmp_path: Path) -> None:
    file_path = tmp_path / "dongzhang.xlsx"
    _write_workbook(
        file_path,
        ["流水号", "动账时间", "备注"],
        [
            ["202606999999", "2026-05-01 10:00:00", "备注里有 202604"],
            ["202607999999", "2026-05-31 23:59:59", "备注里有 202603"],
        ],
    )

    result = extract_upload_period(
        str(file_path),
        platform_code="douyin",
        type_code="动账",
    )

    assert result.year == 2026
    assert result.month == 5
    assert result.header == "动账时间"
    assert result.period_counts == {"2026-05": 2}


def test_extract_upload_period_rejects_multiple_months(tmp_path: Path) -> None:
    file_path = tmp_path / "dongzhang_mixed.xlsx"
    _write_workbook(
        file_path,
        ["流水号", "动账时间"],
        [
            ["a", "2026-05-01"],
            ["b", "2026-06-01"],
        ],
    )

    with pytest.raises(ValueError, match="多个所属年月"):
        extract_upload_period(str(file_path), platform_code="抖音", type_code="动账")


def test_extract_upload_period_supports_header_aliases_and_type_aliases(tmp_path: Path) -> None:
    file_path = tmp_path / "xiaohongshu_gmv.xlsx"
    _write_workbook(
        file_path,
        ["订单号", "结算时间"],
        [["order-1", "2026/05/20"]],
    )

    result = extract_upload_period(
        str(file_path),
        platform_code="小红书",
        type_code="GMV订单货款",
    )

    assert result.year == 2026
    assert result.month == 5
    assert normalize_period_type("GMV其他服务款") == "其他服务款"
    assert get_upload_period_header("视频号小店", "订单") == "订单下单时间"


def test_parse_period_value_rejects_invalid_month_codes() -> None:
    assert parse_period_value("202613") is None
    assert parse_period_value("2026-13-01") is None
