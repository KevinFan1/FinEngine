import { get, post, put } from "./index";
import type { PaginatedData } from "./index";

export interface Organization {
    id: number;
    code: string;
    name: string;
    status: string;
    remark: string;
    created_at: string;
    updated_at: string;
}

export interface OrganizationListParams {
    page?: number;
    page_size?: number;
    keyword?: string;
    status?: string;
}

export interface OrganizationForm {
    name: string;
    code: string;
    remark?: string;
}

/**
 * Get organization list
 */
export function getOrganizationList(params: OrganizationListParams) {
    return get<PaginatedData<Organization>>("/organizations", params);
}

/**
 * Get all organizations (for dropdowns)
 */
export function getAllOrganizations() {
    return get<Organization[]>("/organizations", {});
}

/**
 * Create organization
 */
export function createOrganization(data: OrganizationForm) {
    return post<Organization>("/organizations", data);
}

/**
 * Update organization
 */
export function updateOrganization(id: number, data: OrganizationForm) {
    return put<Organization>(`/organizations/${id}`, data);
}

/**
 * Toggle organization status (enable/disable)
 */
export function toggleOrganizationStatus(id: number, status: string) {
    return put<Organization>(`/organizations/${id}`, { status });
}
