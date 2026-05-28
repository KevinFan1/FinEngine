"""Create monthly partitions for BIC and Douyin source detail tables.

Usage:
    uv run python scripts/ensure_source_partitions.py
    uv run python scripts/ensure_source_partitions.py --start 202301 --end 202612
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.database import async_session_factory
from app.services.partition_maintenance_service import ensure_source_partitions_for_window
from app.services.partition_service import ensure_month_window, BIC_SOURCE_PARTITION, DOUYIN_SOURCE_PARTITION


def _parse_yyyymm(value: str) -> int:
    text = value.strip()
    if len(text) != 6 or not text.isdigit():
        raise argparse.ArgumentTypeError("年月必须是 YYYYMM 格式")
    month = int(text[4:])
    if month < 1 or month > 12:
        raise argparse.ArgumentTypeError("月份必须在 01-12 之间")
    return int(text)


async def main() -> None:
    parser = argparse.ArgumentParser(description="Create monthly partitions for BIC and Douyin source detail tables.")
    parser.add_argument("--start", type=_parse_yyyymm, help="起始年月，格式 YYYYMM")
    parser.add_argument("--end", type=_parse_yyyymm, help="结束年月，格式 YYYYMM")
    args = parser.parse_args()

    async with async_session_factory() as db:
        if args.start or args.end:
            if not args.start or not args.end:
                raise SystemExit("必须同时提供 --start 和 --end，或者都不提供")
            await ensure_month_window(db, spec=BIC_SOURCE_PARTITION, start_period=args.start, end_period=args.end)
            await ensure_month_window(db, spec=DOUYIN_SOURCE_PARTITION, start_period=args.start, end_period=args.end)
            await db.commit()
            print(f"已创建分区窗口: {args.start} ~ {args.end}")
            return

        result = await ensure_source_partitions_for_window(db)
        await db.commit()
        print(
            "已创建分区窗口: "
            f"{result['start_period']} ~ {result['end_period']} "
            f"(base={result['base_period']})"
        )


if __name__ == "__main__":
    asyncio.run(main())

