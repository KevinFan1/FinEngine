"""快手 (Kuaishou) hardcoded processors for GMV/动账/运费险/订单 Excel/CSV files."""

from decimal import Decimal

from app.tasks.processors.base import (
    FinancialSummaryExcelProcessorMixin,
    FinancialSummaryStrategy,
    SimpleMonthlySumProcessorMixin,
    canonical_remark,
    open_tabular_rows,
    parse_datetime,
    safe_str,
)
from app.utils.money import ZERO_MONEY, safe_decimal
from app.utils.text_classifier import classify_text

# ── Kuaishou GMV expected headers ─────────────────────────────────────────────
KUAISHOU_GMV_HEADERS: list[str] = [
    "商家ID",
    "订单号",
    "商品ID",
    "商品名称",
    "商品数量",
    "订单创建时间",
    "订单实付(元)",
    "政府补贴",
    "支付营销补贴",
    "平台补贴",
    "商家补贴(元)",
    "达人补贴",
    "达人补贴明细",
    "合计收入(元)",
    "订单退款(元)",
    "支付营销回退（元）",
    "技术服务费(元)",
    "预售增收技术服务费（元）",
    "达人ID",
    "MCN机构ID",
    "达人佣金(元)",
    "团长id",
    "团长佣金(元)",
    "佣金模式",
    "快赚客ID",
    "快赚客佣金(元)",
    "服务商ID",
    "服务商佣金(元)",
    "分账基数",
    "其他收费",
    "其他收费明细",
    "合计支出(元)",
    "实际结算金额(元)",
    "实际结算时间",
    "结算规则",
    "资金渠道",
    "账户名称",
    "结算商户号",
    "备注",
    "消费金信息",
]

# ── Kuaishou 动账 expected headers ────────────────────────────────────────────
KUAISHOU_DONGZHANG_HEADERS: list[str] = [
    "账务流水号",
    "关联业务单号",
    "入账时间",
    "账务方向",
    "发生额（元）",
    "期末余额（元）",
    "业务类型",
    "描述",
    "备注",
]

# ── Kuaishou 运费险 expected headers ──────────────────────────────────────────
KUAISHOU_SHIPPING_INSURANCE_HEADERS: list[str] = [
    "订单编号",
    "服务费用（元）",
    "商家承担服务费用（元）",
    "平台补贴费用（元）",
    "生效时间",
    "收费编号",
]

# ── Kuaishou 订单 expected headers ────────────────────────────────────────────
KUAISHOU_ORDER_HEADERS: list[str] = [
    "订单号",
    "赠品订单号",
    "活动订单编号",
    "订单创建时间",
    "订单支付时间",
    "预售定金支付时间",
    "订单状态",
    "实付款",
    "快递费",
    "店铺优惠",
    "平台补贴",
    "主播补贴",
    "混资活动优惠",
    "支付优惠",
    "支付方式",
    "成交数量",
    "买家留言",
    "账号类型",
    "账号明细",
    "订单备注",
    "旗帜颜色",
    "售后状态",
    "活动订单",
    "预售/承诺发货时间",
    "订单载体",
    "商品名称",
    "商品ID",
    "商品规格",
    "SKU编码",
    "商品单价",
    "渠道",
    "CPS达人ID",
    "CPS达人昵称",
    "预估推广佣金",
    "预估推广者分佣比例",
    "团长ID",
    "团长昵称",
    "快赚客ID",
    "快赚客昵称",
    "授权推广者ID",
    "授权推广者昵称",
    "收货人姓名",
    "收货人电话",
    "收货地址-省",
    "收货地址-市",
    "收货地址-区",
    "收货地址-街道",
    "收货地址",
    "发货时间",
    "快递公司",
    "快递单号",
    "物流信息",
    "集运类型",
    "直邮类型",
    "仓库名称",
    "仓库地址",
    "实名姓名",
    "服务门店ID",
    "服务门店名称",
    "服务门店地址",
    "国补/类国补/消费券",
]


class KuaishouGmvStrategy(FinancialSummaryStrategy):
    """Kuaishou GMV formulas."""

    @property
    def required_headers(self) -> tuple[str, ...]:
        return (
            "订单创建时间",
            "订单实付(元)",
            "政府补贴",
            "支付营销补贴",
            "平台补贴",
            "商家补贴(元)",
            "达人补贴",
            "订单退款(元)",
            "支付营销回退（元）",
            "技术服务费(元)",
            "达人佣金(元)",
            "团长佣金(元)",
            "其他收费",
        )

    def compute_year_month(self, vals: dict[str, object]) -> tuple[int, int] | None:
        """Prefer order creation time; fallback to actual settlement time."""
        order_time = parse_datetime(vals.get("订单创建时间"))
        if order_time is not None:
            return (order_time.year, order_time.month)

        settlement_time = parse_datetime(vals.get("实际结算时间"))
        if settlement_time is not None:
            return (settlement_time.year, settlement_time.month)

        return None

    def compute_values(
        self,
        vals: dict[str, object],
        category_dict: dict[str, list[str]] | None = None,
    ) -> dict[str, Decimal]:
        _ = category_dict
        return {
            "gmv": self._compute_gmv(vals),
            "platform_income": self._compute_platform_income(vals),
            "platform_fee": self._compute_platform_fee(vals),
            "return_cost": self._compute_return_cost(vals),
            "commission": self._compute_commission(vals),
            "merchant_fee": self._compute_merchant_fee(vals),
            "promotion_fee": self._compute_promotion_fee(vals),
            "provider_commission": self._compute_provider_commission(vals),
            "donation_fee": self._compute_donation_fee(vals),
        }

    @staticmethod
    def _compute_gmv(vals: dict[str, object]) -> Decimal:
        return safe_decimal(vals.get("订单实付(元)")) - safe_decimal(vals.get("订单退款(元)"))

    @staticmethod
    def _compute_platform_income(vals: dict[str, object]) -> Decimal:
        return (
            safe_decimal(vals.get("政府补贴"))
            + safe_decimal(vals.get("支付营销补贴"))
            + safe_decimal(vals.get("平台补贴"))
            + safe_decimal(vals.get("商家补贴(元)"))
            + safe_decimal(vals.get("达人补贴"))
        )

    @staticmethod
    def _compute_platform_fee(vals: dict[str, object]) -> Decimal:
        return safe_decimal(vals.get("技术服务费(元)")) + safe_decimal(vals.get("其他收费")) - safe_decimal(vals.get("支付营销回退（元）"))

    @staticmethod
    def _compute_return_cost(vals: dict[str, object]) -> Decimal:
        """Reserved for future Kuaishou return-cost classification."""
        _ = vals
        return ZERO_MONEY

    @staticmethod
    def _compute_commission(vals: dict[str, object]) -> Decimal:
        return safe_decimal(vals.get("达人佣金(元)")) + safe_decimal(vals.get("团长佣金(元)"))

    @staticmethod
    def _compute_merchant_fee(vals: dict[str, object]) -> Decimal:
        _ = vals
        return ZERO_MONEY

    @staticmethod
    def _compute_promotion_fee(vals: dict[str, object]) -> Decimal:
        _ = vals
        return ZERO_MONEY

    @staticmethod
    def _compute_provider_commission(vals: dict[str, object]) -> Decimal:
        _ = vals
        return ZERO_MONEY

    @staticmethod
    def _compute_donation_fee(vals: dict[str, object]) -> Decimal:
        _ = vals
        return ZERO_MONEY

    @staticmethod
    def _compute_insurance_fee(vals: dict[str, object]) -> Decimal:
        """Reserved for future Kuaishou shipping-insurance order logic."""
        _ = vals
        return ZERO_MONEY

    @staticmethod
    def _compute_bic(vals: dict[str, object]) -> Decimal:
        _ = vals
        return ZERO_MONEY


class KuaishouDongzhangStrategy(FinancialSummaryStrategy):
    """Kuaishou 动账 formulas."""

    fields: tuple[str, ...] = ("return_cost",)

    @property
    def required_headers(self) -> tuple[str, ...]:
        return (
            "关联业务单号",
            "发生额（元）",
            "备注",
        )

    def compute_year_month(self, vals: dict[str, object]) -> tuple[int, int] | None:
        entry_time = parse_datetime(vals.get("入账时间"))
        if entry_time is None:
            return None
        return (entry_time.year, entry_time.month)

    def compute_values(
        self,
        vals: dict[str, object],
        category_dict: dict[str, list[str]] | None = None,
    ) -> dict[str, Decimal]:
        _ = category_dict
        return {"return_cost": safe_decimal(vals.get("发生额（元）"))}


class KuaishouProcessor(FinancialSummaryExcelProcessorMixin, SimpleMonthlySumProcessorMixin):
    """Hardcoded processor for Kuaishou GMV/动账/运费险/订单 Excel/CSV files."""

    summary_strategy = KuaishouGmvStrategy()
    dongzhang_strategy = KuaishouDongzhangStrategy()

    @property
    def platform_label(self) -> str:
        return "快手"

    def get_type_processor(self, type_code: str):
        if type_code == "gmv":
            return self._process_gmv
        if type_code == "动账":
            return self._process_dongzhang
        if type_code == "运费险":
            return self._process_shipping_insurance
        if type_code == "订单":
            return self._process_order
        return None

    def _current_type_code(self, strategy: FinancialSummaryStrategy) -> str:
        if strategy is self.summary_strategy:
            return "gmv"
        if strategy is self.dongzhang_strategy:
            return "动账"
        return super()._current_type_code(strategy)

    def _process_gmv(
        self,
        *,
        file_path: str,
        shop_name: str,
        category_dict: dict[str, list[str]] | None = None,
    ) -> dict:
        return self._process_financial_summary_with_strategy(
            file_path=file_path,
            shop_name=shop_name,
            category_dict=category_dict,
            strategy=self.summary_strategy,
        )

    def _process_dongzhang(
        self,
        *,
        file_path: str,
        shop_name: str,
        category_dict: dict[str, list[str]] | None = None,
    ) -> dict:
        _ = shop_name
        result = {
            "total_rows": 0,
            "success_rows": 0,
            "failed_rows": 0,
            "errors": [],
            "groups": {},
            "return_cost_rows": [],
        }
        required_headers = self.dongzhang_strategy.required_headers
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
                    type_code="动账",
                    actual_headers=[],
                    required_headers=required_headers,
                    missing_headers=required_headers,
                    header_row_number=None,
                )
                return result

            headers, header_row_number = header_result
            col_idx = self._build_col_idx(headers, required_headers)
            missing = self._missing_headers(col_idx, required_headers)
            if missing:
                result["errors"].append(f"缺少必要表头: {', '.join(missing)}")
                self._log_header_compare(
                    file_path=file_path,
                    type_code="动账",
                    actual_headers=headers,
                    required_headers=required_headers,
                    missing_headers=missing,
                    header_row_number=header_row_number,
                )
                return result

            finance_direction_header = "财务方式" if "财务方式" in col_idx else "账务方向" if "账务方向" in col_idx else None
            if finance_direction_header is None:
                result["errors"].append("缺少必要表头: 财务方式/账务方向")
                self._log_header_compare(
                    file_path=file_path,
                    type_code="动账",
                    actual_headers=headers,
                    required_headers=(*required_headers, "财务方式/账务方向"),
                    missing_headers=("财务方式/账务方向",),
                    header_row_number=header_row_number,
                )
                return result

            for row in row_iter:
                result["total_rows"] += 1
                try:
                    vals = self._row_to_values(row, col_idx)
                    order_no = safe_str(vals.get("关联业务单号"))

                    if not order_no:
                        result["failed_rows"] += 1
                        result["errors"].append(f"Row {result['total_rows'] + 1}: 关联业务单号为空")
                        continue

                    amount = self._compute_dongzhang_return_cost(
                        vals=vals,
                        finance_direction_header=finance_direction_header,
                        category_dict=category_dict,
                    )
                    if amount != ZERO_MONEY:
                        result["return_cost_rows"].append(
                            {
                                "order_no": order_no,
                                "return_cost": amount,
                            }
                        )
                    result["success_rows"] += 1
                except Exception as e:
                    result["failed_rows"] += 1
                    result["errors"].append(f"Row {result['total_rows'] + 1}: {e}")

        return result

    @staticmethod
    def _compute_dongzhang_return_cost(
        *,
        vals: dict[str, object],
        finance_direction_header: str,
        category_dict: dict[str, list[str]] | None,
    ) -> Decimal:
        if not category_dict:
            return ZERO_MONEY
        if safe_str(vals.get("业务类型")) == "资金冻结":
            return ZERO_MONEY

        desc = canonical_remark(f"{safe_str(vals.get('描述'))}{safe_str(vals.get('备注'))}")
        classified = classify_text(desc, category_dict)

        if classified.category != "其他费用":
            return ZERO_MONEY

        amount = safe_decimal(vals.get("发生额（元）"))
        finance_direction = safe_str(vals.get(finance_direction_header))
        if finance_direction == "收":
            return abs(amount)
        return -abs(amount)

    def _process_shipping_insurance(
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
            "insurance_fee_rows": [],
        }
        required_headers = ("订单编号", "商家承担服务费用（元）")

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
                    type_code="运费险",
                    actual_headers=[],
                    required_headers=required_headers,
                    missing_headers=required_headers,
                    header_row_number=None,
                )
                return result

            headers, header_row_number = header_result
            col_idx = self._build_col_idx(headers, required_headers)
            missing = self._missing_headers(col_idx, required_headers)
            if missing:
                result["errors"].append(f"缺少必要表头: {', '.join(missing)}")
                self._log_header_compare(
                    file_path=file_path,
                    type_code="运费险",
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
                    order_no = safe_str(vals.get("订单编号"))
                    if not order_no:
                        result["failed_rows"] += 1
                        result["errors"].append(f"Row {result['total_rows'] + 1}: 订单编号为空")
                        continue

                    result["insurance_fee_rows"].append(
                        {
                            "order_no": order_no,
                            "insurance_fee": safe_decimal(vals.get("商家承担服务费用（元）")),
                        }
                    )
                    result["success_rows"] += 1
                except Exception as e:
                    result["failed_rows"] += 1
                    result["errors"].append(f"Row {result['total_rows'] + 1}: {e}")

        return result

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
        required_headers = ("订单号", "订单创建时间")

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
            col_idx = self._build_col_idx(headers, required_headers)
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
                    order_no = safe_str(row[col_idx["订单号"]] if col_idx["订单号"] < len(row) else None)
                    order_created_at = parse_datetime(row[col_idx["订单创建时间"]] if col_idx["订单创建时间"] < len(row) else None)
                    if not order_no:
                        result["failed_rows"] += 1
                        result["errors"].append(f"Row {result['total_rows'] + 1}: 订单号为空")
                        continue
                    if order_created_at is None:
                        result["failed_rows"] += 1
                        result["errors"].append(f"Row {result['total_rows'] + 1}: 无法解析订单创建时间")
                        continue

                    result["orders"].append(
                        {
                            "order_no": order_no,
                            "order_created_at": order_created_at,
                        }
                    )
                    result["success_rows"] += 1
                except Exception as e:
                    result["failed_rows"] += 1
                    result["errors"].append(f"Row {result['total_rows'] + 1}: {e}")

        return result


# ── Module-level singleton ────────────────────────────────────────────────────
kuaishou_processor = KuaishouProcessor()
