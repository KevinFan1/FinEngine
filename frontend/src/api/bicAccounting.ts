import { downloadBlob, get, post } from "./index";
import type { PaginatedData } from "./index";
export interface BicTask {
    id: number;
    file_id: number;
    org_id: number;
    org_name?: string | null;
    user_id: number;
    source_upload_file_id?: number | null;
    original_name?: string | null;
    platform_code?: string | null;
    shop_name?: string | null;
    accounting_year?: number | null;
    accounting_month?: number | null;
    celery_task_id?: string | null;
    status: string;
    progress: number;
    processed_rows: number;
    success_rows: number;
    failed_rows: number;
    result_success?: number | null;
    result_failed?: number | null;
    error_message?: string | null;
    error_reason?: string | null;
    result_summary?: Record<string, any> | null;
    started_at?: string | null;
    finished_at?: string | null;
    created_at: string;
    updated_at: string;
}

export interface BicTaskBatchActionResult {
    total: number;
    success_count: number;
    failed_count: number;
    success_ids: number[];
    failed_items: Array<{
        task_id: number;
        message: string;
    }>;
}

export type BicExportScope = "all" | "current_page" | "selected";
export type BicSourceExportScope = "current_page" | "selected";
export const BIC_EXCEL_EXPORT_ROW_LIMIT = 20000;

export interface BicDetail {
    id: number;
    task_id: number;
    file_id: number;
    org_id: number;
    org_name?: string | null;
    shop_id?: number | null;
    platform_code: string;
    store_short_id?: string | null;
    service_provider: string;
    shop_name: string;
    accounting_year: number;
    accounting_month: number;
    qic_warehouse: string;
    row_count?: number;
    merchant?: string | null;
    tax_no?: string | null;
    shop_type?: string | null;
    registered_address?: string | null;
    total_amount: string;
    created_at: string;
}

export interface BicSourceRow {
    id: number;
    task_id: number;
    file_id: number;
    detail_id: number;
    org_id: number;
    org_name?: string | null;
    shop_id?: number | null;
    platform_code: string;
    store_short_id?: string | null;
    service_provider: string;
    shop_name: string;
    accounting_year: number;
    accounting_month: number;
    qic_warehouse: string;
    source_row_number: number;
    settlement_no: string;
    order_code: string;
    related_order_no: string;
    related_waybill_no: string;
    fee_item: string;
    settlement_amount: string;
    billing_params: string;
    billing_completed_time: string;
    business_node: string;
    business_occurred_time: string;
    settled_at: string;
    status: string;
    transaction_account: string;
    transaction_flow_no: string;
    remark: string;
    is_mudaibao: string;
    is_child_order: string;
    created_at: string;
}

export interface BicTaskListParams {
    page?: number;
    page_size?: number;
    org_id?: number | string;
    status?: string;
    platform_code?: string;
    shop_name?: string;
    shop_ids?: string;
    accounting_start_year?: number;
    accounting_start_month?: number;
    accounting_end_year?: number;
    accounting_end_month?: number;
    keyword?: string;
    created_start_time?: string;
    created_end_time?: string;
}

export interface BicDetailListParams {
    page?: number;
    page_size?: number;
    org_id?: number | string;
    task_id?: number;
    platform_code?: string;
    shop_name?: string;
    service_provider?: string;
    qic_warehouse?: string;
    accounting_year?: number;
    accounting_month?: number;
    accounting_start_year?: number;
    accounting_start_month?: number;
    accounting_end_year?: number;
    accounting_end_month?: number;
}

export interface BicSourceRowListParams {
    page?: number;
    page_size?: number;
    org_id?: number | string;
    detail_id?: number;
    task_id?: number;
    platform_code?: string;
    shop_name?: string;
    shop_ids?: string;
    service_provider?: string;
    qic_warehouse?: string;
    accounting_year?: number;
    accounting_month?: number;
    accounting_start_year?: number;
    accounting_start_month?: number;
    accounting_end_year?: number;
    accounting_end_month?: number;
}

export interface BicExportParams {
    scope?: BicExportScope;
    ids?: string;
    page?: number;
    page_size?: number;
}

export interface BicSourceExportParams {
    scope?: BicSourceExportScope;
    ids?: string;
    page?: number;
    page_size?: number;
}

export function listBicTasks(params: BicTaskListParams) {
    return get<PaginatedData<BicTask>>("/bic-accounting/tasks", params);
}

export function rerunBicTask(id: number) {
    return post<BicTask>(`/bic-accounting/tasks/${id}/run`);
}

export function batchRecalculateBicTasks(taskIds: number[]) {
    return post<BicTaskBatchActionResult>(
        "/bic-accounting/tasks/batch/recalculate",
        { task_ids: taskIds },
    );
}

export function listBicDetails(params: BicDetailListParams) {
    return get<PaginatedData<BicDetail>>("/bic-accounting/details", params);
}

export function exportBicDetailsExcel(params: BicDetailListParams & BicExportParams) {
    return downloadBlob("/bic-accounting/details/export", params);
}

export function listBicSourceRows(params: BicSourceRowListParams) {
    if (params.detail_id) {
        const { detail_id, ...query } = params;
        return get<PaginatedData<BicSourceRow>>(`/bic-accounting/details/${detail_id}/source-rows`, query);
    }
    return get<PaginatedData<BicSourceRow>>("/bic-accounting/source-rows", params);
}

export function exportBicSourceRowsExcel(params: BicSourceRowListParams & BicSourceExportParams) {
    return downloadBlob("/bic-accounting/source-rows/export", params);
}

export function exportBicReconciliationExcel(params: {
    accounting_year: number;
    accounting_month: number;
    service_provider: string;
    platform_code?: string;
    shop_name?: string;
    shop_id?: number;
    qic_warehouse?: string;
    org_id?: number | string;
}) {
    return downloadBlob("/bic-accounting/reconciliation/export", params);
}
