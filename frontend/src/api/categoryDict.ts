import { del, get, post, put, type PaginatedData } from "./index";

export interface CategoryDict {
    id: number;
    platform_id: number;
    type_code: string;
    name: string;
    categories: Record<string, string[]>;
    status: number;
    created_at: string;
    updated_at: string;
}

export interface CategoryDictForm {
    platform_id: number;
    type_code: string;
    name: string;
    categories: Record<string, string[]>;
    status: number;
}

export interface CategoryDictListParams {
    page?: number;
    page_size?: number;
    platform_id?: number;
    type_code?: string;
}

export interface ClassifyRequest {
    text: string;
    platform_id: number;
    type_code: string;
}

export interface ClassifyResult {
    text: string;
    chinese_text: string;
    category: string | null;
    matched_keyword: string | null;
    match_type: "exact" | "contains" | "none" | string;
}

export function getCategoryDictList(params: CategoryDictListParams) {
    return get<PaginatedData<CategoryDict>>(
        "/category-dicts",
        params as Record<string, any>,
    );
}

export function createCategoryDict(data: CategoryDictForm) {
    return post<CategoryDict>("/category-dicts", data);
}

export function updateCategoryDict(
    id: number,
    data: Partial<CategoryDictForm>,
) {
    return put<CategoryDict>(`/category-dicts/${id}`, data);
}

export function deleteCategoryDict(id: number) {
    return del<void>(`/category-dicts/${id}`);
}

export function classifyCategoryText(data: ClassifyRequest) {
    return post<ClassifyResult>("/category-dicts/classify", data);
}
