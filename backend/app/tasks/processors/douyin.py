"""抖音 (Douyin) hardcoded processors for 动账/BIC/运费险 Excel/CSV files."""

from decimal import Decimal

from app.tasks.processors.base import (
    FinancialSummaryExcelProcessorMixin,
    FinancialSummaryStrategy,
    SimpleMonthlySumProcessorMixin,
    canonical_remark,
    normalize_positive_summary_fields,
    open_tabular_rows,
    parse_datetime,
    safe_str,
)
from app.utils.money import ZERO_MONEY, safe_decimal
from app.utils.product_code import extract_product_code
from app.utils.text_classifier import classify_text

DOUYIN_DONGZHANG_DETAIL_FIELD_MAP: tuple[tuple[str, str], ...] = (
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
)

DOUYIN_DONGZHANG_DECIMAL_FIELDS: frozenset[str] = frozenset(
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
    }
)

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
    "商户主体名称",
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

DOUYIN_ORDER_HEADERS: list[str] = [
    "主订单编号",
    "子订单编号",
    "选购商品",
    "商品规格",
    "商品数量",
    "商品ID",
    "商家编码",
    "商品单价",
    "订单应付金额",
    "运费",
    "优惠总金额",
    "平台优惠",
    "商家优惠",
    "达人优惠",
    "商家改价",
    "支付优惠",
    "红包抵扣",
    "支付方式",
    "手续费",
    "收件人",
    "收件人手机号",
    "省",
    "市",
    "区",
    "街道",
    "详细地址",
    "是否修改过地址",
    "地址修改时段",
    "买家留言",
    "订单提交时间",
    "旗帜颜色",
    "商家备注",
    "订单完成时间",
    "支付完成时间",
    "APP渠道",
    "流量来源",
    "订单状态",
    "承诺发货时间",
    "订单类型",
    "鲁班落地页ID",
    "达人ID",
    "达人昵称",
    "所属门店ID",
    "售后状态",
    "取消原因",
    "预约发货时间",
    "仓库ID",
    "仓库名称",
    "序列号",
    "是否安心购",
    "广告渠道",
    "流量类型",
    "流量体裁",
    "流量渠道",
    "发货主体",
    "发货主体明细",
    "发货时间",
    "降价类优惠",
    "平台实际承担优惠金额",
    "商家实际承担优惠金额",
    "达人实际承担优惠金额",
    "预计送达时间",
    "是否平台仓自流转",
    "车型",
    "商品69码",
    "发货SN码",
    "发货IMEI码1",
    "发货IMEI码2",
    "预约送达时间",
    "建议发货时间（起）",
    "建议发货时间（止）",
    "物流SN码",
    "物流IMEI码1",
    "物流IMEI码2",
]


class DouyinDongzhangStrategy(FinancialSummaryStrategy):
    """Douyin 动账 formulas."""

    fields: tuple[str, ...] = (
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
    )

    @property
    def required_headers(self) -> tuple[str, ...]:
        return (
            "下单时间",
            "动账时间",
            "动账方向",
            "动账场景",
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
        period = self.compute_summary_period(vals)
        if period is None:
            return None
        return period[0], period[1]

    def compute_summary_period(self, vals: dict[str, object]) -> tuple[int, int, str] | None:
        """Compute 调年月 from 下单时间 (preferred) or 动账时间 (fallback)."""
        order_time = parse_datetime(vals.get("下单时间"))
        if order_time is not None:
            return (order_time.year, order_time.month, "order_time")

        action_time = parse_datetime(vals.get("动账时间"))
        if action_time is not None:
            year, month = action_time.year, action_time.month
            month -= 1
            if month <= 0:
                year -= 1
                month = 12
            return (year, month, "transaction_time_previous_month")

        return None

    def compute_values(
        self,
        vals: dict[str, object],
        category_dict: dict[str, list[str]] | None = None,
    ) -> dict[str, Decimal]:
        detail_logic = self._compute_detail_logic(vals, category_dict)

        order_paid = safe_decimal(vals.get("订单实付应结"))
        order_refund = safe_decimal(vals.get("订单退款"))
        order_paid_amount = order_paid - detail_logic["cashback"]
        refund_amount = detail_logic["refund_to_compensation"] - order_refund
        gmv = order_paid_amount - refund_amount

        platform_income = safe_decimal(vals.get("实际平台补贴")) + safe_decimal(vals.get("实际抖音支付补贴")) + safe_decimal(vals.get("实际抖音月付营销补贴"))

        return {
            "order_paid_amount": order_paid_amount,
            "refund_amount": refund_amount,
            "gmv": gmv,
            "platform_income": platform_income,
            "platform_fee": -safe_decimal(vals.get("平台服务费")),
            "return_cost": detail_logic["return_cost"],
            "commission": safe_decimal(vals.get("佣金")),
            "merchant_fee": safe_decimal(vals.get("招商服务费")),
            "promotion_fee": safe_decimal(vals.get("站外推广费")),
            "provider_commission": safe_decimal(vals.get("服务商佣金")),
        }

    def finalize_agg(self, agg: dict[str, Decimal]) -> dict[str, Decimal]:
        return normalize_positive_summary_fields(agg)

    @staticmethod
    def _match_compensation(
        beizhu: str,
        category_dict: dict[str, list[str]] | None,
    ) -> str | None:
        if not category_dict or not beizhu:
            return None

        return classify_text(beizhu, category_dict).category

    def build_detail_row(
        self,
        vals: dict[str, object],
        *,
        row_values: dict[str, Decimal],
        source_row_number: int,
        category_dict: dict[str, list[str]] | None = None,
    ) -> dict[str, object] | None:
        period = self.compute_summary_period(vals)
        if period is None:
            return None

        detail_logic = self._compute_detail_logic(vals, category_dict)
        detail_row: dict[str, object] = {
            "source_row_number": source_row_number,
            "summary_year": period[0],
            "summary_month": period[1],
            "period_source": period[2],
            "matched_compensation": detail_logic["matched_compensation"],
            "refund_to_compensation": detail_logic["refund_to_compensation"],
            "cashback": detail_logic["cashback"],
            "order_paid": row_values["order_paid_amount"],
            "refund_amount": row_values["refund_amount"],
            "gmv": row_values["gmv"],
            "platform_income": row_values["platform_income"],
            "platform_fee_positive": row_values["platform_fee"],
            "return_cost": row_values["return_cost"],
            "commission_derived": row_values["commission"],
            "bic": ZERO_MONEY,
            "insurance_fee": ZERO_MONEY,
        }

        for field_name, header in DOUYIN_DONGZHANG_DETAIL_FIELD_MAP:
            raw_value = vals.get(header)
            if field_name in DOUYIN_DONGZHANG_DECIMAL_FIELDS:
                detail_row[field_name] = safe_decimal(raw_value)
            else:
                detail_row[field_name] = safe_str(raw_value)
        detail_row["product_code"] = extract_product_code(detail_row.get("product_name"))
        return detail_row

    def _compute_detail_logic(
        self,
        vals: dict[str, object],
        category_dict: dict[str, list[str]] | None = None,
    ) -> dict[str, Decimal | str]:
        beizhu = canonical_remark(safe_str(vals.get("备注")))
        matched_compensation = self._match_compensation(beizhu, category_dict) or ""

        refund_to_compensation = ZERO_MONEY
        if "退款转赔付" in beizhu:
            refund_to_compensation = safe_decimal(vals.get("动账金额"))

        cashback = ZERO_MONEY
        if "返现" in beizhu and safe_str(vals.get("动账方向")) == "入账":
            cashback = safe_decimal(vals.get("动账金额"))

        return_cost = safe_decimal(vals.get("动账金额")) if matched_compensation else ZERO_MONEY

        return {
            "matched_compensation": matched_compensation,
            "refund_to_compensation": refund_to_compensation,
            "cashback": cashback,
            "return_cost": return_cost,
        }


class DouyinProcessor(FinancialSummaryExcelProcessorMixin, SimpleMonthlySumProcessorMixin):
    """Hardcoded processor for Douyin 动账/BIC/运费险 Excel/CSV files."""

    summary_strategy = DouyinDongzhangStrategy()

    @property
    def platform_label(self) -> str:
        return "抖音"

    def get_type_processor(self, type_code: str):
        if type_code == "订单":
            return self._process_order
        if type_code == "bic":
            return self._process_bic
        if type_code == "运费险":
            return self._process_shipping_insurance
        return super().get_type_processor(type_code)

    def _process_order(
        self,
        *,
        file_path: str,
        shop_name: str,
        category_dict: dict[str, list[str]] | None = None,
    ) -> dict:
        _ = shop_name, category_dict
        result = {
            "total_rows": 0,
            "success_rows": 0,
            "failed_rows": 0,
            "errors": [],
            "groups": {},
            "orders": [],
        }
        required_headers = ("子订单编号", "订单提交时间")
        expected_headers = (*required_headers, "主订单编号")

        with open_tabular_rows(file_path) as rows:
            if rows is None:
                result["errors"].append("无法打开表格文件")
                return result

            row_iter = iter(rows)
            header_result = self._find_header_row(row_iter, required_headers)
            if header_result is None:
                result["errors"].append("无法读取表头")
                self._log_header_compare(
                    file_path=file_path,
                    type_code="订单",
                    actual_headers=[],
                    required_headers=required_headers,
                    missing_headers=required_headers,
                    header_row_number=None,
                )
                return result

            headers, header_row_number = header_result
            col_idx = self._build_col_idx(headers, expected_headers)
            missing = self._missing_headers(col_idx, required_headers)
            if missing:
                result["errors"].append(f"缺少必要表头: {', '.join(missing)}")
                self._log_header_compare(
                    file_path=file_path,
                    type_code="订单",
                    actual_headers=headers,
                    required_headers=required_headers,
                    missing_headers=missing,
                    header_row_number=header_row_number,
                )
                return result

            for row in row_iter:
                result["total_rows"] += 1
                try:
                    vals = self._row_to_values(row, col_idx)
                    order_no = safe_str(vals.get("子订单编号"))
                    order_created_at = parse_datetime(vals.get("订单提交时间"))
                    if not order_no:
                        result["failed_rows"] += 1
                        result["errors"].append(f"Row {result['total_rows'] + header_row_number}: 子订单编号为空")
                        continue
                    if order_created_at is None:
                        result["failed_rows"] += 1
                        result["errors"].append(f"Row {result['total_rows'] + header_row_number}: 无法解析订单提交时间")
                        continue

                    order_item: dict[str, object] = {
                        "order_no": order_no,
                        "order_created_at": order_created_at,
                    }
                    parent_order_no = safe_str(vals.get("主订单编号"))
                    if parent_order_no:
                        order_item["extra_data"] = {"主订单编号": parent_order_no}

                    result["orders"].append(order_item)
                    result["success_rows"] += 1
                except Exception as e:
                    result["failed_rows"] += 1
                    result["errors"].append(f"Row {result['total_rows'] + header_row_number}: {e}")

        return result

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
