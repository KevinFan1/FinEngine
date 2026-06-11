"""Clear raw source-detail tables for manual cleanup or scheduled retention jobs.

Usage:
    uv run python scripts/clear_source_detail_rows.py --all --dry-run
    uv run python scripts/clear_source_detail_rows.py --all
    uv run python scripts/clear_source_detail_rows.py --target dongzhang --before-days 30
    uv run python scripts/clear_source_detail_rows.py --target bic --before-days 7
    uv run python scripts/clear_source_detail_rows.py --target dongzhang --period 202604
    uv run python scripts/clear_source_detail_rows.py --period-start 202604 --period-end 202606 --dry-run
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.database import async_session_factory


@dataclass(frozen=True)
class CleanupTarget:
    code: str
    label: str
    table_name: str
    period_column: str


TARGETS: dict[str, CleanupTarget] = {
    "dongzhang": CleanupTarget(
        code="dongzhang",
        label="动账明细",
        table_name="fin_douyin_dongzhang_details",
        period_column="source_period",
    ),
    "bic": CleanupTarget(
        code="bic",
        label="BIC源数据",
        table_name="fin_bic_source_rows",
        period_column="accounting_period",
    ),
}


def _positive_int(value: str) -> int:
    number = int(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("必须是正整数")
    return number


def _parse_yyyymm(value: str) -> int:
    text_value = value.strip()
    if len(text_value) != 6 or not text_value.isdigit():
        raise argparse.ArgumentTypeError("年月必须是 YYYYMM 格式")
    month = int(text_value[4:])
    if month < 1 or month > 12:
        raise argparse.ArgumentTypeError("月份必须在 01-12 之间")
    return int(text_value)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="清理动账明细和 BIC 源数据表中的原始明细。")
    parser.add_argument(
        "--target",
        action="append",
        choices=sorted(TARGETS.keys()),
        help="指定清理目标，可重复传入；默认同时清理动账明细和 BIC 源数据",
    )
    parser.add_argument("--all", action="store_true", help="显式确认全量清空目标表")
    parser.add_argument("--before-days", type=_positive_int, help="仅清理创建时间早于 N 天前的数据")
    parser.add_argument("--period", type=_parse_yyyymm, help="仅清理指定年月的数据，格式 YYYYMM")
    parser.add_argument("--period-start", type=_parse_yyyymm, help="清理范围起始年月，格式 YYYYMM")
    parser.add_argument("--period-end", type=_parse_yyyymm, help="清理范围结束年月，格式 YYYYMM")
    parser.add_argument("--dry-run", action="store_true", help="仅统计待清理行数，不执行删除")
    args = parser.parse_args()

    mode_count = int(args.all) + int(args.before_days is not None) + int(args.period is not None) + int(args.period_start is not None or args.period_end is not None)
    if mode_count == 0:
        parser.error("必须提供 --all、--before-days、--period，或者同时提供 --period-start 和 --period-end")
    if mode_count > 1:
        parser.error("--all、--before-days、--period、--period-start/--period-end 不能同时混用")
    if args.period_start is not None or args.period_end is not None:
        if args.period_start is None or args.period_end is None:
            parser.error("必须同时提供 --period-start 和 --period-end")
        if args.period_start > args.period_end:
            parser.error("--period-start 不能大于 --period-end")

    return args


def _get_selected_targets(args: argparse.Namespace) -> list[CleanupTarget]:
    selected_codes = args.target or list(TARGETS.keys())
    return [TARGETS[code] for code in selected_codes]


def _build_scope(target: CleanupTarget, *, before_days: int | None, period_start: int | None, period_end: int | None) -> tuple[str | None, dict[str, object]]:
    if before_days is not None:
        return (
            "created_at < now() - make_interval(days => :before_days)",
            {"before_days": before_days},
        )
    if period_start is not None and period_end is not None:
        if period_start == period_end:
            return (f"{target.period_column} = :period_start", {"period_start": period_start})
        return (
            f"{target.period_column} BETWEEN :period_start AND :period_end",
            {"period_start": period_start, "period_end": period_end},
        )
    return None, {}


async def _count_rows(
    db,
    *,
    target: CleanupTarget,
    before_days: int | None,
    period_start: int | None,
    period_end: int | None,
) -> int:
    where_clause, params = _build_scope(
        target,
        before_days=before_days,
        period_start=period_start,
        period_end=period_end,
    )
    if where_clause is None:
        statement = text(f"SELECT COUNT(*) FROM {target.table_name}")
    else:
        statement = text(
            f"""
            SELECT COUNT(*)
            FROM {target.table_name}
            WHERE {where_clause}
            """
        )

    result = await db.execute(statement, params)
    return int(result.scalar() or 0)


async def _delete_rows(
    db,
    *,
    target: CleanupTarget,
    before_days: int | None,
    period_start: int | None,
    period_end: int | None,
) -> int:
    where_clause, params = _build_scope(
        target,
        before_days=before_days,
        period_start=period_start,
        period_end=period_end,
    )
    if where_clause is None:
        await db.execute(text(f"TRUNCATE TABLE {target.table_name}"))
        return 0

    result = await db.execute(
        text(
            f"""
            DELETE FROM {target.table_name}
            WHERE {where_clause}
            """
        ),
        params,
    )
    return max(int(result.rowcount or 0), 0)


def _build_mode_label(*, args: argparse.Namespace) -> str:
    if args.all:
        return "全量清空"
    if args.before_days is not None:
        return f"按创建时间清理 {args.before_days} 天前数据"
    if args.period is not None:
        return f"按年月清理 {args.period}"
    return f"按年月范围清理 {args.period_start} ~ {args.period_end}"


async def main() -> None:
    args = _parse_args()
    targets = _get_selected_targets(args)
    before_days = args.before_days
    period_start = args.period if args.period is not None else args.period_start
    period_end = args.period if args.period is not None else args.period_end
    mode_label = _build_mode_label(args=args)

    async with async_session_factory() as db:
        pending_counts: dict[str, int] = {}
        total_pending = 0
        for target in targets:
            pending_count = await _count_rows(
                db,
                target=target,
                before_days=before_days,
                period_start=period_start,
                period_end=period_end,
            )
            pending_counts[target.code] = pending_count
            total_pending += pending_count
            print(f"目标表={target.label} 待清理行数={pending_count}", flush=True)

        print(
            f"源数据清理准备完成 模式={mode_label} 演练模式={'是' if args.dry_run else '否'} 目标表数={len(targets)} 待清理总行数={total_pending}",
            flush=True,
        )

        if total_pending == 0:
            print("未发现需要清理的源数据。", flush=True)
            await db.rollback()
            return

        if args.dry_run:
            print("演练模式，未执行实际删除。", flush=True)
            await db.rollback()
            return

        deleted_total = 0
        for target in targets:
            pending_count = pending_counts[target.code]
            if pending_count <= 0:
                continue
            deleted_count = await _delete_rows(
                db,
                target=target,
                before_days=before_days,
                period_start=period_start,
                period_end=period_end,
            )
            if args.all:
                deleted_count = pending_count
            elif deleted_count <= 0:
                deleted_count = pending_count
            deleted_total += deleted_count
            print(f"已清理 {target.label} {deleted_count} 行", flush=True)

        await db.commit()
        print(
            f"源数据清理完成 模式={mode_label} 目标表数={len(targets)} 清理总行数={deleted_total}",
            flush=True,
        )


if __name__ == "__main__":
    asyncio.run(main())
