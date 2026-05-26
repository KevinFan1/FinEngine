from __future__ import annotations

from datetime import datetime


def split_csv_values(value: str | int | None) -> list[str]:
    if value is None:
        return []
    if isinstance(value, int):
        return [str(value)]
    return [item.strip() for item in str(value).split(",") if item.strip()]


def split_int_filter_values(value: str | int | None) -> list[int]:
    values: list[int] = []
    for item in split_csv_values(value):
        try:
            values.append(int(item))
        except ValueError:
            continue
    return values


def resolve_org_ids(
    *,
    user_role: str,
    user_org_id: int | None,
    requested_org_id: str | int | None = None,
) -> list[int] | None:
    if user_role != "superadmin":
        return [user_org_id] if user_org_id is not None else []
    org_ids = split_int_filter_values(requested_org_id)
    return org_ids or None


def datetime_range_filters(
    column,
    *,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
) -> list:
    filters = []
    if start_time is not None:
        filters.append(column >= start_time)
    if end_time is not None:
        filters.append(column <= end_time)
    return filters


def parse_query_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        pass
    try:
        return datetime.fromisoformat(normalized.replace(" ", "T"))
    except ValueError:
        return None
