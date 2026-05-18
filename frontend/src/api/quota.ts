import { get, post } from "./index";

export interface QuotaInfo {
    plan_type: string;
    plan_expires_at: string | null;
    is_expired: boolean;
    users: {
        current: number;
        max: number;
        usage_percent: number;
        is_exceeded: boolean;
    };
    storage: {
        current_bytes: number;
        current_gb: number;
        max_bytes: number;
        max_gb: number;
        usage_percent: number;
        is_exceeded: boolean;
    };
    monthly_upload?: {
        current_bytes: number;
        current_gb: number;
        max_bytes: number;
        max_gb: number;
        usage_percent: number;
        is_exceeded: boolean;
    };
}

export interface UpdateQuotaRequest {
    max_users?: number;
    max_storage_gb?: number;
    plan_type?: string;
    plan_expires_at?: string;
}

/**
 * 获取当前组织的配额信息
 */
export function getQuota(): Promise<QuotaInfo> {
    return get<QuotaInfo>("/quota");
}

/**
 * 获取指定组织的配额信息（仅超级管理员）
 */
export function getOrgQuota(orgId: number): Promise<QuotaInfo> {
    return get<QuotaInfo>(`/quota/${orgId}`);
}

/**
 * 检查是否可以上传指定大小的文件
 */
export function checkUploadQuota(totalBytes: number): Promise<{ can_upload: boolean; message: string }> {
    return post<{ can_upload: boolean; message: string }>("/quota/check-upload", { total_bytes: totalBytes });
}

/**
 * 更新组织配额（仅超级管理员）
 */
export function updateQuota(orgId: number, data: UpdateQuotaRequest): Promise<void> {
    return post<void>(`/quota/${orgId}/update`, data);
}

/**
 * 重新计算组织存储使用量（仅超级管理员）
 */
export function recalculateStorage(orgId: number): Promise<void> {
    return post<void>(`/quota/${orgId}/recalculate`);
}
