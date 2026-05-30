"""Extract upload accounting period from the configured source time column."""

import re
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.file_spec import FileSpec
from app.models.platform import Platform
from app.tasks.processors.base import (
    HEADER_SCAN_LIMIT,
    canonical_header,
    open_tabular_rows,
    parse_datetime,
    safe_str,
)


@dataclass(frozen=True)
class UploadPeriodRule:
    platform_code: str
    type_code: str
    header: str


@dataclass(frozen=True)
class UploadPeriodResult:
    year: int
    month: int
    header: str
    row_count: int
    period_counts: dict[str, int]


class EmptyTabularDataError(ValueError):
    """Raised when a table has headers but no non-empty data rows."""


TYPE_ALIASES = {
    "BIC": "bic",
    "GMV": "gmv",
    "GMV订单货款": "gmv",
    "GMV其他服务款": "其他服务款",
    "退货费用及其他": "动账",
}

PLATFORM_ALIASES = {
    "抖音": "douyin",
    "抖店": "douyin",
    "小红书": "xiaohongshu",
    "视频号小店": "weixin_video",
    "视频号": "weixin_video",
    "微信小店": "weixin_video",
    "快手": "kuaishou",
    "千牛": "qianniu",
    "淘宝": "taobao",
    "天猫": "taobao",
    "tmall": "taobao",
    "支付宝": "alipay",
}

UPLOAD_PERIOD_RULES: dict[tuple[str, str], str] = {
    ("douyin", "动账"): "动账时间",
    ("douyin", "运费险"): "承保时间",
    ("douyin", "bic"): "结算时间",
    ("douyin", "订单"): "订单提交时间",
    ("xiaohongshu", "动账"): "创建时间",
    ("xiaohongshu", "运费险"): "结算时间",
    ("xiaohongshu", "gmv"): "结算时间",
    ("xiaohongshu", "其他服务款"): "结算时间",
    ("xiaohongshu", "bic"): "结算时间",
    ("xiaohongshu", "订单"): "订单创建时间",
    ("weixin_video", "动账"): "记账时间",
    ("weixin_video", "bic"): "结算时间",
    ("weixin_video", "运费险"): "开始时间",
    ("weixin_video", "订单"): "订单下单时间",
    ("kuaishou", "订单"): "订单创建时间",
    ("kuaishou", "gmv"): "实际结算时间",
    ("kuaishou", "运费险"): "生效时间",
    ("kuaishou", "动账"): "入账时间",
    ("qianniu", "动账"): "数据创建时间",
    ("qianniu", "订单"): "订单创建时间",
    ("taobao", "动账"): "数据创建时间",
    ("taobao", "订单"): "订单创建时间",
    ("alipay", "动账"): "入账时间",
    ("alipay", "订单"): "创建时间",
}


def normalize_period_platform(platform_code: str | None) -> str:
    value = safe_str(platform_code)
    return PLATFORM_ALIASES.get(value, value).lower()


def normalize_period_type(type_code: str | None) -> str:
    value = safe_str(type_code)
    if not value:
        return ""
    aliased = TYPE_ALIASES.get(value, value)
    lower = aliased.lower()
    return lower if lower in {"bic", "gmv"} else aliased


def get_upload_period_header(platform_code: str | None, type_code: str | None) -> str | None:
    platform = normalize_period_platform(platform_code)
    normalized_type = normalize_period_type(type_code)
    return UPLOAD_PERIOD_RULES.get((platform, normalized_type))


async def get_upload_period_header_from_db(
    db: AsyncSession,
    platform_code: str | None,
    type_code: str | None,
) -> str | None:
    platform = normalize_period_platform(platform_code)
    normalized_type = normalize_period_type(type_code)
    if not platform or not normalized_type:
        return None

    stmt = (
        select(FileSpec.upload_period_header)
        .join(Platform, FileSpec.platform_id == Platform.id)
        .where(
            Platform.code == platform,
            Platform.is_deleted.is_(False),
            FileSpec.type_code == normalized_type,
            FileSpec.status == 1,
            FileSpec.is_deleted.is_(False),
        )
        .limit(1)
    )
    result = await db.execute(stmt)
    header = safe_str(result.scalar_one_or_none())
    return header or None


async def resolve_upload_period_header(
    db: AsyncSession,
    platform_code: str | None,
    type_code: str | None,
) -> str | None:
    platform = normalize_period_platform(platform_code)
    normalized_type = normalize_period_type(type_code)
    if platform and normalized_type:
        stmt = (
            select(FileSpec.upload_period_header)
            .join(Platform, FileSpec.platform_id == Platform.id)
            .where(
                Platform.code == platform,
                Platform.is_deleted.is_(False),
                FileSpec.type_code == normalized_type,
                FileSpec.status == 1,
                FileSpec.is_deleted.is_(False),
            )
            .limit(1)
        )
        result = await db.execute(stmt)
        row = result.first()
        if row is not None:
            return safe_str(row[0]) or None

    return get_upload_period_header(platform_code, type_code)


def extract_upload_period(
    file_path: str,
    *,
    platform_code: str | None,
    type_code: str | None,
    header_name: str | None = None,
) -> UploadPeriodResult:
    """Read the configured time column and require exactly one year-month."""
    resolved_header_name = header_name or get_upload_period_header(platform_code, type_code)
    if not resolved_header_name:
        raise ValueError(f"未配置所属时间规则：平台 [{platform_code or '-'}]，类别 [{type_code or '-'}]")

    with open_tabular_rows(file_path) as rows:
        if rows is None:
            raise ValueError("无法打开表格文件")
        row_iter = iter(rows)
        header_row, header_row_number = _find_period_header_row(row_iter, resolved_header_name)
        target_index = _resolve_single_header_index(header_row, resolved_header_name)

        period_counts: Counter[str] = Counter()
        data_rows = 0
        valid_rows = 0
        for row in row_iter:
            if not any(safe_str(cell) for cell in row):
                continue
            data_rows += 1
            value = row[target_index] if target_index < len(row) else None
            period = parse_period_value(value)
            if period is None:
                continue
            key = f"{period[0]}-{period[1]:02d}"
            period_counts[key] += 1
            valid_rows += 1

    if not period_counts:
        if data_rows == 0:
            raise EmptyTabularDataError("空表，没有数据")
        raise ValueError(f"{resolved_header_name}列未解析到有效所属年月")
    if len(period_counts) > 1:
        summary = "、".join(f"{period} 共 {count} 行" for period, count in sorted(period_counts.items()))
        raise ValueError(f"{resolved_header_name}列检测到多个所属年月：{summary}。请按月份拆分文件后重新上传")

    only_period = next(iter(period_counts))
    year_text, month_text = only_period.split("-", 1)
    return UploadPeriodResult(
        year=int(year_text),
        month=int(month_text),
        header=resolved_header_name,
        row_count=valid_rows,
        period_counts=dict(period_counts),
    )


def parse_period_value(value: object) -> tuple[int, int] | None:
    serial_period = _parse_excel_serial_period(value)
    if serial_period is not None:
        return serial_period

    dt = parse_datetime(value)
    if dt is not None:
        return dt.year, dt.month

    text = safe_str(value)
    if not text:
        return None
    text = text.replace("年", "-").replace("月", "").replace("/", "-").replace(".", "-")
    text = re.sub(r"\s+", " ", text).strip()

    match = re.match(r"^(20\d{2})-(0?[1-9]|1[0-2])(?:-\d{1,2})?(?:\s|$)", text)
    if match:
        return int(match.group(1)), int(match.group(2))

    compact = re.sub(r"\D", "", text)
    if re.match(r"^20\d{4}$", compact):
        month = int(compact[4:6])
        if 1 <= month <= 12:
            return int(compact[:4]), month
    if re.match(r"^20\d{6}$", compact):
        month = int(compact[4:6])
        if 1 <= month <= 12:
            return int(compact[:4]), month
    return None


def _parse_excel_serial_period(value: object) -> tuple[int, int] | None:
    if value is None or isinstance(value, datetime):
        return None
    try:
        serial = float(value)
    except (TypeError, ValueError):
        return None
    if serial < 36526 or serial > 73050:
        return None

    dt = datetime(1899, 12, 30) + timedelta(days=int(serial))
    if 2000 <= dt.year <= 2099:
        return dt.year, dt.month
    return None


def _find_period_header_row(
    row_iter: Iterable[tuple[object, ...] | list[str]],
    header_name: str,
) -> tuple[list[str], int]:
    target = canonical_header(header_name)
    last_headers: list[str] = []
    for row_number, row in enumerate(row_iter, start=1):
        headers = [safe_str(cell) for cell in row]
        if any(headers):
            last_headers = headers
            canonical_headers = [canonical_header(cell) for cell in headers]
            if target in canonical_headers:
                return headers, row_number
        if row_number >= HEADER_SCAN_LIMIT:
            break
    if last_headers:
        raise ValueError(f"前 {HEADER_SCAN_LIMIT} 行未找到所属时间表头：{header_name}")
    raise ValueError("无法读取表头")


def _resolve_single_header_index(headers: list[str], header_name: str) -> int:
    target = canonical_header(header_name)
    indexes = [index for index, header in enumerate(headers) if canonical_header(header) == target]
    if not indexes:
        raise ValueError(f"未找到所属时间表头：{header_name}")
    if len(indexes) > 1:
        raise ValueError(f"所属时间表头重复：{header_name}")
    return indexes[0]
