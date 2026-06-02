from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Index, Integer, SmallInteger, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB, NUMERIC
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, SoftDeleteMixin


class MerchantRedSheet(SoftDeleteMixin, Base):
    __tablename__ = "fin_merchant_reconciliation_red_sheets"
    __table_args__ = (
        Index(
            "idx_fin_merchant_red_sheet_lookup",
            "org_id",
            "platform_code",
            "shop_id",
            "accounting_period",
            postgresql_where=text("is_deleted = false"),
        ),
        Index(
            "idx_fin_merchant_red_sheet_created",
            "org_id",
            "created_at",
            postgresql_where=text("is_deleted = false"),
        ),
        {"comment": "商家对账红单导入批次表"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    org_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("fin_organizations.id"), nullable=False, comment="所属组织ID")
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("fin_users.id"), nullable=False, comment="上传用户ID")
    shop_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("fin_shops.id"), nullable=True, comment="店铺ID")
    platform_code: Mapped[str] = mapped_column(String(50), nullable=False, default="douyin", comment="平台编码")
    shop_name: Mapped[str] = mapped_column(String(500), nullable=False, default="", comment="店铺名称")
    accounting_year: Mapped[int] = mapped_column(SmallInteger, nullable=False, comment="核算年份")
    accounting_month: Mapped[int] = mapped_column(SmallInteger, nullable=False, comment="核算月份")
    accounting_period: Mapped[int] = mapped_column(Integer, nullable=False, comment="核算年月 YYYYMM")
    original_name: Mapped[str] = mapped_column(String(500), nullable=False, comment="原始文件名")
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0, comment="文件大小字节数")
    file_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="文件 SHA-256 哈希值")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="success", comment="状态")
    purchase_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="采购明细行数")
    payment_rows: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="货款明细行数")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True, comment="错误信息")
    result_summary: Mapped[dict | None] = mapped_column(JSONB, nullable=True, comment="导入结果摘要")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="更新时间")


class MerchantRedSheetPurchase(SoftDeleteMixin, Base):
    __tablename__ = "fin_merchant_red_sheet_purchases"
    __table_args__ = (
        Index(
            "idx_fin_merchant_purchase_match",
            "org_id",
            "shop_id",
            "accounting_period",
            "live_code",
            postgresql_where=text("is_deleted = false"),
        ),
        Index(
            "idx_fin_merchant_purchase_merchant",
            "org_id",
            "shop_id",
            "accounting_period",
            "merchant",
            "live_date",
            "live_room",
            postgresql_where=text("is_deleted = false"),
        ),
        {"comment": "商家对账红单采购明细表"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    red_sheet_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("fin_merchant_reconciliation_red_sheets.id"), nullable=False, comment="红单批次ID")
    org_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("fin_organizations.id"), nullable=False, comment="所属组织ID")
    shop_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("fin_shops.id"), nullable=True, comment="店铺ID")
    shop_name: Mapped[str] = mapped_column(String(500), nullable=False, default="", comment="店铺名称快照")
    accounting_period: Mapped[int] = mapped_column(Integer, nullable=False, comment="核算年月 YYYYMM")
    source_row_number: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="源文件行号")
    live_room: Mapped[str] = mapped_column(String(500), nullable=False, default="", comment="直播间")
    merchant: Mapped[str] = mapped_column(String(500), nullable=False, default="", comment="商家")
    live_date: Mapped[str] = mapped_column(String(100), nullable=False, default="", comment="直播日期")
    loan_return_order_no: Mapped[str] = mapped_column(String(500), nullable=False, default="", comment="借/退货单号")
    loan_return_date: Mapped[date | None] = mapped_column(Date, nullable=True, comment="借/退货日期")
    live_code: Mapped[str] = mapped_column(String(500), nullable=False, default="", comment="直播编号")
    normalized_live_code: Mapped[str] = mapped_column(String(500), nullable=False, default="", comment="新直播编码")
    match_status: Mapped[str] = mapped_column(String(500), nullable=False, default="", comment="匹配")
    remark: Mapped[str] = mapped_column(Text, nullable=False, default="", comment="结算状态")
    source_shop_name: Mapped[str] = mapped_column(String(500), nullable=False, default="", comment="店铺")
    subject: Mapped[str] = mapped_column(String(500), nullable=False, default="", comment="主体")
    summary: Mapped[str] = mapped_column(String(500), nullable=False, default="", comment="摘要")
    product_name: Mapped[str] = mapped_column(Text, nullable=False, default="", comment="货品名称")
    piece_price: Mapped[Decimal] = mapped_column(NUMERIC(14, 2), nullable=False, default=0, comment="件/元")
    gram_price: Mapped[Decimal] = mapped_column(NUMERIC(14, 2), nullable=False, default=0, comment="克/元")
    sale_price: Mapped[Decimal] = mapped_column(NUMERIC(14, 2), nullable=False, default=0, comment="卖价")
    borrow_quantity: Mapped[Decimal] = mapped_column(NUMERIC(14, 2), nullable=False, default=0, comment="借货数量")
    borrow_weight_g: Mapped[Decimal] = mapped_column(NUMERIC(14, 2), nullable=False, default=0, comment="借货重量g")
    borrow_amount: Mapped[Decimal] = mapped_column(NUMERIC(14, 2), nullable=False, default=0, comment="借货金额")
    return_quantity: Mapped[Decimal] = mapped_column(NUMERIC(14, 2), nullable=False, default=0, comment="退货数量")
    return_weight_g: Mapped[Decimal] = mapped_column(NUMERIC(14, 2), nullable=False, default=0, comment="退货重量g")
    return_amount: Mapped[Decimal] = mapped_column(NUMERIC(14, 2), nullable=False, default=0, comment="退货金额")
    estimated_settlement_date: Mapped[date | None] = mapped_column(Date, nullable=True, comment="预计结款日期")
    labor_fee_per_gram: Mapped[Decimal] = mapped_column(NUMERIC(14, 2), nullable=False, default=0, comment="工费/克")
    labor_fee_per_piece: Mapped[Decimal] = mapped_column(NUMERIC(14, 2), nullable=False, default=0, comment="工费/件")
    raw_row: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict, comment="原始行JSON")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")


class MerchantRedSheetPayment(SoftDeleteMixin, Base):
    __tablename__ = "fin_merchant_red_sheet_payments"
    __table_args__ = (
        Index(
            "idx_fin_merchant_payment_match",
            "org_id",
            "shop_id",
            "accounting_period",
            "merchant",
            "live_date",
            "live_room",
            postgresql_where=text("is_deleted = false"),
        ),
        {"comment": "商家对账红单货款明细表"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    red_sheet_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("fin_merchant_reconciliation_red_sheets.id"), nullable=False, comment="红单批次ID")
    org_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("fin_organizations.id"), nullable=False, comment="所属组织ID")
    shop_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("fin_shops.id"), nullable=True, comment="店铺ID")
    shop_name: Mapped[str] = mapped_column(String(500), nullable=False, default="", comment="店铺名称快照")
    accounting_period: Mapped[int] = mapped_column(Integer, nullable=False, comment="核算年月 YYYYMM")
    source_row_number: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="源文件行号")
    sequence_no: Mapped[str] = mapped_column(String(100), nullable=False, default="", comment="序号")
    live_room: Mapped[str] = mapped_column(String(500), nullable=False, default="", comment="直播间")
    live_date: Mapped[str] = mapped_column(String(100), nullable=False, default="", comment="直播日期")
    merchant: Mapped[str] = mapped_column(String(500), nullable=False, default="", comment="商家")
    borrow_total_amount: Mapped[Decimal] = mapped_column(NUMERIC(14, 2), nullable=False, default=0, comment="借货总金额")
    return_total_amount: Mapped[Decimal] = mapped_column(NUMERIC(14, 2), nullable=False, default=0, comment="退货总金额")
    business_fee_deduction: Mapped[Decimal] = mapped_column(NUMERIC(14, 2), nullable=False, default=0, comment="冲减业务费用")
    deduction_amount: Mapped[Decimal] = mapped_column(NUMERIC(14, 2), nullable=False, default=0, comment="冲减金额")
    payable_goods_amount: Mapped[Decimal] = mapped_column(NUMERIC(14, 2), nullable=False, default=0, comment="应付货款金额")
    return_rate: Mapped[str] = mapped_column(String(100), nullable=False, default="", comment="退货率")
    settlement_subject: Mapped[str] = mapped_column(String(500), nullable=False, default="", comment="结算主体")
    receipt_subject: Mapped[str] = mapped_column(String(500), nullable=False, default="", comment="收款主体")
    cost_subject: Mapped[str] = mapped_column(String(500), nullable=False, default="", comment="成本主体")
    payable_amount: Mapped[Decimal] = mapped_column(NUMERIC(14, 2), nullable=False, default=0, comment="应付款金额")
    subject_collection_amount: Mapped[Decimal] = mapped_column(NUMERIC(14, 2), nullable=False, default=0, comment="主体回款金额")
    receipt_merchant: Mapped[str] = mapped_column(String(500), nullable=False, default="", comment="收款商家")
    collection_merchant: Mapped[str] = mapped_column(String(500), nullable=False, default="", comment="回款商家")
    is_settled: Mapped[str] = mapped_column(String(100), nullable=False, default="", comment="是否已结款")
    is_collected: Mapped[str] = mapped_column(String(100), nullable=False, default="", comment="是否已回款")
    remark: Mapped[str] = mapped_column(Text, nullable=False, default="", comment="备注")
    payment_screenshot: Mapped[str] = mapped_column(String(1000), nullable=False, default="", comment="付款截图")
    settlement_date: Mapped[date | None] = mapped_column(Date, nullable=True, comment="结算日期")
    collection_date: Mapped[date | None] = mapped_column(Date, nullable=True, comment="回款日期")
    deduction_remark: Mapped[str] = mapped_column(Text, nullable=False, default="", comment="冲减备注")
    pending_issue: Mapped[str] = mapped_column(Text, nullable=False, default="", comment="待解决事项")
    is_receipt_merchant_modified: Mapped[str] = mapped_column(String(100), nullable=False, default="", comment="是否修改收款商家")
    is_receipt_amount_modified: Mapped[str] = mapped_column(String(100), nullable=False, default="", comment="是否修改收款金额")
    modified_month: Mapped[str] = mapped_column(String(100), nullable=False, default="", comment="修改月份")
    application_date: Mapped[date | None] = mapped_column(Date, nullable=True, comment="申请日期")
    paid_amount: Mapped[Decimal] = mapped_column(NUMERIC(14, 2), nullable=False, default=0, comment="已付")
    borrow_minus_return: Mapped[Decimal] = mapped_column(NUMERIC(14, 2), nullable=False, default=0, comment="借-退")
    raw_row: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict, comment="原始行JSON")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")


class MerchantBankFlowFile(SoftDeleteMixin, Base):
    __tablename__ = "fin_merchant_bank_flow_files"
    __table_args__ = (
        Index(
            "idx_fin_merchant_bank_flow_file_lookup",
            "org_id",
            "accounting_period",
            "account_name",
            postgresql_where=text("is_deleted = false"),
        ),
        Index(
            "idx_fin_merchant_bank_flow_file_created",
            "org_id",
            "created_at",
            postgresql_where=text("is_deleted = false"),
        ),
        {"comment": "商家对账银行流水导入批次表"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    org_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("fin_organizations.id"), nullable=False, comment="所属组织ID")
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("fin_users.id"), nullable=False, comment="上传用户ID")
    accounting_year: Mapped[int] = mapped_column(SmallInteger, nullable=False, comment="核算年份")
    accounting_month: Mapped[int] = mapped_column(SmallInteger, nullable=False, comment="核算月份")
    accounting_period: Mapped[int] = mapped_column(Integer, nullable=False, comment="核算年月 YYYYMM")
    original_name: Mapped[str] = mapped_column(String(500), nullable=False, comment="原始文件名")
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0, comment="文件大小字节数")
    file_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="文件 SHA-256 哈希值")
    bank_name: Mapped[str] = mapped_column(String(100), nullable=False, default="", comment="银行名称")
    account_name: Mapped[str] = mapped_column(String(500), nullable=False, default="", comment="账户名称")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="success", comment="状态")
    row_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="流水行数")
    matched_row_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="已解析直播日期行数")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True, comment="错误信息")
    result_summary: Mapped[dict | None] = mapped_column(JSONB, nullable=True, comment="导入结果摘要")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="更新时间")


class MerchantBankFlowRow(SoftDeleteMixin, Base):
    __tablename__ = "fin_merchant_bank_flow_rows"
    __table_args__ = (
        Index(
            "idx_fin_merchant_bank_flow_match",
            "org_id",
            "accounting_period",
            "account_name",
            "counterparty_name",
            "live_date",
            postgresql_where=text("is_deleted = false"),
        ),
        {"comment": "商家对账银行流水明细表"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    bank_flow_file_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("fin_merchant_bank_flow_files.id"), nullable=False, comment="银行流水批次ID")
    org_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("fin_organizations.id"), nullable=False, comment="所属组织ID")
    accounting_period: Mapped[int] = mapped_column(Integer, nullable=False, comment="核算年月 YYYYMM")
    source_row_number: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="源文件行号")
    bank_name: Mapped[str] = mapped_column(String(100), nullable=False, default="", comment="银行名称")
    account_no: Mapped[str] = mapped_column(String(200), nullable=False, default="", comment="账号")
    account_name: Mapped[str] = mapped_column(String(500), nullable=False, default="", comment="账户名称")
    transaction_date: Mapped[date | None] = mapped_column(Date, nullable=True, comment="交易日期")
    transaction_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True, comment="交易时间")
    debit_amount: Mapped[Decimal] = mapped_column(NUMERIC(14, 2), nullable=False, default=0, comment="借方发生额/支出金额")
    credit_amount: Mapped[Decimal] = mapped_column(NUMERIC(14, 2), nullable=False, default=0, comment="贷方发生额/收入金额")
    flow_amount: Mapped[Decimal] = mapped_column(NUMERIC(14, 2), nullable=False, default=0, comment="流水净额：支出为正，收入为负")
    balance: Mapped[Decimal] = mapped_column(NUMERIC(14, 2), nullable=False, default=0, comment="余额")
    counterparty_account_no: Mapped[str] = mapped_column(String(200), nullable=False, default="", comment="对方账号")
    counterparty_name: Mapped[str] = mapped_column(String(500), nullable=False, default="", comment="对方户名")
    counterparty_bank: Mapped[str] = mapped_column(String(500), nullable=False, default="", comment="对方开户机构/行名")
    summary: Mapped[str] = mapped_column(String(500), nullable=False, default="", comment="摘要")
    purpose: Mapped[str] = mapped_column(Text, nullable=False, default="", comment="用途/备注/附言")
    remark: Mapped[str] = mapped_column(Text, nullable=False, default="", comment="备注")
    live_date: Mapped[str] = mapped_column(String(100), nullable=False, default="", comment="解析直播日期")
    transaction_flow_no: Mapped[str] = mapped_column(String(500), nullable=False, default="", comment="交易流水号")
    raw_row: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict, comment="原始行JSON")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")


class MerchantOpeningBalance(SoftDeleteMixin, Base):
    __tablename__ = "fin_merchant_opening_balances"
    __table_args__ = (
        Index(
            "uq_fin_merchant_opening_balance",
            "org_id",
            "platform_code",
            "accounting_period",
            "our_subject",
            "receipt_merchant",
            unique=True,
            postgresql_where=text("is_deleted = false"),
        ),
        Index(
            "idx_fin_merchant_opening_balance_lookup",
            "org_id",
            "platform_code",
            "accounting_period",
            postgresql_where=text("is_deleted = false"),
        ),
        {"comment": "商家对账期初余额表"},
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True, comment="主键ID")
    org_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("fin_organizations.id"), nullable=False, comment="所属组织ID")
    platform_code: Mapped[str] = mapped_column(String(50), nullable=False, default="douyin", comment="平台编码")
    accounting_year: Mapped[int] = mapped_column(SmallInteger, nullable=False, comment="核算年份")
    accounting_month: Mapped[int] = mapped_column(SmallInteger, nullable=False, comment="核算月份")
    accounting_period: Mapped[int] = mapped_column(Integer, nullable=False, comment="核算年月 YYYYMM")
    our_subject: Mapped[str] = mapped_column(String(500), nullable=False, default="", comment="我方主体")
    receipt_merchant: Mapped[str] = mapped_column(String(500), nullable=False, default="", comment="收款商家")
    opening_balance: Mapped[Decimal] = mapped_column(NUMERIC(14, 2), nullable=False, default=0, comment="期初余额")
    remark: Mapped[str] = mapped_column(Text, nullable=False, default="", comment="备注")
    created_by: Mapped[int] = mapped_column(BigInteger, ForeignKey("fin_users.id"), nullable=False, comment="创建用户ID")
    updated_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("fin_users.id"), nullable=True, comment="最近修改用户ID")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), comment="更新时间")
