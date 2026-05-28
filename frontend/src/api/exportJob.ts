import { get, post } from "./index";
import type { PaginatedData } from "./index";

export type ExportJobStatus = "queued" | "running" | "success" | "failed" | "expired";

export interface ExportJob {
    id: number;
    org_id?: number | null;
    user_id: number;
    operator_name?: string | null;
    module: string;
    export_type: string;
    title: string;
    filename: string;
    status: ExportJobStatus;
    progress: number;
    row_count?: number | null;
    file_size?: number | null;
    error_message?: string | null;
    result_summary?: Record<string, any> | null;
    started_at?: string | null;
    finished_at?: string | null;
    expires_at?: string | null;
    created_at: string;
    updated_at: string;
}

export interface CreateExportJobPayload {
    export_type: string;
    title: string;
    filename: string;
    params: Record<string, any>;
}

export interface ExportJobListParams {
    page?: number;
    page_size?: number;
    status?: ExportJobStatus | "";
    module?: string;
}

export interface ExportDownloadCredential {
    access_key_id: string;
    access_key_secret: string;
    security_token: string;
    expiration: string;
    region: string;
    bucket: string;
    endpoint: string;
    oss_key: string;
    filename: string;
}

export function createExportJob(data: CreateExportJobPayload) {
    return post<ExportJob>("/export-jobs", data);
}

export function listExportJobs(params: ExportJobListParams) {
    return get<PaginatedData<ExportJob>>("/export-jobs", params);
}

export function getExportJob(id: number) {
    return get<ExportJob>(`/export-jobs/${id}`);
}

export function getExportJobDownloadCredential(id: number) {
    return post<ExportDownloadCredential>(`/export-jobs/${id}/download-credential`);
}

export async function downloadExportJobFile(id: number) {
    const credential = await getExportJobDownloadCredential(id);
    const { default: OSS } = await import("ali-oss");
    const client = new OSS({
        region: credential.region,
        bucket: credential.bucket,
        endpoint: credential.endpoint,
        accessKeyId: credential.access_key_id,
        accessKeySecret: credential.access_key_secret,
        stsToken: credential.security_token,
        secure: credential.endpoint.startsWith("https://"),
    });
    const result = await client.get(credential.oss_key);
    const content = result.content as Blob | ArrayBuffer | Uint8Array;
    const blob = content instanceof Blob ? content : new Blob([content]);
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = credential.filename || "导出文件.xlsx";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
}
