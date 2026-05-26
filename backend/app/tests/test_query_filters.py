from datetime import datetime

from app.utils.query_filters import parse_query_datetime


def test_parse_query_datetime_supports_space_separator() -> None:
    assert parse_query_datetime("2026-05-26 12:34:56") == datetime(2026, 5, 26, 12, 34, 56)


def test_parse_query_datetime_supports_iso_separator() -> None:
    assert parse_query_datetime("2026-05-26T12:34:56") == datetime(2026, 5, 26, 12, 34, 56)
