from pathlib import Path

from app.tasks.processors.base import TabularFileOpenError, open_tabular_rows


def _read_rows(path: Path) -> list[list[object]]:
    with open_tabular_rows(str(path)) as rows:
        assert rows is not None
        return [list(row) for row in rows]


def test_open_tabular_rows_reads_csv_even_when_suffix_is_xlsx(tmp_path: Path) -> None:
    file_path = tmp_path / "wrong_suffix.xlsx"
    file_path.write_text("日期,金额\n2026-05-01,12.30\n", encoding="utf-8-sig")

    assert _read_rows(file_path) == [["日期", "金额"], ["2026-05-01", "12.30"]]


def test_open_tabular_rows_reads_html_table_even_when_suffix_is_xlsx(tmp_path: Path) -> None:
    file_path = tmp_path / "html_export.xlsx"
    file_path.write_text(
        "<html><body><table><tr><th>日期</th><th>金额</th></tr><tr><td>2026-05-01</td><td>12.30</td></tr></table></body></html>",
        encoding="gb18030",
    )

    assert _read_rows(file_path) == [["日期", "金额"], ["2026-05-01", "12.30"]]


def test_open_tabular_rows_rejects_non_tabular_xlsx_with_clear_error(tmp_path: Path) -> None:
    file_path = tmp_path / "bad.xlsx"
    file_path.write_text("this is not a table", encoding="utf-8")

    try:
        _read_rows(file_path)
    except TabularFileOpenError as exc:
        assert "不是 xlsx 压缩包" in str(exc)
    else:
        raise AssertionError("TabularFileOpenError was not raised")
