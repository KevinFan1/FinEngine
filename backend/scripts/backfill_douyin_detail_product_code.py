"""Backfill Douyin source detail product codes from product names.

Usage:
    uv run python scripts/backfill_douyin_detail_product_code.py --dry-run --limit 10000
    uv run python scripts/backfill_douyin_detail_product_code.py --batch-size 5000
    uv run python scripts/backfill_douyin_detail_product_code.py --start-period 202604 --end-period 202605
    uv run python scripts/backfill_douyin_detail_product_code.py --include-existing
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.database import async_session_factory
from app.utils.product_code import extract_product_code


DEFAULT_BATCH_SIZE = 5000
SQL_PRODUCT_CODE_CANDIDATE_PATTERN = r"([A-Z]{1,16}[0-9]{3,16})"


def _positive_int(value: str) -> int:
    number = int(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("必须是正整数")
    return number


def _non_negative_int(value: str) -> int:
    number = int(value)
    if number < 0:
        raise argparse.ArgumentTypeError("必须是非负整数")
    return number


def _parse_yyyymm(value: str) -> int:
    text_value = value.strip()
    if len(text_value) != 6 or not text_value.isdigit():
        raise argparse.ArgumentTypeError("年月必须是 YYYYMM 格式")
    month = int(text_value[4:])
    if month < 1 or month > 12:
        raise argparse.ArgumentTypeError("月份必须在 01-12 之间")
    return int(text_value)


def _next_yyyymm(value: int) -> int:
    year = value // 100
    month = value % 100
    if month == 12:
        return (year + 1) * 100 + 1
    return year * 100 + month + 1


def _build_where_clauses(args: argparse.Namespace) -> tuple[list[str], dict[str, int | str]]:
    where_clauses = ["COALESCE(product_name, '') <> ''"]
    params: dict[str, int | str] = {}

    if not args.include_deleted:
        where_clauses.append("is_deleted = false")
    if not args.include_existing:
        where_clauses.append("COALESCE(product_code, '') = ''")
    if not args.scan_all_names:
        where_clauses.append("product_name ~* :candidate_pattern")
        params["candidate_pattern"] = SQL_PRODUCT_CODE_CANDIDATE_PATTERN
    if args.start_period is not None:
        where_clauses.append("source_period >= :start_period")
        params["start_period"] = args.start_period
    if args.end_period is not None:
        where_clauses.append("source_period <= :end_period")
        params["end_period"] = args.end_period

    return where_clauses, params


async def _run(args: argparse.Namespace) -> None:
    where_clauses, base_params = _build_where_clauses(args)
    current_period = args.after_period
    last_id = args.after_id or 0
    last_processed_period: int | None = None
    scanned_count = 0
    updated_count = 0
    same_count = 0
    empty_extracted_count = 0

    bounds_sql = text(
        """
        SELECT MIN(source_period) AS min_period,
               MAX(source_period) AS max_period
        FROM fin_douyin_dongzhang_details
        WHERE {where_clause}
        """.format(where_clause=" AND ".join(where_clauses))
    )
    select_sql = text(
        """
        SELECT source_period, id, product_name, product_code
        FROM fin_douyin_dongzhang_details
        WHERE {where_clause}
          AND source_period = :current_period
          AND id > :last_id
        ORDER BY id ASC
        LIMIT :batch_size
        """.format(where_clause=" AND ".join(where_clauses))
    )
    update_sql = text(
        """
        UPDATE fin_douyin_dongzhang_details
        SET product_code = :product_code,
            updated_at = now()
        WHERE source_period = :source_period
          AND id = :id
        """
    )

    print(
        "开始回填 product_code: "
        f"batch_size={args.batch_size}, "
        f"dry_run={args.dry_run}, "
        f"include_existing={args.include_existing}, "
        f"scan_all_names={args.scan_all_names}, "
        f"start_period={args.start_period or '-'}, "
        f"end_period={args.end_period or '-'}",
        flush=True,
    )

    async with async_session_factory() as db:
        if current_period is None:
            bounds = (await db.execute(bounds_sql, base_params)).mappings().one()
            current_period = bounds["min_period"]
            max_period = bounds["max_period"]
        else:
            max_period = args.end_period
            if max_period is None:
                bounds_params = {**base_params, "start_period": current_period}
                bounds_where = where_clauses
                if args.start_period is None:
                    bounds_where = [*where_clauses, "source_period >= :start_period"]
                bounds = (
                    await db.execute(
                        text(
                            """
                            SELECT MAX(source_period) AS max_period
                            FROM fin_douyin_dongzhang_details
                            WHERE {where_clause}
                            """.format(where_clause=" AND ".join(bounds_where))
                        ),
                        bounds_params,
                    )
                ).mappings().one()
                max_period = bounds["max_period"]

        if current_period is None or max_period is None:
            print("没有找到需要回填的数据。", flush=True)
            await db.rollback()
            return

        while current_period <= max_period:
            remaining = None if args.limit is None else args.limit - scanned_count
            if remaining is not None and remaining <= 0:
                break

            batch_size = args.batch_size if remaining is None else min(args.batch_size, remaining)
            params = {
                **base_params,
                "current_period": current_period,
                "last_id": last_id,
                "batch_size": batch_size,
            }
            result = await db.execute(select_sql, params)
            rows = result.mappings().all()
            if not rows:
                current_period = _next_yyyymm(current_period)
                last_id = 0
                continue

            updates: list[dict[str, int | str]] = []
            for row in rows:
                extracted_code = extract_product_code(row["product_name"])
                current_code = row["product_code"] or ""
                if not extracted_code:
                    empty_extracted_count += 1
                    continue
                if extracted_code == current_code:
                    same_count += 1
                    continue
                updates.append(
                    {
                        "source_period": row["source_period"],
                        "id": row["id"],
                        "product_code": extracted_code,
                    }
                )

            if args.dry_run:
                await db.rollback()
            else:
                if updates:
                    await db.execute(update_sql, updates)
                await db.commit()

            scanned_count += len(rows)
            updated_count += len(updates)
            last_processed_period = current_period
            last_id = rows[-1]["id"]
            print(
                "批次完成: "
                f"scanned={scanned_count}, "
                f"updated={updated_count}, "
                f"same={same_count}, "
                f"empty_extracted={empty_extracted_count}, "
                f"last=({current_period}, {last_id})",
                flush=True,
            )

    print(
        "回填结束: "
        f"scanned={scanned_count}, "
        f"updated={updated_count}, "
        f"same={same_count}, "
        f"empty_extracted={empty_extracted_count}",
        flush=True,
    )
    if last_processed_period is not None:
        print(f"断点续跑参数: --after-period {last_processed_period} --after-id {last_id}", flush=True)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="分批从商品名称提取并回填抖音动账明细商品编码。")
    parser.add_argument("--batch-size", type=_positive_int, default=DEFAULT_BATCH_SIZE, help="每批扫描行数，默认 5000")
    parser.add_argument("--limit", type=_positive_int, help="最多扫描行数，常用于 dry-run 抽样")
    parser.add_argument("--start-period", type=_parse_yyyymm, help="起始上传年月，格式 YYYYMM")
    parser.add_argument("--end-period", type=_parse_yyyymm, help="结束上传年月，格式 YYYYMM")
    parser.add_argument("--after-period", type=_parse_yyyymm, help="断点续跑的上一个 source_period")
    parser.add_argument("--after-id", type=_non_negative_int, default=0, help="断点续跑的上一个 id")
    parser.add_argument("--include-existing", action="store_true", help="覆盖重算已有 product_code；默认只回填空值")
    parser.add_argument("--include-deleted", action="store_true", help="包含软删除数据；默认跳过")
    parser.add_argument("--scan-all-names", action="store_true", help="扫描所有非空商品名；默认先用 SQL 正则过滤候选编码")
    parser.add_argument("--dry-run", action="store_true", help="只扫描和统计，不写入数据库")
    args = parser.parse_args()

    if args.start_period is not None and args.end_period is not None and args.start_period > args.end_period:
        parser.error("--start-period 不能大于 --end-period")
    if args.after_id and args.after_period is None:
        parser.error("使用 --after-id 时必须同时提供 --after-period")
    return args


def main() -> int:
    asyncio.run(_run(_parse_args()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
