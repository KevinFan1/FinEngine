from sqlalchemy import column

from app.services.summary_service import build_month_range_filters


def test_build_month_range_filters_supports_closed_range() -> None:
    period = column("period")

    filters = build_month_range_filters(
        period,
        start_year=2026,
        start_month=2,
        end_year=2026,
        end_month=4,
    )

    assert [str(item) for item in filters] == ["period >= :period_1", "period <= :period_1"]
    assert filters[0].right.value == 202602
    assert filters[1].right.value == 202604


def test_build_month_range_filters_ignores_incomplete_range_edges() -> None:
    period = column("period")

    filters = build_month_range_filters(
        period,
        start_year=2026,
        start_month=None,
        end_year=None,
        end_month=4,
    )

    assert filters == []
