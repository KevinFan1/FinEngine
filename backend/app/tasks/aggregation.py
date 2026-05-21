"""Aggregation service — upsert parsed financial data into the summary table."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.shop import Shop
from app.models.summary import FinancialSummary
from app.services.shop_service import ShopService
from app.tasks.processors.base import normalize_positive_summary_fields
from app.utils.money import ZERO_MONEY, safe_decimal


class AggregationService:
    """Upsert financial data into the summary table.

    Same (org_id, business year/month, shop_id, upload year/month) merges into
    one row.
    Different type_codes write to different columns:
      - 动账:  gmv, platform_income, platform_fee, return_cost, commission,
               merchant_fee, promotion_fee, provider_commission, donation_fee
      - gmv:   same financial summary fields as 动账
      - 运费险: insurance_fee
      - bic:   bic
    """

    DONGZHANG_FIELDS = (
        "order_paid_amount",
        "refund_amount",
        "gmv",
        "platform_income",
        "platform_fee",
        "return_cost",
        "commission",
        "merchant_fee",
        "promotion_fee",
        "provider_commission",
        "donation_fee",
    )

    @staticmethod
    async def upsert_summary(
        db: AsyncSession,
        *,
        org_id: int,
        shop_id: int | None,
        year: int,
        month: int,
        platform_name: str,
        shop_name: str,
        type_code: str,
        rows: list[dict],
        source_file_id: int,
        source_year: int | None = None,
        source_month: int | None = None,
        source_platform_code: str | None = None,
        report_platform_code: str | None = None,
        shop_platform_code: str | None = None,
    ) -> FinancialSummary:
        """Merge parsed rows into the summary table."""
        source_platform, report_platform, shop_platform = AggregationService._normalize_platform_codes(
            platform_name=platform_name,
            source_platform_code=source_platform_code,
            report_platform_code=report_platform_code,
            shop_platform_code=shop_platform_code,
        )
        shop = await AggregationService._resolve_shop(
            db,
            org_id=org_id,
            shop_id=shop_id,
            platform_name=shop_platform,
            shop_name=shop_name,
        )
        source_year_value = AggregationService._normalize_source_date_part(source_year)
        source_month_value = AggregationService._normalize_source_date_part(source_month)
        # Find existing or create new
        stmt = select(FinancialSummary).where(
            FinancialSummary.org_id == org_id,
            FinancialSummary.summary_year == year,
            FinancialSummary.summary_month == month,
            FinancialSummary.shop_id == shop.id,
            FinancialSummary.source_platform_code == source_platform,
            FinancialSummary.source_year == source_year_value,
            FinancialSummary.source_month == source_month_value,
            FinancialSummary.is_deleted.is_(False),
        )
        result = await db.execute(stmt)
        summary = result.scalar_one_or_none()

        if summary is None:
            summary = FinancialSummary(
                org_id=org_id,
                shop_id=shop.id,
                summary_year=year,
                summary_month=month,
                source_year=source_year_value,
                source_month=source_month_value,
                source_platform_code=source_platform,
                report_platform_code=report_platform,
                platform_name=source_platform,
                shop_name=shop.shop_name,
            )
            db.add(summary)
            await db.flush()
        else:
            summary.source_platform_code = source_platform
            summary.report_platform_code = report_platform
            summary.platform_name = source_platform
            summary.shop_name = shop.shop_name

        # Aggregate rows by type
        if type_code in {"动账", "gmv"}:
            for key in AggregationService.DONGZHANG_FIELDS:
                setattr(summary, key, AggregationService._sum_rows(rows, key))
            AggregationService._normalize_positive_fields(summary)
        elif type_code == "运费险":
            summary.insurance_fee = AggregationService._sum_rows(rows, "insurance_fee")
        elif type_code == "bic":
            summary.bic = AggregationService._sum_rows(rows, "bic")

        # Track source file
        if summary.source_file_ids is None:
            summary.source_file_ids = []
        if source_file_id not in summary.source_file_ids:
            summary.source_file_ids = summary.source_file_ids + [source_file_id]
        summary.last_file_id = source_file_id

        await db.flush()
        return summary

    @staticmethod
    async def upsert_summary_dict(
        db: AsyncSession,
        *,
        org_id: int,
        shop_id: int | None,
        year: int,
        month: int,
        platform_name: str,
        shop_name: str,
        values: dict,
        source_file_id: int,
        source_year: int | None = None,
        source_month: int | None = None,
        source_platform_code: str | None = None,
        report_platform_code: str | None = None,
        shop_platform_code: str | None = None,
    ) -> FinancialSummary:
        """Write pre-aggregated values directly into the summary table.

        Used by platform processors that have already computed the sums
        internally. *values* keys correspond to FinancialSummary columns:
          order_paid_amount, refund_amount, gmv, platform_income, platform_fee, return_cost, commission,
          merchant_fee, promotion_fee, provider_commission, donation_fee,
          insurance_fee, bic
        """
        source_platform, report_platform, shop_platform = AggregationService._normalize_platform_codes(
            platform_name=platform_name,
            source_platform_code=source_platform_code,
            report_platform_code=report_platform_code,
            shop_platform_code=shop_platform_code,
        )
        shop = await AggregationService._resolve_shop(
            db,
            org_id=org_id,
            shop_id=shop_id,
            platform_name=shop_platform,
            shop_name=shop_name,
        )
        source_year_value = AggregationService._normalize_source_date_part(source_year)
        source_month_value = AggregationService._normalize_source_date_part(source_month)
        stmt = select(FinancialSummary).where(
            FinancialSummary.org_id == org_id,
            FinancialSummary.summary_year == year,
            FinancialSummary.summary_month == month,
            FinancialSummary.shop_id == shop.id,
            FinancialSummary.source_platform_code == source_platform,
            FinancialSummary.source_year == source_year_value,
            FinancialSummary.source_month == source_month_value,
            FinancialSummary.is_deleted.is_(False),
        )
        result = await db.execute(stmt)
        summary = result.scalar_one_or_none()

        if summary is None:
            summary = FinancialSummary(
                org_id=org_id,
                shop_id=shop.id,
                summary_year=year,
                summary_month=month,
                source_year=source_year_value,
                source_month=source_month_value,
                source_platform_code=source_platform,
                report_platform_code=report_platform,
                platform_name=source_platform,
                shop_name=shop.shop_name,
            )
            db.add(summary)
            await db.flush()
        else:
            summary.source_platform_code = source_platform
            summary.report_platform_code = report_platform
            summary.platform_name = source_platform
            summary.shop_name = shop.shop_name

        # Directly set aggregated values
        for key in (
            *AggregationService.DONGZHANG_FIELDS,
            "insurance_fee",
            "bic",
        ):
            if key in values:
                setattr(summary, key, safe_decimal(values[key]))
        AggregationService._normalize_positive_fields(summary)

        # Track source file
        if summary.source_file_ids is None:
            summary.source_file_ids = []
        if source_file_id not in summary.source_file_ids:
            summary.source_file_ids = summary.source_file_ids + [source_file_id]
        summary.last_file_id = source_file_id

        await db.flush()
        return summary

    @staticmethod
    async def upsert_return_cost_contribution(
        db: AsyncSession,
        *,
        org_id: int,
        shop_id: int | None,
        year: int,
        month: int,
        platform_name: str,
        shop_name: str,
        contribution_key: str,
        return_cost: object,
        source_file_id: int,
        source_year: int | None = None,
        source_month: int | None = None,
        source_platform_code: str | None = None,
        report_platform_code: str | None = None,
        shop_platform_code: str | None = None,
    ) -> FinancialSummary:
        """Upsert one file's return-cost contribution and recompute the total.

        小红书的「退货费用及其他费用」来自两个文件:
          其他服务款: 小额打款求和 A
          动账: 小额收款求和 B
        Final value is A - B. We store each source type contribution and set
        return_cost to their sum so recalculating one source replaces its value
        instead of double-counting or clearing the other source's value.
        """
        summary = await AggregationService._get_or_create_summary(
            db,
            org_id=org_id,
            shop_id=shop_id,
            year=year,
            month=month,
            platform_name=platform_name,
            shop_name=shop_name,
            source_year=source_year,
            source_month=source_month,
            source_platform_code=source_platform_code,
            report_platform_code=report_platform_code,
            shop_platform_code=shop_platform_code,
        )

        extra_data = dict(summary.extra_data or {})
        contributions = dict(extra_data.get("return_cost_contributions") or {})
        legacy_prefix = f"{contribution_key}:"
        for key in list(contributions):
            if key == contribution_key or key.startswith(legacy_prefix):
                contributions.pop(key, None)

        contribution_id = contribution_key
        contributions[contribution_id] = str(safe_decimal(return_cost))
        extra_data["return_cost_contributions"] = contributions
        summary.extra_data = extra_data
        summary.return_cost = sum((safe_decimal(value) for value in contributions.values()), ZERO_MONEY)

        if summary.source_file_ids is None:
            summary.source_file_ids = []
        if source_file_id not in summary.source_file_ids:
            summary.source_file_ids = summary.source_file_ids + [source_file_id]
        summary.last_file_id = source_file_id

        await db.flush()
        return summary

    @staticmethod
    def _sum_rows(rows: list[dict], key: str):
        total = ZERO_MONEY
        for row in rows:
            total += safe_decimal(row.get(key))
        return total

    @staticmethod
    def _normalize_positive_fields(summary: FinancialSummary) -> None:
        values = normalize_positive_summary_fields(
            {
                "refund_amount": summary.refund_amount,
                "commission": summary.commission,
                "merchant_fee": summary.merchant_fee,
                "promotion_fee": summary.promotion_fee,
                "provider_commission": summary.provider_commission,
            }
        )
        for field, value in values.items():
            setattr(summary, field, value)

    @staticmethod
    def _normalize_source_date_part(value: int | None) -> int:
        return int(value or 0)

    @staticmethod
    async def _get_or_create_summary(
        db: AsyncSession,
        *,
        org_id: int,
        shop_id: int | None,
        year: int,
        month: int,
        platform_name: str,
        shop_name: str,
        source_year: int | None = None,
        source_month: int | None = None,
        source_platform_code: str | None = None,
        report_platform_code: str | None = None,
        shop_platform_code: str | None = None,
    ) -> FinancialSummary:
        source_platform, report_platform, shop_platform = AggregationService._normalize_platform_codes(
            platform_name=platform_name,
            source_platform_code=source_platform_code,
            report_platform_code=report_platform_code,
            shop_platform_code=shop_platform_code,
        )
        shop = await AggregationService._resolve_shop(
            db,
            org_id=org_id,
            shop_id=shop_id,
            platform_name=shop_platform,
            shop_name=shop_name,
        )
        source_year_value = AggregationService._normalize_source_date_part(source_year)
        source_month_value = AggregationService._normalize_source_date_part(source_month)
        stmt = select(FinancialSummary).where(
            FinancialSummary.org_id == org_id,
            FinancialSummary.summary_year == year,
            FinancialSummary.summary_month == month,
            FinancialSummary.shop_id == shop.id,
            FinancialSummary.source_platform_code == source_platform,
            FinancialSummary.source_year == source_year_value,
            FinancialSummary.source_month == source_month_value,
            FinancialSummary.is_deleted.is_(False),
        )
        result = await db.execute(stmt)
        summary = result.scalar_one_or_none()

        if summary is None:
            summary = FinancialSummary(
                org_id=org_id,
                shop_id=shop.id,
                summary_year=year,
                summary_month=month,
                source_year=source_year_value,
                source_month=source_month_value,
                source_platform_code=source_platform,
                report_platform_code=report_platform,
                platform_name=source_platform,
                shop_name=shop.shop_name,
            )
            db.add(summary)
            await db.flush()
        else:
            summary.source_platform_code = source_platform
            summary.report_platform_code = report_platform
            summary.platform_name = source_platform
            summary.shop_name = shop.shop_name

        return summary

    @staticmethod
    def _normalize_platform_codes(
        *,
        platform_name: str,
        source_platform_code: str | None,
        report_platform_code: str | None,
        shop_platform_code: str | None,
    ) -> tuple[str, str, str]:
        source_platform = (source_platform_code or platform_name).strip()
        report_platform = (report_platform_code or source_platform).strip()
        shop_platform = (shop_platform_code or report_platform).strip()
        return source_platform, report_platform, shop_platform

    @staticmethod
    async def _resolve_shop(
        db: AsyncSession,
        *,
        org_id: int,
        shop_id: int | None,
        platform_name: str,
        shop_name: str,
    ) -> Shop:
        if shop_id is not None:
            result = await db.execute(select(Shop).where(Shop.id == shop_id, Shop.org_id == org_id, Shop.is_deleted.is_(False)))
            shop = result.scalar_one_or_none()
            if shop is not None:
                return shop

        result = await db.execute(
            select(Shop).where(
                Shop.org_id == org_id,
                Shop.platform_name == platform_name,
                Shop.shop_name == shop_name,
                Shop.is_deleted.is_(False),
            )
        )
        shop = result.scalar_one_or_none()
        if shop is None:
            shop = await ShopService.get_or_create_shop(
                db,
                org_id=org_id,
                platform_name=platform_name,
                shop_name=shop_name,
            )
        return shop
