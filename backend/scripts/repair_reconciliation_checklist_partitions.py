"""Repair reconciliation checklist partitions affected by PostgreSQL identifier truncation.

Usage:
    uv run python scripts/repair_reconciliation_checklist_partitions.py --start 202601 --end 202612
    uv run repair-reconciliation-checklist-partitions --start 202601 --end 202612
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.database import async_session_factory
from app.services.partition_maintenance_service import ensure_reconciliation_checklist_partitions_for_window
from app.services.partition_service import (
    RECONCILIATION_CHECKLIST_PARTITION,
    RECONCILIATION_CHECKLIST_PAYABLE_BALANCE_SUMMARY_PARTITION,
    RECONCILIATION_CHECKLIST_SUMMARY_PARTITION,
    RECONCILIATION_CHECKLIST_SUMMARY_PRODUCT_PARTITION,
    next_yyyymm,
)


SPECS = (
    RECONCILIATION_CHECKLIST_PARTITION,
    RECONCILIATION_CHECKLIST_SUMMARY_PARTITION,
    RECONCILIATION_CHECKLIST_SUMMARY_PRODUCT_PARTITION,
    RECONCILIATION_CHECKLIST_PAYABLE_BALANCE_SUMMARY_PARTITION,
)


def _parse_yyyymm(value: str) -> int:
    text = value.strip()
    if len(text) != 6 or not text.isdigit():
        raise argparse.ArgumentTypeError("年月必须是 YYYYMM 格式")
    month = int(text[4:])
    if month < 1 or month > 12:
        raise argparse.ArgumentTypeError("月份必须在 01-12 之间")
    return int(text)


async def _drop_partition_if_present(db, *, table_name: str, partition_bound: str, expected_name: str) -> list[str]:
    result = await db.execute(
        text(
            """
            SELECT child.relname
            FROM pg_inherits i
            JOIN pg_class child ON child.oid = i.inhrelid
            WHERE i.inhparent = to_regclass(:table_name)
              AND pg_get_expr(child.relpartbound, child.oid, true) = :partition_bound
            """
        ),
        {
            "table_name": table_name,
            "partition_bound": partition_bound,
        },
    )
    dropped: list[str] = []
    for (actual_name,) in result.fetchall():
        if actual_name != expected_name:
            await db.execute(text(f'DROP TABLE IF EXISTS "{actual_name}" CASCADE'))
            dropped.append(actual_name)
    return dropped


async def main() -> None:
    parser = argparse.ArgumentParser(description="Repair reconciliation checklist partitions with truncated legacy names.")
    parser.add_argument("--start", type=_parse_yyyymm, required=True, help="起始年月，格式 YYYYMM")
    parser.add_argument("--end", type=_parse_yyyymm, required=True, help="结束年月，格式 YYYYMM")
    args = parser.parse_args()

    if args.end < args.start:
        raise SystemExit("--end 不能小于 --start")

    repaired: list[str] = []
    async with async_session_factory() as db:
        current = args.start
        while current <= args.end:
            next_period = next_yyyymm(current)
            for spec in SPECS:
                expected_name = f"{spec.prefix}{current}"
                partition_bound = f"FOR VALUES FROM ({current}) TO ({next_period})"
                repaired.extend(
                    await _drop_partition_if_present(
                        db,
                        table_name=spec.table_name,
                        partition_bound=partition_bound,
                        expected_name=expected_name,
                    )
                )
            current = next_period

        result = await ensure_reconciliation_checklist_partitions_for_window(
            db,
            start_period=args.start,
            end_period=args.end,
        )
        await db.commit()

    if repaired:
        print("已清理旧分区:")
        for name in repaired:
            print(f" - {name}")
    print(f"已修复并重建对账清单分区窗口: {result['start_period']} ~ {result['end_period']}")


if __name__ == "__main__":
    asyncio.run(main())
