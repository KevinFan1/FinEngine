import { get } from "./index";
import type { PaginatedData } from "./index";
import { downloadBlob } from "./index";

interface SummaryMetricFields {
    real_gmv: number;
    platform_other_income: number;
    platform_service_fee: number;
    return_and_other_fee: number;
    daren_commission: number;
    zhaoshang_service_fee: number;
    outside_promotion_fee: number;
    service_provider_commission: number;
    payment_donation_fee: number;
    shipping_insurance: number;
    bic: number;
}

export interface SummaryReportAdjustmentFields {
    original_gmv: number;
    gmv_adjustment: number;
    original_return_cost: number;
    return_cost_adjustment: number;
}

export interface SummaryRecord extends SummaryMetricFields {
    id: number;
    shop_id: number;
    year: number;
    month: number;
    summary_year: number;
    summary_month: number;
    summary_date: string;
    source_year: number;
    source_month: number;
    source_date: string;
    platform: string;
    platform_name: string;
    shop_name: string;
    created_at: string;
}

export interface SummaryReportRecord extends SummaryMetricFields, SummaryReportAdjustmentFields {
    id: string;
    year: number;
    month: number;
    source_year: number;
    source_month: number;
    source_date: string;
    platform: string;
    platform_name: string;
    shop_id: number;
    shop_name: string;
    summary_count: number;
}

export interface SummaryListParams {
    page?: number;
    page_size?: number;
    summary_year?: number;
    summary_month?: number;
    source_year?: number;
    source_month?: number;
    platform_name?: string;
    shop_name?: string;
    org_id?: number;
}

/**
 * Get summary list
 */
export function getSummaryList(params: SummaryListParams) {
    return get<PaginatedData<SummaryRecord>>("/summaries", params);
}

/**
 * Get upload-month aggregated summary report
 */
export function getSummaryReportList(params: SummaryListParams) {
    return get<PaginatedData<SummaryReportRecord>>("/summaries/report", params);
}

/**
 * Export summary as Excel file (returns blob)
 */
export async function exportSummaryExcel(params: {
    summary_year?: number;
    summary_month?: number;
    source_year?: number;
    source_month?: number;
    platform_name?: string;
    shop_name?: string;
    scope?: "all" | "current_page" | "selected";
    ids?: string;
    page?: number;
    page_size?: number;
}): Promise<Blob> {
    return downloadBlob("/summaries/export", params);
}

/**
 * Export upload-month aggregated summary report
 */
export async function exportSummaryReportExcel(params: {
    source_year?: number;
    source_month?: number;
    platform_name?: string;
    shop_name?: string;
    scope?: "all" | "current_page" | "selected";
    ids?: string;
    page?: number;
    page_size?: number;
}): Promise<Blob> {
    return downloadBlob("/summaries/report/export", params);
}
