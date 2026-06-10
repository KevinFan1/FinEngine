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
    mine_only?: boolean;
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
    file_size?: number | null;
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

type OssContent = Blob | ArrayBuffer | Uint8Array | string;
type OssGetResult = { content: OssContent };
type OssClient = {
    get: (name: string, options?: Record<string, any>) => Promise<OssGetResult>;
};

const OSS_DOWNLOAD_TIMEOUT = 2 * 60 * 1000;
const OSS_CHUNKED_DOWNLOAD_THRESHOLD = 32 * 1024 * 1024;
const OSS_DOWNLOAD_CHUNK_SIZE = 8 * 1024 * 1024;
const OSS_DOWNLOAD_PARALLEL = 4;

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
        timeout: OSS_DOWNLOAD_TIMEOUT,
    }) as OssClient;

    const fileSize = credential.file_size || 0;
    const blob =
        fileSize >= OSS_CHUNKED_DOWNLOAD_THRESHOLD
            ? await downloadOssObjectInChunks(client, credential.oss_key, fileSize)
            : await downloadOssObject(client, credential.oss_key);

    saveBlob(blob, credential.filename || "导出文件.xlsx");
}

async function downloadOssObject(client: OssClient, ossKey: string): Promise<Blob> {
    const result = await client.get(ossKey, { timeout: OSS_DOWNLOAD_TIMEOUT });
    return contentToBlob(result.content);
}

async function downloadOssObjectInChunks(client: OssClient, ossKey: string, fileSize: number): Promise<Blob> {
    const chunks = Array.from(
        { length: Math.ceil(fileSize / OSS_DOWNLOAD_CHUNK_SIZE) },
        (_, index) => {
            const start = index * OSS_DOWNLOAD_CHUNK_SIZE;
            const end = Math.min(start + OSS_DOWNLOAD_CHUNK_SIZE, fileSize) - 1;
            return { index, start, end };
        },
    );
    const parts = new Array<Blob>(chunks.length);
    let cursor = 0;

    async function worker() {
        while (cursor < chunks.length) {
            const chunk = chunks[cursor++];
            const result = await client.get(ossKey, {
                timeout: OSS_DOWNLOAD_TIMEOUT,
                headers: {
                    Range: `bytes=${chunk.start}-${chunk.end}`,
                },
            });
            parts[chunk.index] = contentToBlob(result.content);
        }
    }

    const workerCount = Math.min(OSS_DOWNLOAD_PARALLEL, chunks.length);
    await Promise.all(Array.from({ length: workerCount }, () => worker()));
    return new Blob(parts, {
        type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    });
}

function contentToBlob(content: OssContent): Blob {
    if (content instanceof Blob) return content;
    return new Blob([content]);
}

function saveBlob(blob: Blob, filename: string) {
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
}
