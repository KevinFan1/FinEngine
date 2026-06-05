"""Helpers for monthly range partitions used by source and summary tables."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


def _quote_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def _quote_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


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

RECONCILIATION_CHECKLIST_PARTITION = PartitionSpec(
    table_name="fin_reconciliation_checklist_details",
    partition_column="accounting_period",
    legacy_table_name="fin_reconciliation_checklist_details_legacy",
    prefix="fin_reconciliation_checklist_details_",
)

RECONCILIATION_CHECKLIST_SUMMARY_PARTITION = PartitionSpec(
    table_name="fin_reconciliation_checklist_summary_rows",
    partition_column="accounting_period",
    legacy_table_name="fin_reconciliation_checklist_summary_rows_legacy",
    prefix="fin_reconciliation_checklist_summary_rows_",
)

RECONCILIATION_CHECKLIST_SUMMARY_PRODUCT_PARTITION = PartitionSpec(
    table_name="fin_reconciliation_checklist_summary_product_rows",
    partition_column="accounting_period",
    legacy_table_name="fin_reconciliation_checklist_summary_product_rows_legacy",
    prefix="fin_reconciliation_checklist_summary_product_rows_",
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


async def _copy_parent_comments_to_partition(db: AsyncSession, *, spec: PartitionSpec, partition: str) -> None:
    table_comment = await db.scalar(
        text("SELECT obj_description(to_regclass(:table_name), 'pg_class')"),
        {"table_name": spec.table_name},
    )
    if table_comment:
        await db.execute(
            text(
                f"COMMENT ON TABLE {_quote_identifier(partition)} "
                f"IS {_quote_literal(str(table_comment))}"
            )
        )

    result = await db.execute(
        text(
            """
            SELECT a.attname, d.description
            FROM pg_attribute a
            JOIN pg_description d
              ON d.objoid = a.attrelid
             AND d.objsubid = a.attnum
            WHERE a.attrelid = to_regclass(:table_name)
              AND a.attnum > 0
              AND NOT a.attisdropped
            ORDER BY a.attnum
            """
        ),
        {"table_name": spec.table_name},
    )
    for row in result.mappings():
        await db.execute(
            text(
                f"COMMENT ON COLUMN {_quote_identifier(partition)}.{_quote_identifier(row['attname'])} "
                f"IS {_quote_literal(row['description'])}"
            )
        )


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
    await _copy_parent_comments_to_partition(db, spec=spec, partition=partition)


async def ensure_month_window(
    db: AsyncSession,
    *,
    spec: PartitionSpec,
    start_period: int,
    end_period: int,
) -> None:
    if end_period < start_period:
        return
    if not await _table_exists(db, spec.table_name):
        return
    if not await _is_partitioned(db, spec.table_name):
        return
    for period in iter_yyyymm_range(start_period, end_period):
        if period <= 0:
            continue
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
        await _copy_parent_comments_to_partition(db, spec=spec, partition=partition)
