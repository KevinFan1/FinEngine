from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator


def _live_date_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return str(value).strip()


class MerchantRedSheetOut(BaseModel):
    id: int
    org_id: int
    org_name: str | None = None
    user_id: int
    shop_id: int | None = None
    shop_name: str
    shop_color: str | None = None
    platform_code: str
    accounting_year: int
    accounting_month: int
    accounting_period: int
    original_name: str
    file_size: int
    file_hash: str | None = None
    status: str
    purchase_rows: int
    payment_rows: int
    error_message: str | None = None
    result_summary: dict | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MerchantRedSheetImportResult(BaseModel):
    red_sheet_id: int
    purchase_rows: int
    payment_rows: int
    errors: list[str] = []
    warnings: list[str] = []


class MerchantBankFlowImportResult(BaseModel):
    bank_flow_file_id: int
    row_count: int
    matched_row_count: int
    errors: list[str] = []
    warnings: list[str] = []


class MerchantRedSheetShopValidationResult(BaseModel):
    recognized_shop_names: list[str] = []
    unrecognized_shop_names: list[str] = []


class MerchantReconciliationDetailOut(BaseModel):
    id: int
    org_id: int
    org_name: str | None = None
    shop_id: int
    shop_name: str
    shop_color: str | None = None
    accounting_year: int
    accounting_month: int
    accounting_period: int
    platform_code: str
    platform_label: str
    source_row_number: int
    transaction_time: str = ""
    transaction_flow_no: str = ""
    transaction_direction: str = ""
    transaction_amount: Decimal = Decimal("0")
    transaction_scene: str = ""
    sub_order_no: str = ""
    order_no: str = ""
    order_time: str = ""
    product_id: str = ""
    product_code: str = ""
    product_name: str = ""
    author_name: str = ""
    gmv: Decimal = Decimal("0")
    allocated_bic: Decimal = Decimal("0")
    allocated_insurance_fee: Decimal = Decimal("0")
    live_amount: Decimal = Decimal("0")
    major_merchant_name: str = ""
    receipt_merchant: str = ""
    merchant_receipt_subject: str = ""
    live_room: str = ""
    live_date: str = ""
    match_status: str = ""
    match_error: str = ""

    @field_validator("live_date", mode="before")
    @classmethod
    def validate_live_date(cls, value: object) -> str:
        return _live_date_text(value)


class MerchantReconciliationStatsOut(BaseModel):
    total_gmv: Decimal = Decimal("0")
    total_bic: Decimal = Decimal("0")
    total_allocated_bic: Decimal = Decimal("0")
    total_insurance_fee: Decimal = Decimal("0")
    total_allocated_insurance_fee: Decimal = Decimal("0")
    total_live_amount: Decimal = Decimal("0")
    matched_rows: int = 0
    unmatched_rows: int = 0


class MerchantReconciliationDetailPageOut(BaseModel):
    items: list[MerchantReconciliationDetailOut]
    total: int
    page: int
    page_size: int
    stats: MerchantReconciliationStatsOut


class MerchantRedSheetPurchaseOut(BaseModel):
    id: int
    red_sheet_id: int
    org_id: int
    org_name: str | None = None
    shop_id: int | None = None
    shop_name: str = ""
    shop_color: str | None = None
    accounting_period: int
    source_row_number: int
    live_room: str = ""
    merchant: str = ""
    live_date: str = ""
    loan_return_order_no: str = ""
    loan_return_date: date | None = None
    live_code: str = ""
    normalized_live_code: str = ""
    match_status: str = ""
    remark: str = ""
    source_shop_name: str = ""
    subject: str = ""
    summary: str = ""
    product_name: str = ""
    piece_price: Decimal = Decimal("0")
    gram_price: Decimal = Decimal("0")
    sale_price: Decimal = Decimal("0")
    borrow_quantity: Decimal = Decimal("0")
    borrow_weight_g: Decimal = Decimal("0")
    borrow_amount: Decimal = Decimal("0")
    return_quantity: Decimal = Decimal("0")
    return_weight_g: Decimal = Decimal("0")
    return_amount: Decimal = Decimal("0")
    estimated_settlement_date: date | None = None
    labor_fee_per_gram: Decimal = Decimal("0")
    labor_fee_per_piece: Decimal = Decimal("0")
    created_at: datetime

    @field_validator("live_date", mode="before")
    @classmethod
    def validate_live_date(cls, value: object) -> str:
        return _live_date_text(value)

    class Config:
        from_attributes = True


class MerchantRedSheetPaymentOut(BaseModel):
    id: int
    red_sheet_id: int
    org_id: int
    org_name: str | None = None
    shop_id: int | None = None
    shop_name: str = ""
    shop_color: str | None = None
    accounting_period: int
    source_row_number: int
    sequence_no: str = ""
    live_room: str = ""
    live_date: str = ""
    merchant: str = ""
    borrow_total_amount: Decimal = Decimal("0")
    return_total_amount: Decimal = Decimal("0")
    business_fee_deduction: Decimal = Decimal("0")
    deduction_amount: Decimal = Decimal("0")
    payable_goods_amount: Decimal = Decimal("0")
    return_rate: str = ""
    settlement_subject: str = ""
    receipt_subject: str = ""
    cost_subject: str = ""
    payable_amount: Decimal = Decimal("0")
    subject_collection_amount: Decimal = Decimal("0")
    receipt_merchant: str = ""
    collection_merchant: str = ""
    is_settled: str = ""
    is_collected: str = ""
    remark: str = ""
    settlement_status: str = ""
    payment_screenshot: str = ""
    settlement_date: date | None = None
    collection_date: date | None = None
    deduction_remark: str = ""
    pending_issue: str = ""
    is_receipt_merchant_modified: str = ""
    is_receipt_amount_modified: str = ""
    modified_month: str = ""
    application_date: date | None = None
    paid_amount: Decimal = Decimal("0")
    borrow_minus_return: Decimal = Decimal("0")
    created_at: datetime

    @field_validator("live_date", mode="before")
    @classmethod
    def validate_live_date(cls, value: object) -> str:
        return _live_date_text(value)

    class Config:
        from_attributes = True


class MerchantBankFlowFileOut(BaseModel):
    id: int
    org_id: int
    org_name: str | None = None
    user_id: int
    accounting_year: int
    accounting_month: int
    accounting_period: int
    original_name: str
    file_size: int
    file_hash: str | None = None
    bank_name: str = ""
    account_name: str = ""
    status: str
    row_count: int = 0
    matched_row_count: int = 0
    error_message: str | None = None
    result_summary: dict | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MerchantBankFlowRowOut(BaseModel):
    id: int
    bank_flow_file_id: int
    org_id: int
    org_name: str | None = None
    accounting_period: int
    source_row_number: int
    bank_name: str = ""
    account_no: str = ""
    account_name: str = ""
    transaction_date: date | None = None
    transaction_time: datetime | None = None
    debit_amount: Decimal = Decimal("0")
    credit_amount: Decimal = Decimal("0")
    flow_amount: Decimal = Decimal("0")
    balance: Decimal = Decimal("0")
    counterparty_account_no: str = ""
    counterparty_name: str = ""
    counterparty_bank: str = ""
    summary: str = ""
    purpose: str = ""
    remark: str = ""
    live_date: str = ""
    transaction_flow_no: str = ""
    created_at: datetime

    class Config:
        from_attributes = True


class MerchantReconciliationSummaryOut(BaseModel):
    key: str
    org_id: int | None = None
    org_name: str | None = None
    accounting_year: int
    accounting_month: int
    our_subject: str = ""
    merchant_receipt_subject: str = ""
    gmv: Decimal = Decimal("0")
    merchant_payable_net_amount: Decimal = Decimal("0")
    opening_balance: Decimal = Decimal("0")
    business_fee_deduction: Decimal = Decimal("0")
    other_deduction_amount: Decimal = Decimal("0")
    payable_goods_balance: Decimal = Decimal("0")
    paid_flow_amount: Decimal = Decimal("0")
    unpaid_flow_amount: Decimal = Decimal("0")
    bank_flow_amount: Decimal = Decimal("0")
    bank_payment_diff: Decimal = Decimal("0")
    row_count: int = 0
    bank_status: str = "pending"


class MerchantReconciliationSummaryPageOut(BaseModel):
    items: list[MerchantReconciliationSummaryOut]
    total: int
    page: int
    page_size: int


class MerchantOpeningBalanceOut(BaseModel):
    id: int | None = None
    org_id: int
    org_name: str | None = None
    platform_code: str = "douyin"
    accounting_year: int
    accounting_month: int
    accounting_period: int
    our_subject: str = ""
    receipt_merchant: str = ""
    opening_balance: Decimal = Decimal("0")
    remark: str = ""
    updated_at: datetime | None = None


class MerchantOpeningBalanceUpsertItem(BaseModel):
    org_id: int = Field(..., ge=1)
    our_subject: str = Field(..., min_length=1, max_length=500)
    receipt_merchant: str = Field(..., min_length=1, max_length=500)
    opening_balance: Decimal = Field(Decimal("0"), decimal_places=2)
    remark: str | None = Field("", max_length=2000)

    @field_validator("our_subject", "receipt_merchant")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("不能为空")
        return stripped

    @field_validator("remark")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str:
        return value.strip() if value else ""


class MerchantOpeningBalanceBatchUpsert(BaseModel):
    accounting_year: int = Field(..., ge=2000, le=2100)
    accounting_month: int = Field(..., ge=1, le=12)
    platform_code: str = Field("douyin", min_length=1, max_length=50)
    items: list[MerchantOpeningBalanceUpsertItem] = Field(default_factory=list)

    @field_validator("platform_code")
    @classmethod
    def strip_platform_code(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("不能为空")
        return stripped


class MerchantOpeningBalanceBatchResult(BaseModel):
    created_count: int = 0
    updated_count: int = 0
    total_count: int = 0
