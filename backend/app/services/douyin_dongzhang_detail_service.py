"""Service layer for Douyin dongzhang source details."""

from __future__ import annotations

import io
from datetime import datetime, timezone
from decimal import Decimal
from typing import Iterable

from openpyxl import Workbook
from openpyxl.cell import WriteOnlyCell
from openpyxl.styles import Font
from sqlalchemy import and_, func, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.douyin_dongzhang_detail import DouyinDongzhangDetail
from app.models.organization import Organization
from app.models.shop import Shop
from app.models.summary import FinancialSummary
from app.services.partition_service import DOUYIN_SOURCE_PARTITION, ensure_month_partition
from app.services.shop_visibility import active_shop_filter
from app.tasks.processors.base import parse_datetime
from app.utils.money import safe_decimal

DONGZHANG_DETAIL_EXPORT_ROW_LIMIT = 20000
PLATFORM_LABELS = {
    "douyin": "抖音",
    "抖音": "抖音",
    "抖店": "抖音",
}

DONGZHANG_DETAIL_EXPORT_COLUMNS: tuple[tuple[str, str], ...] = (
    ("platform_label", "平台"),
    ("shop_name", "店铺"),
    ("transaction_time", "动账时间"),
    ("transaction_flow_no", "动帐流水号"),
    ("transaction_direction", "动账方向"),
    ("transaction_amount", "动账金额"),
    ("transaction_account", "动账账户"),
    ("transaction_scene", "动账场景"),
    ("billing_type", "计费类型"),
    ("sub_order_no", "子订单号"),
    ("order_no", "订单号"),
    ("after_sale_no", "售后编号"),
    ("order_time", "下单时间"),
    ("summary_date", "调年月(系统的业务年月)"),
    ("product_id", "商品ID"),
    ("product_name", "商品名称"),
    ("author_id", "达人ID"),
    ("author_name", "达人名称"),
    ("order_type", "订单类型"),
    ("order_paid_amount_raw", "订单实付应结"),
    ("shipping_fee", "运费实付"),
    ("platform_subsidy_shipping", "实际平台补贴_运费"),
    ("platform_subsidy", "实际平台补贴"),
    ("other_platform_subsidy", "其他平台补贴"),
    ("trade_in_deduction", "以旧换新抵扣"),
    ("gov_subsidy_platform", "政府补贴平台垫资"),
    ("author_subsidy", "实际达人补贴"),
    ("douyin_pay_subsidy", "实际抖音支付补贴"),
    ("douyin_monthly_subsidy", "实际抖音月付营销补贴"),
    ("bank_subsidy", "银行补贴"),
    ("order_refund_raw", "订单退款"),
    ("platform_fee_raw", "平台服务费"),
    ("commission_raw", "佣金"),
    ("provider_commission_raw", "服务商佣金"),
    ("channel_share", "渠道分成"),
    ("merchant_fee_raw", "招商服务费"),
    ("promotion_fee_raw", "站外推广费"),
    ("other_share", "其他分成"),
    ("is_commission_free", "是否免佣"),
    ("commission_free_amount", "免佣金额"),
    ("merchant_name", "商户主体名称"),
    ("remark", "备注"),
    ("matched_compensation", "匹配赔付"),
    ("refund_to_compensation", "退款转赔付"),
    ("cashback", "返现"),
    ("order_paid", "收"),
    ("refund_amount", "退"),
    ("gmv", "实收GMV"),
    ("platform_income", "平台其他收入"),
    ("platform_fee_positive", "平台服务费（修改正数）"),
    ("return_cost", "退货及其他费用"),
    ("commission_derived", "达人佣金"),
    ("bic", "BIC"),
    ("insurance_fee", "运费险"),
)

MONEY_FIELDS: frozenset[str] = frozenset(
    {
        "transaction_amount",
        "order_paid_amount_raw",
        "shipping_fee",
        "platform_subsidy_shipping",
        "platform_subsidy",
        "other_platform_subsidy",
        "trade_in_deduction",
        "gov_subsidy_platform",
        "author_subsidy",
        "douyin_pay_subsidy",
        "douyin_monthly_subsidy",
        "bank_subsidy",
        "order_refund_raw",
        "platform_fee_raw",
        "commission_raw",
        "provider_commission_raw",
        "channel_share",
        "merchant_fee_raw",
        "promotion_fee_raw",
        "other_share",
        "commission_free_amount",
        "refund_to_compensation",
        "cashback",
        "order_paid",
        "refund_amount",
        "gmv",
        "platform_income",
        "platform_fee_positive",
        "return_cost",
        "commission_derived",
        "bic",
        "insurance_fee",
    }
)

DATETIME_FIELDS: frozenset[str] = frozenset({"transaction_time", "order_time"})


def _source_period(year: int | None, month: int | None) -> int:
    return int(year or 0) * 100 + int(month or 0)


def _write_only_header_row(sheet, headers: list[str]) -> list[WriteOnlyCell]:
    cells: list[WriteOnlyCell] = []
    for label in headers:
        cell = WriteOnlyCell(sheet, value=label)
        cell.font = Font(bold=True)
        cells.append(cell)
    return cells


class DouyinDongzhangDetailService:
    @staticmethod
    async def sync_details(
        db: AsyncSession,
        *,
        task_id: int,
        file_id: int,
        org_id: int,
        shop_id: int,
        shop_name: str,
        source_year: int,
        source_month: int,
        source_platform_code: str,
        report_platform_code: str,
        detail_rows: list[dict[str, object]],
        summary_lookup: dict[tuple[int, int], int],
    ) -> list[DouyinDongzhangDetail]:
        now = datetime.now(timezone.utc)
        await ensure_month_partition(
            db,
            spec=DOUYIN_SOURCE_PARTITION,
            period=_source_period(source_year, source_month),
        )
        existing_stmt = select(DouyinDongzhangDetail).where(
            DouyinDongzhangDetail.org_id == org_id,
            DouyinDongzhangDetail.shop_id == shop_id,
            DouyinDongzhangDetail.source_platform_code == source_platform_code,
            DouyinDongzhangDetail.source_period == _source_period(source_year, source_month),
            DouyinDongzhangDetail.is_deleted.is_(False),
        )
        existing_rows = (await db.execute(existing_stmt)).scalars().all()
        previous_summary_ids = {int(row.summary_id) for row in existing_rows if row.summary_id is not None}
        for row in existing_rows:
            row.is_deleted = True
            row.deleted_at = now

        created_rows: list[DouyinDongzhangDetail] = []
        for payload in detail_rows:
            summary_year = int(payload["summary_year"])
            summary_month = int(payload["summary_month"])
            detail = DouyinDongzhangDetail(
                task_id=task_id,
                file_id=file_id,
                summary_id=summary_lookup.get((summary_year, summary_month)),
                org_id=org_id,
                shop_id=shop_id,
                source_platform_code=source_platform_code,
                report_platform_code=report_platform_code,
                shop_name=shop_name,
                source_year=source_year,
                source_month=source_month,
                source_period=_source_period(source_year, source_month),
                **DouyinDongzhangDetailService._normalize_payload(payload),
            )
            created_rows.append(detail)
        if created_rows:
            db.add_all(created_rows)

        current_summary_ids = {int(row.summary_id) for row in created_rows if row.summary_id is not None}
        stale_summary_ids = previous_summary_ids - current_summary_ids
        if stale_summary_ids:
            stale_stmt = select(FinancialSummary).where(
                FinancialSummary.id.in_(sorted(stale_summary_ids)),
                FinancialSummary.org_id == org_id,
                FinancialSummary.shop_id == shop_id,
                FinancialSummary.source_platform_code == source_platform_code,
                FinancialSummary.source_year == source_year,
                FinancialSummary.source_month == source_month,
                FinancialSummary.is_deleted.is_(False),
            )
            for summary in (await db.execute(stale_stmt)).scalars().all():
                summary.is_deleted = True
                summary.deleted_at = now
        return created_rows

    @staticmethod
    async def get_summary_details(
        db: AsyncSession,
        *,
        summary_id: int,
        org_ids: list[int] | None,
        page: int,
        page_size: int,
    ) -> tuple[FinancialSummary, str | None, str | None, list[DouyinDongzhangDetail], int]:
        summary, org_name, shop_color = await DouyinDongzhangDetailService._get_summary_context(
            db,
            summary_id=summary_id,
            org_ids=org_ids,
        )
        stmt = (
            select(DouyinDongzhangDetail)
            .where(
                DouyinDongzhangDetail.summary_id == summary_id,
                DouyinDongzhangDetail.is_deleted.is_(False),
            )
            .order_by(DouyinDongzhangDetail.source_row_number.asc(), DouyinDongzhangDetail.id.asc())
        )
        count_stmt = (
            select(func.count())
            .select_from(DouyinDongzhangDetail)
            .where(
                DouyinDongzhangDetail.summary_id == summary_id,
                DouyinDongzhangDetail.is_deleted.is_(False),
            )
        )
        total = (await db.execute(count_stmt)).scalar() or 0
        rows = (await db.execute(stmt.offset((page - 1) * page_size).limit(page_size))).scalars().all()
        return summary, org_name, shop_color, list(rows), total

    @staticmethod
    async def export_summary_details(
        db: AsyncSession,
        *,
        summary_id: int,
        org_ids: list[int] | None,
        ids: list[int] | None = None,
        page: int | None = None,
        page_size: int | None = None,
    ) -> tuple[FinancialSummary, io.BytesIO]:
        summary, org_name, _shop_color = await DouyinDongzhangDetailService._get_summary_context(
            db,
            summary_id=summary_id,
            org_ids=org_ids,
        )
        stmt = (
            select(DouyinDongzhangDetail)
            .where(
                DouyinDongzhangDetail.summary_id == summary_id,
                DouyinDongzhangDetail.is_deleted.is_(False),
            )
            .order_by(DouyinDongzhangDetail.source_row_number.asc(), DouyinDongzhangDetail.id.asc())
        )
        if ids is not None:
            if not ids:
                return summary, DouyinDongzhangDetailService.build_export_workbook([], include_header_only=True)
            stmt = stmt.where(DouyinDongzhangDetail.id.in_(ids))

        if page is not None and page_size is not None:
            stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        else:
            count_stmt = select(func.count()).select_from(stmt.subquery())
            total = (await db.execute(count_stmt)).scalar() or 0
            DouyinDongzhangDetailService._ensure_row_limit("动账源明细", total)

        rows = list((await db.execute(stmt)).scalars().all())
        detail_dicts = [
            DouyinDongzhangDetailService.serialize_detail_row(
                row,
                org_name=org_name,
            )
            for row in rows
        ]
        return summary, DouyinDongzhangDetailService.build_export_workbook(detail_dicts)

    @staticmethod
    async def load_export_rows_for_summary_ids(
        db: AsyncSession,
        *,
        summary_ids: Iterable[int],
    ) -> list[dict[str, object]]:
        summary_id_list = sorted({int(summary_id) for summary_id in summary_ids if int(summary_id) > 0})
        if not summary_id_list:
            return []
        DouyinDongzhangDetailService._ensure_row_limit(
            "动账源明细",
            int(
                (
                    await db.execute(
                        select(func.count())
                        .select_from(DouyinDongzhangDetail)
                        .where(
                            DouyinDongzhangDetail.summary_id.in_(summary_id_list),
                            DouyinDongzhangDetail.is_deleted.is_(False),
                        )
                    )
                ).scalar()
                or 0
            ),
        )
        stmt = (
            select(
                DouyinDongzhangDetail,
                Organization.name.label("org_name"),
            )
            .outerjoin(Organization, Organization.id == DouyinDongzhangDetail.org_id)
            .where(
                DouyinDongzhangDetail.summary_id.in_(summary_id_list),
                DouyinDongzhangDetail.is_deleted.is_(False),
            )
            .order_by(
                DouyinDongzhangDetail.source_year.desc(),
                DouyinDongzhangDetail.source_month.desc(),
                DouyinDongzhangDetail.shop_name.asc(),
                DouyinDongzhangDetail.summary_year.desc(),
                DouyinDongzhangDetail.summary_month.desc(),
                DouyinDongzhangDetail.source_row_number.asc(),
                DouyinDongzhangDetail.id.asc(),
            )
        )
        rows = []
        for detail, org_name in (await db.execute(stmt)).all():
            rows.append(DouyinDongzhangDetailService.serialize_detail_row(detail, org_name=org_name))
        return rows

    @staticmethod
    async def load_export_rows_for_report_rows(
        db: AsyncSession,
        *,
        rows: list[dict],
    ) -> list[dict[str, object]]:
        if not rows:
            return []
        keys = sorted(
            {
                (
                    int(row.get("org_id") or 0),
                    int(row.get("source_year") or 0),
                    int(row.get("source_month") or 0),
                    str(row.get("report_platform_code") or row.get("platform_name") or ""),
                    int(row.get("shop_id") or 0),
                )
                for row in rows
            }
        )
        if not keys:
            return []
        summary_stmt = select(FinancialSummary.id).where(
            FinancialSummary.is_deleted.is_(False),
            active_shop_filter(FinancialSummary.shop_id),
            tuple_(
                FinancialSummary.org_id,
                FinancialSummary.source_year,
                FinancialSummary.source_month,
                FinancialSummary.report_platform_code,
                FinancialSummary.shop_id,
            ).in_(keys),
        )
        summary_ids = list((await db.execute(summary_stmt)).scalars().all())
        return await DouyinDongzhangDetailService.load_export_rows_for_summary_ids(
            db,
            summary_ids=summary_ids,
        )

    @staticmethod
    def serialize_detail_row(
        row: DouyinDongzhangDetail,
        *,
        org_name: str | None = None,
        shop_color: str | None = None,
    ) -> dict[str, object]:
        payload: dict[str, object] = {
            "id": row.id,
            "summary_id": row.summary_id,
            "org_id": row.org_id,
            "org_name": org_name,
            "shop_id": row.shop_id,
            "shop_name": row.shop_name,
            "shop_color": shop_color,
            "source_year": row.source_year,
            "source_month": row.source_month,
            "source_period": getattr(row, "source_period", _source_period(row.source_year, row.source_month)),
            "source_date": f"{int(row.source_year):04d}-{int(row.source_month):02d}",
            "summary_year": row.summary_year,
            "summary_month": row.summary_month,
            "summary_date": f"{int(row.summary_year):04d}-{int(row.summary_month):02d}",
            "platform_name": row.source_platform_code,
            "platform": row.source_platform_code,
            "platform_label": DouyinDongzhangDetailService._platform_label(row.source_platform_code),
            "source_platform_code": row.source_platform_code,
            "report_platform_code": row.report_platform_code,
            "report_platform": row.report_platform_code,
            "period_source": row.period_source,
            "source_row_number": row.source_row_number,
        }
        for field, _label in DONGZHANG_DETAIL_EXPORT_COLUMNS:
            if field in payload:
                continue
            value = getattr(row, field, None)
            if field in MONEY_FIELDS:
                payload[field] = float(value or 0)
            elif field in DATETIME_FIELDS:
                payload[field] = DouyinDongzhangDetailService._format_datetime(value)
            else:
                payload[field] = value
        return payload

    @staticmethod
    def build_export_workbook(
        rows: list[dict[str, object]],
        *,
        include_header_only: bool = False,
    ) -> io.BytesIO:
        wb = Workbook(write_only=True)
        ws = wb.create_sheet(title="Douyin动账源明细")
        ws.append(_write_only_header_row(ws, [label for _field, label in DONGZHANG_DETAIL_EXPORT_COLUMNS]))
        if not include_header_only:
            for row in rows:
                ws.append(
                    [
                        DouyinDongzhangDetailService._format_export_value(row.get(field), money=(field in MONEY_FIELDS))
                        for field, _label in DONGZHANG_DETAIL_EXPORT_COLUMNS
                    ]
                )
        buffer = io.BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        return buffer

    @staticmethod
    async def _get_summary_context(
        db: AsyncSession,
        *,
        summary_id: int,
        org_ids: list[int] | None,
    ) -> tuple[FinancialSummary, str | None, str | None]:
        stmt = (
            select(
                FinancialSummary,
                Organization.name.label("org_name"),
                Shop.shop_color.label("shop_color"),
            )
            .outerjoin(Organization, Organization.id == FinancialSummary.org_id)
            .outerjoin(Shop, Shop.id == FinancialSummary.shop_id)
            .where(
                FinancialSummary.id == summary_id,
                FinancialSummary.is_deleted.is_(False),
                active_shop_filter(FinancialSummary.shop_id),
            )
        )
        if org_ids is not None:
            stmt = stmt.where(FinancialSummary.org_id.in_(org_ids))
        result = (await db.execute(stmt)).first()
        if result is None:
            raise ValueError("数据不存在或无权访问")
        summary, org_name, shop_color = result
        return summary, org_name, shop_color

    @staticmethod
    def _normalize_payload(payload: dict[str, object]) -> dict[str, object]:
        normalized: dict[str, object] = {}
        for key, value in payload.items():
            if key in MONEY_FIELDS:
                normalized[key] = safe_decimal(value)
            elif key in DATETIME_FIELDS:
                normalized[key] = parse_datetime(value)
            elif key in {"source_row_number", "summary_year", "summary_month"}:
                normalized[key] = int(value or 0)
            else:
                normalized[key] = DouyinDongzhangDetailService._clean_excel_text_prefix(value)
        return normalized

    @staticmethod
    def _clean_excel_text_prefix(value: object) -> str:
        text = str(value or "").strip()
        if text.startswith("'"):
            return text[1:].strip()
        return text

    @staticmethod
    def _format_export_value(value: object, *, money: bool) -> object:
        if money:
            return float(safe_decimal(value))
        if isinstance(value, Decimal):
            return float(value)
        if isinstance(value, datetime):
            return DouyinDongzhangDetailService._format_datetime(value)
        return value

    @staticmethod
    def _format_datetime(value: object) -> str:
        if isinstance(value, datetime):
            return value.strftime("%Y-%m-%d %H:%M:%S")
        return str(value or "")

    @staticmethod
    def _platform_label(platform: str | None) -> str:
        key = str(platform or "").strip()
        return PLATFORM_LABELS.get(key, key)

    @staticmethod
    def _ensure_row_limit(label: str, row_count: int) -> None:
        if row_count > DONGZHANG_DETAIL_EXPORT_ROW_LIMIT:
            raise ValueError(
                f"{label}导出数据量 {row_count} 行，超过系统上限 {DONGZHANG_DETAIL_EXPORT_ROW_LIMIT} 行，请缩小筛选范围后再导出"
            )
