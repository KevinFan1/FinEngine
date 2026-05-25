import { del, downloadBlob, get, post, put } from "./index";
import type { PaginatedData } from "./index";

export interface TransactionMajorCategory {
    id: number;
    name: string;
    sort_order: number;
    status: number;
    created_at: string;
    updated_at: string;
}

export interface TransactionCashFlowItem {
    id: number;
    code: string;
    name: string;
    parent_id?: number | null;
    parent_name?: string | null;
    sort_order: number;
}

export interface TransactionSubject {
    id: number;
    name: string;
    account_type: string;
    major_category_id?: number | null;
    major_category_name?: string | null;
    cash_flow_item_id?: number | null;
    cash_flow_item_name?: string | null;
    sort_order: number;
    status: number;
    created_at: string;
    updated_at: string;
}

export interface TransactionCategory {
    id: number;
    subject_id: number;
    name: string;
    sort_order: number;
    status: number;
    created_at: string;
    updated_at: string;
}

export interface TransactionRule {
    id: number;
    subject_id: number;
    category_id: number;
    platform_code?: string | null;
    transaction_direction: string;
    transaction_scene?: string | null;
    remark_field: string;
    direction_field: string;
    match_type: "none" | "exact" | "contains" | "not_contains";
    remark_pattern: string;
    remark_exclude_pattern: string;
    amount_field: string;
    result_direction: "original" | "positive" | "negative" | "directional";
    priority: number;
    status: number;
    subject_name?: string | null;
    category_name?: string | null;
    reclassification_name?: string | null;
    created_at: string;
    updated_at: string;
}

export interface TransactionUploadFile {
    id: number;
    org_id: number;
    org_name?: string | null;
    user_id: number;
    original_name: string;
    oss_key: string;
    file_size: number;
    file_hash?: string | null;
    platform_code?: string | null;
    shop_name?: string | null;
    accounting_year?: number | null;
    accounting_month?: number | null;
    status: string;
    error_message?: string | null;
    created_at: string;
    updated_at: string;
}

export interface TransactionOssCredential {
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

export interface TransactionUploadInitResponse {
    file: TransactionUploadFile;
    upload: TransactionOssCredential;
}

export interface TransactionTask {
    id: number;
    file_id: number;
    org_id: number;
    org_name?: string | null;
    user_id: number;
    celery_task_id?: string | null;
    status: string;
    progress: number;
    total_rows: number;
    matched_rows: number;
    unmatched_rows: number;
    failed_rows: number;
    error_message?: string | null;
    result_summary?: Record<string, any> | null;
    original_name?: string | null;
    platform_code?: string | null;
    shop_name?: string | null;
    accounting_year?: number | null;
    accounting_month?: number | null;
    started_at?: string | null;
    finished_at?: string | null;
    created_at: string;
    updated_at: string;
}

export interface TransactionTaskBatchActionResult {
    total: number;
    success_count: number;
    failed_count: number;
    success_ids: number[];
    failed_items: Array<{
        task_id: number;
        message: string;
    }>;
}

export interface TransactionDetail {
    id: number;
    task_id: number;
    file_id: number;
    org_id: number;
    org_name?: string | null;
    major_category_id?: number | null;
    major_category_name?: string | null;
    subject_id?: number | null;
    category_id?: number | null;
    rule_id?: number | null;
    row_number: number;
    platform_code?: string | null;
    shop_name?: string | null;
    upload_accounting_year?: number | null;
    upload_accounting_month?: number | null;
    accounting_year?: number | null;
    accounting_month?: number | null;
    transaction_direction?: string | null;
    remark?: string | null;
    amount_field?: string | null;
    original_amount: string;
    calculated_amount: string;
    status: "matched" | "unmatched" | "failed";
    error_message?: string | null;
    raw_row: Record<string, any>;
    subject_name?: string | null;
    category_name?: string | null;
    reclassification_name?: string | null;
    cash_flow_group_name?: string | null;
    total_amount?: string | null;
    created_at: string;
}

export interface TransactionSummary {
    id: number;
    task_id: number;
    file_id: number;
    org_id: number;
    org_name?: string | null;
    major_category_id?: number | null;
    major_category_name?: string | null;
    subject_id: number;
    category_id: number;
    subject_name: string;
    category_name: string;
    reclassification_name?: string | null;
    transaction_direction?: string | null;
    platform_code?: string | null;
    shop_name?: string | null;
    upload_accounting_year?: number | null;
    upload_accounting_month?: number | null;
    accounting_year?: number | null;
    accounting_month?: number | null;
    cash_flow_group_name?: string | null;
    row_count: number;
    total_amount: string;
    created_at: string;
}

export interface TransactionAnnualSummaryRow {
    code: string;
    name: string;
    parent_code?: string | null;
    level: number;
    item_type: string;
    flow_section: string;
    flow_direction?: string | null;
    summary_method: string;
    months: Record<string, string>;
    total_amount: string;
}

export interface TransactionAnnualSummary {
    year: number;
    months: string[];
    rows: TransactionAnnualSummaryRow[];
}

export interface TransactionTaskListParams {
    page?: number;
    page_size?: number;
    org_id?: number | string;
    status?: string;
    platform_code?: string;
    shop_name?: string;
    accounting_year?: number;
    accounting_month?: number;
    accounting_start_year?: number;
    accounting_start_month?: number;
    accounting_end_year?: number;
    accounting_end_month?: number;
    keyword?: string;
}

export interface TransactionDetailListParams {
    page?: number;
    page_size?: number;
    org_id?: number | string;
    task_id?: number;
    status?: string;
    platform_code?: string;
    shop_name?: string;
    major_category_id?: number | string;
    subject_id?: number | string;
    category_id?: number | string;
    transaction_direction?: string;
    accounting_year?: number;
    accounting_month?: number;
    accounting_start_year?: number;
    accounting_start_month?: number;
    accounting_end_year?: number;
    accounting_end_month?: number;
    upload_accounting_year?: number;
    upload_accounting_month?: number;
    upload_accounting_start_year?: number;
    upload_accounting_start_month?: number;
    upload_accounting_end_year?: number;
    upload_accounting_end_month?: number;
    keyword?: string;
}

export interface TransactionSummaryListParams {
    page?: number;
    page_size?: number;
    org_id?: number | string;
    task_id?: number;
    platform_code?: string;
    shop_name?: string;
    major_category_id?: number | string;
    subject_id?: number | string;
    category_id?: number | string;
    transaction_direction?: string;
    accounting_year?: number;
    accounting_month?: number;
    accounting_start_year?: number;
    accounting_start_month?: number;
    accounting_end_year?: number;
    accounting_end_month?: number;
    upload_accounting_year?: number;
    upload_accounting_month?: number;
    upload_accounting_start_year?: number;
    upload_accounting_start_month?: number;
    upload_accounting_end_year?: number;
    upload_accounting_end_month?: number;
    keyword?: string;
}

export interface TransactionAnnualSummaryParams {
    year: number;
    org_id?: number | string;
    task_id?: number;
    platform_code?: string;
    shop_name?: string;
    major_category_id?: number | string;
    subject_id?: number | string;
    category_id?: number | string;
    transaction_direction?: string;
    upload_accounting_year?: number;
    upload_accounting_month?: number;
    upload_accounting_start_year?: number;
    upload_accounting_start_month?: number;
    upload_accounting_end_year?: number;
    upload_accounting_end_month?: number;
    keyword?: string;
}

export type TransactionExportScope = "all" | "current_page" | "selected";

export interface TransactionExportParams {
    scope?: TransactionExportScope;
    ids?: string;
    page?: number;
    page_size?: number;
}

export function listTransactionSubjects() {
    return get<TransactionSubject[]>("/transaction-accounting/subjects");
}

export function listTransactionMajorCategories() {
    return get<TransactionMajorCategory[]>("/transaction-accounting/major-categories");
}

export function createTransactionMajorCategory(data: Partial<TransactionMajorCategory>) {
    return post<TransactionMajorCategory>("/transaction-accounting/major-categories", data);
}

export function updateTransactionMajorCategory(id: number, data: Partial<TransactionMajorCategory>) {
    return put<TransactionMajorCategory>(`/transaction-accounting/major-categories/${id}`, data);
}

export function deleteTransactionMajorCategory(id: number) {
    return del<null>(`/transaction-accounting/major-categories/${id}`);
}

export function listTransactionCashFlowItems() {
    return get<TransactionCashFlowItem[]>("/transaction-accounting/cash-flow-items");
}

export function createTransactionSubject(data: Partial<TransactionSubject>) {
    return post<TransactionSubject>("/transaction-accounting/subjects", data);
}

export function updateTransactionSubject(id: number, data: Partial<TransactionSubject>) {
    return put<TransactionSubject>(`/transaction-accounting/subjects/${id}`, data);
}

export function deleteTransactionSubject(id: number) {
    return del<null>(`/transaction-accounting/subjects/${id}`);
}

export function listTransactionCategories(subjectId?: number) {
    return get<TransactionCategory[]>("/transaction-accounting/categories", subjectId ? { subject_id: subjectId } : undefined);
}

export function createTransactionCategory(data: Partial<TransactionCategory>) {
    return post<TransactionCategory>("/transaction-accounting/categories", data);
}

export function updateTransactionCategory(id: number, data: Partial<TransactionCategory>) {
    return put<TransactionCategory>(`/transaction-accounting/categories/${id}`, data);
}

export function deleteTransactionCategory(id: number) {
    return del<null>(`/transaction-accounting/categories/${id}`);
}

export function listTransactionRules() {
    return get<TransactionRule[]>("/transaction-accounting/rules");
}

export function createTransactionRule(data: Partial<TransactionRule>) {
    return post<TransactionRule>("/transaction-accounting/rules", data);
}

export function updateTransactionRule(id: number, data: Partial<TransactionRule>) {
    return put<TransactionRule>(`/transaction-accounting/rules/${id}`, data);
}

export function deleteTransactionRule(id: number) {
    return del<null>(`/transaction-accounting/rules/${id}`);
}

export function initTransactionUpload(data: {
    original_name: string;
    file_size: number;
    platform_code?: string;
    shop_name?: string;
    accounting_year?: number;
    accounting_month?: number;
}, orgId?: number) {
    const url = orgId
        ? `/transaction-accounting/upload-init?org_id=${orgId}`
        : "/transaction-accounting/upload-init";
    return post<TransactionUploadInitResponse>(url, data);
}

export function callbackTransactionUpload(data: {
    file_id: number;
    oss_key: string;
    file_size: number;
    file_hash?: string;
}) {
    return post<TransactionTask>("/transaction-accounting/upload-callback", data);
}

export function listTransactionTasks(params: TransactionTaskListParams) {
    return get<PaginatedData<TransactionTask>>("/transaction-accounting/tasks", params);
}

export function rerunTransactionTask(id: number) {
    return post<TransactionTask>(`/transaction-accounting/tasks/${id}/run`);
}

export function batchRecalculateTransactionTasks(taskIds: number[]) {
    return post<TransactionTaskBatchActionResult>(
        "/transaction-accounting/tasks/batch/recalculate",
        { task_ids: taskIds },
    );
}

export function listTransactionDetails(params: TransactionDetailListParams) {
    return get<PaginatedData<TransactionDetail>>("/transaction-accounting/details", params);
}

export function listTransactionSummary(params: TransactionSummaryListParams) {
    return get<PaginatedData<TransactionSummary>>("/transaction-accounting/summary", params);
}

export function getTransactionAnnualSummary(params: TransactionAnnualSummaryParams) {
    return get<TransactionAnnualSummary>("/transaction-accounting/summary/annual", params);
}

export function exportTransactionDetailsExcel(params: TransactionDetailListParams & TransactionExportParams) {
    return downloadBlob("/transaction-accounting/details/export", params);
}

export function exportTransactionSummaryExcel(params: TransactionSummaryListParams & TransactionExportParams) {
    return downloadBlob("/transaction-accounting/summary/export", params);
}

export function exportTransactionAnnualSummaryExcel(params: TransactionAnnualSummaryParams) {
    return downloadBlob("/transaction-accounting/summary/annual/export", params);
}
