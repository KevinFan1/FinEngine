from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, SmallInteger, String, Text, func, text
from sqlalchemy.dialects.postgresql import NUMERIC
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, SoftDeleteMixin


class DouyinDongzhangDetail(SoftDeleteMixin, Base):
    __tablename__ = "fin_douyin_dongzhang_details"
    __table_args__ = (
        Index(
            "uq_douyin_dongzhang_detail_flow",
            "org_id",
            "source_platform_code",
            "shop_id",
            "source_period",
            "transaction_flow_no",
            unique=True,
            postgresql_where=text("is_deleted = false AND transaction_flow_no <> ''"),
        ),
        Index(
            "idx_douyin_dongzhang_detail_summary",
            "summary_id",
            postgresql_where=text("is_deleted = false"),
        ),
        Index(
            "idx_douyin_dongzhang_detail_summary_id",
            "summary_id",
            "id",
            postgresql_where=text("is_deleted = false"),
        ),
        Index("idx_douyin_dongzhang_detail_id", "id"),
        Index("idx_douyin_dongzhang_detail_task", "task_id"),
        Index("idx_douyin_dongzhang_detail_file", "file_id"),
        Index(
            "idx_douyin_dongzhang_detail_source_period",
            "org_id",
            "source_platform_code",
            "shop_id",
            "source_period",
            postgresql_where=text("is_deleted = false"),
        ),
        Index(
            "idx_douyin_dongzhang_detail_summary_period",
            "org_id",
            "source_platform_code",
            "shop_id",
            "summary_year",
            "summary_month",
            postgresql_where=text("is_deleted = false"),
        ),
        {"comment": "抖音动账核算源明细表", "postgresql_partition_by": "RANGE (source_period)"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    task_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("fin_processing_tasks.id"), nullable=False, comment="处理任务ID")
    file_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("fin_upload_files.id"), nullable=False, comment="上传文件ID")
    summary_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("fin_financial_summaries.id"), nullable=True, comment="汇总表ID")
    org_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("fin_organizations.id"), nullable=False, comment="所属组织ID")
    shop_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("fin_shops.id"), nullable=False, comment="店铺ID")
    source_platform_code: Mapped[str] = mapped_column(String(50), nullable=False, comment="来源平台编码")
    report_platform_code: Mapped[str] = mapped_column(String(50), nullable=False, comment="报表归集平台编码")
    shop_name: Mapped[str] = mapped_column(String(500), nullable=False, comment="店铺名称")
    source_year: Mapped[int] = mapped_column(SmallInteger, nullable=False, comment="核算汇总年月-年份")
    source_month: Mapped[int] = mapped_column(SmallInteger, nullable=False, comment="核算汇总年月-月份")
    source_period: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False, comment="核算汇总年月 YYYYMM")
    summary_year: Mapped[int] = mapped_column(SmallInteger, nullable=False, comment="业务年月-年份")
    summary_month: Mapped[int] = mapped_column(SmallInteger, nullable=False, comment="业务年月-月份")
    period_source: Mapped[str] = mapped_column(String(100), nullable=False, comment="业务年月来源")
    source_row_number: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="源文件行号")

    transaction_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True, comment="动账时间")
    transaction_flow_no: Mapped[str] = mapped_column(String(500), nullable=False, default="", comment="动帐流水号")
    transaction_direction: Mapped[str] = mapped_column(String(50), nullable=False, default="", comment="动账方向")
    transaction_amount: Mapped[Decimal] = mapped_column(NUMERIC(14, 2), nullable=False, default=0, comment="动账金额")
    transaction_account: Mapped[str] = mapped_column(String(500), nullable=False, default="", comment="动账账户")
    transaction_scene: Mapped[str] = mapped_column(String(500), nullable=False, default="", comment="动账场景")
    billing_type: Mapped[str] = mapped_column(String(500), nullable=False, default="", comment="计费类型")
    sub_order_no: Mapped[str] = mapped_column(String(500), nullable=False, default="", comment="子订单号")
    order_no: Mapped[str] = mapped_column(String(500), nullable=False, default="", comment="订单号")
    after_sale_no: Mapped[str] = mapped_column(String(500), nullable=False, default="", comment="售后编号")
    order_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True, comment="下单时间")
    product_id: Mapped[str] = mapped_column(String(500), nullable=False, default="", comment="商品ID")
    product_code: Mapped[str] = mapped_column(String(500), nullable=False, default="", comment="商品编码")
    product_name: Mapped[str] = mapped_column(Text, nullable=False, default="", comment="商品名称")
    author_id: Mapped[str] = mapped_column(String(500), nullable=False, default="", comment="达人ID")
    author_name: Mapped[str] = mapped_column(String(500), nullable=False, default="", comment="达人名称")
    order_type: Mapped[str] = mapped_column(String(200), nullable=False, default="", comment="订单类型")
    order_paid_amount_raw: Mapped[Decimal] = mapped_column(NUMERIC(14, 2), nullable=False, default=0, comment="订单实付应结")
    shipping_fee: Mapped[Decimal] = mapped_column(NUMERIC(14, 2), nullable=False, default=0, comment="运费实付")
    platform_subsidy_shipping: Mapped[Decimal] = mapped_column(NUMERIC(14, 2), nullable=False, default=0, comment="实际平台补贴_运费")
    platform_subsidy: Mapped[Decimal] = mapped_column(NUMERIC(14, 2), nullable=False, default=0, comment="实际平台补贴")
    other_platform_subsidy: Mapped[Decimal] = mapped_column(NUMERIC(14, 2), nullable=False, default=0, comment="其他平台补贴")
    trade_in_deduction: Mapped[Decimal] = mapped_column(NUMERIC(14, 2), nullable=False, default=0, comment="以旧换新抵扣")
    gov_subsidy_platform: Mapped[Decimal] = mapped_column(NUMERIC(14, 2), nullable=False, default=0, comment="政府补贴平台垫资")
    author_subsidy: Mapped[Decimal] = mapped_column(NUMERIC(14, 2), nullable=False, default=0, comment="实际达人补贴")
    douyin_pay_subsidy: Mapped[Decimal] = mapped_column(NUMERIC(14, 2), nullable=False, default=0, comment="实际抖音支付补贴")
    douyin_monthly_subsidy: Mapped[Decimal] = mapped_column(NUMERIC(14, 2), nullable=False, default=0, comment="实际抖音月付营销补贴")
    bank_subsidy: Mapped[Decimal] = mapped_column(NUMERIC(14, 2), nullable=False, default=0, comment="银行补贴")
    order_refund_raw: Mapped[Decimal] = mapped_column(NUMERIC(14, 2), nullable=False, default=0, comment="订单退款")
    platform_fee_raw: Mapped[Decimal] = mapped_column(NUMERIC(14, 2), nullable=False, default=0, comment="平台服务费")
    commission_raw: Mapped[Decimal] = mapped_column(NUMERIC(14, 2), nullable=False, default=0, comment="佣金")
    provider_commission_raw: Mapped[Decimal] = mapped_column(NUMERIC(14, 2), nullable=False, default=0, comment="服务商佣金")
    channel_share: Mapped[Decimal] = mapped_column(NUMERIC(14, 2), nullable=False, default=0, comment="渠道分成")
    merchant_fee_raw: Mapped[Decimal] = mapped_column(NUMERIC(14, 2), nullable=False, default=0, comment="招商服务费")
    promotion_fee_raw: Mapped[Decimal] = mapped_column(NUMERIC(14, 2), nullable=False, default=0, comment="站外推广费")
    other_share: Mapped[Decimal] = mapped_column(NUMERIC(14, 2), nullable=False, default=0, comment="其他分成")
    is_commission_free: Mapped[str] = mapped_column(String(50), nullable=False, default="", comment="是否免佣")
    commission_free_amount: Mapped[Decimal] = mapped_column(NUMERIC(14, 2), nullable=False, default=0, comment="免佣金额")
    merchant_name: Mapped[str] = mapped_column(Text, nullable=False, default="", comment="商户主体名称")
    remark: Mapped[str] = mapped_column(Text, nullable=False, default="", comment="备注")

    matched_compensation: Mapped[str] = mapped_column(String(500), nullable=False, default="", comment="匹配赔付")
    refund_to_compensation: Mapped[Decimal] = mapped_column(NUMERIC(14, 2), nullable=False, default=0, comment="退款转赔付")
    cashback: Mapped[Decimal] = mapped_column(NUMERIC(14, 2), nullable=False, default=0, comment="返现")
    order_paid: Mapped[Decimal] = mapped_column(NUMERIC(14, 2), nullable=False, default=0, comment="收")
    refund_amount: Mapped[Decimal] = mapped_column(NUMERIC(14, 2), nullable=False, default=0, comment="退")
    gmv: Mapped[Decimal] = mapped_column(NUMERIC(14, 2), nullable=False, default=0, comment="实收GMV")
    platform_income: Mapped[Decimal] = mapped_column(NUMERIC(14, 2), nullable=False, default=0, comment="平台其他收入")
    platform_fee_positive: Mapped[Decimal] = mapped_column(NUMERIC(14, 2), nullable=False, default=0, comment="平台服务费（正数）")
    return_cost: Mapped[Decimal] = mapped_column(NUMERIC(14, 2), nullable=False, default=0, comment="退货及其他费用")
    commission_derived: Mapped[Decimal] = mapped_column(NUMERIC(14, 2), nullable=False, default=0, comment="达人佣金")
    bic: Mapped[Decimal] = mapped_column(NUMERIC(14, 2), nullable=False, default=0, comment="BIC")
    insurance_fee: Mapped[Decimal] = mapped_column(NUMERIC(14, 2), nullable=False, default=0, comment="运费险")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="更新时间")
