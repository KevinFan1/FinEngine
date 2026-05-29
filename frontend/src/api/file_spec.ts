import { del, get, post, put, type PaginatedData } from "./index";

export interface FileSpec {
    id: number;
    platform_id: number;
    platform_code: string;
    platform_name?: string;
    type_code: string;
    name: string;
    headers: string[];
    match_threshold: number;
    upload_period_header?: string | null;
    status: number;
    created_at: string;
    updated_at: string;
}

export interface FileSpecListParams {
    platform_code?: string;
    type_code?: string;
}

export interface FileSpecAdminListParams {
    page?: number;
    page_size?: number;
    platform_id?: number;
    type_code?: string;
    status?: number;
    keyword?: string;
}

export interface FileSpecPayload {
    platform_id: number;
    type_code: string;
    name: string;
    headers: string[];
    match_threshold: number;
    upload_period_header?: string | null;
    status: number;
}

/**
 * Get all enabled file specs (with platform info)
 * Used by upload page to auto-detect platform from Excel/CSV headers
 */
export async function getFileSpecs(
    params?: FileSpecListParams,
): Promise<FileSpec[]> {
    return get<FileSpec[]>("/file-specs", params);
}

export function getFileSpecsAdmin(params?: FileSpecAdminListParams) {
    return get<PaginatedData<FileSpec>>("/file-specs/admin", params);
}

export function createFileSpec(data: FileSpecPayload) {
    return post<FileSpec>("/file-specs", data);
}

export function updateFileSpec(id: number, data: Partial<FileSpecPayload>) {
    return put<FileSpec>(`/file-specs/${id}`, data);
}

export function deleteFileSpec(id: number) {
    return del<void>(`/file-specs/${id}`);
}
