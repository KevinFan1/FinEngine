from decimal import Decimal

import pytest

from app.models.shop import Shop
from app.models.summary import FinancialSummary
from app.tasks.aggregation import AggregationService


class _ScalarResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class _SummaryInsertConflictSession:
    def __init__(self, *, shop: Shop, summary: FinancialSummary) -> None:
        self.shop = shop
        self.summary = summary
        self.statements = []
        self.flush_count = 0

    async def execute(self, stmt):
        self.statements.append(stmt)
        if len(self.statements) == 1 and getattr(stmt, "is_select", False):
            return _ScalarResult(self.shop)
        if len(self.statements) == 2 and getattr(stmt, "is_insert", False):
            return _ScalarResult(None)
        if len(self.statements) == 3 and getattr(stmt, "is_select", False):
            return _ScalarResult(self.summary)
        raise AssertionError(f"unexpected statement: {stmt!r}")

    def add(self, _instance):
        raise AssertionError("summary upsert must not use select-then-add")

    async def flush(self):
        self.flush_count += 1


@pytest.mark.asyncio
async def test_summary_upsert_reads_existing_row_after_insert_conflict() -> None:
    shop = Shop(id=12, org_id=2, platform_name="douyin", shop_name="抖音店铺")
    summary = FinancialSummary(
        id=99,
        org_id=2,
        shop_id=12,
        summary_year=2026,
        summary_month=4,
        source_year=2026,
        source_month=4,
        source_platform_code="douyin",
        report_platform_code="douyin",
        platform_name="douyin",
        shop_name="抖音店铺",
        gmv=Decimal("0"),
        source_file_ids=[1],
    )
    db = _SummaryInsertConflictSession(shop=shop, summary=summary)

    result = await AggregationService.upsert_summary_dict(
        db,  # type: ignore[arg-type]
        org_id=2,
        shop_id=12,
        year=2026,
        month=4,
        platform_name="douyin",
        shop_name="抖音店铺",
        values={"gmv": Decimal("123.45")},
        source_file_id=7,
        source_year=2026,
        source_month=4,
        source_platform_code="douyin",
        report_platform_code="douyin",
    )

    assert result is summary
    assert len(db.statements) == 3
    assert getattr(db.statements[1], "is_insert", False)
    assert getattr(db.statements[2], "is_select", False)
    assert summary.gmv == Decimal("123.45")
    assert summary.source_file_ids == [1, 7]
    assert summary.last_file_id == 7
    assert db.flush_count == 1
