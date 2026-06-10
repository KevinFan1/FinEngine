"""Maintenance helpers for monthly partitions."""

from __future__ import annotations

from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.partition_service import (
    BIC_SOURCE_PARTITION,
    DOUYIN_SOURCE_PARTITION,
    RECONCILIATION_CHECKLIST_PAYABLE_BALANCE_SUMMARY_PARTITION,
    RECONCILIATION_CHECKLIST_PARTITION,
    RECONCILIATION_CHECKLIST_SUMMARY_PARTITION,
    RECONCILIATION_CHECKLIST_SUMMARY_PRODUCT_PARTITION,
    ensure_hash_partition_parent_primary_key,
    ensure_month_window,
    month_floor,
    shift_months,
)


PARTITION_PRECREATE_PAST_MONTHS = 36
PARTITION_PRECREATE_FUTURE_MONTHS = 12

RECONCILIATION_CHECKLIST_HASH_PARTITIONS = (
    RECONCILIATION_CHECKLIST_PARTITION,
    RECONCILIATION_CHECKLIST_SUMMARY_PARTITION,
    RECONCILIATION_CHECKLIST_SUMMARY_PRODUCT_PARTITION,
    RECONCILIATION_CHECKLIST_PAYABLE_BALANCE_SUMMARY_PARTITION,
)


async def ensure_reconciliation_checklist_parent_primary_keys(db: AsyncSession) -> None:
    for spec in RECONCILIATION_CHECKLIST_HASH_PARTITIONS:
        await ensure_hash_partition_parent_primary_key(db, spec=spec)


async def ensure_source_partitions_for_window(db: AsyncSession, *, anchor: date | None = None) -> dict[str, int]:
    base = anchor or date.today()
    start_period = shift_months(base, -PARTITION_PRECREATE_PAST_MONTHS)
    end_period = shift_months(base, PARTITION_PRECREATE_FUTURE_MONTHS)

    await ensure_month_window(db, spec=BIC_SOURCE_PARTITION, start_period=start_period, end_period=end_period)
    await ensure_month_window(db, spec=DOUYIN_SOURCE_PARTITION, start_period=start_period, end_period=end_period)
    await ensure_reconciliation_checklist_parent_primary_keys(db)
    for spec in RECONCILIATION_CHECKLIST_HASH_PARTITIONS:
        await ensure_month_window(db, spec=spec, start_period=start_period, end_period=end_period)

    return {
        "start_period": start_period,
        "end_period": end_period,
        "base_period": month_floor(base),
    }


async def ensure_reconciliation_checklist_partitions_for_window(
    db: AsyncSession,
    *,
    start_period: int,
    end_period: int,
) -> dict[str, int]:
    await ensure_reconciliation_checklist_parent_primary_keys(db)
    for spec in RECONCILIATION_CHECKLIST_HASH_PARTITIONS:
        await ensure_month_window(
            db,
            spec=spec,
            start_period=start_period,
            end_period=end_period,
        )
    return {
        "start_period": start_period,
        "end_period": end_period,
    }


async def ensure_reconciliation_checklist_partitions_for_anchor(
    db: AsyncSession,
    *,
    anchor: date | None = None,
) -> dict[str, int]:
    base = anchor or date.today()
    start_period = shift_months(base, -PARTITION_PRECREATE_PAST_MONTHS)
    end_period = shift_months(base, PARTITION_PRECREATE_FUTURE_MONTHS)

    result = await ensure_reconciliation_checklist_partitions_for_window(
        db,
        start_period=start_period,
        end_period=end_period,
    )
    return {
        **result,
        "base_period": month_floor(base),
    }


async def ensure_reconciliation_checklist_partitions_for_year(
    db: AsyncSession,
    *,
    year: int,
) -> dict[str, int]:
    start_period = year * 100 + 1
    end_period = year * 100 + 12
    await ensure_reconciliation_checklist_parent_primary_keys(db)
    for spec in RECONCILIATION_CHECKLIST_HASH_PARTITIONS:
        await ensure_month_window(
            db,
            spec=spec,
            start_period=start_period,
            end_period=end_period,
        )
    return {
        "start_period": start_period,
        "end_period": end_period,
        "year": year,
    }
