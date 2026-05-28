"""Helpers for monthly range partitions used by BIC and Douyin source tables."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(frozen=True)
class PartitionSpec:
    table_name: str
    partition_column: str
    legacy_table_name: str
    prefix: str


BIC_SOURCE_PARTITION = PartitionSpec(
    table_name="fin_bic_source_rows",
    partition_column="accounting_period",
    legacy_table_name="fin_bic_source_rows_legacy_032",
    prefix="fin_bic_source_rows_",
)

DOUYIN_SOURCE_PARTITION = PartitionSpec(
    table_name="fin_douyin_dongzhang_details",
    partition_column="source_period",
    legacy_table_name="fin_douyin_dongzhang_details_legacy_032",
    prefix="fin_douyin_dongzhang_details_",
)


def yyyymm_value(year: int, month: int) -> int:
    return int(year) * 100 + int(month)


def next_yyyymm(value: int) -> int:
    year = value // 100
    month = value % 100
    if month == 12:
        return (year + 1) * 100 + 1
    return year * 100 + month + 1


def iter_yyyymm_range(start: int, end: int) -> Iterable[int]:
    current = int(start)
    while current <= end:
        yield current
        current = next_yyyymm(current)


def month_floor(value: datetime | date) -> int:
    return yyyymm_value(value.year, value.month)


def shift_months(base: datetime | date, offset: int) -> int:
    year = base.year
    month = base.month + offset
    while month <= 0:
        year -= 1
        month += 12
    while month > 12:
        year += 1
        month -= 12
    return yyyymm_value(year, month)


def partition_name(spec: PartitionSpec, period: int) -> str:
    return f"{spec.prefix}{period}"


async def _table_exists(db: AsyncSession, table_name: str) -> bool:
    try:
        result = await db.execute(text("SELECT to_regclass(:table_name) IS NOT NULL"), {"table_name": table_name})
    except TypeError:
        return False
    return bool(result.scalar())


async def _is_partitioned(db: AsyncSession, table_name: str) -> bool:
    try:
        result = await db.execute(
            text(
                """
                SELECT EXISTS (
                    SELECT 1
                    FROM pg_partitioned_table
                    WHERE partrelid = to_regclass(:table_name)
                )
                """
            ),
            {"table_name": table_name},
        )
    except TypeError:
        return False
    return bool(result.scalar())


async def ensure_month_partition(db: AsyncSession, *, spec: PartitionSpec, period: int) -> None:
    if not await _table_exists(db, spec.table_name):
        return
    if not await _is_partitioned(db, spec.table_name):
        return
    if period <= 0:
        return

    partition = partition_name(spec, period)
    next_period = next_yyyymm(period)
    await db.execute(
        text(
            f"""
            CREATE TABLE IF NOT EXISTS {partition}
            PARTITION OF {spec.table_name}
            FOR VALUES FROM ({period}) TO ({next_period})
            """
        )
    )


async def ensure_month_window(
    db: AsyncSession,
    *,
    spec: PartitionSpec,
    start_period: int,
    end_period: int,
) -> None:
    if end_period < start_period:
        return
    for period in iter_yyyymm_range(start_period, end_period):
        await ensure_month_partition(db, spec=spec, period=period)
