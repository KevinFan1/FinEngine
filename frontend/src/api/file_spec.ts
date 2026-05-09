import { get } from "./index";

export interface FileSpec {
    id: number;
    platform_id: number;
    platform_code: string;
    platform_name?: string;
    type_code: string;
    name: string;
    headers: string[];
    match_threshold: number;
    status: number;
    created_at: string;
    updated_at: string;
}

export interface FileSpecListParams {
    platform_code?: string;
    type_code?: string;
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
