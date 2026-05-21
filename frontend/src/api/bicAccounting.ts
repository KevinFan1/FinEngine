import { downloadBlob, get, post } from "./index";
import type { PaginatedData } from "./index";
export interface BicTask {
    id: number;
    file_id: number;
    org_id: number;
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
export type BicExportScope = "all" | "current_page" | "selected";

export interface BicDetail {
    id: number;
    task_id: number;
    file_id: number;
    org_id: number;
    platform_code: string;
    shop_name: string;
    accounting_year: number;
    accounting_month: number;
    qic_warehouse: string;
    row_count: number;
    total_amount: string;
    created_at: string;
}

export interface BicReport {
    id: number;
    task_id: number;
    file_id: number;
    org_id: number;
    platform_code: string;
    shop_name: string;
    accounting_year: number;
    accounting_month: number;
    row_count: number;
    total_amount: string;
    created_at: string;
}

export interface BicTaskListParams {
    page?: number;
    page_size?: number;
    status?: string;
    platform_code?: string;
    shop_name?: string;
    accounting_start_year?: number;
    accounting_start_month?: number;
    accounting_end_year?: number;
    accounting_end_month?: number;
    keyword?: string;
}

export interface BicDetailListParams {
    page?: number;
    page_size?: number;
    task_id?: number;
    platform_code?: string;
    shop_name?: string;
    qic_warehouse?: string;
    accounting_year?: number;
    accounting_month?: number;
    accounting_start_year?: number;
    accounting_start_month?: number;
    accounting_end_year?: number;
    accounting_end_month?: number;
}

export interface BicReportListParams {
    page?: number;
    page_size?: number;
    task_id?: number;
    platform_code?: string;
    shop_name?: string;
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

export function listBicTasks(params: BicTaskListParams) {
    return get<PaginatedData<BicTask>>("/bic-accounting/tasks", params);
}

export function rerunBicTask(id: number) {
    return post<BicTask>(`/bic-accounting/tasks/${id}/run`);
}

export function listBicDetails(params: BicDetailListParams) {
    return get<PaginatedData<BicDetail>>("/bic-accounting/details", params);
}

export function exportBicDetailsExcel(params: BicDetailListParams & BicExportParams) {
    return downloadBlob("/bic-accounting/details/export", params);
}

export function listBicReports(params: BicReportListParams) {
    return get<PaginatedData<BicReport>>("/bic-accounting/summary", params);
}

export function exportBicReportsExcel(params: BicReportListParams & BicExportParams) {
    return downloadBlob("/bic-accounting/summary/export", params);
}
