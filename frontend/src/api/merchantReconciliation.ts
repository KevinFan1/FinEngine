import { downloadBlob, get, post } from "./index";
import type { PaginatedData } from "./index";

export interface MerchantRedSheet {
    id: number;
    org_id: number;
    org_name?: string | null;
    user_id: number;
    shop_id?: number | null;
    shop_name: string;
    shop_color?: string | null;
    platform_code: string;
    accounting_year: number;
    accounting_month: number;
    accounting_period: number;
    original_name: string;
    file_size: number;
    file_hash?: string | null;
    status: string;
    purchase_rows: number;
    payment_rows: number;
    error_message?: string | null;
    result_summary?: Record<string, any> | null;
    created_at: string;
    updated_at: string;
}

export interface MerchantRedSheetImportResult {
    red_sheet_id: number;
    purchase_rows: number;
    payment_rows: number;
    errors: string[];
    warnings?: string[];
}

export interface MerchantBankFlowImportResult {
    bank_flow_file_id: number;
    row_count: number;
    matched_row_count: number;
    errors: string[];
    warnings?: string[];
}

export interface MerchantReconciliationStats {
    total_gmv: string;
    total_bic: string;
    total_allocated_bic: string;
    total_insurance_fee: string;
    total_allocated_insurance_fee: string;
    total_live_amount: string;
    matched_rows: number;
    unmatched_rows: number;
}

export interface MerchantReconciliationDetail {
    id: number;
    org_id: number;
    org_name?: string | null;
    shop_id: number;
    shop_name: string;
    shop_color?: string | null;
    accounting_year: number;
    accounting_month: number;
    accounting_period: number;
    platform_code: string;
    platform_label: string;
    source_row_number: number;
    transaction_time: string;
    transaction_flow_no: string;
    transaction_direction: string;
    transaction_amount: string;
    transaction_scene: string;
    sub_order_no: string;
    order_no: string;
    order_time: string;
    product_id: string;
    product_code: string;
    product_name: string;
    author_name: string;
    gmv: string;
    allocated_bic: string;
    allocated_insurance_fee: string;
    live_amount: string;
    major_merchant_name: string;
    receipt_merchant: string;
    merchant_receipt_subject: string;
    live_room: string;
    live_date?: string | null;
    match_status: string;
    match_error: string;
}

export interface MerchantReconciliationDetailPage extends PaginatedData<MerchantReconciliationDetail> {
    stats: MerchantReconciliationStats;
}

export interface MerchantRedSheetPayment {
    id: number;
    red_sheet_id: number;
    org_id: number;
    org_name?: string | null;
    shop_id?: number | null;
    shop_name: string;
    shop_color?: string | null;
    accounting_period: number;
    source_row_number: number;
    sequence_no: string;
    live_room: string;
    live_date?: string | null;
    merchant: string;
    borrow_total_amount: string;
    return_total_amount: string;
    business_fee_deduction: string;
    deduction_amount: string;
    payable_goods_amount: string;
    return_rate: string;
    settlement_subject: string;
    receipt_subject: string;
    cost_subject: string;
    payable_amount: string;
    subject_collection_amount: string;
    receipt_merchant: string;
    collection_merchant: string;
    is_settled: string;
    is_collected: string;
    remark: string;
    settlement_status: string;
    payment_screenshot: string;
    settlement_date?: string | null;
    collection_date?: string | null;
    deduction_remark: string;
    pending_issue: string;
    is_receipt_merchant_modified: string;
    is_receipt_amount_modified: string;
    modified_month: string;
    application_date?: string | null;
    paid_amount: string;
    borrow_minus_return: string;
    created_at: string;
}

export interface MerchantRedSheetPurchase {
    id: number;
    red_sheet_id: number;
    org_id: number;
    org_name?: string | null;
    shop_id?: number | null;
    shop_name: string;
    shop_color?: string | null;
    accounting_period: number;
    source_row_number: number;
    live_room: string;
    merchant: string;
    live_date?: string | null;
    loan_return_order_no: string;
    loan_return_date?: string | null;
    live_code: string;
    normalized_live_code: string;
    match_status: string;
    remark: string;
    source_shop_name: string;
    subject: string;
    summary: string;
    product_name: string;
    piece_price: string;
    gram_price: string;
    sale_price: string;
    borrow_quantity: string;
    borrow_weight_g: string;
    borrow_amount: string;
    return_quantity: string;
    return_weight_g: string;
    return_amount: string;
    estimated_settlement_date?: string | null;
    labor_fee_per_gram: string;
    labor_fee_per_piece: string;
    created_at: string;
}

export interface MerchantBankFlowFile {
    id: number;
    org_id: number;
    org_name?: string | null;
    user_id: number;
    accounting_year: number;
    accounting_month: number;
    accounting_period: number;
    original_name: string;
    file_size: number;
    file_hash?: string | null;
    bank_name: string;
    account_name: string;
    status: string;
    row_count: number;
    matched_row_count: number;
    error_message?: string | null;
    result_summary?: Record<string, any> | null;
    created_at: string;
    updated_at: string;
}

export interface MerchantBankFlowRow {
    id: number;
    bank_flow_file_id: number;
    org_id: number;
    org_name?: string | null;
    accounting_period: number;
    source_row_number: number;
    bank_name: string;
    account_no: string;
    account_name: string;
    transaction_date?: string | null;
    transaction_time?: string | null;
    debit_amount: string;
    credit_amount: string;
    flow_amount: string;
    balance: string;
    counterparty_account_no: string;
    counterparty_name: string;
    counterparty_bank: string;
    summary: string;
    purpose: string;
    remark: string;
    live_date: string;
    transaction_flow_no: string;
    created_at: string;
}

export interface MerchantReconciliationSummary {
    key: string;
    org_id?: number | null;
    org_name?: string | null;
    accounting_year: number;
    accounting_month: number;
    our_subject: string;
    merchant_receipt_subject: string;
    gmv: string;
    merchant_payable_net_amount: string;
    opening_balance: string;
    business_fee_deduction: string;
    other_deduction_amount: string;
    payable_goods_balance: string;
    paid_flow_amount: string;
    unpaid_flow_amount: string;
    bank_flow_amount: string;
    bank_payment_diff: string;
    row_count: number;
    bank_status: string;
}

export interface MerchantOpeningBalance {
    id?: number | null;
    org_id: number;
    org_name?: string | null;
    platform_code: string;
    accounting_year: number;
    accounting_month: number;
    accounting_period: number;
    our_subject: string;
    receipt_merchant: string;
    opening_balance: string;
    remark: string;
    updated_at?: string | null;
}

export interface MerchantOpeningBalanceUpsertItem {
    org_id: number;
    our_subject: string;
    receipt_merchant: string;
    opening_balance: number | string;
    remark?: string;
}

export interface MerchantOpeningBalanceBatchUpsert {
    accounting_year: number;
    accounting_month: number;
    platform_code?: string;
    items: MerchantOpeningBalanceUpsertItem[];
}

export interface MerchantOpeningBalanceBatchResult {
    created_count: number;
    updated_count: number;
    total_count: number;
}

export interface MerchantRedSheetListParams {
    page?: number;
    page_size?: number;
    org_id?: number | string;
    shop_ids?: string;
    accounting_year?: number;
    accounting_month?: number;
    keyword?: string;
}

export interface MerchantReconciliationDetailParams {
    page?: number;
    page_size?: number;
    org_id?: number | string;
    accounting_year: number;
    accounting_month: number;
    shop_id: number;
    keyword?: string;
    match_status?: string;
    ids?: string;
}

export interface MerchantRedSheetDetailParams {
    page?: number;
    page_size?: number;
    org_id?: number | string;
    shop_ids?: string;
    accounting_year?: number;
    accounting_month?: number;
    keyword?: string;
}

export interface MerchantBankFlowListParams {
    page?: number;
    page_size?: number;
    org_id?: number | string;
    accounting_year?: number;
    accounting_month?: number;
    keyword?: string;
}

export interface MerchantReconciliationSummaryParams {
    page?: number;
    page_size?: number;
    org_id?: number | string;
    accounting_year: number;
    accounting_month: number;
    shop_id?: number;
    keyword?: string;
    bank_status?: string;
}

export interface MerchantReconciliationSummaryDrilldownParams {
    page?: number;
    page_size?: number;
    org_id?: number | string;
    accounting_year: number;
    accounting_month: number;
    shop_id?: number;
    summary_org_id?: number | null;
    our_subject: string;
    merchant_receipt_subject: string;
}

export type MerchantReconciliationExportScope = "all" | "current_page" | "selected";

export function downloadRedSheetTemplate(params: { accounting_year: number; accounting_month: number }) {
    return downloadBlob("/merchant-reconciliation/red-sheet-template", params);
}

export function listMerchantRedSheets(params: MerchantRedSheetListParams) {
    return get<PaginatedData<MerchantRedSheet>>("/merchant-reconciliation/red-sheets", params);
}

export function listMerchantBankFlowFiles(params: MerchantBankFlowListParams) {
    return get<PaginatedData<MerchantBankFlowFile>>("/merchant-reconciliation/bank-flow-files", params);
}

export function listMerchantBankFlowRows(params: MerchantBankFlowListParams) {
    return get<PaginatedData<MerchantBankFlowRow>>("/merchant-reconciliation/bank-flow-rows", params);
}

export function listMerchantReconciliationDetails(params: MerchantReconciliationDetailParams) {
    return get<MerchantReconciliationDetailPage>("/merchant-reconciliation/details", params);
}

export function exportMerchantReconciliationDetails(params: MerchantReconciliationDetailParams & { scope?: MerchantReconciliationExportScope }) {
    return downloadBlob("/merchant-reconciliation/details/export", params);
}

export function listMerchantRedSheetPayments(params: MerchantRedSheetDetailParams) {
    return get<PaginatedData<MerchantRedSheetPayment>>("/merchant-reconciliation/payments", params);
}

export function listMerchantRedSheetPurchases(params: MerchantRedSheetDetailParams) {
    return get<PaginatedData<MerchantRedSheetPurchase>>("/merchant-reconciliation/purchases", params);
}

export function listMerchantReconciliationSummary(params: MerchantReconciliationSummaryParams) {
    return get<PaginatedData<MerchantReconciliationSummary>>("/merchant-reconciliation/summary", params);
}

export function exportMerchantReconciliationSummary(params: MerchantReconciliationSummaryParams) {
    return downloadBlob("/merchant-reconciliation/summary/export", params);
}

export function listMerchantReconciliationSummaryDetails(params: MerchantReconciliationSummaryDrilldownParams) {
    return get<PaginatedData<MerchantReconciliationDetail>>("/merchant-reconciliation/summary/details", params);
}

export function listMerchantReconciliationSummaryPayments(params: MerchantReconciliationSummaryDrilldownParams) {
    return get<PaginatedData<MerchantRedSheetPayment>>("/merchant-reconciliation/summary/payments", params);
}

export function listMerchantReconciliationSummaryPurchases(params: MerchantReconciliationSummaryDrilldownParams) {
    return get<PaginatedData<MerchantRedSheetPurchase>>("/merchant-reconciliation/summary/purchases", params);
}

export function listMerchantReconciliationSummaryBankFlows(params: MerchantReconciliationSummaryDrilldownParams) {
    return get<PaginatedData<MerchantBankFlowRow>>("/merchant-reconciliation/summary/bank-flow-rows", params);
}

export function listMerchantOpeningBalances(params: Omit<MerchantReconciliationSummaryParams, "page" | "page_size" | "bank_status">) {
    return get<MerchantOpeningBalance[]>("/merchant-reconciliation/summary/opening-balances", params);
}

export function upsertMerchantOpeningBalances(data: MerchantOpeningBalanceBatchUpsert) {
    return post<MerchantOpeningBalanceBatchResult>("/merchant-reconciliation/summary/opening-balances", data);
}
