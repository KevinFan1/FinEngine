"""商家对账明细匹配工具。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP

from app.models.douyin_dongzhang_detail import DouyinDongzhangDetail
from app.models.merchant_reconciliation import MerchantRedSheetPayment, MerchantRedSheetPurchase
from app.schemas.merchant_reconciliation import MerchantReconciliationStatsOut
from app.tasks.processors.base import safe_str
from app.utils.money import ZERO_MONEY, safe_decimal
from app.utils.product_code import extract_product_code

MONEY_QUANT = Decimal("0.01")


@dataclass(frozen=True)
class RedSheetContext:
    purchases_by_code: dict[str, MerchantRedSheetPurchase]
    payments_by_key: dict[tuple[str, str, str], MerchantRedSheetPayment]


@dataclass(frozen=True)
class ReconciliationLoadContext:
    org_id: int
    total_gmv: Decimal
    total_bic: Decimal
    total_insurance: Decimal
    red_sheet_context: RedSheetContext
    net_rate: Decimal = Decimal("0.700000")


@dataclass(frozen=True)
class MerchantDerivedFields:
    product_code: str
    major_merchant_name: str
    our_subject: str
    merchant_receipt_subject: str
    receipt_merchant: str
    live_room: str
    live_date: str
    live_date_text: str
    red_sheet_payment_id: int | None
    allocated_bic: Decimal
    allocated_insurance_fee: Decimal
    live_amount: Decimal
    match_status: str
    match_error: str


def _normalize_text(value: object) -> str:
    return safe_str(value).strip()


def _match_text(value: object) -> str:
    return _normalize_text(value).replace("（", "(").replace("）", ")").replace(" ", "").replace("　", "").upper()


def _date_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return _normalize_text(value)


def _allocation_amount(row_gmv: Decimal, total_gmv: Decimal, total_amount: Decimal) -> Decimal:
    if total_gmv == ZERO_MONEY or total_amount == ZERO_MONEY:
        return ZERO_MONEY
    return (row_gmv * total_amount / total_gmv).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)


class MerchantReconciliationMatcher:
    """动账明细到红单采购/货款的匹配边界。"""

    @staticmethod
    def split_product_codes(value: object) -> list[str]:
        codes: list[str] = []
        normalized = safe_str(value).replace("，", ",").replace("＋", ",").replace("+", ",")
        for part in normalized.split(","):
            part = part.strip().upper()
            if part:
                codes.append(part)
        return codes

    @staticmethod
    def build_detail_derived_fields(
        detail: DouyinDongzhangDetail,
        *,
        load_context: ReconciliationLoadContext,
        live_date_key_getter,
    ) -> MerchantDerivedFields:
        product_code = detail.product_code or extract_product_code(detail.product_name)
        product_codes = MerchantReconciliationMatcher.split_product_codes(product_code)
        purchase = next(
            (
                load_context.red_sheet_context.purchases_by_code.get(code)
                for code in product_codes
                if load_context.red_sheet_context.purchases_by_code.get(code)
            ),
            None,
        )
        payment = None
        errors: list[str] = []
        if not product_code:
            errors.append("商品名称未提取到商品编码")
        if purchase is None:
            errors.append("未匹配到红单采购")
        else:
            # 匹配失败是业务结果，前端需要展示原因，不能在这里抛系统异常。
            payment = load_context.red_sheet_context.payments_by_key.get(
                (_match_text(purchase.merchant), live_date_key_getter(purchase.live_date), _match_text(purchase.live_room))
            )
            if payment is None:
                errors.append("未匹配到红单货款")

        gmv = safe_decimal(detail.gmv)
        live_date = purchase.live_date if purchase is not None else ""
        return MerchantDerivedFields(
            product_code=product_code,
            major_merchant_name=purchase.merchant if purchase is not None else "",
            our_subject=payment.settlement_subject if payment is not None else "",
            merchant_receipt_subject=payment.receipt_subject if payment is not None else "",
            receipt_merchant=payment.receipt_merchant if payment is not None else "",
            live_room=purchase.live_room if purchase is not None else "",
            live_date=live_date,
            live_date_text=live_date_key_getter(live_date),
            red_sheet_payment_id=int(payment.id) if payment is not None and payment.id is not None else None,
            allocated_bic=_allocation_amount(gmv, load_context.total_gmv, load_context.total_bic),
            allocated_insurance_fee=_allocation_amount(gmv, load_context.total_gmv, load_context.total_insurance),
            live_amount=(gmv * safe_decimal(load_context.net_rate)).quantize(MONEY_QUANT, rounding=ROUND_HALF_UP),
            match_status="matched" if not errors else "unmatched",
            match_error="；".join(errors),
        )

    @staticmethod
    def build_detail_payload(
        detail: DouyinDongzhangDetail,
        *,
        org_name: str | None,
        shop_color: str | None,
        load_context: ReconciliationLoadContext,
        period_getter,
        datetime_formatter,
        live_date_key_getter,
    ) -> dict[str, object]:
        derived = MerchantReconciliationMatcher.build_detail_derived_fields(
            detail,
            load_context=load_context,
            live_date_key_getter=live_date_key_getter,
        )
        gmv = safe_decimal(detail.gmv)
        return {
            "id": detail.id,
            "org_id": detail.org_id,
            "org_name": org_name,
            "shop_id": detail.shop_id,
            "shop_name": detail.shop_name,
            "shop_color": shop_color,
            "accounting_year": detail.summary_year,
            "accounting_month": detail.summary_month,
            "accounting_period": period_getter(detail.summary_year, detail.summary_month),
            "accounting_date": f"{int(detail.summary_year):04d}-{int(detail.summary_month):02d}",
            "platform_code": detail.source_platform_code,
            "platform_label": "抖音",
            "source_row_number": detail.source_row_number,
            "transaction_time": datetime_formatter(detail.transaction_time),
            "transaction_flow_no": detail.transaction_flow_no,
            "transaction_direction": detail.transaction_direction,
            "transaction_amount": safe_decimal(detail.transaction_amount),
            "transaction_scene": detail.transaction_scene,
            "sub_order_no": detail.sub_order_no,
            "order_no": detail.order_no,
            "order_time": datetime_formatter(detail.order_time),
            "product_id": detail.product_id,
            "product_code": derived.product_code,
            "product_name": detail.product_name,
            "author_name": detail.author_name,
            "merchant_name": getattr(detail, "merchant_name", ""),
            "gmv": gmv,
            "allocated_bic": derived.allocated_bic,
            "allocated_insurance_fee": derived.allocated_insurance_fee,
            "live_amount": derived.live_amount,
            "major_merchant_name": derived.major_merchant_name,
            "our_subject": derived.our_subject,
            "merchant_receipt_subject": derived.merchant_receipt_subject,
            "receipt_merchant": derived.receipt_merchant,
            "red_sheet_payment_id": derived.red_sheet_payment_id,
            "live_room": derived.live_room,
            "live_date": derived.live_date,
            "live_date_text": derived.live_date_text,
            "match_status": derived.match_status,
            "match_error": derived.match_error,
        }

    @staticmethod
    def build_stats(
        rows: list[dict[str, object]],
        *,
        total_bic: Decimal,
        total_insurance: Decimal,
    ) -> MerchantReconciliationStatsOut:
        matched_rows = sum(1 for row in rows if row.get("match_status") == "matched")
        total_gmv = sum((safe_decimal(row.get("gmv")) for row in rows), ZERO_MONEY)
        total_allocated_bic = sum((safe_decimal(row.get("allocated_bic")) for row in rows), ZERO_MONEY)
        total_allocated_insurance = sum((safe_decimal(row.get("allocated_insurance_fee")) for row in rows), ZERO_MONEY)
        total_live_amount = sum((safe_decimal(row.get("live_amount")) for row in rows), ZERO_MONEY)
        return MerchantReconciliationStatsOut(
            total_gmv=total_gmv,
            total_bic=total_bic,
            total_allocated_bic=total_allocated_bic,
            total_insurance_fee=total_insurance,
            total_allocated_insurance_fee=total_allocated_insurance,
            total_live_amount=total_live_amount,
            matched_rows=matched_rows,
            unmatched_rows=len(rows) - matched_rows,
        )
