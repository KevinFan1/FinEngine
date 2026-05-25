import { get } from "./index";
import type { PaginatedData } from "./index";
import { downloadBlob } from "./index";

interface SummaryMetricFields {
    order_paid_amount: number;
    refund_amount: number;
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
    org_id: number;
    org_name?: string | null;
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
    source_platform_code: string;
    report_platform_code: string;
    source_platform: string;
    report_platform: string;
    shop_name: string;
    shop_color?: string | null;
    created_at: string;
}

export interface SummaryReportRecord extends SummaryMetricFields, SummaryReportAdjustmentFields {
    id: string;
    org_id: number;
    org_name?: string | null;
    year: number;
    month: number;
    source_year: number;
    source_month: number;
    source_date: string;
    platform: string;
    platform_name: string;
    source_platform_code?: string;
    report_platform_code: string;
    report_platform: string;
    shop_id: number;
    shop_name: string;
    shop_color?: string | null;
    summary_count: number;
}

export interface SummaryListParams {
    page?: number;
    page_size?: number;
    summary_year?: number;
    summary_month?: number;
    summary_start_year?: number;
    summary_start_month?: number;
    summary_end_year?: number;
    summary_end_month?: number;
    source_year?: number;
    source_month?: number;
    source_start_year?: number;
    source_start_month?: number;
    source_end_year?: number;
    source_end_month?: number;
    accounting_year?: number;
    accounting_month?: number;
    accounting_start_year?: number;
    accounting_start_month?: number;
    accounting_end_year?: number;
    accounting_end_month?: number;
    platform_name?: string;
    report_platform_name?: string;
    shop_name?: string;
    keyword?: string;
    org_id?: number | string;
}

/**
 * Get summary list
 */
export function getSummaryList(params: SummaryListParams) {
    return get<PaginatedData<SummaryRecord>>("/summaries", params);
}

/**
 * Get accounting-month aggregated summary report
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
    summary_start_year?: number;
    summary_start_month?: number;
    summary_end_year?: number;
    summary_end_month?: number;
    source_year?: number;
    source_month?: number;
    source_start_year?: number;
    source_start_month?: number;
    source_end_year?: number;
    source_end_month?: number;
    platform_name?: string;
    report_platform_name?: string;
    shop_name?: string;
    keyword?: string;
    org_id?: number | string;
    scope?: "all" | "current_page" | "selected";
    ids?: string;
    page?: number;
    page_size?: number;
}): Promise<Blob> {
    return downloadBlob("/summaries/export", params);
}

/**
 * Export accounting-month aggregated summary report
 */
export async function exportSummaryReportExcel(params: {
    accounting_year?: number;
    accounting_month?: number;
    accounting_start_year?: number;
    accounting_start_month?: number;
    accounting_end_year?: number;
    accounting_end_month?: number;
    source_year?: number;
    source_month?: number;
    platform_name?: string;
    report_platform_name?: string;
    shop_name?: string;
    keyword?: string;
    org_id?: number | string;
    scope?: "all" | "current_page" | "selected";
    ids?: string;
    page?: number;
    page_size?: number;
}): Promise<Blob> {
    return downloadBlob("/summaries/report/export", params);
}
