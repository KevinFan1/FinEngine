"""Create monthly partitions for reconciliation checklist detail and summary tables.

Usage:
    uv run python scripts/ensure_reconciliation_checklist_partitions.py --start 202601 --end 202612
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.database import async_session_factory
from app.services.partition_maintenance_service import ensure_reconciliation_checklist_partitions_for_window


def _parse_yyyymm(value: str) -> int:
    text = value.strip()
    if len(text) != 6 or not text.isdigit():
        raise argparse.ArgumentTypeError("年月必须是 YYYYMM 格式")
    month = int(text[4:])
    if month < 1 or month > 12:
        raise argparse.ArgumentTypeError("月份必须在 01-12 之间")
    return int(text)


async def main() -> None:
    parser = argparse.ArgumentParser(description="Create monthly partitions for reconciliation checklist detail and summary tables.")
    parser.add_argument("--start", type=_parse_yyyymm, required=True, help="起始年月，格式 YYYYMM")
    parser.add_argument("--end", type=_parse_yyyymm, required=True, help="结束年月，格式 YYYYMM")
    args = parser.parse_args()

    if args.end < args.start:
        raise SystemExit("--end 不能小于 --start")

    async with async_session_factory() as db:
        result = await ensure_reconciliation_checklist_partitions_for_window(
            db,
            start_period=args.start,
            end_period=args.end,
        )
        await db.commit()
        print(f"已创建对账清单分区窗口: {result['start_period']} ~ {result['end_period']}")


if __name__ == "__main__":
    asyncio.run(main())
