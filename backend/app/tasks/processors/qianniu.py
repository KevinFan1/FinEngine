"""千牛 hardcoded processors for 订单/动账 Excel/CSV files."""

from decimal import Decimal

from app.tasks.processors.base import FinancialSummaryExcelProcessorMixin, open_tabular_rows, parse_datetime, safe_str
from app.utils.money import safe_decimal

QIANNIU_ORDER_HEADERS: list[str] = [
    "订单编号",
    "支付单号",
    "支付详情",
    "买家应付货款",
    "买家应付邮费",
    "总金额",
    "买家实付金额",
    "订单创建时间",
    "订单付款时间",
    "商品标题",
    "退款金额",
    "是否主动赔付",
    "主动赔付金额",
    "主动赔付出账时间",
    "商品属性SKU",
    "C2B小额收款",
    "确认收货打款金额",
    "含应开票给个人红包",
    "总金额(旧版)",
]

QIANNIU_DONGZHANG_HEADERS: list[str] = [
    "商家昵称",
    "入帐日期",
    "入帐时间",
    "支付流水号",
    "主订单id",
    "子订单id",
    "入帐类型",
    "收入金额(元)",
    "支出金额(元)",
    "业务描述",
    "备注",
    "收/付渠道",
    "数据创建时间",
    "数据修改时间",
]

QIANNIU_ORDER_SUMMARY_FIELDS: tuple[str, ...] = (
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


class QianniuProcessor(FinancialSummaryExcelProcessorMixin):
    """Processor for 千牛 files that depend on order creation time indexes."""

    @property
    def platform_label(self) -> str:
        return "千牛"

    def get_type_processor(self, type_code: str):
        if type_code == "订单":
            return self._process_order
        if type_code == "动账":
            return self._process_dongzhang
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
        required_headers = ("订单编号", "订单创建时间")

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
                    order_no = safe_str(row[col_idx["订单编号"]] if col_idx["订单编号"] < len(row) else None)
                    order_created_at = parse_datetime(row[col_idx["订单创建时间"]] if col_idx["订单创建时间"] < len(row) else None)
                    if not order_no:
                        result["failed_rows"] += 1
                        result["errors"].append(f"Row {result['total_rows'] + header_row_number}: 订单编号为空")
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
            "order_summary_fields": list(QIANNIU_ORDER_SUMMARY_FIELDS),
            "order_summary_rows": [],
        }
        required_headers = ("主订单id", "入帐类型", "收入金额(元)", "支出金额(元)")

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

                    order_no = safe_str(vals.get("主订单id"))
                    if not order_no:
                        result["failed_rows"] += 1
                        result["errors"].append(f"Row {result['total_rows'] + header_row_number}: 主订单id为空")
                        continue

                    result["order_summary_rows"].append({"order_no": order_no, **row_values})
                    result["success_rows"] += 1
                except Exception as e:
                    result["failed_rows"] += 1
                    result["errors"].append(f"Row {result['total_rows'] + header_row_number}: {e}")

        return result

    @staticmethod
    def _compute_dongzhang_values(vals: dict[str, object]) -> dict[str, Decimal]:
        entry_type = safe_str(vals.get("入帐类型"))
        income = safe_decimal(vals.get("收入金额(元)"))
        expense = safe_decimal(vals.get("支出金额(元)"))
        net_amount = income - expense

        if entry_type == "交易收款":
            return {"order_paid_amount": income, "gmv": net_amount}
        if entry_type == "交易退款(售后)":
            return {"refund_amount": expense}
        if entry_type == "服务费":
            return {"platform_fee": net_amount}
        return {}


qianniu_processor = QianniuProcessor()
