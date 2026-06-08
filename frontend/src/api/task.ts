import { get, post } from "./index";
import type { PaginatedData } from "./index";

export interface Task {
    id: number;
    org_id: number;
    org_name?: string | null;
    file_id?: number;
    batch_id?: number | null;
    filename?: string | null;
    platform?: string | null;
    source_platform_code?: string | null;
    report_platform_code?: string | null;
    shop_id?: number | null;
    shop_name?: string | null;
    shop_color?: string | null;
    parsed_type?: string;
    parsed_year?: number;
    parsed_month?: number;
    status: string;
    progress: number;
    processed_rows?: number;
    success_rows?: number;
    failed_rows?: number;
    result_success?: number;
    result_failed?: number;
    error_message: string | null;
    error_reason: string | null;
    action_expired?: boolean;
    action_expire_reason?: string | null;
    result_summary?: {
        errors?: unknown;
        错误明细?: unknown;
        [key: string]: unknown;
    } | null;
    started_at: string | null;
    finished_at: string | null;
    created_at: string;
    updated_at?: string;
}

export interface TaskProgress {
    task_id: number;
    status: string;
    progress: number;
    result_success?: number;
    result_failed?: number;
    error_message?: string | null;
    error_reason?: string | null;
}

export interface TaskListParams {
    page?: number;
    page_size?: number;
    org_id?: number | string;
    status?: string;
    platform?: string;
    shop_id?: number | string;
    shop_name?: string;
    parsed_type?: string;
    parsed_year?: number;
    parsed_month?: number;
    keyword?: string;
    batch_id?: number;
    created_start_time?: string;
    created_end_time?: string;
}

export interface TaskBatchActionResult {
    total: number;
    success_count: number;
    failed_count: number;
    success_ids: number[];
    failed_items: Array<{
        task_id: number;
        message: string;
    }>;
}

export interface TaskSourceDownload {
    download_url: string;
    filename: string;
    expires_seconds: number;
}

/**
 * Get task list
 */
export function getTaskList(params: TaskListParams) {
    return get<PaginatedData<Task>>("/tasks", params);
}

/**
 * Get task detail
 */
export function getTaskDetail(id: number) {
    return get<Task>(`/tasks/${id}`);
}

/**
 * Get task progress (for polling)
 */
export function getTaskProgress(id: number) {
    return get<TaskProgress>(`/tasks/${id}/progress`);
}

/**
 * Retry a failed task.
 */
export function retryTask(id: number) {
    return post<Task>(`/tasks/${id}/retry`);
}

export function batchRetryTasks(taskIds: number[]) {
    return post<TaskBatchActionResult>("/tasks/batch/retry", { task_ids: taskIds });
}

/**
 * Recalculate an order-dependent task.
 */
export function recalculateTask(id: number) {
    return post<Task>(`/tasks/${id}/recalculate`);
}

export function batchRecalculateTasks(taskIds: number[]) {
    return post<TaskBatchActionResult>("/tasks/batch/recalculate", { task_ids: taskIds });
}

export function getTaskSourceDownload(id: number) {
    return post<TaskSourceDownload>(`/tasks/${id}/source-download`);
}
