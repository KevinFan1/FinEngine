"""Helpers for monthly range partitions used by source and summary tables."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

POSTGRES_IDENTIFIER_MAX_LENGTH = 63


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
    hash_partition_column: str | None = None
    hash_partitions: int = 0


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
    hash_partition_column="org_id",
    hash_partitions=16,
)

RECONCILIATION_CHECKLIST_SUMMARY_PARTITION = PartitionSpec(
    table_name="fin_reconciliation_checklist_receipt_summary_rows",
    partition_column="accounting_period",
    legacy_table_name="fin_reconciliation_checklist_receipt_summary_rows_legacy",
    prefix="fin_reconciliation_checklist_receipt_summary_rows_",
    hash_partition_column="org_id",
    hash_partitions=16,
)

RECONCILIATION_CHECKLIST_SUMMARY_PRODUCT_PARTITION = PartitionSpec(
    table_name="fin_reconciliation_checklist_product_summary_rows",
    partition_column="accounting_period",
    legacy_table_name="fin_reconciliation_checklist_product_summary_rows_legacy",
    prefix="fin_reconciliation_checklist_product_summary_rows_",
    hash_partition_column="org_id",
    hash_partitions=16,
)

RECONCILIATION_CHECKLIST_PAYABLE_BALANCE_SUMMARY_PARTITION = PartitionSpec(
    table_name="fin_reconciliation_checklist_payable_balance_summary_rows",
    partition_column="accounting_period",
    legacy_table_name="fin_reconciliation_checklist_payable_balance_summary_rows_legacy",
    prefix="fin_rcl_payable_balance_summary_",
    hash_partition_column="org_id",
    hash_partitions=16,
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


def _hash_subpartition_name(partition: str, remainder: int) -> str:
    return f"{partition}_h{remainder:02d}"


def _validate_partition_identifier_length(spec: PartitionSpec, partition: str) -> None:
    suffix_length = 0
    if spec.hash_partition_column and spec.hash_partitions > 0:
        suffix_length = len(_hash_subpartition_name("", max(spec.hash_partitions - 1, 0)))
    max_partition_length = POSTGRES_IDENTIFIER_MAX_LENGTH - suffix_length
    if len(partition) > max_partition_length:
        raise ValueError(
            f"partition name too long for PostgreSQL identifier limit: {partition} "
            f"(len={len(partition)}, max={max_partition_length})"
        )


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


async def _primary_key_columns(db: AsyncSession, table_name: str) -> list[str]:
    result = await db.execute(
        text(
            """
            SELECT array_agg(a.attname ORDER BY k.ord)::text[]
            FROM pg_index i
            JOIN LATERAL unnest(i.indkey) WITH ORDINALITY AS k(attnum, ord)
              ON true
            JOIN pg_attribute a
              ON a.attrelid = i.indrelid
             AND a.attnum = k.attnum
            WHERE i.indrelid = to_regclass(:table_name)
              AND i.indisprimary
            """
        ),
        {"table_name": table_name},
    )
    columns = result.scalar()
    return list(columns or [])


async def ensure_hash_partition_parent_primary_key(db: AsyncSession, *, spec: PartitionSpec) -> None:
    if not spec.hash_partition_column or spec.hash_partitions <= 0:
        return
    if spec.partition_column != "accounting_period" or spec.hash_partition_column != "org_id":
        return
    if not await _table_exists(db, spec.table_name):
        return
    if not await _is_partitioned(db, spec.table_name):
        return

    expected_columns = ["id", "org_id", "accounting_period"]
    if await _primary_key_columns(db, spec.table_name) == expected_columns:
        return

    table_name = _quote_identifier(spec.table_name)
    constraint_name = _quote_identifier(f"{spec.table_name}_pkey")
    await db.execute(text(f"ALTER TABLE {table_name} DROP CONSTRAINT IF EXISTS {constraint_name}"))
    await db.execute(text(f"ALTER TABLE {table_name} ADD PRIMARY KEY (id, org_id, accounting_period)"))


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


async def _direct_child_partition_for_bounds(
    db: AsyncSession,
    *,
    spec: PartitionSpec,
    period: int,
    next_period: int,
) -> str | None:
    result = await db.execute(
        text(
            """
            SELECT child.relname
            FROM pg_inherits i
            JOIN pg_class child ON child.oid = i.inhrelid
            WHERE i.inhparent = to_regclass(:table_name)
              AND pg_get_expr(child.relpartbound, child.oid, true) = :partition_bound
            LIMIT 1
            """
        ),
        {
            "table_name": spec.table_name,
            "partition_bound": f"FOR VALUES FROM ({period}) TO ({next_period})",
        },
    )
    return result.scalar()


async def ensure_month_partition(db: AsyncSession, *, spec: PartitionSpec, period: int) -> None:
    if not await _table_exists(db, spec.table_name):
        return
    if not await _is_partitioned(db, spec.table_name):
        return
    if period <= 0:
        return

    partition = partition_name(spec, period)
    next_period = next_yyyymm(period)
    _validate_partition_identifier_length(spec, partition)
    existing_partition = await _direct_child_partition_for_bounds(
        db,
        spec=spec,
        period=period,
        next_period=next_period,
    )
    if existing_partition and existing_partition != partition:
        await db.execute(text(f"DROP TABLE IF EXISTS {_quote_identifier(existing_partition)} CASCADE"))
    hash_clause = f" PARTITION BY HASH ({spec.hash_partition_column})" if spec.hash_partition_column and spec.hash_partitions > 0 else ""
    await db.execute(
        text(
            f"""
            CREATE TABLE IF NOT EXISTS {partition}
            PARTITION OF {spec.table_name}
            FOR VALUES FROM ({period}) TO ({next_period})
            {hash_clause}
            """
        )
    )
    await _copy_parent_comments_to_partition(db, spec=spec, partition=partition)
    if spec.hash_partition_column and spec.hash_partitions > 0:
        for remainder in range(spec.hash_partitions):
            subpartition = _hash_subpartition_name(partition, remainder)
            await db.execute(
                text(
                    f"""
                    CREATE TABLE IF NOT EXISTS {subpartition}
                    PARTITION OF {partition}
                    FOR VALUES WITH (MODULUS {spec.hash_partitions}, REMAINDER {remainder})
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
    if not await _table_exists(db, spec.table_name):
        return
    if not await _is_partitioned(db, spec.table_name):
        return
    for period in iter_yyyymm_range(start_period, end_period):
        if period <= 0:
            continue
        await ensure_month_partition(db, spec=spec, period=period)
