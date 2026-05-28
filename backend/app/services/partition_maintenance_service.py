"""Maintenance helpers for monthly partitions."""

from __future__ import annotations

from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.partition_service import (
    BIC_SOURCE_PARTITION,
    DOUYIN_SOURCE_PARTITION,
    ensure_month_window,
    month_floor,
    shift_months,
)


PARTITION_PRECREATE_PAST_MONTHS = 36
PARTITION_PRECREATE_FUTURE_MONTHS = 12


async def ensure_source_partitions_for_window(db: AsyncSession, *, anchor: date | None = None) -> dict[str, int]:
    base = anchor or date.today()
    start_period = shift_months(base, -PARTITION_PRECREATE_PAST_MONTHS)
    end_period = shift_months(base, PARTITION_PRECREATE_FUTURE_MONTHS)

    await ensure_month_window(db, spec=BIC_SOURCE_PARTITION, start_period=start_period, end_period=end_period)
    await ensure_month_window(db, spec=DOUYIN_SOURCE_PARTITION, start_period=start_period, end_period=end_period)

    return {
        "start_period": start_period,
        "end_period": end_period,
        "base_period": month_floor(base),
    }

