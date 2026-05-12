"""Summary service — query and export financial summaries."""

import io
from decimal import Decimal

from openpyxl import Workbook
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.shop import Shop
from app.models.summary import FinancialSummary
from app.services.summary_adjustment_service import SummaryAdjustmentService

# Export header aligned with actual business Excel.
EXPORT_HEADERS = [
    "核算年月",
    "归属年月",
    "平台",
    "店铺",
    "实收GMV",
    "平台其他收入",
    "平台服务费",
    "退货费用及其他费用",
    "达人佣金",
    "招商服务费",
    "站外推广费",
    "服务商佣金",
    "支付捐赠费用",
    "运费险",
    "BIC",
]

REPORT_EXPORT_HEADERS = [
    "核算年月",
    "平台",
    "店铺",
    "原始实收GMV",
    "GMV调整",
    "调整后实收GMV",
    "平台其他收入",
    "平台服务费",
    "原始退货费用及其他费用",
    "退货费用调整",
    "调整后退货费用及其他费用",
    "达人佣金",
    "招商服务费",
    "站外推广费",
    "服务商佣金",
    "支付捐赠费用",
    "运费险",
    "BIC",
]

SUMMARY_MONEY_FIELDS = (
    "gmv",
    "platform_income",
    "platform_fee",
    "return_cost",
    "commission",
    "merchant_fee",
    "promotion_fee",
    "provider_commission",
    "donation_fee",
    "insurance_fee",
    "bic",
)


def split_filter_values(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def single_filter_value(value: str | None) -> str | None:
    values = split_filter_values(value)
    return values[0] if len(values) == 1 else None


def month_period_value(year: int | None, month: int | None) -> int | None:
    if year is None or month is None:
        return None
    return int(year) * 100 + int(month)


PLATFORM_LABELS = {
    "douyin": "抖音",
    "抖店": "抖音",
    "kuaishou": "快手",
    "快手": "快手",
    "xiaohongshu": "小红书",
    "小红书": "小红书",
    "weixin_video": "微信小店",
    "视频号": "微信小店",
    "微信小店": "微信小店",
    "tmall": "天猫",
    "天猫": "天猫",
    "taobao": "淘宝",
    "淘宝": "淘宝",
    "alipay": "支付宝",
    "支付宝": "支付宝",
    "qianniu": "千牛",
    "千牛": "千牛",
    "miniprogram": "小程序",
    "小程序": "小程序",
}


class SummaryService:
    @staticmethod
    async def list_summaries(
        db: AsyncSession,
        *,
        org_id: int,
        summary_year: int | None = None,
        summary_month: int | None = None,
        source_year: int | None = None,
        source_month: int | None = None,
        platform_name: str | None = None,
        report_platform_name: str | None = None,
        shop_id: int | None = None,
        shop_name: str | None = None,
        keyword: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[dict], int]:
        """Query financial summaries with filters."""
        stmt = (
            select(FinancialSummary, Shop.shop_color.label("shop_color"))
            .outerjoin(Shop, FinancialSummary.shop_id == Shop.id)
            .where(FinancialSummary.org_id == org_id, FinancialSummary.is_deleted.is_(False))
        )
        count_stmt = select(func.count()).select_from(FinancialSummary).where(FinancialSummary.org_id == org_id, FinancialSummary.is_deleted.is_(False))

        if summary_year is not None:
            stmt = stmt.where(FinancialSummary.summary_year == summary_year)
            count_stmt = count_stmt.where(FinancialSummary.summary_year == summary_year)

        if summary_month is not None:
            stmt = stmt.where(FinancialSummary.summary_month == summary_month)
            count_stmt = count_stmt.where(FinancialSummary.summary_month == summary_month)

        if source_year is not None:
            stmt = stmt.where(FinancialSummary.source_year == source_year)
            count_stmt = count_stmt.where(FinancialSummary.source_year == source_year)

        if source_month is not None:
            stmt = stmt.where(FinancialSummary.source_month == source_month)
            count_stmt = count_stmt.where(FinancialSummary.source_month == source_month)

        platform_names = split_filter_values(platform_name)
        if platform_names:
            stmt = stmt.where(FinancialSummary.source_platform_code.in_(platform_names))
            count_stmt = count_stmt.where(FinancialSummary.source_platform_code.in_(platform_names))

        report_platform_names = split_filter_values(report_platform_name)
        if report_platform_names:
            stmt = stmt.where(FinancialSummary.report_platform_code.in_(report_platform_names))
            count_stmt = count_stmt.where(FinancialSummary.report_platform_code.in_(report_platform_names))

        if shop_id is not None:
            stmt = stmt.where(FinancialSummary.shop_id == shop_id)
            count_stmt = count_stmt.where(FinancialSummary.shop_id == shop_id)

        shop_names = split_filter_values(shop_name)
        if shop_names:
            stmt = stmt.where(FinancialSummary.shop_name.in_(shop_names))
            count_stmt = count_stmt.where(FinancialSummary.shop_name.in_(shop_names))

        if keyword:
            like_pattern = f"%{keyword.strip()}%"
            keyword_cond = or_(
                FinancialSummary.shop_name.ilike(like_pattern),
                FinancialSummary.source_platform_code.ilike(like_pattern),
                FinancialSummary.report_platform_code.ilike(like_pattern),
            )
            stmt = stmt.where(keyword_cond)
            count_stmt = count_stmt.where(keyword_cond)

        stmt = stmt.order_by(
            FinancialSummary.source_year.desc(),
            FinancialSummary.source_month.desc(),
            FinancialSummary.summary_year.desc(),
            FinancialSummary.summary_month.desc(),
            FinancialSummary.source_platform_code,
            FinancialSummary.shop_name,
        )

        total_result = await db.execute(count_stmt)
        total = total_result.scalar() or 0

        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        result = await db.execute(stmt)
        summaries = [
            {
                "summary": summary,
                "shop_color": shop_color,
            }
            for summary, shop_color in result.all()
        ]

        return summaries, total

    @staticmethod
    async def export_summaries(
        db: AsyncSession,
        *,
        org_id: int,
        summary_year: int | None = None,
        summary_month: int | None = None,
        source_year: int | None = None,
        source_month: int | None = None,
        platform_name: str | None = None,
        report_platform_name: str | None = None,
        shop_id: int | None = None,
        shop_name: str | None = None,
        keyword: str | None = None,
        ids: list[int] | None = None,
        page: int | None = None,
        page_size: int | None = None,
    ) -> io.BytesIO:
        """Export financial summaries to an Excel file (in-memory BytesIO)."""
        # Query all matching rows (no pagination)
        stmt = select(FinancialSummary).where(FinancialSummary.org_id == org_id, FinancialSummary.is_deleted.is_(False))

        if ids is not None:
            if not ids:
                rows = []
                return SummaryService._build_summary_workbook(rows)
            stmt = stmt.where(FinancialSummary.id.in_(ids))

        if summary_year is not None:
            stmt = stmt.where(FinancialSummary.summary_year == summary_year)
        if summary_month is not None:
            stmt = stmt.where(FinancialSummary.summary_month == summary_month)
        if source_year is not None:
            stmt = stmt.where(FinancialSummary.source_year == source_year)
        if source_month is not None:
            stmt = stmt.where(FinancialSummary.source_month == source_month)
        platform_names = split_filter_values(platform_name)
        if platform_names:
            stmt = stmt.where(FinancialSummary.source_platform_code.in_(platform_names))
        report_platform_names = split_filter_values(report_platform_name)
        if report_platform_names:
            stmt = stmt.where(FinancialSummary.report_platform_code.in_(report_platform_names))
        if shop_id is not None:
            stmt = stmt.where(FinancialSummary.shop_id == shop_id)
        shop_names = split_filter_values(shop_name)
        if shop_names:
            stmt = stmt.where(FinancialSummary.shop_name.in_(shop_names))
        if keyword:
            like_pattern = f"%{keyword.strip()}%"
            stmt = stmt.where(
                or_(
                    FinancialSummary.shop_name.ilike(like_pattern),
                    FinancialSummary.source_platform_code.ilike(like_pattern),
                    FinancialSummary.report_platform_code.ilike(like_pattern),
                )
            )

        stmt = stmt.order_by(
            FinancialSummary.source_year.desc(),
            FinancialSummary.source_month.desc(),
            FinancialSummary.summary_year.desc(),
            FinancialSummary.summary_month.desc(),
            FinancialSummary.source_platform_code,
            FinancialSummary.shop_name,
        )

        if page is not None and page_size is not None:
            stmt = stmt.offset((page - 1) * page_size).limit(page_size)

        result = await db.execute(stmt)
        rows = list(result.scalars().all())

        return SummaryService._build_summary_workbook(rows)

    @staticmethod
    async def list_report_summaries(
        db: AsyncSession,
        *,
        org_id: int,
        source_year: int | None = None,
        source_month: int | None = None,
        source_start_year: int | None = None,
        source_start_month: int | None = None,
        source_end_year: int | None = None,
        source_end_month: int | None = None,
        platform_name: str | None = None,
        report_platform_name: str | None = None,
        shop_id: int | None = None,
        shop_name: str | None = None,
        keyword: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[dict], int]:
        """Aggregate financial summaries by accounting year/month."""
        filters = SummaryService._build_report_filters(
            org_id=org_id,
            source_year=source_year,
            source_month=source_month,
            source_start_year=source_start_year,
            source_start_month=source_start_month,
            source_end_year=source_end_year,
            source_end_month=source_end_month,
            platform_name=report_platform_name or platform_name,
            shop_id=shop_id,
            shop_name=shop_name,
            keyword=keyword,
        )
        group_cols = (
            FinancialSummary.org_id,
            FinancialSummary.source_year,
            FinancialSummary.source_month,
            FinancialSummary.report_platform_code,
            FinancialSummary.shop_id,
            FinancialSummary.shop_name,
        )

        grouped_stmt = select(*group_cols).where(*filters).group_by(*group_cols).subquery()
        total_result = await db.execute(select(func.count()).select_from(grouped_stmt))
        total = total_result.scalar() or 0

        metric_cols = [func.coalesce(func.sum(getattr(FinancialSummary, field)), 0).label(field) for field in SUMMARY_MONEY_FIELDS]
        stmt = (
            select(
                FinancialSummary.org_id.label("org_id"),
                FinancialSummary.source_year.label("source_year"),
                FinancialSummary.source_month.label("source_month"),
                FinancialSummary.report_platform_code.label("platform_name"),
                FinancialSummary.report_platform_code.label("report_platform_code"),
                FinancialSummary.shop_id.label("shop_id"),
                FinancialSummary.shop_name.label("shop_name"),
                func.max(Shop.shop_color).label("shop_color"),
                func.count(FinancialSummary.id).label("summary_count"),
                *metric_cols,
            )
            .outerjoin(Shop, FinancialSummary.shop_id == Shop.id)
            .where(*filters)
            .group_by(*group_cols)
            .order_by(
                FinancialSummary.source_year.desc(),
                FinancialSummary.source_month.desc(),
                FinancialSummary.report_platform_code,
                FinancialSummary.shop_name,
            )
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await db.execute(stmt)
        rows = [dict(row) for row in result.mappings().all()]
        rows = await SummaryService._apply_report_adjustments(
            db,
            org_id=org_id,
            rows=rows,
            source_year=source_year,
            source_month=source_month,
            source_start_year=source_start_year,
            source_start_month=source_start_month,
            source_end_year=source_end_year,
            source_end_month=source_end_month,
            platform_name=single_filter_value(report_platform_name or platform_name),
            shop_id=shop_id,
            shop_name=single_filter_value(shop_name),
        )
        return rows, total

    @staticmethod
    async def export_report_summaries(
        db: AsyncSession,
        *,
        org_id: int,
        source_year: int | None = None,
        source_month: int | None = None,
        source_start_year: int | None = None,
        source_start_month: int | None = None,
        source_end_year: int | None = None,
        source_end_month: int | None = None,
        platform_name: str | None = None,
        report_platform_name: str | None = None,
        shop_id: int | None = None,
        shop_name: str | None = None,
        keyword: str | None = None,
        ids: list[str] | None = None,
        page: int | None = None,
        page_size: int | None = None,
    ) -> io.BytesIO:
        """Export accounting-month aggregated summaries to Excel."""
        filters = SummaryService._build_report_filters(
            org_id=org_id,
            source_year=source_year,
            source_month=source_month,
            source_start_year=source_start_year,
            source_start_month=source_start_month,
            source_end_year=source_end_year,
            source_end_month=source_end_month,
            platform_name=report_platform_name or platform_name,
            shop_id=shop_id,
            shop_name=shop_name,
            keyword=keyword,
        )
        group_cols = (
            FinancialSummary.org_id,
            FinancialSummary.source_year,
            FinancialSummary.source_month,
            FinancialSummary.report_platform_code,
            FinancialSummary.shop_id,
            FinancialSummary.shop_name,
        )
        metric_cols = [func.coalesce(func.sum(getattr(FinancialSummary, field)), 0).label(field) for field in SUMMARY_MONEY_FIELDS]
        stmt = (
            select(
                FinancialSummary.org_id.label("org_id"),
                FinancialSummary.source_year.label("source_year"),
                FinancialSummary.source_month.label("source_month"),
                FinancialSummary.report_platform_code.label("platform_name"),
                FinancialSummary.report_platform_code.label("report_platform_code"),
                FinancialSummary.shop_id.label("shop_id"),
                FinancialSummary.shop_name.label("shop_name"),
                func.max(Shop.shop_color).label("shop_color"),
                func.count(FinancialSummary.id).label("summary_count"),
                *metric_cols,
            )
            .outerjoin(Shop, FinancialSummary.shop_id == Shop.id)
            .where(*filters)
            .group_by(*group_cols)
            .order_by(
                FinancialSummary.source_year.desc(),
                FinancialSummary.source_month.desc(),
                FinancialSummary.report_platform_code,
                FinancialSummary.shop_name,
            )
        )

        if page is not None and page_size is not None:
            stmt = stmt.offset((page - 1) * page_size).limit(page_size)

        result = await db.execute(stmt)
        rows = [dict(row) for row in result.mappings().all()]
        rows = await SummaryService._apply_report_adjustments(
            db,
            org_id=org_id,
            rows=rows,
            source_year=source_year,
            source_month=source_month,
            source_start_year=source_start_year,
            source_start_month=source_start_month,
            source_end_year=source_end_year,
            source_end_month=source_end_month,
            platform_name=single_filter_value(report_platform_name or platform_name),
            shop_id=shop_id,
            shop_name=single_filter_value(shop_name),
        )
        if ids is not None:
            selected_ids = set(ids)
            rows = [row for row in rows if SummaryService.report_row_id(row) in selected_ids]
        return SummaryService._build_report_workbook(rows)

    @staticmethod
    def _build_summary_workbook(rows: list[FinancialSummary]) -> io.BytesIO:
        # Build Excel workbook
        wb = Workbook()
        ws = wb.active
        ws.title = "财务汇总"

        # Write header
        ws.append(EXPORT_HEADERS)

        # Write data rows
        for s in rows:
            ws.append(
                [
                    SummaryService._month_label(s.source_year, s.source_month),
                    f"{s.summary_year}{s.summary_month:02d}",
                    SummaryService._platform_label(s.source_platform_code),
                    s.shop_name,
                    float(s.gmv or 0),
                    float(s.platform_income or 0),
                    float(s.platform_fee or 0),
                    float(s.return_cost or 0),
                    float(s.commission or 0),
                    float(s.merchant_fee or 0),
                    float(s.promotion_fee or 0),
                    float(s.provider_commission or 0),
                    float(s.donation_fee or 0),
                    float(s.insurance_fee or 0),
                    float(s.bic or 0),
                ]
            )

        # Auto-width columns (approximate)
        for col_idx, header in enumerate(EXPORT_HEADERS, 1):
            max_len = len(header)
            for row in ws.iter_rows(min_row=2, min_col=col_idx, max_col=col_idx, values_only=True):
                val = row[0]
                if val is not None:
                    max_len = max(max_len, len(str(val)))
            ws.column_dimensions[ws.cell(row=1, column=col_idx).column_letter].width = min(max_len + 4, 30)

        # Save to BytesIO
        buffer = io.BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        return buffer

    @staticmethod
    def _build_report_workbook(rows: list[dict]) -> io.BytesIO:
        wb = Workbook()
        ws = wb.active
        ws.title = "汇总报表"
        ws.append(REPORT_EXPORT_HEADERS)

        for row in rows:
            ws.append(
                [
                    SummaryService._month_label(int(row.get("source_year") or 0), int(row.get("source_month") or 0)),
                    SummaryService._platform_label(str(row.get("platform_name") or "")),
                    row.get("shop_name") or "",
                    float(row.get("original_gmv") or 0),
                    float(row.get("gmv_adjustment") or 0),
                    float(row.get("gmv") or 0),
                    float(row.get("platform_income") or 0),
                    float(row.get("platform_fee") or 0),
                    float(row.get("original_return_cost") or 0),
                    float(row.get("return_cost_adjustment") or 0),
                    float(row.get("return_cost") or 0),
                    float(row.get("commission") or 0),
                    float(row.get("merchant_fee") or 0),
                    float(row.get("promotion_fee") or 0),
                    float(row.get("provider_commission") or 0),
                    float(row.get("donation_fee") or 0),
                    float(row.get("insurance_fee") or 0),
                    float(row.get("bic") or 0),
                ]
            )

        for col_idx, header in enumerate(REPORT_EXPORT_HEADERS, 1):
            max_len = len(header)
            for row in ws.iter_rows(min_row=2, min_col=col_idx, max_col=col_idx, values_only=True):
                val = row[0]
                if val is not None:
                    max_len = max(max_len, len(str(val)))
            ws.column_dimensions[ws.cell(row=1, column=col_idx).column_letter].width = min(max_len + 4, 30)

        buffer = io.BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        return buffer

    @staticmethod
    def _platform_label(platform_name: str) -> str:
        return PLATFORM_LABELS.get(platform_name, platform_name)

    @staticmethod
    def report_row_id(row: dict) -> str:
        return f"{int(row.get('source_year') or 0)}-{int(row.get('source_month') or 0)}-{row.get('platform_name') or ''}-{int(row.get('shop_id') or 0)}"

    @staticmethod
    def _month_label(year: int | None, month: int | None) -> str:
        if not year or not month:
            return "未解析"
        return f"{int(year)}{int(month):02d}"

    @staticmethod
    async def _apply_report_adjustments(
        db: AsyncSession,
        *,
        org_id: int,
        rows: list[dict],
        source_year: int | None,
        source_month: int | None,
        source_start_year: int | None,
        source_start_month: int | None,
        source_end_year: int | None,
        source_end_month: int | None,
        platform_name: str | None,
        shop_id: int | None,
        shop_name: str | None,
    ) -> list[dict]:
        if not rows:
            return rows

        adjustment_sums = await SummaryAdjustmentService.list_adjustment_sums(
            db,
            org_id=org_id,
            source_year=source_year,
            source_month=source_month,
            source_start_year=source_start_year,
            source_start_month=source_start_month,
            source_end_year=source_end_year,
            source_end_month=source_end_month,
            platform_name=platform_name,
            shop_id=shop_id,
            shop_name=shop_name,
        )
        for row in rows:
            key = (
                int(row.get("source_year") or 0),
                int(row.get("source_month") or 0),
                str(row.get("platform_name") or ""),
                int(row.get("shop_id") or 0),
                str(row.get("shop_name") or ""),
            )
            adjustments = adjustment_sums.get(key, {})
            original_gmv = Decimal(str(row.get("gmv") or 0))
            gmv_adjustment = adjustments.get("gmv", Decimal("0"))
            original_return_cost = Decimal(str(row.get("return_cost") or 0))
            return_cost_adjustment = adjustments.get("return_cost", Decimal("0"))

            row["original_gmv"] = original_gmv
            row["gmv_adjustment"] = gmv_adjustment
            row["gmv"] = original_gmv + gmv_adjustment
            row["original_return_cost"] = original_return_cost
            row["return_cost_adjustment"] = return_cost_adjustment
            row["return_cost"] = original_return_cost + return_cost_adjustment
        return rows

    @staticmethod
    def _build_report_filters(
        *,
        org_id: int,
        source_year: int | None,
        source_month: int | None,
        source_start_year: int | None = None,
        source_start_month: int | None = None,
        source_end_year: int | None = None,
        source_end_month: int | None = None,
        platform_name: str | None,
        shop_id: int | None,
        shop_name: str | None,
        keyword: str | None = None,
    ):
        filters = [FinancialSummary.org_id == org_id, FinancialSummary.is_deleted.is_(False)]
        if source_year is not None:
            filters.append(FinancialSummary.source_year == source_year)
        if source_month is not None:
            filters.append(FinancialSummary.source_month == source_month)
        source_period = FinancialSummary.source_year * 100 + FinancialSummary.source_month
        source_start_period = month_period_value(source_start_year, source_start_month)
        source_end_period = month_period_value(source_end_year, source_end_month)
        if source_start_period is not None:
            filters.append(source_period >= source_start_period)
        if source_end_period is not None:
            filters.append(source_period <= source_end_period)
        platform_names = split_filter_values(platform_name)
        if platform_names:
            filters.append(FinancialSummary.report_platform_code.in_(platform_names))
        if shop_id is not None:
            filters.append(FinancialSummary.shop_id == shop_id)
        shop_names = split_filter_values(shop_name)
        if shop_names:
            filters.append(FinancialSummary.shop_name.in_(shop_names))
        if keyword:
            like_pattern = f"%{keyword.strip()}%"
            filters.append(
                or_(
                    FinancialSummary.shop_name.ilike(like_pattern),
                    FinancialSummary.source_platform_code.ilike(like_pattern),
                    FinancialSummary.report_platform_code.ilike(like_pattern),
                )
            )
        return filters
