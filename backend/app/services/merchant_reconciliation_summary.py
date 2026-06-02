"""商家对账汇总计算工具。

该模块只放纯计算和汇总行合并逻辑，不处理 API、Excel 解析或审计日志。
"""

from __future__ import annotations

from collections.abc import Iterable
from decimal import Decimal, ROUND_HALF_UP

from app.models.merchant_reconciliation import MerchantOpeningBalance
from app.tasks.processors.base import safe_str
from app.utils.money import ZERO_MONEY, safe_decimal

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
    """商家对账汇总行的纯计算边界。"""

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
    def summary_group_key_from_detail_row(row: dict[str, object]) -> tuple[str, str, str]:
        org_id = MerchantReconciliationSummaryBuilder.optional_int(row.get("org_id"))
        return (
            str(org_id) if org_id is not None else _normalize_text(row.get("org_name")),
            _normalize_text(row.get("merchant_name") or row.get("our_subject") or row.get("shop_name")),
            _normalize_text(row.get("receipt_merchant") or row.get("merchant_receipt_subject")),
        )

    @staticmethod
    def collect_summary_detail_totals(
        rows: Iterable[dict[str, object]],
    ) -> tuple[dict[tuple[str, str, str], dict[str, object]], dict[int, dict[tuple[str, str, str], Decimal]]]:
        detail_totals: dict[tuple[str, str, str], dict[str, object]] = {}
        payment_group_weights: dict[int, dict[tuple[str, str, str], Decimal]] = {}
        for row in rows:
            # 汇总口径以动账大商家和红单收款商家为主，不直接按商品编码出汇总行。
            key = MerchantReconciliationSummaryBuilder.summary_group_key_from_detail_row(row)
            item = detail_totals.setdefault(
                key,
                {
                    "org_id": MerchantReconciliationSummaryBuilder.optional_int(row.get("org_id")),
                    "org_name": row.get("org_name"),
                    "gmv": ZERO_MONEY,
                    "merchant_payable_net_amount": ZERO_MONEY,
                    "row_count": 0,
                },
            )
            gmv = safe_decimal(row.get("gmv"))
            live_amount = safe_decimal(row.get("live_amount"))
            item["gmv"] = safe_decimal(item["gmv"]) + gmv
            item["merchant_payable_net_amount"] = safe_decimal(item["merchant_payable_net_amount"]) + live_amount
            item["row_count"] = int(item["row_count"]) + int(row.get("row_count") or 1)
            if not item.get("org_name") and row.get("org_name"):
                item["org_name"] = row.get("org_name")

            payment_id = MerchantReconciliationSummaryBuilder.optional_int(row.get("red_sheet_payment_id"))
            if payment_id is None:
                continue
            group_weights = payment_group_weights.setdefault(payment_id, {})
            group_weights[key] = group_weights.get(key, ZERO_MONEY) + live_amount
        return detail_totals, payment_group_weights

    @staticmethod
    def build_summary_rows_from_aggregates(
        *,
        detail_totals: dict[tuple[str, str, str], dict[str, object]],
        payment_adjustments: dict[tuple[str, str, str], dict[str, Decimal]],
        accounting_year: int,
        accounting_month: int,
    ) -> list[dict[str, object]]:
        summary_by_key: dict[tuple[str, str, str], dict[str, object]] = {}
        for key, adjustment in payment_adjustments.items():
            org_token, our_subject, receipt_merchant = key
            row_org_id = MerchantReconciliationSummaryBuilder.optional_int(
                adjustment.get("org_id")
            ) or MerchantReconciliationSummaryBuilder.optional_int(org_token)
            org_name = safe_str(adjustment.get("org_name")) or (None if row_org_id is not None else org_token)
            summary_by_key[key] = MerchantReconciliationSummaryBuilder.empty_summary_row(
                org_id=row_org_id,
                org_name=org_name or None,
                accounting_year=accounting_year,
                accounting_month=accounting_month,
                our_subject=our_subject,
                receipt_subject=receipt_merchant,
                adjustment=adjustment,
            )
        for key, totals in detail_totals.items():
            org_token, our_subject, receipt_merchant = key
            row_org_id = MerchantReconciliationSummaryBuilder.optional_int(
                totals.get("org_id")
            ) or MerchantReconciliationSummaryBuilder.optional_int(org_token)
            org_name = safe_str(totals.get("org_name")) or (None if row_org_id is not None else org_token)
            adjustment = payment_adjustments.get(key, {})
            item = summary_by_key.setdefault(
                key,
                MerchantReconciliationSummaryBuilder.empty_summary_row(
                    org_id=row_org_id,
                    org_name=org_name or None,
                    accounting_year=accounting_year,
                    accounting_month=accounting_month,
                    our_subject=our_subject,
                    receipt_subject=receipt_merchant,
                    adjustment=adjustment,
                ),
            )
            merchant_payable = safe_decimal(totals.get("merchant_payable_net_amount"))
            if item.get("org_id") is None and row_org_id is not None:
                item["org_id"] = row_org_id
                item["key"] = f"{row_org_id}|{our_subject}|{receipt_merchant}"
            if not item.get("org_name") and org_name:
                item["org_name"] = org_name
            item["gmv"] = safe_decimal(item["gmv"]) + safe_decimal(totals.get("gmv"))
            item["merchant_payable_net_amount"] = safe_decimal(item["merchant_payable_net_amount"]) + merchant_payable
            item["row_count"] = int(item["row_count"]) + int(totals.get("row_count") or 0)
            MerchantReconciliationSummaryBuilder.refresh_summary_flow_amounts(item)

        return MerchantReconciliationSummaryBuilder.sort_summary_rows(list(summary_by_key.values()))

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
    def filter_summary_rows_by_bank_status(
        rows: list[dict[str, object]],
        *,
        bank_status: str | None,
    ) -> list[dict[str, object]]:
        if not bank_status:
            return rows
        return [row for row in rows if row.get("bank_status") == bank_status]

    @staticmethod
    def sort_summary_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
        return sorted(
            rows,
            key=lambda item: (
                str(item.get("org_name") or ""),
                str(item.get("our_subject") or ""),
                str(item.get("merchant_receipt_subject") or item.get("receipt_merchant") or ""),
            ),
        )

    @staticmethod
    def opening_balance_key(*, org_id: int, our_subject: object, receipt_merchant: object) -> tuple[int, str, str]:
        return (
            int(org_id),
            _entity_match_text(our_subject),
            _entity_match_text(receipt_merchant),
        )

    @staticmethod
    def merge_opening_balance_rows(
        summary_rows: list[dict[str, object]],
        opening_balance_rows: list[tuple[MerchantOpeningBalance, str | None]],
        *,
        accounting_year: int,
        accounting_month: int,
        append_missing: bool,
    ) -> None:
        balance_by_key = {
            MerchantReconciliationSummaryBuilder.opening_balance_key(
                org_id=balance.org_id,
                our_subject=balance.our_subject,
                receipt_merchant=balance.receipt_merchant,
            ): (balance, org_name)
            for balance, org_name in opening_balance_rows
        }
        used_keys: set[tuple[int, str, str]] = set()
        for row in summary_rows:
            row_org_id = MerchantReconciliationSummaryBuilder.optional_int(row.get("org_id"))
            if row_org_id is None:
                continue
            key = MerchantReconciliationSummaryBuilder.opening_balance_key(
                org_id=row_org_id,
                our_subject=row.get("our_subject"),
                receipt_merchant=row.get("merchant_receipt_subject") or row.get("receipt_merchant"),
            )
            balance_pair = balance_by_key.get(key)
            if balance_pair is None:
                continue
            balance, _org_name = balance_pair
            row["opening_balance"] = safe_decimal(balance.opening_balance)
            MerchantReconciliationSummaryBuilder.refresh_summary_flow_amounts(row)
            used_keys.add(key)

        if not append_missing:
            return
        for balance, org_name in opening_balance_rows:
            key = MerchantReconciliationSummaryBuilder.opening_balance_key(
                org_id=balance.org_id,
                our_subject=balance.our_subject,
                receipt_merchant=balance.receipt_merchant,
            )
            if key in used_keys:
                continue
            row = MerchantReconciliationSummaryBuilder.empty_summary_row(
                org_id=int(balance.org_id),
                org_name=org_name,
                accounting_year=accounting_year,
                accounting_month=accounting_month,
                our_subject=balance.our_subject,
                receipt_subject=balance.receipt_merchant,
            )
            row["opening_balance"] = safe_decimal(balance.opening_balance)
            MerchantReconciliationSummaryBuilder.refresh_summary_flow_amounts(row)
            summary_rows.append(row)

    @staticmethod
    def merge_bank_flow_totals(
        summary_rows: list[dict[str, object]],
        bank_flow_totals: dict[tuple[str, str, str], Decimal],
    ) -> None:
        for row in summary_rows:
            row_org_id = MerchantReconciliationSummaryBuilder.optional_int(row.get("org_id"))
            org_token = str(row_org_id) if row_org_id is not None else _normalize_text(row.get("org_name"))
            # 银行流水优先在服务层桥接红单付款；这里仅按最终汇总主体键合并金额。
            key = (
                org_token,
                _entity_match_text(row.get("our_subject")),
                _entity_match_text(row.get("merchant_receipt_subject") or row.get("receipt_merchant")),
            )
            row["bank_flow_amount"] = bank_flow_totals.get(key, ZERO_MONEY)
            MerchantReconciliationSummaryBuilder.refresh_summary_flow_amounts(row)

    @staticmethod
    def add_payment_adjustment(
        adjustments: dict[tuple[str, str, str], dict[str, Decimal]],
        key: tuple[str, str, str],
        *,
        business_fee_deduction: Decimal,
        other_deduction_amount: Decimal,
        payable_goods_balance: Decimal,
        paid_flow_amount: Decimal = ZERO_MONEY,
    ) -> None:
        item = adjustments.setdefault(
            key,
            {
                "business_fee_deduction": ZERO_MONEY,
                "other_deduction_amount": ZERO_MONEY,
                "payable_goods_balance": ZERO_MONEY,
                "paid_flow_amount": ZERO_MONEY,
            },
        )
        item["business_fee_deduction"] += business_fee_deduction
        item["other_deduction_amount"] += other_deduction_amount
        item["payable_goods_balance"] += payable_goods_balance
        item["paid_flow_amount"] += paid_flow_amount

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

        # 最后一组吃掉四舍五入尾差，确保分摊后金额总和与原始金额完全一致。
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
