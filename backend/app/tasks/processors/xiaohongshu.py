"""小红书 hardcoded processors for GMV/动账/其他服务款/订单 Excel/CSV files."""

from decimal import Decimal

from app.tasks.processors.base import FinancialSummaryExcelProcessorMixin, GroupKey, normalize_positive_summary_fields, open_tabular_rows, parse_datetime, safe_str
from app.utils.money import ZERO_MONEY, safe_decimal

XIAOHONGSHU_GMV_HEADERS: list[str] = [
    "订单号",
    "售后单号",
    "下单时间",
    "结算时间",
    "交易类型",
    "结算账户",
    "动账金额",
    "计佣基数",
    "商品实付/实退",
    "运费实付/实退",
    "平台优惠补贴",
    "平台运费补贴",
    "跨境税代缴",
    "商品税金",
    "运费税金",
    "佣金",
    "支付渠道费",
    "分销佣金",
    "代运营服务商佣金",
    "代开发服务商佣金",
    "花呗分期手续费",
    "国补订单毛保金额",
    "备注",
]

XIAOHONGSHU_OTHER_SERVICE_HEADERS: list[str] = [
    "业务款项",
    "订单号",
    "业务单据号",
    "结算时间",
    "结算账户",
    "交易类型",
    "动账金额",
    "备注",
]

XIAOHONGSHU_DONGZHANG_HEADERS: list[str] = [
    "创建时间",
    "交易类型描述",
    "收入（元）",
    "支出（元）",
    "账户余额（元）",
    "业务单号",
    "备注",
]

XIAOHONGSHU_ORDER_HEADERS: list[str] = [
    "订单号",
    "订单状态",
    "售后状态",
    "订单类型",
    "订单标记",
    "收件人姓名",
    "收件人电话",
    "收件人地址",
    "省",
    "市",
    "区",
    "区域编码",
    "小红书编码",
    "条形码",
    "规格ID",
    "达人ID",
    "达人名称",
    "SKU名称",
    "SKU规格",
    "SKU件数",
    "是否为赠品",
    "发票/Invoice",
    "商品总价(元)",
    "用户应付金额(元)",
    "平台优惠(元)",
    "店铺优惠(元)",
    "支付渠道优惠(元)",
    "SKU商家改价(元)",
    "商家应收金额(元)（支付金额）",
    "支付方式",
    "支付渠道订单号",
    "支付期数",
    "利息费用",
    "手续费承担方",
    "支付时间",
    "sku净重(kg)",
    "包裹总净重(kg)",
    "包裹总运费(元)",
    "快递公司",
    "快递单号",
    "发货链接",
    "大头笔/Paint Marker",
    "集包地/Express Extend 1",
    "三段码/Express Extend 2",
    "订购人身份证姓名/ID Name",
    "订购人身份证号/ID Number",
    "收件人身份证姓名",
    "收件人身份证号",
    "订单创建时间",
    "预售订单开始发货时间",
    "预售订单截止发货时间",
    "承诺发货时间",
    "订单发货时间",
    "订单完成时间",
    "发货仓库",
    "确认收货类型",
    "是否延迟收货",
    "用户备注",
    "包裹备注标记",
    "包裹备注信息",
    "异常原因",
    "店铺名称",
    "用户编号",
    "运费模版名称",
    "物流方案名称",
    "第三方机构订单号",
    "国补模式",
    "供应商id",
    "供应商名称",
    "商家编码",
    "商品ID",
    "商品名称",
]

XIAOHONGSHU_GMV_FIELDS: tuple[str, ...] = (
    "order_paid_amount",
    "refund_amount",
    "gmv",
    "platform_income",
    "platform_fee",
    "commission",
)


class XiaohongshuProcessor(FinancialSummaryExcelProcessorMixin):
    """Processor for 小红书 GMV and order-dependent return-cost files."""

    @property
    def platform_label(self) -> str:
        return "小红书"

    def get_type_processor(self, type_code: str):
        if type_code == "gmv":
            return self._process_gmv
        if type_code == "其他服务款":
            return self._process_other_service
        if type_code == "动账":
            return self._process_dongzhang
        if type_code == "订单":
            return self._process_order
        return None

    def _process_gmv(
        self,
        *,
        file_path: str,
        shop_name: str,
        category_dict: dict[str, list[str]] | None = None,
    ) -> dict:
        _ = category_dict
        result = {
            "total_rows": 0,
            "success_rows": 0,
            "failed_rows": 0,
            "errors": [],
            "groups": {},
            "orders": [],
        }
        required_headers = ("订单号", "下单时间", "商品实付/实退", "平台优惠补贴", "佣金", "分销佣金")

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
                    type_code="gmv",
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
                    type_code="gmv",
                    actual_headers=headers,
                    required_headers=required_headers,
                    missing_headers=missing,
                    header_row_number=header_row_number,
                )
                return result

            groups: dict[GroupKey, dict[str, Decimal]] = {}
            for row in row_iter:
                result["total_rows"] += 1
                try:
                    vals = self._row_to_values(row, col_idx)
                    order_no = safe_str(vals.get("订单号"))
                    order_created_at = parse_datetime(vals.get("下单时间"))
                    if not order_no:
                        result["failed_rows"] += 1
                        result["errors"].append(f"Row {result['total_rows'] + 1}: 订单号为空")
                        continue
                    if order_created_at is None:
                        result["failed_rows"] += 1
                        result["errors"].append(f"Row {result['total_rows'] + 1}: 无法解析下单时间")
                        continue

                    result["orders"].append(
                        {
                            "order_no": order_no,
                            "order_created_at": order_created_at,
                        }
                    )

                    key = GroupKey(shop=shop_name, year=order_created_at.year, month=order_created_at.month)
                    agg = groups.setdefault(key, {field: ZERO_MONEY for field in XIAOHONGSHU_GMV_FIELDS})
                    paid_or_refund = safe_decimal(vals.get("商品实付/实退"))
                    if paid_or_refund > ZERO_MONEY:
                        agg["order_paid_amount"] += paid_or_refund
                    elif paid_or_refund < ZERO_MONEY:
                        agg["refund_amount"] += paid_or_refund
                    agg["gmv"] += paid_or_refund
                    agg["platform_income"] += safe_decimal(vals.get("平台优惠补贴"))
                    agg["platform_fee"] += safe_decimal(vals.get("佣金"))
                    agg["commission"] += safe_decimal(vals.get("分销佣金"))
                    result["success_rows"] += 1
                except Exception as e:
                    result["failed_rows"] += 1
                    result["errors"].append(f"Row {result['total_rows'] + 1}: {e}")

        result["groups"] = self._serialize_groups({key: normalize_positive_summary_fields(agg) for key, agg in groups.items()})
        return result

    def _process_other_service(
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
            "return_cost_contribution_rows": [],
        }
        required_headers = ("业务款项", "订单号", "动账金额")

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
                    type_code="其他服务款",
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
                    type_code="其他服务款",
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
                    if safe_str(vals.get("业务款项")) != "小额打款":
                        result["success_rows"] += 1
                        continue

                    order_no = safe_str(vals.get("订单号"))
                    if not order_no:
                        result["failed_rows"] += 1
                        result["errors"].append(f"Row {result['total_rows'] + 1}: 订单号为空")
                        continue

                    result["return_cost_contribution_rows"].append(
                        {
                            "order_no": order_no,
                            "return_cost": safe_decimal(vals.get("动账金额")),
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
                    vals = self._row_to_values(row, col_idx)
                    order_no = safe_str(vals.get("订单号"))
                    order_created_at = parse_datetime(vals.get("订单创建时间"))
                    if not order_no:
                        result["failed_rows"] += 1
                        result["errors"].append(f"Row {result['total_rows'] + header_row_number}: 订单号为空")
                        continue
                    if order_created_at is None:
                        result["failed_rows"] += 1
                        result["errors"].append(f"Row {result['total_rows'] + header_row_number}: 无法解析订单创建时间")
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
                    result["errors"].append(f"Row {result['total_rows'] + header_row_number}: {e}")

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
            "return_cost_contribution_rows": [],
        }
        required_headers = ("交易类型描述", "收入（元）", "支出（元）", "业务单号")

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
                    if safe_str(vals.get("交易类型描述")) != "小额收款":
                        result["success_rows"] += 1
                        continue

                    order_no = safe_str(vals.get("业务单号"))
                    if not order_no:
                        result["failed_rows"] += 1
                        result["errors"].append(f"Row {result['total_rows'] + 1}: 业务单号为空")
                        continue

                    received_amount = safe_decimal(vals.get("收入（元）")) - safe_decimal(vals.get("支出（元）"))
                    result["return_cost_contribution_rows"].append(
                        {
                            "order_no": order_no,
                            "return_cost": -received_amount,
                        }
                    )
                    result["success_rows"] += 1
                except Exception as e:
                    result["failed_rows"] += 1
                    result["errors"].append(f"Row {result['total_rows'] + 1}: {e}")

        return result


xiaohongshu_processor = XiaohongshuProcessor()
