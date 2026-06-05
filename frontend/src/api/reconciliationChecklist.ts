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

export interface ReconciliationChecklistSummary {
    key: string;
    org_id: number;
    org_name?: string | null;
    accounting_year: number;
    accounting_month: number;
    accounting_period: number;
    merchant_id?: number | null;
    live_promoter_id?: number | null;
    receipt_merchant_id?: number | null;
    merchant_name: string;
    live_promoter: string;
    receipt_merchant: string;
    product_quantity: number;
    total_order_amount: string;
    total_live_commission: string;
    total_merchant_net_amount: string;
}

export interface ReconciliationChecklistSummaryDetail {
    product_name: string;
    product_quantity: number;
    total_order_amount: string;
    total_live_commission: string;
    total_merchant_net_amount: string;
}

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
    keyword?: string;
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

export function listReconciliationChecklistTasks(params: ReconciliationChecklistTaskParams) {
    return get<PaginatedData<ReconciliationChecklistTask>>("/reconciliation-checklist/tasks", params);
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
