"""微信小店 hardcoded processors for 订单/动账/BIC/运费险 Excel/CSV files."""

from decimal import Decimal

from app.tasks.processors.base import FinancialSummaryExcelProcessorMixin, open_tabular_rows, parse_datetime, safe_str
from app.utils.money import ZERO_MONEY, safe_decimal

WEIXIN_VIDEO_ORDER_HEADERS: list[str] = [
    "订单号",
    "订单下单时间",
    "订单发货时间",
    "订单确认收货时间",
    "订单完成结算时间",
    "订单状态",
    "发货方式",
    "收件人姓名",
    "收件人地址",
    "省",
    "市",
    "区",
    "收件人手机",
    "买家备注",
    "商家备注",
    "打标颜色",
    "商品总价",
    "订单实际支付金额",
    "订单实际收款金额",
    "订单运费",
    "商品优惠",
    "跨店优惠",
    "商品改价",
    "积分抵扣",
    "支付方式",
    "支付时间",
    "交易单号",
    "物流公司",
    "快递单号",
    "技术服务费",
    "技术服务费（将以人气卡形式返还）",
    "运费险预计投保费用",
    "带货方式",
    "带货账号类型",
    "带货账号昵称",
    "带货费用渠道",
    "带货费用类型",
    "带货费用",
    "带货佣金率",
    "礼物单号",
    "商品名称",
    "商品编码(平台)",
    "商品编码(自定义)",
    "SKU编码(自定义)",
    "商品属性",
    "商品价格(单件)",
    "商品实际价格(单件)",
    "商品实际价格(总共)",
    "是否预售",
    "商品数量",
    "商品平台券优惠",
    "商品平均运费",
    "定制信息",
    "定制预览图",
    "商品发货",
    "商品售后",
    "商品已退款金额",
]

WEIXIN_VIDEO_DONGZHANG_HEADERS: list[str] = [
    "流水单号",
    "记账时间",
    "动帐类型",
    "收支类型",
    "收支金额",
    "账户余额",
    "关联订单号",
    "关联售后单号",
    "关联提现单号",
    "关联保单号",
    "关联礼物单号",
    "详情",
]

WEIXIN_VIDEO_BIC_HEADERS: list[str] = [
    "订单编号",
    "质检仓",
    "质检机构",
    "质检状态",
    "结算状态",
    "预扣物流费",
    "预扣包装盒费",
    "预扣首饰盒费",
    "预扣服务费",
    "预扣质检费",
    "预扣合单费",
    "预扣合计",
    "实扣物流费",
    "实扣包装盒费",
    "实扣首饰盒费",
    "实扣服务费",
    "实扣质检费",
    "实扣合单费",
    "实扣合计",
    "已补差",
    "已退回",
    "结算欠款",
]

WEIXIN_VIDEO_ORDER_SUMMARY_FIELDS: tuple[str, ...] = (
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


class WeixinVideoProcessor(FinancialSummaryExcelProcessorMixin):
    """Processor for 微信小店 files that depend on order creation time indexes."""

    @property
    def platform_label(self) -> str:
        return "微信小店"

    def get_type_processor(self, type_code: str):
        if type_code == "订单":
            return self._process_order
        if type_code == "动账":
            return self._process_dongzhang
        if type_code == "bic":
            return self._process_bic
        if type_code == "运费险":
            return self._process_shipping_insurance
        return None

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
        required_headers = ("订单号", "订单下单时间")

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
                    order_created_at = parse_datetime(row[col_idx["订单下单时间"]] if col_idx["订单下单时间"] < len(row) else None)
                    if not order_no:
                        result["failed_rows"] += 1
                        result["errors"].append(f"Row {result['total_rows'] + 1}: 订单号为空")
                        continue
                    if order_created_at is None:
                        result["failed_rows"] += 1
                        result["errors"].append(f"Row {result['total_rows'] + 1}: 无法解析订单下单时间")
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

    def _process_dongzhang(
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
            "order_summary_fields": list(WEIXIN_VIDEO_ORDER_SUMMARY_FIELDS),
            "order_summary_rows": [],
        }
        required_headers = ("动帐类型", "收支金额", "关联订单号")

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

            for row in row_iter:
                result["total_rows"] += 1
                try:
                    vals = self._row_to_values(row, col_idx)
                    row_values = self._compute_dongzhang_values(vals)
                    if not row_values:
                        result["success_rows"] += 1
                        continue

                    order_no = safe_str(vals.get("关联订单号"))
                    if not order_no:
                        result["failed_rows"] += 1
                        result["errors"].append(f"Row {result['total_rows'] + 1}: 关联订单号为空")
                        continue

                    result["order_summary_rows"].append({"order_no": order_no, **row_values})
                    result["success_rows"] += 1
                except Exception as e:
                    result["failed_rows"] += 1
                    result["errors"].append(f"Row {result['total_rows'] + 1}: {e}")

        return result

    @staticmethod
    def _compute_dongzhang_values(vals: dict[str, object]) -> dict[str, Decimal]:
        action_type = safe_str(vals.get("动帐类型"))
        amount = safe_decimal(vals.get("收支金额"))

        if action_type == "订单支付":
            paid_amount = abs(amount)
            return {"order_paid_amount": paid_amount, "gmv": paid_amount}
        if action_type == "订单退款":
            refund_amount = abs(amount)
            return {"refund_amount": refund_amount, "gmv": -refund_amount}
        if action_type == "技术服务费":
            return {"platform_fee": abs(amount)}
        if action_type == "达人佣金":
            return {"commission": abs(amount)}
        return {}

    def _process_bic(
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
            "bic_rows": [],
        }
        required_headers = ("订单编号", "质检状态", "实扣合计")

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
                    type_code="bic",
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
                    type_code="bic",
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
                    if safe_str(vals.get("质检状态")) != "已发货":
                        result["success_rows"] += 1
                        continue

                    order_no = safe_str(vals.get("订单编号"))
                    if not order_no:
                        result["failed_rows"] += 1
                        result["errors"].append(f"Row {result['total_rows'] + 1}: 订单编号为空")
                        continue

                    result["bic_rows"].append(
                        {
                            "order_no": order_no,
                            "bic": safe_decimal(vals.get("实扣合计")),
                        }
                    )
                    result["success_rows"] += 1
                except Exception as e:
                    result["failed_rows"] += 1
                    result["errors"].append(f"Row {result['total_rows'] + 1}: {e}")

        return result

    def _process_shipping_insurance(
        self,
        *,
        file_path: str,
        shop_name: str,
        category_dict: dict[str, list[str]] | None = None,
    ) -> dict:
        _ = file_path, shop_name, category_dict
        return {
            "total_rows": 0,
            "success_rows": 0,
            "failed_rows": 0,
            "errors": [],
            "groups": {},
            "insurance_fee_rows": [],
            "insurance_fee": ZERO_MONEY,
        }


weixin_video_processor = WeixinVideoProcessor()
