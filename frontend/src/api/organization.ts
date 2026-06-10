import { get, post, put } from "./index";
import type { PaginatedData } from "./index";

export interface Organization {
    id: number;
    code: string;
    name: string;
    org_type: "internal" | "external";
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
    org_type: "internal" | "external";
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
export async function getAllOrganizations(): Promise<Organization[]> {
    const pageSize = 100;
    const organizations: Organization[] = [];
    let page = 1;
    let total = 0;

    do {
        const res = await get<PaginatedData<Organization>>("/organizations", { page, page_size: pageSize });
        const items = res.items || [];
        total = res.total || 0;
        organizations.push(...items);

        if (items.length < pageSize) {
            break;
        }
        page += 1;
    } while (organizations.length < total);

    return organizations;
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
