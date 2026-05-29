import { get, post } from "./index";
import type { PaginatedData } from "./index";

export interface UploadBatch {
    id: number;
    org_id: number;
    uploaded_by: number;
    file_count: number;
    status: string;
    created_at: string;
    files?: UploadFileRecord[];
}

export interface UploadFileRecord {
    id: number;
    batch_id: number;
    original_name: string;
    file_size: number;
    oss_key: string;
    platform: string;
    status: string;
    parsed_year?: number | null;
    parsed_month?: number | null;
    parsed_type: string;
    parsed_shop: string;
    created_at: string;
}

export interface OssStsCredential {
    access_key_id: string;
    access_key_secret: string;
    security_token: string;
    expiration: string;
    region: string;
    bucket: string;
    endpoint: string;
    oss_key_prefix: string;
}

export interface BatchListParams {
    page?: number;
    page_size?: number;
    org_id?: number;
    status?: string;
}

/**
 * Get upload batches list
 */
export function getUploadBatches(params: BatchListParams) {
    return get<PaginatedData<UploadBatch>>("/uploads/batches", params);
}

/**
 * Get batch detail with files
 */
export function getBatchDetail(id: number) {
    return get<UploadBatch>(`/uploads/batches/${id}`);
}

/**
 * Create upload batch
 */
export function createBatch(data: {
    file_count: number;
    total_bytes?: number;
    org_id?: number;
    remark?: string;
}) {
    return post<UploadBatch>("/uploads/batch", data);
}

/**
 * Get temporary Alibaba Cloud OSS credentials for a batch upload.
 */
export function getOssSts(batchId: number) {
    return get<OssStsCredential>("/oss/sts", { batch_id: batchId });
}

/**
 * Upload complete callback - notify backend that file has been uploaded
 */
export function uploadCallback(data: {
    batch_id: number;
    original_name: string;
    oss_key: string;
    file_size: number;
    file_hash?: string;
    parsed_year?: number | null;
    parsed_month?: number | null;
    parsed_type: string;
    parsed_shop: string;
    detected_platform: string;
}) {
    return post<null>("/uploads/callback", data);
}
