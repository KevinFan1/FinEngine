"""支付宝 hardcoded processor for 动账 Excel/CSV files."""

from datetime import datetime
from decimal import Decimal

from app.tasks.processors.base import FinancialSummaryExcelProcessorMixin, open_tabular_rows, safe_str
from app.utils.money import ZERO_MONEY, safe_decimal

ALIPAY_DONGZHANG_HEADERS: list[str] = [
    "序号",
    "入账时间",
    "支付宝交易号",
    "支付宝流水号",
    "商户订单号",
    "账务类型",
    "收入（+元）",
    "支出（-元）",
    "账户余额（元）",
    "服务费（元）",
    "支付渠道",
    "签约产品",
    "对方账户",
    "对方名称",
    "银行订单号",
    "商品名称",
    "备注",
    "业务基础订单号",
    "业务订单号",
    "业务账单来源",
    "业务描述",
    "付款备注",
]

ALIPAY_SUMMARY_FIELDS: tuple[str, ...] = (
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


class AlipayProcessor(FinancialSummaryExcelProcessorMixin):
    """Processor for 支付宝 files.

    支付宝动账表的归属年月来自支付交易单号前 6 位。单号长度大于 28 时，
    归属年月取前 6 位对应月份的上一个月。
    """

    @property
    def platform_label(self) -> str:
        return "支付宝"

    def get_type_processor(self, type_code: str):
        if type_code == "动账":
            return self._process_dongzhang
        return None

    def _process_dongzhang(
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
        }
        required_headers = tuple(ALIPAY_DONGZHANG_HEADERS)

        with open_tabular_rows(file_path) as rows:
            if rows is None:
                result["errors"].append("无法打开表格文件")
                return result

            row_iter = iter(rows)
            header_row = self._read_fixed_header_row(row_iter)
            if header_row is None:
                result["errors"].append("无法读取第 3 行表头")
                self._log_header_compare(
                    file_path=file_path,
                    type_code="动账",
                    actual_headers=[],
                    required_headers=required_headers,
                    missing_headers=required_headers,
                    header_row_number=None,
                )
                return result

            headers, header_row_number = header_row
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

            groups: dict[tuple[str, int, int], dict[str, Decimal]] = {}
            for row in row_iter:
                result["total_rows"] += 1
                try:
                    vals = self._row_to_values(row, col_idx)
                    trade_no = self._payment_trade_no(vals)
                    year_month = self._year_month_from_trade_no(trade_no)
                    if year_month is None:
                        result["failed_rows"] += 1
                        result["errors"].append(f"Row {result['total_rows'] + header_row_number}: 无法根据支付交易单号解析归属年月")
                        continue

                    key = (shop_name, year_month[0], year_month[1])
                    agg = groups.setdefault(key, {field: ZERO_MONEY for field in ALIPAY_SUMMARY_FIELDS})
                    row_values = self._compute_dongzhang_values(vals)
                    for field, value in row_values.items():
                        agg[field] = agg.get(field, ZERO_MONEY) + value
                    result["success_rows"] += 1
                except Exception as e:
                    result["failed_rows"] += 1
                    result["errors"].append(f"Row {result['total_rows'] + header_row_number}: {e}")

        result["groups"] = {f"{shop}|{year}|{month}": values for (shop, year, month), values in groups.items()}
        return result

    @staticmethod
    def _read_fixed_header_row(row_iter) -> tuple[list[str], int] | None:
        for row_number, row in enumerate(row_iter, start=1):
            if row_number == 3:
                return FinancialSummaryExcelProcessorMixin._read_headers(row), row_number
        return None

    @staticmethod
    def _payment_trade_no(vals: dict[str, object]) -> str:
        return safe_str(vals.get("支付宝交易号"))

    @staticmethod
    def _year_month_from_trade_no(trade_no: str) -> tuple[int, int] | None:
        compact = "".join(ch for ch in trade_no if ch.isdigit())
        if len(compact) < 6:
            return None

        year_month = compact[:6]
        try:
            dt = datetime.strptime(year_month, "%Y%m")
        except ValueError:
            return None

        year, month = dt.year, dt.month
        if len(trade_no) > 28:
            month -= 1
            if month <= 0:
                year -= 1
                month = 12
        return year, month

    @staticmethod
    def _compute_dongzhang_values(vals: dict[str, object]) -> dict[str, Decimal]:
        account_type = safe_str(vals.get("账务类型"))
        remark = safe_str(vals.get("备注"))
        business_desc = safe_str(vals.get("业务描述"))
        income = safe_decimal(vals.get("收入（+元）"))
        expense = safe_decimal(vals.get("支出（-元）"))
        net_amount = income - expense

        values = {field: ZERO_MONEY for field in ALIPAY_SUMMARY_FIELDS}
        if account_type == "在线支付":
            values["gmv"] += income
        if account_type == "退款（交易退款）":
            values["gmv"] -= expense

        if "其他收入-百亿补贴激励前返" in business_desc:
            values["platform_income"] += net_amount

        if "其他支出-百亿补贴预收" in business_desc:
            values["return_cost"] += abs(net_amount)

        if "淘宝客佣金代扣款" in remark:
            values["platform_fee"] += net_amount

        has_software_service_fee = "软件服务费" in business_desc
        if not business_desc:
            has_software_service_fee = "百亿补贴软件服务费" in remark
        if has_software_service_fee:
            values["platform_fee"] += net_amount

        return values


alipay_processor = AlipayProcessor()
