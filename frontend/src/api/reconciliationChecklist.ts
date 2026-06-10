import { get, post } from "./index";
import type { PaginatedData } from "./index";

export interface ReconciliationChecklistTask {
    id: number;
    file_id: number;
    org_id: number;
    org_name?: string | null;
    user_id: number;
    source_upload_file_id?: number | null;
    original_name: string;
    celery_task_id?: string | null;
    task_type: string;
    status: string;
    progress: number;
    total_rows: number;
    success_rows: number;
    failed_rows: number;
    inserted_rows: number;
    updated_rows: number;
    error_message?: string | null;
    result_summary?: Record<string, any> | null;
    started_at?: string | null;
    finished_at?: string | null;
    created_at: string;
    updated_at: string;
}

export interface ReconciliationChecklistProductSummary {
    key: string;
    org_id: number;
    org_name?: string | null;
    accounting_year: number;
    accounting_month: number;
    accounting_period: number;
    receipt_merchant: string;
    merchant_subject_name: string;
    product_name: string;
    product_quantity: number;
    total_user_paid_amount: string;
    total_live_commission: string;
    total_merchant_net_amount: string;
}

export interface ReconciliationChecklistReceiptSummary {
    key: string;
    org_id: number;
    org_name?: string | null;
    accounting_year: number;
    accounting_month: number;
    accounting_period: number;
    merchant_subject_name: string;
    live_platform: string;
    receipt_merchant: string;
    order_count: number;
    total_user_paid_amount: string;
    total_live_commission: string;
    total_merchant_net_amount: string;
}

export interface ReconciliationChecklistPayableBalanceSummary {
    key: string;
    org_id: number;
    org_name?: string | null;
    accounting_year: number;
    accounting_month: number;
    accounting_period: number;
    merchant_subject_name: string;
    receipt_merchant: string;
    total_user_paid_amount: string;
    total_merchant_net_amount: string;
    total_payment_amount: string;
    total_merchant_net_balance: string;
}

export type ReconciliationChecklistSummary = ReconciliationChecklistProductSummary;
export type ReconciliationChecklistSummaryDetail = ReconciliationChecklistProductSummary;

export interface ReconciliationChecklistTaskParams {
    page?: number;
    page_size?: number;
    org_id?: number | string;
    status?: string;
    keyword?: string;
}

export interface ReconciliationChecklistSummaryParams {
    page?: number;
    page_size?: number;
    org_id?: number | string;
    accounting_year?: number;
    accounting_month?: number;
    accounting_start_year?: number;
    accounting_start_month?: number;
    accounting_end_year?: number;
    accounting_end_month?: number;
    shop_ids?: string;
    merchant_name?: string;
    live_promoter?: string;
    receipt_merchant?: string;
    merchant_ids?: string;
    live_promoter_ids?: string;
    receipt_merchant_ids?: string;
    merchant_subject_name?: string;
    product_name?: string;
    live_platform?: string;
    keyword?: string;
}

export interface ReconciliationChecklistOption {
    label: string;
    value: string;
}

export interface ReconciliationChecklistEntityOption {
    id: number;
    org_id: number;
    parent_id?: number | null;
    platform_code: string;
    entity_type: "live_promoter" | "merchant" | "receipt_merchant";
    name: string;
}

export interface ReconciliationChecklistTaskBatchActionResult {
    total: number;
    success_count: number;
    failed_count: number;
    success_ids: number[];
    failed_items: Array<{
        task_id: number;
        message: string;
    }>;
}

export interface ReconciliationChecklistTaskSourceDownload {
    download_url: string;
    filename: string;
    expires_seconds: number;
}

export interface ReconciliationChecklistDashboardMonthlyMetric {
    month: number;
    task_count: number;
}

export interface ReconciliationChecklistDashboardMonthlyAmount {
    month: number;
    total_user_paid_amount: string;
}

export interface ReconciliationChecklistDashboardMerchant {
    merchant_name: string;
    total_user_paid_amount: string;
}

export interface ReconciliationChecklistDashboardRecentTask {
    id: number;
    original_name: string;
    status: string;
    total_rows: number;
    success_rows: number;
    failed_rows: number;
    inserted_rows: number;
    finished_at?: string | null;
}

export interface ReconciliationChecklistDashboardMetrics {
    processed_task_count: number;
    total_task_count: number;
    failed_task_count: number;
    total_rows: number;
    total_user_paid_amount: string;
    merchant_count: number;
    covered_month_count: number;
    completion_rate: string;
    year: number;
    monthly_task_counts: ReconciliationChecklistDashboardMonthlyMetric[];
    monthly_user_paid_amounts: ReconciliationChecklistDashboardMonthlyAmount[];
    top_merchants: ReconciliationChecklistDashboardMerchant[];
    recent_tasks: ReconciliationChecklistDashboardRecentTask[];
}

export interface ReconciliationChecklistManualEditQueryParams {
    org_id: number;
    sub_order_nos: string[];
}

export interface ReconciliationChecklistInvoiceEditItem {
    unique_id?: string;
    sub_order_no: string;
    settlement_time?: string | null;
    platform_subsidy?: string | null;
    talent_subsidy?: string | null;
    douyin_pay_subsidy?: string | null;
    douyin_monthly_pay_subsidy?: string | null;
    bank_subsidy?: string | null;
    user_paid_amount?: string | null;
    platform_service_fee?: string | null;
    talent_commission?: string | null;
    investment_service_fee?: string | null;
    receipt_merchant: string;
    invoice_time?: string | null;
    invoice_number: string;
}

export interface ReconciliationChecklistMerchantEditItem {
    unique_id?: string;
    sub_order_no: string;
    settlement_time?: string | null;
    platform_subsidy?: string | null;
    talent_subsidy?: string | null;
    douyin_pay_subsidy?: string | null;
    douyin_monthly_pay_subsidy?: string | null;
    bank_subsidy?: string | null;
    user_paid_amount?: string | null;
    platform_service_fee?: string | null;
    talent_commission?: string | null;
    investment_service_fee?: string | null;
    receipt_merchant: string;
    merchant_net_amount?: string | null;
    payment_amount?: string | null;
    merchant_payment_time?: string | null;
}

export interface ReconciliationChecklistManualEditQueryResult<T> {
    matched_items: T[];
    missing_sub_order_nos: string[];
}

export interface ReconciliationChecklistManualEditSaveResult {
    success_count: number;
    failed_count: number;
    unchanged_count: number;
    missing_sub_order_nos: string[];
    affected_periods: number[];
    error_messages: string[];
}

export interface ReconciliationChecklistManualEditUploadFile {
    id: number;
    org_id: number;
    user_id: number;
    original_name: string;
    oss_key: string;
    file_size: number;
    file_hash?: string | null;
    status: string;
}

export interface ReconciliationChecklistManualEditOssCredential {
    file_id: number;
    access_key_id: string;
    access_key_secret: string;
    security_token: string;
    expiration: string;
    region: string;
    bucket: string;
    endpoint: string;
    oss_key_prefix: string;
}

export interface ReconciliationChecklistManualEditUploadInitResponse {
    file: ReconciliationChecklistManualEditUploadFile;
    upload: ReconciliationChecklistManualEditOssCredential;
}

export interface ReconciliationChecklistManualEditUploadTask {
    task_id: number;
    status: string;
}

export function listReconciliationChecklistTasks(params: ReconciliationChecklistTaskParams) {
    return get<PaginatedData<ReconciliationChecklistTask>>("/reconciliation-checklist/tasks", params);
}

export function queryReconciliationChecklistInvoiceEdits(
    data: ReconciliationChecklistManualEditQueryParams,
) {
    return post<ReconciliationChecklistManualEditQueryResult<ReconciliationChecklistInvoiceEditItem>>(
        "/reconciliation-checklist/invoice-edits/query",
        data,
    );
}

export function saveReconciliationChecklistInvoiceEdits(data: {
    org_id: number;
    items: ReconciliationChecklistInvoiceEditItem[];
}) {
    return post<ReconciliationChecklistManualEditSaveResult>(
        "/reconciliation-checklist/invoice-edits/save",
        data,
    );
}

export function uploadReconciliationChecklistInvoiceEdits(data: {
    org_id: number;
    original_name: string;
    file_size: number;
}) {
    return post<ReconciliationChecklistManualEditUploadInitResponse>(
        "/reconciliation-checklist/invoice-edits/upload-init",
        data,
    );
}

export function callbackReconciliationChecklistInvoiceEditsUpload(data: {
    file_id: number;
    oss_key: string;
    file_size: number;
    file_hash?: string;
}) {
    return post<ReconciliationChecklistManualEditUploadTask>(
        "/reconciliation-checklist/invoice-edits/upload-callback",
        data,
    );
}

export function queryReconciliationChecklistMerchantEdits(
    data: ReconciliationChecklistManualEditQueryParams,
) {
    return post<ReconciliationChecklistManualEditQueryResult<ReconciliationChecklistMerchantEditItem>>(
        "/reconciliation-checklist/merchant-edits/query",
        data,
    );
}

export function saveReconciliationChecklistMerchantEdits(data: {
    org_id: number;
    items: ReconciliationChecklistMerchantEditItem[];
}) {
    return post<ReconciliationChecklistManualEditSaveResult>(
        "/reconciliation-checklist/merchant-edits/save",
        data,
    );
}

export function uploadReconciliationChecklistMerchantEdits(data: {
    org_id: number;
    original_name: string;
    file_size: number;
}) {
    return post<ReconciliationChecklistManualEditUploadInitResponse>(
        "/reconciliation-checklist/merchant-edits/upload-init",
        data,
    );
}

export function callbackReconciliationChecklistMerchantEditsUpload(data: {
    file_id: number;
    oss_key: string;
    file_size: number;
    file_hash?: string;
}) {
    return post<ReconciliationChecklistManualEditUploadTask>(
        "/reconciliation-checklist/merchant-edits/upload-callback",
        data,
    );
}

export function getReconciliationChecklistDashboardMetrics(params?: {
    year?: number;
    org_id?: number | string;
}) {
    return get<ReconciliationChecklistDashboardMetrics>("/reconciliation-checklist/dashboard-metrics", params);
}

export function retryReconciliationChecklistTask(taskId: number) {
    return post<{ task_id: number; status: string }>(`/reconciliation-checklist/tasks/${taskId}/run`);
}

export function batchRecalculateReconciliationChecklistTasks(taskIds: number[]) {
    return post<ReconciliationChecklistTaskBatchActionResult>(
        "/reconciliation-checklist/tasks/batch/recalculate",
        { task_ids: taskIds },
    );
}

export function getReconciliationChecklistTaskSourceDownload(taskId: number) {
    return post<ReconciliationChecklistTaskSourceDownload>(`/reconciliation-checklist/tasks/${taskId}/source-download`);
}

export function listReconciliationChecklistSummary(params: ReconciliationChecklistSummaryParams) {
    return get<PaginatedData<ReconciliationChecklistSummary>>("/reconciliation-checklist/summary", params);
}

export function listReconciliationChecklistProductSummary(params: ReconciliationChecklistSummaryParams) {
    return get<PaginatedData<ReconciliationChecklistProductSummary>>("/reconciliation-checklist/product-summary", params);
}

export function listReconciliationChecklistReceiptSummary(params: ReconciliationChecklistSummaryParams) {
    return get<PaginatedData<ReconciliationChecklistReceiptSummary>>("/reconciliation-checklist/receipt-summary", params);
}

export function listReconciliationChecklistPayableBalanceSummary(params: ReconciliationChecklistSummaryParams) {
    return get<PaginatedData<ReconciliationChecklistPayableBalanceSummary>>("/reconciliation-checklist/payable-balance-summary", params);
}

export function listReconciliationChecklistOptions(params: {
    kind: "merchant_subject" | "receipt_merchant" | "live_platform" | "product_name";
    accounting_year?: number;
    accounting_month?: number;
    org_id?: number | string;
    keyword?: string;
    limit?: number;
}) {
    return get<ReconciliationChecklistOption[]>("/reconciliation-checklist/options", params);
}

export function listReconciliationChecklistSummaryDetails(
    params: ReconciliationChecklistSummaryParams & {
        accounting_year: number;
        accounting_month: number;
        merchant_name: string;
        live_promoter: string;
        receipt_merchant: string;
    },
) {
    return get<PaginatedData<ReconciliationChecklistSummaryDetail>>("/reconciliation-checklist/summary/details", params);
}

export function listReconciliationChecklistEntityOptions(params: {
    entity_type: ReconciliationChecklistEntityOption["entity_type"];
    accounting_year: number;
    accounting_month: number;
    org_id?: number | string;
    parent_ids?: string;
    keyword?: string;
    limit?: number;
}) {
    return get<ReconciliationChecklistEntityOption[]>("/reconciliation-checklist/entities/options", params);
}
