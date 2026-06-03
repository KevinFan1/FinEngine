# Merchant Reconciliation Maintainability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract the most complex merchant reconciliation summary/export calculation code into focused modules while preserving existing API behavior and adding concise Chinese business comments.

**Architecture:** Keep `MerchantReconciliationService` as the API-facing facade. Add focused modules for summary calculations and workbook export, then delegate existing static methods to those modules so callers remain compatible. This first version avoids database schema changes, frontend changes, and broad import rewrites.

**Tech Stack:** Python 3, SQLAlchemy async service layer, OpenPyXL workbook generation, Pytest.

---

## File Structure

- Create: `backend/app/services/merchant_reconciliation_summary.py`
  - Owns pure summary-row construction, amount refreshing, opening balance merge, bank-flow total merge, payment adjustment allocation, sorting and filtering.
  - Contains Chinese comments for business rules around matching failures, bank-flow allocation and fallback behavior.

- Create: `backend/app/services/merchant_reconciliation_exporter.py`
  - Owns workbook creation/saving and export value formatting for merchant reconciliation summary/detail exports.
  - Keeps export formatting reusable so page and export calculations do not drift.

- Modify: `backend/app/services/merchant_reconciliation_service.py`
  - Imports the new modules.
  - Replaces extracted method bodies with delegation wrappers to preserve current public/private call sites.
  - Keeps behavior-compatible names such as `_refresh_summary_flow_amounts` and `_allocate_money_by_weight`.

- Modify: `backend/app/tests/test_merchant_reconciliation_service.py`
  - Adds focused tests for the new summary calculator and exporter modules.
  - Reuses existing merchant reconciliation tests as behavior regression coverage.

## Task 1: Summary Calculator Boundary

**Files:**
- Create: `backend/app/services/merchant_reconciliation_summary.py`
- Modify: `backend/app/services/merchant_reconciliation_service.py`
- Test: `backend/app/tests/test_merchant_reconciliation_service.py`

- [ ] **Step 1: Write failing summary calculator tests**

Add imports and tests to `backend/app/tests/test_merchant_reconciliation_service.py`:

```python
from app.services.merchant_reconciliation_summary import MerchantReconciliationSummaryBuilder
```

```python
def test_summary_builder_refreshes_bank_statuses() -> None:
    row = MerchantReconciliationSummaryBuilder.empty_summary_row(
        org_id=2,
        org_name="组织A",
        accounting_year=2026,
        accounting_month=4,
        our_subject="我方主体",
        receipt_subject="收款商家",
        adjustment={"paid_flow_amount": Decimal("70.00")},
    )
    row["merchant_payable_net_amount"] = Decimal("100.00")
    row["opening_balance"] = Decimal("10.00")
    row["business_fee_deduction"] = Decimal("5.00")
    row["other_deduction_amount"] = Decimal("2.00")
    row["bank_flow_amount"] = Decimal("33.00")

    MerchantReconciliationSummaryBuilder.refresh_summary_flow_amounts(row)

    assert row["payable_goods_balance"] == Decimal("103.00")
    assert row["unpaid_flow_amount"] == Decimal("33.00")
    assert row["bank_payment_diff"] == Decimal("0.00")
    assert row["bank_status"] == "matched"
```

```python
def test_summary_builder_allocates_money_by_weight_with_rounding_remainder() -> None:
    allocations = MerchantReconciliationSummaryBuilder.allocate_money_by_weight(
        Decimal("100.00"),
        [
            (("2", "主体A", "商家A"), Decimal("1")),
            (("2", "主体B", "商家B"), Decimal("2")),
            (("2", "主体C", "商家C"), Decimal("3")),
        ],
    )

    assert allocations[("2", "主体A", "商家A")] == Decimal("16.67")
    assert allocations[("2", "主体B", "商家B")] == Decimal("33.33")
    assert allocations[("2", "主体C", "商家C")] == Decimal("50.00")
    assert sum(allocations.values(), Decimal("0.00")) == Decimal("100.00")
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
cd backend && uv run pytest app/tests/test_merchant_reconciliation_service.py::test_summary_builder_refreshes_bank_statuses app/tests/test_merchant_reconciliation_service.py::test_summary_builder_allocates_money_by_weight_with_rounding_remainder -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'app.services.merchant_reconciliation_summary'`.

- [ ] **Step 3: Implement summary calculator**

Create `backend/app/services/merchant_reconciliation_summary.py` with:

```python
from __future__ import annotations

from collections.abc import Iterable
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from app.utils.money import ZERO_MONEY, safe_decimal
from app.tasks.processors.base import safe_str

MONEY_QUANT = Decimal("0.01")


def _normalize_text(value: object) -> str:
    return safe_str(value).strip()


def _entity_match_text(value: object) -> str:
    return (
        _normalize_text(value)
        .replace("（", "(")
        .replace("）", ")")
        .replace(" ", "")
        .replace("　", "")
        .upper()
    )


class MerchantReconciliationSummaryBuilder:
    @staticmethod
    def optional_int(value: object) -> int | None:
        if value is None or value == "":
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def empty_summary_row(
        *,
        org_name: str | None,
        accounting_year: int,
        accounting_month: int,
        our_subject: str,
        receipt_subject: str,
        org_id: int | None = None,
        adjustment: dict[str, Decimal] | None = None,
    ) -> dict[str, object]:
        adjustment = adjustment or {}
        row = {
            "key": f"{org_id or ''}|{our_subject}|{receipt_subject}",
            "org_id": org_id,
            "org_name": org_name,
            "accounting_year": accounting_year,
            "accounting_month": accounting_month,
            "accounting_date": f"{int(accounting_year):04d}-{int(accounting_month):02d}",
            "our_subject": our_subject,
            "merchant_receipt_subject": receipt_subject,
            "receipt_merchant": receipt_subject,
            "gmv": ZERO_MONEY,
            "merchant_payable_net_amount": ZERO_MONEY,
            "opening_balance": ZERO_MONEY,
            "business_fee_deduction": safe_decimal(adjustment.get("business_fee_deduction")),
            "other_deduction_amount": safe_decimal(adjustment.get("other_deduction_amount")),
            "payable_goods_balance": ZERO_MONEY,
            "paid_flow_amount": safe_decimal(adjustment.get("paid_flow_amount")),
            "unpaid_flow_amount": ZERO_MONEY,
            "bank_flow_amount": ZERO_MONEY,
            "bank_payment_diff": ZERO_MONEY,
            "row_count": 0,
            "bank_status": "pending",
        }
        MerchantReconciliationSummaryBuilder.refresh_summary_flow_amounts(row)
        return row

    @staticmethod
    def refresh_summary_flow_amounts(item: dict[str, object]) -> None:
        item["payable_goods_balance"] = (
            safe_decimal(item.get("merchant_payable_net_amount"))
            + safe_decimal(item.get("opening_balance"))
            - safe_decimal(item.get("business_fee_deduction"))
            - safe_decimal(item.get("other_deduction_amount"))
        )
        item["unpaid_flow_amount"] = safe_decimal(item["payable_goods_balance"]) - safe_decimal(item["paid_flow_amount"])
        item["bank_payment_diff"] = safe_decimal(item["unpaid_flow_amount"]) - safe_decimal(item["bank_flow_amount"])
        bank_flow_amount = safe_decimal(item["bank_flow_amount"])
        bank_payment_diff = safe_decimal(item["bank_payment_diff"])
        if bank_flow_amount == ZERO_MONEY:
            item["bank_status"] = "pending"
        elif bank_payment_diff == ZERO_MONEY:
            item["bank_status"] = "matched"
        else:
            item["bank_status"] = "diff"

    @staticmethod
    def allocate_money_by_weight(
        amount: Decimal,
        weighted_keys: list[tuple[tuple[str, str, str], Decimal]],
    ) -> dict[tuple[str, str, str], Decimal]:
        if not weighted_keys:
            return {}
        if len(weighted_keys) == 1:
            return {weighted_keys[0][0]: amount}

        weights = [(key, abs(safe_decimal(weight))) for key, weight in weighted_keys]
        total_weight = sum((weight for _key, weight in weights), ZERO_MONEY)
        if total_weight == ZERO_MONEY:
            weights = [(key, Decimal("1")) for key, _weight in weights]
            total_weight = Decimal(len(weights))

        allocations: dict[tuple[str, str, str], Decimal] = {}
        remaining = amount
        for index, (key, weight) in enumerate(weights):
            if index == len(weights) - 1:
                allocations[key] = remaining
                break
            value = (amount * weight / total_weight).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
            allocations[key] = value
            remaining -= value
        return allocations
```

- [ ] **Step 4: Run focused tests to verify pass**

Run:

```bash
cd backend && uv run pytest app/tests/test_merchant_reconciliation_service.py::test_summary_builder_refreshes_bank_statuses app/tests/test_merchant_reconciliation_service.py::test_summary_builder_allocates_money_by_weight_with_rounding_remainder -q
```

Expected: PASS.

- [ ] **Step 5: Move remaining pure summary methods into the builder**

Move these method bodies from `MerchantReconciliationService` into `MerchantReconciliationSummaryBuilder` and leave delegation wrappers in the service:

```python
_summary_group_key_from_detail_row -> summary_group_key_from_detail_row
_collect_summary_detail_totals -> collect_summary_detail_totals
_build_summary_rows_from_aggregates -> build_summary_rows_from_aggregates
_filter_summary_rows_by_bank_status -> filter_summary_rows_by_bank_status
_sort_summary_rows -> sort_summary_rows
_opening_balance_key -> opening_balance_key
_merge_opening_balance_rows -> merge_opening_balance_rows
_merge_bank_flow_totals -> merge_bank_flow_totals
_add_payment_adjustment -> add_payment_adjustment
```

In `backend/app/services/merchant_reconciliation_service.py`, add:

```python
from app.services.merchant_reconciliation_summary import MerchantReconciliationSummaryBuilder
```

Service wrappers must preserve names and behavior. Example:

```python
@staticmethod
def _allocate_money_by_weight(
    amount: Decimal,
    weighted_keys: list[tuple[tuple[str, str, str], Decimal]],
) -> dict[tuple[str, str, str], Decimal]:
    return MerchantReconciliationSummaryBuilder.allocate_money_by_weight(amount, weighted_keys)
```

- [ ] **Step 6: Run existing merchant reconciliation tests**

Run:

```bash
cd backend && uv run pytest app/tests/test_merchant_reconciliation_service.py -q
```

Expected: PASS.

## Task 2: Workbook Exporter Boundary

**Files:**
- Create: `backend/app/services/merchant_reconciliation_exporter.py`
- Modify: `backend/app/services/merchant_reconciliation_service.py`
- Test: `backend/app/tests/test_merchant_reconciliation_service.py`

- [ ] **Step 1: Write failing exporter test**

Add import:

```python
from app.services.merchant_reconciliation_exporter import MerchantReconciliationExporter
```

Add test:

```python
def test_exporter_formats_money_dates_and_datetimes() -> None:
    assert MerchantReconciliationExporter.format_export_value(Decimal("12.30"), money=True) == 12.3
    assert MerchantReconciliationExporter.format_export_value(datetime(2026, 4, 1, 9, 8, 7)) == "2026-04-01 09:08:07"
```

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
cd backend && uv run pytest app/tests/test_merchant_reconciliation_service.py::test_exporter_formats_money_dates_and_datetimes -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'app.services.merchant_reconciliation_exporter'`.

- [ ] **Step 3: Implement exporter**

Create `backend/app/services/merchant_reconciliation_exporter.py` with:

```python
from __future__ import annotations

import io
from collections.abc import Iterable
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from openpyxl import Workbook
from openpyxl.cell import WriteOnlyCell
from openpyxl.styles import Font

from app.utils.money import safe_decimal


class MerchantReconciliationExporter:
    @staticmethod
    def build_workbook(
        rows: Iterable[dict[str, object]],
        *,
        title: str,
        columns: tuple[tuple[str, str, bool], ...],
    ) -> io.BytesIO:
        wb = Workbook(write_only=True)
        ws = wb.create_sheet(title=title)
        ws.append(MerchantReconciliationExporter.header_row(ws, [label for _field, label, _money_flag in columns]))
        for row in rows:
            MerchantReconciliationExporter.append_row(ws, row, columns=columns)
        buffer = io.BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        return buffer

    @staticmethod
    def save_workbook(
        rows: Iterable[dict[str, object]],
        *,
        output_path: Path,
        title: str,
        columns: tuple[tuple[str, str, bool], ...],
    ) -> int:
        wb = Workbook(write_only=True)
        ws = wb.create_sheet(title=title)
        ws.append(MerchantReconciliationExporter.header_row(ws, [label for _field, label, _money_flag in columns]))
        row_count = 0
        for row in rows:
            MerchantReconciliationExporter.append_row(ws, row, columns=columns)
            row_count += 1
        wb.save(output_path)
        return row_count

    @staticmethod
    def header_row(sheet, headers: list[str]) -> list[WriteOnlyCell]:
        cells: list[WriteOnlyCell] = []
        for label in headers:
            cell = WriteOnlyCell(sheet, value=label)
            cell.font = Font(bold=True)
            cells.append(cell)
        return cells

    @staticmethod
    def append_row(
        ws,
        row: dict[str, object],
        *,
        columns: tuple[tuple[str, str, bool], ...],
    ) -> None:
        ws.append(
            [
                MerchantReconciliationExporter.format_export_value(row.get(field), money=money_flag)
                for field, _label, money_flag in columns
            ]
        )

    @staticmethod
    def format_export_value(value: object, *, money: bool = False) -> object:
        if money:
            return float(safe_decimal(value))
        if isinstance(value, Decimal):
            return float(value)
        if isinstance(value, datetime):
            return value.strftime("%Y-%m-%d %H:%M:%S")
        if isinstance(value, date):
            return value.isoformat()
        return value
```

- [ ] **Step 4: Delegate service export helpers**

In `backend/app/services/merchant_reconciliation_service.py`, add:

```python
from app.services.merchant_reconciliation_exporter import MerchantReconciliationExporter
```

Replace `_build_summary_workbook`, `_save_summary_workbook`, `_build_detail_workbook`, `_save_detail_workbook`, `_append_export_row`, `_format_export_value`, and `_format_datetime` bodies with delegation to `MerchantReconciliationExporter` while keeping the existing method names.

- [ ] **Step 5: Run focused exporter test**

Run:

```bash
cd backend && uv run pytest app/tests/test_merchant_reconciliation_service.py::test_exporter_formats_money_dates_and_datetimes -q
```

Expected: PASS.

- [ ] **Step 6: Run merchant reconciliation regression tests**

Run:

```bash
cd backend && uv run pytest app/tests/test_merchant_reconciliation_service.py -q
```

Expected: PASS.

## Task 3: Comments, Static Hygiene, and Verification

**Files:**
- Modify: `backend/app/services/merchant_reconciliation_summary.py`
- Modify: `backend/app/services/merchant_reconciliation_exporter.py`
- Modify: `backend/app/services/merchant_reconciliation_service.py`

- [ ] **Step 1: Add concise Chinese comments**

Add comments only for non-obvious business rules:

```python
# 匹配失败是业务结果，不能抛异常；前端需要展示具体失败原因让财务处理。
```

```python
# 银行流水先桥接红单付款，再按汇总权重分摊，避免同一笔付款被多个商品编码重复计入。
```

```python
# 兜底主体匹配只用于兼容历史数据；能桥接红单付款时始终以红单付款为准。
```

- [ ] **Step 2: Run placeholder scan**

Run:

```bash
rg -n "pass$" backend/app/services/merchant_reconciliation_summary.py backend/app/services/merchant_reconciliation_exporter.py
```

Expected: no output.

- [ ] **Step 3: Run target tests**

Run:

```bash
cd backend && uv run pytest app/tests/test_merchant_reconciliation_service.py app/tests/test_product_code.py app/tests/test_douyin_dongzhang_detail_service.py -q
```

Expected: PASS.

- [ ] **Step 4: Review changed files**

Run:

```bash
git diff -- backend/app/services/merchant_reconciliation_service.py backend/app/services/merchant_reconciliation_summary.py backend/app/services/merchant_reconciliation_exporter.py backend/app/tests/test_merchant_reconciliation_service.py
```

Expected: diff only contains summary/export extraction, delegation wrappers, focused tests, and concise Chinese comments.

- [ ] **Step 5: Commit only relevant files**

Run:

```bash
git add backend/app/services/merchant_reconciliation_service.py backend/app/services/merchant_reconciliation_summary.py backend/app/services/merchant_reconciliation_exporter.py backend/app/tests/test_merchant_reconciliation_service.py docs/superpowers/plans/2026-06-02-merchant-reconciliation-maintainability.md
git commit -m "refactor: split merchant reconciliation summary helpers"
```

Expected: commit includes only the plan and merchant reconciliation maintainability changes.
