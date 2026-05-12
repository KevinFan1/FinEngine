"""抖音 (Douyin) hardcoded processors for 动账/BIC/运费险 Excel/CSV files."""

from decimal import Decimal

from app.tasks.processors.base import (
    FinancialSummaryExcelProcessorMixin,
    FinancialSummaryStrategy,
    SimpleMonthlySumProcessorMixin,
    canonical_remark,
    parse_datetime,
    safe_str,
)
from app.utils.money import ZERO_MONEY, safe_decimal

# ── Douyin 动账 expected headers ─────────────────────────────────────────────
DOUYIN_DONGZHANG_HEADERS: list[str] = [
    "动账时间",
    "动帐流水号",
    "动账方向",
    "动账金额",
    "动账账户",
    "动账场景",
    "计费类型",
    "子订单号",
    "订单号",
    "售后编号",
    "下单时间",
    "商品ID",
    "商品名称",
    "达人ID",
    "达人名称",
    "订单类型",
    "订单实付应结",
    "运费实付",
    "实际平台补贴_运费",
    "实际平台补贴",
    "其他平台补贴",
    "以旧换新抵扣",
    "政府补贴平台垫资",
    "实际达人补贴",
    "实际抖音支付补贴",
    "实际抖音月付营销补贴",
    "银行补贴",
    "订单退款",
    "平台服务费",
    "佣金",
    "服务商佣金",
    "渠道分成",
    "招商服务费",
    "站外推广费",
    "其他分成",
    "是否免佣",
    "免佣金额",
    "备注",
]

DOUYIN_BIC_HEADERS: list[str] = [
    "结算单号",
    "订单码",
    "关联订单号",
    "关联运单号",
    "费用项",
    "服务商",
    "QIC仓",
    "结算金额",
    "计费参数",
    "计费完成时间",
    "业务节点",
    "业务发生时间",
    "结算时间",
    "状态",
    "动账账户",
    "动账流水号",
    "备注",
    "是否木带宝",
    "是否子单",
]

DOUYIN_SHIPPING_INSURANCE_HEADERS: list[str] = [
    "投保单号",
    "订单编号",
    "下单时间",
    "承保时间",
    "保险名称",
    "承保保司",
    "保费来源",
    "支付保费",
    "保费状态",
    "动账时间",
    "动账流水号",
    "保险交易单号",
    "平台优惠【营销补贴】",
    "保障额度",
    "保障状态",
    "备注",
    "平台优惠【特殊活动】",
    "平台优惠",
]


class DouyinDongzhangStrategy(FinancialSummaryStrategy):
    """Douyin 动账 formulas."""

    fields: tuple[str, ...] = (
        "gmv",
        "platform_income",
        "platform_fee",
        "return_cost",
        "commission",
        "merchant_fee",
        "promotion_fee",
        "provider_commission",
    )

    @property
    def required_headers(self) -> tuple[str, ...]:
        return (
            "下单时间",
            "动账时间",
            "备注",
            "动账金额",
            "订单实付应结",
            "订单退款",
            "实际平台补贴",
            "实际抖音支付补贴",
            "实际抖音月付营销补贴",
            "平台服务费",
            "佣金",
            "招商服务费",
            "站外推广费",
            "服务商佣金",
        )

    def compute_year_month(self, vals: dict[str, object]) -> tuple[int, int] | None:
        """Compute 调年月 from 下单时间 (preferred) or 动账时间 (fallback)."""
        order_time = parse_datetime(vals.get("下单时间"))
        if order_time is not None:
            return (order_time.year, order_time.month)

        action_time = parse_datetime(vals.get("动账时间"))
        if action_time is not None:
            year, month = action_time.year, action_time.month
            month -= 1
            if month <= 0:
                year -= 1
                month = 12
            return (year, month)

        return None

    def compute_values(
        self,
        vals: dict[str, object],
        category_dict: dict[str, list[str]] | None = None,
    ) -> dict[str, Decimal]:
        beizhu = canonical_remark(safe_str(vals.get("备注")))

        matched_compensation = self._match_compensation(beizhu, category_dict)

        refund_to_compensation = ZERO_MONEY
        if "退款转赔付" in beizhu:
            refund_to_compensation = safe_decimal(vals.get("动账金额"))

        cashback = ZERO_MONEY
        if "返现" in beizhu:
            cashback = safe_decimal(vals.get("订单实付应结"))

        order_paid = safe_decimal(vals.get("订单实付应结"))
        order_refund = safe_decimal(vals.get("订单退款"))
        gmv = order_paid + order_refund - refund_to_compensation - cashback

        platform_income = safe_decimal(vals.get("实际平台补贴")) + safe_decimal(vals.get("实际抖音支付补贴")) + safe_decimal(vals.get("实际抖音月付营销补贴"))

        return {
            "gmv": gmv,
            "platform_income": platform_income,
            "platform_fee": -safe_decimal(vals.get("平台服务费")),
            "return_cost": safe_decimal(vals.get("动账金额")) if matched_compensation else ZERO_MONEY,
            "commission": safe_decimal(vals.get("佣金")),
            "merchant_fee": safe_decimal(vals.get("招商服务费")),
            "promotion_fee": safe_decimal(vals.get("站外推广费")),
            "provider_commission": safe_decimal(vals.get("服务商佣金")),
        }

    @staticmethod
    def _match_compensation(
        beizhu: str,
        category_dict: dict[str, list[str]] | None,
    ) -> str | None:
        if not category_dict or not beizhu:
            return None

        for category_name, keywords in category_dict.items():
            if beizhu in keywords:
                return category_name
        return None


class DouyinProcessor(FinancialSummaryExcelProcessorMixin, SimpleMonthlySumProcessorMixin):
    """Hardcoded processor for Douyin 动账/BIC/运费险 Excel/CSV files."""

    summary_strategy = DouyinDongzhangStrategy()

    @property
    def platform_label(self) -> str:
        return "抖音"

    def get_type_processor(self, type_code: str):
        if type_code == "bic":
            return self._process_bic
        if type_code == "运费险":
            return self._process_shipping_insurance
        return super().get_type_processor(type_code)

    def _process_bic(
        self,
        *,
        file_path: str,
        shop_name: str,
        category_dict: dict[str, list[str]] | None = None,
    ) -> dict:
        _ = category_dict
        return self._process_simple_monthly_sum(
            file_path=file_path,
            shop_name=shop_name,
            date_header="业务发生时间",
            amount_header="结算金额",
            output_key="bic",
        )

    def _process_shipping_insurance(
        self,
        *,
        file_path: str,
        shop_name: str,
        category_dict: dict[str, list[str]] | None = None,
    ) -> dict:
        _ = category_dict
        return self._process_simple_monthly_sum(
            file_path=file_path,
            shop_name=shop_name,
            date_header="下单时间",
            amount_header="支付保费",
            output_key="insurance_fee",
        )


# ── Module-level singleton ────────────────────────────────────────────────────
douyin_processor = DouyinProcessor()
